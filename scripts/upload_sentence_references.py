#!/usr/bin/env python3
"""Upload assembled sentence references (TASK-906, ADR-037).

    python scripts/upload_sentence_references.py RUN --dry-run
    python scripts/upload_sentence_references.py RUN --apply

Reads RUN/sentence_refs/upload.json (from sentence_ref_runner.py assemble),
resolves sentence ids by (test_id, idx), verifies tests.transcript_hash
against test_sentences.transcript_hash, inserts test_sentence_references rows
with provenance, and activates pass/rewritten rows while deactivating the
previous active row for the same (sentence, L1). One test at a time; a hash
mismatch skips that test. Idempotent on (run_id, sentence_id, l1_language_id).
Service role only; never called from the app.
"""

import os
import sys
import argparse
import logging

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from services.dual_translation import sentence_refs as sr  # noqa: E402

logging.basicConfig(level=logging.INFO, format='%(levelname)s %(message)s')
log = logging.getLogger('upload_sentence_refs')


def plan_for_test(db, test_id: str, rows: list[dict], run_id: str) -> dict:
    """Return {'skip': reason} or {'insert': [...], 'deactivate': [...], 'activate': [...]}."""
    t = db.table('tests').select('id, transcript_hash').eq('id', test_id).single().execute().data
    sents = db.table('test_sentences').select('id, idx, transcript_hash').eq('test_id', test_id).order('idx').execute().data or []
    if not t or not sents:
        return {'skip': 'no test or no sentence rows'}
    hashes = {s['transcript_hash'] for s in sents}
    if len(hashes) != 1 or (t.get('transcript_hash') and t['transcript_hash'] not in hashes):
        return {'skip': 'transcript hash mismatch (re-run build_test_sentences.py)'}
    by_idx = {s['idx']: s['id'] for s in sents}
    sids = list(by_idx.values())
    l1ids = sorted({r['l1_language_id'] for r in rows})
    existing_run = db.table('test_sentence_references').select('sentence_id, l1_language_id').in_('sentence_id', sids).eq('run_id', run_id).execute().data or []
    already = {(e['sentence_id'], e['l1_language_id']) for e in existing_run}
    active = db.table('test_sentence_references').select('id, sentence_id, l1_language_id').in_('sentence_id', sids).in_('l1_language_id', l1ids).eq('is_active', True).execute().data or []
    existing_active = {(e['sentence_id'], e['l1_language_id']): e['id'] for e in active}
    inserts = []
    for r in rows:
        sid = by_idx.get(r['idx'])
        if sid is None:
            return {'skip': f'idx {r["idx"]} has no sentence row'}
        if (sid, r['l1_language_id']) in already:
            continue
        inserts.append({
            'sentence_id': sid, 'l1_language_id': r['l1_language_id'], 'l1_text': r['l1_text'],
            'author_model': r.get('author_model') or 'claude-subagent', 'prompt_version': r.get('prompt_version') or sr.PROMPT_VERSION,
            'arm': r.get('arm'), 'reviewer_model': r.get('reviewer_model'), 'review_verdict': r['review_verdict'],
            'tightness': r.get('tightness'), 'entailment_ok': r.get('entailment_ok'), 'is_active': False, 'run_id': run_id,
        })
    act = sr.activation_plan(inserts, existing_active)
    return {'insert': inserts, 'deactivate': act['deactivate'], 'activate': act['activate']}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('run')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--no-activate', action='store_true', help='insert only (pilot arms are uploaded inactive)')
    a = ap.parse_args()
    if not (a.dry_run or a.apply):
        ap.error('choose --dry-run or --apply')
    up = sr.load_json(os.path.join(a.run, 'sentence_refs', 'upload.json'))
    run_id = os.path.basename(os.path.normpath(a.run))
    from dotenv import load_dotenv
    load_dotenv()
    from services.supabase_factory import SupabaseFactory, get_supabase_admin
    if not SupabaseFactory.is_initialized():
        SupabaseFactory.initialize()
    db = get_supabase_admin()
    by_test: dict[str, list[dict]] = {}
    for r in up['rows']:
        by_test.setdefault(r['test_id'], []).append(r)
    total_ins = total_act = total_deact = 0
    for tid, rows in by_test.items():
        plan = plan_for_test(db, tid, rows, run_id)
        if 'skip' in plan:
            log.error('%s: SKIP — %s', tid[:8], plan['skip'])
            continue
        verdicts = {}
        for r in rows:
            verdicts[r['review_verdict']] = verdicts.get(r['review_verdict'], 0) + 1
        log.info('%s: %d sentences, L1 %s, verdicts %s -> insert %d, activate %d, deactivate %d',
                 tid[:8], len(rows), up['l1'], verdicts, len(plan['insert']), 0 if a.no_activate else len(plan['activate']), 0 if a.no_activate else len(plan['deactivate']))
        total_ins += len(plan['insert'])
        if not a.apply:
            continue
        if plan['insert']:
            inserted = db.table('test_sentence_references').insert(plan['insert']).execute().data or []
        else:
            inserted = []
        if not a.no_activate:
            if plan['deactivate']:
                db.table('test_sentence_references').update({'is_active': False}).in_('id', plan['deactivate']).execute()
                total_deact += len(plan['deactivate'])
            ids = [row['id'] for row in inserted if (row['sentence_id'], row['l1_language_id']) in set(plan['activate'])]
            if ids:
                db.table('test_sentence_references').update({'is_active': True}).in_('id', ids).execute()
                total_act += len(ids)
    log.info('%s: %d rows to insert%s', 'applied' if a.apply else 'dry run', total_ins,
             f', {total_act} activated, {total_deact} deactivated' if a.apply and not a.no_activate else '')
    return 0


if __name__ == '__main__':
    sys.exit(main())
