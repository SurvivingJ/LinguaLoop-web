"""TASK-520 — L4 + L8 peeled out of the P3 monolith.

LLM-free: every test stubs the generators' ``get_template_config`` /
``call_llm`` boundary. Nothing here touches Supabase or OpenRouter.

Four groups:

  1. **Schema gate** — the accepted shape is accepted, each way of breaking it
     is reported, and an unregistered prompt_version is refused rather than
     silently validated against the wrong schema.
  2. **Split generators** — a schema-valid response remaps into the level dict
     the renderer already reads; a broken one is retried once and then gives
     up; a sense that cannot support the level is a clean skip, not an error.
  3. **Isolation** — the whole point of the split. A failing L4 must not cost
     L8 a call, and the two must not share a model.
  4. **Monolith narrowing** — P3 no longer asks for 4 or 8.
"""

import json

import pytest

from services.exercise_generation.schemas import (
    SchemaError, ladder_schema, validate_ladder_output,
)
from services.vocabulary_ladder.asset_generators import l4_morphology, l8_repair
from services.vocabulary_ladder.asset_generators import prompt3_transforms as p3mod
from services.vocabulary_ladder.asset_generators.l4_morphology import MorphologySlotGenerator
from services.vocabulary_ladder.asset_generators.l8_repair import CollocationRepairGenerator
from services.vocabulary_ladder.config import (
    PROMPT3_LEVELS, PROMPT3_MONOLITH_LEVELS, SPLIT_LEVEL_TASKS,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

# The prompts return numeric keys (TASK-537): 0=options, 9=error escape, and
# within an option 0=text, 1=is_correct, 2=explanation. Tests still name their
# overrides in domain terms and the helpers translate, so a test reads as a
# statement about morphology rather than about indices.
_L4_KEYS = {'options': '0', 'base_form': '1', 'form_label': '2',
            'sentence_index': '3'}
_L8_KEYS = {'options': '0', 'error_collocate': '1'}


def _opt(text, correct, explanation='wrong form'):
    """One option object in the indexed shape."""
    return {'0': text, '1': correct, '2': explanation}


def _options(correct='ran', wrong=('run', 'running', 'runs')):
    opts = [_opt(correct, True, 'past simple')]
    opts += [_opt(w, False) for w in wrong]
    return opts


def _indexed(defaults, key_map, overrides):
    payload = dict(defaults)
    for name, value in overrides.items():
        payload[key_map[name]] = value
    return payload


def _l4_payload(**overrides):
    return _indexed(
        {'0': _options(), '1': 'run', '2': 'past simple'}, _L4_KEYS, overrides,
    )


def _l8_payload(**overrides):
    return _indexed(
        {'0': _options('brew', ('cook', 'build', 'prepare')),
         '1': 'manufacture'},
        _L8_KEYS, overrides,
    )


def _named_l4_payload():
    """The pre-TASK-537 shape, for the "old contract is rejected" tests."""
    return {
        'options': [
            {'text': 'ran', 'is_correct': True, 'explanation': 'past simple'},
            {'text': 'run', 'is_correct': False, 'explanation': 'wrong form'},
            {'text': 'running', 'is_correct': False, 'explanation': 'wrong form'},
            {'text': 'runs', 'is_correct': False, 'explanation': 'wrong form'},
        ],
        'base_form': 'run',
        'form_label': 'past simple',
    }


def _core(sentences=None, forms=2, collocate='brew'):
    if sentences is None:
        sentences = [
            {'text': f'Sentence {i} about coffee.', 'target_word': 'coffee',
             'complexity_tier': 'T2'}
            for i in range(6)
        ]
    return {
        'pos': 'noun',
        'semantic_class': 'concrete',
        'definition': 'a hot drink',
        'register': 'neutral',
        'sense_fingerprint': 'beverage',
        'primary_collocate': collocate,
        'morphological_forms': [{'form': f'f{i}', 'label': f'l{i}'} for i in range(forms)],
        'sentences': sentences,
    }


def _stub(monkeypatch, module, responses, template='{word}|{sentence_text}', version=1):
    """Point a generator module at a fake template and a scripted LLM.

    ``responses`` is consumed one entry per call; an entry that is an
    Exception instance is raised instead of returned, which is how the call
    failure paths are driven.
    """
    calls = []

    monkeypatch.setattr(
        module, 'get_template_config',
        lambda db, task_name, language_id: {
            'template': template, 'model': f'model-for-{task_name}',
            'provider': 'openrouter', 'version': version,
        },
    )

    queue = list(responses)

    def _call(prompt, **kwargs):
        calls.append({'prompt': prompt, **kwargs})
        if not queue:
            raise AssertionError('call_llm called more times than scripted')
        nxt = queue.pop(0)
        if isinstance(nxt, Exception):
            raise nxt
        return nxt

    monkeypatch.setattr(module, 'call_llm', _call)
    return calls


@pytest.fixture
def split_base(monkeypatch):
    """The generators call through _split_base, so that is where to patch."""
    from services.vocabulary_ladder.asset_generators import _split_base
    return _split_base


# ---------------------------------------------------------------------------
# 1. Schema gate
# ---------------------------------------------------------------------------

def test_l4_accepted_shape_validates():
    assert validate_ladder_output('morphology_slot', 1, _l4_payload()) == []


def test_l8_accepted_shape_validates():
    assert validate_ladder_output('collocation_repair', 1, _l8_payload()) == []


@pytest.mark.parametrize('payload, needle', [
    (_l4_payload(options=_options()[:3]), 'expected 4 entries'),
    (_l4_payload(base_form=''), 'base_form'),
    (_l4_payload(form_label=None), 'form_label'),
    (_l4_payload(options=[
        _opt('a', True, 'x'), _opt('b', True, 'x'),
        _opt('c', False, 'x'), _opt('d', False, 'x'),
    ]), 'exactly 1 correct'),
    (_l4_payload(options=[
        {'0': 'a', '1': True},                      # explanation (key 2) missing
        _opt('b', False, 'x'), _opt('c', False, 'x'), _opt('d', False, 'x'),
    ]), 'explanation'),
    (_l4_payload(sentence_index=-1), 'sentence_index'),
])
def test_l4_schema_reports_each_defect(payload, needle):
    errors = validate_ladder_output('morphology_slot', 1, payload)
    assert errors, f'expected a schema error mentioning {needle!r}'
    assert any(needle in e for e in errors), errors


def test_schema_errors_name_the_field_and_the_index():
    """The diagnostics keep the field name that named keys used to give free.

    This was the original argument against numeric keys — that a gate reading
    index 1 could only report ``key '1' missing``. Error strings carry both, so
    an operator reading a batch report still learns which field is wrong.
    """
    errors = validate_ladder_output('morphology_slot', 1, _l4_payload(base_form=''))
    assert any('base_form' in e and 'key 1' in e for e in errors), errors

    errors = validate_ladder_output('morphology_slot', 1, _l4_payload(options=[
        {'1': True, '2': 'x'}, _opt('b', False), _opt('c', False), _opt('d', False),
    ]))
    assert any('options[0]' in e and 'text' in e and 'key 0' in e for e in errors), errors


def test_l8_schema_rejects_error_word_among_the_options():
    """The planted error must not be selectable as the repair.

    This is the defect the gate exists for: a model that helpfully includes
    its own wrong word in the option list produces an item where the "wrong"
    answer and the sentence agree, and the learner has nothing to fix.
    """
    payload = _l8_payload(error_collocate='Cook')  # case-insensitive match
    errors = validate_ladder_output('collocation_repair', 1, payload)
    assert any('must not be selectable' in e for e in errors), errors


def test_l4_schema_rejects_non_dict():
    assert validate_ladder_output('morphology_slot', 1, ['not', 'a', 'dict'])


# --- the old named-key contract must now fail loudly -----------------------

def test_old_named_key_shape_is_rejected():
    """A half-migrated prompt must fail, not quietly produce an empty item.

    Before TASK-537 these prompts returned English field names. If a prompt row
    is ever reverted — or a new language row is authored from the old text — the
    gate has to say so. The failure mode this prevents is the one the whole
    schema layer exists for: a response that parses as JSON, matches nothing,
    and remaps into a blank exercise.
    """
    errors = validate_ladder_output('morphology_slot', 1, _named_l4_payload())
    assert errors, 'the pre-TASK-537 named-key shape must not validate'
    assert any('options' in e for e in errors), errors


def test_old_named_key_shape_is_rejected_for_every_ladder_type():
    named = {
        'morphology_slot': _named_l4_payload(),
        'collocation_repair': {
            'options': [{'text': 'brew', 'is_correct': True, 'explanation': 'x'}],
            'error_collocate': 'manufacture',
        },
        'synonym_antonym_match': {
            'relation': 'synonym',
            'options': [{'text': 'a', 'is_correct': True, 'explanation': 'x'}],
        },
        'word_family': {
            'stem': 'decide',
            'options': [{'text': 'decision', 'is_correct': True,
                         'explanation': 'x', 'part_of_speech': 'noun'}],
        },
        'particle_selection': {
            'blanked_particle': 'を',
            'options': [{'text': 'を', 'is_correct': True, 'explanation': 'x'}],
        },
    }
    for type_code, payload in named.items():
        assert validate_ladder_output(type_code, 1, payload), \
            f'{type_code} still accepts the old named-key shape'


# --- the error escape (key 9) ----------------------------------------------

@pytest.mark.parametrize('type_code, token', [
    ('morphology_slot', 'no_inflection'),
    ('collocation_repair', 'no_collocation'),
    ('synonym_antonym_match', 'no_relation'),
    ('word_family', 'no_family'),
    ('particle_selection', 'no_particle_slot'),
])
def test_error_escape_is_valid_for_every_type(type_code, token):
    assert validate_ladder_output(type_code, 1, {'9': token}) == []


def test_unknown_escape_token_is_an_error_not_a_skip():
    """A novel token means prompt and generator have drifted apart."""
    errors = validate_ladder_output('morphology_slot', 1, {'9': 'no_such_reason'})
    assert any('unknown token' in e for e in errors), errors


def test_string_and_int_keys_both_validate():
    """JSON gives string keys; a Python-built fixture may give ints."""
    int_keyed = {
        0: [{0: 'ran', 1: True, 2: 'past simple'},
            {0: 'run', 1: False, 2: 'x'},
            {0: 'running', 1: False, 2: 'x'},
            {0: 'runs', 1: False, 2: 'x'}],
        1: 'run', 2: 'past simple',
    }
    assert validate_ladder_output('morphology_slot', 1, int_keyed) == []


def test_unregistered_prompt_version_is_refused_not_guessed():
    """A prompt re-authored at v2 without updating the gate fails loudly."""
    with pytest.raises(SchemaError) as exc:
        ladder_schema('morphology_slot', 2)
    assert 'prompt_version=2' in str(exc.value)
    assert 'known versions: [1]' in str(exc.value)


def test_unknown_type_code_is_refused():
    with pytest.raises(SchemaError):
        ladder_schema('not_a_type', 1)


# ---------------------------------------------------------------------------
# 2. Split generators
# ---------------------------------------------------------------------------

def test_l4_generator_remaps_into_the_renderer_shape(monkeypatch, split_base):
    _stub(monkeypatch, split_base, [_l4_payload()])
    gen = MorphologySlotGenerator(db=None, language_id=2)

    out = gen.generate(1, _core(), {4: 1})

    assert set(out) == {'level_4'}
    level = out['level_4']
    assert level['correct_form'] == 'ran'
    assert level['base_form'] == 'run'
    assert level['form_label'] == 'past simple'
    assert len(level['options']) == 4
    assert level['explanations']['ran'] == 'past simple'
    # Ours, not the model's — the model only ever saw sentence 1.
    assert level['sentence_index'] == 1


def test_l4_generator_ignores_a_model_supplied_sentence_index(monkeypatch, split_base):
    """The monolith let the model nominate an index it had never read."""
    _stub(monkeypatch, split_base, [_l4_payload(sentence_index=9)])
    gen = MorphologySlotGenerator(db=None, language_id=2)

    out = gen.generate(1, _core(), {4: 2})

    assert out['level_4']['sentence_index'] == 2


def test_l4_generator_skips_a_sense_with_too_few_forms(monkeypatch, split_base):
    calls = _stub(monkeypatch, split_base, [])
    gen = MorphologySlotGenerator(db=None, language_id=2)

    # {} is "not applicable", distinct from None ("tried and failed") — the
    # pipeline records an error only for the latter.
    assert gen.generate(1, _core(forms=1), {4: 1}) == {}
    assert calls == [], 'a sense that cannot support L4 must not cost an LLM call'


def test_l4_generator_retries_once_on_schema_failure(monkeypatch, split_base):
    calls = _stub(monkeypatch, split_base, [
        _l4_payload(base_form=''),   # schema-invalid
        _l4_payload(),               # good on the retry
    ])
    gen = MorphologySlotGenerator(db=None, language_id=2)

    out = gen.generate(1, _core(), {4: 1})

    assert out['level_4']['base_form'] == 'run'
    assert len(calls) == 2


def test_l4_generator_gives_up_after_two_bad_responses(monkeypatch, split_base):
    calls = _stub(monkeypatch, split_base, [
        _l4_payload(base_form=''),
        _l4_payload(form_label=''),
    ])
    gen = MorphologySlotGenerator(db=None, language_id=2)

    assert gen.generate(1, _core(), {4: 1}) is None
    assert len(calls) == 2, 'exactly one retry, not an unbounded loop'


def test_l4_generator_survives_a_call_exception_then_succeeds(monkeypatch, split_base):
    _stub(monkeypatch, split_base, [RuntimeError('502 from provider'), _l4_payload()])
    gen = MorphologySlotGenerator(db=None, language_id=2)

    assert gen.generate(1, _core(), {4: 1})['level_4']['correct_form'] == 'ran'


def test_l8_generator_picks_a_sentence_that_attests_the_collocate(monkeypatch, split_base):
    sentences = [
        {'text': 'No partner here.', 'target_word': 'coffee'},
        {'text': 'Still nothing.', 'target_word': 'coffee'},
        {'text': 'They brew coffee at dawn.', 'target_word': 'coffee'},
    ]
    _stub(monkeypatch, split_base, [_l8_payload()])
    gen = CollocationRepairGenerator(db=None, language_id=2)

    out = gen.generate(1, _core(sentences=sentences), {8: 0})

    # Assigned index 0 does not contain "brew", so the scan moves on to 2.
    assert out['level_8']['sentence_index'] == 2
    assert out['level_8']['correct_collocate'] == 'brew'
    assert out['level_8']['error_collocate'] == 'manufacture'


def test_l8_generator_skips_when_no_sentence_attests_the_collocate(monkeypatch, split_base):
    sentences = [{'text': 'No partner anywhere.', 'target_word': 'coffee'}]
    calls = _stub(monkeypatch, split_base, [])
    gen = CollocationRepairGenerator(db=None, language_id=2)

    assert gen.generate(1, _core(sentences=sentences), {8: 0}) == {}
    assert calls == []


def test_l8_generator_skips_when_p1_returned_the_null_sentinel(monkeypatch, split_base):
    calls = _stub(monkeypatch, split_base, [])
    gen = CollocationRepairGenerator(db=None, language_id=2)

    assert gen.generate(1, _core(collocate='null'), {8: 0}) == {}
    assert calls == []


def test_l8_whole_word_match_rejects_substrings_but_allows_cjk():
    assert l8_repair.whole_word_match('They brew coffee', 'brew')
    assert not l8_repair.whole_word_match('The brewery opened', 'brew')
    assert l8_repair.whole_word_match('他们沏茶', '沏')


# ---------------------------------------------------------------------------
# 3. Isolation — the reason for the split
# ---------------------------------------------------------------------------

def test_l4_and_l8_use_independently_configured_models(monkeypatch, split_base):
    _stub(monkeypatch, split_base, [])

    l4 = MorphologySlotGenerator(db=None, language_id=2)
    l8 = CollocationRepairGenerator(db=None, language_id=2)

    assert l4.model != l8.model
    assert l4.TASK_NAME == SPLIT_LEVEL_TASKS[4]
    assert l8.TASK_NAME == SPLIT_LEVEL_TASKS[8]


def test_a_failing_l4_costs_l8_nothing(monkeypatch, split_base):
    """Under the monolith, one bad level forced a retry of the other two."""
    calls = _stub(monkeypatch, split_base, [
        _l4_payload(base_form=''), _l4_payload(base_form=''),   # L4 burns both attempts
        _l8_payload(),                                          # L8 succeeds first try
    ])

    l8_core = _core(sentences=[{'text': 'They brew coffee.', 'target_word': 'coffee'}])

    assert MorphologySlotGenerator(None, 2).generate(1, _core(), {4: 1}) is None
    l8_out = CollocationRepairGenerator(None, 2).generate(1, l8_core, {8: 0})

    assert l8_out['level_8']['correct_collocate'] == 'brew'
    assert len(calls) == 3, 'L8 paid for exactly one call despite L4 burning two'


def test_generation_calls_are_labelled_for_the_reject_rate_view(monkeypatch, split_base):
    calls = _stub(monkeypatch, split_base, [_l4_payload()])
    MorphologySlotGenerator(None, 2).generate(1, _core(), {4: 1})

    assert calls[0]['task_name'] == 'ladder_l4_morphology_generation'
    assert calls[0]['template_version'] == 1
    assert calls[0]['pipeline'] == 'vocab_ladder'


def test_json_is_enforced_at_the_provider_not_just_parsed(monkeypatch, split_base):
    """``json_object`` sets response_format on the provider payload.

    Plain ``'json'`` only parses client-side, so a model answering in prose
    burned a full retry cycle to discover it (TASK-539).
    """
    calls = _stub(monkeypatch, split_base, [_l4_payload()])
    MorphologySlotGenerator(None, 2).generate(1, _core(), {4: 1})

    assert calls[0]['response_format'] == 'json_object'


# --- the escape is a skip, not a failure -----------------------------------

def test_l4_error_escape_is_a_clean_skip(monkeypatch, split_base):
    """``{"9": "no_inflection"}`` means the sense cannot carry the level.

    That is the same outcome as a failed precondition — ``{}``, not None — so
    the pipeline does not record it as a generation error and no retry is paid.
    """
    calls = _stub(monkeypatch, split_base, [{'9': 'no_inflection'}])
    gen = MorphologySlotGenerator(db=None, language_id=2)

    assert gen.generate(1, _core(), {4: 1}) == {}
    assert len(calls) == 1, 'an escape must not be retried'


def test_l8_error_escape_is_a_clean_skip(monkeypatch, split_base):
    sentences = [{'text': 'They brew coffee.', 'target_word': 'coffee'}]
    calls = _stub(monkeypatch, split_base, [{'9': 'no_collocation'}])
    gen = CollocationRepairGenerator(db=None, language_id=2)

    assert gen.generate(1, _core(sentences=sentences), {8: 0}) == {}
    assert len(calls) == 1


# ---------------------------------------------------------------------------
# 4. The monolith no longer emits L4 / L8
# ---------------------------------------------------------------------------

def test_monolith_owns_only_l7():
    assert PROMPT3_MONOLITH_LEVELS == {7}
    # The family constant still covers all three: the per-type gate and the
    # renderer's suppression check reason about types, not about prompts.
    assert PROMPT3_LEVELS == {4, 7, 8}
    assert set(SPLIT_LEVEL_TASKS) == {4, 8}


def test_p3_requests_only_level_7(monkeypatch):
    captured = {}

    monkeypatch.setattr(
        p3mod, 'get_template_config',
        lambda db, task_name, language_id: {
            'template': 'levels={active_levels_json}',
            'model': 'm', 'provider': 'openrouter', 'version': 2,
        },
    )

    def _call(prompt, **kwargs):
        captured['prompt'] = prompt
        return {'7': {'1': 'wrong sentence', '2': 'right sentence',
                      '3': 'tense error', '4': [0, 1, 2]}}

    monkeypatch.setattr(p3mod, 'call_llm', _call)

    gen = p3mod.TransformAssetGenerator(db=None, language_id=2)
    out = gen.generate(1, _core(), [4, 7, 8], {4: 1, 7: 4, 8: 4}, [0, 1, 2])

    assert json.loads(captured['prompt'].split('levels=')[1]) == ['7']
    assert set(out) == {'level_7'}


def test_p3_remap_no_longer_knows_about_l4_or_l8():
    """The speculative shape branches are gone, not merely unused."""
    gen = p3mod.TransformAssetGenerator(db=None, language_id=2)
    assert not hasattr(gen, '_remap_level_4')
    assert not hasattr(gen, '_remap_level_8')
    assert not hasattr(gen, '_can_generate_l8')
    assert not hasattr(gen, '_pick_l8_sentence_index')


def test_p3_ignores_a_stray_l4_block_in_the_response(monkeypatch):
    """Even if a stale template answers with "4", the monolith drops it."""
    monkeypatch.setattr(
        p3mod, 'get_template_config',
        lambda db, task_name, language_id: {
            'template': 'x', 'model': 'm', 'provider': 'openrouter', 'version': 2,
        },
    )
    monkeypatch.setattr(
        p3mod, 'call_llm',
        lambda prompt, **kw: {
            '4': {'1': [{'1': 'ran', '2': True}]},
            '7': {'1': 'wrong', '2': 'right', '3': 'tense', '4': [0, 1]},
        },
    )

    out = p3mod.TransformAssetGenerator(None, 2).generate(
        1, _core(), [4, 7, 8], {7: 4}, [0, 1],
    )
    assert set(out) == {'level_7'}


def test_l4_module_task_name_matches_the_migration():
    assert l4_morphology.TASK_NAME == 'ladder_l4_morphology_generation'
    assert l8_repair.TASK_NAME == 'ladder_l8_collocation_repair_generation'
