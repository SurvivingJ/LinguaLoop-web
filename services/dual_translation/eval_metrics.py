"""Pure metric functions for the dual-translation grading eval harness (TASK-622).

This module is the **measuring stick** cited by every later Evidence-First Grading
task (TASK-623..632): it turns per-item (predicted, expected) grading records into the
metric set from `wiki/algorithms/evidence-first-grading.tech.md` §10 —

  * span detection F1 (relaxed: >= 50% overlap counts as a match),
  * subtype accuracy (on matched pairs only, string equality vs the v4 subtype name),
  * severity within-one agreement (on matched pairs),
  * clean-passage false-positive rate,
  * per-dimension band QWK + exact/adjacent agreement,
  * overall-band QWK + exact/adjacent agreement.

**No I/O.** Every function is pure and depends only on the standard library, so the unit
tests in `tests/test_dt_eval_metrics.py` pin the numbers on hand-checked toy inputs and the
harness (`scripts/run_dt_grading_eval.py`) is the only thing that touches the network/DB.

Record shape consumed by `aggregate_metrics` (the runner normalizes the live grading
contract + the gold fixture into this neutral shape so the metrics never depend on either):

    {
      "kind": "clean" | "single" | "multi",
      "pred_errors": [ {"span": [s, e], "subtype": str, "severity": str} ],
      "exp_errors":  [ {"span": [s, e], "subtype": str, "severity": str} ],
      "pred_bands": {dim: int}, "exp_bands": {dim: int},
      "pred_overall": int, "exp_overall": int,
    }

`span` is the *reproduction* span (character offsets into the learner text) — the one common
coordinate system for aligning a predicted error to an expected one.
"""

from __future__ import annotations

from typing import Optional, Sequence

# The five analytic dimensions, in tier0.RUBRIC_DIMENSIONS order. Duplicated as a plain
# constant (rather than imported) to keep this module free of service-code dependencies;
# tests/test_dt_eval_metrics.py asserts the copy still equals tier0.RUBRIC_DIMENSIONS so the
# duplication cannot drift silently.
DIMENSIONS: tuple[str, ...] = ("accuracy", "understandability", "fidelity", "range", "naturalness")

BAND_MIN = 1
BAND_MAX = 4

# Severity orderings, low -> high reader impact. The MQM triad (TASK-625) is what the live
# grader emits and is the default; the retired 2-level global/local enum stays available as
# an explicit opt-in so pre-TASK-625 baseline runs can be re-scored on their own scale.
# `severity within-one` is only informative once the scale has >2 levels; on the 2-level
# baseline scale every pair is trivially within one, so the *exact* agreement number is the
# meaningful baseline figure.
#
# SEVERITY_TRIAD_ORDER must stay index-equal to prompts.SEVERITY_ENUM (the enum the grader
# decodes against); duplicated here for the same no-service-imports reason as DIMENSIONS,
# and pinned by a test in tests/test_dt_eval_metrics.py.
SEVERITY_V1_ORDER: dict[str, int] = {"local": 0, "global": 1}
SEVERITY_TRIAD_ORDER: dict[str, int] = {"minor": 0, "major": 1, "critical": 2}

Span = Sequence[int]


# ---------------------------------------------------------------------------
# Span geometry + alignment
# ---------------------------------------------------------------------------

def _span_len(span: Span) -> int:
    return max(0, int(span[1]) - int(span[0]))


def overlap_length(a: Span, b: Span) -> int:
    """Length of the intersection of two half-open [start, end) spans (0 if disjoint)."""
    return max(0, min(int(a[1]), int(b[1])) - max(int(a[0]), int(b[0])))


def _match_score(a: Span, b: Span) -> float:
    """Match quality of two spans: overlap as a fraction of the *shorter* span.

    Zero-length spans (insertions/omissions reported as a point [i, i]) are scored by
    containment: 1.0 iff the point falls within the other span's closed interval, else 0.0.

    Sole definition of the match rule — `spans_match` thresholds this and `align_errors`
    ranks candidates by it, so the two cannot disagree.
    """
    la, lb = _span_len(a), _span_len(b)
    if la == 0 or lb == 0:
        point, other = (a, b) if la == 0 else (b, a)
        p = int(point[0])
        return 1.0 if int(other[0]) <= p <= int(other[1]) else 0.0
    return overlap_length(a, b) / min(la, lb)


def spans_match(a: Span, b: Span, threshold: float = 0.5) -> bool:
    """Relaxed span match: overlap >= `threshold` of the *shorter* span counts.

    Zero-length spans (insertions/omissions reported as a point [i, i]) are matched by
    containment: the point matches the other span iff it falls within its closed interval.
    """
    return _match_score(a, b) >= threshold


class Alignment:
    """Result of greedily aligning predicted spans to expected spans (one-to-one)."""

    __slots__ = ("matches", "unmatched_pred", "unmatched_exp")

    def __init__(self, matches, unmatched_pred, unmatched_exp):
        self.matches: list[tuple[int, int]] = matches
        self.unmatched_pred: list[int] = unmatched_pred
        self.unmatched_exp: list[int] = unmatched_exp

    @property
    def tp(self) -> int:
        return len(self.matches)

    @property
    def fp(self) -> int:
        return len(self.unmatched_pred)

    @property
    def fn(self) -> int:
        return len(self.unmatched_exp)


def align_errors(pred_spans: list[Span], exp_spans: list[Span], threshold: float = 0.5) -> Alignment:
    """Greedy one-to-one alignment of predicted -> expected spans by overlap quality.

    All candidate (pred, exp) pairs scoring >= `threshold` under `_match_score` (the same
    rule `spans_match` thresholds) are assigned greedily best-first, never reusing an index.
    Unmatched predictions are false positives; unmatched expected spans are false negatives.
    """
    candidates = []
    for i, ps in enumerate(pred_spans):
        for j, es in enumerate(exp_spans):
            score = _match_score(ps, es)
            if score >= threshold:
                candidates.append((score, i, j))
    # Best overlap first; ties broken by earliest indices for determinism.
    candidates.sort(key=lambda c: (-c[0], c[1], c[2]))

    used_pred: set[int] = set()
    used_exp: set[int] = set()
    matches: list[tuple[int, int]] = []
    for _score, i, j in candidates:
        if i in used_pred or j in used_exp:
            continue
        used_pred.add(i)
        used_exp.add(j)
        matches.append((i, j))

    unmatched_pred = [i for i in range(len(pred_spans)) if i not in used_pred]
    unmatched_exp = [j for j in range(len(exp_spans)) if j not in used_exp]
    return Alignment(sorted(matches), unmatched_pred, unmatched_exp)


# ---------------------------------------------------------------------------
# Detection / classification scores
# ---------------------------------------------------------------------------

def prf1(tp: int, fp: int, fn: int) -> dict:
    """Precision / recall / F1 from raw counts. Empty-everything yields 1.0 (nothing to find,
    nothing wrongly found)."""
    if tp == 0 and fp == 0 and fn == 0:
        return {"precision": 1.0, "recall": 1.0, "f1": 1.0, "tp": 0, "fp": 0, "fn": 0}
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    return {"precision": precision, "recall": recall, "f1": f1, "tp": tp, "fp": fp, "fn": fn}


def span_detection_f1(pred_spans: list[Span], exp_spans: list[Span], threshold: float = 0.5) -> dict:
    """Relaxed span-detection P/R/F1 for a single item's predicted vs expected spans."""
    al = align_errors(pred_spans, exp_spans, threshold)
    return prf1(al.tp, al.fp, al.fn)


def false_positive_rate(clean_error_counts: list[int]) -> dict:
    """Clean-passage false-positive rate from per-clean-item predicted-error counts.

    `item_fp_rate` = fraction of clean items that produced >= 1 predicted error (the headline
    number); `mean_errors` = spurious errors per clean item; `total_errors` = all spurious.
    """
    n = len(clean_error_counts)
    if n == 0:
        return {"item_fp_rate": float("nan"), "mean_errors": float("nan"), "total_errors": 0, "n": 0}
    flagged = sum(1 for c in clean_error_counts if c > 0)
    total = sum(clean_error_counts)
    return {
        "item_fp_rate": flagged / n,
        "mean_errors": total / n,
        "total_errors": total,
        "n": n,
    }


# ---------------------------------------------------------------------------
# Ordinal band agreement (QWK + exact/adjacent)
# ---------------------------------------------------------------------------

def _clip(v: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, int(round(float(v)))))


def quadratic_weighted_kappa(y_true, y_pred, min_rating: int = BAND_MIN, max_rating: int = BAND_MAX) -> float:
    """Cohen's quadratic weighted kappa over integer band ratings in [min_rating, max_rating].

    Returns NaN for empty input. When there is no expected disagreement (a rater is constant),
    returns 1.0 iff the observed ratings agree perfectly, else 0.0 — the standard degenerate
    convention.
    """
    if len(y_true) != len(y_pred):
        raise ValueError("y_true and y_pred must be the same length")
    n = len(y_true)
    if n == 0:
        return float("nan")
    ratings = list(range(min_rating, max_rating + 1))
    R = len(ratings)
    if R == 1:
        return 1.0
    index = {r: i for i, r in enumerate(ratings)}

    yt = [_clip(v, min_rating, max_rating) for v in y_true]
    yp = [_clip(v, min_rating, max_rating) for v in y_pred]

    observed = [[0] * R for _ in range(R)]
    hist_t = [0] * R
    hist_p = [0] * R
    for a, b in zip(yt, yp):
        ia, ib = index[a], index[b]
        observed[ia][ib] += 1
        hist_t[ia] += 1
        hist_p[ib] += 1

    denom_w = (R - 1) ** 2
    weights = [[((i - j) ** 2) / denom_w for j in range(R)] for i in range(R)]

    num = sum(weights[i][j] * observed[i][j] for i in range(R) for j in range(R))
    den = sum(weights[i][j] * (hist_t[i] * hist_p[j] / n) for i in range(R) for j in range(R))
    if den == 0:
        return 1.0 if num == 0 else 0.0
    return 1.0 - num / den


def agreement(y_true, y_pred) -> dict:
    """Exact and adjacent (|diff| <= 1) agreement fractions. NaN on empty input."""
    n = len(y_true)
    if n == 0:
        return {"exact": float("nan"), "adjacent": float("nan"), "n": 0}
    exact = sum(1 for a, b in zip(y_true, y_pred) if int(a) == int(b))
    adjacent = sum(1 for a, b in zip(y_true, y_pred) if abs(int(a) - int(b)) <= 1)
    return {"exact": exact / n, "adjacent": adjacent / n, "n": n}


def band_metrics(y_true, y_pred, min_rating: int = BAND_MIN, max_rating: int = BAND_MAX) -> dict:
    """QWK + exact/adjacent agreement for one band series."""
    ag = agreement(y_true, y_pred)
    return {
        "qwk": quadratic_weighted_kappa(y_true, y_pred, min_rating, max_rating),
        "exact": ag["exact"],
        "adjacent": ag["adjacent"],
        "n": ag["n"],
    }


# ---------------------------------------------------------------------------
# Full aggregation over a run's records
# ---------------------------------------------------------------------------

def aggregate_metrics(
    records: list[dict],
    *,
    dimensions: tuple[str, ...] = DIMENSIONS,
    severity_order: Optional[dict[str, int]] = None,
    span_threshold: float = 0.5,
    band_min: int = BAND_MIN,
    band_max: int = BAND_MAX,
) -> dict:
    """Compute the full §10 metric set over a list of per-item records (see module docstring).

    Span F1 / subtype accuracy / severity agreement aggregate matched pairs across *all* items
    (so a false alarm on a clean or single item still counts as a false positive). The
    clean-passage FP rate is reported separately, restricted to `kind == "clean"` items.
    Pure: no I/O, deterministic given the records.

    `severity_order` defaults to the live MQM triad; pass `SEVERITY_V1_ORDER` to re-score a
    pre-TASK-625 baseline run whose records carry global/local. Severities absent from the
    given order are skipped, so scoring records against the wrong scale reports n=0 rather
    than silently mis-ranking them.
    """
    if severity_order is None:
        severity_order = SEVERITY_TRIAD_ORDER

    tp = fp = fn = 0
    sub_correct = sub_total = 0
    sev_exact = sev_within = sev_total = 0
    clean_counts: list[int] = []
    kind_counts = {"clean": 0, "single": 0, "multi": 0}

    for rec in records:
        kind = rec.get("kind", "single")
        kind_counts[kind] = kind_counts.get(kind, 0) + 1

        pred = rec.get("pred_errors", [])
        exp = rec.get("exp_errors", [])
        al = align_errors([p["span"] for p in pred], [e["span"] for e in exp], span_threshold)
        tp += al.tp
        fp += al.fp
        fn += al.fn

        for i, j in al.matches:
            sub_total += 1
            if pred[i].get("subtype") == exp[j].get("subtype"):
                sub_correct += 1
            pv = severity_order.get(pred[i].get("severity"))
            ev = severity_order.get(exp[j].get("severity"))
            if pv is not None and ev is not None:
                sev_total += 1
                if pv == ev:
                    sev_exact += 1
                if abs(pv - ev) <= 1:
                    sev_within += 1

        if kind == "clean":
            clean_counts.append(len(pred))

    bands: dict[str, dict] = {}
    for dim in dimensions:
        present = [
            rec for rec in records
            if dim in rec.get("exp_bands", {}) and dim in rec.get("pred_bands", {})
        ]
        yt = [rec["exp_bands"][dim] for rec in present]
        yp = [rec["pred_bands"][dim] for rec in present]
        bands[dim] = band_metrics(yt, yp, band_min, band_max)

    # A v2 both-roles-failed contract records pred_overall=None (no scores, by
    # design — TASK-628 failure matrix); such items carry no band signal and are
    # excluded from overall agreement rather than crashing the QWK arithmetic.
    overall_pairs = [
        (rec["exp_overall"], rec["pred_overall"])
        for rec in records
        if rec.get("exp_overall") is not None and rec.get("pred_overall") is not None
    ]
    overall_t = [t for t, _ in overall_pairs]
    overall_p = [p for _, p in overall_pairs]

    return {
        "n_items": len(records),
        "kind_counts": kind_counts,
        "span": prf1(tp, fp, fn),
        "subtype_accuracy": {
            "correct": sub_correct,
            "total": sub_total,
            "accuracy": (sub_correct / sub_total) if sub_total else float("nan"),
        },
        "severity": {
            "exact": (sev_exact / sev_total) if sev_total else float("nan"),
            "within_one": (sev_within / sev_total) if sev_total else float("nan"),
            "n": sev_total,
        },
        "clean_fp": false_positive_rate(clean_counts),
        "bands": bands,
        "overall": band_metrics(overall_t, overall_p, band_min, band_max),
    }
