#!/usr/bin/env python3
"""
Re-run services.pinyin_service.process_passage over existing tests.pinyin_payload.

The sandhi engine used to strip punctuation before applying tone-sandhi rules,
so a comma/full-stop-separated clause boundary could be silently treated as
two adjacent characters (e.g. "你好，你好" wrongly flipped the first 好 to
tone 2, as if there were no comma). That bug is fixed in pinyin_service.py,
but every test's pinyin_payload was generated once at test-creation time
(services/test_service.py, services/test_generation/orchestrator.py) and is
served as-is thereafter -- the fix does not apply retroactively on its own.

This script recomputes pinyin_payload for every Chinese (language_id=1) test
that has a transcript, and only writes back rows whose payload actually
changed, so it's cheap and safe to re-run and easy to audit with --dry-run.

Idempotent: a row whose recomputed payload matches the stored payload is
left untouched. Failures are logged with a reason and counted; they never
abort the run.

Usage:
    python scripts/backfill_pinyin_payload_punctuation_fix.py [--dry-run] [--limit N]
"""

import argparse
import logging
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from services.supabase_factory import SupabaseFactory, get_supabase_admin

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Quiet per-request HTTP / segmentation chatter (thousands of rows otherwise).
for _noisy in ('httpx', 'httpcore', 'hpack', 'jieba'):
    logging.getLogger(_noisy).setLevel(logging.WARNING)

ZH_LANGUAGE_ID = 1
PAGE_SIZE = 1000


def fetch_tests(db, limit: int) -> list[dict]:
    """Page through Chinese tests that have a transcript."""
    rows: list[dict] = []
    start = 0
    while True:
        resp = (
            db.table('tests')
            .select('id, transcript, pinyin_payload')
            .eq('language_id', ZH_LANGUAGE_ID)
            .not_.is_('transcript', 'null')
            .range(start, start + PAGE_SIZE - 1)
            .execute()
        )
        batch = resp.data or []
        rows.extend(batch)
        if len(batch) < PAGE_SIZE:
            break
        start += PAGE_SIZE
        if limit and len(rows) >= limit:
            break

    rows = [r for r in rows if (r.get('transcript') or '').strip()]
    if limit:
        rows = rows[:limit]
    return rows


def main():
    parser = argparse.ArgumentParser(
        description='Recompute tests.pinyin_payload after the punctuation-boundary sandhi fix.'
    )
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--limit', type=int, default=0)
    args = parser.parse_args()

    from services.pinyin_service import process_passage

    if not SupabaseFactory.is_initialized():
        SupabaseFactory.initialize()
    db = get_supabase_admin()
    if db is None:
        raise RuntimeError("Service role client unavailable (set SUPABASE_SERVICE_ROLE_KEY).")

    tests = fetch_tests(db, args.limit)
    logger.info("Fetched %d Chinese test(s) with a transcript", len(tests))

    stats = {'changed': 0, 'unchanged': 0, 'failed': 0}
    for row in tests:
        test_id = row['id']
        transcript = row['transcript']
        old_payload = row.get('pinyin_payload')

        try:
            new_payload = process_passage(transcript)
        except Exception as e:
            logger.warning("Sandhi recompute failed for test %s: %s", test_id, e)
            stats['failed'] += 1
            continue

        if new_payload == old_payload:
            stats['unchanged'] += 1
            continue

        stats['changed'] += 1
        if args.dry_run:
            logger.info("[dry-run] test %s pinyin_payload would change (%r)", test_id, transcript[:40])
            continue

        try:
            db.table('tests').update({'pinyin_payload': new_payload}).eq('id', test_id).execute()
        except Exception as e:
            logger.warning("DB update failed for test %s: %s", test_id, e)
            stats['failed'] += 1
            stats['changed'] -= 1

    logger.info("Done. changed=%d unchanged=%d failed=%d",
                stats['changed'], stats['unchanged'], stats['failed'])


if __name__ == '__main__':
    main()
