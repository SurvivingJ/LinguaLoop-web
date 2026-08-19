"""TASK-522 (syn/ant + word_family) and TASK-527 (JA particle_selection).

LLM-free. Every test stubs ``call_llm`` / ``get_template_config`` at the module
that actually issues the call, and the JA tokeniser is stubbed so the suite
does not require the spaCy Japanese model to be installed.

The planted-defect tests are the ones that matter, and each task named its own:

  * TASK-522, syn/ant — a foil that is a synonym of a *different* sense of the
    same word must not survive.
  * TASK-522, word_family — an invented derivation that is actually a real
    word must be dropped.
  * TASK-527 — a distractor particle that also yields a natural sentence
    (the ni/he direction class) must be dropped.
"""

import pytest

from services.exercise_generation.judges import particle as particlemod
from services.exercise_generation.judges import relation as relationmod
from services.exercise_generation.schemas import validate_ladder_output
from services.vocabulary_ladder.asset_generators import (
    _split_base, particle_selection, syn_ant, typed_llm, word_family,
)
from services.vocabulary_ladder.asset_generators.particle_selection import (
    ParticleSelectionGenerator,
)
from services.vocabulary_ladder.asset_generators.syn_ant import SynonymAntonymGenerator
from services.vocabulary_ladder.asset_generators.word_family import WordFamilyGenerator

LANG_ZH, LANG_EN, LANG_JA = 1, 2, 3


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _clear_judge_caches():
    relationmod._cfg_cache.clear()
    particlemod._cfg_cache.clear()
    yield
    relationmod._cfg_cache.clear()
    particlemod._cfg_cache.clear()


# Numeric-key output contract (TASK-537): within an option object 0=text,
# 1=is_correct, 2=explanation, 3=part_of_speech. Top level: 0=options, and
# 9=the error escape.
_POS = '3'


def _opts(correct, wrong, extra=None):
    options = [{'0': correct, '1': True, '2': 'the answer'}]
    for w in wrong:
        options.append({'0': w, '1': False, '2': 'wrong'})
    if extra:
        for opt in options:
            opt.update(extra)
    return options


def _named_opts(correct, wrong, extra=None):
    """The pre-TASK-537 shape, for the "old contract is rejected" test."""
    options = [{'text': correct, 'is_correct': True, 'explanation': 'the answer'}]
    for w in wrong:
        options.append({'text': w, 'is_correct': False, 'explanation': 'wrong'})
    if extra:
        for opt in options:
            opt.update(extra)
    return options


def _core(**overrides):
    core = {
        'pos': 'noun',
        'semantic_class': 'abstract',
        'definition': 'a financial institution',
        'sense_fingerprint': 'money, account, loan',
        'register': 'neutral',
        'morphological_forms': [{'form': 'banks', 'label': 'plural'},
                                {'form': 'banking', 'label': 'gerund'}],
        'sentences': [
            {'text': f'Sentence {i} about the bank.', 'target_word': 'bank',
             'complexity_tier': 'T2'}
            for i in range(10)
        ],
    }
    core.update(overrides)
    return core


def _stub_generation(monkeypatch, responses, version=1):
    """Point the shared generator base at a fake template and scripted LLM."""
    calls = []
    monkeypatch.setattr(
        _split_base, 'get_template_config',
        lambda db, task_name, language_id: {
            'template': '{word}', 'model': f'model-{task_name}',
            'provider': 'openrouter', 'version': version,
        },
    )
    queue = list(responses)

    def _call(prompt, **kwargs):
        calls.append({'prompt': prompt, **kwargs})
        return queue.pop(0)

    monkeypatch.setattr(_split_base, 'call_llm', _call)
    return calls


def _stub_judge(monkeypatch, module, ratings_by_index, template):
    """Stub a judge module to return fixed Likert ratings."""
    monkeypatch.setattr(
        module, 'get_template_config',
        lambda db, task_name, language_id: {
            'template': template, 'model': 'judge-model',
            'provider': 'openrouter', 'version': 1,
        },
    )
    monkeypatch.setattr(module, 'log_judge_verdict', lambda **kw: None)
    calls = []

    def _call(prompt, **kw):
        calls.append(prompt)
        # Judge entries are numerically keyed too: 0=rating, 1=reason. The top
        # level stays the 1-based candidate number the prompt handed the model.
        return {
            str(i): {'0': r, '1': 'stub'}
            for i, r in ratings_by_index.items()
        }

    monkeypatch.setattr(module, 'call_llm', _call)
    return calls


def _stub_relation_judge(monkeypatch, ratings_by_index):
    return _stub_judge(
        monkeypatch, relationmod, ratings_by_index,
        '{target}|{definition}|{relation}|{correct_answer}|{candidates_numbered}',
    )


def _stub_family_judge(monkeypatch, ratings_by_index):
    return _stub_judge(
        monkeypatch, relationmod, ratings_by_index,
        '{stem}|{correct_answer}|{candidates_numbered}',
    )


def _stub_particle_judge(monkeypatch, ratings_by_index):
    return _stub_judge(
        monkeypatch, particlemod, ratings_by_index,
        '{sentence_with_blank}|{correct_particle}|{candidates_numbered}',
    )


@pytest.fixture
def no_embeddings(monkeypatch):
    """The embedding backfill is operator-gated and may not have run."""
    from services.vocabulary_ladder import sense_neighbours
    monkeypatch.setattr(
        sense_neighbours, 'neighbour_similarities',
        lambda db, sense_id, language_id, candidates: {},
    )


@pytest.fixture
def ja_particles(monkeypatch):
    """Stub the JA tokeniser so the suite needs no spaCy model.

    Returns particle spans for a fixed sentence, with correct character
    offsets — the offsets are the point of the helper, so faking them wrongly
    would make the blanking test meaningless.
    """
    sentence = '私は本を読みます。'
    spans = [
        {'particle': 'は', 'index': sentence.index('は')},
        {'particle': 'を', 'index': sentence.index('を')},
    ]
    monkeypatch.setattr(particle_selection, 'particle_spans',
                        lambda text: spans if text == sentence else [])
    return sentence


# ---------------------------------------------------------------------------
# Registry + schema wiring
# ---------------------------------------------------------------------------

def test_all_three_types_are_registered():
    assert typed_llm.registered_types() == {
        'synonym_antonym_match', 'word_family', 'particle_selection',
    }


@pytest.mark.parametrize('language_id, semantic_class, expected', [
    (LANG_EN, 'abstract', {'synonym_antonym_match', 'word_family'}),
    (LANG_JA, 'action', {'synonym_antonym_match', 'particle_selection'}),
    # ZH concrete: syn/ant is abstract|action|property only, word_family is
    # English only, particles are Japanese only.
    (LANG_ZH, 'concrete', set()),
])
def test_matrix_routes_each_type_to_the_right_language(
    language_id, semantic_class, expected,
):
    types = {
        cap['type_code']
        for cap in typed_llm.applicable_types(language_id, semantic_class)
    }
    assert types == expected


@pytest.mark.parametrize('type_code, payload, valid', [
    ('synonym_antonym_match',
     {'0': _opts('exactness', ['vagueness', 'haste', 'clutter']), '1': 'synonym'},
     True),
    ('synonym_antonym_match',
     {'0': _opts('a', ['b', 'c', 'd']), '1': 'hypernym'},
     False),
    ('word_family',
     {'0': _opts('decision', ['decidement', 'decisionment', 'decidal'],
                 extra={_POS: 'noun'}),
      '1': 'decide'},
     True),
    ('word_family',
     {'0': _opts('decision', ['a', 'b', 'c']), '1': 'decide'},
     False),   # missing part_of_speech (option key 3)
])
def test_typed_schemas_gate_their_shapes(type_code, payload, valid):
    errors = validate_ladder_output(type_code, 1, payload)
    assert (errors == []) is valid, errors


def test_typed_schemas_reject_the_old_named_key_shape():
    """A prompt row reverted to the pre-TASK-537 text must fail the gate."""
    named = {
        'synonym_antonym_match': {
            'relation': 'synonym',
            'options': _named_opts('exactness', ['vagueness', 'haste', 'clutter']),
        },
        'word_family': {
            'stem': 'decide',
            'options': _named_opts(
                'decision', ['decidement', 'decisionment', 'decidal'],
                extra={'part_of_speech': 'noun'}),
        },
        'particle_selection': {
            'blanked_particle': 'を',
            'options': _named_opts('を', ['が', 'に', 'で']),
        },
    }
    for type_code, payload in named.items():
        assert validate_ladder_output(type_code, 1, payload), \
            f'{type_code} still accepts the old named-key shape'


def test_particle_schema_rejects_a_correct_option_that_is_not_the_blank():
    """The model re-choosing the blank would leave a hole the answer misses."""
    payload = {'0': _opts('が', ['を', 'に', 'で']), '1': 'を'}
    errors = validate_ladder_output('particle_selection', 1, payload)
    assert any('is not the blanked particle' in e for e in errors), errors


# ---------------------------------------------------------------------------
# syn/ant
# ---------------------------------------------------------------------------

def test_syn_ant_generates_and_renders(monkeypatch, no_embeddings):
    _stub_generation(monkeypatch, [{
        '0': _opts('exactness', ['vagueness', 'haste', 'clutter']),
        '1': 'synonym',
    }])
    _stub_relation_judge(monkeypatch, {1: 5, 2: 5, 3: 5})

    gen = SynonymAntonymGenerator(db=None, language_id=LANG_EN)
    fragment = gen.generate(1, _core(), {6: 3})['synonym_antonym_match']
    content = gen.render(None, fragment, _core(), 1, LANG_EN, 'en')

    assert content['relation'] == 'synonym'
    assert content['correct_answer'] == 'exactness'
    assert len(content['options']) == 4
    assert 'exactness' in content['options']
    # Schema-v2 envelope: nl prose under content.nl, TL options at top level.
    assert content['schema_version'] == 2
    assert content['nl']['en']['definition'] == 'a financial institution'


def test_syn_ant_planted_cross_sense_foil_is_dropped(monkeypatch, no_embeddings):
    """TASK-522 AC: 'sense-anchored foils don't cross senses'.

    'shore' is not a synonym of bank-the-institution, so the generator offers
    it — but it IS a synonym of bank-the-riverbank, so a learner reading that
    sense answers it and is marked wrong. The judge rates it 1.
    """
    _stub_generation(monkeypatch, [{
        '0': _opts('institution', ['shore', 'ledger', 'vault']),
        '1': 'synonym',
    }])
    # Candidate 1 ('shore') is the planted defect.
    _stub_relation_judge(monkeypatch, {1: 1, 2: 5, 3: 5})

    gen = SynonymAntonymGenerator(db=None, language_id=LANG_EN)
    fragment = gen.generate(1, _core(), {6: 3})['synonym_antonym_match']
    content = gen.render(None, fragment, _core(), 1, LANG_EN, 'en')

    # Only 2 clean foils remain, so the variant is skipped rather than shipped
    # with a two-answer item.
    assert content is None


def test_syn_ant_embedding_band_drops_a_near_duplicate(monkeypatch):
    from services.vocabulary_ladder import sense_neighbours
    monkeypatch.setattr(
        sense_neighbours, 'neighbour_similarities',
        lambda db, sense_id, language_id, candidates: {
            'vagueness': 0.55, 'haste': 0.50, 'clutter': 0.95,   # near-duplicate
        },
    )
    _stub_generation(monkeypatch, [{
        '0': _opts('exactness', ['vagueness', 'haste', 'clutter']),
        '1': 'synonym',
    }])
    _stub_relation_judge(monkeypatch, {1: 5, 2: 5})

    gen = SynonymAntonymGenerator(db=None, language_id=LANG_EN)
    fragment = gen.generate(1, _core(), {6: 3})['synonym_antonym_match']
    content = gen.render(object(), fragment, _core(), 1, LANG_EN, 'en')

    # 'clutter' was band-dropped, leaving 2 foils — below the 3 required.
    assert content is None


def test_syn_ant_skips_a_sense_with_no_definition(monkeypatch):
    calls = _stub_generation(monkeypatch, [])
    gen = SynonymAntonymGenerator(db=None, language_id=LANG_EN)

    assert gen.generate(1, _core(definition=''), {6: 3}) == {}
    assert calls == []


def test_syn_ant_skips_a_concrete_noun(monkeypatch):
    """A concrete noun's 'synonym' is a hypernym or a regional variant."""
    calls = _stub_generation(monkeypatch, [])
    gen = SynonymAntonymGenerator(db=None, language_id=LANG_EN)

    assert gen.generate(1, _core(semantic_class='concrete'), {6: 3}) == {}
    assert calls == []


def test_syn_ant_variants_ask_different_relations():
    """A and B must be different questions, not two samples of one."""
    assert SynonymAntonymGenerator.relation_for(3) == 'antonym'
    assert SynonymAntonymGenerator.relation_for(9) == 'antonym'
    assert SynonymAntonymGenerator.relation_for(6) == 'synonym'


# ---------------------------------------------------------------------------
# word_family
# ---------------------------------------------------------------------------

def _family_payload(wrong=('decidement', 'decisionment', 'decidal')):
    return {
        '0': _opts('decision', list(wrong), extra={_POS: 'noun'}),
        '1': 'decide',
    }


def test_word_family_generates_and_renders(monkeypatch):
    _stub_generation(monkeypatch, [_family_payload()])
    _stub_family_judge(monkeypatch, {1: 5, 2: 5, 3: 5})

    gen = WordFamilyGenerator(db=None, language_id=LANG_EN)
    core = _core()
    fragment = gen.generate(1, core, {4: 1})['word_family']
    content = gen.render(None, fragment, core, 1, LANG_EN, 'en')

    assert content['stem'] == 'decide'
    assert content['correct_answer'] == 'decision'
    assert content['required_pos'] == 'noun'
    assert '___' in content['sentence_with_blank']
    assert content['schema_version'] == 2


def test_word_family_planted_real_word_is_dropped(monkeypatch):
    """TASK-522 AC: 'invented-derivation planted defect is dropped'.

    'decisive' is a real word offered as an invented derivation, which gives
    the item two defensible answers.
    """
    _stub_generation(monkeypatch, [
        _family_payload(wrong=('decisive', 'decisionment', 'decidal')),
    ])
    _stub_family_judge(monkeypatch, {1: 1, 2: 5, 3: 5})   # 'decisive' rated 1

    gen = WordFamilyGenerator(db=None, language_id=LANG_EN)
    core = _core()
    fragment = gen.generate(1, core, {4: 1})['word_family']

    assert gen.render(None, fragment, core, 1, LANG_EN, 'en') is None


def test_word_family_dictionary_probe_vetoes_without_a_model_call(monkeypatch):
    """An attested morphological form must never be an 'invented' distractor."""
    _stub_generation(monkeypatch, [
        _family_payload(wrong=('banking', 'decisionment', 'decidal')),
    ])
    judge_calls = _stub_family_judge(monkeypatch, {1: 5, 2: 5})

    gen = WordFamilyGenerator(db=None, language_id=LANG_EN)
    core = _core()   # morphological_forms includes 'banking'
    fragment = gen.generate(1, core, {4: 1})['word_family']

    assert gen.render(None, fragment, core, 1, LANG_EN, 'en') is None
    # 'banking' never reached the judge — the certain signal vetoed it.
    assert 'banking' not in judge_calls[0]


def test_word_family_skips_an_invariant_word(monkeypatch):
    calls = _stub_generation(monkeypatch, [])
    gen = WordFamilyGenerator(db=None, language_id=LANG_EN)

    assert gen.generate(1, _core(morphological_forms=[]), {4: 1}) == {}
    assert calls == []


# ---------------------------------------------------------------------------
# particle_selection
# ---------------------------------------------------------------------------

def _ja_core(sentence):
    return {
        'pos': 'noun', 'semantic_class': 'concrete',
        'definition': '書物', 'sense_fingerprint': '読む対象',
        'register': 'neutral', 'morphological_forms': [],
        'sentences': [
            {'text': sentence, 'target_word': '本', 'complexity_tier': 'T2'}
            for _ in range(4)
        ],
    }


def _particle_payload(wrong=('が', 'に', 'で')):
    return {
        '0': _opts('を', list(wrong)),
        '1': 'を',
        '2': {w: 'object_marking' for w in wrong},
    }


def test_particle_generates_and_renders(monkeypatch, ja_particles):
    _stub_generation(monkeypatch, [_particle_payload()])
    _stub_particle_judge(monkeypatch, {1: 5, 2: 5, 3: 5})

    gen = ParticleSelectionGenerator(db=None, language_id=LANG_JA)
    core = _ja_core(ja_particles)
    fragment = gen.generate(1, core, {4: 0})['particle_selection']
    content = gen.render(None, fragment, core, 1, LANG_JA, 'en')

    assert content['correct_answer'] == 'を'
    assert content['sentence_with_blank'] == '私は本___読みます。'
    assert set(content['error_tags']) == {'が', 'に', 'で'}
    assert content['schema_version'] == 2


def test_particle_planted_also_natural_distractor_is_dropped(monkeypatch, ja_particles):
    """TASK-527 AC: planted also-natural particle (ni/he direction class).

    he is grammatical wherever ni marks a goal, so an item offering both has
    two right answers. The judge rates it 1.
    """
    _stub_generation(monkeypatch, [_particle_payload(wrong=('へ', 'が', 'で'))])
    _stub_particle_judge(monkeypatch, {1: 1, 2: 5, 3: 5})   # he rated 1

    gen = ParticleSelectionGenerator(db=None, language_id=LANG_JA)
    core = _ja_core(ja_particles)
    fragment = gen.generate(1, core, {4: 0})['particle_selection']

    assert gen.render(None, fragment, core, 1, LANG_JA, 'en') is None


def test_particle_blank_is_cut_at_a_tokenised_span_not_a_substring(monkeypatch):
    """``str.replace`` would blank the ni inside ninjin (carrot)."""
    monkeypatch.setattr(particle_selection, 'particle_spans', lambda text: [])
    assert ParticleSelectionGenerator.blank_particle('にんじんを買う', 'に') is None


def test_particle_blank_uses_the_recorded_offset(monkeypatch):
    text = '私は本を読みます。'
    monkeypatch.setattr(
        particle_selection, 'particle_spans',
        lambda t: [
            {'particle': 'は', 'index': text.index('は')},
            {'particle': 'を', 'index': text.index('を')},
        ] if t == text else [],
    )
    assert ParticleSelectionGenerator.blank_particle(text, 'は') == '私___本を読みます。'


def test_particle_skips_a_sentence_with_too_few_particles(monkeypatch):
    monkeypatch.setattr(particle_selection, 'particle_spans', lambda text: [])
    calls = _stub_generation(monkeypatch, [])

    gen = ParticleSelectionGenerator(db=None, language_id=LANG_JA)
    assert gen.generate(1, _ja_core('本。'), {4: 0}) == {}
    assert calls == []


def test_particle_items_carry_the_l4_form_production_metadata():
    from services.vocabulary_ladder.config import EXERCISE_TYPE_FAMILY

    assert ParticleSelectionGenerator.LADDER_LEVEL == 4
    assert EXERCISE_TYPE_FAMILY['particle_selection'] == 'form_production'


def test_task_names_match_the_migrations():
    assert syn_ant.TASK_NAME == 'ladder_syn_ant_generation'
    assert word_family.TASK_NAME == 'ladder_word_family_generation'
    assert particle_selection.TASK_NAME == 'ladder_particle_selection_generation'


# ---------------------------------------------------------------------------
# Shared judge polarity
# ---------------------------------------------------------------------------
# The two ladder judges ask deliberately different questions — "is this a
# non-relation?" vs "does this also yield a natural sentence?" — but they must
# SCORE the answer identically: both call likert_to_verdict on the raw rating
# with no local threshold. Nothing else in the suite would notice if one of them
# grew its own cutoff, and the result would be one judge silently inverted:
# distractors kept where the other drops them, with no test failing.

@pytest.mark.parametrize('rating, expect_kept', [
    (5, True),    # ideal distractor
    (4, True),
    (3, True),    # flag — uncertainty keeps the candidate (v3 fail-open)
    (2, False),   # reject
    (1, False),   # also-correct answer
])
def test_both_ladder_judges_agree_on_every_likert_rating(
    monkeypatch, rating, expect_kept, ja_particles,
):
    _stub_relation_judge(monkeypatch, {1: rating})
    relation_kept, _ = relationmod.filter_relation_foils(
        None, 'bank', 'a financial institution', 'synonym', 'institution',
        ['shore'], LANG_EN,
    )

    _stub_particle_judge(monkeypatch, {1: rating})
    particle_kept, _ = particlemod.filter_particle_foils(
        None, '私は本___読みます。', 'を', ['へ'], LANG_JA,
    )

    assert bool(relation_kept) is expect_kept
    assert bool(particle_kept) is expect_kept, (
        f'particle judge disagrees with the relation judge at rating {rating}'
    )


def test_both_ladder_judges_share_one_verdict_function():
    """Polarity is shared by construction, not by a duplicated threshold."""
    from services.test_generation.schemas import likert_to_verdict

    assert relationmod.likert_to_verdict is likert_to_verdict
    assert particlemod.likert_to_verdict is likert_to_verdict


def test_judges_enforce_json_at_the_provider(monkeypatch):
    captured = {}
    monkeypatch.setattr(
        relationmod, 'get_template_config',
        lambda db, task_name, language_id: {
            'template': '{target}|{definition}|{relation}|{correct_answer}|'
                        '{candidates_numbered}',
            'model': 'judge-model', 'provider': 'openrouter', 'version': 1,
        },
    )

    def _call(prompt, **kw):
        captured.update(kw)
        return {'1': {'0': 5, '1': 'stub'}}

    monkeypatch.setattr(relationmod, 'call_llm', _call)
    relationmod.filter_relation_foils(
        None, 'bank', 'def', 'synonym', 'institution', ['shore'], LANG_EN,
    )

    assert captured['response_format'] == 'json_object'


# ---------------------------------------------------------------------------
# The error escape is a skip, not a failure
# ---------------------------------------------------------------------------

def test_syn_ant_error_escape_is_a_clean_skip(monkeypatch):
    calls = _stub_generation(monkeypatch, [{'9': 'no_relation'}])
    gen = SynonymAntonymGenerator(db=None, language_id=LANG_EN)

    assert gen.generate(1, _core(), {6: 3}) == {}
    assert len(calls) == 1, 'an escape must not be retried'


def test_word_family_error_escape_is_a_clean_skip(monkeypatch):
    calls = _stub_generation(monkeypatch, [{'9': 'no_family'}])
    gen = WordFamilyGenerator(db=None, language_id=LANG_EN)

    assert gen.generate(1, _core(), {4: 1}) == {}
    assert len(calls) == 1


def test_particle_error_escape_is_a_clean_skip(monkeypatch, ja_particles):
    calls = _stub_generation(monkeypatch, [{'9': 'no_particle_slot'}])
    gen = ParticleSelectionGenerator(db=None, language_id=LANG_JA)

    assert gen.generate(1, _ja_core(ja_particles), {4: 0}) == {}
    assert len(calls) == 1


# ---------------------------------------------------------------------------
# The indexed shape stops at the LLM boundary
# ---------------------------------------------------------------------------

def test_stored_fragments_carry_descriptive_keys_not_indices(monkeypatch):
    """``word_assets.content`` must never see a numeric key.

    The indices exist to keep English out of a ZH/JA prompt. Letting them past
    the remap would push the translation onto the renderer, the validators and
    every future reader of a stored asset.
    """
    _stub_generation(monkeypatch, [_family_payload()])
    gen = WordFamilyGenerator(db=None, language_id=LANG_EN)

    fragment = gen.generate(1, _core(), {4: 1})['word_family']

    assert set(fragment) >= {'stem', 'options', 'correct_answer',
                             'explanations', 'parts_of_speech'}
    assert not any(k.isdigit() for k in fragment)
    for option in fragment['options']:
        assert set(option) == {'text', 'is_correct', 'explanation', 'part_of_speech'}
    assert fragment['parts_of_speech']['decision'] == 'noun'
