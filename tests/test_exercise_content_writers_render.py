"""TASK-1012 — the render insert funnels go through ``store.write_sense`` (ADR-049 §4).

``LadderExerciseRenderer.render_all`` is the insert path of the admin
upload/render routes, word-list import, ``run_exercise_generation``,
``scripts/upload_exercises.py``, ``scripts/run_content_build.py`` and
``scripts/render_existing_assets.py`` (ADR-049 Appendix A row 14), and
``scripts/exercise_stage_runner.py cmd_render`` is the staged-CSV / fat-seed
render step (row 17). Both now make one ``store.write_sense`` call per sense.

Pinned here:

* ``render_all`` calls ``store.write_sense(self.db, sense_id, language_id,
  insert_rows=rows)`` once and returns the result's ``inserted_ids``; any
  write error (content conflict, storage error, PostgREST error) is logged
  and gives ``[]``, as an insert error did before.
* ``build_rows`` stays pure: no store call, no database write.
* In ``db`` write mode (the default the conftest pins) the database sees
  exactly today's single ``table('exercises').insert(rows).execute()``.
* ``cmd_render`` keeps its existing-rows refusal, makes no write in
  ``--dry-run``, and blocks a sense whose write fails, then carries on.

The store is monkeypatched (package a is not needed); the db-mode tests run
the real TASK-1008 facade against a recording fake. Fully offline.
"""

from __future__ import annotations

import argparse
import contextlib
import logging
import uuid

import pytest
from postgrest.exceptions import APIError

from services.exercise_content import store
from services.vocabulary_ladder import exercise_renderer as rendermod
from services.vocabulary_ladder import stage_runner as sr

LANG_ZH = 1


# ---------------------------------------------------------------------------
# Recording fake database (local to this file, per the package-b test rule)
# ---------------------------------------------------------------------------

class _Resp:
    def __init__(self, data=None, count=None):
        self.data = data
        self.count = count


class _Chain:
    """Records every builder step of one ``db.table(name)`` chain until ``execute()``."""

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
        return self._db.respond(self._table, self._steps)


class _RecordingDB:
    def __init__(self, existing_counts: dict | None = None, fail_insert_for: set | None = None):
        self.calls: list[tuple[str, list[tuple]]] = []
        self.existing_counts = existing_counts or {}
        self.fail_insert_for = fail_insert_for or set()

    def table(self, name):
        return _Chain(self, name)

    def respond(self, table, steps):
        ops = [s[0] for s in steps]
        if table == 'exercises' and 'select' in ops:
            sense = next(s[1][1] for s in steps if s[0] == 'eq' and s[1][0] == 'word_sense_id')
            return _Resp(data=[], count=self.existing_counts.get(sense, 0))
        if table == 'exercises' and 'insert' in ops:
            rows = next(s[1][0] for s in steps if s[0] == 'insert')
            if any(r.get('word_sense_id') in self.fail_insert_for for r in rows):
                raise APIError({'message': 'insert failed', 'code': '23505'})
            return _Resp(data=list(rows))
        return _Resp(data=[])

    def exercise_writes(self):
        return [(t, steps) for t, steps in self.calls
                if t == 'exercises' and any(s[0] in ('insert', 'upsert', 'update', 'delete')
                                            for s in steps)]


def _row(sense_id: int, level: int = 3, language_id: int = LANG_ZH) -> dict:
    return {
        'id': str(uuid.uuid4()), 'language_id': language_id,
        'exercise_type': 'cloze_completion', 'source_type': 'vocabulary',
        'content': {'sentence': f'level {level}'}, 'tags': {'variant': 'A'},
        'complexity_tier': 'T2', 'is_active': True, 'word_sense_id': sense_id,
        'word_asset_id': 99, 'ladder_level': level,
    }


class _WriteRecorder:
    """Stands in for ``store.write_sense``; optionally raises per sense."""

    def __init__(self, raises: dict | None = None, inserted_ids=None):
        self.calls: list[dict] = []
        self.raises = raises or {}
        self.inserted_ids = inserted_ids

    def __call__(self, db, sense_id, language_id, **kwargs):
        self.calls.append({'db': db, 'sense_id': sense_id, 'language_id': language_id,
                           **kwargs})
        exc = self.raises.get(sense_id)
        if exc is not None:
            raise exc
        rows = list(kwargs.get('insert_rows') or ())
        ids = self.inserted_ids if self.inserted_ids is not None else [r['id'] for r in rows]
        return store.WriteResult(sense_id=sense_id, mode='dual', version=4711,
                                 inserted_ids=list(ids), deleted_count=0, updated_ids=[],
                                 attempts=1)


# ---------------------------------------------------------------------------
# render_all
# ---------------------------------------------------------------------------

def _renderer(db, rows):
    r = rendermod.LadderExerciseRenderer(db=db)
    r.build_rows = lambda sense_id, language_id, levels=None: rows
    return r


def test_render_all_makes_one_write_sense_call_and_returns_its_ids(monkeypatch):
    rows = [_row(7, 1), _row(7, 3)]
    reported = [str(uuid.uuid4()), str(uuid.uuid4())]
    recorder = _WriteRecorder(inserted_ids=reported)
    monkeypatch.setattr(store, 'write_sense', recorder)
    db = _RecordingDB()

    ids = _renderer(db, rows).render_all(7, LANG_ZH)

    assert ids == reported, 'render_all returns the store result, not its own row ids'
    assert len(recorder.calls) == 1
    call = recorder.calls[0]
    assert call['db'] is db
    assert (call['sense_id'], call['language_id']) == (7, LANG_ZH)
    assert call['insert_rows'] is rows or call['insert_rows'] == rows
    assert set(call) == {'db', 'sense_id', 'language_id', 'insert_rows'}, (
        'render_all inserts only: no delete_where, no update_contents')
    assert db.calls == [], 'the renderer itself touches no table once the store owns the write'


@pytest.mark.parametrize('exc', [
    store.ContentWriteConflict('lost the race 3 times'),
    store.ContentStorageError('storage down'),
    store.AlreadyExists('zh/7.v4711.json'),
    APIError({'message': 'duplicate key', 'code': '23505'}),
    RuntimeError('network'),
], ids=['conflict', 'storage', 'already-exists', 'postgrest', 'other'])
def test_render_all_logs_a_write_error_and_returns_empty(monkeypatch, caplog, exc):
    monkeypatch.setattr(store, 'write_sense', _WriteRecorder(raises={7: exc}))

    with caplog.at_level(logging.ERROR, logger=rendermod.logger.name):
        ids = _renderer(_RecordingDB(), [_row(7)]).render_all(7, LANG_ZH)

    assert ids == []
    assert any('Failed to insert ladder exercises for sense 7' in r.getMessage()
               for r in caplog.records)


def test_render_all_with_no_rows_makes_no_write(monkeypatch):
    recorder = _WriteRecorder()
    monkeypatch.setattr(store, 'write_sense', recorder)

    assert _renderer(_RecordingDB(), []).render_all(7, LANG_ZH) == []
    assert recorder.calls == []


def test_render_all_db_mode_emits_exactly_todays_insert():
    """Real store, EXERCISE_CONTENT_WRITE=db (conftest): one insert(rows).execute(), nothing else."""
    assert store.write_mode() == 'db'
    rows = [_row(7, 1), _row(7, 3), _row(7, 5)]
    db = _RecordingDB()

    ids = _renderer(db, rows).render_all(7, LANG_ZH)

    assert ids == [r['id'] for r in rows]
    assert db.calls == [('exercises', [('insert', (rows,), {})])]


def test_render_all_db_mode_insert_error_still_returns_empty(caplog):
    db = _RecordingDB(fail_insert_for={7})

    with caplog.at_level(logging.ERROR, logger=rendermod.logger.name):
        assert _renderer(db, [_row(7)]).render_all(7, LANG_ZH) == []
    assert any('Failed to insert ladder exercises' in r.getMessage() for r in caplog.records)


# ---------------------------------------------------------------------------
# build_rows stays pure
# ---------------------------------------------------------------------------

ZH_CONCRETE_CORE = {
    'pos': '名词',
    'semantic_class': 'concrete',
    'definition': '书本；装订成册的印刷品',
    'primary_collocate': '',
    'pronunciation': 'shū',
    'morphological_forms': [],
    'sentences': [
        {'text': f'我买了一本书，编号{i}。', 'target_word': '书',
         'source': 'generated', 'complexity_tier': 'T2'}
        for i in range(10)
    ],
}

ZH_P3 = {
    'level_4': {
        'options': [{'text': '书们', 'is_correct': True},
                    {'text': '书子', 'is_correct': False},
                    {'text': '书儿', 'is_correct': False},
                    {'text': '书头', 'is_correct': False}],
        'correct_form': '书们', 'base_form': '书', 'form_label': '复数',
        'sentence_index': 1, 'explanations': {'书们': '复数形式'},
    },
    'level_7': {
        'incorrect_sentence': '我买了一本书们。',
        'corrected_sentence': '我买了一本书。',
        'error_description': '量词错误',
        'correct_sentence_indices': [0, 1, 2],
    },
}


def _asset_renderer(monkeypatch, db):
    r = rendermod.LadderExerciseRenderer(db=db)
    monkeypatch.setattr(r, '_load_assets', lambda sense_id: {
        'prompt1_core': ZH_CONCRETE_CORE,
        'prompt2_exercises_A': {},
        'prompt3_transforms_A': ZH_P3,
    })
    monkeypatch.setattr(r, '_load_asset_ids', lambda sense_id: {'prompt1_core': 'asset-1'})
    monkeypatch.setattr(r, '_render_hant_mirror', lambda content, language_id: None)
    return r


# reset_state is left alone: the conftest fixture calls it at teardown.
_STORE_API = ('write_sense', 'hydrate', 'fetch_sense', 'select_columns', 'rpc_content_args',
              'read_mode', 'write_mode', 'backend', 'set_backend')


def _record_store_calls(monkeypatch) -> list:
    seen: list = []
    for name in _STORE_API:
        def spy(*args, _name=name, **kwargs):
            seen.append(_name)
            raise AssertionError(f'build_rows called store.{_name}')
        monkeypatch.setattr(store, name, spy)
    return seen


def test_build_rows_makes_no_store_call_and_no_write(monkeypatch):
    seen = _record_store_calls(monkeypatch)
    db = _RecordingDB()
    r = _asset_renderer(monkeypatch, db)

    rows = r.build_rows(sense_id=10, language_id=LANG_ZH)

    assert rows, 'fixture must render rows for the purity check to mean anything'
    assert seen == []
    assert db.exercise_writes() == []


def test_render_all_end_to_end_db_mode_inserts_exactly_what_build_rows_built(monkeypatch):
    db = _RecordingDB()
    r = _asset_renderer(monkeypatch, db)
    built: list = []
    original = r.build_rows

    def spy(sense_id, language_id, levels=None):
        rows = original(sense_id, language_id, levels=levels)
        built.append(rows)
        return rows
    monkeypatch.setattr(r, 'build_rows', spy)

    ids = r.render_all(10, LANG_ZH)

    assert len(built) == 1 and built[0]
    assert ids == [row['id'] for row in built[0]]
    writes = db.exercise_writes()
    assert writes == [('exercises', [('insert', (built[0],), {})])]


# ---------------------------------------------------------------------------
# scripts/exercise_stage_runner.py cmd_render
# ---------------------------------------------------------------------------

@pytest.fixture
def stage_runner(monkeypatch):
    from scripts import exercise_stage_runner as esr

    state = {'db': _RecordingDB(), 'misses': {}, 'rows': {}, 'built': []}

    monkeypatch.setattr(esr, 'db_and_language',
                        lambda run_dir: (state['db'], LANG_ZH, {'language_id': LANG_ZH}))
    monkeypatch.setattr(esr, 'stored_render_answers', lambda run_dir: {})
    monkeypatch.setattr(esr, 'assembled_sense_ids', lambda run_dir: [1, 2, 3])
    monkeypatch.setattr(esr, 'seed_for_sense', lambda sid: None)

    active: dict = {}

    @contextlib.contextmanager
    def replay(answers):
        # The real context yields a list the judges append unanswered prompts to
        # while build_rows runs; the fake renderer below plays the judges.
        misses: list = []
        active['misses'] = misses
        try:
            yield misses
        finally:
            active.pop('misses', None)
    monkeypatch.setattr(sr, 'replay_llm_calls', replay)

    class _FakeRenderer:
        def __init__(self, db):
            self.db = db

        def build_rows(self, sense_id, language_id, levels=None):
            state['built'].append(sense_id)
            active['misses'].extend(state['misses'].get(sense_id, []))
            return state['rows'].get(sense_id, [])

    # cmd_render imports the class inside the function, from this module.
    monkeypatch.setattr(rendermod, 'LadderExerciseRenderer', _FakeRenderer)
    return esr, state


def _args(**kw):
    base = {'run_dir': '/nonexistent-run-dir', 'senses': None, 'dry_run': False}
    base.update(kw)
    return argparse.Namespace(**base)


def test_cmd_render_writes_each_sense_through_the_store(stage_runner, monkeypatch):
    esr, state = stage_runner
    state['rows'] = {1: [_row(1, 1), _row(1, 3)], 2: [_row(2, 1)], 3: [_row(3, 5)]}
    recorder = _WriteRecorder()
    monkeypatch.setattr(store, 'write_sense', recorder)

    rc = esr.cmd_render(_args())

    assert rc == 0
    assert [(c['sense_id'], c['language_id']) for c in recorder.calls] == [
        (1, LANG_ZH), (2, LANG_ZH), (3, LANG_ZH)]
    for call in recorder.calls:
        assert call['db'] is state['db']
        assert call['insert_rows'] == state['rows'][call['sense_id']]
        assert set(call) == {'db', 'sense_id', 'language_id', 'insert_rows'}
    assert state['db'].exercise_writes() == [], 'no direct insert any more'


def test_cmd_render_existing_rows_refusal_is_unchanged(stage_runner, monkeypatch, caplog):
    esr, state = stage_runner
    state['db'].existing_counts = {2: 13}
    state['rows'] = {1: [_row(1)], 2: [_row(2)], 3: [_row(3)]}
    recorder = _WriteRecorder()
    monkeypatch.setattr(store, 'write_sense', recorder)

    with caplog.at_level(logging.ERROR, logger=esr.logger.name):
        rc = esr.cmd_render(_args())

    assert rc == 1, 'a refused sense counts as blocked'
    assert [c['sense_id'] for c in recorder.calls] == [1, 3]
    assert 2 not in state['built'], 'a refused sense is not even rendered'
    assert any('already has 13 exercise row(s)' in r.getMessage() for r in caplog.records)
    selects = [steps for t, steps in state['db'].calls
               if t == 'exercises' and steps[0][0] == 'select']
    assert len(selects) == 3
    assert selects[0] == [('select', ('id',), {'count': 'exact'}),
                          ('eq', ('word_sense_id', 1), {}), ('limit', (1,), {})]


def test_cmd_render_dry_run_writes_nothing(stage_runner, monkeypatch):
    esr, state = stage_runner
    state['rows'] = {1: [_row(1)], 2: [_row(2)], 3: [_row(3)]}
    recorder = _WriteRecorder()
    monkeypatch.setattr(store, 'write_sense', recorder)

    rc = esr.cmd_render(_args(dry_run=True))

    assert rc == 0
    assert recorder.calls == []
    assert state['db'].exercise_writes() == []


def test_cmd_render_write_error_blocks_the_sense_and_continues(stage_runner, monkeypatch, caplog):
    esr, state = stage_runner
    state['rows'] = {1: [_row(1)], 2: [_row(2), _row(2, 4)], 3: [_row(3)]}
    recorder = _WriteRecorder(raises={2: store.ContentWriteConflict('lost 3 times')})
    monkeypatch.setattr(store, 'write_sense', recorder)

    with caplog.at_level(logging.INFO, logger=esr.logger.name):
        rc = esr.cmd_render(_args())

    assert rc == 1
    assert [c['sense_id'] for c in recorder.calls] == [1, 2, 3], 'the run goes on after a failure'
    messages = [r.getMessage() for r in caplog.records]
    assert any('sense 2: writing 2 row(s) failed' in m and 'lost 3 times' in m for m in messages)
    assert any('inserted 2 rows; 1 sense(s) blocked' in m for m in messages), (
        'the failed sense is not counted as inserted')


def test_cmd_render_unanswered_judge_blocks_without_a_write(stage_runner, monkeypatch):
    esr, state = stage_runner
    state['rows'] = {1: [_row(1)], 2: [_row(2)], 3: [_row(3)]}
    state['misses'] = {2: [{'key': 'k', 'task_name': 'judge'}]}
    recorder = _WriteRecorder()
    monkeypatch.setattr(store, 'write_sense', recorder)

    assert esr.cmd_render(_args()) == 1
    assert [c['sense_id'] for c in recorder.calls] == [1, 3]


def test_cmd_render_senses_flag_limits_the_run(stage_runner, monkeypatch):
    esr, state = stage_runner
    state['rows'] = {1: [_row(1)], 2: [_row(2)], 3: [_row(3)]}
    recorder = _WriteRecorder()
    monkeypatch.setattr(store, 'write_sense', recorder)

    assert esr.cmd_render(_args(senses='3')) == 0
    assert [c['sense_id'] for c in recorder.calls] == [3]


def test_cmd_render_db_mode_emits_todays_insert_chain(stage_runner):
    """Real store in db write mode: per sense, the refusal select then insert(rows).execute()."""
    esr, state = stage_runner
    state['rows'] = {1: [_row(1), _row(1, 4)], 2: [], 3: [_row(3)]}

    assert esr.cmd_render(_args()) == 0

    assert state['db'].calls == [
        ('exercises', [('select', ('id',), {'count': 'exact'}),
                       ('eq', ('word_sense_id', 1), {}), ('limit', (1,), {})]),
        ('exercises', [('insert', (state['rows'][1],), {})]),
        ('exercises', [('select', ('id',), {'count': 'exact'}),
                       ('eq', ('word_sense_id', 2), {}), ('limit', (1,), {})]),
        ('exercises', [('select', ('id',), {'count': 'exact'}),
                       ('eq', ('word_sense_id', 3), {}), ('limit', (1,), {})]),
        ('exercises', [('insert', (state['rows'][3],), {})]),
    ]


def test_cmd_render_db_mode_insert_error_blocks_and_continues(stage_runner):
    esr, state = stage_runner
    state['db'].fail_insert_for = {1}
    state['rows'] = {1: [_row(1)], 2: [_row(2)], 3: []}

    assert esr.cmd_render(_args()) == 1
    inserts = [steps for t, steps in state['db'].calls if steps[0][0] == 'insert']
    assert len(inserts) == 2, 'sense 1 failed, sense 2 still inserted'
    assert inserts[1] == [('insert', (state['rows'][2],), {})]
