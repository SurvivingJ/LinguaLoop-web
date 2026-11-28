"""Author and blind-review Chinese grammar-drill content with headless Claude workers.

The content contract is data/grammar_drills/zh/SPEC.md and the checks are
scripts/grammar_drills.py. This script only runs the workers: for every job an
author writes the file, then a reviewer in a separate context checks it. No
hosted model API is called: the workers are Claude Code headless sessions
(``claude -p``), which use the Claude Code login of the machine.

    python scripts/grammar_drills_swarm.py plan                 # what is missing (writes nothing)
    python scripts/grammar_drills_swarm.py run                  # show what would run
    python scripts/grammar_drills_swarm.py run --apply --jobs 6 [--kind guide|batch|words] [--only JOB]
    python scripts/grammar_drills_swarm.py build-words --apply  # words/polyphones.json -> generators/polyphones-data.js

Jobs, from plan.json:
  guide-<slug>       guides/<slug>.json, then a reviewer checks it (verdicts/guide-<slug>.json)
  batch-<slug>-NN    batches/<slug>-NN.jsonl, then a blind review as SPEC.md describes:
                     strip -> the reviewer solves the blind file -> compare -> full review
                     -> reviewed/<slug>-NN.jsonl + verdicts/<slug>-NN.json
  words-polyphones   words/polyphones.json (the table behind the generated
                     "which reading?" drill), then a reviewer (verdicts/words-polyphones.json)
A job is skipped when its outputs exist and validate, so a run can be restarted.
Batches wait for their topic's guide (the validator needs its sub-points).
"""
import argparse
import concurrent.futures
import json
import os
import re
import subprocess
import sys
import threading
import time

REPO = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import grammar_drills as gd  # noqa: E402

ROOT = os.path.join(REPO, 'data', 'grammar_drills', 'zh')
RUN_DIR = os.path.join(ROOT, '_run')
WORDS = os.path.join(ROOT, 'words', 'polyphones.json')
WORDS_JS = os.path.join(REPO, 'static', 'js', 'grammar', 'generators', 'polyphones-data.js')
MIN_WORDS = 240
AUTHOR_MODEL = {'guide': 'opus', 'batch': 'sonnet', 'words': 'sonnet'}
REVIEW_MODEL = 'opus'
ALLOWED_TOOLS = 'Read,Write,Edit,Glob,Grep,Bash(python:*),Bash(python3:*),Bash(cd:*),Bash(wc:*),Bash(ls:*)'
TIMEOUT_S = 50 * 60
_SYL = re.compile(r'^[a-zāáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜü]+$')


def rel(path):
    return os.path.relpath(path, REPO)


# --------------------------------------------------------------------------- jobs
def jobs():
    plan = gd.load_plan()
    out = {}
    themes = plan['themes']
    for t in plan['topics']:
        slug = t['slug']
        if not t.get('added'):
            continue          # the first build is complete; this runner never reopens it
        # Topics added after the first build carry "added"; the first 39 guides were
        # reviewed with their batches and have no guide verdict of their own.
        if not os.path.exists(gd.guide_path(slug)) or (
                t.get('added') and not os.path.exists(verdict('guide-' + slug))):
            out['guide-' + slug] = {'kind': 'guide', 'slug': slug, 'topic': t}
        for n in range(1, t['batches'] + 1):
            name = f'{slug}-{n:02d}'
            k = (sum(map(ord, slug)) + n * 7) % len(themes)
            out['batch-' + name] = {'kind': 'batch', 'slug': slug, 'name': name, 'n': n, 'topic': t,
                                    'themes': [themes[(k + i * 3) % len(themes)] for i in range(6)]}
    if any(t['slug'] == 'polyphones' for t in plan['topics']):
        out['words-polyphones'] = {'kind': 'words'}
    return out


def verdict(name):
    return os.path.join(ROOT, 'verdicts', name + '.json')


def check_words(path=WORDS):
    """Problems of the polyphone table (a list of strings)."""
    try:
        with open(path, encoding='utf-8') as fh:
            rows = json.load(fh)
    except (OSError, ValueError) as exc:
        return [f'{rel(path)}: {exc}']
    if not isinstance(rows, list):
        return ['must be a JSON array']
    errs, seen = [], set()
    for i, r in enumerate(rows):
        where = f'[{i}] {r.get("w") if isinstance(r, dict) else r}'
        if not isinstance(r, dict) or set(r) != {'w', 'py', 'i', 'wrong', 'en', 'why', 'lvl'}:
            errs.append(f'{where}: needs exactly w, py, i, wrong, en, why, lvl')
            continue
        w, py, idx, wrong = r['w'], r['py'], r['i'], r['wrong']
        syl = py.split(' ') if isinstance(py, str) else []
        if not isinstance(w, str) or not 2 <= len(w) <= 6 or not re.match(r'^[一-鿿]+$', w):
            errs.append(f'{where}: w must be 2 to 6 Chinese characters (a word, not a bare character)')
            continue
        if len(syl) != len(w) or not all(_SYL.match(s) for s in syl):
            errs.append(f'{where}: py needs one lower-case syllable with tone marks per character')
            continue
        if isinstance(idx, bool) or not isinstance(idx, int) or not 0 <= idx < len(w):
            errs.append(f'{where}: i must index the character asked about')
            continue
        known = gd.readings(w[idx])
        if len(known) < 2:
            errs.append(f'{where}: {w[idx]} has one reading only')
        if syl[idx] not in known:
            errs.append(f'{where}: {syl[idx]} is not a reading of {w[idx]} (known: {sorted(known)})')
        if (not isinstance(wrong, list) or not 1 <= len(wrong) <= 3 or len(set(wrong)) != len(wrong)
                or not all(isinstance(x, str) and _SYL.match(x) for x in wrong)):
            errs.append(f'{where}: wrong must be 1 to 3 different syllables')
        else:
            if syl[idx] in wrong:
                errs.append(f'{where}: the right reading is among the wrong ones')
            for x in wrong:
                if x not in known:
                    errs.append(f'{where}: wrong reading {x} is not a reading of {w[idx]}')
        if not isinstance(r['en'], str) or not re.search(r'[A-Za-z]', r['en']):
            errs.append(f'{where}: en missing')
        if not isinstance(r['why'], str) or not 15 <= len(r['why']) <= 200:
            errs.append(f'{where}: why must be 15 to 200 characters')
        if r['lvl'] not in (1, 2, 3):
            errs.append(f'{where}: lvl must be 1, 2 or 3')
        if (w, idx) in seen:
            errs.append(f'{where}: listed twice')
        seen.add((w, idx))
    if len(rows) < MIN_WORDS:
        errs.append(f'{len(rows)} entries; at least {MIN_WORDS} wanted')
    return errs


def authored_ok(job):
    """(ok, detail) for the author's output."""
    plan = gd.load_plan()
    if job['kind'] == 'guide':
        path = gd.guide_path(job['slug'])
        if not os.path.exists(path):
            return False, 'guide missing'
        problems = gd.validate_guide(path, plan, quiet=True)
        problems = problems[1] if isinstance(problems, tuple) else problems
        return (not problems), (problems[0] if problems else '')
    if job['kind'] == 'words':
        errs = check_words()
        return (not errs), (errs[0] if errs else '')
    path = os.path.join(ROOT, 'batches', job['name'] + '.jsonl')
    if not os.path.exists(path):
        return False, 'batch missing'
    _, problems = gd.validate_file(path, plan, quiet=True)
    return (not problems), (problems[0] if problems else '')


def reviewed_ok(job):
    plan = gd.load_plan()
    if job['kind'] == 'guide':
        return os.path.exists(verdict('guide-' + job['slug'])), 'review record missing'
    if job['kind'] == 'words':
        return os.path.exists(verdict('words-polyphones')), 'review record missing'
    path = os.path.join(ROOT, 'reviewed', job['name'] + '.jsonl')
    if not os.path.exists(path) or not os.path.exists(verdict(job['name'])):
        return False, 'reviewed file or verdict missing'
    _, problems = gd.validate_file(path, plan, quiet=True, min_items=90)
    return (not problems), (problems[0] if problems else '')


# --------------------------------------------------------------------------- prompts
def common():
    return f"""You are one member of a content team for Chinese grammar drills in the repository {REPO}. This is a content-writing task only: do not touch the wiki, do not commit, do not edit any file other than the ones named in your assignment, and do not call any external model API.
First read {REPO}/data/grammar_drills/zh/SPEC.md in full: it is the content contract and it overrides your habits. The topic list is {REPO}/data/grammar_drills/zh/plan.json (find your topic's entry; do not read all of it). A wrong answer key teaches a falsehood: correctness beats volume and cleverness. When you are not certain, write a different sentence.
Checks (read-only, from the repo root): cd {REPO} && python scripts/grammar_drills.py validate <file.jsonl> ; python scripts/grammar_drills.py validate-guide <file.json>. They must report no problems for your files."""


def author_prompt(jid, job):
    if job['kind'] == 'guide':
        t = job['topic']
        return f"""{common()}

YOUR ASSIGNMENT: write the guide {REPO}/data/grammar_drills/zh/guides/{t['slug']}.json (section "Guide file" of SPEC.md) for the topic "{t['slug']}": {t['title']}.
Scope of the topic (plan.json): {t['scope']}
The guide is what the learner reads before drilling and after mistakes: a summary with the one idea that makes the topic click, 5 to 10 sub-points with short lowercase keys that together cover the scope (item batches will be written against exactly these keys, so choose them to be drillable and of similar size), a recitable rule per sub-point with natural examples (Chinese, pinyin with tone marks, English), wrong/right contrasts showing the mistakes English speakers really make, and reflex-speed cheat lines. Be exact; state the exceptions that matter.
Run validate-guide on the file until it reports no problems, then re-read it once for accuracy.
Finish with one line naming the file."""
    if job['kind'] == 'words':
        return f"""{common()}

YOUR ASSIGNMENT: write {rel(WORDS)}: the table behind a generated drill that shows a word and asks how one of its characters is read (多音字, characters with more than one reading). A JSON array of about 300 entries, one object per line inside the array:
  {{"w":"银行","py":"yín háng","i":1,"wrong":["xíng","hàng"],"en":"bank","why":"行 is háng for a row, a line of business or a firm (银行, 行业); xíng is to go or to be all right.","lvl":1}}
- "w": a common word or short phrase of 2 to 6 characters that fixes the reading; "py": its pinyin, one lower-case syllable with tone marks per character, neutral tone unmarked; "i": the index (from 0) of the character asked about; "wrong": 1 to 3 OTHER real readings of that same character (never an invented one, never the right one); "en": a short gloss of the word; "why": one English sentence (15 to 200 characters) giving the rule of thumb for this reading against the others; "lvl": 1 (HSK 1-2), 2 (HSK 3) or 3 (HSK 4 and above).
- Cover the characters learners actually misread, several words for each reading: 行 长 得 了 还 重 乐 觉 便 都 为 教 好 少 数 种 发 干 看 空 难 强 相 处 调 传 当 倒 倍? (skip characters with one reading) 差 假 间 角 结 尽 卷 量 落 没 闷 泊 且? 曲 散 舍 省 似 宿 弹 挑 吐 系 兴 要 应 载 着 正 只 转 背 藏 朝 冲 大 单 地 的 肚 分 缝 更 冠 号 和 华 划 几 夹 将 降 禁 劲 卡 壳 累 露 率 模 那 宁 片 铺 切 任 少 盛 什 说 汤? 提 体? 同? 为 鲜 血 咽 与 晕 扎 中 种 重 钻 作.
- About one third level 1, one third level 2, one third level 3. Use each reading in its most common words first. Do not list a word whose reading is disputed or varies by region (for example 血 xuè/xiě in one word): choose words where dictionaries agree.
Check it: cd {REPO} && python scripts/grammar_drills_swarm.py check-words . It must print "0 problems".
Finish with one line: the file and the entry count."""
    t = job['topic']
    return f"""{common()}

YOUR ASSIGNMENT: write batch {job['n']} of {t['batches']} for the topic "{t['slug']}" ({t['title']}): the file {REPO}/data/grammar_drills/zh/batches/{job['name']}.jsonl, 100 items (ids {job['name']}-001 upward), one JSON object per line.
- First read the topic guide {REPO}/data/grammar_drills/zh/guides/{t['slug']}.json: every item's "sub" is one of its sub-point keys. Spread the items over the sub-points, weighted toward the ones learners get wrong most.
- Scope of the topic: {t['scope']}
- Type mix for this topic (per 100 items): {json.dumps(t['mix'])}. Follow the item rules of SPEC.md for each type exactly.
- Themes for this batch, so that parallel batches do not collide: {', '.join(job['themes'])}. Keep about two thirds of the sentences on them.
- Before writing, think through each sub-point: what makes the answer right, and for every distractor why a native speaker would reject it in THAT sentence. Exactly one option of a cloze may be acceptable; a "wrong" judge sentence must be clearly wrong, not merely less common.
- Write the file, run validate on it, fix, repeat until it reports no problems. Then re-read the whole file once as a strict Chinese teacher and replace anything unnatural, ambiguous or with an acceptable distractor.
Finish with one line: the file and the item count."""


def review_prompt(jid, job):
    if job['kind'] == 'guide':
        slug = job['slug']
        return f"""{common()}

YOU ARE THE INDEPENDENT REVIEWER of the guide {REPO}/data/grammar_drills/zh/guides/{slug}.json. You did not write it. Check every statement as a Chinese linguist and every example as a native-level teacher: is each rule true as stated, are the exceptions right, would following it mechanically produce errors; is every example natural with correct pinyin (tone marks, neutral tones, one syllable per character) and accurate English; is each "wrong" sentence really wrong; do the sub-points cover the topic's scope in plan.json and are they drillable. Fix problems in place with Edit, keep the format and the sub-point keys unless one is unusable, and run validate-guide until it reports no problems.
Then write {REPO}/data/grammar_drills/zh/verdicts/guide-{slug}.json: {{"file":"guides/{slug}.json","checked":<sub-points>,"fixed":N,"issues":[{{"problem":"...","action":"..."}}]}}. Writing this record is required: it marks the review as done."""
    if job['kind'] == 'words':
        return f"""{common()}

YOU ARE THE INDEPENDENT REVIEWER of {rel(WORDS)} (a JSON array: w = word, py = its pinyin, i = index of the character asked about, wrong = other real readings of that character, en, why, lvl). You did not write it. Check every entry: is the pinyin of the whole word right (tone marks, neutral tones); is the reading of the character at index i the standard one in THIS word; is every "wrong" reading a real reading of that character and really wrong here; is the gloss right; does "why" state a true and useful rule; is the level plausible. Remove entries whose reading is disputed, regional or rare, and rare words. Fix in place and keep at least {MIN_WORDS} entries (write replacements if you remove many). Run: cd {REPO} && python scripts/grammar_drills_swarm.py check-words until it prints "0 problems".
Then write {REPO}/data/grammar_drills/zh/verdicts/words-polyphones.json: {{"file":"words/polyphones.json","checked":N,"fixed":N,"dropped":N,"issues":[{{"entry":"...","problem":"...","action":"..."}}]}}. Writing this record is required: it marks the review as done."""
    name = job['name']
    return f"""{common()}

YOU ARE THE INDEPENDENT BLIND REVIEWER of the batch batches/{name}.jsonl (topic "{job['slug']}"). You did not write it. Assume there are mistakes: a typical batch has ten or more. Work in this order, and do NOT open batches/{name}.jsonl before step 3.
STEP 1 (blind solve). Run: cd {REPO} && python scripts/grammar_drills.py strip data/grammar_drills/zh/batches/{name}.jsonl . Read data/grammar_drills/zh/blind/{name}.blind.jsonl (the items without their answers) and the topic guide guides/{job['slug']}.json. Solve every item yourself and write data/grammar_drills/zh/blind/{name}.answers.jsonl, one object per line: for a cloze {{"id":"...","ok":[indexes of EVERY option a native speaker would accept]}}; for an order or rewrite item {{"id":"...","zh":"the sentence you would build, without punctuation"}}; for a judge item {{"id":"...","ok":true or false}}.
STEP 2 (compare). Run: python scripts/grammar_drills.py compare data/grammar_drills/zh/batches/{name}.jsonl and note every flag (KEY REJECTED, AMBIGUOUS, DIFFERENT ORDER, JUDGEMENT DIFFERS).
STEP 3 (full review). Now read batches/{name}.jsonl. For every flagged item decide who is right and repair the item: an ambiguous cloze gets a sentence that forces one option or a plainly wrong distractor; an order/rewrite item gets every other correct order in "alts"; a judge item whose "wrong" sentence natives accept is rewritten. Then read every other item as a native-level teacher: natural Chinese, correct pinyin (tone marks, neutral tones, one syllable per character), accurate English, a "why" that states the real reason, a plausible level, the right sub-point.
Write the repaired batch to data/grammar_drills/zh/reviewed/{name}.jsonl (every item, fixed or not; keep the ids; drop an item only if it cannot be repaired, and then write a replacement with the next free id so the count does not fall). Run validate on the reviewed file until it reports no problems.
Then write data/grammar_drills/zh/verdicts/{name}.json: {{"flagged":N,"fixed":N,"dropped":N,"added":N,"summary":"two or three sentences: what the blind compare flagged, the systematic defects you fixed, judgement calls you left","items":{{"<id>":{{"v":"fixed|dropped|added","note":"..."}}}}}}. Writing this record is required: it marks the review as done."""


# --------------------------------------------------------------------------- running
_lock = threading.Lock()


def say(msg):
    with _lock:
        print(time.strftime('%H:%M:%S'), msg, flush=True)


def call_claude(prompt, model, log_path):
    env = dict(os.environ)
    for name in ('ANTHROPIC_API_KEY', 'CLAUDE_API', 'CLAUDE_API_KEY', 'OPENROUTER_API_KEY'):
        env.pop(name, None)
    cmd = ['claude', '-p', prompt, '--model', model, '--output-format', 'json',
           '--allowedTools', ALLOWED_TOOLS, '--permission-mode', 'acceptEdits']
    try:
        proc = subprocess.run(cmd, cwd=REPO, env=env, capture_output=True, text=True, timeout=TIMEOUT_S)
        out, code = proc.stdout, proc.returncode
    except subprocess.TimeoutExpired:
        out, code = '', -1
    cost = 0.0
    try:
        cost = float(json.loads(out).get('total_cost_usd') or 0)
    except (ValueError, AttributeError):
        pass
    with open(log_path, 'a', encoding='utf-8') as fh:
        fh.write(json.dumps({'model': model, 'exit': code, 'cost': cost, 'out': out[-3000:]}) + '\n')
    return code, cost


def run_job(jid, job):
    log_path = os.path.join(RUN_DIR, 'logs', jid + '.log')
    cost = 0.0
    if job['kind'] == 'batch' and not os.path.exists(gd.guide_path(job['slug'])):
        return jid, 'waiting for its guide', cost
    for attempt in (1, 2, 3):
        ok, detail = authored_ok(job)
        if ok:
            break
        say(f'{jid}: author ({AUTHOR_MODEL[job["kind"]]}), try {attempt}: {detail[:90]}')
        cost += call_claude(author_prompt(jid, job), AUTHOR_MODEL[job['kind']], log_path)[1]
    else:
        return jid, f'AUTHOR FAILED: {authored_ok(job)[1][:120]}', cost
    for attempt in (1, 2, 3):
        ok, detail = reviewed_ok(job)
        if ok:
            return jid, 'done', cost
        say(f'{jid}: review ({REVIEW_MODEL}), try {attempt}')
        cost += call_claude(review_prompt(jid, job), REVIEW_MODEL, log_path)[1]
    ok, detail = reviewed_ok(job)
    return jid, ('done' if ok else f'REVIEW FAILED: {detail[:120]}'), cost


def pending(all_jobs):
    return {j: v for j, v in all_jobs.items() if not (authored_ok(v)[0] and reviewed_ok(v)[0])}


def build_words(apply):
    errs = check_words()
    if errs:
        print('\n'.join(errs[:20]))
        return 1
    with open(WORDS, encoding='utf-8') as fh:
        rows = json.load(fh)
    body = ('// Generated by scripts/grammar_drills_swarm.py build-words from\n'
            '// data/grammar_drills/zh/words/polyphones.json (authored and reviewed). Do not edit.\n'
            '// [word, pinyin, index of the character asked about, wrong readings, gloss, why, level]\n'
            'export const POLYPHONES = [\n'
            + ''.join('  ' + json.dumps([r['w'], r['py'], r['i'], r['wrong'], r['en'], r['why'], r['lvl']],
                                        ensure_ascii=False) + ',\n' for r in rows)
            + '];\n')
    current = open(WORDS_JS, encoding='utf-8').read() if os.path.exists(WORDS_JS) else ''
    print(f'{len(rows)} entries; {rel(WORDS_JS)} {"is current" if current == body else "differs"}')
    if apply and current != body:
        with open(WORDS_JS, 'w', encoding='utf-8') as fh:
            fh.write(body)
        print('wrote', rel(WORDS_JS))
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    sub.add_parser('plan')
    sub.add_parser('check-words')
    b = sub.add_parser('build-words')
    b.add_argument('--apply', action='store_true')
    r = sub.add_parser('run')
    r.add_argument('--apply', action='store_true', help='start the workers')
    r.add_argument('--jobs', type=int, default=6)
    r.add_argument('--kind', action='append', help='guide, batch or words (repeatable)')
    r.add_argument('--only', action='append', help='job id (repeatable)')
    args = ap.parse_args()
    if args.cmd == 'check-words':
        errs = check_words()
        print('\n'.join(errs[:60]))
        print(f'{len(errs)} problems')
        return 1 if errs else 0
    if args.cmd == 'build-words':
        return build_words(args.apply)
    todo = pending(jobs())
    if args.cmd == 'plan':
        for jid in todo:
            print(jid)
        print(f'{len(todo)} jobs to do')
        return 0
    if args.kind:
        todo = {j: v for j, v in todo.items() if v['kind'] in args.kind}
    if args.only:
        todo = {j: v for j, v in todo.items() if j in args.only}
    print(f'{len(todo)} to run')
    if not args.apply:
        for jid in todo:
            print(' ', jid)
        return 0
    os.makedirs(os.path.join(RUN_DIR, 'logs'), exist_ok=True)
    for d in ('batches', 'blind', 'reviewed', 'verdicts', 'guides', 'words'):
        os.makedirs(os.path.join(ROOT, d), exist_ok=True)
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
