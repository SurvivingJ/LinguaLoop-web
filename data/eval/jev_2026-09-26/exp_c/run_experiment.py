# -*- coding: utf-8 -*-
"""Runs the jev-1.13 DT-grading experiment against all 90 gold items (native
language) plus a 20-item English-prompt control on zh/ja. Writes raw results
to raw/*.jsonl and a manifest. No repo files touched; no DB writes.
"""
from __future__ import annotations

import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = r"c:\Users\James\Documents\Coding\LinguaLoop\WebApp"
sys.path.insert(0, HERE)

from dotenv import load_dotenv  # noqa: E402
load_dotenv(os.path.join(REPO, ".env"))

import build_requests as BR  # noqa: E402
import jev_client as JC  # noqa: E402

GOLD_DIR = os.path.join(REPO, "tests", "fixtures", "dt_gold")
RAW_DIR = os.path.join(HERE, "raw")
os.makedirs(RAW_DIR, exist_ok=True)

LANGS = ["en", "zh", "ja"]
CONTROL_INDEXES = [0, 3, 6, 9, 12, 15, 18, 21, 24, 27]  # 10 of 30, spread across kind


def load_gold(lang: str) -> list:
    with open(os.path.join(GOLD_DIR, f"{lang}.json"), encoding="utf-8") as f:
        return json.load(f)


def main():
    manifest = {"native": [], "control": []}
    jobs = []  # (job_key, state, questions)
    job_meta = {}  # job_key -> dict

    for lang in LANGS:
        items = load_gold(lang)
        for item in items:
            state, questions = BR.build_request(item, content_lang=lang, prompt_lang=lang)
            key = f"native::{lang}::{item['id']}"
            jobs.append((key, state, questions))
            job_meta[key] = {"run": "native", "lang": lang, "item_id": item["id"], "kind": item["kind"],
                              "expected_bands": item["expected_bands"],
                              "expected_errors": item["expected_errors"]}

    for lang in ["zh", "ja"]:
        items = load_gold(lang)
        for idx in CONTROL_INDEXES:
            item = items[idx]
            state, questions = BR.build_request(item, content_lang=lang, prompt_lang="en")
            key = f"control::{lang}::{item['id']}"
            jobs.append((key, state, questions))
            job_meta[key] = {"run": "control", "lang": lang, "item_id": item["id"], "kind": item["kind"],
                              "expected_bands": item["expected_bands"],
                              "expected_errors": item["expected_errors"]}

    print(f"Total jobs: {len(jobs)}  (native=90, control=20)")

    t0 = time.time()
    results = JC.run_batch(jobs, concurrency=6)
    elapsed = time.time() - t0
    print(f"Batch done in {elapsed:.1f}s")

    out_path = os.path.join(RAW_DIR, "results.jsonl")
    total_cost = 0.0
    n_ok = n_err = 0
    with open(out_path, "w", encoding="utf-8") as f:
        for (key, _state, _q), res in zip(jobs, results):
            meta = job_meta[key]
            rec = {
                "job_key": key,
                "run": meta["run"],
                "lang": meta["lang"],
                "item_id": meta["item_id"],
                "kind": meta["kind"],
                "expected_bands": meta["expected_bands"],
                "expected_errors": meta["expected_errors"],
                "ok": res.ok,
                "error": res.error,
                "latency_s": res.latency_s,
                "attempts": res.attempts,
                "usage": res.usage,
                "raw_model": res.raw_model,
                "answers": res.answers,
            }
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            if res.ok:
                n_ok += 1
                total_cost += float(res.usage.get("cost", 0) or 0)
            else:
                n_err += 1
                print(f"FAILED {key}: {res.error}")

    print(f"ok={n_ok} err={n_err} total_cost=${total_cost:.6f}")
    with open(os.path.join(RAW_DIR, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump({"n_ok": n_ok, "n_err": n_err, "total_cost": total_cost, "elapsed_s": elapsed}, f, indent=2)


if __name__ == "__main__":
    main()
