"""Daily-practice queue rules (tech 7.1-7.3). Pure: fixed intervals, not FSRS.

Dates are learner-local ``date`` objects (``services.day_boundary.plan_today_iso``);
instants are timezone-aware UTC ``datetime`` objects.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Optional

from services.dual_translation.repair import planner, settings

FIXED_OUTCOMES = ("self_repaired", "repaired_alternative", "unsure_revised")
ANSWER_OUTCOMES = ("answer_shown", "shown_directly")


def queued_on_close(step_kind: str, outcome: Optional[str], max_hint_level: Optional[int]) -> bool:
    """Tech 7.1: does a repair-pass item go to daily practice?"""
    if step_kind == "unsure" or outcome is None:
        return False
    if outcome in ("answer_shown", "shown_directly", "skipped"):
        return True
    if outcome in ("self_repaired", "repaired_alternative"):
        return int(max_hint_level or 0) >= 2
    return False


def first_queue_state(local_today: date, closed_at: datetime) -> dict:
    """Queue fields for an item queued at ``closed_at`` (tech 7.1)."""
    return {
        "queue_status": "due",
        "queued_at": closed_at.isoformat(),
        "due_on": (local_today + timedelta(days=1)).isoformat(),
        "not_before": (closed_at + timedelta(hours=settings.DT_REPAIR_FIRST_DUE_MIN_HOURS)).isoformat(),
        "expires_at": (closed_at + timedelta(days=settings.DT_REPAIR_EXPIRY_DAYS)).isoformat(),
    }


def sitting_result(outcome: str) -> str:
    """Daily sitting outcome -> fixed | answer | disputed | skipped."""
    if outcome in FIXED_OUTCOMES:
        return "fixed"
    if outcome in ANSWER_OUTCOMES:
        return "answer"
    if outcome in ("disputed", "unsure_dismissed"):
        return "disputed"
    return "skipped"


def after_sitting(*, outcome: str, sitting_max_hint: int, sitting: int, failed_sittings: int,
                  hinted_sittings: int, local_today: date) -> dict:
    """Next queue state after a daily sitting closes (tech 7.3 table)."""
    kind = sitting_result(outcome)
    out: dict = {"failed_sittings": failed_sittings, "hinted_sittings": hinted_sittings}
    if kind == "fixed":
        if int(sitting_max_hint or 0) <= 1:
            out["queue_status"] = "resolved"
            return out
        out.update(queue_status="due", hinted_sittings=hinted_sittings + 1,
                   due_on=(local_today + timedelta(days=settings.DT_REPAIR_HINTED_RETURN_DAYS)).isoformat())
    elif kind == "answer":
        failed = failed_sittings + 1
        out["failed_sittings"] = failed
        if failed >= settings.DT_REPAIR_RETIRE_AFTER_FAILED:
            out["queue_status"] = "retired"
            return out
        intervals = settings.DT_REPAIR_FAILED_RETURN_DAYS
        days = intervals[min(failed, len(intervals)) - 1]
        out.update(queue_status="due", due_on=(local_today + timedelta(days=days)).isoformat())
    elif kind == "disputed":
        out["queue_status"] = "disputed"
        return out
    else:
        out.update(queue_status="due", due_on=(local_today + timedelta(days=1)).isoformat())
    if sitting >= settings.DT_REPAIR_MAX_SITTINGS:
        out["queue_status"] = "retired"
        out.pop("due_on", None)
    return out


def is_due(item: dict, local_today: date, now: datetime) -> bool:
    """Tech 7.2 due predicate for one item row."""
    if item.get("queue_status") != "due":
        return False
    try:
        due_on = date.fromisoformat(str(item.get("due_on"))[:10])
        not_before = _ts(item.get("not_before"))
        expires = _ts(item.get("expires_at"))
    except (TypeError, ValueError):
        return False
    return (due_on <= local_today and (not_before is None or not_before <= now)
            and (expires is None or expires > now))


def due_order_key(item: dict):
    """Meaning-changing subtype first, then max_hint_level desc, then queued_at asc."""
    return (0 if item.get("subtype") in planner.MEANING_TYPES else 1,
            -int(item.get("max_hint_level") or 0), str(item.get("queued_at") or ""))


def _ts(value) -> Optional[datetime]:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value
    text = str(value).replace("Z", "+00:00")
    return datetime.fromisoformat(text)
