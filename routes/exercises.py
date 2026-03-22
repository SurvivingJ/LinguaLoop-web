# routes/exercises.py
"""Exercise practice routes — browse, attempt, and track exercises."""

from flask import Blueprint, request, g
from datetime import datetime, timezone
import logging

from middleware.auth import jwt_required as supabase_jwt_required
from utils.responses import ApiResponse, api_success, bad_request, server_error

logger = logging.getLogger(__name__)
exercises_bp = Blueprint("exercises", __name__)


@exercises_bp.route('/', methods=['GET'])
@supabase_jwt_required
def get_exercises() -> ApiResponse:
    """List exercises with optional filters.

    Query params:
        language_id, exercise_type, source_type, cefr_level, limit, offset
    """
    try:
        language_id = request.args.get('language_id', type=int)
        if not language_id:
            return bad_request("language_id required")

        exercise_type = request.args.get('exercise_type')
        source_type = request.args.get('source_type')
        cefr_level = request.args.get('cefr_level')
        limit = min(request.args.get('limit', 20, type=int), 100)
        offset = request.args.get('offset', 0, type=int)

        from services.supabase_factory import get_supabase_admin
        db = get_supabase_admin()

        query = db.table('exercises') \
            .select('id, exercise_type, source_type, content, difficulty_static, '
                    'cefr_level, tags, attempt_count, correct_count, word_sense_id') \
            .eq('is_active', True) \
            .eq('language_id', language_id)

        if exercise_type:
            query = query.eq('exercise_type', exercise_type)
        if source_type:
            query = query.eq('source_type', source_type)
        if cefr_level:
            query = query.eq('cefr_level', cefr_level)

        query = query.order('created_at', desc=True) \
            .range(offset, offset + limit - 1)

        response = query.execute()
        exercises = response.data or []

        # Batch-fetch definitions and lemmas for vocabulary exercises
        sense_ids = []
        for ex in exercises:
            if not isinstance(ex.get('content'), dict):
                continue
            if ex['content'].get('word_definition') and ex['content'].get('target_word'):
                continue
            ws_id = ex.get('word_sense_id')
            if not ws_id and ex.get('source_type') == 'vocabulary':
                ws_id = (ex.get('tags') or {}).get('source_id')
            if ws_id:
                sense_ids.append(int(ws_id))

        sense_lookup = {}
        if sense_ids:
            unique_ids = list(set(sense_ids))
            sense_resp = db.table('dim_word_senses') \
                .select('id, definition, dim_vocabulary(lemma)') \
                .in_('id', unique_ids) \
                .execute()
            sense_lookup = {row['id']: row for row in (sense_resp.data or [])}

        for ex in exercises:
            if not isinstance(ex.get('content'), dict):
                continue
            ws_id = ex.get('word_sense_id')
            if not ws_id and ex.get('source_type') == 'vocabulary':
                ws_id = (ex.get('tags') or {}).get('source_id')
            if ws_id:
                row = sense_lookup.get(int(ws_id))
                if row:
                    if not ex['content'].get('word_definition') and row.get('definition'):
                        ex['content']['word_definition'] = row['definition']
                    if not ex['content'].get('target_word'):
                        vocab = row.get('dim_vocabulary') or {}
                        lemma = vocab.get('lemma', '')
                        if lemma:
                            ex['content']['target_word'] = lemma

        return api_success({"exercises": exercises, "count": len(exercises)})

    except Exception as e:
        logger.error(f"Error fetching exercises: {e}")
        return server_error("Failed to fetch exercises")


@exercises_bp.route('/session', methods=['GET'])
@supabase_jwt_required
def get_exercise_session() -> ApiResponse:
    """Get today's exercise session (computed or cached).

    Query params:
        language_id: required
    """
    try:
        language_id = request.args.get('language_id', type=int)
        if not language_id:
            return bad_request("language_id required")

        from services.exercise_session_service import get_exercise_session_service
        service = get_exercise_session_service()
        session = service.get_or_create_daily_session(g.current_user_id, language_id)
        return api_success({"session": session})

    except Exception as e:
        logger.error(f"Error fetching exercise session: {e}")
        return server_error("Failed to fetch exercise session")


@exercises_bp.route('/session/complete', methods=['POST'])
@supabase_jwt_required
def complete_session_exercise() -> ApiResponse:
    """Mark an exercise as completed in today's session.

    Body: exercise_id (required), language_id (required)
    """
    try:
        data = request.get_json()
        if not data or 'exercise_id' not in data or 'language_id' not in data:
            return bad_request("exercise_id and language_id required")

        from services.exercise_session_service import get_exercise_session_service
        service = get_exercise_session_service()
        result = service.mark_exercise_complete(
            g.current_user_id,
            data['language_id'],
            data['exercise_id'],
        )
        return api_success(result)

    except Exception as e:
        logger.error(f"Error completing session exercise: {e}")
        return server_error("Failed to mark exercise complete")


@exercises_bp.route('/attempt', methods=['POST'])
@supabase_jwt_required
def submit_attempt() -> ApiResponse:
    """Record an exercise attempt and trigger BKT + FSRS updates.

    Body: exercise_id (required), user_response, is_correct, time_taken_ms
    """
    try:
        current_user_id = g.current_user_id

        data = request.get_json()
        if not data or 'exercise_id' not in data:
            return bad_request("exercise_id required")

        from services.exercise_session_service import get_exercise_session_service
        service = get_exercise_session_service()
        result = service.record_attempt_with_updates(
            user_id=current_user_id,
            exercise_id=data['exercise_id'],
            is_correct=bool(data.get('is_correct', False)),
            user_response=data.get('user_response', {}),
            time_taken_ms=data.get('time_taken_ms'),
        )

        if result.get('error'):
            return server_error(result['error'])

        return api_success(result)

    except Exception as e:
        logger.error(f"Error submitting exercise attempt: {e}")
        return server_error("Failed to submit attempt")


@exercises_bp.route('/types', methods=['GET'])
@supabase_jwt_required
def get_exercise_types() -> ApiResponse:
    """Get distinct exercise types available for a language."""
    try:
        language_id = request.args.get('language_id', type=int)
        if not language_id:
            return bad_request("language_id required")

        from services.supabase_factory import get_supabase_admin
        db = get_supabase_admin()

        response = db.table('exercises') \
            .select('exercise_type') \
            .eq('is_active', True) \
            .eq('language_id', language_id) \
            .execute()

        types = sorted(set(row['exercise_type'] for row in (response.data or [])))

        return api_success({"types": types})

    except Exception as e:
        logger.error(f"Error fetching exercise types: {e}")
        return server_error("Failed to fetch exercise types")
