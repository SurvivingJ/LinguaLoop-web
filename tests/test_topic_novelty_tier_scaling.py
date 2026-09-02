"""Tests for the tier-scaled topic novelty threshold (plan §3, T3.2).

A single global threshold under-rejects at low tiers. The live corpus had only
one topic pair above 0.90 cosine, yet T1 carried all three of

    "A child building a block tower"
    "A child building a toy castle with blocks"
    "A child building with colorful blocks"

because the legitimate concept space for a five-year-old is small and its
vocabulary is constrained, so genuinely near-identical topics score below a
threshold tuned for T6 prose.
"""

import pytest

from services.topic_generation.config import (
    DEFAULT_TIER_SIMILARITY_THRESHOLDS,
    TopicGenConfig,
    _parse_tier_thresholds,
)


@pytest.fixture
def cfg():
    return TopicGenConfig()


def test_low_tiers_are_stricter_than_high_tiers(cfg):
    assert cfg.threshold_for_tier(1) < cfg.threshold_for_tier(6)


def test_thresholds_increase_monotonically_across_tiers(cfg):
    values = [cfg.threshold_for_tier(t) for t in range(1, 7)]
    assert values == sorted(values), 'a higher tier must never be stricter'


def test_the_band_matches_the_plan(cfg):
    assert cfg.threshold_for_tier(1) == pytest.approx(0.82)
    assert cfg.threshold_for_tier(6) == pytest.approx(0.90)


def test_untiered_candidates_fall_back_to_the_flat_threshold(cfg):
    """43 live topics carry no target_age_tier; an unknown tier is not a
    reason to stop deduplicating them."""
    assert cfg.threshold_for_tier(None) == cfg.similarity_threshold


def test_an_unknown_tier_falls_back_rather_than_raising(cfg):
    assert cfg.threshold_for_tier(99) == cfg.similarity_threshold


def test_string_tiers_are_accepted(cfg):
    """Tier arrives from config as an int but from the DB as whatever the
    driver hands back; don't make the caller care."""
    assert cfg.threshold_for_tier('1') == cfg.threshold_for_tier(1)


# -- env override parsing ---------------------------------------------

def test_env_override_replaces_only_the_named_tiers():
    parsed = _parse_tier_thresholds('1:0.75,6:0.95')
    assert parsed[1] == pytest.approx(0.75)
    assert parsed[6] == pytest.approx(0.95)
    assert parsed[3] == DEFAULT_TIER_SIMILARITY_THRESHOLDS[3]


def test_empty_env_yields_the_defaults():
    assert _parse_tier_thresholds('') == DEFAULT_TIER_SIMILARITY_THRESHOLDS
    assert _parse_tier_thresholds('   ') == DEFAULT_TIER_SIMILARITY_THRESHOLDS


def test_a_fat_fingered_entry_keeps_the_default_for_that_tier():
    """Silently disabling tier scaling because of a typo is the failure mode
    this task exists to remove."""
    parsed = _parse_tier_thresholds('1:not-a-number,6:0.95')
    assert parsed[1] == DEFAULT_TIER_SIMILARITY_THRESHOLDS[1]
    assert parsed[6] == pytest.approx(0.95)


def test_parsed_thresholds_are_a_copy_not_the_shared_default():
    parsed = _parse_tier_thresholds('')
    parsed[1] = 0.1
    assert DEFAULT_TIER_SIMILARITY_THRESHOLDS[1] == pytest.approx(0.82)


def test_out_of_range_thresholds_fail_validation(monkeypatch):
    cfg = TopicGenConfig()
    cfg.openrouter_api_key = 'x'
    cfg.openai_api_key = 'x'
    assert cfg.validate()
    cfg.similarity_threshold_by_tier[1] = 1.5
    assert not cfg.validate()
