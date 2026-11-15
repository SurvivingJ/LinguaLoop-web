"""scripts/archive_llm_calls.py: export, verify, and delete only what was verified."""

import gzip
import json

import pytest

from scripts import archive_llm_calls as arc


class FakeApi:
    def __init__(self, rows, corrupt_download=False, public_bucket=False):
        self.rows = rows
        self.objects = {}
        self.deleted = []
        self.corrupt_download = corrupt_download
        self.public_bucket = public_bucket
        self.bucket_created = False

    def count_before(self, before):
        return sum(1 for r in self.rows if r['created_at'] < before)

    def page_before(self, before, offset, limit):
        sel = sorted((r for r in self.rows if r['created_at'] < before),
                     key=lambda r: (r['created_at'], r['id']))
        return sel[offset:offset + limit]

    def delete_ids(self, ids):
        self.deleted.extend(ids)
        return len(ids)

    def ensure_private_bucket(self, bucket):
        if self.public_bucket:
            raise arc.ArchiveError('public')
        self.bucket_created = True

    def upload(self, bucket, path, data, content_type):
        if path in self.objects:
            return False
        self.objects[path] = data
        return True

    def download(self, bucket, path):
        data = self.objects[path]
        if self.corrupt_download:
            return data[:20] + bytes([data[20] ^ 0xFF]) + data[21:]
        return data


def make_rows(n, day='2026-11-10'):
    tag = day.replace('-', '')[-4:]
    return [{'id': f'{i:08d}-{tag}-0000-0000-000000000000', 'created_at': f'{day}T01:{i // 60 % 60:02d}:{i % 60:02d}+00:00',
             'task_name': 't', 'raw_response': 'résumé 日本'} for i in range(n)]


def test_export_upload_verify_delete_round_trip(tmp_path):
    rows = make_rows(2500) + make_rows(5, day='2026-11-15')
    api = FakeApi(rows)
    m = arc.run(api, '2026-11-15T00:00:00Z', 'b', str(tmp_path), delete=True)

    assert m['rows'] == 2500 and m['deleted'] == 2500
    assert len(api.deleted) == 2500 and len(set(api.deleted)) == 2500
    obj = next(v for k, v in api.objects.items() if k.endswith('.jsonl.gz'))
    lines = gzip.decompress(obj).decode('utf-8').splitlines()
    assert len(lines) == 2500
    assert json.loads(lines[0])['raw_response'] == 'résumé 日本'
    manifest = json.loads(next(v for k, v in api.objects.items() if k.endswith('.manifest.json')))
    assert manifest['rows'] == 2500 and manifest['cutoff_created_at_lt'] == '2026-11-15T00:00:00Z'
    assert (tmp_path / obj_name(api)).exists()


def obj_name(api):
    return next(k for k in api.objects if k.endswith('.jsonl.gz')).split('/')[-1]


def test_no_delete_without_flag(tmp_path):
    api = FakeApi(make_rows(10))
    arc.run(api, '2026-11-15T00:00:00Z', 'b', str(tmp_path), delete=False)
    assert api.deleted == []


def test_corrupt_download_stops_before_delete(tmp_path):
    api = FakeApi(make_rows(10), corrupt_download=True)
    with pytest.raises(arc.ArchiveError):
        arc.run(api, '2026-11-15T00:00:00Z', 'b', str(tmp_path), delete=True)
    assert api.deleted == []


def test_public_bucket_refused(tmp_path):
    api = FakeApi(make_rows(10), public_bucket=True)
    with pytest.raises(arc.ArchiveError):
        arc.run(api, '2026-11-15T00:00:00Z', 'b', str(tmp_path), delete=True)
    assert api.deleted == [] and api.objects == {}


def test_count_mismatch_stops(tmp_path):
    api = FakeApi(make_rows(10))
    api.count_before = lambda before: 11
    with pytest.raises(arc.ArchiveError):
        arc.run(api, '2026-11-15T00:00:00Z', 'b', str(tmp_path), delete=True)
    assert api.deleted == []


def test_nothing_to_archive(tmp_path):
    api = FakeApi(make_rows(3, day='2026-11-16'))
    assert arc.run(api, '2026-11-15T00:00:00Z', 'b', str(tmp_path), delete=True) == {'rows': 0}
    assert api.objects == {}


def test_rerun_with_delete_reuses_identical_stored_object(tmp_path):
    api = FakeApi(make_rows(50))
    arc.run(api, '2026-11-15T00:00:00Z', 'b', str(tmp_path), delete=False)
    stored = dict(api.objects)
    m = arc.run(api, '2026-11-15T00:00:00Z', 'b', str(tmp_path), delete=True)
    assert api.objects == stored            # nothing overwritten
    assert m['deleted'] == 50 and len(api.deleted) == 50


def test_rerun_refuses_delete_if_rows_changed_since_stored(tmp_path):
    api = FakeApi(make_rows(50))
    arc.run(api, '2026-11-15T00:00:00Z', 'b', str(tmp_path), delete=False)
    api.rows[3]['raw_response'] = 'changed after the first archive'
    with pytest.raises(arc.ArchiveError):
        arc.run(api, '2026-11-15T00:00:00Z', 'b', str(tmp_path), delete=True)
    assert api.deleted == []
