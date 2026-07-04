"""Shape + weight-effect tests for the TASK-616 rubric v2 seed.

The taxonomy carries no weights; compute_overall_band reads them only from
dt_rubric_version. So the "JA keigo -> fidelity up-weighted" and "ZH classifier/
aspect -> accuracy up-weighted" acceptance criteria are met by *this* seed, not by
the taxonomy. These tests extract the real config out of
migrations/dt_rubric_v2_seed.sql and prove:

  * ja.fidelity and zh.accuracy are raised above the v1 baseline (and above the
    default), the default weights are untouched, and the band descriptors are
    byte-identical to v1 (only weights change).
  * The up-weight actually MOVES grades: for a reproduction weak on the up-weighted
    dimension, v2's weighted score is strictly lower than v1's (via the real
    grader_cascade.compute_overall_band math).
"""

import json
import pathlib
import re

import pytest

from services.dual_translation import grader_cascade
from services.dual_translation.tier0 import MAX_BAND, RUBRIC_DIMENSIONS

MIGRATIONS = pathlib.Path(__file__).resolve().parents[1] / "migrations"
V1_PATH = MIGRATIONS / "dt_rubric_v1_seed.sql"
V2_PATH = MIGRATIONS / "dt_rubric_v2_seed.sql"


def _extract_config(path: pathlib.Path) -> dict:
    m = re.search(r"\$rubric\$(.*?)\$rubric\$", path.read_text(encoding="utf-8"), re.DOTALL)
    assert m, f"could not find the $rubric$...$rubric$ literal in {path.name}"
    return json.loads(m.group(1))


@pytest.fixture(scope="module")
def v1() -> dict:
    return _extract_config(V1_PATH)


@pytest.fixture(scope="module")
def v2() -> dict:
    return _extract_config(V2_PATH)


def _weighted_mean(scores: dict, cfg: dict, l2: str) -> float:
    """Mirror of compute_overall_band's pre-rounding weighted mean, so we can assert
    the raw grade moves even when it doesn't cross a rounding boundary."""
    weights_cfg = cfg.get("weights", {})
    default = weights_cfg.get("default", {})
    overrides = weights_cfg.get("by_language", {}).get(l2, {})
    raw = {d: overrides.get(d, default.get(d, 1.0 / len(RUBRIC_DIMENSIONS))) for d in RUBRIC_DIMENSIONS}
    total = sum(raw.values()) or 1.0
    return sum(scores.get(d, MAX_BAND) * (w / total) for d, w in raw.items())


# ---------------------------------------------------------------------------
# Weight values
# ---------------------------------------------------------------------------

def test_ja_fidelity_raised_above_baseline_and_default(v1, v2):
    assert v1["weights"]["by_language"]["ja"]["fidelity"] == 0.25
    assert v2["weights"]["by_language"]["ja"]["fidelity"] == 0.30
    # 0.25 <= 0.30 <= 0.35 per the task's stated band, and strictly above baseline + default
    assert 0.25 <= v2["weights"]["by_language"]["ja"]["fidelity"] <= 0.35
    assert v2["weights"]["by_language"]["ja"]["fidelity"] > v2["weights"]["default"]["fidelity"]


def test_zh_accuracy_raised_above_baseline(v1, v2):
    assert v1["weights"]["by_language"]["zh"]["accuracy"] == 0.35
    assert v2["weights"]["by_language"]["zh"]["accuracy"] == 0.40
    assert v2["weights"]["by_language"]["zh"]["accuracy"] > 0.35  # task: "0.35+, higher than baseline"
    assert v2["weights"]["by_language"]["zh"]["accuracy"] > v2["weights"]["default"]["accuracy"]


def test_default_weights_unchanged(v1, v2):
    assert v2["weights"]["default"] == v1["weights"]["default"]


def test_band_descriptors_byte_identical_to_v1(v1, v2):
    assert v2["band_descriptors"] == v1["band_descriptors"], "v2 must change weights only"


# ---------------------------------------------------------------------------
# The up-weight actually moves grades (via the real compute_overall_band math)
# ---------------------------------------------------------------------------

def test_ja_fidelity_upweight_lowers_a_keigo_weak_grade(v1, v2):
    # A reproduction that is fine everywhere except fidelity (the keigo/register
    # dimension) — the v2 up-weight must pull the aggregate score down.
    scores = {"accuracy": 4, "understandability": 4, "fidelity": 1, "naturalness": 4, "range": 4}
    assert _weighted_mean(scores, v2, "ja") < _weighted_mean(scores, v1, "ja")
    assert grader_cascade.compute_overall_band(scores, v2, "ja") <= grader_cascade.compute_overall_band(scores, v1, "ja")


def test_zh_accuracy_upweight_lowers_a_classifier_weak_grade(v1, v2):
    # Weak only on accuracy (where classifier/aspect errors land) — v2 pulls it down.
    scores = {"accuracy": 1, "understandability": 4, "fidelity": 4, "naturalness": 4, "range": 4}
    assert _weighted_mean(scores, v2, "zh") < _weighted_mean(scores, v1, "zh")
    assert grader_cascade.compute_overall_band(scores, v2, "zh") <= grader_cascade.compute_overall_band(scores, v1, "zh")


def test_upweight_is_language_scoped(v1, v2):
    # An all-4 reproduction is unaffected; and en has no overrides in either version.
    perfect = {d: MAX_BAND for d in RUBRIC_DIMENSIONS}
    assert grader_cascade.compute_overall_band(perfect, v2, "ja") == MAX_BAND
    scores = {"accuracy": 2, "understandability": 3, "fidelity": 2, "naturalness": 3, "range": 3}
    assert _weighted_mean(scores, v2, "en") == _weighted_mean(scores, v1, "en")


# ---------------------------------------------------------------------------
# Seed migration safety
# ---------------------------------------------------------------------------

def test_seed_bumps_to_v2_single_active_row():
    sql = V2_PATH.read_text(encoding="utf-8")
    assert "VALUES (\n    2," in sql
    assert "SET is_active = false WHERE is_active AND version <> 2" in sql
    assert "ON CONFLICT (version) DO UPDATE" in sql
    do_update = sql.split("ON CONFLICT (version) DO UPDATE", 1)[1]
    assert "is_active = true" in do_update.split(";", 1)[0]
