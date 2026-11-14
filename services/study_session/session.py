"""Daily study session: the reads and writes behind /api/study-session.

``build_study_session`` assembles the GET payload; ``complete_block`` marks a
non-test block done. The queue itself is composed by the pure helpers in
services.study_session.queue.

"Today" is the learner's LOCAL date (ADR-022 / TASK-716); callers resolve it
once through services.day_boundary and pass it in.
"""

from __future__ import annotations

import logging
import uuid
from datetime import date
from typing import Any, Callable, Dict, List, Optional, Tuple

from config import Config
from services import request_cache
from services import study_plan_service as _plan
from services.concurrency import run_parallel
from services.study_session import queue as _queue
from services.test_service import daily_load_row_key

logger = logging.getLogger(__name__)

# Namespace for the deterministic idempotency key we hand to
# record_session_progress for surface blocks. Surface completions have no
# test_attempts row and therefore no attempt uuid, but the RPC dedupes on
# p_attempt_id — deriving it from (user, language, date, block) makes a
# repeated complete-block POST a no-op instead of a double count.
_SURFACE_PROGRESS_NAMESPACE = uuid.UUID('6f0f1d4e-6b1a-4f6d-9a1e-7147000714aa')

# (value, error) of one read in a concurrent batch.
Outcome = Tuple[Any, Optional[Exception]]


class NoDailyLoad(LookupError):
    """There is no daily_test_loads row for today."""


class InvalidBlockId(ValueError):
    """block_id is not part of today's session; ``valid_ids`` lists what is."""

    def __init__(self, valid_ids: set):
        super().__init__(f"block_id must be one of {sorted(valid_ids)}")
        self.valid_ids = valid_ids


def minutes_per_new_word(db, language_id: int) -> float:
    """Minutes per new word for the language (Config default on any failure)."""
    try:
        return float(_plan.get_minutes_per_new_word(db, language_id))
    except Exception:
        return float(getattr(Config, 'NEW_WORD_MINUTES_DEFAULT', 3.0))


def _attempt(fn: Callable[[], Any]) -> Outcome:
    try:
        return fn(), None
    except Exception as exc:
        return None, exc


# ---------------------------------------------------------------------------
# GET /api/study-session
# ---------------------------------------------------------------------------

def _daily_load_with_intake(
    db, user_id: str, language_id: int, test_service, practice_service,
) -> Dict[str, Any]:
    """Today's enriched load, after topping up the new-word intake.

    The load reuses the existing resolver/enrichment (Study Plan vs legacy
    routing, persists daily_test_loads). The intake then tops today's ladder
    up to the governed started-per-day quota BEFORE the targets are read.
    Best effort -- an intake failure never costs the learner their session.
    When fewer words can be served than Tier C planned inside the budget,
    today's session is rebuilt ONCE (the supply flag written by intake
    prevents a second rebuild) and the load is read again.
    """
    daily_load = test_service.get_or_create_daily_load(user_id, language_id)
    try:
        intake = practice_service.admit_daily_new_words(user_id, language_id)
        if intake.get('needs_rebuild') and Config.STUDY_PLAN_ENABLED:
            _plan.StudyPlanService(db).rebuild_today(user_id, language_id)
            # The rebuild rewrites today's targets; recount below.
            request_cache.invalidate('new_word_state')
            request_cache.invalidate('daily_load_row')
            daily_load = test_service.get_or_create_daily_load(user_id, language_id)
    except Exception as exc:
        logger.warning("daily new-word intake failed (non-fatal): %s", exc)
    return daily_load


def _today_load_row(db, user_id: str, language_id: int, today: str) -> Optional[Dict[str, Any]]:
    """Today's daily_test_loads row (practice targets, completed blocks).

    Usually the row get_or_create_daily_load just read (request cache); read
    again only if something wrote it since (intake shortfall, rebuild).
    """
    def _load_row():
        res = (
            db.table('daily_test_loads')
            .select('*')
            .eq('user_id', user_id)
            .eq('language_id', language_id)
            .eq('load_date', today)
            .limit(1)
            .execute()
        )
        return res.data[0] if res.data else None

    return request_cache.memo(daily_load_row_key(user_id, language_id, today), _load_row)


def due_followup_count(db, user_id: str, language_id: int, today: str) -> int:
    """Prestudy next-day reviews due today (0 when unknown). Best effort."""
    try:
        from services import prestudy
        from services.practice_session_service import PRESTUDY_FOLLOWUPS_PER_SESSION
        return len(prestudy.due_followup_senses(
            db, user_id, language_id, today, limit=PRESTUDY_FOLLOWUPS_PER_SESSION))
    except Exception as exc:
        logger.info("prestudy follow-up count skipped: %s", exc)
        return 0


def intro_review_minutes(n_intro: int, n_followups: int) -> int:
    """Minutes of the intro-review chunk; 0 when nothing is due."""
    if not n_intro and not n_followups:
        return 0
    from services import intro_drill
    from services.practice_session_service import PRESTUDY_FOLLOWUP_EXPECTED_SECONDS
    seconds = (n_intro * 4 * intro_drill.INTRO_ITEM_SECONDS
               + n_followups * PRESTUDY_FOLLOWUP_EXPECTED_SECONDS)
    return max(1, -(-seconds // 60))


def _session_reads(
    db, user_id: str, language_id: int, today: str, tests: List[Dict[str, Any]],
    *, speed_round: bool, intro_counts: bool, mpnw: Optional[Callable[[], float]],
) -> Dict[str, Outcome]:
    """The reads the queue is decorated with, run concurrently.

    They depend only on (user, language, today, tests), not on each other.
    Each comes back as ``(value, error)`` so a failure degrades only its own
    part of the response. The callables run outside the request context, so
    everything they need is captured here and nothing reads the request cache.
    """
    def prestudy_plans():
        from services import prestudy
        return prestudy.plan_for_tests(db, user_id, language_id, tests)

    def speed_round_available():
        from services.vocabulary_ladder.speed_round import get_speed_round_composer
        return get_speed_round_composer().has_enough_mastered(user_id, language_id)

    def intro_due():
        from services import intro_drill
        return intro_drill.due_review_count(
            db, user_id, language_id, date.fromisoformat(today))

    calls: Dict[str, Callable[[], Any]] = {'prestudy_plans': prestudy_plans}
    if speed_round:
        calls['speed_round'] = speed_round_available
    if intro_counts:
        calls['intro_due'] = intro_due
        calls['followups_due'] = lambda: due_followup_count(db, user_id, language_id, today)
    if mpnw is not None:
        calls['mpnw'] = mpnw

    results = run_parallel(*[(lambda fn=fn: _attempt(fn)) for fn in calls.values()])
    return dict(zip(calls, results))


def _speed_round_offered(outcome: Optional[Outcome]) -> bool:
    """TASK-533: offer the fluency battery only when the learner plausibly has
    one. A failed check drops the bonus block rather than the session."""
    if outcome is None:
        return False
    available, error = outcome
    if error is not None:
        logger.warning("speed-round availability check failed: %s", error)
        return False
    return bool(available)


def _with_prestudy(
    db, user_id: str, language_id: int, queue: List[Dict[str, Any]],
    plans_outcome: Outcome, completed_blocks: List[str], targets: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Prestudy blocks before hard new tests and retry slots, the session
    card's "Study first" offer, and honest minutes. Best effort: a planning
    failure leaves the queue exactly as the planner made it."""
    try:
        plans, error = plans_outcome
        if error is not None:
            raise error
        if plans:
            from services import prestudy
            return _queue.apply_prestudy(
                queue, plans, completed_blocks,
                prestudy.get_prestudy_mode(db, user_id, language_id),
                float(targets.get('test_budget_minutes') or 0),
            )
    except Exception as exc:
        logger.warning("prestudy planning failed (non-fatal): %s", exc)
    return queue


def _intro_reviews_status(
    practice_items: List[Dict[str, Any]], targets: Dict[str, Any], completed_blocks: List[str],
) -> str:
    try:
        from services import intro_drill
        return _queue.intro_reviews_status(
            practice_items, targets, completed_blocks, enabled=intro_drill.ENABLED)
    except Exception as exc:
        logger.warning("intro review chunk failed (non-fatal): %s", exc)
        return 'off'


def with_intro_reviews(
    queue: List[Dict[str, Any]], status: str, reads: Dict[str, Outcome],
) -> List[Dict[str, Any]]:
    """Add one maintenance chunk for due review work when the queue has no
    incomplete maintenance chunk to serve it: new-word-drill reviews (sessions
    2-4) and prestudy next-day reviews. The practice player's maintenance
    request serves both (the drill block and the follow-up injection).

    Without this, a learner with no study plan row for the language (whose day
    has no practice chunks at all) saw "No exercises due" in Practice mode
    while follow-ups were waiting. Once done it stays in the queue as done.

    ``status`` is ``queue.intro_reviews_status``; ``reads`` holds the
    ``intro_due`` and ``followups_due`` counts when the status is ``check``.
    """
    if status == 'done':
        return _queue.insert_intro_reviews(queue, 1, True)
    if status != 'check':
        return queue
    try:
        n_intro, error = reads['intro_due']
        if error is not None:
            raise error
        minutes = intro_review_minutes(n_intro, reads['followups_due'][0] or 0)
    except Exception as exc:
        logger.warning("intro review chunk failed (non-fatal): %s", exc)
        return queue
    return _queue.insert_intro_reviews(queue, minutes, False) if minutes else queue


def _governor_and_tail(
    state_outcome: Outcome, mpnw_outcome: Optional[Outcome],
    queue: List[Dict[str, Any]], completed_blocks: List[str],
) -> Dict[str, Any]:
    """``governor``, ``tail`` and ``tail_queue`` (session-budget-settings).

    `progress` and `next_index` count `queue` only; tail items never join it,
    so session completion is unchanged. Best effort.
    """
    try:
        state, error = state_outcome
        if error is not None:
            raise error
        mpnw = 0.0
        if mpnw_outcome is not None:
            mpnw, error = mpnw_outcome
            if error is not None:
                raise error
        # The tail gate ignores test items: "Keep going" is offered once the
        # practice part is done, even if tests were skipped.
        gate_queue = [q for q in queue if q.get('kind') != 'test']
        return _queue.compute_governor_and_tail(state, gate_queue, completed_blocks, mpnw)
    except Exception as exc:
        logger.warning("governor/tail computation failed (non-fatal): %s", exc)
        return {'governor': None, 'tail': None, 'tail_queue': []}


def build_study_session(
    db, user_id: str, language_id: int, today: str, *,
    test_service, practice_service, mpnw: Callable[[], float],
) -> Dict[str, Any]:
    """The GET /api/study-session payload: today's ordered queue with progress,
    the governor message and the live optional tail.

    ``mpnw`` returns the language's minutes per new word. It runs off the
    request thread, and only when a new-word state exists.
    """
    daily_load = _daily_load_with_intake(
        db, user_id, language_id, test_service, practice_service)
    tests = daily_load.get('tests', []) or []

    load_row = _today_load_row(db, user_id, language_id, today)
    targets = ((load_row or {}).get('daily_session_targets') or {})
    completed_blocks = ((load_row or {}).get('completed_blocks') or [])
    load_date = daily_load.get('load_date', today)

    # Normally already in the request cache from the intake above.
    state_outcome = _attempt(lambda: practice_service.new_word_state(user_id, language_id))
    has_state = state_outcome[1] is None and state_outcome[0] is not None

    intro_status = _intro_reviews_status(
        _queue.build_practice_chunks(targets, completed_blocks), targets, completed_blocks)
    reads = _session_reads(
        db, user_id, language_id, today, tests,
        # A speed round is vocabulary review by another name (session-modules):
        # suppressed outright when 'practice' is excluded.
        speed_round='practice' not in (targets.get('excluded_modules') or []),
        intro_counts=intro_status == 'check',
        mpnw=mpnw if has_state else None,
    )

    # Tests round-robined by type, practice split into ≤10-min chunks
    # interleaved mid-session, deterministic per (user, load_date) so resume
    # order is stable (TASK-703); TASK-714 adds the surface queue kinds.
    queue = _queue.build_session_queue(
        tests, targets, completed_blocks, user_id, load_date,
        speed_round_available=_speed_round_offered(reads.get('speed_round')),
    )
    queue = _with_prestudy(
        db, user_id, language_id, queue, reads['prestudy_plans'], completed_blocks, targets)
    queue = with_intro_reviews(queue, intro_status, reads)

    return {
        'load_date':          load_date,
        'language_id':        language_id,
        'study_plan_enabled': bool(Config.STUDY_PLAN_ENABLED),
        'queue':              queue,
        'progress':           {
            'completed': sum(1 for q in queue if q['is_completed']),
            'total':     len(queue),
        },
        'next_index':         _queue.next_incomplete_index(queue),
        **_governor_and_tail(state_outcome, reads.get('mpnw'), queue, completed_blocks),
    }


# ---------------------------------------------------------------------------
# POST /api/study-session/complete-block
# ---------------------------------------------------------------------------

def complete_block(
    db, user_id: str, language_id: int, today: str, block_id: Any,
) -> List[str]:
    """Mark a non-test block complete for today (idempotent); returns the
    day's completed block ids.

    Covers practice chunks (TASK-703), the flashcards / dual_translation
    surface blocks (TASK-714), tail chunks, prestudy blocks and the intro
    review chunk. Practice minutes are credited to the weekly counters by the
    practice service itself (it owns the elapsed time). Surface blocks have no
    such owner, so their progress is recorded here — without it the weekly
    counters never advance, which is exactly the F2 / TASK-701 failure mode
    ADR-021 warns about for any newly planned surface.

    Raises NoDailyLoad or InvalidBlockId.
    """
    res = (
        db.table('daily_test_loads')
        .select('id, completed_blocks, daily_session_targets, test_ids')
        .eq('user_id', user_id)
        .eq('language_id', language_id)
        .eq('load_date', today)
        .limit(1)
        .execute()
    )
    if not res.data:
        raise NoDailyLoad("No daily load for today")
    row = res.data[0]

    # block_id must be one of today's ids, derived from the persisted budget
    # (TASK-703 / TASK-714).
    blocks = row.get('completed_blocks') or []
    valid_ids = _queue.valid_block_ids(
        row.get('daily_session_targets') or {},
        extra_ids=_queue.tail_window_ids(blocks)
        | _queue.today_prestudy_ids(row.get('test_ids'))
        | {_queue.INTRO_REVIEWS_BLOCK_ID},
    )
    if block_id not in valid_ids:
        raise InvalidBlockId(valid_ids)

    if block_id not in blocks:
        blocks.append(block_id)
        db.table('daily_test_loads')\
            .update({'completed_blocks': blocks})\
            .eq('id', row['id'])\
            .execute()
        record_surface_progress(db, user_id, language_id, today, block_id)
    return blocks


def record_surface_progress(
    db, user_id: str, language_id: int, load_date: str, block_id: str
) -> None:
    """Bump the weekly counter for a completed flashcards / DT block.

    Best-effort by design: the learner has already done the work and been told
    so, and record_session_progress is a no-op when no weekly_plan_states row
    exists. The attempt id is a deterministic uuid5 over
    (user, language, date, block) so a retried POST dedupes inside the RPC.
    """
    skill = _queue.surface_skill_for(block_id)
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
            'p_skill':         _queue.SURFACE_BLOCKS[skill]['complete_as'],
            'p_delta_count':   1,
            'p_delta_seconds': 0,
        }).execute()
    except Exception as e:
        logger.warning(
            'record_session_progress failed (non-fatal) for surface block '
            '%s user=%s lang=%s: %s', block_id, user_id, language_id, e,
        )
