"""routes/practice.py forwards the optional-tail flag (session-budget-settings, TASK-872).

GET /api/practice/session?tail=1  -> get_session(tail=True)
POST /api/practice/attempt {is_tail|tail} -> record_attempt_with_updates(is_tail=True)
"""

import pytest
from flask import Flask


class _FakeService:
    def __init__(self):
        self.session_kwargs = None
        self.attempt_kwargs = None

    def get_session(self, **kw):
        self.session_kwargs = kw
        return {'items': [], 'tail': bool(kw.get('tail'))}

    def record_attempt_with_updates(self, **kw):
        self.attempt_kwargs = kw
        return {'ok': True}


@pytest.fixture
def client_and_service(monkeypatch):
    import middleware.auth as auth
    import routes.practice as practice
    import services.practice_session_service as pss

    svc = _FakeService()
    monkeypatch.setattr(auth, '_authenticate', lambda token: ({'sub': 'user-1'}, None))
    monkeypatch.setattr(pss, 'get_practice_session_service', lambda: svc)
    monkeypatch.setattr(practice, '_grade_typed_if_needed', lambda eid, data: None)
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.register_blueprint(practice.practice_bp, url_prefix='/api/practice')
    client = app.test_client()
    client.environ_base['HTTP_AUTHORIZATION'] = 'Bearer fake'
    return client, svc


def test_session_without_tail_flag_is_a_main_session(client_and_service):
    client, svc = client_and_service
    assert client.get('/api/practice/session?language_id=1&mode=maintenance&minutes=5').status_code == 200
    assert svc.session_kwargs['tail'] is False


def test_session_tail_flag_is_forwarded(client_and_service):
    client, svc = client_and_service
    resp = client.get('/api/practice/session?language_id=1&mode=maintenance&minutes=5&tail=1')
    assert resp.status_code == 200
    assert svc.session_kwargs['tail'] is True


@pytest.mark.parametrize('body_extra, expected', [
    ({}, False),
    ({'is_tail': True}, True),
    ({'tail': True}, True),
    ({'is_tail': False}, False),
])
def test_attempt_tail_flag_is_forwarded(client_and_service, body_extra, expected):
    client, svc = client_and_service
    body = {'exercise_id': 'ex-1', 'is_correct': True, 'session_mode': 'acquisition',
            'language_id': 1, **body_extra}
    assert client.post('/api/practice/attempt', json=body).status_code == 200
    assert svc.attempt_kwargs['is_tail'] is expected
