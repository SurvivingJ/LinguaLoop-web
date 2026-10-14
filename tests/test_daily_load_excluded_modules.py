"""TASK-867 — the legacy ``_compute_daily_load`` fallback honours
``user_study_plans.excluded_modules`` (session-modules, ADR-032).

Driven with the same fake-admin approach as test_daily_load_fallback_type.py.
With no plan row there must be no filter, so the existing suites stay green.
"""

from tests.test_daily_load_fallback_type import _FakeAdmin, _skill_rating
from services.dimension_service import DimensionService
from services.test_service import TestService


def _attempt(test_id, pct, type_id, elo=1200):
    return {
        'test_id': test_id, 'percentage': pct, 'test_type_id': type_id,
        'created_at': '2026-01-01T00:00:00+00:00', 'user_elo_after': elo,
    }


def _svc(tables, rpc_data, monkeypatch, excluded=None):
    monkeypatch.setattr(
        DimensionService, '_test_type_cache', {'listening': 1, 'dictation': 2, 'reading': 3},
        raising=False,
    )
    tables = dict(tables)
    if excluded is not None:
        tables['user_study_plans'] = [{'excluded_modules': excluded}]
    return TestService(supabase_admin=_FakeAdmin(tables=tables, rpc_data=rpc_data))


def test_excluded_retry_candidates_are_dropped(monkeypatch):
    svc = _svc(
        {'test_attempts': [_attempt('r1', 40, 1), _attempt('r2', 50, 2)], 'test_skill_ratings': []},
        {'get_recommended_tests': []}, monkeypatch, excluded=['listening'],
    )
    items = svc._compute_daily_load('u1', 1)
    retry_ids = [i['test_id'] for i in items if i['slot_type'] == 'retry']
    assert retry_ids == ['r2']


def test_excluded_recommended_tests_are_dropped(monkeypatch):
    rec = [
        {'test_id': 'n1', 'test_type': 'listening'},
        {'test_id': 'n2', 'test_type': 'reading'},
        {'test_id': 'n3', 'test_type': 'dictation'},
    ]
    svc = _svc({'test_attempts': [], 'test_skill_ratings': []},
               {'get_recommended_tests': rec}, monkeypatch, excluded=['listening', 'dictation'])
    items = svc._compute_daily_load('u1', 1)
    assert [i['test_id'] for i in items] == ['n2']


def test_excluded_types_skipped_in_last_resort_fallback(monkeypatch):
    svc = _svc(
        {'test_attempts': [],
         'test_skill_ratings': [_skill_rating('t1', 'dictation'), _skill_rating('t2', 'reading')]},
        {'get_recommended_tests': []}, monkeypatch, excluded=['dictation'],
    )
    items = svc._compute_daily_load('u1', 1)
    assert [i['test_id'] for i in items] == ['t2']


def test_no_plan_row_means_no_filter(monkeypatch):
    rec = [{'test_id': 'n1', 'test_type': 'listening'}]
    svc = _svc({'test_attempts': [], 'test_skill_ratings': []},
               {'get_recommended_tests': rec}, monkeypatch, excluded=None)
    assert [i['test_id'] for i in svc._compute_daily_load('u1', 1)] == ['n1']


def test_empty_exclusions_means_no_filter(monkeypatch):
    rec = [{'test_id': 'n1', 'test_type': 'listening'}]
    svc = _svc({'test_attempts': [], 'test_skill_ratings': []},
               {'get_recommended_tests': rec}, monkeypatch, excluded=[])
    assert [i['test_id'] for i in svc._compute_daily_load('u1', 1)] == ['n1']


def test_plan_read_failure_fails_open(monkeypatch):
    rec = [{'test_id': 'n1', 'test_type': 'listening'}]
    svc = _svc({'test_attempts': [], 'test_skill_ratings': []},
               {'get_recommended_tests': rec}, monkeypatch, excluded=None)

    real_table = svc.admin.table

    def table(name):
        if name == 'user_study_plans':
            raise RuntimeError('db down')
        return real_table(name)

    svc.admin.table = table
    assert [i['test_id'] for i in svc._compute_daily_load('u1', 1)] == ['n1']
