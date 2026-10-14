"""TASK-882 route hardening: answer keys, timing/count bounds, gate trust."""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest
from flask import Flask

from services import attempt_timing as at
from services.vocabulary_ladder import battery_token as bt

NOW = datetime(2026, 10, 14, 12, 0, tzinfo=timezone.utc)


# --------------------------------------------------------------- timing unit
def test_window_absent_ok():
    assert at.validate_attempt_window(None, None, NOW) == (None, None)


@pytest.mark.parametrize('s,f', [
    ('2026-10-14T11:55:00Z', None),                    # only one
    ('garbage', '2026-10-14T11:56:00Z'),               # unparseable
    ('2026-10-14T11:56:00Z', '2026-10-14T11:55:00Z'),  # reversed
    ('2026-10-14T11:59:00Z', '2026-10-14T13:00:00Z'),  # future
    (123, 456),                                        # wrong type
])
def test_window_rejections(s, f):
    with pytest.raises(at.AttemptTimingError):
        at.validate_attempt_window(s, f, NOW)


def test_window_clamped_to_cap():
    s, f = at.validate_attempt_window('2026-10-14T08:00:00Z', '2026-10-14T11:59:00Z', NOW)
    dur = (datetime.fromisoformat(f) - datetime.fromisoformat(s)).total_seconds()
    assert dur == at.MAX_CREDITED_ATTEMPT_SECONDS


def test_window_normal_untouched():
    s, f = at.validate_attempt_window('2026-10-14T11:55:00Z', '2026-10-14T11:58:00Z', NOW)
    assert (datetime.fromisoformat(f) - datetime.fromisoformat(s)).total_seconds() == 180


@pytest.mark.parametrize('c,t', [(5, 3), (-1, 3), (1, 0), (1.5, 3), (True, 3), ('1', 3), (1, None)])
def test_counts_rejections(c, t):
    with pytest.raises(at.AttemptTimingError):
        at.validate_counts(c, t, 'c', 't')


def test_counts_ok_and_clamps():
    assert at.validate_counts(3, 3, 'c', 't') == (3, 3)
    assert at.clamp_time_taken(10**9) == at.MAX_CREDITED_ATTEMPT_SECONDS
    assert at.clamp_time_taken(-5) == 0
    assert at.clamp_time_taken_ms(10**9) == at.MAX_TIME_TAKEN_MS
    assert at.clamp_time_taken_ms(-1) is None and at.clamp_time_taken_ms('x') is None


# ------------------------------------------------------------- app fixtures
@pytest.fixture
def app(monkeypatch):
    import middleware.auth as auth
    monkeypatch.setattr(auth, '_authenticate', lambda token: ({'sub': 'user-1'}, None))
    from routes.tests import tests_bp
    from routes.vocab_dojo import vocab_dojo_bp
    a = Flask(__name__)
    a.config.update(TESTING=True, SECRET_KEY='k')
    a.supabase_service = MagicMock()
    a.register_blueprint(tests_bp, url_prefix='/api/tests')
    a.register_blueprint(vocab_dojo_bp, url_prefix='/api/vocab-dojo')
    return a


@pytest.fixture
def client(app):
    c = app.test_client()
    c.environ_base['HTTP_AUTHORIZATION'] = 'Bearer x'
    return c


def _chain(data):
    m = MagicMock()
    for name in ('select', 'eq', 'order', 'in_', 'single', 'limit', 'gte'):
        getattr(m, name).return_value = m
    m.execute.return_value = MagicMock(data=data)
    return m


# ------------------------------------------------------------- answer keys
def test_fetch_route_does_not_select_answer_fields(app, client):
    svc = app.supabase_service
    seen = []
    test_row = [{'id': 't1', 'slug': 's', 'dim_languages': {}}]

    def table(name):
        if name == 'questions':
            m = _chain([{'id': 'q1', 'question_text': 'Q'}])
            orig = m.select
            def sel(cols, *a, **k):
                seen.append(cols)
                return m
            m.select = sel
            return m
        if name == 'tests':
            return _chain(test_row)
        return _chain([])
    svc.table.side_effect = table
    resp = client.get('/api/tests/test/s')
    assert resp.status_code == 200
    assert seen and 'answer' not in seen[0].replace('answer_explanation', 'X')
    assert 'answer_explanation' not in seen[0]
    body = resp.get_data(as_text=True)
    assert 'answer_explanation' not in body and '"answer"' not in body


def test_test_service_slug_payload_has_no_answer():
    from services.test_service import TestService
    admin = MagicMock()
    def table(name):
        if name == 'tests':
            return _chain([{'id': 1, 'slug': 's', 'language_id': 1, 'difficulty': 1}])
        return _chain([{'id': 'q1', 'question_text': 'Q', 'choices': '["a","b"]',
                        'correct_answer': 'a', 'answer': 'a'}])
    admin.table.side_effect = table
    client = MagicMock()
    out = TestService(supabase_client=client, supabase_admin=admin).get_test_by_slug('s')
    assert 'answer' not in out['questions'][0]
    client.table.assert_not_called()  # anon client no longer used for reads


def test_submit_returns_explanations(app, client, monkeypatch):
    import routes.tests as rt
    svc = app.supabase_service
    svc.table.side_effect = lambda n: _chain({'id': 't1', 'language_id': 1} if n == 'tests'
                                              else [{'id': 'q1', 'answer_explanation': 'because'}])
    monkeypatch.setattr(rt.DimensionService, 'get_test_type_id', staticmethod(lambda m: 1))
    monkeypatch.setattr(rt, '_call_submission_rpc', lambda *a, **k: {
        'success': True, 'attempt_id': 'a1', 'score': 1, 'total_questions': 1,
        'question_results': [{'question_id': 'q1', 'correct_answer': 'a',
                              'selected_answer': 'a', 'is_correct': True}]})
    monkeypatch.setattr(rt, '_update_vocabulary_tracking', lambda *a, **k: None)
    monkeypatch.setattr(rt, '_apply_timing_and_progress', lambda *a, **k: None)
    resp = client.post('/api/tests/s/submit', json={
        'responses': [{'question_id': 'q1', 'selected_answer': 'a'}]})
    assert resp.status_code == 200
    qr = resp.get_json()['result']['question_results'][0]
    assert qr['answer_explanation'] == 'because' and qr['correct_answer'] == 'a'


# -------------------------------------------------------- submit rejections
def test_submit_rejects_forged_window(app, client):
    resp = client.post('/api/tests/s/submit', json={
        'responses': [{'question_id': 'q1', 'selected_answer': 'a'}],
        'started_at': '2026-10-14T11:00:00Z', 'finished_at': '2020-01-01T00:00:00Z'})
    assert resp.status_code == 400
    app.supabase_service.rpc.assert_not_called()


@pytest.mark.parametrize('route,body', [
    ('submit-pinyin', {'correct_chars': 9, 'total_chars': 3}),
    ('submit-pinyin', {'correct_chars': 1, 'total_chars': 0}),
    ('submit-pinyin', {'correct_chars': 1, 'total_chars': 2,
                       'started_at': 'x', 'finished_at': 'y'}),
    ('submit-pitch-accent', {'correct_units': -1, 'total_units': 3}),
    ('submit-pitch-accent', {'correct_units': 5, 'total_units': 3}),
])
def test_count_routes_reject(app, client, route, body):
    assert client.post(f'/api/tests/s/{route}', json=body).status_code == 400
    app.supabase_service.rpc.assert_not_called()


def test_daily_load_complete_requires_attempt(app, client, monkeypatch):
    import routes.tests as rt
    from services.test_service import NoMatchingAttemptError
    svc = MagicMock()
    svc.mark_daily_test_complete.side_effect = NoMatchingAttemptError('no')
    monkeypatch.setattr(rt, 'get_test_service', lambda: svc)
    resp = client.post('/api/tests/daily-load/complete', json={'test_id': 't', 'language_id': 1})
    assert resp.status_code == 400


def test_mark_daily_complete_service_checks_attempt(monkeypatch):
    import services.test_service as ts
    from services.test_service import NoMatchingAttemptError, TestService
    monkeypatch.setattr(ts, 'plan_today_iso', lambda *a, **k: '2026-10-14')
    monkeypatch.setattr(ts, 'plan_timezone', lambda *a, **k: 'UTC')
    admin = MagicMock()
    admin.table.side_effect = lambda n: _chain([])
    with pytest.raises(NoMatchingAttemptError):
        TestService(supabase_admin=admin).mark_daily_test_complete('u', 1, 't')


# ------------------------------------------------------------- gate trust
def _sense_patch(monkeypatch, exercises):
    import services.vocabulary_ladder.ladder_service as ls
    class FakeLadder:
        def assemble_gate(self, *a): return exercises
        def assemble_stress_test(self, *a): return exercises
        def pass_gate(self, uid, sid, gate): return {'gate': gate, 'passed': True}
        def graduate(self, uid, sid, score, lang): return {'word_state': 'mastered'}
    monkeypatch.setattr(ls, 'LadderService', FakeLadder)


def _ex(i):
    # Real LadderService._fetch_exercises_for_levels shape: id lives under 'exercise_id'.
    return {'exercise_id': i, 'exercise_type': 'multiple_choice', 'content': {}}


def test_gate_flow_server_derives_pass(client, monkeypatch):
    exs = [_ex('e1'), _ex('e2'), _ex('e3')]
    _sense_patch(monkeypatch, exs)
    r = client.post('/api/vocab-dojo/gate', json={'sense_id': 1, 'language_id': 1, 'gate_name': 'gate_a'})
    tok = r.get_json()['battery_token']
    bad = client.post('/api/vocab-dojo/gate/result', json={
        'sense_id': 1, 'gate_name': 'gate_a', 'passed': True, 'battery_token': tok,
        'results': [{'exercise_id': 'e1', 'is_correct': True}]})
    assert bad.get_json()['passed'] is False   # forged passed ignored (1/3)
    good = client.post('/api/vocab-dojo/gate/result', json={
        'sense_id': 1, 'gate_name': 'gate_a', 'battery_token': tok,
        'results': [{'exercise_id': 'e1', 'is_correct': True},
                    {'exercise_id': 'e2', 'is_correct': True}]})
    assert good.get_json()['passed'] is True


def test_gate_result_rejects_bare_passed_and_foreign_items(client, monkeypatch):
    _sense_patch(monkeypatch, [_ex('e1')])
    assert client.post('/api/vocab-dojo/gate/result', json={
        'sense_id': 1, 'gate_name': 'gate_a', 'passed': True}).status_code == 400
    tok = client.post('/api/vocab-dojo/gate', json={
        'sense_id': 1, 'language_id': 1, 'gate_name': 'gate_a'}).get_json()['battery_token']
    for results in ([{'exercise_id': 'zzz', 'is_correct': True}],
                    [{'exercise_id': 'e1', 'is_correct': True}] * 2):
        assert client.post('/api/vocab-dojo/gate/result', json={
            'sense_id': 1, 'gate_name': 'gate_a', 'battery_token': tok,
            'results': results}).status_code == 400
    # token for another sense / gate is refused
    assert client.post('/api/vocab-dojo/gate/result', json={
        'sense_id': 2, 'gate_name': 'gate_a', 'battery_token': tok,
        'results': []}).status_code == 400


def test_stress_flow_server_derives_score(client, monkeypatch):
    exs = [_ex(f'e{i}') for i in range(8)]
    _sense_patch(monkeypatch, exs)
    tok = client.post('/api/vocab-dojo/stress-test', json={
        'sense_id': 1, 'language_id': 1}).get_json()['battery_token']
    low = client.post('/api/vocab-dojo/stress-test/result', json={
        'sense_id': 1, 'language_id': 1, 'score': 1.0, 'passed': True, 'battery_token': tok,
        'results': [{'exercise_id': 'e0', 'is_correct': True}]})
    d = low.get_json()
    assert d['passed'] is False and d['stress_test_score'] == 0.125
    high = client.post('/api/vocab-dojo/stress-test/result', json={
        'sense_id': 1, 'language_id': 1, 'battery_token': tok,
        'results': [{'exercise_id': f'e{i}', 'is_correct': i < 6} for i in range(8)]})
    assert high.get_json()['word_state'] == 'mastered'


def test_battery_token_expired_and_tampered(app, monkeypatch):
    with app.app_context():
        tok = bt.issue('u', 'gate', 1, 'gate_a', ['e1'])
        assert bt.score(tok, 'u', 'gate', 1, 'gate_a', [{'exercise_id': 'e1', 'is_correct': True}]) == (1, 1)
        with pytest.raises(bt.BatteryError):
            bt.score(tok + 'x', 'u', 'gate', 1, 'gate_a', [])
        with pytest.raises(bt.BatteryError):
            bt.score(tok, 'other-user', 'gate', 1, 'gate_a', [])
        monkeypatch.setattr(bt, 'BATTERY_MAX_AGE_SECONDS', -1)
        with pytest.raises(bt.BatteryError):
            bt.score(tok, 'u', 'gate', 1, 'gate_a', [])
