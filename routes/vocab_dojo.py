# routes/vocab_dojo.py
"""Vocabulary Dojo routes — gate and stress-test batteries."""

from flask import Blueprint, request, g
import logging

from middleware.auth import jwt_required as supabase_jwt_required
from utils.responses import ApiResponse, api_success, bad_request, server_error

logger = logging.getLogger(__name__)
vocab_dojo_bp = Blueprint("vocab_dojo", __name__)


@vocab_dojo_bp.route('/gate', methods=['POST'])
@supabase_jwt_required
def start_gate() -> ApiResponse:
    """Assemble a threshold gate battery for a word.

    Body:
        sense_id: required (int)
        language_id: required (int)
        gate_name: required ('gate_a' or 'gate_b')
    """
    try:
        data = request.get_json(silent=True) or {}
        if not data:
            return bad_request("Request body required")

        sense_id = data.get('sense_id')
        language_id = data.get('language_id')
        gate_name = data.get('gate_name')

        if sense_id is None or not language_id or not gate_name:
            return bad_request("sense_id, language_id, and gate_name required")

        if gate_name not in ('gate_a', 'gate_b'):
            return bad_request("gate_name must be 'gate_a' or 'gate_b'")

        from services.vocabulary_ladder.ladder_service import LadderService
        service = LadderService()

        exercises = service.assemble_gate(
            g.current_user_id, int(sense_id), int(language_id), gate_name
        )

        from services.vocabulary_ladder import battery_token
        return api_success({
            'gate_name': gate_name,
            'exercises': exercises,
            'battery_size': len(exercises),
            'battery_token': battery_token.issue(
                g.current_user_id, 'gate', int(sense_id), gate_name,
                [ex.get('exercise_id') or ex.get('id') for ex in exercises],
            ),
        })

    except Exception as e:
        logger.error("Error assembling gate: %s", e, exc_info=True)
        return server_error("Failed to assemble gate")


@vocab_dojo_bp.route('/gate/result', methods=['POST'])
@supabase_jwt_required
def submit_gate_result() -> ApiResponse:
    """Submit the result of a gate battery.

    Body:
        sense_id: required (int)
        gate_name: required ('gate_a' or 'gate_b')
        battery_token: required — issued by POST /gate
        results: required — [{exercise_id, is_correct}] for the issued battery

    Pass/fail is derived server-side (GATES[gate_name]['pass_threshold']); a
    client-supplied ``passed`` flag is ignored (TASK-882 / S14).
    """
    try:
        data = request.get_json(silent=True) or {}
        if not data:
            return bad_request("Request body required")

        sense_id = data.get('sense_id')
        gate_name = data.get('gate_name')

        if sense_id is None or not gate_name:
            return bad_request("sense_id, gate_name, battery_token and results required")

        from services.vocabulary_ladder.config import GATES
        if gate_name not in GATES:
            return bad_request("gate_name must be 'gate_a' or 'gate_b'")

        from services.vocabulary_ladder import battery_token
        try:
            correct, size = battery_token.score(
                data.get('battery_token'), g.current_user_id, 'gate',
                int(sense_id), gate_name, data.get('results'),
            )
        except battery_token.BatteryError as e:
            return bad_request(str(e))
        except (TypeError, ValueError):
            return bad_request("Invalid battery submission")
        passed = size > 0 and correct >= min(GATES[gate_name]['pass_threshold'], size)

        from services.vocabulary_ladder.ladder_service import LadderService
        service = LadderService()

        if passed:
            result = service.pass_gate(g.current_user_id, int(sense_id), gate_name)
        else:
            result = {'gate': gate_name, 'passed': False, 'word_state': 'active'}
        result = dict(result or {})
        result.update({'correct': correct, 'battery_size': size})

        return api_success(result)

    except Exception as e:
        logger.error("Error submitting gate result: %s", e, exc_info=True)
        return server_error("Failed to submit gate result")


@vocab_dojo_bp.route('/stress-test', methods=['POST'])
@supabase_jwt_required
def start_stress_test() -> ApiResponse:
    """Assemble a stress test battery for a word approaching mastery.

    Body:
        sense_id: required (int)
        language_id: required (int)
    """
    try:
        data = request.get_json(silent=True) or {}
        if not data:
            return bad_request("Request body required")

        sense_id = data.get('sense_id')
        language_id = data.get('language_id')

        if sense_id is None or not language_id:
            return bad_request("sense_id and language_id required")

        from services.vocabulary_ladder.ladder_service import LadderService
        service = LadderService()

        exercises = service.assemble_stress_test(
            g.current_user_id, int(sense_id), int(language_id)
        )

        from services.vocabulary_ladder import battery_token
        return api_success({
            'exercises': exercises,
            'battery_size': len(exercises),
            'battery_token': battery_token.issue(
                g.current_user_id, 'stress', int(sense_id), None,
                [ex.get('exercise_id') or ex.get('id') for ex in exercises],
            ),
        })

    except Exception as e:
        logger.error("Error assembling stress test: %s", e, exc_info=True)
        return server_error("Failed to assemble stress test")


@vocab_dojo_bp.route('/stress-test/result', methods=['POST'])
@supabase_jwt_required
def submit_stress_test_result() -> ApiResponse:
    """Submit the result of a stress test battery.

    Body:
        sense_id: required (int)
        language_id: required (int)
        battery_token: required — issued by POST /stress-test
        results: required — [{exercise_id, is_correct}] for the issued battery

    Score and pass/fail are derived server-side (STRESS_TEST['pass_threshold']);
    client-supplied ``score`` / ``passed`` are ignored (TASK-882 / S14).
    """
    try:
        data = request.get_json(silent=True) or {}
        if not data:
            return bad_request("Request body required")

        sense_id = data.get('sense_id')
        language_id = data.get('language_id')

        if sense_id is None or not language_id:
            return bad_request("sense_id, language_id, battery_token and results required")

        from services.vocabulary_ladder import battery_token
        from services.vocabulary_ladder.config import STRESS_TEST
        try:
            correct, size = battery_token.score(
                data.get('battery_token'), g.current_user_id, 'stress',
                int(sense_id), None, data.get('results'),
            )
            language_id = int(language_id)
        except battery_token.BatteryError as e:
            return bad_request(str(e))
        except (TypeError, ValueError):
            return bad_request("Invalid battery submission")
        if size <= 0:
            return bad_request("empty battery")
        score = correct / size
        passed = correct >= min(STRESS_TEST['pass_threshold'], size)

        from services.vocabulary_ladder.ladder_service import LadderService
        service = LadderService()

        if passed:
            result = service.graduate(
                g.current_user_id, int(sense_id),
                float(score), int(language_id)
            )
        else:
            result = {
                'word_state': 'relearning',
                'stress_test_score': float(score),
                'passed': False,
            }
        result = dict(result or {})
        result.update({'correct': correct, 'battery_size': size})

        return api_success(result)

    except Exception as e:
        logger.error("Error submitting stress test result: %s", e, exc_info=True)
        return server_error("Failed to submit stress test result")
