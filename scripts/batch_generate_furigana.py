#!/usr/bin/env python3
"""
Batch Furigana Payload Generator

Fills tests.furigana_payload for Japanese tests that lack one, using
FuriganaService (fugashi/MeCab tokenisation + okurigana alignment).

Why this exists
---------------
services/test_service.py (the single-test UI path) has always written a
furigana payload for ja tests, but services/test_generation/orchestrator.py
(the batch runner that produced the live corpus) only ever had the zh pinyin
branch. Every ja test in the live DB therefore shipped with
furigana_payload NULL. The orchestrator gap is fixed separately; this script
repairs the tests already generated.

Ordering
--------
The payload's `questions` array is positional — the frontend reads
`furiganaPayload.questions[index]` against its own render order. Questions are
fetched here ordered by `question_id`, which the generator writes as
"<slug>-qN" in creation order; the API read paths sort the same way, so index i
in the payload is the same question the page renders at position i. Live ja
tests carry at most 5 questions, so the lexicographic sort on "q1".."q5" is
also numeric order (this would need zero-padding past q9).

Usage:
    python scripts/batch_generate_furigana.py [--limit N] [--dry-run] [--force]

Options:
    --limit N    Process at most N tests (default: all)
    --dry-run    Print a payload summary without writing to DB
    --force      Also reprocess tests that already have a furigana_payload
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
from services.furigana_service import process_test_payload

SupabaseFactory.initialize()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)

JAPANESE_LANGUAGE_ID = 3


def _ruby_count(tokens) -> int:
    """Number of tokens that will actually render as <ruby> (i.e. carry kanji).

    A payload of all-`plain` tokens is technically valid but useless — it means
    the tokenizer degraded or the passage has no kanji. Counting them separates
    "worked" from "silently produced nothing", which a row count alone hides.
    """
    return sum(1 for t in tokens if isinstance(t, dict) and t.get('kind') == 'ruby')


def run(limit: int = 0, dry_run: bool = False, force: bool = False):
    db = get_supabase_admin()

    query = db.table('tests') \
        .select('id, slug, transcript') \
        .eq('language_id', JAPANESE_LANGUAGE_ID) \
        .eq('is_active', True) \
        .not_.is_('transcript', 'null') \
        .order('created_at', desc=False)

    if not force:
        query = query.is_('furigana_payload', 'null')

    if limit > 0:
        query = query.limit(limit)

    tests = (query.execute().data) or []
    logger.info(f"Found {len(tests)} Japanese tests to process")

    processed = 0
    errors = 0
    skipped = 0
    empty = 0

    for test in tests:
        test_id = test['id']
        slug = test.get('slug', 'unknown')
        transcript = test.get('transcript', '')

        if not transcript or not transcript.strip():
            logger.warning(f"Skipping {slug} - empty transcript")
            skipped += 1
            continue

        try:
            questions = (
                db.table('questions')
                .select('question_id, question_text, choices')
                .eq('test_id', test_id)
                .order('question_id')
                .execute()
                .data
            ) or []

            payload = process_test_payload(transcript, questions)

            transcript_ruby = _ruby_count(payload.get('transcript') or [])
            question_ruby = sum(
                _ruby_count(q.get('text') or [])
                + sum(_ruby_count(c) for c in (q.get('choices') or []))
                for q in (payload.get('questions') or [])
            )

            # An all-plain payload means fugashi degraded or the passage has no
            # kanji. Either way there is nothing for the learner to toggle, so
            # count it rather than reporting it as a success.
            if transcript_ruby == 0:
                logger.warning(
                    f"{slug}: 0 ruby tokens in transcript - "
                    f"tokenizer degraded or passage has no kanji"
                )
                empty += 1

            logger.info(
                f"[{processed + 1}/{len(tests)}] {slug}: "
                f"{transcript_ruby} ruby tokens in transcript, "
                f"{question_ruby} across {len(payload.get('questions') or [])} questions"
            )

            if dry_run:
                print(json.dumps(
                    (payload.get('transcript') or [])[:5],
                    ensure_ascii=False, indent=2,
                ))
                print(f"  ... ({len(payload.get('transcript') or [])} total tokens)")
            else:
                db.table('tests') \
                    .update({'furigana_payload': payload}) \
                    .eq('id', test_id) \
                    .execute()

            processed += 1

        except Exception as e:
            logger.error(f"Error processing {slug}: {e}")
            errors += 1

    logger.info(
        f"Done. Processed: {processed}, Errors: {errors}, "
        f"Skipped: {skipped}, No-ruby: {empty}"
    )


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Batch generate furigana payloads for Japanese tests'
    )
    parser.add_argument('--limit', type=int, default=0,
                        help='Max tests to process (0 = all)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Print payload summaries without writing to DB')
    parser.add_argument('--force', action='store_true',
                        help='Reprocess tests that already have a payload')
    args = parser.parse_args()
    run(limit=args.limit, dry_run=args.dry_run, force=args.force)
