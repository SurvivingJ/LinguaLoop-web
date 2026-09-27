"""
Thin HTTP client for OpenRouter's jev (typesafe/jev-1.13) Decisions API.
POST https://openrouter.ai/api/alpha/decisions
Concurrency <= 8, retries on 429 (honors Retry-After) and transient 402
(in-flight budget). Tracks cumulative usage.cost and enforces a hard budget cap.
Never prints the API key.
"""
import json
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from dotenv import load_dotenv

REPO = r"c:\Users\James\Documents\Coding\LinguaLoop\WebApp"
load_dotenv(os.path.join(REPO, ".env"))

API_URL = "https://openrouter.ai/api/alpha/decisions"
API_KEY = os.environ["OPENROUTER_API_KEY"]
assert API_KEY, "OPENROUTER_API_KEY missing"

BUDGET_CAP_USD = 0.90  # hard stop well under the $1 experiment cap

_lock = threading.Lock()
_state = {"cost": 0.0, "calls": 0, "errors": 0}


def get_spend():
    with _lock:
        return dict(_state)


def _post_once(payload, timeout=30):
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }
    t0 = time.monotonic()
    resp = requests.post(API_URL, headers=headers, json=payload, timeout=timeout)
    latency = time.monotonic() - t0
    return resp, latency


def call_jev(payload, max_retries=5, label=None):
    """Call jev once (with its own retry loop). Returns dict with keys:
    ok, status, answers, usage, latency, raw, error, label.
    Raises RuntimeError if the cumulative budget cap would be exceeded.
    """
    with _lock:
        if _state["cost"] >= BUDGET_CAP_USD:
            raise RuntimeError(f"Budget cap ${BUDGET_CAP_USD} reached, refusing further calls")

    attempt = 0
    while True:
        attempt += 1
        try:
            resp, latency = _post_once(payload)
        except requests.RequestException as e:
            if attempt >= max_retries:
                with _lock:
                    _state["errors"] += 1
                return {"ok": False, "error": str(e), "label": label, "latency": None}
            time.sleep(min(2 ** attempt, 20))
            continue

        if resp.status_code == 200:
            data = resp.json()
            usage = data.get("usage", {}) or {}
            cost = usage.get("cost", 0.0) or 0.0
            with _lock:
                _state["cost"] += cost
                _state["calls"] += 1
            return {
                "ok": True,
                "status": 200,
                "answers": data.get("answers", {}),
                "usage": usage,
                "model": data.get("model"),
                "latency": latency,
                "label": label,
            }

        if resp.status_code == 429:
            retry_after = float(resp.headers.get("Retry-After", 2))
            if attempt >= max_retries:
                with _lock:
                    _state["errors"] += 1
                return {"ok": False, "status": 429, "error": "rate limited, exhausted retries", "label": label}
            time.sleep(min(retry_after, 20))
            continue

        if resp.status_code == 402:
            try:
                body = resp.json()
            except Exception:
                body = {}
            transient = body.get("limit_source") == "openrouter_in_flight_budget"
            if transient and attempt < max_retries:
                retry_after = float(resp.headers.get("Retry-After", 2))
                time.sleep(min(retry_after, 20))
                continue
            with _lock:
                _state["errors"] += 1
            return {"ok": False, "status": 402, "error": f"payment required: {body}", "label": label}

        if resp.status_code in (500, 502, 503, 524, 529) and attempt < max_retries:
            time.sleep(min(2 ** attempt, 20))
            continue

        with _lock:
            _state["errors"] += 1
        return {
            "ok": False,
            "status": resp.status_code,
            "error": resp.text[:500],
            "label": label,
        }


def run_batch(payloads_with_labels, concurrency=8):
    """payloads_with_labels: list of (label, payload). Returns list of results in
    the SAME order as input. Stops issuing new calls once budget cap is hit
    (already-issued calls still complete)."""
    results = [None] * len(payloads_with_labels)
    with ThreadPoolExecutor(max_workers=concurrency) as ex:
        futs = {}
        for i, (label, payload) in enumerate(payloads_with_labels):
            spend = get_spend()
            if spend["cost"] >= BUDGET_CAP_USD:
                results[i] = {"ok": False, "error": "budget cap reached before dispatch", "label": label}
                continue
            futs[ex.submit(call_jev, payload, label=label)] = i
        for fut in as_completed(futs):
            i = futs[fut]
            try:
                results[i] = fut.result()
            except Exception as e:
                results[i] = {"ok": False, "error": str(e), "label": payloads_with_labels[i][0]}
    return results


if __name__ == "__main__":
    # smoke test
    payload = {
        "model": "typesafe/jev-1.13",
        "state": {"文章": "我今天很开心，因为天气很好。"},
        "questions": {
            "is_correct": {
                "type": "noul",
                "instructions": "这句话是正面情绪吗？",
                "criteria": {"true": "情绪积极正面。", "false": "情绪消极或中性。"},
            }
        },
    }
    r = call_jev(payload, label="smoke")
    print(json.dumps({k: v for k, v in r.items() if k != "raw"}, ensure_ascii=False, indent=2))
    print("spend:", get_spend())
