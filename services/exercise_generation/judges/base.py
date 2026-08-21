"""
Judge infrastructure — base types, thresholds, and verdict classifier.

All LLM judges in services.exercise_generation.judges import from here so
threshold changes propagate with a single edit and no redeploy of judge logic.

Verdict flow
------------
                       confidence
                           │
              ┌────────────┼────────────┐
              │            │            │
           < 0.6        0.6–0.8       ≥ 0.8
              │            │            │
           reject         flag        accept
       (sync block)  (persist,      (pass
                      enqueue)      through)

Failure-safe contract
---------------------
On any judge error (template missing, LLM call failure, malformed response)
the judge returns safe_accept() — the same "act as if the judge wasn't there"
contract used by cloze_judge.py.  The caller logs the error before delegating
to safe_accept.

Batch mode (TASK-510) inverts that contract
-------------------------------------------
Two total outages came from delisted model slugs: judges silently fell open
and a whole batch shipped unjudged content.  Inside a *generation batch* a
judge that cannot resolve its template/model must abort the batch loudly
instead of rubber-stamping everything.  Serve-adjacent call sites (a learner
waiting on a practice session) keep the fail-open contract — a dead judge
must never break a live session.

The switch is a thread-local flag, so a batch running in an APScheduler
thread can never flip the contract for a request thread in the same
process::

    from services.exercise_generation.judges.base import batch_mode

    with batch_mode():
        run_generation_batch(...)      # judges now raise JudgeUnavailable

Every judge already funnels its error paths through ``safe_accept()``, so
that single chokepoint makes all of them fail closed.  Judges whose fail-open
path returns a bare dict instead (collocation.py) call ``guard_fail_open()``
at the same point.

Thread-local means *per thread*, and a batch that fans work out to a worker
pool runs its generators on threads that never entered the block — so the
judges those generators call quietly fell open again, which is the original
TASK-510 bug wearing a different hat.  ``BatchModeThreadPoolExecutor`` (or
``bind_batch_mode`` on a single callable) carries the flag across that
boundary::

    with BatchModeThreadPoolExecutor(max_workers=8) as pool:
        pool.submit(generator.generate, ...)   # inherits fail-closed

``JudgeUnavailable`` is then raised on the worker and re-raised by
``future.result()``, so any caller that wraps futures in ``except Exception``
must re-raise it explicitly — otherwise the abort degrades into a silent drop
of that one variant, which is quieter than the bug it replaced.
"""

from __future__ import annotations

import functools
import threading
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Callable, Iterator, Literal, TypeVar


# ---------------------------------------------------------------------------
# Verdict thresholds — edit here to re-tune without touching judge logic.
# ---------------------------------------------------------------------------

THRESHOLD_ACCEPT: float = 0.8   # confidence >= THRESHOLD_ACCEPT → accept
THRESHOLD_REJECT: float = 0.6   # confidence <  THRESHOLD_REJECT → reject
                                 # in between → flag


# ---------------------------------------------------------------------------
# Core types
# ---------------------------------------------------------------------------

Verdict = Literal['accept', 'flag', 'reject']


@dataclass
class JudgeOutcome:
    """Result of a single judge evaluation.

    Attributes
    ----------
    verdict:    'accept' | 'flag' | 'reject'  (derived from confidence)
    confidence: the judge's score, on **that judge's** scale — a 1-5 Likert
                rating for every judge except ``cloze`` (see ``classify``),
                which still reports a 0.0-1.0 probability. ``None`` means the
                judge produced no score for this item at all
                (``accept_item``); it is never a substitute for a low one.
    reason:     free-text explanation in the target language
    axes:       for a multi-axis judge, the full per-axis rating map, e.g.
                ``{'fit': 5, 'confusability': 3}``. ``None`` for the
                single-axis judges, which is all of them except
                ``distractor_plausibility`` (TASK-719). ``confidence`` carries
                only the *binding* axis's rating, so this is the one place the
                other axis survives.
    flag_axes:  which axis or axes produced a non-accept verdict, in
                ``schemas.AXES`` order — empty on an accept and on every
                single-axis judge. TASK-720: this is what the review queue
                records so a reviewer knows whether the judge was unsure about
                the subject or about the confusion with the answer.
    """
    verdict: Verdict
    confidence: float | None
    reason: str
    axes: dict[str, int | None] | None = None
    flag_axes: tuple[str, ...] = ()


# ---------------------------------------------------------------------------
# Classifier
# ---------------------------------------------------------------------------

def classify(confidence: float) -> Verdict:
    """Map a raw 0.0–1.0 confidence score to a verdict string.

    LEGACY — one remaining caller: ``judges/cloze.py``.

    Every other judge now reports a 1-5 Likert rating and maps it with
    ``schemas.likert_to_verdict``. Two mappers still exist only because the two
    scales still exist, and they **invert**: a stored ``1.0`` is "maximum
    confidence, accept" here and "worst rating, reject" on the Likert side. That
    collision is what forced ``migrations/null_legacy_judge_confidence.sql`` to
    erase 888 rows of ``llm_calls.judge_confidence``.

    ``judge_answer_entailment`` converted under TASK-723; cloze distractor
    plausibility did not, because it has the same two-axis problem as the
    comprehension distractor judge (topical distance vs confusability with the
    answer) and cloning today's bands would bake that in. TASK-719 has now
    settled that split — ``schemas.axes_to_verdict`` and the v7 rubric are the
    template cloze should be converted onto. Once it is, this function and
    ``THRESHOLD_ACCEPT`` / ``THRESHOLD_REJECT`` can be deleted outright.

    Do not add callers.

    Examples
    --------
    >>> classify(0.9)
    'accept'
    >>> classify(0.7)
    'flag'
    >>> classify(0.5)
    'reject'
    """
    if confidence >= THRESHOLD_ACCEPT:
        return 'accept'
    if confidence >= THRESHOLD_REJECT:
        return 'flag'
    return 'reject'


# ---------------------------------------------------------------------------
# Batch mode — fail-closed judging (TASK-510)
# ---------------------------------------------------------------------------

class JudgeUnavailable(RuntimeError):
    """A judge could not run and the caller is in fail-closed batch mode.

    Raised only inside ``batch_mode()``. Aborts the batch rather than letting
    unjudged content ship, which is what happened during the two delisted-slug
    outages that motivated TASK-510.
    """


_batch_state = threading.local()


def is_batch_mode() -> bool:
    """True when the *current thread* is running a fail-closed generation batch."""
    return getattr(_batch_state, 'enabled', False)


@contextmanager
def batch_mode(enabled: bool = True) -> Iterator[None]:
    """Make judge failures fail closed for the duration of the block.

    Thread-local and re-entrant-safe: the previous value is restored on exit,
    so nesting (or a batch that calls a serve-path helper) behaves sanely.
    Pass ``enabled=False`` to explicitly force fail-open inside a batch.
    """
    previous = getattr(_batch_state, 'enabled', False)
    _batch_state.enabled = enabled
    try:
        yield
    finally:
        _batch_state.enabled = previous


_T = TypeVar('_T')


def bind_batch_mode(fn: Callable[..., _T]) -> Callable[..., _T]:
    """Bind ``fn`` to the batch-mode flag of the thread calling *this* function.

    ``_batch_state`` is thread-local by design (see ``batch_mode``) so a batch
    can never flip the contract for a request thread sharing the process. The
    price is that anything handed to a worker pool executes on a thread that
    never entered ``batch_mode()``, where judges revert to fail-open — the very
    rubber-stamping TASK-510 exists to prevent, in the one place it costs most.

    The flag is captured at wrap time (i.e. on submit, from the submitting
    thread) and re-established inside the worker::

        pool.submit(bind_batch_mode(generator.generate), sense_id, ...)

    Prefer ``BatchModeThreadPoolExecutor``, which applies this to every submit
    so a new call site cannot forget.
    """
    enabled = is_batch_mode()

    @functools.wraps(fn)
    def _carrying_batch_mode(*args, **kwargs) -> _T:
        with batch_mode(enabled):
            return fn(*args, **kwargs)

    return _carrying_batch_mode


class BatchModeThreadPoolExecutor(ThreadPoolExecutor):
    """ThreadPoolExecutor whose workers inherit the submitter's batch mode.

    Drop-in replacement anywhere a fail-closed batch fans work out to threads.
    The snapshot is taken per ``submit`` on the calling thread, so a pool
    constructed outside ``batch_mode()`` but submitted to from inside it still
    fails closed — the flag follows the work, not the pool.
    """

    def submit(self, fn, /, *args, **kwargs):
        return super().submit(bind_batch_mode(fn), *args, **kwargs)


def guard_fail_open(judge: str, reason: str) -> None:
    """Abort in batch mode; no-op when serving.

    For judges whose fail-open path returns a plain dict rather than a
    JudgeOutcome (collocation.py), so they share one fail-closed chokepoint
    with ``safe_accept``. Call it immediately before building the fail-open
    return value.
    """
    if is_batch_mode():
        raise JudgeUnavailable(
            f"{judge} could not run during a generation batch ({reason}). "
            f"Batch aborted rather than shipping unjudged content — check "
            f"prompt_templates for an active row with a live model slug "
            f"(see services/model_health.py)."
        )


# ---------------------------------------------------------------------------
# Safe-default helper (mirrors cloze_judge.py pattern)
# ---------------------------------------------------------------------------

def safe_accept(reason: str = 'judge error – safe-default accept') -> JudgeOutcome:
    """Return an accept outcome for use when a judge fails unexpectedly.

    Failure mode is "act as if the judge wasn't there", not "drop all output".
    Callers must log the underlying error *before* calling this.

    Inside ``batch_mode()`` this inverts and raises ``JudgeUnavailable``: a
    batch must never rubber-stamp content because a judge was unreachable.

    Use this for *judge-down* conditions (template missing, LLM call failed,
    response unusable as a whole). For a gap in one item of an otherwise
    healthy response, use ``accept_item`` — see its docstring.
    """
    guard_fail_open('judge', reason)
    return JudgeOutcome(
        verdict='accept',
        confidence=THRESHOLD_ACCEPT,
        reason=reason,
    )


def accept_item(reason: str) -> JudgeOutcome:
    """Accept a single item whose verdict was missing or unparseable.

    Distinct from ``safe_accept`` and deliberately **never** raises, even in
    batch mode. The judge itself answered — one entry in its response was
    absent or malformed. Per the v3 Likert contract a missing verdict must
    never manufacture a rejection, and aborting a 3,000-sense batch over one
    unparseable rating would be a worse failure than shipping that one item.

    Judge *outages* (dead slug, missing template, unusable response) still go
    through ``safe_accept`` and still abort the batch.

    ``confidence`` is ``None``, not a number. Every caller of this helper is a
    Likert judge, so the old ``THRESHOLD_ACCEPT`` (0.8) was a *probability*
    constant being written into a 1-5 column: ``distractor_plausibility`` logs
    ``worst.confidence``, and whenever the worst outcome was an unrated item the
    row landed in ``llm_calls.judge_confidence`` as 0.8 — reintroducing exactly
    the two-scales-in-one-column collision that
    ``migrations/null_legacy_judge_confidence.sql`` erased 888 rows to clear.
    Substituting 5.0 would be no better: it fabricates a rating, and the whole
    point of the v3 lesson is that a missing rating must stay visibly missing
    rather than become a number nobody made. NULL is the honest value and the
    column is nullable.
    """
    return JudgeOutcome(
        verdict='accept',
        confidence=None,
        reason=reason,
    )


# ---------------------------------------------------------------------------
# Verdict observability helper
# ---------------------------------------------------------------------------

def log_judge_verdict(
    task_name: str,
    model: str,
    verdict: str,
    confidence: float,
    pipeline: str = 'test_gen',
) -> None:
    """Best-effort: write a compact verdict row to llm_calls.

    ``call_llm`` auto-logs the raw LLM round-trip with judge_verdict=NULL.
    This function writes a *second* row that carries the classified verdict
    and confidence, enabling the smoke-test query::

        SELECT task_name, COUNT(*) FILTER (WHERE judge_verdict='accept') ...
        FROM llm_calls
        WHERE task_name LIKE 'judge_%' AND judge_verdict IS NOT NULL

    to compute accept / flag / reject distributions without changing
    call_llm's internals.

    Never raises — verdict logging must never break the generation pipeline.
    """
    try:
        from services.supabase_factory import get_supabase_admin, get_supabase
        client = get_supabase_admin() or get_supabase()
        if client is None:
            return
        client.table('llm_calls').insert({
            'pipeline': pipeline,
            'task_name': task_name,
            'model': model,
            'judge_verdict': verdict,
            'judge_confidence': confidence,
        }).execute()
    except Exception:
        pass
