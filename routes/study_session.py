# routes/study_session.py
"""Daily Study Session — composition API for the single-page session runner.

The runner (templates/study_session.html + static/js/session/*) needs ONE
ordered queue that mixes comprehension-test slots with practice blocks, plus a
server-authoritative completion flag per item so it can resume where the user
left off.

Endpoints (all require auth):
  GET  /api/study-session?language_id=L
       → { load_date, language_id, study_plan_enabled, progress, next_index,
           queue: [ {kind:'test', ...} | {kind:'practice', ...} ] }
       Tests come from test_service.get_or_create_daily_load (which already
       routes through build_daily_session when STUDY_PLAN_ENABLED + a plan
       exists, else legacy). Practice blocks come from
       daily_test_loads.daily_session_targets; per-block completion from
       daily_test_loads.completed_blocks.

  POST /api/study-session/complete-block
       Body: { language_id, block_id }   block_id ∈ {practice_acq, practice_maint}
       → marks a practice block done for today (idempotent append to
         completed_blocks). Test slots use the existing
         POST /api/tests/daily-load/complete instead.

See [[features/study-plans.tech]] and the plan
C:\\Users\\James\\.claude\\plans\\we-now-have-the-swirling-haven.md.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List

from flask import Blueprint, g, request

from config import Config
from middleware.auth import jwt_required as supabase_jwt_required
from services.supabase_factory import get_supabase_admin
from services.test_service import get_test_service, parse_language_id
from utils.responses import (
    ApiResponse, api_success, bad_request, not_found, server_error,
)

logger = logging.getLogger(__name__)
study_session_bp = Blueprint("study_session", __name__)

# Practice block ids the runner understands. Mode is what /api/practice/session
# expects as its `mode` query param.
_PRACTICE_BLOCKS = {
    'practice_acq':   {'mode': 'acquisition', 'targets_key': 'practice_acquisition_min'},
    'practice_maint': {'mode': 'maintenance', 'targets_key': 'practice_maintenance_min'},
}


def _today_iso() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _next_incomplete_index(queue: List[Dict[str, Any]]) -> int:
    """Index of the first not-completed item, or len(queue) when all done."""
    for i, item in enumerate(queue):
        if not item.get('is_completed'):
            return i
    return len(queue)


# ---------------------------------------------------------------------------
# GET /api/study-session?language_id=L
# ---------------------------------------------------------------------------

@study_session_bp.route('', methods=['GET'])
@supabase_jwt_required
def get_study_session() -> ApiResponse:
    """Return today's ordered session queue (tests + practice) with progress."""
    try:
        language_id = parse_language_id(request.args.get('language_id'))
        if not language_id:
            return bad_request("Invalid or missing language_id")

        user_id = g.current_user_id

        # 1. Tests — reuse the existing resolver/enrichment (handles Study Plan
        #    vs legacy routing internally, persists daily_test_loads).
        daily_load = get_test_service().get_or_create_daily_load(user_id, language_id)
        tests = daily_load.get('tests', []) or []

        # 2. Practice targets + per-block completion from the persisted row.
        db = get_supabase_admin()
        row = (
            db.table('daily_test_loads')
            .select('daily_session_targets, completed_blocks')
            .eq('user_id', user_id)
            .eq('language_id', language_id)
            .eq('load_date', _today_iso())
            .limit(1)
            .execute()
        )
        targets = (row.data[0].get('daily_session_targets') or {}) if row.data else {}
        completed_blocks = (row.data[0].get('completed_blocks') or []) if row.data else []

        # 3. Build the ordered queue: tests first, then practice blocks.
        queue: List[Dict[str, Any]] = []
        for t in tests:
            queue.append({
                'kind':         'test',
                'id':           t.get('id'),
                'slug':         t.get('slug'),
                'test_type':    t.get('test_type', 'listening'),
                'title':        t.get('title'),
                'elo_rating':   t.get('elo_rating'),
                'slot_type':    t.get('slot_type', 'new'),
                'is_completed': bool(t.get('is_completed')),
            })

        for block_id, meta in _PRACTICE_BLOCKS.items():
            minutes = int(targets.get(meta['targets_key']) or 0)
            if minutes <= 0:
                continue
            queue.append({
                'kind':         'practice',
                'id':           block_id,
                'mode':         meta['mode'],
                'minutes':      minutes,
                'is_completed': block_id in completed_blocks,
            })

        total = len(queue)
        completed = sum(1 for q in queue if q['is_completed'])

        return api_success({
            'load_date':          daily_load.get('load_date', _today_iso()),
            'language_id':        language_id,
            'study_plan_enabled': bool(Config.STUDY_PLAN_ENABLED),
            'queue':              queue,
            'progress':           {'completed': completed, 'total': total},
            'next_index':         _next_incomplete_index(queue),
        })

    except Exception as e:
        logger.error("get_study_session failed: %s", e)
        return server_error("Failed to build study session")


# ---------------------------------------------------------------------------
# POST /api/study-session/complete-block
# ---------------------------------------------------------------------------

@study_session_bp.route('/complete-block', methods=['POST'])
@supabase_jwt_required
def complete_block() -> ApiResponse:
    """Mark a practice block complete for today (idempotent).

    Test slots are completed via POST /api/tests/daily-load/complete; this is
    only for the non-test practice blocks.
    """
    try:
        data = request.get_json(silent=True) or {}
        language_id = parse_language_id(data.get('language_id'))
        block_id = data.get('block_id')

        if not language_id:
            return bad_request("Invalid or missing language_id")
        if block_id not in _PRACTICE_BLOCKS:
            return bad_request(
                f"block_id must be one of {sorted(_PRACTICE_BLOCKS)}"
            )

        user_id = g.current_user_id
        db = get_supabase_admin()

        row = (
            db.table('daily_test_loads')
            .select('id, completed_blocks')
            .eq('user_id', user_id)
            .eq('language_id', language_id)
            .eq('load_date', _today_iso())
            .limit(1)
            .execute()
        )
        if not row.data:
            return not_found("No daily load for today")

        blocks = row.data[0].get('completed_blocks') or []
        if block_id not in blocks:
            blocks.append(block_id)
            db.table('daily_test_loads')\
                .update({'completed_blocks': blocks})\
                .eq('id', row.data[0]['id'])\
                .execute()

        return api_success({'completed_blocks': blocks})

    except Exception as e:
        logger.error("complete_block failed: %s", e)
        return server_error("Failed to mark block complete")
