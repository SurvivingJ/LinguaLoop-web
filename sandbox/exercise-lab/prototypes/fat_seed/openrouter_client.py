"""
A minimal, sandbox-local OpenRouter chat-completions client, built
specifically for this metered live-LLM probe.

This is deliberately NOT `services/llm_service.py` (production code) and
does not import it. Reasons, per the task's hard rules:
  - `llm_service` freezes `OPENROUTER_API_KEY` at import time (project
    memory) and is wired into production logging (`llm_calls` table) and
    asset-writing paths this sandbox must never touch.
  - This client only ever POSTs to OpenRouter's public chat-completions
    endpoint and reads the key from the environment at CALL time via
    python-dotenv, the same convention the rest of the repo uses
    (`config.py:10-12` — `from dotenv import load_dotenv; load_dotenv()`).
    The key is never printed or logged anywhere in this module.

HARD BUDGET CAP
----------------
`RunBudget` is a running USD counter computed from REAL token usage
returned by OpenRouter (`response["usage"]`) times REAL per-token pricing
fetched live from `GET https://openrouter.ai/api/v1/models` (no auth
required, no cost) at process start. It hard-stops (raises
`BudgetExceededError`) the moment cumulative spend would reach the cap —
checked BEFORE every call using a conservative worst-case estimate
(prompt tokens + the call's max_tokens, both priced at the model's real
rate) so a single large call cannot overshoot the cap, and again
re-reconciled with the ACTUAL usage after the call returns.

CACHING
-------
Every real call is cached to `fixtures/live_responses/<sha256>.json`,
keyed by hash(model, prompt, max_tokens, temperature), BEFORE this
function returns. A second call with identical arguments is served from
the cache at zero cost and zero further spend — this is what makes the
$2 spend a reusable asset for peer agents (and for re-running this
script's own downstream scoring code without paying twice).
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import requests
from dotenv import load_dotenv

OPENROUTER_CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"

FIXTURE_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "live_responses"


class BudgetExceededError(RuntimeError):
    pass


class NoAPIKeyError(RuntimeError):
    pass


class ModelPriceUnknownError(RuntimeError):
    pass


def _hash_key(model: str, prompt: str, max_tokens: int, temperature: float) -> str:
    payload = f"{model}::{max_tokens}::{temperature}::{prompt}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def load_api_key() -> str:
    """Loads OPENROUTER_API_KEY via the repo's existing dotenv convention.
    Never prints or logs the key. Raises loudly if absent, per the hard
    rule: 'If no API key is available, STOP and report that.'"""
    load_dotenv()
    key = os.environ.get("OPENROUTER_API_KEY", "")
    if not key:
        raise NoAPIKeyError(
            "OPENROUTER_API_KEY not found in environment/.env. Per the task's "
            "hard rule, stopping rather than working around this."
        )
    return key


def fetch_model_pricing(model_ids: list[str]) -> dict[str, dict[str, float]]:
    """GET /models (free, no auth) and return {model_id: {"prompt": usd_per_token,
    "completion": usd_per_token}} for exactly the requested ids. Raises
    ModelPriceUnknownError for any id that doesn't resolve — per the hard
    rule 'If you cannot determine a model's price, do not call it.'"""
    resp = requests.get(OPENROUTER_MODELS_URL, timeout=30)
    resp.raise_for_status()
    data = resp.json().get("data", [])
    by_id = {m["id"]: m for m in data}
    out: dict[str, dict[str, float]] = {}
    missing = []
    for mid in model_ids:
        m = by_id.get(mid)
        if m is None:
            missing.append(mid)
            continue
        pricing = m.get("pricing", {})
        try:
            prompt_price = float(pricing["prompt"])
            completion_price = float(pricing["completion"])
        except (KeyError, TypeError, ValueError):
            missing.append(mid)
            continue
        if prompt_price < 0 or completion_price < 0:
            # OpenRouter uses -1 for "variable/auto" pricing on router
            # pseudo-models - we can't compute real cost for those.
            missing.append(mid)
            continue
        out[mid] = {"prompt": prompt_price, "completion": completion_price}
    if missing:
        raise ModelPriceUnknownError(
            f"Could not resolve real per-token pricing for: {missing}. "
            "Per the hard budget rule, refusing to call these models."
        )
    return out


@dataclass
class CallResult:
    model: str
    prompt: str
    text: str
    tokens_in: int
    tokens_out: int
    cost_usd: float
    latency_ms: float
    cache_hit: bool
    error: Optional[str] = None


@dataclass
class RunBudget:
    """Cumulative USD spend counter, computed from real usage x real price.
    Hard-stops at `cap_usd`. This is the ONLY object in this probe allowed
    to authorize a spend."""

    cap_usd: float
    pricing: dict[str, dict[str, float]]
    spent_usd: float = 0.0
    calls_made: int = 0
    calls_skipped_budget: int = 0
    _log: list[dict[str, Any]] = field(default_factory=list)

    def would_exceed(self, model: str, prompt_tokens_est: int, max_tokens: int) -> bool:
        price = self.pricing[model]
        worst_case = (
            prompt_tokens_est * price["prompt"] + max_tokens * price["completion"]
        )
        return (self.spent_usd + worst_case) > self.cap_usd

    def record(self, model: str, tokens_in: int, tokens_out: int) -> float:
        price = self.pricing[model]
        cost = tokens_in * price["prompt"] + tokens_out * price["completion"]
        self.spent_usd += cost
        self.calls_made += 1
        self._log.append(
            {
                "model": model,
                "tokens_in": tokens_in,
                "tokens_out": tokens_out,
                "cost_usd": cost,
                "cumulative_usd": self.spent_usd,
            }
        )
        return cost

    def print_status(self, label: str = "") -> None:
        print(
            f"[budget] {label} cumulative spend: ${self.spent_usd:.6f} / "
            f"${self.cap_usd:.2f} cap ({self.calls_made} calls made, "
            f"{self.calls_skipped_budget} skipped for budget)"
        )


def _estimate_tokens(text: str) -> int:
    # Rough pre-call estimate only, used for the pre-flight budget check.
    # The REAL cost recorded after the call uses OpenRouter's actual
    # `usage` field, not this estimate.
    return max(1, len(text) // 3)


def call_llm(
    model: str,
    prompt: str,
    budget: RunBudget,
    *,
    max_tokens: int = 3000,
    temperature: float = 0.4,
    timeout_s: float = 90.0,
    label: str = "",
) -> CallResult:
    """Cache-first, budget-gated single chat-completion call.

    Cache hit: returns instantly, zero cost, using the ORIGINAL recorded
    latency_ms (a real number from when the call actually happened) so
    latency statistics remain meaningful across re-runs of this script.

    Cache miss: budget-checks BEFORE calling (worst case: prompt tokens +
    max_tokens, both at real price), makes the real HTTP call, reconciles
    with real usage, updates `budget`, writes the cache file, prints
    cumulative spend.
    """
    key = _hash_key(model, prompt, max_tokens, temperature)
    cache_path = FIXTURE_DIR / f"{key}.json"

    if cache_path.exists():
        rec = json.loads(cache_path.read_text(encoding="utf-8"))
        return CallResult(
            model=model,
            prompt=prompt,
            text=rec["text"],
            tokens_in=rec["tokens_in"],
            tokens_out=rec["tokens_out"],
            cost_usd=0.0,  # already paid in a prior run
            latency_ms=rec["latency_ms"],
            cache_hit=True,
        )

    if model not in budget.pricing:
        raise ModelPriceUnknownError(
            f"No verified pricing loaded for {model!r}; refusing to call it."
        )

    prompt_tokens_est = _estimate_tokens(prompt)
    if budget.would_exceed(model, prompt_tokens_est, max_tokens):
        budget.calls_skipped_budget += 1
        return CallResult(
            model=model,
            prompt=prompt,
            text="",
            tokens_in=0,
            tokens_out=0,
            cost_usd=0.0,
            latency_ms=0.0,
            cache_hit=False,
            error="SKIPPED: would exceed hard budget cap",
        )

    api_key = load_api_key()
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://lingualoop.local/sandbox",
        "X-Title": "exercise-lab fat-seed probe",
    }
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": temperature,
    }

    t0 = time.perf_counter()
    error: Optional[str] = None
    text = ""
    tokens_in = tokens_out = 0
    try:
        resp = requests.post(
            OPENROUTER_CHAT_URL, headers=headers, json=body, timeout=timeout_s
        )
        latency_ms = (time.perf_counter() - t0) * 1000
        if resp.status_code != 200:
            error = f"HTTP {resp.status_code}: {resp.text[:500]}"
        else:
            data = resp.json()
            choices = data.get("choices") or []
            if choices:
                msg = choices[0].get("message", {})
                text = msg.get("content", "") or ""
            usage = data.get("usage", {}) or {}
            tokens_in = int(usage.get("prompt_tokens", prompt_tokens_est))
            tokens_out = int(usage.get("completion_tokens", _estimate_tokens(text)))
            if not text:
                error = f"EMPTY_RESPONSE: raw={json.dumps(data)[:500]}"
    except requests.RequestException as exc:
        latency_ms = (time.perf_counter() - t0) * 1000
        error = f"{type(exc).__name__}: {exc}"

    cost = 0.0
    if tokens_in or tokens_out:
        cost = budget.record(model, tokens_in, tokens_out)
    budget.print_status(label=label or model)

    # Cache even error responses' metadata is NOT written (only successful
    # text is worth replaying) - but we still return the CallResult so the
    # caller can see the error.
    if not error and text:
        FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(
            json.dumps(
                {
                    "model": model,
                    "prompt_sha256": key,
                    "text": text,
                    "tokens_in": tokens_in,
                    "tokens_out": tokens_out,
                    "cost_usd": cost,
                    "latency_ms": latency_ms,
                    "recorded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    return CallResult(
        model=model,
        prompt=prompt,
        text=text,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        cost_usd=cost,
        latency_ms=latency_ms,
        cache_hit=False,
        error=error,
    )
