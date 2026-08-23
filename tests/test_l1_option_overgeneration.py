"""L1 alone may over-generate options; every other option level stays at 4.

Why this is worth a test (TASK-735)
-----------------------------------
``exercise_renderer._render_phonetic`` runs each L1 distractor past the
``ladder_l1_distractor_judge`` and drops the WHOLE variant when fewer than three
survive. With exactly three distractors the generator has to bat 1.000 or the
item is lost — and in the 2026-08-22 ja canary it did not: 17 of 18 distractors
were rejected and the ladder produced zero L1 exercises. The ja L1 prompt now
asks for six options so the judge has slack, which only works while the
validator tolerates the extra ones.

The pin in the other direction matters just as much. L3/L5/L8 distractors are
NOT individually filtered before rendering, so a fifth option there reaches the
learner as a fifth option. If someone ever "simplifies" OPTION_COUNTS into a
blanket range, these tests fail.
"""

import pytest

from services.vocabulary_ladder.validators import VocabAssetValidator

VALIDATOR = VocabAssetValidator()

# Levels routed through _validate_option_level that are NOT individually judged.
PINNED_LEVELS = (3, 5, 8)


def _options(n: int, correct_index: int = 0) -> dict:
    return {
        'options': [
            {'text': f'opt{i}', 'explanation': f'why {i}',
             'is_correct': i == correct_index}
            for i in range(n)
        ]
    }


def _errors(level: int, data: dict) -> list[str]:
    errors: list[str] = []
    VALIDATOR._validate_option_level(level, data, errors)
    return errors


@pytest.mark.parametrize('count', [4, 5, 6, 7, 8])
def test_l1_accepts_overgenerated_option_counts(count):
    """L1 tolerates 4-8 options so the judge can reject some and still render."""
    assert _errors(1, _options(count)) == []


@pytest.mark.parametrize('count', [0, 1, 3, 9, 12])
def test_l1_rejects_counts_outside_the_band(count):
    """Below 4 the renderer cannot fill an MCQ; above 8 is a runaway response."""
    errors = _errors(1, _options(count))
    assert errors, f'expected L1 to reject {count} options'
    assert 'expected 4-8 options' in errors[0]


@pytest.mark.parametrize('level', PINNED_LEVELS)
@pytest.mark.parametrize('count', [3, 5, 6, 8])
def test_unjudged_levels_stay_pinned_at_four(level, count):
    """Only L1 may over-generate — its distractors are the only judged ones."""
    errors = _errors(level, _options(count))
    assert errors, f'expected L{level} to reject {count} options'
    assert 'expected 4 options' in errors[0]


@pytest.mark.parametrize('level', (1,) + PINNED_LEVELS)
def test_four_options_is_valid_everywhere(level):
    assert _errors(level, _options(4)) == []


def test_overgenerated_l1_still_needs_exactly_one_correct():
    """The relaxed count must not relax the single-answer invariant."""
    six = _options(6)
    six['options'][3]['is_correct'] = True
    errors = _errors(1, six)
    assert any('exactly 1 correct option' in e for e in errors)


def test_overgenerated_l1_still_needs_every_explanation():
    """Per-option checks must run over ALL options, not just the first four.

    The renderer keeps kept[:3] after judging, so any of the six can end up in
    front of a learner — an unexplained fifth option is a real defect, not slack.
    """
    six = _options(6)
    six['options'][5]['explanation'] = ''
    errors = _errors(1, six)
    assert any('option 5: missing explanation' in e for e in errors)


def test_l1_option_band_is_declared_not_hardcoded():
    """OPTION_COUNTS is the single place the band lives."""
    assert VocabAssetValidator.OPTION_COUNTS[1] == (4, 8)
    assert VocabAssetValidator.DEFAULT_OPTION_COUNT == (4, 4)
    for level in PINNED_LEVELS:
        assert level not in VocabAssetValidator.OPTION_COUNTS
