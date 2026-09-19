"""
Measurement run for google/gemini-3.8-flash on the SAME senses as the
gemini-3.5-flash-lite baseline. Hard budget cap enforced in-process.
Writes: sandbox/exercise-lab/live_probe/results_38flash.json
Caches: sandbox/exercise-lab/fixtures/live_responses/fat_gemini-3.8-flash_*.json
"""
import sys, time, json, hashlib, pathlib, threading
from concurrent.futures import ThreadPoolExecutor, as_completed

ROOT = pathlib.Path(__file__).resolve().parents[3]
LAB = ROOT / "sandbox" / "exercise-lab"
sys.path.insert(0, str(LAB / "prototypes" / "fat_seed"))
from prompt_builder import build_fat_seed_prompt

import requests

env = {}
for line in (ROOT / ".env").read_text(encoding="utf-8", errors="ignore").splitlines():
    line = line.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    k, v = line.split("=", 1)
    env[k.strip()] = v.strip().strip('"').strip("'")
API_KEY = env.get("OPENROUTER_API_KEY")
if not API_KEY:
    print("NO KEY FOUND"); sys.exit(1)

MODEL = "google/gemini-3.8-flash"
PRICE_IN, PRICE_OUT = 0.75, 3.75  # $/1M tokens, fallback only
LANG_ID = {"zh": 1, "en": 2, "ja": 3}
BUDGET_CAP = 0.85  # leave headroom under the $1.00 hard task cap for the batch mechanics probe already spent + margin

CACHE_DIR = LAB / "fixtures" / "live_responses"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

_lock = threading.Lock()
_spend = {"total": 0.0}
_stop = threading.Event()


def call_openrouter(model, prompt, tag):
    if _stop.is_set():
        return {"skipped": True, "tag": tag}
    h = hashlib.sha256((model + "|" + prompt).encode()).hexdigest()[:20]
    cache_path = CACHE_DIR / f"{tag}_{h}.json"
    t0 = time.time()
    try:
        resp = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "response_format": {"type": "json_object"},
            },
            timeout=180,
        )
    except Exception as e:
        elapsed = time.time() - t0
        return {"tag": tag, "model": model, "error": str(e), "elapsed": elapsed}
    elapsed = time.time() - t0

    record = {"tag": tag, "model": model, "status": resp.status_code, "elapsed": elapsed}
    if resp.status_code != 200:
        record["error_body"] = resp.text[:1000]
        print(f"[{tag}] ERROR status={resp.status_code} body={resp.text[:300]}", flush=True)
        return record

    data = resp.json()
    usage = data.get("usage", {}) or {}
    cost = usage.get("cost")
    if cost is None:
        cost = (usage.get("prompt_tokens", 0) * PRICE_IN + usage.get("completion_tokens", 0) * PRICE_OUT) / 1e6
    with _lock:
        _spend["total"] += cost
        running = _spend["total"]
        if running >= BUDGET_CAP:
            _stop.set()
    print(f"[{tag}] {model} status={resp.status_code} elapsed={elapsed:.2f}s "
          f"in={usage.get('prompt_tokens')} out={usage.get('completion_tokens')} "
          f"reasoning={usage.get('completion_tokens_details', {})} "
          f"cost=${cost:.5f} running_total=${running:.4f}", flush=True)

    content = data["choices"][0]["message"]["content"]
    record.update({
        "prompt_tokens": usage.get("prompt_tokens"),
        "completion_tokens": usage.get("completion_tokens"),
        "usage_raw": usage,
        "cost": cost,
        "content": content,
    })
    cache_path.write_text(json.dumps({"prompt": prompt, "elapsed": elapsed, "response": data}, ensure_ascii=False, indent=2), encoding="utf-8")
    return record


def main():
    senses = json.loads((LAB / "live_probe" / "senses.json").read_text(encoding="utf-8"))
    n_per_lang = int(sys.argv[1]) if len(sys.argv) > 1 else 4
    results = []
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = {}
        for lang, lang_id in LANG_ID.items():
            for row in senses[lang][:n_per_lang]:
                vocab_id, lemma, pos, freq = row
                prompt = build_fat_seed_prompt(lemma, lang_id, pos_hint=pos)
                tag = f"fat_{MODEL.split('/')[-1]}_{lang}_{vocab_id}"
                fut = pool.submit(call_openrouter, MODEL, prompt, tag)
                futures[fut] = {"lang": lang, "vocab_id": vocab_id, "lemma": lemma}
        for fut in as_completed(futures):
            meta = futures[fut]
            rec = fut.result()
            rec.update(meta)
            results.append(rec)

    (LAB / "live_probe" / "results_38flash.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"DONE. n_per_lang={n_per_lang} total_spend=${_spend['total']:.4f} stopped_early={_stop.is_set()}")


if __name__ == "__main__":
    main()
