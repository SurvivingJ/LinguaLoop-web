"""Auth hardening: session revocation on logout, no account enumeration or
exception text in auth responses, byte-safe batch-token comparison, and
optional local JWT verification."""

import time
from types import SimpleNamespace
from unittest.mock import MagicMock

import jwt
import pytest
from flask import Flask
from gotrue.errors import AuthApiError

import services.auth_service as auth_service_mod
from middleware import auth

SECRET = 'local-test-secret-of-sufficient-length-0123456789'


@pytest.fixture
def service(monkeypatch):
    admin, auth_client, anon = MagicMock(name='admin'), MagicMock(name='auth'), MagicMock(name='anon')
    monkeypatch.setattr(auth_service_mod, 'get_supabase_admin', lambda: admin)
    monkeypatch.setattr(auth_service_mod, 'get_supabase_auth', lambda: auth_client)
    svc = auth_service_mod.AuthService(anon)
    svc._clients = SimpleNamespace(admin=admin, auth=auth_client, anon=anon)
    return svc


@pytest.fixture
def app_ctx(monkeypatch):
    monkeypatch.delenv('SUPABASE_JWT_SECRET', raising=False)
    monkeypatch.delenv('BATCH_SERVICE_TOKEN', raising=False)
    monkeypatch.setattr(auth, '_AUTH_CACHE_TTL', 60.0)
    auth.clear_auth_cache()
    app = Flask(__name__)
    with app.test_request_context('/x'):
        yield app
    auth.clear_auth_cache()


@pytest.fixture
def gotrue(monkeypatch):
    client = MagicMock()
    client.auth.get_user.return_value = SimpleNamespace(
        user=SimpleNamespace(id='user-1', email='a@b.c'))
    monkeypatch.setattr(auth, '_get_supabase_client', lambda: client)
    return client


def _access_token(secret=SECRET, **overrides):
    payload = {
        'sub': 'user-1', 'email': 'a@b.c', 'role': 'authenticated',
        'aud': 'authenticated', 'exp': int(time.time()) + 3600,
    }
    payload.update(overrides)
    payload = {k: v for k, v in payload.items() if v is not None}
    return jwt.encode(payload, secret, algorithm='HS256')


# -- logout ------------------------------------------------------------------

def test_logout_revokes_the_callers_session_with_the_admin_api(service, app_ctx):
    result = service.logout('user-1', access_token='tok.en.sig')

    assert result == {'success': True, 'message': 'Logged out successfully'}
    service._clients.auth.auth.admin.sign_out.assert_called_once_with('tok.en.sig', 'local')
    service._clients.anon.auth.sign_out.assert_not_called()
    service._clients.admin.auth.admin.sign_out.assert_not_called()


def test_logout_still_succeeds_when_revocation_fails(service, app_ctx):
    service._clients.auth.auth.admin.sign_out.side_effect = RuntimeError('gotrue down')
    assert service.logout('user-1', access_token='tok.en.sig')['success'] is True


def test_logout_evicts_the_token_from_the_auth_cache(service, app_ctx, gotrue):
    token = _access_token()
    claims, err = auth._authenticate(token)
    assert err is None and gotrue.auth.get_user.call_count == 1

    service.logout('user-1', access_token=token)

    claims, err = auth._authenticate(token)
    assert claims is None and err[1] == 401
    # Refused locally, without asking GoTrue again.
    assert gotrue.auth.get_user.call_count == 1


def test_logout_route_passes_the_bearer_token(client, auth_headers):
    from routes.auth import auth_bp
    auth_bp.auth_service.logout.return_value = {'success': True, 'message': 'Logged out successfully'}

    resp = client.post('/api/auth/logout', headers=auth_headers)

    assert resp.status_code == 200
    assert resp.get_json() == {'success': True, 'message': 'Logged out successfully'}
    auth_bp.auth_service.logout.assert_called_once_with(
        'test-user-id-123', access_token='fake-jwt-token-for-testing')


# -- enumeration and error leakage --------------------------------------------

@pytest.mark.parametrize('message', ['User not found', 'Signups not allowed for otp'])
def test_send_otp_does_not_reveal_whether_an_account_exists(service, message):
    service._clients.auth.auth.sign_in_with_otp.return_value = object()
    known = service.send_otp('known@example.com')

    service._clients.auth.auth.sign_in_with_otp.side_effect = AuthApiError(message, 400, None)
    unknown = service.send_otp('unknown@example.com')

    assert unknown['success'] is True
    assert 'code' not in unknown
    assert set(unknown) == set(known)
    assert unknown['message'].replace('unknown', 'known') == known['message']


def test_send_otp_failure_does_not_echo_the_exception(service):
    service._clients.auth.auth.sign_in_with_otp.side_effect = RuntimeError(
        'connect to 10.0.0.5:5432 refused')
    result = service.send_otp('a@b.c')
    assert result['success'] is False
    assert '10.0.0.5' not in result['error']


def test_verify_otp_failure_does_not_echo_the_exception(service):
    service._clients.auth.auth.verify_otp.side_effect = RuntimeError('secret-internal-detail')
    result = service.verify_otp('a@b.c', '123456')
    assert result['success'] is False
    assert 'secret-internal-detail' not in result['error'] + result['message']

    service._clients.auth.auth.verify_otp.side_effect = AuthApiError('Token has expired', 403, None)
    assert service.verify_otp('a@b.c', '123456')['error'] == 'Invalid or expired OTP'


def test_refresh_failure_does_not_echo_the_exception(service):
    service._clients.auth.auth.refresh_session.side_effect = RuntimeError('secret-internal-detail')
    assert service.refresh_session('rt') == {'success': False, 'error': 'Failed to refresh session'}


# -- middleware ---------------------------------------------------------------

def test_non_ascii_bearer_token_is_rejected_not_a_server_error(app_ctx, gotrue, monkeypatch):
    monkeypatch.setenv('BATCH_SERVICE_TOKEN', 'batch-secret')
    gotrue.auth.get_user.side_effect = AuthApiError('bad jwt', 401, None)

    claims, err = auth._authenticate('töken-é')

    assert claims is None and err[1] == 401


def test_batch_token_still_matches_after_byte_comparison(app_ctx, monkeypatch):
    monkeypatch.setenv('BATCH_SERVICE_TOKEN', 'batch-secret')
    claims, err = auth._authenticate('batch-secret')
    assert err is None and claims['sub'] == 'service-account'


def test_user_context_no_longer_sets_the_unused_user_id(app_ctx):
    from flask import g
    auth._set_user_context({'sub': 'user-1', 'user': None})
    assert g.current_user_id == 'user-1'
    assert not hasattr(g, 'user_id')


def test_local_verification_is_off_without_the_secret(app_ctx, gotrue):
    claims, err = auth._authenticate(_access_token())
    assert err is None and claims['sub'] == 'user-1'
    assert gotrue.auth.get_user.call_count == 1


def test_local_verification_accepts_a_valid_token_without_the_network(app_ctx, gotrue, monkeypatch):
    monkeypatch.setenv('SUPABASE_JWT_SECRET', SECRET)
    token = _access_token()

    claims, err = auth._authenticate(token)
    again, _ = auth._authenticate(token)

    assert err is None
    assert claims['sub'] == 'user-1' and claims['email'] == 'a@b.c'
    assert claims['role'] == 'authenticated' and again == claims
    gotrue.auth.get_user.assert_not_called()


@pytest.mark.parametrize('token_kwargs', [
    {'exp': int(time.time()) - 10},
    {'aud': 'something-else'},
    {'aud': None},
    {'sub': None},
    {'exp': None},
    {'role': 'service_role'},
    {'secret': 'a-different-secret-of-sufficient-length-0123456789'},
])
def test_local_verification_rejects_bad_tokens(app_ctx, gotrue, monkeypatch, token_kwargs):
    monkeypatch.setenv('SUPABASE_JWT_SECRET', SECRET)

    claims, err = auth._authenticate(_access_token(**token_kwargs))

    assert claims is None and err[1] == 401
    gotrue.auth.get_user.assert_not_called()


def test_unsigned_token_is_never_accepted_locally(app_ctx, gotrue, monkeypatch):
    monkeypatch.setenv('SUPABASE_JWT_SECRET', SECRET)
    gotrue.auth.get_user.side_effect = AuthApiError('bad jwt', 401, None)
    payload = {'sub': 'user-1', 'role': 'authenticated', 'aud': 'authenticated',
               'exp': int(time.time()) + 3600}
    token = jwt.encode(payload, None, algorithm='none')

    claims, err = auth._authenticate(token)

    assert claims is None and err[1] == 401


def test_non_hs256_tokens_fall_back_to_the_network(app_ctx, gotrue, monkeypatch):
    monkeypatch.setenv('SUPABASE_JWT_SECRET', SECRET)
    es256_shaped = 'eyJhbGciOiJFUzI1NiJ9.eyJzdWIiOiJ1c2VyLTEifQ.sig'

    claims, err = auth._authenticate(es256_shaped)

    assert err is None and claims['sub'] == 'user-1'
    assert gotrue.auth.get_user.call_count == 1
