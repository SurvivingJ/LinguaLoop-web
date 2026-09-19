"""TASK-801: a ja suru-noun labelled `action` must not be planned an L4 morphology slot.

作業 and 循環 are nouns that take する; they carry `semantic_class = action` yet have
no conjugation of their own. The L4 prompt correctly declines for them, the
fragment comes back empty, and ``validate_prompt3`` then rejected the whole P3
asset as "Missing level_4". The gate is the `inflecting_pos` requirement on the
ja ``morphology_slot`` row, fed from P1's ``pos`` — a single definition shared
by the pipeline, the worklist exporter and the renderer.
"""

import pytest

from services.vocabulary_ladder.asset_pipeline import VocabAssetPipeline
from services.vocabulary_ladder.config import (
    JA_NON_INFLECTING_POS,
    active_levels_for_context,
    capability_context_from_core,
    prompt3_levels_for_context,
    type_is_available,
)
from services.vocabulary_ladder.validators import VocabAssetValidator

LANG_ZH, LANG_EN, LANG_JA = 1, 2, 3

_FORMS = [{'form': '作業した', 'label': 'past'}, {'form': '作業しない', 'label': 'neg'}]


def _core(pos, semantic_class='action', forms=_FORMS):
    core = {
        'semantic_class': semantic_class,
        'definition': 'x',
        'pronunciation': 'さぎょう',
        'morphological_forms': list(forms),
        'sentences': [{'text': 's', 'target_word': 't'}],
    }
    if pos is not None:
        core['pos'] = pos
    return core


def _plan(core, language_id=LANG_JA):
    ctx = capability_context_from_core(core)
    levels = active_levels_for_context(core['semantic_class'], language_id, ctx)
    return ctx, levels, prompt3_levels_for_context(levels, core['semantic_class'], language_id, ctx)


@pytest.mark.parametrize('pos', sorted(JA_NON_INFLECTING_POS))
def test_non_inflecting_ja_pos_gets_no_l4(pos):
    _ctx, levels, p3 = _plan(_core(pos))
    assert 4 not in p3                  # no morphology_slot request to the model
    assert 4 in levels                  # L4 itself stays: cloze_typed / particle_selection


def test_suru_noun_keeps_the_rest_of_the_ladder():
    _ctx, levels, p3 = _plan(_core('名詞'))
    assert {1, 2, 3, 6, 7, 9} <= set(levels)
    assert p3 == [7]                    # P3 still asks for L7 (ja L8 is disabled in the matrix)


@pytest.mark.parametrize('pos,semantic_class', [
    ('動詞', 'action'),
    ('形容詞', 'property'),
    ('形状詞', 'property'),   # na-adjectives take endings: deliberately kept
    ('形状詞', 'action'),
])
def test_inflecting_ja_pos_keeps_l4(pos, semantic_class):
    _ctx, levels, p3 = _plan(_core(pos, semantic_class))
    assert 4 in levels and 4 in p3


def test_missing_pos_is_planned_not_gated():
    """A sparse P1 asset has no evidence either way; the old plan stands."""
    ctx, _levels, p3 = _plan(_core(None))
    assert 'inflecting_pos' not in ctx
    assert 4 in p3


def test_other_languages_are_untouched():
    """The token lives on the ja row only: an English noun-labelled action word
    with forms still plans L4, whatever its pos string is."""
    ctx, _levels, p3 = _plan(_core('noun'), LANG_EN)
    assert 4 in p3
    _ctx, _levels, p3 = _plan(_core('名詞'), LANG_EN)
    assert 4 in p3


def test_pipeline_and_renderer_share_the_same_gate():
    core = _core('名詞')
    assert VocabAssetPipeline._capability_context(core) == capability_context_from_core(core)
    # The renderer's per-type suppression (render-time, for already-stored assets).
    assert type_is_available(
        'morphology_slot', LANG_JA, 'action', capability_context_from_core(core),
    ) is False
    assert type_is_available(
        'morphology_slot', LANG_JA, 'action', capability_context_from_core(_core('動詞')),
    ) is True


def test_p3_without_l4_validates_when_l4_is_not_planned():
    """The reported failure: the asset came back with no level_4 and was
    rejected. With L4 gated out of the plan the validator is held to the same
    list and no longer asks for it."""
    _ctx, levels, p3 = _plan(_core('名詞'))
    validator = VocabAssetValidator()
    content = {}                        # an asset that came back without level_4
    _ok, errors = validator.validate_prompt3(content, p3)
    assert 'Missing level_4' not in errors

    # Sanity: had L4 still been planned, that is exactly the message users saw.
    _ok, errors = validator.validate_prompt3(content, [4, 7])
    assert 'Missing level_4' in errors
