"""Derived-scoring tests (TASK-627, tech spec §4).

Two layers:

  * the pure functions in services/dual_translation/scoring.py — penalty sums,
    threshold banding, is_mistake exclusion, weighted-mean renormalization. The
    load-bearing case is `test_worked_example_*`, which reproduces the tech spec
    §4 worked example EXACTLY against the real seeded rubric v5 config + taxonomy
    v5 subtype_meta — it is the contract for the whole module.
  * the dt_rubric_v5_seed.sql migration — that it carries the three scoring keys
    with the pinned values, adds ONLY those on top of v4, keeps band_descriptors/
    weights equal to v2, and preserves the single-active-row guard shape.
"""

import json
import pathlib
import re

import pytest

from services.dual_translation import prompts, scoring
from services.dual_translation.tier0 import MAX_BAND, RUBRIC_DIMENSIONS

MIGRATIONS = pathlib.Path(__file__).resolve().parents[1] / "migrations"
V2_PATH = MIGRATIONS / "dt_rubric_v2_seed.sql"
V4_PATH = MIGRATIONS / "dt_rubric_v4_seed.sql"
V5_PATH = MIGRATIONS / "dt_rubric_v5_seed.sql"
TAXONOMY_V5_PATH = MIGRATIONS / "dt_taxonomy_v5_seed.sql"


def _extract_rubric_config(path: pathlib.Path) -> dict:
    m = re.search(r"\$rubric\$(.*?)\$rubric\$", path.read_text(encoding="utf-8"), re.DOTALL)
    assert m, f"could not find the $rubric$...$rubric$ literal in {path.name}"
    return json.loads(m.group(1))


def _extract_taxonomy(path: pathlib.Path) -> dict:
    body = "\n".join(
        line for line in path.read_text(encoding="utf-8").splitlines()
        if not line.strip().startswith("--")
    )
    m = re.search(r"\$[a-zA-Z_]*\$(.*?)\$[a-zA-Z_]*\$", body, re.DOTALL)
    assert m, f"could not find the dollar-quoted literal in {path.name}"
    return json.loads(m.group(1))


@pytest.fixture(scope="module")
def rubric_v5() -> dict:
    return _extract_rubric_config(V5_PATH)


@pytest.fixture(scope="module")
def subtype_meta() -> dict:
    return _extract_taxonomy(TAXONOMY_V5_PATH)["subtype_meta"]


# A minimal, hermetic scoring config carrying exactly the pinned provisional
# defaults — used by the pure-logic tests that should not depend on the seed file.
PINNED_CFG = {
    "severity_weights": {"minor": 1, "major": 5, "critical": 25},
    "understandability_weights": {"minor": 0, "major": 2, "critical": 25},
    "band_thresholds": {
        "accuracy": [1, 6, 15],
        "fidelity": [1, 6, 15],
        "understandability": [2, 6, 25],
    },
}

# subtype_meta stub for the pure tests — only the `dimension` field is read.
STUB_META = {
    "particle_wa_ga": {"dimension": "accuracy"},
    "word_order": {"dimension": "accuracy"},
    "word_choice": {"dimension": "fidelity"},
    "omission": {"dimension": "fidelity"},
    "collocation": {"dimension": "naturalness"},
}


def _err(subtype, severity, is_mistake=False):
    return {"subtype": subtype, "severity": severity, "is_mistake": is_mistake}


# ---------------------------------------------------------------------------
# Module <-> production-contract consistency
# ---------------------------------------------------------------------------

def test_severities_match_prompts_severity_enum():
    """scoring.SEVERITIES must stay index-aligned with the production severity enum
    the errors are decoded against (prompts.SEVERITY_ENUM, TASK-625)."""
    assert scoring.SEVERITIES == tuple(prompts.SEVERITY_ENUM)


def test_derived_dimensions_are_real_rubric_dimensions():
    assert set(scoring.DERIVED_DIMENSIONS) <= set(RUBRIC_DIMENSIONS)


# ---------------------------------------------------------------------------
# Worked example (tech spec §4) — the module contract
# ---------------------------------------------------------------------------

def test_worked_example_dimension_bands(rubric_v5, subtype_meta):
    """JA, tech spec §4: ① particle_wa_ga major (accuracy +5) + ② word_choice minor
    (fidelity +1) -> accuracy band 3, fidelity band 4, understandability band 4."""
    errors = [_err("particle_wa_ga", "major"), _err("word_choice", "minor")]
    bands = scoring.compute_dimension_bands(errors, subtype_meta, rubric_v5)
    assert bands == {"accuracy": 3, "fidelity": 4, "understandability": 4}


def test_worked_example_overall(rubric_v5):
    """The full §4 example: derived bands + judged naturalness 3 / range 3, weighted
    by the ja config -> (3×.3 + 4×.3 + 4×.3 + 3×.15 + 3×.1)/1.15 = 3.52 -> overall 4."""
    bands = {"accuracy": 3, "fidelity": 4, "understandability": 4, "naturalness": 3, "range": 3}
    weights = scoring.resolve_weights(rubric_v5, "ja")
    # Pin the ja weights the example depends on (fidelity up-weighted to .30).
    assert weights == {"accuracy": 0.3, "understandability": 0.3, "fidelity": 0.3,
                       "range": 0.15, "naturalness": 0.1}
    assert scoring.compute_overall(bands, weights, RUBRIC_DIMENSIONS) == 4


def test_worked_example_end_to_end(rubric_v5, subtype_meta):
    """The whole §4 path in one: errors -> derived bands -> merge judged -> overall."""
    errors = [_err("particle_wa_ga", "major"), _err("word_choice", "minor")]
    bands = scoring.compute_dimension_bands(errors, subtype_meta, rubric_v5)
    bands.update({"naturalness": 3, "range": 3})
    weights = scoring.resolve_weights(rubric_v5, "ja")
    assert scoring.compute_overall(bands, weights, RUBRIC_DIMENSIONS) == 4


# ---------------------------------------------------------------------------
# compute_dimension_bands — penalties, is_mistake, understandability axis
# ---------------------------------------------------------------------------

def test_clean_submission_is_all_full_marks():
    bands = scoring.compute_dimension_bands([], STUB_META, PINNED_CFG)
    assert bands == {"accuracy": 4, "fidelity": 4, "understandability": 4}


def test_is_mistake_errors_excluded_from_penalties():
    """A major accuracy error flagged is_mistake must NOT penalize any dimension —
    displayed, never scored (ADR-019). The non-mistake minor fidelity error is the
    only thing that counts."""
    errors = [
        _err("particle_wa_ga", "major", is_mistake=True),  # excluded everywhere
        _err("word_choice", "minor"),                       # fidelity +1, und +0
    ]
    bands = scoring.compute_dimension_bands(errors, STUB_META, PINNED_CFG)
    assert bands == {"accuracy": 4, "fidelity": 4, "understandability": 4}
    # Contrast: were the accuracy error NOT a mistake, accuracy would drop to 3.
    scored = [_err("particle_wa_ga", "major"), _err("word_choice", "minor")]
    assert scoring.compute_dimension_bands(scored, STUB_META, PINNED_CFG)["accuracy"] == 3


def test_understandability_counts_all_errors_including_naturalness_mapped():
    """collocation maps to naturalness — no accuracy/fidelity penalty, but it still
    costs understandability. One critical -> und weight 25 <= t2 (25) -> band 2."""
    bands = scoring.compute_dimension_bands([_err("collocation", "critical")], STUB_META, PINNED_CFG)
    assert bands["accuracy"] == 4 and bands["fidelity"] == 4
    assert bands["understandability"] == 2


def test_unknown_subtype_scores_understandability_not_accuracy_fidelity():
    """An error whose subtype is absent from subtype_meta must never crash scoring
    nor silently inflate accuracy/fidelity — it still registers on understandability."""
    bands = scoring.compute_dimension_bands([_err("not_a_real_subtype", "major")], STUB_META, PINNED_CFG)
    assert bands["accuracy"] == 4 and bands["fidelity"] == 4
    assert bands["understandability"] == 4  # und weight for major = 2 <= t4 (2)


def test_threshold_banding_boundaries():
    """penalty <= t4 -> 4, <= t3 -> 3, <= t2 -> 2, else 1 (accuracy: t4/t3/t2 = 1/6/15)."""
    def acc(errors):
        return scoring.compute_dimension_bands(errors, STUB_META, PINNED_CFG)["accuracy"]
    assert acc([_err("word_order", "minor")]) == 4              # 1 <= 1
    assert acc([_err("word_order", "major")]) == 3              # 5 <= 6
    assert acc([_err("word_order", "major")] * 2) == 2          # 10 <= 15
    assert acc([_err("word_order", "critical")]) == 1           # 25 > 15


# ---------------------------------------------------------------------------
# compute_overall — weighting + renormalization on missing judged dims
# ---------------------------------------------------------------------------

def test_overall_renormalizes_when_judged_dims_absent():
    """naturalness/range missing (judgment discarded for lacking evidence spans):
    the mean must renormalize over the present dims, NOT default the absent ones to
    a full mark. All-band-1 derived -> overall 1, not pulled up toward 2 by phantom
    band-4 naturalness/range."""
    weights = {"accuracy": 0.3, "understandability": 0.3, "fidelity": 0.3,
               "range": 0.15, "naturalness": 0.1}
    bands = {"accuracy": 1, "fidelity": 1, "understandability": 1}
    present = ["accuracy", "fidelity", "understandability"]
    assert scoring.compute_overall(bands, weights, present) == 1
    # If the absent dims had defaulted to band 4 (the legacy behaviour), the same
    # inputs would round to 2 — this is exactly the inflation renormalization removes.
    legacy = {**bands, "range": 4, "naturalness": 4}
    weighted = sum(legacy[d] * weights[d] for d in weights)
    assert round(weighted / sum(weights.values())) == 2


def test_overall_rounds_to_nearest_band():
    weights = {d: 1.0 for d in ("accuracy", "fidelity", "understandability")}
    assert scoring.compute_overall({"accuracy": 4, "fidelity": 4, "understandability": 3},
                                   weights, weights) == 4  # 11/3 = 3.67 -> 4
    assert scoring.compute_overall({"accuracy": 3, "fidelity": 3, "understandability": 4},
                                   weights, weights) == 3  # 10/3 = 3.33 -> 3


def test_overall_clipped_to_band_range():
    weights = {"accuracy": 1.0}
    assert scoring.compute_overall({"accuracy": 1}, weights, ["accuracy"]) == 1
    assert scoring.compute_overall({"accuracy": 4}, weights, ["accuracy"]) == MAX_BAND


def test_overall_empty_present_dims_is_full_marks():
    assert scoring.compute_overall({}, {}, []) == MAX_BAND


# ---------------------------------------------------------------------------
# scoring_params — explicit config, no silent constant fallback
# ---------------------------------------------------------------------------

def test_scoring_params_raises_on_pre_v5_config():
    """A v4-era config (weights/band_descriptors only) must NOT quietly score —
    that is the silent-full-marks hole this module refuses to reopen."""
    with pytest.raises(RuntimeError, match="TASK-627"):
        scoring.compute_dimension_bands([], STUB_META, {"weights": {}, "band_descriptors": {}})


@pytest.mark.parametrize("broken, match", [
    ({**PINNED_CFG, "severity_weights": {"minor": 1, "major": 5}}, "missing/non-numeric"),
    ({**PINNED_CFG, "understandability_weights": {"minor": 0, "major": "2", "critical": 25}},
     "missing/non-numeric"),
    ({**PINNED_CFG, "band_thresholds": {"accuracy": [1, 6], "fidelity": [1, 6, 15],
                                        "understandability": [2, 6, 25]}}, "3 ints"),
    ({**PINNED_CFG, "band_thresholds": {"accuracy": [15, 6, 1], "fidelity": [1, 6, 15],
                                        "understandability": [2, 6, 25]}}, "ascending"),
])
def test_scoring_params_rejects_malformed_config(broken, match):
    with pytest.raises(ValueError, match=match):
        scoring.scoring_params(broken)


# ---------------------------------------------------------------------------
# dt_rubric_v5_seed.sql — the seed carries the pinned scoring keys, adds only
# those on top of v4, and keeps the single-active-row guard shape.
# ---------------------------------------------------------------------------

def test_v5_carries_the_pinned_scoring_config(rubric_v5):
    assert scoring.scoring_params(rubric_v5)  # validates + does not raise
    assert rubric_v5["severity_weights"] == {"minor": 1, "major": 5, "critical": 25}
    assert rubric_v5["understandability_weights"] == {"minor": 0, "major": 2, "critical": 25}
    assert {d: list(rubric_v5["band_thresholds"][d]) for d in scoring.DERIVED_DIMENSIONS} == {
        "accuracy": [1, 6, 15], "fidelity": [1, 6, 15], "understandability": [2, 6, 25],
    }


def test_v5_adds_only_the_three_scoring_keys_on_top_of_v4(rubric_v5):
    v4 = _extract_rubric_config(V4_PATH)
    assert set(rubric_v5) == set(v4) | set(scoring.SCORING_KEYS)


def test_v5_band_descriptors_and_weights_match_v2(rubric_v5):
    """v5 is a scoring-keys-only bump: descriptors + weights must still equal v2
    (held by test, since the config is self-contained — TASK-636/ADR-020)."""
    v2 = _extract_rubric_config(V2_PATH)
    assert rubric_v5["band_descriptors"] == v2["band_descriptors"]
    assert rubric_v5["weights"] == v2["weights"]


def _executable_sql(path: pathlib.Path) -> str:
    return "\n".join(
        line for line in path.read_text(encoding="utf-8").splitlines()
        if not line.strip().startswith("--")
    )


def test_v5_seed_is_self_contained():
    sql = _executable_sql(V5_PATH)
    assert "src.config" not in sql, "v5 must not derive its config from another row (TASK-636)"
    assert "FROM public.dt_rubric_version src" not in sql
    assert "$add$" not in sql


def test_v5_seed_bumps_to_v5_single_active_row():
    sql = V5_PATH.read_text(encoding="utf-8")
    assert "VALUES (\n    5," in sql
    assert "SET is_active = false WHERE is_active AND version <> 5" in sql
    assert "ON CONFLICT (version) DO UPDATE" in sql
    do_update = sql.split("ON CONFLICT (version) DO UPDATE", 1)[1]
    assert "is_active = true" in do_update.split(";", 1)[0]


def test_v5_seed_guards_the_single_active_row_invariant():
    sql = _executable_sql(V5_PATH)
    assert "WHERE is_active AND version > 5" in sql       # Guard 1: refuse downgrade
    assert "active_count <> 1" in sql                     # Guard 2: exactly one active
    assert "active_version <> 5" in sql                   # Guard 2: and it is v5
    assert sql.count("RAISE EXCEPTION") >= 3
    assert sql.index("BEGIN;") < sql.index("RAISE EXCEPTION") < sql.index("COMMIT;")
