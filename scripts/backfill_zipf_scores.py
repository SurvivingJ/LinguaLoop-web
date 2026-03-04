#!/usr/bin/env python3
"""
Backfill Zipf frequency scores for existing dim_vocabulary rows.

Queries rows where frequency_rank IS NULL, computes Zipf scores via wordfreq,
and updates in batches.

Usage:
    python scripts/backfill_zipf_scores.py --language cn [--dry-run] [--limit 500] [--batch-size 50]
    python scripts/backfill_zipf_scores.py --all [--dry-run]

Options:
    --language CODE   Language code: cn, en, jp
    --all             Process all languages
    --dry-run         Preview changes without writing to DB
    --limit N         Process at most N rows (default: 0 = all)
    --batch-size N    Rows per update batch (default: 50)
"""

import sys
import os
import argparse
import logging

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from config import Config
from services.supabase_factory import SupabaseFactory, get_supabase_admin
from services.vocabulary.frequency_service import get_zipf_score, get_zipf_score_for_phrase

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ZipfBackfillRunner:
    def __init__(self, language_code: str, dry_run: bool = False,
                 limit: int = 0, batch_size: int = 50):
        self.language_code = language_code
        self.dry_run = dry_run
        self.limit = limit
        self.batch_size = batch_size

        self.db = get_supabase_admin()
        self.language_id = Config.LANGUAGE_CODE_TO_ID.get(language_code)
        if not self.language_id:
            raise ValueError(f"Unknown language code: {language_code}")

        self.stats = {
            'rows_fetched': 0,
            'rows_updated': 0,
            'rows_null': 0,
            'rows_failed': 0,
        }

    def _fetch_null_rows(self) -> list[dict]:
        """Fetch dim_vocabulary rows where frequency_rank IS NULL for this language."""
        query = self.db.table('dim_vocabulary') \
            .select('id, lemma, phrase_type, component_lemmas') \
            .eq('language_id', self.language_id) \
            .is_('frequency_rank', 'null') \
            .order('id')

        if self.limit:
            query = query.limit(self.limit)

        response = query.execute()
        return response.data or []

    def _compute_score(self, row: dict) -> float | None:
        """Compute Zipf score for a single row."""
        lemma = row['lemma']
        if row.get('phrase_type') and row.get('component_lemmas'):
            return get_zipf_score_for_phrase(
                lemma, row['component_lemmas'], self.language_code
            )
        return get_zipf_score(lemma, self.language_code)

    def _update_batch(self, updates: list[dict]):
        """Write a batch of updates to the database."""
        for item in updates:
            try:
                self.db.table('dim_vocabulary') \
                    .update({'frequency_rank': item['frequency_rank']}) \
                    .eq('id', item['id']) \
                    .execute()
                self.stats['rows_updated'] += 1
            except Exception as e:
                logger.error(f"Failed to update id={item['id']}: {e}")
                self.stats['rows_failed'] += 1

    def run(self):
        """Execute the backfill."""
        logger.info("=" * 60)
        logger.info(f"Zipf Score Backfill: language={self.language_code} (id={self.language_id})")
        logger.info(f"  dry_run={self.dry_run}, limit={self.limit or 'all'}, batch_size={self.batch_size}")
        logger.info("=" * 60)

        rows = self._fetch_null_rows()
        self.stats['rows_fetched'] = len(rows)
        logger.info(f"Found {len(rows)} rows with NULL frequency_rank")

        if not rows:
            logger.info("Nothing to backfill!")
            return True

        batch = []
        for i, row in enumerate(rows):
            score = self._compute_score(row)
            if score is not None:
                batch.append({'id': row['id'], 'frequency_rank': score})
            else:
                self.stats['rows_null'] += 1

            # Flush batch
            if len(batch) >= self.batch_size:
                if self.dry_run:
                    logger.info(
                        f"[DRY RUN] Would update {len(batch)} rows "
                        f"(sample: id={batch[0]['id']}, score={batch[0]['frequency_rank']})"
                    )
                    self.stats['rows_updated'] += len(batch)
                else:
                    self._update_batch(batch)
                batch = []

            if (i + 1) % 200 == 0:
                logger.info(f"  Progress: {i + 1}/{len(rows)}")

        # Flush remaining
        if batch:
            if self.dry_run:
                logger.info(f"[DRY RUN] Would update {len(batch)} rows")
                self.stats['rows_updated'] += len(batch)
            else:
                self._update_batch(batch)

        # Summary
        logger.info("=" * 60)
        logger.info("Backfill Complete")
        logger.info("=" * 60)
        logger.info(f"  Rows fetched:   {self.stats['rows_fetched']}")
        logger.info(f"  Rows updated:   {self.stats['rows_updated']}")
        logger.info(f"  Rows no score:  {self.stats['rows_null']}")
        logger.info(f"  Rows failed:    {self.stats['rows_failed']}")
        logger.info("=" * 60)

        return self.stats['rows_failed'] == 0


def main():
    parser = argparse.ArgumentParser(description='Backfill Zipf frequency scores for dim_vocabulary')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--language', choices=['cn', 'en', 'jp'],
                       help='Language code to process')
    group.add_argument('--all', action='store_true',
                       help='Process all languages')
    parser.add_argument('--dry-run', action='store_true',
                        help='Preview changes without writing to DB')
    parser.add_argument('--limit', type=int, default=0,
                        help='Max rows to process per language (0=all)')
    parser.add_argument('--batch-size', type=int, default=50,
                        help='Rows per update batch')

    args = parser.parse_args()

    if args.dry_run:
        logger.info("Running in DRY RUN mode -- no changes will be made")

    # Initialize Supabase
    SupabaseFactory.initialize()

    languages = ['cn', 'en', 'jp'] if args.all else [args.language]
    all_success = True

    for lang in languages:
        runner = ZipfBackfillRunner(
            language_code=lang,
            dry_run=args.dry_run,
            limit=args.limit,
            batch_size=args.batch_size,
        )
        success = runner.run()
        if not success:
            all_success = False

    sys.exit(0 if all_success else 1)


if __name__ == '__main__':
    main()
