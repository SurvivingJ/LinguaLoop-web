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
import math
import random
import uuid
from collections import OrderedDict, deque
from typing import Any, Dict, List, Optional

from flask import Blueprint, g, request

from config import Config
from services import study_plan_service as _plan
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

# Optional tail (session-budget-settings, TASK-872): work offered after the
# required session is complete -- due reviews that did not fit, then the rest of
# today's new-word quota. Tail items are NEVER part of `queue`, so progress and
# session completion are unchanged. Reviews come before new words.
_TAIL_BLOCKS = {
    'maintenance': 'tail_maint',
    'acquisition': 'tail_acq',
}

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


def _practice_service():
    """The process-wide practice session service (lazy: keeps imports light)."""
    from services.practice_session_service import get_practice_session_service
    return get_practice_session_service()


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


def _valid_block_ids(targets: Dict[str, Any], extra_ids: Optional[set] = None) -> set:
    """Non-test block ids that are legitimately part of today's session.

    Covers practice chunks, the TASK-714 surface blocks and the TASK-533 speed
    round — everything POST /complete-block will accept.

    The speed round is accepted unconditionally rather than gated on the same
    availability check the GET uses. Re-running that check here would cost a
    second query to reject a completion for work the learner has, by the time
    they POST, already done — and a learner whose last mastered word lapsed
    mid-session would have their finished round rejected. Accepting it is
    harmless: it credits no weekly counter either way.

    ``extra_ids`` carries the optional-tail ids (``_tail_window_ids``) for the
    completion endpoint; the GET never needs them here.
    """
    return (
        {c['id'] for c in _build_practice_chunks(targets, [])}
        | {i['id'] for i in _build_surface_items(targets, [])}
        | {_SPEED_ROUND_BLOCK_ID}
        | set(extra_ids or ())
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


# ---------------------------------------------------------------------------
# Optional tail (session-budget-settings, TASK-872) -- pure helpers, unit-tested
# in tests/test_study_session_tail.py.
# ---------------------------------------------------------------------------

def _tail_offer_max_min() -> int:
    """Max minutes of tail chunks offered per "Keep going?" round (tunable)."""
    try:
        return int(getattr(_plan, 'TAIL_OFFER_MAX_MIN', 20))
    except (TypeError, ValueError):
        return 20


def _is_main_complete(queue: List[Dict[str, Any]]) -> bool:
    """True when every non-bonus item of the required queue is complete."""
    return all(q.get('is_completed') for q in queue if not q.get('is_bonus'))


def _tail_done_count(completed_blocks: List[str], prefix: str) -> int:
    return sum(1 for b in (completed_blocks or []) if str(b).startswith(f"{prefix}_"))


def _build_tail_queue(
    reviews_minutes: float, new_word_minutes: float, completed_blocks: List[str],
) -> List[Dict[str, Any]]:
    """Chunk one round of tail work: reviews first, then new words.

    At most ``TAIL_OFFER_MAX_MIN`` minutes are offered per round
    (``maint_min = min(reviews, cap)``, ``acq_min = min(words, cap - maint)``),
    in chunks of at most ``_PRACTICE_CHUNK_MAX_MIN``. ``k`` continues from the
    completed ids of the same kind so ids never collide across rounds.
    """
    cap = _tail_offer_max_min()
    maint_min = min(int(math.ceil(max(0.0, reviews_minutes))), cap)
    acq_min = min(int(math.ceil(max(0.0, new_word_minutes))), cap - maint_min)
    queue: List[Dict[str, Any]] = []
    for mode, minutes in (('maintenance', maint_min), ('acquisition', acq_min)):
        prefix = _TAIL_BLOCKS[mode]
        k = _tail_done_count(completed_blocks, prefix)
        for n, chunk_min in enumerate(_chunk_minutes(minutes), start=1):
            queue.append({
                'kind':         'practice',
                'id':           f"{prefix}_{k + n}",
                'mode':         mode,
                'minutes':      chunk_min,
                'is_bonus':     True,
                'is_tail':      True,
                'is_completed': False,
            })
    return queue


def _tail_window_ids(completed_blocks: List[str]) -> set:
    """Tail block ids POST /complete-block will accept.

    A tail chunk is derived live, and finishing a chunk's reviews shrinks the
    very backlog it was derived from, so re-deriving the queue at completion time
    would reject legitimate completions. Instead accept the ids a round can
    currently contain (the next ``ceil(cap / chunk)`` of each kind) plus ids
    already completed (idempotent re-POST). Anything else is stale or invented.
    """
    per_round = max(1, int(math.ceil(_tail_offer_max_min() / _PRACTICE_CHUNK_MAX_MIN)))
    ids: set = set()
    for prefix in _TAIL_BLOCKS.values():
        done = _tail_done_count(completed_blocks, prefix)
        ids.update(f"{prefix}_{k}" for k in range(1, done + per_round + 1))
    return ids


def _mpnw(db, language_id: int) -> float:
    """Minutes per new word for the language (Config default on any failure)."""
    try:
        return float(_plan.get_minutes_per_new_word(db, language_id))
    except Exception:
        return float(getattr(Config, 'NEW_WORD_MINUTES_DEFAULT', 3.0))


def compute_governor_and_tail(
    state: Optional[Dict[str, Any]], queue: List[Dict[str, Any]],
    completed_blocks: List[str], mpnw: float,
) -> Dict[str, Any]:
    """The ``governor``, ``tail`` and ``tail_queue`` response fields.

    ``state`` is ``PracticeSessionService.new_word_state`` (None when there is no
    plan or a read failed: no governor message, no tail). ``tail`` is non-null
    only when the required queue is complete and something is left:

        reviews_left_items = governor.due_items   (0 if 'practice' is excluded)
        new_words_left     = max(0, min(E - ST, U))

    Under ``tests_only`` the in-budget pool holds no vocabulary, so every review
    and new word appears here.
    """
    if state is None:
        return {'governor': None, 'tail': None, 'tail_queue': []}

    gov = state['governor'] or {}
    practice_off = 'practice' in (state.get('excluded') or [])
    governor = {
        'level':               state['level'],
        'overdue_items':       int(gov.get('overdue_items') or 0),
        'overdue_minutes':     float(gov.get('overdue_minutes') or 0),
        'threshold_minutes':   float(gov.get('threshold_minutes') or 0),
        'new_words_quota':     int(state['quota']),
        'new_words_effective': int(state['effective']),
    }
    result: Dict[str, Any] = {'governor': governor, 'tail': None, 'tail_queue': []}
    if not _is_main_complete(queue):
        return result

    reviews_items = 0 if practice_off else int(gov.get('due_items') or 0)
    item_seconds = float(gov.get('item_seconds') or getattr(
        Config, 'REVIEW_ITEM_SECONDS_DEFAULT', 20.0))
    reviews_minutes = reviews_items * item_seconds / 60.0
    words_left = max(0, min(state['effective'] - state['started_today'],
                            state['unstarted']))
    words_minutes = (max(1, int(round(words_left * mpnw))) if words_left else 0)
    if reviews_items <= 0 and words_left <= 0:
        return result

    result['tail'] = {
        'reviews_left_items':    reviews_items,
        'reviews_left_minutes':  round(reviews_minutes, 1),
        'new_words_left':        words_left,
        'new_words_left_minutes': words_minutes,
    }
    result['tail_queue'] = _build_tail_queue(
        reviews_minutes, words_minutes, completed_blocks)
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

        # 1b. Session-budget-settings: top today's ladder intake up to the
        #     governed started-per-day quota BEFORE the targets are read. Best
        #     effort -- an intake failure never costs the learner their session.
        #     When fewer words can be served than Tier C planned inside the
        #     budget, rebuild today's session ONCE (the supply flag written by
        #     intake prevents a second rebuild) and re-read the load.
        db = get_supabase_admin()
        practice_service = _practice_service()
        try:
            intake = practice_service.admit_daily_new_words(user_id, language_id)
            if intake.get('needs_rebuild') and Config.STUDY_PLAN_ENABLED:
                _plan.StudyPlanService(db).rebuild_today(user_id, language_id)
                daily_load = get_test_service().get_or_create_daily_load(
                    user_id, language_id)
                tests = daily_load.get('tests', []) or []
        except Exception as exc:
            logger.warning("daily new-word intake failed (non-fatal): %s", exc)

        # 2. Practice targets + per-block completion from the persisted row.
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
        # Suppressed outright when Vocabulary review ('practice') is excluded:
        # a speed round is vocabulary review by another name (session-modules).
        speed_round_available = False
        if 'practice' not in (targets.get('excluded_modules') or []):
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

        # Session-budget-settings: governor message + the live optional tail.
        # `progress` and `next_index` count `queue` only; tail items never join
        # it, so session completion is unchanged. Best effort.
        extras: Dict[str, Any] = {'governor': None, 'tail': None, 'tail_queue': []}
        try:
            state = practice_service.new_word_state(user_id, language_id)
            extras = compute_governor_and_tail(
                state, queue, completed_blocks, _mpnw(db, language_id))
        except Exception as exc:
            logger.warning("governor/tail computation failed (non-fatal): %s", exc)

        return api_success({
            'load_date':          load_date,
            'language_id':        language_id,
            'study_plan_enabled': bool(Config.STUDY_PLAN_ENABLED),
            'queue':              queue,
            'progress':           {'completed': completed, 'total': total},
            'next_index':         _next_incomplete_index(queue),
            'governor':           extras['governor'],
            'tail':               extras['tail'],
            'tail_queue':         extras['tail_queue'],
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
        valid_ids = _valid_block_ids(
            targets,
            extra_ids=_tail_window_ids(row.data[0].get('completed_blocks') or []),
        )
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
