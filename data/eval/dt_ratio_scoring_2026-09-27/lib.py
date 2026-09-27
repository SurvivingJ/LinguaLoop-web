# -*- coding: utf-8 -*-
"""Shared loading + candidate-formula library for the DT ratio-scoring experiment
(2026-09-27). Offline only: no API calls, no DB writes. Reuses the jev_dt_2026-09-26
harness's cached A3 responses + frozen per-language configs, and the gold/silver
fixtures under tests/fixtures/dt_gold and data/eval/jev_dt_2026-09-26/silver.

CRITICAL: gold/silver `expected_bands` were computed by TODAY's absolute formula
(F0). Any metric that scores a candidate formula F by "agreement with expected_bands"
is circular. This module never does that. Instead every candidate F is applied to
BOTH the oracle (gold/silver-labelled) error list and jev's predicted error list for
the same item, and robustness is measured as QWK(F(jev), F(oracle)) -- see run.py.
"""
from __future__ import annotations

import json
import os
import random
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
JEV_DIR = os.path.join(HERE, "..", "jev_dt_2026-09-26")
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))

sys.path.insert(0, JEV_DIR)
sys.path.insert(0, REPO)

from dotenv import load_dotenv  # noqa: E402
load_dotenv(os.path.join(REPO, ".env"))  # HARD RULE: before any services.* import

import score as S  # noqa: E402  (jev harness: load_reference_set, load_responses)
import score_a3 as SA3  # noqa: E402  (jev harness: a3_units, decide_a3)
import sentences as SENT  # noqa: E402
import taxonomy_data as T  # noqa: E402

from services.dual_translation.eval_metrics import quadratic_weighted_kappa  # noqa: E402

LANGS = ("zh", "ja", "en")
SETS = ("gold", "silver")
PENALTY_DIMS = ("accuracy", "fidelity")
ALL_DIMS = ("accuracy", "fidelity", "understandability")

# The absolute formula this experiment is benchmarked against (tech spec §4 /
# scripts.dt_gold_seed_helper.OFFLINE_SCORING_CONFIG). Duplicated as a literal
# (not imported) so this module never depends on the DB-touching services import
# chain beyond eval_metrics, and so the frozen baseline can't silently drift if
# that module is edited.
F0_CONFIG = {
    "severity_weights": {"minor": 1, "major": 5, "critical": 25},
    "understandability_weights": {"minor": 0, "major": 2, "critical": 25},
    "band_thresholds": {
        "accuracy": (1, 6, 15),
        "fidelity": (1, 6, 15),
        "understandability": (2, 6, 25),
    },
}

RESULTS_DIR = os.path.join(HERE, "results")
os.makedirs(RESULTS_DIR, exist_ok=True)


def _frozen_config(lang: str) -> dict:
    path = os.path.join(JEV_DIR, "results", f"frozen_config_{lang}.json")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Record loading: per item, both the oracle error list and jev's predicted
# error list, each tagged with (severity, dimension, sentence_idx).
# ---------------------------------------------------------------------------

def _dimension_of(subtype: str | None) -> str | None:
    if not subtype:
        return None
    return T.SUBTYPE_DIMENSION.get(subtype)


def load_records(lang: str, set_name: str) -> list[dict]:
    reference = S.load_reference_set(lang, set_name)
    a3_by_item = SA3.a3_units(lang, set_name)
    cfg = _frozen_config(lang)

    records = []
    for iid, item in reference.items():
        res = SENT.build_sentence_pairs(item["reference"], item["reproduction"])
        n_sentences = len(res.pairs)
        err_pair_idx = SENT.map_errors_to_pairs(item["expected_errors"], res.pairs)

        oracle_errors = []
        for e, idx in zip(item["expected_errors"], err_pair_idx):
            sev = e.get("severity_v2")
            if not sev:
                continue
            subtype = e.get("subtype_v5_target") or e.get("subtype")
            oracle_errors.append({
                "severity": sev,
                "dimension": _dimension_of(subtype),
                "sentence_idx": idx,
            })

        jev_errors = []
        for u in a3_by_item.get(iid, []):
            err = SA3.decide_a3(u["answers"], lang, cfg["tau"], cfg["tau_n"], cfg["tau_c"], cfg["variant"])
            if err:
                jev_errors.append({
                    "severity": err["severity"],
                    "dimension": _dimension_of(err["subtype"]),
                    "sentence_idx": u["pair_idx"],
                })

        repro = item["reproduction"]
        records.append({
            "id": iid,
            "lang": lang,
            "set": set_name,
            "kind": item.get("kind", "single"),
            "n_sentences": n_sentences,
            "repro_chars": len(repro),
            "repro_words": len(repro.split()),
            "oracle_errors": oracle_errors,
            "jev_errors": jev_errors,
            "expected_bands": item.get("expected_bands", {}),
        })
    return records


def load_all_records() -> dict:
    """{(lang, set_name): [records]}"""
    out = {}
    for lang in LANGS:
        for set_name in SETS:
            out[(lang, set_name)] = load_records(lang, set_name)
    return out


# ---------------------------------------------------------------------------
# Candidate formulas. Every *_band function takes an error list (already
# dimension/severity/sentence_idx-tagged) and a `dim` in ALL_DIMS, and returns
# an int band in [1, 4]. `understandability` always scores over ALL errors
# regardless of `dimension`; accuracy/fidelity filter to matching errors.
# ---------------------------------------------------------------------------

def _relevant(errors: list[dict], dim: str) -> list[dict]:
    if dim == "understandability":
        return list(errors)
    return [e for e in errors if e.get("dimension") == dim]


def _weights_for(weights_cfg: dict, dim: str) -> dict:
    return weights_cfg["understandability"] if dim == "understandability" else weights_cfg["penalty"]


def penalty_sum(errors: list[dict], dim: str, weights_cfg: dict) -> float:
    relevant = _relevant(errors, dim)
    w = _weights_for(weights_cfg, dim)
    return sum(w.get(e["severity"], 0) for e in relevant)


def band_from_value(v: float, t4: float, t3: float, t2: float) -> int:
    return 4 if v <= t4 else 3 if v <= t3 else 2 if v <= t2 else 1


def severity_cap(errors: list[dict], dim: str) -> int:
    relevant = _relevant(errors, dim)
    sevs = {e["severity"] for e in relevant}
    if "critical" in sevs:
        return 2
    if "major" in sevs:
        return 3
    return 4


# -- F0: today's absolute formula (baseline) --------------------------------

def f0_band(errors: list[dict], dim: str, cfg: dict = F0_CONFIG) -> int:
    w = cfg["understandability_weights"] if dim == "understandability" else cfg["severity_weights"]
    penalty = penalty_sum(errors, dim, {"penalty": cfg["severity_weights"], "understandability": cfg["understandability_weights"]})
    t4, t3, t2 = cfg["band_thresholds"][dim]
    return band_from_value(penalty, t4, t3, t2)


# -- F1: weighted rate = penalty / max(n_sentences, m) -----------------------

def f1_band(errors: list[dict], dim: str, n_sentences: int, weights_cfg: dict,
            thresholds: dict, m: int = 1) -> int:
    penalty = penalty_sum(errors, dim, weights_cfg)
    rate = penalty / max(n_sentences, m)
    t4, t3, t2 = thresholds[dim]
    return band_from_value(rate, t4, t3, t2)


# -- F2: F1 + worst-issue severity cap ---------------------------------------

def f2_band(errors: list[dict], dim: str, n_sentences: int, weights_cfg: dict,
            thresholds: dict, m: int = 1) -> int:
    rate_band = f1_band(errors, dim, n_sentences, weights_cfg, thresholds, m)
    return min(rate_band, severity_cap(errors, dim))


# -- F3: error-free-sentence share + caps ------------------------------------

def f3_band(errors: list[dict], dim: str, n_sentences: int,
            share_thresholds=(0.90, 0.75, 0.50)) -> int:
    relevant = _relevant(errors, dim)
    err_sentences = {e["sentence_idx"] for e in relevant if e.get("sentence_idx") is not None}
    n = max(n_sentences, 1)
    share = (n - len(err_sentences)) / n
    t90, t75, t50 = share_thresholds
    band = 4 if share >= t90 else 3 if share >= t75 else 2 if share >= t50 else 1
    return min(band, severity_cap(errors, dim))


# -- F4: per-100-"characters" rate (zh/ja chars, en words*5) + caps ----------

def f4_length(lang: str, repro_chars: int, repro_words: int) -> int:
    return repro_chars if lang in ("zh", "ja") else repro_words * 5


def f4_band(errors: list[dict], dim: str, length: int, weights_cfg: dict,
            thresholds: dict, m: int = 100) -> int:
    penalty = penalty_sum(errors, dim, weights_cfg)
    rate = penalty / (max(length, m) / 100.0)
    t4, t3, t2 = thresholds[dim]
    band = band_from_value(rate, t4, t3, t2)
    return min(band, severity_cap(errors, dim))


# ---------------------------------------------------------------------------
# Weight variants
# ---------------------------------------------------------------------------

WEIGHTS_A = {  # matches F0's own weights (1/5/25, understandability 0/2/25)
    "penalty": {"minor": 1, "major": 5, "critical": 25},
    "understandability": {"minor": 0, "major": 2, "critical": 25},
}
WEIGHTS_B = {  # user-suggested lighter ratio (1/3/10)
    "penalty": {"minor": 1, "major": 3, "critical": 10},
    "understandability": {"minor": 0, "major": 3, "critical": 10},
}
WEIGHT_VARIANTS = {"W_1_5_25": WEIGHTS_A, "W_1_3_10": WEIGHTS_B}


# ---------------------------------------------------------------------------
# Bootstrap QWK CI
# ---------------------------------------------------------------------------

def bootstrap_qwk_ci(y_true: list[int], y_pred: list[int], n_boot: int = 2000, seed: int = 0):
    n = len(y_true)
    if n < 2:
        return (float("nan"), float("nan"))
    rng = random.Random(seed)
    vals = []
    for _ in range(n_boot):
        idx = [rng.randrange(n) for _ in range(n)]
        yt = [y_true[i] for i in idx]
        yp = [y_pred[i] for i in idx]
        vals.append(quadratic_weighted_kappa(yt, yp))
    vals = [v for v in vals if v == v]
    if not vals:
        return (float("nan"), float("nan"))
    vals.sort()
    lo = vals[int(0.025 * len(vals))]
    hi = vals[min(len(vals) - 1, int(0.975 * len(vals)))]
    return (lo, hi)
