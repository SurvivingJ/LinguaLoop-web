# routes/practice.py
"""Practice Engine routes — canonical merged surface (Phase 12).

Replaces the split between /api/exercises/session and /api/vocab-dojo/session
with a single mode-dispatched endpoint. See [[features/practice-engine.tech]]
and [[decisions/ADR-007-merge-exercises-vocab-dojo]].

Endpoints:
  GET  /api/practice/session   — fetch a session in the requested mode
  POST /api/practice/attempt   — submit an attempt, propagate BKT/FSRS/progress

Gate / stress-test marker items in the response carry only
`is_gate_marker` / `is_stress_test_marker` + `sense_id` + `gate_name`.
The FE materialises the actual battery by calling the existing
/api/vocab-dojo/gate or /stress-test endpoints (unchanged by the merger).
"""

from flask import Blueprint, request, g
import logging

from middleware.auth import jwt_required as supabase_jwt_required
from utils.responses import ApiResponse, api_success, bad_request, server_error

logger = logging.getLogger(__name__)
practice_bp = Blueprint("practice", __name__)


# ---------------------------------------------------------------------------
# GET /api/practice/session?mode=...&minutes=...&language_id=...&debug=0|1
# ---------------------------------------------------------------------------

_VALID_MODES = ('acquisition', 'maintenance', 'auto')


@practice_bp.route('/session', methods=['GET'])
@supabase_jwt_required
def get_practice_session() -> ApiResponse:
    """Return today's Practice session.

    Query params:
        language_id : required (int)
        mode        : optional, one of {acquisition, maintenance, auto}
                      (default: auto)
        minutes     : optional time budget (1..180; default 15)
        debug       : optional (0|1); when 1, items include score_breakdown
    """
    try:
        language_id = request.args.get('language_id', type=int)
        if not language_id:
            return bad_request("language_id required")

        mode = (request.args.get('mode') or 'auto').lower()
        if mode not in _VALID_MODES:
            return bad_request(
                f"mode must be one of {_VALID_MODES} (got {mode!r})"
            )

        minutes = request.args.get('minutes', 15, type=int)
        if minutes < 1 or minutes > 180:
            return bad_request("minutes must be between 1 and 180")

        debug = request.args.get('debug', '0') == '1'

        from services.practice_session_service import get_practice_session_service
        payload = get_practice_session_service().get_session(
            user_id=g.current_user_id,
            language_id=int(language_id),
            mode=mode,
            target_minutes=minutes,
            debug=debug,
        )

        if isinstance(payload, dict) and 'error' in payload:
            code = payload.get('code', 'E_UNKNOWN')
            if code in ('E_LANG', 'E_MODE', 'E_RANGE'):
                return bad_request(payload.get('error', code))
            return server_error(payload.get('error', code))

        return api_success(payload)

    except Exception as e:
        logger.error("Error building practice session: %s", e)
        return server_error("Failed to build practice session")


# ---------------------------------------------------------------------------
# POST /api/practice/attempt
# ---------------------------------------------------------------------------

@practice_bp.route('/attempt', methods=['POST'])
@supabase_jwt_required
def submit_practice_attempt() -> ApiResponse:
    """Record a Practice attempt with BKT + FSRS + Study Plan progress updates.

    Body:
        exercise_id   : required (uuid str)
        is_correct    : required (bool)
        user_response : optional (dict)
        time_taken_ms : optional (int)
        session_mode  : optional ('acquisition'|'maintenance'); when set,
                        record_session_progress is called to bump the
                        weekly_plan_states counter for the right Practice
                        mode. Omit for non-plan-tracked attempts (e.g. admin
                        tooling).
        language_id   : optional override; otherwise looked up from
                        exercises.language_id.
    """
    try:
        data = request.get_json() or {}
        exercise_id = data.get('exercise_id')
        if not exercise_id:
            return bad_request("exercise_id required")

        if 'is_correct' not in data:
            return bad_request("is_correct required")

        # Virtual items have no DB row — accept silently for FE simplicity.
        if str(exercise_id).startswith('virtual-'):
            return api_success({
                'is_correct': bool(data.get('is_correct', False)),
                'exercise_type': data.get('exercise_type') or 'virtual',
                'virtual': True,
            })

        # Gate / stress markers should NOT be POSTed here — they flow through
        # the existing /api/vocab-dojo/gate and /stress-test endpoints.
        if data.get('is_gate_marker') or data.get('is_stress_test_marker'):
            return bad_request(
                "Gate and stress-test markers must be submitted via the "
                "existing /api/vocab-dojo/gate and /stress-test endpoints."
            )

        session_mode = data.get('session_mode')
        if session_mode is not None and session_mode not in ('acquisition', 'maintenance'):
            return bad_request("session_mode must be 'acquisition' or 'maintenance'")

        from services.practice_session_service import get_practice_session_service
        result = get_practice_session_service().record_attempt_with_updates(
            user_id=g.current_user_id,
            exercise_id=str(exercise_id),
            is_correct=bool(data['is_correct']),
            user_response=data.get('user_response'),
            time_taken_ms=data.get('time_taken_ms'),
            session_mode=session_mode,
            language_id=data.get('language_id'),
        )

        if isinstance(result, dict) and result.get('error'):
            return server_error(result['error'])

        return api_success(result)

    except Exception as e:
        logger.error("Error submitting practice attempt: %s", e)
        return server_error("Failed to submit attempt")
