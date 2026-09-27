# -*- coding: utf-8 -*-
"""Scores cached A3 responses (silver fitting + frozen-config gold scoring).

Per sentence-pair unit, A3 gives: has_error_p, subtype argmax+probs,
meaning_changed_p, 5 narrow-probe probabilities, severity_choice probs
(minor/major/critical/no_error), native_wrong_p.

Decision pipeline (one error record per pair, or None):
  1. has_error_main = has_error_p >= tau.
  2. narrow_fired    = any of the 5 narrow probes >= tau_n. If fired, its
     mapped subtype (reqbuild.NARROW_SUBTYPE_MAP) is available as a
     detection path independent of has_error_main (task spec: "any narrow
     hit >= tau_n forces an error").
  3. has_error_final = has_error_main OR narrow_fired.
  4. subtype: the primary `subtype` choice argmax when has_error_main fired;
     otherwise (narrow-only) the highest-firing narrow's mapped subtype.
  5. severity: severity_fn(answers, subtype, tau_c) from severity_variants,
     floored at "major" if narrow_fired (task spec: narrow hit forces
     "severity major" -- implemented as a floor so a variant that already
     says "critical" is not downgraded).

This file has ONE job in two modes:
  --mode fit   : 5-fold CV grid search over (tau, tau_n, tau_c, variant) on
                 --set silver, per language. Reports CV mean+-sd of the
                 3-dim QWK mean, top 3 configs, and freezes the best one
                 (written to results/frozen_config_<lang>.json).
  --mode eval  : scores ONE frozen config (loaded from that json, or passed
                 via --tau/--tau-narrow/--tau-c/--variant) against --set
                 gold or silver, reporting the same metric set score.py's
                 A2 reports (bands+CI, detection AUC, subtype top1/3,
                 severity accuracy).
"""
from __future__ import annotations

import argparse
import itertools
import json
import os
import random
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import score as S  # noqa: E402 (loads dotenv + services.* first)
import reqbuild as REQ  # noqa: E402
import sentences as SENT  # noqa: E402
import taxonomy_data as T  # noqa: E402
import severity_variants as SV  # noqa: E402

RESULTS_DIR = os.path.join(HERE, "results")
SEV_ORDER = {"minor": 0, "major": 1, "critical": 2}
DIMS = ("accuracy", "fidelity", "understandability")

VARIANT_NAMES = ("S1_meaning_changed", "S2_argmax", "S2_threshold", "S3_prior", "S4_native_wrong")


# ---------------------------------------------------------------------------
# Loading A3 units (mirrors decompose.a2_units, arm="A3")
# ---------------------------------------------------------------------------

def load_reference(lang: str, set_name: str) -> dict[str, dict]:
    return S.load_reference_set(lang, set_name)


def a3_units(lang: str, set_name: str) -> dict[str, list[dict]]:
    """One entry per item IN THE REFERENCE SET, always -- an item whose
    sentence pairs are all byte-identical (no calls made, e.g. en_clean_05)
    still gets an entry with an empty unit list, so it still yields a
    prediction (0 errors -> bands 4/4/4) instead of silently vanishing from
    every downstream count (bug found by audit: previously such items were
    dropped, undercounting gold n by however many were fully clean)."""
    reference = load_reference(lang, set_name)
    by_item: dict[str, list[dict]] = {iid: [] for iid in reference}
    for r in S.load_responses("A3", lang, set_name):
        if r.get("skipped") or not r.get("ok"):
            continue
        by_item.setdefault(r["item_id"], []).append(r)
    for recs in by_item.values():
        recs.sort(key=lambda r: r["pair_idx"])

    out: dict[str, list[dict]] = {}
    for item_id, recs in by_item.items():
        item = reference[item_id]
        res = SENT.build_sentence_pairs(item["reference"], item["reproduction"])
        err_pair_idx = SENT.map_errors_to_pairs(item["expected_errors"], res.pairs)
        errors_by_pair: dict[int, list[dict]] = {}
        for err, idx in zip(item["expected_errors"], err_pair_idx):
            if idx is not None:
                errors_by_pair.setdefault(idx, []).append(err)

        units = []
        for rec in recs:
            idx = rec["pair_idx"]
            gsub, gsev = S._representative(errors_by_pair.get(idx, [])) if hasattr(S, "_representative") else (None, None)
            units.append({
                "item_id": item_id, "pair_idx": idx, "answers": rec["answers"],
                "gold_has": idx in errors_by_pair,
                "gold_subtype": gsub, "gold_sev": gsev,
            })
        out[item_id] = units
    return out


def _representative(errors: list[dict]) -> tuple[str | None, str | None]:
    usable = [e for e in errors if e.get("severity_v2")]
    if not usable:
        return None, None
    best = max(usable, key=lambda e: SEV_ORDER.get(e["severity_v2"], -1))
    return best.get("subtype_v5_target") or best.get("subtype"), best["severity_v2"]


# monkeypatch-free: score.py has no _representative, define it locally and use it.
S._representative = _representative  # type: ignore[attr-defined]


def item_meta(lang: str, set_name: str) -> dict[str, dict]:
    ref = load_reference(lang, set_name)
    return {iid: {"kind": it["kind"], "expected_bands": it["expected_bands"]} for iid, it in ref.items()}


# ---------------------------------------------------------------------------
# Decision pipeline
# ---------------------------------------------------------------------------

def _narrow_signal(answers: dict, tau_n: float) -> tuple[bool, str | None]:
    best_name, best_p = None, -1.0
    for name in REQ.R.NARROW_NOUL:
        p = REQ.decode_narrow(answers, name) or 0.0
        if p > best_p:
            best_name, best_p = name, p
    fired = best_p >= tau_n
    subtype = REQ.NARROW_SUBTYPE_MAP.get(best_name) if fired else None
    return fired, subtype


def decide_a3(answers: dict, lang: str, tau: float, tau_n: float, tau_c: float, variant: str) -> dict | None:
    he_p = REQ.decode_noul(answers, "has_error") or 0.0
    has_main = he_p >= tau
    narrow_fired, narrow_subtype = _narrow_signal(answers, tau_n)
    has_final = has_main or narrow_fired
    if not has_final:
        return None

    if has_main:
        subtype = None
        _, _, probs = REQ.decode_choice(answers, "subtype")
        if probs:
            best, best_p = None, -1.0
            for opt in T.SUBTYPES[lang]:
                p = probs.get(opt, 0.0) or 0.0
                if p > best_p:
                    best, best_p = opt, p
            subtype = best
        if subtype is None:
            subtype = narrow_subtype
    else:
        subtype = narrow_subtype
    if subtype is None:
        return None

    fn = SV.VARIANTS[variant]
    if variant == "S3_prior":
        severity = fn(subtype, answers, tau_c=tau_c)
    elif variant == "S4_native_wrong":
        severity = fn(answers, tau_c=tau_c)
    elif variant == "S2_threshold":
        severity = fn(answers)  # uses its own default tau_major/tau_critical
    elif variant == "S1_meaning_changed":
        severity = fn(answers)
    else:  # S2_argmax
        severity = fn(answers)

    if narrow_fired and SEV_ORDER[severity] < SEV_ORDER["major"]:
        severity = "major"

    return {"subtype": subtype, "severity": severity}


def predict_item_bands(units: list[dict], lang: str, tau: float, tau_n: float, tau_c: float, variant: str) -> dict:
    errors = []
    for u in units:
        err = decide_a3(u["answers"], lang, tau, tau_n, tau_c, variant)
        if err:
            errors.append(err)
    return S.compute_dimension_bands(errors, S.SUBTYPE_META, S.RUBRIC_CFG)


# ---------------------------------------------------------------------------
# 5-fold CV grid search (silver only)
# ---------------------------------------------------------------------------

def make_folds(item_ids: list[str], k: int = 5, seed: int = 0) -> list[list[str]]:
    ids = sorted(item_ids)
    rng = random.Random(seed)
    rng.shuffle(ids)
    folds = [[] for _ in range(k)]
    for i, iid in enumerate(ids):
        folds[i % k].append(iid)
    return folds


def score_config_on_items(by_item: dict[str, list[dict]], meta: dict[str, dict], item_ids: list[str],
                           lang: str, tau: float, tau_n: float, tau_c: float, variant: str) -> dict:
    yt = {d: [] for d in DIMS}
    yp = {d: [] for d in DIMS}
    for iid in item_ids:
        if iid not in by_item:
            continue
        pred = predict_item_bands(by_item[iid], lang, tau, tau_n, tau_c, variant)
        for d in DIMS:
            yt[d].append(meta[iid]["expected_bands"][d])
            yp[d].append(pred[d])
    qwks = {d: S.quadratic_weighted_kappa(yt[d], yp[d]) for d in DIMS}
    valid = [v for v in qwks.values() if v == v]  # drop NaN
    mean_qwk = statistics.mean(valid) if valid else float("nan")
    return {"qwk": qwks, "mean_qwk": mean_qwk}


def cv_grid_search(lang: str, taus=(0.5, 0.6, 0.7, 0.8, 0.9), tau_ns=(0.5, 0.7, 0.9),
                    tau_cs=(0.7, 0.85, 0.95), variants=VARIANT_NAMES, k: int = 5) -> dict:
    by_item = a3_units(lang, "silver")
    meta = item_meta(lang, "silver")
    item_ids = list(by_item.keys())
    folds = make_folds(item_ids, k=k)

    results = []
    for tau, tau_n, tau_c, variant in itertools.product(taus, tau_ns, tau_cs, variants):
        # S1/S2 don't use tau_c -- collapse the grid for them (avoid duplicate
        # identical configs inflating the "top 3" list with tau_c-only clones).
        if variant in ("S1_meaning_changed", "S2_argmax", "S2_threshold") and tau_c != tau_cs[0]:
            continue
        fold_scores = []
        for fold in folds:
            r = score_config_on_items(by_item, meta, fold, lang, tau, tau_n, tau_c, variant)
            if r["mean_qwk"] == r["mean_qwk"]:  # not NaN
                fold_scores.append(r["mean_qwk"])
        if not fold_scores:
            continue
        cv_mean = statistics.mean(fold_scores)
        cv_sd = statistics.stdev(fold_scores) if len(fold_scores) > 1 else 0.0
        full = score_config_on_items(by_item, meta, item_ids, lang, tau, tau_n, tau_c, variant)
        results.append({
            "tau": tau, "tau_n": tau_n, "tau_c": tau_c, "variant": variant,
            "cv_mean": cv_mean, "cv_sd": cv_sd, "n_folds": len(fold_scores),
            "full_qwk": full["qwk"], "full_mean_qwk": full["mean_qwk"],
        })

    results.sort(key=lambda r: r["cv_mean"], reverse=True)
    return {"lang": lang, "n_items": len(item_ids), "n_configs_tried": len(results), "top": results[:3],
            "frozen": results[0] if results else None}


# ---------------------------------------------------------------------------
# Frozen-config eval (gold or silver)
# ---------------------------------------------------------------------------

def auc_score(labels, scores):
    pos = [s for l, s in zip(labels, scores) if l]
    neg = [s for l, s in zip(labels, scores) if not l]
    if not pos or not neg:
        return float("nan")
    greater = sum(1 for a in pos for b in neg if a > b)
    ties = sum(1 for a in pos for b in neg if a == b)
    return (greater + 0.5 * ties) / (len(pos) * len(neg))


def eval_frozen(lang: str, set_name: str, cfg: dict) -> dict:
    tau, tau_n, tau_c, variant = cfg["tau"], cfg["tau_n"], cfg["tau_c"], cfg["variant"]
    by_item = a3_units(lang, set_name)
    meta = item_meta(lang, set_name)
    item_ids = list(by_item.keys())

    bands = score_config_on_items(by_item, meta, item_ids, lang, tau, tau_n, tau_c, variant)
    band_ci = {}
    for d in DIMS:
        yt = [meta[iid]["expected_bands"][d] for iid in item_ids if iid in by_item]
        yp = [predict_item_bands(by_item[iid], lang, tau, tau_n, tau_c, variant)[d] for iid in item_ids if iid in by_item]
        band_ci[d] = S.bootstrap_qwk_ci(yt, yp)

    # sentence-pair-level detect AUC + subtype top1/3 + severity accuracy
    labels, scores = [], []
    tp = fp = fn = tn = 0
    top1 = top3 = subtotal = 0
    sev_correct = sev_total = 0
    for iid in item_ids:
        for u in by_item[iid]:
            gt = u["gold_has"]
            err = decide_a3(u["answers"], lang, tau, tau_n, tau_c, variant)
            he_p = REQ.decode_noul(u["answers"], "has_error") or 0.0
            labels.append(gt)
            scores.append(he_p)
            pred_flag = err is not None
            if gt and pred_flag:
                tp += 1
            elif not gt and pred_flag:
                fp += 1
            elif gt and not pred_flag:
                fn += 1
            else:
                tn += 1
            if gt and pred_flag:
                subtotal += 1
                _, _, probs = REQ.decode_choice(u["answers"], "subtype")
                ranked = sorted(T.SUBTYPES[lang], key=lambda s: (probs or {}).get(s, 0.0), reverse=True)
                if err["subtype"] == u["gold_subtype"]:
                    top1 += 1
                if u["gold_subtype"] in ranked[:3]:
                    top3 += 1
                if u["gold_sev"]:
                    sev_total += 1
                    if err["severity"] == u["gold_sev"]:
                        sev_correct += 1

    detect_auc = auc_score(labels, scores)
    n = tp + fp + fn + tn
    precision = tp / (tp + fp) if (tp + fp) else (1.0 if fp == fn == tp == 0 else 0.0)
    recall = tp / (tp + fn) if (tp + fn) else (1.0 if fp == fn == tp == 0 else 0.0)
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0

    return {
        "lang": lang, "set": set_name, "config": cfg, "n_items": len(item_ids),
        "bands": bands["qwk"], "bands_ci95": band_ci, "mean_qwk": bands["mean_qwk"],
        "detection": {"auc": detect_auc, "precision": precision, "recall": recall, "f1": f1,
                      "tp": tp, "fp": fp, "fn": fn, "tn": tn},
        "subtype_accuracy": {"top1": (top1 / subtotal) if subtotal else float("nan"),
                              "top3": (top3 / subtotal) if subtotal else float("nan"), "n": subtotal},
        "severity_accuracy": (sev_correct / sev_total) if sev_total else float("nan"),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", required=True, choices=("fit", "eval"))
    ap.add_argument("--lang", required=True, choices=("zh", "ja", "en"))
    ap.add_argument("--set", default="silver", choices=("gold", "silver"))
    ap.add_argument("--tau", type=float)
    ap.add_argument("--tau-narrow", type=float)
    ap.add_argument("--tau-c", type=float)
    ap.add_argument("--variant", choices=VARIANT_NAMES)
    args = ap.parse_args()

    if args.mode == "fit":
        result = cv_grid_search(args.lang)
        out_path = os.path.join(RESULTS_DIR, f"a3_cv_{args.lang}.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        frozen_path = os.path.join(RESULTS_DIR, f"frozen_config_{args.lang}.json")
        with open(frozen_path, "w", encoding="utf-8") as f:
            json.dump(result["frozen"], f, indent=2, ensure_ascii=False)
        print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    else:
        frozen_path = os.path.join(RESULTS_DIR, f"frozen_config_{args.lang}.json")
        if args.tau is not None and args.variant is not None:
            cfg = {"tau": args.tau, "tau_n": args.tau_narrow, "tau_c": args.tau_c, "variant": args.variant}
        else:
            with open(frozen_path, encoding="utf-8") as f:
                cfg = json.load(f)
        result = eval_frozen(args.lang, args.set, cfg)
        out_path = os.path.join(RESULTS_DIR, f"a3_eval_{args.lang}_{args.set}.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False, default=str)
        print(json.dumps(result, indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
