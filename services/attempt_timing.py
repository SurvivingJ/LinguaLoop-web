"""Server-side validation of client-supplied attempt timestamps and counts.

TASK-882 (S15). The browser reports ``started_at`` / ``finished_at`` and
result counts; none of it may be taken at face value because credited
minutes and progress counters are derived from it.

Policy
------
* Unparseable timestamps, ``finished_at < started_at`` and a ``finished_at``
  more than ``FUTURE_SKEW_SECONDS`` ahead of the server clock are REJECTED
  (``AttemptTimingError`` -> HTTP 400) before anything is recorded.
* A window longer than ``MAX_CREDITED_ATTEMPT_SECONDS`` is CLAMPED, not
  rejected: a learner who left a tab open still gets their submission, but is
  credited at most the cap.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Tuple

#: Longest duration credited for one comprehension-test attempt (20 min).
#: Tests are ~5 questions on a short transcript (typical 3-8 min); 20 min is
#: well above a slow honest attempt and well below the 1 h DB CHECK
#: (test_attempts.duration_ms < 3_600_000).
MAX_CREDITED_ATTEMPT_SECONDS = 20 * 60

#: Tolerated client clock skew into the future.
FUTURE_SKEW_SECONDS = 120

#: Upper bound for a single reported ``time_taken_ms`` (5 min, matching
#: services.practice_session_service.PRACTICE_ATTEMPT_MAX_SECONDS).
MAX_TIME_TAKEN_MS = 300_000


class AttemptTimingError(ValueError):
    """Client-supplied timing/count data is invalid (maps to HTTP 400)."""


def _parse(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise AttemptTimingError(f"{field} must be an ISO-8601 timestamp")
    text = value.strip()
    if text.endswith('Z') or text.endswith('z'):
        text = text[:-1] + '+00:00'
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        raise AttemptTimingError(f"{field} must be an ISO-8601 timestamp")
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def validate_attempt_window(
    started_at: Any,
    finished_at: Any,
    now: Optional[datetime] = None,
) -> Tuple[Optional[str], Optional[str]]:
    """Return ``(started_iso, finished_iso)`` safe to hand to the timing RPC.

    Both absent -> ``(None, None)`` (older clients; RPC skips the duration
    update). Exactly one present, malformed, reversed or future -> raises
    ``AttemptTimingError``. Over-long windows are clamped to
    ``MAX_CREDITED_ATTEMPT_SECONDS`` by moving ``started_at`` forward.
    """
    if started_at in (None, '') and finished_at in (None, ''):
        return None, None
    if started_at in (None, '') or finished_at in (None, ''):
        raise AttemptTimingError("started_at and finished_at must be sent together")

    now = now or datetime.now(timezone.utc)
    start = _parse(started_at, 'started_at')
    finish = _parse(finished_at, 'finished_at')

    if finish < start:
        raise AttemptTimingError("finished_at must not be before started_at")
    if finish > now + timedelta(seconds=FUTURE_SKEW_SECONDS):
        raise AttemptTimingError("finished_at must not be in the future")
    if finish > now:
        finish = now
    if start > finish:
        start = finish
    if (finish - start).total_seconds() > MAX_CREDITED_ATTEMPT_SECONDS:
        start = finish - timedelta(seconds=MAX_CREDITED_ATTEMPT_SECONDS)
    return start.isoformat(), finish.isoformat()


def validate_counts(correct: Any, total: Any, correct_name: str, total_name: str) -> Tuple[int, int]:
    """Validate ``0 <= correct <= total`` with ``total >= 1`` (integers only)."""
    for name, v in ((correct_name, correct), (total_name, total)):
        if isinstance(v, bool) or not isinstance(v, int):
            raise AttemptTimingError(f"{name} must be an integer")
    if total < 1:
        raise AttemptTimingError(f"{total_name} must be positive")
    if correct < 0 or correct > total:
        raise AttemptTimingError(f"{correct_name} must be between 0 and {total_name}")
    return correct, total


def clamp_time_taken(value: Any, max_seconds: int = MAX_CREDITED_ATTEMPT_SECONDS) -> int:
    """Seconds (``time_taken``) clamped to ``[0, max_seconds]``; junk -> 0."""
    try:
        n = float(value)
    except (TypeError, ValueError):
        return 0
    if n != n or n < 0:
        return 0
    return int(min(n, max_seconds))


def clamp_time_taken_ms(value: Any) -> Optional[int]:
    """Milliseconds clamped to ``[0, MAX_TIME_TAKEN_MS]``; None/junk -> None."""
    if value is None:
        return None
    try:
        n = float(value)
    except (TypeError, ValueError):
        return None
    if n != n or n < 0:
        return None
    return int(min(n, MAX_TIME_TAKEN_MS))
