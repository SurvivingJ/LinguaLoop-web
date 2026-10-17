# routes/study_plan.py
"""Study Plan routes — per-user, per-language orchestration settings.

Endpoints (all require auth):
  GET  /api/study-plan?language_id=L
       → current user_study_plans row + this week's weekly_plan_states row,
         plus the Daily-session card inputs: available_modules,
         minutes_per_new_word, typical_day, governor, forecast,
         today_new_words_shortfall.
  PUT  /api/study-plan
       Body: { language_id, daily_minutes?, weekday_shape?,
               skill_weight_overrides?, template_id?, timezone?,
               excluded_modules?, budget_scope?, new_words_per_day? }
       → updates whichever fields are present; updated_at touched via trigger.
       If only template_id is given, also resets daily_minutes from the
       template (delegates to apply_study_plan_template).
       A change to excluded_modules / budget_scope / new_words_per_day
       recomputes the learner-local current week and rebuilds today's
       session (best-effort); the response carries session_rebuilt.
  POST /api/study-plan/recompute
       Body: { language_id }
       → manual Tier B recompute for the current week. Returns the persisted
       weekly_plan_states row.
  GET  /api/study-plan/templates?language_id=L
       → array of dim_study_plan_templates available for the language.

See [[features/study-plans.tech]] sections "User plan model" and
"HTTP endpoints", [[features/session-modules.tech]] and
[[features/session-budget-settings.tech]].
"""

from __future__ import annotations

import importlib
import logging
from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Sequence, Tuple

from flask import Blueprint, current_app, g, request

from config import Config
from middleware.auth import jwt_required as supabase_jwt_required
from services.day_boundary import is_valid_timezone, plan_today
from services.study_time import weekly_study_summary
from services.supabase_factory import get_supabase_admin
from utils.responses import (
    ApiResponse, api_error, api_success, bad_request, not_found, server_error,
)

logger = logging.getLogger(__name__)
study_plan_bp = Blueprint("study_plan", __name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Timezone validation (TASK-716 / ADR-022). V1 accepted any non-empty string,
# which was harmless while nothing read the field — it now keys the daily load,
# so garbage in means a learner silently served the UTC day. Validation happens
# here at the edge; services.day_boundary still fails safe to UTC for the rows
# V1 already wrote, per ADR-020.


def _validate_weekday_shape(shape: Any) -> List[float] | None:
    """Return a 7-float list normalized to sum=7, or None if invalid."""
    if not isinstance(shape, list) or len(shape) != 7:
        return None
    try:
        floats = [float(x) for x in shape]
    except (TypeError, ValueError):
        return None
    if any(x < 0 for x in floats):
        return None
    s = sum(floats)
    if s <= 0:
        return None
    # Normalize to sum=7
    return [round(7.0 * x / s, 4) for x in floats]


def _validate_skill_weight_overrides(overrides: Any) -> Dict[str, float] | None:
    """Return a dict of {skill_code: float in [0.5, 2.0]}, or None if invalid."""
    if not isinstance(overrides, dict):
        return None
    out: Dict[str, float] = {}
    for k, v in overrides.items():
        if not isinstance(k, str):
            return None
        try:
            f = float(v)
        except (TypeError, ValueError):
            return None
        if not (0.5 <= f <= 2.0):
            return None
        out[k] = round(f, 3)
    return out


def _monday_of(d: date) -> date:
    return d - timedelta(days=d.weekday())


def _sps():
    """The study-plan service module, imported lazily.

    Resolved through importlib on every call so route tests can swap the
    module in ``sys.modules`` and so importing this blueprint never pulls in
    the heavy service at app start.
    """
    return importlib.import_module('services.study_plan_service')


BUDGET_SCOPES = ('tests_and_review', 'tests_only')
NEW_WORDS_MAX_PER_DAY = 50
MODULE_PRACTICE = 'practice'

# Fallbacks used only when the optional GET enrichments cannot be computed.
_NEW_WORD_MINUTES_FALLBACK = 3.0
_REVIEWS_PER_NEW_WORD_FALLBACK = 7
_REVIEW_ITEM_SECONDS_FALLBACK = 20.0


def _all_modules() -> Tuple[str, ...]:
    return tuple(_sps().ALL_MODULES)


def _normalize_excluded(codes: Sequence[str]) -> List[str]:
    """De-duplicate and order by ALL_MODULES (unknown codes sort last, A-Z)."""
    order = {m: i for i, m in enumerate(_all_modules())}
    return sorted(set(codes), key=lambda c: (order.get(c, len(order)), c))


def _available_modules(db, language_id: int) -> List[str]:
    """Ordered module codes offered for a language.

    Union of the keys of every template for the language (stable across
    template switches) intersected with ALL_MODULES, then ``practice``
    (Vocabulary review). Order follows ALL_MODULES.
    """
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
    return [m for m in _all_modules() if m in keys]


def _validate_excluded_modules(
    value: Any, available: Sequence[str], new_words_per_day: int = 0,
) -> Tuple[Optional[List[str]], Optional[str]]:
    """Validate ``excluded_modules``. Returns ``(normalized_list, None)`` or ``(None, message)``.

    * must be a list of strings;
    * every code must be offered for this language (``available``);
    * at least one module must stay included, where ``new_words_per_day > 0``
      counts as an included module (new words are not a module of their own).
    """
    if not isinstance(value, list) or not all(isinstance(x, str) for x in value):
        return None, "excluded_modules must be a list of module codes"
    normalized = _normalize_excluded(value)
    for code in normalized:
        if code not in available:
            return None, f"unknown module for this language: {code}"
    if not (set(available) - set(normalized)) and not new_words_per_day > 0:
        return None, "at least one module must remain included"
    return normalized, None


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


def _safe(label: str, fn, default=None):
    """Run an optional GET enrichment; log and fall back instead of failing the page."""
    try:
        return fn()
    except Exception as e:
        logger.warning("study-plan GET %s failed: %s", label, e)
        return default


# ---------------------------------------------------------------------------
# GET /api/study-plan?language_id=L
# ---------------------------------------------------------------------------

@study_plan_bp.route('', methods=['GET'])
@supabase_jwt_required
def get_study_plan() -> ApiResponse:
    """Return the user's plan + current week's state for one language."""
    try:
        language_id = request.args.get('language_id', type=int)
        if not language_id:
            return bad_request("language_id required")

        db = get_supabase_admin()
        user_id = g.current_user_id

        plan_resp = (
            db.table('user_study_plans')
            .select(
                'user_id, language_id, template_id, daily_minutes, '
                'weekday_shape, skill_weight_overrides, goal_id, timezone, '
                'excluded_modules, budget_scope, new_words_per_day, '
                'created_at, updated_at'
            )
            .eq('user_id', user_id)
            .eq('language_id', language_id)
            .limit(1)
            .execute()
        )
        if not plan_resp.data:
            return not_found("No study plan for this language")

        plan = plan_resp.data[0]

        # Learner-local week (matches the ledger/record_session_progress writers).
        week_start = _monday_of(plan_today(db, user_id, language_id))
        week_resp = (
            db.table('weekly_plan_states')
            .select(
                'week_start_date, target_counts, skill_values, completed_counts, '
                'practice_target_minutes, practice_completed_maint_min, '
                'practice_completed_acq_min, maintenance_share, '
                'acquisition_share, total_weekly_minutes, computed_at, '
                'budget_scope, review_target_minutes, new_words_target, '
                'new_words_completed, acq_target_minutes, tail_completed_min, '
                'tail_new_words_completed'
            )
            .eq('user_id', user_id)
            .eq('language_id', language_id)
            .eq('week_start_date', week_start.isoformat())
            .limit(1)
            .execute()
        )
        current_week = week_resp.data[0] if week_resp.data else None

        extras = _daily_session_extras(db, user_id, language_id, plan, current_week)
        # Weekly minutes ledger total (ADR-035). Degrades to null; never fails the GET.
        target_minutes = (current_week or {}).get('total_weekly_minutes')
        weekly_study = _safe(
            'weekly_study',
            lambda: weekly_study_summary(
                db, user_id, language_id, week_start, target_minutes,
            ),
            None,
        )
        return api_success({
            'plan': plan,
            'current_week': current_week,
            'weekly_study': weekly_study,
            'study_plan_enabled': bool(Config.STUDY_PLAN_ENABLED),
            **extras,
        })

    except Exception as e:
        logger.error("get_study_plan failed: %s", e)
        return server_error("Failed to fetch study plan")


def _daily_session_extras(
    db, user_id: str, language_id: int, plan: Dict[str, Any],
    current_week: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """Inputs of the settings page's "Daily session" card (session-budget-settings).

    Every piece is best-effort: a failure degrades that piece (None / neutral
    defaults) and never fails the GET.
    """
    sps = _sps()
    available = _safe('available_modules', lambda: _available_modules(db, language_id), [MODULE_PRACTICE])

    mpnw = _safe(
        'minutes_per_new_word',
        lambda: float(sps.get_minutes_per_new_word(db, language_id)),
        float(getattr(Config, 'NEW_WORD_MINUTES_DEFAULT', _NEW_WORD_MINUTES_FALLBACK)),
    )

    typical_day = None
    if current_week:
        typical_day = _safe(
            'typical_day', lambda: sps.typical_day_inputs(db, language_id, plan, current_week), None,
        )

    local_today = _safe('plan_today', lambda: plan_today(db, user_id, language_id), date.today())
    gov_raw = _safe(
        'governor', lambda: sps.get_review_governor(db, user_id, language_id, local_today), None,
    ) or {}
    governor = {
        'level': gov_raw.get('level') or 'normal',
        'overdue_items': gov_raw.get('overdue_items') or 0,
        'overdue_minutes': gov_raw.get('overdue_minutes') or 0,
        'threshold_minutes': gov_raw.get('threshold_minutes') or 0,
    }

    npd = int(plan.get('new_words_per_day') or 0)
    shape = plan.get('weekday_shape') or None
    item_seconds = float(
        gov_raw.get('item_seconds')
        or getattr(Config, 'REVIEW_ITEM_SECONDS_DEFAULT', _REVIEW_ITEM_SECONDS_FALLBACK)
    )
    reviews_per_word = (
        getattr(Config, 'REVIEWS_PER_NEW_WORD_30D', None)
        or getattr(sps, 'REVIEWS_PER_NEW_WORD_30D', None)
        or _REVIEWS_PER_NEW_WORD_FALLBACK
    )

    def _forecast_min() -> float:
        avg = sps.new_words_week_target(npd, shape) / 7.0
        return round(float(sps.review_forecast_min_per_day(avg, item_seconds)), 2)

    forecast = {
        'reviews_per_new_word_30d': reviews_per_word,
        'item_seconds': item_seconds,
        'min_per_day': _safe('forecast', _forecast_min, 0.0),
    }

    def _shortfall() -> Optional[int]:
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

    return {
        'available_modules': available,
        'minutes_per_new_word': mpnw,
        'typical_day': typical_day,
        'governor': governor,
        'forecast': forecast,
        'today_new_words_shortfall': _safe('shortfall', _shortfall, None),
    }


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
    """Set new_words_per_day = max(1, daily_minutes // 6) on a freshly created plan row.

    Words PER DAY (5 per day at 30 min). apply_study_plan_template does not set
    the column, so without this the DB safety default (5) would apply whatever
    the template. Existing rows are never touched. Best-effort.
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
        default = max(1, int(resp.data[0]['daily_minutes']) // 6)
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


def _recompute_and_rebuild(db, user_id: str, language_id: int) -> bool:
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
        svc.compute_weekly_plan(
            user_id, language_id, _monday_of(plan_today(db, user_id, language_id)),
        )
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


# ---------------------------------------------------------------------------
# PUT /api/study-plan
# ---------------------------------------------------------------------------

@study_plan_bp.route('', methods=['PUT'])
@supabase_jwt_required
def update_study_plan() -> ApiResponse:
    """Update (or create-from-template) the user's plan for one language.

    Validation:
      daily_minutes          : int in [10, 180]
      weekday_shape          : list of 7 non-negative floats; normalized to sum=7
      skill_weight_overrides : {skill_code: float in [0.5, 2.0]}
      template_id            : must reference dim_study_plan_templates AND
                                match language_id
      timezone               : a valid IANA zone name (TASK-716); rejected
                                otherwise. Keys the daily load via ADR-022.
      excluded_modules       : list of module codes offered for the language;
                                new_words_per_day > 0 counts as an included
                                module (session-modules / session-budget).
      budget_scope           : 'tests_and_review' | 'tests_only'
      new_words_per_day      : int (not bool/float) in [0, 50]. > 0 with
                                Vocabulary review off is ALLOWED (all new words
                                then go to the optional tail).
    Cross-field rules run on the merged (request-else-stored) state.
    """
    try:
        data = request.get_json() or {}
        language_id = data.get('language_id')
        if not isinstance(language_id, int):
            return bad_request("language_id (int) required")

        db = get_supabase_admin()
        user_id = g.current_user_id

        # If only template_id present (and no other fields), delegate to the
        # idempotent apply_study_plan_template RPC.
        is_template_only = (
            'template_id' in data
            and not any(k in data for k in (
                'daily_minutes', 'weekday_shape',
                'skill_weight_overrides', 'timezone',
                'excluded_modules', 'budget_scope', 'new_words_per_day',
            ))
        )
        if is_template_only:
            tmpl = data.get('template_id')
            if not isinstance(tmpl, int):
                return bad_request("template_id (int) required")
            plan_existed = _plan_row_exists(db, user_id, language_id)
            try:
                rpc_resp = db.rpc('apply_study_plan_template', {
                    'p_user_id':     user_id,
                    'p_language_id': language_id,
                    'p_template_id': tmpl,
                }).execute()
            except Exception as e:
                logger.error("apply_study_plan_template failed: %s", e)
                return server_error("Failed to apply template")
            if plan_existed is False:
                _apply_new_words_default(db, user_id, language_id, rpc_resp.data)
            # Seed this week's plan immediately so the very first daily load
            # after applying a template is plan-driven, instead of waiting for
            # the Sunday pacer (which seeds next week) or leaning on the lazy
            # compute in get_or_create_daily_load. Best-effort: a failure here
            # still returns the applied template — the lazy path recovers it.
            try:
                from services.study_plan_service import StudyPlanService
                StudyPlanService(db=db).compute_weekly_plan(
                    user_id, language_id, _monday_of(plan_today(db, user_id, language_id)),
                )
            except Exception as e:
                logger.warning(
                    "post-template weekly-plan compute failed for "
                    "user=%s lang=%s: %s", user_id, language_id, e,
                )
            return api_success({'plan': rpc_resp.data})

        # Build a partial UPDATE payload.
        update: Dict[str, Any] = {}

        if 'daily_minutes' in data:
            dm = data['daily_minutes']
            if not isinstance(dm, int) or not (10 <= dm <= 180):
                return bad_request("daily_minutes must be int in [10, 180]")
            update['daily_minutes'] = dm

        if 'weekday_shape' in data:
            shape = _validate_weekday_shape(data['weekday_shape'])
            if shape is None:
                return bad_request(
                    "weekday_shape must be 7 non-negative floats summing > 0"
                )
            update['weekday_shape'] = shape

        if 'skill_weight_overrides' in data:
            overrides = _validate_skill_weight_overrides(data['skill_weight_overrides'])
            if overrides is None:
                return bad_request(
                    "skill_weight_overrides must be {skill: float in [0.5, 2.0]}"
                )
            update['skill_weight_overrides'] = overrides

        if 'template_id' in data:
            tmpl = data['template_id']
            if not isinstance(tmpl, int):
                return bad_request("template_id must be int")
            # Validate template belongs to this language
            tmpl_resp = (
                db.table('dim_study_plan_templates')
                .select('template_id, language_id, daily_minutes')
                .eq('template_id', tmpl)
                .limit(1)
                .execute()
            )
            if not tmpl_resp.data:
                return bad_request(f"unknown template_id={tmpl}")
            if int(tmpl_resp.data[0]['language_id']) != language_id:
                return bad_request("template language does not match language_id")
            update['template_id'] = tmpl
            # If daily_minutes not also given, copy from the template
            update.setdefault(
                'daily_minutes', tmpl_resp.data[0]['daily_minutes']
            )

        if 'timezone' in data:
            tz = data['timezone']
            if not isinstance(tz, str) or not tz.strip():
                return bad_request("timezone must be a non-empty string")
            if not is_valid_timezone(tz):
                return bad_request(
                    "timezone must be a valid IANA zone name (e.g. Asia/Tokyo)"
                )
            update['timezone'] = tz.strip()

        session_fields = [
            k for k in ('excluded_modules', 'budget_scope', 'new_words_per_day') if k in data
        ]

        if 'budget_scope' in data:
            if data['budget_scope'] not in BUDGET_SCOPES:
                return bad_request("budget_scope must be 'tests_and_review' or 'tests_only'")
            update['budget_scope'] = data['budget_scope']

        if 'new_words_per_day' in data:
            nwpd = data['new_words_per_day']
            # bool is an int subclass; floats (5.0) are rejected on purpose.
            if (
                not isinstance(nwpd, int) or isinstance(nwpd, bool)
                or not (0 <= nwpd <= NEW_WORDS_MAX_PER_DAY)
            ):
                return bad_request("new_words_per_day must be int in [0, 50]")
            update['new_words_per_day'] = nwpd

        if 'excluded_modules' in data:
            raw_excluded = data['excluded_modules']
            if not isinstance(raw_excluded, list) or not all(isinstance(x, str) for x in raw_excluded):
                return bad_request("excluded_modules must be a list of module codes")

        if not update and not session_fields:
            return bad_request("no editable fields in request body")

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
            return bad_request(
                "no plan exists; PUT with template_id only, "
                "or POST to apply_study_plan_template first"
            )
        stored = existing.data[0]

        # Session settings: validate against the merged state and detect change.
        session_changed = False
        if session_fields:
            stored_excluded = _normalize_excluded(stored.get('excluded_modules') or [])
            stored_scope = stored.get('budget_scope') or 'tests_and_review'
            stored_npd = int(stored.get('new_words_per_day') or 0)

            eff_npd = update.get('new_words_per_day', stored_npd)
            eff_scope = update.get('budget_scope', stored_scope)
            available = _available_modules(db, language_id)

            eff_excluded = stored_excluded
            if 'excluded_modules' in data:
                normalized, err = _validate_excluded_modules(
                    data['excluded_modules'], available, eff_npd,
                )
                if err:
                    return bad_request(err)
                eff_excluded = normalized
                update['excluded_modules'] = normalized

            err = _cross_field_error(available, eff_excluded, eff_scope, eff_npd)
            if err:
                return bad_request(err)

            session_changed = (
                eff_excluded != stored_excluded
                or eff_scope != stored_scope
                or eff_npd != stored_npd
            )

        resp = (
            db.table('user_study_plans')
            .update(update)
            .eq('user_id', user_id)
            .eq('language_id', language_id)
            .execute()
        )
        session_rebuilt = False
        if session_changed:
            session_rebuilt = _recompute_and_rebuild(db, user_id, language_id)

        return api_success({
            'plan': (resp.data or [{}])[0],
            'updated_fields': list(update.keys()),
            'session_rebuilt': session_rebuilt,
        })

    except Exception as e:
        logger.error("update_study_plan failed: %s", e)
        return server_error("Failed to update study plan")


# ---------------------------------------------------------------------------
# POST /api/study-plan/recompute
# ---------------------------------------------------------------------------

@study_plan_bp.route('/recompute', methods=['POST'])
@supabase_jwt_required
def recompute_weekly_plan() -> ApiResponse:
    """Manual Tier B recompute for the current week.

    Body: { language_id }

    Idempotent — same inputs produce the same target_counts thanks to the
    deterministic Beta seed; completed_counts / session_progress_log are
    preserved across recomputes.
    """
    try:
        data = request.get_json() or {}
        language_id = data.get('language_id')
        if not isinstance(language_id, int):
            return bad_request("language_id (int) required")

        if not Config.STUDY_PLAN_ENABLED:
            return bad_request(
                "STUDY_PLAN_ENABLED is False; recompute is disabled."
            )

        from services.study_plan_service import StudyPlanService
        svc = StudyPlanService()
        result = svc.compute_weekly_plan(
            user_id=g.current_user_id,
            language_id=int(language_id),
            week_start=_monday_of(
                plan_today(get_supabase_admin(), g.current_user_id, int(language_id))
            ),
        )
        if result is None:
            return api_error(
                "compute_weekly_plan returned no result — check server logs.",
                500, 'SERVER_ERROR',
                details={'stage': svc.last_failure or 'unknown'},
            )
        # Re-resolve today's unfinished slots too, so the recompute is visible in
        # the daily session (get_or_create_daily_load serves an existing row as-is).
        session_rebuilt = bool(svc.rebuild_today(g.current_user_id, int(language_id)))
        return api_success({'week_state': result, 'session_rebuilt': session_rebuilt})

    except Exception:
        # Full traceback: every handled failure inside compute_weekly_plan
        # returns None (→ the "no result" branch above), so reaching here means
        # an unexpected exception whose stack we need.
        logger.exception("recompute_weekly_plan failed")
        return server_error("Failed to recompute weekly plan")


# ---------------------------------------------------------------------------
# GET /api/study-plan/templates?language_id=L
# ---------------------------------------------------------------------------

@study_plan_bp.route('/templates', methods=['GET'])
@supabase_jwt_required
def get_templates() -> ApiResponse:
    """List available study-plan templates for a language."""
    try:
        language_id = request.args.get('language_id', type=int)
        if not language_id:
            return bad_request("language_id required")

        db = get_supabase_admin()
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
        return api_success({'templates': resp.data or []})

    except Exception as e:
        logger.error("get_templates failed: %s", e)
        return server_error("Failed to fetch templates")
