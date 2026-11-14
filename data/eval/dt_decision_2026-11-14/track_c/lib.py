# -*- coding: utf-8 -*-
"""Offline data assembly for Track C: per-pair records joining gold/silver labels,
cached September jev A3 answers, stage-2 LLM outputs, recorded live-grader outputs."""
from __future__ import annotations
import difflib, json, os, statistics
import common as C

A = C.load_sept()
S, SENT, T, REQ = A.S, A.SENT, A.T, A.REQ
DIMS = A.DIMS
SEV = {"minor": 0, "major": 1, "critical": 2}
LANGS = ("en", "zh", "ja")
MODELS = {"qwen": "qwen/qwen3.7-flash", "deepseek": "deepseek/deepseek-v4.1-flash", "haiku": "anthropic/claude-haiku-5.5"}
LIVE_DIR = os.path.join(C.REPO, "data", "eval", "dt_v6_gate_2026-10-08")
# recorded live-grader runs (2026-10-08 gate): arm A = v5 gold fixtures, arm C = silver
LIVE_COST_PER_ITEM = {"gold": {"en": 0.0461 / 30, "zh": 0.2517 / 30, "ja": 0.3642 / 30},
                      "silver": {"en": 0.0771 / 35, "zh": 0.3199 / 34, "ja": 0.4346 / 32}}
# rough wall time per item from the gate report (EN ~2 min/30 items; ZH ~35 min/30; JA "~1.8 min per item")
LIVE_LATENCY_S = {"en": 4.0, "zh": 70.0, "ja": 108.0}


def frozen_cfg(lang):
    with open(os.path.join(C.SEPT, "results", f"frozen_config_{lang}.json"), encoding="utf-8") as f:
        c = json.load(f)
    return {k: c[k] for k in ("tau", "tau_n", "tau_c", "variant")}


def jev_call_stats(lang, set_name):
    """Per-pair jev A3 cost + latency from the September ledger: {job_key: (usd, latency)}"""
    out = {}
    with open(os.path.join(C.SEPT, "costs.jsonl"), encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            if r.get("arm") == "A3" and r["lang"] == lang and r["set"] == set_name and r.get("ok"):
                out[r["job_key"]] = (r["cost"], r["latency_s"])
    return out


def load_stage2(scope, model_key, lang, set_name):
    fn = os.path.join(C.HERE, "stage2", f"{scope}_{MODELS[model_key].replace('/', '__')}_{lang}_{set_name}.jsonl")
    if not os.path.exists(fn):
        return None
    with open(fn, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def load_live(lang, set_name):
    arm = "A" if set_name == "gold" else "C"
    out = {}
    with open(os.path.join(LIVE_DIR, f"{lang}_{arm}.ckpt.jsonl"), encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            if r.get("type") == "record":
                out[r["data"]["id"]] = r["data"]
    return out


def map_claim_to_pair(claim, pairs, reference, reproduction):
    """Locate an LLM item-level claim in a sentence pair. Prefers non-identical pairs."""
    diff_idx = [i for i, p in enumerate(pairs) if p.ref.text != p.repro.text]
    if not diff_idx:
        return None
    for text, side in ((claim.get("learner") or "", "repro"), (claim.get("correct") or "", "ref")):
        text = text.strip()
        if not text:
            continue
        hits = [i for i in diff_idx if text in getattr(pairs[i], side).text]
        if len(hits) == 1:
            return hits[0]
        if len(hits) > 1:  # disambiguate: the pair where the text is NOT also on the other side
            other = "ref" if side == "repro" else "repro"
            h2 = [i for i in hits if text not in getattr(pairs[i], other).text]
            return (h2 or hits)[0]
    key = (claim.get("learner") or "") + (claim.get("correct") or "")
    if not key:
        return diff_idx[0]
    return max(diff_idx, key=lambda i: difflib.SequenceMatcher(None, key, pairs[i].repro.text + pairs[i].ref.text).ratio())


def build(lang, set_name):
    """-> dict item_id -> {bands, kind, pairs:[{idx, gold_has, gold_sev, gold_n, jev..., llm:{model:[errs]}, ...}],
    item_llm:{model:{claims:[{pair_idx,...}], usd, latency}}, live:{...}}"""
    ref = A.load_reference(lang, set_name)
    units = A.a3_units(lang, set_name)
    cfg = frozen_cfg(lang)
    jstats = jev_call_stats(lang, set_name)
    live = load_live(lang, set_name)
    pair_llm = {}
    for mk in MODELS:
        recs = load_stage2("pair", mk, lang, set_name)
        if recs:
            pair_llm[mk] = {(r["item_id"], r["pair_idx"]): r for r in recs}
    item_llm = {}
    for mk in MODELS:
        recs = load_stage2("item", mk, lang, set_name)
        if recs:
            item_llm[mk] = {r["item_id"]: r for r in recs}

    items = {}
    for iid, it in ref.items():
        res = SENT.build_sentence_pairs(it["reference"], it["reproduction"])
        err_idx = SENT.map_errors_to_pairs(it["expected_errors"], res.pairs)
        gold_by_pair = {}
        for e, i in zip(it["expected_errors"], err_idx):
            if i is not None:
                gold_by_pair.setdefault(i, []).append(e)
        ubyidx = {u["pair_idx"]: u for u in units.get(iid, [])}
        pairs = []
        for idx, pr in enumerate(res.pairs):
            if pr.ref.text == pr.repro.text:
                continue
            u = ubyidx.get(idx)
            ans = u["answers"] if u else {}
            he = REQ.decode_noul(ans, "has_error") or 0.0
            narrow = max([(REQ.decode_narrow(ans, n) or 0.0) for n in REQ.R.NARROW_NOUL] or [0.0])
            jerr = A.decide_a3(ans, lang, **cfg) if u else None
            g = gold_by_pair.get(idx, [])
            gsev = max((e["severity_v2"] for e in g if e.get("severity_v2")), key=lambda s: SEV[s], default=None)
            gsub = None
            if g:
                best = max(g, key=lambda e: SEV.get(e.get("severity_v2"), -1))
                gsub = best.get("subtype_v5_target") or best.get("subtype")
            js = jstats.get(f"{iid}::{idx}", (None, None))
            p = {"idx": idx, "ref": pr.ref.text, "learner": pr.repro.text, "gold_has": bool(g), "gold_sev": gsev,
                 "gold_sub": gsub, "gold_n": len(g), "gold_forms": [(e.get("learner_form"), e.get("corrected_form")) for e in g],
                 "jev_ok": u is not None, "he_p": he, "narrow": narrow, "sig": max(he, narrow), "jev_err": jerr,
                 "jev_usd": js[0], "jev_lat": js[1], "llm": {}}
            for mk, d in pair_llm.items():
                r = d.get((iid, idx))
                if r:
                    p["llm"][mk] = {"errors": r["errors"], "usd": r["usd"], "lat": r["latency_s"], "parse_ok": r["parse_ok"]}
            pairs.append(p)
        rec = {"id": iid, "kind": it["kind"], "bands": {d: it["expected_bands"][d] for d in DIMS}, "pairs": pairs,
               "n_pairs_total": len(res.pairs), "item_llm": {}, "live": None,
               "reference": it["reference"], "reproduction": it["reproduction"]}
        for mk, d in item_llm.items():
            r = d.get(iid)
            if r:
                claims = []
                for e in r["errors"]:
                    pi = map_claim_to_pair(e, res.pairs, it["reference"], it["reproduction"])
                    claims.append({**e, "pair_idx": pi})
                rec["item_llm"][mk] = {"claims": claims, "usd": r["usd"], "lat": r["latency_s"]}
        lv = live.get(iid)
        if lv:
            # map live predicted spans (offsets into the reproduction) to pairs
            lp = []
            for e in lv["pred_errors"]:
                st = e["span"][0]
                pi = next((i for i, pr in enumerate(res.pairs) if pr.repro.start <= st < pr.repro.end), None)
                lp.append({"pair_idx": pi, "subtype": e["subtype"], "severity": e["severity"]})
            rec["live"] = {"bands": {d: lv["pred_bands"][d] for d in DIMS}, "errors": lp}
        items[iid] = rec
    return items


def bands_from_errors(errors):
    """errors: [{subtype, severity}] -> accuracy/fidelity/understandability bands via the live scoring code."""
    b = S.compute_dimension_bands(errors, S.SUBTYPE_META, S.RUBRIC_CFG)
    return {d: b[d] for d in DIMS}


def qwk(yt, yp):
    return S.quadratic_weighted_kappa(yt, yp)


def pct(vals, q):
    vals = sorted(vals)
    if not vals:
        return float("nan")
    k = (len(vals) - 1) * q
    lo, hi = int(k), min(int(k) + 1, len(vals) - 1)
    return vals[lo] + (vals[hi] - vals[lo]) * (k - lo)
