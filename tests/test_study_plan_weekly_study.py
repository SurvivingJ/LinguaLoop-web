"""TASK-892: learner-local week at every reader site + ``weekly_study`` on GET."""

import datetime as dt
from types import SimpleNamespace

import pytest

from tests.study_plan_route_harness import FakeDB, install, make_fake_service_module, plan_tables

LEDGER = {'test': 900, 'practice': 600, 'flashcard': 300, 'dual_translation': 240, 'drill': 0}


class LedgerFakeDB(FakeDB):
    def __init__(self, tables, ledger=LEDGER, fail=False):
        super().__init__(tables)
        self.ledger, self.fail = ledger, fail

    def rpc(self, name, params):
        self.rpcs.append((name, params))

        def _exec():
            if self.fail:
                raise RuntimeError('rpc missing')
            return SimpleNamespace(data=self.ledger if name == 'get_weekly_study_seconds' else {})
        return SimpleNamespace(execute=_exec)


def _client(monkeypatch, db, local_today=dt.date(2026, 10, 14), **kw):
    client, svc = install(monkeypatch, db, **kw)
    import routes.study_plan as sp
    seen = []

    def fake_today(d, u, l):
        seen.append((u, l))
        return local_today
    monkeypatch.setattr(sp, 'plan_today', fake_today)
    return client, svc, seen


def test_weekly_study_exact_shape(monkeypatch):
    db = LedgerFakeDB(plan_tables())
    client, _, _ = _client(monkeypatch, db)
    body = client.get('/api/study-plan?language_id=1').get_json()
    assert body['weekly_study'] == {
        'week_start_date': '2026-10-12', 'studied_seconds': 2040, 'studied_minutes': 34,
        'target_minutes': 210,
        'by_kind': {
            'test': {'seconds': 900, 'minutes': 15},
            'practice': {'seconds': 600, 'minutes': 10},
            'flashcard': {'seconds': 300, 'minutes': 5},
            'dual_translation': {'seconds': 240, 'minutes': 4},
            'drill': {'seconds': 0, 'minutes': 0},
        },
    }
    assert body['current_week']['total_weekly_minutes'] == 210   # unchanged
    (name, params), = [r for r in db.rpcs if r[0] == 'get_weekly_study_seconds']
    assert params == {'p_user_id': 'user-1', 'p_language_id': 1, 'p_week_start': '2026-10-12'}


def test_no_weekly_row_target_null_totals_present(monkeypatch):
    db = LedgerFakeDB(plan_tables(week=False))
    client, _, _ = _client(monkeypatch, db)
    body = client.get('/api/study-plan?language_id=1').get_json()
    assert body['current_week'] is None
    ws = body['weekly_study']
    assert ws['target_minutes'] is None and ws['studied_minutes'] == 34
    assert set(ws['by_kind']) == {'test', 'practice', 'flashcard', 'dual_translation', 'drill'}


def test_empty_ledger_all_five_kinds_zero(monkeypatch):
    db = LedgerFakeDB(plan_tables(), ledger={})
    client, _, _ = _client(monkeypatch, db)
    ws = client.get('/api/study-plan?language_id=1').get_json()['weekly_study']
    assert ws['studied_seconds'] == 0 and all(v == {'seconds': 0, 'minutes': 0} for v in ws['by_kind'].values())


def test_rpc_failure_degrades_to_null_and_get_succeeds(monkeypatch):
    db = LedgerFakeDB(plan_tables(), fail=True)
    client, _, _ = _client(monkeypatch, db)
    r = client.get('/api/study-plan?language_id=1')
    assert r.status_code == 200
    body = r.get_json()
    assert body['weekly_study'] is None and body['plan'] and body['current_week']


def test_get_uses_learner_local_week(monkeypatch):
    # Server-side Monday could be 2026-10-12; learner is already on Monday 10-19 locally.
    db = LedgerFakeDB(plan_tables())
    client, _, seen = _client(monkeypatch, db, local_today=dt.date(2026, 10, 19))
    body = client.get('/api/study-plan?language_id=1').get_json()
    assert body['weekly_study']['week_start_date'] == '2026-10-19'
    week_filters = [a for t, ops in db.executed if t == 'weekly_plan_states'
                    for n, a in ops if n == 'eq' and a[0] == 'week_start_date']
    assert week_filters == [('week_start_date', '2026-10-19')]
    assert ('user-1', 1) in seen


def test_sunday_local_stays_in_previous_week(monkeypatch):
    db = LedgerFakeDB(plan_tables())
    client, _, _ = _client(monkeypatch, db, local_today=dt.date(2026, 10, 18))  # Sunday
    assert client.get('/api/study-plan?language_id=1').get_json()['weekly_study']['week_start_date'] == '2026-10-12'


def test_template_apply_compute_uses_local_week(monkeypatch):
    db = LedgerFakeDB(plan_tables())
    client, svc, _ = _client(monkeypatch, db, local_today=dt.date(2026, 10, 21))
    r = client.put('/api/study-plan', json={'language_id': 1, 'template_id': 101})
    assert r.status_code == 200, r.data
    assert [str(c[2]) for c in svc.calls.compute] == ['2026-10-19']


def test_recompute_uses_local_week(monkeypatch):
    db = LedgerFakeDB(plan_tables())
    client, svc, seen = _client(monkeypatch, db, local_today=dt.date(2026, 10, 21))
    r = client.post('/api/study-plan/recompute', json={'language_id': 1})
    assert r.status_code == 200, r.data
    assert [str(c[2]) for c in svc.calls.compute] == ['2026-10-19']
    assert ('user-1', 1) in seen


def test_no_date_today_week_derivation_left():
    import pathlib
    src = pathlib.Path(__file__).resolve().parents[1].joinpath('routes/study_plan.py').read_text()
    assert '_monday_of(date.today())' not in src
