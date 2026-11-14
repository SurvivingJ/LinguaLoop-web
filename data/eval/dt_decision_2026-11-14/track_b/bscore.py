# -*- coding: utf-8 -*-
"""Score runs/<alias>__<variant>__<set>.jsonl against the v6 fixtures.

Bands come from the UNCHANGED live services.dual_translation.scoring.compute_dimension_bands
fed scripts.dt_gold_seed_helper.OFFLINE_SCORING_CONFIG (what the fixtures were derived with);
span P/R/F1, subtype accuracy, severity agreement, clean FP and QWK come from the live
services.dual_translation.eval_metrics (same functions as the Oct-08 v6 gate), so numbers are
directly comparable with the live grader's.

Severity rule (zero-cost post-processing, chosen on silver):
  model   = the model's own severity
  prior   = the taxonomy default severity of the predicted type; critical if the model said critical
"""
from __future__ import annotations
import json, math, os, random, statistics, sys
import common as C
from scripts.dt_gold_seed_helper import OFFLINE_SCORING_CONFIG as CFG
from services.dual_translation import eval_metrics as EM
from services.dual_translation.scoring import compute_dimension_bands

DIMS = ("accuracy", "fidelity", "understandability", "naturalness")
LANGS = ("en", "zh", "ja")


def apply_sev(errors, rule):
    out = []
    for e in errors:
        e = dict(e)
        if rule == "prior" and e["severity"] != "critical":
            e["severity"] = C.SUBTYPE_META[e["subtype"]]["default_severity"]
            if e["severity"] == "critical":  # meaning_inversion default
                e["severity"] = "critical"
        out.append(e)
    return out


def bands_of(errors):
    b = compute_dimension_bands(errors, C.SUBTYPE_META, CFG)
    # naturalness is model-judged live; here: derived proxy = 3 if any naturalness-type error else 4
    b["naturalness"] = 3 if any(C.SUBTYPE_META[e["subtype"]]["dimension"] == "naturalness" for e in errors) else 4
    return b


def load_run(alias, variant, which):
    p = os.path.join(C.HERE, "runs", f"{alias}__{variant}__{which}.jsonl")
    with open(p, encoding="utf-8") as f:
        return {r["id"]: r for r in map(json.loads, f)}


def records(run, which, lang, rule):
    recs = []
    for it in C.load_set(which, lang):
        r = run[it["id"]]
        pred = apply_sev(r["errors"], rule)
        recs.append({
            "id": it["id"], "kind": it.get("kind", "single"),
            "pred_errors": pred,
            "exp_errors": [{"span": e["span_repro"], "subtype": e["subtype"], "severity": e["severity_v2"]}
                           for e in it["expected_errors"]],
            "pred_bands": bands_of(pred), "exp_bands": it["expected_bands"],
            "exp_overall": None, "pred_overall": None,
            "valid": r["valid"], "usd": r.get("usd") or 0.0, "latency": r.get("latency"),
            "span_miss": r.get("span_miss", 0), "called": bool(r.get("prompt_tokens")),
            "ptok": r.get("prompt_tokens") or 0, "ctok": r.get("completion_tokens") or 0,
        })
    return recs


def _nan0(x):
    return None if (isinstance(x, float) and math.isnan(x)) else x


def boot_ci(yt, yp, n=1000, seed=7):
    rng = random.Random(seed)
    idx = list(range(len(yt)))
    vals = []
    for _ in range(n):
        s = [rng.choice(idx) for _ in idx]
        v = EM.quadratic_weighted_kappa([yt[i] for i in s], [yp[i] for i in s])
        if not math.isnan(v):
            vals.append(v)
    vals.sort()
    if not vals:
        return [None, None]
    return [round(vals[int(.025 * len(vals))], 3), round(vals[int(.975 * len(vals)) - 1], 3)]


def metrics(recs, ci=False):
    m = EM.aggregate_metrics(recs, dimensions=DIMS)
    out = {"n": len(recs)}
    for d in DIMS:
        out["qwk_" + d] = _nan0(round(m["bands"][d]["qwk"], 3)) if not math.isnan(m["bands"][d]["qwk"]) else None
        out["exact_" + d] = round(m["bands"][d]["exact"], 3)
        if ci:
            out["ci_" + d] = boot_ci([r["exp_bands"][d] for r in recs], [r["pred_bands"][d] for r in recs])
    q3 = [out["qwk_" + d] or 0.0 for d in DIMS[:3]]
    out["qwk_mean3"] = round(sum(q3) / 3, 3)
    out["span_p"], out["span_r"], out["span_f1"] = (round(m["span"][k], 3) for k in ("precision", "recall", "f1"))
    out["tp_fp_fn"] = [m["span"]["tp"], m["span"]["fp"], m["span"]["fn"]]
    out["type_top1"] = _nan0(round(m["subtype_accuracy"]["accuracy"], 3))
    out["type_n"] = m["subtype_accuracy"]["total"]
    out["sev_exact"] = _nan0(round(m["severity"]["exact"], 3))
    out["clean_fp_rate"] = _nan0(m["clean_fp"].get("rate"))
    out["clean_fp_raw"] = m["clean_fp"]
    # item-level detection (any error predicted vs any error expected)
    tp = sum(1 for r in recs if r["pred_errors"] and r["exp_errors"])
    fp = sum(1 for r in recs if r["pred_errors"] and not r["exp_errors"])
    fn = sum(1 for r in recs if not r["pred_errors"] and r["exp_errors"])
    out["item_det"] = {"tp": tp, "fp": fp, "fn": fn, "n_clean": sum(1 for r in recs if not r["exp_errors"])}
    # meaning inversion: gold MI errors span-matched by a prediction; split by label/critical
    mi_n = mi_hit = mi_crit = mi_type = 0
    for r in recs:
        al = EM.align_errors([p["span"] for p in r["pred_errors"]], [e["span"] for e in r["exp_errors"]])
        matched = {j: i for i, j in al.matches}
        for j, e in enumerate(r["exp_errors"]):
            if e["subtype"] != "meaning_inversion":
                continue
            mi_n += 1
            if j in matched:
                mi_hit += 1
                p = r["pred_errors"][matched[j]]
                mi_crit += p["severity"] == "critical"
                mi_type += p["subtype"] == "meaning_inversion"
    out["mi"] = {"n": mi_n, "flagged": mi_hit, "critical": mi_crit, "typed_mi": mi_type}
    out["mi_false_pos"] = sum(1 for r in recs for i, p in enumerate(r["pred_errors"])
                              if p["subtype"] == "meaning_inversion") - mi_type
    out["json_valid"] = round(sum(r["valid"] for r in recs) / len(recs), 3)
    called = [r for r in recs if r["called"]]
    out["usd_per_item"] = round(sum(r["usd"] for r in recs) / len(recs), 7)
    lat = [r["latency"] for r in called if r["latency"]]
    out["p50_latency_s"] = round(statistics.median(lat), 2) if lat else None
    out["p90_latency_s"] = round(sorted(lat)[int(.9 * len(lat)) - 1], 2) if lat else None
    out["tok_in"] = round(sum(r["ptok"] for r in called) / max(1, len(called)))
    out["tok_out"] = round(sum(r["ctok"] for r in called) / max(1, len(called)))
    out["span_miss"] = sum(r["span_miss"] for r in recs)
    out["n_pred_errors"] = sum(len(r["pred_errors"]) for r in recs)
    return out


def score(alias, variant, which, rule="model", ci=False):
    run = load_run(alias, variant, which)
    return {l: metrics(records(run, which, l, rule), ci) for l in LANGS}


if __name__ == "__main__":
    which = sys.argv[1]
    arms = sys.argv[2:]
    cols = ["qwk_accuracy", "qwk_fidelity", "qwk_understandability", "qwk_mean3", "span_p", "span_r", "type_top1", "sev_exact"]
    print("arm".ljust(34), "lang", " ".join(c.replace("qwk_", "q_")[:9].rjust(9) for c in cols), "  cleanFP  MI(flag/crit/n) $/item")
    for arm in arms:
        alias, variant = arm.split(":")
        for rule in ("model", "prior"):
            s = score(alias, variant, which, rule)
            for l in LANGS:
                m = s[l]
                print(f"{arm}/{rule}".ljust(34), l.ljust(4), " ".join(("%.3f" % m[c] if m[c] is not None else "  nan").rjust(9) for c in cols),
                      f"  {m['item_det']['fp']}/{m['item_det']['n_clean']}".ljust(9), f"{m['mi']['flagged']}/{m['mi']['critical']}/{m['mi']['n']}".ljust(15), "%.6f" % m["usd_per_item"])
