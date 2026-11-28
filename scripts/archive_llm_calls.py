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

The work is done by ``services/llm_calls_archive.py``, which the weekly job
``llm_calls_archive_weekly`` (``web/scheduler.py``) also runs. Deleting frees
space inside the table; the database's size on disk only falls after
``VACUUM (FULL) public.llm_calls`` (a brief exclusive lock), run separately.

Usage:
  python scripts/archive_llm_calls.py                         # dry run, cutoff = today 00:00 UTC
  python scripts/archive_llm_calls.py --before 2026-11-27 --apply            # archive + verify
  python scripts/archive_llm_calls.py --before 2026-11-27 --apply --delete   # ... then delete
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone
from typing import Optional

try:
    from _common import admin_db, bootstrap
except ImportError:  # imported as scripts.<name>
    from scripts._common import admin_db, bootstrap

ROOT = bootstrap(log_format='%(asctime)s %(levelname)-7s %(name)s: %(message)s')

from services import llm_calls_archive as la  # noqa: E402

LOCAL_DIR = os.path.join(ROOT, 'data', 'llm_calls_archive')


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
        return la.start_of_day()
    ts = la.parse_ts(value if 'T' in value else value + 'T00:00:00+00:00')
    if ts > datetime.now(timezone.utc):
        raise SystemExit(f'--before {value} is in the future')
    return ts


def main(argv: Optional[list[str]] = None, db=None) -> int:
    args = build_parser().parse_args(argv)
    say = lambda msg: print(f'[{la.now_iso()}] {msg}', flush=True)  # noqa: E731
    if args.delete and not args.apply:
        raise SystemExit('--delete needs --apply (rows are deleted only after a verified archive)')
    cutoff = cutoff_of(args.before)
    db = db or admin_db()
    if not args.apply:
        say(f'{la.count_below(db, cutoff)} {la.TABLE} rows created before {cutoff.isoformat()}')
        say('dry run: nothing written (add --apply)')
        return 0
    try:
        result = la.archive(db, cutoff, delete=args.delete, say=say,
                            local_dir=os.path.join(LOCAL_DIR, la.stamp(cutoff)))
    except la.ArchiveError as exc:
        say(f'{exc}')
        return 2
    if result['rows'] and not args.delete:
        say('verified; rows kept (add --delete to remove them from the table)')
    return 0 if result['left'] in (None, 0) else 3


if __name__ == '__main__':
    sys.exit(main())
