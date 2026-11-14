"""Study plan settings: the reads and writes behind /api/study-plan.

``plan_overview`` builds the GET payload (the plan row, this week's state and
the "Daily session" card inputs); ``apply_template`` and ``update_plan`` are
the two PUT shapes; ``recompute_current_week`` is the manual Tier B recompute.

Callers pass ``local_today``, a zero-argument callable returning the learner's
local date (services.day_boundary.plan_today), so the week is always derived
from the learner's day and never from the server's.

See [[features/study-plans.tech]], [[features/session-modules.tech]] and
[[features/session-budget-settings.tech]].
"""

from __future__ import annotations

import importlib
import logging
from datetime import date, timedelta
from typing import Any, Callable, Dict, List, Optional, Sequence

from config import Config
from services.concurrency import run_parallel
from services.day_boundary import plan_row
from services.study_time import weekly_study_summary

logger = logging.getLogger(__name__)

MODULE_PRACTICE = 'practice'

# Fallbacks used only when the optional GET enrichments cannot be computed.
_NEW_WORD_MINUTES_FALLBACK = 3.0
_REVIEWS_PER_NEW_WORD_FALLBACK = 7
_REVIEW_ITEM_SECONDS_FALLBACK = 20.0

# Columns GET /api/study-plan returns as `plan` (the row also holds others).
_PLAN_FIELDS = (
    'user_id', 'language_id', 'template_id', 'daily_minutes',
    'weekday_shape', 'skill_weight_overrides', 'goal_id', 'timezone',
    'excluded_modules', 'budget_scope', 'new_words_per_day',
    'created_at', 'updated_at',
)

_WEEK_FIELDS = (
    'week_start_date, target_counts, skill_values, completed_counts, '
    'practice_target_minutes, practice_completed_maint_min, '
    'practice_completed_acq_min, maintenance_share, '
    'acquisition_share, total_weekly_minutes, computed_at, '
    'budget_scope, review_target_minutes, new_words_target, '
    'new_words_completed, acq_target_minutes, tail_completed_min, '
    'tail_new_words_completed'
)

LocalToday = Callable[[], date]


class PlanUpdateRejected(Exception):
    """The update cannot be applied; carries the API message and status."""

    def __init__(self, message: str, status: int = 400, error_code: Optional[str] = None):
        super().__init__(message)
        self.status = status
        self.error_code = error_code


class TemplateApplyFailed(Exception):
    """The apply_study_plan_template RPC failed."""


class RecomputeFailed(Exception):
    """compute_weekly_plan returned no result; ``stage`` says which step failed."""

    def __init__(self, stage: str):
        super().__init__(stage)
        self.stage = stage


def monday_of(d: date) -> date:
    return d - timedelta(days=d.weekday())


def _sps():
    """The study-plan service module, imported lazily.

    Resolved through importlib on every call so route tests can swap the
    module in ``sys.modules`` and so importing the blueprint never pulls in
    the heavy service at app start.
    """
    return importlib.import_module('services.study_plan_service')


def _safe(label: str, fn, default=None):
    """Run an optional GET enrichment; log and fall back instead of failing the page."""
    try:
        return fn()
    except Exception as e:
        logger.warning("study-plan GET %s failed: %s", label, e)
        return default


# ---------------------------------------------------------------------------
# Modules
# ---------------------------------------------------------------------------

def _normalize_excluded(codes: Sequence[str], all_modules: Sequence[str]) -> List[str]:
    """De-duplicate and order by ALL_MODULES (unknown codes sort last, A-Z)."""
    order = {m: i for i, m in enumerate(all_modules)}
    return sorted(set(codes), key=lambda c: (order.get(c, len(order)), c))


def available_modules(db, language_id: int, all_modules: Optional[Sequence[str]] = None) -> List[str]:
    """Ordered module codes offered for a language.

    Union of the keys of every template for the language (stable across
    template switches) intersected with ALL_MODULES, then ``practice``
    (Vocabulary review). Order follows ALL_MODULES.
    """
    if all_modules is None:
        all_modules = tuple(_sps().ALL_MODULES)
    keys: set = set()
    try:
        resp = (
            db.table('dim_study_plan_templates')
            .select('weekly_test_counts')
            .eq('language_id', language_id)
            .execute()
        )
        for row in (resp.data or []):
            counts = row.get('weekly_test_counts') or {}
            if isinstance(counts, dict):
                keys.update(counts.keys())
    except Exception as e:
        logger.warning("available_modules template read failed lang=%s: %s", language_id, e)
    keys.add(MODULE_PRACTICE)
    return [m for m in all_modules if m in keys]


def _excluded_modules_error(
    normalized: Sequence[str], available: Sequence[str], new_words_per_day: int,
) -> Optional[str]:
    """Every excluded code must be offered for this language, and at least one
    module must stay included, where ``new_words_per_day > 0`` counts as an
    included module (new words are not a module of their own)."""
    for code in normalized:
        if code not in available:
            return f"unknown module for this language: {code}"
    if not (set(available) - set(normalized)) and not new_words_per_day > 0:
        return "at least one module must remain included"
    return None


def _cross_field_error(
    available: Sequence[str], excluded: Sequence[str], scope: str, new_words_per_day: int,
) -> Optional[str]:
    """Rules over the merged (request-else-stored) module / scope / new-words state."""
    included = set(available) - set(excluded)
    if not included and not new_words_per_day > 0:
        return "at least one module must remain included"
    if scope == 'tests_only' and not (included - {MODULE_PRACTICE}):
        return "tests_only scope needs at least one test or surface module included"
    return None


# ---------------------------------------------------------------------------
# GET /api/study-plan
# ---------------------------------------------------------------------------

def _current_week(db, user_id: str, language_id: int, week_start: date) -> Optional[Dict[str, Any]]:
    resp = (
        db.table('weekly_plan_states')
        .select(_WEEK_FIELDS)
        .eq('user_id', user_id)
        .eq('language_id', language_id)
        .eq('week_start_date', week_start.isoformat())
        .limit(1)
        .execute()
    )
    return resp.data[0] if resp.data else None


def _today_shortfall(db, user_id: str, language_id: int, local_today: date) -> Optional[int]:
    resp = (
        db.table('daily_test_loads')
        .select('daily_session_targets')
        .eq('user_id', user_id)
        .eq('language_id', language_id)
        .eq('load_date', local_today.isoformat())
        .limit(1)
        .execute()
    )
    if not resp.data:
        return None
    targets = resp.data[0].get('daily_session_targets') or {}
    value = targets.get('new_words_shortfall')
    return int(value) if value is not None else None


def _forecast(sps, plan: Dict[str, Any], gov_raw: Dict[str, Any]) -> Dict[str, Any]:
    npd = int(plan.get('new_words_per_day') or 0)
    shape = plan.get('weekday_shape') or None
    item_seconds = float(
        gov_raw.get('item_seconds')
        or getattr(Config, 'REVIEW_ITEM_SECONDS_DEFAULT', _REVIEW_ITEM_SECONDS_FALLBACK)
    )
    reviews_per_word = (
        (sps.reviews_per_new_word_30d() if hasattr(sps, 'reviews_per_new_word_30d') else None)
        or getattr(Config, 'REVIEWS_PER_NEW_WORD_30D', None)
        or getattr(sps, 'REVIEWS_PER_NEW_WORD_30D', None)
        or _REVIEWS_PER_NEW_WORD_FALLBACK
    )

    def _forecast_min() -> float:
        avg = sps.new_words_week_target(npd, shape) / 7.0
        return round(float(sps.review_forecast_min_per_day(avg, item_seconds)), 2)

    return {
        'reviews_per_new_word_30d': reviews_per_word,
        'item_seconds': item_seconds,
        'min_per_day': _safe('forecast', _forecast_min, 0.0),
    }


def plan_overview(
    db, user_id: str, language_id: int, local_today: LocalToday,
) -> Optional[Dict[str, Any]]:
    """The GET /api/study-plan payload, or None when there is no plan row.

    Besides the plan and this week's state it carries the settings page's
    "Daily session" card inputs (session-budget-settings) and the weekly
    minutes ledger total (ADR-035). Each of those is best-effort: a failure
    degrades that piece (None / neutral defaults) and never fails the GET.
    The independent reads run concurrently.
    """
    # Test prestudy trigger; read separately so a database without the
    # column (migration pending) still serves the plan.
    from services.prestudy import get_prestudy_mode
    prestudy_mode = get_prestudy_mode(db, user_id, language_id)

    # One cached read serves this, get_prestudy_mode and local_today below.
    row = plan_row(db, user_id, language_id)
    if not row:
        return None
    plan = {k: row.get(k) for k in _PLAN_FIELDS}
    plan['prestudy_mode'] = prestudy_mode

    # Learner-local week (matches the ledger/record_session_progress writers).
    today = local_today()
    week_start = monday_of(today)
    sps = _sps()
    all_modules = tuple(sps.ALL_MODULES)

    current_week, available, mpnw, gov_raw, shortfall, weekly_study = run_parallel(
        lambda: _current_week(db, user_id, language_id, week_start),
        lambda: _safe('available_modules',
                      lambda: available_modules(db, language_id, all_modules), [MODULE_PRACTICE]),
        lambda: _safe(
            'minutes_per_new_word',
            lambda: float(sps.get_minutes_per_new_word(db, language_id)),
            float(getattr(Config, 'NEW_WORD_MINUTES_DEFAULT', _NEW_WORD_MINUTES_FALLBACK)),
        ),
        lambda: _safe('governor',
                      lambda: sps.get_review_governor(db, user_id, language_id, today), None) or {},
        lambda: _safe('shortfall', lambda: _today_shortfall(db, user_id, language_id, today), None),
        lambda: _safe('weekly_study',
                      lambda: weekly_study_summary(db, user_id, language_id, week_start, None), None),
    )
    if weekly_study is not None:
        weekly_study['target_minutes'] = (current_week or {}).get('total_weekly_minutes')

    typical_day = None
    if current_week:
        typical_day = _safe(
            'typical_day', lambda: sps.typical_day_inputs(db, language_id, plan, current_week), None,
        )

    return {
        'plan': plan,
        'current_week': current_week,
        'weekly_study': weekly_study,
        'study_plan_enabled': bool(Config.STUDY_PLAN_ENABLED),
        'available_modules': available,
        'minutes_per_new_word': mpnw,
        'typical_day': typical_day,
        'governor': {
            'level': gov_raw.get('level') or 'normal',
            'overdue_items': gov_raw.get('overdue_items') or 0,
            'overdue_minutes': gov_raw.get('overdue_minutes') or 0,
            'threshold_minutes': gov_raw.get('threshold_minutes') or 0,
        },
        'forecast': _forecast(sps, plan, gov_raw),
        'today_new_words_shortfall': shortfall,
    }


def list_templates(db, language_id: int) -> List[Dict[str, Any]]:
    """The study-plan templates available for a language, shortest day first."""
    resp = (
        db.table('dim_study_plan_templates')
        .select(
            'template_id, language_id, daily_minutes, weekly_test_counts, '
            'practice_total_minutes, base_maintenance_share, '
            'practice_minutes_flex_pct, is_default'
        )
        .eq('language_id', language_id)
        .order('daily_minutes')
        .execute()
    )
    return resp.data or []


# ---------------------------------------------------------------------------
# PUT /api/study-plan — template apply
# ---------------------------------------------------------------------------

def _plan_row_exists(db, user_id: str, language_id: int) -> Optional[bool]:
    """True/False if a plan row exists; None when the read itself fails."""
    try:
        resp = (
            db.table('user_study_plans')
            .select('user_id')
            .eq('user_id', user_id)
            .eq('language_id', language_id)
            .limit(1)
            .execute()
        )
        return bool(resp.data)
    except Exception as e:
        logger.warning("plan existence check failed user=%s lang=%s: %s", user_id, language_id, e)
        return None


def _apply_new_words_default(db, user_id: str, language_id: int, rpc_data: Any) -> None:
    """Set new_words_per_day = max(10, daily_minutes // 6) on a freshly created plan row.

    Words PER DAY: at least 10 (new-word drill, ADR-040, decided 2026-11-09),
    more for plans over 60 min/day. apply_study_plan_template does not set the
    column. Existing rows are never touched. Best-effort.
    """
    try:
        resp = (
            db.table('user_study_plans')
            .select('daily_minutes')
            .eq('user_id', user_id)
            .eq('language_id', language_id)
            .limit(1)
            .execute()
        )
        if not resp.data:
            return
        default = max(10, int(resp.data[0]['daily_minutes']) // 6)
        (
            db.table('user_study_plans')
            .update({'new_words_per_day': default})
            .eq('user_id', user_id)
            .eq('language_id', language_id)
            .execute()
        )
        if isinstance(rpc_data, dict):
            rpc_data['new_words_per_day'] = default
    except Exception as e:
        logger.warning(
            "new_words_per_day default failed for user=%s lang=%s: %s", user_id, language_id, e,
        )


def apply_template(
    db, user_id: str, language_id: int, template_id: int, local_today: LocalToday,
) -> Any:
    """Apply a template through the idempotent apply_study_plan_template RPC
    (creating the plan row when there is none) and return the RPC's plan.

    Raises TemplateApplyFailed when the RPC fails.
    """
    plan_existed = _plan_row_exists(db, user_id, language_id)
    try:
        rpc_resp = db.rpc('apply_study_plan_template', {
            'p_user_id':     user_id,
            'p_language_id': language_id,
            'p_template_id': template_id,
        }).execute()
    except Exception as e:
        logger.error("apply_study_plan_template failed: %s", e)
        raise TemplateApplyFailed(str(e)) from e
    if plan_existed is False:
        _apply_new_words_default(db, user_id, language_id, rpc_resp.data)
    # Seed this week's plan immediately so the very first daily load after
    # applying a template is plan-driven, instead of waiting for the Sunday
    # pacer (which seeds next week) or leaning on the lazy compute in
    # get_or_create_daily_load. Best-effort: a failure here still returns the
    # applied template — the lazy path recovers it.
    try:
        from services.study_plan_service import StudyPlanService
        StudyPlanService(db=db).compute_weekly_plan(
            user_id, language_id, monday_of(local_today()),
        )
    except Exception as e:
        logger.warning(
            "post-template weekly-plan compute failed for "
            "user=%s lang=%s: %s", user_id, language_id, e,
        )
    return rpc_resp.data


# ---------------------------------------------------------------------------
# PUT /api/study-plan — partial update
# ---------------------------------------------------------------------------

def _template_daily_minutes(db, template_id: int, language_id: int) -> Any:
    """daily_minutes of a template that must belong to ``language_id``."""
    resp = (
        db.table('dim_study_plan_templates')
        .select('template_id, language_id, daily_minutes')
        .eq('template_id', template_id)
        .limit(1)
        .execute()
    )
    if not resp.data:
        raise PlanUpdateRejected(f"unknown template_id={template_id}")
    if int(resp.data[0]['language_id']) != language_id:
        raise PlanUpdateRejected("template language does not match language_id")
    return resp.data[0]['daily_minutes']


def _column_updates(db, language_id: int, provided: Dict[str, Any]) -> Dict[str, Any]:
    """The UPDATE payload for every provided field except excluded_modules
    (which needs the stored row; see ``_apply_session_settings``)."""
    update: Dict[str, Any] = {}
    for name, value in provided.items():
        if name == 'excluded_modules':
            continue
        update[name] = value
        if name == 'template_id':
            # If daily_minutes was not also given, copy it from the template.
            update.setdefault('daily_minutes', _template_daily_minutes(db, value, language_id))
    return update


def _apply_session_settings(
    db, language_id: int, provided: Dict[str, Any], stored: Dict[str, Any],
    update: Dict[str, Any],
) -> bool:
    """Validate excluded_modules / budget_scope / new_words_per_day against the
    merged (request-else-stored) state, add excluded_modules to ``update`` and
    return whether the session settings changed."""
    if not any(k in provided for k in ('excluded_modules', 'budget_scope', 'new_words_per_day')):
        return False
    all_modules = tuple(_sps().ALL_MODULES)
    stored_excluded = _normalize_excluded(stored.get('excluded_modules') or [], all_modules)
    stored_scope = stored.get('budget_scope') or 'tests_and_review'
    stored_npd = int(stored.get('new_words_per_day') or 0)

    eff_npd = update.get('new_words_per_day', stored_npd)
    eff_scope = update.get('budget_scope', stored_scope)
    available = available_modules(db, language_id, all_modules)

    eff_excluded = stored_excluded
    if 'excluded_modules' in provided:
        eff_excluded = _normalize_excluded(provided['excluded_modules'], all_modules)
        err = _excluded_modules_error(eff_excluded, available, eff_npd)
        if err:
            raise PlanUpdateRejected(err)
        update['excluded_modules'] = eff_excluded

    err = _cross_field_error(available, eff_excluded, eff_scope, eff_npd)
    if err:
        raise PlanUpdateRejected(err)

    return (
        eff_excluded != stored_excluded
        or eff_scope != stored_scope
        or eff_npd != stored_npd
    )


def _save_plan(db, user_id: str, language_id: int, update: Dict[str, Any]) -> Any:
    """UPDATE the plan row. Before migrations/prestudy_workflow.sql is applied
    the prestudy_mode column does not exist: drop it and save the rest."""
    def _write():
        return (
            db.table('user_study_plans')
            .update(update)
            .eq('user_id', user_id)
            .eq('language_id', language_id)
            .execute()
        )

    try:
        return _write()
    except Exception as e:
        if 'prestudy_mode' not in update or 'prestudy_mode' not in str(e):
            raise
        update.pop('prestudy_mode')
        if not update:
            raise PlanUpdateRejected(
                "Prestudy settings are not available yet", 409, "PRESTUDY_MODE_UNAVAILABLE",
            ) from None
        return _write()


def _recompute_and_rebuild(db, user_id: str, language_id: int, local_today: LocalToday) -> bool:
    """Apply a session-settings change immediately (best-effort).

    Recompute the learner-LOCAL current week, then re-resolve today's
    unfinished slots. A failure of either step logs a WARNING and never fails
    the PUT; the lazy paths recover on the next day. Returns whether today's
    session was rebuilt.
    """
    try:
        from services.study_plan_service import StudyPlanService
        svc = StudyPlanService(db=db)
    except Exception as e:
        logger.warning("session-settings recompute unavailable: %s", e)
        return False

    try:
        svc.compute_weekly_plan(user_id, language_id, monday_of(local_today()))
    except Exception as e:
        logger.warning(
            "post-settings weekly-plan compute failed user=%s lang=%s: %s", user_id, language_id, e,
        )

    if not Config.STUDY_PLAN_ENABLED:
        return False
    try:
        return bool(svc.rebuild_today(user_id, language_id))
    except Exception as e:
        logger.warning(
            "post-settings rebuild_today failed user=%s lang=%s: %s", user_id, language_id, e,
        )
        return False


def update_plan(
    db, user_id: str, language_id: int, provided: Dict[str, Any], local_today: LocalToday,
) -> Dict[str, Any]:
    """Update the fields in ``provided`` (already validated field by field;
    see models.study_plan.StudyPlanUpdate) on the learner's existing plan.

    A change to excluded_modules / budget_scope / new_words_per_day recomputes
    the learner-local current week and rebuilds today's session (best-effort).
    Raises PlanUpdateRejected when a rule that needs the database fails.
    """
    if not provided:
        raise PlanUpdateRejected("no editable fields in request body")
    update = _column_updates(db, language_id, provided)

    # Confirm a row exists; if not, instruct caller to apply a template first.
    existing = (
        db.table('user_study_plans')
        .select('user_id, excluded_modules, budget_scope, new_words_per_day')
        .eq('user_id', user_id)
        .eq('language_id', language_id)
        .limit(1)
        .execute()
    )
    if not existing.data:
        raise PlanUpdateRejected(
            "no plan exists; PUT with template_id only, "
            "or POST to apply_study_plan_template first"
        )

    session_changed = _apply_session_settings(db, language_id, provided, existing.data[0], update)
    resp = _save_plan(db, user_id, language_id, update)
    session_rebuilt = (
        _recompute_and_rebuild(db, user_id, language_id, local_today) if session_changed else False
    )
    return {
        'plan': (resp.data or [{}])[0],
        'updated_fields': list(update.keys()),
        'session_rebuilt': session_rebuilt,
    }


# ---------------------------------------------------------------------------
# POST /api/study-plan/recompute
# ---------------------------------------------------------------------------

def recompute_current_week(user_id: str, language_id: int, local_today: LocalToday) -> Dict[str, Any]:
    """Manual Tier B recompute for the learner's current week.

    Idempotent — same inputs produce the same target_counts thanks to the
    deterministic Beta seed; completed_counts / session_progress_log are
    preserved across recomputes. Raises RecomputeFailed when the compute
    returns no result.
    """
    from services.study_plan_service import StudyPlanService
    svc = StudyPlanService()
    result = svc.compute_weekly_plan(
        user_id=user_id,
        language_id=language_id,
        week_start=monday_of(local_today()),
    )
    if result is None:
        raise RecomputeFailed(svc.last_failure or 'unknown')
    # Re-resolve today's unfinished slots too, so the recompute is visible in
    # the daily session (get_or_create_daily_load serves an existing row as-is).
    session_rebuilt = bool(svc.rebuild_today(user_id, language_id))
    return {'week_state': result, 'session_rebuilt': session_rebuilt}
