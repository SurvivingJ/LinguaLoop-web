# routes/counter_drill.py
"""Counter Drill routes — infinite 助数詞-recall trainer for Japanese.

The Japanese sibling of routes/classifier_drill.py; kept structurally identical
so the two drills stay one pattern.

Two endpoints:
  GET  /api/counter-drill/session?language_id=3&count=20
  POST /api/counter-drill/submit  body: {language_id, correct_items,
                                         total_items, time_taken,
                                         idempotency_key?}
"""

import logging
from flask import Blueprint, request, g, current_app

from middleware.auth import jwt_required as supabase_jwt_required
from services.counter_drill_service import JA_LANGUAGE_ID, get_session, submit_session
from services.dimension_service import DimensionService
from utils.responses import ApiResponse, api_success, bad_request, server_error

logger = logging.getLogger(__name__)
counter_drill_bp = Blueprint("counter_drill", __name__)


@counter_drill_bp.route('/session', methods=['GET'])
@supabase_jwt_required
def get_drill_session() -> ApiResponse:
    """Fetch a batch of counter drill items.

    Query params:
        language_id: required (only 3=Japanese is supported)
        count: optional (default 20, capped at 40)
    """
    try:
        language_id = request.args.get('language_id', type=int)
        if not language_id:
            return bad_request("language_id required")
        if language_id != JA_LANGUAGE_ID:
            return bad_request("Counter drill is Japanese-only")

        count = min(request.args.get('count', 20, type=int), 40)
        items = get_session(g.current_user_id, language_id, count)
        return api_success({
            'items': items,
            'count': len(items),
            'language_id': language_id,
        })

    except Exception as e:
        logger.error("Error building counter drill session: %s", e)
        return server_error("Failed to build counter session")


@counter_drill_bp.route('/submit', methods=['POST'])
@supabase_jwt_required
def submit_drill() -> ApiResponse:
    """Submit a completed drill session.

    Body:
        language_id: required (3=Japanese)
        correct_items: required (int)
        total_items: required (int)
        time_taken: optional (int seconds)
        idempotency_key: optional (uuid string)
    """
    try:
        data = request.get_json() or {}

        language_id = data.get('language_id')
        if not isinstance(language_id, int):
            return bad_request("language_id required")
        if language_id != JA_LANGUAGE_ID:
            return bad_request("Counter drill is Japanese-only")

        correct_items = data.get('correct_items')
        total_items = data.get('total_items')

        if not isinstance(total_items, int) or total_items <= 0:
            return bad_request("total_items must be a positive integer")
        if not isinstance(correct_items, int) or correct_items < 0 or correct_items > total_items:
            return bad_request("correct_items must satisfy 0 <= correct_items <= total_items")

        test_type_id = DimensionService.get_test_type_id('counter_drill')
        if not test_type_id:
            logger.error("counter_drill test type not configured")
            return server_error("Counter drill test type missing")

        rpc_result = submit_session(
            user_id=g.current_user_id,
            language_id=language_id,
            test_type_id=test_type_id,
            correct_items=correct_items,
            total_items=total_items,
            idempotency_key=data.get('idempotency_key'),
        )

        if not rpc_result or not rpc_result.get('success'):
            err = (rpc_result or {}).get('error', 'Unknown RPC failure')
            logger.error("counter_drill submission RPC failed: %s", err)
            return server_error("Failed to record counter session")

        # Study Plan progress hook — mirrors the classifier drill so counter
        # drills count toward weekly_plan_states.completed_counts.
        from routes.tests import _apply_timing_and_progress  # lazy: circular import
        _apply_timing_and_progress(
            current_app.supabase_service, rpc_result.get('attempt_id'), data,
        )

        accuracy = (correct_items / total_items) * 100.0 if total_items else 0.0

        return api_success({
            'accuracy': round(accuracy, 1),
            'correct_items': correct_items,
            'total_items': total_items,
            'time_taken': data.get('time_taken', 0),
            'test_mode': 'counter_drill',
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
        })

    except Exception as e:
        logger.error("Error submitting counter drill: %s", e)
        return server_error("Failed to submit counter drill")
