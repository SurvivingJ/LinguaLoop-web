"""Per-option spot-the-error explanations in the learner's language (ADR-064,
services/exercise_explanations.py, GET /api/practice/explanations/<id>)."""

from __future__ import annotations

import copy
import threading
import time
from types import SimpleNamespace

import pytest
from flask import Flask

from config import Config
from services import exercise_explanations as xe
from services.exercise_content import store

JA, EN = 3, 2
EID = '9da9df5c-7a75-4bae-83a6-fbe77b57cf27'

SENTENCES = [
    {'is_correct': True, 'text': 'これは心理学に基づいた人間の無意識の反応を利用したものだ。'},
    {'is_correct': True, 'text': '人間は言葉を使う。'},
    {'is_correct': False, 'text': '人間は言葉が使う。',
     'error_description': '助詞：他動詞「使う」の対象は「を」で示す。「が」は誤り。'},
    {'is_correct': True, 'text': '彼は優しい人間だ。'},
]


def content():
    return {'sentences': copy.deepcopy(SENTENCES)}


def model_answer(correction='人間は言葉を使う。', **override):
    entries = [
        {'index': 1, 'meaning': 'This uses unconscious human reactions based on psychology.',
         'explanation': '「に基づいた」 means "based on" and modifies the noun phrase.', 'correction': None},
        {'index': 2, 'meaning': 'Humans use language.',
         'explanation': '「を」 marks 「言葉」 as the object of the transitive verb 「使う」.',
         'correction': 'should be dropped'},
        {'index': 3, 'meaning': 'Humans use language.',
         'explanation': 'The object of 「使う」 takes 「を」, not 「が」.', 'correction': correction},
        {'index': 4, 'meaning': 'He is a kind person.',
         'explanation': 'The i-adjective 「優しい」 modifies 「人間」 directly.', 'correction': None},
    ]
    for k, v in override.items():
        entries[int(k[1:]) - 1].update(v)
    return {'sentences': entries}


@pytest.fixture(autouse=True)
def _clean(monkeypatch):
    xe.reset_state()
    monkeypatch.setattr(Config, 'EXERCISE_EXPLANATIONS_ENABLED', True)
    monkeypatch.setattr(Config, 'EXERCISE_EXPLANATION_MODEL', 'primary/model')
    monkeypatch.setattr(Config, 'EXERCISE_EXPLANATION_FALLBACK_MODEL', 'fallback/model')
    yield
    xe.reset_state()


class _Query:
    def __init__(self, db, name):
        self.db, self.name, self.filters, self.row = db, name, [], None

    def select(self, *_a):
        return self

    def eq(self, col, val):
        self.filters.append((col, {val}))
        return self

    def in_(self, col, vals):
        self.filters.append((col, set(vals)))
        return self

    def limit(self, _n):
        return self

    def upsert(self, row, on_conflict=None):
        self.row = row
        return self

    def execute(self):
        self.db.calls.append(self.name)
        if self.name in self.db.broken:
            raise RuntimeError('relation "exercise_explanations" does not exist')
        if self.row is not None:
            self.db.upserts.append(dict(self.row))
            return SimpleNamespace(data=[self.row])
        rows = [dict(r) for r in self.db.tables.get(self.name, [])
                if all(r.get(c) in vals for c, vals in self.filters)]
        return SimpleNamespace(data=rows)


class FakeDB:
    def __init__(self, tables=None, broken=()):
        self.tables, self.broken = tables or {}, set(broken)
        self.calls, self.upserts = [], []

    def table(self, name):
        return _Query(self, name)


def _llm(answers):
    """call_llm stand-in: answers per model, recording calls."""
    calls = []

    def fake(prompt, **kw):
        calls.append(kw['model'])
        ans = answers.get(kw['model'])
        if isinstance(ans, Exception):
            raise ans
        return copy.deepcopy(ans)
    fake.calls = calls
    return fake


def _item(eid=EID, version=0, c=None):
    return {'exercise_id': eid, 'sense_id': 35443, 'exercise_type': 'spot_incorrect_sentence',
            'content_version': version, 'content': c if c is not None else content()}


# ---------------------------------------------------------------------------
# Prompt and validation
# ---------------------------------------------------------------------------

def test_the_prompt_fixes_the_key_and_asks_in_the_learners_language():
    system, user = xe.build_prompt(SENTENCES, JA, EN)
    assert 'Japanese teacher' in system and 'native language is English' in system
    assert '3. [ERROR] 人間は言葉が使う。' in user and '1. [CORRECT]' in user
    assert '助詞：他動詞「使う」' in user                     # the stored note is a hint
    assert 'do not change that judgement' in user
    assert 'write in English' in user


def test_parse_keeps_one_entry_per_sentence_and_corrections_only_on_the_wrong_one():
    out = xe.parse(model_answer(), SENTENCES, EN)
    assert [e['is_correct'] for e in out] == [True, True, False, True]
    assert out[1]['correction'] is None                      # a right sentence needs no fix
    assert out[2]['correction'] == '人間は言葉を使う。'
    assert [e['text'] for e in out] == [s['text'] for s in SENTENCES]


@pytest.mark.parametrize('answer', [
    {'sentences': model_answer()['sentences'][:3]},                          # one missing
    model_answer(_2={'explanation': ''}),                                    # empty
    model_answer(_4={'explanation': '形容詞「優しい」が名詞を修飾している。'}),  # not English
    'not json',
])
def test_parse_rejects_unusable_answers(answer):
    assert xe.parse(answer, SENTENCES, EN) is None


def test_parse_reorders_by_index():
    shuffled = model_answer()
    shuffled['sentences'].reverse()
    out = xe.parse(shuffled, SENTENCES, EN)
    assert out[2]['meaning'] == 'Humans use language.' and out[2]['correction']


def test_the_fallback_model_answers_when_the_primary_is_unusable(monkeypatch):
    fake = _llm({'primary/model': {'sentences': []}, 'fallback/model': model_answer()})
    monkeypatch.setattr('services.llm_service.call_llm', fake)
    payload, model = xe.generate(content(), JA, EN, EID)
    assert model == 'fallback/model' and fake.calls == ['primary/model', 'fallback/model']
    assert len(payload['sentences']) == 4


def test_no_usable_answer_gives_none(monkeypatch):
    monkeypatch.setattr('services.llm_service.call_llm',
                        _llm({'primary/model': RuntimeError('down'), 'fallback/model': 'junk'}))
    assert xe.generate(content(), JA, EN, EID) is None


def test_an_item_with_no_wrong_sentence_is_not_explainable():
    assert xe.sentences_of({'sentences': [{'is_correct': True, 'text': 'a'},
                                          {'is_correct': True, 'text': 'b'}]}) is None
    assert xe.generate({'sentences': []}, JA, EN) is None


# ---------------------------------------------------------------------------
# Serving
# ---------------------------------------------------------------------------

def _wait_idle(timeout=2.0):
    end = time.time() + timeout
    while time.time() < end:
        with xe._lock:
            if not xe._inflight:
                return
        time.sleep(0.01)
    raise AssertionError('generation still running')


def test_cached_rows_are_attached_aligned_with_the_sentences():
    payload = {'sentences': xe.parse(model_answer(), SENTENCES, EN)}
    db = FakeDB({'exercise_explanations': [
        {'exercise_id': EID, 'nl_language_id': EN, 'content_version': 0, 'payload': payload}]})
    items = [_item(), {'exercise_id': 'x', 'exercise_type': 'cloze_completion', 'content': {}}]
    assert xe.prepare_items(db, items, language_id=JA, nl_language_id=EN) == 0
    c = items[0]['content']
    assert [e['meaning'] for e in c['option_explanations']][3] == 'He is a kind person.'
    assert c['option_explanations'][2]['correction'] == '人間は言葉を使う。'
    assert c['explanation_language'] == 'en'
    assert items[1]['content'] == {}


def test_missing_or_stale_rows_are_written_in_the_background(monkeypatch):
    fake = _llm({'primary/model': model_answer()})
    monkeypatch.setattr('services.llm_service.call_llm', fake)
    stale = {'sentences': [dict(e, text='old') for e in model_answer()['sentences']]}
    db = FakeDB({'exercise_explanations': [
        {'exercise_id': EID, 'nl_language_id': EN, 'content_version': 0, 'payload': stale}]})
    items = [_item()]
    assert xe.prepare_items(db, items, language_id=JA, nl_language_id=EN) == 1
    assert 'option_explanations' not in items[0]['content']
    _wait_idle()
    assert db.upserts and db.upserts[0]['exercise_id'] == EID
    assert db.upserts[0]['nl_language_id'] == EN and db.upserts[0]['model'] == 'primary/model'
    # the next request is served from memory, with no table read and no model call
    db.calls.clear()
    again = [_item()]
    xe.prepare_items(db, again, language_id=JA, nl_language_id=EN)
    assert again[0]['content']['option_explanations'][1]['meaning'] == 'Humans use language.'
    assert db.calls == [] and fake.calls == ['primary/model']


def test_a_regenerated_item_is_explained_afresh(monkeypatch):
    monkeypatch.setattr('services.llm_service.call_llm', _llm({'primary/model': model_answer()}))
    payload = {'sentences': xe.parse(model_answer(), SENTENCES, EN)}
    db = FakeDB({'exercise_explanations': [
        {'exercise_id': EID, 'nl_language_id': EN, 'content_version': 0, 'payload': payload}]})
    assert xe.prepare_items(db, [_item(version=1)], language_id=JA, nl_language_id=EN) == 1
    _wait_idle()


def test_background_generation_is_capped_per_request(monkeypatch):
    monkeypatch.setattr('services.llm_service.call_llm', _llm({'primary/model': model_answer()}))
    items = [_item(eid=f'00000000-0000-0000-0000-00000000000{i}') for i in range(5)]
    assert xe.prepare_items(FakeDB(), items, language_id=JA, nl_language_id=EN, warm_limit=2) == 2
    _wait_idle()


def test_without_the_table_explanations_live_in_memory(monkeypatch):
    monkeypatch.setattr('services.llm_service.call_llm', _llm({'primary/model': model_answer()}))
    db = FakeDB(broken={'exercise_explanations'})
    xe.prepare_items(db, [_item()], language_id=JA, nl_language_id=EN)
    _wait_idle()
    db.calls.clear()
    items = [_item()]
    xe.prepare_items(db, items, language_id=JA, nl_language_id=EN)
    assert items[0]['content']['option_explanations']
    assert db.calls == []                                     # table not asked again


def test_nothing_happens_when_disabled_or_without_a_learner_language(monkeypatch):
    db = FakeDB()
    xe.prepare_items(db, [_item()], language_id=JA, nl_language_id=None)
    monkeypatch.setattr(Config, 'EXERCISE_EXPLANATIONS_ENABLED', False)
    xe.prepare_items(db, [_item()], language_id=JA, nl_language_id=EN)
    assert db.calls == []


def _exercise_db(**kw):
    return FakeDB({'exercises': [{'id': EID, 'word_sense_id': 35443, 'language_id': JA,
                                  'exercise_type': 'spot_incorrect_sentence',
                                  'content_version': 0, 'is_active': True}]}, **kw)


@pytest.fixture
def hydrate(monkeypatch):
    def fake(rows, language_id=None, drop_missing=True, **_k):
        for r in rows:
            r['content'] = content()
    monkeypatch.setattr(store, 'hydrate', fake)


def test_get_or_generate_writes_once_and_waits_for_a_running_generation(monkeypatch, hydrate):
    gate = threading.Event()

    def slow(prompt, **kw):
        gate.wait(2)
        return model_answer()
    monkeypatch.setattr('services.llm_service.call_llm', slow)
    db = _exercise_db()
    results = []
    threads = [threading.Thread(target=lambda: results.append(xe.get_or_generate(db, EID, EN)))
               for _ in range(2)]
    for t in threads:
        t.start()
    time.sleep(0.05)
    gate.set()
    for t in threads:
        t.join()
    assert [r[0] for r in results] == ['ready', 'ready']
    assert len(db.upserts) == 1                               # one generation for both
    assert results[0][1]['option_explanations'][2]['correction'] == '人間は言葉を使う。'


def test_get_or_generate_reports_pending_unsupported_and_unavailable(monkeypatch, hydrate):
    gate = threading.Event()
    monkeypatch.setattr('services.llm_service.call_llm',
                        lambda prompt, **kw: gate.wait(2) and model_answer())
    assert xe.get_or_generate(_exercise_db(), EID, EN, timeout=0.05) == ('pending', None)
    gate.set()
    _wait_idle()
    xe.reset_state()
    monkeypatch.setattr('services.llm_service.call_llm', lambda prompt, **kw: 'junk')
    assert xe.get_or_generate(_exercise_db(), EID, EN) == ('unavailable', None)
    assert xe.get_or_generate(FakeDB({'exercises': []}), EID, EN) == ('unsupported', None)


# ---------------------------------------------------------------------------
# Route
# ---------------------------------------------------------------------------

@pytest.fixture
def client(monkeypatch):
    import middleware.auth as auth
    import routes.practice as practice
    monkeypatch.setattr(auth, '_authenticate', lambda token: ({'sub': 'user-1'}, None))
    monkeypatch.setattr(practice, 'get_db', lambda: object())
    monkeypatch.setattr('services.vocabulary.gloss_lookup.get_user_definition_language_id',
                        lambda db, user_id: EN)
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.register_blueprint(practice.practice_bp, url_prefix='/api/practice')
    c = app.test_client()
    c.environ_base['HTTP_AUTHORIZATION'] = 'Bearer fake'
    return c


def test_route_returns_the_explanations_in_the_learners_language(client, monkeypatch):
    seen = {}

    def fake(db, exercise_id, nl):
        seen.update(exercise_id=exercise_id, nl=nl)
        return 'ready', {'option_explanations': [{'meaning': 'm'}], 'explanation_language': 'en'}
    monkeypatch.setattr(xe, 'get_or_generate', fake)
    resp = client.get(f'/api/practice/explanations/{EID}')
    body = resp.get_json()
    assert resp.status_code == 200 and body['state'] == 'ready'
    assert body['option_explanations'] == [{'meaning': 'm'}] and seen == {'exercise_id': EID, 'nl': EN}


def test_route_rejects_a_non_uuid(client):
    assert client.get('/api/practice/explanations/not-a-uuid').status_code == 400
