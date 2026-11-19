"""TASK-1011 — the write path (ADR-049 §4, §8, §9) and the shared FakeContentDB.

Runs ``store.write_sense`` against ``FakeContentDB`` (the §8 RPCs + an
in-memory ``exercises`` table without the dropped ``content`` column) and an
``InMemoryBackend``. Fully offline. Since TASK-1031 the file at the sense's
current version is the only content source, so "what is stored" is read back
with ``_served`` (file v(current) for each live row of the sense).
"""

from __future__ import annotations

import copy
import logging
import sys
import threading
import uuid

import pytest
from postgrest.exceptions import APIError

from services.exercise_content import store, writer
from services.exercise_content.store import (
    AlreadyExists, ContentStorageError, ContentWriteConflict, DeleteWhere, ExerciseContentError,
    WriteResult,
)
from services.pagination import fetch_all
from tests.exercise_content_fakes import (
    CONTEXT_FREE_TYPES, FakeContentDB, FakeDBError, InMemoryBackend, dedupe_key_for,
)

LOGGER = 'services.exercise_content'
SENSE = 5


def _uuid() -> str:
    return str(uuid.uuid4())


@pytest.fixture
def mem(monkeypatch) -> InMemoryBackend:
    monkeypatch.setattr(writer, 'RETRY_BACKOFF_S', 0.0)
    backend = InMemoryBackend()
    store.set_backend(backend)
    return backend


def _content(tag: str, **extra) -> dict:
    return {'sentence': f'sentence {tag}', 'options': [f'{tag}-a', f'{tag}-b'],
            'hant': {'sentence': f'句 {tag}'}, **extra}


def _row(*, sense=SENSE, lang=1, level=3, asset=99, kind='cloze_completion', tag=None,
         **extra) -> dict:
    row = {'id': _uuid(), 'language_id': lang, 'exercise_type': kind,
           'source_type': 'vocabulary', 'content': _content(tag or kind + str(level)),
           'tags': {'variant': 'A'}, 'complexity_tier': 'T2', 'is_active': True,
           'word_sense_id': sense, 'word_asset_id': asset, 'ladder_level': level}
    row.update(extra)
    return row


def _bare(row: dict, **extra) -> dict:
    """``row`` as a direct table insert would send it: no ``content`` column any more."""
    return {**{k: v for k, v in row.items() if k != 'content'}, **extra}


def _file(mem, version, sense=SENSE, lang=1) -> dict:
    data = mem.objects()[store.content_path(lang, sense, version)]
    return store.decode_sense_file(data, sense_id=sense, version=version)


def _served(db, mem, sense=SENSE, lang=1) -> dict:
    """What a reader gets now: file v(current) for each live row of the sense."""
    (version,) = db.versions(sense)
    content = _file(mem, version, sense, lang)
    return {r['id']: content[r['id']] for r in db.rows(sense)}


def _seed_sense(db, mem, rows, *, version=0, lang=1, file_contents=None):
    """Rows at ``version`` in the table and, unless ``file_contents is False``, file ``version``."""
    db.seed([{**r, 'content_version': version} for r in rows])
    db.next_version = max(db.next_version, version + 1)
    if file_contents is not False:
        contents = file_contents if file_contents is not None else {r['id']: r['content']
                                                                     for r in rows}
        mem.seed(store.content_path(lang, SENSE, version),
                 store.encode_sense_file(SENSE, lang, version, contents))


# ---------------------------------------------------------------------------
# writes
# ---------------------------------------------------------------------------

def test_new_sense_one_begin_one_file_one_commit(mem, caplog):
    caplog.set_level(logging.INFO, logger=LOGGER)
    db = FakeContentDB()
    rows = [_row(level=1), _row(level=2, kind='tone_id_word')]

    result = store.write_sense(db, SENSE, 1, insert_rows=rows)

    assert db.rpc_calls('exercise_content_begin') == [{'p_sense_id': SENSE}]
    assert db.rpc_calls('exercise_content_commit') == [{
        'p_sense_id': SENSE, 'p_expected_version': 0, 'p_expected_ids': [], 'p_new_version': 1,
        'p_delete_ids': [], 'p_insert_rows': rows, 'p_update_contents': {}}]
    assert mem.calls_for('get') == [] and mem.calls_for('put') == ['zh/5.v1.json']
    assert mem.objects()['zh/5.v1.json'] == store.encode_sense_file(
        SENSE, 1, 1, {r['id']: r['content'] for r in rows})
    assert result == WriteResult(sense_id=SENSE, version=1,
                                 inserted_ids=[r['id'] for r in rows], deleted_count=0,
                                 updated_ids=[], attempts=1)
    stored = {r['id']: r for r in db.rows(SENSE)}
    assert all(stored[r['id']]['content_version'] == 1 for r in rows)
    assert all('content' not in stored[r['id']] for r in rows), 'no content column'
    assert stored[rows[0]['id']]['dedupe_key'] is None
    assert stored[rows[1]['id']]['dedupe_key'] == dedupe_key_for('tone_id_word', rows[1]['content'])
    lines = [r.getMessage() for r in caplog.records if r.getMessage().startswith(
        'exercise_content.write ')]
    assert lines == ['exercise_content.write sense=5 version=1 attempts=1 inserted=2 '
                     'deleted=0 updated=0']


def test_scoped_replace_keeps_untouched_content_from_file_v(mem):
    db = FakeContentDB()
    keep3, old4, plain4, keep5 = (_row(level=3), _row(level=4), _row(level=4, asset=None),
                                  _row(level=5))
    rows = [keep3, old4, plain4, keep5]
    file_v = {r['id']: _content('from-file-' + r['id'][:4]) for r in rows}
    _seed_sense(db, mem, rows, version=7, file_contents=file_v)
    db.next_version = 20
    new4 = [_row(level=4, tag='new-a'), _row(level=4, tag='new-b')]
    mem.clear_calls()

    result = store.write_sense(db, SENSE, 1, insert_rows=new4,
                               delete_where=DeleteWhere(require_word_asset=True, ladder_levels=(4,)))

    (commit,) = db.rpc_calls('exercise_content_commit')
    assert commit['p_delete_ids'] == [old4['id']]
    assert commit['p_expected_version'] == 7 and commit['p_new_version'] == 20
    assert commit['p_expected_ids'] == sorted(r['id'] for r in rows)
    new_file = _file(mem, 20)
    assert set(new_file) == {keep3['id'], plain4['id'], keep5['id'], *(r['id'] for r in new4)}
    for kept in (keep3, plain4, keep5):
        assert store.canonical(new_file[kept['id']]) == store.canonical(file_v[kept['id']])
    assert old4['id'] not in new_file
    assert mem.calls_for('get') == ['zh/5.v7.json']
    assert db.table_calls('select') == [], 'everything came from file v7'
    assert sorted(r['id'] for r in db.rows(SENSE)) == sorted(new_file)
    assert db.versions(SENSE) == [20]
    assert result.deleted_count == 1 and result.version == 20


def test_full_replace_without_levels(mem):
    db = FakeContentDB()
    asset_rows = [_row(level=1), _row(level=2)]
    sense_less_asset = _row(level=3, asset=None)
    _seed_sense(db, mem, asset_rows + [sense_less_asset])
    new = [_row(level=1, tag='n1')]
    result = store.write_sense(db, SENSE, 1, insert_rows=new,
                               delete_where=DeleteWhere(require_word_asset=True))
    assert result.deleted_count == 2
    assert set(_file(mem, 1)) == {sense_less_asset['id'], new[0]['id']}


@pytest.mark.parametrize('case', ['not_in_sense', 'deleted', 'insert_exists'])
def test_conflicting_ids_raise_value_error_before_any_upload(mem, case):
    db = FakeContentDB()
    level4 = _row(level=4)
    other = _row(level=2)
    _seed_sense(db, mem, [level4, other])
    mem.clear_calls()
    kwargs = {
        'not_in_sense': dict(update_contents={_uuid(): _content('x')}),
        'deleted': dict(update_contents={level4['id']: _content('x')},
                        delete_where=DeleteWhere(ladder_levels=(4,))),
        'insert_exists': dict(insert_rows=[{**_row(level=2), 'id': other['id']}]),
    }[case]
    with pytest.raises(ValueError):
        store.write_sense(db, SENSE, 1, **kwargs)
    assert mem.calls_for('put') == []
    assert db.rpc_calls('exercise_content_commit') == []


def test_reinserting_a_deleted_id_is_allowed(mem):
    db = FakeContentDB()
    row = _row(level=4)
    _seed_sense(db, mem, [row])
    again = {**row, 'content': _content('replacement')}
    store.write_sense(db, SENSE, 1, insert_rows=[again],
                      delete_where=DeleteWhere(ladder_levels=(4,)))
    assert db.row(row['id'])['content_version'] == 1
    assert _file(mem, 1) == {row['id']: _content('replacement')}


def test_update_writes_one_new_version(mem):
    db = FakeContentDB()
    a, b = _row(level=1), _row(level=2, kind='hanzi_to_pinyin')
    _seed_sense(db, mem, [a, b])
    new_b = _content('edited', context_sentence='我们')
    result = store.write_sense(db, SENSE, 1, update_contents={b['id']: new_b})
    assert result.updated_ids == [b['id']] and result.version == 1
    assert _file(mem, 1) == {a['id']: a['content'], b['id']: new_b}
    assert _served(db, mem) == {a['id']: a['content'], b['id']: new_b}
    assert db.row(b['id'])['dedupe_key'] == dedupe_key_for('hanzi_to_pinyin', new_b)
    (commit,) = db.rpc_calls('exercise_content_commit')
    assert commit['p_update_contents'] == {b['id']: new_b}


# ---------------------------------------------------------------------------
# base content
# ---------------------------------------------------------------------------

def test_rows_at_mixed_versions_are_reunified(mem):
    """The commit stamps every row of the sense, so a row left at an older version moves
    to the new version with the rest (its content comes from file v(current))."""
    db = FakeContentDB()
    a, late = _row(level=1), _row(level=2)
    _seed_sense(db, mem, [a, late], version=4)
    db.table('exercises').update({'content_version': 0}).eq('id', late['id']).execute()
    db.next_version = 10
    assert db.versions(SENSE) == [0, 4]
    result = store.write_sense(db, SENSE, 1, update_contents={a['id']: _content('a2')})
    assert result.version == 10 and db.versions(SENSE) == [10]
    assert mem.calls_for('get') == ['zh/5.v4.json']
    assert _file(mem, 10) == {a['id']: _content('a2'), late['id']: late['content']}


def test_without_file_v_the_write_raises_before_upload(mem):
    db = FakeContentDB()
    a = _row(level=1)
    _seed_sense(db, mem, [a], file_contents=False)
    with pytest.raises(ContentStorageError, match='in file v0'):
        store.write_sense(db, SENSE, 1, insert_rows=[_row(level=2)])
    assert mem.calls_for('get') == ['zh/5.v0.json']
    assert db.table_calls() == [], 'no table read: the file is the only source'
    assert mem.calls_for('put') == [] and db.rpc_calls('exercise_content_commit') == []


def test_after_the_column_drop_the_file_is_the_only_source(mem):
    db = FakeContentDB()
    a, b = _row(level=1), _row(level=2)
    _seed_sense(db, mem, [a, b], file_contents={a['id']: a['content']})
    with pytest.raises(ContentStorageError, match=f"1 surviving exercise.*first: {b['id']}"):
        store.write_sense(db, SENSE, 1, insert_rows=[_row(level=3)])
    assert mem.calls_for('put') == [] and db.table_calls() == []

    db2 = FakeContentDB()
    _seed_sense(db2, mem, [a, b], version=2)
    new = _row(level=3, kind='tone_id_word')
    store.write_sense(db2, SENSE, 1, insert_rows=[new])
    assert db2.table_calls('select') == []
    stored = db2.row(new['id'])
    assert 'content' not in stored
    assert stored['dedupe_key'] == dedupe_key_for('tone_id_word', new['content'])


def test_a_corrupt_or_unreadable_base_file_raises(mem):
    db = FakeContentDB()
    a = _row(level=1)
    _seed_sense(db, mem, [a], file_contents=False)
    mem.seed('zh/5.v0.json', b'{"format": 1, "sense_id": 6, "version": 0, "language_id": 1, '
                             b'"exercises": {}}')
    with pytest.raises(ContentStorageError):
        store.write_sense(db, SENSE, 1, insert_rows=[_row(level=2)])

    db2 = FakeContentDB()
    _seed_sense(db2, mem, [a], version=3)
    mem.fail_next('get', RuntimeError('socket closed'))
    with pytest.raises(ContentStorageError):
        store.write_sense(db2, SENSE, 1, insert_rows=[_row(level=2)])
    assert mem.calls_for('put') == []


# ---------------------------------------------------------------------------
# races
# ---------------------------------------------------------------------------

def test_a_commit_between_begin_and_commit_is_retried_and_preserved(mem):
    db = FakeContentDB()
    a, b = _row(level=1), _row(level=2)
    _seed_sense(db, mem, [a, b])

    def other_writer(db_, params):
        store.write_sense(db_, SENSE, 1, update_contents={b['id']: _content('other')})

    db.on('before:exercise_content_commit', other_writer)
    result = store.write_sense(db, SENSE, 1, update_contents={a['id']: _content('mine')})

    assert result.attempts == 2 and result.version == 3
    assert mem.calls_for('put') == ['zh/5.v1.json', 'zh/5.v2.json', 'zh/5.v3.json']
    assert mem.calls_for('delete') == ['zh/5.v1.json']
    assert not mem.exists('zh/5.v1.json')
    assert _file(mem, 3) == {a['id']: _content('mine'), b['id']: _content('other')}
    assert _served(db, mem) == {a['id']: _content('mine'), b['id']: _content('other')}
    assert db.versions(SENSE) == [3]


def test_a_row_deleted_outside_the_store_gives_rows_changed_and_a_retry(mem, caplog):
    caplog.set_level(logging.INFO, logger=LOGGER)
    db = FakeContentDB()
    a, b = _row(level=1), _row(level=2)
    _seed_sense(db, mem, [a, b])
    db.on('before:exercise_content_commit',
          lambda db_, params: db_.table('exercises').delete().eq('id', b['id']).execute())

    result = store.write_sense(db, SENSE, 1, update_contents={a['id']: _content('mine')})

    assert result.attempts == 2
    assert any('reason=rows_changed' in r.getMessage() for r in caplog.records)
    assert _file(mem, result.version) == {a['id']: _content('mine')}
    assert mem.calls_for('delete') == ['zh/5.v1.json']


def test_max_retries_conflicts_raise_and_change_nothing(mem):
    db = FakeContentDB()
    a = _row(level=1)
    _seed_sense(db, mem, [a])

    def bump(db_, params):                       # another writer commits file + rows first
        version = db_.next_version
        db_.next_version += 1
        mem.seed(store.content_path(1, SENSE, version),
                 store.encode_sense_file(SENSE, 1, version, {a['id']: a['content']}))
        db_.table('exercises').update({'content_version': version}).eq(
            'word_sense_id', SENSE).execute()

    db.on('before:exercise_content_commit', bump, once=False)
    new = _row(level=2)
    with pytest.raises(ContentWriteConflict):
        store.write_sense(db, SENSE, 1, insert_rows=[new], max_retries=3)

    assert len(db.rpc_calls('exercise_content_begin')) == 3
    assert len(db.rpc_calls('exercise_content_commit')) == 3
    assert db.row(new['id']) is None
    assert [r['id'] for r in db.rows(SENSE)] == [a['id']]
    assert _file(mem, 0) == {a['id']: a['content']}
    puts = mem.calls_for('put')
    assert len(puts) == 3 and mem.calls_for('delete') == puts
    assert all(not mem.exists(p) for p in puts)


# ---------------------------------------------------------------------------
# expected_version: read-modify-write callers (review finding 2026-11-17)
# ---------------------------------------------------------------------------

def test_expected_version_matching_writes_normally(mem):
    db = FakeContentDB()
    a = _row(level=1)
    _seed_sense(db, mem, [a], version=4)
    result = store.write_sense(db, SENSE, 1, update_contents={a['id']: _content('mine')},
                               expected_version=4)
    assert result.version == 5 and _file(mem, 5) == {a['id']: _content('mine')}


def test_a_stale_read_modify_write_is_refused_before_any_upload(mem, caplog):
    """The fix scripts read content at version N, edit it for a while, then write it back.
    If another writer committed N+1 meanwhile, writing would silently drop that edit."""
    caplog.set_level(logging.INFO, logger=LOGGER)
    db = FakeContentDB()
    a, b = _row(level=1), _row(level=2)
    _seed_sense(db, mem, [a, b])
    read_at = store.base_version([{**r, 'content_version': 0} for r in (a, b)])
    stale_a = {**a['content'], 'audio_url': 'https://r2.example/a.mp3'}

    other = store.write_sense(db, SENSE, 1, update_contents={a['id']: _content('mirror')})
    mem.clear_calls()
    db.calls.clear()

    with pytest.raises(ContentWriteConflict, match='read at version 0, now at 1'):
        store.write_sense(db, SENSE, 1, update_contents={a['id']: stale_a},
                          expected_version=read_at)

    assert len(db.rpc_calls('exercise_content_begin')) == 1, 'no retry: the base is stale'
    assert db.rpc_calls('exercise_content_commit') == []
    assert mem.calls_for('put') == []
    assert _served(db, mem)[a['id']] == _content('mirror')
    assert db.versions(SENSE) == [other.version]
    assert any('write_stale' in r.getMessage() for r in caplog.records)


def test_a_commit_racing_a_read_modify_write_is_not_retried_over(mem):
    db = FakeContentDB()
    a, b = _row(level=1), _row(level=2)
    _seed_sense(db, mem, [a, b])

    def other_writer(db_, params):
        store.write_sense(db_, SENSE, 1, update_contents={b['id']: _content('other')})

    db.on('before:exercise_content_commit', other_writer)
    with pytest.raises(ContentWriteConflict, match='now at 2'):
        store.write_sense(db, SENSE, 1, update_contents={a['id']: _content('mine')},
                          expected_version=0)
    assert _served(db, mem) == {a['id']: a['content'], b['id']: _content('other')}
    assert not mem.exists('zh/5.v1.json'), 'the lost attempt\'s file is removed'


@pytest.mark.parametrize('bad', [-1, 1.0, '0', True])
def test_expected_version_must_be_a_non_negative_int(mem, bad):
    db = FakeContentDB()
    with pytest.raises(ValueError, match='expected_version'):
        store.write_sense(db, SENSE, 1, update_contents={_uuid(): _content('x')},
                          expected_version=bad)
    assert db.calls == []


@pytest.mark.parametrize('rows, expected', [
    ([{'content_version': 3}, {'content_version': '5'}], 5),
    ([{'content_version': 0}], 0),
    ([{'content_version': 3}, {}], None),          # a select without content_version
    ([{'content_version': None}], None),
    ([], None),
    ([{'content_version': -1}], None),
])
def test_base_version(rows, expected):
    assert store.base_version(rows) == expected


def test_two_threads_updating_different_exercises_lose_nothing(mem):
    db = FakeContentDB()
    a, b = _row(level=1), _row(level=2)
    _seed_sense(db, mem, [a, b])
    gate = threading.Barrier(2)
    begins = []
    lock = threading.Lock()

    def both_begin_first(db_, payload):
        with lock:
            begins.append(1)
            first_round = len(begins) <= 2
        if first_round:
            gate.wait(timeout=5)

    db.on('after:exercise_content_begin', both_begin_first, once=False)
    results, errors = {}, []

    def run(name, exercise_id):
        try:
            results[name] = store.write_sense(db, SENSE, 1,
                                              update_contents={exercise_id: _content(name)})
        except Exception as exc:  # pragma: no cover - surfaced below
            errors.append(exc)

    threads = [threading.Thread(target=run, args=('A', a['id'])),
               threading.Thread(target=run, args=('B', b['id']))]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(10)

    assert errors == []
    assert sorted(r.attempts for r in results.values()) == [1, 2]
    final = max(r.version for r in results.values())
    assert db.versions(SENSE) == [final]
    assert _file(mem, final) == {a['id']: _content('A'), b['id']: _content('B')}
    assert _served(db, mem) == {a['id']: _content('A'), b['id']: _content('B')}


# ---------------------------------------------------------------------------
# failures
# ---------------------------------------------------------------------------

def test_a_failing_commit_leaves_the_file_and_propagates(mem, caplog):
    caplog.set_level(logging.ERROR, logger=LOGGER)
    db = FakeContentDB()

    def broken(db_, params):
        raise APIError({'code': '57014', 'message': 'canceling statement due to statement timeout',
                        'details': None, 'hint': None})

    db.rpc_handlers['exercise_content_commit'] = broken
    with pytest.raises(APIError):
        store.write_sense(db, SENSE, 1, insert_rows=[_row()])
    assert mem.calls_for('put') == ['zh/5.v1.json'] and mem.exists('zh/5.v1.json')
    assert mem.calls_for('delete') == []
    assert any(r.getMessage().startswith('exercise_content.commit_failed') for r in caplog.records)


def test_already_exists_on_upload_is_a_storage_error(mem):
    db = FakeContentDB()
    mem.seed('zh/5.v1.json', b'someone else')
    with pytest.raises(ContentStorageError) as info:
        store.write_sense(db, SENSE, 1, insert_rows=[_row()])
    assert not isinstance(info.value, AlreadyExists)
    assert isinstance(info.value.__cause__, AlreadyExists)
    assert mem.objects()['zh/5.v1.json'] == b'someone else'
    assert mem.calls_for('delete') == [] and db.rpc_calls('exercise_content_commit') == []


def test_an_upload_failure_is_a_storage_error(mem):
    db = FakeContentDB()
    mem.fail_next('put', RuntimeError('connection reset'))
    with pytest.raises(ContentStorageError):
        store.write_sense(db, SENSE, 1, insert_rows=[_row()])
    assert db.rpc_calls('exercise_content_commit') == [] and db.rows() == []


@pytest.mark.parametrize('response', [
    {'ok': False, 'reason': 'something_else'},
    {'unexpected': True},
    ['not', 'an', 'object'],
])
def test_a_malformed_commit_response_raises(mem, response):
    db = FakeContentDB()
    db.rpc_handlers['exercise_content_commit'] = lambda db_, params: response
    with pytest.raises(ExerciseContentError):
        store.write_sense(db, SENSE, 1, insert_rows=[_row()])
    assert mem.calls_for('delete') == []


@pytest.mark.parametrize('response', [
    {'current_version': 0, 'new_version': None, 'rows': []},
    {'current_version': 3, 'new_version': 3, 'rows': []},
    {'current_version': 0, 'new_version': 1, 'rows': [{'language_id': 1}]},
    {'sense_id': 6, 'current_version': 0, 'new_version': 1, 'rows': []},
    'nope',
])
def test_a_malformed_begin_response_raises_before_upload(mem, response):
    db = FakeContentDB()
    db.rpc_handlers['exercise_content_begin'] = lambda db_, params: response
    with pytest.raises(ExerciseContentError):
        store.write_sense(db, SENSE, 1, insert_rows=[_row()])
    assert mem.calls_for('put') == []


def test_begin_wrapped_in_a_list_is_accepted(mem):
    db = FakeContentDB()
    original = db.rpc_handlers['exercise_content_begin']
    db.rpc_handlers['exercise_content_begin'] = lambda db_, params: [original(db_, params)]
    assert store.write_sense(db, SENSE, 1, insert_rows=[_row()]).version == 1


def test_rows_that_are_not_json_safe_are_rejected_before_any_call(mem):
    db = FakeContentDB()
    for bad in ({'generation_batch_id': uuid.uuid4()}, {'difficulty_static': float('nan')}):
        with pytest.raises(ValueError):
            store.write_sense(db, SENSE, 1, insert_rows=[_row(**bad)])
    with pytest.raises(ValueError):
        store.write_sense(db, SENSE, 1, insert_rows=[_row(content={'when': {1, 2}})])
    assert db.calls == [] and mem.calls == []


def test_rows_of_another_language_raise_value_error(mem):
    db = FakeContentDB()
    _seed_sense(db, mem, [_row(lang=3)], lang=3)
    with pytest.raises(ValueError):
        store.write_sense(db, SENSE, 1, insert_rows=[_row(level=2)])
    assert mem.calls_for('put') == []


def test_deleting_every_row_uploads_nothing(mem):
    db = FakeContentDB()
    rows = [_row(level=1), _row(level=2)]
    _seed_sense(db, mem, rows)
    mem.clear_calls()
    result = store.write_sense(db, SENSE, 1, delete_where=DeleteWhere())
    assert result.deleted_count == 2 and result.version == 1
    assert mem.calls == [] and db.rows(SENSE) == []


def test_a_delete_that_matches_nothing_commits_nothing(mem):
    db = FakeContentDB()
    _seed_sense(db, mem, [_row(level=1)], version=6)
    db.next_version = 9
    result = store.write_sense(db, SENSE, 1, delete_where=DeleteWhere(ladder_levels=(8,)))
    assert result == WriteResult(sense_id=SENSE, version=6, inserted_ids=[],
                                 deleted_count=0, updated_ids=[], attempts=1)
    assert db.rpc_calls('exercise_content_commit') == [] and mem.calls_for('put') == []


# ---------------------------------------------------------------------------
# read cache
# ---------------------------------------------------------------------------

def test_success_warms_the_read_cache(mem):
    db = FakeContentDB()
    row = _row()
    store.write_sense(db, SENSE, 1, insert_rows=[row])
    cached = store._content_cache().get(store._cache_key(1, SENSE, 1))
    assert cached == mem.objects()['zh/5.v1.json']

    mem.clear_calls()
    items = [{'id': row['id'], 'word_sense_id': SENSE, 'content_version': 1, 'language_id': 1}]
    store.hydrate(items)
    assert items[0]['content'] == row['content'] and mem.calls == []


def test_writes_work_without_the_cache_module(mem, monkeypatch):
    monkeypatch.setitem(sys.modules, 'services.exercise_content.cache', None)
    store.set_backend(mem)
    assert store._content_cache() is None
    db = FakeContentDB()
    assert store.write_sense(db, SENSE, 1, insert_rows=[_row()]).version == 1


# ---------------------------------------------------------------------------
# FakeContentDB itself (shared with TASK-1025)
# ---------------------------------------------------------------------------

def test_fake_begin_shape():
    db = FakeContentDB(next_version=41)
    rows = [_row(level=1), _row(level=2), _row(sense=6)]
    db.seed([{**rows[0], 'content_version': 3}, rows[1], rows[2]])
    data = db.rpc('exercise_content_begin', {'p_sense_id': SENSE}).execute().data
    assert data['sense_id'] == SENSE and data['current_version'] == 3
    assert data['new_version'] == 41
    assert [r['id'] for r in data['rows']] == sorted(r['id'] for r in rows[:2])
    assert set(data['rows'][0]) == {'id', 'language_id', 'exercise_type', 'ladder_level',
                                    'word_asset_id', 'is_active', 'content_version'}
    assert db.rpc('exercise_content_begin', {'p_sense_id': 99}).execute().data[
        'current_version'] == 0
    assert db.next_version == 43


def test_fake_commit_cas_and_errors_change_nothing():
    db = FakeContentDB()
    a = _row(level=1)
    db.seed([a])
    snapshot = db.rows()

    def commit(**overrides):
        params = {'p_sense_id': SENSE, 'p_expected_version': 0, 'p_expected_ids': [a['id']],
                  'p_new_version': 5}
        params.update(overrides)
        return db.rpc('exercise_content_commit', params).execute().data

    assert commit(p_expected_version=2) == {'ok': False, 'reason': 'version_conflict',
                                            'current_version': 0}
    assert commit(p_expected_ids=[]) == {'ok': False, 'reason': 'rows_changed',
                                         'current_version': 0}
    for bad in (dict(p_insert_rows=[_row(sense=6)]), dict(p_delete_ids=[_uuid()]),
                dict(p_update_contents={_uuid(): {}}), dict(p_new_version=0)):
        with pytest.raises(FakeDBError) as info:
            commit(**bad)
        assert info.value.code == '22023' and isinstance(info.value, ValueError)
    assert db.rows() == snapshot

    assert commit(p_insert_rows=[_row(level=2)], p_update_contents={a['id']: {'x': 1}}) == {
        'ok': True, 'version': 5, 'deleted': 0, 'inserted': 1, 'updated': 1}
    assert db.versions(SENSE) == [5]


def test_fake_dedupe_key_unique_index_and_dropped_column():
    assert sorted(CONTEXT_FREE_TYPES) == sorted([
        'tone_id_word', 'hanzi_to_pinyin', 'pinyin_to_hanzi', 'kanji_to_reading',
        'reading_to_kanji', 'phonetic_recognition', 'classifier_match', 'counter_match'])
    assert dedupe_key_for('cloze_completion', {'context_sentence': 'x'}) is None
    assert dedupe_key_for('tone_id_word', {}) == dedupe_key_for('tone_id_word',
                                                                 {'context_sentence': None})

    db = FakeContentDB()
    key = dedupe_key_for('tone_id_word', {'context_sentence': 'a'})
    first = _bare(_row(kind='tone_id_word'), dedupe_key=key)
    db.table('exercises').insert(first).execute()
    with pytest.raises(FakeDBError) as info:
        db.table('exercises').insert(_bare(_row(kind='tone_id_word'), dedupe_key=key)).execute()
    assert info.value.code == '23505'
    assert 'uq_exercises_context_free_variant_v2' in str(info.value)
    db.table('exercises').insert(_bare(_row(kind='tone_id_word'), dedupe_key=key,
                                       is_active=False)).execute()
    with pytest.raises(FakeDBError):
        db.table('exercises').insert({'id': first['id'], 'word_sense_id': 1}).execute()

    # seed: a content key only fills dedupe_key, as the cut-over backfill did live
    seeded = _row(kind='tone_id_word', content={'context_sentence': 'b'})
    db.seed([seeded])
    assert db.row(seeded['id'])['dedupe_key'] == dedupe_key_for('tone_id_word',
                                                                {'context_sentence': 'b'})

    # exercises.content is gone
    assert all('content' not in r for r in db.rows())
    with pytest.raises(FakeDBError) as info:
        db.table('exercises').select('id, content').execute()
    assert info.value.code == '42703'
    with pytest.raises(FakeDBError) as info:
        db.table('exercises').update({'content': {}}).eq('id', first['id']).execute()
    assert info.value.code == 'PGRST204'
    with pytest.raises(FakeDBError) as info:
        db.table('exercises').insert(_row()).execute()
    assert info.value.code == 'PGRST204'
    assert 'content' not in db.table('exercises').select('*').execute().data[0]


def test_fake_live_versions():
    db = FakeContentDB()
    db.seed([_row(sense=5), {**_row(sense=5), 'content_version': 3}, _row(sense=12),
             _row(sense=7, lang=3), {**_row(sense=None), 'word_sense_id': None}])
    data = db.rpc('exercise_content_live_versions', {'p_language_id': 1}).execute().data
    assert data == {'5': [0, 3], '12': [0]}


def test_fake_table_queries_and_pagination():
    db = FakeContentDB()
    rows = [_row(level=level % 5 + 1, asset=None if level % 3 == 0 else 7) for level in range(25)]
    db.seed(rows)
    query = db.table('exercises').select('id, ladder_level').eq('word_sense_id', SENSE) \
        .not_.is_('word_asset_id', 'null').in_('ladder_level', [1, 2]).order('ladder_level', desc=True)
    data = query.execute().data
    expected = [r for r in rows if r['word_asset_id'] is not None and r['ladder_level'] in (1, 2)]
    assert len(data) == len(expected) and all(set(d) == {'id', 'ladder_level'} for d in data)
    assert [d['ladder_level'] for d in data] == sorted((r['ladder_level'] for r in expected),
                                                       reverse=True)
    paged = fetch_all(lambda: db.table('exercises').select('id').order('id'), page_size=10)
    assert [p['id'] for p in paged] == sorted(r['id'] for r in rows)
    assert len(db.table('exercises').select('id').limit(3).execute().data) == 3
    updated = db.table('exercises').update({'is_active': False}).eq('ladder_level', 1).execute()
    assert updated.data and all(not r['is_active'] for r in updated.data)
    deleted = db.table('exercises').delete().eq('is_active', False).execute().data
    assert len(deleted) == len(updated.data) and len(db.rows()) == 25 - len(deleted)
    with pytest.raises(AssertionError):
        db.table('exercises').upsert([{}])


def test_fake_hooks_once_and_persistent():
    db = FakeContentDB()
    seen = []
    db.on('before:exercises.insert', lambda db_, q: seen.append(('once', q.op)))
    db.on('after:exercise_content_begin', lambda db_, payload: seen.append(
        ('after', payload[1]['new_version'])), once=False)
    db.table('exercises').insert(_bare(_row())).execute()
    db.table('exercises').insert(_bare(_row())).execute()
    db.rpc('exercise_content_begin', {'p_sense_id': 1}).execute()
    db.rpc('exercise_content_begin', {'p_sense_id': 1}).execute()
    assert seen == [('once', 'insert'), ('after', 1), ('after', 2)]


def test_fake_generic_tables_and_unknown_rpc():
    db = FakeContentDB()
    db.table('dim_word_senses').insert([{'id': 1, 'lemma': 'a'}, {'id': 2, 'lemma': 'b'}]).execute()
    assert db.table('dim_word_senses').select('lemma').eq('id', 2).execute().data == [{'lemma': 'b'}]
    db.rpc_handlers['echo'] = lambda db_, params: copy.deepcopy(params)
    assert db.rpc('echo', {'x': 1}).execute().data == {'x': 1}
    with pytest.raises(FakeDBError):
        db.rpc('missing_fn', {}).execute()
