"""Unit tests for services.dual_translation.eval_metrics (TASK-622).

Every number here is hand-checked against a small synthetic input so the harness's metric
math is pinned independently of any live grading run. Pure functions, no I/O, no fixtures.
"""

import math

import pytest

from services.dual_translation import eval_metrics as em
from services.dual_translation import prompts, tier0


# ---------------------------------------------------------------------------
# Contract pins (TASK-640)
#
# eval_metrics deliberately hand-copies two production constants to stay
# service-import-free. These tests are the only thing stopping those copies from
# drifting away from what the grader actually emits — drift would silently corrupt
# every harness comparison rather than fail anything.
# ---------------------------------------------------------------------------

def test_dimensions_match_tier0_rubric_dimensions():
    assert em.DIMENSIONS == tuple(tier0.RUBRIC_DIMENSIONS)


def test_severity_triad_order_matches_prompts_severity_enum():
    # Same members, each mapped to its index in the enum (low -> high reader impact).
    assert em.SEVERITY_TRIAD_ORDER == {name: i for i, name in enumerate(prompts.SEVERITY_ENUM)}


# ---------------------------------------------------------------------------
# Span geometry + relaxed matching
# ---------------------------------------------------------------------------

def test_overlap_length():
    assert em.overlap_length([0, 5], [2, 7]) == 3
    assert em.overlap_length([0, 5], [5, 9]) == 0   # touching, half-open -> no overlap
    assert em.overlap_length([0, 5], [6, 9]) == 0   # disjoint


def test_spans_match_relaxed_threshold():
    # overlap 3 of shorter span 5 -> 0.6 >= 0.5 -> match
    assert em.spans_match([0, 5], [2, 7]) is True
    # overlap 1 of shorter span 3 -> 0.33 < 0.5 -> no match
    assert em.spans_match([0, 3], [2, 7]) is False
    # exact
    assert em.spans_match([4, 9], [4, 9]) is True


def test_spans_match_point_spans():
    # zero-length (insertion/omission) point inside closed interval -> match
    assert em.spans_match([3, 3], [2, 7]) is True
    assert em.spans_match([3, 3], [4, 7]) is False
    # two coincident points
    assert em.spans_match([3, 3], [3, 3]) is True


# ---------------------------------------------------------------------------
# Greedy alignment
# ---------------------------------------------------------------------------

def test_align_perfect_one_to_one():
    al = em.align_errors([[0, 5], [10, 15]], [[2, 7], [9, 14]])
    assert al.matches == [(0, 0), (1, 1)]
    assert al.fp == 0 and al.fn == 0


def test_align_greedy_prefers_better_overlap():
    al = em.align_errors([[0, 10], [8, 12]], [[0, 10], [8, 12]])
    assert al.matches == [(0, 0), (1, 1)]
    assert al.tp == 2


def test_align_extra_prediction_is_false_positive():
    al = em.align_errors([[0, 5], [20, 25]], [[0, 5]])
    assert al.matches == [(0, 0)]
    assert al.unmatched_pred == [1]
    assert al.fp == 1 and al.fn == 0


def test_align_missed_expected_is_false_negative():
    al = em.align_errors([], [[0, 5], [10, 15]])
    assert al.matches == []
    assert al.fn == 2 and al.fp == 0


# ---------------------------------------------------------------------------
# P/R/F1
# ---------------------------------------------------------------------------

def test_prf1_basic():
    m = em.prf1(tp=3, fp=1, fn=2)
    assert m["precision"] == pytest.approx(3 / 4)
    assert m["recall"] == pytest.approx(3 / 5)
    assert m["f1"] == pytest.approx(2 * (0.75 * 0.6) / (0.75 + 0.6))


def test_prf1_empty_is_perfect():
    m = em.prf1(0, 0, 0)
    assert m["precision"] == 1.0 and m["recall"] == 1.0 and m["f1"] == 1.0


def test_span_detection_f1_end_to_end():
    # 1 match, 1 spurious prediction, 1 missed expected -> tp1 fp1 fn1
    m = em.span_detection_f1([[0, 5], [30, 35]], [[0, 5], [50, 55]])
    assert (m["tp"], m["fp"], m["fn"]) == (1, 1, 1)
    assert m["f1"] == pytest.approx(0.5)


# ---------------------------------------------------------------------------
# Clean-passage false positives
# ---------------------------------------------------------------------------

def test_false_positive_rate():
    m = em.false_positive_rate([0, 0, 1, 2])
    assert m["item_fp_rate"] == pytest.approx(0.5)   # 2 of 4 items flagged
    assert m["mean_errors"] == pytest.approx(0.75)   # 3 spurious / 4
    assert m["total_errors"] == 3
    assert m["n"] == 4


def test_false_positive_rate_all_clean():
    m = em.false_positive_rate([0, 0, 0])
    assert m["item_fp_rate"] == 0.0 and m["total_errors"] == 0


def test_false_positive_rate_empty_is_nan():
    m = em.false_positive_rate([])
    assert math.isnan(m["item_fp_rate"])


# ---------------------------------------------------------------------------
# QWK + agreement
# ---------------------------------------------------------------------------

def test_qwk_perfect():
    assert em.quadratic_weighted_kappa([1, 2, 3, 4], [1, 2, 3, 4]) == pytest.approx(1.0)


def test_qwk_constant_true_perfect_match():
    assert em.quadratic_weighted_kappa([4, 4, 4], [4, 4, 4]) == pytest.approx(1.0)


def test_qwk_constant_true_with_disagreement():
    assert em.quadratic_weighted_kappa([4, 4, 4], [4, 3, 4]) == pytest.approx(0.0)


def test_qwk_known_value():
    # Hand-computed: true=[1,2,3,4], pred=[2,2,3,3] on the 1..4 scale.
    # Two exact, plus disagreements (1->2) and (4->3), each squared-weight 1/9.
    # num = 2/9. hist_t=[1,1,1,1], hist_p=[0,2,2,0], n=4 -> den = 2/3.
    # kappa = 1 - (2/9)/(2/3) = 1 - 1/3 = 0.6667
    val = em.quadratic_weighted_kappa([1, 2, 3, 4], [2, 2, 3, 3])
    assert val == pytest.approx(0.6667, abs=1e-3)


def test_qwk_penalizes_far_more_than_adjacent():
    near = em.quadratic_weighted_kappa([1, 2, 3, 4], [2, 3, 4, 3])
    far = em.quadratic_weighted_kappa([1, 2, 3, 4], [4, 1, 1, 1])
    assert near > far


def test_qwk_empty_is_nan():
    assert math.isnan(em.quadratic_weighted_kappa([], []))


def test_agreement_exact_and_adjacent():
    ag = em.agreement([1, 2, 3, 4], [1, 2, 4, 4])
    assert ag["exact"] == pytest.approx(0.75)     # 3 of 4 exact
    assert ag["adjacent"] == pytest.approx(1.0)   # every diff <= 1


def test_band_metrics_bundle():
    m = em.band_metrics([3, 3, 4], [3, 4, 4])
    assert m["exact"] == pytest.approx(2 / 3)
    assert m["adjacent"] == pytest.approx(1.0)
    assert m["n"] == 3


# ---------------------------------------------------------------------------
# Full aggregation
# ---------------------------------------------------------------------------

def _rec(kind, pred_errors, exp_errors, pred_bands, exp_bands, pred_overall, exp_overall):
    return {
        "kind": kind,
        "pred_errors": pred_errors,
        "exp_errors": exp_errors,
        "pred_bands": pred_bands,
        "exp_bands": exp_bands,
        "pred_overall": pred_overall,
        "exp_overall": exp_overall,
    }


def test_aggregate_metrics_hand_checked():
    bands4 = {d: 4 for d in em.DIMENSIONS}
    records = [
        # clean item the grader wrongly flagged once (false positive)
        _rec("clean",
             [{"span": [0, 4], "subtype": "word_choice", "severity": "local"}],
             [],
             bands4, bands4, 4, 4),
        # single item: correct span, correct subtype, correct severity
        _rec("single",
             [{"span": [10, 16], "subtype": "particle", "severity": "global"}],
             [{"span": [10, 16], "subtype": "particle", "severity": "global"}],
             {**bands4, "accuracy": 3}, {**bands4, "accuracy": 3}, 3, 3),
        # single item: correct span, wrong subtype, wrong severity
        _rec("single",
             [{"span": [5, 9], "subtype": "omission", "severity": "local"}],
             [{"span": [5, 9], "subtype": "word_choice", "severity": "global"}],
             {**bands4, "fidelity": 3}, {**bands4, "fidelity": 4}, 4, 4),
    ]
    # These records carry the retired global/local severities, so they must opt into the
    # V1 order explicitly now that the triad is the default (TASK-640).
    m = em.aggregate_metrics(records, severity_order=em.SEVERITY_V1_ORDER)

    # Span: 2 matched (items 2 & 3), 1 spurious (clean), 0 missed
    assert (m["span"]["tp"], m["span"]["fp"], m["span"]["fn"]) == (2, 1, 0)

    # Subtype: 1 of 2 matched pairs correct
    assert m["subtype_accuracy"] == {"correct": 1, "total": 2, "accuracy": pytest.approx(0.5)}

    # Severity (global/local): item2 exact; item3 global vs local -> not exact but within-one
    assert m["severity"]["exact"] == pytest.approx(0.5)
    assert m["severity"]["within_one"] == pytest.approx(1.0)

    # Clean FP: 1 of 1 clean item flagged
    assert m["clean_fp"]["item_fp_rate"] == pytest.approx(1.0)
    assert m["clean_fp"]["total_errors"] == 1

    # Bands present for every dimension; accuracy perfectly agrees
    assert m["bands"]["accuracy"]["exact"] == pytest.approx(1.0)
    # fidelity: item3 predicted 3 vs expected 4 -> 2 of 3 exact
    assert m["bands"]["fidelity"]["exact"] == pytest.approx(2 / 3)

    assert m["kind_counts"] == {"clean": 1, "single": 2, "multi": 0}


def test_aggregate_triad_severity_order():
    bands4 = {d: 4 for d in em.DIMENSIONS}
    records = [
        _rec("single",
             [{"span": [0, 3], "subtype": "x", "severity": "minor"}],
             [{"span": [0, 3], "subtype": "x", "severity": "critical"}],
             bands4, bands4, 4, 4),
    ]
    m = em.aggregate_metrics(records, severity_order=em.SEVERITY_TRIAD_ORDER)
    # minor(0) vs critical(2): not exact, not within-one
    assert m["severity"]["exact"] == pytest.approx(0.0)
    assert m["severity"]["within_one"] == pytest.approx(0.0)


def test_aggregate_defaults_to_triad_severity_order():
    """The default must be the live triad, not the retired V1 order (TASK-640).

    minor vs major is within-one but not exact — a result only the 3-level scale can
    produce. Under the V1 order neither slug resolves, so severity would score n=0.
    """
    bands4 = {d: 4 for d in em.DIMENSIONS}
    records = [
        _rec("single",
             [{"span": [0, 3], "subtype": "x", "severity": "minor"}],
             [{"span": [0, 3], "subtype": "x", "severity": "major"}],
             bands4, bands4, 4, 4),
    ]
    m = em.aggregate_metrics(records)
    assert m["severity"]["n"] == 1
    assert m["severity"]["exact"] == pytest.approx(0.0)
    assert m["severity"]["within_one"] == pytest.approx(1.0)


def test_aggregate_v1_order_remains_available_for_baseline_reruns():
    """Pre-TASK-625 baseline records stay re-scorable via the explicit opt-in."""
    bands4 = {d: 4 for d in em.DIMENSIONS}
    records = [
        _rec("single",
             [{"span": [0, 3], "subtype": "x", "severity": "local"}],
             [{"span": [0, 3], "subtype": "x", "severity": "global"}],
             bands4, bands4, 4, 4),
    ]
    m = em.aggregate_metrics(records, severity_order=em.SEVERITY_V1_ORDER)
    assert m["severity"]["n"] == 1
    assert m["severity"]["exact"] == pytest.approx(0.0)
    assert m["severity"]["within_one"] == pytest.approx(1.0)

    # Same records under the default triad: neither slug resolves -> nothing scored,
    # rather than a silently wrong number.
    m_triad = em.aggregate_metrics(records)
    assert m_triad["severity"]["n"] == 0
    assert math.isnan(m_triad["severity"]["exact"])


# ---------------------------------------------------------------------------
# Shared match rule (TASK-640)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("a, b", [
    ([0, 5], [2, 7]),     # partial overlap, above threshold
    ([0, 3], [2, 7]),     # partial overlap, below threshold
    ([4, 9], [4, 9]),     # exact
    ([0, 5], [20, 25]),   # disjoint
    ([3, 3], [2, 7]),     # point inside
    ([3, 3], [4, 7]),     # point outside
    ([3, 3], [3, 3]),     # coincident points
])
def test_spans_match_agrees_with_match_score_threshold(a, b):
    """spans_match must be exactly `_match_score >= threshold` — the rule align_errors
    ranks by — so the two can never drift apart."""
    assert em.spans_match(a, b) == (em._match_score(a, b) >= 0.5)


def test_align_errors_ranks_by_match_score():
    """Greedy assignment prefers the higher-scoring pair when two predictions compete
    for one expected span."""
    exp = [[0, 10]]
    # [0,10] covers the expected span exactly (10/10); [5,20] overlaps only half of it
    # (5 of the shorter span, 10) — both clear the 0.5 threshold and compete for exp[0].
    pred = [[0, 10], [5, 20]]
    assert em._match_score(pred[0], exp[0]) == pytest.approx(1.0)
    assert em._match_score(pred[1], exp[0]) == pytest.approx(0.5)
    al = em.align_errors(pred, exp)
    assert al.matches == [(0, 0)]
    assert al.unmatched_pred == [1]


def test_aggregate_excludes_none_pred_overall():
    """A v2 both-roles-failed contract records pred_overall=None (TASK-628 failure
    matrix: no scores, nothing persisted). Such items must drop out of overall-band
    agreement — not crash the QWK arithmetic or score as a band."""
    bands4 = {d: 4 for d in em.DIMENSIONS}
    records = [
        _rec("single",
             [{"span": [0, 3], "subtype": "x", "severity": "minor"}],
             [{"span": [0, 3], "subtype": "x", "severity": "minor"}],
             bands4, bands4, 4, 4),
        _rec("single",
             [],
             [{"span": [0, 3], "subtype": "x", "severity": "minor"}],
             {}, bands4, None, 4),  # both-fail: no pred bands, no pred overall
    ]
    m = em.aggregate_metrics(records)
    assert m["overall"]["n"] == 1
    assert m["overall"]["exact"] == pytest.approx(1.0)
