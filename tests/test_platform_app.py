"""App wiring: single build, page table, headers, body cap, error envelopes."""

import importlib
import json
import sys
from unittest.mock import MagicMock

import pytest
from flask import url_for

from models.requests import VOCAB_EXTRACT_MAX_CHARS
from web.pages import LOGIN_REDIRECTS, PAGES
from web.security import CSP_REPORT_ONLY


def _json(resp):
    return json.loads(resp.data)


# ---------------------------------------------------------------------------
# The app is built exactly once
# ---------------------------------------------------------------------------

def test_importing_app_does_not_build_an_application():
    import app as app_module
    assert not hasattr(app_module, 'app')


def test_wsgi_builds_the_application_once(monkeypatch):
    import app as app_module
    built = MagicMock(name='flask_app')
    factory = MagicMock(return_value=built)
    monkeypatch.setattr(app_module, 'create_app', factory)
    monkeypatch.delitem(sys.modules, 'wsgi', raising=False)

    wsgi = importlib.import_module('wsgi')

    assert factory.call_count == 1
    assert wsgi.app is built
    sys.modules.pop('wsgi', None)


def test_never_read_app_attributes_are_gone(app):
    for name in ('test_service', 'practice_session_service', 'service_factory', 'prompt_service'):
        assert not hasattr(app, name)


# ---------------------------------------------------------------------------
# Page routes
# ---------------------------------------------------------------------------

EXPECTED_PAGE_URLS = {
    'index': '/',
    'login': '/login',
    'signup': '/signup',
    'welcome': '/welcome',
    'language_selection': '/language-selection',
    'tests': '/tests',
    'profile': '/profile',
    'study_plan_page': '/study-plan',
    'study_session_page': '/session',
    'test_preview': '/test/abc/preview',
    'test_prestudy_page': '/test/abc/prestudy',
    'test_page': '/test/abc',
    'pinyin_test_page': '/test/abc/pinyin',
    'pitch_accent_test_page': '/test/abc/pitch-accent',
    'dictation_test_page': '/test/abc/dictation',
    'flashcards': '/flashcards',
    'word_list_page': '/word-list',
    'calibration_page': '/calibration',
    'classifier_drill_page': '/classifier-drill',
    'counter_drill_page': '/counter-drill',
    'dual_translation_page': '/dual-translation',
    'dual_translation_profile_page': '/dual-translation/profile',
    'admin_vocab_preview': '/admin/vocab-preview',
    'logout': '/logout',
}


def test_page_table_covers_every_known_endpoint():
    declared = {endpoint for _, endpoint, _ in PAGES} | {e for _, e in LOGIN_REDIRECTS}
    assert declared == set(EXPECTED_PAGE_URLS)


@pytest.mark.parametrize('endpoint,url', sorted(EXPECTED_PAGE_URLS.items()))
def test_page_endpoint_keeps_its_name_and_url(app, endpoint, url):
    values = {'slug': 'abc'} if '/abc' in url else {}
    with app.test_request_context():
        assert url_for(endpoint, **values) == url


@pytest.mark.parametrize('rule,endpoint,template', PAGES)
def test_page_renders_its_template(app, client, rule, endpoint, template):
    assert (app.jinja_loader.searchpath and
            app.jinja_env.get_template(template) is not None)
    resp = client.get(rule.replace('<slug>', 'abc'))
    assert resp.status_code == 200
    assert resp.content_type.startswith('text/html')


@pytest.mark.parametrize('url', ['/', '/logout'])
def test_login_redirects(client, url):
    resp = client.get(url)
    assert resp.status_code == 302
    assert resp.headers['Location'].endswith('/login')


# ---------------------------------------------------------------------------
# Security headers
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('url', ['/login', '/api/health', '/api/does-not-exist'])
def test_security_headers_on_every_response(client, url):
    resp = client.get(url)
    assert resp.headers['X-Content-Type-Options'] == 'nosniff'
    assert resp.headers['X-Frame-Options'] == 'SAMEORIGIN'
    assert resp.headers['Referrer-Policy'] == 'strict-origin-when-cross-origin'
    assert 'Strict-Transport-Security' not in resp.headers


def test_hsts_only_when_the_request_is_secure(client):
    resp = client.get('/api/health', headers={'X-Forwarded-Proto': 'https'})
    assert resp.headers['Strict-Transport-Security'].startswith('max-age=')


def test_csp_stays_report_only(client):
    resp = client.get('/login')
    assert resp.headers['Content-Security-Policy-Report-Only'] == CSP_REPORT_ONLY
    assert 'Content-Security-Policy' not in resp.headers


# ---------------------------------------------------------------------------
# Request size
# ---------------------------------------------------------------------------

def test_default_body_cap_is_one_megabyte(app):
    assert app.config['MAX_CONTENT_LENGTH'] == 1024 * 1024


def test_oversized_body_is_rejected_with_413(app, client, auth_headers):
    # send-otp reads the body inside a broad except; the cap must still win.
    resp = client.post('/api/auth/send-otp', data='x' * (app.config['MAX_CONTENT_LENGTH'] + 1),
                       content_type='application/json')
    assert resp.status_code == 413
    assert _json(resp) == {
        'status': 'error', 'error': 'Request body too large', 'error_code': 'PAYLOAD_TOO_LARGE',
    }


def test_vocabulary_extract_rejects_overlong_text(client, auth_headers):
    resp = client.post('/api/vocabulary/extract',
                       json={'text': 'a' * (VOCAB_EXTRACT_MAX_CHARS + 1), 'language_code': 'en'},
                       headers=auth_headers)
    assert resp.status_code == 400


def test_vocabulary_extract_validates_before_checking_the_pipeline(app, client, auth_headers):
    app.vocab_pipeline = None
    assert client.post('/api/vocabulary/extract', json={}, headers=auth_headers).status_code == 400
    resp = client.post('/api/vocabulary/extract', json={'text': 'hola', 'language_code': 'es'},
                       headers=auth_headers)
    assert resp.status_code == 503


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

@pytest.fixture()
def failing_app(app):
    def boom():
        raise RuntimeError('secret detail')
    app.add_url_rule('/api/_boom', 'api_boom', boom)
    app.add_url_rule('/_boom', 'page_boom', boom)
    return app


def test_unhandled_exception_on_api_path_uses_the_error_envelope(failing_app):
    resp = failing_app.test_client().get('/api/_boom')
    assert resp.status_code == 500
    assert _json(resp) == {
        'status': 'error', 'error': 'Internal server error', 'error_code': 'SERVER_ERROR',
    }


def test_unhandled_exception_on_a_page_renders_error_html(failing_app):
    resp = failing_app.test_client().get('/_boom')
    assert resp.status_code == 500
    assert resp.content_type.startswith('text/html')
    body = resp.get_data(as_text=True)
    assert 'Something went wrong' in body
    assert 'secret detail' not in body


def test_unknown_api_path_uses_the_error_envelope(client):
    resp = client.get('/api/does-not-exist')
    assert resp.status_code == 404
    assert _json(resp) == {
        'status': 'error', 'error': 'Endpoint not found', 'error_code': 'NOT_FOUND',
    }


def test_unknown_page_redirects_to_login(client):
    resp = client.get('/no-such-page')
    assert resp.status_code == 302
    assert resp.headers['Location'].endswith('/login')


def test_wrong_method_uses_the_error_envelope(client):
    resp = client.delete('/api/health')
    assert resp.status_code == 405
    assert _json(resp) == {
        'status': 'error', 'error': 'Method not allowed', 'error_code': 'METHOD_NOT_ALLOWED',
    }
    assert 'GET' in resp.headers['Allow']


def test_test_apps_do_not_start_the_scheduler(app):
    assert not hasattr(app, 'scheduler')
