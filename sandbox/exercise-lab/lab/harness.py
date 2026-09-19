"""
The measurement harness: times and costs any "generator" without caring
what it does internally.

WHY THIS EXISTS
----------------
The whole point of this sandbox is "measure a new exercise-generation
pipeline against the old one" (see README). You cannot compare pipelines
without a common stopwatch and a common cost meter that neither pipeline
controls. This module is that stopwatch: it knows nothing about prompts,
judges, or asset tables - it calls `generator.generate(sense)`, times it,
reads back whatever telemetry the generator chose to report, and aggregates.

Reports BOTH single-sense latency and batch throughput under concurrency,
because they answer different questions and the task brief explicitly
warns against collapsing them:
  - single-item latency (p50/p95/mean wall-clock per sense) is what "10
    seconds per word" means - can one word go from nothing to a rendered
    exercise inside a user-facing wait?
  - throughput (senses/minute at concurrency=N) is what a nightly batch job
    or a "backfill 25,000 senses" run cares about - and per
    docs/recon-generation.md §6, production's own batch driver deliberately
    caps concurrency low (OpenRouter rate limits, a shared cost-ceiling
    check that isn't safe to race). A pipeline can have poor single-item
    latency but still hit a throughput target via concurrency, or the
    reverse (fast per item, but serialized by a shared limit) - reporting
    only one number would hide which lever a later agent actually needs to
    pull.

# FIDELITY GAP: concurrency here is threads in one Python process talking to
# lab/mock_llm.py, which never makes a real network call. It measures the
# GENERATOR'S OWN logic/overhead accurately, but says nothing about real
# provider rate limits, real network latency variance, or the cross-run
# budget-ceiling race documented in docs/recon-generation.md §6
# ("three concurrent runs trip each other's ceilings on each other's
# spend"). A later agent wiring live calls must re-measure concurrency
# behavior against the real provider, not trust this harness's throughput
# number as a live-system prediction.
"""
from __future__ import annotations

import concurrent.futures as cf
import statistics
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional, Protocol, Sequence

from lab.models import ExerciseRow, SenseRow


class Generator(Protocol):
    name: str

    def generate(self, sense: SenseRow) -> list[ExerciseRow]: ...


@dataclass
class SenseRunResult:
    sense_id: int
    lemma: str
    wall_clock_ms: float
    llm_calls: int
    tokens_in: int
    tokens_out: int
    cost_usd: float
    exercises_produced: int
    exercises_passing_validation: int
    error: Optional[str] = None


@dataclass
class HarnessReport:
    generator_name: str
    n_senses: int
    concurrency: int
    total_wall_clock_s: float
    single_item_latency_ms_p50: float
    single_item_latency_ms_p95: float
    single_item_latency_ms_mean: float
    throughput_senses_per_min: float
    total_llm_calls: int
    total_tokens_in: int
    total_tokens_out: int
    total_cost_usd: float
    total_exercises_produced: int
    total_exercises_passing: int
    validation_pass_rate: float
    errors: int
    per_sense: list[SenseRunResult] = field(default_factory=list)

    def to_json(self) -> str:
        import json

        return json.dumps(asdict(self), ensure_ascii=False, indent=2)

    def to_markdown(self) -> str:
        lines = [
            f"# Harness report: {self.generator_name}",
            "",
            f"- senses run: {self.n_senses}  (concurrency={self.concurrency})",
            f"- total wall clock: {self.total_wall_clock_s:.2f}s",
            (
                "- **single-item latency** (what \"10s/word\" means): "
                f"p50={self.single_item_latency_ms_p50:.0f}ms, "
                f"p95={self.single_item_latency_ms_p95:.0f}ms, "
                f"mean={self.single_item_latency_ms_mean:.0f}ms"
            ),
            (
                "- **batch throughput** (what a nightly backfill cares about): "
                f"{self.throughput_senses_per_min:.1f} senses/min at "
                f"concurrency={self.concurrency}"
            ),
            (
                f"- LLM calls: {self.total_llm_calls} "
                f"(tokens in={self.total_tokens_in}, out={self.total_tokens_out})"
            ),
            (
                f"- estimated cost: ${self.total_cost_usd:.4f} "
                f"(${self.total_cost_usd / max(self.n_senses, 1):.5f}/sense)"
            ),
            (
                f"- exercises produced: {self.total_exercises_produced}, "
                f"passing validation: {self.total_exercises_passing} "
                f"({self.validation_pass_rate * 100:.1f}%)"
            ),
            f"- errors: {self.errors}",
            "",
            "| sense_id | lemma | ms | llm_calls | cost_usd | produced | passing | error |",
            "|---|---|---|---|---|---|---|---|",
        ]
        for r in self.per_sense:
            lines.append(
                f"| {r.sense_id} | {r.lemma} | {r.wall_clock_ms:.1f} | {r.llm_calls} | "
                f"{r.cost_usd:.5f} | {r.exercises_produced} | "
                f"{r.exercises_passing_validation} | {r.error or ''} |"
            )
        return "\n".join(lines)


def _run_one(generator: Generator, sense: SenseRow) -> SenseRunResult:
    t0 = time.perf_counter()
    llm_calls = tokens_in = tokens_out = 0
    cost = 0.0
    produced = passing = 0
    error: Optional[str] = None
    try:
        exercises = generator.generate(sense)
        produced = len(exercises)
        passing = sum(1 for e in exercises if e.passed_validation)
        # A Generator MAY expose last_call_stats() -> (llm_calls, tokens_in,
        # tokens_out, cost_usd) describing the call(s) it just made. Purely
        # deterministic generators (no LLM at all) simply won't have one,
        # and telemetry stays at zero - that's a valid, expected value, not
        # a missing-data error.
        stats_fn = getattr(generator, "last_call_stats", None)
        if callable(stats_fn):
            llm_calls, tokens_in, tokens_out, cost = stats_fn()
    except Exception as exc:  # noqa: BLE001 - one bad sense must not kill the batch
        error = f"{type(exc).__name__}: {exc}"
    wall_clock_ms = (time.perf_counter() - t0) * 1000
    return SenseRunResult(
        sense_id=sense.sense_id,
        lemma=sense.lemma,
        wall_clock_ms=wall_clock_ms,
        llm_calls=llm_calls,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        cost_usd=cost,
        exercises_produced=produced,
        exercises_passing_validation=passing,
        error=error,
    )


def run_harness(
    generator: Generator, senses: Sequence[SenseRow], *, concurrency: int = 1
) -> HarnessReport:
    t_start = time.perf_counter()
    results: list[SenseRunResult] = []

    if concurrency <= 1:
        for s in senses:
            results.append(_run_one(generator, s))
    else:
        with cf.ThreadPoolExecutor(max_workers=concurrency) as ex:
            futures = [ex.submit(_run_one, generator, s) for s in senses]
            for fut in cf.as_completed(futures):
                results.append(fut.result())
        results.sort(key=lambda r: r.sense_id)

    total_wall = time.perf_counter() - t_start
    latencies = sorted(r.wall_clock_ms for r in results)
    n = len(results)
    errors = sum(1 for r in results if r.error)
    produced = sum(r.exercises_produced for r in results)
    passing = sum(r.exercises_passing_validation for r in results)

    return HarnessReport(
        generator_name=getattr(generator, "name", generator.__class__.__name__),
        n_senses=n,
        concurrency=concurrency,
        total_wall_clock_s=total_wall,
        single_item_latency_ms_p50=(statistics.median(latencies) if latencies else 0.0),
        single_item_latency_ms_p95=(
            latencies[min(len(latencies) - 1, int(0.95 * (len(latencies) - 1)))]
            if latencies
            else 0.0
        ),
        single_item_latency_ms_mean=(statistics.fmean(latencies) if latencies else 0.0),
        throughput_senses_per_min=((n / total_wall) * 60 if total_wall > 0 else 0.0),
        total_llm_calls=sum(r.llm_calls for r in results),
        total_tokens_in=sum(r.tokens_in for r in results),
        total_tokens_out=sum(r.tokens_out for r in results),
        total_cost_usd=sum(r.cost_usd for r in results),
        total_exercises_produced=produced,
        total_exercises_passing=passing,
        validation_pass_rate=(passing / produced) if produced else 0.0,
        errors=errors,
        per_sense=results,
    )


def write_report(report: HarnessReport, out_dir: Path, slug: str) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / f"{slug}.json"
    md_path = out_dir / f"{slug}.md"
    json_path.write_text(report.to_json(), encoding="utf-8")
    md_path.write_text(report.to_markdown(), encoding="utf-8")
    return json_path, md_path
