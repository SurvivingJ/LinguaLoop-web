"""Pin `DIFFICULTY_TO_TIER` to the `dim_complexity_tiers` bands.

`dim_complexity_tiers` is the source of truth for difficulty -> tier: test
generation resolves the tier from that table (``get_cefr_config``), and the
word-count range and seed ELO for a test come off the same row. Two Python
copies of those bands exist for code paths that must not pay for a DB round
trip:

  * ``services.conversation_generation.categorical_maps.DIFFICULTY_TO_TIER``
    (dual translation age_tier, model arena, mystery generation, and the
    ``ProseWriter`` fallback), and
  * ``services.dictation.cap.DIFFICULTY_TO_TIER`` (transcript length cap).

They disagreed at difficulty 4 — categorical_maps said T3, the table and the
dictation copy said T2 — so a d4 item was T2 to test generation (T2 word
budget, T2 seed ELO) and T3 to everything reading the constant. These tests
stop the two copies drifting apart again.
"""

import pytest

from services.conversation_generation.categorical_maps import (
    DIFFICULTY_TO_TIER,
    TIER_TO_IRT,
    TIER_TO_PHASE,
)
from services.dictation.cap import DIFFICULTY_TO_TIER as DICTATION_DIFFICULTY_TO_TIER

#: The live `dim_complexity_tiers` bands (difficulty_min..difficulty_max).
DB_BANDS = {
    'T1': (1, 2),
    'T2': (3, 4),
    'T3': (5, 5),
    'T4': (6, 6),
    'T5': (7, 7),
    'T6': (8, 9),
}

EXPECTED = {
    d: tier
    for tier, (lo, hi) in DB_BANDS.items()
    for d in range(lo, hi + 1)
}


@pytest.mark.parametrize('difficulty,tier', sorted(EXPECTED.items()))
def test_difficulty_maps_to_the_dim_complexity_tiers_band(difficulty, tier):
    assert DIFFICULTY_TO_TIER[difficulty] == tier


def test_the_two_python_copies_agree():
    """The regression that prompted this file: d4 was T3 here, T2 there."""
    assert DIFFICULTY_TO_TIER == DICTATION_DIFFICULTY_TO_TIER


def test_every_difficulty_is_covered_exactly_once():
    """tests.difficulty is 1-9 NOT NULL, so a gap would silently fall back."""
    assert sorted(DIFFICULTY_TO_TIER) == list(range(1, 10))


def test_the_map_is_monotone():
    """Tier must never go down as difficulty goes up."""
    tiers = [DIFFICULTY_TO_TIER[d] for d in range(1, 10)]
    assert tiers == sorted(tiers)


def test_every_tier_resolves_downstream():
    """DIFFICULTY_TO_TIER feeds tier-keyed maps; an unknown code would fall
    back to a mid-tier default instead of raising."""
    for tier in set(DIFFICULTY_TO_TIER.values()):
        assert tier in TIER_TO_IRT
        assert tier in TIER_TO_PHASE
