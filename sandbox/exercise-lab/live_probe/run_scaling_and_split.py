"""
Follow-up run per coordinator request:
  1. Small/medium/fat output-token scaling on gemini-3.5-flash-lite, SAME senses
     as the existing fat measurements (fat point reused from cached results, NOT
     re-called).
  2. One-call vs two-parallel-call split, same model, same sense subset.
Deepseek is skipped entirely (already established to fail the latency target).
"""
import os, sys, time, json, hashlib, pathlib, threading, re
from concurrent.futures import ThreadPoolExecutor, as_completed

ROOT = pathlib.Path(__file__).resolve().parents[3]
LAB = ROOT / "sandbox" / "exercise-lab"
sys.path.insert(0, str(LAB / "prototypes" / "fat_seed"))

from prompt_builder import build_correct_content_prompt, build_wrong_content_prompt

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

MODEL = "google/gemini-3.5-flash-lite"
LANG_ID = {"zh": 1, "en": 2, "ja": 3}
LANG_NAME = {1: "Mandarin Chinese", 2: "English", 3: "Japanese"}
BUDGET_CAP = 2.00

CACHE_DIR = LAB / "fixtures" / "live_responses"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

_lock = threading.Lock()
_spend = {"total": 0.0}
_stop = threading.Event()


def small_seed_prompt(lemma, language_id):
    lang = LANG_NAME.get(language_id, "the target language")
    return (f'Generate a SMALL vocabulary seed for "{lemma}" in {lang}. Return JSON with: '
            f'definition_simple, definition_standard, and exactly 3 example sentences using '
            f'"{lemma}" as a whole word. Strict JSON, no prose outside it.')


def medium_seed_prompt(lemma, language_id, pos_hint=None):
    lang = LANG_NAME.get(language_id, "the target language")
    return f"""Generate a MEDIUM vocabulary seed for "{lemma}" in {lang}{f' (expected part of speech: {pos_hint})' if pos_hint else ''}.
Return ONE JSON object with: definition_simple, definition_standard, pos,
semantic_class, sentences (exactly 6 example sentences using "{lemma}" as a
whole word, tagged with difficulty tier T1-T6, spanning a spread of tiers),
primary_collocate (or null), collocation_distractors (3 words semantically
related but NOT genuine collocates, each with a one-sentence reason),
syn_ant_candidates (up to 4 candidates tagged synonym or antonym, anchored to
this specific sense). Strict JSON, no prose outside it."""


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
    cost = usage.get("cost", 0.0) or 0.0
    with _lock:
        _spend["total"] += cost
        running = _spend["total"]
        if running >= BUDGET_CAP:
            _stop.set()
    print(f"[{tag}] status=200 elapsed={elapsed:.2f}s "
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
    all_results = []

    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {}
        for lang, lang_id in LANG_ID.items():
            for row in senses[lang][:4]:
                vocab_id, lemma, pos, freq = row
                # scaling: small + medium
                fut_s = pool.submit(call_openrouter, MODEL, small_seed_prompt(lemma, lang_id), f"scale_small_{lang}_{vocab_id}")
                fut_m = pool.submit(call_openrouter, MODEL, medium_seed_prompt(lemma, lang_id, pos), f"scale_medium_{lang}_{vocab_id}")
                futures[fut_s] = {"kind": "scale_small", "lang": lang, "vocab_id": vocab_id, "lemma": lemma}
                futures[fut_m] = {"kind": "scale_medium", "lang": lang, "vocab_id": vocab_id, "lemma": lemma}
                # split: correct + wrong, fired in parallel too
                fut_c = pool.submit(call_openrouter, MODEL, build_correct_content_prompt(lemma, lang_id, pos), f"split_correct_{lang}_{vocab_id}")
                fut_w = pool.submit(call_openrouter, MODEL, build_wrong_content_prompt(lemma, lang_id, pos), f"split_wrong_{lang}_{vocab_id}")
                futures[fut_c] = {"kind": "split_correct", "lang": lang, "vocab_id": vocab_id, "lemma": lemma}
                futures[fut_w] = {"kind": "split_wrong", "lang": lang, "vocab_id": vocab_id, "lemma": lemma}
        for fut in as_completed(futures):
            meta = futures[fut]
            rec = fut.result()
            rec.update(meta)
            all_results.append(rec)

    (LAB / "live_probe" / "results_scaling_split.json").write_text(json.dumps(all_results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"ALL DONE. total_spend=${_spend['total']:.4f}")


if __name__ == "__main__":
    main()
