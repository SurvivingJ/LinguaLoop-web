"""Author and review particle-drill content with headless Claude workers.

Every job is two ``claude -p`` calls in separate contexts: an author writes the
files of one assignment, then an independent reviewer checks and repairs them.
No hosted model API is called: the workers are Claude Code headless sessions
(``claude -p``), which use the Claude Code login of the machine.

    python scripts/particle_drill_swarm.py plan            # list the jobs (writes nothing)
    python scripts/particle_drill_swarm.py plan --apply    # write the assignment files
    python scripts/particle_drill_swarm.py plan --topup --apply   # only what is under target
    python scripts/particle_drill_swarm.py run             # show what would run
    python scripts/particle_drill_swarm.py run --apply --jobs 10 [--kind items] [--only items-003]

A job is skipped when its output already exists and validates (author stage)
and its review record exists (review stage), so a run can be stopped and
restarted. Formats and rules: data/particle_drill/AUTHORING.md.
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

REPO = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import particle_drill_validate as validate  # noqa: E402

ROOT = validate.ROOT
COURSE = validate.COURSE                 # 'ja' (particles) or 'ja-grammar' (PD_COURSE)
GRAMMAR = COURSE != 'ja'
RUN_DIR = os.path.join(REPO, 'data', 'particle_drill', '_run' + ('-grammar' if GRAMMAR else ''))
VALIDATOR = 'grammar_drill_validate.py' if GRAMMAR else 'particle_drill_validate.py'
THEMES = ['home, family and daily routine', 'school, study and work',
          'travel, transport and the city', 'food, shopping and money',
          'hobbies, sport, nature and health', 'friends, plans, feelings and opinions']
AUTHOR_MODEL = {'items': 'sonnet', 'guides': 'opus', 'packs': 'opus', 'lex': 'sonnet', 'conj': 'opus',
                'kata': 'sonnet'}
REVIEW_MODEL = 'opus'
ALLOWED_TOOLS = 'Read,Write,Edit,Glob,Grep,Bash(python:*),Bash(python3:*),Bash(cd:*),Bash(wc:*),Bash(ls:*)'
TIMEOUT_S = 45 * 60

LEX = [
    ('lex-verbs-n5', 'conjugation/verbs_n5.json',
     'all the verbs of JLPT N5 (about 130): every common N5 verb, including the irregulars する and 来る, '
     'noun+する verbs such as 勉強する, and every N5 godan verb ending in -iru/-eru'),
    ('lex-verbs-n4', 'conjugation/verbs_n4.json',
     'about 170 verbs of JLPT N4 (not N5 ones): include transitive/intransitive partners (開ける/開く, '
     '閉める/閉まる, 付ける/付く, 消す/消える, 始める/始まる, 入れる/入る, 出す/出る, 落とす/落ちる, 壊す/壊れる, '
     '直す/直る, 決める/決まる, 集める/集まる, 続ける/続く, 変える/変わる, 止める/止まる, 並べる/並ぶ, 届ける/届く, '
     '見つける/見つかる, 育てる/育つ, 起こす/起きる ...) and the tricky godan -iru/-eru verbs'),
    ('lex-verbs-n3', 'conjugation/verbs_n3.json',
     'about 170 common verbs of JLPT N3 and N2 (none from N5 or N4), a mix of godan, ichidan and noun+する'),
    ('lex-adjectives', 'conjugation/adjectives.json',
     'about 130 i-adjectives and about 110 na-adjectives from JLPT N5 to N3 in one array (i-adjectives '
     'first). Beware na-adjectives that end in い (きれい, 嫌い, 有名, 得意 ... are "na") and list いい as 良い / よい'),
]


def _row(s):
    return {k: s[k] for k in ('id', 'p', 'title', 'lv', 'conf', 'ask') if k in s}


def _item_counts():
    counts = {}
    d = os.path.join(ROOT, 'items')
    for name in sorted(os.listdir(d)) if os.path.isdir(d) else []:
        if name.endswith('.jsonl'):
            with open(os.path.join(d, name), encoding='utf-8') as fh:
                n = sum(1 for line in fh if line.strip())
            sid = validate.skill_of(name)
            counts[sid] = counts.get(sid, 0) + n
    return counts


def build_plan(topup=False, tag=''):
    """{job_id: assignment}. With ``topup`` only item tasks for skills under target."""
    catalog = validate.load_catalog()
    skills = catalog['skills']
    jobs = {}
    if topup:
        have = _item_counts()
        tasks = []
        for s in skills:
            short = s['n'] - have.get(s['id'], 0)
            if short > 0:
                tasks.append({**_row(s), 'n': short + 2,
                              'file': f"items/{s['id']}__{tag or 't'}.jsonl",
                              'theme': THEMES[len(tasks) % 6], 'part': 'top-up (avoid repeating the '
                              f"sentences already in items/{s['id']}*.jsonl; read them first)"})
        batch, total = [], 0
        for t in tasks:
            if batch and (total + t['n'] > 70 or len(batch) >= 5):
                jobs[f"items-{tag or 't'}{len(jobs):03d}"] = {'kind': 'items', 'tasks': batch}
                batch, total = [], 0
            batch.append(t)
            total += t['n']
        if batch:
            jobs[f"items-{tag or 't'}{len(jobs):03d}"] = {'kind': 'items', 'tasks': batch}
        return jobs

    batches, cur = [], None
    for s in skills:
        if s['n'] > 70:
            k = math.ceil(s['n'] / 65)
            per = math.ceil(s['n'] / k / 5) * 5
            left = s['n']
            for i in range(k):
                n = min(per, left)
                left -= n
                batches.append({'tasks': [{**_row(s), 'n': n, 'file': f"items/{s['id']}__{i + 1}.jsonl",
                                           'theme': THEMES[i % 6], 'part': f'{i + 1} of {k}'}]})
            cur = None
            continue
        if cur is None or cur['stage'] != s['stage'] or cur['total'] + s['n'] > 80 or len(cur['tasks']) >= 4:
            cur = {'stage': s['stage'], 'total': 0, 'tasks': []}
            batches.append(cur)
        cur['tasks'].append({**_row(s), 'n': s['n'], 'file': f"items/{s['id']}.jsonl",
                             'theme': 'mixed everyday topics', 'part': '1 of 1'})
        cur['total'] += s['n']
    for i, b in enumerate(batches):
        jobs[f'items-{i:03d}'] = {'kind': 'items', 'tasks': b['tasks']}

    by_id = {s['id']: s for s in skills}
    gb, cur = [], None
    for st in catalog['stages']:
        for g in st['groups']:
            w = len(g['skills'])
            if cur is None or cur['st'] != st['id'] or cur['w'] + w > 6:
                cur = {'st': st['id'], 'w': 0, 'groups': []}
                gb.append(cur)
            cur['groups'].append({'group': g['id'], 'p': g['p'], 'name': g['name'],
                                  'file': f"guides/{g['id']}.json",
                                  'skills': [_row(by_id[k]) for k in g['skills']]})
            cur['w'] += w
    for i, b in enumerate(gb):
        jobs[f'guides-{i:03d}'] = {'kind': 'guides', 'groups': b['groups']}

    pb, cur = [], None
    for s in skills:
        if not s['packs']:
            continue
        if cur is None or cur['st'] != s['stage'] or cur['w'] + s['packs'] > 7:
            cur = {'st': s['stage'], 'w': 0, 'tasks': []}
            pb.append(cur)
        cur['tasks'].append({**_row(s), 'packs': s['packs'], 'file': f"packs/{s['id']}.json"})
        cur['w'] += s['packs']
    for i, b in enumerate(pb):
        jobs[f'packs-{i:03d}'] = {'kind': 'packs', 'tasks': b['tasks']}

    if GRAMMAR:
        jobs['kata-list'] = {'kind': 'kata', 'file': 'reading/katakana.json'}
        return jobs
    for jid, path, what in LEX:
        jobs[jid] = {'kind': 'lex', 'file': path, 'what': what}
    jobs['conj-guide'] = {'kind': 'conj', 'file': 'conjugation/guide.json'}
    return jobs


def job_files(job):
    if job['kind'] in ('items', 'packs'):
        return [t['file'] for t in job['tasks']]
    if job['kind'] == 'guides':
        return [g['file'] for g in job['groups']]
    return [job['file']]


# --------------------------------------------------------------------------- prompts
def common():
    if GRAMMAR:
        return f"""You are one member of a content team for a Japanese grammar drill in the repository {REPO}. This is a content-writing task only: do not touch the wiki, do not commit, do not edit any file other than the ones named in your assignment, and do not call any external model API.
First read {REPO}/data/particle_drill/AUTHORING.md and then {REPO}/data/particle_drill/AUTHORING_GRAMMAR.md in full. Together they define the file formats and the quality rules, and they override your habits; where they differ, AUTHORING_GRAMMAR.md wins. THIS IS THE GRAMMAR COURSE: wherever these instructions say "particle", read "the expression in the slot" (a verb, a pattern, a connector, an adverb, a kanji word ...); one slot per sentence is enough and particles are NOT marked; a skill that covers a set of words rotates its answers over the set. Each task row gives the skill's "title" (the words or patterns it covers) and, for the kanji areas, "ask". Skill ids come from {REPO}/data/particle_drill/{COURSE}/catalog.json (grep it for ids; do not read all of it unless you need to). All content paths below are relative to {REPO}/data/particle_drill/{COURSE}/.
Validator (read-only): cd {REPO} && python scripts/{VALIDATOR} <relative paths>. It must end with "0 errors" for your files."""
    return f"""You are one member of a content team for a Japanese particle drill in the repository {REPO}. This is a content-writing task only: do not touch the wiki, do not commit, do not edit any file other than the ones named in your assignment, and do not call any external model API.
First read {REPO}/data/particle_drill/AUTHORING.md in full: it defines the file formats and the quality rules, and it overrides your habits. Skill ids come from {REPO}/data/particle_drill/ja/catalog.json (grep it for ids; do not read all of it unless you need to). All content paths below are relative to {REPO}/data/particle_drill/ja/.
Validator (read-only): cd {REPO} && python scripts/particle_drill_validate.py <relative paths>. It must end with "0 errors" for your files."""


def author_prompt(jid, job, plan_path):
    kind = job['kind']
    if kind == 'items':
        return f"""{common()}

YOUR ASSIGNMENT: {plan_path} lists one or more tasks. For each task write the exercise file named in "file" (section 2 of AUTHORING.md) for the skill "id": at least "n" items (up to 5 extra are welcome), one JSON object per line.
- The task gives the particle ("p"), the function ("title"), the skill's JLPT level ("lv"), the usual confusions ("conf"), a topic theme and which part of the skill this is. Lean on the theme for about two thirds of the sentences so parallel parts do not duplicate each other.
- About 70% of the items use vocabulary no harder than the skill's level; the rest may be one or two levels harder. Set each item's "lv" honestly.
- Before writing, think through the skill precisely: what makes this particle right, and for each distractor why a native speaker would reject it in THAT sentence. Use the skill's own function in every focus slot; do not drift into another function of the same particle.
- Mark every other real particle in each sentence as a slot with the right catalog skill id and generous alternatives.
- Write the file with the Write tool, run the validator on it, fix, repeat until 0 errors. Then re-read your file once as a strict Japanese teacher and replace any sentence that is unnatural, ambiguous, or whose distractors could be accepted.
Finish with one line: the files you wrote and the item count of each."""
    if kind == 'guides':
        return f"""{common()}

YOUR ASSIGNMENT: {plan_path} lists particle groups. For each group write the guide file named in "file" (section 4 of AUTHORING.md), covering exactly the group's skills in the given order.
The guide is what the learner reads before drilling, and re-reads after mistakes. Aim for the clarity of the best grammar references (Tae Kim, A Dictionary of Basic Japanese Grammar, Imabi) but shorter: one core image per particle, a recitable rule per skill, the real boundary with the neighbouring particles, the mistakes English speakers actually make, and a sub-second test the learner can apply mid-sentence. Every Japanese example must be natural and correctly marked up with full furigana. State exceptions that matter (for example: relative time words take no に). For clinic groups (ids starting clinic- or x-) the guide is a decision procedure: the questions to ask, in order, to choose between the particles, with minimal pairs as examples.
Run the validator on your files until 0 errors, then re-read each guide once for accuracy.
Finish with one line naming the files you wrote."""
    if kind == 'packs':
        return f"""{common()}

YOUR ASSIGNMENT: {plan_path} lists skills with a number of pattern packs each ("packs"). For each task write the pack file named in "file" (section 3 of AUTHORING.md): a JSON array with that many packs for the skill "id", ids "<skill>-1", "<skill>-2", ...
A pack is a frame whose parts are swapped at random to give endless drill sentences, so EVERY combination must be natural Japanese, must keep every particle answer and alternative correct, and must make every distractor plainly wrong. Design each pack so this holds by construction: pick semantically tight value sets (all places where one can do every listed action; all people who could do them), keep dependent parts inside one value, and avoid values that would make a distractor acceptable. 6 to 10 values per variable, 150+ combinations, English that reads correctly for every combination. Different packs of one skill use clearly different frames. For clinic skills (x-...), build packs whose values force one member of the set, and split the members across packs.
After writing, test yourself: pick 12 random combinations per pack, write them out in full, and reject any that sound odd; fix the value sets. Run the validator on your files until 0 errors.
Finish with one line naming the files you wrote and the number of packs in each."""
    if kind == 'kata':
        return f"""{common()}

YOUR ASSIGNMENT: write {job['file']} (section 7 of AUTHORING_GRAMMAR.md): a JSON array of about 600 common katakana loanwords for a speed-reading drill, one object per line inside the array, most common first: about 200 at JLPT N5 to N4 (コーヒー, テレビ, パン ...), 250 at N3 and 150 at N2 to N1, across food, technology, work, sport, clothes, places and abstract words. Include words with small ッ, long ー, and the extended sounds (ファ, ティ, ウィ, ヴ, デュ) so every reading habit is drilled. Spell each word the standard dictionary way. No brands, no personal names, no duplicates. Run the validator on the file until 0 errors.
Finish with one line: the file and the entry count."""
    if kind == 'lex':
        return f"""{common()}

YOUR ASSIGNMENT: write {job['file']} (section 5 of AUTHORING.md): a JSON array of {job['what']}. One object per entry, each on its own line inside the array. The class field decides how the drill conjugates the word, so a wrong class produces wrong answers for every form: verify each entry individually, especially verbs ending in る. Order by frequency (most common first). No duplicates. Run the validator on the file until 0 errors.
Finish with one line: the file and the entry count."""
    return f"""{common()}

YOUR ASSIGNMENT: write {REPO}/data/particle_drill/ja/conjugation/guide.json: the conjugation guides shown beside an endless conjugation drill. A JSON array, one object per topic, in this exact order of "id":
verb-groups, masu, te, ta, nai, nakatta, potential, passive, causative, causative-passive, volitional, imperative, prohibitive, ba, tara, tai, tari, i-adjectives, na-adjectives, copula, transitive-intransitive.
Each object: {{"id":"te","title":"て-form","rule":"one recitable sentence","explain":"2 to 4 short paragraphs separated by blank lines","table":[["ending","becomes","example"]],"examples":[{{"jp":"...","en":"..."}}],"mistakes":[{{"bad":"...","good":"...","note":"..."}}],"tip":"..."}}
Use the furigana markup of section 1 in all Japanese. Be exact and complete: this is the reference the learner trusts."""


def review_prompt(jid, job, plan_path):
    kind = job['kind']
    record = f'{REPO}/data/particle_drill/{COURSE}/review/{jid}.json'
    if kind == 'kata':
        return f"""{common()}

YOU ARE THE INDEPENDENT REVIEWER of {job['file']} (section 7 of AUTHORING_GRAMMAR.md). You did not write it. Check every entry: is it a real, common loanword; is the katakana spelling the standard dictionary spelling (long vowels, small ッ, ィ / ェ / ォ); is the gloss right; is the level plausible. Remove brands, names and rare words; fix spellings in place. Run the validator until 0 errors.
Then write {record}: {{"batch":"{jid}","files":["{job['file']}"],"checked":N,"fixed":N,"deleted":N,"issues":[{{"entry":"...","problem":"...","action":"..."}}]}}. Writing this record is required: it marks the review as done."""
    if kind == 'items':
        return f"""{common()}

YOU ARE THE INDEPENDENT REVIEWER of the exercise files named in {plan_path} (the "file" of each task). You did not write them. Assume there are mistakes: a typical batch has several. Read every line and judge it as a native-level Japanese teacher:
1. The sentence is natural, correct standard Japanese; the furigana readings are right for this context; the English is an accurate, natural translation.
2. The focus slot (index "f") really drills the file's skill, and its answer is right.
3. ADVERSARIAL DISTRACTOR CHECK. For each distractor in "d", put it in the blank and ask: could a native speaker say this and still mean the English given? If the result is acceptable or only slightly marked, the item is wrong. Fix it: move an equally natural particle into the slot's alternatives ({{a/b|skill}}) and replace the distractor with a plainly wrong particle; or rewrite the sentence so the distractor becomes impossible. Watch especially: は/も standing in for が/を; へ for に; が for は (and the reverse) without context that forces one; から vs ので; けど vs が; と vs や; だけ vs しか where the negative is not in the blank; に vs で with verbs that take both.
4. Every other slot: the answer is right, the skill id fits its function, and every equally natural alternative is listed.
5. "why" states the real reason, correctly, in plain English. "lv" is plausible.
6. Within a file: no near-duplicates, reasonable variety.
Fix problems in place with the Edit tool (rewrite the line). Delete a line only if it cannot be repaired; if you delete, write a replacement item of the same skill so the count does not drop. Do not reformat lines you do not change. Run the validator on the files until 0 errors.
Then write {record}: {{"batch":"{jid}","files":[...],"checked":N,"fixed":N,"deleted":N,"replaced":N,"issues":[{{"file":"...","jp_before":"...","problem":"...","action":"..."}}]}} listing every change you made (an empty "issues" list if you changed nothing). Writing this record is required: it marks the review as done."""
    if kind == 'guides':
        return f"""{common()}

YOU ARE THE INDEPENDENT REVIEWER of the guide files named in {plan_path} (the "file" of each group). You did not write them. Check every statement as a Japanese linguist and every example as a native-level teacher:
- Is each rule true as stated? Are the stated exceptions right, and is an important exception missing? Would following the rule mechanically produce errors?
- Is every example natural, with the particle used in exactly the function the skill teaches, correct furigana, accurate English?
- In "mistakes": is the "bad" sentence really wrong (not merely less common), and is the "good" one right?
- In "contrast": is the description of the other particle accurate?
- Is the writing direct and free of filler; is the "tip" usable in under a second?
Fix problems in place (Edit). Keep the format. Run the validator until 0 errors.
Then write {record}: {{"batch":"{jid}","files":[...],"checked":<skills>,"fixed":N,"deleted":0,"issues":[{{"file":"...","problem":"...","action":"..."}}]}}. Writing this record is required: it marks the review as done."""
    if kind == 'packs':
        return f"""{common()}

YOU ARE THE INDEPENDENT REVIEWER of the pattern-pack files named in {plan_path} (the "file" of each task). You did not write them. A pack generates sentences from every combination of its values, so one bad value poisons many sentences. For each pack:
- Expand combinations systematically (each value of each variable against at least three values of the others) and judge each sentence: natural? every slot answer right? every equally natural alternative listed? each distractor in "d" plainly wrong for EVERY combination? English correct for every combination (agreement, articles, tense)?
- Check that the focus index "f" points at the intended slot for every combination (values with slots shift indexes).
- Remove or replace values that break any combination; tighten the frame if needed. Keep at least 6 values per variable and 150 combinations.
Print expansions with: cd {REPO} && python scripts/{VALIDATOR} --expand packs/<skill>.json
Fix in place, run the validator until 0 errors.
Then write {record}: {{"batch":"{jid}","files":[...],"checked":<packs>,"fixed":N,"deleted":N,"issues":[{{"file":"...","pack":"...","problem":"...","action":"..."}}]}}. Writing this record is required: it marks the review as done."""
    if kind == 'lex':
        return f"""{common()}

YOU ARE THE INDEPENDENT REVIEWER of {job['file']} (section 5 of AUTHORING.md). You did not write it. Check every entry: reading, class (godan / ichidan / suru / kuru, or i / na), transitivity for verbs, gloss, level. For every verb ending in る decide deliberately: is the negative ～らない (godan) or ～ない (ichidan)? For every adjective ending in い: is the negative ～くない (i) or ～じゃない (na)? Remove entries whose conjugation is irregular beyond する / 来る / 行く / ある / 良い, and the honorific ～ます verbs (いらっしゃる, おっしゃる, くださる, なさる, ござる must be removed). Fix in place, run the validator until 0 errors.
Then write {record}: {{"batch":"{jid}","files":["{job['file']}"],"checked":N,"fixed":N,"deleted":N,"issues":[{{"entry":"...","problem":"...","action":"..."}}]}}. Writing this record is required: it marks the review as done."""
    return f"""{common()}

YOU ARE THE INDEPENDENT REVIEWER of {REPO}/data/particle_drill/ja/conjugation/guide.json, the conjugation guides shown beside an endless conjugation drill (a JSON array of topics: id, title, rule, explain, table, examples, mistakes, tip). You did not write it. Check every rule, every table row and every example as a Japanese linguist: the sound changes of the て/た forms, the exceptions (行く→行って, ある→ない, する, 来る readings, 良い), which verbs have no short causative-passive, ら-dropping, the particles each form governs. Every "bad" sentence must really be wrong and every "good" one right; furigana must be correct. Fix in place with Edit, keep the structure, and make sure the file still loads as JSON.
Then write {record}: {{"batch":"{jid}","files":["conjugation/guide.json"],"checked":<topics>,"fixed":N,"deleted":0,"issues":[{{"topic":"...","problem":"...","action":"..."}}]}}. Writing this record is required: it marks the review as done."""


# --------------------------------------------------------------------------- running
_print_lock = threading.Lock()


def say(msg):
    with _print_lock:
        print(time.strftime('%H:%M:%S'), msg, flush=True)


def files_valid(job):
    """(ok, detail): every output file exists and passes the validator."""
    catalog = validate.load_catalog()
    skills = {s['id']: s for s in catalog['skills']}
    for rel in job_files(job):
        path = os.path.join(ROOT, rel)
        if not os.path.exists(path) or os.path.getsize(path) == 0:
            return False, f'{rel} missing'
        kind = rel.split('/')[0]
        try:
            if kind == 'items':
                errs, n = validate.check_items_file(path, skills)
                want = next(t['n'] for t in job['tasks'] if t['file'] == rel)
                if not errs and n < want * 0.9:
                    errs = [f'{rel}: {n} items, wanted {want}']
            elif kind == 'packs':
                errs, _n = validate.check_packs_file(path, skills)
            elif kind == 'guides':
                errs = validate.check_guide_file(path, catalog)
            elif kind == 'reading':
                errs, n = validate.check_katakana_file(path)
                if not errs and n < 450:
                    errs = [f'{rel}: {n} entries, wanted about 600']
            elif os.path.basename(rel).startswith('guide'):
                with open(path, encoding='utf-8') as fh:
                    errs = [] if isinstance(json.load(fh), list) else ['guide.json is not a list']
            else:
                errs, _n = validate.check_lexicon_file(path)
        except Exception as exc:  # noqa: BLE001
            errs = [f'{rel}: {exc}']
        if errs:
            return False, errs[0]
    return True, ''


def call_claude(prompt, model, log_path):
    env = dict(os.environ)
    for name in ('ANTHROPIC_API_KEY', 'CLAUDE_API', 'CLAUDE_API_KEY', 'OPENROUTER_API_KEY'):
        env.pop(name, None)      # the workers use the Claude Code login, never a hosted API key
    cmd = ['claude', '-p', prompt, '--model', model, '--permission-mode', 'acceptEdits',
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
        fh.write(json.dumps({'model': model, 'exit': code, 'cost': cost, 'out': out[-3000:]},
                            ensure_ascii=False) + '\n')
    return code, cost


def run_job(jid, job, plan_dir, log_dir, review_only=False):
    plan_path = os.path.join(plan_dir, f'{jid}.json')
    log_path = os.path.join(log_dir, f'{jid}.log')
    record = os.path.join(ROOT, 'review', f'{jid}.json')
    cost = 0.0
    ok, detail = files_valid(job)
    if not ok and review_only:
        return jid, 'skipped (not authored)', cost
    tries = 0
    while not ok and tries < 2:
        tries += 1
        say(f'{jid}: author ({AUTHOR_MODEL[job["kind"]]}), try {tries}: {detail}')
        _code, c = call_claude(author_prompt(jid, job, plan_path), AUTHOR_MODEL[job['kind']], log_path)
        cost += c
        ok, detail = files_valid(job)
    if not ok:
        return jid, f'AUTHOR FAILED: {detail}', cost
    tries = 0
    while not os.path.exists(record) and tries < 2:
        tries += 1
        say(f'{jid}: review ({REVIEW_MODEL}), try {tries}')
        _code, c = call_claude(review_prompt(jid, job, plan_path), REVIEW_MODEL, log_path)
        cost += c
    if not os.path.exists(record):
        return jid, 'REVIEW FAILED: no review record', cost
    ok, detail = files_valid(job)
    return jid, ('done' if ok else f'INVALID AFTER REVIEW: {detail}'), cost


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('plan')
    p.add_argument('--topup', action='store_true', help='only item jobs for skills under their target')
    p.add_argument('--tag', default='', help='suffix for top-up part files and job ids (one per top-up round)')
    p.add_argument('--apply', action='store_true', help='write the assignment files')
    r = sub.add_parser('run')
    r.add_argument('--apply', action='store_true', help='start the workers')
    r.add_argument('--jobs', type=int, default=8)
    r.add_argument('--kind', action='append', help='items, guides, packs, lex or conj (repeatable)')
    r.add_argument('--only', action='append', help='job id (repeatable)')
    r.add_argument('--prefix', help='only job ids starting with this')
    for q in (p, r):
        q.add_argument('--run-dir', default=RUN_DIR)
    args = ap.parse_args()
    plan_dir = os.path.join(args.run_dir, 'plan')
    log_dir = os.path.join(args.run_dir, 'logs')

    if args.cmd == 'plan':
        jobs = build_plan(topup=args.topup, tag=args.tag)
        kinds = {}
        for job in jobs.values():
            kinds[job['kind']] = kinds.get(job['kind'], 0) + 1
        print(f'{len(jobs)} jobs: {kinds}')
        if args.apply:
            os.makedirs(plan_dir, exist_ok=True)
            for jid, job in jobs.items():
                with open(os.path.join(plan_dir, f'{jid}.json'), 'w', encoding='utf-8') as fh:
                    json.dump(job, fh, ensure_ascii=False, indent=1)
            print('wrote', plan_dir)
        return 0

    jobs = {}
    for name in sorted(os.listdir(plan_dir)) if os.path.isdir(plan_dir) else []:
        with open(os.path.join(plan_dir, name), encoding='utf-8') as fh:
            jobs[name[:-5]] = json.load(fh)
    if args.kind:
        jobs = {j: v for j, v in jobs.items() if v['kind'] in args.kind}
    if args.only:
        jobs = {j: v for j, v in jobs.items() if j in args.only}
    if args.prefix:
        jobs = {j: v for j, v in jobs.items() if j.startswith(args.prefix)}
    todo = {j: v for j, v in jobs.items()
            if not (files_valid(v)[0] and os.path.exists(os.path.join(ROOT, 'review', f'{j}.json')))}
    print(f'{len(jobs)} jobs selected, {len(todo)} to run')
    if not args.apply:
        for j in list(todo)[:40]:
            print(' ', j)
        return 0
    os.makedirs(log_dir, exist_ok=True)
    os.makedirs(os.path.join(ROOT, 'review'), exist_ok=True)
    total, failed = 0.0, []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as pool:
        futures = [pool.submit(run_job, j, v, plan_dir, log_dir) for j, v in todo.items()]
        for n, fut in enumerate(concurrent.futures.as_completed(futures), 1):
            jid, status, cost = fut.result()
            total += cost
            if status != 'done':
                failed.append(jid)
            say(f'[{n}/{len(futures)}] {jid}: {status} (notional ${cost:.2f}, total ${total:.2f})')
    print(f'finished: {len(todo) - len(failed)} done, {len(failed)} failed: {failed}')
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
