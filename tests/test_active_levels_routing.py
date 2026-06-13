"""Routing matrix for compute_active_levels over the ratified semantic_class enum.

TASK-502 / plan §4. The six ratified, language-neutral semantic classes route to
distinct active-level sets:

  concrete            -> skip collocation L5/L8, keep L4 (matrix routes the type)
  abstract/action/property -> full 9-level ladder
  function            -> L1-L3 + L6/L7 only
  proper              -> not subscribed to the ladder (empty)
  NULL / unrecognised -> permissive full ladder (pre-backfill default)
"""

import pytest

from services.vocabulary_ladder.config import (
    compute_active_levels, normalize_semantic_class, SEMANTIC_CLASSES, ALL_LEVELS,
)

# language_id convention: 1 = Chinese, 2 = English, 3 = Japanese
ZH, EN, JA = 1, 2, 3
FULL = list(ALL_LEVELS)


@pytest.mark.parametrize("semantic_class,language_id,expected", [
    # concrete: drop collocation levels (5, 8), keep L4
    ('concrete', EN, [1, 2, 3, 4, 6, 7, 9]),
    ('concrete', ZH, [1, 2, 3, 4, 6, 7, 9]),
    ('concrete', JA, [1, 2, 3, 4, 6, 7, 9]),
    # abstract / action / property: full ladder, every language
    ('abstract', EN, FULL),
    ('abstract', ZH, FULL),
    ('action',   ZH, FULL),
    ('action',   JA, FULL),
    ('property', EN, FULL),
    ('property', JA, FULL),
    # function words: receptive + discrimination only
    ('function', EN, [1, 2, 3, 6, 7]),
    ('function', ZH, [1, 2, 3, 6, 7]),
    ('function', JA, [1, 2, 3, 6, 7]),
    # proper nouns: not subscribed to the ladder
    ('proper', EN, []),
    ('proper', ZH, []),
    ('proper', JA, []),
    # unclassified (pre-backfill) falls through to the full ladder
    (None, EN, FULL),
    ('',   ZH, FULL),
    ('mystery_legacy_value', JA, FULL),
])
def test_active_levels_routing(semantic_class, language_id, expected):
    assert compute_active_levels(semantic_class, language_id) == expected


def test_concrete_zh_drops_collocation_keeps_l4():
    """Verification (TASK-502): ZH concrete drops 5/8 but keeps L4 for classifier routing."""
    active = compute_active_levels('concrete', ZH)
    assert 5 not in active
    assert 8 not in active
    assert 4 in active


def test_proper_excluded_from_ladder():
    """`proper` is definition-flashcard only — no ladder subscription."""
    assert compute_active_levels('proper', EN) == []
    assert compute_active_levels('proper', ZH) == []


def test_function_has_no_morphology_or_collocation_levels():
    active = compute_active_levels('function', EN)
    for lv in (4, 5, 8, 9):
        assert lv not in active


@pytest.mark.parametrize("raw,expected", [
    # ratified values pass through
    ('concrete', 'concrete'),
    ('proper', 'proper'),
    ('  function  ', 'function'),       # whitespace tolerated
    # legacy EN labels
    ('concrete_noun', 'concrete'),
    ('abstract_noun', 'abstract'),
    ('action_verb', 'action'),
    ('state_verb', 'action'),
    ('adjective', 'property'),
    ('adverb', 'property'),
    ('function_word', 'function'),
    # legacy ZH labels
    ('具体名词', 'concrete'),
    ('抽象名词', 'abstract'),
    ('动作动词', 'action'),
    ('形容词', 'property'),
    ('功能词', 'function'),
    # unclassified / unknown -> None (NULL-safe, stays inside the CHECK constraint)
    ('other', None),
    ('其他', None),
    ('', None),
    (None, None),
])
def test_normalize_semantic_class(raw, expected):
    assert normalize_semantic_class(raw) == expected


def test_normalize_only_emits_ratified_or_none():
    """A normalised value is always a ratified enum member or None."""
    for raw in ('concrete_noun', '具体名词', 'state_verb', 'other', None, 'proper'):
        out = normalize_semantic_class(raw)
        assert out is None or out in SEMANTIC_CLASSES
