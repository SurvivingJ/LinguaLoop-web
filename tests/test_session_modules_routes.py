"""TASK-866 — module include/exclude on GET/PUT /api/study-plan.

Route-level tests with a fake Supabase and a fake study-plan service (see
tests/study_plan_route_harness.py). Budget-scope / new-words behaviour is in
tests/test_session_budget_settings_routes.py.
"""

import pytest

import routes.study_plan as sp
from tests.study_plan_route_harness import (
    ZH_AVAILABLE, FakeDB, install, plan_tables,
)


def put(client, **body):
    body.setdefault('language_id', 1)
    return client.put('/api/study-plan', json=body)


@pytest.fixture
def setup(monkeypatch):
    def _make(**kwargs):
        db = FakeDB(plan_tables(**kwargs))
        client, service = install(monkeypatch, db)
        return client, db, service
    return _make


class TestGet:
    def test_available_modules_in_all_modules_order_with_practice_last(self, setup):
        client, _, _ = setup(templates=[
            {'weekly_test_counts': {'flashcards': 7, 'reading': 6, 'bogus_key': 1}},
            {'weekly_test_counts': {'listening': 5, 'reading': 3}},
        ])
        body = client.get('/api/study-plan?language_id=1').get_json()
        assert body['available_modules'] == ['reading', 'listening', 'flashcards', 'practice']

    def test_returns_excluded_modules_on_plan(self, setup):
        client, _, _ = setup(excluded=['listening'])
        body = client.get('/api/study-plan?language_id=1').get_json()
        assert body['plan']['excluded_modules'] == ['listening']

    def test_get_selects_new_plan_and_week_columns(self, setup):
        client, db, _ = setup()
        client.get('/api/study-plan?language_id=1')
        selects = {t: [a[0] for n, a in ops if n == 'select']
                   for t, ops in db.executed}
        assert 'excluded_modules' in selects['user_study_plans'][0]
        assert 'budget_scope' in selects['user_study_plans'][0]
        assert 'new_words_per_day' in selects['user_study_plans'][0]
        wk = selects['weekly_plan_states'][0]
        for col in ('review_target_minutes', 'new_words_target', 'new_words_completed',
                    'acq_target_minutes', 'tail_completed_min', 'tail_new_words_completed'):
            assert col in wk


class TestPutValidation:
    @pytest.mark.parametrize('value', ['listening', {'a': 1}, [1, 2], None, ['reading', 3]])
    def test_non_list_of_strings_is_400(self, setup, value):
        client, _, _ = setup()
        r = put(client, excluded_modules=value)
        assert r.status_code == 400
        assert r.get_json()['error'] == 'excluded_modules must be a list of module codes'

    def test_unknown_module_for_language_is_400(self, setup):
        client, _, _ = setup()
        r = put(client, excluded_modules=['pitch_accent'])  # ja-only code on zh
        assert r.status_code == 400
        assert r.get_json()['error'] == 'unknown module for this language: pitch_accent'

    def test_all_modules_excluded_is_400_when_no_new_words(self, setup):
        client, _, _ = setup(npd=0)
        r = put(client, excluded_modules=list(ZH_AVAILABLE))
        assert r.status_code == 400
        assert r.get_json()['error'] == 'at least one module must remain included'

    def test_all_modules_excluded_ok_when_new_words_positive(self, setup):
        client, db, _ = setup(npd=5)
        r = put(client, excluded_modules=list(ZH_AVAILABLE))
        assert r.status_code == 200
        assert db.updates_for('user_study_plans')[-1]['excluded_modules'] == ZH_AVAILABLE

    def test_all_modules_excluded_with_request_npd_zero_is_400(self, setup):
        client, _, _ = setup(npd=5)
        r = put(client, excluded_modules=list(ZH_AVAILABLE), new_words_per_day=0)
        assert r.status_code == 400

    def test_stored_value_is_normalized_before_write(self, setup):
        client, db, _ = setup()
        r = put(client, excluded_modules=['pinyin', 'listening', 'pinyin'])
        assert r.status_code == 200
        assert db.updates_for('user_study_plans')[-1]['excluded_modules'] == ['listening', 'pinyin']


class TestPutTemplateOnlyGuard:
    def test_excluded_modules_never_template_only(self, setup):
        client, db, _ = setup()
        r = put(client, template_id=101, excluded_modules=['listening'])
        assert r.status_code == 200
        assert db.rpcs == []  # apply_study_plan_template NOT called


class TestPutRebuild:
    def test_changed_value_recomputes_local_week_then_rebuilds(self, setup):
        client, _, service = setup()
        r = put(client, excluded_modules=['listening'])
        body = r.get_json()
        assert body['session_rebuilt'] is True
        # plan_today is patched to 2026-10-14 (Wed) -> Monday 2026-10-12
        assert [str(c[2]) for c in service.calls.compute] == ['2026-10-12']
        assert service.calls.rebuild == [('user-1', 1)]

    def test_unchanged_value_does_nothing(self, setup):
        client, _, service = setup(excluded=['listening', 'pinyin'])
        r = put(client, excluded_modules=['pinyin', 'listening'])  # same set, other order
        assert r.status_code == 200
        assert r.get_json()['session_rebuilt'] is False
        assert service.calls.compute == [] and service.calls.rebuild == []

    def test_flag_off_recomputes_but_does_not_rebuild(self, monkeypatch):
        db = FakeDB(plan_tables())
        client, service = install(monkeypatch, db, study_plan_enabled=False)
        r = put(client, excluded_modules=['listening'])
        assert r.get_json()['session_rebuilt'] is False
        assert len(service.calls.compute) == 1 and service.calls.rebuild == []

    def test_rebuild_returning_false_is_reported(self, monkeypatch):
        from tests.study_plan_route_harness import make_fake_service_module
        db = FakeDB(plan_tables())
        client, _ = install(monkeypatch, db, service=make_fake_service_module(rebuild_result=False))
        assert put(client, excluded_modules=['listening']).get_json()['session_rebuilt'] is False

    def test_failures_are_best_effort(self, monkeypatch):
        from tests.study_plan_route_harness import make_fake_service_module
        db = FakeDB(plan_tables())
        svc = make_fake_service_module(compute_raises=True, rebuild_raises=True)
        client, _ = install(monkeypatch, db, service=svc)
        r = put(client, excluded_modules=['listening'])
        assert r.status_code == 200
        assert r.get_json()['session_rebuilt'] is False
        assert db.updates_for('user_study_plans')  # the setting was still saved

    def test_no_plan_row_is_400(self, setup):
        client, db, _ = setup()
        db.tables['user_study_plans'] = []
        r = put(client, excluded_modules=['listening'])
        assert r.status_code == 400
