#!/usr/bin/env python3
"""
Batch Pitch Accent Payload Generator

Processes all Japanese tests that lack a pitch_payload and generates one
using the PitchAccentService (pyopenjtalk-based NJD analysis + mora segmentation).

Usage:
    python scripts/batch_generate_pitch_accent.py [--limit N] [--dry-run]

Options:
    --limit N    Process at most N tests (default: all)
    --dry-run    Print payloads without writing to DB
"""

import argparse
import json
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from services.supabase_factory import SupabaseFactory, get_supabase_admin
from services.pitch_accent_service import process_passage

SupabaseFactory.initialize()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)


def run(limit: int = 0, dry_run: bool = False):
    db = get_supabase_admin()

    query = db.table('tests') \
        .select('id, slug, transcript') \
        .eq('language_id', 3) \
        .eq('is_active', True) \
        .is_('pitch_payload', 'null') \
        .not_.is_('transcript', 'null') \
        .order('created_at', desc=False)

    if limit > 0:
        query = query.limit(limit)

    result = query.execute()
    tests = result.data or []
    logger.info(f"Found {len(tests)} Japanese tests to process")

    processed = 0
    errors = 0
    skipped = 0

    for test in tests:
        test_id = test['id']
        slug = test.get('slug', 'unknown')
        transcript = test.get('transcript', '')

        if not transcript or not transcript.strip():
            logger.warning(f"Skipping {slug} - empty transcript")
            skipped += 1
            continue

        try:
            payload = process_passage(transcript)
            playable = [t for t in payload if not t['is_punctuation'] and t.get('pattern_class') != 'unknown']
            review_count = sum(1 for t in payload if t.get('requires_review'))

            logger.info(
                f"[{processed + 1}/{len(tests)}] {slug}: "
                f"{len(playable)} drillable words, "
                f"{review_count} flagged for review"
            )

            if dry_run:
                print(json.dumps(payload[:5], ensure_ascii=False, indent=2))
                print(f"  ... ({len(payload)} total tokens)")
            else:
                db.table('tests').update({'pitch_payload': payload}).eq('id', test_id).execute()

            processed += 1

        except Exception as e:
            logger.error(f"Error processing {slug}: {e}")
            errors += 1

    logger.info(f"Done. Processed: {processed}, Errors: {errors}, Skipped: {skipped}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Batch generate pitch accent payloads for Japanese tests')
    parser.add_argument('--limit', type=int, default=0, help='Max tests to process (0 = all)')
    parser.add_argument('--dry-run', action='store_true', help='Print payloads without writing to DB')
    args = parser.parse_args()
    run(limit=args.limit, dry_run=args.dry_run)
