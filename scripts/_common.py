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


def base_parser(description: str | None = None, **kwargs) -> argparse.ArgumentParser:
    """An ArgumentParser with the standard ``--apply`` flag; without it a script is a dry run."""
    parser = argparse.ArgumentParser(description=description, **kwargs)
    parser.add_argument('--apply', action='store_true',
                        help='write the changes (default: dry run, nothing is written)')
    return parser
