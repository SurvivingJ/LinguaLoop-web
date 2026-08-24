# routes/vocab_dojo.py
"""Vocabulary Dojo routes — ladder sessions, attempts, and word preview."""

from flask import Blueprint, request, g, redirect
import logging

from middleware.auth import jwt_required as supabase_jwt_required
from utils.responses import ApiResponse, api_success, bad_request, server_error

logger = logging.getLogger(__name__)
vocab_dojo_bp = Blueprint("vocab_dojo", __name__)


@vocab_dojo_bp.route('/session', methods=['GET'])
@supabase_jwt_required
def dojo_session_redirect():
    """DEPRECATED (TASK-220) — 302 to the canonical Practice surface.

    The standalone Vocab Dojo page was retired; word-acquisition sessions are
    now served by the merged Practice Engine (/api/practice/session) in
    `acquisition` mode. This redirect is kept only so bookmarked / straggler
    callers land on the canonical endpoint. Ladder lazy-init (formerly done
    here) is handled inside the Practice Engine's acquisition path.
    """
    language_id = request.args.get('language_id', '')
    return redirect(
        f"/api/practice/session?mode=acquisition&language_id={language_id}",
        code=302,
    )


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
        data = request.get_json(silent=True) or {}
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
        logger.error("Error submitting dojo attempt: %s", e, exc_info=True)
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

        # TASK-517 — sense-subscription top-up. A learner has opened a word's
        # ladder and there is nothing to show: that is the one moment we know
        # for certain a sense needs generating, and the one the nightly
        # coverage sweep cannot infer, because the sweep only looks at senses
        # that already have assets to find gaps *in*.
        #
        # Deliberately gated on "no exercises at all" rather than on the
        # coverage view. A partial gap is the sweep's job; running the view on
        # every word open would add a query per request to serve a case that is
        # already handled within 24 hours. `enqueue` is a no-op when the sense
        # is already queued, so a learner refreshing does not pile up rows.
        if not exercises:
            try:
                from services.vocabulary_ladder import queue_drain
                queue_drain.enqueue(
                    db, sense_id, language_id,
                    queue_drain.REASON_SUBSCRIBE_TOPUP,
                    {'trigger': 'word_exercises', 'user_visible': True},
                )
            except Exception as exc:
                # Never fail the read because the top-up could not be queued.
                logger.warning("subscribe_topup enqueue failed for sense %s: %s",
                               sense_id, exc)

        # Fetch word metadata
        sense_resp = (
            db.table('dim_word_senses')
            .select('id, vocab_id, definition, pronunciation, ipa_pronunciation, '
                    'morphological_forms, sense_rank, definition_level, '
                    'dim_vocabulary(lemma, semantic_class, part_of_speech, language_id)')
            .eq('id', sense_id)
            .single()
            .execute()
        )
        sense_data = sense_resp.data or {}
        vocab = sense_data.get('dim_vocabulary') or {}

        # Swap in the learner's preferred-language gloss, if they've set one
        # (users.native_language_id) and one exists for this word.
        from services.vocabulary.gloss_lookup import (
            apply_definition_language_preference, get_user_definition_language_id,
        )
        gloss_row = {
            'vocab_id': sense_data.get('vocab_id'),
            'sense_rank': sense_data.get('sense_rank'),
            'definition_level': sense_data.get('definition_level'),
            'definition': sense_data.get('definition', ''),
            'language_id': vocab.get('language_id'),
        }
        preferred_lang_id = get_user_definition_language_id(db, g.current_user_id)
        apply_definition_language_preference(db, [gloss_row], preferred_lang_id)
        sense_data['definition'] = gloss_row['definition']

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
                'definition_language_id': gloss_row['definition_language_id'],
                'definition_is_gloss': gloss_row['definition_is_gloss'],
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

        return api_success({
            'gate_name': gate_name,
            'exercises': exercises,
            'battery_size': len(exercises),
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
        passed: required (bool) — caller computes pass/fail from battery results
    """
    try:
        data = request.get_json(silent=True) or {}
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

        return api_success({
            'exercises': exercises,
            'battery_size': len(exercises),
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
        score: required (float, 0.0-1.0, e.g. 6/8 = 0.75)
        passed: required (bool) — caller computes pass/fail
    """
    try:
        data = request.get_json(silent=True) or {}
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
        logger.error("Error submitting stress test result: %s", e, exc_info=True)
        return server_error("Failed to submit stress test result")
