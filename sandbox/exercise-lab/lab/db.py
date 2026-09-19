"""
Tiny connection helper for lab.sqlite.

WHY THIS EXISTS: SQLite does not enforce declared FOREIGN KEY constraints
unless `PRAGMA foreign_keys = ON` is set on every connection - forgetting
this is a classic silent-corruption trap (orphaned rows insert without
complaint). Centralizing connect() here means every reader/writer in this
sandbox (build_db.py, tests, a later prototype) gets that pragma and a
dict-like Row factory for free, instead of every caller having to remember.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "db" / "lab.sqlite"


def connect(db_path: Path | str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn
