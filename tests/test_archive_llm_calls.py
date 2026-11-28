"""services/llm_calls_archive.py and scripts/archive_llm_calls.py: llm_calls rows below a
cutoff go to Storage, are verified there, and only then deleted; the weekly job claims each
cutoff once. Offline: a fake PostgREST table and a fake bucket."""

from __future__ import annotations

import gzip
import hashlib
import io
import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from scripts import archive_llm_calls as al
from services import llm_calls_archive as la

CUTOFF = datetime(2026, 11, 27, tzinfo=timezone.utc)


def _row(i, day):
    ts = (datetime(2026, 11, day, tzinfo=timezone.utc) + timedelta(minutes=i)).isoformat()
    return {'id': f'00000000-0000-0000-0000-{i:012d}', 'created_at': ts, 'task_name': 't',
            'raw_response': f'answer {i} 答え'}


class _Q:
    def __init__(self, db):
        self.db, self.filters, self.window, self.mode, self.count = db, [], None, 'select', None

    def select(self, *_cols, count=None):
        self.count = count
        return self

    def lt(self, col, val):
        self.filters.append(lambda r: la.parse_ts(r[col]) < la.parse_ts(val))
        return self

    def in_(self, col, vals):
        vals = set(vals)
        self.filters.append(lambda r: r[col] in vals)
        return self

    def order(self, *_a, **_k):
        return self

    def range(self, a, b):
        self.window = (a, b)
        return self

    def limit(self, _n):
        return self

    def delete(self, returning=None):
        self.mode = 'delete'
        return self

    def execute(self):
        hit = [r for r in sorted(self.db.rows, key=lambda r: (r['created_at'], r['id']))
               if all(f(r) for f in self.filters)]
        if self.mode == 'delete':
            self.db.deleted += [r['id'] for r in hit]
            self.db.rows = [r for r in self.db.rows if r not in hit]
            return SimpleNamespace(data=[], count=None)
        if self.window:
            hit = hit[self.window[0]:self.window[1] + 1]
        return SimpleNamespace(data=[dict(r) for r in hit],
                               count=len(hit) if self.count else None)


class _Bucket:
    def __init__(self, store):
        self.store = store

    def upload(self, path, data, opts):
        if path in self.store:
            raise RuntimeError('409 Duplicate')
        self.store[path] = bytes(data)

    def download(self, path):
        if path not in self.store:
            raise RuntimeError('404')
        return self.store[path]


class FakeDB:
    def __init__(self, rows):
        self.rows, self.deleted, self.objects = list(rows), [], {}
        self.storage = SimpleNamespace(from_=lambda bucket: _Bucket(self.objects))

    def table(self, _name):
        return _Q(self)


@pytest.fixture
def db(monkeypatch, tmp_path):
    monkeypatch.setattr(al, 'LOCAL_DIR', str(tmp_path / 'local'))
    monkeypatch.setattr(la, 'PAGE', 3)                     # several pages
    monkeypatch.setattr(la, 'DELETE_CHUNK', 2)
    rows = [_row(i, 25) for i in range(7)] + [_row(100 + i, 27) for i in range(2)]
    return FakeDB(rows)


def _run(db, *args):
    return al.main(['--before', '2026-11-27', *args], db=db)


def test_dry_run_writes_and_deletes_nothing(db):
    assert _run(db) == 0
    assert db.objects == {} and db.deleted == []


def test_apply_archives_verifies_and_keeps_rows_without_delete(db):
    assert _run(db, '--apply') == 0
    (obj,) = [p for p in db.objects if p.endswith('.jsonl.gz')]
    assert obj == ('llm_calls/llm_calls_20261125T000000_to_20261125T000600'
                   '__cutoff_20261127T000000.jsonl.gz')
    manifest = json.loads(db.objects[la.manifest_name(obj)])
    assert manifest['rows'] == 7 and manifest['cutoff_created_at_lt'] == '2026-11-27T00:00:00Z'
    assert manifest['sha256'] == hashlib.sha256(db.objects[obj]).hexdigest()
    lines = gzip.GzipFile(fileobj=io.BytesIO(db.objects[obj])).read().decode().splitlines()
    assert [json.loads(x)['id'] for x in lines] == [_row(i, 25)['id'] for i in range(7)]
    assert '答え' in lines[0]                                  # UTF-8, not escaped
    assert db.deleted == [] and len(db.rows) == 9


def test_delete_removes_exactly_the_archived_rows(db):
    assert _run(db, '--apply', '--delete') == 0
    assert sorted(db.deleted) == sorted(_row(i, 25)['id'] for i in range(7))
    assert [r['id'] for r in db.rows] == [_row(100, 27)['id'], _row(101, 27)['id']]


def test_a_failed_verification_deletes_nothing(db, monkeypatch):
    real = la.rows_below

    def extra(dbx, cutoff, columns='*'):
        rows = list(real(dbx, cutoff, columns))
        if columns == 'id':                                  # a row appeared below the cutoff
            rows.append({'id': 'late'})
        return rows
    monkeypatch.setattr(la, 'rows_below', extra)
    assert _run(db, '--apply', '--delete') == 2
    assert db.deleted == []


def test_a_rerun_accepts_its_own_identical_upload_and_refuses_a_different_one(db):
    assert _run(db, '--apply') == 0
    first = dict(db.objects)
    assert _run(db, '--apply', '--delete') == 0               # same bytes already there
    assert db.objects == first and len(db.deleted) == 7
    (obj,) = [p for p in db.objects if p.endswith('.jsonl.gz')]
    with pytest.raises(la.ArchiveError):
        la.upload_once(db, obj, b'other', 'application/gzip')


def test_encode_is_deterministic():
    rows = [_row(i, 25) for i in range(3)]
    assert la.encode(rows)[0] == la.encode(rows)[0]


def test_delete_needs_apply_and_the_cutoff_cannot_be_in_the_future():
    with pytest.raises(SystemExit):
        al.main(['--delete'], db=FakeDB([]))
    with pytest.raises(SystemExit):
        al.cutoff_of('2999-01-01')


# ---------------------------------------------------------------------------
# Weekly job (web/scheduler.py: llm_calls_archive_weekly)
# ---------------------------------------------------------------------------

NOW = datetime(2026, 11, 29, 3, 40, tzinfo=timezone.utc)   # a Sunday


def test_weekly_job_keeps_the_last_days_and_moves_the_rest(db, monkeypatch):
    monkeypatch.setattr('config.Config.LLM_CALLS_ARCHIVE_KEEP_DAYS', 3, raising=False)
    result = la.run_weekly(db, now=NOW)                     # cutoff 2026-11-26 00:00
    assert result['rows'] == 7 and result['deleted'] == 7 and result['left'] == 0
    assert result['cutoff'] == '2026-11-26T00:00:00+00:00'
    assert [r['id'] for r in db.rows] == [_row(100, 27)['id'], _row(101, 27)['id']]
    assert la.lock_path(datetime(2026, 11, 26, tzinfo=timezone.utc)) in db.objects
    assert not any(p.startswith(al.LOCAL_DIR) for p in db.objects)


def test_a_second_worker_skips_a_claimed_cutoff(db, monkeypatch):
    monkeypatch.setattr('config.Config.LLM_CALLS_ARCHIVE_KEEP_DAYS', 3, raising=False)
    cutoff = datetime(2026, 11, 26, tzinfo=timezone.utc)
    db.objects[la.lock_path(cutoff)] = b'{"claimed_at": "earlier"}'   # the other worker
    result = la.run_weekly(db, now=NOW)
    assert result == {'skipped': True, 'reason': 'cutoff 20261126T000000 already claimed'}
    assert db.deleted == [] and len(db.rows) == 9


def test_weekly_job_with_nothing_old_enough_does_nothing(db, monkeypatch):
    monkeypatch.setattr('config.Config.LLM_CALLS_ARCHIVE_KEEP_DAYS', 7, raising=False)
    result = la.run_weekly(db, now=NOW)                     # cutoff 2026-11-22: nothing below
    assert result['skipped'] is True and db.objects == {}


def test_keep_days_is_at_least_one(monkeypatch):
    monkeypatch.setattr('config.Config.LLM_CALLS_ARCHIVE_KEEP_DAYS', 0, raising=False)
    assert la.keep_days() == 1
