"""TASK-992 — scripts/sweep_exercise_content.py (ADR-047 orphan-file sweep).

Fully offline: ``InMemoryBackend`` (settable ``created_at``) installed with
``store.set_backend`` and a fake client that only answers
``rpc('exercise_content_live_versions')``.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from config import Config
from scripts import sweep_exercise_content as sweep
from services.exercise_content import store
from services.exercise_content.backends import InMemoryBackend, StoredObject

REPO_ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 12, 1, 12, 0, tzinfo=timezone.utc)
OLD = NOW - timedelta(days=3)
ZH, EN, JA = 1, 2, 3


class _Resp:
    def __init__(self, data):
        self.data = data


class _Call:
    def __init__(self, fn):
        self.fn = fn

    def execute(self):
        return _Resp(self.fn())


class FakeDB:
    """Only the live-versions RPC; ``live`` maps language_id -> RPC result (or a callable)."""

    def __init__(self, live):
        self.live = live
        self.rpcs = []

    def rpc(self, name, params):
        self.rpcs.append((name, params))
        assert name == 'exercise_content_live_versions'
        value = self.live.get(params['p_language_id'], {})
        return _Call(value if callable(value) else (lambda: value))

    def table(self, name):
        raise AssertionError(f'the sweep must not read table {name}')


@pytest.fixture
def mem():
    backend = InMemoryBackend()
    store.set_backend(backend)
    return backend


@pytest.fixture
def report_path(tmp_path):
    return tmp_path / 'sweep.json'


def run(db, report_path, *argv, now=NOW):
    return sweep.main(list(argv) + ['--report', str(report_path)], db=db, now=lambda: now)


def report(report_path):
    return json.loads(Path(report_path).read_text(encoding='utf-8'))


def seed(mem, path, *, created_at=OLD, size=10):
    mem.seed(path, b'x' * size, created_at=created_at)


def _rule_fixture(mem):
    seed(mem, 'zh/10.v3.json', size=11)                              # live
    seed(mem, 'zh/11.v0.json', size=12)                              # live (v0 export)
    seed(mem, 'zh/10.v1.json', size=13)                              # superseded, old
    seed(mem, 'zh/12.v0.json', size=14)                              # sense wiped, old
    seed(mem, 'zh/10.v9.json', created_at=NOW - timedelta(hours=1))  # writer mid-commit
    seed(mem, 'zh/13.v0.json')
    mem.set_created_at('zh/13.v0.json', None)                        # no created_at
    seed(mem, 'zh/notes.txt')                                        # unknown names
    seed(mem, 'zh/10.v3.json.tmp')
    seed(mem, 'zh/abc.v1.json')
    seed(mem, '_archive/exercises-content-T/zh.jsonl.gz')
    seed(mem, '_archive/exercises-no-sense-20261201.json')
    mem.clear_calls()
    return FakeDB({ZH: {'10': [3], '11': [0]}})


def _clean_env():
    return {k: v for k, v in os.environ.items()
            if not k.startswith(('SUPABASE_', 'EXERCISE_CONTENT_')) and k != 'OPENROUTER_API_KEY'}


def test_help_exits_zero_offline():
    result = subprocess.run([sys.executable, 'scripts/sweep_exercise_content.py', '--help'],
                            cwd=str(REPO_ROOT), env=_clean_env(), capture_output=True,
                            text=True, timeout=120)
    assert result.returncode == 0, result.stderr
    for flag in ('--language', '--apply', '--grace-hours', '--report'):
        assert flag in result.stdout


@pytest.mark.parametrize('argv', [[], ['--language', 'fr'], ['--language', 'zh',
                                                             '--grace-hours', '-1'],
                                  ['--language', 'zh', '--grace-hours', 'nan']])
def test_bad_arguments_exit_2(argv, mem, report_path):
    with pytest.raises(SystemExit) as excinfo:
        run(FakeDB({}), report_path, *argv)
    assert excinfo.value.code == 2
    assert mem.calls == []


def test_apply_deletes_exactly_the_old_files_no_row_points_at(mem, report_path):
    db = _rule_fixture(mem)
    assert run(db, report_path, '--language', 'zh', '--apply') == 0

    assert mem.calls_for('delete') == ['zh/10.v1.json', 'zh/12.v0.json']
    assert sorted(mem.paths()) == [
        '_archive/exercises-content-T/zh.jsonl.gz', '_archive/exercises-no-sense-20261201.json',
        'zh/10.v3.json', 'zh/10.v3.json.tmp', 'zh/10.v9.json', 'zh/11.v0.json',
        'zh/13.v0.json', 'zh/abc.v1.json', 'zh/notes.txt']
    assert mem.calls_for('list') == ['zh/']                          # _archive/ never listed
    assert db.rpcs == [('exercise_content_live_versions', {'p_language_id': ZH})]
    rep = report(report_path)
    assert rep['mode'] == 'apply'
    assert (rep['files_listed'], rep['kept_live'], rep['kept_grace'], rep['kept_no_created_at'],
            rep['unknown_names'], rep['deleted'], rep['would_delete'], rep['bytes_freed']) == (
        9, 2, 1, 1, 3, 2, 0, 27)
    assert sorted(rep['unknown']) == ['zh/10.v3.json.tmp', 'zh/abc.v1.json', 'zh/notes.txt']
    assert rep['no_created_at'] == ['zh/13.v0.json']
    assert rep['deleted_paths'] == ['zh/10.v1.json', 'zh/12.v0.json']
    assert rep['per_language']['zh']['deleted'] == 2 and rep['exit_code'] == 0


def test_dry_run_is_the_default_and_deletes_nothing(mem, report_path):
    db = _rule_fixture(mem)
    before = mem.objects()
    assert run(db, report_path, '--language', 'zh') == 0
    assert mem.calls_for('delete') == [] and mem.objects() == before
    rep = report(report_path)
    assert rep['mode'] == 'dry_run'
    assert (rep['deleted'], rep['would_delete'], rep['bytes_freed'], rep['would_free_bytes']) == (
        0, 2, 0, 27)
    assert rep['would_delete_paths'] == ['zh/10.v1.json', 'zh/12.v0.json']


def test_grace_period_boundary(mem, report_path):
    seed(mem, 'zh/20.v1.json', created_at=NOW - timedelta(hours=24))
    seed(mem, 'zh/21.v1.json', created_at=NOW - timedelta(hours=24) + timedelta(seconds=1))
    seed(mem, 'zh/22.v1.json', created_at=NOW + timedelta(minutes=5))   # clock skew: keep
    db = FakeDB({ZH: {'20': [2], '21': [2], '22': [2]}})
    assert run(db, report_path, '--language', 'zh', '--apply') == 0
    assert mem.calls_for('delete') == ['zh/20.v1.json']

    seed(mem, 'zh/23.v1.json', created_at=NOW)
    assert run(db, report_path, '--language', 'zh', '--apply', '--grace-hours', '0') == 0
    assert sorted(mem.calls_for('delete')) == ['zh/20.v1.json', 'zh/21.v1.json', 'zh/23.v1.json']


def test_naive_created_at_is_read_as_utc():
    obj = StoredObject(path='zh/5.v1.json', size=1,
                       created_at=(NOW - timedelta(hours=30)).replace(tzinfo=None))
    groups = sweep.classify([obj], {5: {2}}, 'zh', NOW, timedelta(hours=24))
    assert groups['delete'] == [obj]


def test_deletes_are_batched_by_100(mem, report_path):
    for sense in range(1, 251):
        seed(mem, f'zh/{sense}.v1.json')
    mem.clear_calls()
    db = FakeDB({ZH: {'9999': [0]}})
    assert run(db, report_path, '--language', 'zh', '--apply') == 0
    assert [len(batch) for batch in mem.delete_batches] == [100, 100, 50]
    assert mem.paths() == [] and report(report_path)['deleted'] == 250


def test_language_all_sweeps_each_language_against_its_own_live_set(mem, report_path):
    for path in ('en/5.v0.json', 'en/5.v2.json', 'ja/5.v0.json', 'ja/7.v4.json',
                 'zh/5.v2.json', 'zh/7.v4.json'):
        seed(mem, path)
    mem.clear_calls()
    db = FakeDB({EN: {'5': [2]}, JA: {'7': [4]}, ZH: {'5': [2], '7': [4]}})
    assert run(db, report_path, '--language', 'all', '--apply') == 0
    assert sorted(mem.paths()) == ['en/5.v2.json', 'ja/7.v4.json', 'zh/5.v2.json',
                                   'zh/7.v4.json']
    assert mem.calls_for('list') == ['en/', 'ja/', 'zh/']
    assert [params['p_language_id'] for _, params in db.rpcs] == [EN, JA, ZH]
    rep = report(report_path)
    assert {lang: per['deleted'] for lang, per in rep['per_language'].items()} == {
        'en': 1, 'ja': 1, 'zh': 0}


def test_an_empty_live_set_never_deletes_without_the_override(mem, report_path):
    seed(mem, 'zh/5.v0.json')
    seed(mem, 'zh/6.v0.json')
    db = FakeDB({ZH: {}})
    assert run(db, report_path, '--language', 'zh', '--apply') == 1
    assert mem.calls_for('delete') == []
    assert report(report_path)['anomalies'][0]['kind'] == 'empty_live_set'

    assert run(db, report_path, '--language', 'zh', '--apply', '--allow-empty-live-set') == 0
    assert mem.paths() == []


@pytest.mark.parametrize('bad', [None, ['not', 'an', 'object'], {'abc': [1]}, {'5': ['x']},
                                 {'5': 3}])
def test_a_bad_live_set_deletes_nothing(bad, mem, report_path):
    seed(mem, 'zh/5.v0.json')
    seed(mem, 'zh/6.v0.json')
    db = FakeDB({ZH: (lambda: bad)})
    code = run(db, report_path, '--language', 'zh', '--apply')
    assert mem.calls_for('delete') == []
    if bad is None:                                   # None reads as "no live sense"
        assert code == 1 and report(report_path)['anomalies'][0]['kind'] == 'empty_live_set'
    else:
        assert code == 1 and report(report_path)['anomalies'][0]['kind'] == 'read_failed'


def test_rpc_failure_deletes_nothing(mem, report_path):
    seed(mem, 'zh/5.v0.json')

    def boom():
        raise RuntimeError('PGRST202 function not found')
    db = FakeDB({ZH: boom})
    assert run(db, report_path, '--language', 'zh', '--apply') == 1
    assert mem.calls_for('delete') == [] and mem.paths() == ['zh/5.v0.json']
    [anomaly] = report(report_path)['anomalies']
    assert anomaly['kind'] == 'read_failed' and 'PGRST202' in anomaly['error']


def test_a_failed_delete_batch_is_reported_and_the_rest_continue(mem, report_path):
    for sense in range(1, 151):
        seed(mem, f'zh/{sense}.v1.json', size=2)
    mem.clear_calls()
    mem.fail_next('delete', store.ContentStorageError('storage returned 500'))
    db = FakeDB({ZH: {'9999': [0]}})
    assert run(db, report_path, '--language', 'zh', '--apply') == 1
    rep = report(report_path)
    assert rep['deleted'] == 50 and rep['bytes_freed'] == 100
    [failed] = rep['anomalies']
    assert failed['kind'] == 'delete_failed' and len(failed['paths']) == 100
    assert len(mem.paths()) == 100


def test_a_recursive_listing_never_touches_archive_paths():
    objects = [StoredObject('_archive/zh/5.v0.json', 1, OLD),
               StoredObject('zh/5.v0.json', 1, OLD)]
    groups = sweep.classify(objects, {}, 'zh', NOW, timedelta(hours=24))
    assert [o.path for o in groups['protected']] == ['_archive/zh/5.v0.json']
    assert [o.path for o in groups['delete']] == ['zh/5.v0.json']


def test_refuses_without_storage_credentials(monkeypatch, report_path):
    monkeypatch.setattr(Config, 'SUPABASE_URL', None)
    db = FakeDB({ZH: {}})
    assert run(db, report_path, '--language', 'zh', '--apply') == 2
    assert db.rpcs == [] and not Path(report_path).exists()


def test_default_report_path():
    assert sweep.default_report_path('zh', NOW).endswith(
        os.path.join('data', 'exercise_content_sweep', 'report-zh-20261201T120000Z.json'))
