"""Unit tests for the Dual Translation recurrence-reduction instrumentation
(TASK-615).

Pure-logic tests — no DB — mirroring the "mock every boundary" / plain-dict
fixture convention of ``test_dual_translation_synthesis.py``. The DB join
(``dt_card_review`` -> ``dt_card.subtype``) is intentionally not exercised
here; the module under test never touches it.
"""

from datetime import datetime, timedelta, timezone

from services.dual_translation import metrics

NOW = datetime(2026, 7, 14, 12, 0, 0, tzinfo=timezone.utc)


def review(card_id, cycle, was_correct, *, subtype="particle"):
    """Build one dt_card_review-shaped record (already joined to subtype).

    ``cycle`` just spaces out ``reviewed_at`` so chronological ordering
    matches the intended cycle number; the module derives cycle number from
    order, not from this helper.
    """
    return {
        "card_id": card_id,
        "subtype": subtype,
        "was_correct": was_correct,
        "reviewed_at": NOW + timedelta(days=cycle),
    }


def improving_fixture(subtype="particle", n_cards=4):
    """Reviews for ``n_cards`` cards of one subtype, each reviewed 4 times,
    with the wrong-rate dropping from 100% at cycle 1 to 0% at cycle 4 —
    the "seeded improving fixture" the task's acceptance criterion names."""
    error_rate_by_cycle = {1: 1.0, 2: 0.75, 3: 0.25, 4: 0.0}
    rows = []
    for card_id in range(n_cards):
        for cycle in (1, 2, 3, 4):
            n_wrong = round(error_rate_by_cycle[cycle] * n_cards)
            was_correct = card_id >= n_wrong
            rows.append(review(card_id, cycle, was_correct, subtype=subtype))
    return rows


def stalled_fixture(subtype="particle", n_cards=4):
    """Reviews for a subtype whose error rate never drops below its cycle-1
    baseline — the "not improving" / flagged case."""
    rows = []
    for card_id in range(n_cards):
        for cycle in (1, 2, 3, 4):
            was_correct = False  # every review wrong, every cycle
            rows.append(review(card_id, cycle, was_correct, subtype=subtype))
    return rows


# ---------------------------------------------------------------------------
# recurrence_rate_by_cycle — cycle indexing + rate math
# ---------------------------------------------------------------------------

def test_cycle_index_assigned_per_card_not_globally():
    """Two cards each reviewed twice produce cycles {1, 2}, not {1, 2, 3, 4} —
    cycle number is per-card repetition count, not a global review counter."""
    rows = [
        review("card-a", 1, True),
        review("card-a", 2, True),
        review("card-b", 1, False),
        review("card-b", 2, False),
    ]
    curve = metrics.recurrence_rate_by_cycle(rows)
    assert set(curve.keys()) == {1, 2}


def test_recurrence_rate_is_fraction_wrong():
    """cycle 1: 1 of 2 cards wrong -> rate 0.5; cycle 2: 0 of 2 wrong -> rate 0."""
    rows = [
        review("card-a", 1, was_correct=False),
        review("card-b", 1, was_correct=True),
        review("card-a", 2, was_correct=True),
        review("card-b", 2, was_correct=True),
    ]
    curve = metrics.recurrence_rate_by_cycle(rows)
    assert curve[1] == 0.5
    assert curve[2] == 0.0


def test_cards_reviewed_out_of_chronological_input_order_still_sort_correctly():
    """Reviews arriving in a shuffled (non-chronological) list still get the
    right cycle number, since indexing sorts by reviewed_at per card first."""
    rows = [
        review("card-a", 2, was_correct=True),   # later review listed first
        review("card-a", 1, was_correct=False),  # earlier review listed second
    ]
    curve = metrics.recurrence_rate_by_cycle(rows)
    assert curve[1] == 1.0   # cycle 1 (the earlier timestamp) was wrong
    assert curve[2] == 0.0   # cycle 2 (the later timestamp) was correct


# ---------------------------------------------------------------------------
# evaluate_trend + compute_recurrence_metrics — the task's acceptance criterion
# ---------------------------------------------------------------------------

def test_seeded_improving_fixture_shows_decreasing_recurrence():
    """The task's literal acceptance criterion: recurrence is computable per
    subtype and decreasing on a seeded improving fixture."""
    curve = metrics.recurrence_rate_by_cycle(improving_fixture())
    ordered_cycles = sorted(curve)
    rates = [curve[c] for c in ordered_cycles]
    assert rates == sorted(rates, reverse=True)  # monotonically non-increasing
    assert curve[1] > curve[4]  # strictly lower by the end of the window

    trend = metrics.evaluate_trend(curve)
    assert trend["status"] == metrics.STATUS_IMPROVING
    assert trend["flagged"] is False


def test_stalled_subtype_is_flagged_not_improving():
    """A subtype whose recurrence never drops below its cycle-1 baseline
    within the 3-4 cycle window is flagged — the dashboard's whole point."""
    curve = metrics.recurrence_rate_by_cycle(stalled_fixture())
    trend = metrics.evaluate_trend(curve)
    assert trend["status"] == metrics.STATUS_NOT_IMPROVING
    assert trend["flagged"] is True


def test_insufficient_cycles_is_never_flagged():
    """Fewer than MIN_CYCLES_TO_EVALUATE (3) observed -> too early to judge,
    never flagged even though the raw rate hasn't dropped yet."""
    rows = [
        review("card-a", 1, was_correct=False),
        review("card-a", 2, was_correct=False),
    ]
    curve = metrics.recurrence_rate_by_cycle(rows)
    trend = metrics.evaluate_trend(curve)
    assert trend["status"] == metrics.STATUS_INSUFFICIENT_DATA
    assert trend["flagged"] is False


def test_compute_recurrence_metrics_is_computable_per_subtype_independently():
    """Two subtypes mixed in one input list are scored independently — an
    improving subtype and a stalled subtype don't bleed into each other."""
    rows = improving_fixture(subtype="particle") + stalled_fixture(subtype="classifier")
    result = metrics.compute_recurrence_metrics(rows)

    assert set(result.keys()) == {"particle", "classifier"}
    assert result["particle"]["status"] == metrics.STATUS_IMPROVING
    assert result["particle"]["flagged"] is False
    assert result["classifier"]["status"] == metrics.STATUS_NOT_IMPROVING
    assert result["classifier"]["flagged"] is True


def test_empty_input_yields_empty_metrics():
    assert metrics.compute_recurrence_metrics([]) == {}
