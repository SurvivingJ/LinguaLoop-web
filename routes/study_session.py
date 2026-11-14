# routes/study_session.py
"""Daily Study Session — composition API for the single-page session runner.

The runner (templates/study_session.html + static/js/session/*) needs ONE
ordered queue that mixes comprehension-test slots with practice blocks, plus a
server-authoritative completion flag per item so it can resume where the user
left off.

Endpoints (all require auth):
  GET  /api/study-session?language_id=L
       → { load_date, language_id, study_plan_enabled, progress, next_index,
           queue: [ {kind:'test', ...} | {kind:'practice', ...}
                  | {kind:'flashcards', ...} | {kind:'dual_translation', ...} ] }
       Tests come from test_service.get_or_create_daily_load (which already
       routes through build_daily_session when STUDY_PLAN_ENABLED + a plan
       exists, else legacy). Practice blocks and the TASK-714 surface blocks
       come from daily_test_loads.daily_session_targets; per-block completion
       from daily_test_loads.completed_blocks.

  POST /api/study-session/complete-block
       Body: { language_id, block_id }   block_id ∈ chunked practice ids
         (practice_acq_1, practice_acq_2, practice_maint_1, …; TASK-703) or
         surface ids (flashcards_1, dual_translation_1, …; TASK-714)
       → marks the block done for today (idempotent append to
         completed_blocks) and, for surface blocks, credits the weekly counter
         via record_session_progress. Test slots use the existing
         POST /api/tests/daily-load/complete instead.

"Today" is the learner's LOCAL date throughout (ADR-022 / TASK-716) — see
services.day_boundary, the single shared derivation this module and
services.test_service both call.

The queue composition lives in services.study_session.queue and the reads and
writes in services.study_session.session; this module parses the request,
calls them and shapes the response. See [[features/study-plans.tech]].
"""

from __future__ import annotations

import logging

from flask import Blueprint, g, request

from middleware.auth import jwt_required as supabase_jwt_required
from routes.common import get_db
from services import study_plan_service as _plan  # noqa: F401  (patched by tests)
from services.day_boundary import plan_today_iso
from services.study_session import session as _session
from services.study_session.queue import (  # noqa: F401  (re-exported: earlier import path)
    SURFACE_BLOCKS as _SURFACE_BLOCKS,
    _FLASHCARD_CARDS_PER_BLOCK,
    _PRACTICE_CHUNK_MAX_MIN,
    _build_tail_queue,
    _chunk_minutes,
    _is_main_complete,
    _tail_offer_max_min,
    apply_prestudy,
    build_practice_chunks as _build_practice_chunks,
    build_session_queue,
    build_surface_items as _build_surface_items,
    compute_governor_and_tail,
    next_incomplete_index as _next_incomplete_index,
    prestudy_block_id,
    surface_skill_for as _surface_skill_for,
    tail_window_ids as _tail_window_ids,
    today_prestudy_ids as _today_prestudy_ids,
    valid_block_ids as _valid_block_ids,
)
from services.study_session.session import minutes_per_new_word as _mpnw
from services.test_service import get_test_service, parse_language_id
from utils.responses import (
    api_errors, ApiResponse, api_success, bad_request, not_found,
)
from utils.validation import json_body

logger = logging.getLogger(__name__)
study_session_bp = Blueprint("study_session", __name__)


def _today_iso(db, user_id: str, language_id: int) -> str:
    """Today's date for THIS learner (ADR-022 / TASK-716).

    Delegates to the one shared helper in services.day_boundary so this route
    and services.test_service can never disagree about what "today" is inside
    a single request. An unset or invalid plan timezone fails safe to UTC
    inside the helper; this function does not raise.
    """
    return plan_today_iso(db, user_id, language_id)


def _practice_service():
    """The process-wide practice session service (lazy: keeps imports light)."""
    from services.practice_session_service import get_practice_session_service
    return get_practice_session_service()


# ---------------------------------------------------------------------------
# GET /api/study-session?language_id=L
# ---------------------------------------------------------------------------

@study_session_bp.route('', methods=['GET'])
@supabase_jwt_required
@api_errors("Failed to build study session")
def get_study_session() -> ApiResponse:
    """Return today's ordered session queue (tests + practice) with progress."""
    language_id = parse_language_id(request.args.get('language_id'))
    if not language_id:
        return bad_request("Invalid or missing language_id")

    user_id = g.current_user_id
    db = get_db()
    return api_success(_session.build_study_session(
        db, user_id, language_id, _today_iso(db, user_id, language_id),
        test_service=get_test_service(),
        practice_service=_practice_service(),
        mpnw=lambda: _mpnw(db, language_id),
    ))


# ---------------------------------------------------------------------------
# POST /api/study-session/complete-block
# ---------------------------------------------------------------------------

@study_session_bp.route('/complete-block', methods=['POST'])
@supabase_jwt_required
@api_errors("Failed to mark block complete")
def complete_block() -> ApiResponse:
    """Mark a non-test block complete for today (idempotent).

    Test slots are completed via POST /api/tests/daily-load/complete instead.
    """
    data = json_body(silent=True)
    language_id = parse_language_id(data.get('language_id'))
    if not language_id:
        return bad_request("Invalid or missing language_id")

    user_id = g.current_user_id
    db = get_db()
    try:
        blocks = _session.complete_block(
            db, user_id, language_id, _today_iso(db, user_id, language_id),
            data.get('block_id'),
        )
    except _session.NoDailyLoad as e:
        return not_found(str(e))
    except _session.InvalidBlockId as e:
        return bad_request(str(e))
    return api_success({'completed_blocks': blocks})
