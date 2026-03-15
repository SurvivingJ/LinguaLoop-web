# routes/exercises.py
"""Exercise practice routes — browse, attempt, and track exercises."""

from flask import Blueprint, request, jsonify, g
from datetime import datetime, timezone
import logging

from middleware.auth import jwt_required as supabase_jwt_required

logger = logging.getLogger(__name__)
exercises_bp = Blueprint("exercises", __name__)


@exercises_bp.route('/', methods=['GET'])
@supabase_jwt_required
def get_exercises():
    """
    List exercises with optional filters.

    Query params:
        language_id:   required (int)
        exercise_type: optional — e.g. cloze_completion, tl_nl_translation
        source_type:   optional — grammar, vocabulary, collocation
        cefr_level:    optional — A1..C2
        limit:         optional (int, default 20, max 100)
        offset:        optional (int, default 0)
    """
    try:
        language_id = request.args.get('language_id', type=int)
        if not language_id:
            return jsonify({"error": "language_id required"}), 400

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

        # Batch-fetch definitions for vocabulary exercises missing word_definition.
        # Try word_sense_id first, fall back to tags.source_id for older exercises.
        sense_ids = []
        for ex in exercises:
            if not isinstance(ex.get('content'), dict) or ex['content'].get('word_definition'):
                continue
            ws_id = ex.get('word_sense_id')
            if not ws_id and ex.get('source_type') == 'vocabulary':
                ws_id = (ex.get('tags') or {}).get('source_id')
            if ws_id:
                sense_ids.append(int(ws_id))

        definitions = {}
        if sense_ids:
            unique_ids = list(set(sense_ids))
            sense_resp = db.table('dim_word_senses') \
                .select('id, definition') \
                .in_('id', unique_ids) \
                .execute()
            definitions = {
                row['id']: row['definition']
                for row in (sense_resp.data or [])
                if row.get('definition')
            }

        for ex in exercises:
            if isinstance(ex.get('content'), dict) and not ex['content'].get('word_definition'):
                ws_id = ex.get('word_sense_id')
                if not ws_id and ex.get('source_type') == 'vocabulary':
                    ws_id = (ex.get('tags') or {}).get('source_id')
                if ws_id:
                    defn = definitions.get(int(ws_id))
                    if defn:
                        ex['content']['word_definition'] = defn

        return jsonify({
            "status": "success",
            "exercises": exercises,
            "count": len(exercises),
        })

    except Exception as e:
        logger.error(f"Error fetching exercises: {e}")
        return jsonify({"error": "Failed to fetch exercises"}), 500


@exercises_bp.route('/attempt', methods=['POST'])
@supabase_jwt_required
def submit_attempt():
    """
    Record an exercise attempt.

    Body:
        exercise_id:   UUID string (required)
        user_response: dict (required)
        is_correct:    bool (required)
        time_taken_ms: int (optional)
    """
    try:
        current_user_id = g.supabase_claims.get('sub')
        if not current_user_id:
            return jsonify({"error": "User authentication failed"}), 401

        data = request.get_json()
        if not data or 'exercise_id' not in data:
            return jsonify({"error": "exercise_id required"}), 400

        exercise_id = data['exercise_id']
        is_correct = bool(data.get('is_correct', False))

        from services.supabase_factory import get_supabase_admin
        db = get_supabase_admin()

        # Insert attempt
        db.table('exercise_attempts').insert({
            'user_id': current_user_id,
            'exercise_id': exercise_id,
            'user_response': data.get('user_response', {}),
            'is_correct': is_correct,
            'time_taken_ms': data.get('time_taken_ms'),
            'created_at': datetime.now(timezone.utc).isoformat(),
        }).execute()

        # Update exercise counters
        exercise = db.table('exercises') \
            .select('attempt_count, correct_count') \
            .eq('id', exercise_id).single().execute().data

        if exercise:
            updates = {'attempt_count': (exercise.get('attempt_count') or 0) + 1}
            if is_correct:
                updates['correct_count'] = (exercise.get('correct_count') or 0) + 1
            db.table('exercises').update(updates).eq('id', exercise_id).execute()

        return jsonify({"status": "success"})

    except Exception as e:
        logger.error(f"Error submitting exercise attempt: {e}")
        return jsonify({"error": "Failed to submit attempt"}), 500


@exercises_bp.route('/types', methods=['GET'])
@supabase_jwt_required
def get_exercise_types():
    """
    Get distinct exercise types available for a language.

    Query params:
        language_id: required (int)
    """
    try:
        language_id = request.args.get('language_id', type=int)
        if not language_id:
            return jsonify({"error": "language_id required"}), 400

        from services.supabase_factory import get_supabase_admin
        db = get_supabase_admin()

        response = db.table('exercises') \
            .select('exercise_type') \
            .eq('is_active', True) \
            .eq('language_id', language_id) \
            .execute()

        types = sorted(set(row['exercise_type'] for row in (response.data or [])))

        return jsonify({
            "status": "success",
            "types": types,
        })

    except Exception as e:
        logger.error(f"Error fetching exercise types: {e}")
        return jsonify({"error": "Failed to fetch exercise types"}), 500
