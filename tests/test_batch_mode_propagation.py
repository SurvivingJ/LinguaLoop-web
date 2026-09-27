"""Batch mode must survive a thread boundary (fail-closed judging).

TASK-510 made judges fail *closed* inside a generation batch via a
thread-local flag. Thread-local is right — a batch must not flip the contract
for a request thread in the same process — but it meant work handed to a
worker pool ran on threads that had never entered ``batch_mode()``. Judges
called from there fell back to fail-open and rubber-stamped unjudged content,
which is the bug TASK-510 was written to kill.

Measured before the fix, on the real pipeline:

    outer thread      in batch_mode: True
    inner pool thread in batch_mode: False
    judge outage on pool thread -> FAIL-OPEN (accepted unjudged content)
    judge outage on outer thread -> fail-closed (raised)

Only P1 ran on the outer thread, so P2, P3, the split levels and the typed-LLM
generators — the bulk of every sense — were unguarded.

These tests pin both halves of the fix: the flag now crosses into workers, and
a ``JudgeUnavailable`` raised there is not swallowed on the way back out.
"""

import threading
from concurrent.futures import ThreadPoolExecutor

import pytest

from services.exercise_generation.judges.base import (
    BatchModeThreadPoolExecutor,
    JudgeUnavailable,
    batch_mode,
    bind_batch_mode,
    guard_fail_open,
    is_batch_mode,
    safe_accept,
)


# ---------------------------------------------------------------------------
# bind_batch_mode
# ---------------------------------------------------------------------------

def test_bind_captures_flag_at_wrap_time_not_call_time():
    """The snapshot is taken where submit happens, not where the work runs."""
    with batch_mode():
        bound = bind_batch_mode(is_batch_mode)

    # Wrapped inside the block, invoked outside it: still fail-closed.
    assert bound() is True


def test_bind_outside_batch_stays_fail_open():
    bound = bind_batch_mode(is_batch_mode)
    with batch_mode():
        # Wrapped outside the block, invoked inside it: still fail-open. The
        # flag follows the submitting context, which is the batch boundary.
        assert bound() is False


def test_bind_restores_previous_value_on_the_worker():
    seen = {}

    def _work():
        seen['inside'] = is_batch_mode()

    with batch_mode():
        bound = bind_batch_mode(_work)

    t = threading.Thread(target=bound)
    t.start()
    t.join()

    assert seen['inside'] is True
    # The calling thread was never in batch mode and must not have been left in it.
    assert is_batch_mode() is False


def test_bind_preserves_function_identity():
    def judge_something():
        """Docstring survives."""

    bound = bind_batch_mode(judge_something)
    assert bound.__name__ == 'judge_something'
    assert bound.__doc__ == 'Docstring survives.'


# ---------------------------------------------------------------------------
# BatchModeThreadPoolExecutor
# ---------------------------------------------------------------------------

def test_plain_executor_loses_batch_mode():
    """The bug, pinned. If this ever fails, the stdlib changed under us."""
    with batch_mode():
        with ThreadPoolExecutor(max_workers=2) as pool:
            assert pool.submit(is_batch_mode).result() is False


def test_batch_mode_executor_carries_the_flag():
    with batch_mode():
        with BatchModeThreadPoolExecutor(max_workers=2) as pool:
            assert pool.submit(is_batch_mode).result() is True


def test_batch_mode_executor_is_inert_outside_a_batch():
    """Serve paths must keep fail-open: a dead judge cannot break a session."""
    with BatchModeThreadPoolExecutor(max_workers=2) as pool:
        assert pool.submit(is_batch_mode).result() is False


def test_flag_follows_the_submit_not_the_pool_construction():
    """Pool built outside the batch, submitted to from inside it."""
    pool = BatchModeThreadPoolExecutor(max_workers=2)
    try:
        assert pool.submit(is_batch_mode).result() is False
        with batch_mode():
            assert pool.submit(is_batch_mode).result() is True
        # Worker threads are reused; the flag must not stick to them.
        assert pool.submit(is_batch_mode).result() is False
    finally:
        pool.shutdown(wait=True)


def test_executor_passes_args_and_kwargs_through():
    with BatchModeThreadPoolExecutor(max_workers=2) as pool:
        fut = pool.submit(lambda a, b, c=0: (a, b, c), 1, 2, c=3)
        assert fut.result() == (1, 2, 3)


def test_executor_carries_flag_to_every_worker():
    """All 8 lanes, not just the first one to pick up work."""
    barrier = threading.Barrier(8)

    def _work():
        # Force all 8 threads to be live at once so none is a reused lane.
        barrier.wait(timeout=10)
        return is_batch_mode()

    with batch_mode():
        with BatchModeThreadPoolExecutor(max_workers=8) as pool:
            futures = [pool.submit(_work) for _ in range(8)]
            assert all(f.result() for f in futures)


# ---------------------------------------------------------------------------
# The judge chokepoints, exercised across the boundary
# ---------------------------------------------------------------------------

def test_safe_accept_fails_closed_on_a_worker():
    with batch_mode():
        with BatchModeThreadPoolExecutor(max_workers=2) as pool:
            fut = pool.submit(safe_accept, 'model 404')
            with pytest.raises(JudgeUnavailable):
                fut.result()


def test_guard_fail_open_fails_closed_on_a_worker():
    """collocation.py's dict-returning fail-open path shares the chokepoint."""
    with batch_mode():
        with BatchModeThreadPoolExecutor(max_workers=2) as pool:
            fut = pool.submit(guard_fail_open, 'collocation', 'template missing')
            with pytest.raises(JudgeUnavailable):
                fut.result()


def test_safe_accept_still_accepts_on_a_worker_when_serving():
    with BatchModeThreadPoolExecutor(max_workers=2) as pool:
        outcome = pool.submit(safe_accept, 'model 404').result()
    assert outcome.verdict == 'accept'


# ---------------------------------------------------------------------------
# asset_pipeline: the abort must not be swallowed on the way out
# ---------------------------------------------------------------------------

def test_asset_pipeline_uses_the_propagating_executor():
    """Guards against a refactor quietly restoring the bare executor."""
    from services.vocabulary_ladder import asset_pipeline as ap

    assert ap.BatchModeThreadPoolExecutor is BatchModeThreadPoolExecutor
    assert not hasattr(ap, 'ThreadPoolExecutor'), (
        'asset_pipeline imported the bare ThreadPoolExecutor again — its inner '
        'pool must use BatchModeThreadPoolExecutor or judges fail open'
    )


def test_generate_batch_reraises_judge_unavailable():
    """One dead judge aborts the run; it does not become 'sense failed'."""
    from services.vocabulary_ladder.asset_pipeline import VocabAssetPipeline

    pipeline = VocabAssetPipeline.__new__(VocabAssetPipeline)
    seen = []

    def _boom(sense_id, language_id, force=False, batch_id=None):
        seen.append(sense_id)
        raise JudgeUnavailable('distractor judge: model 404')

    pipeline.generate_for_sense = _boom

    with pytest.raises(JudgeUnavailable):
        pipeline.generate_batch([1, 2, 3], language_id=2)

    # Aborted on the first sense rather than grinding through the rest unjudged.
    assert seen == [1]


# ---------------------------------------------------------------------------
# Contextvars (Phase 0 cost instrumentation) — same boundary, different flag
# ---------------------------------------------------------------------------
#
# services.llm_service.generation_context binds sense_id/generation_batch_id
# via contextvars so every call_llm() nested under
# VocabAssetPipeline._generate_for_sense_impl logs them without every
# generator file threading two extra parameters through. Contextvars, unlike
# the thread-local batch_mode flag, propagate down a normal call stack for
# free — but NOT into a plain ThreadPoolExecutor worker, for the same reason
# batch_mode doesn't. BatchModeThreadPoolExecutor.submit was extended to also
# capture contextvars.copy_context() at submit time, generically (it knows
# nothing about llm_service's specific vars) — these tests pin that.

def test_plain_executor_loses_contextvars():
    """The bug this fix addresses, pinned for contextvars specifically."""
    import services.llm_service as svc

    with svc.generation_context(sense_id=42, generation_batch_id='batch-1'):
        with ThreadPoolExecutor(max_workers=2) as pool:
            seen_sense_id = pool.submit(svc._ctx_sense_id.get).result()
    assert seen_sense_id is None


def test_batch_mode_executor_carries_contextvars():
    import services.llm_service as svc

    with svc.generation_context(sense_id=42, generation_batch_id='batch-1'):
        with BatchModeThreadPoolExecutor(max_workers=2) as pool:
            sense_id = pool.submit(svc._ctx_sense_id.get).result()
            batch_id = pool.submit(svc._ctx_generation_batch_id.get).result()
    assert sense_id == 42
    assert batch_id == 'batch-1'


def test_contextvars_do_not_leak_back_to_the_submitting_thread():
    import services.llm_service as svc

    with BatchModeThreadPoolExecutor(max_workers=2) as pool:
        with svc.generation_context(sense_id=7):
            pool.submit(lambda: None).result()
        assert svc._ctx_sense_id.get() is None  # scope closed on this thread


def test_contextvars_and_batch_mode_both_cross_the_same_submit():
    """Both flags travel together through one submit — no interference."""
    import services.llm_service as svc

    with batch_mode(), svc.generation_context(sense_id=99):
        with BatchModeThreadPoolExecutor(max_workers=2) as pool:
            def _probe():
                return is_batch_mode(), svc._ctx_sense_id.get()

            batch_flag, sense_id = pool.submit(_probe).result()
    assert batch_flag is True
    assert sense_id == 99


def test_generate_batch_still_absorbs_ordinary_failures():
    """Only judge outages abort. A bad sense is still just a failed sense."""
    from services.vocabulary_ladder.asset_pipeline import VocabAssetPipeline

    pipeline = VocabAssetPipeline.__new__(VocabAssetPipeline)

    def _flaky(sense_id, language_id, force=False, batch_id=None):
        if sense_id == 2:
            raise RuntimeError('transient provider error')
        return {'sense_id': sense_id, 'status': 'success', 'errors': []}

    pipeline.generate_for_sense = _flaky

    out = pipeline.generate_batch([1, 2, 3], language_id=2)
    assert out['success'] == 2
    assert out['failed'] == 1
