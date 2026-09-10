"""TASK-752 — calibration completion is wired to the guarded rating writer.

Pins the contract of `calibration_service.end_session` against the
`apply_calibration_to_skill_ratings` RPC (TASK-747):

  * it fires exactly once, and only AFTER `user_calibration_state` was written;
  * definition mode only — the writer reads the 'definition' row;
  * a failure is logged and non-fatal: the learner still gets their result;
  * the RPC's decisions reach the result view verbatim, refusals included —
    Python re-implements no gate and filters nothing.

The gates themselves are tested in SQL (tests/sql/test_task747_rating_writer.sql).
"""

import logging
from unittest.mock import MagicMock

import pytest

from services import calibration_service as cs

USER = 'user-1'
POOLED = {'ability_zipf': 5.0, 'ability_se': 0.2, 'items_answered': 60,
          'sessions_pooled': 1, 'bands': []}
DECISIONS = [
    {'test_type': 'reading', 'source': 'calibration_seed',
     'reason': 'seed_tests_taken_lt_5', 'elo_before': None, 'elo_after': 1250},
    {'test_type': 'pitch_accent', 'source': 'skipped',
     'reason': 'within_deadband', 'elo_before': 1182, 'elo_after': 1182},
    {'test_type': 'listening', 'source': 'skipped',
     'reason': 'G6_rate_limit', 'elo_before': 1250, 'elo_after': 1250},
]


def _session(mode='definition'):
    return {'id': 'session-1', 'word_language_id': 3, 'mode': mode}


@pytest.fixture
def wiring(monkeypatch):
    """A fake DB and a call log recording the order state-write -> rpc."""
    calls = []
    db = MagicMock()

    def rpc(name, params):
        calls.append(('rpc', name, params))
        result = MagicMock()
        result.execute.return_value.data = {'decisions': DECISIONS}
        return result

    db.rpc.side_effect = rpc

    def write_state(user_id, language_id, mode=cs.MODE_DEFINITION):
        calls.append(('state', user_id, language_id, mode))
        return dict(POOLED)

    monkeypatch.setattr(cs, 'get_supabase_admin', lambda: db)
    monkeypatch.setattr(cs, 'ability', lambda user_id, session, fit=True: {'answered': 60})
    monkeypatch.setattr(cs, 'write_calibration_state', write_state)
    return db, calls


def _rpc_calls(calls):
    return [c for c in calls if c[0] == 'rpc' and c[1] == 'apply_calibration_to_skill_ratings']


def test_writer_fires_once_after_the_state_write(wiring):
    _db, calls = wiring
    cs.end_session(USER, _session())

    rpc = _rpc_calls(calls)
    assert len(rpc) == 1
    assert rpc[0][2] == {'p_user_id': USER, 'p_language_id': 3}
    order = [c[0] for c in calls]
    assert order.index('state') < order.index('rpc')


def test_decisions_reach_the_result_view_unfiltered(wiring):
    report = cs.end_session(USER, _session())
    # Refusals (skipped + gate code) are surfaced exactly as the RPC returned them.
    assert report['rating_decisions'] == DECISIONS
    assert report['pooled']['ability_zipf'] == 5.0


def test_rpc_failure_is_logged_and_non_fatal(wiring, caplog):
    db, _calls = wiring
    db.rpc.side_effect = RuntimeError('connection reset')

    with caplog.at_level(logging.WARNING, logger=cs.logger.name):
        report = cs.end_session(USER, _session())

    assert report['answered'] == 60             # the result is kept
    assert 'pooled' in report                   # ...and so is the published state
    assert 'rating_decisions' not in report     # nothing invented
    assert any('apply_calibration_to_skill_ratings' in r.getMessage() for r in caplog.records)


def test_not_called_when_the_state_write_did_not_land(wiring, monkeypatch):
    _db, calls = wiring
    monkeypatch.setattr(cs, 'write_calibration_state', lambda *a, **k: None)

    report = cs.end_session(USER, _session())

    assert _rpc_calls(calls) == []
    assert 'rating_decisions' not in report


def test_not_called_for_a_pronunciation_run(wiring):
    _db, calls = wiring
    report = cs.end_session(USER, _session(mode='pronunciation'))

    assert _rpc_calls(calls) == []
    assert 'pooled' in report
    assert 'rating_decisions' not in report


def test_malformed_rpc_payload_yields_no_decisions_not_an_error(monkeypatch):
    db = MagicMock()
    db.rpc.return_value.execute.return_value.data = None
    monkeypatch.setattr(cs, 'get_supabase_admin', lambda: db)

    assert cs.apply_calibration_to_ratings(USER, 3) == []
