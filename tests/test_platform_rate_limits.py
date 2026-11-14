"""Rate limiting: off under the normal test config, enforced when switched on."""

import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from middleware.auth import clear_auth_cache
from tests.conftest import TestConfig as BaseTestConfig
from tests.conftest import _make_mock_dimension_service, _make_mock_supabase
from web.rate_limits import ENDPOINT_LIMITS, EXEMPT_ENDPOINTS


class RateLimitedConfig(BaseTestConfig):
    RATELIMIT_ENABLED_IN_TESTS = True
    RATELIMIT_STORAGE_URI = 'memory://'
    RATELIMIT_API_DEFAULT = '8 per minute'


def _build(config):
    mock_supabase = _make_mock_supabase()
    # Each bearer token is its own user: "Bearer user-a" -> id "user-a".
    mock_supabase.auth.get_user.side_effect = lambda token: SimpleNamespace(
        user=SimpleNamespace(id=token, email=f'{token}@example.com'))
    with patch('services.supabase_factory.get_supabase', return_value=mock_supabase), \
         patch('services.supabase_factory.get_supabase_admin', return_value=mock_supabase), \
         patch('app.DimensionService') as dim, \
         patch('app.ServiceFactory'), \
         patch('app.R2Service'), \
         patch('app.AuthService'):
        data = _make_mock_dimension_service()
        dim.initialize = MagicMock()
        dim.get_all_languages = MagicMock(side_effect=data['get_all_languages'])
        dim.get_all_test_types = MagicMock(side_effect=data['get_all_test_types'])
        dim._test_types_metadata = []
        from app import create_app
        flask_app = create_app(config)
        flask_app.supabase = flask_app.supabase_service = mock_supabase
        yield flask_app


@pytest.fixture()
def limited_app():
    clear_auth_cache()
    yield from _build(RateLimitedConfig)
    clear_auth_cache()


@pytest.fixture()
def limited(limited_app):
    from routes.auth import auth_bp
    auth_bp.auth_service = MagicMock()
    auth_bp.auth_service.send_otp.return_value = {'success': True}
    return limited_app.test_client()


def _send_otp(client, email, ip='203.0.113.1'):
    return client.post('/api/auth/send-otp', json={'email': email},
                       headers={'X-Forwarded-For': ip})


def _bearer(user):
    return {'Authorization': f'Bearer {user}'}


def test_limiter_is_off_under_the_default_test_config(app, client):
    assert app.extensions['rate_limiter'].enabled is False
    for _ in range(30):
        assert client.post('/api/auth/send-otp', json={}).status_code != 429


def test_every_configured_endpoint_exists(limited_app):
    for endpoint in list(ENDPOINT_LIMITS) + list(EXEMPT_ENDPOINTS):
        assert endpoint in limited_app.view_functions, endpoint


def test_send_otp_is_limited_per_ip(limited):
    # A different address each time, so only the per-IP limit can trip.
    codes = [_send_otp(limited, f'user{i}@example.com').status_code for i in range(6)]
    assert codes == [200] * 5 + [429]


def test_rate_limited_response_uses_the_error_envelope(limited):
    for i in range(5):
        _send_otp(limited, f'user{i}@example.com')
    resp = _send_otp(limited, 'last@example.com')
    assert resp.status_code == 429
    assert json.loads(resp.data) == {
        'status': 'error',
        'error': 'Too many requests. Please try again later.',
        'error_code': 'RATE_LIMITED',
    }
    assert int(resp.headers['Retry-After']) > 0


def test_send_otp_is_limited_per_email_across_ips(limited):
    codes = [_send_otp(limited, 'Victim@Example.com ', ip=f'198.51.100.{i}').status_code
             for i in range(4)]
    assert codes == [200] * 3 + [429]
    # Another address from a fresh IP is unaffected.
    assert _send_otp(limited, 'other@example.com', ip='198.51.100.99').status_code == 200


def test_ip_limit_follows_the_forwarded_client_address(limited):
    for i in range(5):
        _send_otp(limited, f'a{i}@example.com', ip='203.0.113.7')
    assert _send_otp(limited, 'a9@example.com', ip='203.0.113.7').status_code == 429
    assert _send_otp(limited, 'b@example.com', ip='203.0.113.8').status_code == 200


def test_verify_otp_is_limited_per_ip(limited):
    from routes.auth import auth_bp
    auth_bp.auth_service.verify_otp.return_value = {'success': False, 'error': 'bad code'}
    codes = [limited.post('/api/auth/verify-otp',
                          json={'email': f'u{i}@example.com', 'otp': '000000'},
                          headers={'X-Forwarded-For': '203.0.113.5'}).status_code
             for i in range(11)]
    assert 429 not in codes[:10]
    assert codes[10] == 429


def test_user_limit_is_keyed_on_the_verified_user_not_the_ip(limited):
    def extract(user, ip):
        return limited.post('/api/vocabulary/extract', json={},
                            headers={**_bearer(user), 'X-Forwarded-For': ip}).status_code

    # An endpoint with its own limit (10/min) is not also bound by the API default.
    assert [extract('user-a', '192.0.2.1') for _ in range(10)] == [400] * 10
    assert extract('user-a', '192.0.2.1') == 429
    # Same user from another IP is still limited; another user on the first IP is not.
    assert extract('user-a', '192.0.2.2') == 429
    assert extract('user-b', '192.0.2.1') == 400


def test_word_list_submit_has_its_own_per_user_limit(limited):
    def submit(user):
        return limited.post('/api/word-list/submit', json={}, headers=_bearer(user)).status_code

    codes = [submit('user-a') for _ in range(6)]
    assert 429 not in codes[:5]
    assert codes[5] == 429
    assert submit('user-b') != 429


def test_unauthenticated_requests_fall_back_to_the_ip(limited):
    codes = [limited.get('/api/metadata', headers={'X-Forwarded-For': '192.0.2.50'}).status_code
             for _ in range(9)]
    assert codes == [200] * 8 + [429]
    assert limited.get('/api/metadata', headers={'X-Forwarded-For': '192.0.2.51'}).status_code == 200


def test_pages_static_and_health_are_not_rate_limited(limited):
    for _ in range(12):
        assert limited.get('/login').status_code == 200
        assert limited.get('/api/health').status_code == 200
