# routes/vocabulary.py
"""Vocabulary tracking routes — word quiz submission, knowledge stats."""

from flask import Blueprint, request, jsonify, current_app, g
import logging

from middleware.auth import jwt_required as supabase_jwt_required

logger = logging.getLogger(__name__)
vocabulary_bp = Blueprint("vocabulary", __name__)


@vocabulary_bp.route('/word-quiz', methods=['POST'])
@supabase_jwt_required
def submit_word_quiz():
    """
    Submit post-test word quiz results.

    Accepts:
        {
            "attempt_id": "uuid-or-null",
            "language_id": 1,
            "results": [
                {
                    "sense_id": 123,
                    "selected_answer": "printing; to print",
                    "correct_answer": "printing; to print",
                    "is_correct": true,
                    "response_time_ms": 2300
                }
            ]
        }

    Returns updated BKT state for each word.
    """
    try:
        current_user_id = g.supabase_claims.get('sub')
        if not current_user_id:
            return jsonify({"error": "User authentication failed"}), 401

        data = request.get_json() or {}
        results = data.get('results', [])
        language_id = data.get('language_id')
        attempt_id = data.get('attempt_id')

        if not results:
            return jsonify({"error": "No results provided"}), 400
        if not language_id:
            return jsonify({"error": "language_id required"}), 400

        from services.vocabulary.knowledge_service import VocabularyKnowledgeService
        knowledge_svc = VocabularyKnowledgeService()

        bkt_updates = knowledge_svc.record_word_quiz_results(
            user_id=current_user_id,
            attempt_id=attempt_id,
            results=results,
            language_id=language_id,
        )

        return jsonify({
            'status': 'success',
            'updates': bkt_updates,
        }), 200

    except Exception as e:
        current_app.logger.error(f"Word quiz submission error: {e}")
        return jsonify({"error": "Failed to submit word quiz"}), 500
