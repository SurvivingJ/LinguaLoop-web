#!/usr/bin/env python3
"""
Batch Pitch Accent Payload Generator

Processes all Japanese tests that lack a pitch_payload and generates one
using the PitchAccentService (pyopenjtalk-based NJD analysis + mora segmentation).

Usage:
    python scripts/batch_generate_pitch_accent.py [--limit N] [--apply]

Options:
    --limit N    Process at most N tests (default: all)
    --apply      Write the payloads (default: dry run)
    --dry-run    Print payloads without writing to DB (the default)
"""

import json
import logging

try:
    from _common import base_parser, bootstrap
except ImportError:  # run or imported as scripts.<name>
    from scripts._common import base_parser, bootstrap

bootstrap()


from services.supabase_factory import SupabaseFactory, get_supabase_admin
from services.pitch_accent_service import process_passage

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


def main(argv=None):
    parser = base_parser(description='Batch generate pitch accent payloads for Japanese tests',
                         dry_run_help='Print payloads without writing to DB (the default)')
    parser.add_argument('--limit', type=int, default=0, help='Max tests to process (0 = all)')
    args = parser.parse_args(argv)
    # Here, not at import: --help and the tests must not need Supabase credentials.
    if not SupabaseFactory.is_initialized():
        SupabaseFactory.initialize()
    run(limit=args.limit, dry_run=args.dry_run)


if __name__ == '__main__':
    main()
