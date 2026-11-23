"""Nightly knowledge snapshots (ADR-053; wiki/features/knowledge-report.tech.md §7, TASK-1037).

Once a day (APScheduler, 04:25 UTC, ``web/scheduler.py``) every active (user, language) pair gets
one ``user_knowledge_snapshots`` row holding the estimator's **inputs** (``cal_bands``,
``frame_bands``, answer dates) as well as its outputs, so later growth figures can recompute "then"
on today's frame (§2.10). Growth history starts at the first run (no back-fill, OQ7), which is why
this job ships before the page and is **not** gated by ``KNOWLEDGE_REPORT_ENABLED``.

Idempotent: one upsert per pair on the primary key (user_id, language_id, snapshot_date), so the
copy of the job in each gunicorn worker just rewrites the same rows (no advisory lock — performance
research §7.4). A failing pair is logged and skipped. Then ``knowledge_snapshots_prune(120)``.

Manual run: ``python -m services.knowledge_snapshots --once`` (rows get ``source='manual'``).
"""
from __future__ import annotations

import argparse
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping, Optional

from services.vocabulary import knowledge_estimate as ke

logger = logging.getLogger(__name__)

TABLE = 'user_knowledge_snapshots'
CONFLICT_COLUMNS = 'user_id,language_id,snapshot_date'
KEEP_DAILY_DAYS = 120
LABEL_CODES = {'low': 1, 'medium': 2, 'good': 3}
KIND_CODES = {'none': 0, 'range': 1, 'upper_only': 2}


def _missing_function(exc: Exception) -> bool:
    text = str(exc)
    return 'PGRST202' in text or 'Could not find the function' in text


def _rpc(db, name: str, params: Mapping[str, Any]) -> Any:
    return db.rpc(name, dict(params)).execute().data


def _object(data: Any) -> dict:
    """A jsonb object RPC result (PostgREST may wrap a scalar result in a one-row list)."""
    if isinstance(data, list) and len(data) == 1 and isinstance(data[0], dict):
        data = data[0]
    if not isinstance(data, dict):
        raise ValueError(f'expected a json object, got {type(data).__name__}')
    return data


def _num(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _bands(raw: Any) -> Optional[list[list[int]]]:
    if not isinstance(raw, (list, tuple)) or len(raw) != ke.N_BANDS:
        return None
    return [[_num(r[0]), _num(r[1]), _num(r[2])] for r in raw]


def snapshot_row(user_id: str, language_id: int, summary: Mapping, frames: Mapping,
                 *, as_of: datetime, source: str) -> dict:
    """One ``user_knowledge_snapshots`` row (tech §5.1) from a ``knowledge_report_summary`` result
    and the ``knowledge_frame_bands`` map."""
    tracked = summary.get('tracked') or {}
    states = summary.get('states') or {}
    d30 = (summary.get('activity') or {}).get('d30') or {}
    cal = summary.get('calibration') or {}
    d_raw = cal.get('definition_language_id')
    d_star = _num(d_raw) if d_raw is not None else None
    bands = _bands(cal.get('bands')) if d_star is not None else None
    frame = frames.get(f'{language_id}:{d_star}') if d_star is not None else None
    frame = [_num(x) for x in frame] if isinstance(frame, (list, tuple)) and len(frame) == ke.N_BANDS else None

    est = None
    if bands is not None and frame is not None and all(N > 0 or row[0] == 0 for N, row in zip(frame, bands)):
        alltime = cal.get('alltime_n')
        alltime = [_num(x) for x in alltime] if isinstance(alltime, (list, tuple)) and len(alltime) == ke.N_BANDS else None
        est = ke.estimate_range(bands, frame, alltime)
    shown = bool(est and est.get('shown'))

    checked = summary.get('checked_meanings')
    if checked is None:
        # Meanings with any direct check: the three checked evidence states (§2.4). For
        # de6fd05b/ja 10 + 69 + 30 = 109, the K3 count of rows with word-test answers.
        checked = (_num(states.get('missed_last')) + _num(states.get('rated_known'))
                   + _num(states.get('checked')))

    return {
        'user_id': str(user_id),
        'language_id': int(language_id),
        'snapshot_date': as_of.astimezone(timezone.utc).date().isoformat(),
        'method_version': ke.METHOD_VERSION,
        'tracked_words': _num(tracked.get('words')),
        'tracked_meanings': _num(tracked.get('meanings')),
        'rated_known_words': _num(summary.get('rated_known_words')),
        'checked_meanings': _num(checked),
        'missed_recent_meanings': _num((summary.get('missed_recent') or {}).get('meanings')),
        'idle60_meanings': _num(summary.get('idle60_meanings')),
        'practised_30_meanings': _num(d30.get('practised_meanings')),
        'direct_checks_30': _num(d30.get('direct_outcomes')),
        'cal_definition_language_id': d_star,
        'cal_bands': ke.bands_to_snapshot(bands) if bands is not None else None,
        'frame_bands': frame,
        'cal_answers': _num(cal.get('answers')),
        'cal_first_answer_at': cal.get('first_answer_at', cal.get('first_at')),
        'cal_last_answer_at': cal.get('last_answer_at', cal.get('last_at')),
        'est_kind': KIND_CODES.get(est['kind'], 0) if shown else 0,
        'est_lo': int(est['lo_disp']) if shown else None,
        'est_hi': int(est['hi_disp']) if shown else None,
        'est_label': LABEL_CODES.get(est.get('label')) if shown else None,
        'source': source,
        'computed_at': datetime.now(timezone.utc).isoformat(),
    }


def run_nightly(db=None, *, source: str = 'nightly', now: Optional[datetime] = None) -> dict:
    """Write today's snapshot for every active pair, then prune. Returns
    ``{pairs, written, failed, pruned}`` (or ``{skipped, reason}`` before the foundation migration
    is applied)."""
    if db is None:
        from services.supabase_factory import get_supabase_admin
        db = get_supabase_admin()
    as_of = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    since = as_of - timedelta(days=ke.WINDOW_DAYS)

    try:
        pairs = _rpc(db, 'knowledge_active_pairs', {'p_since': since.isoformat()})
    except Exception as exc:
        if _missing_function(exc):
            return {'skipped': True, 'reason': 'knowledge_active_pairs not deployed'}
        raise
    frames = _object(_rpc(db, 'knowledge_frame_bands', {}))
    pairs = [p for p in (pairs if isinstance(pairs, list) else []) if isinstance(p, dict)]

    written = failed = 0
    for pair in pairs:
        user_id, language_id = pair.get('user_id'), pair.get('language_id')
        try:
            summary = _object(_rpc(db, 'knowledge_report_summary', {
                'p_user_id': user_id, 'p_language_id': int(language_id),
                'p_as_of': as_of.isoformat(), 'p_cal_since': [],
            }))
            row = snapshot_row(user_id, int(language_id), summary, frames, as_of=as_of, source=source)
            db.table(TABLE).upsert(row, on_conflict=CONFLICT_COLUMNS).execute()
            written += 1
        except Exception as exc:
            failed += 1
            logger.warning('knowledge_snapshot_failed user=%s lang=%s (%s)',
                           str(user_id or '')[:8], language_id, exc)

    pruned = _num(_rpc(db, 'knowledge_snapshots_prune', {'p_keep_daily_days': KEEP_DAILY_DAYS}))
    return {'pairs': len(pairs), 'written': written, 'failed': failed, 'pruned': pruned}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description='Write knowledge snapshots now (source=manual).')
    parser.add_argument('--once', action='store_true', help='run one snapshot pass and exit')
    args = parser.parse_args(argv)
    if not args.once:
        parser.error('pass --once to write snapshots now (the nightly run is scheduled by the app)')
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    result = run_nightly(source='manual')
    print(json.dumps(result))
    return 0 if not result.get('failed') else 1


if __name__ == '__main__':
    raise SystemExit(main())
