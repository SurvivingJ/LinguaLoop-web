"""Session assembly reads: what is fetched once, what is fetched together, and
that a read made ahead of time still fails where it is used."""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from services import intro_drill, prestudy
from services import practice_session_service as pss
from services.practice_session_service import PracticeSessionService


def _service(rpc_data=None):
    s = PracticeSessionService.__new__(PracticeSessionService)
    s.db = MagicMock()
    s.rpc_calls = []

    def rpc(name, params):
        s.rpc_calls.append((name, params))
        data = (rpc_data or {}).get(name, {'items': []})
        if isinstance(data, Exception):
            raise data
        return SimpleNamespace(execute=lambda: SimpleNamespace(data=data))

    s.db.rpc.side_effect = rpc
    return s


@pytest.fixture
def session_svc(monkeypatch):
    monkeypatch.setattr(pss, 'plan_today_iso', lambda db, u, lang: '2026-11-14')
    monkeypatch.setattr(intro_drill, 'ENABLED', True)
    monkeypatch.setattr(intro_drill, 'block_for_session', lambda *a: None)
    items = [{'exercise_id': f'e{i}', 'sense_id': i, 'mode': 'maintenance',
              'exercise_type': 'definition_match'} for i in range(25)]
    s = _service({'get_practice_session': {'items': items}})
    s._maybe_top_up_ladder = lambda u, lang: []
    s._order_items = lambda *a: None
    s._prepare_jumbled_items = lambda *a: None
    s.seen = {}
    s._inject_prestudy_followups = lambda payload, u, lang, due=None: s.seen.update(due=due)
    monkeypatch.setattr(
        'services.dual_translation.cards.select_error_exercises_for_practice',
        lambda *a, **k: [])
    return s


def test_session_reads_are_made_once_and_handed_to_their_steps(session_svc, monkeypatch):
    asked = []
    monkeypatch.setattr(prestudy, 'due_followup_senses',
                        lambda db, u, lang, today, limit: asked.append((today, limit)) or [7])
    monkeypatch.setattr(intro_drill, 'intro_sense_ids', lambda db, u: {3, 4})
    payload = session_svc.get_session('u', 1, mode='auto')
    assert [n for n, _ in session_svc.rpc_calls] == ['get_practice_session']
    assert asked == [('2026-11-14', pss.PRESTUDY_FOLLOWUPS_PER_SESSION)]
    assert session_svc.seen == {'due': [7]}
    assert {i['sense_id'] for i in payload['items']} == set(range(25)) - {3, 4}


def test_a_failed_side_read_is_non_fatal_and_only_skips_its_step(session_svc, monkeypatch):
    def boom(*_a, **_k):
        raise RuntimeError('down')
    monkeypatch.setattr(prestudy, 'due_followup_senses', boom)
    monkeypatch.setattr(intro_drill, 'intro_sense_ids', boom)
    payload = session_svc.get_session('u', 1, mode='auto')
    assert len(payload['items']) == 25 and session_svc.seen == {}


def test_followups_are_not_read_for_tail_or_acquisition(session_svc, monkeypatch):
    asked = []
    monkeypatch.setattr(prestudy, 'due_followup_senses', lambda *a, **k: asked.append(1) or [])
    monkeypatch.setattr(intro_drill, 'intro_sense_ids', lambda db, u: set())
    session_svc._apply_session_floor = lambda *a: None
    session_svc.get_session('u', 1, mode='auto', tail=True)
    session_svc.get_session('u', 1, mode='acquisition')
    assert asked == [] and session_svc.seen == {}


def test_session_rpc_failure_is_reported_as_before(session_svc, monkeypatch):
    monkeypatch.setattr(prestudy, 'due_followup_senses', lambda *a, **k: [])
    monkeypatch.setattr(intro_drill, 'intro_sense_ids', lambda db, u: set())
    s = _service({'get_practice_session': RuntimeError('rpc down')})
    s._maybe_top_up_ladder = lambda u, lang: []
    out = s.get_session('u', 1, mode='maintenance')
    assert out == {'error': 'rpc_failed', 'code': 'E_RPC', 'detail': 'rpc down'}


def test_nomination_reads_the_calibration_ledger_once():
    s = _service()
    counts = {'ledger': 0, 'wrong': 0, 'rows': 0}

    def ledger(u, lang):
        counts['ledger'] += 1
        return {5: {'cal_n': 1, 'cal_wrong': 1, 'last_answer_wrong': True,
                    'last_at': '9999-01-01T00:00:00'}}

    s._calibration_ledger = ledger
    s._wrong_answer_sense_counts = lambda u: counts.update(wrong=counts['wrong'] + 1) or {}
    s._evidence_rows = lambda u, lang: counts.update(rows=counts['rows'] + 1) or []
    s._recent_test_sense_ids = lambda u, lang: set()
    s._sense_frequency = lambda ids: {}
    s._gate_and_admit = lambda candidates, want, lang: list(candidates)[:want]
    s.db.table.return_value.select.return_value.eq.return_value.in_.return_value \
        .execute.return_value.data = []
    assert s._nominate_new_words('u', 1, 3, set()) == [5]      # queue A2 used the same ledger
    assert counts == {'ledger': 1, 'wrong': 1, 'rows': 1}


def test_extra_round_makes_one_session_call_per_half():
    s = _service({
        'get_practice_session': {'items': [
            {'exercise_id': 'a', 'sense_id': 1, 'mode': 'acquisition'},
            {'exercise_id': 'm', 'sense_id': 2, 'mode': 'maintenance'}]},
        'get_review_ahead_items': [],
    })
    s.new_word_state = lambda u, lang: {'unstarted_sense_ids': [1], 'effective': 5, 'started_today': 0}
    s._promote_unstarted_to_intro = lambda *a: None
    s._inject_prestudy_followups = lambda payload, u, lang: 0
    s._most_overdue_first = lambda items, u: None
    s._apply_script_variant = lambda *a, **k: None
    s._prepare_jumbled_items = lambda *a, **k: None
    s._extra_acquisition_minutes = lambda lang, n: 3
    out = s.get_extra_round('u', 1, reviews=True, new_words=1)
    modes = sorted(p['p_mode'] for n, p in s.rpc_calls if n == 'get_practice_session')
    assert modes == ['acquisition', 'maintenance']
    assert {i['exercise_id'] for i in out['items']} <= {'a', 'm'}
