"""Recall drill routes: Chinese measure words and Japanese counters.

Each drill gets the same two endpoints under its own prefix:
  GET  /api/<drill>/session?language_id=N&count=20
  POST /api/<drill>/submit  body: {language_id, correct_items, total_items,
                                   time_taken?, idempotency_key?, item_results?}

``item_results`` ([{classifier_id, is_correct}]) is read only by the drill
that tracks per-item mastery (measure words).
"""

import logging
from flask import Blueprint, request, g

from middleware.auth import jwt_required as supabase_jwt_required
from routes.common import db
from services.dimension_service import DimensionService
from services.drill_service import CLASSIFIER_DRILL, COUNTER_DRILL, DrillService
from utils.responses import ApiResponse, api_errors, api_success, bad_request, server_error
from utils.validation import json_body, require_language_id

logger = logging.getLogger(__name__)


def make_drill_blueprint(drill: DrillService, *, label: str, wrong_language: str,
                         type_missing: str) -> Blueprint:
    """The blueprint for one drill. ``label`` is the drill's name in client
    error messages; the blueprint and its test_mode are ``drill.name``."""
    bp = Blueprint(drill.name, __name__)

    @bp.route('/session', methods=['GET'])
    @supabase_jwt_required
    @api_errors(f"Failed to build {label} session")
    @require_language_id
    def get_drill_session(language_id: int) -> ApiResponse:
        """A batch of drill items. ``count`` defaults to 20, capped at 40."""
        if language_id != drill.language_id:
            return bad_request(wrong_language)

        count = min(request.args.get('count', 20, type=int), 40)
        items = drill.get_session(g.current_user_id, language_id, count)
        return api_success({
            'items': items,
            'count': len(items),
            'language_id': language_id,
        })

    @bp.route('/submit', methods=['POST'])
    @supabase_jwt_required
    @api_errors(f"Failed to submit {label} drill")
    def submit_drill() -> ApiResponse:
        """Record a completed drill session."""
        data = json_body()

        language_id = data.get('language_id')
        if not isinstance(language_id, int):
            return bad_request("language_id required")
        if language_id != drill.language_id:
            return bad_request(wrong_language)

        correct_items = data.get('correct_items')
        total_items = data.get('total_items')

        if not isinstance(total_items, int) or total_items <= 0:
            return bad_request("total_items must be a positive integer")
        if not isinstance(correct_items, int) or correct_items < 0 or correct_items > total_items:
            return bad_request("correct_items must satisfy 0 <= correct_items <= total_items")

        test_type_id = DimensionService.get_test_type_id(drill.name)
        if not test_type_id:
            logger.error("%s test type not configured", drill.name)
            return server_error(type_missing)

        submission = {}
        if drill.mastery_rpc:
            item_results = data.get('item_results') or []
            if not isinstance(item_results, list):
                return bad_request("item_results must be a list when provided")
            submission['item_results'] = item_results

        rpc_result = drill.submit_session(
            user_id=g.current_user_id,
            language_id=language_id,
            test_type_id=test_type_id,
            correct_items=correct_items,
            total_items=total_items,
            idempotency_key=data.get('idempotency_key'),
            **submission,
        )

        if not rpc_result or not rpc_result.get('success'):
            err = (rpc_result or {}).get('error', 'Unknown RPC failure')
            logger.error("%s submission RPC failed: %s", drill.name, err)
            return server_error(f"Failed to record {label} session")

        # Study Plan progress hook, as the standard submission handlers do, so
        # drills count toward weekly_plan_states.completed_counts.
        from routes.tests import _apply_timing_and_progress  # lazy: circular import
        _apply_timing_and_progress(
            db(), rpc_result.get('attempt_id'), data,
            user_id=g.current_user_id, language_id=language_id, kind='drill',
        )

        result = {
            'accuracy': round((correct_items / total_items) * 100.0, 1),
            'correct_items': correct_items,
            'total_items': total_items,
            'time_taken': data.get('time_taken', 0),
            'test_mode': drill.name,
            'attempt_id': str(rpc_result.get('attempt_id')) if rpc_result.get('attempt_id') else None,
            'is_first_attempt': rpc_result.get('is_first_attempt'),
            'user_elo_change': {
                'before': rpc_result.get('user_elo_before'),
                'after':  rpc_result.get('user_elo_after'),
                'change': rpc_result.get('user_elo_change', 0),
            },
            'test_elo_change': {
                'before': rpc_result.get('test_elo_before'),
                'after':  rpc_result.get('test_elo_after'),
                'change': rpc_result.get('test_elo_change', 0),
            },
        }
        if drill.mastery_rpc:
            result['mastery_updates'] = rpc_result.get('mastery_updates') or []
        return api_success(result)

    return bp


classifier_drill_bp = make_drill_blueprint(
    CLASSIFIER_DRILL, label='measure-word',
    wrong_language="Measure-word drill is currently Chinese-only",
    type_missing="Classifier drill test type missing",
)
counter_drill_bp = make_drill_blueprint(
    COUNTER_DRILL, label='counter',
    wrong_language="Counter drill is Japanese-only",
    type_missing="Counter drill test type missing",
)
