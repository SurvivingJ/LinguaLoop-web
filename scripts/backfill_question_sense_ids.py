#!/usr/bin/env python3
"""
Backfill sense_ids on the questions table.

For each test with a vocab_token_map, assigns all non-zero sense_ids
from the token map to every question in that test. This is intentionally
broad — comprehension questions test understanding of the whole passage,
so all vocabulary in the passage is relevant evidence.

Usage:
    python scripts/backfill_question_sense_ids.py --language cn [--limit 10] [--force]

Options:
    --language CODE   Required. Language code: cn, en, jp
    --limit N         Process at most N tests (default: all)
    --force           Overwrite existing sense_ids on questions
"""

import sys
import os
import argparse
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from config import Config
from services.supabase_factory import SupabaseFactory, get_supabase_admin

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_backfill(language_code: str, limit: int = 0, force: bool = False):
    db = get_supabase_admin()
    language_id = Config.LANGUAGE_CODE_TO_ID.get(language_code)
    if not language_id:
        raise ValueError(f"Unknown language code: {language_code}")

    # Fetch tests with vocab_token_map
    query = db.table('tests') \
        .select('id, slug, vocab_token_map') \
        .eq('language_id', language_id) \
        .eq('is_active', True) \
        .not_.is_('vocab_token_map', 'null') \
        .order('created_at')

    if limit:
        query = query.limit(limit)

    tests = (query.execute()).data or []
    logger.info(f"Found {len(tests)} tests with vocab_token_map for {language_code}")

    stats = {'tests': 0, 'questions_updated': 0, 'skipped': 0}

    for i, test in enumerate(tests):
        test_id = test['id']
        slug = test['slug']
        token_map = test.get('vocab_token_map') or []

        # Extract unique non-zero sense_ids from token map
        sense_ids = list(set(s for _, s in token_map if s))
        if not sense_ids:
            logger.warning(f"Skipping {slug}: no sense_ids in token map")
            stats['skipped'] += 1
            continue

        # Fetch questions for this test
        q_query = db.table('questions') \
            .select('id, sense_ids') \
            .eq('test_id', test_id)

        questions = (q_query.execute()).data or []
        if not questions:
            logger.warning(f"Skipping {slug}: no questions found")
            stats['skipped'] += 1
            continue

        # Update each question
        updated = 0
        for q in questions:
            if not force and q.get('sense_ids') and len(q['sense_ids']) > 0:
                continue  # Already has sense_ids

            db.table('questions') \
                .update({'sense_ids': sense_ids}) \
                .eq('id', q['id']) \
                .execute()
            updated += 1

        stats['questions_updated'] += updated
        stats['tests'] += 1
        logger.info(
            f"[{i+1}/{len(tests)}] {slug}: "
            f"{len(sense_ids)} sense_ids → {updated}/{len(questions)} questions"
        )

    logger.info("=" * 60)
    logger.info("Backfill Complete")
    logger.info(f"  Tests processed:    {stats['tests']}")
    logger.info(f"  Tests skipped:      {stats['skipped']}")
    logger.info(f"  Questions updated:  {stats['questions_updated']}")
    logger.info("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description='Backfill sense_ids on questions table'
    )
    parser.add_argument('--language', required=True, choices=['cn', 'en', 'jp'],
                        help='Language code to process')
    parser.add_argument('--limit', type=int, default=0,
                        help='Max number of tests to process (0=all)')
    parser.add_argument('--force', action='store_true',
                        help='Overwrite existing sense_ids')

    args = parser.parse_args()

    SupabaseFactory.initialize()
    run_backfill(
        language_code=args.language,
        limit=args.limit,
        force=args.force,
    )


if __name__ == '__main__':
    main()
