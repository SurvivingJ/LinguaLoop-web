"""Runs the placement SQL behaviour tests against a LOCAL harness database (TASK-1077/1079).

Skipped unless PLACEMENT_TEST_DSN is set. The database must be a throwaway UTF8 copy with
the harness base files, tests/sql/fixtures/placement_harness_fks.sql, a
calibration_zh_tone_variants (tests/sql/fixtures/calibration_zh_tone_variants_stub.sql or
migrations/calibration_zh_tones.sql + calibration_refresh_zh_tone_inventory()), and
migrations/calibration_placement.sql, calibration_placement_rpcs.sql and
knowledge_calibration_inputs.sql applied. Both SQL files run in one transaction and roll
back, but they write rows and edit a sense row inside it: never point this at Supabase.

    PLACEMENT_TEST_DSN="host=/tmp port=55435 user=postgres dbname=postgres" \
        python -m pytest tests/test_calibration_placement_sql.py -q
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
DSN = os.environ.get('PLACEMENT_TEST_DSN', '')

pytestmark = [
    pytest.mark.skipif(not DSN, reason='PLACEMENT_TEST_DSN not set (local harness only)'),
    pytest.mark.skipif(shutil.which('psql') is None, reason='psql not installed'),
]


def _run(sql_file: str) -> str:
    assert not re.search(r'supabase\.(co|com)|pooler', DSN, re.I), 'refusing to run against Supabase'
    proc = subprocess.run(
        ['psql', DSN, '-X', '-q', '-v', 'ON_ERROR_STOP=1', '-f', str(ROOT / 'tests' / 'sql' / sql_file)],
        capture_output=True, text=True, timeout=900)
    out = proc.stdout + proc.stderr
    assert proc.returncode == 0, out[-4000:]
    return out


def test_placement_sessions_sql():
    out = _run('test_calibration_placement.sql')
    for marker in ('PASS session zh', 'PASS session ja', 'PASS session en', 'PASS session zhja',
                   'PASS session jazh', 'PASS session jasp', 'PASS ownership', 'PASS close_stale',
                   'PASS fallback and exhaustion', 'PASS recheck', 'PASS ready_counts',
                   'PASS zh readiness', 'PASS knowledge_calibration_inputs'):
        assert marker in out, marker


def test_knowledge_calibration_inputs_sql():
    out = _run('test_knowledge_calibration_inputs.sql')
    for marker in ('PASS A', 'PASS B', 'PASS C', 'PASS D', 'PASS E'):
        assert marker in out, marker


def test_verify_script_against_the_harness():
    """scripts/verify_placement_rpcs.py over psql (--dsn): the owner's live checks, run locally."""
    assert not re.search(r'supabase\.(co|com)|pooler', DSN, re.I), 'refusing to run against Supabase'
    proc = subprocess.run(
        [sys.executable, str(ROOT / 'scripts' / 'verify_placement_rpcs.py'), '--user', str(uuid.uuid4()),
         '--dsn', DSN, '--pairs', '1:2,3:2,2:2', '--draws', '25'],
        capture_output=True, text=True, timeout=900)
    out = proc.stdout + proc.stderr
    assert proc.returncode == 0, out[-4000:]
    assert 'OK every check passed' in out
