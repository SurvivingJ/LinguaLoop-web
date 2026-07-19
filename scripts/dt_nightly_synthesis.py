#!/usr/bin/env python3
"""Dual Translation — nightly error-synthesis runner (TASK-610).

Off-hot-path batch job. Reads the last ``2 × W`` days of ``dt_error_instance``
rows, joins each to its submission (user, L1) and passage (L2), then hands the
flat record list to ``services.dual_translation.synthesis`` — which does the
pure mistake-gate → cluster → promote → profile work — and upserts the result
into ``dt_error_profile_entry`` (one row per user × l1↔l2 pair × subtype).

No embeddings and no LLM calls: clustering is a deterministic group-by on the
taxonomy ``subtype`` the grader already emitted. All LLM spend stays in grading.

Idempotent: upsert on the ``(user_id, l1_language_id, l2_language_id, subtype)``
UNIQUE key, so re-running the same window converges to the same profile rows.
In-flight (``drilling``) and finished (``resolved``) statuses are read back and
preserved — the nightly re-count never regresses them.

The two knobs (W = window days, N = promotion threshold) are read from the
environment (``DT_SYNTHESIS_WINDOW_DAYS`` / ``DT_SYNTHESIS_PROMOTE_THRESHOLD``)
and overridable per-run via flags, so promotion sensitivity is tunable without a
code deploy. (These mirror the other DT_* ops knobs in config.py and can be
promoted onto ``Config`` later.)

Usage:
    python scripts/dt_nightly_synthesis.py [--window-days N] [--threshold N]
                                           [--user UUID] [--dry-run]
"""

import argparse
import logging
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from services.supabase_factory import get_supabase_admin
from services.dual_translation import synthesis

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('dt_nightly_synthesis')

DEFAULT_WINDOW_DAYS = int(os.environ.get('DT_SYNTHESIS_WINDOW_DAYS', '30'))
DEFAULT_THRESHOLD = int(os.environ.get('DT_SYNTHESIS_PROMOTE_THRESHOLD', '3'))

# PostgREST caps a single response page; chunk the .in_() lookups and upserts.
_CHUNK = 500


def _parse_ts(value: str) -> datetime:
    """Parse a Postgres timestamptz string into a tz-aware datetime.

    Supabase returns ISO-8601 (``2026-07-01T12:00:00.123456+00:00`` or a
    trailing ``Z``). A value that somehow lacks an offset is treated as UTC so
    the window comparison never blows up on a naive/aware mismatch.
    """
    ts = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts


def _fetch_in_chunks(db, table: str, key: str, values: list, columns: str) -> list[dict]:
    """SELECT ``columns`` from ``table`` WHERE ``key`` IN ``values``, chunked."""
    rows: list[dict] = []
    for i in range(0, len(values), _CHUNK):
        chunk = values[i:i + _CHUNK]
        resp = db.table(table).select(columns).in_(key, chunk).execute()
        rows.extend(resp.data or [])
    return rows


def fetch_error_records(db, *, since: datetime, user_id: str | None = None) -> list[dict]:
    """Load ``dt_error_instance`` rows since ``since`` and join them to their
    submission (user_id, l1) and passage (l2) into flat synthesis records.

    The join is done with explicit id-set lookups rather than a PostgREST
    embedded select so it never depends on FK-relationship auto-detection.
    """
    errors = (
        db.table('dt_error_instance')
        .select('submission_id, subtype, severity, is_mistake, created_at')
        .gte('created_at', since.isoformat())
        .execute()
        .data
        or []
    )
    if not errors:
        return []

    submission_ids = sorted({e['submission_id'] for e in errors})
    submissions = _fetch_in_chunks(
        db, 'dt_submission', 'id', submission_ids,
        'id, user_id, l1_language_id, passage_id',
    )
    if user_id is not None:
        submissions = [s for s in submissions if s['user_id'] == user_id]
    submission_by_id = {s['id']: s for s in submissions}

    passage_ids = sorted({s['passage_id'] for s in submissions})
    passages = _fetch_in_chunks(db, 'dt_passage', 'id', passage_ids, 'id, l2_language_id')
    l2_by_passage = {p['id']: p['l2_language_id'] for p in passages}

    records: list[dict] = []
    dropped = 0
    for e in errors:
        sub = submission_by_id.get(e['submission_id'])
        if sub is None:  # filtered out by --user, or a dangling submission_id
            continue
        l2 = l2_by_passage.get(sub['passage_id'])
        if l2 is None:
            dropped += 1
            continue
        records.append({
            'user_id': sub['user_id'],
            'l1_language_id': sub['l1_language_id'],
            'l2_language_id': l2,
            'subtype': e['subtype'],
            'severity': e['severity'],
            'is_mistake': bool(e.get('is_mistake', False)),
            'created_at': _parse_ts(e['created_at']),
        })
    if dropped:
        logger.warning('%d error rows dropped: submission had no resolvable passage L2', dropped)
    return records


def fetch_existing_status(db, user_ids: list[str]) -> dict[tuple, str]:
    """Current ``remediation_status`` per cluster key, so an in-flight/resolved
    status is preserved across the re-count."""
    if not user_ids:
        return {}
    rows = _fetch_in_chunks(
        db, 'dt_error_profile_entry', 'user_id', user_ids,
        'user_id, l1_language_id, l2_language_id, subtype, remediation_status',
    )
    return {
        (r['user_id'], r['l1_language_id'], r['l2_language_id'], r['subtype']):
            r['remediation_status']
        for r in rows
    }


def upsert_profile_rows(db, rows: list[dict]) -> None:
    """Upsert profile rows on the composite UNIQUE key, chunked."""
    for i in range(0, len(rows), _CHUNK):
        chunk = rows[i:i + _CHUNK]
        db.table('dt_error_profile_entry').upsert(
            chunk, on_conflict='user_id,l1_language_id,l2_language_id,subtype',
        ).execute()


def run(db, *, window_days: int, threshold: int, user_id: str | None, dry_run: bool) -> list[dict]:
    """One synthesis pass. Returns the upsert rows (also written unless dry-run)."""
    now = datetime.now(timezone.utc)
    records = fetch_error_records(db, since=now - timedelta(days=2 * window_days), user_id=user_id)
    logger.info(
        'Loaded %d error records over the last %d days (2×W).', len(records), 2 * window_days,
    )

    user_ids = sorted({r['user_id'] for r in records})
    existing = fetch_existing_status(db, user_ids)

    rows = synthesis.synthesize(
        records, existing, now=now, window_days=window_days, threshold=threshold,
    )
    promoted = sum(1 for r in rows if r['remediation_status'] == synthesis.STATUS_QUEUED)
    logger.info(
        '%d profile rows across %d learners (%d queued / promoted).',
        len(rows), len(user_ids), promoted,
    )

    if dry_run:
        for r in rows[:20]:
            logger.info(
                '  [dry-run] user=%s pair=%s→%s subtype=%s count=%d rank=%.1f status=%s',
                r['user_id'][:8], r['l1_language_id'], r['l2_language_id'],
                r['subtype'], r['count'], r['severity_rank'], r['remediation_status'],
            )
        logger.info('[dry-run] nothing written.')
        return rows

    if rows:
        upsert_profile_rows(db, rows)
        logger.info('Upserted %d dt_error_profile_entry rows.', len(rows))
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--window-days', type=int, default=DEFAULT_WINDOW_DAYS,
                        help=f'W: rolling window in days (default {DEFAULT_WINDOW_DAYS}).')
    parser.add_argument('--threshold', type=int, default=DEFAULT_THRESHOLD,
                        help=f'N: recurrences within W to promote (default {DEFAULT_THRESHOLD}).')
    parser.add_argument('--user', dest='user_id', default=None,
                        help='Restrict to a single user_id (uuid).')
    parser.add_argument('--dry-run', action='store_true',
                        help='Compute + report, but write nothing.')
    args = parser.parse_args()

    db = get_supabase_admin()
    run(
        db,
        window_days=args.window_days,
        threshold=args.threshold,
        user_id=args.user_id,
        dry_run=args.dry_run,
    )
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
