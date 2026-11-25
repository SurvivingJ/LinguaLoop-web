"""The token economy is retired (TASK-1210, owner decision 2026-11-23).

Nothing here changes what a learner can do: the submission RPCs still price a test
through ``get_test_token_cost`` and every caller still passes ``p_was_free_test=True``.
What is gone is the application-side dead ends: the ``grant_daily_free_tokens`` calls,
the token balance endpoint, the token-package list, and the config that advertised them.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

import services.auth_service as auth_service_mod
from config import Config


@pytest.fixture
def service(monkeypatch):
    admin, auth_client, anon = MagicMock(name='admin'), MagicMock(name='auth'), MagicMock(name='anon')
    monkeypatch.setattr(auth_service_mod, 'get_supabase_admin', lambda: admin)
    monkeypatch.setattr(auth_service_mod, 'get_supabase_auth', lambda: auth_client)
    svc = auth_service_mod.AuthService(anon)
    svc._clients = SimpleNamespace(admin=admin, auth=auth_client, anon=anon)
    return svc


def _rpc_names(admin):
    return [c.args[0] for c in admin.rpc.call_args_list]


def _users_table(admin, rows):
    admin.table.return_value.select.return_value.eq.return_value.execute.return_value = (
        SimpleNamespace(data=rows))


def test_existing_user_payload_has_no_token_balance_and_no_rpc(service):
    admin = service.supabase_admin
    _users_table(admin, [{'id': 'u1', 'email': 'a@b.c', 'total_tests_taken': 4,
                          'has_seen_welcome': True, 'subscription_tier': 'free'}])
    out = service._get_user_data('u1', 'a@b.c')
    assert admin.rpc.call_count == 0
    assert 'token_balance' not in out
    assert out['id'] == 'u1' and out['total_tests_taken'] == 4
    assert out['has_seen_welcome'] is True and out['subscription_tier'] == 'free'


def test_missing_user_is_created_without_a_grant_call(service):
    admin = service.supabase_admin
    _users_table(admin, [])
    out = service._get_user_data('u2', 'n@b.c')
    assert 'grant_daily_free_tokens' not in _rpc_names(admin)
    assert admin.rpc.call_count == 0
    admin.table.return_value.insert.assert_called_once()
    assert out['id'] == 'u2' and out['email'] == 'n@b.c'
    assert out['has_seen_welcome'] is False
    assert out['total_tests_taken'] == 0 and out['total_tests_generated'] == 0
    assert out['subscription_tier'] == 'free'
    assert 'token_balance' not in out


def test_get_user_profile_does_not_read_a_token_balance(service):
    admin = service.supabase_admin
    _users_table(admin, [{'id': 'u1', 'email': 'a@b.c'}])
    out = service.get_user_profile('u1')
    assert out['success'] is True
    assert admin.rpc.call_count == 0
    assert 'token_balance' not in out['user']


@pytest.mark.parametrize('method,path', [
    ('get', '/api/users/tokens'),
    ('get', '/api/payments/token-packages'),
])
def test_token_routes_are_gone(app, client, auth_headers, method, path):
    rules = {r.rule for r in app.url_map.iter_rules()}
    assert path not in rules
    assert getattr(client, method)(path, headers=auth_headers).status_code == 404


def test_no_payments_blueprint_is_registered(app):
    assert not [r.rule for r in app.url_map.iter_rules() if r.rule.startswith('/api/payments')]


def test_health_does_not_advertise_the_token_economy(client):
    import json
    health = json.loads(client.get('/api/health').data)
    assert 'stripe' not in health['services']


@pytest.mark.parametrize('name', ['TOKEN_COSTS', 'DAILY_FREE_TOKENS', 'TOKEN_PACKAGES', 'STRIPE_SECRET_KEY'])
def test_token_config_is_removed(name):
    assert not hasattr(Config, name)
