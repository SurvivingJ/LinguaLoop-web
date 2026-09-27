"""Thin client for OpenRouter's Decisions API (typesafe/jev-1.13).

POST https://openrouter.ai/api/alpha/decisions
{model, state: {...}, questions: {key: {type, instructions, criteria}}}

Concurrency <= 8, retries on 429 (honor Retry-After) and transient 402
(limit_source == 'openrouter_in_flight_budget'). Never prints the API key.

Usage:
    from jev_client import call_jev, call_jev_batch
    resp = call_jev(state={...}, questions={...})
    results = call_jev_batch([{"state":..., "questions":...}, ...], max_workers=8)
"""
from __future__ import annotations

import os
import time
import json
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

DECISIONS_URL = "https://openrouter.ai/api/alpha/decisions"
MODEL = "typesafe/jev-1.13"

_lock = threading.Lock()
_total_cost = 0.0
_call_count = 0


def _get_key() -> str:
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY not set in environment (call load_dotenv first)")
    return key


def call_jev(state: dict, questions: dict, max_retries: int = 5, timeout: float = 30.0) -> dict:
    """One Decisions request. Returns the parsed JSON response (with a few
    convenience fields added: _latency_s, _cost). Raises on unrecoverable errors."""
    global _total_cost, _call_count
    key = _get_key()
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    body = {"model": MODEL, "state": state, "questions": questions}

    attempt = 0
    while True:
        attempt += 1
        t0 = time.time()
        try:
            r = requests.post(DECISIONS_URL, headers=headers, json=body, timeout=timeout)
        except requests.RequestException as e:
            if attempt > max_retries:
                raise
            time.sleep(min(2 ** attempt, 20))
            continue
        latency = time.time() - t0

        if r.status_code == 429:
            if attempt > max_retries:
                r.raise_for_status()
            retry_after = float(r.headers.get("Retry-After", 2 ** attempt))
            time.sleep(min(retry_after, 30))
            continue
        if r.status_code == 402:
            try:
                body_json = r.json()
            except Exception:
                body_json = {}
            if body_json.get("limit_source") == "openrouter_in_flight_budget" and attempt <= max_retries:
                retry_after = float(r.headers.get("Retry-After", 2 ** attempt))
                time.sleep(min(retry_after, 30))
                continue
            r.raise_for_status()
        if r.status_code >= 500:
            if attempt > max_retries:
                r.raise_for_status()
            time.sleep(min(2 ** attempt, 20))
            continue

        r.raise_for_status()
        data = r.json()
        data["_latency_s"] = latency
        cost = (data.get("usage") or {}).get("cost", 0.0) or 0.0
        with _lock:
            _total_cost += cost
            _call_count += 1
        return data


def call_jev_batch(requests_list: list[dict], max_workers: int = 8) -> list[dict]:
    """requests_list: list of {"state":..., "questions":..., "_meta": {...}}.
    Returns list of results in the SAME order, each either the response dict
    (with "_meta" copied over) or {"_error": str, "_meta": {...}} on failure."""
    results: list[dict | None] = [None] * len(requests_list)

    def _run(i, item):
        try:
            resp = call_jev(item["state"], item["questions"])
            resp["_meta"] = item.get("_meta")
            return i, resp
        except Exception as e:
            return i, {"_error": str(e), "_meta": item.get("_meta")}

    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futs = [ex.submit(_run, i, item) for i, item in enumerate(requests_list)]
        for fut in as_completed(futs):
            i, res = fut.result()
            results[i] = res
    return results


def get_running_totals() -> tuple[float, int]:
    with _lock:
        return _total_cost, _call_count


if __name__ == "__main__":
    # smoke test
    import env_setup  # noqa: F401  (loads OPENROUTER_API_KEY)
    resp = call_jev(
        state={"sentence": "The cat sat on the mat."},
        questions={
            "grammatical": {
                "type": "noul",
                "instructions": "Is the sentence grammatically correct English?",
                "criteria": {"true": "No grammar errors.", "false": "Contains a grammar error."},
            }
        },
    )
    print(json.dumps(resp, ensure_ascii=False, indent=2))
