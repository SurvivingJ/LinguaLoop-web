#!/usr/bin/env python3
"""
Retire legacy vocabulary exercises for covered senses (TASK-518).

Two generations of vocabulary content coexist in the ``exercises`` table:

  * **legacy** — ``source_type='vocabulary' AND word_asset_id IS NULL``.
    Produced by the pre-ladder generator. Never judged.
  * **ladder** — ``word_asset_id IS NOT NULL``. Judge-gated, capability-routed,
    the output of the batch runner.

While both are active a practice session mixes them, so a learner working a
fully-generated sense still meets unjudged content roughly half the time, and
the whole judging apparatus buys nothing for that sense.

Usage::

    python -m scripts.dedupe_legacy_vocab_exercises --dry-run
    python -m scripts.dedupe_legacy_vocab_exercises --language 1
    python -m scripts.dedupe_legacy_vocab_exercises --reactivate   # undo

Two safety properties, both deliberate:

**Only fully-covered senses.** A sense is deduped only when
``v_sense_family_coverage`` reports no missing family. Retiring legacy content
for a partially-covered sense would leave a family with *nothing* to serve,
which is strictly worse than serving unjudged content for it.

**Deactivate, never delete.** ``is_active=false`` is reversible; a DELETE is
not, and these rows carry the attempt history that IRT calibration reads.
``--reactivate`` is the undo, and it exists so running this is not a one-way
door.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger('dedupe_legacy')

_PAGE = 1000
_UPDATE_BATCH = 200


def covered_sense_ids(db, language_id: int | None) -> set[int]:
    """Senses whose every required family has an active ladder exercise.

    Built from the view's own rows rather than by subtracting gaps: a sense
    absent from the view has no ladder assets at all, and must not be deduped
    either.
    """
    covered: set[int] = set()
    offset = 0
    while True:
        try:
            query = (
                db.table('v_sense_family_coverage')
                .select('sense_id, language_id, missing_count')
                .eq('missing_count', 0)
                .range(offset, offset + _PAGE - 1)
            )
            if language_id is not None:
                query = query.eq('language_id', language_id)
            rows = query.execute().data or []
        except Exception as exc:
            logger.error('coverage query failed: %s', exc)
            return covered
        covered |= {row['sense_id'] for row in rows}
        if len(rows) < _PAGE:
            break
        offset += _PAGE
    return covered


def legacy_rows(db, sense_ids: set[int], active: bool = True) -> list[dict]:
    """Legacy vocabulary exercises belonging to the given senses."""
    if not sense_ids:
        return []
    ids = sorted(sense_ids)
    found: list[dict] = []
    for start in range(0, len(ids), _UPDATE_BATCH):
        window = ids[start:start + _UPDATE_BATCH]
        try:
            rows = (
                db.table('exercises')
                .select('id, word_sense_id, exercise_type, language_id')
                .eq('source_type', 'vocabulary')
                .is_('word_asset_id', 'null')
                .eq('is_active', active)
                .in_('word_sense_id', window)
                .execute()
            ).data or []
            found.extend(rows)
        except Exception as exc:
            logger.error('legacy lookup failed for a window: %s', exc)
    return found


def set_active(db, exercise_ids: list[str], active: bool) -> int:
    changed = 0
    for start in range(0, len(exercise_ids), _UPDATE_BATCH):
        window = exercise_ids[start:start + _UPDATE_BATCH]
        try:
            db.table('exercises').update(
                {'is_active': active}).in_('id', window).execute()
            changed += len(window)
        except Exception as exc:
            logger.error('update failed for a window of %d: %s', len(window), exc)
    return changed


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Deactivate legacy vocabulary exercises for covered senses')
    parser.add_argument('--language', type=int, choices=[1, 2, 3], default=None)
    parser.add_argument('--dry-run', action='store_true',
                        help='count what would change and stop')
    parser.add_argument('--reactivate', action='store_true',
                        help='undo: reactivate previously deduped legacy rows')
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s %(levelname)s %(message)s',
                        stream=sys.stdout)

    from services.supabase_factory import SupabaseFactory, get_supabase_admin
    SupabaseFactory.initialize()
    db = get_supabase_admin()

    covered = covered_sense_ids(db, args.language)
    logger.info('%d fully-covered senses', len(covered))
    if not covered:
        logger.info('nothing to do — run the batch first')
        return

    # When reactivating, the rows to find are the *inactive* ones.
    rows = legacy_rows(db, covered, active=not args.reactivate)
    by_type: dict[str, int] = {}
    for row in rows:
        by_type[row['exercise_type']] = by_type.get(row['exercise_type'], 0) + 1

    verb = 'reactivate' if args.reactivate else 'deactivate'
    logger.info('%d legacy exercises to %s across %d senses',
                len(rows), verb, len({r['word_sense_id'] for r in rows}))
    for exercise_type, count in sorted(by_type.items(), key=lambda kv: -kv[1]):
        logger.info('  %-28s %d', exercise_type, count)

    if args.dry_run:
        logger.info('[dry-run] no rows changed')
        return
    if not rows:
        return

    changed = set_active(db, [r['id'] for r in rows], active=args.reactivate)
    logger.info('%sd %d rows — reversible with --%s',
                verb, changed, 'dry-run' if args.reactivate else 'reactivate')


if __name__ == '__main__':
    main()
