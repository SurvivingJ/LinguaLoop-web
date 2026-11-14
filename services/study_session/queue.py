"""Daily study session queue: pure composition helpers.

Turns today's tests, the persisted minute targets and the completed block ids
into the ordered queue the session runner plays (TASK-703 / TASK-714), plus
the optional tail (TASK-872), prestudy blocks and the intro-review chunk.
Nothing here reads the database; services.study_session.session does that.
Unit-tested in tests/test_study_session_ordering.py, test_study_session_tail.py,
test_plannable_surfaces.py and test_prestudy_session.py.
"""

from __future__ import annotations

import hashlib
import math
import random
from collections import OrderedDict, deque
from typing import Any, Dict, List, Optional

from config import Config
from services import study_plan_service as _plan

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
SURFACE_BLOCKS = {
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
# SURFACE_BLOCKS: it is a bonus, not a planned surface.
#
# ADR-021 draws the planner's boundary, and a speed round sits outside it on
# every criterion. It teaches nothing new (mastered words only), it must not
# move family confidence, and it has no weekly target or test_time_estimate
# seed — so budgeting minutes for it would make the plan claim work it never
# scheduled. It is appended after the planned queue instead: the day's actual
# work first, fluency practice as an optional tail.
#
# Consequently its completion credits no weekly counter. surface_skill_for
# returns None for this id, so recording surface progress no-ops on it, which
# is correct here rather than an oversight.
SPEED_ROUND_BLOCK_ID = 'speed_round_1'
SPEED_ROUND_KIND = 'speed_round'



def next_incomplete_index(queue: List[Dict[str, Any]]) -> int:
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


def build_practice_chunks(
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
    for skill in SURFACE_BLOCKS:
        try:
            n = int(raw.get(skill) or 0)
        except (TypeError, ValueError):
            n = 0
        if n > 0:
            out[skill] = n
    return out


def build_surface_items(
    targets: Dict[str, Any], completed_blocks: List[str]
) -> List[Dict[str, Any]]:
    """Expand budgeted flashcards / dual_translation slots into queue items.

    Item ids follow the practice convention (`{skill}_{n}`) because they share
    the completion endpoint, POST /api/study-session/complete-block.
    """
    done = set(completed_blocks or [])
    items: List[Dict[str, Any]] = []
    for skill, count in _surface_counts(targets).items():
        meta = SURFACE_BLOCKS[skill]
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


def valid_block_ids(targets: Dict[str, Any], extra_ids: Optional[set] = None) -> set:
    """Non-test block ids that are legitimately part of today's session.

    Covers practice chunks, the TASK-714 surface blocks and the TASK-533 speed
    round — everything POST /complete-block will accept.

    The speed round is accepted unconditionally rather than gated on the same
    availability check the GET uses. Re-running that check here would cost a
    second query to reject a completion for work the learner has, by the time
    they POST, already done — and a learner whose last mastered word lapsed
    mid-session would have their finished round rejected. Accepting it is
    harmless: it credits no weekly counter either way.

    ``extra_ids`` carries the optional-tail ids (``tail_window_ids``) for the
    completion endpoint; the GET never needs them here.
    """
    return (
        {c['id'] for c in build_practice_chunks(targets, [])}
        | {i['id'] for i in build_surface_items(targets, [])}
        | {SPEED_ROUND_BLOCK_ID}
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


def tail_window_ids(completed_blocks: List[str]) -> set:
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
    surface_items = build_surface_items(targets, completed_blocks)
    flashcards = [i for i in surface_items if i['kind'] == 'flashcards']
    other_surfaces = [i for i in surface_items if i['kind'] != 'flashcards']

    practice_chunks = build_practice_chunks(targets, completed_blocks)
    queue = flashcards + _interleave_practice(
        test_seq, practice_chunks + other_surfaces
    )

    # TASK-533 — fluency battery, appended rather than interleaved. Placing it
    # mid-session would put timed recall over already-mastered words ahead of
    # the acquisition work the plan actually budgeted for.
    if speed_round_available:
        queue.append({
            'kind':         SPEED_ROUND_KIND,
            'id':           SPEED_ROUND_BLOCK_ID,
            'skill':        SPEED_ROUND_KIND,
            'is_bonus':     True,
            'is_completed': SPEED_ROUND_BLOCK_ID in set(completed_blocks or []),
        })
    return queue


# ---------------------------------------------------------------------------
# Test prestudy blocks (wiki/features/test-prestudy.md, Triggers) -- pure,
# unit-tested in tests/test_prestudy_session.py.
# ---------------------------------------------------------------------------

_PRESTUDY_PREFIX = 'prestudy_'
_PRESTUDY_KIND = 'prestudy'


def prestudy_block_id(test_id: Any) -> str:
    return f"{_PRESTUDY_PREFIX}{test_id}"


def apply_prestudy(
    queue: List[Dict[str, Any]],
    plans: Dict[str, Dict[str, Any]],
    completed_blocks: List[str],
    prestudy_mode: str,
    test_budget_minutes: float,
) -> List[Dict[str, Any]]:
    """Insert prestudy blocks before the tests that need one and say honestly
    what they cost.

    * ``auto``: a block before every unfinished retry slot, every unfinished
      new test over 25% unknown (full) and every new test between 5% and 25%
      (light, about a minute).
    * ``ask``: no blocks; those same tests carry ``prestudy_offer.recommended``.
    * ``off``: no blocks, no recommendation.
    Every reading/listening test with linked words carries ``prestudy_offer``
    (the session card's "Study first" button) in every mode.

    The blocks spend tests-share minutes. When their unfinished total reaches
    the cost of a test slot (``test_budget_minutes / number of tests``), that
    many unstarted new tests without a block move to the end as optional
    (``is_bonus``, ``deferred_for_prestudy``), and each block says so.
    """
    done = set(completed_blocks or [])
    tests = [q for q in queue if q.get('kind') == 'test']
    out: List[Dict[str, Any]] = []
    blocks: List[Dict[str, Any]] = []
    for item in queue:
        plan = plans.get(str(item.get('id'))) if item.get('kind') == 'test' else None
        if not plan:
            out.append(item)
            continue
        is_retry = item.get('slot_type') == 'retry'
        wants = is_retry or plan['plan_mode'] in ('full', 'light')
        item['prestudy_offer'] = {
            'unknown_share': plan['unknown_share'],
            'minutes_est': plan['minutes_est'],
            'recommended': bool(prestudy_mode == 'ask' and (is_retry or plan['plan_mode'] == 'full')),
        }
        if prestudy_mode == 'auto' and wants and not item.get('is_completed'):
            block_id = prestudy_block_id(item['id'])
            block = {
                'kind':          _PRESTUDY_KIND,
                'id':            block_id,
                'test_id':       item['id'],
                'slug':          item.get('slug'),
                'test_type':     item.get('test_type'),
                'title':         item.get('title'),
                'trigger':       'retry' if is_retry else 'auto',
                'plan_mode':     'full' if is_retry and plan['plan_mode'] != 'full' else plan['plan_mode'],
                'unknown_share': plan['unknown_share'],
                'minutes_est':   plan['minutes_est'] if not (is_retry and plan['plan_mode'] != 'full')
                                 else max(2, plan['minutes_est']),
                'tests_dropped_today': 0,
                'is_completed':  block_id in done,
            }
            out.append(block)
            blocks.append(block)
        out.append(item)

    pending = [b for b in blocks if not b['is_completed']]
    per_test = (float(test_budget_minutes or 0) / len(tests)) if tests else 0.0
    if not pending or per_test <= 0:
        return out
    n_drop = int(sum(b['minutes_est'] for b in pending) // per_test)
    blocked = {b['test_id'] for b in blocks}
    candidates = [t for t in tests if t.get('slot_type', 'new') == 'new' and not t.get('is_completed')
                  and t.get('id') not in blocked and not t.get('is_bonus')]
    n_drop = min(n_drop, len(candidates), max(0, len(tests) - 1))
    if n_drop <= 0:
        return out
    deferred = candidates[-n_drop:]
    ids = {id(t) for t in deferred}
    for t in deferred:
        t['is_bonus'] = True
        t['deferred_for_prestudy'] = True
    for b in pending:
        b['tests_dropped_today'] = n_drop
    kept = [q for q in out if id(q) not in ids]
    # optional tests go after the planned work, before any bonus speed round
    tail_at = next((i for i, q in enumerate(kept) if q.get('kind') == SPEED_ROUND_KIND), len(kept))
    return kept[:tail_at] + deferred + kept[tail_at:]


def today_prestudy_ids(test_ids: Any) -> set:
    """Prestudy block ids POST /complete-block accepts: one per test in today's load."""
    out = set()
    for t in test_ids or []:
        tid = t.get('test_id') if isinstance(t, dict) else t
        if tid:
            out.add(prestudy_block_id(tid))
    return out


def surface_skill_for(block_id: str) -> Optional[str]:
    """Map a block id (`flashcards_2`) back to its surface skill, or None when
    the block is a practice chunk (whose counters the practice service owns)."""
    for skill in SURFACE_BLOCKS:
        if block_id.startswith(f"{skill}_"):
            return skill
    return None


# ---------------------------------------------------------------------------
# Intro-review chunk (ADR-040): intro sessions 2-4 and prestudy next-day
# reviews are served by a maintenance practice request.
# ---------------------------------------------------------------------------

INTRO_REVIEWS_BLOCK_ID = 'intro_reviews'


def intro_reviews_status(
    queue: List[Dict[str, Any]], targets: Dict[str, Any],
    completed_blocks: List[str], enabled: bool = True,
) -> str:
    """Whether the queue needs the intro-review chunk.

    ``off``: the drill is disabled or Vocabulary review is excluded.
    ``done``: the chunk was completed today (it stays in the queue as done).
    ``covered``: an open maintenance chunk already serves the reviews.
    ``check``: add the chunk if any review is due (the caller counts them).
    """
    if not enabled or 'practice' in (targets.get('excluded_modules') or []):
        return 'off'
    if INTRO_REVIEWS_BLOCK_ID in (completed_blocks or []):
        return 'done'
    if any(q.get('kind') == 'practice' and q.get('mode') == 'maintenance'
           and not q.get('is_completed') for q in queue):
        return 'covered'
    return 'check'


def insert_intro_reviews(
    queue: List[Dict[str, Any]], minutes: int, done: bool,
) -> List[Dict[str, Any]]:
    """Place the intro-review chunk where the practice part starts."""
    block = {'kind': 'practice', 'id': INTRO_REVIEWS_BLOCK_ID, 'mode': 'maintenance',
             'minutes': minutes, 'is_completed': done}
    at = next((i for i, q in enumerate(queue) if q.get('kind') == 'practice'), len(queue))
    return queue[:at] + [block] + queue[at:]

