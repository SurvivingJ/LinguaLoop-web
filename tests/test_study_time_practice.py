"""TASK-890: every vocabulary practice attempt credits the study-time ledger.

The credit is made inside record_exercise_attempt (migrations/
record_exercise_attempt.sql): ``credit_study_time(user, lang, 'practice',
p_credit_seconds, 'exercise_attempts', attempt_id)`` on every attempt with a
language, whatever the session mode, so the ledger's (kind, source) key credits
an attempt once; a failed credit is a warning, never a failed attempt. Here the
Python half is pinned: the seconds it sends and the plan kind.
"""

import re
from pathlib import Path
from types import SimpleNamespace

import pytest

from config import Config
from services.practice_session_service import PracticeSessionService

SQL = re.sub(r'\s+', ' ', (Path(__file__).resolve().parent.parent / 'migrations'
                           / 'record_exercise_attempt.sql').read_text())


class _DB:
    def __init__(self, warnings=()):
        self.rpcs = []
        self.answer = {'attempt_id': 'attempt-1', 'is_first_attempt': True,
                       'exercise_type': 'definition_match', 'sense_id': None,
                       'language_id': 1, 'warnings': list(warnings)}

    def rpc(self, name, args):
        self.rpcs.append((name, args))
        return SimpleNamespace(execute=lambda: SimpleNamespace(data=self.answer))

    def args(self):
        (a,) = [a for n, a in self.rpcs if n == 'record_exercise_attempt']
        return a


@pytest.fixture
def make_svc(monkeypatch):
    monkeypatch.setattr(Config, 'STUDY_PLAN_ENABLED', True)

    def _make(**kw):
        s = PracticeSessionService.__new__(PracticeSessionService)
        s.db = _DB(**kw)
        return s
    return _make


def test_attempt_without_session_context_credits_ledger(make_svc):
    svc = make_svc()
    svc.record_attempt_with_updates('u', 'ex-1', True, time_taken_ms=12_400)
    a = svc.db.args()
    assert a['p_credit_seconds'] == 12 and a['p_plan_kind'] is None
    assert ("credit_study_time( p_user_id, v_lang, 'practice', v_secs, 'exercise_attempts', "
            "v_attempt_id::text)") in SQL


def test_attempt_with_session_credits_both_and_progress_unchanged(make_svc):
    svc = make_svc()
    svc.record_attempt_with_updates('u', 'ex-1', True, time_taken_ms=20_000,
                                    session_mode='acquisition', language_id=1)
    a = svc.db.args()
    assert a['p_credit_seconds'] == 20 and a['p_plan_kind'] == 'practice_acq'
    # The ledger and the plan get the same seconds; plan count delta stays 0.
    assert 'p_delta_seconds => v_secs' in SQL and 'p_delta_count => 0' in SQL


def test_credits_even_when_study_plan_disabled(make_svc, monkeypatch):
    monkeypatch.setattr(Config, 'STUDY_PLAN_ENABLED', False)
    svc = make_svc()
    svc.record_attempt_with_updates('u', 'ex-1', True, time_taken_ms=8_000, session_mode='acquisition')
    a = svc.db.args()
    assert a['p_credit_seconds'] == 8 and a['p_plan_kind'] is None
    # The credit is not gated on the plan kind.
    assert SQL.index('IF v_lang IS NOT NULL AND v_secs > 0 THEN') < SQL.index('credit_study_time(')


@pytest.mark.parametrize('ms', [None, 0, 900_000])
def test_estimate_fallback_seconds_are_credited(make_svc, ms):
    svc = make_svc()
    svc.record_attempt_with_updates('u', 'ex-1', True, time_taken_ms=ms, expected_seconds=25)
    assert svc.db.args()['p_credit_seconds'] == 25


def test_estimate_clamped_at_practice_cap(make_svc):
    svc = make_svc()
    svc.record_attempt_with_updates('u', 'ex-1', True, time_taken_ms=None, expected_seconds=9999)
    assert svc.db.args()['p_credit_seconds'] == 300


def test_credit_is_keyed_by_the_attempt_id():
    # credit_study_time credits once per (kind, source_table, source_id); the
    # source is the attempt row the same transaction inserted.
    assert 'RETURNING id INTO v_attempt_id' in SQL
    assert "'exercise_attempts', v_attempt_id::text" in SQL


def test_credit_failure_never_fails_attempt(make_svc):
    svc = make_svc(warnings=[{'step': 'study_time', 'error': 'ledger down'}])
    out = svc.record_attempt_with_updates('u', 'ex-1', True, time_taken_ms=5_000,
                                          session_mode='maintenance', language_id=1)
    assert out['attempt_id'] == 'attempt-1'
    assert svc.db.args()['p_plan_kind'] == 'practice_maint'
    assert "jsonb_build_object('step', 'study_time', 'error', SQLERRM)" in SQL
