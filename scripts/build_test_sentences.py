#!/usr/bin/env python3
"""Backfill `test_sentences` for every active test (TASK-902, ADR-037).

    python scripts/build_test_sentences.py --dry-run            # counts only
    python scripts/build_test_sentences.py --apply              # service role
    python scripts/build_test_sentences.py --apply --test-id X  # one test
    python scripts/build_test_sentences.py --fixture data.json --out spans.json   # offline

Segmentation is services.dual_translation.sentence_refs.segment_with_spans (the
same terminators as passage_builder.segment_sentences, applied to the raw
transcript so spans index into tests.transcript). Token spans come from
tests.vocab_token_map. A test whose transcript_hash matches its existing
sentence rows is skipped; a changed hash replaces the rows and retires the
test's references (is_active = false).
"""

import os
import sys
import argparse
import logging
import json
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from services.dual_translation import sentence_refs as sr  # noqa: E402

logging.basicConfig(level=logging.INFO, format='%(levelname)s %(message)s')
log = logging.getLogger('build_test_sentences')


def rows_for_test(test: dict) -> tuple[list[dict], list[str]]:
    code = sr.LANG_CODE.get(int(test['language_id']), 'en')
    transcript = test.get('transcript') or ''
    spans = sr.segment_with_spans(transcript, code)
    warnings = sr.attach_token_spans(spans, test.get('vocab_token_map'))
    # invariant: spans reproduce the transcript's non-space content in order
    joined = ''.join(sp.text for sp in spans)
    if joined.replace(' ', '') != transcript.replace(' ', '').replace('\n', '').replace('\t', ''):
        warnings.append('spans do not reproduce the transcript')
    canon = sr.segment_sentences(transcript, code)
    if [sp.text for sp in spans] != canon:
        warnings.append('span texts differ from passage_builder.segment_sentences (internal whitespace)')
    h = sr.transcript_hash(transcript)
    rows = [{
        'test_id': test['id'], 'idx': sp.idx,
        'char_start': sp.char_start, 'char_end': sp.char_end,
        'token_start': sp.token_start, 'token_end': sp.token_end,
        'l2_text': sp.text, 'transcript_hash': h,
    } for sp in spans]
    return rows, warnings


def summarise(all_rows: dict[str, list[dict]], tests: list[dict]) -> None:
    by_lang = Counter()
    sents = Counter()
    short = Counter()
    for t in tests:
        rows = all_rows.get(t['id'], [])
        by_lang[t['language_id']] += 1
        sents[t['language_id']] += len(rows)
        if len(rows) < 2:
            short[t['language_id']] += 1
    for lang in sorted(by_lang):
        n = by_lang[lang]
        log.info('language %s: %d tests, %d sentences, %.1f per test, %d tests under 2 sentences',
                 lang, n, sents[lang], sents[lang] / max(1, n), short[lang])


def run_fixture(path: str, out: str | None) -> int:
    data = sr.load_json(path)
    tests = data['tests'] if isinstance(data, dict) else data
    result = {}
    for t in tests:
        rows, warnings = rows_for_test(t)
        for w in warnings:
            log.warning('%s: %s', t['id'][:8], w)
        result[t['id']] = rows
    summarise(result, tests)
    if out:
        sr.dump_json(out, result)
        log.info('wrote %s', out)
    return 0


def run_db(apply: bool, test_id: str | None) -> int:
    from services.supabase_factory import get_supabase_admin
    db = get_supabase_admin()
    q = db.table('tests').select('id, language_id, transcript, vocab_token_map, transcript_hash').eq('is_active', True)
    if test_id:
        q = q.eq('id', test_id)
    tests = q.execute().data or []
    existing = {}
    for r in (db.table('test_sentences').select('test_id, transcript_hash').execute().data or []):
        existing[r['test_id']] = r['transcript_hash']
    all_rows, changed, skipped = {}, 0, 0
    for t in tests:
        rows, warnings = rows_for_test(t)
        for w in warnings:
            log.warning('%s: %s', t['id'][:8], w)
        all_rows[t['id']] = rows
        h = rows[0]['transcript_hash'] if rows else sr.transcript_hash(t.get('transcript') or '')
        if existing.get(t['id']) == h:
            skipped += 1
            continue
        changed += 1
        if not apply:
            continue
        if t['id'] in existing:
            ids = [r['id'] for r in (db.table('test_sentences').select('id').eq('test_id', t['id']).execute().data or [])]
            if ids:
                db.table('test_sentence_references').update({'is_active': False}).in_('sentence_id', ids).execute()
                log.info('%s: transcript changed, retired references on %d sentences', t['id'][:8], len(ids))
            db.table('test_sentences').delete().eq('test_id', t['id']).execute()
        if rows:
            db.table('test_sentences').insert(rows).execute()
        if (t.get('transcript_hash') or '') != h:
            db.table('tests').update({'transcript_hash': h}).eq('id', t['id']).execute()
    summarise(all_rows, tests)
    log.info('%s: %d tests to (re)build, %d unchanged', 'applied' if apply else 'dry run', changed, skipped)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--test-id')
    ap.add_argument('--fixture', help='offline: JSON with tests[] (id, language_id, transcript, vocab_token_map)')
    ap.add_argument('--out', help='with --fixture: write the span rows here')
    a = ap.parse_args()
    if a.fixture:
        return run_fixture(a.fixture, a.out)
    if not (a.dry_run or a.apply):
        ap.error('choose --dry-run or --apply (or --fixture)')
    return run_db(a.apply, a.test_id)


if __name__ == '__main__':
    sys.exit(main())
