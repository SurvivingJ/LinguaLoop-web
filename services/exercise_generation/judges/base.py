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

import contextvars
import functools
import logging
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Callable, Iterator, Literal, TypeVar

from services.exercise_generation.config import LANG_ID_TO_CODE

logger = logging.getLogger(__name__)


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
    probability: a probability-scored backend's P(yes), for judges that have
                one (answer entailment on the jev backend). ``confidence`` is
                ``None`` for those outcomes -- a probability must never be
                written into the 1-5 ``llm_calls.judge_confidence`` column, the
                two-scales-in-one-column collision that migrations/
                null_legacy_judge_confidence.sql erased 888 rows to clear.
    backend:    which implementation produced the outcome ('llm' | 'jev').
    """
    verdict: Verdict
    confidence: float | None
    reason: str
    axes: dict[str, int | None] | None = None
    flag_axes: tuple[str, ...] = ()
    probability: float | None = None
    backend: str = 'llm'


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
    """ThreadPoolExecutor whose workers inherit the submitter's batch mode
    AND contextvars.

    Drop-in replacement anywhere a fail-closed batch fans work out to threads.
    The batch-mode snapshot is taken per ``submit`` on the calling thread, so a
    pool constructed outside ``batch_mode()`` but submitted to from inside it
    still fails closed — the flag follows the work, not the pool.

    Contextvars (Phase 0 cost instrumentation): ``contextvars.copy_context()``
    is captured at submit time and the worker runs inside it, the same way
    ``asyncio`` tasks inherit their creator's context — plain
    ``ThreadPoolExecutor`` workers do not do this on their own. This is what
    lets ``services.llm_service.generation_context(sense_id=..., ...)``,
    entered once on the submitting thread in
    ``VocabAssetPipeline._generate_for_sense_impl``, still be visible to
    ``call_llm()`` when it actually runs on a pool thread for the P2/P3/
    split-level/typed-generator fan-out. Generic on purpose: this executor
    knows nothing about llm_service's specific contextvars, so any future
    contextvar-based observability gets the same propagation for free.
    """

    def submit(self, fn, /, *args, **kwargs):
        ctx = contextvars.copy_context()
        bound = bind_batch_mode(fn)
        return super().submit(ctx.run, bound, *args, **kwargs)


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
    confidence: float | None,
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


# ---------------------------------------------------------------------------
# Shared runner — the template-load / LLM-call / parse ladder every judge runs
# ---------------------------------------------------------------------------

VERDICT_ORDER = {'reject': 0, 'flag': 1, 'accept': 2}  # lower = worse

# Rating reported when the judge is unreachable. Keeps the candidate — an
# outage must never manufacture a rejection (v3 Likert contract).
KEEP_RATING = 5.0


@dataclass(frozen=True)
class JudgeSpec:
    """What differs between judges; ``ask_judge`` and the runners do the rest.

    ``module`` is the judge module's ``__name__``. Its ``_cfg_cache``,
    ``get_template_config`` and ``log_judge_verdict`` attributes are resolved
    through the module at call time, because that is where tests and the eval
    harness patch them. ``ask`` is the module's own ``call_llm`` site,
    ``ask(spec, prompt, cfg, language_id)`` — it stays in the judge module so
    each ``max_tokens`` cap sits next to the measurement that justifies it.
    """
    name: str                        # prefix in log lines and fail-closed errors
    module: str
    task_name: str                   # label in llm_calls
    pt_name: str                     # task_name in prompt_templates
    ask: Callable[..., object]
    pipeline: str = 'vocab_ladder'
    response_format: str = 'json'
    provider: str | None = None      # None = the prompt_templates row's provider
    numeric_entries: bool = False    # entries keyed 0=rating, 1=reason (TASK-537)
    keyed_cache: bool = False        # cache on (pt_name, language_id), not language_id
    expect_dict: bool = True
    load_cfg: Callable[..., dict] | None = None


@dataclass
class JudgeReply:
    """Outcome of one judge round-trip. ``ok`` is False on every fail-open path."""
    ok: bool
    result: object = None
    model: str = 'unknown'
    version: int = 0
    error: str = ''


def numbered(items) -> str:
    """``1. first\\n2. second`` — the candidate list every judge prompt takes."""
    return '\n'.join(f'{i + 1}. {item}' for i, item in enumerate(items))


def llm_call_kwargs(spec: JudgeSpec, cfg: dict, language_id: int) -> dict:
    """The ``call_llm`` keyword arguments common to every judge call."""
    return {
        'model': cfg['model'],
        'temperature': 0.0,
        'response_format': spec.response_format,
        'provider': spec.provider or cfg['provider'],
        'pipeline': spec.pipeline,
        'task_name': spec.task_name,
        'template_version': cfg['version'],
        'language_code': LANG_ID_TO_CODE.get(language_id),
    }


def _load_cfg(spec: JudgeSpec, db, language_id: int) -> dict:
    if spec.load_cfg is not None:
        return spec.load_cfg(db, language_id)
    mod = sys.modules[spec.module]
    key = (spec.pt_name, language_id) if spec.keyed_cache else language_id
    if key not in mod._cfg_cache:
        mod._cfg_cache[key] = mod.get_template_config(db, spec.pt_name, language_id)
    return mod._cfg_cache[key]


def ask_judge(
    spec: JudgeSpec, db, language_id: int, build_prompt: Callable[[str], str],
    fallback_model: str | None = None,
) -> JudgeReply:
    """Load the template, build the prompt, call the model. Never raises for a
    judge outage: every failure is logged and returned as ``ok=False`` with
    the reason, for the caller to fail open (or closed, in batch mode) on.
    """
    try:
        cfg = _load_cfg(spec, db, language_id)
    except Exception as exc:
        logger.warning(
            "%s: template load failed for lang=%d, fail-open: %s",
            spec.name, language_id, exc,
        )
        return JudgeReply(False, model=fallback_model or 'unknown',
                          error=f'template load error: {exc}')

    prompt = build_prompt(cfg['template'])
    model, version = cfg.get('model', 'unknown'), cfg.get('version', 0)

    try:
        result = spec.ask(spec, prompt, cfg, language_id)
    except Exception as exc:
        logger.warning(
            "%s: LLM call failed for lang=%d, fail-open: %s",
            spec.name, language_id, exc,
        )
        return JudgeReply(False, None, model, version, f'llm call error: {exc}')

    if spec.expect_dict and not isinstance(result, dict):
        logger.warning(
            "%s: non-dict response (%s), fail-open", spec.name, type(result).__name__,
        )
        return JudgeReply(False, None, model, version, 'non-dict judge response')

    return JudgeReply(True, result, model, version)


def _read_rating(spec: JudgeSpec, result: dict, index: int):
    """``(rating, reason, gap)`` for the 0-based ``index``-th item.

    ``rating`` is None when the entry is missing or its rating unparseable;
    ``gap`` then says which. The top level is always keyed by 1-based number.
    """
    if spec.numeric_entries:
        from services.exercise_generation.schemas import (
            JUDGE_RATING_KEY, JUDGE_REASON_KEY, read_index,
        )
        entry = read_index(result, index + 1)
        if not isinstance(entry, dict):
            return None, '', 'missing per-sentence verdict'
        raw_rating = read_index(entry, JUDGE_RATING_KEY)
        raw_reason = read_index(entry, JUDGE_REASON_KEY) or ''
    else:
        entry = result.get(str(index + 1))
        if not isinstance(entry, dict):
            return None, '', 'missing per-sentence verdict'
        raw_rating = entry.get('rating')
        raw_reason = entry.get('reason', '')
    try:
        rating = float(raw_rating)
    except (TypeError, ValueError):
        return None, '', 'unparseable rating'
    return rating, str(raw_reason)[:200], ''


def log_verdict(spec: JudgeSpec, model: str, verdict: str, confidence) -> None:
    sys.modules[spec.module].log_judge_verdict(
        task_name=spec.task_name, model=model, verdict=verdict,
        confidence=confidence, pipeline=spec.pipeline,
    )


def log_worst_verdict(spec: JudgeSpec, model: str, outcomes: list[JudgeOutcome]) -> None:
    """One llm_calls row per call carrying the worst verdict — the binding
    signal for the item as a whole — so the smoke-test query can count
    accept/flag/reject by task_name."""
    worst = min(outcomes, key=lambda o: VERDICT_ORDER.get(o.verdict, 2))
    log_verdict(spec, model, worst.verdict, worst.confidence)


def run_likert_judge(
    spec: JudgeSpec, db, language_id: int, n: int, build_prompt: Callable[[str], str],
) -> list[JudgeOutcome]:
    """One index-aligned ``JudgeOutcome`` per item, ``confidence`` = the raw
    1-5 rating. Any judge outage yields ``safe_accept()`` for every item.
    """
    from services.test_generation.schemas import likert_to_verdict

    reply = ask_judge(spec, db, language_id, build_prompt)
    if not reply.ok:
        return [safe_accept(reply.error) for _ in range(n)]

    outcomes: list[JudgeOutcome] = []
    for i in range(n):
        rating, reason, gap = _read_rating(spec, reply.result, i)
        if rating is None:
            # A missing or malformed per-item verdict must never manufacture
            # a rejection — keep the item and move on.
            outcomes.append(accept_item(gap))
            continue
        outcomes.append(JudgeOutcome(
            verdict=likert_to_verdict(rating), confidence=rating, reason=reason,
        ))

    log_worst_verdict(spec, reply.model, outcomes)
    return outcomes


def run_candidate_judge(
    spec: JudgeSpec, db, language_id: int, candidates: list[str],
    build_prompt: Callable[[str], str],
) -> dict:
    """Run a numbered-candidate Likert prompt.

    Returns::

        {'verdicts': {cand: 'accept'|'flag'|'reject'},   # likert_to_verdict
         'ratings':  {cand: float},                       # raw 1-5 Likert
         'reasons':  {cand: str},
         'model': ..., 'version': ..., 'ok': bool}

    ``ok`` is False on any fail-open path; every candidate is then reported as
    ``accept`` at the keep rating so nothing is dropped on an outage. Inside
    ``batch_mode()`` that path raises instead (TASK-510). A missing or
    unparseable per-candidate rating never manufactures a ``reject`` — it maps
    to ``flag`` (keep), per the v3 Likert contract.
    """
    from services.test_generation.schemas import likert_to_verdict

    reply = ask_judge(spec, db, language_id, build_prompt)
    if not reply.ok:
        guard_fail_open(spec.name, f'model={reply.model!r} version={reply.version}')
        return {
            'verdicts': {c: 'accept' for c in candidates},
            'ratings': {c: KEEP_RATING for c in candidates},
            'reasons': {c: '' for c in candidates},
            'model': reply.model, 'version': reply.version, 'ok': False,
        }

    verdicts: dict[str, str] = {}
    ratings: dict[str, float] = {}
    reasons: dict[str, str] = {}
    for idx, candidate in enumerate(candidates):
        rating, reason, _gap = _read_rating(spec, reply.result, idx)
        if rating is None:
            verdicts[candidate], ratings[candidate], reasons[candidate] = 'flag', 3.0, ''
            continue
        verdicts[candidate] = likert_to_verdict(rating)
        ratings[candidate] = rating
        reasons[candidate] = reason

    return {
        'verdicts': verdicts, 'ratings': ratings, 'reasons': reasons,
        'model': reply.model, 'version': reply.version, 'ok': True,
    }


def run_keep_reject_judge(
    spec: JudgeSpec, db, language_id: int, items: list[str],
    build_prompt: Callable[[str], str], fallback_model: str | None = None,
) -> dict:
    """Run a numbered prompt whose entries carry a ``verdict`` of keep/reject.

    Returns ``{'verdicts': {item: 'keep'|'reject'}, 'reasons': {item: str},
    'model': ..., 'version': ...}``. Any outage keeps every item — or, inside
    ``batch_mode()``, raises: an unreachable judge must abort the batch, not
    silently ship unjudged content (TASK-510).
    """
    reply = ask_judge(spec, db, language_id, build_prompt, fallback_model)
    if not reply.ok:
        guard_fail_open(spec.name, f'model={reply.model!r} version={reply.version}')
        return {
            'verdicts': {d: 'keep' for d in items},
            'reasons': {d: '' for d in items},
            'model': reply.model, 'version': reply.version,
        }

    verdicts: dict[str, str] = {}
    reasons: dict[str, str] = {}
    for idx, item in enumerate(items):
        entry = reply.result.get(str(idx + 1)) or {}
        if not isinstance(entry, dict):
            verdicts[item], reasons[item] = 'keep', ''
            continue
        verdict = str(entry.get('verdict', 'keep')).strip().lower()
        verdicts[item] = 'reject' if verdict == 'reject' else 'keep'
        reasons[item] = str(entry.get('reason', ''))[:200]

    return {
        'verdicts': verdicts, 'reasons': reasons,
        'model': reply.model, 'version': reply.version,
    }


def split_rejected(items: list[str], judged: dict, **extra) -> tuple[list[str], dict]:
    """``(kept, judge_meta)``: drop only the items whose verdict is ``reject``.

    ``judge_meta`` is the generalized sidecar lifted into ``exercises.tags``.
    """
    verdicts = judged['verdicts']
    rejected = [i for i in items if verdicts.get(i) == 'reject']
    kept = [i for i in items if verdicts.get(i) != 'reject']
    return kept, {
        'rejected': len(rejected), 'kept': len(kept), 'rejected_items': rejected,
        **extra, 'model': judged['model'], 'version': judged['version'],
    }


def empty_meta() -> dict:
    return {
        'rejected': 0, 'kept': 0, 'rejected_items': [],
        'model': 'unknown', 'version': 0,
    }


def candidate_outcome(judged: dict, candidate: str) -> JudgeOutcome:
    """The single-candidate ``JudgeOutcome`` out of a ``run_candidate_judge`` result."""
    return JudgeOutcome(
        verdict=judged['verdicts'].get(candidate, 'flag'),
        confidence=judged['ratings'].get(candidate, KEEP_RATING),
        reason=judged['reasons'].get(candidate, ''),
    )
