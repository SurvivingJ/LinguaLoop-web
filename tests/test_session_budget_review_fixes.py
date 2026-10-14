"""Review fixes for session-budget-settings (regressions pinned by a reviewer's findings).

SQL behaviour (ladder_new_word_state, build_daily_session same-day rebuild, grants) is covered
by tests/sql/test_session_budget_settings.sql; this file pins what runs without a database.
"""

import re
from fractions import Fraction
from pathlib import Path

import pytest

from services.study_plan_service import new_words_for_day
from tests.test_ladder_new_word_quota import QuotaDB, _admit, governor  # noqa: F401
from tests.test_ladder_topup import _missed, _supply_for

MIG = Path(__file__).resolve().parents[1] / 'migrations'


# -- 5. Python == SQL rounding ------------------------------------------------

def _sql_new_words_for_day(n, w):
    """public.new_words_for_day evaluated in exact numeric: FLOOR(n * w + 0.5)."""
    if w <= 0 or n <= 0:
        return 0
    x = Fraction(n) * Fraction(str(w)) + Fraction(1, 2)
    return x.numerator // x.denominator


def test_new_words_for_day_matches_sql_numeric_on_a_grid():
    weights = [round(i / 100, 2) for i in range(0, 301)]       # 0.00 .. 3.00, every hundredth
    for n in range(0, 51):
        for w in weights:
            assert new_words_for_day(n, w) == _sql_new_words_for_day(n, w), (n, w)


def test_new_words_for_day_known_float_disagreement():
    # 25 * 0.58 is 14.499999999999998 in binary floating point; SQL numeric gives 15.
    assert new_words_for_day(25, 0.58) == 15


# -- 4. a supply check is only valid for the E it was made under -------------

def _targets(**kw):
    t = {'new_words_in_budget': 4, 'new_words_supply_checked': True}
    t.update(kw)
    return t


def test_supply_check_for_a_different_e_is_stale_and_rebuild_fires_again(governor):
    # Checked earlier today under E=3; the learner has since raised the quota to 5.
    db = QuotaDB(npd=5, evidence=_missed([1]), supply=_supply_for([1]),
                 targets=_targets(new_words_supply_checked_e=3))
    assert _admit(db)['needs_rebuild'] is True


def test_supply_check_for_the_same_e_still_fires_only_once(governor):
    db = QuotaDB(npd=5, evidence=_missed([1]), supply=_supply_for([1]),
                 targets=_targets(new_words_supply_checked_e=5))
    assert _admit(db)['needs_rebuild'] is False


def test_shortfall_write_records_the_e_it_was_checked_under(governor):
    db = QuotaDB(npd=5, evidence=_missed([1]), supply=_supply_for([1]))
    calls = []
    orig = db.rpc

    def rpc(name, args):
        if name == 'set_new_words_shortfall':
            calls.append(args)
        return orig(name, args)
    db.rpc = rpc
    _admit(db)
    assert calls and calls[0]['p_checked_e'] == 5


# -- 2. SECURITY DEFINER functions taking a caller-supplied user id are backend-only ----

def _strip_comments(sql):
    return re.sub(r'--[^\n]*', '', sql)


@pytest.mark.parametrize('fn_args', [
    r'plan_local_day_start\(\s*uuid,\s*smallint\s*\)',
    r'record_session_progress\(\s*uuid,\s*smallint,\s*uuid,\s*text,\s*text,\s*integer,\s*integer,'
    r'\s*integer,\s*bigint,\s*boolean\s*\)',
])
def test_new_definer_functions_are_revoked_from_clients_and_granted_to_service_role(fn_args):
    sql = _strip_comments((MIG / 'new_words_completed_accrual.sql').read_text(encoding='utf-8'))
    assert re.search(
        r'REVOKE\s+ALL\s+ON\s+FUNCTION\s+public\.' + fn_args + r'\s+FROM\s+PUBLIC,\s*anon,\s*authenticated',
        sql, re.I), 'missing REVOKE'
    assert re.search(
        r'GRANT\s+EXECUTE\s+ON\s+FUNCTION\s+public\.' + fn_args + r'\s+TO\s+service_role', sql, re.I)


def test_every_security_definer_in_the_new_migrations_is_locked_down():
    """Any SECURITY DEFINER function created by a new migration needs a REVOKE in that file,
    unless it is a pre-existing signature (CREATE OR REPLACE keeps its ACL)."""
    preexisting = {'compute_weekly_plan_persist', 'build_daily_session', 'record_session_progress_old',
                   'plan_local_date'}
    for name in ('new_words_completed_accrual.sql', 'session_module_exclusions.sql',
                 'session_module_exclusions_build_daily_session.sql', 'review_governor.sql',
                 'new_word_minutes_estimate.sql', 'calibration_bkt_evidence.sql'):
        sql = _strip_comments((MIG / name).read_text(encoding='utf-8'))
        for m in re.finditer(r'CREATE\s+OR\s+REPLACE\s+FUNCTION\s+public\.(\w+)(.*?)(?=CREATE\s+OR\s+REPLACE\s+FUNCTION|\Z)',
                             sql, re.I | re.S):
            fn, body = m.group(1), m.group(0)
            if not re.search(r'SECURITY\s+DEFINER', body.split('$')[0], re.I) or fn in preexisting:
                continue
            assert re.search(r'REVOKE[^;]*public\.' + fn + r'\b', sql, re.I | re.S), (name, fn)
