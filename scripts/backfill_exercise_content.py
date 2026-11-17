#!/usr/bin/env python3
"""Export, verify, repair and archive exercise content files (ADR-049, TASK-1023).

ADR-049 moves exercise ``content`` out of ``exercises.content`` into one immutable
JSON file per sense and version in the private Storage bucket ``exercise-content``
(``{lang}/{sense_id}.v{content_version}.json``, written with
``store.encode_sense_file``). Every row written before the move carries
``content_version`` 0 (the column default), so this script exports that content
as the version-0 files; rows written later by ``store.write_sense`` in ``dual``
mode already have their file. It reads the database and writes files; it never
changes ``exercises`` except through ``store.write_sense`` in ``--repair``.

Needs the Phase-1 migrations (``exercise_content_live_versions``,
``content_version``) and, before the export, ``EXERCISE_CONTENT_WRITE=dual`` in
every environment that writes exercises (ADR-049 section 10).

Modes (one per run)
-------------------
export (default)
    Senses come from one ``rpc('exercise_content_live_versions')`` per language
    and are read in batches of ``--batch-senses`` (every row, active or not,
    ordered by id, paged past PostgREST's 1,000-row cap). A sense whose rows are
    all at version 0 gets ``store.content_path(lang, sense, 0)`` written with
    ``store.backend().put`` on ``--concurrency`` threads. A v0 file that already
    exists is never overwritten; it is verified instead. A sense at a later
    version is verified only. Senses that end clean are added to the state file
    after each batch, and a re-run skips them.
--verify
    No content writes and no state file. Every row of every sense in scope must satisfy
    canonical(DB content) == canonical(file[(sense, row content_version)][id]).
    Mismatch kinds: ``missing_file`` (one per sense and version; ``reason`` is
    ``not_found`` or ``corrupt``), ``missing_exercise`` and ``content_diff`` (one
    per row), ``mixed_versions`` (one per sense whose rows disagree).
    A clean full run (``--language all``, no ``--senses`` / ``--limit`` /
    ``--dry-run``, exit 0) then writes one marker object,
    ``_archive/verify-ok/{YYYYMMDDTHHMMSSZ}.json``. Step 3a of
    migrations/exercise_content_drop_column.sql refuses to run without one
    from the last 24 hours. A failed marker write is an error (exit 1).
--verify --repair
    After each batch every mismatched sense is read again and, if it still
    mismatches, rewritten with ``store.write_sense(db, sense, lang,
    update_contents={id: DB content of every row of the sense})``: one new
    version and file per sense. Refused (exit 2) unless
    ``store.write_mode() == 'dual'``.
--archive-all TAG / --archive-sense-less / --archive-semdisc (need --language all)
    The pre-cut-over archives under ``_archive/`` (never swept), written data
    objects first and ``manifest.json`` last, never overwritten (an existing
    object with identical bytes counts as already archived; different bytes are
    an error). Gzip objects are deterministic (mtime 0) and split into parts of at
    most ``--archive-max-bytes`` (default 1 MiB, the bucket's file size limit):
    ``<stem>.jsonl.gz`` when one part is enough, else ``<stem>.part-0001.jsonl.gz``,
    ``...part-0002...``; the manifest lists every object with rows, bytes and
    sha256.

    * ``--archive-all TAG``: ``_archive/exercises-content-{TAG}/{lang}.jsonl.gz``
      for zh, ja and en, one line per row (id, word_sense_id, language_id,
      exercise_type, is_active, content_version, content), every row of the
      language including the rows without a sense, checked against an exact row
      count before anything is written.
    * ``--archive-sense-less``: every row with ``word_sense_id IS NULL`` (all
      columns, all languages) to ``_archive/exercises-no-sense-{YYYYMMDD}.json``.
    * ``--archive-semdisc`` (owner decision 2026-11-17): every row of
      ``backup_semdisc_content_20261115`` and ``semdisc_rewrite_work`` to
      ``_archive/semdisc-20261115/{table}.jsonl.gz``, the definition of
      ``public.apply_semdisc_notes(jsonb)`` to ``.../apply_semdisc_notes.sql`` and
      a ``manifest.json``. The definition comes from ``--semdisc-function-file``
      (exported by the operator, e.g. the output of ``select
      pg_get_functiondef('public.apply_semdisc_notes(jsonb)'::regprocedure)``) or
      from a read-only RPC named with ``--semdisc-function-rpc`` that returns that
      text; the script itself never needs SQL-editor access.

Exit codes: 0 clean; 1 mismatches left unrepaired or errors (see the report's
``anomalies`` with ``severity: error``); 2 refused (bad arguments, ``--repair``
without ``dual`` writes, missing Storage credentials, unreadable state file).

Usage:
    python scripts/backfill_exercise_content.py --language en --dry-run
    python scripts/backfill_exercise_content.py --language zh
    python scripts/backfill_exercise_content.py --language all --verify
    python scripts/backfill_exercise_content.py --language zh --verify --repair
    python scripts/backfill_exercise_content.py --language all --archive-all 20261201 \\
        --archive-sense-less
    python scripts/backfill_exercise_content.py --language all --archive-semdisc \\
        --semdisc-function-file apply_semdisc_notes.sql
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import re
import sys
import zlib
from collections.abc import Callable, Iterable, Iterator, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

try:
    from _common import LOG_FORMAT, admin_db, bootstrap
except ImportError:  # imported as scripts.backfill_exercise_content (tests)
    from scripts._common import LOG_FORMAT, admin_db, bootstrap

ROOT = bootstrap(log_level=None)

from config import Config
from services.exercise_content import store
from services.pagination import fetch_all

logger = logging.getLogger('scripts.backfill_exercise_content')

LANGUAGE_IDS = {code: language_id for language_id, code in store.LANGUAGE_CODES.items()}
LANGUAGE_ORDER = ('en', 'ja', 'zh')          # smallest first, as in TASK-1027
LIVE_VERSIONS_RPC = 'exercise_content_live_versions'
ROW_COLUMNS = 'id, word_sense_id, language_id, exercise_type, is_active, content_version, content'
ARCHIVE_FIELDS = ('id', 'word_sense_id', 'language_id', 'exercise_type', 'is_active',
                  'content_version', 'content')
DEFAULT_DIR = os.path.join(ROOT, 'data', 'exercise_content_backfill')
MAX_BATCH_SENSES = 200
DEFAULT_ARCHIVE_MAX_BYTES = 1_048_576        # file_size_limit of the exercise-content bucket
MIN_ARCHIVE_MAX_BYTES = 65_536
ARCHIVE_ROOT = '_archive'
SEMDISC_TAG = 'semdisc-20261115'
VERIFY_MARKER_FOLDER = f'{ARCHIVE_ROOT}/verify-ok'
SEMDISC_TABLES = ('backup_semdisc_content_20261115', 'semdisc_rewrite_work')
SEMDISC_FUNCTION = 'public.apply_semdisc_notes(jsonb)'
SEMDISC_FUNCTION_NAME = 'apply_semdisc_notes'
SEMDISC_FUNCTION_FILE = 'apply_semdisc_notes.sql'
STATE_FORMAT = 1
MANIFEST_FORMAT = 1

EXIT_OK = 0
EXIT_FINDINGS = 1
EXIT_REFUSED = 2

_TAG_RE = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$')
_IDENT_RE = re.compile(r'^[a-z_][a-z0-9_]{0,62}$')
_UNSET = object()


class Refusal(Exception):
    """A precondition failed before any work was done (exit 2)."""


class ArchiveError(Exception):
    """An archive could not be built or written safely; nothing more is written for it."""


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------

def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _as_int(value: Any) -> int | None:
    if _is_int(value):
        return value
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    return None


def _chunks(values: Sequence, size: int) -> Iterator[list]:
    for start in range(0, len(values), size):
        yield list(values[start:start + size])


def _iso(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')


def _stamp(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).strftime('%Y%m%dT%H%M%SZ')


def _error_text(exc: BaseException) -> str:
    text = str(exc).strip()
    return f'{type(exc).__name__}: {text}' if text else type(exc).__name__


def _short_hash(text: str) -> str:
    return hashlib.sha256(text.encode('utf-8')).hexdigest()[:16]


def _json_line(doc: dict) -> bytes:
    return (json.dumps(doc, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
            + '\n').encode('utf-8')


def _json_doc(doc: dict) -> bytes:
    return (json.dumps(doc, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode('utf-8')


def _entry(kind: str, language: str | None, **fields: Any) -> dict:
    out: dict[str, Any] = {'kind': kind}
    if language is not None:
        out['language'] = language
    out.update(fields)
    return out


def _anomaly(kind: str, severity: str, language: str | None, **fields: Any) -> dict:
    out = _entry(kind, language, **fields)
    out['severity'] = severity
    return out


def default_state_path(language: str) -> str:
    return os.path.join(DEFAULT_DIR, f'state-{language}.json')


def default_report_path(language: str, moment: datetime) -> str:
    return os.path.join(DEFAULT_DIR, f'report-{language}-{_stamp(moment)}.json')


# ---------------------------------------------------------------------------
# Database reads
# ---------------------------------------------------------------------------

def live_versions(db, language_id: int) -> dict[int, list[int]]:
    """``{sense_id: [version, ...]}`` from ``exercise_content_live_versions`` (ADR-049 §8)."""
    data = db.rpc(LIVE_VERSIONS_RPC, {'p_language_id': language_id}).execute().data
    if data is None:
        return {}
    if isinstance(data, str):
        data = json.loads(data)
    if not isinstance(data, dict):
        raise ValueError(f'{LIVE_VERSIONS_RPC} returned {type(data).__name__}, expected an object')
    out: dict[int, list[int]] = {}
    for key, versions in data.items():
        sense_id = _as_int(key)
        if sense_id is None or not isinstance(versions, list) or not all(
                _is_int(v) and v >= 0 for v in versions):
            raise ValueError(f'{LIVE_VERSIONS_RPC} returned a bad entry {key!r}: {versions!r}')
        out[sense_id] = sorted(set(versions))
    return out


def fetch_sense_rows(db, sense_ids: Sequence[int]) -> list[dict]:
    """Every row of these senses (any language, active or not), ordered by id."""
    ids = list(sense_ids)
    return fetch_all(lambda: db.table('exercises').select(ROW_COLUMNS)
                     .in_('word_sense_id', ids).order('id'))


def _group_by_sense(rows: Iterable[dict]) -> dict[int, list[dict]]:
    grouped: dict[int, list[dict]] = {}
    for row in rows:
        sense_id = _as_int(row.get('word_sense_id'))
        if sense_id is not None:
            grouped.setdefault(sense_id, []).append(row)
    return grouped


def _exact_count(query) -> int | None:
    count = getattr(query.limit(1).execute(), 'count', None)
    return count if _is_int(count) else None


# ---------------------------------------------------------------------------
# State file (export mode only)
# ---------------------------------------------------------------------------

class StateFile:
    """Completed sense ids per language, saved after each batch (atomic replace)."""

    def __init__(self, path: str):
        self.path = path
        self.completed: dict[str, set[int]] = {}
        if not os.path.exists(path):
            return
        try:
            with open(path, encoding='utf-8') as handle:
                doc = json.load(handle)
        except (OSError, ValueError) as exc:
            raise Refusal(f'state file {path} is unreadable ({_error_text(exc)}); '
                          'fix it or delete it to start over') from exc
        completed = doc.get('completed') if isinstance(doc, dict) else None
        if not isinstance(doc, dict) or doc.get('format') != STATE_FORMAT or not isinstance(
                completed, dict):
            raise Refusal(f'state file {path} is not a format-{STATE_FORMAT} backfill state file')
        for language, ids in completed.items():
            if language not in LANGUAGE_IDS or not isinstance(ids, list) or not all(
                    _is_int(i) for i in ids):
                raise Refusal(f'state file {path} has a bad entry for {language!r}')
            self.completed[language] = set(ids)

    def done(self, language: str) -> set[int]:
        return self.completed.get(language, set())

    def add(self, language: str, sense_ids: Iterable[int]) -> None:
        self.completed.setdefault(language, set()).update(sense_ids)

    def save(self, moment: datetime) -> None:
        directory = os.path.dirname(os.path.abspath(self.path))
        os.makedirs(directory, exist_ok=True)
        doc = {'format': STATE_FORMAT, 'updated_at': _iso(moment),
               'completed': {lang: sorted(ids) for lang, ids in sorted(self.completed.items())}}
        tmp = f'{self.path}.tmp'
        with open(tmp, 'w', encoding='utf-8') as handle:
            json.dump(doc, handle)
        os.replace(tmp, self.path)


# ---------------------------------------------------------------------------
# Run context and report
# ---------------------------------------------------------------------------

@dataclass
class Context:
    args: argparse.Namespace
    mode: str                                   # export | verify | repair | archive
    db: Any
    backend: Any
    now: Callable[[], datetime]
    languages: tuple[str, ...]
    report: dict
    pool: ThreadPoolExecutor | None = None
    states: dict[str, StateFile] = field(default_factory=dict)
    resolved: set[tuple[str, int]] = field(default_factory=set)
    semdisc_sql: bytes | None = None

    @property
    def dry_run(self) -> bool:
        return bool(self.args.dry_run)


_COUNTERS = ('senses', 'rows', 'files_written', 'would_write', 'files_verified',
             'skipped_from_state')


def _new_report(args: argparse.Namespace, mode: str, started: datetime) -> dict:
    report: dict[str, Any] = {'language': args.language, 'mode': mode,
                              'dry_run': bool(args.dry_run)}
    report.update({name: 0 for name in _COUNTERS})
    report.update({'mismatches': [], 'anomalies': [], 'repaired': [], 'would_repair': [],
                   'archives': [], 'per_language': {}, 'started_at': _iso(started),
                   'finished_at': None, 'exit_code': None})
    return report


def _bump(ctx: Context, language: str, name: str, amount: int = 1) -> None:
    if not amount:
        return
    ctx.report[name] += amount
    per = ctx.report['per_language'].setdefault(language, {key: 0 for key in _COUNTERS})
    per[name] = per.get(name, 0) + amount


def _exit_code(ctx: Context) -> int:
    unresolved = [m for m in ctx.report['mismatches']
                  if (m.get('language'), m.get('sense_id')) not in ctx.resolved]
    errors = [a for a in ctx.report['anomalies'] if a.get('severity') == 'error']
    return EXIT_FINDINGS if unresolved or errors else EXIT_OK


def _full_verify_scope(args: argparse.Namespace) -> bool:
    return (args.language == 'all' and not args.senses and not args.limit
            and not args.dry_run)


def write_verify_marker(ctx: Context, started: datetime, finished: datetime) -> int:
    """After a clean full --verify: put ``_archive/verify-ok/<UTC>.json``.

    The cut-over (migrations/exercise_content_drop_column.sql, step 3a) aborts unless
    storage.objects holds one of these from the last 24 hours. ``_archive/`` is never swept.
    """
    stamp = finished.astimezone(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    path = f'{VERIFY_MARKER_FOLDER}/{stamp}.json'
    doc = {'format': MANIFEST_FORMAT, 'kind': 'verify-ok', 'languages': list(ctx.languages),
           'started_at': _iso(started), 'finished_at': _iso(finished),
           'senses': ctx.report['senses'], 'rows': ctx.report['rows'],
           'files_verified': ctx.report['files_verified']}
    try:
        ctx.backend.put(path, _json_doc(doc))
    except store.AlreadyExists:
        pass                                     # a second clean run in the same second
    except Exception as exc:                     # noqa: BLE001 - reported, exit 1
        ctx.report['anomalies'].append(_anomaly('verify_marker', 'error', None, path=path,
                                                error=_error_text(exc)))
        return EXIT_FINDINGS
    ctx.report['verify_marker'] = path
    return EXIT_OK


def _write_report(path: str, report: dict) -> None:
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
        handle.write('\n')


# ---------------------------------------------------------------------------
# Export / verify / repair
# ---------------------------------------------------------------------------

@dataclass
class SenseOutcome:
    sense_id: int
    rows: int = 0
    written: bool = False
    would_write: bool = False
    files_verified: int = 0
    mismatches: list[dict] = field(default_factory=list)
    anomalies: list[dict] = field(default_factory=list)

    @property
    def clean(self) -> bool:
        return not self.mismatches and not any(
            a.get('severity') == 'error' for a in self.anomalies)


def _verify_file(ctx: Context, out: SenseOutcome, language: str, language_id: int,
                 sense_id: int, version: int, rows: list[dict], data: Any = _UNSET) -> None:
    path = store.content_path(language_id, sense_id, version)
    if data is _UNSET:
        data = ctx.backend.get(path)
    if data is None:
        out.mismatches.append(_entry('missing_file', language, sense_id=sense_id,
                                     version=version, path=path, reason='not_found',
                                     exercise_ids=sorted(row['id'] for row in rows)))
        return
    try:
        exercises = store.decode_sense_file(data, sense_id=sense_id, version=version)
    except store.ContentStorageError as exc:
        out.mismatches.append(_entry('missing_file', language, sense_id=sense_id,
                                     version=version, path=path, reason='corrupt',
                                     detail=str(exc),
                                     exercise_ids=sorted(row['id'] for row in rows)))
        return
    out.files_verified += 1
    for row in rows:
        exercise_id = row['id']
        if exercise_id not in exercises:
            out.mismatches.append(_entry('missing_exercise', language, sense_id=sense_id,
                                         version=version, exercise_id=exercise_id, path=path))
            continue
        db_text = store.canonical(row.get('content'))
        file_text = store.canonical(exercises[exercise_id])
        if db_text != file_text:
            out.mismatches.append(_entry('content_diff', language, sense_id=sense_id,
                                         version=version, exercise_id=exercise_id, path=path,
                                         db_sha256=_short_hash(db_text),
                                         file_sha256=_short_hash(file_text)))


def _export_v0(ctx: Context, out: SenseOutcome, language: str, language_id: int,
               sense_id: int, rows: list[dict]) -> None:
    path = store.content_path(language_id, sense_id, 0)
    data = store.encode_sense_file(sense_id, language_id, 0,
                                   {row['id']: row['content'] for row in rows})
    if ctx.dry_run:
        existing = ctx.backend.get(path)
        if existing is None:
            out.would_write = True
        else:
            _verify_file(ctx, out, language, language_id, sense_id, 0, rows, data=existing)
        return
    try:
        ctx.backend.put(path, data)
    except store.AlreadyExists:
        _verify_file(ctx, out, language, language_id, sense_id, 0, rows)
        return
    out.written = True


def process_sense(ctx: Context, language: str, language_id: int, sense_id: int,
                  rows: list[dict], *, export: bool) -> SenseOutcome:
    """Export (an all-v0 sense, ``export=True``) or verify one sense. Never raises."""
    out = SenseOutcome(sense_id=sense_id, rows=len(rows))
    try:
        by_version: dict[int, list[dict]] = {}
        exportable = True
        for row in rows:
            exercise_id = row.get('id')
            if not isinstance(exercise_id, str) or not exercise_id:
                out.anomalies.append(_anomaly('bad_row', 'error', language, sense_id=sense_id,
                                              detail=f'row without an id: {exercise_id!r}'))
                exportable = False
                continue
            if _as_int(row.get('language_id')) != language_id:
                out.anomalies.append(_anomaly('language_mismatch', 'info', language,
                                              sense_id=sense_id, exercise_id=exercise_id,
                                              row_language_id=row.get('language_id')))
            if not isinstance(row.get('content'), dict):
                out.anomalies.append(_anomaly('bad_content', 'error', language,
                                              sense_id=sense_id, exercise_id=exercise_id,
                                              detail=f"content is {type(row.get('content')).__name__}"))
                exportable = False
            version = row.get('content_version')
            if not _is_int(version) or version < 0:
                out.anomalies.append(_anomaly('bad_version', 'error', language,
                                              sense_id=sense_id, exercise_id=exercise_id,
                                              detail=f'content_version {version!r}'))
                exportable = False
                continue
            by_version.setdefault(version, []).append(row)
        if len(by_version) > 1:
            out.mismatches.append(_entry(
                'mixed_versions', language, sense_id=sense_id, versions=sorted(by_version),
                rows_per_version={str(v): len(r) for v, r in sorted(by_version.items())}))
        if export and exportable and set(by_version) == {0}:
            _export_v0(ctx, out, language, language_id, sense_id, by_version[0])
            return out
        for version in sorted(by_version):
            _verify_file(ctx, out, language, language_id, sense_id, version, by_version[version])
    except store.ContentStorageError as exc:  # backend failure: report, keep going
        out.anomalies.append(_anomaly('storage_error', 'error', language, sense_id=sense_id,
                                      error=_error_text(exc)))
    except Exception as exc:                  # anything else: same, under its own kind
        out.anomalies.append(_anomaly('sense_failed', 'error', language, sense_id=sense_id,
                                      error=_error_text(exc)))
    return out


def _repair(ctx: Context, language: str, language_id: int, sense_ids: list[int]) -> None:
    """Rewrite each still-mismatched sense from its DB content through the store."""
    if not sense_ids:
        return
    try:
        fresh = _group_by_sense(fetch_sense_rows(ctx.db, sense_ids))
    except Exception as exc:
        for sense_id in sense_ids:
            ctx.report['anomalies'].append(_anomaly('repair_failed', 'error', language,
                                                    sense_id=sense_id, error=_error_text(exc)))
        return
    for sense_id in sense_ids:
        rows = fresh.get(sense_id)
        if not rows:
            ctx.report['anomalies'].append(_anomaly('sense_vanished', 'info', language,
                                                    sense_id=sense_id,
                                                    detail='no rows left at repair time'))
            ctx.resolved.add((language, sense_id))
            continue
        recheck = process_sense(ctx, language, language_id, sense_id, rows, export=False)
        if recheck.clean:
            ctx.report['anomalies'].append(_anomaly('repair_not_needed', 'info', language,
                                                    sense_id=sense_id,
                                                    detail='clean when read again'))
            ctx.resolved.add((language, sense_id))
            continue
        updates = {row['id']: row['content'] for row in rows
                   if isinstance(row.get('id'), str) and isinstance(row.get('content'), dict)}
        if ctx.dry_run:
            ctx.report['would_repair'].append({'language': language, 'sense_id': sense_id,
                                               'rows': len(updates)})
            continue
        try:
            # The rows were just re-read with their content_version: if anyone writes the sense
            # before this commit, the write is refused (repair_failed, exit 1; re-run --verify).
            result = store.write_sense(ctx.db, sense_id, language_id, update_contents=updates,
                                       expected_version=store.base_version(rows))
        except Exception as exc:
            ctx.report['anomalies'].append(_anomaly('repair_failed', 'error', language,
                                                    sense_id=sense_id, error=_error_text(exc)))
            continue
        ctx.report['repaired'].append({'language': language, 'sense_id': sense_id,
                                       'version': result.version,
                                       'updated': len(result.updated_ids),
                                       'attempts': result.attempts})
        ctx.resolved.add((language, sense_id))


def _state_for(ctx: Context, language: str) -> StateFile:
    path = ctx.args.state_file or default_state_path(language)
    if path not in ctx.states:
        ctx.states[path] = StateFile(path)
    return ctx.states[path]


def run_language(ctx: Context, language: str) -> None:
    language_id = LANGUAGE_IDS[language]
    args = ctx.args
    try:
        live = live_versions(ctx.db, language_id)
    except Exception as exc:
        ctx.report['anomalies'].append(_anomaly('live_versions_failed', 'error', language,
                                                error=_error_text(exc)))
        return
    senses = sorted(live)
    if args.senses:
        wanted = set(args.senses)
        for sense_id in sorted(wanted - set(senses)):
            ctx.report['anomalies'].append(_anomaly(
                'sense_not_found', 'info', language, sense_id=sense_id,
                detail='no exercise row with this sense in this language'))
        senses = [s for s in senses if s in wanted]
    state = _state_for(ctx, language) if ctx.mode == 'export' else None
    if state is not None:
        done = state.done(language)
        skipped = sum(1 for s in senses if s in done)
        senses = [s for s in senses if s not in done]
        _bump(ctx, language, 'skipped_from_state', skipped)
    if args.limit:
        senses = senses[:args.limit]

    batches = list(_chunks(senses, args.batch_senses))
    logger.info('%s %s: %d sense(s) in %d batch(es)%s', ctx.mode, language, len(senses),
                len(batches), ' (dry run)' if ctx.dry_run else '')
    export = ctx.mode == 'export'
    for index, batch in enumerate(batches, 1):
        try:
            rows = fetch_sense_rows(ctx.db, batch)
        except Exception as exc:
            ctx.report['anomalies'].append(_anomaly('batch_read_failed', 'error', language,
                                                    first_sense=batch[0], last_sense=batch[-1],
                                                    error=_error_text(exc)))
            continue
        grouped = _group_by_sense(rows)
        for sense_id in batch:
            if sense_id not in grouped:
                ctx.report['anomalies'].append(_anomaly('sense_vanished', 'info', language,
                                                        sense_id=sense_id,
                                                        detail='listed live, no rows read'))
        work = [(sense_id, grouped[sense_id]) for sense_id in batch if sense_id in grouped]
        outcomes = list(ctx.pool.map(
            lambda item: process_sense(ctx, language, language_id, item[0], item[1],
                                       export=export), work))
        batch_mismatches = 0
        for outcome in outcomes:
            _bump(ctx, language, 'senses')
            _bump(ctx, language, 'rows', outcome.rows)
            _bump(ctx, language, 'files_written', int(outcome.written))
            _bump(ctx, language, 'would_write', int(outcome.would_write))
            _bump(ctx, language, 'files_verified', outcome.files_verified)
            ctx.report['mismatches'].extend(outcome.mismatches)
            ctx.report['anomalies'].extend(outcome.anomalies)
            batch_mismatches += len(outcome.mismatches)
        if ctx.mode == 'repair':
            _repair(ctx, language, language_id,
                    [o.sense_id for o in outcomes if o.mismatches])
        if state is not None and not ctx.dry_run:
            state.add(language, [o.sense_id for o in outcomes if o.clean])
            state.save(ctx.now())
        logger.info('%s %s batch %d/%d: senses=%d rows=%d written=%d would_write=%d '
                    'verified=%d mismatches=%d', ctx.mode, language, index, len(batches),
                    len(outcomes), sum(o.rows for o in outcomes),
                    sum(o.written for o in outcomes), sum(o.would_write for o in outcomes),
                    sum(o.files_verified for o in outcomes), batch_mismatches)


# ---------------------------------------------------------------------------
# Archives
# ---------------------------------------------------------------------------

# zlib with a gzip wrapper (wbits 31): the header carries mtime 0 and no file name, so
# the same lines always give the same bytes (a re-run can compare an existing object).
_GZIP_WBITS = 31
# The compressor holds back up to one deflate block (about 24 KB measured on zh-like
# JSON), so a part is closed this far below the limit; _fit() re-splits the rare part
# that still ends up over it.
_GZIP_MARGIN_MAX = 64 * 1024


def _compressor():
    return zlib.compressobj(9, zlib.DEFLATED, _GZIP_WBITS)


def _gzip(lines: Sequence[bytes]) -> bytes:
    compressor = _compressor()
    return b''.join([compressor.compress(line) for line in lines] + [compressor.flush()])


def _fit(lines: list[bytes], max_bytes: int) -> list[tuple[bytes, int]]:
    data = _gzip(lines)
    if len(data) <= max_bytes:
        return [(data, len(lines))]
    if len(lines) <= 1:
        raise ArchiveError(f'one archive line compresses to {len(data)} bytes, over the '
                           f'{max_bytes}-byte object limit')
    middle = len(lines) // 2
    return _fit(lines[:middle], max_bytes) + _fit(lines[middle:], max_bytes)


class GzipParts:
    """JSON lines split into deterministic gzip objects of at most ``max_bytes`` each."""

    def __init__(self, max_bytes: int):
        self.max_bytes = max_bytes
        self.margin = min(_GZIP_MARGIN_MAX, max_bytes // 2)
        self.parts: list[tuple[bytes, int]] = []
        self.rows = 0
        self._compressor = None
        self._chunks: list[bytes] = []
        self._size = 0
        self._lines: list[bytes] = []

    def _open(self) -> None:
        self._compressor = _compressor()
        self._chunks, self._size, self._lines = [], 0, []

    def _close(self) -> None:
        self._chunks.append(self._compressor.flush())
        data = b''.join(self._chunks)
        if len(data) <= self.max_bytes:
            self.parts.append((data, len(self._lines)))
        else:
            self.parts.extend(_fit(self._lines, self.max_bytes))
        self._compressor = None
        self._chunks, self._size, self._lines = [], 0, []

    def add(self, line: bytes) -> None:
        if (self._compressor is not None and self._lines
                and self._size + len(line) + self.margin > self.max_bytes):
            self._close()
        if self._compressor is None:
            self._open()
        chunk = self._compressor.compress(line)
        self._chunks.append(chunk)
        self._size += len(chunk)
        self._lines.append(line)
        self.rows += 1

    def finish(self) -> list[tuple[bytes, int]]:
        if self._compressor is None and not self.parts:
            self._open()                       # an empty archive is one empty gzip object
        if self._compressor is not None:
            self._close()
        return self.parts


def _part_paths(stem: str, count: int) -> list[str]:
    if count == 1:
        return [f'{stem}.jsonl.gz']
    return [f'{stem}.part-{index:04d}.jsonl.gz' for index in range(1, count + 1)]


@dataclass
class ArchiveObject:
    path: str
    data: bytes
    meta: dict

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.data).hexdigest()

    def manifest_entry(self) -> dict:
        return {'path': self.path, 'bytes': len(self.data), 'sha256': self.sha256, **self.meta}


def _gzip_objects(stem: str, parts: GzipParts, meta: dict) -> list[ArchiveObject]:
    blobs = parts.finish()
    paths = _part_paths(stem, len(blobs))
    return [ArchiveObject(path, data, {**meta, 'part': index, 'parts': len(blobs), 'rows': rows})
            for index, (path, (data, rows)) in enumerate(zip(paths, blobs), 1)]


def _put_objects(ctx: Context, kind: str, objects: list[ArchiveObject]) -> None:
    """Data objects first, the last object (the manifest) last; never overwrites."""
    for obj in objects:
        entry = {'kind': kind, 'path': obj.path, 'bytes': len(obj.data), 'sha256': obj.sha256}
        if 'rows' in obj.meta:
            entry['rows'] = obj.meta['rows']
        if ctx.dry_run:
            entry['status'] = 'would_write'
            ctx.report['archives'].append(entry)
            continue
        try:
            ctx.backend.put(obj.path, obj.data)
            entry['status'] = 'written'
            ctx.report['files_written'] += 1
        except store.AlreadyExists:
            existing = ctx.backend.get(obj.path)
            if existing != obj.data:
                raise ArchiveError(f'{obj.path} already exists with different content; '
                                   'archives are never overwritten (use a new TAG or '
                                   'inspect the existing object)') from None
            entry['status'] = 'identical'
            ctx.report['files_verified'] += 1
        ctx.report['archives'].append(entry)


def _archive_line(row: dict) -> bytes:
    return _json_line({name: row.get(name) for name in ARCHIVE_FIELDS})


def archive_all(ctx: Context, tag: str) -> None:
    folder = f'{ARCHIVE_ROOT}/exercises-content-{tag}'
    objects: list[ArchiveObject] = []
    languages: dict[str, dict] = {}
    for language in ctx.languages:
        language_id = LANGUAGE_IDS[language]
        parts = GzipParts(ctx.args.archive_max_bytes)
        senses = sorted(live_versions(ctx.db, language_id))
        with_sense = 0
        for batch in _chunks(senses, ctx.args.batch_senses):
            rows = [row for row in fetch_sense_rows(ctx.db, batch)
                    if _as_int(row.get('language_id')) == language_id]
            rows.sort(key=lambda row: (_as_int(row.get('word_sense_id')), str(row.get('id'))))
            for row in rows:
                parts.add(_archive_line(row))
            with_sense += len(rows)
        sense_less = fetch_all(lambda: ctx.db.table('exercises').select(ROW_COLUMNS)
                               .is_('word_sense_id', 'null').eq('language_id', language_id)
                               .order('id'))
        for row in sense_less:
            parts.add(_archive_line(row))
        expected = _exact_count(ctx.db.table('exercises').select('id', count='exact')
                                .eq('language_id', language_id))
        if expected is None:
            ctx.report['anomalies'].append(_anomaly(
                'count_unavailable', 'info', language,
                detail='no exact row count returned; archive not cross-checked'))
        elif expected != parts.rows:
            raise ArchiveError(f'{language}: archived {parts.rows} rows but the table has '
                               f'{expected} (rows changed during the run?); nothing written')
        language_objects = _gzip_objects(f'{folder}/{language}', parts,
                                         {'language': language, 'language_id': language_id})
        objects.extend(language_objects)
        languages[language] = {'rows': parts.rows, 'rows_with_sense': with_sense,
                               'rows_without_sense': len(sense_less), 'senses': len(senses),
                               'objects': len(language_objects)}
        _bump(ctx, language, 'senses', len(senses))
        _bump(ctx, language, 'rows', parts.rows)
    manifest = {'format': MANIFEST_FORMAT, 'kind': 'exercises-content', 'tag': tag,
                'fields': list(ARCHIVE_FIELDS), 'compression': 'gzip', 'encoding': 'jsonl',
                'languages': languages,
                'total_rows': sum(info['rows'] for info in languages.values()),
                'objects': [obj.manifest_entry() for obj in objects]}
    objects.append(ArchiveObject(f'{folder}/manifest.json', _json_doc(manifest), {}))
    _put_objects(ctx, 'archive_all', objects)


def archive_sense_less(ctx: Context) -> None:
    date = ctx.now().astimezone(timezone.utc).strftime('%Y%m%d')
    path = f'{ARCHIVE_ROOT}/exercises-no-sense-{date}.json'
    rows = fetch_all(lambda: ctx.db.table('exercises').select('*')
                     .is_('word_sense_id', 'null').order('id'))
    expected = _exact_count(ctx.db.table('exercises').select('id', count='exact')
                            .is_('word_sense_id', 'null'))
    if expected is not None and expected != len(rows):
        raise ArchiveError(f'read {len(rows)} sense-less rows but the table has {expected}; '
                           'nothing written')
    doc = {'format': MANIFEST_FORMAT, 'kind': 'exercises-no-sense', 'date': date,
           'rows': rows}
    data = _json_doc(doc)
    if len(data) > ctx.args.archive_max_bytes:
        raise ArchiveError(f'{path} would be {len(data)} bytes, over the '
                           f'{ctx.args.archive_max_bytes}-byte object limit')
    ctx.report['rows'] += len(rows)
    _put_objects(ctx, 'archive_sense_less', [ArchiveObject(path, data, {'rows': len(rows)})])


def _freeze(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False)


def _read_semdisc_table(ctx: Context, table: str) -> tuple[list[dict], list[str]]:
    order_by = ctx.args.semdisc_order_map.get(table)
    if order_by is None:
        first = ctx.db.table(table).select('*').limit(1).execute().data or []
        if not first:
            order_by = []
        else:
            order_by = next(([column] for column in ('id', 'exercise_id') if column in first[0]),
                            None)
            if order_by is None:
                raise ArchiveError(f'{table} has no id or exercise_id column '
                                   f'(columns: {sorted(first[0])}); pass '
                                   f'--semdisc-order {table}=COLUMN[,COLUMN]')

    def make_query():
        query = ctx.db.table(table).select('*')
        for column in order_by:
            query = query.order(column)
        return query

    rows = fetch_all(make_query) if order_by else []
    if order_by:
        missing = [column for column in order_by if rows and column not in rows[0]]
        if missing:
            raise ArchiveError(f'{table} has no column(s) {missing}')
        keys = [tuple(_freeze(row.get(column)) for column in order_by) for row in rows]
        if len(set(keys)) != len(keys):
            raise ArchiveError(f'{table}: {order_by} does not identify rows uniquely, so paging '
                               f'could skip rows; pass --semdisc-order {table}=COL1,COL2')
    expected = _exact_count(ctx.db.table(table).select('*', count='exact'))
    if expected is not None and expected != len(rows):
        raise ArchiveError(f'{table}: read {len(rows)} rows but the table has {expected}')
    return rows, order_by


def _semdisc_function_text(ctx: Context) -> bytes:
    if ctx.semdisc_sql is not None:
        return ctx.semdisc_sql
    name = ctx.args.semdisc_function_rpc
    data = ctx.db.rpc(name, {}).execute().data
    if isinstance(data, list) and len(data) == 1:
        data = data[0]
    if isinstance(data, dict) and len(data) == 1:
        data = next(iter(data.values()))
    if not isinstance(data, str):
        raise ArchiveError(f'rpc {name} returned {type(data).__name__}, expected the function '
                           'definition as text')
    return _check_function_text(data, f'rpc {name}', ArchiveError)


def _check_function_text(text: str, source: str, error: type[Exception]) -> bytes:
    if not text.strip() or SEMDISC_FUNCTION_NAME not in text.lower():
        raise error(f'{source} does not look like the definition of {SEMDISC_FUNCTION} '
                    f'(no "{SEMDISC_FUNCTION_NAME}" in it)')
    return text.encode('utf-8')


def archive_semdisc(ctx: Context) -> None:
    folder = f'{ARCHIVE_ROOT}/{SEMDISC_TAG}'
    objects: list[ArchiveObject] = []
    tables: dict[str, dict] = {}
    for table in SEMDISC_TABLES:
        rows, order_by = _read_semdisc_table(ctx, table)
        parts = GzipParts(ctx.args.archive_max_bytes)
        for row in rows:
            parts.add(_json_line(row))
        table_objects = _gzip_objects(f'{folder}/{table}', parts,
                                      {'table': table, 'order_by': order_by})
        objects.extend(table_objects)
        tables[table] = {'rows': len(rows), 'objects': len(table_objects), 'order_by': order_by}
        ctx.report['rows'] += len(rows)
    function_sql = _semdisc_function_text(ctx)
    objects.append(ArchiveObject(f'{folder}/{SEMDISC_FUNCTION_FILE}', function_sql,
                                 {'function': SEMDISC_FUNCTION}))
    manifest = {'format': MANIFEST_FORMAT, 'kind': SEMDISC_TAG, 'compression': 'gzip',
                'encoding': 'jsonl', 'tables': tables, 'function': SEMDISC_FUNCTION,
                'objects': [obj.manifest_entry() for obj in objects]}
    objects.append(ArchiveObject(f'{folder}/manifest.json', _json_doc(manifest), {}))
    _put_objects(ctx, 'archive_semdisc', objects)


def run_archives(ctx: Context) -> None:
    jobs: list[tuple[str, Callable[[], None]]] = []
    if ctx.args.archive_all:
        jobs.append(('archive_all', lambda: archive_all(ctx, ctx.args.archive_all)))
    if ctx.args.archive_sense_less:
        jobs.append(('archive_sense_less', lambda: archive_sense_less(ctx)))
    if ctx.args.archive_semdisc:
        jobs.append(('archive_semdisc', lambda: archive_semdisc(ctx)))
    for kind, job in jobs:
        try:
            job()
        except Exception as exc:
            logger.error('%s failed: %s', kind, _error_text(exc))
            ctx.report['anomalies'].append(_anomaly(f'{kind}_failed', 'error', None,
                                                    error=_error_text(exc)))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _sense_list(text: str) -> list[int]:
    ids: list[int] = []
    for part in text.split(','):
        part = part.strip()
        if not part:
            continue
        if not part.isdigit() or int(part) <= 0:
            raise argparse.ArgumentTypeError(f'{part!r} is not a positive sense id')
        ids.append(int(part))
    if not ids:
        raise argparse.ArgumentTypeError('no sense ids given')
    return sorted(set(ids))


def _positive_int(text: str) -> int:
    try:
        value = int(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f'{text!r} is not an integer') from None
    if value < 1:
        raise argparse.ArgumentTypeError(f'{text!r} must be >= 1')
    return value


def _tag(text: str) -> str:
    if not _TAG_RE.match(text):
        raise argparse.ArgumentTypeError(
            f'{text!r}: use letters, digits, dot, dash or underscore (e.g. 20261201)')
    return text


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog='backfill_exercise_content.py',
        description='Export exercises.content as version-0 Storage files, verify every row '
                    'against its file, repair through the store, and write the pre-cut-over '
                    'archives (ADR-049, TASK-1023).',
        epilog='Exit codes: 0 clean; 1 mismatches left or errors (see the report); '
               '2 refused. See the module docstring for details.')
    parser.add_argument('--language', required=True, choices=('zh', 'ja', 'en', 'all'))
    parser.add_argument('--senses', type=_sense_list, metavar='1,2,3',
                        help='only these sense ids (default: every sense of the language)')
    parser.add_argument('--limit', type=_positive_int, metavar='N',
                        help='at most N senses per language (after skipping the state file)')
    parser.add_argument('--dry-run', action='store_true',
                        help='read only: no files, no state, no repairs (the report is written)')
    parser.add_argument('--verify', action='store_true',
                        help='check every row against its file; no writes')
    parser.add_argument('--repair', action='store_true',
                        help='with --verify: rewrite mismatched senses through store.write_sense '
                             '(needs EXERCISE_CONTENT_WRITE=dual)')
    parser.add_argument('--archive-all', metavar='TAG', type=_tag,
                        help='archive every row of every language to '
                             '_archive/exercises-content-TAG/ (needs --language all)')
    parser.add_argument('--archive-sense-less', action='store_true',
                        help='archive the rows without a sense to '
                             '_archive/exercises-no-sense-YYYYMMDD.json (needs --language all)')
    parser.add_argument('--archive-semdisc', action='store_true',
                        help='archive backup_semdisc_content_20261115, semdisc_rewrite_work and '
                             'the apply_semdisc_notes definition to _archive/semdisc-20261115/ '
                             '(needs --language all)')
    parser.add_argument('--semdisc-function-file', metavar='PATH',
                        help='file holding pg_get_functiondef of public.apply_semdisc_notes(jsonb)')
    parser.add_argument('--semdisc-function-rpc', metavar='NAME',
                        help='read-only RPC (no arguments) returning that definition as text')
    parser.add_argument('--semdisc-order', metavar='TABLE=COL[,COL]', action='append',
                        default=[], help='order/unique key of a semdisc table '
                                         '(default: id, else exercise_id)')
    parser.add_argument('--archive-max-bytes', type=int, default=DEFAULT_ARCHIVE_MAX_BYTES,
                        metavar='N', help='largest archive object; bigger archives are split '
                                          f'into parts (default {DEFAULT_ARCHIVE_MAX_BYTES}, the '
                                          'bucket file size limit)')
    parser.add_argument('--batch-senses', type=_positive_int, default=MAX_BATCH_SENSES,
                        metavar='N', help=f'senses per read batch (1-{MAX_BATCH_SENSES})')
    parser.add_argument('--concurrency', type=_positive_int, default=8, metavar='N',
                        help='parallel uploads / file reads')
    parser.add_argument('--state-file', metavar='PATH',
                        help='export resume state (default '
                             'data/exercise_content_backfill/state-{lang}.json per language)')
    parser.add_argument('--report', metavar='PATH',
                        help='report JSON (default '
                             'data/exercise_content_backfill/report-{lang}-{UTC timestamp}.json)')
    return parser


ARCHIVE_FLAGS = ('archive_all', 'archive_sense_less', 'archive_semdisc')


def _validate(parser: argparse.ArgumentParser, args: argparse.Namespace) -> str:
    archiving = any(getattr(args, flag) for flag in ARCHIVE_FLAGS)
    if args.repair and not args.verify:
        parser.error('--repair needs --verify')
    if archiving and args.verify:
        parser.error('the --archive-* flags cannot be combined with --verify / --repair')
    if archiving and args.language != 'all':
        parser.error('the --archive-* flags need --language all (the cut-over deletes and drops '
                     'for every language)')
    if args.archive_all and (args.senses or args.limit):
        parser.error('--archive-all archives every row; --senses / --limit are not allowed')
    if args.batch_senses > MAX_BATCH_SENSES:
        parser.error(f'--batch-senses must be between 1 and {MAX_BATCH_SENSES}')
    if args.archive_max_bytes < MIN_ARCHIVE_MAX_BYTES:
        parser.error(f'--archive-max-bytes must be at least {MIN_ARCHIVE_MAX_BYTES}')
    semdisc_sources = [s for s in (args.semdisc_function_file, args.semdisc_function_rpc) if s]
    if args.archive_semdisc and len(semdisc_sources) != 1:
        parser.error('--archive-semdisc needs exactly one of --semdisc-function-file / '
                     '--semdisc-function-rpc (the definition of public.apply_semdisc_notes)')
    if not args.archive_semdisc and (semdisc_sources or args.semdisc_order):
        parser.error('--semdisc-* options need --archive-semdisc')
    if args.semdisc_function_rpc and not _IDENT_RE.match(args.semdisc_function_rpc):
        parser.error('--semdisc-function-rpc must be a plain function name')
    order_map: dict[str, list[str]] = {}
    for item in args.semdisc_order:
        table, _, columns = item.partition('=')
        cols = [c.strip() for c in columns.split(',') if c.strip()]
        if table not in SEMDISC_TABLES or not cols or not all(_IDENT_RE.match(c) for c in cols):
            parser.error(f'--semdisc-order {item!r}: expected TABLE=COL[,COL] with TABLE one of '
                         f'{", ".join(SEMDISC_TABLES)}')
        order_map[table] = cols
    args.semdisc_order_map = order_map
    if archiving:
        return 'archive'
    if args.repair:
        return 'repair'
    if args.verify:
        return 'verify'
    return 'export'


def _check_backend(backend: Any) -> None:
    if not hasattr(backend, 'base_url'):
        return                                   # a test backend (InMemoryBackend)
    key = getattr(Config, 'SUPABASE_SERVICE_ROLE_KEY', None)
    if backend.base_url is None or not (isinstance(key, str) and key.strip()):
        raise Refusal('Storage needs SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY')


def _make_context(args: argparse.Namespace, mode: str, db: Any,
                  now: Callable[[], datetime], report: dict) -> Context:
    if mode == 'repair' and store.write_mode() != 'dual':
        raise Refusal('--repair writes through store.write_sense and needs '
                      f'EXERCISE_CONTENT_WRITE=dual (it is {store.write_mode()!r})')
    if mode == 'export' and not args.dry_run and store.write_mode() != 'dual':
        logger.warning('EXERCISE_CONTENT_WRITE is not dual in this shell. Every environment '
                       'that writes exercises must run dual before the backfill (ADR-049 §10), '
                       'or rows written there are served only by the DB fallback.')
    semdisc_sql = None
    if args.archive_semdisc and args.semdisc_function_file:
        path = args.semdisc_function_file
        try:
            with open(path, encoding='utf-8') as handle:
                text = handle.read()
        except (OSError, UnicodeDecodeError) as exc:
            raise Refusal(f'--semdisc-function-file {path}: {_error_text(exc)}') from exc
        semdisc_sql = _check_function_text(text, path, Refusal)
    backend = store.backend()
    _check_backend(backend)
    languages = LANGUAGE_ORDER if args.language == 'all' else (args.language,)
    ctx = Context(args=args, mode=mode, db=None, backend=backend, now=now,
                  languages=languages, report=report, semdisc_sql=semdisc_sql)
    if mode == 'export':
        for language in languages:
            _state_for(ctx, language)            # refuses on an unreadable state file now
    ctx.db = db if db is not None else admin_db()
    return ctx


def main(argv: Sequence[str] | None = None, *, db: Any = None,
         now: Callable[[], datetime] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    mode = _validate(parser, args)
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
    for noisy in ('httpx', 'httpcore', 'hpack'):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    clock = now or (lambda: datetime.now(timezone.utc))
    started = clock()
    report = _new_report(args, mode, started)
    report_path = args.report or default_report_path(args.language, started)
    try:
        ctx = _make_context(args, mode, db, clock, report)
    except Refusal as exc:
        print(f'refused: {exc}', file=sys.stderr)
        return EXIT_REFUSED

    ctx.pool = ThreadPoolExecutor(max_workers=args.concurrency,
                                  thread_name_prefix='exc-backfill')
    try:
        if mode == 'archive':
            run_archives(ctx)
        else:
            for language in ctx.languages:
                run_language(ctx, language)
    except BaseException as exc:
        report['anomalies'].append(_anomaly('aborted', 'error', None, error=_error_text(exc)))
        report['finished_at'] = _iso(clock())
        report['exit_code'] = EXIT_FINDINGS
        _write_report(report_path, report)
        raise
    finally:
        ctx.pool.shutdown(wait=True)

    code = _exit_code(ctx)
    finished = clock()
    if code == EXIT_OK and mode == 'verify' and _full_verify_scope(args):
        code = write_verify_marker(ctx, started, finished)
    report['finished_at'] = _iso(finished)
    report['exit_code'] = code
    _write_report(report_path, report)
    errors = sum(1 for a in report['anomalies'] if a.get('severity') == 'error')
    logger.info('%s %s done: senses=%d rows=%d written=%d would_write=%d verified=%d '
                'skipped_from_state=%d mismatches=%d repaired=%d errors=%d',
                mode, args.language, report['senses'], report['rows'], report['files_written'],
                report['would_write'], report['files_verified'], report['skipped_from_state'],
                len(report['mismatches']), len(report['repaired']), errors)
    print(f'report: {report_path}')
    return code


if __name__ == '__main__':
    sys.exit(main())
