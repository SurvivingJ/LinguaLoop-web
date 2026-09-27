# -*- coding: utf-8 -*-
"""Routing (R): "confidently clean" pre-filter using the frozen A3 config's
own raw signals (has_error_p + the 5 narrow probes), NOT its derived bands.

item is "confidently clean" at threshold tau_r iff, for EVERY sentence pair
in the item: has_error_p < tau_r AND every narrow probe < tau_r. Skipped
(byte-identical) pairs trivially satisfy this (they carry no probes) and
count as clean, per the coordinator's spec.

tau_r is fit on silver: the largest value in a fine grid such that ZERO
routed items have a gold band < 4 on the gate dimensions (all of
accuracy/fidelity/understandability for the "full" gate; accuracy+
understandability only for the variant gate that tolerates a sub-4
fidelity). Then both frozen tau_r values are applied to gold and reported:
% routed, over-grade rate (routed item with any gate-dimension gold band <
4), and >=2-band misses.
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import score as S  # noqa: E402
import score_a3 as SA3  # noqa: E402
import reqbuild as REQ  # noqa: E402

RESULTS_DIR = os.path.join(HERE, "results")
GRID = [0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5]


def item_max_signal(units: list[dict]) -> float:
    best = 0.0
    for u in units:
        he_p = REQ.decode_noul(u["answers"], "has_error") or 0.0
        best = max(best, he_p)
        for name in REQ.R.NARROW_NOUL:
            p = REQ.decode_narrow(u["answers"], name) or 0.0
            best = max(best, p)
    return best


def item_signals(lang: str, set_name: str) -> dict[str, float]:
    by_item = SA3.a3_units(lang, set_name)
    return {iid: item_max_signal(units) for iid, units in by_item.items()}


def gate_ok(bands: dict, dims: tuple[str, ...]) -> bool:
    return all(bands[d] == 4 for d in dims)


def fit_tau_r(lang: str, dims: tuple[str, ...]) -> dict:
    signals = item_signals(lang, "silver")
    meta = SA3.item_meta(lang, "silver")
    best_tau, best_routed = 0.0, 0
    for tau_r in GRID:
        routed = [iid for iid, s in signals.items() if s < tau_r]
        misses = [iid for iid in routed if not gate_ok(meta[iid]["expected_bands"], dims)]
        if not misses and len(routed) >= best_routed:
            best_tau, best_routed = tau_r, len(routed)
    return {"tau_r": best_tau, "n_routed_silver": best_routed, "n_silver": len(signals)}


def eval_tau_r(lang: str, set_name: str, tau_r: float, dims: tuple[str, ...]) -> dict:
    signals = item_signals(lang, set_name)
    meta = SA3.item_meta(lang, set_name)
    routed = [iid for iid, s in signals.items() if s < tau_r]
    n = len(signals)
    n_routed = len(routed)
    over_grade = []
    two_band_miss = []
    for iid in routed:
        bands = meta[iid]["expected_bands"]
        if not gate_ok(bands, dims):
            over_grade.append(iid)
        # >=2-band miss: any gate dim at or below band 2 (i.e. >=2 bands
        # below the perfect-mark ceiling of 4) among a routed item.
        if any(bands[d] <= 2 for d in dims):
            two_band_miss.append(iid)
    return {
        "lang": lang, "set": set_name, "tau_r": tau_r, "gate_dims": dims,
        "n_items": n, "n_routed": n_routed, "pct_routed": n_routed / n if n else float("nan"),
        "over_grade_items": over_grade, "over_grade_rate": (len(over_grade) / n_routed) if n_routed else 0.0,
        "two_band_miss_items": two_band_miss,
    }


def main():
    out = {}
    for lang in ("zh", "ja"):
        out[lang] = {}
        for label, dims in (("full_3dim", ("accuracy", "fidelity", "understandability")),
                             ("acc_und_only", ("accuracy", "understandability"))):
            fit = fit_tau_r(lang, dims)
            gold_eval = eval_tau_r(lang, "gold", fit["tau_r"], dims)
            out[lang][label] = {"fit_on_silver": fit, "gold": gold_eval}

    out_path = os.path.join(RESULTS_DIR, "routing.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False, default=str)
    print(json.dumps(out, indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
