# -*- coding: utf-8 -*-
"""DT ratio-scoring offline experiment (2026-09-27). Reproduces every number in
results/*.json. No API calls, no DB writes -- pure re-derivation over the
jev_dt_2026-09-26 cached A3 responses + tests/fixtures/dt_gold + jev silver sets.

Run: python run.py   (from this directory)
"""
from __future__ import annotations

import itertools
import json
import os
import statistics

import lib
from lib import (
    ALL_DIMS, PENALTY_DIMS, LANGS, SETS, F0_CONFIG, WEIGHT_VARIANTS,
    f0_band, f1_band, f2_band, f3_band, f4_band, f4_length,
    bootstrap_qwk_ci, quadratic_weighted_kappa,
)

RESULTS_DIR = lib.RESULTS_DIR


def dump(name, obj):
    path = os.path.join(RESULTS_DIR, name)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False, default=str)
    return path


# ---------------------------------------------------------------------------
# 0. Load everything
# ---------------------------------------------------------------------------

print("Loading records...")
ALL = lib.load_all_records()  # {(lang,set): [records]}

n_sentences_dist = {}
for (lang, set_name), recs in ALL.items():
    ns = [r["n_sentences"] for r in recs]
    n_sentences_dist.setdefault(lang, {})[set_name] = {
        "n_items": len(ns),
        "min": min(ns), "max": max(ns),
        "mean": round(statistics.mean(ns), 2),
        "median": statistics.median(ns),
        "histogram": {str(k): ns.count(k) for k in sorted(set(ns))},
    }
dump("n_sentences_distribution.json", n_sentences_dist)


# ---------------------------------------------------------------------------
# 1. Threshold selection for F1 (distribution matching against F0 on ORACLE
#    errors, gold+silver pooled across all 3 languages -- never item-matching,
#    never using jev at all here).
# ---------------------------------------------------------------------------

ORACLE_POOL = [r for recs in ALL.values() for r in recs]  # all langs, gold+silver


def band_histogram(bands):
    h = {1: 0, 2: 0, 3: 0, 4: 0}
    for b in bands:
        h[b] += 1
    return h


def hist_distance(h1, h2):
    return sum(abs(h1[k] - h2[k]) for k in (1, 2, 3, 4))


def f0_oracle_bands(dim):
    return [f0_band(r["oracle_errors"], dim) for r in ORACLE_POOL]


T4_GRID = [0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6]
T3_GRID = [0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
T2_GRID = [0.7, 0.8, 0.9, 1.0, 1.2, 1.5, 1.8, 2.0, 2.5, 3.0]

threshold_search = {}
CHOSEN_THRESHOLDS = {}  # (weight_variant, m) -> {dim: (t4,t3,t2)}

for wv_name, weights_cfg in WEIGHT_VARIANTS.items():
    for m in (1, 4):
        key = f"{wv_name}_m{m}"
        CHOSEN_THRESHOLDS[key] = {}
        threshold_search[key] = {}
        for dim in ALL_DIMS:
            target_hist = band_histogram(f0_oracle_bands(dim))
            best = None
            candidates = []
            for t4, t3, t2 in itertools.product(T4_GRID, T3_GRID, T2_GRID):
                if not (t4 < t3 < t2):
                    continue
                bands = [
                    f1_band(r["oracle_errors"], dim, r["n_sentences"], weights_cfg,
                            {dim: (t4, t3, t2)}, m=m)
                    for r in ORACLE_POOL
                ]
                dist = hist_distance(band_histogram(bands), target_hist)
                candidates.append({"t4": t4, "t3": t3, "t2": t2, "distance": dist})
                if best is None or dist < best["distance"]:
                    best = {"t4": t4, "t3": t3, "t2": t2, "distance": dist}
            candidates.sort(key=lambda c: c["distance"])
            CHOSEN_THRESHOLDS[key][dim] = (best["t4"], best["t3"], best["t2"])
            threshold_search[key][dim] = {
                "target_f0_histogram": target_hist,
                "chosen": best,
                "top5": candidates[:5],
                "n_candidates": len(candidates),
            }

dump("threshold_search.json", threshold_search)
dump("chosen_thresholds.json", CHOSEN_THRESHOLDS)


# ---------------------------------------------------------------------------
# 2. Formula runners -- one function per formula name that takes a record and
#    a dim and returns a band, given the fitted params for a (weight,m) combo.
# ---------------------------------------------------------------------------

def make_formula_fns(wv_name, weights_cfg, m):
    key = f"{wv_name}_m{m}"
    thresholds = CHOSEN_THRESHOLDS[key]

    def fF0(errors, dim, r):
        return f0_band(errors, dim)

    def fF1(errors, dim, r):
        return f1_band(errors, dim, r["n_sentences"], weights_cfg, thresholds, m=m)

    def fF2(errors, dim, r):
        return f2_band(errors, dim, r["n_sentences"], weights_cfg, thresholds, m=m)

    def fF3(errors, dim, r):
        return f3_band(errors, dim, r["n_sentences"])

    def fF4(errors, dim, r):
        length = f4_length(r["lang"], r["repro_chars"], r["repro_words"])
        return f4_band(errors, dim, length, weights_cfg, thresholds, m=100)

    return {"F0": fF0, "F1": fF1, "F2": fF2, "F3": fF3, "F4": fF4}


# Primary reporting configuration: WEIGHTS_A ("1/5/25", matches F0's own
# weights so the comparison isolates rate-vs-absolute, not weight choice),
# m=1. WEIGHTS_B / m=4 are computed too and reported as a sensitivity check.
PRIMARY = ("W_1_5_25", 1)


# ---------------------------------------------------------------------------
# 3. M1 -- robustness: QWK(F(jev), F(oracle)) per dim, per language, gold vs
#    silver, with bootstrap 95% CI. Computed for every (weight,m) combo; the
#    primary combo is reported in the top-level summary.
# ---------------------------------------------------------------------------

m1_results = {}
for wv_name, weights_cfg in WEIGHT_VARIANTS.items():
    for m in (1, 4):
        combo_key = f"{wv_name}_m{m}"
        fns = make_formula_fns(wv_name, weights_cfg, m)
        m1_results[combo_key] = {}
        for lang in LANGS:
            m1_results[combo_key][lang] = {}
            for set_name in SETS:
                recs = ALL[(lang, set_name)]
                m1_results[combo_key][lang][set_name] = {}
                for dim in ALL_DIMS:
                    m1_results[combo_key][lang][set_name][dim] = {}
                    for fname, fn in fns.items():
                        yt = [fn(r["oracle_errors"], dim, r) for r in recs]
                        yp = [fn(r["jev_errors"], dim, r) for r in recs]
                        qwk = quadratic_weighted_kappa(yt, yp)
                        lo, hi = bootstrap_qwk_ci(yt, yp)
                        m1_results[combo_key][lang][set_name][dim][fname] = {
                            "qwk": qwk, "ci95": [lo, hi], "n": len(yt),
                        }

dump("m1_robustness.json", m1_results)


# ---------------------------------------------------------------------------
# 4. M2 -- length fairness. Synthetic passages tiling clean + erroneous
#    sentences so the same error RATE (fixed fraction of sentences erroneous,
#    fixed severity) appears at n_sentences in {4, 8, 12, 20}. Reports the
#    resulting accuracy-dimension band under each formula. Ideal: stable
#    across lengths.
# ---------------------------------------------------------------------------

def synth_errors(n_sentences, error_rate, severity, dimension):
    n_err = max(1, round(n_sentences * error_rate))
    n_err = min(n_err, n_sentences)
    # spread the erroneous sentences evenly through the passage
    idxs = sorted({round(i * n_sentences / n_err) for i in range(n_err)})
    while len(idxs) < n_err:
        for i in range(n_sentences):
            if i not in idxs:
                idxs.append(i)
                break
    return [{"severity": severity, "dimension": dimension, "sentence_idx": i} for i in idxs[:n_err]]


LENGTHS = (4, 8, 12, 20)
RATE = 0.25  # 1 in 4 sentences erroneous, held fixed across lengths

m2_results = {}
for wv_name, weights_cfg in WEIGHT_VARIANTS.items():
    for m in (1, 4):
        combo_key = f"{wv_name}_m{m}"
        fns = make_formula_fns(wv_name, weights_cfg, m)
        m2_results[combo_key] = {}
        for severity in ("minor", "major", "critical"):
            m2_results[combo_key][severity] = {}
            for fname, fn in fns.items():
                bands = []
                for n in LENGTHS:
                    errors = synth_errors(n, RATE, severity, "accuracy")
                    fake_record = {"lang": "zh", "repro_chars": n * 25, "repro_words": n * 8}
                    band = fn(errors, "accuracy", fake_record | {"n_sentences": n})
                    bands.append({"n_sentences": n, "n_errors": len(errors), "band": band})
                m2_results[combo_key][severity][fname] = bands

dump("m2_length_fairness.json", m2_results)


# ---------------------------------------------------------------------------
# 5. M3 -- severity sanity.
#    (a) ONE critical error in an otherwise-clean LONG passage (20 sentences)
#        -- does the band still drop appropriately?
#    (b) MANY minor errors in a long passage (8 of 20 sentences minor) --
#        does the band stay reasonable (not bottoming out to band 1)?
# ---------------------------------------------------------------------------

m3_results = {}
for wv_name, weights_cfg in WEIGHT_VARIANTS.items():
    for m in (1, 4):
        combo_key = f"{wv_name}_m{m}"
        fns = make_formula_fns(wv_name, weights_cfg, m)
        m3_results[combo_key] = {}

        one_critical = [{"severity": "critical", "dimension": "accuracy", "sentence_idx": 0}]
        record_long = {"lang": "zh", "n_sentences": 20, "repro_chars": 500, "repro_words": 160}
        many_minor = [{"severity": "minor", "dimension": "accuracy", "sentence_idx": i} for i in range(8)]

        m3_results[combo_key]["one_critical_in_20"] = {
            fname: fn(one_critical, "accuracy", record_long) for fname, fn in fns.items()
        }
        m3_results[combo_key]["8_of_20_minor"] = {
            fname: fn(many_minor, "accuracy", record_long) for fname, fn in fns.items()
        }
        # control: 1 minor in 20 (should be the mildest case, all formulas -> band 4 ideally)
        one_minor = [{"severity": "minor", "dimension": "accuracy", "sentence_idx": 0}]
        m3_results[combo_key]["1_of_20_minor"] = {
            fname: fn(one_minor, "accuracy", record_long) for fname, fn in fns.items()
        }

dump("m3_severity_sanity.json", m3_results)


# ---------------------------------------------------------------------------
# 6. M4 -- band distribution per formula on ORACLE errors (real gold+silver
#    items, pooled across languages), flagging degenerate formulas.
# ---------------------------------------------------------------------------

m4_results = {}
for wv_name, weights_cfg in WEIGHT_VARIANTS.items():
    for m in (1, 4):
        combo_key = f"{wv_name}_m{m}"
        fns = make_formula_fns(wv_name, weights_cfg, m)
        m4_results[combo_key] = {}
        for dim in ALL_DIMS:
            m4_results[combo_key][dim] = {}
            for fname, fn in fns.items():
                bands = [fn(r["oracle_errors"], dim, r) for r in ORACLE_POOL]
                hist = band_histogram(bands)
                n = len(bands)
                m4_results[combo_key][dim][fname] = {
                    "histogram": hist,
                    "pct": {str(k): round(100 * v / n, 1) for k, v in hist.items()},
                    "band4_share": round(hist[4] / n, 3),
                }

dump("m4_band_distribution.json", m4_results)


# ---------------------------------------------------------------------------
# Console summary (short -- full detail is in results/*.json)
# ---------------------------------------------------------------------------

print("\n=== M1 robustness (primary combo %s), mean QWK across langs, gold ===" % (PRIMARY,))
pk = f"{PRIMARY[0]}_m{PRIMARY[1]}"
for dim in ALL_DIMS:
    for fname in ("F0", "F1", "F2", "F3", "F4"):
        vals = [m1_results[pk][lang]["gold"][dim][fname]["qwk"] for lang in LANGS]
        vals = [v for v in vals if v == v]
        mean_v = round(statistics.mean(vals), 3) if vals else float("nan")
        print(f"  {dim:16s} {fname}  mean_qwk={mean_v}")

print("\n=== M4 band-4 share (primary combo), oracle errors, all langs pooled ===")
for dim in ALL_DIMS:
    for fname in ("F0", "F1", "F2", "F3", "F4"):
        print(f"  {dim:16s} {fname}  band4_share={m4_results[pk][dim][fname]['band4_share']}")

print("\nAll results written to", RESULTS_DIR)
