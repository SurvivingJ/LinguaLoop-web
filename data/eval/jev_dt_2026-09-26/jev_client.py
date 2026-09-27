# -*- coding: utf-8 -*-
"""Thin HTTP client for OpenRouter's Jev Decisions API (typesafe/jev-1.13).

Not a chat-completions call -- POST https://openrouter.ai/api/alpha/decisions
with {model, state, questions}. See scratchpad/jev_api_summary.md.

Concurrency <=8, retry on 429/5xx with Retry-After honoring, per the task's
HARD instructions. Never prints the API key.
"""
from __future__ import annotations

import os
import time
import threading
import concurrent.futures as cf
from dataclasses import dataclass, field
from typing import Any

import requests

DECISIONS_URL = "https://openrouter.ai/api/alpha/decisions"
MODEL = "typesafe/jev-1.13"

_RETRYABLE_STATUS = {429, 500, 502, 503, 524, 529}


def _api_key() -> str:
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY not set in environment (load_dotenv before calling).")
    return key


@dataclass
class DecisionCallResult:
    ok: bool
    item_id: str
    answers: dict = field(default_factory=dict)
    usage: dict = field(default_factory=dict)
    latency_s: float = 0.0
    error: str | None = None
    attempts: int = 1
    raw_model: str | None = None


_session_local = threading.local()


def _session() -> requests.Session:
    s = getattr(_session_local, "s", None)
    if s is None:
        s = requests.Session()
        _session_local.s = s
    return s


def call_decisions(item_id: str, state: dict, questions: dict, *, max_retries: int = 5, timeout: float = 60.0) -> DecisionCallResult:
    """One Decisions API call. Retries on 429/5xx honoring Retry-After; other
    4xx are fatal for this item (returned as ok=False, not retried)."""
    headers = {
        "Authorization": f"Bearer {_api_key()}",
        "Content-Type": "application/json",
    }
    body = {"model": MODEL, "state": state, "questions": questions}
    sess = _session()

    last_err = None
    for attempt in range(1, max_retries + 1):
        t0 = time.monotonic()
        try:
            resp = sess.post(DECISIONS_URL, headers=headers, json=body, timeout=timeout)
        except requests.RequestException as exc:
            last_err = f"network error: {exc}"
            time.sleep(min(2 ** attempt, 20))
            continue
        latency = time.monotonic() - t0

        if resp.status_code == 200:
            data = resp.json()
            return DecisionCallResult(
                ok=True,
                item_id=item_id,
                answers=data.get("answers", {}),
                usage=data.get("usage", {}),
                latency_s=latency,
                attempts=attempt,
                raw_model=data.get("model"),
            )

        if resp.status_code in _RETRYABLE_STATUS:
            retry_after = resp.headers.get("Retry-After")
            wait = float(retry_after) if retry_after else min(2 ** attempt, 20)
            last_err = f"HTTP {resp.status_code}: {resp.text[:300]}"
            time.sleep(wait)
            continue

        if resp.status_code == 402:
            try:
                j = resp.json()
            except Exception:
                j = {}
            if (j.get("limit_source") == "openrouter_in_flight_budget"):
                retry_after = resp.headers.get("Retry-After")
                wait = float(retry_after) if retry_after else min(2 ** attempt, 20)
                last_err = "402 transient in-flight budget"
                time.sleep(wait)
                continue
            return DecisionCallResult(ok=False, item_id=item_id, error=f"402 non-transient: {resp.text[:300]}", attempts=attempt)

        # Other 4xx: fatal, don't retry.
        return DecisionCallResult(ok=False, item_id=item_id, error=f"HTTP {resp.status_code}: {resp.text[:500]}", attempts=attempt)

    return DecisionCallResult(ok=False, item_id=item_id, error=f"exhausted retries: {last_err}", attempts=max_retries)


def run_batch(jobs: list[tuple[str, dict, dict]], *, concurrency: int = 6) -> list[DecisionCallResult]:
    """jobs: list of (item_id, state, questions). Runs with bounded concurrency."""
    results: list[DecisionCallResult | None] = [None] * len(jobs)
    with cf.ThreadPoolExecutor(max_workers=concurrency) as ex:
        futs = {ex.submit(call_decisions, jid, state, qs): i for i, (jid, state, qs) in enumerate(jobs)}
        for fut in cf.as_completed(futs):
            i = futs[fut]
            results[i] = fut.result()
    return results  # type: ignore
