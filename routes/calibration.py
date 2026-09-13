# routes/calibration.py
"""Calibration routes — standalone infinite MCQ that measures vocabulary knowledge.

Five endpoints:
  POST /api/calibration/start    body: {word_language_id, definition_language_id, mode?}
  GET  /api/calibration/next     query: session_id, count? (1..MAX_BATCH)
  POST /api/calibration/answer   body: {session_id, response_id, position|null, latency_ms?}
  GET  /api/calibration/ability  query: session_id
  POST /api/calibration/end      body: {session_id}

Calibration is deliberately outside session planning: unlike the drill routes,
nothing here calls `_apply_timing_and_progress` or any `process_*_submission`
RPC, so a calibration run does not move mastery or weekly plan state. See
decision 4 in migrations/calibration_sessions_and_ability.sql. The only rating
effect is at /end, where the service hands a definition-mode result to the
guarded `apply_calibration_to_skill_ratings` RPC (TASK-752); its decisions come
back in `ability.rating_decisions`.
"""

import logging

from flask import Blueprint, request, g

from middleware.auth import jwt_required as supabase_jwt_required
from services import calibration_service
from services.calibration_service import CalibrationError
from utils.responses import (ApiResponse, api_success, bad_request, not_found,
                             server_error)

logger = logging.getLogger(__name__)
calibration_bp = Blueprint("calibration", __name__)

#: dim_languages ids that can be studied. `es` is a UI locale only — there is no
#: dim_languages row for it and therefore no senses to calibrate against.
_SUPPORTED_LANGUAGE_IDS = {1, 2, 3}


def _load_session(session_id: str):
    """Resolve a session for the current user, or return an error response."""
    if not session_id:
        return None, bad_request("session_id required")
    session = calibration_service.get_session(g.current_user_id, session_id)
    if not session:
        # Deliberately 404 rather than 403: a session belonging to someone else
        # should be indistinguishable from one that does not exist.
        return None, not_found("Calibration session not found")
    return session, None


@calibration_bp.route('/start', methods=['POST'])
@supabase_jwt_required
def start() -> ApiResponse:
    """Open a calibration session."""
    try:
        data = request.get_json() or {}
        word_language_id = data.get('word_language_id')
        definition_language_id = data.get('definition_language_id')

        if word_language_id not in _SUPPORTED_LANGUAGE_IDS:
            return bad_request("word_language_id must be 1 (zh), 2 (en) or 3 (ja)")
        if definition_language_id not in _SUPPORTED_LANGUAGE_IDS:
            return bad_request("definition_language_id must be 1 (zh), 2 (en) or 3 (ja)")

        mode = data.get('mode') or calibration_service.MODE_DEFINITION
        if mode not in calibration_service.MODES:
            return bad_request("mode must be 'definition' or 'pronunciation'")
        # Refused rather than degraded: English has 21 senses with a stored
        # reading out of 6,555, so an English pronunciation run would fail to
        # build nearly every item.
        if (mode == calibration_service.MODE_PRONUNCIATION
                and word_language_id not in calibration_service.PRONUNCIATION_LANGUAGE_IDS):
            return bad_request(
                "Pronunciation calibration is available for Chinese and Japanese only")

        session = calibration_service.start_session(
            g.current_user_id, word_language_id, definition_language_id, mode)
        return api_success({
            'session_id': str(session['id']),
            'word_language_id': session['word_language_id'],
            'definition_language_id': session['definition_language_id'],
            'mode': session.get('mode', mode),
        })
    except CalibrationError as e:
        return bad_request(str(e))
    except Exception as e:
        logger.error("Error starting calibration session: %s", e)
        return server_error("Failed to start calibration")


@calibration_bp.route('/next', methods=['GET'])
@supabase_jwt_required
def next_item() -> ApiResponse:
    """Serve the next item, or a batch of them.

    `count` (TASK-770) asks for up to that many items in one request; the client
    keeps them in a queue and renders from it, so no answer is ever followed by a
    wait for the next word. Without `count` this behaves exactly as before and
    still answers with a single `item`, so an old client keeps working.

    Both shapes are returned every time: `items` is the batch, `item` is its
    first element. `exhausted` means the language pair has nothing unseen left —
    it is NOT the same as an empty batch, which can also mean every candidate in
    this attempt had to be skipped.
    """
    try:
        session, err = _load_session(request.args.get('session_id'))
        if err:
            return err

        try:
            count = int(request.args.get('count', 1))
        except (TypeError, ValueError):
            return bad_request("count must be an integer")
        if count < 1 or count > calibration_service.MAX_BATCH:
            return bad_request(
                f"count must be between 1 and {calibration_service.MAX_BATCH}")

        batch = calibration_service.build_items(
            g.current_user_id, session, count=count)
        items = batch['items']
        return api_success({
            'items': items,
            'item': items[0] if items else None,
            'built': batch['built'],
            'exhausted': batch['exhausted'],
        })
    except CalibrationError as e:
        return bad_request(str(e))
    except Exception as e:
        logger.error("Error building calibration item: %s", e)
        return server_error("Failed to build a calibration item")


@calibration_bp.route('/answer', methods=['POST'])
@supabase_jwt_required
def answer() -> ApiResponse:
    """Record one answer. `position` may be null, meaning the learner skipped.

    TASK-769: this endpoint deliberately does NOT load the session first. The
    reveal is the one place a learner feels every millisecond, and the session
    read was a round trip spent proving something the grading RPC proves anyway —
    it checks that the response belongs to this user AND to this session before
    it writes. A session id that is wrong or not the caller's therefore comes back
    as "item does not belong to this session" (400) rather than a 404, which is
    the same amount of information: neither answer tells you whether the session
    exists.
    """
    try:
        data = request.get_json() or {}
        session_id = data.get('session_id')
        if not session_id:
            return bad_request("session_id required")
        session = {'id': session_id}

        response_id = data.get('response_id')
        if not isinstance(response_id, int):
            return bad_request("response_id required")

        position = data.get('position')
        if position is not None and not isinstance(position, int):
            return bad_request("position must be an integer or null")

        latency_ms = data.get('latency_ms')
        if latency_ms is not None and not isinstance(latency_ms, int):
            return bad_request("latency_ms must be an integer when provided")

        result = calibration_service.record_answer(
            g.current_user_id, session, response_id, position, latency_ms)
        # The counts come back from the grading RPC itself. This used to call
        # calibration_ability(fit=False) — 47 ms of SQL plus a round trip — to
        # read `answered` and `correct` out of a report whose every other field
        # was then discarded. The ability CURVE is still computed by the same
        # estimator, at /ability and /end, where someone actually looks at it.
        return api_success(result)
    except CalibrationError as e:
        return bad_request(str(e))
    except Exception as e:
        logger.error("Error recording calibration answer: %s", e)
        return server_error("Failed to record the answer")


@calibration_bp.route('/ability', methods=['GET'])
@supabase_jwt_required
def ability() -> ApiResponse:
    """The Zipf knowledge curve and its crossings so far."""
    try:
        session, err = _load_session(request.args.get('session_id'))
        if err:
            return err
        return api_success({
            'ability': calibration_service.ability(g.current_user_id, session),
        })
    except Exception as e:
        logger.error("Error computing calibration ability: %s", e)
        return server_error("Failed to compute the ability estimate")


@calibration_bp.route('/end', methods=['POST'])
@supabase_jwt_required
def end() -> ApiResponse:
    """Close the session and return the final report."""
    try:
        data = request.get_json() or {}
        session, err = _load_session(data.get('session_id'))
        if err:
            return err
        return api_success({
            'ability': calibration_service.end_session(g.current_user_id, session),
        })
    except Exception as e:
        logger.error("Error ending calibration session: %s", e)
        return server_error("Failed to end the calibration session")
