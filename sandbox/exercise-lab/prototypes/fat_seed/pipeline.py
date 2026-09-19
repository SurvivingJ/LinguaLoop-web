"""
Two-Phase Promote: Phase A (blocking, <=10s target, writes is_active=false)
and Phase B (async, one batched judge call per sense, promotes to active).

CORRECTED UNDERSTANDING (per orchestrator): nothing provisional is ever
served. Phase A's output never reaches a learner until Phase B promotes it.
So the earlier draft's framing ("nothing synchronous catches bad content, a
real quality regression") was WRONG about where the safety net is -- the net
exists, it is just asynchronous. What IS real, and worth measuring
separately, is the gap between:

  TIME-TO-GENERATED: Phase A finishes, exercises exist as is_active=false.
                      This is the number held to the <=10s target.
  TIME-TO-SERVABLE:  Phase B's judge call has ALSO completed and promoted
                      the rows to is_active=true. This is the number that
                      determines when a learner can actually be served this
                      word -- and it is allowed to be async/slower, per the
                      user's stated requirement.

Phase B here is modelled as exactly what the design specifies: ONE batched
judge call per sense covering every rendered level at once (not one judge
call per level, which is today's real architecture and is instead what
variant (c)'s per-level judges approximate for the control baseline).
"""
from __future__ import annotations

import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

_LAB_ROOT = Path(__file__).resolve().parents[2]
if str(_LAB_ROOT) not in sys.path:
    sys.path.insert(0, str(_LAB_ROOT))

from lab.mock_llm import MockLLMClient  # noqa: E402
from lab.models import ExerciseRow, SenseRow  # noqa: E402

from prototypes.fat_seed.render import RenderSkip, render_all_for_seed  # noqa: E402
from prototypes.fat_seed.seed_schema import FatSeed, validate_fat_seed  # noqa: E402
from prototypes.fat_seed.synth_seed import synthesize_fat_seed  # noqa: E402


@dataclass
class PhaseAResult:
    seed: FatSeed
    seed_valid: bool
    rows: list[ExerciseRow]
    skips: list[RenderSkip]
    latency_ms: float
    llm_calls: int
    tokens_in: int
    tokens_out: int
    cost_usd: float


@dataclass
class PhaseBResult:
    latency_ms: float
    llm_calls: int
    tokens_in: int
    tokens_out: int
    cost_usd: float
    promoted: bool  # whether the batched judge accepted (vs rejected -> stays is_active=false forever)


def build_phase_b_prompt(seed: FatSeed, rows: list[ExerciseRow]) -> str:
    """ONE batched judge call per sense, covering every rendered level at
    once -- the design's other core idea, kept separate from Phase A's own
    seed-generation call(s)."""
    levels = ", ".join(sorted({r.exercise_type for r in rows}))
    return (
        f"[Phase B batched judge] Sense \"{seed.lemma}\" (language_id={seed.language_id}). "
        f"Review these {len(rows)} rendered exercises across types [{levels}] in ONE pass. "
        f"For each: is the wrong content actually wrong for its stated reason, is exactly "
        f"one option correct, is any distractor also defensibly correct? "
        f"Return accept/flag/reject per exercise. Strict JSON."
    )


def run_phase_a(
    seed: FatSeed, client: MockLLMClient, prompt_text: str,
    sibling_pool: Optional[list[FatSeed]] = None,
    extra_prompt_for_parallel_call: Optional[str] = None,
) -> PhaseAResult:
    """Runs the seed call(s) + render + structural validation. If
    `extra_prompt_for_parallel_call` is given (variant b), both calls are
    fired and timed as latency=max(call1, call2), calls=2 -- true parallel
    latency, not summed."""
    t0 = time.perf_counter()
    llm_calls = 0
    tokens_in = tokens_out = 0
    cost = 0.0

    if extra_prompt_for_parallel_call is None:
        resp = client.complete(prompt_text)
        llm_calls += 1
        tokens_in += resp.tokens_in
        tokens_out += resp.tokens_out
        cost += resp.cost_usd
    else:
        import concurrent.futures as cf
        with cf.ThreadPoolExecutor(max_workers=2) as ex:
            f1 = ex.submit(client.complete, prompt_text)
            f2 = ex.submit(client.complete, extra_prompt_for_parallel_call)
            r1, r2 = f1.result(), f2.result()
        llm_calls += 2
        tokens_in += r1.tokens_in + r2.tokens_in
        tokens_out += r1.tokens_out + r2.tokens_out
        cost += r1.cost_usd + r2.cost_usd

    rows, skips = render_all_for_seed(seed, sibling_pool)
    validation = validate_fat_seed(seed)
    latency_ms = (time.perf_counter() - t0) * 1000
    return PhaseAResult(
        seed=seed, seed_valid=validation.passed, rows=rows, skips=skips,
        latency_ms=latency_ms, llm_calls=llm_calls,
        tokens_in=tokens_in, tokens_out=tokens_out, cost_usd=cost,
    )


def run_phase_b(seed: FatSeed, rows: list[ExerciseRow], client: MockLLMClient) -> PhaseBResult:
    t0 = time.perf_counter()
    if not rows:
        return PhaseBResult(0.0, 0, 0, 0, 0.0, promoted=False)
    prompt = build_phase_b_prompt(seed, rows)
    resp = client.complete(prompt)
    latency_ms = (time.perf_counter() - t0) * 1000
    return PhaseBResult(
        latency_ms=latency_ms, llm_calls=1, tokens_in=resp.tokens_in,
        tokens_out=resp.tokens_out, cost_usd=resp.cost_usd, promoted=True,
    )
