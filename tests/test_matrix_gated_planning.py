"""TASK-514/B5 — matrix-gated L4 planning.

Before this, ``active_levels`` came straight from ``compute_active_levels`` and
L4 was planned for every word regardless of language. The pipeline then relied
on the model returning null morphology for languages that have none. It does
not reliably do that: ZH words came back with invented "inflections", which
rendered as morphology_slot exercises for a language without inflection.

The gate is now the capability matrix's own ``requires`` column
(``morph_forms>=2``), evaluated against what P1 actually produced.
"""

import pytest

from services.vocabulary_ladder.asset_pipeline import VocabAssetPipeline
from services.vocabulary_ladder.config import (
    CAPABILITY_MATRIX,
    active_levels_for_context,
    compute_active_levels,
    enabled_capabilities,
    requirements_met,
)

LANG_ZH, LANG_EN, LANG_JA = 1, 2, 3


# ---------------------------------------------------------------------------
# requirements_met
# ---------------------------------------------------------------------------

def test_threshold_requirement_blocks_below_the_bar():
    assert requirements_met(('morph_forms>=2',), {'morph_forms': 2}) is True
    assert requirements_met(('morph_forms>=2',), {'morph_forms': 1}) is False
    assert requirements_met(('morph_forms>=2',), {'morph_forms': 0}) is False


def test_presence_requirement_blocks_when_falsy():
    assert requirements_met(('pronunciation',), {'pronunciation': True}) is True
    assert requirements_met(('pronunciation',), {'pronunciation': False}) is False


def test_unknown_requirements_are_treated_as_satisfied():
    """Planning must not drop a level over something only the renderer can see."""
    assert requirements_met(('tts', 'same_tier_senses'), {}) is True
    assert requirements_met(('morph_forms>=2',), {}) is True


def test_empty_requirements_are_satisfied():
    assert requirements_met((), {'morph_forms': 0}) is True
    assert requirements_met(None, {}) is True


def test_non_numeric_context_value_fails_a_threshold():
    assert requirements_met(('morph_forms>=2',), {'morph_forms': 'lots'}) is False


# ---------------------------------------------------------------------------
# active_levels_for_context
# ---------------------------------------------------------------------------

def test_empty_context_is_identical_to_compute_active_levels():
    for lang in (LANG_ZH, LANG_EN, LANG_JA):
        for sc in ('concrete', 'abstract', 'action', 'property'):
            assert (active_levels_for_context(sc, lang, {})
                    == compute_active_levels(sc, lang))
            assert (active_levels_for_context(sc, lang, None)
                    == compute_active_levels(sc, lang))


def _l4_types(language_id, semantic_class):
    return {
        cap['type_code']
        for cap in enabled_capabilities(language_id, semantic_class)
        if cap['ladder_level'] == 4
    }


def test_zh_concrete_noun_drops_l4_without_morphological_forms():
    """The headline case: ZH has no inflection, so L4 morphology can't fire.

    Guarded — if a ZH-concrete L4 capability that does NOT need morphology is
    added later (classifier_match, TASK-528), L4 legitimately stays and this
    assertion should be updated rather than silently passing.
    """
    l4 = _l4_types(LANG_ZH, 'concrete')
    if l4 - {'morphology_slot'}:
        pytest.skip(f'ZH concrete now has a non-morphology L4 capability: {l4}')

    assert 4 in compute_active_levels('concrete', LANG_ZH)

    levels = active_levels_for_context('concrete', LANG_ZH, {'morph_forms': 0})

    assert 4 not in levels
    # Nothing else is disturbed.
    assert [lv for lv in compute_active_levels('concrete', LANG_ZH)
            if lv != 4] == levels


def test_l4_survives_when_the_word_has_enough_forms():
    levels = active_levels_for_context('action', LANG_EN, {'morph_forms': 4})
    assert 4 in levels


def test_a_level_survives_while_any_of_its_capabilities_can_fire():
    """Level gating is per-level, not per-type — by design.

    EN 'action' L4 is served by morphology_slot, word_family (both
    ``morph_forms>=2``) and cloze_typed (``cloze_asset``). A one-form word
    kills the first two, but cloze_typed can still carry L4, so the level
    stays. Dropping it would silently remove a level the word *can* do.

    Per-*type* gating — not asking P3 for morphology on such a word — is the
    other half of TASK-514/B5 and lives in ``test_p3_type_gating.py``.
    """
    l4_types = _l4_types(LANG_EN, 'action')
    assert 'cloze_typed' in l4_types, 'fixture assumption changed'

    levels = active_levels_for_context('action', LANG_EN, {'morph_forms': 1})
    assert 4 in levels


def test_level_drops_only_when_every_capability_for_it_fails():
    """With all of L4's requirements unmet, the level does drop."""
    ctx = {'morph_forms': 1, 'cloze_asset': False}

    assert 4 not in active_levels_for_context('action', LANG_EN, ctx)


def test_context_never_adds_a_level_the_matrix_excluded():
    """Narrowing only. A generous context can't resurrect an excluded level."""
    generous = {'morph_forms': 99, 'pronunciation': True,
                'p1_definition': True, 'p1_sentences': True}
    for lang in (LANG_ZH, LANG_EN, LANG_JA):
        for sc in ('concrete', 'abstract', 'action', 'property', 'function'):
            base = set(compute_active_levels(sc, lang))
            assert set(active_levels_for_context(sc, lang, generous)) <= base


def test_unclassified_semantic_class_stays_permissive():
    """Pre-backfill senses keep the full ladder rather than being gated to nothing."""
    assert (active_levels_for_context(None, LANG_ZH, {'morph_forms': 0})
            == compute_active_levels(None, LANG_ZH))


# ---------------------------------------------------------------------------
# _capability_context — what the pipeline feeds the gate
# ---------------------------------------------------------------------------

def test_capability_context_counts_morphological_forms():
    ctx = VocabAssetPipeline._capability_context({
        'semantic_class': 'action',
        'morphological_forms': ['run', 'ran', 'running'],
        'pronunciation': '', 'definition': 'to move fast', 'sentences': ['a'],
    })

    assert ctx['morph_forms'] == 3
    assert ctx['p1_definition'] is True
    assert ctx['p1_sentences'] is True
    assert ctx['pronunciation'] is False


def test_capability_context_handles_missing_and_null_fields():
    """A sparse P1 asset must not raise — it must gate."""
    assert VocabAssetPipeline._capability_context({})['morph_forms'] == 0
    assert VocabAssetPipeline._capability_context(
        {'morphological_forms': None})['morph_forms'] == 0


def test_zh_concrete_pipeline_context_end_to_end():
    """A realistic ZH concrete-noun P1 asset yields a plan without L4."""
    if _l4_types(LANG_ZH, 'concrete') - {'morphology_slot'}:
        pytest.skip('ZH concrete has a non-morphology L4 capability')

    core_asset = {
        'semantic_class': 'concrete',
        'morphological_forms': [],           # ZH: no inflection
        'pronunciation': 'shū',
        'definition': 'book',
        'sentences': ['我买了一本书。'],
    }

    levels = active_levels_for_context(
        'concrete', LANG_ZH, VocabAssetPipeline._capability_context(core_asset),
    )

    assert 4 not in levels, 'ZH concrete noun must not be planned for morphology'
    assert 1 in levels and 2 in levels        # the rest of the ladder is intact


def test_every_matrix_requires_token_is_parseable():
    """Guards the token grammar: a typo'd requirement must not silently pass."""
    for cap in CAPABILITY_MATRIX:
        for token in cap['requires']:
            assert token and isinstance(token, str)
            if '>=' in token:
                name, _, threshold = token.partition('>=')
                assert name.strip(), f'empty name in {token!r}'
                float(threshold)             # raises if not numeric
