# -*- coding: utf-8 -*-
"""Track A shared plumbing: budget-guarded, disk-cached Decisions API client +
unit builders. Imports the Sept harness (data/eval/jev_dt_2026-09-26) read-only.

Budget: every call is logged to costs.jsonl (tokens + USD); the guard refuses
to send once cumulative spend >= GUARD_USD. Cache: cache/<sha256>.json keyed by
(model, state, questions) so re-runs are free. The API key is read from
OPENROUTER_API and never printed/written.
"""
from __future__ import annotations

import concurrent.futures as cf
import difflib
import hashlib
import json
import os
import re
import sys
import threading
import time

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
SEPT = os.path.join(REPO, "data", "eval", "jev_dt_2026-09-26")
sys.path.insert(0, SEPT)

import score as S  # noqa: E402  (Sept harness; loads services.* scoring)
import score_a3 as SA3  # noqa: E402
import sentences as SENT  # noqa: E402
import reqbuild as REQ  # noqa: E402
import taxonomy_data as T  # noqa: E402

URL = "https://openrouter.ai/api/alpha/decisions"
CACHE_DIR = os.path.join(HERE, "cache")
COSTS = os.path.join(HERE, "costs.jsonl")
os.makedirs(CACHE_DIR, exist_ok=True)

BUDGET_USD = 0.55
GUARD_USD = 0.50

# USD per input token (output is free for all decision models listed 2026-11-14)
PRICE = {
    "typesafe/jev-1.13": 0.042e-6, "typesafe/jev-1.14": 0.042e-6,
    "google/gemini-decision-1": 0.10e-6, "openai/gpt-6-luna-decisions": 0.10e-6,
    "perplexity/pplx-decider-v1.2": 0.02e-6, "perplexity/pplx-decider-flash-v1.2": 0.01e-6,
    "liquid/d1-ultra": 0.042e-6, "liquid/d1.1": 0.02e-6,
    "microsoft/microsoft-decision-1": 0.042e-6, "upstage/solar-decide": 0.05e-6,
    "upstage/solar-decide-flash": 0.05e-6, "heygen/heygen-decision-1-turbo": 0.09e-6,
    "morph/reflex": 0.042e-6, "nace-ai/drex-max": 0.06e-6, "respan/span-02": 0.01e-6,
    "baseten/elephant-1": 0.035e-6, "cloudflare/clef-flash": 0.019e-6,
    "scaledown/classify-1": 0.04e-6, "baseten/joey-1": 0.01e-6,
    "togethercomputer/tev1-4b-experimental": 0.042e-6, "jaredpalmer/kev-4b": 0.042e-6,
    "perplexity/pplx-decider-v1.3:free": 0.0, "perplexity/pplx-decider-flash-v1.3:free": 0.0,
    "cloudflare/clef-omni": 0.15e-6, "heygen/heygen-decision-1": 0.14e-6,
}

_lock = threading.Lock()
_spent = None


def ledger_total() -> float:
    tot = 0.0
    if os.path.exists(COSTS):
        with open(COSTS, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    tot += float(json.loads(line).get("usd", 0) or 0)
    return tot


def _key(model, state, questions) -> str:
    blob = json.dumps({"m": model, "s": state, "q": questions}, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


class BudgetExceeded(RuntimeError):
    pass


def call(model: str, state: dict, questions: dict, tag: str = "", max_retries: int = 4) -> dict:
    """Returns {"ok", "answers", "usage", "latency_s", "cached"}; cached on disk."""
    global _spent
    k = _key(model, state, questions)
    path = os.path.join(CACHE_DIR, k + ".json")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            rec = json.load(f)
        rec["cached"] = True
        return rec
    api_key = os.environ.get("OPENROUTER_API")
    if not api_key:
        raise RuntimeError("OPENROUTER_API not set")
    # worst-case estimate so that concurrent in-flight calls cannot overshoot
    est_tokens = len(json.dumps({"s": state, "q": questions}, ensure_ascii=False)) * 1.5
    est = est_tokens * PRICE.get(model, 0.2e-6)
    with _lock:
        if _spent is None:
            _spent = ledger_total()
        if _spent + est >= GUARD_USD:
            raise BudgetExceeded(f"spend ${_spent:.4f} (+est ${est:.5f}) >= guard ${GUARD_USD}")
        _spent += est  # reserve
    body = {"model": model, "state": state, "questions": questions}
    last = None
    usd = 0.0
    rec = None
    try:
        for attempt in range(1, max_retries + 1):
            t0 = time.monotonic()
            try:
                r = requests.post(URL, headers={"Authorization": f"Bearer {api_key}",
                                                "Content-Type": "application/json"}, json=body, timeout=90)
            except requests.RequestException as exc:
                last = f"network: {type(exc).__name__}"
                time.sleep(min(2 ** attempt, 15))
                continue
            lat = time.monotonic() - t0
            if r.status_code == 200:
                d = r.json()
                usage = d.get("usage", {}) or {}
                if usage.get("cost") is not None:
                    usd = float(usage["cost"])
                    src = "usage.cost"
                else:
                    usd = float(usage.get("input_tokens", usage.get("prompt_tokens", 0)) or 0) * PRICE.get(model, 0.2e-6)
                    src = "computed"
                rec = {"ok": True, "model": model, "raw_model": d.get("model"), "answers": d.get("answers", {}),
                       "usage": usage, "usd": usd, "usd_source": src, "latency_s": lat, "tag": tag}
                break
            if r.status_code in (429, 500, 502, 503, 524, 529):
                last = f"HTTP {r.status_code}"
                ra = r.headers.get("Retry-After")
                time.sleep(float(ra) if ra else min(2 ** attempt, 15))
                continue
            last = f"HTTP {r.status_code}: {r.text[:300]}"
            break
    finally:
        with _lock:
            _spent += usd - est  # replace reservation with actual
            with open(COSTS, "a", encoding="utf-8") as f:
                u = (rec or {}).get("usage", {})
                f.write(json.dumps({"ts": time.time(), "model": model, "tag": tag, "key": k[:16],
                                    "ok": rec is not None,
                                    "input_tokens": u.get("input_tokens", u.get("prompt_tokens")),
                                    "output_tokens": u.get("output_tokens", u.get("completion_tokens")),
                                    "usd": usd, "usd_source": (rec or {}).get("usd_source"),
                                    "latency_s": (rec or {}).get("latency_s"),
                                    "cumulative_usd": round(_spent, 8)}) + "\n")
    if rec is None:
        return {"ok": False, "error": last, "cached": False}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(rec, f, ensure_ascii=False)
    rec["cached"] = False
    return rec


def run_jobs(jobs: list[tuple], concurrency: int = 6) -> list[dict]:
    """jobs: (model, state, questions, tag)."""
    out = [None] * len(jobs)
    with cf.ThreadPoolExecutor(max_workers=concurrency) as ex:
        futs = {ex.submit(call, *j): i for i, j in enumerate(jobs)}
        for fu in cf.as_completed(futs):
            try:
                out[futs[fu]] = fu.result()
            except BudgetExceeded as e:
                out[futs[fu]] = {"ok": False, "error": str(e), "cached": False}
    return out


# --------------------------------------------------------------------------
# Units: one per non-identical sentence pair (same unit definition as Sept A3)
# --------------------------------------------------------------------------
SEV_ORDER = {"minor": 0, "major": 1, "critical": 2}


def load_set(lang: str, set_name: str) -> dict[str, dict]:
    return S.load_reference_set(lang, set_name)


def sept_a3_answers(lang: str, set_name: str) -> dict[str, dict]:
    out = {}
    for r in S.load_responses("A3", lang, set_name):
        if r.get("ok") and not r.get("skipped"):
            out[f"{r['item_id']}::{r['pair_idx']}"] = r
    return out


def _tok(text: str, lang: str) -> list[str]:
    if lang == "en":
        return re.findall(r"\s+|\w+|[^\w\s]", text)
    return list(text)


def diff_marks(ref: str, rep: str, lang: str) -> tuple[str, str, str]:
    """Returns (ref_marked, learner_marked, changes_text). Differing fragments are
    wrapped in [[ ]]; changes lists each edit with a little context."""
    a, b = _tok(ref, lang), _tok(rep, lang)
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    ra, rb, changes = [], [], []
    ctx = 2 if lang == "en" else 3
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == "equal":
            ra.append("".join(a[i1:i2])); rb.append("".join(b[j1:j2]))
            continue
        fa, fb = "".join(a[i1:i2]), "".join(b[j1:j2])
        if fa:
            ra.append("[[" + fa + "]]")
        if fb:
            rb.append("[[" + fb + "]]")
        pre = "".join(b[max(0, j1 - ctx):j1]); post = "".join(b[j2:j2 + ctx])
        if op == "replace":
            changes.append(f'reference "{fa.strip()}" -> learner "{fb.strip()}" (in: ...{pre}[[{fb}]]{post}...)')
        elif op == "delete":
            changes.append(f'learner dropped "{fa.strip()}" (in: ...{pre}[[]]{post}...)')
        else:
            changes.append(f'learner inserted "{fb.strip()}" (in: ...{pre}[[{fb}]]{post}...)')
    return "".join(ra), "".join(rb), "\n".join(f"{i+1}. {c}" for i, c in enumerate(changes))


def build_units(lang: str, set_name: str) -> list[dict]:
    """Every non-identical sentence pair of every item, with gold labels attached
    (labels are only read by fit/eval code, never put in a request)."""
    ref = load_set(lang, set_name)
    units = []
    for iid, item in ref.items():
        res = SENT.build_sentence_pairs(item["reference"], item["reproduction"])
        idxs = SENT.map_errors_to_pairs(item["expected_errors"], res.pairs)
        by_pair: dict[int, list[dict]] = {}
        for e, i in zip(item["expected_errors"], idxs):
            if i is not None:
                by_pair.setdefault(i, []).append(e)
        for i, pr in enumerate(res.pairs):
            if pr.ref.text == pr.repro.text:
                continue
            errs = by_pair.get(i, [])
            gsub, gsev = SA3._representative(errs)
            units.append({"key": f"{iid}::{i}", "item_id": iid, "pair_idx": i, "lang": lang, "set": set_name,
                          "ref": pr.ref.text.strip(), "rep": pr.repro.text.strip(),
                          "prev_ref": res.pairs[i - 1].ref.text.strip() if i > 0 else "",
                          "gold_has": bool(errs), "gold_subtype": gsub, "gold_sev": gsev,
                          "gold_errors": [{"subtype": e.get("subtype_v5_target") or e.get("subtype"),
                                           "severity": e.get("severity_v2")} for e in errs]})
    return units


def item_meta(lang: str, set_name: str) -> dict[str, dict]:
    return {iid: {"kind": it["kind"], "bands": it["expected_bands"]} for iid, it in load_set(lang, set_name).items()}


def bands_from_errors(errors: list[dict]) -> dict:
    return S.compute_dimension_bands(errors, S.SUBTYPE_META, S.RUBRIC_CFG)


qwk = S.quadratic_weighted_kappa
bootstrap_ci = S.bootstrap_qwk_ci
auc = SA3.auc_score
DIMS = ("accuracy", "fidelity", "understandability")
LANGS = ("zh", "ja", "en")
