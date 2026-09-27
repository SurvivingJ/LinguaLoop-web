"""Fixture-based unit tests for VocabAssetValidator.validate_prompt1.

Three representative Prompt 1 cases, each asserting the asset validates
(is_valid == True) and that the resulting active_levels list contains
at least one exercise level. No live LLM; all data is stubbed inline.

Cases:
  1. Invariant English noun — "sheep" (1 morphological form, warn not block)
  2. Chinese concrete noun — "小熊" (no morphological forms; measure-word word class)
  3. English function word — "the" (0 morphological forms; function_word class)
"""

import pytest

from services.vocabulary_ladder.config import compute_active_levels
from services.vocabulary_ladder.validators import VocabAssetValidator

VALIDATOR = VocabAssetValidator()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_sentences(word: str, n: int = 10) -> list[dict]:
    """Build n minimal valid sentence dicts containing `word`."""
    return [
        {
            'text': f'The word {word} appears here in sentence {i}.',
            'target_word': word,
            'source': 'test',
            'complexity_tier': 'B1',
        }
        for i in range(n)
    ]


def _make_sentences_zh(word: str, n: int = 10) -> list[dict]:
    """Build n minimal valid sentence dicts containing a CJK `word`."""
    return [
        {
            'text': f'这是一只{word}，很可爱。{i}',
            'target_word': word,
            'source': 'test',
            'complexity_tier': 'A2',
        }
        for i in range(n)
    ]


# ---------------------------------------------------------------------------
# Case 1: invariant English noun — "sheep"
# ---------------------------------------------------------------------------

_SHEEP_ASSET = {
    'pos': 'noun',
    'semantic_class': 'concrete',
    'definition': 'A domesticated ruminant mammal.',
    'primary_collocate': 'woolly',
    'pronunciation': 'sheep',
    'ipa': '/ʃiːp/',
    'syllable_count': 1,
    'sentences': _make_sentences('sheep'),
    # Only 1 form — English profile expects >=2, so a warning is issued but
    # the asset is still valid (non-blocking).
    'morphological_forms': [{'form': 'sheep', 'label': 'plural'}],
    'register': 'neutral',
    'sense_fingerprint': 'sheep:domesticated_animal',
}


def test_sheep_validates():
    is_valid, errors, warnings = VALIDATOR.validate_prompt1(_SHEEP_ASSET, language_id=2)
    assert is_valid, f"Expected valid, got errors: {errors}"
    assert errors == []
    # Morphology shortfall → exactly 1 warning expected
    assert any('morphological_forms' in w for w in warnings)


def test_sheep_has_active_levels():
    active = compute_active_levels(_SHEEP_ASSET['semantic_class'])
    assert len(active) >= 1


# ---------------------------------------------------------------------------
# Case 2: Chinese concrete noun — "小熊"
# ---------------------------------------------------------------------------

_XIONG_ASSET = {
    'pos': '名词',
    'semantic_class': 'concrete',
    'definition': '体型较小的熊；也常指玩具熊。',
    'primary_collocate': '一只',
    'pronunciation': 'xiǎo xióng',
    'ipa': '',                          # Chinese carries pinyin, not IPA
    'syllable_count': 2,
    'sentences': _make_sentences_zh('小熊'),
    'morphological_forms': [],          # analytic language — no inflection
    'register': 'neutral',
    'sense_fingerprint': '小熊:animal',
}


def test_xiong_validates():
    is_valid, errors, warnings = VALIDATOR.validate_prompt1(_XIONG_ASSET, language_id=1)
    assert is_valid, f"Expected valid, got errors: {errors}"
    assert errors == []
    # Chinese profile: no IPA warning, no morphology warning expected
    assert warnings == []


def test_xiong_has_active_levels():
    # 具体名词 skips collocation levels (5, 8) but still has active levels
    active = compute_active_levels(_XIONG_ASSET['semantic_class'])
    assert len(active) >= 1
    # Confirm collocation levels are skipped
    assert 5 not in active
    assert 8 not in active


# ---------------------------------------------------------------------------
# Case 3: English function word — "the"
# ---------------------------------------------------------------------------

_THE_ASSET = {
    'pos': 'determiner',
    'semantic_class': 'function',
    'definition': 'Definite article used before nouns.',
    'primary_collocate': '',
    'pronunciation': 'the',
    'ipa': '/ðə/',
    'syllable_count': 1,
    'sentences': _make_sentences('the'),
    # Zero morphological forms — English profile warns (non-blocking)
    'morphological_forms': [],
    'register': 'neutral',
    'sense_fingerprint': 'the:definite_article',
}


def test_the_validates():
    is_valid, errors, warnings = VALIDATOR.validate_prompt1(_THE_ASSET, language_id=2)
    assert is_valid, f"Expected valid, got errors: {errors}"
    assert errors == []
    # IPA present so no IPA warning; morphology shortfall → warning
    assert any('morphological_forms' in w for w in warnings)


def test_the_has_active_levels():
    active = compute_active_levels(_THE_ASSET['semantic_class'])
    assert len(active) >= 1


# ---------------------------------------------------------------------------
# ADR-028 Phase 0 fix: legacy semantic_class labels (what the live P1 prompt
# templates for ALL THREE languages actually instruct the model to emit --
# "concrete_noun, abstract_noun, action_verb, state_verb, adjective, adverb,
# other", not the ratified 'concrete'/'abstract'/'action'/'property'/
# 'function'/'proper' set) must validate on the FIRST attempt, not only after
# a repair round. Before this fix, `validate_prompt1` checked the raw value
# against the ratified set directly, so every P1 call in every language
# failed here and paid for an extra repair call -- confirmed empirically via
# the pilot_en/pilot_zh/pilot_ja eval runs (6/6 senses needed a P1 repair
# round; data/eval/runs/pilot_*/*.json each carry a `p1_repair` stage_seconds
# entry). `asset_pipeline.py` already normalizes this same field with
# `normalize_semantic_class()` moments after storing the asset (before
# writing dim_vocabulary.semantic_class) -- this brings the validator's
# blocking check in line with that same accepted mapping instead of ahead of
# it.
# ---------------------------------------------------------------------------

_DIFFERENT_ASSET_LEGACY_LABELS = {
    'pos': 'adjective',
    'semantic_class': 'adjective',  # legacy label -- prompt-instructed value
    'definition': 'Not the same as another or each other; unlike.',
    'primary_collocate': None,
    'pronunciation': 'dif-uh-ruhnt',
    'ipa': '/ˈdɪfərənt/',
    'syllable_count': 3,
    'sentences': _make_sentences('different'),
    'morphological_forms': [
        {'form': 'differently', 'label': 'adverb form'},
        {'form': 'difference', 'label': 'noun form'},
    ],
    'register': 'neutral',
}


def test_legacy_semantic_class_label_validates_without_repair():
    """This is the exact shape google/gemini-3.5-flash-lite returns for en
    P1's first (non-repair) attempt -- see llm_calls raw_response for
    task_name='vocab_prompt1_core', language_code='en'."""
    is_valid, errors, warnings = VALIDATOR.validate_prompt1(
        _DIFFERENT_ASSET_LEGACY_LABELS, language_id=2,
    )
    assert is_valid, f"Expected valid, got errors: {errors}"
    assert errors == []


@pytest.mark.parametrize('legacy_label,ratified_label', [
    ('adjective', 'property'),
    ('concrete_noun', 'concrete'),
    ('abstract_noun', 'abstract'),
    ('action_verb', 'action'),
    ('state_verb', 'action'),
    ('adverb', 'property'),
    ('function_word', 'function'),
])
def test_every_legacy_semantic_class_label_from_the_live_prompts_validates(
    legacy_label, ratified_label,
):
    asset = dict(_DIFFERENT_ASSET_LEGACY_LABELS, semantic_class=legacy_label)
    is_valid, errors, _warnings = VALIDATOR.validate_prompt1(asset, language_id=2)
    assert is_valid, f"legacy label {legacy_label!r} (-> {ratified_label!r}) should validate: {errors}"


def test_semantic_class_other_is_still_rejected():
    """'other' is one of the values the live P1 templates list as an escape
    hatch, but it has no ratified mapping (`_LEGACY_SEMANTIC_CLASS_MAP` maps
    unrecognised/'other' to None deliberately) -- it must still block, not
    silently pass, since nothing downstream knows what to do with it."""
    asset = dict(_DIFFERENT_ASSET_LEGACY_LABELS, semantic_class='other')
    is_valid, errors, _warnings = VALIDATOR.validate_prompt1(asset, language_id=2)
    assert not is_valid
    assert any('semantic_class' in e for e in errors)


def test_genuinely_invalid_semantic_class_is_still_rejected():
    asset = dict(_DIFFERENT_ASSET_LEGACY_LABELS, semantic_class='not_a_real_class')
    is_valid, errors, _warnings = VALIDATOR.validate_prompt1(asset, language_id=2)
    assert not is_valid
    assert any('not_a_real_class' in e for e in errors)
