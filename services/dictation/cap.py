"""Tier-scaled dictation transcript cap (TASK-715 / ADR-021).

Dictation's transcript limit used to be a single constant — 80 words at every
difficulty, hard-coded inside ``get_recommended_tests``. Against live content
that made the dictation pool effectively "difficulty 1 only": English
transcripts run ~49-91 words at difficulty 1 but ~78-158 at difficulty 3 and
~259-389 at difficulty 6, so a learner who advanced watched their dictation
pool empty out instead of getting harder.

The cap now scales with the complexity tier. Every per-tier value is **greater
than or equal to** the old flat 80, so the eligible set only grows: no existing
dictation test becomes ineligible and nothing needs regenerating.

Canonical for application code. The SQL twin is
``public.dictation_max_words(integer)`` in
migrations/task715_test_time_estimate_tiered.sql; tests/test_dictation_tier_cap.py
parses that migration and asserts the two tables agree, because a divergence
would mean generation targets one length while selection filters at another.
"""

from __future__ import annotations

from typing import Optional

#: difficulty (tests.difficulty, 1-9) -> dim_complexity_tiers.tier_code.
#: Mirrors the difficulty_min/difficulty_max bounds of dim_complexity_tiers.
DIFFICULTY_TO_TIER = {
    1: "T1", 2: "T1",
    3: "T2", 4: "T2",
    5: "T3",
    6: "T4",
    7: "T5",
    8: "T6", 9: "T6",
}

#: tier_code -> max dictation transcript length in words.
#:
#: Rationale for the curve: dictation is listen-and-type, so duration is close
#: to linear in length. The T1 value is deliberately the legacy 80 — beginners'
#: experience is unchanged — and each step up roughly tracks the observed growth
#: in generated passage length, stopping at 400 because beyond that a single
#: dictation stops being a study item and becomes an endurance test.
DICTATION_MAX_WORDS = {
    "T1": 80,
    "T2": 120,
    "T3": 160,
    "T4": 220,
    "T5": 300,
    "T6": 400,
}

#: Used when a test's difficulty is NULL or outside 1-9. Fails SAFE to the old
#: flat cap, the narrowest of the per-tier values — an uncalibrated test keeps
#: exactly the rule it has today rather than silently widening.
DEFAULT_MAX_WORDS = 80

#: tier_code -> (min, max) PASSAGE length in words for generation (TASK-715).
#:
#: The upper bound is exactly DICTATION_MAX_WORDS for the tier, so every test
#: generated from here on is dictation-eligible at its own difficulty — which
#: is what "generation respects the cap" means, given dictation reuses the same
#: `tests` rows as listening and reading rather than having content of its own.
#:
#: This REPLACES a genuine defect in the generation pipeline: it previously read
#: the range from dim_complexity_tiers.word_count_min/max, but word_count_max in
#: that table is a VOCABULARY SIZE (500 / 2000 / 5000 / 10000 / 15000 / 25000),
#: not a passage length. The prose prompt was therefore being told to write
#: "600-25000 words" at T6, which is why live English difficulty-9 transcripts
#: average ~777 words. Consequence to be aware of: new T5/T6 passages will be
#: materially SHORTER than the ones already in the corpus. Existing tests are
#: untouched.
PASSAGE_WORD_RANGE = {
    "T1": (40, 80),
    "T2": (70, 120),
    "T3": (100, 160),
    "T4": (140, 220),
    "T5": (200, 300),
    "T6": (260, 400),
}

#: Fallback passage range for an unknown tier: the legacy flat cap as the
#: ceiling, matching DEFAULT_MAX_WORDS.
DEFAULT_PASSAGE_WORD_RANGE = (40, DEFAULT_MAX_WORDS)

#: Ceiling on how many per-token diff entries are persisted to
#: test_attempts.dictation_diff. Must stay >= the largest possible token count
#: or the stored diff silently truncates mid-passage for high-tier learners —
#: the "truncation surprise" TASK-715 calls out. The 2x headroom covers
#: 'insert' ops, which add user-side tokens beyond the canonical count.
MAX_STORED_DIFF_ENTRIES = max(DICTATION_MAX_WORDS.values()) * 2


def tier_for_difficulty(difficulty: Optional[int]) -> Optional[str]:
    """``tests.difficulty`` -> tier code, or None when out of range."""
    if difficulty is None:
        return None
    try:
        return DIFFICULTY_TO_TIER.get(int(difficulty))
    except (TypeError, ValueError):
        return None


def max_words_for_difficulty(difficulty: Optional[int]) -> int:
    """Transcript word cap for a test of this difficulty.

    Never raises and never returns None — an unknown difficulty gets
    ``DEFAULT_MAX_WORDS``.
    """
    tier = tier_for_difficulty(difficulty)
    if tier is None:
        return DEFAULT_MAX_WORDS
    return DICTATION_MAX_WORDS.get(tier, DEFAULT_MAX_WORDS)


def max_words_for_tier(tier_code: Optional[str]) -> int:
    """Transcript word cap for a ``dim_complexity_tiers.tier_code``."""
    if not tier_code:
        return DEFAULT_MAX_WORDS
    return DICTATION_MAX_WORDS.get(str(tier_code).upper(), DEFAULT_MAX_WORDS)


def passage_word_range(difficulty: Optional[int]) -> tuple:
    """``(min_words, max_words)`` to generate a passage at this difficulty.

    ``max_words`` always equals this tier's dictation cap, so generated content
    stays dictation-eligible. Never raises.
    """
    tier = tier_for_difficulty(difficulty)
    if tier is None:
        return DEFAULT_PASSAGE_WORD_RANGE
    return PASSAGE_WORD_RANGE.get(tier, DEFAULT_PASSAGE_WORD_RANGE)
