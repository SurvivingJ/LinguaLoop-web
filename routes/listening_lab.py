# routes/listening_lab.py
"""Listening Lab routes — speed-graded listening comprehension flow.

A learner plays the same passage at 0.75x -> 0.9x -> 1.0x -> 1.15x. After
each tier they take a 5-MCQ comprehension check; 4/5 unlocks the next tier.
Final tier completion writes a single test_attempts row (test_type =
listening_lab) and updates ELO. Token-economy integration is intentionally
deferred for this iteration.
"""

import logging
import traceback

from flask import Blueprint, request, g

from middleware.auth import jwt_required as supabase_jwt_required
from utils.responses import (
    ApiResponse, api_success, bad_request, not_found, server_error,
)
from services.listening_lab_service import get_listening_lab_service
from services.dimension_service import parse_language_id

logger = logging.getLogger(__name__)
listening_lab_bp = Blueprint("listening_lab", __name__)


# ============================================================================
# PASSAGE LISTING
# ============================================================================

@listening_lab_bp.route('/', methods=['GET'])
@supabase_jwt_required
def list_passages() -> ApiResponse:
    """List active Lab-enrolled passages.

    Query params: language_id (required), difficulty (optional), limit (optional)
    """
    try:
        language_id = parse_language_id(request.args.get('language_id'))
        if not language_id:
            return bad_request("language_id required")

        difficulty = request.args.get('difficulty', type=int)
        limit = request.args.get('limit', 50, type=int)

        service = get_listening_lab_service()
        passages = service.list_passages(language_id, difficulty=difficulty, limit=limit)

        return api_success({'passages': passages})

    except Exception as e:
        logger.error(f"Error listing listening lab passages: {e}")
        return server_error("Failed to fetch listening lab passages")


@listening_lab_bp.route('/recommended', methods=['GET'])
@supabase_jwt_required
def get_recommended() -> ApiResponse:
    """ELO-matched listening lab passage recommendations for the current user."""
    try:
        language_id = parse_language_id(request.args.get('language_id'))
        if not language_id:
            return bad_request("language_id required")

        service = get_listening_lab_service()
        passages = service.get_recommended(g.current_user_id, language_id)

        return api_success({'passages': passages})

    except Exception as e:
        logger.error(f"Error fetching listening lab recommendations: {e}")
        return server_error("Failed to fetch recommendations")


# ============================================================================
# PASSAGE DETAIL + SESSION RESUME
# ============================================================================

@listening_lab_bp.route('/<slug>', methods=['GET'])
@supabase_jwt_required
def get_passage(slug: str) -> ApiResponse:
    """Return passage metadata plus the user's open session (if any).

    The audio URLs and transcript come back here so the page can render the
    tier stepper immediately. Active question ids are NOT exposed here —
    they only come from start/submit RPC responses.
    """
    try:
        service = get_listening_lab_service()
        passage = service.get_passage_by_slug(slug)

        if not passage:
            return not_found(f"Listening lab passage not found: {slug}")

        active_session = service.get_active_session(g.current_user_id, passage['id'])

        return api_success({
            'passage': passage,
            'active_session': active_session,
        })

    except Exception as e:
        logger.error(f"Error fetching listening lab passage '{slug}': {e}")
        logger.error(traceback.format_exc())
        return server_error("Failed to fetch passage")


# ============================================================================
# SESSION LIFECYCLE
# ============================================================================

@listening_lab_bp.route('/<slug>/start', methods=['POST'])
@supabase_jwt_required
def start_session(slug: str) -> ApiResponse:
    """Start (or resume) a session for the passage referenced by `slug`."""
    try:
        service = get_listening_lab_service()
        passage = service.get_passage_by_slug(slug)
        if not passage:
            return not_found(f"Listening lab passage not found: {slug}")

        result = service.start_session(g.current_user_id, passage['id'])

        if not result.get('success'):
            return bad_request(result.get('error', 'Failed to start session'))

        return api_success(result)

    except Exception as e:
        logger.error(f"Error starting listening lab session for '{slug}': {e}")
        logger.error(traceback.format_exc())
        return server_error("Failed to start session")


@listening_lab_bp.route('/session/<sid>/tier/<int:tier>/submit', methods=['POST'])
@supabase_jwt_required
def submit_tier(sid: str, tier: int) -> ApiResponse:
    """Submit answers for the current tier of a session."""
    try:
        if tier < 0 or tier > 3:
            return bad_request("Tier must be between 0 and 3")

        data = request.get_json(silent=True) or {}
        responses = data.get('responses') or []
        idempotency_key = data.get('idempotency_key')

        if not responses:
            return bad_request("No responses provided")

        service = get_listening_lab_service()
        result = service.submit_tier(
            g.current_user_id, sid, tier, responses, idempotency_key=idempotency_key
        )

        if not result.get('success'):
            return bad_request(result.get('error', 'Submission failed'))

        # On final-tier success the RPC has already written a test_attempts row.
        # Feed BKT from the per-question results in the embedded ELO result.
        if result.get('completed'):
            _update_listening_lab_vocabulary(g.current_user_id, result)

        return api_success(result)

    except Exception as e:
        logger.error(f"Error submitting listening lab tier {tier} on session {sid}: {e}")
        logger.error(traceback.format_exc())
        return server_error("Failed to submit tier")


@listening_lab_bp.route('/session/<sid>/abandon', methods=['POST'])
@supabase_jwt_required
def abandon_session(sid: str) -> ApiResponse:
    """Mark a session abandoned. No refunds, no ELO."""
    try:
        service = get_listening_lab_service()
        ok = service.abandon_session(g.current_user_id, sid)

        if not ok:
            return bad_request("Session not found or already closed")

        return api_success({'abandoned': True})

    except Exception as e:
        logger.error(f"Error abandoning session {sid}: {e}")
        return server_error("Failed to abandon session")


# ============================================================================
# HELPERS
# ============================================================================

def _update_listening_lab_vocabulary(user_id: str, submit_result: dict) -> None:
    """Run BKT vocabulary tracking from the final ELO result's question_results.

    Mirrors the mystery pattern: best-effort, non-fatal. The 20 final responses
    are scored by process_test_submission and surfaced under
    `submit_result['elo_result']['question_results']`.
    """
    try:
        elo_result = submit_result.get('elo_result') or {}
        question_results = elo_result.get('question_results') or []
        if not question_results:
            return

        bkt_results = [
            {
                'question_id': str(qr['question_id']),
                'is_correct': qr.get('is_correct', False),
            }
            for qr in question_results
            if qr.get('question_id')
        ]
        if not bkt_results:
            return

        # Derive language_id: the ELO result doesn't include it, so we look up
        # the just-written test_attempts row by attempt_id.
        from services.supabase_factory import get_supabase_admin
        admin = get_supabase_admin()
        attempt_id = elo_result.get('attempt_id')
        if not attempt_id:
            return

        attempt_row = (
            admin.table('test_attempts')
            .select('language_id')
            .eq('id', attempt_id)
            .limit(1)
            .execute()
        )
        if not attempt_row.data:
            return
        language_id = attempt_row.data[0]['language_id']

        from services.vocabulary.knowledge_service import VocabularyKnowledgeService
        knowledge_svc = VocabularyKnowledgeService()
        knowledge_svc.update_from_comprehension(
            user_id=user_id, language_id=language_id, question_results=bkt_results,
        )
        logger.info(
            f"Listening Lab BKT: updated vocab from {len(bkt_results)} question results"
        )

    except Exception as e:
        logger.warning(f"Listening Lab BKT vocab update failed (non-fatal): {e}")
