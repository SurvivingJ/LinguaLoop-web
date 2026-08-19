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
        time_taken_ms : optional (int) — render→submit elapsed for this item;
                        drives weekly practice-minute accrual (TASK-701).
        expected_seconds : optional (int) — the item's p50 time estimate;
                        credited as a fallback when time_taken_ms is missing,
                        zero, or absurdly large.
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
        service = get_practice_session_service()

        # TASK-532: cloze_typed is graded on the server, not in the browser.
        # The comparison is a normalisation rule (NFKC, t2s, case, trailing
        # punctuation); duplicating it in JS would leave two implementations of
        # one rule to keep in step. The client still sends is_correct — for
        # this type it is a hint that gets overwritten.
        typed_grade = _grade_typed_if_needed(str(exercise_id), data)
        if typed_grade is not None:
            data['is_correct'] = typed_grade['is_correct']
            response = dict(data.get('user_response') or {})
            response['grading'] = typed_grade
            data['user_response'] = response

        # TASK-533: a speed-round attempt updates FSRS only. A slow-but-correct
        # answer under a clock is not evidence that a mastered word's family
        # confidence has decayed, so it must not move the ladder — see
        # speed_round.UPDATES_FAMILY_CONFIDENCE.
        if data.get('is_speed_round'):
            result = service.record_speed_round_attempt(
                user_id=g.current_user_id,
                exercise_id=str(exercise_id),
                is_correct=bool(data['is_correct']),
                time_taken_ms=data.get('time_taken_ms'),
                timed_out=bool(data.get('timed_out')),
            )
        else:
            result = service.record_attempt_with_updates(
                user_id=g.current_user_id,
                exercise_id=str(exercise_id),
                is_correct=bool(data['is_correct']),
                user_response=data.get('user_response'),
                time_taken_ms=data.get('time_taken_ms'),
                session_mode=session_mode,
                language_id=data.get('language_id'),
                expected_seconds=data.get('expected_seconds'),
            )

        if isinstance(result, dict) and result.get('error'):
            return server_error(result['error'])

        return api_success(result)

    except Exception as e:
        logger.error("Error submitting practice attempt: %s", e)
        return server_error("Failed to submit attempt")


#: Exercise types whose correctness the server decides rather than the client.
#: Only free-input types belong here — for a multiple-choice item the correct
#: option is already in the payload, so re-deciding it server-side would add a
#: query and protect nothing.
_SERVER_GRADED_TYPES = ('cloze_typed',)


def _grade_typed_if_needed(exercise_id: str, data: dict):
    """Re-grade a free-input answer server-side, or None if not applicable.

    Returns None — meaning "leave the client's verdict alone" — for every type
    outside :data:`_SERVER_GRADED_TYPES`, and also when the item cannot be
    loaded. Failing open matters here: a learner who typed the right answer
    should not be marked wrong because a lookup failed, and the alternative
    (rejecting the attempt) loses their work entirely.
    """
    response = data.get('user_response') or {}
    typed = response.get('typed') if isinstance(response, dict) else None
    if typed is None:
        return None

    try:
        from services.supabase_factory import get_supabase_admin
        row = (
            get_supabase_admin()
            .table('exercises')
            .select('exercise_type, content, language_id')
            .eq('id', exercise_id)
            .limit(1)
            .execute()
        )
        item = (row.data or [None])[0]
    except Exception as exc:
        logger.warning("typed-grade lookup failed for %s: %s", exercise_id, exc)
        return None

    if not item or item.get('exercise_type') not in _SERVER_GRADED_TYPES:
        return None

    from services.vocabulary_ladder.deterministic.cloze_typed import grade
    return grade(
        item.get('content') or {},
        typed,
        data.get('language_id') or item.get('language_id'),
    )


# ---------------------------------------------------------------------------
# GET /api/practice/speed-round
# ---------------------------------------------------------------------------

@practice_bp.route('/speed-round', methods=['GET'])
@supabase_jwt_required
def get_speed_round() -> ApiResponse:
    """Return a timed fluency battery over the learner's mastered words.

    Query params:
        language_id      : required (int)
        size             : optional battery size (10..20; default 20)
        seconds_per_item : optional per-item clock (3..30; default 8)

    An empty battery is a 200 with ``no_content_reason``, not an error: "you
    have not mastered enough words yet" is a normal state for most learners
    and the FE renders it as a nudge rather than a failure.
    """
    try:
        language_id = request.args.get('language_id', type=int)
        if not language_id:
            return bad_request("language_id required")

        from services.vocabulary_ladder.speed_round import (
            DEFAULT_SECONDS_PER_ITEM, MAX_BATTERY, get_speed_round_composer,
        )

        battery = get_speed_round_composer().compose(
            user_id=g.current_user_id,
            language_id=int(language_id),
            size=request.args.get('size', MAX_BATTERY, type=int),
            seconds_per_item=request.args.get(
                'seconds_per_item', DEFAULT_SECONDS_PER_ITEM, type=int,
            ),
        )
        return api_success(battery.to_payload())

    except Exception as e:
        logger.error("Error composing speed round: %s", e)
        return server_error("Failed to compose speed round")
