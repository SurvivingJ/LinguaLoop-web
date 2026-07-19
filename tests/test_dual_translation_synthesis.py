"""Unit tests for the Dual Translation nightly error synthesis (TASK-610).

Pure-logic tests — no DB, no OpenRouter — mirroring the "mock every boundary"
convention of the other dual-translation suites. The DB/CLI wiring in
scripts/dt_nightly_synthesis.py is intentionally not exercised here (it needs a
live Supabase, out of scope for unit tests); everything testable lives in the
pure ``services.dual_translation.synthesis`` module.
"""

from datetime import datetime, timedelta, timezone

import pytest

from services.dual_translation import synthesis

NOW = datetime(2026, 7, 14, 12, 0, 0, tzinfo=timezone.utc)

# A default pair: user A, L1=en(2) → L2=zh(1).
USER_A = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
USER_B = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"


def err(subtype, *, severity="minor", is_mistake=False, days_ago=1,
        user_id=USER_A, l1=2, l2=1):
    """Build one dt_error_instance-shaped record."""
    return {
        "user_id": user_id,
        "l1_language_id": l1,
        "l2_language_id": l2,
        "subtype": subtype,
        "severity": severity,
        "is_mistake": is_mistake,
        "created_at": NOW - timedelta(days=days_ago),
    }


def synth(errors, existing=None, *, window_days=30, threshold=3, **kw):
    return synthesis.synthesize(
        errors, existing, now=NOW, window_days=window_days, threshold=threshold, **kw
    )


def by_subtype(rows):
    return {r["subtype"]: r for r in rows}


# ---------------------------------------------------------------------------
# Mistake gate — the headline acceptance criterion
# ---------------------------------------------------------------------------

def test_all_mistakes_produce_no_cluster():
    """is_mistake=True rows are dropped before clustering — even N of them
    never form a promotable cluster."""
    rows = synth([err("article", is_mistake=True) for _ in range(5)], threshold=3)
    assert rows == []


def test_mistakes_do_not_count_toward_threshold():
    """A subtype that would promote on raw volume stays sub-threshold once the
    mistakes are gated out."""
    errors = [err("article", is_mistake=True) for _ in range(4)]
    errors += [err("article")]  # one real error
    rows = by_subtype(synth(errors, threshold=3))
    assert rows["article"]["count"] == 1
    assert rows["article"]["remediation_status"] == synthesis.STATUS_WATCHING


def test_seeded_fixture_promotes_only_the_recurring_subtype():
    """The task's verification: given a mix, only the subtype that recurs >= N
    (excluding mistakes) is promoted to `queued`; the rest stay `watching`."""
    errors = (
        [err("preposition") for _ in range(3)]          # recurs 3x → promote
        + [err("article") for _ in range(2)]            # only 2x → watching
        + [err("tense_aspect", is_mistake=True) for _ in range(4)]  # mistakes → gated
    )
    rows = by_subtype(synth(errors, threshold=3))
    assert rows["preposition"]["remediation_status"] == synthesis.STATUS_QUEUED
    assert rows["article"]["remediation_status"] == synthesis.STATUS_WATCHING
    assert "tense_aspect" not in rows  # fully gated, no row at all
    promoted = [s for s, r in rows.items()
                if r["remediation_status"] == synthesis.STATUS_QUEUED]
    assert promoted == ["preposition"]


# ---------------------------------------------------------------------------
# Deterministic clustering — no embeddings
# ---------------------------------------------------------------------------

def test_clustering_is_group_by_on_the_key():
    errors = [
        err("article", user_id=USER_A),
        err("article", user_id=USER_A),
        err("article", user_id=USER_B),      # different user → different cluster
        err("particle", user_id=USER_A, l2=3),  # different subtype+pair
    ]
    clusters = synthesis.cluster_errors(errors)
    assert clusters[(USER_A, 2, 1, "article")] and len(clusters[(USER_A, 2, 1, "article")]) == 2
    assert len(clusters[(USER_B, 2, 1, "article")]) == 1
    assert len(clusters[(USER_A, 2, 3, "particle")]) == 1


def test_same_subtype_different_pair_does_not_merge():
    """A subtype string shared across two directed pairs must not collapse into
    one cluster — the pair is part of the key."""
    errors = [err("topic_comment", l2=1) for _ in range(3)]  # en→zh
    errors += [err("topic_comment", l2=3) for _ in range(3)]  # en→ja
    rows = synth(errors, threshold=3)
    assert len(rows) == 2
    assert {r["l2_language_id"] for r in rows} == {1, 3}
    assert all(r["remediation_status"] == synthesis.STATUS_QUEUED for r in rows)


def test_emission_order_is_deterministic():
    errors = [err("word_order"), err("register"), err("article")]
    rows = synth(errors)
    keys = [(r["user_id"], r["l1_language_id"], r["l2_language_id"], r["subtype"]) for r in rows]
    assert keys == sorted(keys)


# ---------------------------------------------------------------------------
# Promotion threshold
# ---------------------------------------------------------------------------

def test_below_threshold_stays_watching():
    rows = by_subtype(synth([err("article"), err("article")], threshold=3))
    assert rows["article"]["remediation_status"] == synthesis.STATUS_WATCHING


def test_at_threshold_promotes():
    rows = by_subtype(synth([err("article") for _ in range(3)], threshold=3))
    assert rows["article"]["count"] == 3
    assert rows["article"]["remediation_status"] == synthesis.STATUS_QUEUED


def test_proceduralization_gap_promotes_below_threshold():
    key = (USER_A, 2, 1, "article")
    rows = by_subtype(synth([err("article")], threshold=3,
                            proceduralization_gaps={key: True}))
    assert rows["article"]["remediation_status"] == synthesis.STATUS_QUEUED


# ---------------------------------------------------------------------------
# Status state machine — never regress in-flight / resolved
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("status", [synthesis.STATUS_DRILLING, synthesis.STATUS_RESOLVED])
def test_drilling_and_resolved_are_never_regressed(status):
    """Even a fresh promotion must not overwrite a card-pipeline-owned status."""
    key = (USER_A, 2, 1, "article")
    rows = by_subtype(synth([err("article") for _ in range(5)],
                            existing={key: status}, threshold=3))
    assert rows["article"]["remediation_status"] == status


def test_queued_stays_queued_when_window_goes_quiet():
    key = (USER_A, 2, 1, "article")
    rows = by_subtype(synth([err("article")],  # only 1 this window
                            existing={key: synthesis.STATUS_QUEUED}, threshold=3))
    assert rows["article"]["remediation_status"] == synthesis.STATUS_QUEUED


def test_watching_promotes_to_queued_on_recurrence():
    key = (USER_A, 2, 1, "article")
    rows = by_subtype(synth([err("article") for _ in range(3)],
                            existing={key: synthesis.STATUS_WATCHING}, threshold=3))
    assert rows["article"]["remediation_status"] == synthesis.STATUS_QUEUED


# ---------------------------------------------------------------------------
# severity_rank = frequency × severity
# ---------------------------------------------------------------------------

def test_severity_rank_is_sum_of_weights():
    rank = synthesis.severity_rank([
        {"severity": "minor"}, {"severity": "major"}, {"severity": "critical"},
    ])
    assert rank == 1.0 + 2.0 + 3.0


def test_critical_outranks_minor_at_equal_frequency():
    minor = by_subtype(synth([err("article", severity="minor") for _ in range(3)]))
    critical = by_subtype(synth([err("preposition", severity="critical") for _ in range(3)]))
    assert critical["preposition"]["severity_rank"] > minor["article"]["severity_rank"]


def test_legacy_global_local_severity_still_ranks():
    """Pre-triad rows (global/local) map defensively so they rank sanely."""
    rank = synthesis.severity_rank([{"severity": "global"}, {"severity": "local"}])
    assert rank == 2.0 + 1.0


# ---------------------------------------------------------------------------
# Windowing + trend
# ---------------------------------------------------------------------------

def test_previous_window_errors_do_not_count_toward_current():
    errors = [err("article", days_ago=1) for _ in range(2)]        # current window
    errors += [err("article", days_ago=40) for _ in range(5)]      # previous window
    rows = by_subtype(synth(errors, window_days=30, threshold=3))
    assert rows["article"]["count"] == 2  # only current window
    assert rows["article"]["remediation_status"] == synthesis.STATUS_WATCHING


def test_errors_older_than_two_windows_are_ignored():
    errors = [err("article", days_ago=1)]
    errors += [err("article", days_ago=100)]  # older than 2×W
    rows = by_subtype(synth(errors, window_days=30))
    assert rows["article"]["count"] == 1
    assert rows["article"]["trend"]["previous_count"] == 0


def test_trend_delta_pct_reflects_previous_window():
    errors = [err("article", days_ago=1) for _ in range(3)]    # current: 3
    errors += [err("article", days_ago=40) for _ in range(6)]  # previous: 6
    rows = by_subtype(synth(errors, window_days=30))
    trend = rows["article"]["trend"]
    assert trend["current_count"] == 3
    assert trend["previous_count"] == 6
    assert trend["delta_pct"] == -50.0  # improving


def test_trend_delta_pct_none_without_baseline():
    rows = by_subtype(synth([err("article", days_ago=1)], window_days=30))
    assert rows["article"]["trend"]["delta_pct"] is None
