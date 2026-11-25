#!/usr/bin/env python3
"""Write or review JLPT definitions through headless `claude -p` (no tools), one JSON batch per call.

    python3 scratch_offline/jlpt_defs_cli.py write  IN.json OUT.json [--model sonnet] [--chunk 25]
    python3 scratch_offline/jlpt_defs_cli.py review IN.json OUT.json [--model sonnet] [--chunk 25]

Same contract as the N3 subagent briefs (data/sense_seeding/ja_jlpt/n3_write_*/n3_review_*), but the text comes
back on stdout as a JSON array and is validated here (one entry per input, same order, shape rules); a chunk that
fails validation is retried once with the errors. Run with scratch_offline/bin first on PATH so the calls bill
the owner's API key. Usage per call is appended to OUT.json.usage.jsonl. Exits 3 on a credit/billing error.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor

REPO = '/home/user/LinguaLoop-web'
SKILLS = [f'{REPO}/.claude/skills/batch-sense-generation/SKILL.md', f'{REPO}/.claude/skills/cross-language-glosses/SKILL.md']
STOP_RE = re.compile(r'credit balance|billing|insufficient|quota', re.I)
WAIT_RE = re.compile(r'rate.?limit|overloaded|\b429\b|\b529\b', re.I)

RULES = """Key rules:
- ONE sense only: define exactly the sense given by jlpt_meaning + reading. Never join two meanings with 「また、」 or "; also" — a definition covering two senses is rejected downstream. If the hint lists several meanings, pick the first/central one.
- ja_simple: Japanese, child register (a primary schooler's 2000 words, compound sentences, literal/concrete), mostly hiragana, one or two short sentences, must not use the word itself or grammar terms like けんじょうご/そんけいご.
- ja_standard: ordinary Japanese dictionary definition (genus + distinguishing property).
- example: one short natural Japanese sentence (< ~60 chars) using the word, simple register.
- en_simple / zh_simple: single best equivalent (≤ 60 chars). zh in Simplified Chinese, natural Chinese (not copied Japanese kanji when that is not the Chinese word).
- en_standard / zh_standard: equivalent set with "; " / "；", clarifier after " — " / " —— " ONLY where the mapping is lossy; ≤ 120 chars; strictly longer than simple. No kana in en/zh glosses. Keep digits to a minimum in zh (a Chinese-character-ratio check applies).
- Honorific/humble words must be marked as such in all three languages.
- confidence: honest, 0-1."""

WRITE_TASK = """You are writing dictionary definitions for new Japanese words (JLPT {level}) for a language-learning app.
Input below: a JSON list of words with lemma, reading (hiragana), pos (English label), level, jlpt_meaning (English hint = WHICH sense to define).
Return ONLY a JSON array (no prose, no code fence), one object per input word, same order:
{{"lemma", "reading", "pos": "noun|verb|adjective|adverb|pronoun|particle|conjunction|auxiliary|adnominal|interjection|idiom|numeral|other", "confidence", "ja_simple", "ja_standard", "example", "en_simple", "en_standard", "zh_simple", "zh_standard"}}
or {{"lemma", "skip": true, "reason"}} only if it is genuinely not a word.
{rules}
Style reference (already accepted entries):
{style}
Input:
{items}"""

REVIEW_TASK = """You are reviewing pre-drafted dictionary definitions of Japanese words (JLPT {level}) before upload.
Input below: words with lemma, reading (hiragana), jlpt_meaning (English hint = the sense the exam means) and `draft` (pos in Japanese, def_ja_simple, def_ja_standard, def_en_simple, def_en_standard, def_zh_simple, def_zh_standard, example_ja).
For EVERY entry decide "ok" or "fix". Fix (rewrite only the fields that need it) when:
- the draft defines a different word or sense than reading + jlpt_meaning (e.g. a homophone);
- a definition joins TWO OR MORE meanings (「また、」, "; also", lists of distinct senses) — reduce it to the single sense the JLPT hint means;
- honorific/humble not marked; Japanese simple uses the word itself or grammar terms (けんじょうご etc.) or is not child register;
- en/zh gloss contains the Japanese word, uses kana, is a sentence, or zh copies Japanese kanji that are not natural Chinese;
- shape: en/zh simple ≤ 60 chars; standard ≤ 120 chars and strictly longer than simple (equivalent set "; "/"；", clarifier " — "/" —— " only where lossy); example < ~60 chars and uses the word; avoid many digits in zh.
Be strict on meaning and single-sense, light on style.
Return ONLY a JSON array (no prose, no code fence), one per input, same order: {{"lemma","verdict":"ok"}} or {{"lemma","verdict":"fix","note","changes":{{...draft field names...}}}}.
Input:
{items}"""

KANA = re.compile(r'[ぁ-ゟァ-ヿ]')


def shape_errors(e, pre=''):
    errs = []
    for l in ('en', 'zh'):
        s, t = e.get(f'{pre}{l}_simple') or '', e.get(f'{pre}{l}_standard') or ''
        if s or t:
            if not s or not t:
                errs.append(f'{l} simple/standard missing')
            elif len(s) > 60 or len(t) > 120 or len(t) <= len(s):
                errs.append(f'{l}: simple ≤60, standard ≤120 and longer than simple')
            if KANA.search(s + t):
                errs.append(f'{l} gloss contains kana')
    return errs


def validate(mode, inp, out):
    if not isinstance(out, list) or len(out) != len(inp):
        return [f'expected a JSON array of {len(inp)} objects, got {len(out) if isinstance(out, list) else type(out).__name__}']
    errs = []
    for a, b in zip(inp, out):
        if not isinstance(b, dict) or b.get('lemma') != a['lemma']:
            errs.append(f"order/lemma mismatch at {a['lemma']}")
            continue
        if mode == 'write':
            if b.get('skip'):
                continue
            for k in ('ja_simple', 'ja_standard', 'example', 'en_simple', 'en_standard', 'zh_simple', 'zh_standard'):
                if not str(b.get(k) or '').strip():
                    errs.append(f"{a['lemma']}: {k} empty")
            errs += [f"{a['lemma']}: {x}" for x in shape_errors(b)]
            if 'また、' in (b.get('ja_standard') or ''):
                errs.append(f"{a['lemma']}: ja_standard joins two senses (また、)")
        else:
            if b.get('verdict') not in ('ok', 'fix'):
                errs.append(f"{a['lemma']}: verdict must be ok or fix")
            elif b['verdict'] == 'fix':
                merged = dict(a['draft'])
                merged.update(b.get('changes') or {})
                errs += [f"{a['lemma']}: {x}" for x in shape_errors(merged, 'def_')]
    return errs


def call(system, prompt, model, usage_path, tag):
    for attempt in range(30):
        p = subprocess.run(['claude', '-p', '--model', model, '--tools', '', '--no-session-persistence',
                            '--output-format', 'json', '--system-prompt', system],
                           input=prompt, capture_output=True, text=True, cwd='/tmp', timeout=1800)
        try:
            res = json.loads(p.stdout)
        except json.JSONDecodeError:
            res = None
        blob = p.stdout + p.stderr
        if (res is None or res.get('is_error')) and STOP_RE.search(blob):
            print(f'STOP {tag}: billing/credit error: {blob[:300]}', flush=True)
            os._exit(3)
        if (res is None or res.get('is_error')) and WAIT_RE.search(blob):
            print(f'  [{tag}] rate limited; waiting 60s', flush=True)
            time.sleep(60)
            continue
        break
    if res is None or res.get('is_error'):
        raise RuntimeError(f'{tag}: CLI error {blob[:400]}')
    u = res.get('usage', {})
    with open(usage_path, 'a') as fh:
        fh.write(json.dumps({'tag': tag, 'model': model, 'cost_usd': res.get('total_cost_usd'),
                             'input': u.get('input_tokens'), 'output': u.get('output_tokens')}) + '\n')
    text = res.get('result') or ''
    m = re.search(r'\[.*\]', text, re.S)
    try:
        return json.loads(m.group(0) if m else text)
    except json.JSONDecodeError:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('mode', choices=['write', 'review'])
    ap.add_argument('inp')
    ap.add_argument('out')
    ap.add_argument('--model', default='sonnet')
    ap.add_argument('--chunk', type=int, default=25)
    ap.add_argument('--workers', type=int, default=6)
    ap.add_argument('--level', default='N2')
    args = ap.parse_args()
    items = json.load(open(args.inp))
    system = 'You write and check bilingual dictionary entries. House style follows.\n\n' + '\n\n'.join(open(s).read() for s in SKILLS)
    style = json.dumps(json.load(open(f'{REPO}/data/sense_seeding/ja_jlpt/n5n4_final.json'))[:4], ensure_ascii=False)
    chunks = [items[i:i + args.chunk] for i in range(0, len(items), args.chunk)]
    part_dir = args.out + '.parts'
    os.makedirs(part_dir, exist_ok=True)

    def run(ix):
        part = f'{part_dir}/{ix:03d}.json'
        if os.path.exists(part):
            return ix, 'cached'
        ch = chunks[ix]
        body = json.dumps(ch, ensure_ascii=False, indent=1)
        prompt = (WRITE_TASK.format(level=args.level, rules=RULES, style=style, items=body) if args.mode == 'write'
                  else REVIEW_TASK.format(level=args.level, items=body))
        out, errs = None, ['not run']
        for attempt in range(3):
            out = call(system, prompt, args.model, args.out + '.usage.jsonl', f'{args.mode}{ix}.{attempt}')
            errs = validate(args.mode, ch, out) if out is not None else ['reply was not a JSON array']
            if not errs:
                break
            prompt += '\n\nYour previous answer failed validation:\n- ' + '\n- '.join(errs[:30]) + \
                      '\nReturn the full corrected JSON array for ALL input words.'
        if errs:
            return ix, 'FAILED: ' + '; '.join(errs[:5])
        json.dump(out, open(part, 'w'), ensure_ascii=False, indent=1)
        return ix, 'ok'

    with ThreadPoolExecutor(args.workers) as pool:
        for ix, st in pool.map(run, range(len(chunks))):
            print(f'chunk {ix}: {st}', flush=True)
    parts = [f'{part_dir}/{i:03d}.json' for i in range(len(chunks))]
    if all(os.path.exists(p) for p in parts):
        json.dump([x for p in parts for x in json.load(open(p))], open(args.out, 'w'), ensure_ascii=False, indent=1)
        print('WROTE', args.out)
    else:
        print('INCOMPLETE: rerun to retry failed chunks')
        sys.exit(1)


if __name__ == '__main__':
    main()
