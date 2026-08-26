#!/usr/bin/env python3
"""
Backfill dim_vocabulary.reading for existing Japanese rows.

New rows get `reading` populated at creation time (see
services/test_generation/orchestrator.py _get_or_create_vocab_id). This
script fills it in for everything created before that — required before
the homophone-family lookup (services/vocabulary/kana_homophone_judge.py)
can see any pre-existing vocabulary as candidates.

Reading is derived by re-running fugashi on each stored `lemma` in
isolation (JapaneseProcessor.reading_for). That's a *different* code path
from how a live token's reading is captured (straight from the token's own
analysis inside its sentence) — re-deriving from an isolated lemma string
can occasionally disagree with how that lemma was reached in a real
sentence (為る is the documented case: isolated it reads なる, but it is
also UniDic's own 'lemma' output for conjugated する-forms — see
japanese.py). That's an accepted, unavoidable approximation for a backfill
that only has the stored lemma text to work from; it's still far better
than no reading at all, and the homophone judge sees the ambiguity as a
same-reading collision either way and reasons over sentence context, not
over which code path produced the reading.

Usage:
    python scripts/backfill_vocab_reading.py [--dry-run] [--limit N] [--batch-size 500]
"""

import sys
import os
import argparse
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from services.supabase_factory import SupabaseFactory, get_supabase_admin
from services.vocabulary.processors.japanese import JapaneseProcessor

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

LANGUAGE_ID_JA = 3


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--limit', type=int, default=0)
    parser.add_argument('--batch-size', type=int, default=500)
    args = parser.parse_args()

    SupabaseFactory.initialize()
    db = get_supabase_admin()
    processor = JapaneseProcessor()

    # Paginate — PostgREST caps a single response at 1000 rows by default,
    # and this table has 3000+ Japanese entries.
    rows = []
    page_size = 1000
    offset = 0
    while True:
        resp = db.table('dim_vocabulary') \
            .select('id, lemma') \
            .eq('language_id', LANGUAGE_ID_JA) \
            .is_('reading', 'null') \
            .range(offset, offset + page_size - 1) \
            .execute()
        page = resp.data or []
        rows.extend(page)
        if len(page) < page_size:
            break
        offset += page_size
        if args.limit and len(rows) >= args.limit:
            break
    if args.limit:
        rows = rows[:args.limit]

    logger.info("Found %d dim_vocabulary rows (language_id=%d) missing reading",
                len(rows), LANGUAGE_ID_JA)

    updated = 0
    failed = 0
    for row in rows:
        lemma = row.get('lemma') or ''
        if not lemma.strip():
            continue
        try:
            reading = processor.reading_for(lemma)
        except Exception as e:
            logger.warning("reading_for failed for id=%s lemma=%r: %s", row['id'], lemma, e)
            failed += 1
            continue

        if not reading:
            continue

        if args.dry_run:
            logger.info("[dry-run] id=%s lemma=%r -> reading=%r", row['id'], lemma, reading)
        else:
            db.table('dim_vocabulary').update({'reading': reading}).eq('id', row['id']).execute()
        updated += 1

    logger.info("Done: %d updated, %d failed, %s", updated, failed,
                '(dry-run, nothing written)' if args.dry_run else '')


if __name__ == '__main__':
    main()
