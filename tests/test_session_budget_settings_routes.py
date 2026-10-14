"""TASK-866 (session-budget-settings) — budget_scope / new_words_per_day on
GET/PUT /api/study-plan. See tests/study_plan_route_harness.py for the fakes.
"""

import pytest

from tests.study_plan_route_harness import (
    ZH_AVAILABLE, FakeDB, install, make_fake_service_module, plan_tables,
)

ALL_BUT_PRACTICE_AND_FLASH = [m for m in ZH_AVAILABLE if m not in ('practice', 'flashcards')]


def put(client, **body):
    body.setdefault('language_id', 1)
    return client.put('/api/study-plan', json=body)


@pytest.fixture
def setup(monkeypatch):
    def _make(service=None, **kwargs):
        db = FakeDB(plan_tables(**kwargs))
        client, svc = install(monkeypatch, db, service=service)
        return client, db, svc
    return _make


class TestBudgetScopeValidation:
    @pytest.mark.parametrize('value', ['both', '', None, 1, True])
    def test_bad_scope_is_400(self, setup, value):
        client, _, _ = setup()
        r = put(client, budget_scope=value)
        assert r.status_code == 400
        assert r.get_json()['error'] == "budget_scope must be 'tests_and_review' or 'tests_only'"

    @pytest.mark.parametrize('value', ['tests_only', 'tests_and_review'])
    def test_valid_scope_saved(self, setup, value):
        client, db, _ = setup(scope='tests_and_review' if value == 'tests_only' else 'tests_only')
        r = put(client, budget_scope=value)
        assert r.status_code == 200
        assert db.updates_for('user_study_plans')[-1]['budget_scope'] == value


class TestNewWordsValidation:
    @pytest.mark.parametrize('value', [-1, 51, 5.0, 2.5, '5', True, False, None, [5]])
    def test_bad_values_are_400(self, setup, value):
        client, _, _ = setup()
        r = put(client, new_words_per_day=value)
        assert r.status_code == 400
        assert r.get_json()['error'] == 'new_words_per_day must be int in [0, 50]'

    @pytest.mark.parametrize('value', [0, 1, 50])
    def test_bounds_accepted(self, setup, value):
        client, db, _ = setup(npd=7)
        r = put(client, new_words_per_day=value)
        assert r.status_code == 200
        assert db.updates_for('user_study_plans')[-1]['new_words_per_day'] == value


class TestMergedStateRules:
    def test_new_words_zero_with_every_module_stored_excluded_is_400(self, setup):
        # Stored: everything excluded, kept legal only by new words > 0.
        client, _, _ = setup(excluded=list(ZH_AVAILABLE), npd=5)
        r = put(client, new_words_per_day=0)
        assert r.status_code == 400
        assert r.get_json()['error'] == 'at least one module must remain included'

    def test_tests_only_needs_a_test_or_surface_module(self, setup):
        client, _, _ = setup(excluded=ALL_BUT_PRACTICE_AND_FLASH + ['flashcards'], npd=5)
        r = put(client, budget_scope='tests_only')
        assert r.status_code == 400
        assert r.get_json()['error'] == (
            'tests_only scope needs at least one test or surface module included')

    def test_excluding_last_test_module_under_stored_tests_only_is_400(self, setup):
        client, _, _ = setup(scope='tests_only', npd=5)
        r = put(client, excluded_modules=[m for m in ZH_AVAILABLE if m != 'practice'])
        assert r.status_code == 400
        assert 'tests_only scope' in r.get_json()['error']

    def test_review_off_with_new_words_is_allowed(self, setup):
        client, db, _ = setup(npd=5)
        r = put(client, excluded_modules=['practice'])
        assert r.status_code == 200
        assert db.updates_for('user_study_plans')[-1]['excluded_modules'] == ['practice']

    def test_tests_only_with_review_off_and_new_words_is_allowed(self, setup):
        client, _, _ = setup(excluded=['practice'], npd=5)
        assert put(client, budget_scope='tests_only').status_code == 200

    def test_all_modules_excluded_with_tests_only_is_400_even_with_new_words(self, setup):
        client, _, _ = setup(npd=5)
        r = put(client, excluded_modules=list(ZH_AVAILABLE), budget_scope='tests_only')
        assert r.status_code == 400
        assert 'tests_only scope' in r.get_json()['error']


class TestRecomputeOnChange:
    @pytest.mark.parametrize('body', [
        {'budget_scope': 'tests_only'},
        {'new_words_per_day': 9},
        {'excluded_modules': ['pinyin']},
    ])
    def test_each_field_triggers_recompute_and_rebuild(self, setup, body):
        client, _, svc = setup()
        r = put(client, **body)
        assert r.status_code == 200
        assert r.get_json()['session_rebuilt'] is True
        assert [str(c[2]) for c in svc.calls.compute] == ['2026-10-12']
        assert svc.calls.rebuild == [('user-1', 1)]

    @pytest.mark.parametrize('body', [
        {'budget_scope': 'tests_and_review'},
        {'new_words_per_day': 5},
        {'excluded_modules': []},
    ])
    def test_same_values_do_not(self, setup, body):
        client, _, svc = setup()
        r = put(client, **body)
        assert r.status_code == 200
        assert r.get_json()['session_rebuilt'] is False
        assert svc.calls.compute == [] and svc.calls.rebuild == []

    def test_daily_minutes_only_change_does_not_recompute_here(self, setup):
        client, _, svc = setup()
        r = put(client, daily_minutes=45)
        assert r.status_code == 200
        assert r.get_json()['session_rebuilt'] is False
        assert svc.calls.compute == []

    def test_updated_fields_lists_written_keys(self, setup):
        client, _, _ = setup()
        r = put(client, budget_scope='tests_only', new_words_per_day=9)
        assert set(r.get_json()['updated_fields']) == {'budget_scope', 'new_words_per_day'}


class TestNewRowDefault:
    def _client(self, monkeypatch, existed):
        calls = {'n': 0}

        def plan_rows(q):
            names = [n for n, _ in q.ops]
            if 'select' in names and 'update' not in names:
                sel = [a[0] for n, a in q.ops if n == 'select'][0]
                calls['n'] += 1
                if sel == 'user_id':
                    return [{'user_id': 'user-1'}] if existed else []
                return [{'daily_minutes': 45}]
            return [{}]

        tables = plan_tables()
        tables['user_study_plans'] = plan_rows
        db = FakeDB(tables)
        client, svc = install(monkeypatch, db)
        return client, db, svc

    def test_new_row_gets_minutes_div_6_words_per_day(self, monkeypatch):
        client, db, svc = self._client(monkeypatch, existed=False)
        r = put(client, template_id=101)
        assert r.status_code == 200
        assert db.rpcs and db.rpcs[0][0] == 'apply_study_plan_template'
        assert {'new_words_per_day': 7} in db.updates_for('user_study_plans')  # 45 // 6
        assert len(svc.calls.compute) == 1  # template seeding still runs

    def test_existing_row_is_not_touched(self, monkeypatch):
        client, db, _ = self._client(monkeypatch, existed=True)
        r = put(client, template_id=101)
        assert r.status_code == 200
        assert db.updates_for('user_study_plans') == []

    def test_minimum_is_one_word(self, monkeypatch):
        calls = []

        def plan_rows(q):
            names = [n for n, _ in q.ops]
            sel = [a[0] for n, a in q.ops if n == 'select']
            if 'update' in names:
                return [{}]
            calls.append(sel)
            if sel and sel[0] == 'user_id':
                return [] if len(calls) == 1 else [{'user_id': 'user-1'}]
            return [{'daily_minutes': 10}]

        tables = plan_tables()
        tables['user_study_plans'] = plan_rows
        db = FakeDB(tables)
        client, _ = install(monkeypatch, db)
        put(client, template_id=101)
        assert {'new_words_per_day': 1} in db.updates_for('user_study_plans')  # max(1, 10 // 6)


class TestGetShape:
    def test_card_inputs_present(self, setup):
        client, _, _ = setup(npd=5, targets={'new_words_shortfall': 2})
        body = client.get('/api/study-plan?language_id=1').get_json()
        assert body['minutes_per_new_word'] == 3.0
        assert body['typical_day'] == {'practice_room_min_per_day': 9.0, 'review_min_per_day': 4.0}
        assert body['governor'] == {
            'level': 'normal', 'overdue_items': 0, 'overdue_minutes': 0.0, 'threshold_minutes': 3.0,
        }
        f = body['forecast']
        assert f['reviews_per_new_word_30d'] == 7 and f['item_seconds'] == 20.0
        assert f['min_per_day'] == pytest.approx(11.67, abs=0.01)  # 5 * 7 * 20 / 60
        assert body['today_new_words_shortfall'] == 2
        assert body['plan']['budget_scope'] == 'tests_and_review'
        assert body['plan']['new_words_per_day'] == 5

    def test_shortfall_null_without_daily_load_row(self, setup):
        client, _, _ = setup()
        assert client.get('/api/study-plan?language_id=1').get_json()['today_new_words_shortfall'] is None

    def test_typical_day_null_without_current_week(self, setup):
        client, _, _ = setup(week=False)
        body = client.get('/api/study-plan?language_id=1').get_json()
        assert body['current_week'] is None and body['typical_day'] is None

    def test_governor_reduced_is_passed_through(self, setup):
        svc = make_fake_service_module()
        svc.get_review_governor = lambda *a: {
            'level': 'reduced', 'overdue_items': 24, 'overdue_minutes': 8.0,
            'threshold_minutes': 4.0, 'item_seconds': 30.0,
        }
        client, _, _ = setup(service=svc)
        body = client.get('/api/study-plan?language_id=1').get_json()
        assert body['governor']['level'] == 'reduced' and body['governor']['overdue_items'] == 24
        assert body['forecast']['item_seconds'] == 30.0

    def test_enrichment_failures_degrade_to_normal(self, setup):
        svc = make_fake_service_module()

        def boom(*a, **k):
            raise RuntimeError('rpc down')

        svc.get_review_governor = boom
        svc.typical_day_inputs = boom
        svc.get_minutes_per_new_word = boom
        svc.review_forecast_min_per_day = boom
        client, _, _ = setup(service=svc)
        r = client.get('/api/study-plan?language_id=1')
        assert r.status_code == 200
        body = r.get_json()
        assert body['governor']['level'] == 'normal'
        assert body['typical_day'] is None
        assert body['minutes_per_new_word'] == 3.0
        assert body['forecast']['min_per_day'] == 0.0
