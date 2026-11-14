# routes/vocabulary.py
"""Vocabulary tracking routes — word quiz submission, knowledge stats."""

from flask import Blueprint, request, current_app, g
import logging
from uuid import UUID
from pydantic import ValidationError

from middleware.auth import jwt_required as supabase_jwt_required
from utils.responses import (
    ApiResponse, api_success, bad_request, not_found, server_error,
)
from models.requests import WordQuizRequest

logger = logging.getLogger(__name__)
vocabulary_bp = Blueprint("vocabulary", __name__)


def _attempt_belongs_to(attempt_id: str, user_id: str) -> bool:
    resp = (
        current_app.supabase_service.table('test_attempts')
        .select('id')
        .eq('id', attempt_id)
        .eq('user_id', user_id)
        .limit(1)
        .execute()
    )
    return bool(resp.data)


@vocabulary_bp.route('/word-quiz', methods=['POST'])
@supabase_jwt_required
def submit_word_quiz() -> ApiResponse:
    """Submit post-test word quiz results. Returns updated BKT state."""
    try:
        body = WordQuizRequest.model_validate(request.get_json() or {})
    except ValidationError as e:
        return bad_request(e.errors()[0]['msg'])

    try:
        current_user_id = g.current_user_id

        if body.attempt_id:
            try:
                attempt_id = str(UUID(body.attempt_id))
            except ValueError:
                return bad_request("attempt_id must be a valid id")
            if not _attempt_belongs_to(attempt_id, current_user_id):
                return not_found("Attempt not found")
            body.attempt_id = attempt_id

        from services.vocabulary.knowledge_service import VocabularyKnowledgeService
        knowledge_svc = VocabularyKnowledgeService()

        bkt_updates = knowledge_svc.record_word_quiz_results(
            user_id=current_user_id,
            attempt_id=body.attempt_id,
            results=[r.model_dump() for r in body.results],
            language_id=body.language_id,
        )

        return api_success({'updates': bkt_updates})

    except Exception as e:
        current_app.logger.error(f"Word quiz submission error: {e}")
        return server_error("Failed to submit word quiz")
