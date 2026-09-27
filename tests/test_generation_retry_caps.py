"""TASK-810 — cap retries at <=2 real calls/step; remove the P3 salvage call.

Two independent retry layers used to stack: each generator's own 2-attempt
outer loop, plus `call_llm`'s internal JSON-repair turn firing on top of
EVERY attempt (a single bad completion could cost up to 4 real calls before
P3's salvage call -- a 5th -- even engaged). This file pins:

  1. `call_llm(..., allow_internal_repair=False)` re-raises a malformed-JSON /
     empty-response failure immediately instead of running `_repair_malformed_json`.
  2. `CoreAssetGenerator` (prompt1_core) still caps at exactly 2 real calls
     under forced failure, and passes `allow_internal_repair=False` so those
     2 calls are exactly 2, not up to 4.
  3. `TransformAssetGenerator` (prompt3_transforms) no longer has a salvage
     call at all -- a repeated failure costs exactly 2 calls and returns None,
     and `_salvage_from_text` no longer exists on the class.

LLM-free throughout: `call_llm` is stubbed at the module boundary each
generator actually imports it through, same pattern as
tests/test_prompt_split_l4_l8.py and tests/test_p3_type_gating.py.
"""

import json

import pytest

import services.llm_service as svc
from services.vocabulary_ladder.asset_generators import prompt1_core as p1mod
from services.vocabulary_ladder.asset_generators import prompt3_transforms as p3mod


# ---------------------------------------------------------------------------
# 1. call_llm(allow_internal_repair=False) re-raises instead of repairing
# ---------------------------------------------------------------------------

def test_call_llm_allow_internal_repair_false_reraises_on_bad_json(monkeypatch):
    def _boom(**kwargs):
        raise json.JSONDecodeError('bad json', 'doc', 0)

    repair_calls = []
    monkeypatch.setattr(svc, '_make_one_call', _boom)
    monkeypatch.setattr(
        svc, '_repair_malformed_json',
        lambda **kw: repair_calls.append(kw) or {'ok': True},
    )
    monkeypatch.setattr(svc, 'get_client', lambda *a, **kw: object())

    with pytest.raises(json.JSONDecodeError):
        svc.call_llm(
            'prompt', model='m', response_format='json_object',
            provider='openrouter', task_name='unit_probe', pipeline='diagnostics',
            allow_internal_repair=False,
        )

    assert repair_calls == [], '_repair_malformed_json must not fire when disabled'


def test_call_llm_allow_internal_repair_true_still_repairs(monkeypatch):
    """Default behaviour (no caller opt-out) is unchanged."""
    def _boom(**kwargs):
        raise json.JSONDecodeError('bad json', 'doc', 0)

    repair_calls = []
    monkeypatch.setattr(svc, '_make_one_call', _boom)
    monkeypatch.setattr(
        svc, '_repair_malformed_json',
        lambda **kw: repair_calls.append(kw) or {'ok': True},
    )
    monkeypatch.setattr(svc, 'get_client', lambda *a, **kw: object())

    result = svc.call_llm(
        'prompt', model='m', response_format='json_object',
        provider='openrouter', task_name='unit_probe', pipeline='diagnostics',
    )

    assert result == {'ok': True}
    assert len(repair_calls) == 1


# ---------------------------------------------------------------------------
# 2. prompt1_core caps at exactly 2 real calls under forced failure
# ---------------------------------------------------------------------------

_P1_TEMPLATE = (
    '{word} {existing_definition} {sense_id} {sense_definition} '
    '{complexity_tier} {corpus_sentences_json} {sentences_needed}'
)


def _stub_p1(monkeypatch, side_effect):
    calls = []

    def _call(prompt, **kwargs):
        calls.append(kwargs)
        return side_effect(len(calls))

    monkeypatch.setattr(p1mod, 'call_llm', _call)
    monkeypatch.setattr(
        p1mod, 'get_template_config',
        lambda db, task_name, language_id: {
            'template': _P1_TEMPLATE, 'model': 'm',
            'provider': 'openrouter', 'version': 1,
        },
    )
    return calls


def test_prompt1_core_caps_at_two_calls_on_repeated_failure(monkeypatch):
    def _always_raise(_n):
        raise RuntimeError('provider down')

    calls = _stub_p1(monkeypatch, _always_raise)
    gen = p1mod.CoreAssetGenerator(db=object(), language_id=2)
    monkeypatch.setattr(gen, '_load_word_data', lambda sense_id: {
        'sense_id': sense_id, 'lemma': 'run', 'pos': 'verb',
        'definition': 'to move fast', 'pronunciation': '', 'complexity_tier': 'T2',
    })

    result = gen.generate(sense_id=1, corpus_sentences=[])

    assert result is None
    assert len(calls) == 2, 'must give up after exactly 2 attempts, not loop or salvage'
    assert all(c.get('allow_internal_repair') is False for c in calls), (
        'each attempt must disable the internal repair turn so a single bad '
        'completion cannot cost more than 1 real call'
    )
    assert calls[0]['call_role'] == 'primary'
    assert calls[1]['call_role'] == 'retry'


def test_prompt1_core_recovers_on_the_second_attempt(monkeypatch):
    good = {'1': 'noun', '9': 1}

    def _fail_then_succeed(n):
        if n == 1:
            raise RuntimeError('transient')
        return good

    calls = _stub_p1(monkeypatch, _fail_then_succeed)
    gen = p1mod.CoreAssetGenerator(db=object(), language_id=2)
    monkeypatch.setattr(gen, '_load_word_data', lambda sense_id: {
        'sense_id': sense_id, 'lemma': 'run', 'pos': 'verb',
        'definition': 'to move fast', 'pronunciation': '', 'complexity_tier': 'T2',
    })
    monkeypatch.setattr(gen, '_remap_output', lambda raw: {'pos': raw.get('1')})

    result = gen.generate(sense_id=1, corpus_sentences=[])

    assert result is not None
    assert len(calls) == 2


# ---------------------------------------------------------------------------
# 3. prompt3_transforms: the salvage call is gone
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

_P3_CORE = {
    'pos': 'verb', 'semantic_class': 'action', 'definition': 'to move fast',
    'primary_collocate': '', 'register': 'neutral', 'sense_fingerprint': 'speed',
    'morphological_forms': [],
    'sentences': [
        {'text': f'Sentence {i} about running.', 'target_word': 'run',
         'complexity_tier': 'T2'}
        for i in range(10)
    ],
}


def _stub_p3(monkeypatch, side_effect):
    calls = []

    def _call(prompt, **kwargs):
        calls.append(kwargs)
        return side_effect(len(calls))

    monkeypatch.setattr(p3mod, 'call_llm', _call)
    monkeypatch.setattr(
        p3mod, 'get_template_config',
        lambda db, task_name, language_id: {
            'template': _P3_TEMPLATE, 'model': 'm',
            'provider': 'openrouter', 'version': 1,
        },
    )
    return calls


def test_prompt3_salvage_never_fires(monkeypatch):
    """A repeated total failure costs exactly 2 calls and returns None --
    no third 'text' mode salvage call, and no `call_role='salvage'` row."""

    def _always_raise(_n):
        raise RuntimeError('provider down')

    calls = _stub_p3(monkeypatch, _always_raise)
    gen = p3mod.TransformAssetGenerator(db=object(), language_id=2)

    result = gen.generate(sense_id=1, core_asset=_P3_CORE, active_levels=[7])

    assert result is None
    assert len(calls) == 2, 'no salvage call: exactly 2 attempts, then give up'
    assert not any(c.get('call_role') == 'salvage' for c in calls)
    assert all(c.get('allow_internal_repair') is False for c in calls)


def test_salvage_from_text_no_longer_exists():
    assert not hasattr(p3mod.TransformAssetGenerator, '_salvage_from_text')


def test_prompt3_still_accepts_a_partial_response_on_the_retry(monkeypatch):
    """Parity guard: the 'accept partial after retry' branch is unchanged by
    the salvage removal -- a still-missing level on attempt 2 returns the
    partial dict rather than None."""

    def _missing_then_missing(_n):
        return {}  # never includes level 7

    calls = _stub_p3(monkeypatch, _missing_then_missing)
    gen = p3mod.TransformAssetGenerator(db=object(), language_id=2)

    result = gen.generate(sense_id=1, core_asset=_P3_CORE, active_levels=[7])

    assert len(calls) == 2
    assert result == {}, 'accepted partial (empty) output, not None'
