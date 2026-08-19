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

See [[features/study-plans.tech]] and the plan
C:\\Users\\James\\.claude\\plans\\we-now-have-the-swirling-haven.md.
"""

from __future__ import annotations

import hashlib
import logging
import random
import uuid
from collections import OrderedDict, deque
from typing import Any, Dict, List

from flask import Blueprint, g, request

from config import Config
from middleware.auth import jwt_required as supabase_jwt_required
from services.day_boundary import plan_today_iso
from services.supabase_factory import get_supabase_admin
from services.test_service import get_test_service, parse_language_id
from utils.responses import (
    ApiResponse, api_success, bad_request, not_found, server_error,
)

logger = logging.getLogger(__name__)
study_session_bp = Blueprint("study_session", __name__)

# Base practice blocks the runner understands. Mode is what /api/practice/session
# expects as its `mode` query param; targets_key names the minute budget in
# daily_session_targets. Each base block is chunked into ≤_PRACTICE_CHUNK_MAX_MIN
# pieces (TASK-703) with ids `{base}_{n}` (e.g. practice_acq_1, practice_acq_2).
_PRACTICE_BLOCKS = {
    'practice_acq':   {'mode': 'acquisition', 'targets_key': 'practice_acquisition_min'},
    'practice_maint': {'mode': 'maintenance', 'targets_key': 'practice_maintenance_min'},
}

# Cap on a single practice chunk so practice lands as mid-session breathers
# rather than one monolithic block. The practice player takes `minutes` per
# chunk via /api/practice/session?minutes=.
_PRACTICE_CHUNK_MAX_MIN = 10

# ---------------------------------------------------------------------------
# Plannable non-test surfaces (TASK-714 / ADR-021).
#
# flashcards and dual_translation are NOT dim_test_types rows and never resolve
# to an ELO-rated `tests` row, so they cannot ride the `kind:'test'` path. They
# get their own queue kinds instead — the runner's player_registry dispatches on
# item.kind, so widening the union is cheaper and more honest than inventing
# type codes (ADR-021, "Harder / newly constrained").
#
# One budgeted slot == one queue item:
#   flashcards       -> one review block of _FLASHCARD_CARDS_PER_BLOCK cards
#   dual_translation -> one passage
# so weekly target_counts stays homogeneous with the test skills (a count of
# slots) and test_time_estimate stays homogeneous (minutes per slot).
#
# listening_lab and mystery are deliberately ABSENT and must stay that way —
# ADR-021 puts them outside the planner on purpose. tests/test_plannable_
# surfaces.py pins that so a later change cannot quietly pull them in.
_SURFACE_BLOCKS = {
    'flashcards': {
        'kind':        'flashcards',
        'complete_as': 'flashcards',     # record_session_progress p_skill
    },
    'dual_translation': {
        'kind':        'dual_translation',
        'complete_as': 'dual_translation',
    },
}

# Cards per flashcards block. Mirrors the minutes-per-slot seed for
# 'flashcards' in test_time_estimate (see migrations/task714_*.sql) — change
# one and you must change the other or the budget lies.
_FLASHCARD_CARDS_PER_BLOCK = 15

# TASK-533 — the timed speed round. Deliberately NOT a member of
# _SURFACE_BLOCKS: it is a bonus, not a planned surface.
#
# ADR-021 draws the planner's boundary, and a speed round sits outside it on
# every criterion. It teaches nothing new (mastered words only), it must not
# move family confidence, and it has no weekly target or test_time_estimate
# seed — so budgeting minutes for it would make the plan claim work it never
# scheduled. It is appended after the planned queue instead: the day's actual
# work first, fluency practice as an optional tail.
#
# Consequently its completion credits no weekly counter. _surface_skill_for
# returns None for this id, so _record_surface_progress no-ops on it, which is
# correct here rather than an oversight.
_SPEED_ROUND_BLOCK_ID = 'speed_round_1'
_SPEED_ROUND_KIND = 'speed_round'

# Namespace for the deterministic idempotency key we hand to
# record_session_progress for surface blocks. Surface completions have no
# test_attempts row and therefore no attempt uuid, but the RPC dedupes on
# p_attempt_id — deriving it from (user, language, date, block) makes a
# repeated complete-block POST a no-op instead of a double count.
_SURFACE_PROGRESS_NAMESPACE = uuid.UUID('6f0f1d4e-6b1a-4f6d-9a1e-7147000714aa')


def _today_iso(db, user_id: str, language_id: int) -> str:
    """Today's date for THIS learner (ADR-022 / TASK-716).

    Delegates to the one shared helper in services.day_boundary so this route
    and services.test_service can never disagree about what "today" is inside
    a single request. An unset or invalid plan timezone fails safe to UTC
    inside the helper; this function does not raise.
    """
    return plan_today_iso(db, user_id, language_id)


def _next_incomplete_index(queue: List[Dict[str, Any]]) -> int:
    """Index of the first not-completed item, or len(queue) when all done."""
    for i, item in enumerate(queue):
        if not item.get('is_completed'):
            return i
    return len(queue)


# ---------------------------------------------------------------------------
# Queue ordering (TASK-703) — pure helpers, unit-tested in
# tests/test_study_session_ordering.py. Kept out of the RPC: cheap to iterate
# in Python and easier to reason about / test here.
# ---------------------------------------------------------------------------

def _stable_seed(user_id: str, load_date: str) -> int:
    """Deterministic 32-bit seed per (user, load_date) so two GETs order alike."""
    digest = hashlib.sha256(f"{user_id}:{load_date}".encode("utf-8")).hexdigest()
    return int(digest[:8], 16)


def _chunk_minutes(total: int, max_chunk: int = _PRACTICE_CHUNK_MAX_MIN) -> List[int]:
    """Split a minute budget into chunks of at most `max_chunk` (25 -> [10,10,5])."""
    if total <= 0:
        return []
    chunks: List[int] = []
    remaining = total
    while remaining > 0:
        take = min(max_chunk, remaining)
        chunks.append(take)
        remaining -= take
    return chunks


def _build_practice_chunks(
    targets: Dict[str, Any], completed_blocks: List[str]
) -> List[Dict[str, Any]]:
    """Expand the two base practice blocks into ≤10-minute chunk items."""
    done = set(completed_blocks or [])
    chunks: List[Dict[str, Any]] = []
    for base_id, meta in _PRACTICE_BLOCKS.items():
        minutes = int(targets.get(meta['targets_key']) or 0)
        for n, chunk_min in enumerate(_chunk_minutes(minutes), start=1):
            block_id = f"{base_id}_{n}"
            chunks.append({
                'kind':         'practice',
                'id':           block_id,
                'mode':         meta['mode'],
                'minutes':      chunk_min,
                'is_completed': block_id in done,
            })
    return chunks


def _surface_counts(targets: Dict[str, Any]) -> Dict[str, int]:
    """Per-surface HYDRATED slot counts the resolver placed for today.

    build_daily_session writes `surface_counts` into daily_session_targets
    alongside the practice minutes (TASK-714). Missing key -> no surfaces, which
    is what every pre-TASK-714 row looks like, so old rows degrade to the
    previous behaviour rather than erroring.
    """
    raw = (targets or {}).get('surface_counts') or {}
    out: Dict[str, int] = {}
    for skill in _SURFACE_BLOCKS:
        try:
            n = int(raw.get(skill) or 0)
        except (TypeError, ValueError):
            n = 0
        if n > 0:
            out[skill] = n
    return out


def _build_surface_items(
    targets: Dict[str, Any], completed_blocks: List[str]
) -> List[Dict[str, Any]]:
    """Expand budgeted flashcards / dual_translation slots into queue items.

    Item ids follow the practice convention (`{skill}_{n}`) because they share
    the completion endpoint, POST /api/study-session/complete-block.
    """
    done = set(completed_blocks or [])
    items: List[Dict[str, Any]] = []
    for skill, count in _surface_counts(targets).items():
        meta = _SURFACE_BLOCKS[skill]
        for n in range(1, count + 1):
            block_id = f"{skill}_{n}"
            item: Dict[str, Any] = {
                'kind':         meta['kind'],
                'id':           block_id,
                'skill':        skill,
                'is_completed': block_id in done,
            }
            if skill == 'flashcards':
                item['cards'] = _FLASHCARD_CARDS_PER_BLOCK
            items.append(item)
    return items


def _valid_block_ids(targets: Dict[str, Any]) -> set:
    """Non-test block ids that are legitimately part of today's session.

    Covers practice chunks, the TASK-714 surface blocks and the TASK-533 speed
    round — everything POST /complete-block will accept.

    The speed round is accepted unconditionally rather than gated on the same
    availability check the GET uses. Re-running that check here would cost a
    second query to reject a completion for work the learner has, by the time
    they POST, already done — and a learner whose last mastered word lapsed
    mid-session would have their finished round rejected. Accepting it is
    harmless: it credits no weekly counter either way.
    """
    return (
        {c['id'] for c in _build_practice_chunks(targets, [])}
        | {i['id'] for i in _build_surface_items(targets, [])}
        | {_SPEED_ROUND_BLOCK_ID}
    )


def _round_robin_tests(
    tests: List[Dict[str, Any]], rng: random.Random
) -> List[Dict[str, Any]]:
    """Round-robin tests across test_type so no two same-type are adjacent while
    another type still has items. Within a type, resolver order is preserved.
    The seeded RNG only fixes which type leads — the interleave itself is
    structural, so determinism never depends on it."""
    groups: "OrderedDict[str, List[Dict[str, Any]]]" = OrderedDict()
    for t in tests:
        groups.setdefault(t.get('test_type', 'listening'), []).append(t)

    order = list(groups.keys())
    rng.shuffle(order)
    queues = {k: deque(groups[k]) for k in order}

    result: List[Dict[str, Any]] = []
    while any(queues[k] for k in order):
        for k in order:
            if queues[k]:
                result.append(queues[k].popleft())
    return result


def _interleave_practice(
    test_seq: List[Dict[str, Any]], practice_chunks: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Spread practice chunks across the test sequence at even fractional
    positions (P chunks -> roughly 1/(P+1), 2/(P+1), … of the way through) so
    practice appears mid-session rather than only at the end."""
    if not practice_chunks:
        return list(test_seq)
    if not test_seq:
        return list(practice_chunks)

    total_tests = len(test_seq)
    num_chunks = len(practice_chunks)
    insert_before: Dict[int, List[Dict[str, Any]]] = {}
    for i in range(num_chunks):
        idx = ((i + 1) * total_tests) // (num_chunks + 1)
        insert_before.setdefault(idx, []).append(practice_chunks[i])

    result: List[Dict[str, Any]] = []
    for j in range(total_tests):
        result.extend(insert_before.get(j, []))
        result.append(test_seq[j])
    result.extend(insert_before.get(total_tests, []))  # guard: trailing chunks
    return result


def build_session_queue(
    tests: List[Dict[str, Any]],
    targets: Dict[str, Any],
    completed_blocks: List[str],
    user_id: str,
    load_date: str,
    speed_round_available: bool = False,
) -> List[Dict[str, Any]]:
    """Assemble the ordered, interleaved session queue for one (user, load_date).

    Deterministic: same inputs -> same order on every GET, so resume is stable.

    ``speed_round_available`` appends the TASK-533 fluency battery as a tail
    bonus. It defaults to False so the queue stays a pure function of the
    planner's own output unless a caller has actually checked.
    """
    test_items: List[Dict[str, Any]] = [
        {
            'kind':         'test',
            'id':           t.get('id'),
            'slug':         t.get('slug'),
            'test_type':    t.get('test_type', 'listening'),
            'title':        t.get('title'),
            'elo_rating':   t.get('elo_rating'),
            'slot_type':    t.get('slot_type', 'new'),
            'is_completed': bool(t.get('is_completed')),
        }
        for t in tests
    ]

    rng = random.Random(_stable_seed(user_id, load_date))
    test_seq = _round_robin_tests(test_items, rng)

    # TASK-714: flashcards lead the session — FSRS reviews are due-driven and
    # work best as a warm-up, and putting them first means the single most
    # under-counted surface is also the one most likely to actually get done.
    # Dual Translation is effortful production, so it interleaves with practice
    # rather than stacking at the end.
    surface_items = _build_surface_items(targets, completed_blocks)
    flashcards = [i for i in surface_items if i['kind'] == 'flashcards']
    other_surfaces = [i for i in surface_items if i['kind'] != 'flashcards']

    practice_chunks = _build_practice_chunks(targets, completed_blocks)
    queue = flashcards + _interleave_practice(
        test_seq, practice_chunks + other_surfaces
    )

    # TASK-533 — fluency battery, appended rather than interleaved. Placing it
    # mid-session would put timed recall over already-mastered words ahead of
    # the acquisition work the plan actually budgeted for.
    if speed_round_available:
        queue.append({
            'kind':         _SPEED_ROUND_KIND,
            'id':           _SPEED_ROUND_BLOCK_ID,
            'skill':        _SPEED_ROUND_KIND,
            'is_bonus':     True,
            'is_completed': _SPEED_ROUND_BLOCK_ID in set(completed_blocks or []),
        })
    return queue


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
        today = _today_iso(db, user_id, language_id)
        row = (
            db.table('daily_test_loads')
            .select('daily_session_targets, completed_blocks')
            .eq('user_id', user_id)
            .eq('language_id', language_id)
            .eq('load_date', today)
            .limit(1)
            .execute()
        )
        targets = (row.data[0].get('daily_session_targets') or {}) if row.data else {}
        completed_blocks = (row.data[0].get('completed_blocks') or []) if row.data else []

        # 3. Build the ordered queue: tests round-robined by type, practice
        #    split into ≤10-min chunks interleaved mid-session, deterministic
        #    per (user, load_date) so resume order is stable (TASK-703).
        #    TASK-714 adds flashcards / dual_translation queue kinds.
        load_date = daily_load.get('load_date', today)

        # TASK-533 — offer the fluency battery only when the learner plausibly
        # has one. Best-effort: a failure here drops the bonus block rather
        # than the session, because a speed round is the least important thing
        # on this screen.
        speed_round_available = False
        try:
            from services.vocabulary_ladder.speed_round import get_speed_round_composer
            speed_round_available = (
                get_speed_round_composer().has_enough_mastered(user_id, language_id)
            )
        except Exception as exc:
            logger.warning("speed-round availability check failed: %s", exc)

        queue = build_session_queue(
            tests, targets, completed_blocks, user_id, load_date,
            speed_round_available=speed_round_available,
        )

        total = len(queue)
        completed = sum(1 for q in queue if q['is_completed'])

        return api_success({
            'load_date':          load_date,
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
    """Mark a non-test block complete for today (idempotent).

    Covers practice chunks (TASK-703) and the flashcards / dual_translation
    surface blocks (TASK-714). Test slots are completed via
    POST /api/tests/daily-load/complete instead.

    Practice minutes are credited to the weekly counters by the practice
    service itself (it owns the elapsed time). Surface blocks have no such
    owner, so this endpoint calls record_session_progress for them directly —
    without it the weekly counters never advance, which is exactly the F2 /
    TASK-701 failure mode ADR-021 warns about for any newly planned surface.
    """
    try:
        data = request.get_json(silent=True) or {}
        language_id = parse_language_id(data.get('language_id'))
        block_id = data.get('block_id')

        if not language_id:
            return bad_request("Invalid or missing language_id")

        user_id = g.current_user_id
        db = get_supabase_admin()
        today = _today_iso(db, user_id, language_id)

        row = (
            db.table('daily_test_loads')
            .select('id, completed_blocks, daily_session_targets')
            .eq('user_id', user_id)
            .eq('language_id', language_id)
            .eq('load_date', today)
            .limit(1)
            .execute()
        )
        if not row.data:
            return not_found("No daily load for today")

        # block_id must be one of today's chunked practice ids (e.g.
        # practice_acq_1) or surface ids (e.g. flashcards_1), derived from the
        # persisted budget (TASK-703 / TASK-714).
        targets = row.data[0].get('daily_session_targets') or {}
        valid_ids = _valid_block_ids(targets)
        if block_id not in valid_ids:
            return bad_request(
                f"block_id must be one of {sorted(valid_ids)}"
            )

        blocks = row.data[0].get('completed_blocks') or []
        newly_completed = block_id not in blocks
        if newly_completed:
            blocks.append(block_id)
            db.table('daily_test_loads')\
                .update({'completed_blocks': blocks})\
                .eq('id', row.data[0]['id'])\
                .execute()

        if newly_completed:
            _record_surface_progress(db, user_id, language_id, today, block_id)

        return api_success({'completed_blocks': blocks})

    except Exception as e:
        logger.error("complete_block failed: %s", e)
        return server_error("Failed to mark block complete")


def _surface_skill_for(block_id: str) -> str | None:
    """Map a block id (`flashcards_2`) back to its surface skill, or None when
    the block is a practice chunk (whose counters the practice service owns)."""
    for skill in _SURFACE_BLOCKS:
        if block_id.startswith(f"{skill}_"):
            return skill
    return None


def _record_surface_progress(
    db, user_id: str, language_id: int, load_date: str, block_id: str
) -> None:
    """Bump the weekly counter for a completed flashcards / DT block.

    Best-effort by design: the learner has already done the work and been told
    so, and record_session_progress is a no-op when no weekly_plan_states row
    exists. The attempt id is a deterministic uuid5 over
    (user, language, date, block) so a retried POST dedupes inside the RPC.
    """
    skill = _surface_skill_for(block_id)
    if not skill or not Config.STUDY_PLAN_ENABLED:
        return

    attempt_id = uuid.uuid5(
        _SURFACE_PROGRESS_NAMESPACE,
        f"{user_id}:{language_id}:{load_date}:{block_id}",
    )
    try:
        db.rpc('record_session_progress', {
            'p_user_id':       user_id,
            'p_language_id':   language_id,
            'p_attempt_id':    str(attempt_id),
            'p_kind':          'surface',
            'p_skill':         _SURFACE_BLOCKS[skill]['complete_as'],
            'p_delta_count':   1,
            'p_delta_seconds': 0,
        }).execute()
    except Exception as e:
        logger.warning(
            'record_session_progress failed (non-fatal) for surface block '
            '%s user=%s lang=%s: %s', block_id, user_id, language_id, e,
        )
