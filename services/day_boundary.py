"""Local-day boundary resolution (TASK-716 / [[decisions/ADR-022-local-day-boundary]]).

THE SINGLE PLACE the application derives "today" for study-plan purposes.

Before this module, `routes/study_session.py::_today_iso()` and
`services/test_service.py` each computed `datetime.now(timezone.utc).date()`
independently, so the daily load rolled over at UTC midnight — 07:00-09:00
local for the primary ZH/JA audience — while `user_study_plans.timezone` was
collected and never read. Two independent derivations is also how one request
ends up with two different "today"s; ADR-022 requires exactly one helper.

Contract
--------
* ``resolve_zone`` NEVER raises. An unknown, malformed, empty or non-string
  timezone falls back to UTC. This is deliberate: V1 plan validation accepted
  any non-empty string, so garbage is already stored, and a resolver that
  throws would take the whole session down — cf.
  [[decisions/ADR-020-late-symbolic-resolution-must-fail-safe]].
* ``plan_today_iso`` is the call-site helper: it reads the plan timezone for
  (user, language) and returns that learner's local ISO date. A missing plan,
  a DB error, or an unusable timezone all degrade to the UTC date rather than
  failing the request.

The SQL side mirrors this in ``public.resolve_plan_timezone(text)`` and
``public.plan_local_date(uuid, smallint, timestamptz)`` — see
migrations/task716_local_day_boundary.sql. Both sides must agree; the Python
helper is authoritative for route/service code, the SQL helper for RPC bodies
(``record_session_progress``) that have no Python caller.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from typing import Any, Optional

try:  # Python 3.9+
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover - the app targets 3.11
    ZoneInfo = None  # type: ignore[assignment]


logger = logging.getLogger(__name__)

#: Fallback used whenever a plan has no timezone or an unusable one.
DEFAULT_TIMEZONE = "UTC"

_UTC = timezone.utc


def is_valid_timezone(tz_name: Any) -> bool:
    """True when ``tz_name`` names a zone the runtime can actually load.

    Used by ``PUT /api/study-plan`` to reject garbage at the edge. The resolver
    below still fails safe, so this is a usability guard, not a safety one.
    """
    if not isinstance(tz_name, str) or not tz_name.strip():
        return False
    if ZoneInfo is None:  # pragma: no cover
        return tz_name.strip().upper() == "UTC"
    try:
        ZoneInfo(tz_name.strip())
        return True
    except Exception:
        return False


def resolve_zone(tz_name: Any):
    """Return a tzinfo for ``tz_name``, falling back to UTC. Never raises."""
    if not isinstance(tz_name, str) or not tz_name.strip():
        return _UTC
    name = tz_name.strip()
    if ZoneInfo is None:  # pragma: no cover
        return _UTC
    try:
        return ZoneInfo(name)
    except Exception:
        # Invalid IANA name (a typo, a UI-locale string like "es", a raw
        # offset). Log rather than raise — a bad stored string must never take
        # down the daily session.
        logger.warning(
            "Unresolvable plan timezone %r; falling back to %s", name, DEFAULT_TIMEZONE
        )
        return _UTC


def local_date(tz_name: Any, now: Optional[datetime] = None) -> date:
    """The calendar date it is *right now* in ``tz_name`` (UTC on failure)."""
    moment = now or datetime.now(_UTC)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=_UTC)
    return moment.astimezone(resolve_zone(tz_name)).date()


def local_today_iso(tz_name: Any, now: Optional[datetime] = None) -> str:
    """ISO ``YYYY-MM-DD`` for the current local date in ``tz_name``."""
    return local_date(tz_name, now).isoformat()


def plan_timezone(db, user_id: str, language_id: int) -> str:
    """The learner's configured timezone for (user, language), or ``UTC``.

    Any failure — no plan row, NULL timezone, network error — yields the UTC
    default. Callers never have to handle an exception from this.
    """
    try:
        resp = (
            db.table("user_study_plans")
            .select("timezone")
            .eq("user_id", user_id)
            .eq("language_id", language_id)
            .limit(1)
            .execute()
        )
    except Exception as exc:
        logger.warning(
            "plan_timezone lookup failed for user=%s lang=%s: %s; using %s",
            user_id, language_id, exc, DEFAULT_TIMEZONE,
        )
        return DEFAULT_TIMEZONE

    if not getattr(resp, "data", None):
        return DEFAULT_TIMEZONE
    return resp.data[0].get("timezone") or DEFAULT_TIMEZONE


def plan_today_iso(
    db, user_id: str, language_id: int, now: Optional[datetime] = None
) -> str:
    """Today's ISO date for this learner's plan timezone (ADR-022).

    This is the value that keys ``daily_test_loads (user_id, language_id,
    load_date)``. The uniqueness *shape* is unchanged; its derivation is now
    per-user, which is the risk ADR-022 accepts.
    """
    return local_today_iso(plan_timezone(db, user_id, language_id), now)


def plan_today(
    db, user_id: str, language_id: int, now: Optional[datetime] = None
) -> date:
    """``plan_today_iso`` as a ``date`` (for week-start arithmetic)."""
    return local_date(plan_timezone(db, user_id, language_id), now)


def utc_today_iso(now: Optional[datetime] = None) -> str:
    """The pre-ADR-022 behaviour, kept explicit for callers that genuinely
    want a global date (cron sweeps) rather than a learner-local one."""
    return (now or datetime.now(_UTC)).astimezone(_UTC).date().isoformat()
