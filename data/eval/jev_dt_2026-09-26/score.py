# -*- coding: utf-8 -*-
"""Scores cached jev responses (A1/A2/NR) against tests/fixtures/dt_gold and
writes results/<arm>_<lang>_<set>.json + a markdown table.

Decision rule (pluggable severity_fn, default `severity_major_minor`):
    error exists   <=> has_error probability >= tau (default 0.5)
    subtype        = argmax over the choice-question's non-"no_error" options
                      (only computed/used when an error is judged present)
    severity       = severity_fn(meaning_changed_probability)
        default:  major if p >= 0.5 else minor
        variant:  critical if p >= 0.9 else (major if p >= 0.5 else minor)

Built error records are handed to services.dual_translation.scoring's live
derivation (compute_dimension_bands / resolve_weights / compute_overall),
fed the OFFLINE pinned config (scripts.dt_gold_seed_helper.OFFLINE_SCORING_CONFIG)
that the gold `expected_bands` were themselves derived under (per
tests/fixtures/dt_gold/README.md), so predicted and gold bands are computed
by the exact same formula. NR's score-mode answers supply naturalness/range
directly (model-judged in production too, so no derivation needed there).

QWK is `services.dual_translation.eval_metrics.quadratic_weighted_kappa` --
reused, not reimplemented, per the task's explicit instruction.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import random
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, HERE)

from dotenv import load_dotenv  # noqa: E402
load_dotenv(os.path.join(REPO, ".env"))  # HARD RULE: before any services.* import

sys.path.insert(0, REPO)
from scripts.dt_gold_seed_helper import OFFLINE_SCORING_CONFIG  # noqa: E402
from services.dual_translation.eval_metrics import quadratic_weighted_kappa  # noqa: E402
from services.dual_translation.scoring import compute_dimension_bands, resolve_weights, compute_overall  # noqa: E402

import rubric_data as R  # noqa: E402
import reqbuild as REQ  # noqa: E402
import taxonomy_data as T  # noqa: E402
import sentences as SENT  # noqa: E402

GOLD_DIR = os.path.join(REPO, "tests", "fixtures", "dt_gold")
RESPONSES_DIR = os.path.join(HERE, "responses")
RESULTS_DIR = os.path.join(HERE, "results")
os.makedirs(RESULTS_DIR, exist_ok=True)

RUBRIC_CFG = OFFLINE_SCORING_CONFIG
SUBTYPE_META = {s: {"dimension": d} for s, d in T.SUBTYPE_DIMENSION.items()}


# ---------------------------------------------------------------------------
# Decision rule (pluggable)
# ---------------------------------------------------------------------------

def severity_major_minor(meaning_changed_p: float | None) -> str:
    """Default rule: major if meaning_changed>=0.5 else minor."""
    p = meaning_changed_p if meaning_changed_p is not None else 0.0
    return "major" if p >= 0.5 else "minor"


def severity_with_critical(meaning_changed_p: float | None) -> str:
    """Variant: critical if meaning_changed>=0.9, else major/minor at 0.5."""
    p = meaning_changed_p if meaning_changed_p is not None else 0.0
    if p >= 0.9:
        return "critical"
    return "major" if p >= 0.5 else "minor"


SEVERITY_FNS = {"major_minor": severity_major_minor, "with_critical": severity_with_critical}


def decide_error(answers: dict, lang: str, tau: float, severity_fn) -> dict:
    """Turn one call's raw `answers` into a decision record:
    {has_error_p, has_error, subtype, subtype_probs, meaning_changed_p, severity}."""
    he_p = REQ.decode_noul(answers, "has_error")
    mc_p = REQ.decode_noul(answers, "meaning_changed")
    choice_key, choice_conf, choice_probs = REQ.decode_choice(answers, "subtype")

    has_error = (he_p if he_p is not None else 0.0) >= tau

    subtype = None
    if has_error:
        options = T.SUBTYPES[lang] + ["no_error"]
        if choice_probs:
            # argmax over probabilities restricted to real subtypes (exclude no_error)
            best, best_p = None, -1.0
            for opt in T.SUBTYPES[lang]:
                p = choice_probs.get(opt, 0.0) or 0.0
                if p > best_p:
                    best, best_p = opt, p
            subtype = best
        elif choice_key and choice_key != "no_error":
            subtype = choice_key

    severity = severity_fn(mc_p) if has_error else None

    return {
        "has_error_p": he_p, "has_error": has_error,
        "subtype": subtype, "choice_key": choice_key, "choice_probs": choice_probs,
        "meaning_changed_p": mc_p, "severity": severity,
    }


# ---------------------------------------------------------------------------
# Loading cached responses
# ---------------------------------------------------------------------------

SILVER_DIR = os.path.join(HERE, "silver")


def load_gold(lang: str) -> dict[str, dict]:
    with open(os.path.join(GOLD_DIR, f"{lang}.json"), encoding="utf-8") as f:
        items = json.load(f)
    return {it["id"]: it for it in items}


def silver_path(lang: str) -> str:
    """Prefer <lang>_final3.json (MQM-severity-labeled silver set) over
    <lang>_final.json when both exist -- mirrors run.py's silver_path."""
    p3 = os.path.join(SILVER_DIR, f"{lang}_final3.json")
    if os.path.exists(p3):
        return p3
    return os.path.join(SILVER_DIR, f"{lang}_final.json")


def load_silver(lang: str) -> dict[str, dict]:
    path = silver_path(lang)
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"--set silver requested but neither {os.path.join(SILVER_DIR, lang + '_final3.json')} "
            f"nor {path} exists yet (same schema as tests/fixtures/dt_gold/{lang}.json expected) "
            f"-- this harness does not create it."
        )
    with open(path, encoding="utf-8") as f:
        items = json.load(f)
    return {it["id"]: it for it in items}


def load_reference_set(lang: str, set_name: str) -> dict[str, dict]:
    return load_gold(lang) if set_name == "gold" else load_silver(lang)


def load_responses(arm: str, lang: str, set_name: str) -> list[dict]:
    path = os.path.join(RESPONSES_DIR, f"{arm}_{lang}_{set_name}.jsonl")
    recs = []
    if not os.path.exists(path):
        return recs
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                recs.append(json.loads(line))
    return recs


# ---------------------------------------------------------------------------
# Per-item derived predictions
# ---------------------------------------------------------------------------

def predict_a1(records: list[dict], gold: dict[str, dict], lang: str, tau: float, severity_fn) -> dict[str, dict]:
    """One record per item -> {item_id: {pred_bands, decisions:[decision]}}."""
    out = {}
    for rec in records:
        if rec.get("skipped") or not rec.get("ok", True):
            continue
        item_id = rec["item_id"]
        decision = decide_error(rec["answers"], lang, tau, severity_fn)
        errors = []
        if decision["has_error"] and decision["subtype"]:
            errors.append({"subtype": decision["subtype"], "severity": decision["severity"]})
        pred_bands = compute_dimension_bands(errors, SUBTYPE_META, RUBRIC_CFG)
        out[item_id] = {"decisions": [decision], "pred_bands": pred_bands, "errors": errors}
    return out


def predict_a2(records: list[dict], gold: dict[str, dict], lang: str, tau: float, severity_fn) -> dict[str, dict]:
    """Group sentence-pair records by item_id -> aggregate error list -> pred_bands."""
    by_item: dict[str, list[dict]] = {}
    for rec in records:
        if rec.get("skipped"):
            continue
        by_item.setdefault(rec["item_id"], []).append(rec)

    out = {}
    for item_id, recs in by_item.items():
        recs.sort(key=lambda r: r.get("pair_idx", 0))
        decisions = []
        errors = []
        for rec in recs:
            if not rec.get("ok", True):
                decisions.append(None)
                continue
            decision = decide_error(rec["answers"], lang, tau, severity_fn)
            decision["pair_idx"] = rec.get("pair_idx")
            decisions.append(decision)
            if decision["has_error"] and decision["subtype"]:
                errors.append({"subtype": decision["subtype"], "severity": decision["severity"]})
        pred_bands = compute_dimension_bands(errors, SUBTYPE_META, RUBRIC_CFG)
        out[item_id] = {"decisions": decisions, "pred_bands": pred_bands, "errors": errors}
    return out


def predict_nr(records: list[dict], gold: dict[str, dict], lang: str) -> dict[str, dict]:
    out = {}
    for rec in records:
        if rec.get("skipped") or not rec.get("ok", True):
            continue
        item_id = rec["item_id"]
        nat_raw, nat_conf = REQ.decode_score(rec["answers"], "score_naturalness")
        rng_raw, rng_conf = REQ.decode_score(rec["answers"], "score_range")
        nat_band = None if nat_raw is None else max(1, min(4, round(float(nat_raw)) + 1))
        rng_band = None if rng_raw is None else max(1, min(4, round(float(rng_raw)) + 1))
        out[item_id] = {"naturalness_band": nat_band, "range_band": rng_band,
                         "naturalness_raw": nat_raw, "range_raw": rng_raw}
    return out


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

def bootstrap_qwk_ci(y_true: list[int], y_pred: list[int], n_boot: int = 1000, seed: int = 0) -> tuple[float, float]:
    n = len(y_true)
    if n == 0:
        return (float("nan"), float("nan"))
    rng = random.Random(seed)
    vals = []
    for _ in range(n_boot):
        idx = [rng.randrange(n) for _ in range(n)]
        yt = [y_true[i] for i in idx]
        yp = [y_pred[i] for i in idx]
        vals.append(quadratic_weighted_kappa(yt, yp))
    vals.sort()
    lo = vals[int(0.025 * n_boot)]
    hi = vals[min(n_boot - 1, int(0.975 * n_boot))]
    return (lo, hi)


def auc_score(labels: list[bool], scores: list[float]) -> float:
    pos = [s for l, s in zip(labels, scores) if l]
    neg = [s for l, s in zip(labels, scores) if not l]
    if not pos or not neg:
        return float("nan")
    greater = sum(1 for a in pos for b in neg if a > b)
    ties = sum(1 for a in pos for b in neg if a == b)
    return (greater + 0.5 * ties) / (len(pos) * len(neg))


def prf1(tp, fp, fn):
    if tp == 0 and fp == 0 and fn == 0:
        return {"precision": 1.0, "recall": 1.0, "f1": 1.0, "tp": 0, "fp": 0, "fn": 0}
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    return {"precision": precision, "recall": recall, "f1": f1, "tp": tp, "fp": fp, "fn": fn}


def item_has_error_gold(item: dict) -> bool:
    return len(item.get("expected_errors", [])) > 0


def item_meaning_severity_gold(item: dict) -> str:
    """Max severity_v2 among the item's expected_errors, or 'none'."""
    order = {"minor": 0, "major": 1, "critical": 2}
    sevs = [e.get("severity_v2") for e in item.get("expected_errors", []) if e.get("severity_v2")]
    if not sevs:
        return "none"
    return max(sevs, key=lambda s: order.get(s, -1))


def sentence_pair_gold_labels(item: dict) -> tuple[list, list]:
    """Per aligned sentence pair: (has_error bool, subtype-or-None) from gold,
    using the same sentence splitter as A2's request builder."""
    res = SENT.build_sentence_pairs(item["reference"], item["reproduction"])
    err_pair_idx = SENT.map_errors_to_pairs(item["expected_errors"], res.pairs)
    n = len(res.pairs)
    has_error = [False] * n
    subtype = [None] * n
    for err, idx in zip(item["expected_errors"], err_pair_idx):
        if idx is None:
            continue
        has_error[idx] = True
        subtype[idx] = err.get("subtype_v5_target") or err.get("subtype")
    return has_error, subtype, res


def score_a1_or_nr_dims(preds: dict[str, dict], golds: dict[str, dict], dims: tuple[str, ...]) -> dict:
    out = {}
    for dim in dims:
        yt, yp = [], []
        for item_id, g in golds.items():
            if item_id not in preds:
                continue
            pb = preds[item_id].get("pred_bands") or preds[item_id]
            if dim not in pb or pb[dim] is None:
                continue
            yt.append(g["expected_bands"][dim])
            yp.append(pb[dim])
        qwk = quadratic_weighted_kappa(yt, yp) if yt else float("nan")
        lo, hi = bootstrap_qwk_ci(yt, yp) if yt else (float("nan"), float("nan"))
        exact = sum(1 for a, b in zip(yt, yp) if a == b) / len(yt) if yt else float("nan")
        out[dim] = {"n": len(yt), "qwk": qwk, "qwk_ci95": [lo, hi], "exact": exact}
    return out


def score_a1(lang: str, set_name: str, tau: float, severity_fn_name: str) -> dict:
    gold = load_reference_set(lang, set_name)
    records = load_responses("A1", lang, set_name)
    severity_fn = SEVERITY_FNS[severity_fn_name]
    preds = predict_a1(records, gold, lang, tau, severity_fn)

    dims = score_a1_or_nr_dims(preds, gold, ("accuracy", "fidelity", "understandability"))

    # sentence-level (=item-level here) error-detection AUC/PR
    labels, scores, tp = [], [], 0
    fp = fn = tn = 0
    for item_id, g in gold.items():
        if item_id not in preds:
            continue
        gt = item_has_error_gold(g)
        p = preds[item_id]["decisions"][0]
        labels.append(gt)
        scores.append(p["has_error_p"] if p["has_error_p"] is not None else 0.0)
        if gt and p["has_error"]:
            tp += 1
        elif not gt and p["has_error"]:
            fp += 1
        elif gt and not p["has_error"]:
            fn += 1
        else:
            tn += 1
    detect = {"auc": auc_score(labels, scores), **prf1(tp, fp, fn), "tn": tn}

    # subtype top1/top3 on truly-erroneous items (gold has >=1 error)
    top1 = top3 = total = 0
    for item_id, g in gold.items():
        if item_id not in preds or not item_has_error_gold(g):
            continue
        gold_subtypes = {e.get("subtype_v5_target") or e.get("subtype") for e in g["expected_errors"]}
        p = preds[item_id]["decisions"][0]
        if not p["has_error"]:
            continue
        total += 1
        probs = p["choice_probs"] or {}
        ranked = sorted(T.SUBTYPES[lang], key=lambda s: probs.get(s, 0.0), reverse=True)
        if p["subtype"] in gold_subtypes:
            top1 += 1
        if any(s in gold_subtypes for s in ranked[:3]):
            top3 += 1
    subtype_acc = {"top1": (top1 / total) if total else float("nan"),
                    "top3": (top3 / total) if total else float("nan"), "n": total}

    # meaning_changed AUC vs gold severity major/critical
    mc_labels, mc_scores = [], []
    for item_id, g in gold.items():
        if item_id not in preds:
            continue
        sev = item_meaning_severity_gold(g)
        mc_labels.append(sev in ("major", "critical"))
        p = preds[item_id]["decisions"][0]
        mc_scores.append(p["meaning_changed_p"] if p["meaning_changed_p"] is not None else 0.0)
    mc_auc = auc_score(mc_labels, mc_scores)

    cost_lat = cost_latency_stats(records)

    return {"arm": "A1", "lang": lang, "set": set_name, "tau": tau, "severity_fn": severity_fn_name,
            "n_items": len(preds), "bands": dims, "error_detection": detect,
            "subtype_accuracy": subtype_acc, "meaning_changed_auc": mc_auc,
            "cost_latency": cost_lat}


def score_a2(lang: str, set_name: str, tau: float, severity_fn_name: str) -> dict:
    gold = load_reference_set(lang, set_name)
    records = load_responses("A2", lang, set_name)
    severity_fn = SEVERITY_FNS[severity_fn_name]
    preds = predict_a2(records, gold, lang, tau, severity_fn)

    dims = score_a1_or_nr_dims(preds, gold, ("accuracy", "fidelity", "understandability"))

    # sentence-pair-level detection AUC/PR (flatten across items)
    labels, scores = [], []
    tp = fp = fn = tn = 0
    top1 = top3 = subtotal = 0
    mc_labels, mc_scores = [], []
    for item_id, g in gold.items():
        if item_id not in preds:
            continue
        gt_has, gt_subtype, _res = sentence_pair_gold_labels(g)
        decisions = preds[item_id]["decisions"]
        for idx, gt in enumerate(gt_has):
            if idx >= len(decisions) or decisions[idx] is None:
                continue
            d = decisions[idx]
            p_flag = d["has_error"]
            p_score = d["has_error_p"] if d["has_error_p"] is not None else 0.0
            labels.append(gt)
            scores.append(p_score)
            if gt and p_flag:
                tp += 1
            elif not gt and p_flag:
                fp += 1
            elif gt and not p_flag:
                fn += 1
            else:
                tn += 1
            if gt and p_flag:
                subtotal += 1
                probs = d["choice_probs"] or {}
                ranked = sorted(T.SUBTYPES[lang], key=lambda s: probs.get(s, 0.0), reverse=True)
                if d["subtype"] == gt_subtype[idx]:
                    top1 += 1
                if gt_subtype[idx] in ranked[:3]:
                    top3 += 1
            if gt:
                # meaning-changed AUC needs a per-sentence gold severity; use the
                # matched expected_errors' severity_v2 for that pair.
                pass

        # item-level meaning_changed AUC proxy: max has_error-conditioned meaning_changed_p
        # across sentence pairs vs item gold severity major/critical (mirrors A1's framing
        # at item granularity so A1 vs A2 stay comparable on this metric).
        sev = item_meaning_severity_gold(g)
        best_mc = 0.0
        for d in decisions:
            if d and d.get("meaning_changed_p") is not None:
                best_mc = max(best_mc, d["meaning_changed_p"])
        mc_labels.append(sev in ("major", "critical"))
        mc_scores.append(best_mc)

    detect = {"auc": auc_score(labels, scores), **prf1(tp, fp, fn), "tn": tn}
    subtype_acc = {"top1": (top1 / subtotal) if subtotal else float("nan"),
                    "top3": (top3 / subtotal) if subtotal else float("nan"), "n": subtotal}
    mc_auc = auc_score(mc_labels, mc_scores)
    cost_lat = cost_latency_stats(records)

    return {"arm": "A2", "lang": lang, "set": set_name, "tau": tau, "severity_fn": severity_fn_name,
            "n_items": len(preds), "n_sentence_pairs_scored": len(labels), "bands": dims,
            "error_detection": detect, "subtype_accuracy": subtype_acc,
            "meaning_changed_auc": mc_auc, "cost_latency": cost_lat}


def score_nr(lang: str, set_name: str) -> dict:
    gold = load_reference_set(lang, set_name)
    records = load_responses("NR", lang, set_name)
    preds = predict_nr(records, gold, lang)

    out = {}
    for dim, band_key in (("naturalness", "naturalness_band"), ("range", "range_band")):
        yt, yp = [], []
        for item_id, g in gold.items():
            if item_id not in preds or preds[item_id][band_key] is None:
                continue
            yt.append(g["expected_bands"][dim])
            yp.append(preds[item_id][band_key])
        qwk = quadratic_weighted_kappa(yt, yp) if yt else float("nan")
        lo, hi = bootstrap_qwk_ci(yt, yp) if yt else (float("nan"), float("nan"))
        exact = sum(1 for a, b in zip(yt, yp) if a == b) / len(yt) if yt else float("nan")
        out[dim] = {"n": len(yt), "qwk": qwk, "qwk_ci95": [lo, hi], "exact": exact}

    cost_lat = cost_latency_stats(records)
    return {"arm": "NR", "lang": lang, "set": set_name, "n_items": len(preds),
            "bands": out, "cost_latency": cost_lat}


def cost_latency_stats(records: list[dict]) -> dict:
    called = [r for r in records if not r.get("skipped")]
    costs = [float(r.get("usage", {}).get("cost", 0) or 0) for r in called]
    lats = [r.get("latency_s", 0) for r in called if r.get("ok")]
    return {
        "n_calls": len(called),
        "n_skipped": len(records) - len(called),
        "total_cost_usd": sum(costs),
        "mean_cost_per_call": statistics.mean(costs) if costs else float("nan"),
        "mean_latency_s": statistics.mean(lats) if lats else float("nan"),
        "p95_latency_s": (sorted(lats)[max(0, int(round(0.95 * (len(lats) - 1))))] if lats else float("nan")),
    }


def write_markdown(result: dict, path: str) -> None:
    lines = [f"# {result['arm']} / {result['lang']} / {result['set']}", ""]
    if "bands" in result:
        lines.append("| dim | n | QWK | 95% CI | exact |")
        lines.append("|---|---|---|---|---|")
        for dim, m in result["bands"].items():
            ci = m.get("qwk_ci95", [float("nan"), float("nan")])
            lines.append(f"| {dim} | {m['n']} | {m['qwk']:.3f} | [{ci[0]:.3f}, {ci[1]:.3f}] | {m['exact']:.1%} |")
        lines.append("")
    if "error_detection" in result:
        d = result["error_detection"]
        lines.append(f"Error detection: AUC={d['auc']:.3f} P={d['precision']:.2f} R={d['recall']:.2f} "
                      f"F1={d['f1']:.2f} (tp={d['tp']} fp={d['fp']} fn={d['fn']} tn={d['tn']})")
        lines.append("")
    if "subtype_accuracy" in result:
        s = result["subtype_accuracy"]
        lines.append(f"Subtype accuracy (n={s['n']}): top1={s['top1']:.1%} top3={s['top3']:.1%}")
        lines.append("")
    if "meaning_changed_auc" in result:
        lines.append(f"meaning_changed AUC vs gold severity>=major: {result['meaning_changed_auc']:.3f}")
        lines.append("")
    cl = result.get("cost_latency", {})
    lines.append(f"Cost: ${cl.get('total_cost_usd', 0):.6f} total, "
                 f"${cl.get('mean_cost_per_call', float('nan')):.6f}/call, "
                 f"n_calls={cl.get('n_calls', 0)}, n_skipped={cl.get('n_skipped', 0)}")
    lines.append(f"Latency: mean={cl.get('mean_latency_s', float('nan')):.2f}s "
                 f"p95={cl.get('p95_latency_s', float('nan')):.2f}s")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", required=True, choices=("A1", "A2", "NR"))
    ap.add_argument("--lang", required=True, choices=("zh", "ja", "en"))
    ap.add_argument("--set", required=True, choices=("gold", "silver"))
    ap.add_argument("--tau", type=float, default=0.5)
    ap.add_argument("--severity-fn", default="major_minor", choices=list(SEVERITY_FNS))
    args = ap.parse_args()

    if args.arm == "A1":
        result = score_a1(args.lang, args.set, args.tau, args.severity_fn)
    elif args.arm == "A2":
        result = score_a2(args.lang, args.set, args.tau, args.severity_fn)
    else:
        result = score_nr(args.lang, args.set)

    out_json = os.path.join(RESULTS_DIR, f"{args.arm}_{args.lang}_{args.set}.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    write_markdown(result, os.path.join(RESULTS_DIR, f"{args.arm}_{args.lang}_{args.set}.md"))
    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
