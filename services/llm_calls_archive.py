"""Move ``llm_calls`` rows older than a cutoff into Storage, then delete them.

Why
---
``llm_calls`` keeps one row per model call with the full raw response
(``services/llm_service.py::_log_llm_call``); it is the fastest-growing log
table and the database sits close to the Free plan's 500 MB cap. Nothing in the
app reads old rows back (the readers are reporting / smoke scripts that read
their own run's recent rows), so old rows live in Storage. Owner 2026-11-27:
"Can we move the LLM calls table data into storage?", then "set it up on a
schedule".

Format (the same as the 2026-11-15 archive), private bucket ``llm-logs-archive``::

    llm_calls/llm_calls_{first}_to_{last}__cutoff_{cutoff}.jsonl.gz
    llm_calls/llm_calls_{first}_to_{last}__cutoff_{cutoff}.manifest.json

gzip JSON Lines, one PostgREST row per line, ordered by (created_at, id); the
manifest gives table, object, rows, sha256, bytes, cutoff, first / last
created_at, format and archived_at. Restore: gunzip and insert the lines (every
column is there). If a run stopped between upload and delete, a later run
archives the same rows again: restore by id, keeping one.

``archive``: export -> upload (never overwriting: an object already at the path
is accepted only with identical bytes) -> download back and verify (sha256, row
count, and the ids are exactly the table's ids below the cutoff) -> only then,
when asked, delete exactly those ids. Used by ``scripts/archive_llm_calls.py``
and by the weekly job ``run_weekly`` (``web/scheduler.py``).

``run_weekly`` keeps the last ``Config.LLM_CALLS_ARCHIVE_KEEP_DAYS`` days in the
table. The scheduler runs in each gunicorn worker; a worker claims the week's
cutoff by creating ``llm_calls/locks/cutoff_<cutoff>.json`` (Storage refuses a
second object at a path, so one worker wins) and the other skips. A claim is
never released: if its run stopped half-way, next week's cutoff covers the rows.

Deleting frees space inside the table, which new rows then reuse; the
database's size on disk falls only after ``VACUUM (FULL) public.llm_calls``,
which cannot run through PostgREST (owner, by hand, when wanted).
"""

from __future__ import annotations

import gzip
import hashlib
import io
import json
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Callable, Iterable, Optional

logger = logging.getLogger(__name__)

TABLE = 'llm_calls'
BUCKET = 'llm-logs-archive'
PREFIX = 'llm_calls'
LOCK_PREFIX = f'{PREFIX}/locks'
PAGE = 1000
DELETE_CHUNK = 200
FORMAT = 'gzip JSON Lines, one PostgREST row per line, ordered by created_at, id'
DEFAULT_KEEP_DAYS = 3


class ArchiveError(Exception):
    """The archive could not be made or trusted; nothing was deleted."""


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


def start_of_day(ts: Optional[datetime] = None) -> datetime:
    ts = (ts or datetime.now(timezone.utc)).astimezone(timezone.utc)
    return datetime(ts.year, ts.month, ts.day, tzinfo=timezone.utc)


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

def _bucket(db):
    return db.storage.from_(BUCKET)


def _download(db, path: str) -> Optional[bytes]:
    try:
        return _bucket(db).download(path)
    except Exception:
        return None


def create_once(db, path: str, data: bytes, content_type: str) -> bool:
    """Create the object; False when one is already at the path (left untouched)."""
    try:
        _bucket(db).upload(path, data, {'content-type': content_type, 'upsert': 'false'})
        return True
    except Exception as exc:              # storage3 raises StorageException on a 409
        if _download(db, path) is None:
            raise ArchiveError(f'upload of {path} failed: {exc}') from exc
        return False


def upload_once(db, path: str, data: bytes, content_type: str) -> str:
    """'uploaded', or 'identical' when the same bytes are already there. ArchiveError
    when a different object is at the path (never overwritten)."""
    if create_once(db, path, data, content_type):
        return 'uploaded'
    existing = _download(db, path)
    if existing is not None and hashlib.sha256(existing).digest() == hashlib.sha256(data).digest():
        return 'identical'
    raise ArchiveError(f'{path} exists in {BUCKET} with different contents: not overwritten')


def verify(db, obj: str, data: bytes, ids: list[str], cutoff: datetime,
           say: Callable[[str], None]) -> bool:
    """The uploaded object is these bytes, and its ids are exactly the table's ids below
    the cutoff now."""
    got = _download(db, obj)
    if got is None or hashlib.sha256(got).digest() != hashlib.sha256(data).digest():
        say('verify: the object in Storage differs from the export')
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


def delete_archived(db, ids: list[str], cutoff: datetime, say: Callable[[str], None]) -> int:
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
# One archive
# ---------------------------------------------------------------------------

def archive(db, cutoff: datetime, *, delete: bool, say: Optional[Callable[[str], None]] = None,
            local_dir: Optional[str] = None) -> dict:
    """Archive every row below ``cutoff``; with ``delete``, then delete them.

    Returns ``{'cutoff', 'rows', 'object', 'bytes', 'verified', 'deleted', 'left'}``
    (``rows`` 0 and no object when there is nothing below the cutoff). Raises
    ArchiveError, having deleted nothing, when the export or the object cannot be
    trusted. ``local_dir``: also keep the file and manifest there (the CLI)."""
    say = say or logger.info
    out = {'cutoff': cutoff.isoformat(), 'rows': 0, 'object': None, 'bytes': 0,
           'verified': False, 'deleted': 0, 'left': None}
    n = count_below(db, cutoff)
    say(f'{n} {TABLE} rows created before {cutoff.isoformat()}')
    if n == 0:
        return out
    data, rows, ids, first, last = encode(rows_below(db, cutoff))
    if rows != n:
        raise ArchiveError(f'exported {rows} rows but counted {n}: rows changed during export')
    obj = object_name(parse_ts(first), parse_ts(last), cutoff)
    sha = hashlib.sha256(data).hexdigest()
    manifest = {'table': TABLE, 'object': obj, 'rows': rows, 'sha256': sha, 'bytes': len(data),
                'cutoff_created_at_lt': cutoff.strftime('%Y-%m-%dT%H:%M:%SZ'),
                'first_created_at': first, 'last_created_at': last, 'format': FORMAT,
                'archived_at': now_iso()}
    out.update(rows=rows, object=obj, bytes=len(data))
    say(f'exported {rows} rows, {len(data):,} bytes gzip')

    upload_once(db, obj, data, 'application/gzip')
    man_path = manifest_name(obj)
    if not create_once(db, man_path, json.dumps(manifest, indent=2).encode('utf-8'),
                       'application/json'):
        try:
            existing = json.loads(_download(db, man_path) or b'{}')
        except ValueError:
            existing = {}
        if (existing.get('object'), existing.get('sha256'), existing.get('rows')) != (obj, sha, rows):
            raise ArchiveError(f'{man_path} exists and describes another object')
        manifest = existing               # a re-run: keep the first archived_at
    say(f'uploaded {BUCKET}/{obj} and its manifest')
    if local_dir:
        os.makedirs(local_dir, exist_ok=True)
        with open(os.path.join(local_dir, os.path.basename(obj)), 'wb') as fh:
            fh.write(data)
        with open(os.path.join(local_dir, os.path.basename(man_path)), 'w', encoding='utf-8') as fh:
            json.dump(manifest, fh, indent=2)

    if not verify(db, obj, data, ids, cutoff, say):
        raise ArchiveError('verification failed: nothing deleted')
    out['verified'] = True
    if delete:
        out['left'] = delete_archived(db, ids, cutoff, say)
        out['deleted'] = len(ids)
    return out


# ---------------------------------------------------------------------------
# Weekly job (web/scheduler.py)
# ---------------------------------------------------------------------------

def keep_days() -> int:
    from config import Config
    try:
        return max(1, int(getattr(Config, 'LLM_CALLS_ARCHIVE_KEEP_DAYS', DEFAULT_KEEP_DAYS)))
    except (TypeError, ValueError):
        return DEFAULT_KEEP_DAYS


def lock_path(cutoff: datetime) -> str:
    return f'{LOCK_PREFIX}/cutoff_{stamp(cutoff)}.json'


def run_weekly(db, now: Optional[datetime] = None) -> dict:
    """Archive and delete every row older than the last ``keep_days()`` whole UTC days.
    ``{'skipped': True, 'reason'}`` when another worker has claimed this cutoff or there
    is nothing to move."""
    cutoff = start_of_day(now) - timedelta(days=keep_days())
    if db is None:
        return {'skipped': True, 'reason': 'no database client'}
    if count_below(db, cutoff) == 0:
        return {'skipped': True, 'reason': f'nothing before {cutoff.isoformat()}'}
    claim = json.dumps({'claimed_at': now_iso(), 'pid': os.getpid()}).encode('utf-8')
    if not create_once(db, lock_path(cutoff), claim, 'application/json'):
        return {'skipped': True, 'reason': f'cutoff {stamp(cutoff)} already claimed'}
    result = archive(db, cutoff, delete=True, say=lambda msg: logger.info('llm_calls archive: %s', msg))
    return {k: result[k] for k in ('cutoff', 'rows', 'object', 'bytes', 'deleted', 'left')}
