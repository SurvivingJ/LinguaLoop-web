# tests/test_bundle_generator.py
"""BundleGenerator: one call, per-family validation, per-family fallback.

All LLM calls are mocked — no paid calls, per the Phase 2 brief. Fallback
paths are exercised by monkeypatching the EXISTING per-generator classes'
``generate`` methods (and ``typed_llm.generate_all``), not by letting them
reach a real ``call_llm`` — this isolates "does BundleGenerator call the
right fallback with the right args" from "does the fallback generator itself
work" (already covered by the pipeline's own tests).
"""

from __future__ import annotations

import services.vocabulary_ladder.bundle.generator as generator_mod
from services.vocabulary_ladder.asset_generators.l4_morphology import MorphologySlotGenerator
from services.vocabulary_ladder.asset_generators.l8_repair import CollocationRepairGenerator
from services.vocabulary_ladder.asset_generators.prompt2_exercises import ExerciseAssetGenerator
from services.vocabulary_ladder.asset_generators.prompt3_transforms import TransformAssetGenerator
from services.vocabulary_ladder.asset_generators import typed_llm
from services.vocabulary_ladder.bundle.generator import BundleGenerator

LANG_EN = 2

CORE_ASSET = {
    'pos': 'verb',
    'semantic_class': 'action',
    'definition': 'to move quickly on foot',
    'primary_collocate': 'fast',
    'register': 'neutral',
    'sense_fingerprint': 'run-move-quickly',
    'morphological_forms': [{'form': 'ran', 'label': 'past'}, {'form': 'running', 'label': 'gerund'}],
    'sentences': [
        {'text': f'Sentence number {i} about run.', 'target_word': 'run', 'complexity_tier': 'T3'}
        for i in range(10)
    ],
}

VARIANTS = {
    'A': {'sentence_assignments': {3: 0, 4: 1, 5: 2, 6: 3, 8: 4}, 'l7_correct_indices': [0, 1, 2]},
    'B': {'sentence_assignments': {3: 6, 4: 7, 5: 8, 6: 9, 8: 8}, 'l7_correct_indices': [6, 7, 9]},
}
L7_INDICES = {'A': [0, 1, 2], 'B': [6, 7, 9]}


def _p2_option(text, correct, explanation):
    return {'1': text, '2': correct, '3': explanation}


def _split_option(text, correct, explanation):
    return {'0': text, '1': correct, '2': explanation}


def _fake_cfg(monkeypatch):
    monkeypatch.setattr(
        generator_mod, 'get_template_config',
        lambda db, task_name, language_id: {
            'template': 'BUNDLE PROMPT (no placeholders needed for this test)',
            'model': 'qwen/qwen3.7-plus', 'provider': 'openrouter', 'version': 2,
        },
    )


def _valid_variant_block(l4_ok=True, typed_ok=True):
    block = {
        '3': [_p2_option('run', True, 'ok'), _p2_option('walk', False, 'x'),
              _p2_option('jog', False, 'x'), _p2_option('sprint', False, 'x')],
        '6': {'1': 3, '2': [
            {'1': 'He run fast.', '2': 'agreement'},
            {'1': 'He runned fast.', '2': 'wrong past form'},
            {'1': 'He is run fast.', '2': 'missing -ing'},
        ]},
        '7': {'1': 'She run every day.', '2': 'She runs every day.', '3': 'agreement', '4': [0, 1, 2]},
    }
    block['4'] = (
        {'0': [_split_option('ran', True, 'ok'), _split_option('run', False, 'x'),
               _split_option('running', False, 'x'), _split_option('runned', False, 'x')],
         '1': 'run', '2': 'past simple'}
        if l4_ok else
        {'0': [_split_option('ran', True, 'ok')] * 3, '1': 'run', '2': 'past simple'}  # only 3 options -> invalid
    )
    block['syn_ant'] = (
        {'0': [_split_option('sprint', True, 'ok'), _split_option('walk', False, 'x'),
               _split_option('sit', False, 'x'), _split_option('sleep', False, 'x')],
         '1': 'synonym'}
        if typed_ok else
        {'0': [_split_option('sprint', True, 'ok')] * 2, '1': 'synonym'}  # invalid: only 2 options
    )
    return block


def test_generate_bundle_full_success_no_fallbacks(monkeypatch):
    _fake_cfg(monkeypatch)
    raw = {'A': _valid_variant_block(), 'B': _valid_variant_block()}
    monkeypatch.setattr(generator_mod, 'call_llm', lambda *a, **k: raw)

    gen = BundleGenerator(db=object(), language_id=LANG_EN)
    result = gen.generate_bundle(
        sense_id=1, core_asset=CORE_ASSET, active_levels=[3, 4, 6, 7],
        semantic_class='action', capability_context={'morph_forms': 2},
        p3_expected_levels=[7], split_levels_wanted=[4],
        typed_wanted_codes={'synonym_antonym_match'},
        variants=VARIANTS, l7_correct_indices=L7_INDICES,
    )

    assert result.ok is True
    assert result.fallback_calls == []
    assert result.p2['A']['level_3']['correct_answer'] == 'run'
    assert result.p3['A']['level_7']['incorrect_sentence'] == 'She run every day.'
    assert result.l4['A']['level_4']['correct_form'] == 'ran'
    assert 'synonym_antonym_match' in result.typed['A'][0]
    assert result.typed['A'][1] == []  # no typed failures

    flat = result.to_variant_results()
    assert flat[('p2', 'A')]['level_3']['correct_answer'] == 'run'
    assert flat[('l4', 'B')]['level_4']['correct_form'] == 'ran'
    assert flat[('typed', 'A')][0]['synonym_antonym_match']['relation'] == 'synonym'


def test_bundle_call_total_failure_falls_back_every_family(monkeypatch):
    _fake_cfg(monkeypatch)

    def _always_fail(*a, **k):
        raise RuntimeError('simulated empty completion')
    monkeypatch.setattr(generator_mod, 'call_llm', _always_fail)

    monkeypatch.setattr(ExerciseAssetGenerator, 'generate', lambda self, *a, **k: {'level_3': {'fallback': True}})
    monkeypatch.setattr(TransformAssetGenerator, 'generate', lambda self, *a, **k: {'level_7': {'fallback': True}})
    monkeypatch.setattr(MorphologySlotGenerator, 'generate', lambda self, *a, **k: {'level_4': {'fallback': True}})
    monkeypatch.setattr(
        typed_llm, 'generate_all',
        lambda *a, **k: ({'synonym_antonym_match': {'fallback': True}}, []),
    )

    gen = BundleGenerator(db=object(), language_id=LANG_EN)
    result = gen.generate_bundle(
        sense_id=1, core_asset=CORE_ASSET, active_levels=[3, 4, 6, 7],
        semantic_class='action', capability_context={'morph_forms': 2},
        p3_expected_levels=[7], split_levels_wanted=[4],
        typed_wanted_codes={'synonym_antonym_match'},
        variants=VARIANTS, l7_correct_indices=L7_INDICES,
    )

    assert result.ok is False
    assert result.p2['A'] == {'level_3': {'fallback': True}}
    assert result.p3['A'] == {'level_7': {'fallback': True}}
    assert result.l4['A'] == {'level_4': {'fallback': True}}
    assert result.typed['A'][0] == {'synonym_antonym_match': {'fallback': True}}
    for expected in ('p2:A', 'p2:B', 'l7:A', 'l7:B', 'l4:A', 'l4:B'):
        assert expected in result.fallback_calls


def test_partial_failure_falls_back_only_for_the_bad_family(monkeypatch):
    _fake_cfg(monkeypatch)
    # Variant A: L4 and syn_ant are schema-invalid; everything else valid.
    raw = {
        'A': _valid_variant_block(l4_ok=False, typed_ok=False),
        'B': _valid_variant_block(),
    }
    monkeypatch.setattr(generator_mod, 'call_llm', lambda *a, **k: raw)
    monkeypatch.setattr(
        MorphologySlotGenerator, 'generate',
        lambda self, *a, **k: {'level_4': {'correct_form': 'FALLBACK'}},
    )
    monkeypatch.setattr(
        typed_llm, 'generate_all',
        lambda *a, **k: ({'synonym_antonym_match': {'correct_answer': 'FALLBACK'}}, []),
    )

    gen = BundleGenerator(db=object(), language_id=LANG_EN)
    result = gen.generate_bundle(
        sense_id=1, core_asset=CORE_ASSET, active_levels=[3, 4, 6, 7],
        semantic_class='action', capability_context={'morph_forms': 2},
        p3_expected_levels=[7], split_levels_wanted=[4],
        typed_wanted_codes={'synonym_antonym_match'},
        variants=VARIANTS, l7_correct_indices=L7_INDICES,
    )

    # Variant A: L4/syn_ant used the fallback; L3/L7 used the bundle mapping.
    assert result.l4['A']['level_4']['correct_form'] == 'FALLBACK'
    assert result.typed['A'][0]['synonym_antonym_match']['correct_answer'] == 'FALLBACK'
    assert result.p2['A']['level_3']['correct_answer'] == 'run'
    assert result.p3['A']['level_7']['incorrect_sentence'] == 'She run every day.'
    assert 'l4:A' in result.fallback_calls
    assert any(c.startswith('typed:synonym_antonym_match:A') for c in result.fallback_calls)

    # Variant B: everything came from the bundle, no fallback needed.
    assert result.l4['B']['level_4']['correct_form'] == 'ran'
    assert 'l4:B' not in result.fallback_calls


def test_not_requested_families_are_clean_skips_not_fallbacks(monkeypatch):
    _fake_cfg(monkeypatch)
    raw = {'A': {'3': _valid_variant_block()['3']}, 'B': {'3': _valid_variant_block()['3']}}
    monkeypatch.setattr(generator_mod, 'call_llm', lambda *a, **k: raw)

    gen = BundleGenerator(db=object(), language_id=LANG_EN)
    result = gen.generate_bundle(
        sense_id=1, core_asset=CORE_ASSET, active_levels=[3],
        semantic_class='action', capability_context={},
        p3_expected_levels=[], split_levels_wanted=[],
        typed_wanted_codes=set(),
        variants=VARIANTS, l7_correct_indices=L7_INDICES,
    )
    assert result.ok is True
    assert result.fallback_calls == []
    assert result.p3['A'] == {}
    assert result.l4['A'] == {}
    assert result.l8['A'] == {}
    assert result.typed['A'] == ({}, [])
