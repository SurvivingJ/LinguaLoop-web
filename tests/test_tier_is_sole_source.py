"""Phase 0 guardrail for the difficulty->tier collapse (see plan discussed
2026-08-29: "eliminate difficulty as an independent axis, target_age_tier is
the sole source of truth for prose complexity, question distribution, word
count, and ELO seeding").

This file is written BEFORE the collapse lands and is expected to be RED
until Phase 2 (test_generation orchestrator + difficulty_scorer rewrite) is
implemented. Its job is to pin the target contract now, so no intermediate
commit on the way there can silently reintroduce a difficulty-keyed fallback
or a second copy of the tier bands.

Scope: only `services.test_generation` (test/question generation + ELO
seeding). `services.conversation_generation.categorical_maps` and
`services.dictation.cap` keep their own difficulty->tier maps for now — they
read the legacy `tests.difficulty` column for historical rows and are out of
scope for this pass (see test_difficulty_to_tier_matches_db.py, which still
guards those two agreeing with each other).
"""

import inspect

import pytest


# ---------------------------------------------------------------------------
# test_generation.database_client must be tier-native: callers pass a
# dim_complexity_tiers.id (1-6), never a 1-9 difficulty.
# ---------------------------------------------------------------------------

def test_database_client_exposes_tier_native_lookups():
    from services.test_generation.database_client import TestDatabaseClient

    for method_name in (
        'get_tier_config',
        'get_tier_word_count_range',
        'get_tier_initial_elo',
        'get_tier_question_distribution',
    ):
        assert hasattr(TestDatabaseClient, method_name), (
            f"TestDatabaseClient.{method_name} is missing — test generation "
            "must resolve tier config directly by tier_id, not via a "
            "difficulty->tier range scan."
        )


def test_database_client_no_longer_exposes_difficulty_keyed_lookups():
    from services.test_generation.database_client import TestDatabaseClient

    for method_name in (
        'get_cefr_config',
        'get_tier_difficulties',
        'get_initial_elo',
        'get_word_count_range',
        'get_question_distribution',
    ):
        assert not hasattr(TestDatabaseClient, method_name), (
            f"TestDatabaseClient.{method_name} still exists — difficulty "
            "must not be a resolvable axis once the tier collapse lands. "
            "If a caller still needs it, it should be reading "
            "tests.target_age_tier directly."
        )


def test_get_initial_elo_hardcoded_difficulty_fallback_is_gone():
    """The 510-515 hardcoded {1: 800, ..., 9: 2000} fallback in the old
    get_initial_elo silently masked a missing dim_complexity_tiers row. A
    tier-keyed lookup miss must raise instead."""
    import services.test_generation.database_client as dbc
    source = inspect.getsource(dbc)
    assert 'difficulty_to_elo' not in source, (
        "Hardcoded difficulty->ELO fallback table found — a tier lookup "
        "miss must raise (finding #4), not silently degrade to a guessed "
        "ELO."
    )


# ---------------------------------------------------------------------------
# difficulty_scorer: seed_test_elo must key off tier_id, and the reference
# bands must be tier-keyed (6 entries), not difficulty-keyed (9 entries).
# ---------------------------------------------------------------------------

def test_seed_test_elo_takes_tier_id_not_difficulty():
    from services.test_generation import difficulty_scorer

    sig = inspect.signature(difficulty_scorer.seed_test_elo)
    params = list(sig.parameters)

    assert 'target_difficulty' not in params, (
        "seed_test_elo still takes target_difficulty — ELO seeding must "
        "derive directly from target_age_tier (dim_complexity_tiers.id), "
        "per the plan's requirement to remove difficulty as an axis."
    )
    assert 'tier_id' in params, (
        "seed_test_elo must accept tier_id (dim_complexity_tiers.id, 1-6)."
    )


def test_reference_bands_are_tier_keyed_not_difficulty_keyed():
    """Answer to open question #2: keep ONE reference point per tier (6
    entries), not 9 difficulty-level sub-bands, for the a-priori Zipf/
    sentence-length/TTR reference points that anchor ELO seeding."""
    from services.test_generation import difficulty_scorer

    for name in ('_REF_ZIPF', '_REF_SENT_LEN', '_REF_TTR'):
        ref = getattr(difficulty_scorer, name)
        assert set(ref.keys()) == {1, 2, 3, 4, 5, 6}, (
            f"{name} must be keyed 1-6 (dim_complexity_tiers.id), not "
            f"1-9 (legacy difficulty). Found keys: {sorted(ref.keys())}"
        )


def test_seed_test_elo_flags_out_of_band_result():
    """The plan requires seed_test_elo to log (not silently clamp away) when
    the computed ELO falls outside the expected band for its tier. We assert
    the hook point exists rather than asserting on log output, since the
    band definition itself lives in dim_complexity_tiers (DB, not testable
    here without a live/mocked client)."""
    from services.test_generation import difficulty_scorer

    assert hasattr(difficulty_scorer, 'is_elo_in_tier_band') or hasattr(
        difficulty_scorer, 'check_tier_band'
    ), (
        "difficulty_scorer needs an explicit tier-band sanity check "
        "function so seed_test_elo can flag (not mask) an out-of-band "
        "result — see plan requirement #6."
    )


# ---------------------------------------------------------------------------
# Orchestrator: one topic must not fan out one test per difficulty rung.
# ---------------------------------------------------------------------------

def test_generate_test_takes_tier_id_not_difficulty():
    from services.test_generation.orchestrator import TestGenerationOrchestrator

    sig = inspect.signature(TestGenerationOrchestrator._generate_test)
    params = list(sig.parameters)

    assert 'difficulty' not in params, (
        "_generate_test still takes a difficulty param — it must take "
        "tier_id and resolve everything (word count, ELO, question mix) "
        "from dim_complexity_tiers via tier-native lookups."
    )
    assert 'tier_id' in params


def test_orchestrator_source_has_no_difficulty_fanout_loop():
    """Finding #2: one topic used to fan out into one test per difficulty
    rung in target_difficulties. Post-collapse there is exactly one tier per
    topic, so that loop construct must be gone."""
    import services.test_generation.orchestrator as orch
    source = inspect.getsource(orch)
    assert 'target_difficulties' not in source, (
        "target_difficulties fan-out loop still present — a topic's tier "
        "is singular now, so per-topic test generation must be governed by "
        "the Phase 4 cap/spacing policy, not a difficulty-rung loop."
    )
