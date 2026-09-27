# -*- coding: utf-8 -*-
"""Loss decomposition over ALREADY-CACHED A1/A2 responses. Makes NO new jev
API calls (reads responses/A1_*.jsonl / A2_*.jsonl only) and touches no DB.

For each unit (A1: one item; A2: one aligned sentence pair) we have three
independent jev signals (has_error, subtype, severity-from-meaning_changed)
and three matching gold signals (has_error, representative subtype, severity).
Swapping jev<->gold per signal and re-deriving accuracy/fidelity/
understandability via services.dual_translation.scoring (same OFFLINE
config as score.py) isolates how much QWK loss each signal contributes.

ALL numbers in this file that involve gold-oracle signals are DIAGNOSTIC --
they exist to explain where jev's error comes from, never to pick a
deployment threshold or otherwise tune behavior on the gold set.
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import score as S  # noqa: E402 (loads dotenv + services.* itself, before any other import here)
import reqbuild as REQ  # noqa: E402
import sentences as SENT  # noqa: E402
import taxonomy_data as T  # noqa: E402

DIMS = ("accuracy", "fidelity", "understandability")
SEV_ORDER = {"minor": 0, "major": 1, "critical": 2}


def _representative(errors: list[dict]) -> tuple[str | None, str | None]:
    """Pick one (subtype, severity) to represent possibly-multiple gold
    errors assigned to one unit: the highest-severity one, first on ties.
    This mirrors the structural limit of A1/A2's own decomposed design
    (one has_error/subtype/severity triple per unit), so oracle and jev are
    compared on the same footing."""
    usable = [e for e in errors if e.get("severity_v2")]
    if not usable:
        return None, None
    best = max(usable, key=lambda e: SEV_ORDER.get(e["severity_v2"], -1))
    return best.get("subtype_v5_target") or best.get("subtype"), best["severity_v2"]


def jev_subtype_always(answers: dict, lang: str) -> str | None:
    """argmax subtype choice, independent of has_error (unlike score.decide_error,
    which only computes subtype when has_error fires)."""
    _, _, probs = REQ.decode_choice(answers, "subtype")
    if not probs:
        return None
    best, best_p = None, -1.0
    for opt in T.SUBTYPES[lang]:
        p = probs.get(opt, 0.0) or 0.0
        if p > best_p:
            best, best_p = opt, p
    return best


def jev_severity_always(answers: dict, severity_fn) -> str:
    mc_p = REQ.decode_noul(answers, "meaning_changed")
    return severity_fn(mc_p)


def jev_has_error(answers: dict, tau: float) -> bool:
    p = REQ.decode_noul(answers, "has_error")
    return (p if p is not None else 0.0) >= tau


# ---------------------------------------------------------------------------
# A1: one unit = one item
# ---------------------------------------------------------------------------

def a1_units(lang: str) -> list[dict]:
    gold = S.load_gold(lang)
    records = {r["item_id"]: r for r in S.load_responses("A1", lang, "gold") if r.get("ok")}
    units = []
    for item_id, item in gold.items():
        rec = records.get(item_id)
        if rec is None:
            continue
        gold_has = S.item_has_error_gold(item)
        gold_subtype, gold_sev = _representative(item.get("expected_errors", []))
        units.append({
            "item_id": item_id, "kind": item["kind"], "expected_bands": item["expected_bands"],
            "answers": rec["answers"],
            "gold_has": gold_has, "gold_subtype": gold_subtype, "gold_sev": gold_sev,
        })
    return units


# ---------------------------------------------------------------------------
# A2: one unit = one sentence pair
# ---------------------------------------------------------------------------

def a2_units(lang: str) -> dict[str, list[dict]]:
    """item_id -> ordered list of unit dicts (one per aligned sentence pair).
    Every gold item gets an entry (possibly []) -- an all-byte-identical
    item made no calls but still must yield a prediction (bug fix)."""
    gold = S.load_gold(lang)
    by_item: dict[str, list[dict]] = {iid: [] for iid in gold}
    for r in S.load_responses("A2", lang, "gold"):
        if r.get("skipped") or not r.get("ok"):
            continue
        by_item.setdefault(r["item_id"], []).append(r)
    for recs in by_item.values():
        recs.sort(key=lambda r: r["pair_idx"])

    out: dict[str, list[dict]] = {}
    for item_id, recs in by_item.items():
        item = gold[item_id]
        res = SENT.build_sentence_pairs(item["reference"], item["reproduction"])
        err_pair_idx = SENT.map_errors_to_pairs(item["expected_errors"], res.pairs)
        errors_by_pair: dict[int, list[dict]] = {}
        for err, idx in zip(item["expected_errors"], err_pair_idx):
            if idx is not None:
                errors_by_pair.setdefault(idx, []).append(err)

        # byte-identical pairs were never called -- they are gold-clean by
        # construction (no expected_error can map there) and contribute no
        # unit; skip idx not present in `recs` (they were skipped, not just missing).
        called_idx = {r["pair_idx"] for r in recs}
        units = []
        for rec in recs:
            idx = rec["pair_idx"]
            gold_subtype, gold_sev = _representative(errors_by_pair.get(idx, []))
            units.append({
                "item_id": item_id, "pair_idx": idx, "answers": rec["answers"],
                "gold_has": idx in errors_by_pair, "gold_subtype": gold_subtype, "gold_sev": gold_sev,
            })
        out[item_id] = units
    return out


def a2_item_meta(lang: str) -> dict[str, dict]:
    gold = S.load_gold(lang)
    return {iid: {"kind": it["kind"], "expected_bands": it["expected_bands"]} for iid, it in gold.items()}


# ---------------------------------------------------------------------------
# Generic combo scorer
# ---------------------------------------------------------------------------

def combo_error(unit: dict, lang: str, detection: str, subtype_src: str, severity_src: str,
                 tau: float, severity_fn) -> dict | None:
    """One unit -> an error dict (or None), per the requested source combo."""
    if detection == "oracle":
        has = unit["gold_has"]
    else:
        has = jev_has_error(unit["answers"], tau)
    if not has:
        return None

    if subtype_src == "oracle":
        subtype = unit["gold_subtype"]
    else:
        subtype = jev_subtype_always(unit["answers"], lang)
    if subtype is None or subtype == "no_error":
        return None

    if severity_src == "oracle":
        severity = unit["gold_sev"] or "minor"
    else:
        severity = jev_severity_always(unit["answers"], severity_fn)

    return {"subtype": subtype, "severity": severity}


def score_a1_combo(lang: str, units: list[dict], detection: str, subtype_src: str, severity_src: str,
                    tau: float = 0.5, severity_fn=S.severity_major_minor) -> dict:
    yt = {d: [] for d in DIMS}
    yp = {d: [] for d in DIMS}
    for u in units:
        err = combo_error(u, lang, detection, subtype_src, severity_src, tau, severity_fn)
        errors = [err] if err else []
        pred_bands = S.compute_dimension_bands(errors, S.SUBTYPE_META, S.RUBRIC_CFG)
        for d in DIMS:
            yt[d].append(u["expected_bands"][d])
            yp[d].append(pred_bands[d])
    return {d: S.quadratic_weighted_kappa(yt[d], yp[d]) for d in DIMS}


def score_a2_combo(lang: str, by_item: dict[str, list[dict]], item_meta: dict[str, dict],
                    detection: str, subtype_src: str, severity_src: str,
                    tau: float = 0.5, severity_fn=S.severity_major_minor,
                    cap_max_confidence: bool = False) -> dict:
    yt = {d: [] for d in DIMS}
    yp = {d: [] for d in DIMS}
    for item_id, units in by_item.items():
        errs = []
        confs = []
        for u in units:
            err = combo_error(u, lang, detection, subtype_src, severity_src, tau, severity_fn)
            if err is not None:
                he_p = REQ.decode_noul(u["answers"], "has_error") or 0.0
                errs.append(err)
                confs.append(he_p)
        if cap_max_confidence and len(errs) > 1:
            best_i = max(range(len(confs)), key=lambda i: confs[i])
            errs = [errs[best_i]]
        pred_bands = S.compute_dimension_bands(errs, S.SUBTYPE_META, S.RUBRIC_CFG)
        meta = item_meta[item_id]
        for d in DIMS:
            yt[d].append(meta["expected_bands"][d])
            yp[d].append(pred_bands[d])
    return {d: S.quadratic_weighted_kappa(yt[d], yp[d]) for d in DIMS}


# ---------------------------------------------------------------------------
# FP-on-clean / confusion matrix / subtype-dimension routing
# ---------------------------------------------------------------------------

def clean_false_positives_a1(units: list[dict], tau: float = 0.5) -> dict:
    clean = [u for u in units if u["kind"] == "clean"]
    fp = sum(1 for u in clean if jev_has_error(u["answers"], tau))
    return {"n_clean_items": len(clean), "false_positive_items": fp}


def clean_false_positives_a2(by_item: dict, item_meta: dict, tau: float = 0.5) -> dict:
    n_clean_pairs = fp = 0
    for item_id, units in by_item.items():
        if item_meta[item_id]["kind"] != "clean":
            continue
        for u in units:
            n_clean_pairs += 1
            if jev_has_error(u["answers"], tau):
                fp += 1
    return {"n_clean_sentence_pairs": n_clean_pairs, "false_positive_pairs": fp}


def accuracy_confusion(lang: str, units_or_by_item, item_meta: dict | None, arm: str, tau: float = 0.5) -> list[list[int]]:
    """4x4 confusion of derived accuracy band (baseline: all-jev, tau=0.5) vs gold accuracy band."""
    mat = [[0] * 4 for _ in range(4)]  # mat[gold-1][pred-1]
    if arm == "A1":
        for u in units_or_by_item:
            err = combo_error(u, lang, "jev", "jev", "jev", tau, S.severity_major_minor)
            pred = S.compute_dimension_bands([err] if err else [], S.SUBTYPE_META, S.RUBRIC_CFG)["accuracy"]
            gold = u["expected_bands"]["accuracy"]
            mat[gold - 1][pred - 1] += 1
    else:
        for item_id, units in units_or_by_item.items():
            errs = []
            for u in units:
                err = combo_error(u, lang, "jev", "jev", "jev", tau, S.severity_major_minor)
                if err:
                    errs.append(err)
            pred = S.compute_dimension_bands(errs, S.SUBTYPE_META, S.RUBRIC_CFG)["accuracy"]
            gold = item_meta[item_id]["expected_bands"]["accuracy"]
            mat[gold - 1][pred - 1] += 1
    return mat


def subtype_dimension_routing(lang: str, units_flat: list[dict], tau: float = 0.5) -> dict:
    """Among units where BOTH gold and jev flag an error (tau=0.5 baseline),
    cross-tab gold_subtype's dimension vs jev_subtype's dimension."""
    dims = ("accuracy", "fidelity", "naturalness")
    mat = {g: {p: 0 for p in dims} for g in dims}
    n_considered = 0
    for u in units_flat:
        if not (u["gold_has"] and jev_has_error(u["answers"], tau)):
            continue
        gold_dim = T.SUBTYPE_DIMENSION.get(u["gold_subtype"])
        jev_sub = jev_subtype_always(u["answers"], lang)
        jev_dim = T.SUBTYPE_DIMENSION.get(jev_sub)
        if gold_dim in dims and jev_dim in dims:
            mat[gold_dim][jev_dim] += 1
            n_considered += 1
    return {"n": n_considered, "matrix": mat}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run_lang(lang: str) -> dict:
    out: dict = {"lang": lang}

    a1u = a1_units(lang)
    a2_by_item = a2_units(lang)
    a2_meta = a2_item_meta(lang)
    a2_flat = [u for units in a2_by_item.values() for u in units]

    combos = {
        "baseline_all_jev": ("jev", "jev", "jev"),
        "a_oracle_detection": ("oracle", "jev", "jev"),
        "b_oracle_subtype": ("jev", "oracle", "jev"),
        "c_oracle_severity": ("jev", "jev", "oracle"),
        "all_oracle_ref": ("oracle", "oracle", "oracle"),
    }

    out["A1"] = {}
    for name, (det, sub, sev) in combos.items():
        out["A1"][name] = score_a1_combo(lang, a1u, det, sub, sev)
    out["A1"]["d_tau_sweep_all_oracle_except_detection_DIAGNOSTIC"] = {
        str(tau): score_a1_combo(lang, a1u, "jev", "oracle", "oracle", tau=tau)
        for tau in (0.5, 0.6, 0.7, 0.8, 0.9)
    }
    out["A1"]["clean_false_positives"] = clean_false_positives_a1(a1u)
    out["A1"]["accuracy_confusion_gold_rows_pred_cols"] = accuracy_confusion(lang, a1u, None, "A1")

    out["A2"] = {}
    for name, (det, sub, sev) in combos.items():
        out["A2"][name] = score_a2_combo(lang, a2_by_item, a2_meta, det, sub, sev)
    out["A2"]["d_tau_sweep_all_oracle_except_detection_DIAGNOSTIC"] = {
        str(tau): score_a2_combo(lang, a2_by_item, a2_meta, "jev", "oracle", "oracle", tau=tau)
        for tau in (0.5, 0.6, 0.7, 0.8, 0.9)
    }
    out["A2"]["clean_false_positives"] = clean_false_positives_a2(a2_by_item, a2_meta)
    out["A2"]["accuracy_confusion_gold_rows_pred_cols"] = accuracy_confusion(lang, a2_by_item, a2_meta, "A2")
    out["A2"]["capped_max_confidence_error_per_item"] = score_a2_combo(
        lang, a2_by_item, a2_meta, "jev", "jev", "jev", cap_max_confidence=True
    )

    out["subtype_dimension_routing"] = {
        "A1": subtype_dimension_routing(lang, a1u),
        "A2": subtype_dimension_routing(lang, a2_flat),
    }
    return out


def main():
    results = {lang: run_lang(lang) for lang in ("zh", "ja")}
    out_path = os.path.join(HERE, "results", "decomposition.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(json.dumps(results, indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
