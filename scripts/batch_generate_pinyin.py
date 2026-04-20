#!/usr/bin/env python3
"""
Batch Pinyin Payload Generator

Processes all Chinese tests that lack a pinyin_payload and generates one
using the PinyinService (jieba + pypinyin + deterministic sandhi).

Optionally resolves flagged polyphones via LLM (--resolve-polyphones flag).

Usage:
    python scripts/batch_generate_pinyin.py [--limit N] [--resolve-polyphones] [--dry-run]

Options:
    --limit N               Process at most N tests (default: all)
    --resolve-polyphones    Use LLM to resolve ambiguous polyphones
    --dry-run               Print payloads without writing to DB
"""

import sys
import os
import json
import argparse
import logging
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from services.supabase_factory import get_supabase_admin
from services.pinyin_service import process_passage, resolve_polyphones_llm

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run(limit: int = 0, resolve_polyphones: bool = False, dry_run: bool = False):
    db = get_supabase_admin()

    # Fetch Chinese tests without pinyin_payload
    query = db.table('tests') \
        .select('id, slug, transcript') \
        .eq('language_id', 1) \
        .eq('is_active', True) \
        .is_('pinyin_payload', 'null') \
        .not_.is_('transcript', 'null') \
        .order('created_at', desc=False)

    if limit > 0:
        query = query.limit(limit)

    result = query.execute()
    tests = result.data or []

    logger.info(f"Found {len(tests)} Chinese tests to process")

    processed = 0
    errors = 0

    for test in tests:
        test_id = test['id']
        slug = test.get('slug', 'unknown')
        transcript = test.get('transcript', '')

        if not transcript or not transcript.strip():
            logger.warning(f"Skipping test {slug} — empty transcript")
            continue

        try:
            payload = process_passage(transcript)

            if resolve_polyphones:
                flagged_count = sum(1 for t in payload if t.get('requires_review'))
                if flagged_count > 0:
                    logger.info(f"  Resolving {flagged_count} polyphones for {slug}...")
                    payload = resolve_polyphones_llm(transcript, payload)
                    time.sleep(0.5)  # Rate limiting for LLM calls

            playable = [t for t in payload if not t['is_punctuation']]
            logger.info(
                f"[{processed + 1}/{len(tests)}] {slug}: "
                f"{len(playable)} chars, "
                f"{sum(1 for t in playable if t['is_sandhi'])} sandhi, "
                f"{sum(1 for t in playable if t['requires_review'])} unresolved"
            )

            if dry_run:
                print(json.dumps(payload[:5], ensure_ascii=False, indent=2))
                print(f"  ... ({len(payload)} total tokens)")
            else:
                db.table('tests').update({
                    'pinyin_payload': payload
                }).eq('id', test_id).execute()

            processed += 1

        except Exception as e:
            logger.error(f"Error processing {slug}: {e}")
            errors += 1

    logger.info(f"Done. Processed: {processed}, Errors: {errors}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Batch generate pinyin payloads for Chinese tests')
    parser.add_argument('--limit', type=int, default=0, help='Max tests to process (0 = all)')
    parser.add_argument('--resolve-polyphones', action='store_true', help='Use LLM for polyphone disambiguation')
    parser.add_argument('--dry-run', action='store_true', help='Print payloads without writing to DB')
    args = parser.parse_args()

    run(limit=args.limit, resolve_polyphones=args.resolve_polyphones, dry_run=args.dry_run)
