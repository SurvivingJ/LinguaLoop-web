"""TASK-991 — scripts/backfill_exercise_content.py (ADR-047 export, verify, repair, archives).

Fully offline: a local fake PostgREST client (tables in memory, the
``exercise_content_live_versions`` RPC computed from them, the 1,000-row cap) and
``InMemoryBackend`` installed with ``store.set_backend``. ``store.write_sense`` is
monkeypatched where a repair is exercised (the dual writer is TASK-979's).
"""

from __future__ import annotations

import copy
import gzip
import hashlib
import json
import os
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest

from config import Config
from scripts import backfill_exercise_content as bf
from services.exercise_content import store
from services.exercise_content.backends import InMemoryBackend

REPO_ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 12, 1, 9, 30, tzinfo=timezone.utc)
ZH, EN, JA = 1, 2, 3
SEMDISC_SQL = ('CREATE OR REPLACE FUNCTION public.apply_semdisc_notes(p_notes jsonb)\n'
               ' RETURNS integer\n LANGUAGE plpgsql\nAS $function$ BEGIN RETURN 0; END $function$\n')


# ---------------------------------------------------------------------------
# Local fake PostgREST client
# ---------------------------------------------------------------------------

class FakeAPIError(Exception):
    pass


class _Resp:
    def __init__(self, data, count=None):
        self.data = data
        self.count = count


class _Query:
    def __init__(self, db, table):
        self.db = db
        self.table = table
        self.columns = '*'
        self.count = None
        self.filters = []
        self.orders = []
        self.start = 0
        self.stop = None
        self.negate = False
        self.write = None
        self.steps = [('table', table)]
        db.queries.append(self.steps)

    def select(self, *columns, count=None):
        self.columns = ','.join(columns) if columns else '*'
        self.count = count
        self.steps.append(('select', self.columns, count))
        return self

    @property
    def not_(self):
        self.negate = True
        return self

    def _filter(self, name, column, predicate, arg):
        negate, self.negate = self.negate, False
        self.steps.append(('not.' + name if negate else name, column, arg))
        self.filters.append((lambda row: not predicate(row)) if negate else predicate)
        return self

    def eq(self, column, value):
        return self._filter('eq', column, lambda row: row.get(column) == value, value)

    def in_(self, column, values):
        values = list(values)
        return self._filter('in', column, lambda row: row.get(column) in values, values)

    def is_(self, column, value):
        assert value == 'null'
        return self._filter('is', column, lambda row: row.get(column) is None, value)

    def order(self, column, desc=False):
        assert not desc
        self.orders.append(column)
        self.steps.append(('order', column))
        return self

    def range(self, start, end):
        self.start, self.stop = start, end + 1
        self.steps.append(('range', start, end))
        return self

    def limit(self, size):
        self.stop = self.start + size
        self.steps.append(('limit', size))
        return self

    def _record_write(self, op, *args):
        self.write = op
        self.db.writes.append((self.table, op, args))
        return self

    def insert(self, *args, **kwargs):
        return self._record_write('insert', *args)

    def upsert(self, *args, **kwargs):
        return self._record_write('upsert', *args)

    def update(self, *args, **kwargs):
        return self._record_write('update', *args)

    def delete(self, *args, **kwargs):
        return self._record_write('delete', *args)

    def _project(self, row):
        if self.columns.strip() == '*':
            return copy.deepcopy(row)
        names = [c.strip() for c in self.columns.split(',') if c.strip()]
        return {name: copy.deepcopy(row.get(name)) for name in names}

    def execute(self):
        if self.write is not None:
            return _Resp([])
        if self.table not in self.db.tables:
            raise FakeAPIError(f'relation "public.{self.table}" does not exist')
        rows = [row for row in self.db.tables[self.table] if all(f(row) for f in self.filters)]
        count = len(rows) if self.count == 'exact' else None
        if self.count == 'exact' and self.table in self.db.count_override:
            count = self.db.count_override[self.table]
        for column in reversed(self.orders):
            rows.sort(key=lambda row: (row.get(column) is None, row.get(column)))
        stop = len(rows) if self.stop is None else self.stop
        stop = min(stop, self.start + self.db.max_rows)
        return _Resp([self._project(row) for row in rows[self.start:stop]], count)


class _RpcCall:
    def __init__(self, fn):
        self.fn = fn

    def execute(self):
        return _Resp(self.fn())


class FakeDB:
    def __init__(self, rows=(), tables=None):
        self.tables = {'exercises': [dict(r) for r in rows]}
        self.tables.update(tables or {})
        self.queries: list[list] = []
        self.rpcs: list[tuple] = []
        self.writes: list[tuple] = []
        self.count_override: dict[str, int] = {}
        self.max_rows = 1000
        self.rpc_handlers = {'exercise_content_live_versions': self._live_versions}

    def table(self, name):
        return _Query(self, name)

    def rpc(self, name, params):
        self.rpcs.append((name, copy.deepcopy(params)))
        handler = self.rpc_handlers.get(name)
        if handler is None:
            raise FakeAPIError(f'Could not find the function public.{name}')
        return _RpcCall(lambda: handler(params))

    def _live_versions(self, params):
        out: dict[str, set] = {}
        for row in self.tables['exercises']:
            if row['language_id'] == params['p_language_id'] and row['word_sense_id'] is not None:
                out.setdefault(str(row['word_sense_id']), set()).add(row['content_version'])
        return {key: sorted(values) for key, values in out.items()}

    def rows(self, sense_id=None):
        return [r for r in self.tables['exercises']
                if sense_id is None or r['word_sense_id'] == sense_id]

    def exercise_selects(self):
        return [steps for steps in self.queries
                if steps[0] == ('table', 'exercises') and steps[1][0] == 'select']


# ---------------------------------------------------------------------------
# Fixtures and helpers
# ---------------------------------------------------------------------------

_counter = iter(range(1, 10**9))


def _uid() -> str:
    return str(uuid.UUID(int=next(_counter)))


def _content(tag, extra=None):
    doc = {'question': f'q-{tag}', 'options': ['甲', '乙', '丙'], 'answer': 1,
           'explanation': {'en': f'because {tag}'}}
    if extra:
        doc.update(extra)
    return doc


def row(sense, *, lang=ZH, version=0, active=True, content=None, ex_type='cloze_completion',
        exercise_id=None):
    exercise_id = exercise_id or _uid()
    return {'id': exercise_id, 'word_sense_id': sense, 'language_id': lang,
            'exercise_type': ex_type, 'is_active': active, 'content_version': version,
            'content': content if content is not None else _content(exercise_id),
            'word_asset_id': 7, 'tags': {'variant': 'A'}}


@pytest.fixture
def mem():
    backend = InMemoryBackend()
    store.set_backend(backend)
    return backend


@pytest.fixture
def paths(tmp_path):
    return {'state': tmp_path / 'state.json', 'report': tmp_path / 'report.json'}


def run(db, paths, *argv, now=NOW):
    args = list(argv) + ['--state-file', str(paths['state']), '--report', str(paths['report'])]
    return bf.main(args, db=db, now=lambda: now)


def report(paths):
    return json.loads(Path(paths['report']).read_text(encoding='utf-8'))


def expected_file(db, lang, sense, version=0):
    exercises = {r['id']: r['content'] for r in db.rows(sense)}
    return store.encode_sense_file(sense, lang, version, exercises)


def kinds(rep):
    return sorted(m['kind'] for m in rep['mismatches'])


def _clean_env():
    return {k: v for k, v in os.environ.items()
            if not k.startswith(('SUPABASE_', 'EXERCISE_CONTENT_')) and k != 'OPENROUTER_API_KEY'}


def _gunzip_lines(data):
    text = gzip.decompress(data).decode('utf-8')
    return [json.loads(line) for line in text.splitlines()]


def _standard_db():
    rows = [row(101), row(101, active=False), row(101, ex_type='definition_match'),
            row(102), row(102),
            row(201, lang=JA), row(201, lang=JA),
            row(None), row(None)]                          # two zh rows without a sense
    return FakeDB(rows)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def test_help_exits_zero_offline():
    result = subprocess.run([sys.executable, 'scripts/backfill_exercise_content.py', '--help'],
                            cwd=str(REPO_ROOT), env=_clean_env(), capture_output=True,
                            text=True, timeout=120)
    assert result.returncode == 0, result.stderr
    for flag in ('--language', '--senses', '--limit', '--dry-run', '--verify', '--repair',
                 '--archive-all', '--archive-sense-less', '--archive-semdisc',
                 '--batch-senses', '--concurrency', '--state-file', '--report'):
        assert flag in result.stdout


@pytest.mark.parametrize('argv', [
    [],                                                          # --language is required
    ['--language', 'fr'],
    ['--language', 'zh', '--repair'],                            # --repair needs --verify
    ['--language', 'zh', '--archive-all', '20261201'],           # archives need all
    ['--language', 'all', '--archive-all', '20261201', '--verify'],
    ['--language', 'all', '--archive-all', '20261201', '--senses', '1'],
    ['--language', 'all', '--archive-all', '20261201', '--limit', '3'],
    ['--language', 'all', '--archive-all', 'bad/tag'],
    ['--language', 'all', '--archive-semdisc'],                  # no function source
    ['--language', 'all', '--archive-semdisc', '--semdisc-function-file', 'a.sql',
     '--semdisc-function-rpc', 'f'],
    ['--language', 'zh', '--semdisc-function-file', 'a.sql'],    # without --archive-semdisc
    ['--language', 'all', '--archive-semdisc', '--semdisc-function-rpc', 'f; drop'],
    ['--language', 'all', '--archive-semdisc', '--semdisc-function-rpc', 'f',
     '--semdisc-order', 'other_table=id'],
    ['--language', 'zh', '--batch-senses', '201'],
    ['--language', 'zh', '--batch-senses', '0'],
    ['--language', 'zh', '--concurrency', '0'],
    ['--language', 'zh', '--senses', '1,x'],
    ['--language', 'all', '--archive-all', 'T', '--archive-max-bytes', '1000'],
])
def test_bad_arguments_exit_2(argv, mem, paths):
    db = FakeDB()
    with pytest.raises(SystemExit) as excinfo:
        run(db, paths, *argv)
    assert excinfo.value.code == 2
    assert db.queries == [] and db.rpcs == [] and mem.calls == []


def test_default_paths():
    assert bf.default_state_path('zh').endswith(
        os.path.join('data', 'exercise_content_backfill', 'state-zh.json'))
    assert bf.default_report_path('all', NOW).endswith(
        os.path.join('data', 'exercise_content_backfill', 'report-all-20261201T093000Z.json'))


def test_refuses_without_storage_credentials(monkeypatch, paths):
    monkeypatch.setattr(Config, 'SUPABASE_URL', None)
    db = FakeDB([row(101)])
    assert run(db, paths, '--language', 'zh') == 2
    assert db.queries == [] and db.rpcs == []


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

def test_export_writes_one_v0_file_per_sense_equal_to_encode_sense_file(mem, paths):
    db = _standard_db()
    assert run(db, paths, '--language', 'zh') == 0

    assert mem.objects() == {'zh/101.v0.json': expected_file(db, ZH, 101),
                             'zh/102.v0.json': expected_file(db, ZH, 102)}
    decoded = store.decode_sense_file(mem.objects()['zh/101.v0.json'], sense_id=101, version=0)
    assert len(decoded) == 3                                   # active and inactive rows
    assert db.writes == []                                     # never touches exercises
    assert db.rpcs == [('exercise_content_live_versions', {'p_language_id': ZH})]
    rep = report(paths)
    assert (rep['senses'], rep['rows'], rep['files_written'], rep['files_verified']) == (2, 5, 2, 0)
    assert rep['mode'] == 'export' and rep['mismatches'] == [] and rep['exit_code'] == 0


def test_rows_are_read_in_sense_batches_with_fetch_all(mem, paths):
    rows = [row(s) for s in (11, 12, 13, 14, 15)]
    rows += [row(16) for _ in range(1205)]                     # one sense over the 1,000-row cap
    db = FakeDB(rows)
    assert run(db, paths, '--language', 'zh', '--batch-senses', '2') == 0

    selects = db.exercise_selects()
    assert selects, 'no exercises select'
    for steps in selects:
        assert steps[1] == ('select', bf.ROW_COLUMNS, None)
        filt = [s for s in steps if s[0] == 'in']
        assert len(filt) == 1 and filt[0][1] == 'word_sense_id' and len(filt[0][2]) <= 2
        assert ('order', 'id') in steps
        assert any(s[0] == 'range' for s in steps)
    batches = sorted({tuple(s[2]) for steps in selects for s in steps if s[0] == 'in'})
    assert batches == [(11, 12), (13, 14), (15, 16)]
    big = store.decode_sense_file(mem.objects()['zh/16.v0.json'], sense_id=16, version=0)
    assert len(big) == 1205


def test_sense_less_rows_never_enter_sense_files(mem, paths):
    db = _standard_db()
    assert run(db, paths, '--language', 'all') == 0
    sense_less = {r['id'] for r in db.rows() if r['word_sense_id'] is None}
    in_files = set()
    for path, data in mem.objects().items():
        lang, name = path.split('/')
        sense = int(name.split('.')[0])
        in_files |= set(store.decode_sense_file(data, sense_id=sense, version=0))
    assert in_files and not (in_files & sense_less)
    assert sorted(mem.paths()) == ['ja/201.v0.json', 'zh/101.v0.json', 'zh/102.v0.json']


def test_rerun_with_state_skips_completed_senses(mem, paths):
    db = _standard_db()
    assert run(db, paths, '--language', 'zh') == 0
    state = json.loads(paths['state'].read_text())
    assert state['completed'] == {'zh': [101, 102]}
    mem.clear_calls()
    before = mem.objects()

    assert run(db, paths, '--language', 'zh') == 0
    assert mem.calls == [] and mem.objects() == before
    rep = report(paths)
    assert (rep['skipped_from_state'], rep['senses'], rep['files_written']) == (2, 0, 0)


def test_rerun_without_state_writes_nothing_and_verifies(mem, paths, tmp_path):
    db = _standard_db()
    assert run(db, paths, '--language', 'zh') == 0
    before = mem.objects()
    mem.clear_calls()
    paths['state'] = tmp_path / 'fresh-state.json'

    assert run(db, paths, '--language', 'zh') == 0
    assert mem.objects() == before                             # put refused, nothing replaced
    assert sorted(mem.calls_for('put')) == ['zh/101.v0.json', 'zh/102.v0.json']
    rep = report(paths)
    assert (rep['files_written'], rep['files_verified'], rep['mismatches']) == (0, 2, [])


def test_existing_v0_is_never_overwritten_and_a_difference_is_reported(mem, paths):
    db = FakeDB([row(101), row(101)])
    stale = {r['id']: _content('stale') for r in db.rows(101)}
    mem.seed('zh/101.v0.json', store.encode_sense_file(101, ZH, 0, stale))
    before = mem.objects()

    assert run(db, paths, '--language', 'zh') == 1
    assert mem.objects() == before
    rep = report(paths)
    assert kinds(rep) == ['content_diff', 'content_diff']
    assert json.loads(paths['state'].read_text())['completed'] == {'zh': []}


def test_senses_at_a_later_version_are_verified_only(mem, paths):
    db = FakeDB([row(101, version=7), row(101, version=7), row(102, version=9)])
    mem.seed('zh/101.v7.json', expected_file(db, ZH, 101, version=7))

    assert run(db, paths, '--language', 'zh') == 1             # sense 102 has no v9 file
    assert mem.calls_for('put') == []
    assert sorted(mem.paths()) == ['zh/101.v7.json']
    rep = report(paths)
    assert rep['files_verified'] == 1
    [missing] = rep['mismatches']
    assert (missing['kind'], missing['sense_id'], missing['version'], missing['reason']) == (
        'missing_file', 102, 9, 'not_found')
    assert json.loads(paths['state'].read_text())['completed'] == {'zh': [101]}


def test_mixed_versions_are_not_exported(mem, paths):
    db = FakeDB([row(101, version=0), row(101, version=5)])
    assert run(db, paths, '--language', 'zh') == 1
    assert mem.calls_for('put') == []
    rep = report(paths)
    assert kinds(rep) == ['missing_file', 'missing_file', 'mixed_versions']
    mixed = next(m for m in rep['mismatches'] if m['kind'] == 'mixed_versions')
    assert mixed['versions'] == [0, 5] and mixed['rows_per_version'] == {'0': 1, '5': 1}


def test_dry_run_writes_nothing(mem, paths):
    db = _standard_db()
    mem.seed('zh/102.v0.json', expected_file(db, ZH, 102))
    mem.clear_calls()

    assert run(db, paths, '--language', 'zh', '--dry-run') == 0
    assert mem.calls_for('put') == [] and mem.calls_for('delete') == []
    assert sorted(mem.paths()) == ['zh/102.v0.json']
    assert not paths['state'].exists()
    rep = report(paths)                                        # the report is still written
    assert rep['dry_run'] is True
    assert (rep['would_write'], rep['files_written'], rep['files_verified']) == (1, 0, 1)


def test_state_resume_after_a_failed_upload(mem, paths):
    db = _standard_db()
    mem.fail_next('put', store.ContentStorageError('503 from storage'))
    assert run(db, paths, '--language', 'zh', '--concurrency', '1') == 1
    rep = report(paths)
    [error] = [a for a in rep['anomalies'] if a['severity'] == 'error']
    assert error['kind'] == 'storage_error' and error['sense_id'] == 101
    assert json.loads(paths['state'].read_text())['completed'] == {'zh': [102]}
    assert sorted(mem.paths()) == ['zh/102.v0.json']

    mem.clear_calls()
    assert run(db, paths, '--language', 'zh') == 0
    assert mem.calls_for('put') == ['zh/101.v0.json']
    assert mem.objects()['zh/101.v0.json'] == expected_file(db, ZH, 101)
    assert json.loads(paths['state'].read_text())['completed'] == {'zh': [101, 102]}


def test_unreadable_state_file_is_refused(mem, paths):
    paths['state'].write_text('{not json', encoding='utf-8')
    db = _standard_db()
    assert run(db, paths, '--language', 'zh') == 2
    assert db.rpcs == [] and mem.calls == []


def test_language_all_keeps_a_state_file_per_language(mem, tmp_path, monkeypatch):
    monkeypatch.setattr(bf, 'DEFAULT_DIR', str(tmp_path))
    db = _standard_db()
    assert bf.main(['--language', 'all', '--report', str(tmp_path / 'r.json')], db=db,
                   now=lambda: NOW) == 0
    assert json.loads((tmp_path / 'state-zh.json').read_text())['completed'] == {'zh': [101, 102]}
    assert json.loads((tmp_path / 'state-ja.json').read_text())['completed'] == {'ja': [201]}
    assert [p for name, p in db.rpcs] == [{'p_language_id': EN}, {'p_language_id': JA},
                                          {'p_language_id': ZH}]
    rep = json.loads((tmp_path / 'r.json').read_text())
    assert rep['per_language']['zh']['files_written'] == 2
    assert rep['per_language']['ja']['files_written'] == 1


def test_senses_and_limit_filters(mem, paths):
    db = FakeDB([row(s) for s in (101, 102, 103, 104)])
    assert run(db, paths, '--language', 'zh', '--senses', '104,102,103,999', '--limit', '2') == 0
    assert sorted(mem.paths()) == ['zh/102.v0.json', 'zh/103.v0.json']
    rep = report(paths)
    [missing] = [a for a in rep['anomalies'] if a['kind'] == 'sense_not_found']
    assert (missing['sense_id'], missing['severity']) == (999, 'info')


def test_rows_in_another_language_stay_in_the_sense_file(mem, paths):
    db = FakeDB([row(101), row(101, lang=JA)])
    assert run(db, paths, '--language', 'zh') == 0
    assert mem.objects()['zh/101.v0.json'] == expected_file(db, ZH, 101)
    rep = report(paths)
    [mismatch] = [a for a in rep['anomalies'] if a['kind'] == 'language_mismatch']
    assert mismatch['severity'] == 'info' and mismatch['row_language_id'] == JA


def test_non_object_content_blocks_the_export_of_that_sense(mem, paths):
    db = FakeDB([row(101), row(101, content=['not', 'an', 'object']), row(102)])
    assert run(db, paths, '--language', 'zh') == 1
    assert sorted(mem.paths()) == ['zh/102.v0.json']
    rep = report(paths)
    assert [a['kind'] for a in rep['anomalies'] if a['severity'] == 'error'] == ['bad_content']


def test_live_versions_failure_is_an_error(mem, paths):
    db = _standard_db()
    db.rpc_handlers['exercise_content_live_versions'] = lambda params: ['unexpected']
    assert run(db, paths, '--language', 'zh') == 1
    assert mem.calls == [] and db.exercise_selects() == []
    assert report(paths)['anomalies'][0]['kind'] == 'live_versions_failed'


def test_report_has_the_documented_shape(mem, paths):
    db = _standard_db()
    run(db, paths, '--language', 'zh', now=NOW)
    rep = report(paths)
    for key in ('language', 'mode', 'senses', 'rows', 'files_written', 'files_verified',
                'skipped_from_state', 'mismatches', 'anomalies', 'started_at', 'finished_at'):
        assert key in rep
    assert rep['language'] == 'zh'
    assert rep['started_at'] == rep['finished_at'] == '2026-12-01T09:30:00Z'


# ---------------------------------------------------------------------------
# Verify and repair
# ---------------------------------------------------------------------------

def _exported(mem, paths, tmp_path):
    db = FakeDB([row(101), row(101), row(102), row(103)])
    assert run(db, paths, '--language', 'zh') == 0
    mem.clear_calls()
    paths['report'] = tmp_path / 'verify.json'
    return db


def test_verify_passes_after_an_export(mem, paths, tmp_path):
    db = _exported(mem, paths, tmp_path)
    assert run(db, paths, '--language', 'zh', '--verify') == 0
    rep = report(paths)
    assert rep['mode'] == 'verify' and rep['files_verified'] == 3 and rep['mismatches'] == []
    assert mem.calls_for('put') == [] and db.writes == []


def test_verify_finds_tampered_content_a_missing_exercise_and_a_missing_file(
        mem, paths, tmp_path):
    db = _exported(mem, paths, tmp_path)
    tampered = db.rows(101)[0]
    tampered['content'] = _content('edited in place by a WRITE=db shell')
    added = row(102)                                           # inserted outside the store
    db.tables['exercises'].append(added)
    db.tables['exercises'].append(row(104))                    # a sense with no file at all
    state_before = paths['state'].read_text()

    assert run(db, paths, '--language', 'zh', '--verify') == 1
    rep = report(paths)
    by_kind = {m['kind']: m for m in rep['mismatches']}
    assert sorted(by_kind) == ['content_diff', 'missing_exercise', 'missing_file']
    assert (by_kind['content_diff']['sense_id'], by_kind['content_diff']['exercise_id']) == (
        101, tampered['id'])
    assert by_kind['content_diff']['db_sha256'] != by_kind['content_diff']['file_sha256']
    assert (by_kind['missing_exercise']['sense_id'],
            by_kind['missing_exercise']['exercise_id']) == (102, added['id'])
    assert by_kind['missing_file']['sense_id'] == 104
    assert mem.calls_for('put') == [] and mem.calls_for('delete') == []
    assert paths['state'].read_text() == state_before          # verify never touches state


def test_verify_reports_a_corrupt_file_as_missing(mem, paths, tmp_path):
    db = _exported(mem, paths, tmp_path)
    mem.seed('zh/103.v0.json', b'{"format": 1, "sense_id": 999}')
    assert run(db, paths, '--language', 'zh', '--verify') == 1
    [mismatch] = report(paths)['mismatches']
    assert (mismatch['kind'], mismatch['reason'], mismatch['sense_id']) == (
        'missing_file', 'corrupt', 103)


def test_verify_read_failures_are_errors_not_mismatches(mem, paths, tmp_path):
    db = _exported(mem, paths, tmp_path)
    mem.fail_next('get', store.ContentStorageError('storage returned 503'))
    mem.fail_next('get', RuntimeError('unexpected'))
    assert run(db, paths, '--language', 'zh', '--verify', '--concurrency', '1') == 1
    rep = report(paths)
    assert rep['mismatches'] == []
    assert [(a['kind'], a['sense_id']) for a in rep['anomalies']] == [
        ('storage_error', 101), ('sense_failed', 102)]
    assert rep['files_verified'] == 1


def test_repair_refuses_in_db_write_mode(mem, paths):
    db = _standard_db()
    assert store.write_mode() == 'db'
    assert run(db, paths, '--language', 'zh', '--verify', '--repair') == 2
    assert db.rpcs == [] and db.queries == [] and mem.calls == []


def _dual(monkeypatch, result_version=4711):
    monkeypatch.setattr(Config, 'EXERCISE_CONTENT_WRITE', 'dual')
    calls = []

    def fake_write_sense(db, sense_id, language_id, **kwargs):
        calls.append((sense_id, language_id, kwargs))
        return store.WriteResult(sense_id=sense_id, mode='dual', version=result_version,
                                 inserted_ids=[], deleted_count=0,
                                 updated_ids=list(kwargs.get('update_contents') or {}),
                                 attempts=1)
    monkeypatch.setattr(store, 'write_sense', fake_write_sense)
    return calls


def test_repair_rewrites_each_mismatched_sense_from_db_content(mem, paths, tmp_path,
                                                               monkeypatch):
    db = _exported(mem, paths, tmp_path)
    db.rows(101)[0]['content'] = _content('fixed in the DB')
    calls = _dual(monkeypatch)
    assert store.write_mode() == 'dual'

    assert run(db, paths, '--language', 'zh', '--verify', '--repair') == 0
    assert len(calls) == 1
    sense_id, language_id, kwargs = calls[0]
    assert (sense_id, language_id) == (101, ZH)
    assert kwargs == {'update_contents': {r['id']: r['content'] for r in db.rows(101)}}
    rep = report(paths)
    assert rep['mode'] == 'repair'
    assert rep['repaired'] == [{'language': 'zh', 'sense_id': 101, 'version': 4711,
                                'updated': 2, 'attempts': 1}]
    assert kinds(rep) == ['content_diff']                      # found, then repaired
    assert db.writes == []                                     # only through write_sense


def test_repair_dry_run_lists_senses_without_writing(mem, paths, tmp_path, monkeypatch):
    db = _exported(mem, paths, tmp_path)
    db.rows(102)[0]['content'] = _content('changed')
    calls = _dual(monkeypatch)
    assert run(db, paths, '--language', 'zh', '--verify', '--repair', '--dry-run') == 1
    assert calls == []
    assert report(paths)['would_repair'] == [{'language': 'zh', 'sense_id': 102, 'rows': 1}]


def test_repair_failure_is_reported(mem, paths, tmp_path, monkeypatch):
    db = _exported(mem, paths, tmp_path)
    db.rows(103)[0]['content'] = _content('changed')
    monkeypatch.setattr(Config, 'EXERCISE_CONTENT_WRITE', 'dual')

    def conflict(*args, **kwargs):
        raise store.ContentWriteConflict('lost the compare-and-swap 3 times')
    monkeypatch.setattr(store, 'write_sense', conflict)
    assert run(db, paths, '--language', 'zh', '--verify', '--repair') == 1
    rep = report(paths)
    [failed] = [a for a in rep['anomalies'] if a['kind'] == 'repair_failed']
    assert failed['sense_id'] == 103 and 'ContentWriteConflict' in failed['error']


def test_repair_skips_a_sense_that_is_clean_when_read_again(mem, paths, tmp_path,
                                                            monkeypatch):
    db = _exported(mem, paths, tmp_path)
    target = db.rows(101)[0]
    original = copy.deepcopy(target['content'])
    target['content'] = _content('transient')
    calls = _dual(monkeypatch)
    real_fetch = bf.fetch_sense_rows
    reads = []

    def fetch(db_, sense_ids):
        reads.append(list(sense_ids))
        if len(reads) == 2:                                    # the repair's fresh read
            target['content'] = original
        return real_fetch(db_, sense_ids)
    monkeypatch.setattr(bf, 'fetch_sense_rows', fetch)

    assert run(db, paths, '--language', 'zh', '--verify', '--repair') == 0
    assert calls == [] and reads[1] == [101]
    assert any(a['kind'] == 'repair_not_needed' for a in report(paths)['anomalies'])


# ---------------------------------------------------------------------------
# Archives
# ---------------------------------------------------------------------------

def _manifest(mem, path):
    return json.loads(mem.objects()[path].decode('utf-8'))


def _archive_line(r):
    return {k: r[k] for k in bf.ARCHIVE_FIELDS}


def test_archive_all_writes_per_language_objects_and_a_matching_manifest(mem, paths):
    db = _standard_db()
    assert run(db, paths, '--language', 'all', '--archive-all', '20261201') == 0
    folder = '_archive/exercises-content-20261201'
    assert sorted(mem.paths()) == [f'{folder}/en.jsonl.gz', f'{folder}/ja.jsonl.gz',
                                   f'{folder}/manifest.json', f'{folder}/zh.jsonl.gz']
    assert mem.calls_for('put')[-1] == f'{folder}/manifest.json'      # manifest last

    manifest = _manifest(mem, f'{folder}/manifest.json')
    objects = mem.objects()
    for entry in manifest['objects']:
        assert entry['sha256'] == hashlib.sha256(objects[entry['path']]).hexdigest()
        assert entry['bytes'] == len(objects[entry['path']])
        assert entry['rows'] == len(_gunzip_lines(objects[entry['path']]))
    assert manifest['languages']['zh']['rows'] == 7
    assert manifest['languages']['zh']['rows_without_sense'] == 2
    assert manifest['languages']['en']['rows'] == 0
    assert manifest['total_rows'] == len(db.rows())

    zh_lines = _gunzip_lines(objects[f'{folder}/zh.jsonl.gz'])
    zh_rows = [r for r in db.rows() if r['language_id'] == ZH]
    assert sorted(json.dumps(line, sort_keys=True) for line in zh_lines) == sorted(
        json.dumps(_archive_line(r), sort_keys=True) for r in zh_rows)
    assert all(set(line) == set(bf.ARCHIVE_FIELDS) for line in zh_lines)
    assert db.writes == []


def test_archive_all_is_never_overwritten(mem, paths):
    db = _standard_db()
    assert run(db, paths, '--language', 'all', '--archive-all', 'T1') == 0
    first = mem.objects()

    assert run(db, paths, '--language', 'all', '--archive-all', 'T1') == 0   # identical: fine
    assert mem.objects() == first
    assert {a['status'] for a in report(paths)['archives']} == {'identical'}

    db.rows(101)[0]['content'] = _content('edited since')
    assert run(db, paths, '--language', 'all', '--archive-all', 'T1') == 1
    assert mem.objects() == first
    assert report(paths)['anomalies'][-1]['kind'] == 'archive_all_failed'


def test_archive_all_row_count_mismatch_writes_nothing(mem, paths):
    db = _standard_db()
    db.count_override['exercises'] = 999
    assert run(db, paths, '--language', 'all', '--archive-all', 'T1') == 1
    assert mem.calls_for('put') == []


def test_archive_all_splits_objects_over_the_size_limit(mem, paths):
    def noise(i):
        return hashlib.sha256(str(i).encode()).hexdigest() * 8   # ~512 hex chars, poor compression
    rows = [row(300 + i // 10, content={'blob': noise(i)}) for i in range(400)]
    db = FakeDB(rows)
    assert run(db, paths, '--language', 'all', '--archive-all', 'T2',
               '--archive-max-bytes', '65536') == 0
    folder = '_archive/exercises-content-T2'
    zh_parts = sorted(p for p in mem.paths() if p.startswith(f'{folder}/zh.part-'))
    assert len(zh_parts) >= 2
    assert zh_parts[0] == f'{folder}/zh.part-0001.jsonl.gz'
    assert f'{folder}/zh.jsonl.gz' not in mem.paths()
    objects = mem.objects()
    assert all(len(objects[p]) <= 65536 for p in zh_parts)
    lines = [line for p in zh_parts for line in _gunzip_lines(objects[p])]
    assert [line['id'] for line in lines] == [r['id'] for r in sorted(
        db.rows(), key=lambda r: (r['word_sense_id'], r['id']))]
    manifest = _manifest(mem, f'{folder}/manifest.json')
    zh_entries = [e for e in manifest['objects'] if e['language'] == 'zh']
    assert [e['path'] for e in zh_entries] == zh_parts
    assert {e['parts'] for e in zh_entries} == {len(zh_parts)}
    assert sum(e['rows'] for e in zh_entries) == 400


def test_gzip_parts_are_deterministic_and_bounded():
    lines = [json.dumps({'i': i, 'x': hashlib.sha256(str(i).encode()).hexdigest() * 4})
             .encode() + b'\n' for i in range(600)]

    def build():
        parts = bf.GzipParts(65536)
        for line in lines:
            parts.add(line)
        return parts.finish()
    first, second = build(), build()
    assert first == second
    assert all(len(data) <= 65536 for data, _ in first)
    assert sum(rows for _, rows in first) == 600
    assert b''.join(gzip.decompress(data) for data, _ in first) == b''.join(lines)
    with pytest.raises(bf.ArchiveError):
        bf._fit([os.urandom(80_000)], 65536)


def test_archive_sense_less(mem, paths):
    db = _standard_db()
    db.tables['exercises'].append(row(None, lang=JA))
    assert run(db, paths, '--language', 'all', '--archive-sense-less') == 0
    path = '_archive/exercises-no-sense-20261201.json'
    assert mem.paths() == [path]
    doc = json.loads(mem.objects()[path])
    expected = sorted((r for r in db.rows() if r['word_sense_id'] is None), key=lambda r: r['id'])
    assert doc['rows'] == expected                              # every column, all languages
    assert doc['kind'] == 'exercises-no-sense' and doc['date'] == '20261201'

    assert run(db, paths, '--language', 'all', '--archive-sense-less') == 0   # same day, same rows
    db.tables['exercises'].append(row(None))
    assert run(db, paths, '--language', 'all', '--archive-sense-less') == 1   # never overwritten
    assert json.loads(mem.objects()[path]) == doc


def test_archive_dry_run_writes_nothing(mem, paths):
    db = _standard_db()
    assert run(db, paths, '--language', 'all', '--archive-all', 'T3', '--archive-sense-less',
               '--dry-run') == 0
    assert mem.calls_for('put') == []
    assert {a['status'] for a in report(paths)['archives']} == {'would_write'}


def _semdisc_db():
    backup = [{'id': _uid(), 'content': _content(i), 'exercise_type': 'semantic_discrimination'}
              for i in range(5)]
    work = [{'exercise_id': _uid(), 'note': f'n{i}', 'applied': i % 2 == 0} for i in range(3)]
    return FakeDB(tables={'backup_semdisc_content_20261115': backup,
                          'semdisc_rewrite_work': work})


def _check_semdisc(mem, db):
    folder = '_archive/semdisc-20261115'
    assert sorted(mem.paths()) == [f'{folder}/apply_semdisc_notes.sql',
                                   f'{folder}/backup_semdisc_content_20261115.jsonl.gz',
                                   f'{folder}/manifest.json',
                                   f'{folder}/semdisc_rewrite_work.jsonl.gz']
    assert mem.calls_for('put')[-1] == f'{folder}/manifest.json'
    objects = mem.objects()
    manifest = _manifest(mem, f'{folder}/manifest.json')
    assert len(manifest['objects']) == 3
    for entry in manifest['objects']:
        assert entry['sha256'] == hashlib.sha256(objects[entry['path']]).hexdigest()
    assert objects[f'{folder}/apply_semdisc_notes.sql'] == SEMDISC_SQL.encode()
    backup = _gunzip_lines(objects[f'{folder}/backup_semdisc_content_20261115.jsonl.gz'])
    assert backup == sorted(db.tables['backup_semdisc_content_20261115'], key=lambda r: r['id'])
    work = _gunzip_lines(objects[f'{folder}/semdisc_rewrite_work.jsonl.gz'])
    assert work == sorted(db.tables['semdisc_rewrite_work'], key=lambda r: r['exercise_id'])
    assert manifest['tables'] == {
        'backup_semdisc_content_20261115': {'rows': 5, 'objects': 1, 'order_by': ['id']},
        'semdisc_rewrite_work': {'rows': 3, 'objects': 1, 'order_by': ['exercise_id']}}


def test_archive_semdisc_from_a_function_file(mem, paths, tmp_path):
    sql = tmp_path / 'apply_semdisc_notes.sql'
    sql.write_text(SEMDISC_SQL, encoding='utf-8')
    db = _semdisc_db()
    assert run(db, paths, '--language', 'all', '--archive-semdisc',
               '--semdisc-function-file', str(sql)) == 0
    _check_semdisc(mem, db)
    assert db.rpcs == [] and db.writes == []
    before = mem.objects()
    assert run(db, paths, '--language', 'all', '--archive-semdisc',
               '--semdisc-function-file', str(sql)) == 0          # identical re-run
    assert mem.objects() == before


def test_archive_semdisc_from_a_read_only_rpc(mem, paths):
    db = _semdisc_db()
    db.rpc_handlers['semdisc_function_definition'] = lambda params: SEMDISC_SQL
    assert run(db, paths, '--language', 'all', '--archive-semdisc',
               '--semdisc-function-rpc', 'semdisc_function_definition') == 0
    _check_semdisc(mem, db)
    assert db.rpcs == [('semdisc_function_definition', {})]


def test_archive_semdisc_refuses_a_file_that_is_not_the_definition(mem, paths, tmp_path):
    sql = tmp_path / 'wrong.sql'
    sql.write_text('select 1;', encoding='utf-8')
    db = _semdisc_db()
    assert run(db, paths, '--language', 'all', '--archive-semdisc',
               '--semdisc-function-file', str(sql)) == 2
    assert run(db, paths, '--language', 'all', '--archive-semdisc',
               '--semdisc-function-file', str(tmp_path / 'absent.sql')) == 2
    assert db.queries == [] and mem.calls == []


def test_archive_semdisc_missing_table_writes_nothing(mem, paths, tmp_path):
    sql = tmp_path / 'f.sql'
    sql.write_text(SEMDISC_SQL, encoding='utf-8')
    db = _semdisc_db()
    del db.tables['semdisc_rewrite_work']
    assert run(db, paths, '--language', 'all', '--archive-semdisc',
               '--semdisc-function-file', str(sql)) == 1
    assert mem.calls_for('put') == []
    [failed] = report(paths)['anomalies']
    assert failed['kind'] == 'archive_semdisc_failed' and 'does not exist' in failed['error']


def test_archive_semdisc_refuses_a_non_unique_order_key(mem, paths, tmp_path):
    sql = tmp_path / 'f.sql'
    sql.write_text(SEMDISC_SQL, encoding='utf-8')
    db = _semdisc_db()
    dup = db.tables['semdisc_rewrite_work'][0]['exercise_id']
    db.tables['semdisc_rewrite_work'].append({'exercise_id': dup, 'note': 'second', 'applied': 1})
    assert run(db, paths, '--language', 'all', '--archive-semdisc',
               '--semdisc-function-file', str(sql)) == 1
    assert mem.calls_for('put') == []
    assert 'unique' in report(paths)['anomalies'][0]['error']

    assert run(db, paths, '--language', 'all', '--archive-semdisc',
               '--semdisc-function-file', str(sql),
               '--semdisc-order', 'semdisc_rewrite_work=exercise_id,note') == 0
    lines = _gunzip_lines(mem.objects()['_archive/semdisc-20261115/semdisc_rewrite_work.jsonl.gz'])
    assert len(lines) == 4
