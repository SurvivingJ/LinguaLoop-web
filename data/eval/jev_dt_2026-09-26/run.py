# -*- coding: utf-8 -*-
"""CLI runner for the three jev DT-grading arms (A1/A2/NR).

    python run.py --arm A1 --lang zh --set gold [--limit N]
    python run.py --arm A2 --lang ja --set gold
    python run.py --arm NR --lang zh --set gold

No DB writes; nothing under services/, tests/fixtures/, raw/ is modified.
.env is loaded before anything else so OPENROUTER_API_KEY is available
(this module never imports services.* -- only score.py does, and it loads
dotenv first too, per the same rule).

Every raw response is cached to responses/<arm>_<lang>_<set>.jsonl keyed by
item id (A1/NR) or "<item_id>::<pair_idx>" (A2), so a rerun costs nothing for
already-answered jobs. A hard spend cap for the WHOLE experiment is enforced
via a shared costs.jsonl ledger: before sending any new calls, the ledger's
running total is checked and the run refuses to send more if it is already
>= $1.80 (SOFT_CAP); the absolute cap for the experiment is $2.00 (HARD_CAP).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, HERE)

from dotenv import load_dotenv  # noqa: E402
load_dotenv(os.path.join(REPO, ".env"))

import jev_client as JC  # noqa: E402
import reqbuild as REQ  # noqa: E402
import sentences as SENT  # noqa: E402

GOLD_DIR = os.path.join(REPO, "tests", "fixtures", "dt_gold")
RESPONSES_DIR = os.path.join(HERE, "responses")
COSTS_PATH = os.path.join(HERE, "costs.jsonl")
os.makedirs(RESPONSES_DIR, exist_ok=True)

SOFT_CAP = 1.80
HARD_CAP = 2.00

LANGS = ("zh", "ja", "en")
# A3 is BUILT (reqbuild.build_a3_request) but not yet run -- the coordinator
# asked for it to exist for later use once tau/tau_narrow are fit on silver.
ARMS = ("A1", "A2", "NR", "NRv2", "A3")


def load_gold(lang: str) -> list[dict]:
    with open(os.path.join(GOLD_DIR, f"{lang}.json"), encoding="utf-8") as f:
        return json.load(f)


SILVER_DIR = os.path.join(HERE, "silver")


def silver_path(lang: str) -> str:
    """Prefer <lang>_final3.json (the MQM-severity-labeled silver set the
    coordinator specified) over <lang>_final.json when both exist."""
    p3 = os.path.join(SILVER_DIR, f"{lang}_final3.json")
    if os.path.exists(p3):
        return p3
    return os.path.join(SILVER_DIR, f"{lang}_final.json")


def load_silver(lang: str) -> list[dict]:
    path = silver_path(lang)
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"--set silver requested but neither {os.path.join(SILVER_DIR, lang + '_final3.json')} "
            f"nor {path} exists yet. Expected schema matches tests/fixtures/dt_gold/{lang}.json -- "
            f"this harness does not create it."
        )
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_set(lang: str, set_name: str) -> list[dict]:
    if set_name == "gold":
        return load_gold(lang)
    return load_silver(lang)


def ledger_total() -> float:
    if not os.path.exists(COSTS_PATH):
        return 0.0
    total = 0.0
    with open(COSTS_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                total += float(json.loads(line).get("cost", 0) or 0)
            except Exception:
                pass
    return total


def append_ledger(records: list[dict]) -> float:
    total = ledger_total()
    with open(COSTS_PATH, "a", encoding="utf-8") as f:
        for rec in records:
            total += float(rec.get("cost", 0) or 0)
            rec["cumulative_cost_after"] = total
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return total


def load_cache(path: str) -> dict[str, dict]:
    cache: dict[str, dict] = {}
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                # A failed call (ok=False) is NOT a cache hit -- retry it on
                # the next run instead of permanently skipping it.
                if rec.get("skipped") or rec.get("ok"):
                    cache[rec["job_key"]] = rec
    return cache


def append_cache(path: str, records: list[dict]) -> None:
    with open(path, "a", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def run_arm(arm: str, lang: str, set_name: str, limit: int | None) -> dict:
    items = load_set(lang, set_name)
    if limit:
        items = items[:limit]

    cache_path = os.path.join(RESPONSES_DIR, f"{arm}_{lang}_{set_name}.jsonl")
    cache = load_cache(cache_path)

    jobs: list[tuple[str, dict, dict]] = []
    job_meta: dict[str, dict] = {}
    skipped: list[dict] = []
    alignment_failures: list[dict] = []

    for item in items:
        item_id = item["id"]

        if arm == "A1":
            key = item_id
            if key in cache:
                continue
            state, questions = REQ.build_a1_request(item, lang)
            jobs.append((key, state, questions))
            job_meta[key] = {"item_id": item_id, "kind": item["kind"]}

        elif arm == "NR":
            key = item_id
            if key in cache:
                continue
            state, questions = REQ.build_nr_request(item, lang)
            jobs.append((key, state, questions))
            job_meta[key] = {"item_id": item_id, "kind": item["kind"]}

        elif arm == "NRv2":
            key = item_id
            if key in cache:
                continue
            state, questions = REQ.build_nr_v2_request(item, lang)
            jobs.append((key, state, questions))
            job_meta[key] = {"item_id": item_id, "kind": item["kind"]}

        elif arm == "A2":
            res = SENT.build_sentence_pairs(item["reference"], item["reproduction"])
            if not res.ok:
                alignment_failures.append({"item_id": item_id, "reason": res.reason})
            for idx, pr in enumerate(res.pairs):
                key = f"{item_id}::{idx}"
                if key in cache:
                    continue
                if pr.ref.text == pr.repro.text:
                    skipped.append({"job_key": key, "item_id": item_id, "pair_idx": idx,
                                     "reason": "byte-identical sentence pair", "skipped": True})
                    continue
                state, questions = REQ.build_a2_request(
                    item["reference"], item["reproduction"], pr.ref.text, pr.repro.text, lang
                )
                jobs.append((key, state, questions))
                job_meta[key] = {"item_id": item_id, "kind": item["kind"], "pair_idx": idx,
                                  "ref_sentence": pr.ref.text, "repro_sentence": pr.repro.text,
                                  "merged": pr.merged}

        elif arm == "A3":
            # Same sentence-pair skip rule as A2 (byte-identical -> clean by
            # construction, no call). Not exercised yet by design.
            res = SENT.build_sentence_pairs(item["reference"], item["reproduction"])
            if not res.ok:
                alignment_failures.append({"item_id": item_id, "reason": res.reason})
            for idx, pr in enumerate(res.pairs):
                key = f"{item_id}::{idx}"
                if key in cache:
                    continue
                if pr.ref.text == pr.repro.text:
                    skipped.append({"job_key": key, "item_id": item_id, "pair_idx": idx,
                                     "reason": "byte-identical sentence pair", "skipped": True})
                    continue
                state, questions = REQ.build_a3_request(
                    item["reference"], item["reproduction"], pr.ref.text, pr.repro.text, lang
                )
                jobs.append((key, state, questions))
                job_meta[key] = {"item_id": item_id, "kind": item["kind"], "pair_idx": idx,
                                  "ref_sentence": pr.ref.text, "repro_sentence": pr.repro.text,
                                  "merged": pr.merged}
        else:
            raise ValueError(f"unknown arm {arm!r}")

    if skipped:
        append_cache(cache_path, skipped)

    if not jobs:
        print(f"[{arm}/{lang}/{set_name}] nothing to do (all {len(items)} item(s) cached or skipped; "
              f"{len(skipped)} sentence pairs skipped as byte-identical)")
        return {"arm": arm, "lang": lang, "set": set_name, "n_jobs": 0,
                "n_skipped": len(skipped), "alignment_failures": alignment_failures}

    current_total = ledger_total()
    if current_total >= SOFT_CAP:
        raise SystemExit(
            f"REFUSING to send {len(jobs)} call(s): jev spend ledger already at "
            f"${current_total:.4f} >= SOFT_CAP ${SOFT_CAP:.2f} (HARD_CAP ${HARD_CAP:.2f}). "
            f"See {COSTS_PATH}."
        )

    print(f"[{arm}/{lang}/{set_name}] sending {len(jobs)} call(s) "
          f"(ledger so far: ${current_total:.4f} / ${SOFT_CAP:.2f} soft cap)")

    t0 = time.time()
    results = JC.run_batch(jobs, concurrency=6)
    elapsed = time.time() - t0

    out_records = []
    ledger_records = []
    n_ok = n_err = 0
    for (key, _state, _q), res in zip(jobs, results):
        meta = job_meta[key]
        rec = {
            "job_key": key,
            "arm": arm,
            "lang": lang,
            "set": set_name,
            **meta,
            "ok": res.ok,
            "error": res.error,
            "latency_s": res.latency_s,
            "attempts": res.attempts,
            "usage": res.usage,
            "raw_model": res.raw_model,
            "answers": res.answers,
        }
        out_records.append(rec)
        cost = float(res.usage.get("cost", 0) or 0)
        ledger_records.append({
            "ts": time.time(), "arm": arm, "lang": lang, "set": set_name,
            "job_key": key, "ok": res.ok, "cost": cost, "latency_s": res.latency_s,
        })
        if res.ok:
            n_ok += 1
        else:
            n_err += 1
            print(f"FAILED {key}: {res.error}")

    append_cache(cache_path, out_records)
    new_total = append_ledger(ledger_records)

    if new_total >= HARD_CAP:
        raise SystemExit(
            f"jev spend ledger hit ${new_total:.4f} >= HARD_CAP ${HARD_CAP:.2f} "
            f"after this batch. Halting all further runs."
        )

    print(f"[{arm}/{lang}/{set_name}] done in {elapsed:.1f}s ok={n_ok} err={n_err} "
          f"batch_cost=${sum(r['cost'] for r in ledger_records):.6f} "
          f"cumulative=${new_total:.6f}")

    return {"arm": arm, "lang": lang, "set": set_name, "n_jobs": len(jobs),
            "n_ok": n_ok, "n_err": n_err, "n_skipped": len(skipped),
            "alignment_failures": alignment_failures, "elapsed_s": elapsed,
            "cumulative_cost": new_total}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", required=True, choices=ARMS)
    ap.add_argument("--lang", required=True, choices=LANGS)
    ap.add_argument("--set", required=True, choices=("gold", "silver"))
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()

    summary = run_arm(args.arm, args.lang, args.set, args.limit)
    print(json.dumps(summary, indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
