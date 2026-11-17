"""TASK-978 — the ``storage`` / ``shadow`` read path and ``fetch_sense`` (ADR-047 §5, §9).

Runs through the public facade (``store.hydrate`` / ``store.fetch_sense``)
with an ``InMemoryBackend`` installed by ``store.set_backend`` and a local fake
PostgREST client for the DB fallback. Fully offline.
"""

from __future__ import annotations

import ast
import copy
import logging
import threading
import time
import uuid
from pathlib import Path

import pytest
from postgrest.exceptions import APIError

from config import Config
from services.exercise_content import reader, shadow, store
from services.exercise_content.backends import InMemoryBackend
from services.exercise_content.store import ContentStorageError

LOGGER = 'services.exercise_content'
PACKAGE = Path(__file__).resolve().parents[1] / 'services' / 'exercise_content'


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _uuid() -> str:
    return str(uuid.uuid4())


def _mode(monkeypatch, source: str, *, fallback: bool = False) -> InMemoryBackend:
    monkeypatch.setattr(Config, 'SUPABASE_URL', 'https://fake.supabase.co')
    monkeypatch.setattr(Config, 'SUPABASE_SERVICE_ROLE_KEY', 'fake-service-role-key')
    monkeypatch.setattr(Config, 'EXERCISE_CONTENT_SOURCE', source)
    monkeypatch.setattr(Config, 'EXERCISE_CONTENT_WRITE', 'dual')
    monkeypatch.setattr(Config, 'EXERCISE_CONTENT_DB_FALLBACK', fallback)
    mem = InMemoryBackend()
    store.set_backend(mem)
    return mem


def _seed(mem: InMemoryBackend, sense: int, exercises: dict, *, version: int = 0,
          lang: int = 1) -> None:
    mem.seed(store.content_path(lang, sense, version),
             store.encode_sense_file(sense, lang, version, exercises))


def _item(eid: str, sense: int, *, version=0, lang=1, **extra) -> dict:
    item = {'id': eid, 'word_sense_id': sense, 'content_version': version,
            'language_id': lang, 'exercise_type': 'cloze_completion'}
    item.update(extra)
    return item


def _content(n: int) -> dict:
    return {'sentence': f'sentence {n}', 'options': [f'a{n}', f'b{n}'], 'answer': n,
            'hant': {'sentence': f'句子 {n}'}}


def _warnings(caplog, prefix: str) -> list[logging.LogRecord]:
    return [r for r in caplog.records if r.name == LOGGER and r.levelno == logging.WARNING
            and r.getMessage().startswith(prefix)]


def _errors(caplog, prefix: str = '') -> list[logging.LogRecord]:
    return [r for r in caplog.records if r.name == LOGGER and r.levelno == logging.ERROR
            and r.getMessage().startswith(prefix)]


class _Resp:
    def __init__(self, data):
        self.data = data


class FallbackDB:
    """Fake PostgREST client for ``table('exercises').select('id, content').in_(...)``."""

    def __init__(self, rows: dict[str, dict] | None = None, error: BaseException | None = None):
        self.rows = rows or {}
        self.error = error
        self.calls: list[tuple] = []

    def table(self, name):
        db = self
        steps = [('table', name)]

        class Chain:
            def select(self, columns):
                steps.append(('select', columns))
                return self

            def in_(self, column, values):
                steps.append(('in_', column, list(values)))
                return self

            def execute(self):
                db.calls.append(tuple(steps))
                if db.error is not None:
                    raise db.error
                ids = steps[-1][2]
                return _Resp([{'id': i, 'content': copy.deepcopy(db.rows[i])}
                              for i in ids if i in db.rows])

        return Chain()

    def rpc(self, *args, **kwargs):  # pragma: no cover - the reader never calls an RPC
        raise AssertionError('reader must not call an RPC')


class ExplodingDB:
    def __getattr__(self, name):
        raise AssertionError(f'unexpected db access: {name}')


# ---------------------------------------------------------------------------
# storage: basic hydration
# ---------------------------------------------------------------------------

def test_storage_fills_content_and_leaves_other_items_alone(monkeypatch):
    mem = _mode(monkeypatch, 'storage')
    a1, a2, b1, pre = _uuid(), _uuid(), _uuid(), _uuid()
    _seed(mem, 10, {a1: _content(1), a2: _content(2)})
    _seed(mem, 11, {b1: _content(3)}, version=7)
    own = {'already': 'here'}
    marker = {'kind': 'dt_error_card', 'text': 'x'}
    items = [_item(a1, 10), marker, _item(b1, 11, version=7), _item(pre, 10, content=own),
             _item(a2, 10), 'not a dict', {'id': None, 'word_sense_id': 10}]
    before_marker = copy.deepcopy(marker)

    report = store.hydrate(items)

    assert items[0]['content'] == _content(1)
    assert items[2]['content'] == _content(3)
    assert items[3]['content'] is own
    assert items[4]['content'] == _content(2)
    assert items[1] is marker and marker == before_marker
    assert items[5] == 'not a dict' and items[6] == {'id': None, 'word_sense_id': 10}
    assert report.mode == 'storage'
    assert (report.items, report.groups, report.fetched, report.cache_hits) == (4, 2, 2, 0)
    assert (report.db_fallback, report.over_cap, report.dropped) == (0, 0, 0)
    assert report.missing_ids == [] and report.elapsed_ms > 0
    assert sorted(mem.calls_for('get')) == ['zh/10.v0.json', 'zh/11.v7.json']


def test_second_call_is_served_from_the_byte_cache(monkeypatch):
    mem = _mode(monkeypatch, 'storage')
    eid = _uuid()
    _seed(mem, 10, {eid: _content(1)})
    store.hydrate([_item(eid, 10)])
    mem.clear_calls()

    items = [_item(eid, 10)]
    report = store.hydrate(items)
    assert items[0]['content'] == _content(1)
    assert (report.cache_hits, report.fetched) == (1, 0)
    assert mem.calls == []


def test_language_comes_from_the_argument_else_the_item(monkeypatch):
    mem = _mode(monkeypatch, 'storage')
    zh, ja, none = _uuid(), _uuid(), _uuid()
    _seed(mem, 10, {zh: _content(1)}, lang=1)
    _seed(mem, 10, {ja: _content(2)}, lang=3)

    items = [_item(ja, 10, lang=1)]
    store.hydrate(items, language_id=3)
    assert items[0]['content'] == _content(2)

    items = [_item(zh, 10, lang='1'), {'id': none, 'word_sense_id': 10, 'content_version': 0}]
    report = store.hydrate(items, drop_missing=False)
    assert items[0]['content'] == _content(1)
    assert items[1]['content'] is None and report.missing_ids == [none]


def test_custom_id_and_sense_keys(monkeypatch):
    mem = _mode(monkeypatch, 'storage')
    eid = _uuid()
    _seed(mem, 42, {eid: _content(9)})
    items = [{'exercise_id': eid, 'sense': 42, 'content_version': 0}]
    store.hydrate(items, language_id=1, id_key='exercise_id', sense_key='sense')
    assert items[0]['content'] == _content(9)


def test_missing_items_are_dropped_in_place_keeping_order(monkeypatch, caplog):
    caplog.set_level(logging.WARNING, logger=LOGGER)
    mem = _mode(monkeypatch, 'storage')
    keep1, gone_ex, keep2, gone_file = _uuid(), _uuid(), _uuid(), _uuid()
    _seed(mem, 10, {keep1: _content(1), keep2: _content(2)})
    marker = {'kind': 'gate_marker'}
    items = [_item(keep1, 10), _item(gone_ex, 10), marker, _item(gone_file, 99),
             _item(keep2, 10)]
    same_list = items

    report = store.hydrate(items)

    assert items is same_list
    assert [i.get('id') for i in items] == [keep1, None, keep2]
    assert items[1] is marker
    assert report.dropped == 2 and report.missing_ids == [gone_ex, gone_file]
    assert len(_warnings(caplog, 'exercise_content.missing ')) == 1


def test_drop_missing_false_sets_content_none(monkeypatch):
    mem = _mode(monkeypatch, 'storage')
    present, absent = _uuid(), _uuid()
    _seed(mem, 10, {present: _content(1)})
    items = [_item(absent, 10), _item(present, 10)]
    report = store.hydrate(items, drop_missing=False)
    assert [i['id'] for i in items] == [absent, present]
    assert items[0]['content'] is None and items[1]['content'] == _content(1)
    assert report.dropped == 0 and report.missing_ids == [absent]


@pytest.mark.parametrize('bad', [None, 'x', True, -1, 1.5])
def test_items_without_a_valid_version_go_straight_to_the_fallback(monkeypatch, bad):
    mem = _mode(monkeypatch, 'storage', fallback=True)
    eid = _uuid()
    _seed(mem, 10, {eid: _content(1)})
    db = FallbackDB({eid: _content(5)})
    items = [_item(eid, 10, version=bad)]

    report = store.hydrate(items, db=db)

    assert items[0]['content'] == _content(5)
    assert mem.calls == []
    assert report.groups == 0 and report.db_fallback == 1


def test_a_digit_string_version_is_accepted(monkeypatch):
    mem = _mode(monkeypatch, 'storage')
    eid = _uuid()
    _seed(mem, 10, {eid: _content(1)}, version=3)
    items = [_item(eid, 10, version='3')]
    store.hydrate(items)
    assert items[0]['content'] == _content(1)


# ---------------------------------------------------------------------------
# fresh objects
# ---------------------------------------------------------------------------

def test_every_item_gets_its_own_object(monkeypatch):
    mem = _mode(monkeypatch, 'storage')
    eid, other = _uuid(), _uuid()
    _seed(mem, 10, {eid: _content(1), other: _content(2)})

    items = [_item(eid, 10), _item(eid, 10), _item(other, 10)]
    store.hydrate(items)
    assert items[0]['content'] == items[1]['content'] == _content(1)
    assert items[0]['content'] is not items[1]['content']
    assert items[0]['content']['options'] is not items[1]['content']['options']

    items[0]['content']['options'].append('mutated')
    items[0]['content']['hant']['sentence'] = 'changed'
    cached = store._content_cache().get(store._cache_key(1, 10, 0))
    assert store.decode_sense_file(cached, sense_id=10, version=0)[eid] == _content(1)

    again = [_item(eid, 10)]
    store.hydrate(again)
    assert again[0]['content'] == _content(1)
    assert store.fetch_sense(1, 10, 0)[eid] == _content(1)


def test_a_repeated_id_from_the_fallback_gets_a_copy(monkeypatch):
    _mode(monkeypatch, 'storage', fallback=True)
    eid = _uuid()
    db = FallbackDB({eid: _content(4)})
    items = [_item(eid, 10), _item(eid, 10)]
    report = store.hydrate(items, db=db)
    assert items[0]['content'] == items[1]['content'] == _content(4)
    assert items[0]['content'] is not items[1]['content']
    assert report.db_fallback == 2 and len(db.calls) == 1


# ---------------------------------------------------------------------------
# parallel fetch on the store's own pool
# ---------------------------------------------------------------------------

def _ten_groups(mem):
    items = []
    for sense in range(100, 110):
        eid = _uuid()
        _seed(mem, sense, {eid: _content(sense)})
        items.append(_item(eid, sense))
    return items


def test_ten_groups_are_fetched_in_parallel_on_exc_fetch_threads(monkeypatch):
    mem = _mode(monkeypatch, 'storage')
    items = _ten_groups(mem)
    mem.latency_s = {'get': 0.2}

    started = time.monotonic()
    report = store.hydrate(items)
    elapsed = time.monotonic() - started

    assert elapsed < 0.6, elapsed
    assert report.fetched == 10 and all(i['content'] for i in items)
    assert len(mem.call_threads) == 10
    assert all(name.startswith('exc-fetch') for name in mem.call_threads), mem.call_threads


def test_a_call_from_an_io_pool_thread_is_still_parallel(monkeypatch):
    mem = _mode(monkeypatch, 'storage')
    items = _ten_groups(mem)
    mem.latency_s = {'get': 0.2}
    result = {}

    def run():
        started = time.monotonic()
        result['report'] = store.hydrate(items)
        result['elapsed'] = time.monotonic() - started

    thread = threading.Thread(target=run, name='io_0')
    thread.start()
    thread.join()
    assert result['elapsed'] < 0.6, result['elapsed']
    assert result['report'].fetched == 10
    assert all(name.startswith('exc-fetch') for name in mem.call_threads)


def test_pool_size_follows_config(monkeypatch):
    mem = _mode(monkeypatch, 'storage')
    monkeypatch.setattr(Config, 'EXERCISE_CONTENT_FETCH_CONCURRENCY', 2)
    store.reset_state()
    store.set_backend(mem)
    items = _ten_groups(mem)
    store.hydrate(items)
    assert len(set(mem.call_threads)) <= 2


def test_the_read_path_never_imports_services_concurrency():
    for path in sorted(PACKAGE.glob('*.py')):
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ''] + [f'{node.module}.{a.name}' for a in node.names]
            else:
                continue
            assert not any(n == 'services.concurrency' or n.startswith('services.concurrency.')
                           for n in names), f'{path.name} imports services.concurrency'


# ---------------------------------------------------------------------------
# cap and deadline
# ---------------------------------------------------------------------------

def test_per_call_cap_fetches_the_first_groups_and_counts_the_rest(monkeypatch):
    mem = _mode(monkeypatch, 'storage')
    monkeypatch.setattr(Config, 'EXERCISE_CONTENT_MAX_SENSES_PER_CALL', 160)
    items = []
    for sense in range(1, 201):
        eid = _uuid()
        _seed(mem, sense, {eid: _content(sense)})
        items.append(_item(eid, sense))

    report = store.hydrate(items, drop_missing=False)

    assert report.groups == 200 and report.fetched == 160 and report.over_cap == 40
    assert sorted(mem.calls_for('get')) == sorted(
        store.content_path(1, s, 0) for s in range(1, 161))
    assert all(i['content'] is not None for i in items[:160])
    assert all(i['content'] is None for i in items[160:])
    assert len(report.missing_ids) == 40


def test_explicit_max_senses_zero_serves_nothing_from_files(monkeypatch):
    mem = _mode(monkeypatch, 'storage', fallback=True)
    eid = _uuid()
    _seed(mem, 10, {eid: _content(1)})
    db = FallbackDB({eid: _content(1)})
    items = [_item(eid, 10)]
    report = store.hydrate(items, db=db, max_senses=0)
    assert report.over_cap == 1 and report.db_fallback == 1 and mem.calls == []


def test_deadline_returns_on_time_and_late_fetches_warm_the_cache(monkeypatch):
    mem = _mode(monkeypatch, 'storage')
    items = []
    for sense in (1, 2, 3):
        eid = _uuid()
        _seed(mem, sense, {eid: _content(sense)})
        items.append(_item(eid, sense))
    mem.latency_s = {'get': 0.6}

    started = time.monotonic()
    report = store.hydrate(copy.deepcopy(items), deadline_s=0.2)
    elapsed = time.monotonic() - started

    assert elapsed < 0.2 + 0.2, elapsed
    assert report.over_cap == 3 and report.fetched == 0 and report.dropped == 3

    time.sleep(0.7)                               # the GETs finish after the deadline
    mem.latency_s = 0.0
    mem.clear_calls()
    warm = copy.deepcopy(items)
    report = store.hydrate(warm)
    assert report.cache_hits == 3 and mem.calls == []
    assert [i['content'] for i in warm] == [_content(1), _content(2), _content(3)]


def test_default_deadline_comes_from_config(monkeypatch):
    mem = _mode(monkeypatch, 'storage')
    monkeypatch.setattr(Config, 'EXERCISE_CONTENT_DEADLINE_S', 0.15)
    eid = _uuid()
    _seed(mem, 1, {eid: _content(1)})
    mem.latency_s = {'get': 0.5}
    started = time.monotonic()
    report = store.hydrate([_item(eid, 1)])
    assert time.monotonic() - started < 0.35
    assert report.over_cap == 1


# ---------------------------------------------------------------------------
# negative cache, corrupt files, fetch errors
# ---------------------------------------------------------------------------

def test_a_missing_file_is_fetched_once_per_minute(monkeypatch):
    mem = _mode(monkeypatch, 'storage')
    eid = _uuid()
    for _ in range(3):
        store.hydrate([_item(eid, 10)])
    assert mem.calls_for('get') == ['zh/10.v0.json']

    clock = [time.monotonic() + 61]
    store._negative_cache().clock = lambda: clock[0]
    store.hydrate([_item(eid, 10)])
    assert mem.calls_for('get') == ['zh/10.v0.json'] * 2


def test_a_corrupt_file_is_logged_and_treated_as_missing(monkeypatch, caplog):
    caplog.set_level(logging.WARNING, logger=LOGGER)
    mem = _mode(monkeypatch, 'storage', fallback=True)
    eid = _uuid()
    mem.seed('zh/10.v0.json', b'{"format": 1, "sense_id": 10, "trunc')
    db = FallbackDB({eid: _content(8)})

    items = [_item(eid, 10)]
    report = store.hydrate(items, db=db)
    assert items[0]['content'] == _content(8) and report.db_fallback == 1
    assert len(_errors(caplog, 'exercise_content.corrupt_file')) == 1
    assert store._content_cache().get(store._cache_key(1, 10, 0)) is None

    store.hydrate([_item(eid, 10)], db=db)
    assert mem.calls_for('get') == ['zh/10.v0.json'], 'negative-cached after corruption'


def test_a_file_for_another_sense_counts_as_corrupt(monkeypatch, caplog):
    caplog.set_level(logging.ERROR, logger=LOGGER)
    mem = _mode(monkeypatch, 'storage')
    eid = _uuid()
    mem.seed('zh/10.v0.json', store.encode_sense_file(11, 1, 0, {eid: _content(1)}))
    items = [_item(eid, 10)]
    report = store.hydrate(items)
    assert items == [] and report.dropped == 1
    assert len(_errors(caplog, 'exercise_content.corrupt_file')) == 1


def test_a_fetch_error_is_logged_and_retried_by_the_next_call(monkeypatch, caplog):
    caplog.set_level(logging.WARNING, logger=LOGGER)
    mem = _mode(monkeypatch, 'storage')
    eid = _uuid()
    _seed(mem, 10, {eid: _content(1)})
    mem.fail_next('get', ContentStorageError('HTTP 503'))

    items = [_item(eid, 10)]
    report = store.hydrate(items)
    assert items == [] and report.dropped == 1 and report.fetched == 0
    assert len(_warnings(caplog, 'exercise_content.fetch_error n=1')) == 1

    items = [_item(eid, 10)]
    report = store.hydrate(items)
    assert items[0]['content'] == _content(1) and report.fetched == 1


def test_an_unexpected_backend_exception_does_not_escape(monkeypatch):
    mem = _mode(monkeypatch, 'storage')
    eid = _uuid()
    _seed(mem, 10, {eid: _content(1)})
    mem.fail_next('get', RuntimeError('socket gone'))
    items = [_item(eid, 10)]
    report = store.hydrate(items, drop_missing=False)
    assert items[0]['content'] is None and report.missing_ids == [eid]


# ---------------------------------------------------------------------------
# DB fallback
# ---------------------------------------------------------------------------

def test_fallback_reads_missing_ids_in_chunks_of_200_with_one_warning(monkeypatch, caplog):
    caplog.set_level(logging.WARNING, logger=LOGGER)
    mem = _mode(monkeypatch, 'storage', fallback=True)
    rows, items = {}, []
    for n in range(450):
        eid = _uuid()
        rows[eid] = _content(n)
        items.append(_item(eid, 1000 + n % 30))
    served = _uuid()
    _seed(mem, 5, {served: _content(999)})
    items.insert(7, _item(served, 5))
    db = FallbackDB(rows)

    report = store.hydrate(items, db=db, max_senses=1000)

    assert [c[1:] for c in db.calls] == [
        (('select', 'id, content'), ('in_', 'id', ids))
        for ids in ([i['id'] for i in items if i['id'] != served][s:s + 200]
                    for s in (0, 200, 400))]
    assert [len(c[2][2]) for c in db.calls] == [200, 200, 50]
    assert all(c[0] == ('table', 'exercises') for c in db.calls)
    lines = _warnings(caplog, 'exercise_content.db_fallback ')
    assert [r.getMessage() for r in lines] == ['exercise_content.db_fallback n=450 senses=30']
    assert report.db_fallback == 450 and report.dropped == 0 and report.missing_ids == []
    assert items[7]['content'] == _content(999)
    assert all(i['content'] == rows[i['id']] for i in items if i['id'] in rows)


@pytest.mark.parametrize('error', [
    APIError({'code': '42703', 'message': 'column exercises.content does not exist',
              'details': None, 'hint': None}),
    APIError({'code': 'PGRST204', 'message': "Could not find the 'content' column",
              'details': None, 'hint': None}),
    RuntimeError("{'code': '42703', 'message': 'column does not exist'}"),
])
def test_a_missing_column_turns_the_fallback_off_for_the_process(monkeypatch, caplog, error):
    caplog.set_level(logging.WARNING, logger=LOGGER)
    _mode(monkeypatch, 'storage', fallback=True)
    eid = _uuid()
    db = FallbackDB(error=error)

    items = [_item(eid, 10)]
    report = store.hydrate(items, db=db)
    assert items == [] and report.dropped == 1 and report.db_fallback == 0
    assert len(_errors(caplog, 'exercise_content.db_fallback_disabled')) == 1

    store.hydrate([_item(eid, 10)], db=db)
    assert len(db.calls) == 1, 'the fallback stays off'
    assert len(_errors(caplog, 'exercise_content.db_fallback_disabled')) == 1

    store.reset_state()
    store.set_backend(InMemoryBackend())
    store.hydrate([_item(eid, 10)], db=db)
    assert len(db.calls) == 2, 'reset_state turns the fallback back on'


def test_another_fallback_error_is_logged_and_the_fallback_stays_on(monkeypatch, caplog):
    caplog.set_level(logging.WARNING, logger=LOGGER)
    _mode(monkeypatch, 'storage', fallback=True)
    eid = _uuid()
    db = FallbackDB(error=APIError({'code': '57014', 'message': 'statement timeout',
                                    'details': None, 'hint': None}))
    items = [_item(eid, 10)]
    report = store.hydrate(items, db=db)
    assert items == [] and report.dropped == 1
    assert len(_warnings(caplog, 'exercise_content.db_fallback_error')) == 1
    db.error = None
    db.rows = {eid: _content(1)}
    items = [_item(eid, 10)]
    store.hydrate(items, db=db)
    assert items[0]['content'] == _content(1)


def test_fallback_off_by_config_makes_no_db_call(monkeypatch):
    _mode(monkeypatch, 'storage', fallback=False)
    items = [_item(_uuid(), 10)]
    report = store.hydrate(items, db=ExplodingDB())
    assert items == [] and report.dropped == 1


def test_db_none_uses_the_admin_client_only_when_needed(monkeypatch):
    import services.supabase_factory as factory

    mem = _mode(monkeypatch, 'storage', fallback=True)
    eid, missing = _uuid(), _uuid()
    _seed(mem, 10, {eid: _content(1)})
    fake = FallbackDB({missing: _content(2)})
    calls = []
    monkeypatch.setattr(factory, 'get_supabase_admin', lambda: calls.append(1) or fake)

    store.hydrate([_item(eid, 10)])
    assert calls == []

    items = [_item(missing, 10)]
    store.hydrate(items)
    assert calls == [1] and items[0]['content'] == _content(2)


def test_db_none_without_an_admin_client_counts_items_as_missing(monkeypatch, caplog):
    import services.supabase_factory as factory

    caplog.set_level(logging.WARNING, logger=LOGGER)
    _mode(monkeypatch, 'storage', fallback=True)

    def broken():
        raise RuntimeError('no credentials')

    monkeypatch.setattr(factory, 'get_supabase_admin', broken)
    items = [_item(_uuid(), 10)]
    report = store.hydrate(items)
    assert items == [] and report.dropped == 1
    assert len(_warnings(caplog, 'exercise_content.db_fallback_unavailable')) == 1


def test_report_counters_in_a_mixed_scenario(monkeypatch):
    mem = _mode(monkeypatch, 'storage', fallback=True)
    hit, fetched, from_db, gone, over = (_uuid() for _ in range(5))
    _seed(mem, 1, {hit: _content(1)})
    _seed(mem, 2, {fetched: _content(2)})
    store.hydrate([_item(hit, 1)])                       # warm the cache for sense 1
    db = FallbackDB({from_db: _content(3), over: _content(5)})
    items = [_item(hit, 1), _item(fetched, 2), _item(from_db, 3), _item(gone, 4),
             _item(over, 5), _item(_uuid(), 2, content={'kept': True})]

    report = store.hydrate(items, db=db, max_senses=4)

    assert report == store.HydrationReport(
        mode='storage', items=6, groups=5, cache_hits=1, fetched=1, db_fallback=2,
        over_cap=1, dropped=1, missing_ids=[gone], elapsed_ms=report.elapsed_ms)
    assert report.elapsed_ms > 0
    assert [i['content'] for i in items] == [_content(1), _content(2), _content(3),
                                             _content(5), {'kept': True}]


def test_storage_hydrate_with_nothing_to_do_makes_no_call(monkeypatch):
    mem = _mode(monkeypatch, 'storage', fallback=True)
    items = [_item(_uuid(), 1, content={'x': 1}), {'kind': 'marker'}]
    report = store.hydrate(items, db=ExplodingDB())
    assert mem.calls == [] and report.items == 1 and report.groups == 0


def test_reader_rejects_an_unknown_mode():
    with pytest.raises(ValueError):
        reader.hydrate([], language_id=None, id_key='id', sense_key='word_sense_id', db=None,
                       drop_missing=True, max_senses=None, deadline_s=None, mode='db')


# ---------------------------------------------------------------------------
# fetch_sense
# ---------------------------------------------------------------------------

def test_fetch_sense_uses_the_cache_and_returns_fresh_objects(monkeypatch):
    mem = InMemoryBackend()
    store.set_backend(mem)                    # mode-independent: conftest pins db
    eid = _uuid()
    _seed(mem, 7, {eid: _content(1)}, version=4, lang=3)

    first = store.fetch_sense(3, 7, 4)
    assert first == {eid: _content(1)}
    first[eid]['options'].append('x')
    second = store.fetch_sense(3, 7, 4)
    assert second == {eid: _content(1)}
    assert mem.calls_for('get') == ['ja/7.v4.json']


def test_fetch_sense_missing_corrupt_and_failing(monkeypatch, caplog):
    caplog.set_level(logging.WARNING, logger=LOGGER)
    mem = InMemoryBackend()
    store.set_backend(mem)
    assert store.fetch_sense(1, 7, 0) is None
    assert store.fetch_sense(1, 7, 0) is None
    assert mem.calls_for('get') == ['zh/7.v0.json']

    mem.seed('zh/8.v0.json', b'not json')
    assert store.fetch_sense(1, 8, 0) is None
    assert len(_errors(caplog, 'exercise_content.corrupt_file')) == 1

    mem.fail_next('get', RuntimeError('boom'))
    assert store.fetch_sense(1, 9, 0) is None
    assert store.fetch_sense('x', 9, 0) is None
    assert store.fetch_sense(1, -1, 0) is None
    assert store.fetch_sense(1, 9, True) is None


# ---------------------------------------------------------------------------
# shadow
# ---------------------------------------------------------------------------

def _shadow_items(mem, *, tamper=None, missing_exercise=None):
    a, b, c = _uuid(), _uuid(), _uuid()
    file_a = {a: _content(1), b: _content(2)}
    if tamper:
        file_a[b] = {**_content(2), 'answer': 'tampered'}
    if missing_exercise:
        del file_a[a]
    _seed(mem, 10, file_a)
    _seed(mem, 11, {c: _content(3)}, version=2)
    items = [_item(a, 10, content=_content(1)), _item(b, 10, content=_content(2)),
             {'kind': 'marker'}, _item(c, 11, version=2, content=_content(3))]
    return items, (a, b, c)


def test_shadow_never_mutates_and_finds_no_mismatch_on_equal_files(monkeypatch, caplog):
    caplog.set_level(logging.INFO, logger=LOGGER)
    mem = _mode(monkeypatch, 'shadow')
    items, _ = _shadow_items(mem)
    snapshot = copy.deepcopy(items)
    ids_before = [id(i.get('content')) for i in items]

    report = store.hydrate(items)
    assert shadow.drain(5)

    assert items == snapshot and [id(i.get('content')) for i in items] == ids_before
    assert report.mode == 'shadow' and report.items == 3 and report.groups == 2
    assert _warnings(caplog, 'exercise_content.shadow_mismatch') == []
    stats = shadow.stats()
    assert stats['compared'] == 3 and stats['ok'] == 3 and stats['dropped'] == 0


def test_shadow_logs_one_content_diff_for_a_tampered_exercise(monkeypatch, caplog):
    caplog.set_level(logging.WARNING, logger=LOGGER)
    mem = _mode(monkeypatch, 'shadow')
    items, (_, b, _) = _shadow_items(mem, tamper=True)
    store.hydrate(items)
    assert shadow.drain(5)
    lines = [r.getMessage() for r in _warnings(caplog, 'exercise_content.shadow_mismatch')]
    assert lines == [f'exercise_content.shadow_mismatch kind=content_diff sense=10 version=0 '
                     f'exercise={b}']
    assert shadow.stats()['content_diff'] == 1 and shadow.stats()['ok'] == 2


def test_shadow_missing_exercise_missing_file_and_fetch_error(monkeypatch, caplog):
    caplog.set_level(logging.WARNING, logger=LOGGER)
    mem = _mode(monkeypatch, 'shadow')
    items, (a, _, _) = _shadow_items(mem, missing_exercise=True)
    lonely = _uuid()
    items.append(_item(lonely, 12, content=_content(4)))        # no file for sense 12
    broken = _uuid()
    items.append(_item(broken, 13, content=_content(5)))
    _seed(mem, 13, {broken: _content(5)})
    original_get = mem.get

    def get(path):
        if path == 'zh/13.v0.json':
            raise ContentStorageError('HTTP 503')
        return original_get(path)

    monkeypatch.setattr(mem, 'get', get)
    store.hydrate(items)
    assert shadow.drain(5)

    lines = sorted(r.getMessage() for r in _warnings(caplog, 'exercise_content.shadow_mismatch'))
    assert lines == sorted([
        f'exercise_content.shadow_mismatch kind=missing_exercise sense=10 version=0 exercise={a}',
        'exercise_content.shadow_mismatch kind=missing_file sense=12 version=0 exercise=* n=1',
        'exercise_content.shadow_mismatch kind=fetch_error sense=13 version=0 exercise=* n=1 '
        'error=ContentStorageError',
    ])
    stats = shadow.stats()
    assert (stats['compared'], stats['ok'], stats['missing_exercise'], stats['missing_file'],
            stats['fetch_error']) == (5, 2, 1, 1, 1)


def test_shadow_summary_every_500_comparisons(monkeypatch, caplog):
    caplog.set_level(logging.INFO, logger=LOGGER)
    mem = _mode(monkeypatch, 'shadow')
    items = []
    for sense in (1, 2, 3):
        exercises = {_uuid(): _content(n) for n in range(200)}
        _seed(mem, sense, exercises)
        items += [_item(eid, sense, content=content) for eid, content in exercises.items()]
    store.hydrate(items)
    assert shadow.drain(5)
    summaries = [r.getMessage() for r in caplog.records
                 if r.levelno == logging.INFO and 'shadow_summary' in r.getMessage()]
    assert summaries == ['exercise_content.shadow_summary compared=600 ok=600 missing_file=0 '
                         'missing_exercise=0 content_diff=0 dropped=0 fetch_error=0']


def test_shadow_sample_zero_queues_nothing(monkeypatch):
    mem = _mode(monkeypatch, 'shadow')
    monkeypatch.setattr(Config, 'EXERCISE_CONTENT_SHADOW_SAMPLE', 0)
    items, _ = _shadow_items(mem)
    report = store.hydrate(items)
    assert shadow.drain(1)
    assert mem.calls == [] and shadow.stats()['compared'] == 0 and report.groups == 2


def test_shadow_sample_is_per_group(monkeypatch):
    mem = _mode(monkeypatch, 'shadow')
    monkeypatch.setattr(Config, 'EXERCISE_CONTENT_SHADOW_SAMPLE', 0.5)
    draws = iter([0.9, 0.1])
    monkeypatch.setattr(reader.random, 'random', lambda: next(draws))
    items, _ = _shadow_items(mem)
    store.hydrate(items)
    assert shadow.drain(5)
    assert mem.calls_for('get') == ['zh/11.v2.json']


def test_shadow_queue_overflow_is_counted_and_never_blocks(monkeypatch):
    mem = _mode(monkeypatch, 'shadow')
    release = threading.Event()
    original_get = mem.get

    def blocked_get(path):
        release.wait(5)
        return original_get(path)

    monkeypatch.setattr(mem, 'get', blocked_get)
    items = [_item(_uuid(), sense, content=_content(sense)) for sense in range(1, 301)]

    started = time.monotonic()
    store.hydrate(items)
    assert time.monotonic() - started < 0.5
    stats = shadow.stats()
    assert stats['dropped'] >= 300 - 256 - 1
    assert stats['dropped'] + stats['queued'] <= 300

    release.set()
    assert shadow.drain(10)
    final = shadow.stats()
    assert final['missing_file'] + final['dropped'] == 300


def test_shadow_worker_thread_and_reset(monkeypatch):
    mem = _mode(monkeypatch, 'shadow')
    items, _ = _shadow_items(mem)
    store.hydrate(items)
    assert shadow.drain(5)
    worker = shadow._current().thread
    assert worker.name == 'exc-shadow' and worker.daemon

    store.reset_state()
    worker.join(2)
    assert not worker.is_alive()
    assert shadow.stats()['compared'] == 0

    store.set_backend(mem)
    store.hydrate(items)
    assert shadow.drain(5) and shadow.stats()['compared'] == 3


def test_shadow_skips_items_that_cannot_be_compared(monkeypatch):
    mem = _mode(monkeypatch, 'shadow')
    items = [_item(_uuid(), 10, content=None), _item(_uuid(), 10, version=None, content={'a': 1}),
             _item(_uuid(), 10, content={'bad': {1, 2}})]
    report = store.hydrate(items)
    assert shadow.drain(1)
    assert report.items == 3 and report.groups == 0 and mem.calls == []
