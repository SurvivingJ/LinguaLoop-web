# -*- coding: utf-8 -*-
"""Track C shared plumbing: budget ledger + hard guard, on-disk response cache,
OpenRouter chat + jev Decisions calls. Never prints/writes the API key."""
from __future__ import annotations
import hashlib, json, os, sys, threading, time
import requests

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
SEPT = os.path.join(REPO, "data", "eval", "jev_dt_2026-09-26")
LEDGER = os.path.join(HERE, "costs.jsonl")
CACHE_DIR = os.path.join(HERE, "cache")
os.makedirs(CACHE_DIR, exist_ok=True)

BUDGET_STOP_USD = 0.50   # refuse to send once cumulative spend >= this
CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"
DECISIONS_URL = "https://openrouter.ai/api/alpha/decisions"
JEV_MODEL = "typesafe/jev-1.13"

# listed $/M tokens (prompt, completion) -- fallback only when usage.cost is absent
LISTED = {
    "qwen/qwen3.7-flash": (0.03, 0.13),
    "deepseek/deepseek-v4.1-flash": (0.051, 0.203),
    "anthropic/claude-haiku-5.5": (0.10, 0.50),
}
_lock = threading.Lock()


class BudgetExceeded(RuntimeError):
    pass


def spent() -> float:
    if not os.path.exists(LEDGER):
        return 0.0
    tot = 0.0
    with open(LEDGER, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                tot += json.loads(line).get("usd", 0.0)
    return tot


def _log(rec: dict):
    with _lock:
        with open(LEDGER, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def _guard():
    s = spent()
    if s >= BUDGET_STOP_USD:
        raise BudgetExceeded(f"cumulative spend ${s:.4f} >= ${BUDGET_STOP_USD}")


def _key() -> str:
    k = os.environ.get("OPENROUTER_API")
    if not k:
        raise RuntimeError("OPENROUTER_API not set")
    return k


def _hash(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:32]


def _cache_get(h):
    p = os.path.join(CACHE_DIR, h + ".json")
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    return None


def _cache_put(h, rec):
    p = os.path.join(CACHE_DIR, h + ".json")
    with open(p + ".tmp", "w", encoding="utf-8") as f:
        json.dump(rec, f, ensure_ascii=False)
    os.replace(p + ".tmp", p)


def _post(url, body, timeout=90, retries=4):
    last = None
    for a in range(1, retries + 1):
        _guard()
        t0 = time.monotonic()
        try:
            r = requests.post(url, headers={"Authorization": f"Bearer {_key()}", "Content-Type": "application/json"},
                              json=body, timeout=timeout)
        except requests.RequestException as e:
            last = f"network: {type(e).__name__}"
            time.sleep(2 * a)
            continue
        lat = time.monotonic() - t0
        if r.status_code == 200:
            return r.json(), lat, a
        last = f"HTTP {r.status_code}: {r.text[:200]}"
        if r.status_code in (429, 500, 502, 503, 524, 529):
            time.sleep(2 * a)
            continue
        break
    raise RuntimeError(last)


def chat(model: str, messages: list, *, tag: str, max_tokens: int = 300, extra: dict | None = None) -> dict:
    """Cached chat completion. Returns {content, usage, usd, latency_s, cached}."""
    body = {"model": model, "messages": messages, "max_tokens": max_tokens, "temperature": 0,
            "usage": {"include": True}}
    body.update(extra or {})
    h = _hash({"url": "chat", "body": body})
    c = _cache_get(h)
    if c is not None:
        c["cached"] = True
        return c
    data, lat, attempts = _post(CHAT_URL, body)
    if "choices" not in data:
        raise RuntimeError(f"no choices: {json.dumps(data)[:200]}")
    u = data.get("usage") or {}
    usd = u.get("cost")
    src = "usage.cost"
    if usd is None:
        pi, po = LISTED[model]
        usd = (u.get("prompt_tokens", 0) * pi + u.get("completion_tokens", 0) * po) / 1e6
        src = "listed_price"
    msg = data["choices"][0]["message"]
    rec = {"content": msg.get("content") or "", "finish": data["choices"][0].get("finish_reason"),
           "usage": {"prompt_tokens": u.get("prompt_tokens"), "completion_tokens": u.get("completion_tokens"),
                     "reasoning_tokens": (u.get("completion_tokens_details") or {}).get("reasoning_tokens")},
           "usd": float(usd), "latency_s": lat, "model": data.get("model"), "provider": data.get("provider")}
    _log({"ts": time.time(), "kind": "chat", "tag": tag, "model": model, "hash": h, "usd": float(usd), "cost_source": src,
          "prompt_tokens": u.get("prompt_tokens"), "completion_tokens": u.get("completion_tokens"),
          "reasoning_tokens": rec["usage"]["reasoning_tokens"], "latency_s": lat, "attempts": attempts})
    _cache_put(h, rec)
    rec["cached"] = False
    return rec


def jev(state: dict, questions: dict, *, tag: str) -> dict:
    body = {"model": JEV_MODEL, "state": state, "questions": questions}
    h = _hash({"url": "jev", "body": body})
    c = _cache_get(h)
    if c is not None:
        c["cached"] = True
        return c
    data, lat, attempts = _post(DECISIONS_URL, body, timeout=60)
    u = data.get("usage") or {}
    usd = u.get("cost")
    src = "usage.cost"
    if usd is None:  # Sept run: ~ $0.00003-0.00006 per call; assume the upper figure
        usd, src = 0.00006, "assumed_upper"
    rec = {"answers": data.get("answers", {}), "usage": u, "usd": float(usd), "latency_s": lat}
    _log({"ts": time.time(), "kind": "jev", "tag": tag, "model": JEV_MODEL, "hash": h, "usd": float(usd),
          "cost_source": src, "usage": u, "latency_s": lat, "attempts": attempts})
    _cache_put(h, rec)
    rec["cached"] = False
    return rec


def load_sept():
    """Import the frozen September harness modules (read-only reuse)."""
    if SEPT not in sys.path:
        sys.path.insert(0, SEPT)
    import score_a3 as A  # noqa
    return A
