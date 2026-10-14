"""Study-time ledger client (weekly-minutes, ADR-035).

Thin, best-effort wrapper over the ``credit_study_time`` and
``get_weekly_study_seconds`` RPCs. The SQL side clamps and dedupes again
(defense in depth); this module never trusts client-reported time beyond the
per-kind caps below and never raises into a learner's request.

Spec: wiki/features/weekly-minutes.tech.md.
"""

from __future__ import annotations

import logging
import math
import uuid
from typing import Any, Dict, Optional

from services.attempt_timing import MAX_CREDITED_ATTEMPT_SECONDS
from services.practice_session_service import PRACTICE_ATTEMPT_MAX_SECONDS

logger = logging.getLogger(__name__)

#: Mirror of the SQL per-kind clamp in ``credit_study_time``.
KIND_CAPS_SECONDS: Dict[str, int] = {
    'test': MAX_CREDITED_ATTEMPT_SECONDS,
    'drill': MAX_CREDITED_ATTEMPT_SECONDS,
    'practice': PRACTICE_ATTEMPT_MAX_SECONDS,
    'flashcard': 120,
    'dual_translation': 900,
}

KINDS = ('test', 'practice', 'flashcard', 'dual_translation', 'drill')


def _cap(kind: str) -> int:
    return KIND_CAPS_SECONDS.get(kind, 0)


def clamp_active_ms(kind: str, value: Any) -> int:
    """Client-reported ``active_ms`` -> whole seconds clamped to the kind cap.

    Junk, bool, NaN, infinity, negative -> 0. Unknown kind -> 0.
    """
    if isinstance(value, bool) or value is None:
        return 0
    try:
        n = float(value)
    except (TypeError, ValueError, OverflowError):
        return 0
    if math.isnan(n) or n <= 0:
        return 0
    seconds = n / 1000.0
    return int(min(seconds, _cap(kind)))


def clamp_seconds(kind: str, seconds: Any) -> int:
    """Server-computed seconds -> int in ``[0, cap(kind)]``."""
    if isinstance(seconds, bool) or seconds is None:
        return 0
    try:
        n = float(seconds)
    except (TypeError, ValueError, OverflowError):
        return 0
    if math.isnan(n) or n <= 0:
        return 0
    return int(min(n, _cap(kind)))


def parse_client_event_id(value: Any) -> Optional[str]:
    """Canonical uuid string for a client-minted event id, else None.

    Invalid ids are ignored (no credit), never a 400.
    """
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return str(uuid.UUID(value.strip()))
    except (ValueError, AttributeError):
        return None


def credit_study_time(
    db,
    user_id: Any,
    language_id: Any,
    kind: str,
    seconds: Any,
    source_table: str,
    source_id: Any,
) -> bool:
    """Credit ``seconds`` once per ``(kind, source_table, source_id)``.

    Returns True when newly credited, False for duplicates, zero seconds, bad
    input or any failure. Never raises.
    """
    try:
        secs = clamp_seconds(kind, seconds)
        if secs <= 0 or not user_id or language_id is None:
            return False
        if source_id is None or not str(source_id).strip() or not source_table:
            return False
        resp = db.rpc('credit_study_time', {
            'p_user_id': str(user_id),
            'p_language_id': int(language_id),
            'p_kind': kind,
            'p_seconds': secs,
            'p_source_table': source_table,
            'p_source_id': str(source_id),
        }).execute()
        return getattr(resp, 'data', None) is True
    except Exception as exc:
        logger.warning(
            'credit_study_time failed (non-fatal) kind=%s source=%s/%s: %s',
            kind, source_table, source_id, exc,
        )
        return False


# Minutes are rounded half-up (matches JS Math.round on the client).


def _int_seconds(value: Any) -> int:
    if isinstance(value, bool):
        return 0
    try:
        n = int(value)
    except (TypeError, ValueError):
        return 0
    return max(n, 0)


def weekly_study_summary(
    db,
    user_id: Any,
    language_id: Any,
    week_start: Any,
    target_minutes: Optional[int],
) -> Optional[Dict[str, Any]]:
    """Build the ``weekly_study`` response object, or None on any failure."""
    try:
        week_iso = week_start.isoformat() if hasattr(week_start, 'isoformat') else str(week_start)
        resp = db.rpc('get_weekly_study_seconds', {
            'p_user_id': str(user_id),
            'p_language_id': int(language_id),
            'p_week_start': week_iso,
        }).execute()
        raw = getattr(resp, 'data', None)
        if not isinstance(raw, dict):
            return None
        by_kind: Dict[str, Dict[str, int]] = {}
        total = 0
        for kind in KINDS:
            secs = _int_seconds(raw.get(kind))
            total += secs
            by_kind[kind] = {'seconds': secs, 'minutes': (secs + 30) // 60}
        return {
            'week_start_date': week_iso,
            'studied_seconds': total,
            'studied_minutes': (total + 30) // 60,
            'target_minutes': target_minutes,
            'by_kind': by_kind,
        }
    except Exception as exc:
        logger.warning('weekly_study_summary failed (non-fatal): %s', exc)
        return None
