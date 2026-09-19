"""
A mock LLM client for the exercise-lab sandbox.

WHY THIS EXISTS
----------------
This sandbox's hardest rule is: never make a real LLM/OpenRouter API call.
But a prototype generation pipeline needs *something* shaped like an LLM
client to call, so its plumbing (prompt building, response parsing, retry
logic, judge wiring) can be written and timed without depending on that
call being real. This module is that stand-in, with three modes:

  - "replay":   deterministic playback from a prompt-hash-keyed fixture
                cache on disk (lab/fixtures/mock_llm_cache.json). Use this
                to regression-test a prompt/parser change against a FROZEN
                prior response, or to replay a real recorded conversation
                without spending money to re-run it.
  - "synthetic": returns instantly-generated, structurally-plausible fake
                text with no real linguistic content. Use this for
                latency/throughput/architecture testing where content
                quality is irrelevant - see lab/harness.py's "single-item
                latency vs batch throughput" split, which this mode is
                built to exercise cheaply and repeatably.
  - "live":     a stub that RAISES unless BOTH an explicit constructor flag
                AND an environment variable are set. A later agent may wire
                a real OpenRouter call in here, metered against
                `usd_ceiling`, but only deliberately: the project's total
                remaining OpenRouter budget for this whole effort is
                **$6.31**, not per-run, so "live" must be nearly impossible
                to trigger by accident.

# FIDELITY GAP: "synthetic" mode content is template-filled placeholder
# text (see _synthesize below) - it is not linguistically valid in any
# language and must never be shown to a real learner, scored for content
# quality, or counted as a data point about exercise quality. It is only
# valid for timing/plumbing measurements.

# FIDELITY GAP: token counts are estimated as len(text)//4 (a common rough
# heuristic), not computed with any real tokenizer (no tiktoken/model
# tokenizer is wired in). Cost estimates derived from this are therefore
# order-of-magnitude, not exact - fine for comparing two pipelines'
# relative cost, not fine for reconciling against a real OpenRouter bill.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, Optional

Mode = Literal["replay", "synthetic", "live"]

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"
DEFAULT_CACHE_PATH = FIXTURE_DIR / "mock_llm_cache.json"

# Rough, illustrative-only per-token pricing (order of magnitude of a cheap
# hosted model). NOT tied to any real OpenRouter rate card - see FIDELITY GAP
# above. Only used to produce comparable, consistent cost estimates across
# runs of this sandbox.
_USD_PER_1K_TOKENS_IN = 0.0002
_USD_PER_1K_TOKENS_OUT = 0.0006

# The real, hard project-wide ceiling this module exists partly to protect,
# quoted here so anyone reading the code sees the number, not just the docstring.
PROJECT_OPENROUTER_BUDGET_USD = 6.31


class LiveCallDisabledError(RuntimeError):
    """Raised whenever 'live' mode is used without explicit, double opt-in."""


class BudgetExceededError(RuntimeError):
    """Raised when a call would push cumulative estimated spend over usd_ceiling."""


def _hash_prompt(prompt: str, model: str) -> str:
    return hashlib.sha256(f"{model}::{prompt}".encode("utf-8")).hexdigest()


def _estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


@dataclass
class LLMResponse:
    text: str
    tokens_in: int
    tokens_out: int
    cost_usd: float
    latency_ms: float
    mode: Mode
    cache_hit: bool = False


@dataclass
class MockLLMClient:
    mode: Mode = "synthetic"
    cache_path: Path = field(default_factory=lambda: DEFAULT_CACHE_PATH)
    allow_live: bool = False
    usd_ceiling: Optional[float] = None
    synthetic_latency_ms: float = 5.0
    model: str = "mock/sandbox-model"

    def __post_init__(self) -> None:
        self._spent_usd = 0.0
        self._calls_made = 0
        self._cache: dict[str, str] = {}
        if self.mode == "replay":
            self._load_cache()

    def _load_cache(self) -> None:
        if self.cache_path.exists():
            self._cache = json.loads(self.cache_path.read_text(encoding="utf-8"))
        else:
            self._cache = {}

    def save_cache(self) -> None:
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.cache_path.write_text(
            json.dumps(self._cache, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def record_fixture(self, prompt: str, response_text: str) -> None:
        """Populate the replay cache with a known prompt/response pair
        (e.g. one captured from a real, already-paid-for run elsewhere)."""
        key = _hash_prompt(prompt, self.model)
        self._cache[key] = response_text

    def spent_usd(self) -> float:
        return self._spent_usd

    def calls_made(self) -> int:
        return self._calls_made

    def complete(self, prompt: str, *, max_tokens: int = 256) -> LLMResponse:
        t0 = time.perf_counter()
        tokens_in = _estimate_tokens(prompt)

        if self.mode == "live":
            if not (self.allow_live and os.environ.get("EXERCISE_LAB_ALLOW_LIVE_LLM") == "1"):
                raise LiveCallDisabledError(
                    "mock_llm 'live' mode requires BOTH allow_live=True on the "
                    "client AND the EXERCISE_LAB_ALLOW_LIVE_LLM=1 environment "
                    "variable. This is deliberately hard to trigger by accident: "
                    f"the project's total remaining OpenRouter budget is "
                    f"${PROJECT_OPENROUTER_BUDGET_USD} for the WHOLE project, not "
                    "per-run. See lab/mock_llm.py module docstring."
                )
            raise NotImplementedError(
                "live mode is an intentional stub. A later agent must wire a "
                "real OpenRouter call here, hard-metered against usd_ceiling, "
                "before this branch can return real content. Nothing in this "
                "sandbox task authorizes making that call."
            )

        if self.mode == "replay":
            key = _hash_prompt(prompt, self.model)
            if key not in self._cache:
                raise KeyError(
                    f"No replay fixture for this prompt (hash={key[:12]}...). "
                    "Call record_fixture(prompt, response_text) first, or use "
                    "mode='synthetic' if exact content doesn't matter."
                )
            text = self._cache[key]
            cache_hit = True
        else:  # synthetic
            text = self._synthesize(prompt)
            cache_hit = False
            if self.synthetic_latency_ms:
                time.sleep(self.synthetic_latency_ms / 1000.0)

        tokens_out = _estimate_tokens(text)
        cost = (tokens_in / 1000) * _USD_PER_1K_TOKENS_IN + (
            tokens_out / 1000
        ) * _USD_PER_1K_TOKENS_OUT
        if self.usd_ceiling is not None and self._spent_usd + cost > self.usd_ceiling:
            raise BudgetExceededError(
                f"This call (${cost:.6f}) would push cumulative spend "
                f"(${self._spent_usd:.6f}) past the ceiling (${self.usd_ceiling:.6f})."
            )
        self._spent_usd += cost
        self._calls_made += 1
        latency_ms = (time.perf_counter() - t0) * 1000
        return LLMResponse(
            text=text,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_usd=cost,
            latency_ms=latency_ms,
            mode=self.mode,
            cache_hit=cache_hit,
        )

    @staticmethod
    def _synthesize(prompt: str) -> str:
        """Instant, structurally-plausible, LINGUISTICALLY MEANINGLESS output.
        Seeded from the prompt's own hash so the same prompt always produces
        the same synthetic output (deterministic, reproducible timing runs)."""
        digest = hashlib.md5(prompt.encode("utf-8")).hexdigest()[:8]
        payload: dict[str, Any] = {
            "_synthetic": True,
            "_seed": digest,
            "sentences": [f"[synthetic sentence {i} seed={digest}]" for i in range(3)],
            "distractors": [f"[synthetic distractor {i} seed={digest}]" for i in range(3)],
        }
        return json.dumps(payload, ensure_ascii=False)
