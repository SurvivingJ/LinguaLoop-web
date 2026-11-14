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
               excluded_modules?, budget_scope?, new_words_per_day?,
               prestudy_mode? }
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

Request validation lives in models.study_plan and the reads and writes in
services.study_plan_settings; this module parses, calls and responds.

See [[features/study-plans.tech]] sections "User plan model" and
"HTTP endpoints", [[features/session-modules.tech]] and
[[features/session-budget-settings.tech]].
"""

from __future__ import annotations

import logging

from flask import Blueprint, g

from config import Config
from middleware.auth import jwt_required as supabase_jwt_required
from routes.common import get_db
from models.study_plan import (
    InvalidStudyPlanRequest, StudyPlanTemplateApply, parse_study_plan_request,
)
from services import study_plan_settings as _settings
from services.day_boundary import plan_today
from services.study_plan_settings import monday_of as _monday_of  # noqa: F401  (earlier import path)
from utils.responses import (
    api_errors, ApiResponse, api_error, api_success, bad_request, not_found, server_error,
)
from utils.validation import json_body, require_language_id

logger = logging.getLogger(__name__)
study_plan_bp = Blueprint("study_plan", __name__)


# ---------------------------------------------------------------------------
# GET /api/study-plan?language_id=L
# ---------------------------------------------------------------------------

@study_plan_bp.route('', methods=['GET'])
@supabase_jwt_required
@api_errors("Failed to fetch study plan")
@require_language_id
def get_study_plan(language_id: int) -> ApiResponse:
    """Return the user's plan + current week's state for one language."""
    db = get_db()
    user_id = g.current_user_id
    overview = _settings.plan_overview(
        db, user_id, language_id, lambda: plan_today(db, user_id, language_id),
    )
    if overview is None:
        return not_found("No study plan for this language")
    return api_success(overview)


# ---------------------------------------------------------------------------
# PUT /api/study-plan
# ---------------------------------------------------------------------------

@study_plan_bp.route('', methods=['PUT'])
@supabase_jwt_required
@api_errors("Failed to update study plan")
def update_study_plan() -> ApiResponse:
    """Update (or create-from-template) the user's plan for one language.

    Field rules are in models.study_plan.StudyPlanUpdate; the rules that need
    the database (template language, modules offered for the language, the
    merged session settings) in services.study_plan_settings.update_plan.
    """
    try:
        body = parse_study_plan_request(json_body())
    except InvalidStudyPlanRequest as e:
        return bad_request(str(e))

    db = get_db()
    user_id = g.current_user_id
    language_id = body.language_id

    def local_today():
        return plan_today(db, user_id, language_id)

    if isinstance(body, StudyPlanTemplateApply):
        try:
            plan = _settings.apply_template(
                db, user_id, language_id, body.template_id, local_today)
        except _settings.TemplateApplyFailed:
            return server_error("Failed to apply template")
        return api_success({'plan': plan})

    try:
        return api_success(_settings.update_plan(
            db, user_id, language_id, body.provided(), local_today))
    except _settings.PlanUpdateRejected as e:
        if e.status == 400:
            return bad_request(str(e))
        return api_error(str(e), e.status, error_code=e.error_code)


# ---------------------------------------------------------------------------
# POST /api/study-plan/recompute
# ---------------------------------------------------------------------------

@study_plan_bp.route('/recompute', methods=['POST'])
@supabase_jwt_required
@api_errors("Failed to recompute weekly plan")
def recompute_weekly_plan() -> ApiResponse:
    """Manual Tier B recompute for the current week.

    Body: { language_id }
    """
    data = json_body()
    language_id = data.get('language_id')
    if not isinstance(language_id, int):
        return bad_request("language_id (int) required")

    if not Config.STUDY_PLAN_ENABLED:
        return bad_request(
            "STUDY_PLAN_ENABLED is False; recompute is disabled."
        )

    user_id = g.current_user_id
    try:
        return api_success(_settings.recompute_current_week(
            user_id, int(language_id),
            lambda: plan_today(get_db(), user_id, int(language_id)),
        ))
    except _settings.RecomputeFailed as e:
        return api_error(
            "compute_weekly_plan returned no result — check server logs.",
            500, 'SERVER_ERROR',
            details={'stage': e.stage},
        )


# ---------------------------------------------------------------------------
# GET /api/study-plan/templates?language_id=L
# ---------------------------------------------------------------------------

@study_plan_bp.route('/templates', methods=['GET'])
@supabase_jwt_required
@api_errors("Failed to fetch templates")
@require_language_id
def get_templates(language_id: int) -> ApiResponse:
    """List available study-plan templates for a language."""
    return api_success({
        'templates': _settings.list_templates(get_db(), language_id),
    })
