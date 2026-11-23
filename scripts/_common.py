"""Shared start-up helpers for the command-line scripts in this folder.

A script run as ``python scripts/name.py`` imports this with
``from _common import bootstrap``; one that tests or other modules also import
as ``scripts.name`` falls back to ``from scripts._common import ...``.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

LOG_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'


def bootstrap(log_level: int | None = logging.INFO, log_format: str = LOG_FORMAT) -> str:
    """Put the repo root on sys.path, load ROOT/.env, set up logging and UTF-8 output.

    ``log_level=None`` leaves logging alone, for scripts that configure it
    themselves or only print. Safe to call more than once. Returns the repo root.
    """
    if ROOT not in sys.path:
        sys.path.insert(0, ROOT)
    from dotenv import load_dotenv
    load_dotenv(os.path.join(ROOT, '.env'))
    if log_level is not None:
        logging.basicConfig(level=log_level, format=log_format)
    for stream in (sys.stdout, sys.stderr):
        encoding = (getattr(stream, 'encoding', None) or '').lower().replace('-', '')
        if encoding != 'utf8' and hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8')
    return ROOT


def admin_db():
    """The service-role Supabase client, initialising the factory on first use."""
    from services import supabase_factory
    if not supabase_factory.SupabaseFactory.is_initialized():
        supabase_factory.SupabaseFactory.initialize()
    return supabase_factory.get_supabase_admin()


def paginate(query_builder, page_size: int = 1000):
    """Yield every row of a select, one ``.range()`` page at a time.

    ``query_builder`` is a zero-argument callable returning a FRESH query on
    each call (postgrest's ``.range()`` mutates the builder, so one query object
    cannot serve two pages). The query must have a stable total order, e.g.
    ``.order('id')``: without one, rows can repeat or go missing between pages.
    PostgREST caps a response at 1000 rows, so ``page_size`` above that stops
    after the first page.
    """
    start = 0
    while True:
        page = query_builder().range(start, start + page_size - 1).execute().data or []
        yield from page
        if len(page) < page_size:
            return
        start += page_size


class ApplyArgumentParser(argparse.ArgumentParser):
    """An ArgumentParser that enforces the write convention after parsing.

    ``--apply`` together with ``--dry-run`` is an error (exit code 2). After
    parsing, ``args.dry_run`` is ``not args.apply`` (so code written against the
    old ``--dry-run`` flag keeps working), and ``args.dry_run_flag`` records
    whether ``--dry-run`` itself was typed, for the scripts that make the
    caller name the mode explicitly.
    """

    def parse_known_args(self, args=None, namespace=None):
        return self._resolve_apply(*super().parse_known_args(args, namespace))

    def parse_known_intermixed_args(self, args=None, namespace=None):
        return self._resolve_apply(*super().parse_known_intermixed_args(args, namespace))

    def _resolve_apply(self, namespace, extras):
        if hasattr(namespace, 'apply') and hasattr(namespace, 'dry_run_flag'):
            if namespace.apply and namespace.dry_run_flag:
                self.error('--apply and --dry-run cannot be used together')
            namespace.dry_run = not namespace.apply
        return namespace, extras


def base_parser(description: str | None = None, *,
                apply_help: str = 'write the changes (default: dry run, nothing is written)',
                dry_run_help: str = 'explicit dry run (the default; cannot be combined with --apply)',
                dry_run_flags: tuple[str, ...] = ('--dry-run',),
                **kwargs) -> argparse.ArgumentParser:
    """An ArgumentParser with the standard write flags: a script is a dry run unless ``--apply``.

    ``--dry-run`` (plus any extra spellings in ``dry_run_flags``) is accepted as an
    explicit alias for the default; ``--apply --dry-run`` exits with code 2.
    Scripts must not define their own ``--dry-run``: tests/test_scripts_apply_convention.py
    fails when one does.
    """
    parser = ApplyArgumentParser(description=description, **kwargs)
    return add_apply_flags(parser, apply_help=apply_help, dry_run_help=dry_run_help,
                           dry_run_flags=dry_run_flags)


def add_apply_flags(parser: ApplyArgumentParser, *,
                    apply_help: str = 'write the changes (default: dry run, nothing is written)',
                    dry_run_help: str = 'explicit dry run (the default; cannot be combined with --apply)',
                    dry_run_flags: tuple[str, ...] = ('--dry-run',)) -> ApplyArgumentParser:
    """Add ``--apply`` / ``--dry-run`` to one parser, e.g. the writing sub-command of a runner.

    The parser must be an ``ApplyArgumentParser`` (a sub-command parser is one when
    the top-level parser is), so the two flags are checked after parsing.
    """
    if not isinstance(parser, ApplyArgumentParser):
        raise TypeError('add_apply_flags needs an ApplyArgumentParser (use base_parser)')
    parser.add_argument('--apply', action='store_true', help=apply_help)
    parser.add_argument(*dry_run_flags, dest='dry_run_flag', action='store_true', help=dry_run_help)
    return parser
