"""Practice attempts move the ladder again (ladder fix, 2026-11-10).

PracticeSessionService._apply_ladder_progress calls ladder_apply_progress
(migrations/ladder_apply_progress.sql) and, for a word demoted from ring 2 that
came through the new-word drill, restarts the drill (ADR-040).
"""

from services import intro_drill
from services.practice_session_service import PracticeSessionService


class _Rpc:
    def __init__(self, data, calls, name, params):
        self.data, calls[:] = data, calls + [(name, params)]

    def execute(self):
        return self


class _Db:
    def __init__(self, data):
        self.data, self.calls = data, []

    def rpc(self, name, params):
        return _Rpc(self.data, self.calls, name, params)


def _svc(data):
    s = PracticeSessionService.__new__(PracticeSessionService)
    s.db = _Db(data)
    return s


def test_ladder_progress_called_with_context_and_summarised(monkeypatch):
    monkeypatch.setattr(intro_drill, 'restart_if_demoted', lambda *a: False)
    svc = _svc({'family': 'meaning_recall', 'current_ring': 2, 'word_state': 'active',
                'gate_pending': None, 'stress_test_ready': False, 'demoted': False, 'is_lapse': False})
    result = {}
    svc._apply_ladder_progress(result, 'u', 5, 'ex-1', True, True, 3, 'gate')
    name, params = svc.db.calls[0]
    assert name == 'ladder_apply_progress'
    assert params['p_exercise_context'] == 'gate' and params['p_is_first_attempt'] is True
    assert result['ladder']['current_ring'] == 2


def test_unknown_context_falls_back_to_standard(monkeypatch):
    monkeypatch.setattr(intro_drill, 'restart_if_demoted', lambda *a: False)
    svc = _svc({'skipped': 'retry'})
    result = {}
    svc._apply_ladder_progress(result, 'u', 5, 'ex-1', False, False, 3, 'bogus')
    assert svc.db.calls[0][1]['p_exercise_context'] == 'standard'
    assert 'ladder' not in result          # skipped: nothing reported


def test_ring2_demotion_restarts_the_drill(monkeypatch):
    seen = []
    monkeypatch.setattr(intro_drill, 'restart_if_demoted',
                        lambda db, u, sid, lang, ladder: seen.append(ladder['demoted']) or True)
    svc = _svc({'current_ring': 1, 'demoted': True, 'word_state': 'active'})
    result = {}
    svc._apply_ladder_progress(result, 'u', 5, 'ex-1', False, True, 3, 'standard')
    assert seen == [True] and result['ladder']['intro_restart'] is True


def test_rpc_failure_is_non_fatal():
    class Boom:
        def rpc(self, *_a):
            raise RuntimeError('down')
    s = PracticeSessionService.__new__(PracticeSessionService)
    s.db = Boom()
    result = {}
    s._apply_ladder_progress(result, 'u', 5, 'ex-1', True, True, 3, 'standard')
    assert result == {}
