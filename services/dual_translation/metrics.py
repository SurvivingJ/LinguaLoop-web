"""Dual Translation — recurrence-reduction instrumentation (TASK-615).

Pure metric functions over ``dt_card_review`` rows (joined to their card's
``subtype``) that answer the report's non-negotiable instrumentation
requirement: log delayed re-test accuracy on previously-errored items, keyed
back to subtype, and flag any subtype whose recurrence rate is not dropping
within ~3-4 review cycles — the signal that a card's formulation is
violating the SuperMemo minimum-information principle
([[features/dual-translation-remediation.tech]] §Instrumentation requirement).

No I/O. Every function is pure and takes already-joined review records
shaped like:

    {"card_id": ..., "subtype": str, "was_correct": bool, "reviewed_at": <sortable>}

(``reviewed_at`` only needs to support ``<`` — a ``datetime`` or ISO string
both work.) The DB join (``dt_card_review`` -> ``dt_card.subtype``) is the
caller's job, mirroring ``synthesis.py``'s "pure function over plain dicts"
convention.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Sequence

# A subtype's recurrence trend can only be judged once at least this many
# review cycles have been observed; the report's window is "~3-4 cycles".
MIN_CYCLES_TO_EVALUATE = 3
MAX_CYCLE_WINDOW = 4

STATUS_IMPROVING = "improving"
STATUS_NOT_IMPROVING = "not_improving"
STATUS_INSUFFICIENT_DATA = "insufficient_data"


def _cycle_index_reviews(reviews: Sequence[dict]) -> list[dict]:
    """Assign a 1-indexed review-cycle number to each review, per card.

    Each card's own reviews are sorted chronologically and numbered 1, 2, 3...
    so "cycle 1" means "this card's first review", not a calendar period —
    the delayed re-test signal is about repetition count, not wall-clock time.
    """
    by_card: dict[Any, list[dict]] = defaultdict(list)
    for r in reviews:
        by_card[r["card_id"]].append(r)

    indexed: list[dict] = []
    for card_reviews in by_card.values():
        ordered = sorted(card_reviews, key=lambda r: r["reviewed_at"])
        for cycle, r in enumerate(ordered, start=1):
            indexed.append({**r, "cycle": cycle})
    return indexed


def recurrence_rate_by_cycle(reviews: Sequence[dict]) -> dict[int, float]:
    """``{cycle: recurrence_rate}`` for ONE subtype's reviews (pre-filtered).

    ``recurrence_rate`` at a cycle = fraction of that cycle's reviews (across
    all of the subtype's cards) that were incorrect (``was_correct`` falsy)
    — the "did the error recur" rate. Cards naturally drop out of later
    cycles as they graduate (fewer total reviews at cycle 4 than cycle 1);
    that attrition is expected and not corrected for.
    """
    by_cycle: dict[int, list[bool]] = defaultdict(list)
    for r in _cycle_index_reviews(reviews):
        by_cycle[r["cycle"]].append(bool(r["was_correct"]))
    return {
        cycle: 1.0 - (sum(vals) / len(vals))
        for cycle, vals in by_cycle.items()
    }


def evaluate_trend(
    curve: dict[int, float],
    *,
    min_cycles: int = MIN_CYCLES_TO_EVALUATE,
    max_cycles: int = MAX_CYCLE_WINDOW,
) -> dict:
    """Judge one subtype's recurrence curve against the ~3-4 cycle window.

    Returns ``{"status", "flagged", "baseline_rate", "latest_rate",
    "cycles_observed"}``. ``status`` is:
      - ``insufficient_data`` — fewer than ``min_cycles`` observed yet; too
        early to judge (never flagged — a quiet subtype is not a failing one).
      - ``not_improving`` — recurrence at the latest observed cycle (capped
        at ``max_cycles``) has not dropped below the cycle-1 baseline.
      - ``improving`` — recurrence at that cycle is below the baseline.
    """
    cycles_observed = max(curve) if curve else 0
    observed_in_window = sorted(c for c in curve if c <= max_cycles)

    if not observed_in_window or observed_in_window[-1] < min_cycles:
        return {
            "status": STATUS_INSUFFICIENT_DATA,
            "flagged": False,
            "baseline_rate": curve.get(1),
            "latest_rate": None,
            "cycles_observed": cycles_observed,
        }

    latest_cycle = observed_in_window[-1]
    baseline_rate = curve[1]
    latest_rate = curve[latest_cycle]
    improving = latest_rate < baseline_rate

    return {
        "status": STATUS_IMPROVING if improving else STATUS_NOT_IMPROVING,
        "flagged": not improving,
        "baseline_rate": baseline_rate,
        "latest_rate": latest_rate,
        "cycles_observed": cycles_observed,
    }


def compute_recurrence_metrics(
    reviews: Sequence[dict],
    *,
    min_cycles: int = MIN_CYCLES_TO_EVALUATE,
    max_cycles: int = MAX_CYCLE_WINDOW,
) -> dict[str, dict]:
    """Full per-subtype recurrence-reduction metric (dashboard entry point).

    Groups already-joined ``dt_card_review`` records by ``subtype``, then
    computes each subtype's cycle-indexed recurrence curve and trend
    judgement independently.

    Returns ``{subtype: {"curve": {cycle: rate}, "status", "flagged",
    "baseline_rate", "latest_rate", "cycles_observed"}}``.
    """
    by_subtype: dict[str, list[dict]] = defaultdict(list)
    for r in reviews:
        by_subtype[r["subtype"]].append(r)

    result: dict[str, dict] = {}
    for subtype, subtype_reviews in by_subtype.items():
        curve = recurrence_rate_by_cycle(subtype_reviews)
        trend = evaluate_trend(curve, min_cycles=min_cycles, max_cycles=max_cycles)
        result[subtype] = {"curve": curve, **trend}
    return result
