#!/usr/bin/env python3
"""
Backfill Traditional-script mirrors for ZH content (TASK-509).

Two targets, both idempotent and both routed through ScriptConverter (OpenCC
s2twp + the script_conversion_overrides table):

  lemmas    — fill dim_vocabulary.lemma_traditional for every ZH lemma.
  exercises — set content['hant'] on every existing ZH exercise (~2,393 rows),
              a deep Traditional mirror of all learner-visible TL strings.

Idempotency / override-correction: each row's Traditional form is recomputed and
written ONLY when it differs from what is stored. So a plain re-run is a no-op,
but correcting an override row and re-running updates exactly the affected
mirrors (and only the `hant` key — the Simplified content is never touched).

Failures are logged and counted; they never abort the run.

Usage:
    python scripts/backfill_hant_mirrors.py --target all   [--dry-run] [--limit N] [--force]
    python scripts/backfill_hant_mirrors.py --target lemmas
    python scripts/backfill_hant_mirrors.py --target exercises --limit 20
"""

import argparse
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from services.supabase_factory import SupabaseFactory, get_supabase_admin
from services.vocabulary_ladder.script_converter import ScriptConverter

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

for _noisy in ('httpx', 'httpcore', 'hpack'):
    logging.getLogger(_noisy).setLevel(logging.WARNING)

ZH = 1
PAGE_SIZE = 1000


def backfill_lemmas(db, conv: ScriptConverter, dry_run: bool, limit: int, force: bool) -> dict:
    stats = {'updated': 0, 'skipped': 0, 'failed': 0}
    rows: list[dict] = []
    start = 0
    while True:
        batch = (
            db.table('dim_vocabulary')
            .select('id, lemma, lemma_traditional')
            .eq('language_id', ZH)
            .order('id')
            .range(start, start + PAGE_SIZE - 1)
            .execute()
        ).data or []
        rows.extend(batch)
        if len(batch) < PAGE_SIZE:
            break
        start += PAGE_SIZE
    if limit:
        rows = rows[:limit]

    logger.info("lemmas: %d ZH lemma(s) loaded", len(rows))
    for r in rows:
        lemma = (r.get('lemma') or '').strip()
        if not lemma:
            stats['skipped'] += 1
            continue
        try:
            trad = conv.convert(lemma)
        except Exception as e:
            logger.warning("convert failed for lemma %r (id=%s): %s", lemma, r['id'], e)
            stats['failed'] += 1
            continue
        current = r.get('lemma_traditional')
        if not force and current == trad:
            stats['skipped'] += 1
            continue
        if dry_run:
            stats['updated'] += 1
            continue
        try:
            db.table('dim_vocabulary').update(
                {'lemma_traditional': trad}).eq('id', r['id']).execute()
            stats['updated'] += 1
        except Exception as e:
            logger.warning("update failed for lemma id=%s: %s", r['id'], e)
            stats['failed'] += 1
    logger.info("lemmas DONE. updated=%d skipped=%d failed=%d",
                stats['updated'], stats['skipped'], stats['failed'])
    return stats


def backfill_exercises(db, conv: ScriptConverter, dry_run: bool, limit: int, force: bool) -> dict:
    stats = {'updated': 0, 'skipped': 0, 'failed': 0}
    rows: list[dict] = []
    start = 0
    while True:
        batch = (
            db.table('exercises')
            .select('id, content')
            .eq('language_id', ZH)
            .order('id')
            .range(start, start + PAGE_SIZE - 1)
            .execute()
        ).data or []
        rows.extend(batch)
        if len(batch) < PAGE_SIZE:
            break
        start += PAGE_SIZE
    if limit:
        rows = rows[:limit]

    logger.info("exercises: %d ZH exercise(s) loaded", len(rows))
    for r in rows:
        content = r.get('content')
        if not isinstance(content, dict):
            stats['skipped'] += 1
            continue
        # Mirror everything EXCEPT a pre-existing hant key (avoid nesting it).
        base = {k: v for k, v in content.items() if k != 'hant'}
        try:
            mirror = conv.convert_content(base)
        except Exception as e:
            logger.warning("convert failed for exercise %s: %s", r['id'], e)
            stats['failed'] += 1
            continue
        if not force and content.get('hant') == mirror:
            stats['skipped'] += 1
            continue
        if dry_run:
            stats['updated'] += 1
            continue
        new_content = dict(content)
        new_content['hant'] = mirror
        try:
            db.table('exercises').update(
                {'content': new_content}).eq('id', r['id']).execute()
            stats['updated'] += 1
        except Exception as e:
            logger.warning("update failed for exercise %s: %s", r['id'], e)
            stats['failed'] += 1
    logger.info("exercises DONE. updated=%d skipped=%d failed=%d",
                stats['updated'], stats['skipped'], stats['failed'])
    return stats


def main():
    parser = argparse.ArgumentParser(description='Backfill ZH Traditional mirrors (TASK-509).')
    parser.add_argument('--target', choices=['lemmas', 'exercises', 'all'], default='all')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--limit', type=int, default=0)
    parser.add_argument('--force', action='store_true',
                        help='Rewrite even rows whose mirror already matches.')
    args = parser.parse_args()

    if not SupabaseFactory.is_initialized():
        SupabaseFactory.initialize()
    db = get_supabase_admin()
    if db is None:
        raise RuntimeError("Service role client unavailable (set SUPABASE_SERVICE_ROLE_KEY).")

    conv = ScriptConverter.from_db(db)

    if args.target in ('lemmas', 'all'):
        backfill_lemmas(db, conv, args.dry_run, args.limit, args.force)
    if args.target in ('exercises', 'all'):
        backfill_exercises(db, conv, args.dry_run, args.limit, args.force)


if __name__ == '__main__':
    main()
