# routes/test_intros.py
"""First-time test-type explainer popup — "seen" tracking endpoints.

See services/test_intro_service.py for the storage model and rationale.
"""

import logging

from flask import Blueprint, request, g

from middleware.auth import jwt_required
from services import test_intro_service
from utils.responses import ApiResponse, api_success, bad_request, server_error

logger = logging.getLogger(__name__)
test_intros_bp = Blueprint('test_intros', __name__, url_prefix='/api/test-intros')

# Kept in sync with static/js/test-intro.js TEST_TYPE_INTRO_KEYS.
VALID_TEST_TYPES = {
    'reading', 'listening', 'dictation', 'pinyin', 'pitch_accent',
    'classifier_drill', 'counter_drill',
}


@test_intros_bp.route('/seen', methods=['GET'])
@jwt_required
def get_seen() -> ApiResponse:
    """Return the test_type codes this user has already seen the intro for."""
    try:
        seen = test_intro_service.get_seen_test_types(g.current_user_id)
        return api_success({'seen': sorted(seen)})
    except Exception:
        logger.exception('get_seen failed')
        return server_error()


@test_intros_bp.route('/seen', methods=['POST'])
@jwt_required
def mark_seen() -> ApiResponse:
    """Flag one test type's intro as seen for this user. Idempotent."""
    try:
        body = request.get_json(silent=True) or {}
        test_type = body.get('test_type')
        if not test_type or test_type not in VALID_TEST_TYPES:
            return bad_request('Unknown test_type')

        result = test_intro_service.mark_test_intro_seen(g.current_user_id, test_type)
        if not result.get('success'):
            return server_error(result.get('error', 'Failed to record intro as seen'))
        return api_success()
    except Exception:
        logger.exception('mark_seen failed')
        return server_error()
