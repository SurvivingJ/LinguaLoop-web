"""TASK-982 — the content fix scripts read and write through the content store.

``scripts/backfill_exercise_audio.py`` (ADR-047 Appendix A row 18) and
``scripts/backfill_hant_mirrors.py`` (row 19) read exercise content and rewrite
it. They now:

* select ``store.select_columns('id, exercise_type, word_sense_id, language_id,
  {content}')`` (paged as before) and fill content with ``store.hydrate(rows,
  db=db)``, at most 100 senses per call;
* write once per sense with ``store.write_sense(db, sense_id, language_id,
  update_contents={id: new_content})``; a failed write counts every row it
  carried as failed and the run continues;
* make no write call in ``--dry-run`` (both) or ``report_coverage`` (audio);
* skip rows with no ``word_sense_id`` and count them as ``skipped_no_sense``.

The store is monkeypatched with fakes that behave like ``storage`` mode (the
select has no content; ``hydrate`` fills it from "files" and drops what is
missing). The db-mode tests run the real TASK-976 facade and pin today's
PostgREST calls. Fully offline: no Supabase, no TTS, no OpenCC overrides table.
"""

from __future__ import annotations

import copy
import logging

import pytest

from scripts import backfill_exercise_audio as audio
from scripts import backfill_hant_mirrors as hant
from services.exercise_content import store

ZH = 1
TEMPLATE = 'id, exercise_type, word_sense_id, language_id, {content}'


# ---------------------------------------------------------------------------
# Local fakes
# ---------------------------------------------------------------------------

class _Resp:
    def __init__(self, data):
        self.data = data


class _Query:
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
        if 'select' in ops:
            if self._db.read_error is not None:
                raise self._db.read_error
            rows = list(self._db.tables.get(self._table, []))
            for step in self._steps:
                if step[0] == 'eq':
                    rows = [r for r in rows if r.get(step[1][0]) == step[1][1]]
                elif step[0] == 'in_':
                    rows = [r for r in rows if r.get(step[1][0]) in step[1][1]]
            for step in self._steps:
                if step[0] == 'range':
                    rows = rows[step[1][0]:step[1][1] + 1]
            return _Resp(copy.deepcopy(rows))
        return _Resp([])


class _FakeDB:
    def __init__(self, exercises: list[dict]):
        self.tables = {'exercises': exercises}
        self.calls: list[tuple[str, list[tuple]]] = []
        self.read_error: Exception | None = None

    def table(self, name):
        return _Query(self, name)

    def writes(self):
        return [(t, steps) for t, steps in self.calls
                if any(s[0] in ('insert', 'upsert', 'update', 'delete') for s in steps)]

    def selects(self):
        return [steps for t, steps in self.calls if steps and steps[0][0] == 'select']


class _FakeStore:
    """storage-mode stand-ins for select_columns / hydrate / write_sense."""

    def __init__(self, files: dict[str, dict], raise_for: dict | None = None):
        self.files = files
        self.raise_for = raise_for or {}
        self.templates: list[str] = []
        self.hydrate_calls: list[dict] = []
        self.writes: list[dict] = []

    def select_columns(self, template):
        self.templates.append(template)
        return template.replace('{content}', 'content_version')

    def hydrate(self, items, **kwargs):
        self.hydrate_calls.append({
            'senses': sorted({i['word_sense_id'] for i in items}),
            'ids': [i['id'] for i in items], **kwargs})
        kept = []
        for item in items:
            if item.get('content') is None and item['id'] in self.files:
                item['content'] = copy.deepcopy(self.files[item['id']])
            if item.get('content') is not None:
                kept.append(item)
        items[:] = kept
        return store.HydrationReport(mode='storage', items=len(kept))

    def write_sense(self, db, sense_id, language_id, **kwargs):
        self.writes.append({'db': db, 'sense_id': sense_id, 'language_id': language_id,
                            **kwargs})
        exc = self.raise_for.get(sense_id)
        if exc is not None:
            raise exc
        updates = kwargs.get('update_contents') or {}
        return store.WriteResult(sense_id=sense_id, mode='dual', version=9, inserted_ids=[],
                                 deleted_count=0, updated_ids=list(updates), attempts=1)

    def install(self, monkeypatch):
        monkeypatch.setattr(store, 'select_columns', self.select_columns)
        monkeypatch.setattr(store, 'hydrate', self.hydrate)
        monkeypatch.setattr(store, 'write_sense', self.write_sense)
        return self


# ---------------------------------------------------------------------------
# backfill_hant_mirrors.backfill_exercises
# ---------------------------------------------------------------------------

class _FakeConverter:
    def __init__(self, fail_for: set | None = None):
        self.fail_for = fail_for or set()

    def convert_content(self, base):
        if base.get('s') in self.fail_for:
            raise RuntimeError('opencc exploded')
        return {k: f'T({v})' if isinstance(v, str) else v for k, v in base.items()}


def _zh_row(row_id, sense_id, **extra):
    return {'id': row_id, 'exercise_type': 'cloze_completion', 'word_sense_id': sense_id,
            'language_id': ZH, **extra}


def _hant_fixture():
    """Rows in id order with the senses interleaved, plus one sense-less row."""
    rows = [_zh_row('a1', 1), _zh_row('b1', 2), _zh_row('a2', 1), _zh_row('x0', None),
            _zh_row('a3', 1), _zh_row('b2', 2)]
    files = {
        'a1': {'s': '书'}, 'a2': {'s': '本'},
        'a3': {'s': '书本', 'hant': {'s': 'T(书本)'}},      # already mirrored
        'b1': {'s': '学'}, 'b2': {'s': '习', 'hant': {'s': 'stale'}},
        'x0': {'s': '搭配'},
    }
    return rows, files


def test_hant_reads_through_select_columns_and_writes_once_per_sense(monkeypatch):
    rows, files = _hant_fixture()
    fake = _FakeStore(files).install(monkeypatch)
    db = _FakeDB(rows)

    stats = hant.backfill_exercises(db, _FakeConverter(), dry_run=False, limit=0, force=False)

    assert fake.templates == [TEMPLATE]
    assert db.selects() == [[
        ('select', ('id, exercise_type, word_sense_id, language_id, content_version',), {}),
        ('eq', ('language_id', ZH), {}), ('order', ('id',), {}), ('range', (0, 999), {})]]
    assert [(w['sense_id'], w['language_id']) for w in fake.writes] == [(1, ZH), (2, ZH)]
    for write in fake.writes:
        assert write['db'] is db
        assert set(write) == {'db', 'sense_id', 'language_id', 'update_contents'}
    assert fake.writes[0]['update_contents'] == {
        'a1': {'s': '书', 'hant': {'s': 'T(书)'}},
        'a2': {'s': '本', 'hant': {'s': 'T(本)'}},
    }
    assert fake.writes[1]['update_contents'] == {
        'b1': {'s': '学', 'hant': {'s': 'T(学)'}},
        'b2': {'s': '习', 'hant': {'s': 'T(习)'}},
    }
    assert stats == {'updated': 4, 'skipped': 1, 'failed': 0, 'skipped_no_sense': 1,
                     'unavailable': 0}
    assert db.writes() == [], 'no direct exercises write'


def test_hant_skips_sense_less_rows_before_the_store(monkeypatch):
    rows, files = _hant_fixture()
    fake = _FakeStore(files).install(monkeypatch)

    stats = hant.backfill_exercises(_FakeDB(rows), _FakeConverter(), False, 0, False)

    assert stats['skipped_no_sense'] == 1
    assert all('x0' not in call['ids'] for call in fake.hydrate_calls)
    assert all('x0' not in (w['update_contents'] or {}) for w in fake.writes)


def test_hant_hydrates_at_most_100_senses_per_call(monkeypatch):
    rows = [_zh_row(f'r{i:03d}', 1000 + i) for i in range(250)]
    files = {r['id']: {'s': f'字{i}'} for i, r in enumerate(rows)}
    fake = _FakeStore(files).install(monkeypatch)
    db = _FakeDB(rows)

    stats = hant.backfill_exercises(db, _FakeConverter(), False, 0, False)

    assert [len(c['senses']) for c in fake.hydrate_calls] == [100, 100, 50]
    assert all(c['db'] is db for c in fake.hydrate_calls)
    assert all(set(c) == {'senses', 'ids', 'db'} for c in fake.hydrate_calls), (
        'store.hydrate(rows, db=db): language comes from each row')
    assert len(fake.writes) == 250
    assert stats['updated'] == 250


def test_hant_pages_as_before(monkeypatch):
    rows, files = _hant_fixture()
    _FakeStore(files).install(monkeypatch)
    monkeypatch.setattr(hant, 'PAGE_SIZE', 4)
    db = _FakeDB(rows)

    hant.backfill_exercises(db, _FakeConverter(), False, 0, False)

    assert [steps[-1] for steps in db.selects()] == [('range', (0, 3), {}),
                                                    ('range', (4, 7), {})]


def test_hant_dry_run_makes_no_write_call(monkeypatch):
    rows, files = _hant_fixture()
    fake = _FakeStore(files).install(monkeypatch)
    db = _FakeDB(rows)

    stats = hant.backfill_exercises(db, _FakeConverter(), dry_run=True, limit=0, force=False)

    assert fake.writes == []
    assert db.writes() == []
    assert stats['updated'] == 4, 'dry run still counts what it would update'


def test_hant_write_error_fails_that_senses_rows_and_continues(monkeypatch, caplog):
    rows, files = _hant_fixture()
    fake = _FakeStore(files, raise_for={1: store.ContentWriteConflict('lost 3 times')})
    fake.install(monkeypatch)

    with caplog.at_level(logging.WARNING, logger=hant.logger.name):
        stats = hant.backfill_exercises(_FakeDB(rows), _FakeConverter(), False, 0, False)

    assert [w['sense_id'] for w in fake.writes] == [1, 2], 'the run goes on'
    assert stats['failed'] == 2, 'both rows the sense-1 write carried'
    assert stats['updated'] == 2
    assert any('content write failed for sense 1' in r.getMessage() for r in caplog.records)


def test_hant_convert_failure_and_unavailable_content(monkeypatch):
    rows, files = _hant_fixture()
    del files['b1']                       # no file, no DB fallback: dropped by hydrate
    fake = _FakeStore(files).install(monkeypatch)

    stats = hant.backfill_exercises(_FakeDB(rows), _FakeConverter(fail_for={'书'}),
                                    False, 0, False)

    assert stats['unavailable'] == 1
    assert stats['failed'] == 1
    assert fake.writes[0]['update_contents'] == {'a2': {'s': '本', 'hant': {'s': 'T(本)'}}}
    assert list(fake.writes[1]['update_contents']) == ['b2']


def test_hant_force_and_limit(monkeypatch):
    rows, files = _hant_fixture()
    fake = _FakeStore(files).install(monkeypatch)

    stats = hant.backfill_exercises(_FakeDB(rows), _FakeConverter(), False, 3, True)

    assert stats['updated'] == 3, '--limit 3 keeps a1, b1, a2; --force rewrites all'
    assert [sorted(w['update_contents']) for w in fake.writes] == [['a1', 'a2'], ['b1']]


def test_hant_db_mode_reads_and_writes_todays_calls():
    """Real store, both flags db: today's select string with content, per-row update chains."""
    assert (store.read_mode(), store.write_mode()) == ('db', 'db')
    rows, files = _hant_fixture()
    for row in rows:
        row['content'] = copy.deepcopy(files[row['id']])
    db = _FakeDB(rows)

    stats = hant.backfill_exercises(db, _FakeConverter(), False, 0, False)

    assert db.selects()[0][0] == (
        'select', ('id, exercise_type, word_sense_id, language_id, content',), {})
    assert db.writes() == [
        ('exercises', [('update', ({'content': {'s': '书', 'hant': {'s': 'T(书)'}}},), {}),
                       ('eq', ('id', 'a1'), {})]),
        ('exercises', [('update', ({'content': {'s': '本', 'hant': {'s': 'T(本)'}}},), {}),
                       ('eq', ('id', 'a2'), {})]),
        ('exercises', [('update', ({'content': {'s': '学', 'hant': {'s': 'T(学)'}}},), {}),
                       ('eq', ('id', 'b1'), {})]),
        ('exercises', [('update', ({'content': {'s': '习', 'hant': {'s': 'T(习)'}}},), {}),
                       ('eq', ('id', 'b2'), {})]),
    ]
    assert stats['updated'] == 4 and stats['skipped_no_sense'] == 1


# ---------------------------------------------------------------------------
# backfill_exercise_audio.AudioBackfillRun
# ---------------------------------------------------------------------------

class _FakeSynth:
    def __init__(self, fail_for: set | None = None):
        self.calls: list[dict] = []
        self.fail_for = fail_for or set()

    def generate_and_upload(self, text, file_id, voice, speed):
        self.calls.append({'text': text, 'file_id': file_id})
        if text in self.fail_for:
            raise RuntimeError('azure 429')
        return f'https://r2.example/{file_id}/{text}.mp3'


def _audio_row(row_id, sense_id, exercise_type='phonetic_recognition', language_id=3,
               active=True):
    return {'id': row_id, 'exercise_type': exercise_type, 'word_sense_id': sense_id,
            'language_id': language_id, 'is_active': active}


def _audio_fixture():
    rows = [
        _audio_row('p10a', 10), _audio_row('p11', 11), _audio_row('f10', 10, 'listening_flashcard'),
        _audio_row('nos', None), _audio_row('p10b', 10), _audio_row('p12', 12),
        _audio_row('off', 12, active=False),
    ]
    files = {
        'p10a': {'word': 'ねこ'}, 'p10b': {'correct_answer': 'ネコ'},
        'f10': {'word_of_interest': 'ねこ', 'back_sentence': 'ねこがいる'},
        'p11': {'word': 'いぬ', 'audio_url': 'https://r2.example/existing.mp3'},
        'p12': {'word': 'とり'},
        'nos': {'word': 'まとめ'}, 'off': {'word': 'x'},
    }
    return rows, files


@pytest.fixture
def audio_env(monkeypatch):
    queued: list = []
    monkeypatch.setattr(audio, 'pick_voice', lambda db, language_id: ('ja-voice', 1.0))
    monkeypatch.setattr(audio.queue_drain, 'enqueue',
                        lambda db, sense_id, language_id, reason, detail: queued.append(
                            (sense_id, reason, detail)) or True)
    return queued


def _run(db, synth=None, **kw):
    params = {'dry_run': False, 'cap': 500, 'types': audio.AUDIO_TYPES}
    params.update(kw)
    return audio.AudioBackfillRun(db, 3, synthesizer=synth or _FakeSynth(), **params)


def test_audio_reads_through_select_columns_and_writes_once_per_sense(monkeypatch, audio_env):
    rows, files = _audio_fixture()
    fake = _FakeStore(files).install(monkeypatch)
    db = _FakeDB(rows)
    synth = _FakeSynth()
    run = _run(db, synth)
    monkeypatch.setattr(run, 'report_coverage', lambda: None)

    assert run.run() is True

    assert fake.templates == [TEMPLATE]
    assert db.selects()[0] == [
        ('select', ('id, exercise_type, word_sense_id, language_id, content_version',), {}),
        ('eq', ('language_id', 3), {}), ('eq', ('is_active', True), {}),
        ('in_', ('exercise_type', ['phonetic_recognition', 'listening_flashcard']), {}),
        ('range', (0, 499), {})]
    assert [(w['sense_id'], w['language_id']) for w in fake.writes] == [(10, 3), (12, 3)]
    for write in fake.writes:
        assert write['db'] is db
        assert set(write) == {'db', 'sense_id', 'language_id', 'update_contents'}
    sense10 = fake.writes[0]['update_contents']
    assert list(sense10) == ['p10a', 'f10', 'p10b']
    assert sense10['p10a'] == {'word': 'ねこ', 'audio_url': 'https://r2.example/l1_10_3/ねこ.mp3'}
    assert sense10['f10']['front_audio_url'] == (
        'https://r2.example/listening_flashcard_10_3/ねこ.mp3'), 'per-type URL key kept'
    assert 'audio_url' not in sense10['f10']
    assert run.stats['synthesised'] == 4
    assert run.stats['skipped_no_sense'] == 1
    assert 'nos' not in [c['file_id'] for c in synth.calls]
    assert db.writes() == []


def test_audio_hydrates_at_most_100_senses_per_call(monkeypatch, audio_env):
    rows = [_audio_row(f'r{i:03d}', 2000 + i) for i in range(230)]
    files = {r['id']: {'word': f'w{i}'} for i, r in enumerate(rows)}
    fake = _FakeStore(files).install(monkeypatch)
    db = _FakeDB(rows)

    pending = _run(db).fetch_pending()

    assert len(pending) == 230
    assert [len(c['senses']) for c in fake.hydrate_calls] == [100, 100, 30]
    assert all(c['db'] is db and set(c) == {'senses', 'ids', 'db'} for c in fake.hydrate_calls)


def test_audio_dry_run_synthesises_and_writes_nothing(monkeypatch, audio_env):
    rows, files = _audio_fixture()
    fake = _FakeStore(files).install(monkeypatch)
    db = _FakeDB(rows)
    synth = _FakeSynth()
    run = _run(db, synth, dry_run=True)

    run.run()

    assert synth.calls == []
    assert fake.writes == []
    assert db.writes() == []
    assert run.stats['would_synthesise'] == 4


def test_audio_report_coverage_makes_no_write_call(monkeypatch, audio_env, caplog):
    rows, files = _audio_fixture()
    files['p12']['audio_url'] = 'https://r2.example/p12.mp3'
    fake = _FakeStore(files).install(monkeypatch)
    db = _FakeDB(rows)

    with caplog.at_level(logging.INFO, logger=audio.logger.name):
        _run(db).report_coverage()

    assert fake.writes == [] and db.writes() == []
    assert fake.templates == [TEMPLATE]
    messages = [r.getMessage() for r in caplog.records]
    assert any('phonetic_recognition' in m and '2/4' in m for m in messages)
    assert any('listening_flashcard' in m and '0/1' in m for m in messages)
    assert any('not counted: 1 item(s) without a sense' in m for m in messages)


def test_audio_write_error_fails_every_row_of_the_write_and_continues(
        monkeypatch, audio_env, caplog):
    rows, files = _audio_fixture()
    fake = _FakeStore(files, raise_for={10: store.ContentStorageError('upload 503')})
    fake.install(monkeypatch)
    run = _run(_FakeDB(rows))
    monkeypatch.setattr(run, 'report_coverage', lambda: None)

    with caplog.at_level(logging.ERROR, logger=audio.logger.name):
        run.run()

    assert [w['sense_id'] for w in fake.writes] == [10, 12]
    assert run.stats['failed'] == 3
    assert run.stats['synthesised'] == 1
    failed = [f for f in run.failures if 'content write failed' in f['reason']]
    assert sorted(f['exercise_id'] for f in failed) == ['f10', 'p10a', 'p10b']
    assert all(f['sense_id'] == 10 for f in failed)
    assert any('sense 10: writing 3 audio url(s) failed' in r.getMessage()
               for r in caplog.records)


def test_audio_tts_failure_queues_a_retry_and_the_rest_of_the_sense_is_written(
        monkeypatch, audio_env):
    rows, files = _audio_fixture()
    fake = _FakeStore(files).install(monkeypatch)
    run = _run(_FakeDB(rows), _FakeSynth(fail_for={'ネコ'}))
    monkeypatch.setattr(run, 'report_coverage', lambda: None)

    run.run()

    assert list(fake.writes[0]['update_contents']) == ['p10a', 'f10']
    assert run.stats['failed'] == 1
    assert audio_env == [(10, audio.QUEUE_REASON,
                          {'exercise_id': 'p10b', 'reason': 'azure 429'})]


def test_audio_cap_counts_urls_of_the_current_sense(monkeypatch, audio_env, caplog):
    rows, files = _audio_fixture()
    fake = _FakeStore(files).install(monkeypatch)
    synth = _FakeSynth()
    run = _run(_FakeDB(rows), synth, cap=2)
    monkeypatch.setattr(run, 'report_coverage', lambda: None)

    with caplog.at_level(logging.WARNING, logger=audio.logger.name):
        run.run()

    assert len(synth.calls) == 2
    assert [(w['sense_id'], list(w['update_contents'])) for w in fake.writes] == [
        (10, ['p10a', 'f10'])], 'the capped sense still writes what it synthesised'
    assert run.stats['synthesised'] == 2
    assert run.stats['capped'] == 2
    assert any('cap of 2 reached' in r.getMessage() for r in caplog.records)


def test_audio_read_error_keeps_the_partial_read(monkeypatch, audio_env, caplog):
    rows, files = _audio_fixture()
    _FakeStore(files).install(monkeypatch)
    db = _FakeDB(rows)
    db.read_error = RuntimeError('timeout')

    with caplog.at_level(logging.ERROR, logger=audio.logger.name):
        assert _run(db).fetch_pending() == []
        _run(db).report_coverage()

    messages = [r.getMessage() for r in caplog.records]
    assert any('could not read exercises: timeout' in m for m in messages)
    assert any('coverage query failed: timeout' in m for m in messages)


def test_audio_db_mode_reads_and_writes_todays_calls(audio_env):
    """Real store, both flags db: content in the select, one update chain per row."""
    assert (store.read_mode(), store.write_mode()) == ('db', 'db')
    rows, files = _audio_fixture()
    for row in rows:
        row['content'] = copy.deepcopy(files[row['id']])
    db = _FakeDB(rows)
    run = _run(db)
    run.report_coverage = lambda: None

    run.run()

    assert db.selects()[0][0] == (
        'select', ('id, exercise_type, word_sense_id, language_id, content',), {})
    updates = db.writes()
    assert [steps[1] for _, steps in updates] == [
        ('eq', ('id', 'p10a'), {}), ('eq', ('id', 'f10'), {}), ('eq', ('id', 'p10b'), {}),
        ('eq', ('id', 'p12'), {})]
    assert updates[0][1][0] == ('update', ({'content': {
        'word': 'ねこ', 'audio_url': 'https://r2.example/l1_10_3/ねこ.mp3'}},), {})
    assert run.stats['synthesised'] == 4
