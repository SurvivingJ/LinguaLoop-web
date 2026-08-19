#!/usr/bin/env python3
"""
Validate vw_exercise_type_effectiveness against synthetic fixtures (TASK-534).

The view's logic lives in SQL, so the only honest way to test it is to run it.
This inserts a small set of exercise_attempts rows whose correct aggregate is
worked out by hand, queries the view, compares, and deletes them again.

The fixtures are chosen to exercise the decisions the view actually makes, not
just the happy path:

  * bucket boundaries        — 0.199/0.2 and 0.799/0.8 must land either side
  * bucketing on BEFORE      — a row that crosses a boundary stays in its
                               arrival bucket
  * uncaptured rows excluded — NULL p_known contributes neither delta nor time
  * zero/NULL time excluded  — otherwise the rate divides by zero
  * the 5-minute clamp       — a 60-minute row counts as 5
  * negative deltas          — BKT can move p_known down; that must drag the
                               rate down, not be silently floored at 0

Usage:
    PYTHONPATH=. python scripts/validate_effectiveness_view.py
    PYTHONPATH=. python scripts/validate_effectiveness_view.py --keep
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import uuid
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

from services.supabase_factory import SupabaseFactory, get_supabase_admin

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger('validate_effectiveness_view')

# Distinctive so a failed cleanup is obvious and greppable.
FIXTURE_TYPE_FAST = '__fixture_fast'
FIXTURE_TYPE_SLOW = '__fixture_slow'
FIXTURE_TYPE_EDGE = '__fixture_edge'
FIXTURE_TYPES = (FIXTURE_TYPE_FAST, FIXTURE_TYPE_SLOW, FIXTURE_TYPE_EDGE)

MINUTE_MS = 60_000


def _row(user_id, exercise_type, before, after, ms, correct=True, sense_id=1):
    return {
        'id': str(uuid.uuid4()),
        'user_id': user_id,
        'exercise_id': None,
        'user_response': {},
        'is_correct': correct,
        'exercise_type': exercise_type,
        'sense_id': sense_id,
        'time_taken_ms': ms,
        'p_known_before': before,
        'p_known_after': after,
        'created_at': datetime.now(timezone.utc).isoformat(),
    }


def build_fixtures(user_a: str, user_b: str) -> tuple[list[dict], dict]:
    """Return (rows, expected) where expected is hand-computed, not derived."""
    rows = [
        # --- fast type, 0.2-0.4 bucket -------------------------------------
        # two attempts, +0.10 over 1 min and +0.20 over 1 min
        # => delta 0.30 over 2.0 min => 0.15 / min
        _row(user_a, FIXTURE_TYPE_FAST, 0.20, 0.30, MINUTE_MS, sense_id=101),
        _row(user_b, FIXTURE_TYPE_FAST, 0.30, 0.50, MINUTE_MS, sense_id=102),

        # --- slow type, same bucket ----------------------------------------
        # +0.30 over 4 min => 0.075 / min. Bigger gain than either fast row,
        # worse rate: the comparison the whole view exists to make. Kept under
        # the 5-minute clamp so this case measures the rate, not the clamp.
        _row(user_a, FIXTURE_TYPE_SLOW, 0.25, 0.55, 4 * MINUTE_MS, sense_id=103),

        # --- rows that must NOT count --------------------------------------
        # no capture (BKT never ran)
        _row(user_a, FIXTURE_TYPE_FAST, None, None, MINUTE_MS, sense_id=104),
        # capture but no time
        _row(user_a, FIXTURE_TYPE_FAST, 0.20, 0.90, 0, sense_id=105),
        _row(user_a, FIXTURE_TYPE_FAST, 0.20, 0.90, None, sense_id=106),

        # --- bucket edges ---------------------------------------------------
        # Each boundary needs BOTH sides, or a bucket that swallowed everything
        # would still pass. 0.199 -> 0.0-0.2 and 0.200 -> 0.2-0.4.
        _row(user_a, FIXTURE_TYPE_EDGE, 0.199, 0.299, MINUTE_MS, sense_id=107),
        _row(user_b, FIXTURE_TYPE_EDGE, 0.200, 0.300, MINUTE_MS, sense_id=113),
        # 0.799 -> 0.6-0.8 ;  0.800 -> 0.8-1.0
        _row(user_a, FIXTURE_TYPE_EDGE, 0.799, 0.899, MINUTE_MS, sense_id=108),
        _row(user_a, FIXTURE_TYPE_EDGE, 0.800, 0.850, MINUTE_MS, sense_id=109),

        # --- clamp: 60 minutes must count as 5 ------------------------------
        # +0.40 over a claimed 60 min. Clamped => 0.40/5 = 0.08 / min.
        # Unclamped it would read 0.0067/min and the type would look useless.
        _row(user_b, FIXTURE_TYPE_SLOW, 0.60, 1.00, 60 * MINUTE_MS,
             sense_id=110, correct=False),

        # --- a negative delta must pull the rate down -----------------------
        # 0.4-0.6 bucket: +0.10 over 1 min and -0.10 over 1 min => 0.0 / min
        _row(user_a, FIXTURE_TYPE_FAST, 0.40, 0.50, MINUTE_MS, sense_id=111),
        _row(user_b, FIXTURE_TYPE_FAST, 0.50, 0.40, MINUTE_MS,
             sense_id=112, correct=False),
    ]

    expected = {
        # (bucket, type): (attempts, users, delta_per_minute, total_minutes)
        ('0.2-0.4', FIXTURE_TYPE_FAST): (2, 2, 0.150, 2.0),
        ('0.2-0.4', FIXTURE_TYPE_SLOW): (1, 1, 0.075, 4.0),  # 0.30 / 4 min
        ('0.2-0.4', FIXTURE_TYPE_EDGE): (1, 1, 0.100, 1.0),  # the 0.200 row
        ('0.0-0.2', FIXTURE_TYPE_EDGE): (1, 1, 0.100, 1.0),  # the 0.199 row
        ('0.6-0.8', FIXTURE_TYPE_EDGE): (1, 1, 0.100, 1.0),  # the 0.799 row
        ('0.8-1.0', FIXTURE_TYPE_EDGE): (1, 1, 0.050, 1.0),  # the 0.800 row
        ('0.6-0.8', FIXTURE_TYPE_SLOW): (1, 1, 0.080, 5.0),  # 0.40 / clamped 5
        ('0.4-0.6', FIXTURE_TYPE_FAST): (2, 2, 0.000, 2.0),  # +0.10 and -0.10
    }
    return rows, expected


def _close(a, b, tol=1e-6):
    if a is None or b is None:
        return a is None and b is None
    return abs(float(a) - float(b)) <= tol


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[1])
    parser.add_argument('--keep', action='store_true',
                        help='leave the fixture rows in place for inspection')
    args = parser.parse_args()

    if not SupabaseFactory.is_initialized():
        SupabaseFactory.initialize()
    db = get_supabase_admin()

    # Real user ids: exercise_attempts.user_id is a FK to auth users.
    users = (db.table('exercise_attempts').select('user_id')
               .limit(50).execute().data) or []
    distinct = list(dict.fromkeys(r['user_id'] for r in users if r.get('user_id')))
    if len(distinct) < 2:
        profiles = (db.table('users').select('id').limit(2).execute().data) or []
        distinct = [p['id'] for p in profiles]
    if len(distinct) < 2:
        logger.error('need two real user ids to build fixtures; found %d', len(distinct))
        return 1
    user_a, user_b = distinct[0], distinct[1]

    rows, expected = build_fixtures(user_a, user_b)

    logger.info('inserting %d fixture rows', len(rows))
    db.table('exercise_attempts').insert(rows).execute()

    failures: list[str] = []
    try:
        view = (db.table('vw_exercise_type_effectiveness')
                  .select('*')
                  .in_('exercise_type', list(FIXTURE_TYPES))
                  .execute().data) or []
        actual = {(r['p_known_bucket'], r['exercise_type']): r for r in view}

        for key, (att, usr, rate, minutes) in sorted(expected.items()):
            got = actual.get(key)
            if got is None:
                failures.append(f'{key}: MISSING from the view')
                continue
            problems = []
            if int(got['attempts']) != att:
                problems.append(f"attempts {got['attempts']} != {att}")
            if int(got['users']) != usr:
                problems.append(f"users {got['users']} != {usr}")
            if not _close(got['delta_p_known_per_minute'], rate):
                problems.append(
                    f"rate {got['delta_p_known_per_minute']} != {rate}")
            if not _close(got['total_minutes'], minutes):
                problems.append(f"minutes {got['total_minutes']} != {minutes}")
            if problems:
                failures.extend(f'{key}: {p}' for p in problems)
            else:
                logger.info('OK  %-28s attempts=%s users=%s rate=%s min=%s',
                            key, got['attempts'], got['users'],
                            got['delta_p_known_per_minute'], got['total_minutes'])

        # Nothing beyond what was predicted — catches uncaptured/zero-time rows
        # leaking in as extra cells.
        for key in sorted(set(actual) - set(expected)):
            failures.append(f'{key}: UNEXPECTED cell (attempts='
                            f"{actual[key]['attempts']})")
    finally:
        if args.keep:
            logger.warning('--keep: %d fixture rows left in exercise_attempts',
                           len(rows))
        else:
            db.table('exercise_attempts').delete().in_(
                'id', [r['id'] for r in rows]).execute()
            logger.info('fixtures removed')

    if failures:
        logger.error('%d FAILURE(S):', len(failures))
        for failure in failures:
            logger.error('  %s', failure)
        return 1

    logger.info('all %d fixture expectations hold', len(expected))
    return 0


if __name__ == '__main__':
    sys.exit(main())
