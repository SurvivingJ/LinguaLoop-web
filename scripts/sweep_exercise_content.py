#!/usr/bin/env python3
"""Delete exercise content files that no row points at (ADR-049, TASK-1024).

Exercise content lives in one immutable file per sense and version,
``{lang}/{sense_id}.v{version}.json`` in the private bucket ``exercise-content``
(ADR-049 §1-§3). Files nothing points at any more pile up: the version a later
write superseded, the file of a writer that lost a race or crashed between upload
and commit, and every file of a sense the admin wiped. Each one also costs about
0.6 KB of ``storage.objects`` in the database, so run this after every bulk edit.

Per language (``--language all`` = en, ja, zh):

1. list the language folder with ``store.backend().list('{lang}/')`` (one level:
   ``_archive/`` is never listed, and any path under it is never touched);
2. read the live set with ``rpc('exercise_content_live_versions',
   {'p_language_id': id})`` (``{sense_id: [version, ...]}``);
3. classify every file whose name matches ``^(\\d+)\\.v(\\d+)\\.json$``:
   (sense, version) live -> kept_live; else no ``created_at`` -> kept and
   reported; else younger than ``--grace-hours`` (default 24; protects a writer
   between its upload and its commit) -> kept_grace; else deleted (with
   ``--apply``) or would_delete (the default dry run). Any other name is kept and
   reported under ``unknown``.
4. delete in batches of 100 paths.

Safety: an RPC failure or a malformed live set stops that language with nothing
deleted. An empty live set next to files that would be deleted is treated as a
failed read (exit 1, nothing deleted) unless ``--allow-empty-live-set``.

Exit codes: 0 done; 1 errors (see the report's ``anomalies``); 2 refused
(missing Storage credentials).

Usage:
    python scripts/sweep_exercise_content.py --language all            # dry run
    python scripts/sweep_exercise_content.py --language zh --apply
    python scripts/sweep_exercise_content.py --language all --apply --grace-hours 48
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import os
import re
import sys
from collections.abc import Callable, Sequence
from datetime import datetime, timedelta, timezone
from typing import Any

try:
    from _common import LOG_FORMAT, admin_db, bootstrap
except ImportError:  # imported as scripts.sweep_exercise_content (tests)
    from scripts._common import LOG_FORMAT, admin_db, bootstrap

ROOT = bootstrap(log_level=None)

from config import Config
from services.exercise_content import store

logger = logging.getLogger('scripts.sweep_exercise_content')

LANGUAGE_IDS = {code: language_id for language_id, code in store.LANGUAGE_CODES.items()}
LANGUAGE_ORDER = ('en', 'ja', 'zh')
LIVE_VERSIONS_RPC = 'exercise_content_live_versions'
FILE_NAME_RE = re.compile(r'^(\d+)\.v(\d+)\.json$')
ARCHIVE_PREFIX = '_archive/'
DELETE_BATCH = 100
DEFAULT_GRACE_HOURS = 24.0
DEFAULT_DIR = os.path.join(ROOT, 'data', 'exercise_content_sweep')

EXIT_OK = 0
EXIT_ERRORS = 1
EXIT_REFUSED = 2

_COUNTERS = ('files_listed', 'kept_live', 'kept_grace', 'kept_no_created_at', 'unknown_names',
             'deleted', 'would_delete', 'bytes_freed', 'would_free_bytes', 'unknown_size')


class Refusal(Exception):
    """A precondition failed before anything was listed (exit 2)."""


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _iso(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')


def _error_text(exc: BaseException) -> str:
    text = str(exc).strip()
    return f'{type(exc).__name__}: {text}' if text else type(exc).__name__


def _aware(moment: datetime) -> datetime:
    return moment if moment.tzinfo is not None else moment.replace(tzinfo=timezone.utc)


def default_report_path(language: str, moment: datetime) -> str:
    stamp = moment.astimezone(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    return os.path.join(DEFAULT_DIR, f'report-{language}-{stamp}.json')


def live_versions(db, language_id: int) -> dict[int, set[int]]:
    """``{sense_id: {version, ...}}``; raises on anything but the ADR-049 §8 shape.

    On a statement timeout the map is read in keyset pages instead, exactly as the
    backfill does (scripts/backfill_exercise_content.py ``_live_versions_paged``).
    """
    try:
        data = db.rpc(LIVE_VERSIONS_RPC, {'p_language_id': language_id}).execute().data
    except Exception as exc:                      # noqa: BLE001 - narrowed just below
        from scripts.backfill_exercise_content import _is_statement_timeout, _live_versions_paged
        if not _is_statement_timeout(exc):
            raise
        logger.warning('%s(%s) hit the statement timeout; reading the versions in pages',
                       LIVE_VERSIONS_RPC, language_id)
        return {sid: set(v) for sid, v in _live_versions_paged(db, language_id).items()}
    if isinstance(data, str):
        data = json.loads(data)
    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise ValueError(f'{LIVE_VERSIONS_RPC} returned {type(data).__name__}, expected an object')
    live: dict[int, set[int]] = {}
    for key, versions in data.items():
        text = key.strip() if isinstance(key, str) else None
        if not text or not text.isdigit() or not isinstance(versions, list) or not all(
                _is_int(v) and v >= 0 for v in versions):
            raise ValueError(f'{LIVE_VERSIONS_RPC} returned a bad entry {key!r}: {versions!r}')
        live[int(text)] = set(versions)
    return live


def classify(objects, live: dict[int, set[int]], folder: str, now: datetime,
             grace: timedelta) -> dict[str, list]:
    """Split listed objects into kept_live / kept_grace / no_created_at / unknown / delete."""
    out: dict[str, list] = {'kept_live': [], 'kept_grace': [], 'no_created_at': [],
                            'unknown': [], 'protected': [], 'delete': []}
    head = folder + '/'
    for obj in objects:
        path = obj.path
        if path.startswith(ARCHIVE_PREFIX):
            out['protected'].append(obj)
            continue
        name = path[len(head):] if path.startswith(head) else None
        match = FILE_NAME_RE.match(name) if name else None
        if match is None:
            out['unknown'].append(obj)
            continue
        sense_id, version = int(match.group(1)), int(match.group(2))
        if version in live.get(sense_id, ()):
            out['kept_live'].append(obj)
        elif obj.created_at is None:
            out['no_created_at'].append(obj)
        elif now - _aware(obj.created_at) < grace:
            out['kept_grace'].append(obj)
        else:
            out['delete'].append(obj)
    return out


def _bump(report: dict, language: str, name: str, amount: int) -> None:
    if not amount:
        return
    report[name] += amount
    per = report['per_language'].setdefault(language, {key: 0 for key in _COUNTERS})
    per[name] += amount


def sweep_language(report: dict, db, backend, language: str, *, apply: bool, now: datetime,
                   grace: timedelta, allow_empty_live: bool) -> None:
    language_id = LANGUAGE_IDS[language]
    report['per_language'].setdefault(language, {key: 0 for key in _COUNTERS})
    try:
        objects = list(backend.list(f'{language}/'))
        live = live_versions(db, language_id)
    except Exception as exc:
        logger.error('%s: listing or live set failed, nothing deleted: %s', language,
                     _error_text(exc))
        report['anomalies'].append({'kind': 'read_failed', 'language': language,
                                    'severity': 'error', 'error': _error_text(exc)})
        return
    groups = classify(objects, live, language, now, grace)
    _bump(report, language, 'files_listed', len(objects))
    _bump(report, language, 'kept_live', len(groups['kept_live']))
    _bump(report, language, 'kept_grace', len(groups['kept_grace']))
    _bump(report, language, 'kept_no_created_at', len(groups['no_created_at']))
    _bump(report, language, 'unknown_names', len(groups['unknown']))
    report['unknown'].extend(obj.path for obj in groups['unknown'])
    report['no_created_at'].extend(obj.path for obj in groups['no_created_at'])
    if groups['protected']:                      # a backend listing recursively: never touch
        report['anomalies'].append({'kind': 'archive_listed', 'language': language,
                                    'severity': 'info',
                                    'paths': [obj.path for obj in groups['protected']]})

    candidates = groups['delete']
    if candidates and not live and not allow_empty_live:
        logger.error('%s: the live set is empty but %d file(s) would be deleted; nothing '
                     'deleted (pass --allow-empty-live-set if the language really has no '
                     'exercises)', language, len(candidates))
        report['anomalies'].append({'kind': 'empty_live_set', 'language': language,
                                    'severity': 'error', 'candidates': len(candidates)})
        return

    if not apply:
        _bump(report, language, 'would_delete', len(candidates))
        _bump(report, language, 'would_free_bytes', sum(o.size or 0 for o in candidates))
        _bump(report, language, 'unknown_size', sum(1 for o in candidates if o.size is None))
        report['would_delete_paths'].extend(obj.path for obj in candidates)
        return

    for start in range(0, len(candidates), DELETE_BATCH):
        batch = candidates[start:start + DELETE_BATCH]
        paths = [obj.path for obj in batch]
        if any(path.startswith(ARCHIVE_PREFIX) for path in paths):   # unreachable by design
            raise AssertionError('refusing to delete under _archive/')
        try:
            backend.delete(paths)
        except Exception as exc:
            logger.error('%s: deleting %d file(s) failed: %s', language, len(paths),
                         _error_text(exc))
            report['anomalies'].append({'kind': 'delete_failed', 'language': language,
                                        'severity': 'error', 'paths': paths,
                                        'error': _error_text(exc)})
            continue
        _bump(report, language, 'deleted', len(batch))
        _bump(report, language, 'bytes_freed', sum(o.size or 0 for o in batch))
        _bump(report, language, 'unknown_size', sum(1 for o in batch if o.size is None))
        report['deleted_paths'].extend(paths)


def _hours(text: str) -> float:
    try:
        value = float(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f'{text!r} is not a number') from None
    if not math.isfinite(value) or value < 0:
        raise argparse.ArgumentTypeError(f'{text!r} must be >= 0')
    return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog='sweep_exercise_content.py',
        description='Delete exercise content files no exercises row points at, after a grace '
                    'period (ADR-049, TASK-1024). Dry run unless --apply.',
        epilog='Exit codes: 0 done; 1 errors (see the report); 2 refused.')
    parser.add_argument('--language', required=True, choices=('zh', 'ja', 'en', 'all'))
    parser.add_argument('--apply', action='store_true',
                        help='delete the files (default: dry run, nothing is deleted)')
    parser.add_argument('--grace-hours', type=_hours, default=DEFAULT_GRACE_HOURS, metavar='H',
                        help=f'keep files younger than this (default {DEFAULT_GRACE_HOURS:g})')
    parser.add_argument('--allow-empty-live-set', action='store_true',
                        help='delete even when a language has no live sense at all')
    parser.add_argument('--report', metavar='PATH',
                        help='report JSON (default '
                             'data/exercise_content_sweep/report-{lang}-{UTC timestamp}.json)')
    return parser


def _check_backend(backend: Any) -> None:
    if not hasattr(backend, 'base_url'):
        return                                   # a test backend (InMemoryBackend)
    key = getattr(Config, 'SUPABASE_SERVICE_ROLE_KEY', None)
    if backend.base_url is None or not (isinstance(key, str) and key.strip()):
        raise Refusal('Storage needs SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY')


def main(argv: Sequence[str] | None = None, *, db: Any = None,
         now: Callable[[], datetime] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
    for noisy in ('httpx', 'httpcore', 'hpack'):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    clock = now or (lambda: datetime.now(timezone.utc))
    started = _aware(clock())
    report_path = args.report or default_report_path(args.language, started)
    try:
        backend = store.backend()
        _check_backend(backend)
    except Refusal as exc:
        print(f'refused: {exc}', file=sys.stderr)
        return EXIT_REFUSED
    if args.apply and args.grace_hours < 1:
        logger.warning('--grace-hours %g: a writer between its upload and its commit can lose '
                       'its file', args.grace_hours)
    db = db if db is not None else admin_db()

    report: dict[str, Any] = {'language': args.language,
                              'mode': 'apply' if args.apply else 'dry_run',
                              'grace_hours': args.grace_hours}
    report.update({name: 0 for name in _COUNTERS})
    report.update({'per_language': {}, 'deleted_paths': [], 'would_delete_paths': [],
                   'unknown': [], 'no_created_at': [], 'anomalies': [],
                   'started_at': _iso(started), 'finished_at': None, 'exit_code': None})
    grace = timedelta(hours=args.grace_hours)
    languages = LANGUAGE_ORDER if args.language == 'all' else (args.language,)
    for language in languages:
        sweep_language(report, db, backend, language, apply=args.apply, now=started,
                       grace=grace, allow_empty_live=args.allow_empty_live_set)
        per = report['per_language'][language]
        logger.info('%s %s: listed=%d kept_live=%d kept_grace=%d no_created_at=%d unknown=%d '
                    '%s=%d bytes=%d', report['mode'], language, per['files_listed'],
                    per['kept_live'], per['kept_grace'], per['kept_no_created_at'],
                    per['unknown_names'], 'deleted' if args.apply else 'would_delete',
                    per['deleted'] if args.apply else per['would_delete'],
                    per['bytes_freed'] if args.apply else per['would_free_bytes'])

    code = EXIT_ERRORS if any(a.get('severity') == 'error' for a in report['anomalies']) \
        else EXIT_OK
    report['finished_at'] = _iso(clock())
    report['exit_code'] = code
    os.makedirs(os.path.dirname(os.path.abspath(report_path)), exist_ok=True)
    with open(report_path, 'w', encoding='utf-8') as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
        handle.write('\n')
    print(f'report: {report_path}')
    return code


if __name__ == '__main__':
    sys.exit(main())
