#!/usr/bin/env python3
"""Move ``llm_calls`` rows older than a cutoff into Storage, then delete them.

Why
---
``llm_calls`` keeps one row per model call with the full raw response
(``services/llm_service.py::_log_llm_call``). It is the fastest-growing log
table, and the database sits close to the Free plan's 500 MB cap. Nothing in
the app reads old rows back: the readers are reporting / smoke scripts that
read their own run's recent rows. So old rows can live in Storage, where the
2026-11-15 archive already put rows up to 2026-11-14.

Format (the same as that archive), in the private bucket ``llm-logs-archive``::

    llm_calls/llm_calls_{first}_to_{last}__cutoff_{cutoff}.jsonl.gz
    llm_calls/llm_calls_{first}_to_{last}__cutoff_{cutoff}.manifest.json

gzip JSON Lines, one PostgREST row per line, ordered by (created_at, id); the
manifest gives table, object, rows, sha256, bytes, cutoff, first / last
created_at, format and archived_at.

Stages
------
  (default)  dry run: count the rows below the cutoff; nothing written.
  --apply    export them to a local file (data/llm_calls_archive/, git-ignored),
             upload object then manifest (never overwriting: an object already
             at the path is accepted only if its bytes are identical), download
             it back and verify: same sha256, same row count, and the archived
             ids are exactly the table's ids below the cutoff.
  --delete   with --apply, after a passing verification: delete exactly the
             archived ids, then re-count (0 expected below the cutoff).

Deleting frees space inside the table; the database's size on disk only falls
after ``VACUUM (FULL) public.llm_calls`` (a brief exclusive lock), run
separately.

Usage:
  python scripts/archive_llm_calls.py                         # dry run, cutoff = today 00:00 UTC
  python scripts/archive_llm_calls.py --before 2026-11-27 --apply            # archive + verify
  python scripts/archive_llm_calls.py --before 2026-11-27 --apply --delete   # ... then delete
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Iterable, Optional

try:
    from _common import admin_db, bootstrap
except ImportError:  # imported as scripts.<name>
    from scripts._common import admin_db, bootstrap

ROOT = bootstrap(log_format='%(asctime)s %(levelname)-7s %(name)s: %(message)s')

logger = logging.getLogger('archive_llm_calls')

TABLE = 'llm_calls'
BUCKET = 'llm-logs-archive'
PREFIX = 'llm_calls'
PAGE = 1000
DELETE_CHUNK = 200
FORMAT = 'gzip JSON Lines, one PostgREST row per line, ordered by created_at, id'
LOCAL_DIR = os.path.join(ROOT, 'data', 'llm_calls_archive')


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_ts(value: str) -> datetime:
    return datetime.fromisoformat(str(value).replace('Z', '+00:00')).astimezone(timezone.utc)


def stamp(ts: datetime) -> str:
    return ts.astimezone(timezone.utc).strftime('%Y%m%dT%H%M%S')


def object_name(first: datetime, last: datetime, cutoff: datetime) -> str:
    return f'{PREFIX}/{TABLE}_{stamp(first)}_to_{stamp(last)}__cutoff_{stamp(cutoff)}.jsonl.gz'


def manifest_name(obj: str) -> str:
    return obj[:-len('.jsonl.gz')] + '.manifest.json'


# ---------------------------------------------------------------------------
# Read
# ---------------------------------------------------------------------------

def count_below(db, cutoff: datetime) -> int:
    res = (db.table(TABLE).select('id', count='exact').lt('created_at', cutoff.isoformat())
           .limit(1).execute())
    return int(res.count or 0)


def rows_below(db, cutoff: datetime, columns: str = '*') -> Iterable[dict]:
    """Every row below the cutoff, ordered by (created_at, id), a page at a time.

    Offset paging over a stable order is exact as long as no row below the
    cutoff appears or goes while it runs (``created_at`` defaults to now(), so
    new calls land above it)."""
    offset = 0
    while True:
        page = (db.table(TABLE).select(columns).lt('created_at', cutoff.isoformat())
                .order('created_at').order('id').range(offset, offset + PAGE - 1)
                .execute().data or [])
        yield from page
        if len(page) < PAGE:
            return
        offset += PAGE


def encode(rows: Iterable[dict]) -> tuple[bytes, int, list[str], Optional[str], Optional[str]]:
    """(gzip bytes, row count, ids, first created_at, last created_at). Deterministic: the
    same rows always give the same bytes (gzip mtime 0)."""
    buf = io.BytesIO()
    ids: list[str] = []
    first = last = None
    with gzip.GzipFile(fileobj=buf, mode='wb', mtime=0) as gz:
        for row in rows:
            gz.write(json.dumps(row, ensure_ascii=False, separators=(',', ':')).encode('utf-8'))
            gz.write(b'\n')
            ids.append(str(row['id']))
            first = first or row.get('created_at')
            last = row.get('created_at')
    return buf.getvalue(), len(ids), ids, first, last


def decode_ids(data: bytes) -> list[str]:
    with gzip.GzipFile(fileobj=io.BytesIO(data), mode='rb') as gz:
        return [str(json.loads(line)['id']) for line in gz if line.strip()]


# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------

def upload_once(db, path: str, data: bytes, content_type: str, say) -> str:
    """'uploaded', or 'identical' when the same bytes are already there. Raises when a
    different object is at the path (never overwritten)."""
    bucket = db.storage.from_(BUCKET)
    try:
        bucket.upload(path, data, {'content-type': content_type, 'upsert': 'false'})
        return 'uploaded'
    except Exception as exc:              # storage3 raises StorageException on a 409
        try:
            existing = bucket.download(path)
        except Exception:
            raise exc
        if hashlib.sha256(existing).hexdigest() == hashlib.sha256(data).hexdigest():
            say(f'{path} already uploaded (identical bytes)')
            return 'identical'
        raise SystemExit(f'{path} exists in {BUCKET} with different contents: not overwritten')


def verify(db, obj: str, data: bytes, ids: list[str], cutoff: datetime, say) -> bool:
    """The uploaded object is these bytes, and its ids are exactly the table's ids below
    the cutoff now."""
    got = db.storage.from_(BUCKET).download(obj)
    if hashlib.sha256(got).hexdigest() != hashlib.sha256(data).hexdigest():
        say('verify: downloaded object differs from the export')
        return False
    archived = decode_ids(got)
    if len(archived) != len(ids) or len(set(archived)) != len(archived):
        say(f'verify: {len(archived)} rows in the object, {len(ids)} exported')
        return False
    in_table = [str(r['id']) for r in rows_below(db, cutoff, 'id')]
    if set(in_table) != set(archived):
        say(f'verify: table has {len(in_table)} ids below the cutoff, object {len(archived)}; '
            f'{len(set(in_table) - set(archived))} not archived, '
            f'{len(set(archived) - set(in_table))} archived but gone')
        return False
    say(f'verify: object sha256 ok, {len(archived)} rows = the table\'s rows below the cutoff')
    return True


def delete_archived(db, ids: list[str], cutoff: datetime, say) -> int:
    """Delete exactly these ids (and only below the cutoff); the count left below it."""
    from postgrest.types import ReturnMethod
    for i in range(0, len(ids), DELETE_CHUNK):
        (db.table(TABLE).delete(returning=ReturnMethod.minimal)
         .in_('id', ids[i:i + DELETE_CHUNK]).lt('created_at', cutoff.isoformat()).execute())
        if (i // DELETE_CHUNK) % 50 == 0:
            say(f'deleted {min(i + DELETE_CHUNK, len(ids))}/{len(ids)}')
    left = count_below(db, cutoff)
    say(f'{left} rows left below the cutoff')
    return left


# ---------------------------------------------------------------------------
# Entry
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--before', default='',
                    help='archive rows created before this UTC date or timestamp '
                         '(default: today 00:00 UTC)')
    ap.add_argument('--apply', action='store_true', help='export, upload and verify')
    ap.add_argument('--delete', action='store_true',
                    help='with --apply: delete the archived rows after a passing verification')
    return ap


def cutoff_of(value: str) -> datetime:
    if not value:
        today = datetime.now(timezone.utc).date()
        return datetime(today.year, today.month, today.day, tzinfo=timezone.utc)
    ts = parse_ts(value if 'T' in value else value + 'T00:00:00+00:00')
    if ts > datetime.now(timezone.utc):
        raise SystemExit(f'--before {value} is in the future')
    return ts


def main(argv: Optional[list[str]] = None, db=None) -> int:
    args = build_parser().parse_args(argv)
    say = lambda msg: print(f'[{now_iso()}] {msg}', flush=True)  # noqa: E731
    if args.delete and not args.apply:
        raise SystemExit('--delete needs --apply (rows are deleted only after a verified archive)')
    cutoff = cutoff_of(args.before)
    db = db or admin_db()
    n = count_below(db, cutoff)
    say(f'{n} {TABLE} rows created before {cutoff.isoformat()}')
    if not args.apply or n == 0:
        if not args.apply:
            say('dry run: nothing written (add --apply)')
        return 0

    data, rows, ids, first, last = encode(rows_below(db, cutoff))
    if rows != n:
        raise SystemExit(f'exported {rows} rows but counted {n}: rows changed during export')
    obj = object_name(parse_ts(first), parse_ts(last), cutoff)
    manifest = {'table': TABLE, 'object': obj, 'rows': rows,
                'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data),
                'cutoff_created_at_lt': cutoff.strftime('%Y-%m-%dT%H:%M:%SZ'),
                'first_created_at': first, 'last_created_at': last, 'format': FORMAT,
                'archived_at': now_iso()}
    run_dir = os.path.join(LOCAL_DIR, stamp(cutoff))
    os.makedirs(run_dir, exist_ok=True)
    with open(os.path.join(run_dir, os.path.basename(obj)), 'wb') as fh:
        fh.write(data)
    say(f'exported {rows} rows, {len(data):,} bytes gzip -> {run_dir}')

    upload_once(db, obj, data, 'application/gzip', say)
    existing_manifest = None
    try:
        existing_manifest = json.loads(db.storage.from_(BUCKET).download(manifest_name(obj)))
    except Exception:
        pass
    if existing_manifest and existing_manifest.get('sha256') == manifest['sha256']:
        manifest = existing_manifest          # a resumed run: keep the first archived_at
    else:
        upload_once(db, manifest_name(obj),
                    json.dumps(manifest, indent=2).encode('utf-8'), 'application/json', say)
    with open(os.path.join(run_dir, os.path.basename(manifest_name(obj))), 'w',
              encoding='utf-8') as fh:
        json.dump(manifest, fh, indent=2)
    say(f'uploaded {BUCKET}/{obj} and its manifest')

    if not verify(db, obj, data, ids, cutoff, say):
        say('verification failed: nothing deleted')
        return 2
    if not args.delete:
        say('verified; rows kept (add --delete to remove them from the table)')
        return 0
    left = delete_archived(db, ids, cutoff, say)
    return 0 if left == 0 else 3


if __name__ == '__main__':
    sys.exit(main())
