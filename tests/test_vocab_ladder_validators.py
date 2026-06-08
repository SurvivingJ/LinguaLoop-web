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
    'semantic_class': 'concrete_noun',
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
    'semantic_class': '具体名词',
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
    'semantic_class': 'function_word',
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
