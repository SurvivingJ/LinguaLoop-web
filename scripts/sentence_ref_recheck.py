#!/usr/bin/env python3
"""Second review of active sentence references below the tightness floor
(TASK-908 acceptance: "the rest are listed for a second review pass").

    python scripts/sentence_ref_recheck.py export --out-dir RUN [--per-pack 25]
    python scripts/sentence_ref_recheck.py score RUN
    python scripts/upload_sentence_references.py RUN --dry-run | --apply

`export` reads every active, usable reference whose tightness is below the
Produce floor for its test language (services.prestudy.PRODUCE_TIGHTNESS_FLOOR)
and writes, per pack, a blind file (the L1 target sentence with its L1
neighbours as context) and a gold file (the L2 sentence, its L2 neighbours and
the current reference). A reviewer subagent, in a fresh context, follows the
sentence-reference-review skill on that one sentence: blind back-translation
first (`back/NN.json`), then judge against the gold, rewrite the reference if
it is loose, and record `verdicts/NN.json`.

`score` checks every final reference with the same deterministic checks as the
runner (L2 script leak, missing numbers, preamble, empty), computes tightness
from the new blind back-translation, and writes RUN/sentence_refs/upload.json
in the shape upload_sentence_references.py reads. Only the re-reviewed
sentences are uploaded; a `fail` verdict is not activated, so the previous
reference stays active. No hosted model API is called.
"""

import argparse
import glob
import json
import logging
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from services.dual_translation import sentence_refs as sr  # noqa: E402

logging.basicConfig(level=logging.INFO, format='%(levelname)s %(message)s')
log = logging.getLogger('sentence_ref_recheck')
logging.getLogger('httpx').setLevel(logging.WARNING)

SUBDIR = 'sentence_refs'
NAMES = {'zh': 'Chinese', 'en': 'English', 'ja': 'Japanese'}

WHY_FLOOR = """references that scored low on tightness: a first
reviewer's blind back-translation landed far from the gold. Decide whether the
reference is loose (rewrite it) or the gold simply has several faithful
renderings (pass, with a note)."""

WHY_GIVEN = """references flagged for this reason: {reason}
Rewrite the reference when the reason holds and a more natural, equally faithful
rendering exists; otherwise pass it with a note."""

RULES = """\
You are the second reviewer of {why} Follow `.claude/skills/sentence-reference-review/SKILL.md`
for what to check (meaning, numbers and names, sentence identity, register,
leakage, tightness). The neighbours are context only; judge the TARGET.

Order (hard rule): write `{run}/sentence_refs/back/{nn}.json` with your blind
back-translation of every TARGET into the studied language BEFORE opening
`recheck_{nn}.gold.md`:

    {{"reviewer_model": "<your model id>", "items": [{{"key": "<key>", "back": "<your L2 version>"}}]}}

Then open the gold file and write `{run}/sentence_refs/verdicts/{nn}.json`:

    {{"reviewer_model": "<your model id>", "items": [{{"key": "<key>", "verdict": "pass|rewritten|fail",
      "entailment_ok": true, "l1": "<final reference: unchanged for pass, your rewrite for rewritten>",
      "gold_seen_early": false, "notes": "<one line: why low, what you changed>"}}]}}

`fail` only for a gold that is itself broken (fragment, leaked preamble, mixed script).
A rewrite stays one sentence, keeps every number and name, adds nothing, and has
no L2 script, notes or parentheses. Never change the gold. Every key gets a verdict.
"""


def _db():
    from dotenv import load_dotenv
    load_dotenv()
    from services.supabase_factory import SupabaseFactory, get_supabase_admin
    if not SupabaseFactory.is_initialized():
        SupabaseFactory.initialize()
    return get_supabase_admin()


def _floors() -> dict:
    from services.prestudy import PRODUCE_TIGHTNESS_FLOOR
    return dict(PRODUCE_TIGHTNESS_FLOOR)


def cmd_export(a) -> int:
    db = _db()
    floors = _floors()
    select = ('id, sentence_id, l1_language_id, l1_text, tightness, review_verdict, author_model, '
              'prompt_version, arm, test_sentences!inner(test_id, idx, l2_text)')
    picked = None
    if a.sentences:
        # Named sentences (test_id:idx), whatever their tightness or review history.
        picked = set()
        for part in a.sentences.split(','):
            tid, idx = part.strip().rsplit(':', 1)
            picked.add((tid, int(idx)))
        sids = []
        for tid, idx in sorted(picked):
            sids += [x['id'] for x in db.table('test_sentences').select('id').eq('test_id', tid)
                     .eq('idx', idx).execute().data or []]
        rows = (
            db.table('test_sentence_references').select(select).in_('sentence_id', sids or [-1])
            .eq('is_active', True).in_('review_verdict', ['pass', 'rewritten']).execute().data or []
        )
    else:
        rows = (
            db.table('test_sentence_references').select(select)
            .eq('is_active', True).in_('review_verdict', ['pass', 'rewritten'])
            .lt('tightness', max(floors.values())).limit(5000).execute().data or []
        )
    tests = {}
    tids = sorted({r['test_sentences']['test_id'] for r in rows})
    for i in range(0, len(tids), 100):
        for t in db.table('tests').select('id, language_id, is_active').in_('id', tids[i:i + 100]).execute().data or []:
            tests[t['id']] = t
    # A sentence that already had a second review (a row from a `recheck-*` run)
    # is not exported again unless --include-rechecked.
    rechecked: set = set()
    if not a.include_rechecked and picked is None:
        sids = sorted({r['sentence_id'] for r in rows})
        for i in range(0, len(sids), 200):
            for x in db.table('test_sentence_references').select('sentence_id, l1_language_id, run_id') \
                    .in_('sentence_id', sids[i:i + 200]).like('run_id', 'recheck%').execute().data or []:
                rechecked.add((x['sentence_id'], x['l1_language_id']))
    items = []
    context_cache: dict = {}
    for r in rows:
        if (r['sentence_id'], r['l1_language_id']) in rechecked:
            continue
        s = r['test_sentences']
        t = tests.get(s['test_id'])
        if not t or not t.get('is_active'):
            continue
        l2_id = int(t['language_id'])
        if picked is None and (r['tightness'] is None or r['tightness'] >= floors.get(l2_id, 0.6)):
            continue
        key_ctx = (s['test_id'], r['l1_language_id'])
        if key_ctx not in context_cache:
            sents = db.table('test_sentences').select('id, idx, l2_text').eq('test_id', s['test_id']).order('idx').execute().data or []
            refs = db.table('test_sentence_references').select('sentence_id, l1_text') \
                .in_('sentence_id', [x['id'] for x in sents]).eq('l1_language_id', r['l1_language_id']) \
                .eq('is_active', True).execute().data or []
            ref_by = {x['sentence_id']: x['l1_text'] for x in refs}
            context_cache[key_ctx] = {x['idx']: {'l2': x['l2_text'], 'l1': ref_by.get(x['id'], '')} for x in sents}
        ctx = context_cache[key_ctx]
        idx = int(s['idx'])
        items.append({
            'key': f"{s['test_id'][:8]}-{idx}-{sr.LANG_CODE[r['l1_language_id']]}",
            'test_id': s['test_id'], 'idx': idx, 'sentence_id': r['sentence_id'], 'ref_id': r['id'],
            'l2': sr.LANG_CODE[l2_id], 'l1': sr.LANG_CODE[r['l1_language_id']],
            'l1_language_id': r['l1_language_id'],
            'l2_text': s['l2_text'], 'l1_text': r['l1_text'], 'old_tightness': r['tightness'],
            'floor': floors.get(l2_id, 0.6), 'author_model': r.get('author_model'),
            'prompt_version': r.get('prompt_version'), 'arm': r.get('arm'),
            'prev': ctx.get(idx - 1), 'next': ctx.get(idx + 1),
        })
    items.sort(key=lambda x: (x['l2'], x['l1'], x['test_id'], x['idx']))
    base = os.path.join(a.out_dir, SUBDIR)
    os.makedirs(os.path.join(base, 'packs'), exist_ok=True)
    sr.dump_json(os.path.join(base, 'recheck_items.json'), {'items': items})
    why = WHY_GIVEN.format(reason=a.reason) if a.reason else WHY_FLOOR
    per = max(1, a.per_pack)
    n = 0
    for start in range(0, len(items), per):
        n += 1
        nn = f'{n:02d}'
        chunk = items[start:start + per]
        blind = [f'# Recheck pack {nn} — BLIND HALF\n', RULES.format(run=a.out_dir, nn=nn, why=why),
                 f'\nThe gold half is `{a.out_dir}/{SUBDIR}/packs/recheck_{nn}.gold.md`. Do not open it yet.\n']
        gold = [f'# Recheck pack {nn} — GOLD HALF\n',
                'Open this only after `back/' + nn + '.json` holds a back-translation for every key.\n']
        for it in chunk:
            l1n, l2n = NAMES[it['l1']], NAMES[it['l2']]
            blind.append(f"\n## {it['key']}  ({l1n} reference -> back-translate into {l2n})\n")
            if it['prev']:
                blind.append(f"- context before: {it['prev']['l1']}")
            blind.append(f"- **TARGET:** {it['l1_text']}")
            if it['next']:
                blind.append(f"- context after: {it['next']['l1']}")
            score = f"{it['old_tightness']:.2f}" if it['old_tightness'] is not None else 'n/a'
            gold.append(f"\n## {it['key']}  (first-review tightness {score}, floor {it['floor']:.2f})\n")
            if it['prev']:
                gold.append(f"- gold before: {it['prev']['l2']}")
            gold.append(f"- **GOLD:** {it['l2_text']}")
            if it['next']:
                gold.append(f"- gold after: {it['next']['l2']}")
            gold.append(f"- current reference: {it['l1_text']}")
        with open(os.path.join(base, 'packs', f'recheck_{nn}.md'), 'w', encoding='utf-8') as fh:
            fh.write('\n'.join(blind) + '\n')
        with open(os.path.join(base, 'packs', f'recheck_{nn}.gold.md'), 'w', encoding='utf-8') as fh:
            fh.write('\n'.join(gold) + '\n')
    log.info('exported %d references into %d packs', len(items), n)
    return 0


def _load_dir(path: str) -> dict:
    out = {}
    for p in sorted(glob.glob(os.path.join(path, '*.json'))):
        doc = sr.load_json(p)
        for it in doc.get('items', []):
            out[it['key']] = {**it, 'reviewer_model': doc.get('reviewer_model')}
    return out


def cmd_score(a) -> int:
    base = os.path.join(a.run, SUBDIR)
    items = {it['key']: it for it in sr.load_json(os.path.join(base, 'recheck_items.json'))['items']}
    backs = _load_dir(os.path.join(base, 'back'))
    verdicts = _load_dir(os.path.join(base, 'verdicts'))
    rows, problems, report = [], 0, []
    for key, it in items.items():
        v, b = verdicts.get(key), backs.get(key)
        if not v or not b or v.get('verdict') not in ('pass', 'rewritten', 'fail'):
            log.error('%s: missing back-translation or verdict', key)
            problems += 1
            continue
        l1_text = (v.get('l1') or '').strip() if v['verdict'] == 'rewritten' else it['l1_text']
        fails = []
        if not l1_text:
            fails.append('empty_l1')
        leak = sr.leaked_script(l1_text, it['l2'])
        if leak:
            fails.append('l2_script_leak:' + ''.join(leak))
        miss = sr.missing_numbers(it['l2_text'], l1_text)
        if miss:
            fails.append('missing_number:' + ','.join(miss))
        if sr.has_preamble(l1_text):
            fails.append('preamble')
        if fails:
            log.error('%s: %s', key, fails)
            problems += 1
            continue
        t = sr.tightness(b.get('back', ''), it['l2_text'], it['l2'])
        report.append({'key': key, 'verdict': v['verdict'], 'old': it['old_tightness'], 'new': t,
                       'floor': it['floor'], 'gold_seen_early': bool(v.get('gold_seen_early')),
                       'notes': v.get('notes', '')})
        rows.append({
            'test_id': it['test_id'], 'idx': it['idx'], 'sentence_id': it['sentence_id'],
            'l1': it['l1'], 'l1_language_id': it['l1_language_id'], 'l1_text': l1_text,
            'author_model': it.get('author_model') if v['verdict'] == 'pass' else v.get('reviewer_model'),
            'prompt_version': it.get('prompt_version'), 'arm': it.get('arm'),
            'reviewer_model': v.get('reviewer_model'), 'review_verdict': v['verdict'],
            'tightness': None if v.get('gold_seen_early') else t,
            'entailment_ok': v.get('entailment_ok'), 'run_id': os.path.basename(os.path.normpath(a.run)),
        })
    sr.dump_json(os.path.join(base, 'upload.json'), {'language': 'mixed', 'l1': 'mixed', 'arm': 'recheck', 'rows': rows})
    sr.dump_json(os.path.join(base, 'recheck_report.json'), {'items': report})
    below = sum(1 for r in report if r['verdict'] != 'fail' and r['new'] < r['floor'])
    by = {}
    for r in report:
        by[r['verdict']] = by.get(r['verdict'], 0) + 1
    log.info('scored %d items (%s); %d still below floor; %d problems', len(report), by, below, problems)
    return 1 if problems else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('export')
    p.add_argument('--out-dir', required=True)
    p.add_argument('--per-pack', type=int, default=25)
    p.add_argument('--include-rechecked', action='store_true',
                   help='also export sentences that already have a row from a recheck-* run')
    p.add_argument('--sentences', help='test_id:idx,... — these sentences only, whatever their tightness')
    p.add_argument('--reason', help='why these references are re-reviewed (replaces the tightness intro)')
    p.set_defaults(fn=cmd_export)
    p = sub.add_parser('score')
    p.add_argument('run')
    p.set_defaults(fn=cmd_score)
    a = ap.parse_args()
    return a.fn(a)


if __name__ == '__main__':
    sys.exit(main())
