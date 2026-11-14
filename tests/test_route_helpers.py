"""Route helpers: api_errors, json_body, require_language_id, get_db."""

import pytest
from flask import Flask

from utils.responses import api_errors, api_success
from utils.validation import json_body, require_language_id
from web.errors import register_error_handlers


@pytest.fixture
def client():
    app = Flask(__name__)
    app.config['TESTING'] = True

    @app.route('/api/named')
    @api_errors("Failed to load things")
    def named():
        raise RuntimeError('boom')

    @app.route('/api/unnamed')
    def unnamed():
        raise RuntimeError('boom')

    @app.route('/api/body', methods=['POST'])
    def body():
        return api_success({'body': json_body()})

    @app.route('/api/silent', methods=['POST'])
    def silent():
        return api_success({'body': json_body(silent=True)})

    @app.route('/api/lang')
    @require_language_id
    def lang(language_id):
        return api_success({'language_id': language_id})

    register_error_handlers(app)
    return app.test_client()


def test_api_errors_names_the_failure_in_the_standard_envelope(client):
    r = client.get('/api/named')
    assert r.status_code == 500
    assert r.get_json() == {'status': 'error', 'error': 'Failed to load things',
                            'error_code': 'SERVER_ERROR'}


def test_unnamed_failure_keeps_the_generic_message(client):
    r = client.get('/api/unnamed')
    assert r.status_code == 500
    assert r.get_json()['error'] == 'Internal server error'


def test_json_body_returns_the_object_and_empty_for_no_body(client):
    assert client.post('/api/body', json={'a': 1}).get_json()['body'] == {'a': 1}
    assert client.post('/api/body', data='null',
                       content_type='application/json').get_json()['body'] == {}


def test_json_body_rejects_bad_input_with_a_4xx(client):
    bad = client.post('/api/body', data='{nope', content_type='application/json')
    assert bad.status_code == 400 and bad.get_json()['status'] == 'error'
    assert client.post('/api/body', data='a=1').status_code == 415
    not_object = client.post('/api/body', json=[1, 2])
    assert not_object.status_code == 400
    assert not_object.get_json()['error'] == 'Request body must be a JSON object'


def test_silent_json_body_treats_unreadable_input_as_empty(client):
    assert client.post('/api/silent', data='{nope',
                       content_type='application/json').get_json()['body'] == {}
    assert client.post('/api/silent', data='a=1').get_json()['body'] == {}
    assert client.post('/api/silent', json=[1]).status_code == 400


@pytest.mark.parametrize('query', ['', '?language_id=', '?language_id=0', '?language_id=abc'])
def test_require_language_id_rejects(client, query):
    r = client.get('/api/lang' + query)
    assert r.status_code == 400
    assert r.get_json() == {'status': 'error', 'error': 'language_id required',
                            'error_code': 'BAD_REQUEST'}


def test_require_language_id_passes_the_int(client):
    assert client.get('/api/lang?language_id=3').get_json()['language_id'] == 3


def test_get_db_is_the_factory_service_client(monkeypatch):
    from routes.common import get_db
    sentinel = object()
    monkeypatch.setattr('services.supabase_factory.get_supabase_admin', lambda: sentinel)
    assert get_db() is sentinel


def test_route_failure_reaches_the_client_with_its_message(monkeypatch):
    """A real route: the handler-wide wrapper is gone, the message is not."""
    import middleware.auth as auth
    import routes.flashcards as fc
    monkeypatch.setattr(auth, '_authenticate', lambda token: ({'sub': 'user-1'}, None))

    def boom():
        raise RuntimeError('db down')
    monkeypatch.setattr(fc, 'get_db', boom)
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.register_blueprint(fc.flashcards_bp, url_prefix='/api/flashcards')
    register_error_handlers(app)
    r = app.test_client().get('/api/flashcards/due?language_id=1',
                              headers={'Authorization': 'Bearer t'})
    assert r.status_code == 500
    assert r.get_json()['error'] == 'Failed to fetch flashcards'
