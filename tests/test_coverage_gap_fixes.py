"""Coverage-gap diagnosis fixes (ADR-028, wiki/evaluations/exercise-gen-phase1-2026-09.md §14).

Items 5 and 6 specifically — the two fixes that don't fit naturally into an
existing test module:

  5. Bundle typed-dispatch must fall back (not silently clean-skip) when the
     bundle call succeeds but omits a key the capability gate says is wanted
     — `BundleGenerator._resolve_l4`/`_resolve_l8`/`_resolve_typed`.
  6. A non-int sentence index surviving P2/P3 remap (`_remap_level_6` /
     `_remap_level_7`) must be coerced, and a bundle-judge gather/call
     failure must never sink the whole `build_rows` call for a sense.

Items 1-4 and 7 are covered in tests/test_generation_retry_caps.py,
tests/test_prompt_split_l4_l8.py, tests/test_asset_pipeline_p1_gate.py,
tests/test_vocab_ladder_validators.py, and tests/test_deterministic_generators.py.

LLM-free throughout.
"""

from __future__ import annotations

import services.vocabulary_ladder.bundle.generator as generator_mod
from services.vocabulary_ladder.asset_generators.l4_morphology import MorphologySlotGenerator
from services.vocabulary_ladder.asset_generators.l8_repair import CollocationRepairGenerator
from services.vocabulary_ladder.asset_generators import prompt2_exercises as p2mod
from services.vocabulary_ladder.asset_generators import prompt3_transforms as p3mod
from services.vocabulary_ladder.asset_generators import typed_llm
from services.vocabulary_ladder.bundle.generator import BundleGenerator
import services.vocabulary_ladder.exercise_renderer as renderer_mod
from services.vocabulary_ladder.exercise_renderer import LadderExerciseRenderer

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


# ---------------------------------------------------------------------------
# Item 5 — bundle typed-dispatch: an outright-missing wanted key must fall
# back, not read as a clean skip identical to the model's own "9" decline.
# ---------------------------------------------------------------------------

def test_typed_section_silently_omitted_by_bundle_falls_back(monkeypatch):
    """Regression for ja sense 34998: synonym_antonym_match was applicable
    (the capability gate wanted it) but the bundle response simply didn't
    include a "syn_ant" key for one variant -- no "9" escape, just absent.
    That must trigger the real per-type fallback call, matching what the
    legacy per-generator loop would have produced, not a silent loss."""
    _fake_cfg(monkeypatch)
    block_with_syn_ant = {
        '3': [_p2_option('run', True, 'ok'), _p2_option('walk', False, 'x'),
              _p2_option('jog', False, 'x'), _p2_option('sprint', False, 'x')],
        'syn_ant': {'0': [_split_option('sprint', True, 'ok'), _split_option('walk', False, 'x'),
                          _split_option('sit', False, 'x'), _split_option('sleep', False, 'x')],
                    '1': 'synonym'},
    }
    block_without_syn_ant = {k: v for k, v in block_with_syn_ant.items() if k != 'syn_ant'}
    raw = {'A': block_without_syn_ant, 'B': block_with_syn_ant}
    monkeypatch.setattr(generator_mod, 'call_llm', lambda *a, **k: raw)

    fallback_calls = []

    def _fake_generate_all(db, language_id, sense_id, core_asset, semantic_class,
                            sentence_assignments, capability_context, type_codes=None):
        fallback_calls.append(set(type_codes or set()))
        return {'synonym_antonym_match': {'correct_answer': 'FALLBACK'}}, []

    monkeypatch.setattr(typed_llm, 'generate_all', _fake_generate_all)

    gen = BundleGenerator(db=object(), language_id=LANG_EN)
    result = gen.generate_bundle(
        sense_id=1, core_asset=CORE_ASSET, active_levels=[3],
        semantic_class='action', capability_context={'morph_forms': 2},
        p3_expected_levels=[], split_levels_wanted=[],
        typed_wanted_codes={'synonym_antonym_match'},
        variants=VARIANTS, l7_correct_indices=L7_INDICES,
    )

    # Variant A silently omitted the key -> must have fallen back.
    assert fallback_calls == [{'synonym_antonym_match'}]
    assert result.typed['A'][0]['synonym_antonym_match']['correct_answer'] == 'FALLBACK'
    assert any(c.startswith('typed:synonym_antonym_match:A') for c in result.fallback_calls)
    # Variant B had the key -> no fallback needed for it.
    assert result.typed['B'][0]['synonym_antonym_match']['relation'] == 'synonym'


def test_l4_section_silently_omitted_by_bundle_falls_back(monkeypatch):
    _fake_cfg(monkeypatch)
    raw = {
        'A': {'3': [_p2_option('run', True, 'ok'), _p2_option('walk', False, 'x'),
                    _p2_option('jog', False, 'x'), _p2_option('sprint', False, 'x')]},
        'B': {'3': [_p2_option('run', True, 'ok'), _p2_option('walk', False, 'x'),
                    _p2_option('jog', False, 'x'), _p2_option('sprint', False, 'x')]},
    }
    monkeypatch.setattr(generator_mod, 'call_llm', lambda *a, **k: raw)
    monkeypatch.setattr(
        MorphologySlotGenerator, 'generate',
        lambda self, *a, **k: {'level_4': {'correct_form': 'FALLBACK'}},
    )

    gen = BundleGenerator(db=object(), language_id=LANG_EN)
    result = gen.generate_bundle(
        sense_id=1, core_asset=CORE_ASSET, active_levels=[3],
        semantic_class='action', capability_context={'morph_forms': 2},
        p3_expected_levels=[], split_levels_wanted=[4],
        typed_wanted_codes=set(),
        variants=VARIANTS, l7_correct_indices=L7_INDICES,
    )

    assert result.l4['A']['level_4']['correct_form'] == 'FALLBACK'
    assert 'l4:A' in result.fallback_calls


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


# ---------------------------------------------------------------------------
# Item 6 — a bundle-judge gather/call failure must not sink the whole render.
# ---------------------------------------------------------------------------

def test_bundle_judge_gather_failure_is_caught_and_recorded_not_fatal(monkeypatch):
    """Regression for en senses 13900/13902 (phase2_smoke_en): a non-int
    sentence index reaching `_gather_bundle_judge_requests` raised a
    TypeError that propagated out of `build_rows` entirely, producing ZERO
    rows with no error/skip recorded anywhere. The gather/call is now
    wrapped: a failure logs, records a Skip, and lets the per-level direct
    judge calls run instead (exactly what `_bundle_judge_result = None`
    already means for every judged call site)."""
    renderer = LadderExerciseRenderer(db=object())

    monkeypatch.setattr(renderer, '_load_assets', lambda sid: {'prompt1_core': CORE_ASSET})
    monkeypatch.setattr(renderer, '_load_asset_ids', lambda sid: {'prompt1_core': 'asset-1'})
    monkeypatch.setattr(renderer, '_get_tier', lambda core: 'T3')
    monkeypatch.setattr(renderer, '_render_deterministic', lambda **kw: [])
    monkeypatch.setattr(renderer, '_render_llm_types', lambda **kw: [])
    monkeypatch.setattr(renderer_mod, 'compute_active_levels', lambda *a, **k: [])
    monkeypatch.setattr(renderer_mod, 'bundle_enabled', lambda: True)

    def _boom(*a, **k):
        raise TypeError("'<' not supported between instances of 'str' and 'int'")

    monkeypatch.setattr(renderer, '_gather_bundle_judge_requests', _boom)

    rows = renderer.build_rows(sense_id=1, language_id=LANG_EN)

    assert rows == []  # no levels requested in this stripped-down fixture
    assert renderer._bundle_judge_result is None
    assert any(s.type_code == 'bundle_judge' for s in renderer.last_skips), (
        'the gather failure must be recorded as a skip, not silently dropped'
    )
