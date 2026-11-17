"""TASK-1013 — the regeneration writers replace a sense's rows through ``store.write_sense``.

``queue_drain._regenerate`` (ADR-049 Appendix A row 15) and
``scripts/run_generation_batch.py`` (row 16) used to delete a sense's
asset-linked ladder rows (optionally only some levels) and insert the new
set with two direct PostgREST calls. Both are now one ``store.write_sense``
call with a ``store.DeleteWhere``, so in ``dual`` write mode a regen produces
one new content version for the sense.

Pinned here:

* the exact ``write_sense`` arguments (``DeleteWhere(require_word_asset=True,
  ladder_levels=<sorted tuple> | None)``);
* queue drain: ``detail['rendered']`` on success; a content conflict or
  storage error gives ``detail['error'] = 'content_write_conflict' |
  'content_storage_error'`` and ``(False, detail)``; the coverage re-check
  runs only after a successful write;
* generation batch: a write error fails the sense with the error in the log
  and is queued for regen exactly as an insert error was;
* ``db`` write mode (the conftest default) still emits today's chains, delete
  before insert.

The store is monkeypatched where the call shape is asserted; the db-mode tests
run the real TASK-1008 facade against a recording fake. Fully offline.
"""

from __future__ import annotations

import logging

import pytest
from postgrest.exceptions import APIError

import services.vocabulary_ladder.queue_drain as qd
from scripts import run_generation_batch as batch
from services.exercise_content import store

LANG_EN = 2


# ---------------------------------------------------------------------------
# Local fakes
# ---------------------------------------------------------------------------

class _Resp:
    def __init__(self, data=None):
        self.data = data


class _Chain:
    def __init__(self, db, table):
        self._db = db
        self._table = table
        self._steps: list[tuple] = []

    def __getattr__(self, name):
        if name.startswith('__'):
            raise AttributeError(name)
        if name == 'not_':
            self._steps.append(('not_',))
            return self

        def step(*args, **kwargs):
            self._steps.append((name, args, kwargs))
            return self
        return step

    def execute(self):
        self._db.calls.append((self._table, list(self._steps)))
        ops = [s[0] for s in self._steps]
        if 'insert' in ops:
            return _Resp(data=list(self._steps[ops.index('insert')][1][0]))
        if 'delete' in ops:
            return _Resp(data=[{'id': 'old-1'}, {'id': 'old-2'}])
        return _Resp(data=[])


class _RecordingDB:
    def __init__(self):
        self.calls: list[tuple[str, list[tuple]]] = []

    def table(self, name):
        return _Chain(self, name)


class _WriteRecorder:
    def __init__(self, events: list | None = None, raises: Exception | None = None,
                 raises_for: dict | None = None):
        self.calls: list[dict] = []
        self.events = events if events is not None else []
        self.raises = raises
        self.raises_for = raises_for or {}

    def __call__(self, db, sense_id, language_id, **kwargs):
        self.calls.append({'db': db, 'sense_id': sense_id, 'language_id': language_id,
                           **kwargs})
        self.events.append(('write', sense_id))
        exc = self.raises_for.get(sense_id, self.raises)
        if exc is not None:
            raise exc
        rows = list(kwargs.get('insert_rows') or ())
        return store.WriteResult(sense_id=sense_id, mode='dual', version=77,
                                 inserted_ids=[r.get('id') for r in rows], deleted_count=3,
                                 updated_ids=[], attempts=1)


# ---------------------------------------------------------------------------
# queue_drain._regenerate
# ---------------------------------------------------------------------------

class _FakePipeline:
    result = {'status': 'success', 'errors': []}

    def __init__(self, db):
        self.db = db

    def generate_for_sense(self, sense_id, language_id, force=True, levels=None):
        return dict(type(self).result)


def _rows_for(sense_id, levels):
    return [{'id': f'00000000-0000-4000-8000-00000000000{lv}', 'ladder_level': lv,
             'word_sense_id': sense_id, 'language_id': LANG_EN,
             'content': {'level': lv}, 'word_asset_id': 5}
            for lv in sorted(levels)]


@pytest.fixture
def drain(monkeypatch):
    """Wire _regenerate's late imports to fakes; record the coverage re-check."""
    import services.vocabulary_ladder.asset_pipeline as pipeline_mod
    import services.vocabulary_ladder.config as config_mod
    import services.vocabulary_ladder.exercise_renderer as renderer_mod

    state = {'events': [], 'scoped': {9, 2, 4}, 'rows_levels': {1, 3, 5},
             'remaining': [], 'built': []}
    _FakePipeline.result = {'status': 'success', 'errors': []}

    class _FakeRenderer:
        def __init__(self, db):
            self.last_skips = []

        def build_rows(self, sense_id, language_id, levels=None):
            rows = _rows_for(sense_id, levels if levels is not None else state['rows_levels'])
            state['built'] = rows
            return rows

    def coverage_gaps(db, sense_ids=None, language_id=None):
        state['events'].append(('coverage', tuple(sense_ids or ())))
        return state['remaining']

    monkeypatch.setattr(pipeline_mod, 'VocabAssetPipeline', _FakePipeline)
    monkeypatch.setattr(renderer_mod, 'LadderExerciseRenderer', _FakeRenderer)
    monkeypatch.setattr(config_mod, 'families_to_levels',
                        lambda families, semantic_class, language_id: set(state['scoped']))
    monkeypatch.setattr(qd, '_semantic_class_for_sense', lambda db, sense_id: 'action')
    monkeypatch.setattr(qd, 'coverage_gaps', coverage_gaps)
    return state


def _gap_row(sense_id=42):
    return {'sense_id': sense_id, 'language_id': LANG_EN, 'reason': qd.REASON_COVERAGE_GAP,
            'detail': {'missing_families': ['form_production']}}


def _regen_row(sense_id=43):
    return {'sense_id': sense_id, 'language_id': LANG_EN, 'reason': qd.REASON_REGEN,
            'detail': {}}


def test_scoped_regen_is_one_write_sense_call_with_sorted_levels(drain, monkeypatch):
    recorder = _WriteRecorder(drain['events'])
    monkeypatch.setattr(store, 'write_sense', recorder)
    db = object()

    ok, detail = qd._regenerate(db, _gap_row())

    assert ok is True
    assert len(recorder.calls) == 1
    call = recorder.calls[0]
    assert call['db'] is db
    assert (call['sense_id'], call['language_id']) == (42, LANG_EN)
    assert call['insert_rows'] == drain['built']
    assert call['delete_where'] == store.DeleteWhere(require_word_asset=True,
                                                     ladder_levels=(2, 4, 9))
    assert call['delete_where'].ladder_levels == (2, 4, 9)
    assert set(call) == {'db', 'sense_id', 'language_id', 'insert_rows', 'delete_where'}
    assert detail['rendered'] == 3
    assert detail['scoped_levels'] == [2, 4, 9]
    assert drain['events'] == [('write', 42), ('coverage', (42,))], (
        'the coverage re-check runs after the write')


def test_unscoped_regen_deletes_every_asset_linked_level(drain, monkeypatch):
    recorder = _WriteRecorder(drain['events'])
    monkeypatch.setattr(store, 'write_sense', recorder)

    ok, detail = qd._regenerate(object(), _regen_row())

    assert ok is True
    assert recorder.calls[0]['delete_where'] == store.DeleteWhere(require_word_asset=True)
    assert recorder.calls[0]['delete_where'].ladder_levels is None
    assert detail['rendered'] == 3
    assert 'scoped_levels' not in detail


@pytest.mark.parametrize('exc, code', [
    (store.ContentWriteConflict('lost the race 3 times'), 'content_write_conflict'),
    (store.ContentStorageError('upload failed: 503'), 'content_storage_error'),
    (store.AlreadyExists('en/43.v77.json'), 'content_storage_error'),
], ids=['conflict', 'storage', 'already-exists'])
def test_content_write_errors_fail_the_regen_without_a_coverage_check(
        drain, monkeypatch, caplog, exc, code):
    monkeypatch.setattr(store, 'write_sense', _WriteRecorder(drain['events'], raises=exc))

    with caplog.at_level(logging.ERROR, logger=qd.logger.name):
        ok, detail = qd._regenerate(object(), _regen_row())

    assert ok is False
    assert detail['error'] == code
    assert str(exc) in detail['error_detail']
    assert 'rendered' not in detail
    assert drain['events'] == [('write', 43)], 'no coverage re-check after a failed write'
    assert any(code in r.getMessage() and 'sense 43' in r.getMessage() for r in caplog.records)


def test_postgrest_error_keeps_todays_generic_failure(drain, monkeypatch):
    exc = APIError({'message': 'violates unique constraint', 'code': '23505'})
    monkeypatch.setattr(store, 'write_sense', _WriteRecorder(drain['events'], raises=exc))

    ok, detail = qd._regenerate(object(), _regen_row())

    assert ok is False
    assert detail['error'] == str(exc)[:500]
    assert 'rendered' not in detail
    assert drain['events'] == [('write', 43)]


def test_no_rows_or_failed_pipeline_makes_no_write(drain, monkeypatch):
    recorder = _WriteRecorder(drain['events'])
    monkeypatch.setattr(store, 'write_sense', recorder)

    drain['rows_levels'] = set()
    ok, detail = qd._regenerate(object(), _regen_row())
    assert (ok, detail['error']) == (False, 'render produced no rows')

    drain['rows_levels'] = {1}
    _FakePipeline.result = {'status': 'failed', 'errors': ['boom']}
    ok, detail = qd._regenerate(object(), _regen_row())
    assert ok is False

    assert recorder.calls == []


def test_gap_still_open_after_a_successful_write(drain, monkeypatch):
    monkeypatch.setattr(store, 'write_sense', _WriteRecorder(drain['events']))
    drain['remaining'] = [{'sense_id': 42, 'missing_families': ['form_production']}]

    ok, detail = qd._regenerate(object(), _gap_row())

    assert ok is False
    assert detail['rendered'] == 3
    assert detail['still_missing'] == ['form_production']


def test_db_mode_scoped_regen_emits_todays_delete_then_insert(drain):
    assert store.write_mode() == 'db'
    db = _RecordingDB()

    ok, detail = qd._regenerate(db, _gap_row())

    assert ok is True
    assert db.calls == [
        ('exercises', [('delete', (), {}), ('eq', ('word_sense_id', 42), {}), ('not_',),
                       ('is_', ('word_asset_id', 'null'), {}),
                       ('in_', ('ladder_level', [2, 4, 9]), {})]),
        ('exercises', [('insert', (drain['built'],), {})]),
    ]


def test_db_mode_unscoped_regen_emits_todays_delete_then_insert(drain):
    db = _RecordingDB()

    ok, _ = qd._regenerate(db, _regen_row())

    assert ok is True
    assert db.calls == [
        ('exercises', [('delete', (), {}), ('eq', ('word_sense_id', 43), {}), ('not_',),
                       ('is_', ('word_asset_id', 'null'), {})]),
        ('exercises', [('insert', (drain['built'],), {})]),
    ]


# ---------------------------------------------------------------------------
# scripts/run_generation_batch.py
# ---------------------------------------------------------------------------

class _BatchPipeline:
    def __init__(self, status='success'):
        self.status = status

    def generate_for_sense(self, sense_id, language_id):
        return {'status': self.status, 'errors': []}


class _BatchRenderer:
    def __init__(self, _db=None):
        self.last_skips = []

    def build_rows(self, sense_id, language_id):
        return [{'id': f'00000000-0000-4000-8000-0000000000{sense_id:02d}',
                 'word_sense_id': sense_id, 'language_id': language_id,
                 'content': {'n': 1}, 'word_asset_id': 9, 'ladder_level': 1},
                {'id': f'00000000-0000-4000-9000-0000000000{sense_id:02d}',
                 'word_sense_id': sense_id, 'language_id': language_id,
                 'content': {'n': 2}, 'word_asset_id': 9, 'ladder_level': 3}]


@pytest.fixture
def enqueued(monkeypatch):
    calls: list = []

    def enqueue(db, sense_id, language_id, reason, detail=None):
        calls.append((sense_id, language_id, reason, detail))
        return True
    monkeypatch.setattr(qd, 'enqueue', enqueue)
    return calls


def _sense(sense_id=7):
    return {'sense_id': sense_id, 'lemma': f'word{sense_id}'}


def test_batch_replaces_rows_with_one_write_sense_call(monkeypatch, enqueued):
    recorder = _WriteRecorder()
    monkeypatch.setattr(store, 'write_sense', recorder)
    db = object()

    outcome = batch._process_sense(db, 1, _sense(7), _BatchPipeline(), _BatchRenderer())

    assert outcome.status == 'success'
    assert outcome.exercises == 2
    assert len(recorder.calls) == 1
    call = recorder.calls[0]
    assert call['db'] is db
    assert (call['sense_id'], call['language_id']) == (7, 1)
    assert [r['ladder_level'] for r in call['insert_rows']] == [1, 3]
    assert call['delete_where'] == store.DeleteWhere(require_word_asset=True)
    assert set(call) == {'db', 'sense_id', 'language_id', 'insert_rows', 'delete_where'}
    assert enqueued == []


def test_batch_partial_status_still_writes(monkeypatch, enqueued):
    recorder = _WriteRecorder()
    monkeypatch.setattr(store, 'write_sense', recorder)

    outcome = batch._process_sense(object(), 1, _sense(7), _BatchPipeline('partial'),
                                   _BatchRenderer())

    assert (outcome.status, outcome.exercises) == ('partial', 2)
    assert len(recorder.calls) == 1


@pytest.mark.parametrize('exc', [
    store.ContentWriteConflict('lost the race 3 times'),
    store.ContentStorageError('storage down'),
    APIError({'message': 'insert failed', 'code': '23505'}),
], ids=['conflict', 'storage', 'postgrest'])
def test_batch_write_error_fails_the_sense_logs_and_queues(monkeypatch, caplog, enqueued, exc):
    monkeypatch.setattr(store, 'write_sense', _WriteRecorder(raises=exc))

    with caplog.at_level(logging.ERROR, logger=batch.logger.name):
        outcome = batch._process_sense(object(), 1, _sense(7), _BatchPipeline(),
                                       _BatchRenderer())

    assert outcome.status == 'failed'
    assert outcome.exercises == 0
    assert outcome.fatal is None, 'a write error is this sense\'s failure, not a chunk abort'
    assert any('sense 7 (word7) failed' in r.getMessage() and str(exc) in r.getMessage()
               for r in caplog.records)
    assert len(enqueued) == 1, 'queued for regen exactly as an insert error was'
    sense_id, language_id, reason, detail = enqueued[0]
    assert (sense_id, language_id, reason) == (7, 1, qd.REASON_REGEN)
    assert detail == {'error': str(exc)[:500], 'lemma': 'word7'}
    assert outcome.queued is True


def test_batch_no_rows_makes_no_write(monkeypatch, enqueued):
    recorder = _WriteRecorder()
    monkeypatch.setattr(store, 'write_sense', recorder)

    class _Empty(_BatchRenderer):
        def build_rows(self, sense_id, language_id):
            return []

    outcome = batch._process_sense(object(), 1, _sense(7), _BatchPipeline(), _Empty())

    assert outcome.status == 'failed'
    assert recorder.calls == []
    assert enqueued[0][3]['error'] == 'render produced no rows'


def test_batch_db_mode_emits_todays_delete_then_insert(enqueued):
    assert store.write_mode() == 'db'
    db = _RecordingDB()
    renderer = _BatchRenderer()

    outcome = batch._process_sense(db, 1, _sense(7), _BatchPipeline(), renderer)

    assert outcome.status == 'success'
    rows = renderer.build_rows(7, 1)
    assert db.calls == [
        ('exercises', [('delete', (), {}), ('eq', ('word_sense_id', 7), {}), ('not_',),
                       ('is_', ('word_asset_id', 'null'), {})]),
        ('exercises', [('insert', (rows,), {})]),
    ]


def test_run_chunk_counts_a_write_failure_once(monkeypatch, enqueued):
    """End to end over the worker pool: one sense's write fails, the rest succeed."""
    import services.vocabulary_ladder.asset_pipeline as ap
    import services.vocabulary_ladder.exercise_renderer as er

    monkeypatch.setattr(ap, 'VocabAssetPipeline', lambda db: _BatchPipeline())
    monkeypatch.setattr(er, 'LadderExerciseRenderer', _BatchRenderer)
    monkeypatch.setattr(batch, 'spend_since', lambda *a, **k: 0.0)
    monkeypatch.setattr(batch, '_judge_verdicts_since', lambda *a, **k: {})
    recorder = _WriteRecorder(raises_for={3: store.ContentWriteConflict('busy sense')})
    monkeypatch.setattr(store, 'write_sense', recorder)
    senses = [_sense(i) for i in range(1, 6)]

    report = batch.run_chunk(object(), 1, senses, None, False, workers=2)

    assert (report.succeeded, report.failed, report.exercises_created, report.queued) == (
        4, 1, 8, 1)
    assert sorted(c['sense_id'] for c in recorder.calls) == [1, 2, 3, 4, 5]
