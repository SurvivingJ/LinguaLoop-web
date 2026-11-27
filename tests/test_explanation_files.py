"""Pre-written exercise explanations in Storage files (services/explanation_files.py)
and their place in serving (services/exercise_explanations.py): memory -> stored
notes -> Storage file -> table -> model.

Offline: the conftest installs an empty ``InMemoryBackend`` per test (and
``store.reset_state()`` also forgets this module's caches); the table is a
small fake; ``call_llm`` is patched.
"""

from __future__ import annotations

import copy
import json
import logging
import time
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from config import Config
from services import exercise_explanations as xe
from services import explanation_files as xf
from services.exercise_content import store
from services.exercise_content.backends import InMemoryBackend, StoredObject
from services.exercise_content.store import ContentStorageError

ZH, EN, JA = 1, 2, 3
SENSE, SENSE2 = 35443, 35444
EID = '9da9df5c-7a75-4bae-83a6-fbe77b57cf27'
EID2 = '0b0c6a35-3c3e-4a4e-9d0e-6f3b1e2f8a11'
P = xe.PROMPT_VERSION
LOGGER = 'services.explanation_files'

SENTENCES = [
    {'is_correct': True, 'text': 'これは心理学に基づいた人間の無意識の反応を利用したものだ。'},
    {'is_correct': True, 'text': '人間は言葉を使う。'},
    {'is_correct': False, 'text': '人間は言葉が使う。',
     'error_description': '助詞：他動詞「使う」の対象は「を」で示す。「が」は誤り。'},
    {'is_correct': True, 'text': '彼は優しい人間だ。'},
]


def answer():
    return {'sentences': [
        {'index': 1, 'meaning': 'This uses unconscious human reactions based on psychology.',
         'explanation': '「に基づいた」 means "based on" and modifies the noun phrase.'},
        {'index': 2, 'meaning': 'Humans use language.',
         'explanation': '「を」 marks 「言葉」 as the object of the transitive verb 「使う」.'},
        {'index': 3, 'meaning': 'Humans use language.',
         'explanation': 'The object of 「使う」 takes 「を」, not 「が」.',
         'correction': '人間は言葉を使う。'},
        {'index': 4, 'meaning': 'He is a kind person.',
         'explanation': 'The i-adjective 「優しい」 modifies 「人間」 directly.'},
    ]}


def payload(prompt_version=P):
    return {'sentences': xe.parse(answer(), SENTENCES, EN), 'prompt_version': prompt_version}


def entry(version=0, p=None, model='batch/model'):
    return {'content_version': version, 'model': model, 'payload': p if p is not None else payload()}


def spot(eid=EID, version=0, sense=SENSE, *, id_key='exercise_id', sense_key='sense_id'):
    return {id_key: eid, sense_key: sense, 'exercise_type': xe.SPOT, 'content_version': version,
            'content': {'sentences': copy.deepcopy(SENTENCES)}}


def path(sense=SENSE, prompt=P):
    return xf.file_path(JA, sense, EN, prompt)


def seed_file(mem, exercises, sense=SENSE, prompt=P):
    mem.seed(path(sense, prompt), xf.encode(JA, sense, EN, prompt, exercises))


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


@pytest.fixture
def model(monkeypatch):
    calls = []

    def fake(prompt, **kw):
        calls.append(kw['model'])
        return answer()
    monkeypatch.setattr('services.llm_service.call_llm', fake)
    return calls


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
        if self.db.delay:
            time.sleep(self.db.delay)
        if self.name in self.db.broken:
            raise RuntimeError(f'relation "{self.name}" does not exist')
        if self.row is not None:
            self.db.upserts.append(dict(self.row))
            return SimpleNamespace(data=[self.row])
        return SimpleNamespace(data=[dict(r) for r in self.db.tables.get(self.name, [])
                                     if all(r.get(c) in v for c, v in self.filters)])


class FakeDB:
    def __init__(self, tables=None, broken=(), delay=0.0):
        self.tables, self.broken, self.delay = tables or {}, set(broken), delay
        self.calls, self.upserts = [], []

    def table(self, name):
        return _Query(self, name)


def _row(eid=EID, version=0, p=None):
    return {'exercise_id': eid, 'nl_language_id': EN, 'content_version': version,
            'payload': p if p is not None else payload()}


def _wait_idle(timeout=2.0):
    end = time.time() + timeout
    while time.time() < end:
        with xe._lock:
            if not xe._inflight:
                return
        time.sleep(0.01)
    raise AssertionError('generation still running')


def _warnings(caplog):
    return [r.getMessage() for r in caplog.records
            if r.name == LOGGER and r.levelno == logging.WARNING]


# ---------------------------------------------------------------------------
# Path and codec
# ---------------------------------------------------------------------------

def test_the_path_names_both_languages_by_code():
    assert xf.file_path(JA, 35443, EN, 2) == 'explanations/ja/35443.en.p2.json'
    assert xf.file_path(ZH, 7, JA, 1) == 'explanations/zh/7.ja.p1.json'
    assert xf.FORMAT == 1


@pytest.mark.parametrize('args', [(9, 1, EN, 2), (JA, 1, 0, 2), (True, 1, EN, 2),
                                  (JA, -1, EN, 2), (JA, '5', EN, 2), (JA, 1, EN, None)])
def test_the_path_refuses_unknown_ids(args):
    with pytest.raises(ValueError):
        xf.file_path(*args)


def test_encode_and_decode_round_trip():
    data = xf.encode(JA, SENSE, EN, P, {EID2: entry(1), EID: entry(0, model=None)})
    text = data.decode('utf-8')
    assert '人間は言葉を使う。' in text                              # ensure_ascii=False
    assert data == json.dumps(json.loads(text), ensure_ascii=False,
                              separators=(',', ':')).encode('utf-8')   # compact
    doc = xf.decode(data)
    assert list(doc) == ['format', 'language_id', 'sense_id', 'nl_language_id',
                         'prompt_version', 'exercises']
    assert doc == {'format': 1, 'language_id': JA, 'sense_id': SENSE, 'nl_language_id': EN,
                   'prompt_version': P, 'exercises': {
                       EID: {'content_version': 0, 'model': None, 'payload': payload()},
                       EID2: {'content_version': 1, 'model': 'batch/model', 'payload': payload()}}}
    # the same input always gives the same bytes (exercises in id order)
    assert xf.encode(JA, SENSE, EN, P, {EID: entry(0, model=None), EID2: entry(1)}) == data


@pytest.mark.parametrize('exercises', [
    {},                                                               # could never be replaced
    {EID: entry(p=payload(P - 1))},                                   # another prompt version
    {EID: entry(p={'sentences': [], 'prompt_version': P})},
    {EID: {'content_version': -1, 'payload': payload()}},
    {EID: {'content_version': '0', 'payload': payload()}},
    {EID: {'content_version': 0, 'model': 5, 'payload': payload()}},
    {EID: {'content_version': 0, 'payload': 'text'}},
    {'': entry()},
])
def test_encode_refuses_what_could_never_be_served(exercises):
    with pytest.raises(ValueError):
        xf.encode(JA, SENSE, EN, P, exercises)


def _doc(**override):
    doc = json.loads(xf.encode(JA, SENSE, EN, P, {EID: entry()}))
    doc.update(override)
    return json.dumps(doc).encode()


@pytest.mark.parametrize('data', [
    b'\xff\xfe', b'not json', b'[]', _doc(format=2), _doc(language_id=9), _doc(sense_id='1'),
    _doc(exercises=[]), _doc(exercises={EID: {'payload': {}}}),
    _doc(exercises={EID: {'content_version': 0, 'payload': None}}),
])
def test_decode_rejects_malformed_files_with_one_warning(data, caplog):
    with caplog.at_level(logging.WARNING, logger=LOGGER):
        assert xf.decode(data) is None
    assert len(_warnings(caplog)) == 1


# ---------------------------------------------------------------------------
# write_file
# ---------------------------------------------------------------------------

def test_write_file_writes_once_and_never_overwrites(mem):
    assert xf.write_file(JA, SENSE, EN, P, {EID: entry()}) == 'written'
    first = mem.objects()[path()]
    assert xf.decode(first)['exercises'][EID]['content_version'] == 0
    assert xf.write_file(JA, SENSE, EN, P, {EID: entry(1), EID2: entry()}) == 'exists'
    assert mem.objects()[path()] == first                     # left exactly as it was
    assert mem.calls_for('put') == [path(), path()] and mem.calls_for('delete') == []


def test_write_file_validates_first_and_lets_storage_errors_through(mem):
    with pytest.raises(ValueError):
        xf.write_file(9, SENSE, EN, P, {EID: entry()})
    with pytest.raises(ValueError):
        xf.write_file(JA, SENSE, EN, P, {})
    assert mem.calls == []
    mem.fail_next('put', ContentStorageError('HTTP 503'))
    with pytest.raises(ContentStorageError):
        xf.write_file(JA, SENSE, EN, P, {EID: entry()})


def test_a_file_written_after_a_miss_is_read_at_once(mem):
    assert xf.read_for_senses(JA, [SENSE], EN, P) == {}       # missing: negative-cached
    assert xf.write_file(JA, SENSE, EN, P, {EID: entry()}) == 'written'
    assert set(xf.read_for_senses(JA, [SENSE], EN, P)) == {EID}
    assert mem.calls_for('get') == [path()]                   # the write warmed the cache


# ---------------------------------------------------------------------------
# read_for_senses
# ---------------------------------------------------------------------------

def test_read_merges_the_files_and_caches_their_bytes(mem):
    seed_file(mem, {EID: entry(0)})
    seed_file(mem, {EID2: entry(3, model=None)}, sense=SENSE2)
    got = xf.read_for_senses(JA, [SENSE, SENSE2, SENSE, str(SENSE2), None, 'x'], EN, P)
    assert got == {EID: entry(0), EID2: entry(3, model=None)}
    assert sorted(mem.calls_for('get')) == sorted([path(), path(SENSE2)])
    assert all(name.startswith('explain-file') for name in mem.call_threads)

    got[EID]['payload']['sentences'].clear()                  # callers own what they get
    mem.clear_calls()
    again = xf.read_for_senses(JA, [SENSE, SENSE2], EN, P)
    assert again == {EID: entry(0), EID2: entry(3, model=None)}
    assert mem.calls == []                                    # served from the byte cache


def test_a_missing_file_is_not_asked_for_again_for_ten_minutes(mem, monkeypatch):
    clock = [1000.0]
    monkeypatch.setattr(xf, '_now', lambda: clock[0])
    assert xf.NEGATIVE_TTL_S == 600
    assert xf.read_for_senses(JA, [SENSE], EN, P) == {}
    seed_file(mem, {EID: entry()})                            # e.g. the batch, elsewhere
    clock[0] += xf.NEGATIVE_TTL_S - 1
    assert xf.read_for_senses(JA, [SENSE], EN, P) == {}
    assert mem.calls_for('get') == [path()]
    clock[0] += 2
    assert set(xf.read_for_senses(JA, [SENSE], EN, P)) == {EID}
    assert mem.calls_for('get') == [path(), path()]


def test_files_still_in_flight_at_the_deadline_count_as_missing(mem, caplog):
    seed_file(mem, {EID: entry()})
    mem.latency_s = {'get': 0.5}
    started = time.monotonic()
    with caplog.at_level(logging.WARNING, logger=LOGGER):
        assert xf.read_for_senses(JA, [SENSE], EN, P, deadline_s=0.05) == {}
    assert time.monotonic() - started < 0.4
    assert len(_warnings(caplog)) == 1 and 'late=1' in _warnings(caplog)[0]
    # the late GET finishes in the background and warms the cache for the next call
    end = time.monotonic() + 3
    while time.monotonic() < end and path() not in xf._lru:
        time.sleep(0.02)
    mem.latency_s = 0.0
    mem.clear_calls()
    assert set(xf.read_for_senses(JA, [SENSE], EN, P)) == {EID}
    assert mem.calls == []


def test_storage_failures_never_raise_and_are_retried_by_the_next_call(mem, caplog):
    seed_file(mem, {EID: entry()})
    mem.fail_next('get', ContentStorageError('connection reset'))
    assert set(xf.read_for_senses(JA, [SENSE], EN, P)) == {EID}      # one retry inside
    xf.reset_cache()
    mem.fail_next('get', ContentStorageError('HTTP 503'))
    mem.fail_next('get', ContentStorageError('HTTP 503'))
    with caplog.at_level(logging.WARNING, logger=LOGGER):
        assert xf.read_for_senses(JA, [SENSE], EN, P) == {}
    assert len(_warnings(caplog)) == 1 and 'failed=1' in _warnings(caplog)[0]
    assert set(xf.read_for_senses(JA, [SENSE], EN, P)) == {EID}      # not negative-cached


def test_corrupt_or_mislabelled_files_are_ignored(mem, caplog):
    mem.seed(path(), b'{"format": 1, "exercises": ')
    mem.seed(path(SENSE2), xf.encode(JA, 99, EN, P, {EID2: entry()}))  # another sense's file
    with caplog.at_level(logging.WARNING, logger=LOGGER):
        assert xf.read_for_senses(JA, [SENSE, SENSE2], EN, P) == {}
    assert len(_warnings(caplog)) == 1 and 'malformed=2' in _warnings(caplog)[0]
    mem.clear_calls()
    assert xf.read_for_senses(JA, [SENSE, SENSE2], EN, P) == {}
    assert mem.calls == []                                    # not fetched again soon


def test_nothing_is_read_without_storage(monkeypatch):
    store.set_backend(None)
    monkeypatch.setattr(Config, 'SUPABASE_URL', '')
    monkeypatch.setattr(Config, 'SUPABASE_SERVICE_ROLE_KEY', '')
    monkeypatch.setattr(store, 'backend', lambda: pytest.fail('no backend without Storage'))
    assert xf.read_for_senses(JA, [SENSE], EN, P) == {}
    assert xf.read_for_senses(9, [SENSE], EN, P) == {}        # unknown language: {} too
    # serving still works from the table
    db = FakeDB({'exercise_explanations': [_row()]})
    items = [spot()]
    assert xe.prepare_items(db, items, language_id=JA, nl_language_id=EN) == 0
    assert items[0]['content']['option_explanations'][2]['correction'] == '人間は言葉を使う。'


def test_another_backend_gets_fresh_caches(mem):
    seed_file(mem, {EID: entry()})
    assert set(xf.read_for_senses(JA, [SENSE], EN, P)) == {EID}
    store.set_backend(InMemoryBackend())                      # has no file
    assert xf.read_for_senses(JA, [SENSE], EN, P) == {}
    store.set_backend(mem)
    xe.reset_state()                                          # also forgets the files
    mem.clear_calls()
    assert set(xf.read_for_senses(JA, [SENSE], EN, P)) == {EID}
    assert mem.calls_for('get') == [path()]


# ---------------------------------------------------------------------------
# Serving: prepare_items / prefetch
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('broken', [(), ('exercise_explanations',)])
def test_prepare_items_serves_a_pre_written_explanation(mem, no_model, broken):
    seed_file(mem, {EID: entry()})
    db = FakeDB(broken=broken)                                # the table has nothing / is down
    items = [spot(), {'exercise_id': 'x', 'sense_id': 1, 'exercise_type': 'cloze_completion',
                      'content': {}}]
    assert xe.prepare_items(db, items, language_id=JA, nl_language_id=EN) == 0
    notes = items[0]['content']['option_explanations']
    assert [n['meaning'] for n in notes][3] == 'He is a kind person.'
    assert notes[2]['correction'] == '人間は言葉を使う。'
    assert items[0]['content']['explanation_language'] == 'en' and items[1]['content'] == {}
    assert db.upserts == [] and mem.calls_for('put') == []
    assert mem.calls_for('get') == [path()]                   # the cloze item's sense: no read
    # remembered: the next request reads neither Storage nor the table
    mem.clear_calls()
    db.calls.clear()
    again = [spot()]
    assert xe.prepare_items(db, again, language_id=JA, nl_language_id=EN) == 0
    assert again[0]['content']['option_explanations'] == notes
    assert mem.calls == [] and db.calls == []


def test_new_word_drill_rows_use_word_sense_id(mem, no_model):
    seed_file(mem, {EID: entry()})
    row = spot(id_key='id', sense_key='word_sense_id')
    assert xe.prepare_items(FakeDB(), [row], language_id=JA, nl_language_id=EN, id_key='id') == 0
    assert row['content']['option_explanations'][2]['correction'] == '人間は言葉を使う。'


def test_prefetch_reads_the_files_and_the_table_together(mem, no_model):
    seed_file(mem, {EID: entry()})
    mem.latency_s = {'get': 0.4}
    db = FakeDB({'exercise_explanations': [_row(EID2)]}, delay=0.4)
    items = [spot(), spot(EID2, sense=SENSE2),
             {'exercise_id': 'x', 'sense_id': 9, 'exercise_type': 'cloze_completion'}]
    ids_only = [{k: v for k, v in i.items() if k != 'content'} for i in items]
    started = time.monotonic()
    pf = xe.prefetch(db, ids_only, language_id=JA, nl_language_id=EN)
    assert time.monotonic() - started < 0.7                   # overlapped, not 0.4 + 0.4
    assert isinstance(pf, xe.Prefetched)
    assert set(pf.files) == {EID} and set(pf.rows) == {EID2}
    assert sorted(mem.calls_for('get')) == sorted([path(), path(SENSE2)])
    assert db.calls == ['exercise_explanations']

    mem.clear_calls()
    db.calls.clear()
    assert xe.prepare_items(db, items, language_id=JA, nl_language_id=EN, prefetched=pf) == 0
    assert items[0]['content']['option_explanations'][2]['correction'] == '人間は言葉を使う。'
    assert items[1]['content']['option_explanations'][1]['meaning'] == 'Humans use language.'
    assert mem.calls == [] and db.calls == []                 # no second round trip


def test_prefetch_with_nothing_explainable_reads_nothing(mem):
    db = FakeDB()
    assert xe.prefetch(db, [{'exercise_id': 'x', 'sense_id': 9,
                             'exercise_type': 'cloze_completion'}],
                       language_id=JA, nl_language_id=EN) is None
    assert xe.prefetch(db, [spot()], language_id=JA, nl_language_id=None) is None
    assert mem.calls == [] and db.calls == []


def test_a_session_attaches_pre_written_explanations(mem, no_model, monkeypatch):
    """Through ``_hydrate_items``: the prefetch result reaches ``prepare_items``."""
    from services.practice_session_service import PracticeSessionService
    from services.vocabulary_ladder import definition_serving
    monkeypatch.setattr(definition_serving, 'prepare', lambda *a, **k: None)
    monkeypatch.setattr(definition_serving, 'apply', lambda plan, items: None)
    mem.seed(store.content_path(JA, SENSE, 4),
             store.encode_sense_file(SENSE, JA, 4, {EID: {'sentences': SENTENCES}}))
    seed_file(mem, {EID: entry(version=4)})
    svc = PracticeSessionService.__new__(PracticeSessionService)
    svc.db = FakeDB()
    payload_ = {'items': [{'exercise_id': EID, 'sense_id': SENSE, 'exercise_type': xe.SPOT,
                           'content_version': 4}]}
    svc._hydrate_items(payload_, JA, nl_language_id=EN)
    content = payload_['items'][0]['content']
    assert content['option_explanations'][2]['correction'] == '人間は言葉を使う。'
    assert svc.db.upserts == []


def test_a_file_written_for_another_content_version_is_not_served(mem, model):
    seed_file(mem, {EID: entry(version=0)})
    db = FakeDB()
    items = [spot(version=1)]                                 # the content changed since
    assert xe.prepare_items(db, items, language_id=JA, nl_language_id=EN) == 1
    assert 'option_explanations' not in items[0]['content']
    _wait_idle()
    assert model == ['primary/model']
    # written lazily to the table, as before, never to Storage
    assert db.upserts and db.upserts[0]['content_version'] == 1
    assert mem.calls_for('put') == []


def _raw_file(prompt_in_path, prompt_in_payload):
    return json.dumps({'format': 1, 'language_id': JA, 'sense_id': SENSE, 'nl_language_id': EN,
                       'prompt_version': prompt_in_path,
                       'exercises': {EID: entry(p=payload(prompt_in_payload))}},
                      ensure_ascii=False).encode('utf-8')


@pytest.mark.parametrize('prompt_in_path, prompt_in_payload', [(P - 1, P - 1), (P, P - 1)])
def test_files_of_an_older_prompt_are_not_served(mem, model, prompt_in_path, prompt_in_payload):
    mem.seed(path(prompt=prompt_in_path), _raw_file(prompt_in_path, prompt_in_payload))
    items = [spot()]
    assert xe.prepare_items(FakeDB(), items, language_id=JA, nl_language_id=EN) == 1
    assert 'option_explanations' not in items[0]['content']
    assert mem.calls_for('get') == [path()]                   # only the current prompt's path
    _wait_idle()


# ---------------------------------------------------------------------------
# Serving: get_or_generate
# ---------------------------------------------------------------------------

def _exercise_db(tables=None):
    return FakeDB({'exercises': [{'id': EID, 'word_sense_id': SENSE, 'language_id': JA,
                                  'exercise_type': xe.SPOT, 'content_version': 0,
                                  'is_active': True}], **(tables or {})})


def _seed_content(mem, version=0):
    mem.seed(store.content_path(JA, SENSE, version),
             store.encode_sense_file(SENSE, JA, version, {EID: {'sentences': SENTENCES}}))


def test_get_or_generate_serves_the_pre_written_file(mem, no_model):
    _seed_content(mem)
    seed_file(mem, {EID: entry()})
    db = _exercise_db()
    state, shaped = xe.get_or_generate(db, EID, EN)
    assert state == 'ready'
    assert shaped['option_explanations'][2]['correction'] == '人間は言葉を使う。'
    assert shaped['explanation_language'] == 'en'
    assert db.calls == ['exercises'] and db.upserts == []     # the table was not needed
    mem.clear_calls()
    assert xe.get_or_generate(db, EID, EN)[0] == 'ready'
    assert path() not in mem.calls_for('get')                 # from memory now


def test_get_or_generate_falls_back_to_the_table_when_the_file_is_stale(mem, no_model):
    _seed_content(mem)
    seed_file(mem, {EID: entry(version=5)})
    db = _exercise_db(tables={'exercise_explanations': [_row()]})
    state, shaped = xe.get_or_generate(db, EID, EN)
    assert state == 'ready' and shaped['option_explanations'][1]['meaning'] == 'Humans use language.'
    assert db.calls == ['exercises', 'exercise_explanations']


# ---------------------------------------------------------------------------
# The orphan-file sweep leaves explanation files alone
# ---------------------------------------------------------------------------

class _LiveDB:
    """The live-versions RPC only: sense 6 at version 0 in every language."""

    def rpc(self, name, params):
        assert name == 'exercise_content_live_versions'
        return SimpleNamespace(execute=lambda: SimpleNamespace(data={'6': [0]}))

    def table(self, name):
        raise AssertionError(f'the sweep must not read table {name}')


def test_the_orphan_sweep_never_lists_or_deletes_explanation_files(mem, tmp_path):
    from scripts import sweep_exercise_content as sweep
    now = datetime(2026, 12, 1, tzinfo=timezone.utc)
    old = now - timedelta(days=30)
    kept = [xf.file_path(lang, 5, nl, P) for lang in (ZH, EN, JA) for nl in (ZH, EN, JA)]
    for p in kept:
        mem.seed(p, b'{}', created_at=old)
    mem.seed('ja/5.v0.json', b'{}', created_at=old)           # an orphan content file
    mem.clear_calls()
    code = sweep.main(['--language', 'all', '--apply', '--report', str(tmp_path / 'r.json')],
                      db=_LiveDB(), now=lambda: now)
    assert code == 0
    assert mem.calls_for('delete') == ['ja/5.v0.json']
    assert all(mem.exists(p) for p in kept)
    assert sorted(mem.calls_for('list')) == ['en/', 'ja/', 'zh/']

    # even a backend that listed recursively would not make them candidates
    listed = [StoredObject(p, 2, old) for p in kept] + [StoredObject('ja/5.v0.json', 2, old)]
    groups = sweep.classify(listed, {}, 'ja', now, timedelta(hours=24))
    assert [o.path for o in groups['delete']] == ['ja/5.v0.json']


def test_a_background_job_serves_a_file_the_request_read_missed(mem, no_model):
    """Review finding 6 (2026-11-27): when the request's file read missed its deadline the
    item was queued for generation; the job now reads the sense's file first and pays
    for no model call when the pre-written entry is there."""
    seed_file(mem, {EID: entry()})
    item = spot()
    fut = xe._start(None, EID, item['content'], 0, JA, EN, xe.SPOT, SENSE)
    got = fut.result(timeout=5)
    assert got == payload()
    again = [spot()]
    xe.prepare_items(None, again, language_id=JA, nl_language_id=EN, warm_limit=0)
    assert again[0]['content']['option_explanations'][2]['correction'] == '人間は言葉を使う。'


def test_a_background_job_generates_when_the_file_is_for_another_content_version(mem, model):
    seed_file(mem, {EID: entry(version=3)})
    item = spot(version=0)
    got = xe._start(None, EID, item['content'], 0, JA, EN, xe.SPOT, SENSE).result(timeout=5)
    assert got['sentences'][0]['meaning'] == answer()['sentences'][0]['meaning']


# ---------------------------------------------------------------------------
# kinds: 'p' (sentence types) and 'o' (word-option types), 2026-11-27
# ---------------------------------------------------------------------------

def test_kind_is_in_the_path_and_only_an_o_file_records_it():
    assert xf.file_path(JA, 35443, EN, 1, 'o') == 'explanations/ja/35443.en.o1.json'
    assert xf.file_path(JA, 35443, EN, 2) == xf.file_path(JA, 35443, EN, 2, 'p')
    with pytest.raises(ValueError):
        xf.file_path(JA, 35443, EN, 1, 'x')
    p_doc = json.loads(xf.encode(JA, SENSE, EN, P, {EID: entry()}))
    o_doc = json.loads(xf.encode(JA, SENSE, EN, P, {EID: entry()}, 'o'))
    assert 'kind' not in p_doc and o_doc['kind'] == 'o'
    assert list(o_doc) == ['format', 'language_id', 'sense_id', 'nl_language_id',
                           'prompt_version', 'kind', 'exercises']


def test_both_kinds_of_one_sense_live_side_by_side(mem):
    assert xf.write_file(JA, SENSE, EN, P, {EID: entry()}) == 'written'
    assert xf.write_file(JA, SENSE, EN, P, {EID2: entry(1)}, kind='o') == 'written'
    assert set(xf.read_for_senses(JA, [SENSE], EN, P)) == {EID}
    assert set(xf.read_for_senses(JA, [SENSE], EN, P, kind='o')) == {EID2}


def test_read_files_fetches_both_kinds_under_one_deadline(mem):
    seed_file(mem, {EID: entry()})
    mem.seed(xf.file_path(JA, SENSE2, EN, 1, 'o'), xf.encode(JA, SENSE2, EN, 1, {EID2: entry(p={
        'sentences': [{'text': 'を'}], 'prompt_version': 1})}, 'o'))
    got = xf.read_files(JA, EN, [(SENSE, 'p', P), (SENSE2, 'o', 1), (SENSE2, 'o', 1), ('x', 'o', 1)])
    assert set(got) == {EID, EID2}
    assert sorted(mem.calls_for('get')) == sorted([path(), xf.file_path(JA, SENSE2, EN, 1, 'o')])


def test_a_file_of_the_other_kind_at_a_path_is_refused(mem, caplog):
    # a 'p' document stored where an 'o' file belongs names the wrong kind
    mem.seed(xf.file_path(JA, SENSE, EN, P, 'o'), xf.encode(JA, SENSE, EN, P, {EID: entry()}))
    with caplog.at_level(logging.WARNING, logger=LOGGER):
        assert xf.read_for_senses(JA, [SENSE], EN, P, kind='o') == {}
    assert 'names another sense, language, kind or prompt version' in caplog.text


def test_read_files_with_a_bad_kind_reads_nothing(mem, caplog):
    seed_file(mem, {EID: entry()})
    with caplog.at_level(logging.WARNING, logger=LOGGER):
        assert xf.read_files(JA, EN, [(SENSE, 'q', P)]) == {}
    assert 'bad_arguments' in caplog.text
