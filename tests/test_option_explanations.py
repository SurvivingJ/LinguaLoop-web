"""Per-option explanations for the word-option types (2026-11-27, ADR-064 amendment):
choose the particle (``particle_selection``), the word form (``morphology_slot``) and
the synonym / antonym (``synonym_antonym_match``).

Offline: the conftest installs an empty ``InMemoryBackend`` per test; ``call_llm`` is
patched; the table is a small fake.
"""

from __future__ import annotations

import copy
from types import SimpleNamespace

import pytest

from config import Config
from services import exercise_explanations as xe
from services import explanation_files as xf
from services import explanations_anthropic as xa
from services.exercise_content import store
from services.exercise_content.backends import InMemoryBackend

ZH, EN, JA = 1, 2, 3
SENSE = 36401
EID = '5b0d2c4e-1f0a-4c55-9a51-3f6e2d7c8b90'
EID_SPOT = '9da9df5c-7a75-4bae-83a6-fbe77b57cf27'

PARTICLE = {
    'correct_answer': 'が', 'error_tags': {'から': '', 'と': '並列', 'を': '目的語'},
    'nl': {'en': {'explanation': '正解。「時計が」で、朝七時を知らせる主語を示す。'}},
    'options': ['から', 'を', 'と', 'が'],
    'original_sentence': '机の上の時計が、朝七時を知らせた。',
    'sentence_with_blank': '机の上の時計___、朝七時を知らせた。', 'target_word': '時計',
}
FORM = {
    'base_form': '扱う', 'correct_answer': '扱って', 'explanation': 'て形。「扱ってくれた」と続き、正しい。',
    'form_label': 'て形', 'options': ['扱った', '扱って', '扱い', '扱う'],
    'original_sentence': '先生は生徒の意見を公平に扱ってくれた。',
    'sentence_with_blank': '先生は生徒の意見を公平に___くれた。', 'target_word': '扱って',
    'word_definition': '物事を自分の思い通りに動かしたり、操作したりすること。',
}
RELATION = {
    'correct_answer': '海外', 'relation': 'antonym', 'word': '国内',
    'nl': {'en': {'definition': 'その国の内部。国家の領域内。', 'explanation': '「国内」の対義語。'}},
    'options': ['海外', '城下', '郷土', '田園'],
}
SPOT_SENTENCES = [
    {'is_correct': True, 'text': '人間は言葉を使う。'},
    {'is_correct': False, 'text': '人間は言葉が使う。'},
]


def particle_answer(**override):
    entries = [
        {'index': 1, 'meaning': 'marks a starting point',
         'explanation': '「から」 marks where something starts, which makes no sense after 「時計」.'},
        {'index': 2, 'meaning': 'marks the direct object',
         'explanation': '「を」 would make 「時計」 the object, but nothing acts on the clock.'},
        {'index': 3, 'meaning': 'joins nouns ("and") or marks a partner',
         'explanation': '「と」 needs a second noun or a partner; here it leaves the verb with no subject.'},
        {'index': 4, 'meaning': 'The clock on the desk announced seven in the morning.',
         'explanation': '「が」 marks 「時計」 as the subject of 「知らせた」.'},
    ]
    for k, v in override.items():
        entries[int(k[1:]) - 1].update(v)
    return {'options': entries}


@pytest.fixture(autouse=True)
def _clean(monkeypatch):
    xe.reset_state()
    monkeypatch.setattr(Config, 'EXERCISE_EXPLANATIONS_ENABLED', True)
    monkeypatch.setattr(Config, 'EXERCISE_EXPLANATION_MODEL', 'primary/model')
    monkeypatch.setattr(Config, 'EXERCISE_EXPLANATION_FALLBACK_MODEL', '')
    yield
    xe.reset_state()


@pytest.fixture
def mem():
    backend = InMemoryBackend()
    store.set_backend(backend)
    return backend


@pytest.fixture
def no_model(monkeypatch):
    def boom(*_a, **_k):
        raise AssertionError('no model call expected')
    monkeypatch.setattr('services.llm_service.call_llm', boom)


def _item(eid=EID, etype=xe.PARTICLE, c=None, version=0, sense=SENSE):
    return {'exercise_id': eid, 'sense_id': sense, 'exercise_type': etype,
            'content_version': version, 'content': copy.deepcopy(c if c is not None else PARTICLE)}


def _payload(c=PARTICLE, etype=xe.PARTICLE, answer=None):
    units = xe.sentences_of(c, etype)
    return {'sentences': xe.parse(answer or particle_answer(), units, EN, etype),
            'prompt_version': xe.prompt_version(etype)}


# ---------------------------------------------------------------------------
# Shape
# ---------------------------------------------------------------------------

def test_options_are_units_in_stored_order_with_the_key_marked():
    units = xe.sentences_of(PARTICLE, xe.PARTICLE)
    assert units == [{'text': 'から', 'is_correct': False}, {'text': 'を', 'is_correct': False},
                     {'text': 'と', 'is_correct': False}, {'text': 'が', 'is_correct': True}]
    assert xe.sentences_of(PARTICLE) is None            # without the type: the sentence shape
    assert xe.sentences_of({'options': [{'text': 'A'}, {'text': 'B'}], 'correct_answer': 'B'},
                           xe.RELATION)[1] == {'text': 'B', 'is_correct': True}


@pytest.mark.parametrize('change', [
    {'options': ['が']},                                   # one option
    {'options': ['が', 'が', 'を']},                        # duplicates
    {'correct_answer': 'に'},                              # key not among the options
    {'correct_answer': ''},
    {'options': ['が', '', 'を']},
    {'accepted_answers': ['が', 'を']},                    # several right answers
])
def test_unexplainable_option_items(change):
    assert xe.sentences_of(dict(PARTICLE, **change), xe.PARTICLE) is None


def test_types_have_their_own_prompt_version_and_file_kind():
    assert xe.TYPES == xe.SENTENCE_TYPES | xe.OPTION_TYPES
    assert {t: (xe.prompt_version(t), xe.file_kind(t)) for t in xe.TYPES} == {
        xe.SPOT: (2, 'p'), xe.PICK: (2, 'p'),
        xe.PARTICLE: (1, 'o'), xe.FORM: (1, 'o'), xe.RELATION: (1, 'o')}


# ---------------------------------------------------------------------------
# Prompts and validation
# ---------------------------------------------------------------------------

def _user(c, etype, tl=JA):
    return xe.build_prompt(xe.sentences_of(c, etype), tl, EN, etype, content=c)[1]


def test_particle_prompt_gives_the_sentence_the_key_the_tags_and_the_note():
    user = _user(PARTICLE, xe.PARTICLE)
    assert 'Sentence with the blank: 机の上の時計___、朝七時を知らせた。' in user
    assert 'Complete sentence: 机の上の時計が、朝七時を知らせた。' in user
    assert '4. [CORRECT] が' in user and '1. [WRONG] から\n' in user
    assert '2. [WRONG] を   (item tag for this option, may be in another language: 目的語)' in user
    assert "Teacher's note on the correct option (may be in another language): 正解。" in user
    assert 'what that particle generally marks' in user
    assert '{"options": [' in user


def test_form_prompt_names_the_base_form_and_the_form_asked_for():
    user = _user(FORM, xe.FORM)
    assert 'picks the form of 「扱う」 that fills it (the form asked for: て形)' in user
    assert 'the name of that form and what it expresses' in user
    assert "Teacher's note on the correct option (may be in another language): て形。" in user


def test_relation_prompt_says_antonym_and_asks_for_readings():
    user = _user(RELATION, xe.RELATION)
    assert 'picks its antonym: a word with the opposite meaning' in user
    assert 'Dictionary definition of 「国内」 (may be in another language): その国の内部。' in user
    assert 'reading in hiragana' in user
    assert 'or a synonym rather than an antonym' in user
    syn = _user(dict(RELATION, relation='synonym'), xe.RELATION)
    assert 'picks its synonym: a word with the same or a very close meaning' in syn
    assert 'or an antonym rather than a synonym' in syn
    zh = _user(dict(RELATION, options=['购买', '种植', '保存', '修理'], correct_answer='购买',
                    word='出售'), xe.RELATION, tl=ZH)
    assert 'pinyin with tone marks' in zh


def test_parse_reads_options_needs_a_meaning_and_writes_no_correction():
    units = xe.sentences_of(PARTICLE, xe.PARTICLE)
    got = xe.parse(particle_answer(), units, EN, xe.PARTICLE, corrected='ignored')
    assert [e['text'] for e in got] == ['から', 'を', 'と', 'が']
    assert [e['is_correct'] for e in got] == [False, False, False, True]
    assert all(e['correction'] is None for e in got)
    assert xe.parse(particle_answer(o2={'meaning': ''}), units, EN, xe.PARTICLE) is None
    assert xe.parse(particle_answer(o4={'explanation': '主語を示す。'}), units, EN,
                    xe.PARTICLE) is None                   # not English
    assert xe.parse({'sentences': particle_answer()['options']}, units, EN, xe.PARTICLE)


def test_the_items_own_note_never_counts_as_a_complete_explanation():
    english = dict(FORM, explanation='Te-form, joined to くれた.')
    units = xe.sentences_of(english, xe.FORM)
    assert xe.stored_entries(units, EN, xe.FORM) is None


# ---------------------------------------------------------------------------
# Serving
# ---------------------------------------------------------------------------

def test_an_option_item_is_served_from_its_o_file_with_no_model_call(mem, no_model):
    xf.write_file(JA, SENSE, EN, xe.OPTION_PROMPT_VERSION,
                  {EID: {'content_version': 0, 'model': 'm', 'payload': _payload()}}, kind='o')
    items = [_item()]
    pre = xe.prefetch(None, items, language_id=JA, nl_language_id=EN)
    assert xe.prepare_items(None, items, language_id=JA, nl_language_id=EN, prefetched=pre) == 0
    expl = items[0]['content']['option_explanations']
    assert expl[3]['meaning'] == 'The clock on the desk announced seven in the morning.'
    assert len(expl) == 4 and items[0]['content']['explanation_language'] == 'en'


def test_one_request_reads_both_kinds_of_file_together(mem, no_model):
    spot_payload = {'sentences': xe.parse({'sentences': [
        {'index': 1, 'meaning': 'Humans use language.', 'explanation': '「を」 marks the object.'},
        {'index': 2, 'meaning': 'Humans language uses.', 'explanation': '「使う」 takes 「を」.'}]},
        SPOT_SENTENCES, EN), 'prompt_version': xe.PROMPT_VERSION}
    xf.write_file(JA, SENSE, EN, xe.PROMPT_VERSION,
                  {EID_SPOT: {'content_version': 0, 'model': 'm', 'payload': spot_payload}})
    xf.write_file(JA, SENSE, EN, xe.OPTION_PROMPT_VERSION,
                  {EID: {'content_version': 0, 'model': 'm', 'payload': _payload()}}, kind='o')
    xe.reset_state()
    mem.clear_calls()
    items = [_item(), {'exercise_id': EID_SPOT, 'sense_id': SENSE, 'exercise_type': xe.SPOT,
                       'content_version': 0, 'content': {'sentences': copy.deepcopy(SPOT_SENTENCES)}}]
    pre = xe.prefetch(None, items, language_id=JA, nl_language_id=EN)
    assert set(pre.files) == {EID, EID_SPOT}
    assert sorted(mem.calls_for('get')) == sorted([
        xf.file_path(JA, SENSE, EN, 2, 'p'), xf.file_path(JA, SENSE, EN, 1, 'o')])
    xe.prepare_items(None, items, language_id=JA, nl_language_id=EN, prefetched=pre)
    assert all(i['content'].get('option_explanations') for i in items)


def test_a_payload_at_the_sentence_prompt_version_is_not_served_to_an_option_item(monkeypatch):
    calls = []
    monkeypatch.setattr('services.llm_service.call_llm',
                        lambda prompt, **kw: calls.append(kw) or particle_answer())
    wrong_version = dict(_payload(), prompt_version=xe.PROMPT_VERSION)
    pre = xe.Prefetched(files={EID: {'content_version': 0, 'payload': wrong_version}})
    items = [_item()]
    assert xe.prepare_items(None, items, language_id=JA, nl_language_id=EN, prefetched=pre) == 1
    assert 'option_explanations' not in items[0]['content']
    fut = xe._inflight.get((EID, EN))
    payload = fut.result(timeout=5) if fut else None
    assert payload['prompt_version'] == xe.OPTION_PROMPT_VERSION
    assert calls[0]['task_name'] == 'particle_choice_explanation'
    assert calls[0]['template_version'] == xe.OPTION_PROMPT_VERSION


def test_get_or_generate_serves_an_option_item(monkeypatch, mem):
    monkeypatch.setattr('services.llm_service.call_llm', lambda prompt, **kw: particle_answer())

    class DB:
        def table(self, name):
            q = SimpleNamespace()
            rows = {'exercises': [{'id': EID, 'word_sense_id': SENSE, 'language_id': JA,
                                   'exercise_type': xe.PARTICLE, 'content_version': 0,
                                   'is_active': True}]}.get(name, [])
            for m in ('select', 'eq', 'in_', 'limit', 'upsert'):
                setattr(q, m, lambda *a, **k: q)
            q.execute = lambda: SimpleNamespace(data=[dict(r) for r in rows])
            return q

    def hydrate(rows, language_id=None, drop_missing=True, **_k):
        for r in rows:
            r['content'] = copy.deepcopy(PARTICLE)
    monkeypatch.setattr(store, 'hydrate', hydrate)
    state, shaped = xe.get_or_generate(DB(), EID, EN)
    assert state == 'ready'
    assert [e['meaning'] for e in shaped['option_explanations']][1] == 'marks the direct object'


# ---------------------------------------------------------------------------
# Batch helpers (services/explanations_anthropic.py)
# ---------------------------------------------------------------------------

def test_batch_request_and_answer_for_an_option_item():
    params = xa.request_params(FORM, JA, EN, xe.FORM, None, 'claude-sonnet-5-5', 'medium')
    assert 'picks the form of 「扱う」' in params['messages'][0]['content']
    assert xa.request_params(dict(FORM, options=['扱って']), JA, EN, xe.FORM, None,
                             'claude-sonnet-5-5', 'medium') is None
    import json
    answer = {'options': [
        {'index': i + 1, 'meaning': f'form {i}', 'explanation': f'Why form {i} does or does not fit.'}
        for i in range(4)]}
    msg = SimpleNamespace(stop_reason='end_turn',
                          content=[SimpleNamespace(type='text', text=json.dumps(answer))])
    payload = xa.payload_from_message(msg, FORM, EN, xe.FORM, None)
    assert payload['prompt_version'] == xe.OPTION_PROMPT_VERSION
    assert [e['is_correct'] for e in payload['sentences']] == [False, True, False, False]
