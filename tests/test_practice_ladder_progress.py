"""Practice attempts move the ladder (ladder fix, 2026-11-10).

record_exercise_attempt (migrations/record_exercise_attempt.sql) calls
ladder_apply_progress in the attempt's transaction; Python summarises its
result onto the response (``_report_ladder_progress``) and, for a word demoted
from ring 2 that came through the new-word drill, restarts the drill (ADR-040).
"""

import re
from pathlib import Path

from services import intro_drill
from services.practice_session_service import PracticeSessionService

SQL = re.sub(r'\s+', ' ', (Path(__file__).resolve().parent.parent / 'migrations'
                           / 'record_exercise_attempt.sql').read_text())


def _svc():
    s = PracticeSessionService.__new__(PracticeSessionService)
    s.db = object()
    return s


def test_ladder_progress_called_with_context_and_summarised(monkeypatch):
    monkeypatch.setattr(intro_drill, 'restart_if_demoted', lambda *a: False)
    ladder = {'family': 'meaning_recall', 'current_ring': 2, 'word_state': 'active',
              'gate_pending': None, 'stress_test_ready': False, 'demoted': False,
              'is_lapse': False, 'internal': 'not reported'}
    result = {}
    _svc()._report_ladder_progress(result, ladder, 'u', 5, 3)
    assert result['ladder'] == {k: v for k, v in ladder.items() if k != 'internal'}
    # The RPC passes the context and whether this was the first attempt.
    assert ('ladder_apply_progress( p_user_id, v_sense, p_exercise_id, p_is_correct, v_first, '
            "CASE WHEN p_exercise_context IN ('standard', 'gate', 'stress_test')") in SQL


def test_unknown_context_falls_back_to_standard(monkeypatch):
    monkeypatch.setattr(intro_drill, 'restart_if_demoted', lambda *a: False)
    assert "THEN p_exercise_context ELSE 'standard' END" in SQL
    result = {}
    _svc()._report_ladder_progress(result, {'skipped': 'retry'}, 'u', 5, 3)
    assert 'ladder' not in result          # skipped: nothing reported


def test_ring2_demotion_restarts_the_drill(monkeypatch):
    seen = []
    monkeypatch.setattr(intro_drill, 'restart_if_demoted',
                        lambda db, u, sid, lang, ladder: seen.append((sid, lang, ladder['demoted'])) or True)
    result = {}
    _svc()._report_ladder_progress(
        result, {'current_ring': 1, 'demoted': True, 'word_state': 'active'}, 'u', 5, 3)
    assert seen == [(5, 3, True)] and result['ladder']['intro_restart'] is True


def test_ladder_failure_is_non_fatal():
    # A failed ladder step rolls back to its savepoint and is reported as a
    # warning; the RPC returns ladder NULL and nothing is reported.
    assert "jsonb_build_object('step', 'ladder', 'error', SQLERRM)" in SQL
    result = {}
    _svc()._report_ladder_progress(result, None, 'u', 5, 3)
    assert result == {}
