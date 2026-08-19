"""TASK-526 — Traditional-script serve toggle.

The mirror is dual-stored at generation time (TASK-509); this suite covers the
read side. Three properties matter, and each has a test that would fail if the
implementation drifted:

  1. **Pure field selection.** No OpenCC on the request path — the 發/髮
     ambiguity needs phrase context that only the generation-time converter
     had. Enforced by source inspection, not just by convention.
  2. **Every learner-visible string**, including options and reasoning, not
     only the stem.
  3. **A missing mirror field serves Simplified and is flagged**, so a drifted
     mirror is a review task rather than a blank exercise.
"""

import ast
import pathlib

import pytest

from services.vocabulary_ladder import script_serving
from services.vocabulary_ladder.script_serving import (
    FALLBACK_KEY, VARIANT_SIMPLIFIED, VARIANT_TRADITIONAL,
    apply_to_items, applies_to, select_script_fields, variant_from_preferences,
)
from utils.answer_normalization import matches, normalize

LANG_ZH, LANG_EN, LANG_JA = 1, 2, 3

REPO = pathlib.Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _zh_item(mirror=None, **content_overrides):
    """A ZH cloze item with a full Traditional mirror.

    发 is the interesting character: it is 發 (to send / develop) here and
    would be 髮 (hair) in another phrase. Only a phrase-aware converter with
    the whole sentence gets that right, which is why the mirror is computed
    once at generation time.
    """
    content = {
        'schema_version': 2,
        'sentence_with_blank': '他___了一封信。',
        'original_sentence': '他发了一封信。',
        'correct_answer': '发',
        'options': ['发', '发展', '头发', '发现'],
        'explanation': '发送信件',
        'word_definition': 'to send',
        'expected_seconds': 30,
        'audio_url': None,
    }
    content.update(content_overrides)
    if mirror is None:
        mirror = {
            'schema_version': 2,
            'sentence_with_blank': '他___了一封信。',
            'original_sentence': '他發了一封信。',
            'correct_answer': '發',
            'options': ['發', '發展', '頭髮', '發現'],
            'explanation': '發送信件',
            'word_definition': 'to send',
            'expected_seconds': 30,
            'audio_url': None,
        }
    if mirror is not False:
        content['hant'] = mirror
    return content


# ---------------------------------------------------------------------------
# Preference reading
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('prefs, expected', [
    ({'script_variant': 'traditional'}, VARIANT_TRADITIONAL),
    ({'script_variant': 'simplified'}, VARIANT_SIMPLIFIED),
    # Every existing user is in this state — the key has never been written.
    ({}, VARIANT_SIMPLIFIED),
    (None, VARIANT_SIMPLIFIED),
    ({'script_variant': 'hanzi'}, VARIANT_SIMPLIFIED),
    ({'script_variant': None}, VARIANT_SIMPLIFIED),
])
def test_variant_from_preferences(prefs, expected):
    assert variant_from_preferences(prefs) == expected


@pytest.mark.parametrize('language_id, variant, expected', [
    (LANG_ZH, VARIANT_TRADITIONAL, True),
    (LANG_ZH, VARIANT_SIMPLIFIED, False),
    (LANG_JA, VARIANT_TRADITIONAL, False),
    (LANG_EN, VARIANT_TRADITIONAL, False),
])
def test_applies_only_to_chinese_traditional(language_id, variant, expected):
    assert applies_to(language_id, variant) is expected


# ---------------------------------------------------------------------------
# Field selection
# ---------------------------------------------------------------------------

def test_traditional_selects_every_learner_visible_field():
    """AC: 'renders traditional for all item types incl. options and reasoning'."""
    out = select_script_fields(_zh_item(), VARIANT_TRADITIONAL, LANG_ZH)

    assert out['original_sentence'] == '他發了一封信。'
    assert out['correct_answer'] == '發'
    assert out['options'] == ['發', '發展', '頭髮', '發現']
    assert out['explanation'] == '發送信件'
    assert out['script_variant'] == VARIANT_TRADITIONAL
    # The 發/髮 split survives: both are 发 in Simplified.
    assert '頭髮' in out['options'] and '發展' in out['options']


def test_mirror_is_stripped_from_the_served_payload():
    out = select_script_fields(_zh_item(), VARIANT_TRADITIONAL, LANG_ZH)
    assert 'hant' not in out


def test_non_string_values_pass_through_untouched():
    out = select_script_fields(_zh_item(), VARIANT_TRADITIONAL, LANG_ZH)
    assert out['expected_seconds'] == 30
    assert out['audio_url'] is None
    assert out['schema_version'] == 2


def test_simplified_leaves_content_alone():
    original = _zh_item()
    out = select_script_fields(original, VARIANT_SIMPLIFIED, LANG_ZH)

    assert out is original
    assert out['correct_answer'] == '发'


def test_japanese_is_untouched_even_when_traditional_is_set():
    """Kanji is not a script variant this toggle governs."""
    item = {'original_sentence': '本を読む。', 'hant': {'original_sentence': 'WRONG'}}
    assert select_script_fields(item, VARIANT_TRADITIONAL, LANG_JA) is item


def test_legacy_content_without_a_mirror_serves_simplified():
    item = _zh_item(mirror=False)
    out = select_script_fields(item, VARIANT_TRADITIONAL, LANG_ZH)

    assert out is item
    assert out['correct_answer'] == '发'


def test_the_source_is_never_mutated():
    item = _zh_item()
    select_script_fields(item, VARIANT_TRADITIONAL, LANG_ZH)
    assert item['correct_answer'] == '发'
    assert 'hant' in item


# ---------------------------------------------------------------------------
# Missing-mirror fallback (AC: simplified served + flagged for review)
# ---------------------------------------------------------------------------

def test_a_field_absent_from_the_mirror_falls_back_and_is_flagged():
    mirror = {
        'original_sentence': '他發了一封信。',
        'correct_answer': '發',
        'options': ['發', '發展', '頭髮', '發現'],
        # 'explanation' was added to content after this mirror was written.
    }
    out = select_script_fields(_zh_item(mirror=mirror), VARIANT_TRADITIONAL, LANG_ZH)

    assert out['correct_answer'] == '發'          # what the mirror has
    assert out['explanation'] == '发送信件'         # what it does not
    assert any('explanation' in f for f in out[FALLBACK_KEY])


def test_a_mirror_list_of_a_different_length_falls_back_wholesale():
    """A shape mismatch means the two have drifted; the pairing is unreliable."""
    mirror = {'options': ['發', '發展'], 'correct_answer': '發'}
    out = select_script_fields(_zh_item(mirror=mirror), VARIANT_TRADITIONAL, LANG_ZH)

    assert out['options'] == ['发', '发展', '头发', '发现']
    assert any('options' in f for f in out[FALLBACK_KEY])


def test_a_clean_mirror_adds_no_review_flag():
    out = select_script_fields(_zh_item(), VARIANT_TRADITIONAL, LANG_ZH)
    assert FALLBACK_KEY not in out


def test_nested_dicts_are_walked():
    """The v2 nl block is nested, and its prose is learner-visible."""
    content = {
        'stem': '发',
        'nl': {'en': {'definition': 'to send'}},
        'hant': {'stem': '發', 'nl': {'en': {'definition': 'to send'}}},
    }
    out = select_script_fields(content, VARIANT_TRADITIONAL, LANG_ZH)
    assert out['stem'] == '發'
    assert out['nl']['en']['definition'] == 'to send'


# ---------------------------------------------------------------------------
# Session payload
# ---------------------------------------------------------------------------

def test_apply_to_items_converts_a_whole_session_and_counts_fallbacks():
    items = [
        {'exercise_id': 'a', 'content': _zh_item()},
        {'exercise_id': 'b', 'content': _zh_item(mirror={'correct_answer': '發'})},
        {'exercise_id': 'c', 'content': None},          # must not raise
    ]
    flagged = apply_to_items(items, VARIANT_TRADITIONAL, LANG_ZH)

    assert items[0]['content']['correct_answer'] == '發'
    assert items[1]['content']['correct_answer'] == '發'
    assert flagged == 1, 'only item b has a partial mirror'


def test_apply_to_items_is_a_no_op_for_simplified():
    items = [{'content': _zh_item()}]
    assert apply_to_items(items, VARIANT_SIMPLIFIED, LANG_ZH) == 0
    assert items[0]['content']['correct_answer'] == '发'


# ---------------------------------------------------------------------------
# AC: no serve-time OpenCC calls
# ---------------------------------------------------------------------------

def test_serve_path_imports_no_converter():
    """AC: 'No serve-time OpenCC calls (pure field selection)'.

    Checked by parsing the module rather than by reading it, so the property
    survives a future edit that adds a conversion 'just for this one field'.
    The 發/髮 disambiguation needs phrase context the serve path does not have.
    """
    source = (REPO / 'services' / 'vocabulary_ladder' / 'script_serving.py').read_text(
        encoding='utf-8',
    )
    tree = ast.parse(source)

    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module or '')

    forbidden = {'opencc', 'services.vocabulary_ladder.script_converter'}
    assert not (imported & forbidden), (
        f'script_serving must not import a converter; found {imported & forbidden}'
    )
    assert 'ScriptConverter' not in source


# ---------------------------------------------------------------------------
# AC: cloze_typed accepts Traditional-typed input
# ---------------------------------------------------------------------------

def test_cloze_typed_accepts_traditional_input_via_t2s():
    """AC: a learner with a Traditional IME typing 發 for a stored 发 is right.

    The fold runs one way only (t2s), so the stored Simplified key is never
    rewritten — this is about grading, not about content.
    """
    pytest.importorskip('opencc', reason='OpenCC is optional on the serve path')

    accepted = ['发']
    assert matches('發', accepted, language_id=LANG_ZH)
    assert matches('发', accepted, language_id=LANG_ZH)
    assert not matches('收', accepted, language_id=LANG_ZH)


def test_t2s_fold_does_not_apply_to_other_languages():
    """The fold is Chinese-only; kanji must not be folded for Japanese."""
    assert normalize('發', language_id=LANG_JA) == '發'


def test_valid_variants_are_what_the_route_accepts():
    """The route validates against this tuple; keep them in step."""
    assert set(script_serving.VALID_VARIANTS) == {'simplified', 'traditional'}
