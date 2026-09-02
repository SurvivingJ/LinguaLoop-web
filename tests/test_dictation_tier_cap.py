"""TASK-715 / ADR-021 — tier-scaled dictation transcript cap.

The cap used to be one constant (80 words) applied at every difficulty, which
made the dictation pool effectively "difficulty 1 only". These tests pin:

  * the cap varies by tier and is monotone non-decreasing (so an advancing
    learner gets harder passages, not an empty pool);
  * no tier is narrower than the old flat 80, so nothing eligible today becomes
    ineligible and no existing test needs regenerating;
  * the SQL and Python tables agree — a divergence would have generation
    targeting one length while selection filtered at another;
  * the time estimate is no longer a single scalar for dictation, which is the
    part that couples back into the planner;
  * the stored-diff ceiling covers the longest tier (the truncation surprise).
"""

import re
from pathlib import Path

import pytest

from services.dictation.cap import (
    DEFAULT_MAX_WORDS,
    DICTATION_MAX_WORDS,
    MAX_STORED_DIFF_ENTRIES,
    PASSAGE_WORD_RANGE,
    max_words_for_difficulty,
    max_words_for_tier,
    passage_word_range,
    tier_for_difficulty,
)

REPO = Path(__file__).resolve().parents[1]
CAP_SQL = (
    REPO / 'migrations' / 'task715_test_time_estimate_tiered.sql'
).read_text(encoding='utf-8')
RECOMMENDED_SQL = (
    REPO / 'migrations' / 'archive' / 'task715_get_recommended_tests_tier_cap.sql'
).read_text(encoding='utf-8')

TIERS = ['T1', 'T2', 'T3', 'T4', 'T5', 'T6']

#: The flat cap TASK-715 replaces. Kept as a literal so the "nothing gets
#: narrower" guarantee is checked against the real historical value.
LEGACY_FLAT_CAP = 80


# ---------------------------------------------------------------------------
# The cap is per-tier, not a constant
# ---------------------------------------------------------------------------

def test_cap_is_not_a_constant_across_tiers():
    values = [DICTATION_MAX_WORDS[t] for t in TIERS]
    assert len(set(values)) > 1, 'the cap is still effectively flat'


def test_cap_is_monotone_non_decreasing():
    values = [DICTATION_MAX_WORDS[t] for t in TIERS]
    assert values == sorted(values)


def test_lowest_and_highest_tier_differ_materially():
    """The verification step: lowest vs highest tier must not be the same."""
    assert DICTATION_MAX_WORDS['T6'] > DICTATION_MAX_WORDS['T1']


@pytest.mark.parametrize('tier', TIERS)
def test_no_tier_is_narrower_than_the_legacy_flat_cap(tier):
    """Guarantees "existing dictation tests are unaffected": the eligible set
    only grows, so nothing that qualifies today stops qualifying."""
    assert DICTATION_MAX_WORDS[tier] >= LEGACY_FLAT_CAP


def test_t1_preserves_the_legacy_cap_exactly():
    assert DICTATION_MAX_WORDS['T1'] == LEGACY_FLAT_CAP


# ---------------------------------------------------------------------------
# difficulty -> tier -> cap resolution, and the fail-safe
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('difficulty,tier', [
    (1, 'T1'), (2, 'T1'), (3, 'T2'), (4, 'T2'),
    (5, 'T3'), (6, 'T4'), (7, 'T5'), (8, 'T6'), (9, 'T6'),
])
def test_difficulty_maps_to_the_dim_complexity_tiers_bands(difficulty, tier):
    assert tier_for_difficulty(difficulty) == tier
    assert max_words_for_difficulty(difficulty) == DICTATION_MAX_WORDS[tier]


@pytest.mark.parametrize('bad', [None, 0, 10, -1, 'six'])
def test_unknown_difficulty_falls_back_to_the_legacy_cap(bad):
    """Fail SAFE, not wide: an uncalibrated test keeps today's narrower rule."""
    assert max_words_for_difficulty(bad) == DEFAULT_MAX_WORDS
    assert DEFAULT_MAX_WORDS == LEGACY_FLAT_CAP


def test_max_words_for_tier_handles_case_and_none():
    assert max_words_for_tier('t3') == DICTATION_MAX_WORDS['T3']
    assert max_words_for_tier(None) == DEFAULT_MAX_WORDS
    assert max_words_for_tier('T99') == DEFAULT_MAX_WORDS


# ---------------------------------------------------------------------------
# Python and SQL must agree
# ---------------------------------------------------------------------------

def _sql_caps():
    return {
        tier: int(n)
        for tier, n in re.findall(r"WHEN '(T[1-6])' THEN (\d+)", CAP_SQL)
    }


@pytest.mark.parametrize('tier', TIERS)
def test_sql_and_python_caps_agree(tier):
    """Generation (Python) and selection (SQL) must use the same number."""
    sql = _sql_caps()
    assert tier in sql, f'{tier} missing from the SQL dictation_max_words CASE'
    assert sql[tier] == DICTATION_MAX_WORDS[tier]


def _executable_sql(text):
    """Strip `--` comment lines. The migration headers quote the old constant
    verbatim to explain what changed, so a naive substring check would match
    the prose rather than the code."""
    return '\n'.join(
        line for line in text.splitlines() if not line.lstrip().startswith('--')
    )


def test_get_recommended_tests_uses_the_function_not_a_constant():
    assert 'public.dictation_max_words(t.difficulty)' in RECOMMENDED_SQL
    assert 'v_dictation_max_words' not in _executable_sql(RECOMMENDED_SQL), (
        'the flat 80-word constant is still declared in get_recommended_tests'
    )


def test_get_recommended_tests_keeps_the_task702_rank_cap():
    """This revision must not silently undo TASK-702's 3 -> 10 widening."""
    assert 'rank_in_type <= 10' in RECOMMENDED_SQL


# ---------------------------------------------------------------------------
# The time estimate is tier-aware (the part that couples into the planner)
# ---------------------------------------------------------------------------

def _sql_dictation_minutes(cap):
    """Mirror of the SQL model: ROUND(2.0 + cap/20.0, 1)."""
    return round(2.0 + cap / 20.0, 1)


def test_dictation_estimate_is_no_longer_a_single_scalar():
    lowest = _sql_dictation_minutes(DICTATION_MAX_WORDS['T1'])
    highest = _sql_dictation_minutes(DICTATION_MAX_WORDS['T6'])
    assert lowest != highest, (
        'dictation minutes must vary by tier or daily budgets drift for '
        'advanced learners (ADR-021)'
    )
    # T1 reproduces the legacy 6.0 exactly, so beginners see no budget change.
    assert lowest == 6.0


def test_two_arg_time_estimate_exists_in_sql():
    assert 'test_time_estimate(p_skill text, p_difficulty integer)' in CAP_SQL


def test_one_arg_time_estimate_still_exists_for_tier_agnostic_skills():
    """Dropping it would break every existing call site, and adding a DEFAULT
    to the second parameter instead would make the 1-arg call ambiguous."""
    assert 'test_time_estimate(p_skill text)' in CAP_SQL


def test_two_arg_estimate_delegates_for_non_dictation_skills():
    assert 'ELSE public.test_time_estimate(p_skill)' in CAP_SQL


def test_resolver_prices_dictation_by_tier_at_both_ends():
    """Budgeting uses the learner's expected tier; accounting uses the tier of
    the test actually placed. Both must be tier-aware or the honest-minutes
    claim is false at one end."""
    resolver = (
        REPO / 'migrations' / 'archive' / 'task714_build_daily_session_surfaces.sql'
    ).read_text(encoding='utf-8')
    assert "CASE WHEN skill_key = 'dictation' THEN v_dict_difficulty END" in resolver
    assert "CASE WHEN ct.skill = 'dictation' THEN t.difficulty END" in resolver


# ---------------------------------------------------------------------------
# Grader / storage handle the longest tier
# ---------------------------------------------------------------------------

def test_stored_diff_ceiling_covers_the_longest_tier():
    """At 400 canonical tokens the old flat 200-entry cap would have truncated
    the stored diff mid-passage, with no error anywhere."""
    assert MAX_STORED_DIFF_ENTRIES >= DICTATION_MAX_WORDS['T6']


def test_stored_diff_ceiling_has_headroom_for_insert_ops():
    """'insert' ops add user-side tokens beyond the canonical count, so the
    ceiling must exceed the canonical maximum rather than merely meet it."""
    assert MAX_STORED_DIFF_ENTRIES > DICTATION_MAX_WORDS['T6']


def test_grader_handles_a_longest_tier_transcript_without_truncating():
    from services.dictation import grade_dictation

    words = [f'word{i}' for i in range(DICTATION_MAX_WORDS['T6'])]
    transcript = ' '.join(words)
    result = grade_dictation(transcript, transcript, 'en')

    assert result.word_total == DICTATION_MAX_WORDS['T6']
    assert result.word_correct == DICTATION_MAX_WORDS['T6']
    assert len(result.diff_payload()) <= MAX_STORED_DIFF_ENTRIES


# ---------------------------------------------------------------------------
# Generation respects the cap
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('tier', TIERS)
def test_generation_range_upper_bound_is_the_dictation_cap(tier):
    """Dictation reuses the same `tests` rows as listening/reading, so the only
    way generation can respect the cap is for the passage ceiling to BE it."""
    assert PASSAGE_WORD_RANGE[tier][1] == DICTATION_MAX_WORDS[tier]


@pytest.mark.parametrize('tier', TIERS)
def test_generation_range_is_well_formed(tier):
    lo, hi = PASSAGE_WORD_RANGE[tier]
    assert 0 < lo < hi


def test_generation_ranges_grow_with_tier():
    lows = [PASSAGE_WORD_RANGE[t][0] for t in TIERS]
    assert lows == sorted(lows)


def test_lowest_and_highest_tier_generate_different_lengths():
    """The verification step, at the generation end."""
    assert passage_word_range(1) != passage_word_range(9)
    assert passage_word_range(9)[1] > passage_word_range(1)[1]


def test_generation_range_survives_an_unknown_difficulty():
    lo, hi = passage_word_range(None)
    assert hi == DEFAULT_MAX_WORDS
    assert 0 < lo < hi


def test_database_client_sources_the_range_from_the_cap_module():
    """It used to return dim_complexity_tiers.word_count_max, which is a
    VOCABULARY size (up to 25000), not a passage length — the prose prompt was
    being told to write "600-25000 words" at T6.

    TASK-740: test generation is tier-native now — get_tier_word_count_range
    reads passage_word_range_for_tier(tier_code) from the cap module, not a
    difficulty-keyed lookup.
    """
    src = (
        REPO / 'services' / 'test_generation' / 'database_client.py'
    ).read_text(encoding='utf-8')
    assert 'return passage_word_range_for_tier(tier.tier_code)' in src
    assert 'return (cefr.word_count_min, cefr.word_count_max)' not in src
