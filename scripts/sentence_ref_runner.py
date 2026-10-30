#!/usr/bin/env python3
"""Sentence-reference authoring harness (TASK-903, ADR-037).

File-based. No command calls a hosted model; authors and reviewers are Claude
subagents driven by .claude/skills/sentence-reference-authoring and
.claude/skills/sentence-reference-review.

    export       --language ja --l1 en --limit 30 --arm aligned --out-dir RUN
                 (reads test_sentences via the admin client; --fixture FILE reads
                 an offline JSON with tests[] instead, segmenting on the fly)
    brief        RUN [--width 6]     briefs/author_NN.md + rules_authoring.md
    check        RUN [--source docs|reviewed] [--tests id,id]
    review-pack  RUN [--width 6]     review_packs/review_NN.md + rules_review.md
    tightness    RUN                 score back_translations/*.json -> verdicts
    assemble     RUN                 reviewed/ + verdicts/ -> upload.json
    status       RUN

Layout under RUN/sentence_refs/:
    worklist.json               canonical sentences per test (from export)
    briefs/author_NN.md         what one author subagent reads
    docs/<test_id>.<l1>.json    authored documents
    check.json                  last check result
    review_packs/review_NN.md   what one reviewer subagent reads
    back_translations/<test_id>.<l1>.json   reviewer's blind L2 versions
    reviewed/<test_id>.<l1>.json            reviewer's corrected documents
    verdicts/<test_id>.<l1>.json            per-sentence verdict records
    upload.json                 assembled rows for upload_sentence_references.py
"""

import os
import sys
import csv
import glob
import json
import argparse
import logging

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from services.dual_translation import sentence_refs as sr  # noqa: E402

logging.basicConfig(level=logging.INFO, format='%(levelname)s %(message)s')
log = logging.getLogger('sentence_refs')
SUBDIR = 'sentence_refs'
DEFAULT_WIDTH = 6


def rdir(run: str, *parts: str) -> str:
    """Directory under RUN/sentence_refs/, created on demand."""
    p = os.path.join(run, SUBDIR, *parts)
    os.makedirs(p, exist_ok=True)
    return p


def worklist(run: str) -> dict:
    return sr.load_json(os.path.join(run, SUBDIR, 'worklist.json'))


def docs_in(run: str, source: str) -> dict[str, dict]:
    out = {}
    for path in sorted(glob.glob(os.path.join(run, SUBDIR, source, '*.json'))):
        try:
            d = sr.load_json(path)
        except Exception as exc:  # noqa: BLE001
            log.error('%s: unreadable (%s)', path, exc)
            continue
        out[os.path.basename(path)[:-5]] = d
    return out


# ---------------------------------------------------------------------------
# export
# ---------------------------------------------------------------------------

def _tests_from_fixture(path: str, language: str) -> list[dict]:
    data = sr.load_json(path)
    tests = data['tests'] if isinstance(data, dict) else data
    lid = sr.LANG_ID[language]
    out = []
    for t in tests:
        if int(t['language_id']) != lid:
            continue
        spans = sr.segment_with_spans(t.get('transcript') or '', language)
        sr.attach_token_spans(spans, t.get('vocab_token_map'))
        out.append({'test_id': t['id'], 'title': t.get('title'), 'language': language,
                    'sentences': [{'idx': s.idx, 'l2_text': s.text, 'token_start': s.token_start, 'token_end': s.token_end} for s in spans],
                    'vocab_token_map': t.get('vocab_token_map')})
    return out


def _tests_from_db(language: str, l1: str, limit: int, test_ids: list[str] | None) -> list[dict]:
    from services.supabase_factory import get_supabase_admin
    db = get_supabase_admin()
    lid, l1id = sr.LANG_ID[language], sr.LANG_ID[l1]
    q = db.table('tests').select('id, title, vocab_token_map').eq('is_active', True).eq('language_id', lid).order('created_at')
    if test_ids:
        q = q.in_('id', test_ids)
    tests = q.execute().data or []
    out = []
    for t in tests:
        rows = db.table('test_sentences').select('id, idx, l2_text, token_start, token_end').eq('test_id', t['id']).order('idx').execute().data or []
        if len(rows) < 1:
            continue
        sids = [r['id'] for r in rows]
        active = db.table('test_sentence_references').select('sentence_id').in_('sentence_id', sids) \
            .eq('l1_language_id', l1id).eq('is_active', True).eq('review_verdict', 'pass').execute().data or []
        if len(active) == len(rows):
            continue  # fully covered already
        out.append({'test_id': t['id'], 'title': t.get('title'), 'language': language,
                    'sentences': [{'idx': r['idx'], 'l2_text': r['l2_text'], 'token_start': r['token_start'], 'token_end': r['token_end'], 'sentence_id': r['id']} for r in rows],
                    'vocab_token_map': t.get('vocab_token_map')})
        if len(out) >= limit:
            break
    return out


def cmd_export(a) -> int:
    run = a.out_dir
    os.makedirs(os.path.join(run, SUBDIR), exist_ok=True)
    ids = [x.strip() for x in a.tests.split(',')] if a.tests else None
    tests = _tests_from_fixture(a.fixture, a.language) if a.fixture else _tests_from_db(a.language, a.l1, a.limit, ids)
    if ids:
        tests = [t for t in tests if t['test_id'] in ids]
    tests = tests[:a.limit]
    wl = {'language': a.language, 'l1': a.l1, 'arm': a.arm, 'prompt_version': sr.PROMPT_VERSION, 'tests': tests}
    sr.dump_json(os.path.join(run, SUBDIR, 'worklist.json'), wl)
    with open(os.path.join(run, SUBDIR, 'worklist.csv'), 'w', encoding='utf-8', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['test_id', 'title', 'n_sentences', 'sentences_json'])
        for t in tests:
            w.writerow([t['test_id'], t.get('title') or '', len(t['sentences']), json.dumps([s['l2_text'] for s in t['sentences']], ensure_ascii=False)])
    log.info('exported %d tests (%s -> %s, arm %s) to %s', len(tests), a.language, a.l1, a.arm, run)
    return 0


# ---------------------------------------------------------------------------
# brief
# ---------------------------------------------------------------------------

RULES_AUTHORING = """# Rules for authoring sentence references ({l2} -> {l1}, arm `{arm}`)

You translate the sentences of a test transcript into the learner's native
language ({l1_name}). The translations are **references for back-translation**:
a learner will read your {l1_name} and try to write the original {l2_name}.
So every sentence must be faithful and tight, not pretty.

1. One entry per sentence, in order, same count as the transcript. Never merge
   or split, even when {l1_name} would naturally do so.
2. Keep every piece of information: numbers, names, lists, negation, tense or
   aspect markers, politeness markers, and the sentence's own focus. Add
   nothing. Explain nothing. No parentheses, no translator's notes in `l1`.
3. Prefer the wording that most directly maps back to the original structure
   while still being natural {l1_name}. When two phrasings are equally natural,
   choose the one whose word order follows the original.
4. No {l2_name} script in `l1` (no kanji, kana or hanzi in English; no romaji
   either). Loanwords go back to their source form (カタログ -> catalogue).
5. Proper nouns: use the standard {l1_name} form if one exists, else a
   transliteration. Keep digits as digits.
6. Terminators: end each `l1` with the punctuation the sentence type needs in
   {l1_name}. Question stays a question.
7. Arm `sentencewise`: translate one sentence at a time, re-reading the whole
   passage before each. Arm `aligned`: translate the whole passage first, then
   split it into the aligned array and adjust each entry so it stands alone.
   Either way the output shape is identical.
8. Write `author_notes` only for things the reviewer must know (an ambiguous
   gold, a possible transcript error). They are stripped before review.
9. Do not touch `l2`. Do not reorder `idx`.

Document shape (one file per test, `docs/<test_id>.{l1}.json`):

```json
{{"test_id": "...", "l2": "{l2}", "l1": "{l1}", "arm": "{arm}", "prompt_version": "{pv}",
 "sentences": [{{"idx": 0, "l2": "<copied exactly>", "l1": "<your translation>"}}, ...],
 "author_notes": ""}}
```
"""

LANG_NAME = {'zh': 'Chinese', 'en': 'English', 'ja': 'Japanese'}


def cmd_brief(a) -> int:
    run = a.run
    wl = worklist(run)
    l2, l1, arm = wl['language'], wl['l1'], wl['arm']
    rules = RULES_AUTHORING.format(l2=l2, l1=l1, arm=arm, l1_name=LANG_NAME[l1], l2_name=LANG_NAME[l2], pv=wl['prompt_version'])
    with open(os.path.join(run, SUBDIR, 'rules_authoring.md'), 'w', encoding='utf-8') as fh:
        fh.write(rules)
    bdir = rdir(run, 'briefs')
    width = a.width or DEFAULT_WIDTH
    tests = wl['tests']
    n = 0
    for i in range(0, len(tests), width):
        n += 1
        chunk = tests[i:i + width]
        lines = [f'# Author brief {n:02d} — {l2} -> {l1}, arm `{arm}`', '',
                 f'Read `{os.path.join(run, SUBDIR, "rules_authoring.md")}` first. Write one file per test under',
                 f'`{os.path.join(run, SUBDIR, "docs")}/<test_id>.{l1}.json` in the shape the rules give.', '',
                 f'Then run: `PYTHONIOENCODING=utf-8 python scripts/sentence_ref_runner.py check {run} --tests {",".join(t["test_id"] for t in chunk)}`',
                 'and fix until every test is `ok`.', '']
        for t in chunk:
            lines += [f'## {t["test_id"]} — {t.get("title") or ""}', '',
                      'Passage (for context, do not translate as a block unless the arm says so):', '']
            lines.append(''.join(s['l2_text'] for s in t['sentences']) if l2 in ('zh', 'ja') else ' '.join(s['l2_text'] for s in t['sentences']))
            lines += ['', 'Sentences:', '']
            for s in t['sentences']:
                lines.append(f'- idx {s["idx"]}: {s["l2_text"]}')
            lines.append('')
        with open(os.path.join(bdir, f'author_{n:02d}.md'), 'w', encoding='utf-8') as fh:
            fh.write('\n'.join(lines))
    log.info('wrote %d briefs (width %d) and rules_authoring.md', n, width)
    return 0


# ---------------------------------------------------------------------------
# check
# ---------------------------------------------------------------------------

def cmd_check(a) -> int:
    run = a.run
    wl = worklist(run)
    canon = {t['test_id']: t['sentences'] for t in wl['tests']}
    want = set(x.strip() for x in a.tests.split(',')) if a.tests else set(canon)
    docs = docs_in(run, a.source)
    results, failed = [], 0
    for tid in sorted(want):
        key = sr.doc_path_name(tid, wl['l1'])[:-5]
        d = docs.get(key)
        if d is None:
            results.append({'test_id': tid, 'l1': wl['l1'], 'ok': False, 'failures': ['missing_doc'], 'warnings': []})
            failed += 1
            continue
        r = sr.validate_doc(d, [{'idx': s['idx'], 'l2_text': s['l2_text']} for s in canon[tid]], wl['language'])
        results.append(r.as_dict())
        failed += 0 if r.ok else 1
        log.info('%s %s%s', tid[:8], 'ok' if r.ok else 'FAIL ' + ' '.join(r.failures), (' warn ' + ' '.join(r.warnings)) if r.warnings else '')
    sr.dump_json(os.path.join(run, SUBDIR, f'check{"_reviewed" if a.source == "reviewed" else ""}.json'), results)
    log.info('check (%s): %d ok, %d failed', a.source, len(results) - failed, failed)
    return 1 if failed else 0


# ---------------------------------------------------------------------------
# review-pack
# ---------------------------------------------------------------------------

RULES_REVIEW = """# Rules for reviewing sentence references ({l2} -> {l1})

You have NOT seen the authoring. Work in this order and do not skip ahead.

**Step 1 — blind back-translation.** Your pack comes in two files:
`review_NN.md` (the {l1_name} references only) and `review_NN.gold.md` (the
gold). Do not open the gold file until step 2. From the references alone, write
your own {l2_name} version of each sentence, as a competent learner would, into
`back_translations/<test_id>.{l1}.json`:

```json
{{"test_id": "...", "l1": "{l1}", "sentences": [{{"idx": 0, "back": "<your {l2_name}>"}}, ...]}}
```

Only after every back-translation file for the pack is written may you open `review_NN.gold.md`.

**Step 2 — judge against the gold.** For each sentence decide whether the `l1`
and the gold `l2` entail each other (same facts, same scope, same polarity,
same focus). Flag additions, omissions, wrong numbers or names, register drift,
and any {l2_name} script in `l1`. If a sentence fails, REWRITE the `l1` so it
passes; mark `rewritten`. Use `fail` only when the gold itself is broken (a
fragment, a leaked preamble) so no faithful reference is possible.

**Step 3 — write.** `reviewed/<test_id>.{l1}.json` (same shape as the authored
document, `author_notes` removed, your rewrites in place) and
`verdicts/<test_id>.{l1}.json`:

```json
{{"test_id": "...", "l1": "{l1}", "reviewer_model": "<your model>",
 "sentences": [{{"idx": 0, "verdict": "pass|rewritten|fail", "entailment_ok": true, "changed": false, "notes": ""}}, ...]}}
```

Then run `PYTHONIOENCODING=utf-8 python scripts/sentence_ref_runner.py tightness RUN`
(or ask the orchestrator to) — it scores your back-translations against the
gold and adds `tightness` to each verdict. A low tightness with `pass` is
allowed when the gold has several equally faithful renderings; say so in notes.
"""


def cmd_review_pack(a) -> int:
    run = a.run
    wl = worklist(run)
    l2, l1 = wl['language'], wl['l1']
    with open(os.path.join(run, SUBDIR, 'rules_review.md'), 'w', encoding='utf-8') as fh:
        fh.write(RULES_REVIEW.format(l2=l2, l1=l1, l1_name=LANG_NAME[l1], l2_name=LANG_NAME[l2]))
    docs = docs_in(run, 'docs')
    check = {r['test_id']: r for r in (sr.load_json(os.path.join(run, SUBDIR, 'check.json')) if os.path.exists(os.path.join(run, SUBDIR, 'check.json')) else [])}
    pdir = rdir(run, 'review_packs')
    for p_ in glob.glob(os.path.join(pdir, '*.md')):
        os.remove(p_)
    width = a.width or DEFAULT_WIDTH
    items = [(k, d) for k, d in docs.items() if check.get(d.get('test_id'), {}).get('ok', True)]
    n = 0
    for i in range(0, len(items), width):
        n += 1
        chunk = items[i:i + width]
        blind = [f'# Review pack {n:02d} — {l2} -> {l1} — BLIND HALF', '',
             f'Read `{os.path.join(run, SUBDIR, "rules_review.md")}` first. This file holds only the {LANG_NAME[l1]} references.',
             f'Write every back-translation file for this pack BEFORE opening `review_{n:02d}.gold.md`.', '']
        gold = [f'# Review pack {n:02d} — {l2} -> {l1} — GOLD HALF', '',
                'Open this file only after all back-translation files for this pack are written.', '']
        for key, d in chunk:
            clean = sr.strip_author_notes(d)
            blind += [f'## {d["test_id"]}', '', f'Write `back_translations/{key}.json` from these {LANG_NAME[l1]} sentences:', '']
            for s_ in clean['sentences']:
                blind.append(f'- idx {s_["idx"]}: {s_["l1"]}')
            blind.append('')
            gold += [f'## {d["test_id"]}', '']
            for s_ in clean['sentences']:
                gold.append(f'- idx {s_["idx"]} gold: {s_["l2"]}')
                gold.append(f'  ref: {s_["l1"]}')
            flagged = check.get(d['test_id'], {}).get('warnings') or []
            if flagged:
                gold += ['', 'Deterministic warnings: ' + '; '.join(flagged)]
            gold.append('')
        with open(os.path.join(pdir, f'review_{n:02d}.md'), 'w', encoding='utf-8') as fh:
            fh.write('\n'.join(blind))
        with open(os.path.join(pdir, f'review_{n:02d}.gold.md'), 'w', encoding='utf-8') as fh:
            fh.write('\n'.join(gold))
    log.info('wrote %d review packs (width %d) and rules_review.md; %d docs excluded by check', n, width, len(docs) - len(items))
    return 0


# ---------------------------------------------------------------------------
# tightness
# ---------------------------------------------------------------------------

def cmd_tightness(a) -> int:
    run = a.run
    wl = worklist(run)
    canon = {t['test_id']: {s['idx']: s['l2_text'] for s in t['sentences']} for t in wl['tests']}
    backs = docs_in(run, 'back_translations')
    verdicts = docs_in(run, 'verdicts')
    vdir = rdir(run, 'verdicts')
    scored = 0
    for key, b in backs.items():
        tid = b.get('test_id')
        v = verdicts.get(key) or {'test_id': tid, 'l1': wl['l1'], 'sentences': []}
        by_idx = {s['idx']: s for s in v.get('sentences', [])}
        for s in b.get('sentences', []):
            gold = canon.get(tid, {}).get(s['idx'])
            if gold is None:
                continue
            rec = by_idx.setdefault(s['idx'], {'idx': s['idx'], 'verdict': 'pending', 'entailment_ok': None, 'changed': False, 'notes': ''})
            rec['tightness'] = sr.tightness(s.get('back', ''), gold, wl['language'])
            rec['back_translation'] = s.get('back', '')
            scored += 1
        v['sentences'] = [by_idx[k] for k in sorted(by_idx)]
        sr.dump_json(os.path.join(vdir, key + '.json'), v)
    log.info('scored %d sentences into verdicts/', scored)
    return 0


# ---------------------------------------------------------------------------
# assemble
# ---------------------------------------------------------------------------

def cmd_assemble(a) -> int:
    run = a.run
    wl = worklist(run)
    reviewed = docs_in(run, 'reviewed')
    verdicts = docs_in(run, 'verdicts')
    canon = {t['test_id']: t for t in wl['tests']}
    rows, problems = [], 0
    for key, d in reviewed.items():
        tid = d.get('test_id')
        r = sr.validate_doc(d, [{'idx': s['idx'], 'l2_text': s['l2_text']} for s in canon[tid]['sentences']], wl['language']) if tid in canon else None
        if r is None or not r.ok:
            log.error('%s: reviewed doc fails check: %s', key, r.failures if r else 'unknown test')
            problems += 1
            continue
        v = verdicts.get(key)
        if not v:
            log.error('%s: no verdict record', key)
            problems += 1
            continue
        vmap = {s['idx']: s for s in v.get('sentences', [])}
        for s in d['sentences']:
            vr = vmap.get(s['idx'])
            if not vr or vr.get('verdict') not in sr.VERDICTS or vr.get('verdict') == 'pending':
                log.error('%s idx %s: missing or pending verdict', key, s['idx'])
                problems += 1
                continue
            canon_s = canon[tid]['sentences'][s['idx']]
            rows.append({
                'test_id': tid, 'idx': s['idx'], 'sentence_id': canon_s.get('sentence_id'),
                'l1': wl['l1'], 'l1_language_id': sr.LANG_ID[wl['l1']], 'l1_text': s['l1'],
                'author_model': d.get('author_model') or 'claude-subagent', 'prompt_version': d.get('prompt_version'),
                'arm': d.get('arm'), 'reviewer_model': v.get('reviewer_model'),
                'review_verdict': vr['verdict'], 'tightness': vr.get('tightness'), 'entailment_ok': vr.get('entailment_ok'),
                'run_id': os.path.basename(os.path.normpath(run)),
            })
    out = {'language': wl['language'], 'l1': wl['l1'], 'arm': wl['arm'], 'rows': rows}
    sr.dump_json(os.path.join(run, SUBDIR, 'upload.json'), out)
    log.info('assembled %d rows into upload.json (%d problems)', len(rows), problems)
    return 1 if problems else 0


# ---------------------------------------------------------------------------
# status
# ---------------------------------------------------------------------------

def cmd_status(a) -> int:
    run = a.run
    wl = worklist(run)
    l1 = wl['l1']
    docs, reviewed, verdicts, backs = (docs_in(run, s) for s in ('docs', 'reviewed', 'verdicts', 'back_translations'))
    check = {r['test_id']: r.get('ok') for r in (sr.load_json(os.path.join(run, SUBDIR, 'check.json')) if os.path.exists(os.path.join(run, SUBDIR, 'check.json')) else [])}
    up = sr.load_json(os.path.join(run, SUBDIR, 'upload.json')) if os.path.exists(os.path.join(run, SUBDIR, 'upload.json')) else {'rows': []}
    assembled = {r['test_id'] for r in up['rows']}
    print(f'{"test":10} {"authored":9} {"checked":8} {"backtr":7} {"reviewed":9} {"verdict":8} {"assembled":9}')
    for t in wl['tests']:
        tid = t['test_id']
        key = f'{tid}.{l1}'
        print(f'{tid[:8]:10} {"yes" if key in docs else "-":9} {("ok" if check.get(tid) else ("FAIL" if tid in check else "-")):8} {"yes" if key in backs else "-":7} {"yes" if key in reviewed else "-":9} {"yes" if key in verdicts else "-":8} {"yes" if tid in assembled else "-":9}')
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('export'); p.add_argument('--language', required=True, choices=['zh', 'en', 'ja']); p.add_argument('--l1', required=True, choices=['zh', 'en', 'ja'])
    p.add_argument('--limit', type=int, default=30); p.add_argument('--arm', default='aligned', choices=list(sr.ARMS)); p.add_argument('--out-dir', required=True)
    p.add_argument('--fixture'); p.add_argument('--tests'); p.set_defaults(fn=cmd_export)
    for name, fn in (('brief', cmd_brief), ('review-pack', cmd_review_pack)):
        p = sub.add_parser(name); p.add_argument('run'); p.add_argument('--width', type=int); p.set_defaults(fn=fn)
    p = sub.add_parser('check'); p.add_argument('run'); p.add_argument('--source', default='docs', choices=['docs', 'reviewed']); p.add_argument('--tests'); p.set_defaults(fn=cmd_check)
    for name, fn in (('tightness', cmd_tightness), ('assemble', cmd_assemble), ('status', cmd_status)):
        p = sub.add_parser(name); p.add_argument('run'); p.set_defaults(fn=fn)
    a = ap.parse_args()
    return a.fn(a)


if __name__ == '__main__':
    sys.exit(main())
