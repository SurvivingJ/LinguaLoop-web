"""
Three variants, each implementing lab/harness.py's Generator protocol
(`generate(sense) -> list[ExerciseRow]`, optional `last_call_stats()`), so
`run_harness()` can measure and compare them directly.

  (a) FatSeedOneCallGenerator   -- ONE fat call, Phase A only in .generate();
                                   call .run_phase_b_for_all() afterwards.
  (b) FatSeedTwoCallGenerator   -- TWO parallel calls (correct-content +
                                   wrong-content), latency = max not sum.
  (c) LegacyFanoutGenerator     -- the ~10-call fan-out CONTROL baseline:
                                   1 sequential P1 call, 1 sequential P1
                                   judge call, then a concurrent fan-out of
                                   P2/P3/L4/L8/typed calls (latency = max of
                                   the fan-out, not sum). Old architecture:
                                   judges are inline, so there is no separate
                                   async Phase B for this variant -- content
                                   is already servable when generation ends.

LATENCY MODEL: each mock_llm call sleeps for `synthetic_latency_ms` (a real
`time.sleep`), so the harness's own wall-clock measurement organically
reflects true thread concurrency (parallel calls really overlap). To keep an
actual test run fast, `synthetic_latency_ms` is set to a small NOMINAL value
during measurement (see docs/results-fat-seed.md methodology) and the
resulting call-count / concurrency STRUCTURE is measured for real; the
seconds-per-call ASSUMPTION is applied afterwards, analytically, as a
sensitivity sweep (2s / 5s / 12s per call) -- this prototype does not have a
real per-call latency number (checked `fixtures/live_responses/`: it exists
but is EMPTY as of this run, so no real OpenRouter measurement was available
to use instead).
"""
from __future__ import annotations

import sys
from pathlib import Path

_LAB_ROOT = Path(__file__).resolve().parents[2]
if str(_LAB_ROOT) not in sys.path:
    sys.path.insert(0, str(_LAB_ROOT))

from lab.mock_llm import MockLLMClient  # noqa: E402
from lab.models import ExerciseRow, SenseRow  # noqa: E402

from prototypes.fat_seed import prompt_builder as pb  # noqa: E402
from prototypes.fat_seed.pipeline import PhaseAResult, PhaseBResult, run_phase_a, run_phase_b  # noqa: E402
from prototypes.fat_seed.seed_schema import FatSeed  # noqa: E402
from prototypes.fat_seed.synth_seed import synthesize_fat_seed  # noqa: E402


class _BaseVariant:
    """Shared bookkeeping: sibling pool for L2 distractors, and per-sense
    Phase A / Phase B results kept alongside the harness's own report so
    time-to-generated / time-to-servable can be reported separately."""

    def __init__(self, synthetic_latency_ms: float = 20.0):
        self.client = MockLLMClient(mode="synthetic", synthetic_latency_ms=synthetic_latency_ms)
        self.sibling_pool: list[FatSeed] = []
        self.phase_a_results: dict[int, PhaseAResult] = {}
        self.phase_b_results: dict[int, PhaseBResult] = {}
        self._last_stats = (0, 0, 0, 0.0)

    def last_call_stats(self):
        return self._last_stats

    def run_phase_b_for_all(self) -> None:
        """Call after a full harness batch: async Phase B, one batched judge
        call per sense, using the SAME synthetic-latency client."""
        for sense_id, pa in self.phase_a_results.items():
            self.phase_b_results[sense_id] = run_phase_b(pa.seed, pa.rows, self.client)


class FatSeedOneCallGenerator(_BaseVariant):
    """Variant (a): ONE fat call."""
    name = "fat_seed_one_call"

    def generate(self, sense: SenseRow) -> list[ExerciseRow]:
        seed = synthesize_fat_seed(sense, seed_variant_tag="a")
        prompt = pb.build_fat_seed_prompt(sense.lemma, sense.language_id, sense.part_of_speech)
        result = run_phase_a(seed, self.client, prompt, sibling_pool=self.sibling_pool)
        self.sibling_pool.append(seed)
        self.phase_a_results[sense.sense_id] = result
        self._last_stats = (result.llm_calls, result.tokens_in, result.tokens_out, result.cost_usd)
        return result.rows


class FatSeedTwoCallGenerator(_BaseVariant):
    """Variant (b): TWO parallel calls (correct-content + wrong-content)."""
    name = "fat_seed_two_call"

    def generate(self, sense: SenseRow) -> list[ExerciseRow]:
        seed = synthesize_fat_seed(sense, seed_variant_tag="b")
        p_correct = pb.build_correct_content_prompt(sense.lemma, sense.language_id, sense.part_of_speech)
        p_wrong = pb.build_wrong_content_prompt(sense.lemma, sense.language_id, sense.part_of_speech)
        result = run_phase_a(
            seed, self.client, p_correct, sibling_pool=self.sibling_pool,
            extra_prompt_for_parallel_call=p_wrong,
        )
        self.sibling_pool.append(seed)
        self.phase_a_results[sense.sense_id] = result
        self._last_stats = (result.llm_calls, result.tokens_in, result.tokens_out, result.cost_usd)
        return result.rows


class LegacyFanoutGenerator(_BaseVariant):
    """Variant (c): the ~10-call fan-out CONTROL baseline, modelling today's
    real architecture's round-trip shape (recon-generation.md §2,§6):
    1 sequential P1 call, 1 sequential P1-sentence-judge call, then a
    concurrent fan-out of P2/P3/L4/L8/typed calls (latency=max, calls=all).
    Old architecture: judges run inline during generation, so there is no
    separate async Phase B here -- .generate() IS time-to-servable already.
    Produces the SAME synthesized content as (a)/(b) (this prototype is
    comparing round-trip cost/latency of reaching that content, not content
    quality, which the mock LLM cannot meaningfully differ on anyway)."""
    name = "legacy_fanout_control"

    def generate(self, sense: SenseRow) -> list[ExerciseRow]:
        import concurrent.futures as cf
        import time as _time

        seed = synthesize_fat_seed(sense, seed_variant_tag="c")
        t0 = _time.perf_counter()
        llm_calls = 0
        tokens_in = tokens_out = 0
        cost = 0.0

        r = self.client.complete(pb.build_legacy_p1_prompt(sense.lemma, sense.language_id))
        llm_calls += 1
        tokens_in += r.tokens_in
        tokens_out += r.tokens_out
        cost += r.cost_usd

        r = self.client.complete(pb.build_legacy_p1_judge_prompt(sense.lemma, sense.language_id))
        llm_calls += 1
        tokens_in += r.tokens_in
        tokens_out += r.tokens_out
        cost += r.cost_usd

        fanout_prompts = pb.build_legacy_fanout_prompts(sense.lemma, sense.language_id)
        with cf.ThreadPoolExecutor(max_workers=12) as ex:
            futures = [ex.submit(self.client.complete, p) for p in fanout_prompts]
            responses = [f.result() for f in futures]
        llm_calls += len(responses)
        tokens_in += sum(x.tokens_in for x in responses)
        tokens_out += sum(x.tokens_out for x in responses)
        cost += sum(x.cost_usd for x in responses)

        rows, skips = None, None
        from prototypes.fat_seed.render import render_all_for_seed
        rows, skips = render_all_for_seed(seed, self.sibling_pool)
        self.sibling_pool.append(seed)

        latency_ms = (_time.perf_counter() - t0) * 1000
        pa = PhaseAResult(
            seed=seed, seed_valid=True, rows=rows, skips=skips, latency_ms=latency_ms,
            llm_calls=llm_calls, tokens_in=tokens_in, tokens_out=tokens_out, cost_usd=cost,
        )
        self.phase_a_results[sense.sense_id] = pa
        # No async Phase B for the control -- content is already servable.
        self.phase_b_results[sense.sense_id] = PhaseBResult(0.0, 0, 0, 0, 0.0, promoted=True)
        self._last_stats = (llm_calls, tokens_in, tokens_out, cost)
        return rows
