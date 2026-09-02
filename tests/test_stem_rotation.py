"""Tests for question stem rotation and recency exclusion (plan §1, T1.1/T1.2).

The defect: 9.4% of live question stems repeat while the choice sets behind
them are almost entirely distinct. The worst case is a single Japanese
author_purpose stem appearing 36 times across 36 unrelated topics
(fermentation, wine terroir, venture capital). The generator is fine; the
surface phrasing is what reads as repetitive.

Duplication concentrates in the two topic-independent types — main_idea (3
groups) and author_purpose (6) — which is why only those, plus inference, have
a pool.
"""

import pytest

from services.test_generation import stem_rotation
from services.test_generation.stem_rotation import (
    ROTATED_QUESTION_TYPES,
    STEM_POOLS,
    build_directive,
    pool_for,
    select_stem,
)

LANGUAGES = ('en', 'zh', 'ja')

# The stem measured 36 times across 36 topics.
JA_OFFENDER = 'この文章における筆者の態度として最も適切なものはどれか。'


# ----------------------------------------------------------------------
# The pools
# ----------------------------------------------------------------------

@pytest.mark.parametrize('language', LANGUAGES)
@pytest.mark.parametrize('question_type', ROTATED_QUESTION_TYPES)
def test_every_rotated_type_has_a_pool_in_every_language(language, question_type):
    assert len(pool_for(language, question_type)) >= 5


@pytest.mark.parametrize('language', LANGUAGES)
@pytest.mark.parametrize('question_type', ROTATED_QUESTION_TYPES)
def test_pool_entries_are_distinct(language, question_type):
    pool = pool_for(language, question_type)
    assert len(set(pool)) == len(pool)


@pytest.mark.parametrize('language', LANGUAGES)
@pytest.mark.parametrize('question_type', ROTATED_QUESTION_TYPES)
def test_pool_entries_are_non_empty(language, question_type):
    assert all(s.strip() for s in pool_for(language, question_type))


def test_the_36_times_offender_is_one_option_among_several():
    """It is correct Japanese — the defect was its frequency, not its wording,
    so it stays in the pool rather than being banned."""
    pool = pool_for('ja', 'author_purpose')
    assert JA_OFFENDER in pool
    assert len(pool) >= 6


def test_topic_dependent_types_have_no_pool():
    """literal_detail and vocabulary_context vary because the detail does;
    imposing a fixed stem on them would make them worse, not better."""
    for question_type in ('literal_detail', 'vocabulary_context',
                          'supporting_detail'):
        assert pool_for('en', question_type) == ()
        assert select_stem('en', question_type, 'topic-1:4') is None


def test_an_unknown_language_has_no_pool():
    assert pool_for('es', 'main_idea') == ()
    assert select_stem('es', 'main_idea', 'topic-1:4') is None


def test_language_code_is_case_insensitive():
    assert pool_for('ZH', 'main_idea') == pool_for('zh', 'main_idea')


# ----------------------------------------------------------------------
# Selection
# ----------------------------------------------------------------------

def test_selection_is_deterministic():
    """Regenerating the same test must produce the same stem, so a diff of a
    regenerated batch stays readable."""
    first = select_stem('ja', 'author_purpose', 'topic-abc:4')
    for _ in range(5):
        assert select_stem('ja', 'author_purpose', 'topic-abc:4') == first


def test_selection_varies_across_tests():
    """The whole point: 36 different topics must not all land on one stem."""
    chosen = {
        select_stem('ja', 'author_purpose', f'topic-{i}:4') for i in range(60)
    }
    assert len(chosen) >= 5, f'only {len(chosen)} distinct stems across 60 tests'


def test_selection_covers_the_whole_pool_over_enough_tests():
    pool = set(pool_for('en', 'main_idea'))
    chosen = {
        select_stem('en', 'main_idea', f'topic-{i}:3') for i in range(400)
    }
    assert chosen == pool


def test_different_types_in_one_test_select_independently():
    key = 'topic-abc:5'
    main = select_stem('en', 'main_idea', key)
    purpose = select_stem('en', 'author_purpose', key)
    assert main in pool_for('en', 'main_idea')
    assert purpose in pool_for('en', 'author_purpose')


def test_the_same_topic_at_two_tiers_can_differ():
    """Tier is part of the rotation key, so a topic generated at T3 and T6
    does not repeat its own phrasing."""
    chosen = {
        select_stem('en', 'inference', f'topic-{i}:{tier}')
        for i in range(40) for tier in (3, 6)
    }
    assert len(chosen) > 1


# ----------------------------------------------------------------------
# The kill switch
# ----------------------------------------------------------------------

def test_rotation_can_be_switched_off(monkeypatch):
    monkeypatch.setenv('TEST_GEN_STEM_ROTATION', '0')
    assert select_stem('ja', 'author_purpose', 'topic-abc:4') is None
    assert 'QUESTION STEM' not in build_directive(
        'ja', 'author_purpose', 'topic-abc:4'
    )


def test_rotation_is_on_by_default(monkeypatch):
    monkeypatch.delenv('TEST_GEN_STEM_ROTATION', raising=False)
    assert stem_rotation.is_enabled()


# ----------------------------------------------------------------------
# The prompt directive
# ----------------------------------------------------------------------

def test_directive_carries_the_selected_stem():
    directive = build_directive('en', 'main_idea', 'topic-abc:3')
    assert select_stem('en', 'main_idea', 'topic-abc:3') in directive


def test_directive_is_empty_for_an_unrotated_type():
    assert build_directive('en', 'literal_detail', 'topic-abc:3') == ''


def test_recent_stems_are_listed_as_forbidden():
    directive = build_directive(
        'en', 'main_idea', 'topic-abc:3',
        recent_stems=['What is the main idea of this passage?'],
    )
    assert 'do NOT reuse' in directive
    assert 'What is the main idea of this passage?' in directive


def test_the_chosen_stem_is_never_also_listed_as_forbidden():
    """Requiring a stem and forbidding it in the same prompt is the kind of
    self-contradiction that makes a model pick neither."""
    chosen = select_stem('en', 'main_idea', 'topic-abc:3')
    directive = build_directive(
        'en', 'main_idea', 'topic-abc:3',
        recent_stems=[chosen, 'Some other phrasing?'],
    )
    assert directive.count(chosen) == 1
    assert 'Some other phrasing?' in directive


def test_recent_stems_are_deduplicated_and_blanks_dropped():
    directive = build_directive(
        'en', 'main_idea', 'topic-abc:3',
        recent_stems=['Repeated?', 'Repeated?', '', '   ', None],
    )
    assert directive.count('Repeated?') == 1


def test_recency_works_without_a_pool():
    """An unrotated type still benefits from the do-not-reuse list."""
    directive = build_directive(
        'en', 'literal_detail', 'topic-abc:3',
        recent_stems=['Who founded the company?'],
    )
    assert 'Who founded the company?' in directive
    assert 'QUESTION STEM' not in directive
