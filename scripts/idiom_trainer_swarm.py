"""Author and review idiom-trainer content with headless Claude workers.

Every job is two ``claude -p`` calls in separate contexts: an author writes
the file, then an independent reviewer checks and repairs it. Both run on
Opus (owner, 2026-11-28: "run on opus for authoring"). No hosted model API is
called: the workers are Claude Code headless sessions, which use the Claude
Code login of the machine.

    python scripts/idiom_trainer_swarm.py plan                    # what is missing
    python scripts/idiom_trainer_swarm.py run                     # show what would run
    python scripts/idiom_trainer_swarm.py run --apply --jobs 8 [--kind list|cards] [--lang zh] [--only JOB]

Jobs:
  list-<lang>-<set>        lists/<set>.json: the ranked core list of a set
  cards-<lang>-<set>-NN    cards/<set>-NN.json: full cards for ten idioms of the reviewed list
A job is skipped when its file validates and its review record exists, so a
run can be restarted. Card jobs exist only for sets whose list has been reviewed.
Formats and rules: data/idioms/AUTHORING.md; checks: scripts/idiom_trainer.py.
"""
import argparse
import concurrent.futures
import json
import math
import os
import subprocess
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import idiom_trainer as it  # noqa: E402

REPO = it.REPO
RUN_DIR = os.path.join(it.DATA, '_run')
MODEL = 'opus'
ALLOWED_TOOLS = 'Read,Write,Edit,Glob,Grep,Bash(python:*),Bash(python3:*),Bash(cd:*),Bash(wc:*),Bash(ls:*)'
TIMEOUT_S = 50 * 60
LANG_NAME = {'zh': 'Chinese', 'ja': 'Japanese'}
#: a reviewed list may be shorter than the core size: the reviewer removes what does not belong
LIST_FLOOR = 0.85


def rel(path):
    return os.path.relpath(path, REPO)


def review_path(job_id, lang):
    return os.path.join(it.DATA, lang, 'review', job_id + '.json')


def jobs():
    out = {}
    for lang, sets in it.SETS.items():
        for key, code, title, en, core in sets:
            jid = f'list-{lang}-{key}'
            out[jid] = {'kind': 'list', 'lang': lang, 'set': key, 'code': code, 'title': title, 'en': en,
                        'core': core, 'file': it.list_path(lang, key)}
            if not os.path.exists(review_path(jid, lang)):
                continue                      # cards wait for the reviewed list
            n = math.ceil(len(it.load_list(lang, key)) / it.CHUNK)
            for i in range(1, n + 1):
                cid = f'cards-{lang}-{key}-{i:02d}'
                out[cid] = {'kind': 'cards', 'lang': lang, 'set': key, 'title': title, 'en': en, 'n': i,
                            'ids': it.chunk_ids(lang, key, i),
                            'file': os.path.join(it.DATA, lang, 'cards', f'{key}-{i:02d}.json')}
    return out


def authored_ok(job):
    if not os.path.exists(job['file']):
        return False, 'file missing'
    floor = int(job['core'] * LIST_FLOOR) if job['kind'] == 'list' else None
    problems = it.validate_file(job['file'], floor)
    return (not problems), (problems[0] if problems else '')


def reviewed_ok(jid, job):
    if not os.path.exists(review_path(jid, job['lang'])):
        return False, 'review record missing'
    return authored_ok(job)


# --------------------------------------------------------------------------- prompts
def common(job):
    return f"""You are one member of a content team for an idiom trainer in the repository {REPO}. This is a content-writing task only: do not touch the wiki, do not commit, do not edit any file other than the ones named in your assignment, and do not call any external model API.
First read {REPO}/data/idioms/AUTHORING.md in full: it defines the file formats and the quality rules, and it overrides your habits. The learner is an English speaker; the language is {LANG_NAME[job['lang']]}. An idiom taught with a wrong meaning, register or origin is worse than no idiom: when you are not certain, leave it out or say less.
Check (read-only, from the repo root): cd {REPO} && python scripts/idiom_trainer.py validate <file> . It must print "0 problems" for your file."""


def author_prompt(jid, job):
    if job['kind'] == 'list':
        return f"""{common(job)}

YOUR ASSIGNMENT: write {rel(job['file'])} (section 2 of AUTHORING.md): the CORE list of the set "{job['set']}" ({job['title']}, {job['en']}): exactly {job['core']} entries, ids {job['code']}001 upward, most useful first, one JSON object per line inside the array.
- This is the first tier a learner studies, so every entry must earn its place: the expressions a learner at intermediate to upper-intermediate level actually meets in conversation, drama, news and ordinary writing today. Rank by present-day frequency and usefulness; leave out the dated, the bookish, the regional, the vulgar and anything a native speaker would recognise but not use.
- Spread the entries over the themes (tag) so the set is not twenty ways to say one thing; where two expressions mean nearly the same, keep the more common one.
- The meaning line ("mean") must be specific enough to identify this expression among the others of the set: no two entries may share one.
- Verify each reading. For Chinese give the dictionary reading of every character (tone marks; neutral tone unmarked only where the dictionary has it).
Run the validator on the file until it prints "0 problems", then re-read the list once as a native-speaking teacher and replace anything that does not belong in a core list.
Finish with one line: the file and the entry count."""
    return f"""{common(job)}

YOUR ASSIGNMENT: write {rel(job['file'])} (section 3 of AUTHORING.md): the full cards for these ten entries of {rel(it.list_path(job['lang'], job['set']))}, in this order: {', '.join(job['ids'])}. Read those entries from the list file and copy id, t, r, mean, lvl and tag unchanged.
For each idiom, think first, then write:
- What exactly does it mean, who says it, about what, in which register and tone? Where is its edge: the situation where a learner would use it and be wrong?
- THE STORY. Does it have a real origin: a classical text, a fable, a historical episode, a religious or theatrical term, a known first use? If you are sure of it, tell it plainly as it is traditionally told and name the source. If there is none, or you are not sure of the details or the source, set "story" to null and make "lit" (the literal image) carry the memory. Never invent, embellish or guess a source.
- Six contexts that show its range, each a different situation and sentence shape, easiest first, natural and modern; the idiom once, in braces, in the form it takes there. From the situation alone a learner should be able to tell that this idiom, and not a near-synonym in the set, is the one that fits.
- Two misuses a learner would really write, each clearly wrong to a native speaker, with the reason.
- A cue in English: a situation that calls for this idiom and no other.
Write the file with the Write tool, run the validator until it prints "0 problems", then re-read every card once as a strict native-speaking teacher and fix anything unnatural, ambiguous or uncertain.
Finish with one line: the file and how many of the ten cards have a story."""


def review_prompt(jid, job):
    record = rel(review_path(jid, job['lang']))
    if job['kind'] == 'list':
        return f"""{common(job)}

YOU ARE THE INDEPENDENT REVIEWER of {rel(job['file'])}, the core list of the set "{job['set']}" ({job['title']}). You did not write it. Go through every entry as a native-speaking teacher choosing what a learner should study first:
1. Does it belong in a CORE list: in real present-day use, not dated, bookish, regional or vulgar? Remove what does not, and replace it with a more useful expression that is missing (give it the removed entry's id) so the list stays near {job['core']} entries; do not pad with weak entries.
2. Is the text the standard form and is the reading right, character by character?
3. Is the meaning line accurate, and specific enough that no other entry could be described the same way?
4. Level and theme plausible? Is the order roughly most useful first? Are there near-duplicates (keep the more common)?
Fix in place with Edit; keep ids unique and in the same code. Run the validator until it prints "0 problems" (a reviewed list may hold as few as {int(job['core'] * LIST_FLOOR)} entries: run it with --min-entries {int(job['core'] * LIST_FLOOR)}).
Then write {record}: {{"job":"{jid}","file":"{rel(job['file'])}","checked":N,"fixed":N,"removed":N,"added":N,"issues":[{{"entry":"...","problem":"...","action":"..."}}]}}. Writing this record is required: it marks the review as done."""
    return f"""{common(job)}

YOU ARE THE INDEPENDENT REVIEWER of {rel(job['file'])} (ten idiom cards of the set "{job['set']}"). You did not write it. Assume there are mistakes. For every card:
1. STORY CHECK, the strictest one. If "story" is not null: is this the origin as it is traditionally told, are the details right, and is the named source right? If you cannot stand behind every part of it, cut it back to what is certain or set it to null. If "story" is null but the idiom has a well-known origin you are sure of, add it. A wrong story is a defect; a missing one is not.
2. Meaning, literal sense, register, tone and the "how" line: accurate?
3. Each of the six contexts: natural modern {LANG_NAME[job['lang']]}; the idiom used correctly and in a form it really takes; the English accurate; the six really different. ADVERSARIAL CHECK: could a near-synonym from the same set fill the braces just as well? Then rewrite the context so this idiom is the one that fits.
4. The two misuses: clearly wrong to a native speaker, not merely unusual? Is the reason right?
5. The cue: does it call for this idiom and no other? "near": is the stated difference true? "parts": a natural place to cut?
6. Japanese: furigana on every kanji, correct readings in context.
Fix problems in place with Edit; keep id, t, r, mean, lvl and tag as in the list (if one of those is wrong, fix the list file entry too and say so in the record). Run the validator until it prints "0 problems".
Then write {record}: {{"job":"{jid}","file":"{rel(job['file'])}","checked":10,"fixed":N,"stories_kept":N,"stories_removed":N,"stories_added":N,"issues":[{{"idiom":"...","problem":"...","action":"..."}}]}}. Writing this record is required: it marks the review as done."""


# --------------------------------------------------------------------------- running
_lock = threading.Lock()


def say(msg):
    with _lock:
        print(time.strftime('%H:%M:%S'), msg, flush=True)


def call_claude(prompt, log_path):
    env = dict(os.environ)
    for name in ('ANTHROPIC_API_KEY', 'CLAUDE_API', 'CLAUDE_API_KEY', 'OPENROUTER_API_KEY'):
        env.pop(name, None)      # the workers use the Claude Code login, never a hosted API key
    cmd = ['claude', '-p', prompt, '--model', MODEL, '--permission-mode', 'acceptEdits',
           '--allowedTools', ALLOWED_TOOLS, '--output-format', 'json']
    try:
        proc = subprocess.run(cmd, cwd=REPO, env=env, capture_output=True, text=True, timeout=TIMEOUT_S)
        out, code = proc.stdout, proc.returncode
    except subprocess.TimeoutExpired:
        out, code = 'timeout', -1
    cost = 0.0
    try:
        cost = float(json.loads(out).get('total_cost_usd') or 0)
    except (ValueError, AttributeError):
        pass
    with open(log_path, 'a', encoding='utf-8') as fh:
        fh.write(json.dumps({'model': MODEL, 'exit': code, 'cost': cost, 'out': out[-3000:]},
                            ensure_ascii=False) + '\n')
    return cost


def run_job(jid, job):
    log_path = os.path.join(RUN_DIR, 'logs', jid + '.log')
    cost = 0.0
    for attempt in (1, 2, 3):
        ok, detail = authored_ok(job)
        if ok:
            break
        say(f'{jid}: author ({MODEL}), try {attempt}: {detail[:90]}')
        cost += call_claude(author_prompt(jid, job), log_path)
    else:
        return jid, f'AUTHOR FAILED: {authored_ok(job)[1][:120]}', cost
    for attempt in (1, 2, 3):
        if reviewed_ok(jid, job)[0]:
            return jid, 'done', cost
        say(f'{jid}: review ({MODEL}), try {attempt}')
        cost += call_claude(review_prompt(jid, job), log_path)
    ok, detail = reviewed_ok(jid, job)
    return jid, ('done' if ok else f'REVIEW FAILED: {detail[:120]}'), cost


def pending(all_jobs):
    return {j: v for j, v in all_jobs.items() if not reviewed_ok(j, v)[0]}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    sub.add_parser('plan')
    r = sub.add_parser('run')
    r.add_argument('--apply', action='store_true', help='start the workers')
    r.add_argument('--jobs', type=int, default=8)
    r.add_argument('--kind', action='append', help='list or cards (repeatable)')
    r.add_argument('--lang', action='append', help='zh or ja (repeatable)')
    r.add_argument('--only', action='append', help='job id (repeatable)')
    args = ap.parse_args()
    todo = pending(jobs())
    if args.cmd == 'plan':
        for jid in todo:
            print(jid)
        print(f'{len(todo)} jobs to do')
        return 0
    if args.kind:
        todo = {j: v for j, v in todo.items() if v['kind'] in args.kind}
    if args.lang:
        todo = {j: v for j, v in todo.items() if v['lang'] in args.lang}
    if args.only:
        todo = {j: v for j, v in todo.items() if j in args.only}
    print(f'{len(todo)} to run')
    if not args.apply:
        for jid in todo:
            print(' ', jid)
        return 0
    os.makedirs(os.path.join(RUN_DIR, 'logs'), exist_ok=True)
    for lang in it.SETS:
        for d in ('lists', 'cards', 'review'):
            os.makedirs(os.path.join(it.DATA, lang, d), exist_ok=True)
    total, failed, done = 0.0, [], 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as pool:
        for jid, status, cost in pool.map(lambda kv: run_job(*kv), todo.items()):
            total += cost
            done += 1
            if status != 'done':
                failed.append(jid)
            say(f'[{done}/{len(todo)}] {jid}: {status} (notional ${cost:.2f}, total ${total:.2f})')
    say(f'finished: {done - len(failed)} done, {len(failed)} not done: {failed}')
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
