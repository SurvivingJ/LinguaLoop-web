# routes/vocab_dojo.py
"""Vocabulary Dojo routes — ladder sessions, attempts, and word preview."""

from flask import Blueprint, request, g
import logging

from middleware.auth import jwt_required as supabase_jwt_required
from utils.responses import ApiResponse, api_success, bad_request, server_error

logger = logging.getLogger(__name__)
vocab_dojo_bp = Blueprint("vocab_dojo", __name__)


@vocab_dojo_bp.route('/session', methods=['GET'])
@supabase_jwt_required
def get_dojo_session() -> ApiResponse:
    """Get a vocabulary dojo session via the get_ladder_session RPC.

    Query params:
        language_id: required
        count: optional (default 20)
    """
    try:
        language_id = request.args.get('language_id', type=int)
        if not language_id:
            return bad_request("language_id required")

        count = min(request.args.get('count', 20, type=int), 50)

        from services.supabase_factory import get_supabase_admin
        db = get_supabase_admin()

        resp = db.rpc('get_ladder_session', {
            'p_user_id': g.current_user_id,
            'p_language_id': language_id,
            'p_count': count,
        }).execute()

        exercises = resp.data or []

        # Prepare jumbled sentence content at serve time
        from services.exercise_generation.language_processor import prepare_jumbled_content
        from services.vocabulary_ladder.config import LADDER_LEVELS
        for ex in exercises:
            level = ex.get('out_ladder_level')
            if level and level in LADDER_LEVELS:
                ex['ladder_name'] = LADDER_LEVELS[level]['name']
                ex['family'] = LADDER_LEVELS[level].get('family', '')

            content = ex.get('out_content')
            if (ex.get('out_exercise_type') == 'jumbled_sentence'
                    and isinstance(content, dict)
                    and 'chunks' not in content):
                try:
                    ex['out_content'] = prepare_jumbled_content(content, language_id)
                except Exception as e:
                    logger.error("Failed to prepare jumbled content: %s", e)

        return api_success({
            'exercises': exercises,
            'count': len(exercises),
        })

    except Exception as e:
        logger.error("Error building dojo session: %s", e)
        return server_error("Failed to build vocabulary session")


@vocab_dojo_bp.route('/attempt', methods=['POST'])
@supabase_jwt_required
def submit_dojo_attempt() -> ApiResponse:
    """Submit a vocabulary ladder exercise attempt.

    Body:
        exercise_id: required
        sense_id: required
        is_correct: required (bool)
        is_first_attempt: required (bool)
        time_taken_ms: optional (int)
        language_id: optional (int)
    """
    try:
        data = request.get_json()
        if not data:
            return bad_request("Request body required")

        exercise_id = data.get('exercise_id')
        sense_id = data.get('sense_id')
        is_correct = data.get('is_correct')

        if not exercise_id or sense_id is None or is_correct is None:
            return bad_request("exercise_id, sense_id, and is_correct required")

        from services.vocabulary_ladder.ladder_service import LadderService
        service = LadderService()

        result = service.record_attempt(
            user_id=g.current_user_id,
            sense_id=int(sense_id),
            exercise_id=str(exercise_id),
            is_correct=bool(is_correct),
            is_first_attempt=bool(data.get('is_first_attempt', True)),
            time_taken_ms=data.get('time_taken_ms'),
            language_id=data.get('language_id'),
            exercise_type=data.get('exercise_type'),
            ladder_level=data.get('ladder_level'),
            exercise_context=data.get('exercise_context', 'standard'),
        )

        return api_success(result)

    except Exception as e:
        logger.error("Error submitting dojo attempt: %s", e)
        return server_error("Failed to submit attempt")


@vocab_dojo_bp.route('/word/<int:sense_id>/exercises', methods=['GET'])
@supabase_jwt_required
def get_word_exercises(sense_id: int) -> ApiResponse:
    """Get all ladder exercises for a specific word sense.

    Query params:
        language_id: required
    """
    try:
        language_id = request.args.get('language_id', type=int)
        if not language_id:
            return bad_request("language_id required")

        from services.supabase_factory import get_supabase_admin
        db = get_supabase_admin()

        # Fetch all ladder exercises for this sense
        resp = (
            db.table('exercises')
            .select('id, exercise_type, content, complexity_tier, ladder_level')
            .eq('word_sense_id', sense_id)
            .eq('language_id', language_id)
            .eq('is_active', True)
            .not_.is_('ladder_level', 'null')
            .order('ladder_level')
            .execute()
        )
        exercises = resp.data or []

        # Fetch word metadata
        sense_resp = (
            db.table('dim_word_senses')
            .select('id, definition, pronunciation, ipa_pronunciation, '
                    'morphological_forms, dim_vocabulary(lemma, semantic_class, '
                    'part_of_speech)')
            .eq('id', sense_id)
            .single()
            .execute()
        )
        sense_data = sense_resp.data or {}
        vocab = sense_data.get('dim_vocabulary') or {}

        # Fetch word assets
        assets_resp = (
            db.table('word_assets')
            .select('asset_type, content, model_used, is_valid, created_at')
            .eq('sense_id', sense_id)
            .execute()
        )
        assets = assets_resp.data or []

        # Prepare jumbled sentence content
        from services.exercise_generation.language_processor import prepare_jumbled_content
        for ex in exercises:
            if (ex.get('exercise_type') == 'jumbled_sentence'
                    and isinstance(ex.get('content'), dict)
                    and 'chunks' not in ex['content']):
                try:
                    ex['content'] = prepare_jumbled_content(ex['content'], language_id)
                except Exception:
                    pass

        from services.vocabulary_ladder.config import LADDER_LEVELS
        for ex in exercises:
            level = ex.get('ladder_level')
            if level and level in LADDER_LEVELS:
                ex['ladder_name'] = LADDER_LEVELS[level]['name']

        return api_success({
            'word': {
                'sense_id': sense_id,
                'lemma': vocab.get('lemma', ''),
                'pos': vocab.get('part_of_speech', ''),
                'semantic_class': vocab.get('semantic_class', ''),
                'definition': sense_data.get('definition', ''),
                'pronunciation': sense_data.get('pronunciation', ''),
                'ipa': sense_data.get('ipa_pronunciation', ''),
                'morphological_forms': sense_data.get('morphological_forms'),
            },
            'exercises': exercises,
            'assets': assets,
        })

    except Exception as e:
        logger.error("Error fetching word exercises for sense %s: %s", sense_id, e)
        return server_error("Failed to fetch word exercises")


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
        data = request.get_json()
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

        return api_success({
            'gate_name': gate_name,
            'exercises': exercises,
            'battery_size': len(exercises),
        })

    except Exception as e:
        logger.error("Error assembling gate: %s", e)
        return server_error("Failed to assemble gate")


@vocab_dojo_bp.route('/gate/result', methods=['POST'])
@supabase_jwt_required
def submit_gate_result() -> ApiResponse:
    """Submit the result of a gate battery.

    Body:
        sense_id: required (int)
        gate_name: required ('gate_a' or 'gate_b')
        passed: required (bool) — caller computes pass/fail from battery results
    """
    try:
        data = request.get_json()
        if not data:
            return bad_request("Request body required")

        sense_id = data.get('sense_id')
        gate_name = data.get('gate_name')
        passed = data.get('passed')

        if sense_id is None or not gate_name or passed is None:
            return bad_request("sense_id, gate_name, and passed required")

        from services.vocabulary_ladder.ladder_service import LadderService
        service = LadderService()

        if passed:
            result = service.pass_gate(g.current_user_id, int(sense_id), gate_name)
        else:
            result = {'gate': gate_name, 'passed': False, 'word_state': 'active'}

        return api_success(result)

    except Exception as e:
        logger.error("Error submitting gate result: %s", e)
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
        data = request.get_json()
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

        return api_success({
            'exercises': exercises,
            'battery_size': len(exercises),
        })

    except Exception as e:
        logger.error("Error assembling stress test: %s", e)
        return server_error("Failed to assemble stress test")


@vocab_dojo_bp.route('/stress-test/result', methods=['POST'])
@supabase_jwt_required
def submit_stress_test_result() -> ApiResponse:
    """Submit the result of a stress test battery.

    Body:
        sense_id: required (int)
        language_id: required (int)
        score: required (float, 0.0-1.0, e.g. 6/8 = 0.75)
        passed: required (bool) — caller computes pass/fail
    """
    try:
        data = request.get_json()
        if not data:
            return bad_request("Request body required")

        sense_id = data.get('sense_id')
        language_id = data.get('language_id')
        score = data.get('score')
        passed = data.get('passed')

        if sense_id is None or not language_id or score is None or passed is None:
            return bad_request("sense_id, language_id, score, and passed required")

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

        return api_success(result)

    except Exception as e:
        logger.error("Error submitting stress test result: %s", e)
        return server_error("Failed to submit stress test result")
