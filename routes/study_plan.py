# routes/study_plan.py
"""Study Plan routes — per-user, per-language orchestration settings.

Endpoints (all require auth):
  GET  /api/study-plan?language_id=L
       → current user_study_plans row + this week's weekly_plan_states row.
  PUT  /api/study-plan
       Body: { language_id, daily_minutes?, weekday_shape?,
               skill_weight_overrides?, template_id?, timezone? }
       → updates whichever fields are present; updated_at touched via trigger.
       If only template_id is given, also resets daily_minutes from the
       template (delegates to apply_study_plan_template).
  POST /api/study-plan/recompute
       Body: { language_id }
       → manual Tier B recompute for the current week. Returns the persisted
       weekly_plan_states row.
  GET  /api/study-plan/templates?language_id=L
       → array of dim_study_plan_templates available for the language.

See [[features/study-plans.tech]] sections "User plan model" and
"HTTP endpoints".
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any, Dict, List

from flask import Blueprint, current_app, g, request

from config import Config
from middleware.auth import jwt_required as supabase_jwt_required
from services.supabase_factory import get_supabase_admin
from utils.responses import (
    ApiResponse, api_success, bad_request, not_found, server_error,
)

logger = logging.getLogger(__name__)
study_plan_bp = Blueprint("study_plan", __name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_VALID_TIMEZONE_RE = None  # validation deferred to V2; V1 stores any string.


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

        week_start = _monday_of(date.today())
        week_resp = (
            db.table('weekly_plan_states')
            .select(
                'week_start_date, target_counts, skill_values, completed_counts, '
                'practice_target_minutes, practice_completed_maint_min, '
                'practice_completed_acq_min, maintenance_share, '
                'acquisition_share, total_weekly_minutes, computed_at'
            )
            .eq('user_id', user_id)
            .eq('language_id', language_id)
            .eq('week_start_date', week_start.isoformat())
            .limit(1)
            .execute()
        )
        current_week = week_resp.data[0] if week_resp.data else None

        return api_success({
            'plan': plan,
            'current_week': current_week,
            'study_plan_enabled': bool(Config.STUDY_PLAN_ENABLED),
        })

    except Exception as e:
        logger.error("get_study_plan failed: %s", e)
        return server_error("Failed to fetch study plan")


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
      timezone               : opaque string (V1 stores any non-empty string)
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
            ))
        )
        if is_template_only:
            tmpl = data.get('template_id')
            if not isinstance(tmpl, int):
                return bad_request("template_id (int) required")
            try:
                rpc_resp = db.rpc('apply_study_plan_template', {
                    'p_user_id':     user_id,
                    'p_language_id': language_id,
                    'p_template_id': tmpl,
                }).execute()
            except Exception as e:
                logger.error("apply_study_plan_template failed: %s", e)
                return server_error("Failed to apply template")
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
            update['timezone'] = tz.strip()

        if not update:
            return bad_request("no editable fields in request body")

        # Confirm a row exists; if not, instruct caller to apply a template first.
        existing = (
            db.table('user_study_plans')
            .select('user_id')
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

        resp = (
            db.table('user_study_plans')
            .update(update)
            .eq('user_id', user_id)
            .eq('language_id', language_id)
            .execute()
        )
        return api_success({
            'plan': (resp.data or [{}])[0],
            'updated_fields': list(update.keys()),
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
            week_start=_monday_of(date.today()),
        )
        if result is None:
            return server_error(
                "compute_weekly_plan returned no result — check server logs."
            )
        return api_success({'week_state': result})

    except Exception as e:
        logger.error("recompute_weekly_plan failed: %s", e)
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
