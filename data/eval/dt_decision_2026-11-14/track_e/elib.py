# -*- coding: utf-8 -*-
"""Track E plumbing. Imports Track A (lib/reqs/feats/pipeline) and Track B (common/bscore)
read-only and re-points their cache/ledger/budget globals at THIS directory, so every call
made here is logged to track_e/costs.jsonl and guarded at $0.55. Their caches (and the Sept
A3 response files) are consulted read-only first, so original-gold results cost nothing."""
from __future__ import annotations
import hashlib, json, os, sys, random

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TA, TB = os.path.join(ROOT, "track_a"), os.path.join(ROOT, "track_b")
sys.path.insert(0, TB); sys.path.insert(0, TA)
import common as C            # noqa: E402  Track B
import bscore as BS           # noqa: E402
import lib as L               # noqa: E402  Track A
import reqs as RQ             # noqa: E402
import feats as F             # noqa: E402
import pipeline as P          # noqa: E402

GUARD = 0.55
CACHE = os.path.join(HERE, "cache"); os.makedirs(CACHE, exist_ok=True)
LEDGER = os.path.join(HERE, "costs.jsonl")
B_CACHE_RO, A_CACHE_RO = C.CACHE_DIR, L.CACHE_DIR
C.CACHE_DIR = CACHE; C.LEDGER = LEDGER; C.BUDGET_STOP_USD = GUARD
L.CACHE_DIR = CACHE; L.COSTS = LEDGER; L.GUARD_USD = GUARD
REPO, SENT = C.REPO, C.SENT
LANGS = ("en", "zh", "ja")


def spent() -> float:
    return C.spent()


def chat(body: dict, tag: dict, price=None) -> dict:
    """Track B client; read-only lookup in Track B's cache first."""
    p = os.path.join(B_CACHE_RO, C._key(body) + ".json")
    if os.path.exists(p):
        rec = json.load(open(p, encoding="utf-8")); rec["cached"] = True; rec["from_track"] = "b"
        return rec
    return C.call(body, tag, price)


def decide_call(model: str, state: dict, questions: dict, tag: str) -> dict:
    p = os.path.join(A_CACHE_RO, L._key(model, state, questions) + ".json")
    if os.path.exists(p):
        rec = json.load(open(p, encoding="utf-8")); rec["cached"] = True; rec["from_track"] = "a"
        return rec
    return L.call(model, state, questions, tag)


def decide_jobs(jobs, concurrency=6):
    import concurrent.futures as cf
    L._spent = None  # re-sync Track A's in-memory budget view with the shared ledger
    out = [None] * len(jobs)
    with cf.ThreadPoolExecutor(concurrency) as ex:
        futs = {ex.submit(decide_call, *j): i for i, j in enumerate(jobs)}
        for fu in cf.as_completed(futs):
            try:
                out[futs[fu]] = fu.result()
            except L.BudgetExceeded as e:
                out[futs[fu]] = {"ok": False, "error": str(e), "cached": False}
    return out


def gold(lang):
    v6 = C.load_set("gold", lang)
    v5 = {i["id"]: i for i in json.load(open(os.path.join(REPO, "tests/fixtures/dt_gold", f"{lang}.json"), encoding="utf-8"))}
    for it in v6:
        it["expected_bands_v5"] = v5[it["id"]]["expected_bands"]
    return v6


def load_stress():
    with open(os.path.join(HERE, "stress_set.jsonl"), encoding="utf-8") as f:
        return [json.loads(x) for x in f if x.strip()]
