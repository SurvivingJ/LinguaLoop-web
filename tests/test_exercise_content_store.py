"""TASK-1008 / TASK-1031 — the exercise-content store facade (ADR-049 §9) and its plumbing.

Covers the public interface every other package codes against (names,
signatures, dataclass fields, exception hierarchy), the tuning settings in
``config.py``, the Storage-credential rule, ``select_columns`` /
``rpc_content_args``, ``hydrate`` and ``write_sense`` validation and their
delegation to ``reader.py`` / ``writer.py``, the pure codec, the
``InMemoryBackend`` every later test uses, and the backend / cache / reset
plumbing behind ``store.backend()`` and ``store.reset_state()``.

There are no modes since TASK-1031 (``exercises.content`` was dropped on
2026-11-19): reads always come from the files and writes always go file first,
then the rows by compare-and-swap. The read and write paths themselves are
tested in ``test_exercise_content_reader.py`` and ``test_exercise_content_writer.py``.

Fully offline: no Supabase client, no network.
"""

from __future__ import annotations

import copy
import dataclasses
import inspect
import json
import logging
import os
import subprocess
import sys
import threading
import time
import types
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from config import Config
from services.exercise_content import store
from services.exercise_content.backends import (
    InMemoryBackend, StorageBackend, StoredObject, SupabaseStorageBackend,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
LOGGER = 'services.exercise_content'

E = inspect.Parameter.empty
POS = inspect.Parameter.POSITIONAL_OR_KEYWORD
KW = inspect.Parameter.KEYWORD_ONLY


def _uuid() -> str:
    return str(uuid.uuid4())


def _params(fn) -> list[tuple[str, object, object]]:
    return [(p.name, p.kind, p.default) for p in inspect.signature(fn).parameters.values()]


def _clean_env(**extra: str) -> dict:
    env = {k: v for k, v in os.environ.items()
           if not k.startswith('EXERCISE_CONTENT_') and not k.startswith('SUPABASE_')
           and k != 'OPENROUTER_API_KEY'}
    env.update(extra)
    return env


def _run_python(code: str, **extra_env: str) -> str:
    result = subprocess.run(
        [sys.executable, '-c', code], cwd=str(REPO_ROOT), env=_clean_env(**extra_env),
        capture_output=True, text=True, timeout=120,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout.strip().splitlines()[-1]


def _no_credentials(monkeypatch, missing=('SUPABASE_URL', 'SUPABASE_SERVICE_ROLE_KEY')):
    """No Storage credentials and no installed backend (the conftest installs one)."""
    store.set_backend(None)
    for name in missing:
        monkeypatch.setattr(Config, name, None)


def _errors(caplog):
    return [r for r in caplog.records if r.name == LOGGER and r.levelno == logging.ERROR]


# ---------------------------------------------------------------------------
# Recording fake PostgREST client
# ---------------------------------------------------------------------------

class _Resp:
    def __init__(self, data):
        self.data = data


class _Chain:
    def __init__(self, db, table):
        self._db = db
        self.steps = [('table', (table,))]
        db.chains.append(self.steps)

    @property
    def not_(self):
        self.steps.append(('not_', ()))
        return self

    def __getattr__(self, name):
        if name.startswith('_'):
            raise AttributeError(name)

        def method(*args, **kwargs):
            assert not kwargs, f'unexpected keyword args to {name}: {kwargs}'
            self.steps.append((name, args))
            if name == 'execute':
                return _Resp(self._db.data_for(self.steps[1][0]))
            return self
        return method


class RecordingDB:
    """Records every `table(...)` chain as [(method, args), ...]."""

    def __init__(self, delete_data=None):
        self.chains: list[list[tuple]] = []
        self.delete_data = delete_data if delete_data is not None else []

    def table(self, name):
        return _Chain(self, name)

    def data_for(self, op):
        return self.delete_data if op == 'delete' else []

    def rpc(self, *args, **kwargs):  # pragma: no cover - must never be called
        raise AssertionError('the facade must not call an RPC itself')


class ExplodingDB:
    """Any attribute access is a failure: proves a code path makes no db call."""

    def __getattr__(self, name):
        raise AssertionError(f'unexpected db access: {name}')


def _row(sense_id=7, language_id=1, **overrides):
    row = {'id': _uuid(), 'word_sense_id': sense_id, 'language_id': language_id,
           'exercise_type': 'cloze_completion', 'ladder_level': 3,
           'content': {'sentence': '我买了一本书。', 'options': ['书', '笔']}}
    row.update(overrides)
    return row


# ---------------------------------------------------------------------------
# 1. Public interface (ADR-049 §9)
# ---------------------------------------------------------------------------

def test_store_exposes_the_adr_constants():
    assert store.LANGUAGE_CODES == {1: 'zh', 2: 'en', 3: 'ja'}
    assert store.FILE_FORMAT == 1
    assert store.COMMIT_LOCK_NAMESPACE == 47047
    assert store.CONTENT_COLUMNS == 'content_version'


def test_the_transition_modes_are_gone():
    """TASK-1031: no read/write modes, no DB fallback, no shadow comparer."""
    for name in ('READ_MODES', 'WRITE_MODES', 'read_mode', 'write_mode', '_resolve_mode',
                 '_write_sense_db', '_setting_bool'):
        assert not hasattr(store, name), name
    from services.exercise_content import reader, writer
    for name in ('_db_fallback', '_is_missing_column', '_hydrate_shadow', 'MISSING_COLUMN_CODES',
                 'FALLBACK_CHUNK'):
        assert not hasattr(reader, name), name
    for name in ('_is_missing_column', 'MISSING_COLUMN_CODES', 'BASE_SELECT_CHUNK',
                 'write_sense_dual'):
        assert not hasattr(writer, name), name
    assert not (REPO_ROOT / 'services' / 'exercise_content' / 'shadow.py').exists()


def test_language_codes_match_intro_drill_and_config():
    from services.intro_drill import LANG_CODE
    assert store.LANGUAGE_CODES == LANG_CODE
    assert store.LANGUAGE_CODES == {k: v['code'] for k, v in Config.LANGUAGES.items()}


def test_exception_hierarchy():
    assert issubclass(store.ExerciseContentError, Exception)
    assert issubclass(store.ContentStorageError, store.ExerciseContentError)
    assert issubclass(store.AlreadyExists, store.ContentStorageError)
    assert issubclass(store.ContentWriteConflict, store.ExerciseContentError)
    assert not issubclass(store.ContentWriteConflict, store.ContentStorageError)


def test_dataclass_fields_and_defaults():
    def shape(cls):
        out = []
        for f in dataclasses.fields(cls):
            if f.default is not dataclasses.MISSING:
                default = f.default
            elif f.default_factory is not dataclasses.MISSING:
                default = f.default_factory()
            else:
                default = 'REQUIRED'
            out.append((f.name, default))
        return out

    assert shape(store.HydrationReport) == [
        ('items', 0), ('groups', 0), ('cache_hits', 0), ('fetched', 0),
        ('over_cap', 0), ('dropped', 0), ('missing_ids', []), ('elapsed_ms', 0.0),
    ]
    assert shape(store.DeleteWhere) == [('require_word_asset', False), ('ladder_levels', None)]
    assert shape(store.WriteResult) == [
        ('sense_id', 'REQUIRED'), ('version', 'REQUIRED'),
        ('inserted_ids', 'REQUIRED'), ('deleted_count', 'REQUIRED'),
        ('updated_ids', 'REQUIRED'), ('attempts', 'REQUIRED'),
    ]
    assert shape(StoredObject) == [
        ('path', 'REQUIRED'), ('size', 'REQUIRED'), ('created_at', 'REQUIRED')]
    assert store.DeleteWhere.__dataclass_params__.frozen
    assert StoredObject.__dataclass_params__.frozen
    assert store.HydrationReport().missing_ids is not store.HydrationReport().missing_ids


def test_function_signatures():
    assert _params(store.select_columns) == [('template', POS, E)]
    assert _params(store.rpc_content_args) == []
    assert _params(store.hydrate) == [
        ('items', POS, E), ('language_id', KW, None), ('id_key', KW, 'id'),
        ('sense_key', KW, 'word_sense_id'), ('drop_missing', KW, True),
        ('max_senses', KW, None), ('deadline_s', KW, None),
    ]
    assert _params(store.fetch_sense) == [
        ('language_id', POS, E), ('sense_id', POS, E), ('version', POS, E)]
    assert _params(store.write_sense) == [
        ('db', POS, E), ('sense_id', POS, E), ('language_id', POS, E),
        ('insert_rows', KW, ()), ('delete_where', KW, None), ('update_contents', KW, None),
        ('max_retries', KW, 3), ('expected_version', KW, None),
    ]
    assert _params(store.base_version) == [('rows', POS, E)]
    assert _params(store.content_path) == [
        ('language_id', POS, E), ('sense_id', POS, E), ('version', POS, E)]
    assert _params(store.encode_sense_file) == [
        ('sense_id', POS, E), ('language_id', POS, E), ('version', POS, E), ('exercises', POS, E)]
    assert _params(store.decode_sense_file) == [
        ('data', POS, E), ('sense_id', KW, E), ('version', KW, E)]
    assert _params(store.canonical) == [('content', POS, E)]
    assert _params(store.backend) == []
    assert _params(store.set_backend) == [('b', POS, E)]
    assert _params(store.reset_state) == []


def test_reader_and_writer_signatures():
    from services.exercise_content import reader, writer

    assert _params(reader.hydrate) == [
        ('items', POS, E), ('language_id', KW, E), ('id_key', KW, E), ('sense_key', KW, E),
        ('drop_missing', KW, E), ('max_senses', KW, E), ('deadline_s', KW, E),
    ]
    assert _params(reader.fetch_sense) == [
        ('language_id', POS, E), ('sense_id', POS, E), ('version', POS, E)]
    assert _params(writer.write_sense) == [
        ('db', POS, E), ('sense_id', POS, E), ('language_id', POS, E), ('insert_rows', KW, E),
        ('delete_where', KW, E), ('update_contents', KW, E), ('max_retries', KW, E),
        ('expected_version', KW, None),
    ]


def test_backend_protocol_shape():
    for name, params in (('get', ['self', 'path']), ('put', ['self', 'path', 'data']),
                         ('delete', ['self', 'paths']), ('list', ['self', 'prefix'])):
        assert [p.name for p in inspect.signature(getattr(StorageBackend, name)).parameters.values()] == params
    assert isinstance(InMemoryBackend(), StorageBackend)
    assert isinstance(SupabaseStorageBackend('https://x.supabase.co', 'k'), StorageBackend)


# ---------------------------------------------------------------------------
# 2. Config settings
# ---------------------------------------------------------------------------

_SETTINGS = ('EXERCISE_CONTENT_BUCKET', 'EXERCISE_CONTENT_CACHE_MB',
             'EXERCISE_CONTENT_FETCH_CONCURRENCY', 'EXERCISE_CONTENT_MAX_SENSES_PER_CALL',
             'EXERCISE_CONTENT_DEADLINE_S', 'EXERCISE_CONTENT_HTTP_TIMEOUT_S')
_REMOVED = ('EXERCISE_CONTENT_SOURCE', 'EXERCISE_CONTENT_WRITE', 'EXERCISE_CONTENT_DB_FALLBACK',
            'EXERCISE_CONTENT_SHADOW_SAMPLE')

_DUMP_SETTINGS = ('import json; from config import Config; '
                  f'print(json.dumps({{**{{n: getattr(Config, n) for n in {_SETTINGS!r}}}, '
                  f'"removed": [n for n in {_REMOVED!r} if hasattr(Config, n)]}}))')


def test_config_defaults_in_a_clean_interpreter():
    values = json.loads(_run_python(_DUMP_SETTINGS))
    assert values == {
        'EXERCISE_CONTENT_BUCKET': 'exercise-content',
        'EXERCISE_CONTENT_CACHE_MB': 32,
        'EXERCISE_CONTENT_FETCH_CONCURRENCY': 16,
        'EXERCISE_CONTENT_MAX_SENSES_PER_CALL': 160,
        'EXERCISE_CONTENT_DEADLINE_S': 3.0,
        'EXERCISE_CONTENT_HTTP_TIMEOUT_S': 2.0,
        'removed': [],
    }
    assert all(hasattr(Config, name) for name in _SETTINGS)


def test_config_reads_the_environment_and_ignores_the_removed_flags():
    values = json.loads(_run_python(
        _DUMP_SETTINGS,
        EXERCISE_CONTENT_BUCKET='other-bucket', EXERCISE_CONTENT_CACHE_MB='8',
        EXERCISE_CONTENT_FETCH_CONCURRENCY='4', EXERCISE_CONTENT_MAX_SENSES_PER_CALL='50',
        EXERCISE_CONTENT_DEADLINE_S='1.5', EXERCISE_CONTENT_HTTP_TIMEOUT_S='0.5',
        EXERCISE_CONTENT_SOURCE='db', EXERCISE_CONTENT_WRITE='db',
        EXERCISE_CONTENT_DB_FALLBACK='1', EXERCISE_CONTENT_SHADOW_SAMPLE='0.25',
    ))
    assert values == {
        'EXERCISE_CONTENT_BUCKET': 'other-bucket', 'EXERCISE_CONTENT_CACHE_MB': 8,
        'EXERCISE_CONTENT_FETCH_CONCURRENCY': 4, 'EXERCISE_CONTENT_MAX_SENSES_PER_CALL': 50,
        'EXERCISE_CONTENT_DEADLINE_S': 1.5, 'EXERCISE_CONTENT_HTTP_TIMEOUT_S': 0.5,
        'removed': [],
    }


def test_config_bad_numbers_fall_back_to_the_defaults():
    values = json.loads(_run_python(
        _DUMP_SETTINGS, EXERCISE_CONTENT_CACHE_MB='lots', EXERCISE_CONTENT_DEADLINE_S='soon',
        EXERCISE_CONTENT_BUCKET='  ',
    ))
    assert values['EXERCISE_CONTENT_CACHE_MB'] == 32
    assert values['EXERCISE_CONTENT_DEADLINE_S'] == 3.0
    assert values['EXERCISE_CONTENT_BUCKET'] == 'exercise-content'


def test_conftest_installs_a_fresh_in_memory_backend():
    backend = store.backend()
    assert isinstance(backend, InMemoryBackend) and store._backend_override is True
    assert backend.paths() == [] and backend.calls == []


_LEAK: dict = {}


def test_state_leaks_into_the_next_test_part_1_of_2():
    _LEAK['backend'] = store.backend()
    store.backend().seed('zh/1.v0.json', b'{}')
    store._warn_once(('leak-check',), logging.INFO, 'leak check')


def test_state_leaks_into_the_next_test_part_2_of_2():
    assert store.backend() is not _LEAK['backend']
    assert store.backend().paths() == []
    assert ('leak-check',) not in store._warned


# ---------------------------------------------------------------------------
# 3. Storage credentials
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('missing', [('SUPABASE_URL',), ('SUPABASE_SERVICE_ROLE_KEY',),
                                     ('SUPABASE_URL', 'SUPABASE_SERVICE_ROLE_KEY')])
def test_without_credentials_hydrate_treats_every_group_as_missing_with_one_error(
        monkeypatch, caplog, missing):
    caplog.set_level(logging.ERROR, logger=LOGGER)
    _no_credentials(monkeypatch, missing)
    has = {'id': _uuid(), 'word_sense_id': 7, 'content_version': 0, 'content': {'k': 1}}
    needs = [{'id': _uuid(), 'word_sense_id': 7 + n, 'content_version': 0} for n in range(3)]

    items = [has, *needs]
    report = store.hydrate(items, language_id=1)
    again = [{'id': _uuid(), 'word_sense_id': 7, 'content_version': 0}]
    store.hydrate(again, language_id=1, drop_missing=False)

    assert items == [has] and report.dropped == 3
    assert report.missing_ids == [n['id'] for n in needs] and report.fetched == 0
    assert again[0]['content'] is None
    assert store._backend is None, 'no backend was built, so nothing was fetched'
    errors = _errors(caplog)
    assert len(errors) == 1
    assert 'SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are not set' in errors[0].getMessage()


def test_without_credentials_fetch_sense_is_none(monkeypatch, caplog):
    caplog.set_level(logging.ERROR, logger=LOGGER)
    _no_credentials(monkeypatch)
    assert store.fetch_sense(1, 5, 0) is None
    assert store._backend is None and len(_errors(caplog)) == 1


def test_without_credentials_write_sense_raises_before_any_call(monkeypatch, caplog):
    caplog.set_level(logging.ERROR, logger=LOGGER)
    _no_credentials(monkeypatch, ('SUPABASE_SERVICE_ROLE_KEY',))
    with pytest.raises(store.ContentStorageError, match='SUPABASE_SERVICE_ROLE_KEY'):
        store.write_sense(ExplodingDB(), 7, 1, insert_rows=[_row()])
    with pytest.raises(store.ContentStorageError):
        store.write_sense(ExplodingDB(), 7, 1, delete_where=store.DeleteWhere())
    assert store._backend is None and len(_errors(caplog)) == 1
    # Validation still comes first, and a call with nothing to do needs no storage.
    with pytest.raises(ValueError):
        store.write_sense(ExplodingDB(), 7, 1, insert_rows=[_row(sense_id=8)])
    assert store.write_sense(ExplodingDB(), 7, 1).attempts == 0


def test_an_installed_backend_needs_no_credentials(monkeypatch):
    monkeypatch.setattr(Config, 'SUPABASE_URL', None)
    monkeypatch.setattr(Config, 'SUPABASE_SERVICE_ROLE_KEY', None)
    mem = InMemoryBackend()
    item_id = _uuid()
    mem.seed('zh/7.v0.json', store.encode_sense_file(7, 1, 0, {item_id: {'k': 1}}))
    store.set_backend(mem)
    items = [{'id': item_id, 'word_sense_id': 7, 'content_version': 0}]
    store.hydrate(items, language_id=1)
    assert items[0]['content'] == {'k': 1}
    assert store._storage_configured()

    store.set_backend(None)
    assert not store._storage_configured()
    items = [{'id': item_id, 'word_sense_id': 7, 'content_version': 0}]
    store.hydrate(items, language_id=1)
    assert items == []


def test_credentials_are_read_at_call_time(monkeypatch):
    _no_credentials(monkeypatch)
    assert not store._storage_configured()
    monkeypatch.setattr(Config, 'SUPABASE_URL', 'https://fake.supabase.co')
    assert not store._storage_configured()
    monkeypatch.setattr(Config, 'SUPABASE_SERVICE_ROLE_KEY', 'fake-service-role-key')
    assert store._storage_configured()
    monkeypatch.setattr(Config, 'SUPABASE_URL', '   ')
    assert not store._storage_configured()


# ---------------------------------------------------------------------------
# 4. select_columns / rpc_content_args
# ---------------------------------------------------------------------------

TEMPLATE = 'id, word_sense_id, exercise_type, {content}, ladder_level'


def test_select_columns_reads_content_version_in_place_of_content():
    assert store.select_columns(TEMPLATE) == \
        'id, word_sense_id, exercise_type, content_version, ladder_level'
    for template, expected in (
            ('exercise_type, {content}, language_id, word_sense_id',
             'exercise_type, content_version, language_id, word_sense_id'),
            ('id, exercise_type, {content}, complexity_tier, ladder_level, tags, word_sense_id',
             'id, exercise_type, content_version, complexity_tier, ladder_level, tags, '
             'word_sense_id'),
            ('{content}', 'content_version')):
        assert store.select_columns(template) == expected


@pytest.mark.parametrize('bad', [
    'id, content, ladder_level', 'id, {content}, {content}', '', '{Content}', None, 5])
def test_select_columns_rejects_templates_without_exactly_one_placeholder(bad):
    with pytest.raises(ValueError):
        store.select_columns(bad)


def test_rpc_content_args_never_asks_for_content():
    args = store.rpc_content_args()
    assert args == {'p_include_content': False}
    args['mutated'] = 1
    assert store.rpc_content_args() == {'p_include_content': False}


# ---------------------------------------------------------------------------
# 5. hydrate
# ---------------------------------------------------------------------------

def _items():
    return [
        {'exercise_id': _uuid(), 'sense_id': 7, 'content': {'a': 1}, 'content_version': 0},
        {'exercise_id': _uuid(), 'sense_id': 8, 'content': None},
        {'type': 'dt_error_card', 'payload': {'x': 1}},          # no id: untouched
        {'exercise_id': None, 'marker': 'gate'},                  # falsy id: untouched
        'not-a-dict',
    ]


def test_hydrate_leaves_items_without_an_id_or_with_content_alone():
    mem = store.backend()
    items = _items()
    has_content, needs_content = items[0], items[1]
    others = items[2:]
    before = copy.deepcopy(items)

    report = store.hydrate(items, language_id=1, id_key='exercise_id', sense_key='sense_id')

    assert report.items == 2
    assert report.missing_ids == [needs_content['exercise_id']] and report.dropped == 1
    assert items[0] is has_content and items[0] == before[0]
    assert items[1:] == others and items[1:] == before[2:]
    assert mem.calls == [], 'the item without a version cannot be fetched'


def test_hydrate_default_id_key_with_nothing_to_fetch_makes_no_call():
    items = [{'id': 'a', 'content': {}}, {'id': ''}, {}]
    report = store.hydrate(items)
    assert (report.items, report.groups, report.dropped) == (1, 0, 0)
    assert store.backend().calls == []


@pytest.mark.parametrize('kwargs', [
    {'items': None}, {'items': ({'id': 1},)}, {'id_key': ''}, {'sense_key': None},
    {'language_id': 'zh'}, {'language_id': 1.5}, {'max_senses': -1}, {'max_senses': 2.0},
    {'deadline_s': 0}, {'deadline_s': -1.0}, {'deadline_s': float('nan')}, {'deadline_s': True},
])
def test_hydrate_rejects_bad_arguments(kwargs):
    args = {'items': []}
    args.update(kwargs)
    items = args.pop('items')
    with pytest.raises(ValueError):
        store.hydrate(items, **args)


def test_hydrate_delegates_to_the_reader_with_resolved_arguments(monkeypatch):
    from services.exercise_content import reader

    monkeypatch.setattr(Config, 'EXERCISE_CONTENT_MAX_SENSES_PER_CALL', 120)
    monkeypatch.setattr(Config, 'EXERCISE_CONTENT_DEADLINE_S', 2.5)
    calls = []

    def fake(items, **kwargs):
        calls.append((items, kwargs))
        return store.HydrationReport(items=len(items))

    monkeypatch.setattr(reader, 'hydrate', fake)
    items = [{'id': 'x'}]
    report = store.hydrate(items, language_id='3', drop_missing=False)

    assert calls == [(items, {
        'language_id': 3, 'id_key': 'id', 'sense_key': 'word_sense_id',
        'drop_missing': False, 'max_senses': 120, 'deadline_s': 2.5,
    })]
    assert calls[0][0] is items
    assert report == store.HydrationReport(items=1)      # the reader's report, passed through

    store.hydrate(items, max_senses=5, deadline_s=1)
    assert calls[1][1]['max_senses'] == 5 and calls[1][1]['deadline_s'] == 1.0


def test_hydrate_propagates_reader_bugs(monkeypatch):
    from services.exercise_content import reader

    def broken(items, **kwargs):
        raise RuntimeError('bug')

    monkeypatch.setattr(reader, 'hydrate', broken)
    with pytest.raises(RuntimeError):
        store.hydrate([{'id': 'a'}])


def test_fetch_sense_delegates_to_the_reader(monkeypatch):
    from services.exercise_content import reader

    seen = []
    monkeypatch.setattr(reader, 'fetch_sense',
                        lambda language_id, sense_id, version: seen.append(
                            (language_id, sense_id, version)) or {'x': {}})
    assert store.fetch_sense(1, 5, 0) == {'x': {}}
    assert seen == [(1, 5, 0)]


# ---------------------------------------------------------------------------
# 6. write_sense: validation and delegation to writer.write_sense
# ---------------------------------------------------------------------------

@pytest.fixture()
def writer_calls(monkeypatch):
    from services.exercise_content import writer

    calls = []

    def fake(db, sense_id, language_id, **kwargs):
        calls.append((db, sense_id, language_id, kwargs))
        return store.WriteResult(sense_id=sense_id, version=42,
                                 inserted_ids=[r['id'] for r in kwargs['insert_rows']],
                                 deleted_count=0, updated_ids=list(kwargs['update_contents']),
                                 attempts=1)

    monkeypatch.setattr(writer, 'write_sense', fake)
    return calls


def test_write_sense_delegates_with_normalised_arguments(writer_calls):
    db = RecordingDB()
    rows = (_row(), _row())
    upd = _uuid()
    where = store.DeleteWhere(require_word_asset=True, ladder_levels=(4,))

    result = store.write_sense(db, 7, 1, insert_rows=rows, delete_where=where,
                               update_contents={upd: {'v': 1}}, max_retries=5,
                               expected_version=3)

    assert result.version == 42
    assert db.chains == [], 'the facade makes no table call itself'
    assert len(writer_calls) == 1
    got_db, sense_id, language_id, kwargs = writer_calls[0]
    assert (got_db, sense_id, language_id) == (db, 7, 1)
    assert kwargs == {'insert_rows': list(rows), 'delete_where': where,
                      'update_contents': {upd: {'v': 1}}, 'max_retries': 5,
                      'expected_version': 3}
    assert type(kwargs['insert_rows']) is list and type(kwargs['update_contents']) is dict

    store.write_sense(db, 7, 1, insert_rows=[_row()])
    assert writer_calls[1][3]['expected_version'] is None and writer_calls[1][3]['max_retries'] == 3


def test_write_sense_nothing_to_do_makes_no_call(writer_calls):
    result = store.write_sense(ExplodingDB(), 7, 1)
    assert result == store.WriteResult(sense_id=7, version=None, inserted_ids=[],
                                       deleted_count=0, updated_ids=[], attempts=0)
    assert store.write_sense(ExplodingDB(), 7, 1, insert_rows=[], update_contents={}).attempts == 0
    assert writer_calls == []


@pytest.mark.parametrize('rows', [
    [_row(sense_id=8)],                               # word_sense_id != sense_id
    [{'id': 'x'}],                                    # no word_sense_id
    [_row(language_id=3)],                            # language_id != language_id
    [_row(content='not a dict')],                     # non-dict content
    [_row(content=None)],
    [_row(), 'not-a-row'],
    [_row(word_sense_id=True)],
    [{'word_sense_id': 7, 'language_id': 1, 'content': {}}],                      # no id
    [_row(id='ex-1')],                                                            # not a uuid
    [_row(id=_uuid().upper())],                                                   # not canonical
    [_row(id=uuid.uuid4())],                                                      # UUID object
    [{'id': _uuid(), 'word_sense_id': 7, 'content': {}}],                        # no language_id
    [{'id': _uuid(), 'word_sense_id': 7, 'language_id': 1}],                     # no content
])
def test_write_sense_validation_happens_before_any_call(writer_calls, rows):
    db = RecordingDB()
    with pytest.raises(ValueError):
        store.write_sense(db, 7, 1, insert_rows=rows,
                          delete_where=store.DeleteWhere(require_word_asset=True))
    assert db.chains == [] and writer_calls == []


@pytest.mark.parametrize('kwargs', [
    {'db': None},
    {'sense_id': None}, {'sense_id': True}, {'language_id': None},
    {'insert_rows': None}, {'insert_rows': 'rows'}, {'insert_rows': {'id': 1}}, {'insert_rows': 5},
    {'delete_where': {'require_word_asset': True}},
    {'update_contents': [('a', {})]}, {'update_contents': {'a': 'text'}}, {'update_contents': {5: {}}},
    {'update_contents': {'': {}}},
    {'max_retries': 0}, {'max_retries': 1.5},
])
def test_write_sense_rejects_bad_arguments_without_calls(writer_calls, kwargs):
    db = RecordingDB()
    args = {'db': db, 'sense_id': 7, 'language_id': 1, 'insert_rows': [_row()]}
    args.update(kwargs)
    with pytest.raises(ValueError):
        store.write_sense(args.pop('db'), args.pop('sense_id'), args.pop('language_id'), **args)
    assert db.chains == [] and writer_calls == []


def test_write_sense_compares_row_ids_as_ints(writer_calls):
    store.write_sense(RecordingDB(), 7, 1, insert_rows=[_row(word_sense_id='7', language_id='1')])
    assert len(writer_calls) == 1


def test_delete_where_normalises_levels():
    assert store.DeleteWhere(ladder_levels=[9, 4, 4]).ladder_levels == (4, 9)
    assert store.DeleteWhere(ladder_levels={7}).ladder_levels == (7,)
    assert store.DeleteWhere(ladder_levels=()).ladder_levels == ()
    assert store.DeleteWhere(ladder_levels=(4, 9)) == store.DeleteWhere(ladder_levels=(9, 4))
    for bad in ((4, '9'), (True,), 4, '49', (4.0,)):
        with pytest.raises(ValueError):
            store.DeleteWhere(ladder_levels=bad)
    with pytest.raises(dataclasses.FrozenInstanceError):
        store.DeleteWhere().require_word_asset = True


def test_the_facade_loads_nothing_heavy_until_it_reads_or_writes():
    out = _run_python(
        'import json, sys\n'
        'from services.exercise_content import store\n'
        'store.rpc_content_args(); store.select_columns("id, {content}")\n'
        'store.DeleteWhere(ladder_levels=(4,)); store.base_version([])\n'
        'store.content_path(1, 2, 0); store.canonical({}); store.reset_state()\n'
        'names = ["services.exercise_content.reader", "services.exercise_content.writer",\n'
        '         "services.exercise_content.backends", "services.supabase_factory",\n'
        '         "supabase", "httpx", "storage3"]\n'
        'print(json.dumps({n: n in sys.modules for n in names}))\n'
    )
    assert json.loads(out) == {
        'services.exercise_content.reader': False, 'services.exercise_content.writer': False,
        'services.exercise_content.backends': False, 'services.supabase_factory': False,
        'supabase': False, 'httpx': False, 'storage3': False,
    }


@pytest.mark.parametrize('sense_id, language_id', [('7', 1), (7, '1'), (0, 1), (7, True)])
def test_write_sense_needs_positive_int_sense_and_language(writer_calls, sense_id, language_id):
    with pytest.raises(ValueError):
        store.write_sense(RecordingDB(), sense_id, language_id, update_contents={_uuid(): {}})
    assert writer_calls == []


def test_write_sense_rejects_duplicates_and_bad_update_ids(writer_calls):
    row = _row()
    with pytest.raises(ValueError):
        store.write_sense(RecordingDB(), 7, 1, insert_rows=[row, dict(row)])
    with pytest.raises(ValueError):
        store.write_sense(RecordingDB(), 7, 1, update_contents={'ex-1': {}})
    with pytest.raises(ValueError):
        store.write_sense(RecordingDB(), 7, 1, insert_rows=[row],
                          update_contents={row['id']: {}})
    assert writer_calls == []


# ---------------------------------------------------------------------------
# 8. Codec
# ---------------------------------------------------------------------------

def test_content_path():
    assert store.content_path(1, 5, 0) == 'zh/5.v0.json'
    assert store.content_path(2, 5, 3) == 'en/5.v3.json'
    assert store.content_path(3, 123, 4711) == 'ja/123.v4711.json'
    assert store.content_path(9, 5, 0) == '9/5.v0.json'
    for bad in ((1, '5', 0), (1, 5, -1), (True, 5, 0), (1, 5, 1.0), (None, 5, 0)):
        with pytest.raises(ValueError):
            store.content_path(*bad)


EXERCISES = {
    'b0000000-0000-4000-8000-000000000002': {'z': 1, 'a': ['书', {'y': True, 'b': None}]},
    'a0000000-0000-4000-8000-000000000001': {'sentence': '日本語の文。', 'n': 1.5},
}


def test_encode_sense_file_matches_the_adr_bytes():
    data = store.encode_sense_file(12345, 1, 0, EXERCISES)
    expected = json.dumps(
        {'format': 1, 'sense_id': 12345, 'language_id': 1, 'version': 0, 'exercises': EXERCISES},
        ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')
    assert data == expected
    assert data.startswith(b'{"exercises":{"a0000000-')
    assert data.endswith(b'"format":1,"language_id":1,"sense_id":12345,"version":0}')
    assert '日本語の文。'.encode('utf-8') in data          # ensure_ascii=False
    assert b' ' not in data.replace('日本語の文。'.encode('utf-8'), b'')
    reordered = dict(reversed(list(EXERCISES.items())))
    assert store.encode_sense_file(12345, 1, 0, reordered) == data


def test_encode_sense_file_rejects_bad_input():
    with pytest.raises(ValueError):
        store.encode_sense_file(1, 1, 0, {'x': 'not a dict'})
    with pytest.raises(ValueError):
        store.encode_sense_file(1, 1, 0, {5: {}})
    with pytest.raises(ValueError):
        store.encode_sense_file(1, 1, 0, [('x', {})])
    with pytest.raises(ValueError):
        store.encode_sense_file(1, 1, 0, {'x': {'when': datetime.now()}})
    with pytest.raises(ValueError):
        store.encode_sense_file(1, 1, -1, {})


def test_decode_sense_file_round_trips_with_fresh_objects():
    data = store.encode_sense_file(77, 3, 9, EXERCISES)
    first = store.decode_sense_file(data, sense_id=77, version=9)
    assert first == EXERCISES
    first['a0000000-0000-4000-8000-000000000001']['n'] = 99
    assert store.decode_sense_file(data, sense_id=77, version=9) == EXERCISES
    assert store.decode_sense_file(bytearray(data), sense_id=77, version=9) == EXERCISES
    assert store.decode_sense_file(memoryview(data), sense_id=77, version=9) == EXERCISES
    assert store.decode_sense_file(data.decode('utf-8'), sense_id=77, version=9) == EXERCISES
    assert store.decode_sense_file(store.encode_sense_file(1, 1, 0, {}), sense_id=1, version=0) == {}


def _doc(**overrides):
    doc = {'format': 1, 'sense_id': 5, 'language_id': 1, 'version': 2, 'exercises': {'x': {}}}
    doc.update(overrides)
    return json.dumps(doc).encode('utf-8')


@pytest.mark.parametrize('data', [
    b'{not json', b'\xff\xfe', b'[]', b'null', _doc(format=2), _doc(format='1'),
    _doc(format=True), json.dumps({'sense_id': 5, 'version': 2, 'language_id': 1,
                                   'exercises': {}}).encode(),
    _doc(sense_id=6), _doc(sense_id='5'), _doc(version=3), _doc(version=None),
    _doc(language_id=None), _doc(language_id='zh'), _doc(exercises=[]), _doc(exercises=None),
    _doc(exercises={'x': 'text'}), _doc(exercises={'x': None}),
])
def test_decode_sense_file_rejects_corrupt_or_mismatched_files(data):
    with pytest.raises(store.ContentStorageError):
        store.decode_sense_file(data, sense_id=5, version=2)


def test_decode_sense_file_rejects_non_bytes_as_corrupt_and_bad_args_as_value_error():
    with pytest.raises(store.ContentStorageError):
        store.decode_sense_file(None, sense_id=5, version=2)
    with pytest.raises(ValueError):
        store.decode_sense_file(_doc(), sense_id='5', version=2)


def test_canonical_is_deterministic():
    a = {'b': 1, 'a': {'d': [1, 2], 'c': '书'}}
    b = {'a': {'c': '书', 'd': [1, 2]}, 'b': 1}
    assert store.canonical(a) == store.canonical(b) == '{"a":{"c":"书","d":[1,2]},"b":1}'
    assert store.canonical(None) == 'null'
    assert store.canonical({'a': [2, 1]}) != store.canonical({'a': [1, 2]})


# ---------------------------------------------------------------------------
# 9. InMemoryBackend
# ---------------------------------------------------------------------------

def test_in_memory_put_get_delete_and_calls():
    mem = InMemoryBackend()
    assert mem.get('zh/1.v0.json') is None
    mem.put('zh/1.v0.json', b'{}')
    mem.put('zh/2.v0.json', bytearray(b'[]'))
    assert mem.get('zh/1.v0.json') == b'{}'
    assert mem.get('zh/2.v0.json') == b'[]'
    with pytest.raises(store.AlreadyExists):
        mem.put('zh/1.v0.json', b'other')
    assert mem.get('zh/1.v0.json') == b'{}'
    mem.delete(['zh/1.v0.json', 'zh/missing.json'])
    mem.delete([])
    assert mem.get('zh/1.v0.json') is None
    assert mem.calls == [
        ('get', 'zh/1.v0.json'), ('put', 'zh/1.v0.json'), ('put', 'zh/2.v0.json'),
        ('get', 'zh/1.v0.json'), ('get', 'zh/2.v0.json'), ('put', 'zh/1.v0.json'),
        ('get', 'zh/1.v0.json'), ('delete', 'zh/1.v0.json'), ('delete', 'zh/missing.json'),
        ('get', 'zh/1.v0.json'),
    ]
    assert mem.delete_batches == [('zh/1.v0.json', 'zh/missing.json')]
    assert mem.calls_for('put') == ['zh/1.v0.json', 'zh/2.v0.json', 'zh/1.v0.json']
    assert len(mem.call_threads) == len(mem.calls)
    mem.clear_calls()
    assert mem.calls == [] and mem.delete_batches == []


def test_in_memory_rejects_bad_paths_and_data():
    mem = InMemoryBackend()
    for bad in ('', '/zh/1.json', None):
        with pytest.raises(ValueError):
            mem.get(bad)
    with pytest.raises(TypeError):
        mem.put('zh/1.json', 'text')
    with pytest.raises(TypeError):
        mem.delete('zh/1.json')


def test_in_memory_list_is_sorted_and_folder_scoped():
    t0 = datetime(2026, 11, 1, tzinfo=timezone.utc)
    mem = InMemoryBackend(clock=lambda: t0)
    for path in ('zh/20.v1.json', 'zh/3.v0.json', 'ja/1.v0.json', '_archive/zh/1.v0.json',
                 'zh/sub/9.v0.json', 'root.json'):
        mem.put(path, b'12345')

    listed = list(mem.list('zh/'))
    assert [o.path for o in listed] == ['zh/20.v1.json', 'zh/3.v0.json']
    assert listed[0] == StoredObject(path='zh/20.v1.json', size=5, created_at=t0)
    assert [o.path for o in mem.list('zh')] == ['zh/20.v1.json', 'zh/3.v0.json']
    assert [o.path for o in mem.list('')] == ['root.json']
    assert [o.path for o in mem.list('_archive/zh/')] == ['_archive/zh/1.v0.json']
    assert list(mem.list('en/')) == []
    assert ('list', 'zh/') in mem.calls


def test_in_memory_created_at_is_settable():
    mem = InMemoryBackend()
    old = datetime.now(timezone.utc) - timedelta(days=3)
    mem.put('zh/1.v0.json', b'{}')
    mem.set_created_at('zh/1.v0.json', old)
    mem.seed('zh/2.v0.json', b'{}', created_at=None)
    mem.set_created_at('zh/2.v0.json', None)
    by_path = {o.path: o for o in mem.list('zh/')}
    assert by_path['zh/1.v0.json'].created_at == old
    assert by_path['zh/2.v0.json'].created_at is None
    with pytest.raises(KeyError):
        mem.set_created_at('zh/9.v0.json', old)


def test_in_memory_seed_does_not_record_and_may_overwrite():
    mem = InMemoryBackend()
    mem.seed('zh/1.v0.json', b'a')
    mem.seed('zh/1.v0.json', b'b')
    assert mem.calls == []
    assert mem.objects() == {'zh/1.v0.json': b'b'}
    assert mem.paths() == ['zh/1.v0.json'] and mem.exists('zh/1.v0.json')


def test_in_memory_fail_next_is_per_op_and_used_once():
    mem = InMemoryBackend()
    mem.seed('zh/1.v0.json', b'{}')
    mem.fail_next('get', store.ContentStorageError('503'))
    mem.fail_next('get', TimeoutError('slow'))
    mem.fail_next('put', store.AlreadyExists('raced'))
    with pytest.raises(store.ContentStorageError):
        mem.get('zh/1.v0.json')
    with pytest.raises(TimeoutError):
        mem.get('zh/1.v0.json')
    assert mem.get('zh/1.v0.json') == b'{}'
    with pytest.raises(store.AlreadyExists):
        mem.put('zh/2.v0.json', b'{}')
    assert not mem.exists('zh/2.v0.json')
    mem.fail_next('delete', RuntimeError('down'))
    with pytest.raises(RuntimeError):
        mem.delete(['zh/1.v0.json'])
    assert mem.exists('zh/1.v0.json')
    with pytest.raises(ValueError):
        mem.fail_next('head', RuntimeError())
    assert mem.calls[:2] == [('get', 'zh/1.v0.json'), ('get', 'zh/1.v0.json')]


def test_in_memory_latency_overlaps_across_threads():
    mem = InMemoryBackend(latency_s=0.2)
    for i in range(8):
        mem.seed(f'zh/{i}.v0.json', b'{}')
    threads = [threading.Thread(target=mem.get, args=(f'zh/{i}.v0.json',), name=f'exc-fetch_{i}')
               for i in range(8)]
    started = time.monotonic()
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert time.monotonic() - started < 0.6
    assert sorted(mem.call_threads) == sorted(f'exc-fetch_{i}' for i in range(8))

    per_op = InMemoryBackend(latency_s={'put': 0.05})
    started = time.monotonic()
    per_op.get('zh/x.json')
    assert time.monotonic() - started < 0.05
    started = time.monotonic()
    per_op.put('zh/x.json', b'{}')
    assert time.monotonic() - started >= 0.05


def test_in_memory_put_is_write_once_under_concurrency():
    mem = InMemoryBackend()
    barrier = threading.Barrier(50)
    outcomes: list[str] = []
    lock = threading.Lock()

    def put(i):
        barrier.wait()
        try:
            mem.put('zh/1.v5.json', str(i).encode())
            result = 'ok'
        except store.AlreadyExists:
            result = 'exists'
        with lock:
            outcomes.append(result)

    threads = [threading.Thread(target=put, args=(i,)) for i in range(50)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert outcomes.count('ok') == 1 and outcomes.count('exists') == 49
    assert len(mem.calls) == 50


# ---------------------------------------------------------------------------
# 10. Backend singleton, caches, reset
# ---------------------------------------------------------------------------

def test_backend_is_a_lazy_singleton_built_from_config_without_io(monkeypatch):
    import socket

    def no_network(*args, **kwargs):
        raise AssertionError('constructing the backend must not open a socket')

    monkeypatch.setattr(socket, 'socket', no_network)
    monkeypatch.setattr(socket, 'create_connection', no_network)
    store.set_backend(None)
    monkeypatch.setattr(Config, 'SUPABASE_URL', 'https://abc.supabase.co/')
    monkeypatch.setattr(Config, 'SUPABASE_SERVICE_ROLE_KEY', 'super-secret-service-key')
    monkeypatch.setattr(Config, 'EXERCISE_CONTENT_BUCKET', 'my-bucket')

    first = store.backend()
    assert isinstance(first, SupabaseStorageBackend)
    assert store.backend() is first
    assert first.bucket == 'my-bucket'
    assert 'super-secret-service-key' not in repr(first)


def test_backend_builds_even_without_credentials(monkeypatch):
    """The sweep builds it and refuses on its own (exit 2) when base_url is None."""
    _no_credentials(monkeypatch)
    backend = store.backend()
    assert isinstance(backend, SupabaseStorageBackend) and backend.base_url is None


def test_set_backend_overrides_and_none_rebuilds(monkeypatch):
    monkeypatch.setattr(Config, 'SUPABASE_URL', 'https://abc.supabase.co')
    monkeypatch.setattr(Config, 'SUPABASE_SERVICE_ROLE_KEY', 'k')
    mem = InMemoryBackend()
    store.set_backend(mem)
    assert store.backend() is mem
    store.set_backend(None)
    rebuilt = store.backend()
    assert isinstance(rebuilt, SupabaseStorageBackend)
    store.reset_state()
    assert store.backend() is not rebuilt


def test_reset_state_clears_backend_warnings_and_runs_hooks(monkeypatch, caplog):
    caplog.set_level(logging.ERROR, logger=LOGGER)
    monkeypatch.setattr(store, '_reset_hooks', dict(store._reset_hooks))
    ran = []
    store._on_reset('test-hook', lambda: ran.append('a'))
    store._on_reset('test-hook', lambda: ran.append('b'))       # replaces by key
    store._on_reset('broken-hook', lambda: 1 / 0)                # logged, not raised

    mem = InMemoryBackend()
    store.set_backend(mem)
    store._log_not_configured()
    store._log_not_configured()
    store.reset_state()

    assert ran == ['b']
    assert store._backend is None and store._backend_override is False
    store._log_not_configured()
    logged = [r for r in _errors(caplog) if 'are not set' in r.getMessage()]
    assert len(logged) == 2, 'the warn-once flag must be cleared by reset_state'


def test_reset_state_closes_only_a_backend_it_built(monkeypatch):
    closed = []

    class Closable(InMemoryBackend):
        def close(self):
            closed.append(self)

    built = Closable()
    monkeypatch.setattr(SupabaseStorageBackend, 'from_config', classmethod(lambda cls: built))
    store.set_backend(None)
    assert store.backend() is built
    store.reset_state()
    assert closed == [built]

    installed = Closable()
    store.set_backend(installed)
    store.reset_state()
    assert closed == [built]


def _fake_cache_module():
    module = types.ModuleType('services.exercise_content.cache')

    class ByteLRU:
        def __init__(self, max_bytes):
            self.max_bytes = max_bytes

    class NegativeCache:
        def __init__(self, ttl_s=60.0, clock=time.monotonic):
            self.ttl_s = ttl_s

    module.ByteLRU = ByteLRU
    module.NegativeCache = NegativeCache
    return module


def test_cache_slots_are_lazy_process_singletons(monkeypatch):
    monkeypatch.setitem(sys.modules, 'services.exercise_content.cache', _fake_cache_module())
    monkeypatch.setattr(Config, 'EXERCISE_CONTENT_CACHE_MB', 8)

    lru = store._content_cache()
    neg = store._negative_cache()
    assert lru.max_bytes == 8 * 1024 * 1024
    assert neg.ttl_s == 60.0
    assert store._content_cache() is lru and store._negative_cache() is neg

    store.set_backend(InMemoryBackend())
    assert store._content_cache() is not lru
    lru2, neg2 = store._content_cache(), store._negative_cache()
    store.reset_state()
    assert store._content_cache() is not lru2 and store._negative_cache() is not neg2


def test_cache_slots_are_none_without_cache_module(monkeypatch):
    monkeypatch.setitem(sys.modules, 'services.exercise_content.cache', None)
    assert store._content_cache() is None
    assert store._negative_cache() is None


def test_cache_key_and_lang_code():
    assert store._cache_key(1, 5, 0) == ('zh', 5, 0)
    assert store._cache_key(3, 5, 7) == ('ja', 5, 7)
    assert store._lang_code(9) == '9'


def test_settings_fall_back_on_bad_values(monkeypatch, caplog):
    caplog.set_level(logging.ERROR, logger=LOGGER)
    monkeypatch.setattr(Config, 'EXERCISE_CONTENT_MAX_SENSES_PER_CALL', -3)
    monkeypatch.setattr(Config, 'EXERCISE_CONTENT_DEADLINE_S', 'never')
    monkeypatch.setattr(Config, 'EXERCISE_CONTENT_HTTP_TIMEOUT_S', 1.5)
    monkeypatch.setattr(Config, 'EXERCISE_CONTENT_BUCKET', None)
    assert store._setting_int('EXERCISE_CONTENT_MAX_SENSES_PER_CALL', 160) == 160
    assert store._setting_float('EXERCISE_CONTENT_DEADLINE_S', 3.0, low=0.0,
                                low_inclusive=False) == 3.0
    assert store._setting_float('EXERCISE_CONTENT_HTTP_TIMEOUT_S', 2.0, high=1.0) == 2.0
    assert store._setting_str('EXERCISE_CONTENT_BUCKET', 'exercise-content') == 'exercise-content'
    assert len(_errors(caplog)) == 3
