"""TASK-514/B5 (second half) — per-*type* gating of the Prompt-3 levels.

Level gating (``active_levels_for_context``, tested in
``test_matrix_gated_planning.py``) answers "can this word do L4 at all?".
It cannot answer "does *this prompt* own the capability keeping L4 alive",
and that distinction is where the bug lived: TASK-504 seeded ZH ``concrete``
with ``classifier_match`` + ``cloze_typed`` at L4, so the level survives — and
P3 kept asking Sonnet for Chinese morphology, which it duly invented.

The gate here is per type_code: P3 asks for ``morphology_slot`` only when an
enabled capability row for that type has its ``requires`` satisfied. Two sides
are covered because assets generated before the gate still exist:

  * generation — ``TransformAssetGenerator.generate`` never puts "4" in the
    request for a ZH concrete noun;
  * rendering  — ``LadderExerciseRenderer.build_rows`` never emits a
    ``morphology_slot`` row for one, even from a stale asset that has
    ``level_4`` content.

LLM-free and DB-free: the LLM boundary and the two asset loaders are stubbed.
"""

import json

from services.vocabulary_ladder import exercise_renderer as rendermod
from services.vocabulary_ladder.asset_generators import prompt3_transforms as p3mod
from services.vocabulary_ladder.config import (
    CAPABILITY_MATRIX,
    PROMPT3_TYPE_FOR_LEVEL,
    capability_context_from_core,
    compute_active_levels,
    enabled_capabilities,
    prompt3_levels_for_context,
    type_is_available,
)

LANG_ZH, LANG_EN, LANG_JA = 1, 2, 3


# ---------------------------------------------------------------------------
# Fixtures — a ZH concrete noun and an EN action verb, as P1 would emit them
# ---------------------------------------------------------------------------

ZH_CONCRETE_CORE = {
    'pos': '名词',
    'semantic_class': 'concrete',
    'definition': '书本；装订成册的印刷品',
    'primary_collocate': '',
    'pronunciation': 'shū',
    'morphological_forms': [],           # Chinese does not inflect
    'sentences': [
        {'text': f'我买了一本书，编号{i}。', 'target_word': '书',
         'source': 'generated', 'complexity_tier': 'T2'}
        for i in range(10)
    ],
}

EN_ACTION_CORE = {
    'pos': 'verb',
    'semantic_class': 'action',
    'definition': 'to move at speed on foot',
    'primary_collocate': 'quickly',
    'pronunciation': 'rʌn',
    'morphological_forms': [
        {'form': 'runs', 'label': '3sg'},
        {'form': 'ran', 'label': 'past'},
        {'form': 'running', 'label': 'gerund'},
    ],
    'sentences': [
        {'text': f'She had to run quickly to catch bus {i}.', 'target_word': 'run',
         'source': 'generated', 'complexity_tier': 'T2'}
        for i in range(10)
    ],
}


def _l4_types(language_id, semantic_class):
    return {
        cap['type_code']
        for cap in enabled_capabilities(language_id, semantic_class)
        if cap['ladder_level'] == 4
    }


# ---------------------------------------------------------------------------
# type_is_available
# ---------------------------------------------------------------------------

def test_morphology_slot_is_unavailable_for_chinese():
    """ZH's morphology_slot row is seeded but disabled — the gate must see that."""
    assert type_is_available('morphology_slot', LANG_ZH, 'concrete', {}) is False
    assert type_is_available('morphology_slot', LANG_ZH, 'abstract', {}) is False


def test_morphology_slot_is_available_for_an_inflecting_english_verb():
    ctx = capability_context_from_core(EN_ACTION_CORE)
    assert type_is_available('morphology_slot', LANG_EN, 'action', ctx) is True


def test_morphology_slot_drops_for_an_english_word_with_too_few_forms():
    """The level survives on cloze_typed; the *type* must not."""
    assert 'cloze_typed' in _l4_types(LANG_EN, 'action'), 'fixture assumption changed'
    ctx = {'morph_forms': 1}

    assert 4 in compute_active_levels('action', LANG_EN)
    assert type_is_available('morphology_slot', LANG_EN, 'action', ctx) is False


def test_unknown_semantic_class_stays_permissive():
    """Pre-backfill senses must not be gated to nothing."""
    assert type_is_available('morphology_slot', LANG_ZH, None, {}) is True
    assert type_is_available('morphology_slot', LANG_ZH, 'legacy_label', {}) is True


def test_unconfigured_language_stays_permissive():
    assert type_is_available('morphology_slot', 999, 'action', {'morph_forms': 0}) is True


# ---------------------------------------------------------------------------
# prompt3_levels_for_context
# ---------------------------------------------------------------------------

def test_zh_concrete_keeps_l4_as_a_level_but_loses_it_from_p3():
    """The headline assertion: same word, two different answers, both correct."""
    assert 4 in compute_active_levels('concrete', LANG_ZH)
    assert _l4_types(LANG_ZH, 'concrete'), 'ZH concrete should still have an L4 type'

    ctx = capability_context_from_core(ZH_CONCRETE_CORE)
    assert 4 not in prompt3_levels_for_context([4, 7, 8], 'concrete', LANG_ZH, ctx)


def test_p3_keeps_the_levels_it_does_own():
    ctx = capability_context_from_core(ZH_CONCRETE_CORE)
    levels = prompt3_levels_for_context([4, 7, 8], 'concrete', LANG_ZH, ctx)

    assert 7 in levels                       # spot_incorrect_sentence: ZH 'all'
    # L8 is collocation — dropped for `concrete` by the matrix, not by us.
    assert 8 not in compute_active_levels('concrete', LANG_ZH)


def test_english_action_verb_keeps_all_three_p3_levels():
    ctx = capability_context_from_core(EN_ACTION_CORE)
    assert prompt3_levels_for_context([4, 7, 8], 'action', LANG_EN, ctx) == [4, 7, 8]


def test_non_p3_levels_are_never_returned():
    ctx = capability_context_from_core(EN_ACTION_CORE)
    assert prompt3_levels_for_context(
        [1, 2, 3, 4, 5, 6, 7, 8, 9], 'action', LANG_EN, ctx) == [4, 7, 8]


def test_gate_is_narrowing_only():
    """A generous context can never add a level the caller did not plan."""
    generous = {'morph_forms': 99, 'pronunciation': True,
                'p1_definition': True, 'p1_sentences': True}
    for lang in (LANG_ZH, LANG_EN, LANG_JA):
        for sc in ('concrete', 'abstract', 'action', 'property', 'function'):
            planned = compute_active_levels(sc, lang)
            got = prompt3_levels_for_context(planned, sc, lang, generous)
            assert set(got) <= set(planned)


def test_every_p3_level_maps_to_a_real_matrix_type():
    """Guards the mapping against a typo silently disabling the gate."""
    known = {cap['type_code'] for cap in CAPABILITY_MATRIX}
    for level, type_code in PROMPT3_TYPE_FOR_LEVEL.items():
        assert type_code in known, f'L{level} maps to unknown type {type_code!r}'


# ---------------------------------------------------------------------------
# Generation side — the P3 *request*
# ---------------------------------------------------------------------------

_P3_TEMPLATE = (
    'word={word} class={semantic_class} levels={active_levels_json} '
    'sentences={sentences_json} morph={morphological_forms_json} '
    'l4idx={level_4_sentence_index} l7={level_7_correct_indices} '
    'l8idx={level_8_sentence_index} l8s={level_8_sentence_text} '
    'l8c={level_8_collocate_word} used={used_distractors_json} '
    'pos={pos} tier={complexity_tier} coll={primary_collocate} '
    'reg={register} fp={sense_fingerprint}'
)


class _Recorder:
    """Captures the prompt text P3 would send, and replies with a fixed body."""

    def __init__(self, reply):
        self.reply = reply
        self.prompts: list[str] = []

    def __call__(self, prompt_text, **kwargs):
        self.prompts.append(prompt_text)
        return self.reply


def _patch_p3(monkeypatch, reply):
    recorder = _Recorder(reply)
    monkeypatch.setattr(
        p3mod, 'get_template_config',
        lambda db, task_name, language_id: {
            'template': _P3_TEMPLATE, 'model': 'test-model',
            'provider': 'openrouter', 'version': 1,
        },
    )
    monkeypatch.setattr(p3mod, 'call_llm', recorder)
    return recorder


def _requested_levels(prompt_text):
    """Pull the active_levels list back out of the rendered prompt."""
    marker = 'levels='
    start = prompt_text.index(marker) + len(marker)
    end = prompt_text.index(']', start) + 1
    return json.loads(prompt_text[start:end])


def test_p3_request_for_a_zh_concrete_noun_omits_morphology(monkeypatch):
    """AC: 'ZH concrete noun's plan contains no morphology_slot'."""
    recorder = _patch_p3(monkeypatch, {'7': {'1': 'bad', '2': 'good', '3': 'why',
                                             '4': [0, 1, 2]}})
    gen = p3mod.TransformAssetGenerator(db=object(), language_id=LANG_ZH)

    result = gen.generate(
        sense_id=1,
        core_asset=ZH_CONCRETE_CORE,
        active_levels=compute_active_levels('concrete', LANG_ZH),
        semantic_class='concrete',
        capability_context=capability_context_from_core(ZH_CONCRETE_CORE),
    )

    assert recorder.prompts, 'P3 should still run for L7'
    assert _requested_levels(recorder.prompts[0]) == ['7']
    assert 'level_4' not in result


def test_gate_still_keeps_morphology_alive_for_an_english_verb(monkeypatch):
    """The gate must not be a blanket L4 kill-switch.

    Since TASK-520 the monolith no longer *asks* for L4 — the dedicated L4
    prompt does — so the surviving question is whether the shared per-type
    gate still says yes for an English action verb. It does; what changed is
    which prompt acts on that answer.
    """
    recorder = _patch_p3(monkeypatch, {'7': {'1': 'bad', '2': 'good', '3': 'why',
                                             '4': [0, 1, 2]}})
    gen = p3mod.TransformAssetGenerator(db=object(), language_id=LANG_EN)

    active_levels = compute_active_levels('action', LANG_EN)
    context = capability_context_from_core(EN_ACTION_CORE)

    result = gen.generate(
        sense_id=2,
        core_asset=EN_ACTION_CORE,
        active_levels=active_levels,
        semantic_class='action',
        capability_context=context,
    )

    assert 4 in prompt3_levels_for_context(active_levels, 'action', LANG_EN, context)
    assert _requested_levels(recorder.prompts[0]) == ['7']
    assert 'level_4' not in result, 'L4 comes from ladder_l4_morphology_generation now'


def test_omitting_semantic_class_preserves_legacy_behaviour(monkeypatch):
    """Callers that don't opt in (admin one-offs) skip the per-type gate.

    They still only get the levels this prompt owns: the ungated path bypasses
    the *semantic_class* narrowing, not the split.
    """
    recorder = _patch_p3(monkeypatch, {'7': {'1': 'a', '2': 'b', '3': 'c', '4': [0]}})
    gen = p3mod.TransformAssetGenerator(db=object(), language_id=LANG_ZH)

    gen.generate(sense_id=3, core_asset=ZH_CONCRETE_CORE, active_levels=[4, 7])

    assert _requested_levels(recorder.prompts[0]) == ['7']


def test_gate_that_empties_p3_short_circuits_without_calling_the_llm(monkeypatch):
    recorder = _patch_p3(monkeypatch, {})
    gen = p3mod.TransformAssetGenerator(db=object(), language_id=LANG_ZH)

    result = gen.generate(
        sense_id=4, core_asset=ZH_CONCRETE_CORE, active_levels=[4],
        semantic_class='concrete',
        capability_context=capability_context_from_core(ZH_CONCRETE_CORE),
    )

    assert result == {}
    assert recorder.prompts == [], 'no LLM spend when every level is gated out'


# ---------------------------------------------------------------------------
# Render side — the exercise rows
# ---------------------------------------------------------------------------

def _renderer_with(monkeypatch, core, p3_content):
    r = rendermod.LadderExerciseRenderer(db=object())
    monkeypatch.setattr(r, '_load_assets', lambda sense_id: {
        'prompt1_core': core,
        'prompt2_exercises_A': {},
        'prompt3_transforms_A': p3_content,
    })
    monkeypatch.setattr(r, '_load_asset_ids', lambda sense_id: {'prompt1_core': 'asset-1'})
    # Keep the ZH hant mirror out of the way — it is TASK-509's concern.
    monkeypatch.setattr(r, '_render_hant_mirror', lambda content, language_id: None)
    return r


# A stale asset: generated before the gate, so it carries invented ZH morphology.
_STALE_ZH_P3 = {
    'level_4': {
        'options': [{'text': '书们', 'is_correct': True},
                    {'text': '书子', 'is_correct': False},
                    {'text': '书儿', 'is_correct': False},
                    {'text': '书头', 'is_correct': False}],
        'correct_form': '书们',
        'base_form': '书',
        'form_label': '复数',
        'sentence_index': 1,
        'explanations': {'书们': '复数形式'},
    },
    'level_7': {
        'incorrect_sentence': '我买了一本书们。',
        'corrected_sentence': '我买了一本书。',
        'error_description': '量词错误',
        'correct_sentence_indices': [0, 1, 2],
    },
}


def test_stale_zh_morphology_asset_is_not_rendered(monkeypatch):
    """AC: the ZH concrete noun's *rendered output* contains no morphology_slot."""
    r = _renderer_with(monkeypatch, ZH_CONCRETE_CORE, _STALE_ZH_P3)

    rows = r.build_rows(sense_id=10, language_id=LANG_ZH)

    assert rows, 'other levels must still render'
    assert not [row for row in rows if row['exercise_type'] == 'morphology_slot']

    # L4 itself is *not* empty for a ZH concrete noun — the capability matrix
    # routes it to classifier_match / cloze_typed (TASK-528, TASK-532). What
    # must never appear is an L4 row produced by the P3 morphology path, so
    # assert on the generator rather than on the level going unused.
    for row in rows:
        if row['ladder_level'] == 4:
            assert row['tags'].get('generator') == 'deterministic', row['exercise_type']


def test_the_rest_of_the_zh_ladder_still_renders(monkeypatch):
    """The gate must remove one type, not quietly break the sense."""
    r = _renderer_with(monkeypatch, ZH_CONCRETE_CORE, _STALE_ZH_P3)

    rows = r.build_rows(sense_id=10, language_id=LANG_ZH)

    assert 'spot_incorrect_sentence' in {row['exercise_type'] for row in rows}


def test_english_morphology_still_renders(monkeypatch):
    en_p3 = {
        'level_4': {
            'options': [{'text': 'ran', 'is_correct': True},
                        {'text': 'runs', 'is_correct': False},
                        {'text': 'running', 'is_correct': False},
                        {'text': 'runned', 'is_correct': False}],
            'correct_form': 'ran', 'base_form': 'run', 'form_label': 'past',
            'sentence_index': 1, 'explanations': {},
        },
    }
    r = _renderer_with(monkeypatch, EN_ACTION_CORE, en_p3)

    rows = r.build_rows(sense_id=11, language_id=LANG_EN)

    assert 'morphology_slot' in {row['exercise_type'] for row in rows}


def test_legacy_semantic_class_label_is_normalised_by_the_gate(monkeypatch):
    """Assets predating the ratified enum still say 'concrete_noun'."""
    core = dict(ZH_CONCRETE_CORE, semantic_class='concrete_noun')
    r = _renderer_with(monkeypatch, core, _STALE_ZH_P3)

    rows = r.build_rows(sense_id=12, language_id=LANG_ZH)

    assert not [row for row in rows if row['exercise_type'] == 'morphology_slot']


def test_render_gate_is_a_no_op_when_there_is_nothing_to_suppress(monkeypatch):
    """An EN verb's row set must be unchanged by the gate being present."""
    r = _renderer_with(monkeypatch, EN_ACTION_CORE, {})
    before = {(row['exercise_type'], row['ladder_level'])
              for row in r.build_rows(sense_id=13, language_id=LANG_EN)}

    monkeypatch.setattr(rendermod, 'type_is_available', lambda *a, **k: True)
    after = {(row['exercise_type'], row['ladder_level'])
             for row in r.build_rows(sense_id=13, language_id=LANG_EN)}

    assert before == after
