#!/usr/bin/env python3
"""
Export tests whose vocabulary has never been linked to word senses.

Stage 1 of the sense-linking workflow (.claude/skills/test-sense-linking/SKILL.md).
Selects every test with a NULL or empty `vocab_sense_ids` and writes one CSV row
per test, transcript included, as the worklist the later stages iterate.

The CSV is a worklist, not a store. Nothing downstream reads a sense, a vocab_id
or a definition back out of it — stage 2 re-queries the database for those. Its
only job is to name which tests need work and carry the text to extract from.

Two columns exist to spot the cheap cases before any LLM runs:
`token_map_tokens` and `token_map_linked_tokens`. A test with a populated token
map already carries sense ids inside it, and its `vocab_sense_ids` can be
rebuilt from that map with no LLM call at all — see
`scripts/upload_test_senses.py --from-token-map`.

Usage:
    python scripts/export_tests_missing_senses.py
    python scripts/export_tests_missing_senses.py --language zh
    python scripts/export_tests_missing_senses.py --include-inactive -o data/sense_linking/all.csv

Options:
    --language CODE      zh | en | ja. Default: all languages.
    --output PATH        CSV destination (default: data/sense_linking/tests_missing_senses.csv)
    --include-inactive   Include tests with is_active = false (default: active only)
    --limit N            Export at most N tests (0 = all)
"""

import os
import sys
import csv
import argparse
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from config import Config
from services.supabase_factory import SupabaseFactory, get_supabase_admin
from scripts.sense_linking_common import PAGE, language_code_for

if not SupabaseFactory.is_initialized():
    SupabaseFactory.initialize()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DEFAULT_OUTPUT = os.path.join('data', 'sense_linking', 'tests_missing_senses.csv')

COLUMNS = [
    'test_id',
    'slug',
    'language_code',
    'language_id',
    'difficulty',
    'is_active',
    'transcript_chars',
    'token_map_tokens',
    'token_map_linked_tokens',
    'transcript',
]


def fetch_tests(db, language_id: int | None, include_inactive: bool) -> list[dict]:
    """Page through tests and keep the ones with no linked senses.

    The empty-array test is done in Python rather than PostgREST: `vocab_sense_ids`
    is NULL on some rows and `{}` on others, and an or-filter spanning both is
    easy to get subtly wrong against a few hundred rows that all fit in memory.
    """
    rows: list[dict] = []
    offset = 0
    while True:
        q = db.table('tests') \
            .select('id, slug, language_id, difficulty, is_active, transcript, '
                    'vocab_sense_ids, vocab_token_map') \
            .order('id')
        if language_id is not None:
            q = q.eq('language_id', language_id)
        if not include_inactive:
            q = q.eq('is_active', True)

        page = (q.range(offset, offset + PAGE - 1).execute().data or [])
        rows.extend(page)
        if len(page) < PAGE:
            break
        offset += PAGE

    return [r for r in rows if not (r.get('vocab_sense_ids') or [])]


def to_csv_row(test: dict) -> dict:
    token_map = test.get('vocab_token_map') or []
    linked = sum(1 for t in token_map if isinstance(t, (list, tuple)) and len(t) > 1 and t[1])
    transcript = test.get('transcript') or ''
    return {
        'test_id': test['id'],
        'slug': test.get('slug') or '',
        'language_code': language_code_for(test['language_id']),
        'language_id': test['language_id'],
        'difficulty': test.get('difficulty'),
        'is_active': test.get('is_active'),
        'transcript_chars': len(transcript),
        'token_map_tokens': len(token_map),
        'token_map_linked_tokens': linked,
        'transcript': transcript,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--language', choices=['zh', 'en', 'ja'],
                        help='Restrict to one language (default: all)')
    parser.add_argument('--output', '-o', default=DEFAULT_OUTPUT,
                        help=f'CSV destination (default: {DEFAULT_OUTPUT})')
    parser.add_argument('--include-inactive', action='store_true',
                        help='Include tests with is_active = false')
    parser.add_argument('--limit', type=int, default=0,
                        help='Export at most N tests (0 = all)')
    args = parser.parse_args()

    language_id = Config.LANGUAGE_CODE_TO_ID.get(args.language) if args.language else None
    db = get_supabase_admin()

    tests = fetch_tests(db, language_id, args.include_inactive)
    if args.limit:
        tests = tests[:args.limit]

    if not tests:
        logger.info("No tests are missing senses — nothing to export.")
        return 0

    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)

    # utf-8-sig: these files get opened in Excel to eyeball a transcript, and
    # without the BOM every CJK transcript renders as mojibake there.
    with open(args.output, 'w', encoding='utf-8-sig', newline='') as fh:
        writer = csv.DictWriter(fh, fieldnames=COLUMNS)
        writer.writeheader()
        by_language: dict[str, int] = {}
        reusable = 0
        for test in tests:
            row = to_csv_row(test)
            writer.writerow(row)
            by_language[row['language_code']] = by_language.get(row['language_code'], 0) + 1
            if row['token_map_linked_tokens']:
                reusable += 1

    logger.info("Wrote %d tests to %s", len(tests), args.output)
    for code in sorted(by_language):
        logger.info("  %s: %d", code, by_language[code])
    if reusable:
        logger.info(
            "%d of them already carry sense ids in vocab_token_map — those need no "
            "LLM pass, see: python scripts/upload_test_senses.py --from-token-map",
            reusable,
        )
    return 0


if __name__ == '__main__':
    sys.exit(main())
