"""Lightweight stage-timing helper for generation pipelines.

Not a metrics/observability system — just a way to answer "where did the
wall clock go" for the sense/ladder and test-gen batch pipelines without
wiring up a new dependency. Timings are collected into a plain dict the
caller already owns and prints/stores wherever that caller already reports
its results (canary output, per-test batch log lines, etc.).

    stages: dict[str, float] = {}
    with stage('p1_generate', stages):
        core_asset = p1_gen.generate(...)
    ...
    result['stage_seconds'] = stages
"""

from __future__ import annotations

import logging
import time
from contextlib import contextmanager
from typing import Iterator

logger = logging.getLogger(__name__)


@contextmanager
def stage(name: str, bucket: dict) -> Iterator[None]:
    """Time a block, adding its duration (seconds) to ``bucket[name]``.

    Accumulates rather than overwrites: a stage entered more than once in the
    same run (e.g. a repair pass re-entering 'p1_judge') sums across calls,
    so the bucket's total stays an honest wall-clock breakdown.
    """
    t0 = time.time()
    try:
        yield
    finally:
        bucket[name] = bucket.get(name, 0.0) + (time.time() - t0)


def log_stage_seconds(
    stages: dict,
    *,
    pipeline: str,
    language_code: str | None = None,
    artifact_id: str | None = None,
    run_id: str | None = None,
) -> None:
    """Persist a completed ``stage()`` bucket to generation_stage_timings.

    One row per stage name in ``stages`` — NOT one row per LLM call inside
    that stage (``llm_calls`` already has call-level granularity via
    services.llm_service.call_llm's ``language_code``/``pipeline``/
    ``task_name``). This is the wall-clock complement: DB writes, audio
    synthesis, tokenization, non-LLM validation — everything a stage spans
    that isn't itself an LLM round-trip.

    Mirrors services.llm_service._log_llm_call's contract: best-effort,
    batched into one call per artifact rather than per stage() exit (a test
    or sense build has a handful of stages, not hundreds — no need for a DB
    round-trip inside the hot loop), and never raises. A failure here must
    never break the generation pipeline it is only trying to observe.
    """
    if not stages:
        return
    try:
        from services.supabase_factory import get_supabase_admin, get_supabase
        client = get_supabase_admin() or get_supabase()
        if client is None:
            return
        rows = [
            {
                'pipeline': pipeline,
                'stage_name': stage_name,
                'language_code': language_code,
                'artifact_id': artifact_id,
                'run_id': run_id,
                'duration_ms': int(round(duration_seconds * 1000)),
            }
            for stage_name, duration_seconds in stages.items()
        ]
        client.table('generation_stage_timings').insert(rows).execute()
    except Exception as exc:
        # Observability must never break the calling pipeline.
        logger.warning("generation_stage_timings logging failed: %s", exc)
