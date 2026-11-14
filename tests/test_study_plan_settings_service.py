"""PUT/GET /api/study-plan paths that sit behind services/study_plan_settings.py
and were not pinned before the route was split: the template checks, the
missing-plan answer, the prestudy_mode column fallback, and a GET whose
optional reads fail. See tests/study_plan_route_harness.py for the fakes.
"""

import pytest

from tests.study_plan_route_harness import FakeDB, FakeQuery, install, plan_tables


def put(client, **body):
    body.setdefault('language_id', 1)
    return client.put('/api/study-plan', json=body)


@pytest.fixture
def setup(monkeypatch):
    def _make(db=None, **kwargs):
        db = db or FakeDB(plan_tables(**kwargs))
        client, svc = install(monkeypatch, db)
        return client, db, svc
    return _make


class TestTemplateWithOtherFields:
    def test_unknown_template_is_400(self, setup):
        client, db, _ = setup(templates=[])
        r = put(client, template_id=999, timezone='UTC')
        assert r.status_code == 400
        assert r.get_json()['error'] == "unknown template_id=999"
        assert db.updates_for('user_study_plans') == []

    def test_template_of_another_language_is_400(self, setup):
        client, _, _ = setup(templates=[{'template_id': 101, 'language_id': 2, 'daily_minutes': 30}])
        r = put(client, template_id=101, timezone='UTC')
        assert r.status_code == 400
        assert r.get_json()['error'] == "template language does not match language_id"

    def test_daily_minutes_is_copied_from_the_template(self, setup):
        client, db, _ = setup()
        r = put(client, template_id=101, timezone='Asia/Tokyo')
        assert r.status_code == 200
        assert db.updates_for('user_study_plans') == [
            {'template_id': 101, 'daily_minutes': 30, 'timezone': 'Asia/Tokyo'}]
        assert r.get_json()['updated_fields'] == ['template_id', 'daily_minutes', 'timezone']
        assert db.rpcs == []

    def test_an_explicit_daily_minutes_wins_over_the_template(self, setup):
        client, db, _ = setup()
        r = put(client, template_id=101, daily_minutes=45)
        assert r.status_code == 200
        assert db.updates_for('user_study_plans') == [{'daily_minutes': 45, 'template_id': 101}]

    def test_an_invalid_field_is_rejected_before_the_template_is_read(self, setup):
        client, db, _ = setup()
        r = put(client, template_id=101, timezone='nowhere')
        assert r.status_code == 400
        assert db.executed == []


class TestUpdateWithoutAPlan:
    def test_no_plan_row_is_400_with_the_template_hint(self, setup):
        tables = plan_tables()
        tables['user_study_plans'] = []
        client, db, _ = setup(db=FakeDB(tables))
        r = put(client, daily_minutes=30)
        assert r.status_code == 400
        assert r.get_json()['error'].startswith("no plan exists; PUT with template_id only")
        assert db.updates_for('user_study_plans') == []

    def test_no_editable_fields_is_400(self, setup):
        client, db, _ = setup()
        r = put(client)
        assert r.status_code == 400
        assert r.get_json()['error'] == "no editable fields in request body"
        assert db.executed == []


class _NoPrestudyColumnDB(FakeDB):
    """user_study_plans has no prestudy_mode column (migration not applied)."""

    def table(self, name):
        query = FakeQuery(self, name)
        if name == 'user_study_plans':
            run = query.execute

            def execute():
                payloads = [a[0] for n, a in query.ops if n == 'update']
                if payloads and 'prestudy_mode' in payloads[0]:
                    raise RuntimeError("column prestudy_mode does not exist")
                return run()
            query.execute = execute
        return query


class TestPrestudyModeColumnMissing:
    def test_prestudy_mode_alone_is_409(self, setup):
        client, db, _ = setup(db=_NoPrestudyColumnDB(plan_tables()))
        r = put(client, prestudy_mode='ask')
        assert r.status_code == 409
        assert r.get_json()['error_code'] == 'PRESTUDY_MODE_UNAVAILABLE'
        assert db.updates_for('user_study_plans') == []

    def test_the_other_fields_are_still_saved(self, setup):
        client, db, _ = setup(db=_NoPrestudyColumnDB(plan_tables()))
        r = put(client, prestudy_mode='ask', daily_minutes=40)
        assert r.status_code == 200
        assert r.get_json()['updated_fields'] == ['daily_minutes']
        assert db.updates_for('user_study_plans') == [{'daily_minutes': 40}]


class TestGet:
    def test_no_plan_is_404(self, setup):
        tables = plan_tables()
        tables['user_study_plans'] = []
        client, _, _ = setup(db=FakeDB(tables))
        assert client.get('/api/study-plan?language_id=1').status_code == 404

    def test_each_read_is_made_once(self, setup):
        client, db, _ = setup(targets={'new_words_shortfall': 1})
        assert client.get('/api/study-plan?language_id=1').status_code == 200
        assert sorted(t for t, _ in db.executed) == [
            'daily_test_loads', 'dim_study_plan_templates', 'user_study_plans', 'weekly_plan_states']

    def test_failed_optional_reads_degrade_only_their_part(self, setup):
        def boom(_query):
            raise RuntimeError('db down')

        tables = plan_tables()
        tables['dim_study_plan_templates'] = boom
        tables['daily_test_loads'] = boom
        client, _, _ = setup(db=FakeDB(tables))
        r = client.get('/api/study-plan?language_id=1')
        assert r.status_code == 200
        body = r.get_json()
        assert body['available_modules'] == ['practice']
        assert body['today_new_words_shortfall'] is None
        assert body['current_week']['total_weekly_minutes'] == 210
        assert body['minutes_per_new_word'] == 3.0

    def test_a_failed_week_read_fails_the_request(self, setup):
        def boom(_query):
            raise RuntimeError('db down')

        tables = plan_tables()
        tables['weekly_plan_states'] = boom
        client, _, _ = setup(db=FakeDB(tables))
        assert client.get('/api/study-plan?language_id=1').status_code == 500
