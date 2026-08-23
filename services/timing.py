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

import time
from contextlib import contextmanager
from typing import Iterator


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
