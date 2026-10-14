"""TASK-889: tests and drills credit measured duration to the study-time ledger."""

import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import patch

import pytest

USER = 'test-user-id-123'


class LedgerDB:
    """Fake service client: rpc() records calls; credit_study_time dedupes on
    (kind, source_table, source_id) like the SQL UNIQUE constraint."""

    def __init__(self, test_row=None):
        self.rpcs, self.seen, self.test_row = [], set(), test_row or {'id': 7, 'language_id': 3}

    def rpc(self, name, params):
        self.rpcs.append((name, params))
        data = {}
        if name == 'credit_study_time':
            key = (params['p_kind'], params['p_source_table'], params['p_source_id'])
            data = key not in self.seen
            self.seen.add(key)
        return SimpleNamespace(execute=lambda: SimpleNamespace(data=data))

    def table(self, name):
        chain = self

        class _Q:
            def __getattr__(s, _):
                return lambda *a, **k: s

            def execute(s):
                return SimpleNamespace(data=chain.test_row)
        return _Q()

    def credits(self):
        return [p for n, p in self.rpcs if n == 'credit_study_time']


def window(seconds, end_ago=1):
    end = datetime.now(timezone.utc) - timedelta(seconds=end_ago)
    start = end - timedelta(seconds=seconds)
    return {'started_at': start.isoformat(), 'finished_at': end.isoformat()}


@pytest.fixture
def db(app):
    fake = LedgerDB()
    app.supabase_service = fake
    return fake


def _rpc_ok(attempt_id='att-1'):
    return {'success': True, 'attempt_id': attempt_id, 'score': 1, 'total_questions': 1}


# ---- helper-level --------------------------------------------------------

class TestApplyTimingHelper:
    def _call(self, app, db, body, **kw):
        from routes.tests import _apply_timing_and_progress
        with app.test_request_context():
            _apply_timing_and_progress(db, 'att-1', body, **kw)

    def test_credits_window_seconds(self, app):
        db = LedgerDB()
        self._call(app, db, window(180), user_id=USER, language_id=3)
        (c,) = db.credits()
        assert c['p_kind'] == 'test' and c['p_source_table'] == 'test_attempts'
        assert c['p_source_id'] == 'att-1' and c['p_language_id'] == 3
        assert 179 <= c['p_seconds'] <= 181
        # existing timing RPC still runs first and unchanged
        assert db.rpcs[0][0] == 'apply_attempt_timing_and_progress'

    def test_overlong_window_capped_at_1200(self, app):
        db = LedgerDB()
        self._call(app, db, window(5 * 3600), user_id=USER, language_id=3)
        assert db.credits()[0]['p_seconds'] == 1200

    @pytest.mark.parametrize('body', [{}, {'started_at': None, 'finished_at': None},
                                      {'started_at': 'junk', 'finished_at': 'junk'}])
    def test_no_valid_window_no_credit(self, app, body):
        db = LedgerDB()
        self._call(app, db, body, user_id=USER, language_id=3)
        assert db.credits() == []

    def test_no_user_context_no_credit(self, app):
        db = LedgerDB()
        self._call(app, db, window(60))
        assert db.credits() == []

    def test_repeat_credits_once(self, app):
        db = LedgerDB()
        body = window(60)
        self._call(app, db, body, user_id=USER, language_id=3)
        self._call(app, db, body, user_id=USER, language_id=3)
        assert len(db.credits()) == 2          # both hit the RPC ...
        assert len(db.seen) == 1               # ... the unique key dedupes

    def test_drill_forged_window_not_stored_in_timing_rpc(self, app):
        db = LedgerDB()
        body = {'started_at': 'junk', 'finished_at': '2999-01-01T00:00:00Z'}
        self._call(app, db, body, user_id=USER, language_id=1, kind='drill')
        name, params = db.rpcs[0]
        assert name == 'apply_attempt_timing_and_progress'
        assert params['p_started_at'] is None and params['p_finished_at'] is None
        assert db.credits() == []

    def test_credit_failure_is_non_fatal(self, app):
        db = LedgerDB()
        orig = db.rpc

        def boom(name, params):
            if name == 'credit_study_time':
                raise RuntimeError('db down')
            return orig(name, params)
        db.rpc = boom
        self._call(app, db, window(60), user_id=USER, language_id=3)   # no raise


# ---- route-level ---------------------------------------------------------

class TestTestSubmitRoutes:
    def test_reading_submit_credits_once(self, client, auth_headers, db):
        body = {'responses': [{'question_id': 'q', 'selected_answer': 'a'}],
                'test_mode': 'reading', **window(240)}
        with patch('routes.tests._call_submission_rpc', return_value=_rpc_ok()), \
             patch('routes.tests._update_vocabulary_tracking', return_value=None), \
             patch('routes.tests._build_submission_response', return_value={}), \
             patch('routes.tests._attach_explanations'), \
             patch('routes.tests.DimensionService.get_test_type_id', return_value=1):
            r = client.post('/api/tests/slug/submit', json=body, headers=auth_headers)
        assert r.status_code == 200, r.data
        (c,) = db.credits()
        assert (c['p_user_id'], c['p_language_id'], c['p_kind']) == (USER, 3, 'test')
        assert c['p_source_id'] == 'att-1' and 239 <= c['p_seconds'] <= 241

    def test_reading_submit_without_window_no_credit(self, client, auth_headers, db):
        body = {'responses': [{'question_id': 'q', 'selected_answer': 'a'}]}
        with patch('routes.tests._call_submission_rpc', return_value=_rpc_ok()), \
             patch('routes.tests._update_vocabulary_tracking', return_value=None), \
             patch('routes.tests._build_submission_response', return_value={}), \
             patch('routes.tests._attach_explanations'), \
             patch('routes.tests.DimensionService.get_test_type_id', return_value=1):
            r = client.post('/api/tests/slug/submit', json=body, headers=auth_headers)
        assert r.status_code == 200
        assert db.credits() == []

    def test_pinyin_submit_credits(self, client, auth_headers, db):
        db.test_row = {'id': 7, 'language_id': 1}
        body = {'correct_chars': 3, 'total_chars': 4, **window(90)}
        with patch('routes.tests._call_pinyin_submission_rpc', return_value=_rpc_ok('att-p')), \
             patch('routes.tests.DimensionService.get_test_type_id', return_value=9):
            r = client.post('/api/tests/slug/submit-pinyin', json=body, headers=auth_headers)
        assert r.status_code == 200, r.data
        (c,) = db.credits()
        assert c['p_kind'] == 'test' and c['p_source_id'] == 'att-p' and c['p_language_id'] == 1

    def test_forged_future_window_rejected_no_credit(self, client, auth_headers, db):
        future = datetime.now(timezone.utc) + timedelta(hours=2)
        body = {'responses': [{'question_id': 'q', 'selected_answer': 'a'}],
                'started_at': (future - timedelta(hours=1)).isoformat(),
                'finished_at': future.isoformat()}
        r = client.post('/api/tests/slug/submit', json=body, headers=auth_headers)
        assert r.status_code == 400
        assert db.credits() == []


class TestDrillRoutes:
    def test_classifier_drill_credits_kind_drill(self, client, auth_headers, db):
        body = {'language_id': 1, 'correct_items': 4, 'total_items': 5, **window(100)}
        with patch('routes.classifier_drill.submit_session', return_value=_rpc_ok('att-c')), \
             patch('routes.classifier_drill.DimensionService.get_test_type_id', return_value=14):
            r = client.post('/api/classifier-drill/submit', json=body, headers=auth_headers)
        assert r.status_code == 200, r.data
        (c,) = db.credits()
        assert (c['p_kind'], c['p_source_table'], c['p_source_id'], c['p_language_id']) == \
            ('drill', 'test_attempts', 'att-c', 1)
        assert 99 <= c['p_seconds'] <= 101

    def test_counter_drill_credits_kind_drill_and_caps(self, client, auth_headers, db):
        body = {'language_id': 3, 'correct_items': 4, 'total_items': 5, **window(4 * 3600)}
        with patch('routes.counter_drill.submit_session', return_value=_rpc_ok('att-k')), \
             patch('routes.counter_drill.DimensionService.get_test_type_id', return_value=15):
            r = client.post('/api/counter-drill/submit', json=body, headers=auth_headers)
        assert r.status_code == 200, r.data
        (c,) = db.credits()
        assert c['p_kind'] == 'drill' and c['p_source_id'] == 'att-k' and c['p_seconds'] == 1200

    def test_drill_without_window_no_credit(self, client, auth_headers, db):
        body = {'language_id': 3, 'correct_items': 4, 'total_items': 5, 'time_taken': 999}
        with patch('routes.counter_drill.submit_session', return_value=_rpc_ok('att-k')), \
             patch('routes.counter_drill.DimensionService.get_test_type_id', return_value=15):
            r = client.post('/api/counter-drill/submit', json=body, headers=auth_headers)
        assert r.status_code == 200
        assert db.credits() == []
