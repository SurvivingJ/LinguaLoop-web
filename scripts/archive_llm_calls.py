#!/usr/bin/env python3
"""Move old ``llm_calls`` rows out of Postgres into a Supabase Storage bucket.

Why: ``llm_calls`` is an append-only log (one row per LLM round-trip, plus a
verdict-only row per judge call). Nothing in the app reads it; only reporting
and budget-ceiling scripts do, and those read rows from the current run. Kept
in the database it counted ~54 MB (20 MB rows + 33 MB indexes) against the
database size limit. Storage has its own, larger quota.

What a run does
  1. Counts the rows with ``created_at < --before`` (default: 00:00 UTC today).
  2. Exports exactly those rows, every column, ordered by (created_at, id), to a
     gzipped JSON Lines file (one row per line, as PostgREST returns it;
     ``prompt_hash`` comes out as a ``\\x...`` hex string).
  3. Uploads the file plus a ``.manifest.json`` (row count, sha256, time range,
     cutoff) to the private bucket ``--bucket`` (created if missing, never
     public). Uploads never overwrite an existing object.
  4. Downloads the object back and checks: same sha256, same row count, same
     set of ids as the database. Any mismatch stops the run before step 5.
  5. Only with ``--delete``: deletes exactly the exported ids, in batches, and
     checks the deleted count equals the exported count.

Deleting rows does not shrink the database file. Afterwards run, in the
Supabase SQL editor:  VACUUM (FULL, ANALYZE) public.llm_calls;

Safe to re-run: rows already archived and deleted are gone, so the next run
picks up only newer rows. If the same range was uploaded by an earlier run
(e.g. a first run without --delete), the stored object is never overwritten;
it is downloaded and must be byte-identical to a fresh export before anything
is deleted.

Reading an archive back:
    import gzip, json
    rows = [json.loads(l) for l in gzip.open('llm_calls_....jsonl.gz', 'rt')]

Usage
    SUPABASE_URL=... SUPABASE_SERVICE_ROLE_KEY=... \\
        python scripts/archive_llm_calls.py                     # export + upload + verify
    python scripts/archive_llm_calls.py --delete                # ... then delete from the DB
    python scripts/archive_llm_calls.py --before 2026-11-01T00:00:00Z --delete
"""

from __future__ import annotations

import argparse
import datetime as dt
import gzip
import hashlib
import io
import json
import os
import sys
import tempfile
from dataclasses import dataclass, field

import requests

TABLE = 'llm_calls'
DEFAULT_BUCKET = 'llm-logs-archive'
OBJECT_PREFIX = 'llm_calls'
PAGE_SIZE = 1000          # Supabase PostgREST caps responses at 1000 rows
DELETE_BATCH = 200        # ids per DELETE ... id=in.(...) request (~7.5 KB of URL)
MAX_OBJECT_BYTES = 45 * 1024 * 1024   # under the 50 MB free-plan per-file limit


class ArchiveError(RuntimeError):
    """A check failed; nothing after the failing step was done."""


class Api:
    """The few PostgREST and Storage calls this script needs."""

    def __init__(self, url: str, key: str, session: requests.Session | None = None):
        self.url = url.rstrip('/')
        self.s = session or requests.Session()
        self.s.headers.update({'apikey': key, 'Authorization': f'Bearer {key}'})

    # -- PostgREST -----------------------------------------------------------
    def count_before(self, before: str) -> int:
        r = self.s.get(f'{self.url}/rest/v1/{TABLE}',
                       params={'select': 'id', 'created_at': f'lt.{before}', 'limit': '1'},
                       headers={'Prefer': 'count=exact'}, timeout=60)
        r.raise_for_status()
        return int(r.headers['Content-Range'].split('/')[-1])

    def page_before(self, before: str, offset: int, limit: int) -> list[dict]:
        r = self.s.get(f'{self.url}/rest/v1/{TABLE}',
                       params={'select': '*', 'created_at': f'lt.{before}',
                               'order': 'created_at.asc,id.asc',
                               'offset': str(offset), 'limit': str(limit)},
                       timeout=120)
        r.raise_for_status()
        return r.json()

    def delete_ids(self, ids: list[str]) -> int:
        r = self.s.delete(f'{self.url}/rest/v1/{TABLE}',
                          params={'id': f'in.({",".join(ids)})'},
                          headers={'Prefer': 'return=minimal,count=exact'}, timeout=120)
        r.raise_for_status()
        return int(r.headers['Content-Range'].split('/')[-1])

    # -- Storage -------------------------------------------------------------
    def ensure_private_bucket(self, bucket: str) -> None:
        r = self.s.get(f'{self.url}/storage/v1/bucket/{bucket}', timeout=60)
        if r.ok:
            if r.json().get('public'):
                raise ArchiveError(f'bucket {bucket!r} exists and is PUBLIC; refusing to archive logs into it')
            return
        r = self.s.post(f'{self.url}/storage/v1/bucket',
                        json={'id': bucket, 'name': bucket, 'public': False}, timeout=60)
        if not r.ok and 'already exists' not in r.text.lower():
            raise ArchiveError(f'could not create bucket {bucket!r}: {r.status_code} {r.text[:300]}')

    def upload(self, bucket: str, path: str, data: bytes, content_type: str) -> bool:
        """Upload without overwriting. Returns False if the object already exists."""
        r = self.s.post(f'{self.url}/storage/v1/object/{bucket}/{path}', data=data,
                        headers={'Content-Type': content_type, 'x-upsert': 'false'}, timeout=300)
        if r.ok:
            return True
        if 'already exists' in r.text.lower() or 'duplicate' in r.text.lower():
            return False
        raise ArchiveError(f'upload of {path} failed: {r.status_code} {r.text[:300]}')

    def download(self, bucket: str, path: str) -> bytes:
        r = self.s.get(f'{self.url}/storage/v1/object/authenticated/{bucket}/{path}', timeout=300)
        r.raise_for_status()
        return r.content


@dataclass
class Export:
    rows: int = 0
    ids: list[str] = field(default_factory=list)
    first_created_at: str | None = None
    last_created_at: str | None = None
    gz_bytes: bytes = b''

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.gz_bytes).hexdigest()


def export_rows(api: Api, before: str, expected: int, page_size: int = PAGE_SIZE) -> Export:
    """Page through every row older than ``before`` into one gzipped JSONL blob."""
    out = Export()
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode='wb', mtime=0) as gz:
        offset = 0
        while True:
            page = api.page_before(before, offset, page_size)
            for row in page:
                gz.write(json.dumps(row, ensure_ascii=False, separators=(',', ':')).encode('utf-8'))
                gz.write(b'\n')
                out.ids.append(row['id'])
                out.first_created_at = out.first_created_at or row['created_at']
                out.last_created_at = row['created_at']
            out.rows += len(page)
            offset += len(page)
            if len(page) < page_size:
                break
            if offset and offset % 10000 == 0:
                print(f'  exported {offset:,}/{expected:,}', flush=True)
    out.gz_bytes = buf.getvalue()
    if out.rows != expected:
        raise ArchiveError(f'exported {out.rows} rows but the database counted {expected}')
    if len(set(out.ids)) != out.rows:
        raise ArchiveError('duplicate ids in the export (pagination was not stable)')
    return out


def verify_object(blob: bytes, exp: Export) -> None:
    if hashlib.sha256(blob).hexdigest() != exp.sha256:
        raise ArchiveError('downloaded object sha256 differs from the uploaded file')
    ids = [json.loads(line)['id'] for line in gzip.decompress(blob).decode('utf-8').splitlines() if line]
    if len(ids) != exp.rows or set(ids) != set(exp.ids):
        raise ArchiveError(f'downloaded object has {len(ids)} rows / a different id set; expected {exp.rows}')


def delete_exported(api: Api, ids: list[str], batch: int = DELETE_BATCH) -> int:
    deleted = 0
    for i in range(0, len(ids), batch):
        deleted += api.delete_ids(ids[i:i + batch])
        if (i // batch) % 50 == 49:
            print(f'  deleted {deleted:,}/{len(ids):,}', flush=True)
    return deleted


def default_cutoff() -> str:
    today = dt.datetime.now(dt.timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    return today.isoformat().replace('+00:00', 'Z')


def object_name(exp: Export, before: str) -> str:
    def stamp(ts: str) -> str:
        return ts[:19].replace(':', '').replace('-', '')   # 20260921T211404
    return f'{OBJECT_PREFIX}/{TABLE}_{stamp(exp.first_created_at)}_to_{stamp(exp.last_created_at)}' \
           f'__cutoff_{stamp(before)}.jsonl.gz'


def run(api: Api, before: str, bucket: str, out_dir: str, delete: bool) -> dict:
    expected = api.count_before(before)
    print(f'{expected:,} {TABLE} rows with created_at < {before}')
    if expected == 0:
        return {'rows': 0}

    exp = export_rows(api, before, expected)
    size = len(exp.gz_bytes)
    print(f'exported {exp.rows:,} rows -> {size / 1e6:.1f} MB gzipped, sha256 {exp.sha256[:16]}...')
    if size > MAX_OBJECT_BYTES:
        raise ArchiveError(f'archive is {size / 1e6:.1f} MB, over the per-file limit; pass an earlier --before')

    path = object_name(exp, before)
    os.makedirs(out_dir, exist_ok=True)
    local = os.path.join(out_dir, os.path.basename(path))
    with open(local, 'wb') as f:
        f.write(exp.gz_bytes)
    manifest = {
        'table': TABLE, 'object': path, 'rows': exp.rows, 'sha256': exp.sha256,
        'bytes': size, 'cutoff_created_at_lt': before,
        'first_created_at': exp.first_created_at, 'last_created_at': exp.last_created_at,
        'format': 'gzip JSON Lines, one PostgREST row per line, ordered by created_at, id',
        'archived_at': dt.datetime.now(dt.timezone.utc).isoformat(),
    }
    print(f'local copy: {local}')

    api.ensure_private_bucket(bucket)
    if api.upload(bucket, path, exp.gz_bytes, 'application/gzip'):
        api.upload(bucket, path.replace('.jsonl.gz', '.manifest.json'),
                   json.dumps(manifest, indent=2).encode('utf-8'), 'application/json')
        print(f'uploaded to storage: {bucket}/{path}')
    else:
        # An earlier run already stored this exact range. The gzip is
        # deterministic (mtime=0), so the check below passes only if the stored
        # object is byte-identical to what the database holds now.
        print(f'already in storage: {bucket}/{path} (checking it matches the database)')

    verify_object(api.download(bucket, path), exp)
    print('verified: stored object matches the database (sha256, row count, id set)')

    if not delete:
        print('not deleting (pass --delete to remove the archived rows from the database)')
        return manifest

    deleted = delete_exported(api, exp.ids)
    manifest['deleted'] = deleted
    if deleted != exp.rows:
        raise ArchiveError(f'deleted {deleted} rows but archived {exp.rows}; check the table by hand')
    print(f'deleted {deleted:,} archived rows from {TABLE}')
    print(f'reclaim disk now, in the SQL editor:  VACUUM (FULL, ANALYZE) public.{TABLE};')
    return manifest


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    p.add_argument('--before', default=default_cutoff(),
                   help='archive rows with created_at < this ISO timestamp (default: 00:00 UTC today)')
    p.add_argument('--bucket', default=DEFAULT_BUCKET)
    p.add_argument('--out-dir', default=os.path.join(tempfile.gettempdir(), 'llm_calls_archive'),
                   help='where the local copy of the archive is written')
    p.add_argument('--delete', action='store_true',
                   help='after a verified upload, delete the archived rows from the database')
    a = p.parse_args(argv)

    url = os.environ.get('SUPABASE_URL')
    key = os.environ.get('SUPABASE_SERVICE_ROLE_KEY')
    if not url or not key:
        print('SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set', file=sys.stderr)
        return 2
    try:
        manifest = run(Api(url, key), a.before, a.bucket, a.out_dir, a.delete)
    except ArchiveError as e:
        print(f'STOPPED: {e}', file=sys.stderr)
        return 1
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
