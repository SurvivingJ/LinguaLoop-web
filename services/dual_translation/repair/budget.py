"""Per-user daily cost caps for re-checks (tech 9.3).

``grade_tokens_today`` is the logic of ``routes/dual_translation._tokens_used_today``
(moved here; the route keeps a thin wrapper that adds ``recheck_tokens_today``).
Same window for both: the UTC day.
"""

from __future__ import annotations

import logging
from datetime import datetime, time as dtime, timezone

from config import Config
from services.dual_translation.repair import settings

logger = logging.getLogger(__name__)


def _start_of_utc_day() -> str:
    return datetime.combine(datetime.now(timezone.utc).date(), dtime.min, tzinfo=timezone.utc).isoformat()


def grade_tokens_today(db, user_id: str) -> int:
    """Sum of dt_grade.grader_trace token counts (in+out) across this user's
    submissions created since UTC midnight (TASK-601 window)."""
    submissions_resp = (
        db.table('dt_submission')
        .select('id')
        .eq('user_id', user_id)
        .gte('created_at', _start_of_utc_day())
        .execute()
    )
    submission_ids = [row['id'] for row in (submissions_resp.data or [])]
    if not submission_ids:
        return 0
    grades_resp = (
        db.table('dt_grade')
        .select('grader_trace')
        .in_('submission_id', submission_ids)
        .execute()
    )
    total = 0
    for row in (grades_resp.data or []):
        tokens = (row.get('grader_trace') or {}).get('tokens') or {}
        total += int(tokens.get('in', 0) or 0) + int(tokens.get('out', 0) or 0)
    return total


def _recheck_rows_today(db, user_id: str) -> list:
    return (
        db.table('dt_repair_event')
        .select('tokens_in, tokens_out, model_slug')
        .eq('user_id', user_id)
        .eq('kind', 'revision_checked')
        .gte('created_at', _start_of_utc_day())
        .execute()
    ).data or []


def recheck_tokens_today(db, user_id: str) -> int:
    """Tokens of today's re-check calls. 0 on any failure (e.g. the repair
    migration not applied yet) - this is called on every submit."""
    from services.dual_translation.repair import store
    if not store.tables_available():
        return 0  # the migration is not applied: no query on every submit
    try:
        return sum(int(r.get('tokens_in') or 0) + int(r.get('tokens_out') or 0)
                   for r in _recheck_rows_today(db, user_id))
    except Exception as exc:  # noqa: BLE001 - never break grading over the add-on
        if store.is_missing_table_error(exc):
            store.note_missing_tables(exc)
        else:
            logger.debug("dt_repair.budget: recheck tokens unavailable: %s", exc)
        return 0


def checks_today(db, user_id: str) -> int:
    """Grader calls made by re-checks today (rows with a model; tier-0 and
    unchanged checks make no call)."""
    return sum(1 for r in _recheck_rows_today(db, user_id) if r.get('model_slug'))


def recheck_allowed(db, user_id: str) -> bool:
    """Within the per-user daily count and token caps. Fails closed (False) when
    the usage cannot be read: the item then shows its answer, never a dead end."""
    try:
        rows = _recheck_rows_today(db, user_id)
        if sum(1 for r in rows if r.get('model_slug')) >= settings.DT_REPAIR_MAX_CHECKS_PER_DAY:
            return False
        recheck = sum(int(r.get('tokens_in') or 0) + int(r.get('tokens_out') or 0) for r in rows)
        return grade_tokens_today(db, user_id) + recheck < (
            Config.DT_DAILY_TOKEN_BUDGET + settings.DT_REPAIR_TOKEN_ALLOWANCE)
    except Exception as exc:  # noqa: BLE001
        logger.warning("dt_repair.budget: usage unreadable, refusing the re-check: %s", exc)
        return False
