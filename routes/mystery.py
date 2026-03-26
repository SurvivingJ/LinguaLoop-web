# routes/mystery.py
"""Mystery routes — browse, play, and complete murder mystery comprehension series."""

from flask import Blueprint, request, g
import logging
import traceback

from middleware.auth import jwt_required as supabase_jwt_required
from utils.responses import ApiResponse, api_success, bad_request, not_found, server_error
from services.mystery_service import get_mystery_service
from services.dimension_service import parse_language_id

logger = logging.getLogger(__name__)
mystery_bp = Blueprint("mystery", __name__)


# ============================================================================
# MYSTERY LISTING
# ============================================================================

@mystery_bp.route('/', methods=['GET'])
@supabase_jwt_required
def list_mysteries() -> ApiResponse:
    """List mysteries with optional filters.

    Query params: language_id (required), difficulty (optional), limit (optional)
    """
    try:
        language_id = parse_language_id(request.args.get('language_id'))
        if not language_id:
            return bad_request("language_id required")

        difficulty = request.args.get('difficulty', type=int)
        limit = request.args.get('limit', 50, type=int)

        service = get_mystery_service()
        mysteries = service.get_mysteries(language_id, difficulty=difficulty, limit=limit)

        return api_success({'mysteries': mysteries})

    except Exception as e:
        logger.error(f"Error listing mysteries: {e}")
        return server_error("Failed to fetch mysteries")


@mystery_bp.route('/recommended', methods=['GET'])
@supabase_jwt_required
def get_recommended() -> ApiResponse:
    """Get ELO-matched mysteries for the current user."""
    try:
        language_id = parse_language_id(request.args.get('language_id'))
        if not language_id:
            return bad_request("language_id required")

        service = get_mystery_service()
        mysteries = service.get_recommended_mysteries(g.current_user_id, language_id)

        return api_success({'mysteries': mysteries})

    except Exception as e:
        logger.error(f"Error fetching recommended mysteries: {e}")
        return server_error("Failed to fetch recommended mysteries")


# ============================================================================
# MYSTERY DETAIL & PROGRESS
# ============================================================================

@mystery_bp.route('/<slug>', methods=['GET'])
@supabase_jwt_required
def get_mystery(slug: str) -> ApiResponse:
    """Get mystery metadata + user progress (for resume support)."""
    try:
        service = get_mystery_service()
        mystery = service.get_mystery_by_slug(slug)

        if not mystery:
            return not_found(f"Mystery not found: {slug}")

        # Get or create progress
        mode = request.args.get('mode', 'reading')
        if mode not in ('reading', 'listening'):
            mode = 'reading'

        progress = service.get_or_create_progress(
            g.current_user_id, mystery['id'], mode
        )

        return api_success({
            'mystery': mystery,
            'progress': progress,
        })

    except Exception as e:
        logger.error(f"Error fetching mystery '{slug}': {e}")
        logger.error(traceback.format_exc())
        return server_error("Failed to fetch mystery")


# ============================================================================
# SCENE ACCESS
# ============================================================================

@mystery_bp.route('/<slug>/scene/<int:scene_number>', methods=['GET'])
@supabase_jwt_required
def get_scene(slug: str, scene_number: int) -> ApiResponse:
    """Get scene content + questions. Enforces progression (can't skip ahead)."""
    try:
        if scene_number < 1 or scene_number > 5:
            return bad_request("Scene number must be between 1 and 5")

        service = get_mystery_service()
        mystery = service.get_mystery_by_slug(slug)
        if not mystery:
            return not_found(f"Mystery not found: {slug}")

        # Check progress — can't access scenes beyond current
        progress = service.get_or_create_progress(
            g.current_user_id, mystery['id']
        )
        if scene_number > progress['current_scene']:
            return bad_request(
                f"Scene {scene_number} is locked. Complete scene {progress['current_scene']} first."
            )

        scene = service.get_scene(mystery['id'], scene_number)
        if not scene:
            return not_found(f"Scene {scene_number} not found")

        # For listening mode, check if transcript should be hidden
        mode = progress.get('mode', 'reading')
        scene_responses = progress.get('scene_responses', {})
        scene_completed = scene_responses.get(str(scene_number), {}).get('correct', False)

        # Hide transcript in listening mode if scene not yet completed
        if mode == 'listening' and not scene_completed:
            scene['transcript_locked'] = True
        else:
            scene['transcript_locked'] = False

        return api_success({
            'scene': scene,
            'progress': {
                'current_scene': progress['current_scene'],
                'mode': mode,
                'notebook_state': progress.get('notebook_state', {}),
            }
        })

    except Exception as e:
        logger.error(f"Error fetching scene {scene_number} for '{slug}': {e}")
        logger.error(traceback.format_exc())
        return server_error("Failed to fetch scene")


# ============================================================================
# SCENE SUBMISSION
# ============================================================================

@mystery_bp.route('/<slug>/scene/<int:scene_number>/submit', methods=['POST'])
@supabase_jwt_required
def submit_scene(slug: str, scene_number: int) -> ApiResponse:
    """Submit answers for a scene. Must retry until all correct to get clue."""
    try:
        data = request.get_json()
        if not data:
            return bad_request("Request body required")

        responses = data.get('responses', [])
        if not responses:
            return bad_request("No responses provided")

        service = get_mystery_service()
        mystery = service.get_mystery_by_slug(slug)
        if not mystery:
            return not_found(f"Mystery not found: {slug}")

        result = service.submit_scene(
            g.current_user_id, mystery['id'], scene_number, responses
        )

        if result.get('error'):
            return bad_request(result['error'])

        return api_success(result)

    except Exception as e:
        logger.error(f"Error submitting scene {scene_number} for '{slug}': {e}")
        logger.error(traceback.format_exc())
        return server_error("Failed to submit scene answers")


# ============================================================================
# FINALE SUBMISSION
# ============================================================================

@mystery_bp.route('/<slug>/submit', methods=['POST'])
@supabase_jwt_required
def submit_finale(slug: str) -> ApiResponse:
    """Submit the complete mystery (all 5 scenes). Triggers ELO + BKT."""
    try:
        data = request.get_json()
        if not data:
            return bad_request("Request body required")

        responses = data.get('responses', [])
        if not responses:
            return bad_request("No responses provided")

        service = get_mystery_service()
        mystery = service.get_mystery_by_slug(slug)
        if not mystery:
            return not_found(f"Mystery not found: {slug}")

        result = service.submit_finale(
            g.current_user_id, mystery['id'], responses
        )

        if not result.get('success'):
            error_msg = result.get('error', 'Submission failed')
            return bad_request(error_msg)

        # BKT vocabulary tracking
        _update_mystery_vocabulary(
            g.current_user_id, mystery['id'], mystery['language_id'], result
        )

        return api_success({'result': result})

    except Exception as e:
        logger.error(f"Error submitting mystery finale for '{slug}': {e}")
        logger.error(traceback.format_exc())
        return server_error("Failed to submit mystery")


# ============================================================================
# HELPERS
# ============================================================================

def _update_mystery_vocabulary(user_id, mystery_id, language_id, rpc_result):
    """Run BKT vocabulary tracking from mystery question results."""
    try:
        from services.vocabulary.knowledge_service import VocabularyKnowledgeService
        from services.supabase_factory import get_supabase_admin

        question_results = rpc_result.get('question_results', [])
        if not question_results:
            return

        bkt_results = [
            {'question_id': str(qr['question_id']), 'is_correct': qr.get('is_correct', False)}
            for qr in question_results
            if qr.get('question_id')
        ]

        if not bkt_results:
            return

        # Collect sense_ids from mystery questions
        admin = get_supabase_admin()
        all_sense_ids = set()

        scenes_res = admin.table('mystery_scenes').select('id')\
            .eq('mystery_id', str(mystery_id)).execute()

        for scene in (scenes_res.data or []):
            questions_res = admin.table('mystery_questions')\
                .select('sense_ids').eq('scene_id', scene['id']).execute()
            for q in (questions_res.data or []):
                if q.get('sense_ids'):
                    all_sense_ids.update(q['sense_ids'])

        if not all_sense_ids:
            logger.info("Mystery BKT: No sense_ids on questions")
            return

        knowledge_svc = VocabularyKnowledgeService()
        knowledge_svc.update_from_comprehension(
            user_id=user_id, language_id=language_id, question_results=bkt_results,
        )
        logger.info(f"Mystery BKT: Updated vocabulary for {len(all_sense_ids)} senses")

    except Exception as e:
        logger.warning(f"Mystery BKT vocabulary update failed (non-fatal): {e}")
