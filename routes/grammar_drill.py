"""Grammar-drill progress tracking routes (TASK-1259, ADR-066).

  POST /api/grammar-drill/round     body: {language_id, round_key (uuid),
        mode: 'round'|'mixed'|'endless'|'sync', played_at? (epoch seconds),
        topics: [{topic, answers, correct, timed, ms_sum, stage, instant,
                  sub_misses, state}]}
  GET  /api/grammar-drill/progress?language_id=N&days=180

The drills themselves are static files; these two routes only keep daily
summaries and a small state row per topic. Until
migrations/grammar_drill_tracking.sql is applied both answer 503
(GRAMMAR_TRACKING_UNAVAILABLE) and the page keeps its progress locally.
"""

import logging

from flask import Blueprint, g, request

from middleware.auth import jwt_required as supabase_jwt_required
from routes.common import get_db
from services import grammar_drill_tracking as tracking
from utils.responses import ApiResponse, api_error, api_errors, api_success, bad_request
from utils.validation import json_body, require_language_id

logger = logging.getLogger(__name__)

grammar_drill_bp = Blueprint('grammar_drill', __name__)


def _unavailable() -> ApiResponse:
    return api_error("Grammar drill tracking is not available yet", 503,
                     'GRAMMAR_TRACKING_UNAVAILABLE')


@grammar_drill_bp.route('/round', methods=['POST'])
@supabase_jwt_required
@api_errors("Failed to record grammar drill round")
def record_round() -> ApiResponse:
    """Record the first-answer totals of one finished round (idempotent on
    round_key), and the learner's current state per topic."""
    try:
        round_ = tracking.validate_round(json_body())
    except tracking.ValidationError as exc:
        return bad_request(str(exc))
    try:
        result = tracking.record_round(get_db(), g.current_user_id, round_)
    except tracking.TrackingUnavailable:
        return _unavailable()
    return api_success({
        'recorded': result['recorded'],
        'replayed': result['replayed'],
        'practice_day': round_['practice_day'].isoformat(),
    })


@grammar_drill_bp.route('/progress', methods=['GET'])
@supabase_jwt_required
@api_errors("Failed to load grammar drill progress")
@require_language_id
def get_progress(language_id: int) -> ApiResponse:
    """The caller's own state per topic and daily summaries (``days`` back,
    default 180, capped at 365)."""
    if language_id != tracking.LANGUAGE_ID:
        return bad_request("Grammar drills are Chinese-only")
    days = request.args.get('days', tracking.DEFAULT_DAYS, type=int)
    if not days or days < 1:
        return bad_request("days must be a positive integer")
    try:
        progress = tracking.load_progress(get_db(), g.current_user_id, days)
    except tracking.TrackingUnavailable:
        return _unavailable()
    return api_success(progress)
