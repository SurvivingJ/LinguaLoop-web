"""Coverage-gap diagnosis fixes (ADR-028, wiki/evaluations/exercise-gen-phase1-2026-09.md §14).

Item 6 specifically — the fix that doesn't fit naturally into an existing test
module: a non-int sentence index surviving P2/P3 remap (`_remap_level_6` /
`_remap_level_7`) must be coerced at the source.  (Item 5 and the bundle-judge
gather test covered the retired bundle mode and were removed with it.)

Items 1-4 and 7 are covered in tests/test_generation_retry_caps.py,
tests/test_prompt_split_l4_l8.py, tests/test_asset_pipeline_p1_gate.py,
tests/test_vocab_ladder_validators.py, and tests/test_deterministic_generators.py.

LLM-free throughout.
"""

from __future__ import annotations

from services.vocabulary_ladder.asset_generators import prompt2_exercises as p2mod
from services.vocabulary_ladder.asset_generators import prompt3_transforms as p3mod

LANG_EN = 2

# ---------------------------------------------------------------------------
# Item 6 — non-int sentence indices from P2/P3 remap, coerced at the source.
# ---------------------------------------------------------------------------

def test_remap_level_6_coerces_a_string_correct_index():
    gen = p2mod.ExerciseAssetGenerator(db=None, language_id=LANG_EN)
    out = gen._remap_level_6({'1': '3', '2': [
        {'1': 'He run fast.', '2': 'agreement'},
        {'1': 'He runned fast.', '2': 'wrong past form'},
        {'1': 'He is run fast.', '2': 'missing -ing'},
    ]}, sentence_assignments={6: 9})
    assert out['correct_sentence_index'] == 3
    assert isinstance(out['correct_sentence_index'], int)


def test_remap_level_6_falls_back_to_default_on_unparseable_index():
    gen = p2mod.ExerciseAssetGenerator(db=None, language_id=LANG_EN)
    out = gen._remap_level_6({'1': 'not-a-number', '2': []}, sentence_assignments={6: 9})
    assert out['correct_sentence_index'] == 9


def test_remap_level_7_coerces_string_correct_indices():
    gen = p3mod.TransformAssetGenerator(db=None, language_id=LANG_EN)
    out = gen._remap_level_7({'1': 'bad', '2': 'good', '3': 'tense', '4': ['0', '1', '2']})
    assert out['correct_sentence_indices'] == [0, 1, 2]
    assert all(isinstance(i, int) for i in out['correct_sentence_indices'])


def test_remap_level_7_drops_unparseable_indices_but_keeps_valid_ones():
    gen = p3mod.TransformAssetGenerator(db=None, language_id=LANG_EN)
    out = gen._remap_level_7({'1': 'bad', '2': 'good', '3': 'tense', '4': ['0', 'oops', 2]})
    assert out['correct_sentence_indices'] == [0, 2]


def test_remap_level_7_uses_default_when_list_is_entirely_unparseable():
    gen = p3mod.TransformAssetGenerator(db=None, language_id=LANG_EN)
    out = gen._remap_level_7({'1': 'bad', '2': 'good', '3': 'tense', '4': ['x', 'y']})
    assert out['correct_sentence_indices'] == [0, 1, 2]
