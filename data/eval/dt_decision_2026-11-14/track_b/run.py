# -*- coding: utf-8 -*-
"""Run one (model, variant, set) arm. Usage:
    python run.py MODEL_ALIAS VARIANT SET [--langs en,zh,ja] [--limit N] [--workers 6]
Writes runs/<alias>__<variant>__<set>.jsonl (one record per item; rewritten from cache each time).
"""
from __future__ import annotations
import argparse, json, os, sys
from concurrent.futures import ThreadPoolExecutor
import common as C

NO_REASON = {"reasoning": {"enabled": False}}
MODELS = {
    # alias: (openrouter id, extra body, list price $/M (in, out) used only if usage.cost is absent)
    "gemini25fl": ("google/gemini-2.5-flash-lite", {}, (0.10, 0.40)),
    "gemini31fl": ("google/gemini-3.1-flash-lite", {"reasoning": {"effort": "minimal"}}, (0.25, 1.50)),
    "gpt6luna": ("openai/gpt-6-luna", {"reasoning": {"effort": "none"}}, (0.10, 0.50)),
    "gpt41nano": ("openai/gpt-4.1-nano", {}, (0.10, 0.40)),
    "deepseek41f": ("deepseek/deepseek-v4.1-flash", NO_REASON, (0.051, 0.203)),
    "qwen38f": ("qwen/qwen3.8-flash", NO_REASON, (0.15, 0.47)),
    "qwen37f": ("qwen/qwen3.7-flash", NO_REASON, (0.03, 0.13)),
    "mistral32": ("mistralai/mistral-small-3.2-24b-instruct", {}, (0.10, 0.30)),
    "glm53f": ("z-ai/glm-5.3-flash", NO_REASON, (0.04, 0.078)),
    "gemma4": ("google/gemma-4-31b-it", NO_REASON, (0.20, 0.40)),
    "llama4s": ("meta-llama/llama-4-scout", {}, (0.10, 0.30)),
}
RUNS = os.path.join(C.HERE, "runs")
os.makedirs(RUNS, exist_ok=True)


def one(alias, variant, which, lang, item):
    mid, extra, price = MODELS[alias]
    body = C.build_request(mid, item, lang, variant, extra)
    base = {"id": item["id"], "lang": lang, "kind": item.get("kind")}
    if body is None:
        return {**base, "skipped_identical": True, "valid": True, "errors": [], "usd": 0.0, "latency": 0.0}
    try:
        r = C.call(body, {"alias": alias, "variant": variant, "set": which, "item": item["id"]}, price)
    except C.BudgetExceeded as e:
        return {**base, "budget_stop": True, "valid": False, "errors": [], "error": str(e)}
    d = C.decode(item, lang, variant, r.get("content"))
    u = r.get("usage") or {}
    return {**base, "valid": d["valid"], "errors": d["errors"], "span_miss": d["span_miss"],
            "usd": u.get("cost"), "latency": r.get("latency"), "prompt_tokens": u.get("prompt_tokens"),
            "completion_tokens": u.get("completion_tokens"), "reasoning_tokens": u.get("reasoning_tokens"),
            "finish": r.get("finish"), "provider": r.get("provider"), "error": r.get("error"),
            "raw": r.get("content") if not d["valid"] else None}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("alias"); ap.add_argument("variant"); ap.add_argument("set")
    ap.add_argument("--langs", default="en,zh,ja"); ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--workers", type=int, default=6)
    a = ap.parse_args()
    jobs = []
    for lang in a.langs.split(","):
        items = C.load_set(a.set, lang)
        if a.limit:
            # smoke: mix of clean and error items
            items = items[:1] + items[len(items) // 2: len(items) // 2 + a.limit - 1]
        jobs += [(a.alias, a.variant, a.set, lang, it) for it in items]
    before = C.spent()
    with ThreadPoolExecutor(a.workers) as ex:
        recs = list(ex.map(lambda j: one(*j), jobs))
    tag = f"{a.alias}__{a.variant}__{a.set}" + ("__smoke" if a.limit else "")
    with open(os.path.join(RUNS, tag + ".jsonl"), "w", encoding="utf-8") as f:
        for r in recs:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    called = [r for r in recs if r.get("prompt_tokens")]
    n = len(called) or 1
    usd = sum(r["usd"] or 0 for r in called)
    print(f"{tag}: items={len(recs)} called={len(called)} valid={sum(r['valid'] for r in recs)} "
          f"errors_api={sum(1 for r in recs if r.get('error'))} "
          f"tok in/out/reason={sum(r['prompt_tokens'] for r in called)/n:.0f}/"
          f"{sum(r['completion_tokens'] or 0 for r in called)/n:.0f}/{sum(r['reasoning_tokens'] or 0 for r in called)/n:.0f} "
          f"usd/item={usd/n:.6f} new_spend=${C.spent()-before:.4f} total=${C.spent():.4f}")
    for r in recs:
        if r.get("error"):
            print("  ERR", r["id"], r["error"][:300]); break


if __name__ == "__main__":
    main()
