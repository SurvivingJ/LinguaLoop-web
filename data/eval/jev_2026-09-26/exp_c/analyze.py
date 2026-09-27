# -*- coding: utf-8 -*-
"""Analysis pass over raw/results.jsonl: per-dimension QWK (score & choice mode)
vs gold, overall-band QWK, noul error-detection accuracy, hybrid tier-0 routing
simulation, cost/latency, and native-vs-English-control comparison.

Reuses services.dual_translation.eval_metrics.quadratic_weighted_kappa (pure,
stdlib-only module -- confirmed no DB/service imports) so QWK numbers are
computed with the exact same function LinguaLoop's own DT harness uses.
"""
from __future__ import annotations

import json
import os
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = r"c:\Users\James\Documents\Coding\LinguaLoop\WebApp"
sys.path.insert(0, HERE)
sys.path.insert(0, REPO)

import rubric_data as R  # noqa: E402
import build_requests as BR  # noqa: E402
from services.dual_translation.eval_metrics import quadratic_weighted_kappa, agreement  # noqa: E402

RAW = os.path.join(HERE, "raw", "results.jsonl")


def load_records():
    recs = []
    with open(RAW, encoding="utf-8") as f:
        for line in f:
            recs.append(json.loads(line))
    return recs


def compute_overall(bands: dict, weights: dict, present) -> int:
    present = [d for d in present if d in bands and d in weights]
    total_w = sum(weights[d] for d in present)
    if total_w <= 0:
        vals = [bands[d] for d in present]
        return max(1, min(4, round(sum(vals) / len(vals)))) if vals else 4
    s = sum(bands[d] * weights[d] for d in present)
    return max(1, min(4, round(s / total_w)))


def pct(x):
    return f"{100*x:.1f}%" if x == x else "n/a"  # NaN check


def main():
    recs = load_records()
    native = [r for r in recs if r["run"] == "native"]
    control = [r for r in recs if r["run"] == "control"]

    for r in recs:
        r["decoded"] = BR.decode_answers(r["answers"])

    report = {"per_lang_dim": {}, "overall": {}, "noul": {}, "hybrid": {}, "cost_latency": {}, "control": {}}

    # ---------------- per-dimension QWK, score mode vs choice mode ----------------
    for lang in ["en", "zh", "ja"]:
        lang_recs = [r for r in native if r["lang"] == lang]
        report["per_lang_dim"][lang] = {}
        for dim in R.DIMENSIONS:
            yt = [r["expected_bands"][dim] for r in lang_recs]
            yp_score = [r["decoded"]["dims"][dim]["score_band"] for r in lang_recs]
            yp_choice = [r["decoded"]["dims"][dim]["choice_band"] for r in lang_recs]
            qwk_score = quadratic_weighted_kappa(yt, yp_score)
            qwk_choice = quadratic_weighted_kappa(yt, yp_choice)
            ag_score = agreement(yt, yp_score)
            ag_choice = agreement(yt, yp_choice)
            report["per_lang_dim"][lang][dim] = {
                "n": len(lang_recs),
                "qwk_score": qwk_score, "qwk_choice": qwk_choice,
                "exact_score": ag_score["exact"], "adjacent_score": ag_score["adjacent"],
                "exact_choice": ag_choice["exact"], "adjacent_choice": ag_choice["adjacent"],
            }

    # ---------------- overall band (weighted mean) QWK ----------------
    for lang in ["en", "zh", "ja"]:
        lang_recs = [r for r in native if r["lang"] == lang]
        w = R.resolve_weights(lang)
        yt, yp_s, yp_c = [], [], []
        for r in lang_recs:
            exp_overall = compute_overall(r["expected_bands"], w, R.DIMENSIONS)
            score_bands = {d: r["decoded"]["dims"][d]["score_band"] or 1 for d in R.DIMENSIONS}
            choice_bands = {d: r["decoded"]["dims"][d]["choice_band"] or 1 for d in R.DIMENSIONS}
            pred_overall_s = compute_overall(score_bands, w, R.DIMENSIONS)
            pred_overall_c = compute_overall(choice_bands, w, R.DIMENSIONS)
            yt.append(exp_overall)
            yp_s.append(pred_overall_s)
            yp_c.append(pred_overall_c)
        report["overall"][lang] = {
            "n": len(lang_recs),
            "qwk_score_mode": quadratic_weighted_kappa(yt, yp_s),
            "qwk_choice_mode": quadratic_weighted_kappa(yt, yp_c),
            "exact_score_mode": agreement(yt, yp_s)["exact"],
            "exact_choice_mode": agreement(yt, yp_c)["exact"],
        }

    # ---------------- noul error-detection ----------------
    def has_omission(exp_errors):
        return any(e.get("subtype") == "omission" for e in exp_errors)

    for lang in ["en", "zh", "ja"]:
        lang_recs = [r for r in native if r["lang"] == lang]
        omission_gt = [has_omission(r["expected_errors"]) for r in lang_recs]
        grammar_gt = [r["expected_bands"]["accuracy"] < 4 for r in lang_recs]
        omission_p = [r["decoded"]["noul"]["noul_omission"] for r in lang_recs]
        grammar_p = [r["decoded"]["noul"]["noul_grammar"] for r in lang_recs]

        def eval_noul(gt, p, thresh=0.5):
            tp = sum(1 for g, pr in zip(gt, p) if g and pr >= thresh)
            fp = sum(1 for g, pr in zip(gt, p) if not g and pr >= thresh)
            fn = sum(1 for g, pr in zip(gt, p) if g and pr < thresh)
            tn = sum(1 for g, pr in zip(gt, p) if not g and pr < thresh)
            acc = (tp + tn) / len(gt) if gt else float("nan")
            pos_rate = sum(gt) / len(gt) if gt else float("nan")
            # simple rank AUC (Mann-Whitney U)
            pos = [pr for g, pr in zip(gt, p) if g]
            neg = [pr for g, pr in zip(gt, p) if not g]
            auc = float("nan")
            if pos and neg:
                greater = sum(1 for a in pos for b in neg if a > b)
                ties = sum(1 for a in pos for b in neg if a == b)
                auc = (greater + 0.5 * ties) / (len(pos) * len(neg))
            return {"tp": tp, "fp": fp, "fn": fn, "tn": tn, "accuracy": acc, "base_rate": pos_rate, "auc": auc}

        report["noul"][lang] = {
            "omission": eval_noul(omission_gt, omission_p),
            "grammar": eval_noul(grammar_gt, grammar_p),
        }

    # ---------------- hybrid tier-0 routing simulation ----------------
    # Candidate rule: item is "confidently perfect" if EVERY dim's choice ==
    # band4 with confidence >= tau; "confidently bad" if EVERY dim's choice
    # <= band2 with confidence >= tau. Both classes are candidates to skip the
    # expensive cascade. Error rate = fraction of routed items whose jev
    # overall band (weighted mean) != gold overall band.
    for lang in ["en", "zh", "ja"]:
        lang_recs = [r for r in native if r["lang"] == lang]
        w = R.resolve_weights(lang)
        report["hybrid"][lang] = {}
        for tau in (0.7, 0.8, 0.9, 0.95):
            routed = 0
            wrong = 0
            for r in lang_recs:
                dims = r["decoded"]["dims"]
                confs = [dims[d]["choice_confidence"] or 0 for d in R.DIMENSIONS]
                bands = [dims[d]["choice_band"] or 0 for d in R.DIMENSIONS]
                all_perfect = all(b == 4 for b in bands) and min(confs) >= tau
                all_bad = all(b <= 2 for b in bands) and min(confs) >= tau
                if all_perfect or all_bad:
                    routed += 1
                    w_ = R.resolve_weights(lang)
                    exp_overall = compute_overall(r["expected_bands"], w_, R.DIMENSIONS)
                    pred_bands = {d: dims[d]["choice_band"] or 1 for d in R.DIMENSIONS}
                    pred_overall = compute_overall(pred_bands, w_, R.DIMENSIONS)
                    if pred_overall != exp_overall:
                        wrong += 1
            report["hybrid"][lang][str(tau)] = {
                "n": len(lang_recs), "routed": routed,
                "routed_pct": routed / len(lang_recs) if lang_recs else float("nan"),
                "wrong_among_routed": wrong,
                "error_rate_if_routed": (wrong / routed) if routed else float("nan"),
            }

    # ---------------- cost / latency ----------------
    all_costs = [float(r["usage"].get("cost", 0) or 0) for r in recs]
    all_lat = sorted(r["latency_s"] for r in recs)
    n = len(all_lat)
    def pctl(p):
        if not all_lat:
            return float("nan")
        idx = min(n - 1, int(round(p * (n - 1))))
        return all_lat[idx]
    report["cost_latency"] = {
        "n_calls": len(recs),
        "total_cost_usd": sum(all_costs),
        "mean_cost_per_call": statistics.mean(all_costs) if all_costs else float("nan"),
        "mean_input_tokens": statistics.mean([r["usage"].get("input_tokens", 0) for r in recs]),
        "mean_output_tokens": statistics.mean([r["usage"].get("output_tokens", 0) for r in recs]),
        "latency_p50": pctl(0.50),
        "latency_p95": pctl(0.95),
        "latency_mean": statistics.mean(all_lat) if all_lat else float("nan"),
        # cost per single dimension-judgment: 1 call answers 5 dims x 2 modes + 2 noul.
        "cost_per_item_all_12_questions": statistics.mean(all_costs) if all_costs else float("nan"),
        "cost_per_dimension_judgment_score_mode": (statistics.mean(all_costs) / 5) if all_costs else float("nan"),
    }

    # ---------------- native vs English-prompt control (zh/ja) ----------------
    for lang in ["zh", "ja"]:
        native_subset_ids = {r["item_id"] for r in control if r["lang"] == lang}
        native_subset = [r for r in native if r["lang"] == lang and r["item_id"] in native_subset_ids]
        control_subset = [r for r in control if r["lang"] == lang]
        # order both by item_id to align
        native_subset.sort(key=lambda r: r["item_id"])
        control_subset.sort(key=lambda r: r["item_id"])
        entry = {"n": len(control_subset), "per_dim": {}}
        for dim in R.DIMENSIONS:
            yt = [r["expected_bands"][dim] for r in native_subset]
            yp_native = [r["decoded"]["dims"][dim]["score_band"] for r in native_subset]
            yp_control = [r["decoded"]["dims"][dim]["score_band"] for r in control_subset]
            entry["per_dim"][dim] = {
                "native_exact": agreement(yt, yp_native)["exact"],
                "control_exact": agreement(yt, yp_control)["exact"],
                "native_qwk": quadratic_weighted_kappa(yt, yp_native),
                "control_qwk": quadratic_weighted_kappa(yt, yp_control),
            }
        report["control"][lang] = entry

    out_path = os.path.join(HERE, "raw", "analysis.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
