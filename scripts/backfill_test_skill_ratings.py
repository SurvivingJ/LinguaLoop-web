#!/usr/bin/env python3
"""
Backfill test_skill_ratings for existing tests.

This script finds tests that don't have skill ratings and creates them
with the correct ELO based on difficulty level.

Usage:
    python scripts/backfill_test_skill_ratings.py [--dry-run]

Options:
    --dry-run   Preview changes without inserting
"""

import sys
import os
import logging

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from services.supabase_factory import SupabaseFactory, get_supabase_admin

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Difficulty to ELO mapping (matches get_initial_elo() in database_client.py)
DIFFICULTY_ELO_MAP = {
    1: 800,   # A1
    2: 950,   # A1+
    3: 1100,  # A2
    4: 1250,  # B1
    5: 1400,  # B1+
    6: 1550,  # B2
    7: 1700,  # C1
    8: 1850,  # C1+
    9: 2000   # C2
}


class BackfillRunner:
    def __init__(self, dry_run: bool = False):
        self.db = get_supabase_admin()
        self.dry_run = dry_run
        self.stats = {'processed': 0, 'inserted': 0, 'skipped': 0}

    def get_active_test_types(self) -> list:
        """Fetch active test types from dim_test_types."""
        response = self.db.table('dim_test_types') \
            .select('id, type_code, requires_audio') \
            .eq('is_active', True) \
            .execute()
        return response.data or []

    def get_tests_missing_ratings(self) -> list:
        """Fetch tests that have no skill ratings."""
        # Get all test IDs that already have ratings
        existing = self.db.table('test_skill_ratings') \
            .select('test_id') \
            .execute()
        existing_ids = {r['test_id'] for r in (existing.data or [])}

        # Get all tests
        tests = self.db.table('tests') \
            .select('id, slug, difficulty, audio_url') \
            .execute()

        # Filter to those missing ratings
        return [t for t in (tests.data or []) if t['id'] not in existing_ids]

    def run(self) -> bool:
        """Execute the backfill."""
        active_types = self.get_active_test_types()
        logger.info(f"Active test types: {[t['type_code'] for t in active_types]}")

        tests = self.get_tests_missing_ratings()
        logger.info(f"Found {len(tests)} tests missing skill ratings")

        if not tests:
            logger.info("Nothing to backfill!")
            return True

        for test in tests:
            self._process_test(test, active_types)

        logger.info(f"Backfill complete: {self.stats}")
        return True

    def _process_test(self, test: dict, active_types: list):
        """Process a single test."""
        test_id = test['id']
        difficulty = test['difficulty']
        has_audio = bool(test.get('audio_url'))
        elo = DIFFICULTY_ELO_MAP.get(difficulty, 1400)

        # Filter types based on audio availability
        types_to_create = [
            t for t in active_types
            if not t['requires_audio'] or has_audio
        ]

        if not types_to_create:
            self.stats['skipped'] += 1
            return

        rows = [
            {
                'test_id': test_id,
                'test_type_id': t['id'],
                'elo_rating': elo,
                'volatility': 1.0,
                'total_attempts': 0
            }
            for t in types_to_create
        ]

        if self.dry_run:
            type_codes = [t['type_code'] for t in types_to_create]
            logger.info(f"[DRY RUN] Would insert {type_codes} for {test['slug']} (ELO {elo})")
        else:
            self.db.table('test_skill_ratings').insert(rows).execute()
            type_codes = [t['type_code'] for t in types_to_create]
            logger.info(f"Inserted {type_codes} for {test['slug']} (ELO {elo})")

        self.stats['processed'] += 1
        self.stats['inserted'] += len(rows)


def main():
    dry_run = '--dry-run' in sys.argv

    if dry_run:
        logger.info("Running in DRY RUN mode - no changes will be made")

    SupabaseFactory.initialize()
    runner = BackfillRunner(dry_run=dry_run)
    success = runner.run()
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
