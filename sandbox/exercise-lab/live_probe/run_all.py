"""
Live latency/cost probe for the fat-seed generation call.
Writes: sandbox/exercise-lab/live_probe/results.json (raw per-call records)
Caches: sandbox/exercise-lab/fixtures/live_responses/<hash>.json (raw API responses)

Run: python sandbox/exercise-lab/live_probe/run_all.py
"""
import os, sys, time, json, hashlib, pathlib, threading
from concurrent.futures import ThreadPoolExecutor, as_completed

ROOT = pathlib.Path(__file__).resolve().parents[3]
LAB = ROOT / "sandbox" / "exercise-lab"
sys.path.insert(0, str(LAB / "prototypes" / "fat_seed"))

from prompt_builder import (
    build_fat_seed_prompt,
    build_correct_content_prompt,
    build_wrong_content_prompt,
)

import requests

# ---- env ----
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

MODELS = ["google/gemini-3.5-flash-lite", "deepseek/deepseek-v4-flash"]
PRICES = {  # $/1M tokens, (in, out) -- fallback if usage.cost missing
    "google/gemini-3.5-flash-lite": (0.30, 2.50),
    "deepseek/deepseek-v4-flash": (0.089, 0.177),
    "qwen/qwen3.7-flash": (0.03, 0.13),
}
LANG_ID = {"zh": 1, "en": 2, "ja": 3}
BUDGET_CAP = 2.00

CACHE_DIR = LAB / "fixtures" / "live_responses"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

_lock = threading.Lock()
_spend = {"total": 0.0}
_stop = threading.Event()


def small_seed_prompt(lemma, language_id):
    lang = {1: "Mandarin Chinese", 2: "English", 3: "Japanese"}.get(language_id, "the target language")
    return (f'Generate a SMALL vocabulary seed for "{lemma}" in {lang}. Return JSON with: '
            f'definition_simple, definition_standard, and exactly 3 example sentences using '
            f'"{lemma}" as a whole word. Strict JSON, no prose outside it.')


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
        return record

    data = resp.json()
    usage = data.get("usage", {}) or {}
    cost = usage.get("cost")
    if cost is None:
        pin, pout = PRICES.get(model, (0, 0))
        cost = (usage.get("prompt_tokens", 0) * pin + usage.get("completion_tokens", 0) * pout) / 1e6
    with _lock:
        _spend["total"] += cost
        running = _spend["total"]
        if running >= BUDGET_CAP:
            _stop.set()
    print(f"[{tag}] {model} status={resp.status_code} elapsed={elapsed:.2f}s "
          f"in={usage.get('prompt_tokens')} out={usage.get('completion_tokens')} "
          f"cost=${cost:.5f} running_total=${running:.4f}", flush=True)

    content = data["choices"][0]["message"]["content"]
    record.update({
        "prompt_tokens": usage.get("prompt_tokens"),
        "completion_tokens": usage.get("completion_tokens"),
        "cost": cost,
        "content": content,
    })
    cache_path.write_text(json.dumps({"prompt": prompt, "elapsed": elapsed, "response": data}, ensure_ascii=False, indent=2), encoding="utf-8")
    return record


def main():
    senses = json.loads((LAB / "live_probe" / "senses.json").read_text(encoding="utf-8"))
    results = []

    # ---- Step 1: fat-seed latency matrix, 2 models x 3 langs x 8 senses ----
    jobs = []
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {}
        for model in MODELS:
            for lang, lang_id in LANG_ID.items():
                for row in senses[lang][:8]:
                    vocab_id, lemma, pos, freq = row
                    prompt = build_fat_seed_prompt(lemma, lang_id, pos_hint=pos)
                    tag = f"fat_{model.split('/')[-1]}_{lang}_{vocab_id}"
                    fut = pool.submit(call_openrouter, model, prompt, tag)
                    futures[fut] = {"step": "fat", "model": model, "lang": lang, "vocab_id": vocab_id, "lemma": lemma}
        for fut in as_completed(futures):
            meta = futures[fut]
            rec = fut.result()
            rec.update(meta)
            results.append(rec)

    (LAB / "live_probe" / "results_step1.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"STEP1 DONE. running_total=${_spend['total']:.4f}")

    if _stop.is_set():
        print("BUDGET CAP HIT — stopping before step 2/3")
        (LAB / "live_probe" / "results.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
        return

    # ---- Step 2: one fat call vs two parallel (correct/wrong) — gemini only, 4 senses/lang ----
    step2_results = []
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {}
        model = "google/gemini-3.5-flash-lite"
        for lang, lang_id in LANG_ID.items():
            for row in senses[lang][:4]:
                vocab_id, lemma, pos, freq = row
                pc = build_correct_content_prompt(lemma, lang_id, pos_hint=pos)
                pw = build_wrong_content_prompt(lemma, lang_id, pos_hint=pos)
                fut_c = pool.submit(call_openrouter, model, pc, f"split_correct_{lang}_{vocab_id}")
                fut_w = pool.submit(call_openrouter, model, pw, f"split_wrong_{lang}_{vocab_id}")
                futures[fut_c] = {"step": "split", "half": "correct", "lang": lang, "vocab_id": vocab_id, "lemma": lemma}
                futures[fut_w] = {"step": "split", "half": "wrong", "lang": lang, "vocab_id": vocab_id, "lemma": lemma}
        for fut in as_completed(futures):
            meta = futures[fut]
            rec = fut.result()
            rec.update(meta)
            step2_results.append(rec)

    (LAB / "live_probe" / "results_step2.json").write_text(json.dumps(step2_results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"STEP2 DONE. running_total=${_spend['total']:.4f}")

    if _stop.is_set():
        print("BUDGET CAP HIT — stopping before step 3")
        results.extend(step2_results)
        (LAB / "live_probe" / "results.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
        return

    # ---- Step 3: output-token scaling — small seed vs fat, gemini only, 4 senses/lang ----
    step3_results = []
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {}
        model = "google/gemini-3.5-flash-lite"
        for lang, lang_id in LANG_ID.items():
            for row in senses[lang][:4]:
                vocab_id, lemma, pos, freq = row
                prompt = small_seed_prompt(lemma, lang_id)
                fut = pool.submit(call_openrouter, model, prompt, f"small_{lang}_{vocab_id}")
                futures[fut] = {"step": "small", "lang": lang, "vocab_id": vocab_id, "lemma": lemma}
        for fut in as_completed(futures):
            meta = futures[fut]
            rec = fut.result()
            rec.update(meta)
            step3_results.append(rec)

    (LAB / "live_probe" / "results_step3.json").write_text(json.dumps(step3_results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"STEP3 DONE. running_total=${_spend['total']:.4f}")

    results.extend(step2_results)
    results.extend(step3_results)
    (LAB / "live_probe" / "results.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"ALL DONE. total_spend=${_spend['total']:.4f}")


if __name__ == "__main__":
    main()
