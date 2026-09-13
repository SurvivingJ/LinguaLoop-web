"""TASK-774 — token validation is cached, without outliving the token.

`auth.get_user(token)` is a network call to GoTrue and ran on EVERY authenticated
request: a fixed ~65-150 ms toll before any handler started (measured round trip
to this project's region, 2026-09-13).

The cache is only safe because of three properties, and these pin all three:

  * a repeat call with the same token does not go to the network;
  * a REJECTION is never cached, so a bad token is re-checked every time;
  * an entry never outlives the token's own `exp`, so an expired token is always
    re-checked and rejected even inside the TTL window.

The residual, intended risk — a revoked-but-unexpired session keeps working for
up to the TTL — is the thing AUTH_CACHE_TTL_SECONDS exists to bound, and setting
it to 0 disables the cache entirely. That is pinned too.
"""

import time
from unittest.mock import MagicMock

import pytest
from flask import Flask

from middleware import auth


def _token(exp=None):
    """A structurally valid JWT whose payload carries `exp`. Never verified."""
    import base64
    import json

    def seg(obj):
        raw = base64.urlsafe_b64encode(json.dumps(obj).encode()).decode()
        return raw.rstrip('=')

    payload = {'sub': 'user-1'}
    if exp is not None:
        payload['exp'] = exp
    return '%s.%s.%s' % (seg({'alg': 'HS256'}), seg(payload), 'sig')


@pytest.fixture
def gotrue(monkeypatch):
    """A fake Supabase auth client that counts network validations."""
    client = MagicMock()
    client.calls = 0

    def get_user(token):
        client.calls += 1
        user = MagicMock()
        user.id = 'user-1'
        user.email = 'a@b.c'
        response = MagicMock()
        response.user = user
        return response

    client.auth.get_user.side_effect = get_user
    monkeypatch.setattr(auth, '_get_supabase_client', lambda: client)
    monkeypatch.setattr(auth, '_AUTH_CACHE_TTL', 60.0)
    auth.clear_auth_cache()
    yield client
    auth.clear_auth_cache()


@pytest.fixture
def app_ctx():
    """_authenticate builds jsonify() responses, so it needs an app context."""
    app = Flask(__name__)
    with app.app_context():
        yield app


def test_a_repeated_token_is_not_revalidated_over_the_network(gotrue, app_ctx):
    token = _token(exp=time.time() + 3600)

    first, err1 = auth._authenticate(token)
    second, err2 = auth._authenticate(token)

    assert err1 is None and err2 is None
    assert first['sub'] == second['sub'] == 'user-1'
    assert gotrue.calls == 1


def test_different_tokens_are_cached_separately(gotrue, app_ctx):
    auth._authenticate(_token(exp=time.time() + 3600))
    auth._authenticate(_token(exp=time.time() + 7200))

    assert gotrue.calls == 2


def test_a_rejection_is_never_cached(gotrue, app_ctx):
    gotrue.auth.get_user.side_effect = None
    gotrue.auth.get_user.return_value = MagicMock(user=None)
    token = _token(exp=time.time() + 3600)

    for _ in range(3):
        claims, err = auth._authenticate(token)
        assert claims is None and err is not None

    assert gotrue.auth.get_user.call_count == 3


def test_an_entry_never_outlives_the_token(gotrue, app_ctx):
    # Already expired: the cache must refuse to hold it at all, so the next
    # request goes back to GoTrue and is rejected there.
    token = _token(exp=time.time() - 1)

    auth._authenticate(token)
    auth._authenticate(token)

    assert gotrue.calls == 2


def test_expiry_is_clamped_to_the_token_not_the_ttl(gotrue, app_ctx):
    # TTL is 60 s but the token dies in 1 s. The entry must die with the token.
    token = _token(exp=time.time() + 1)
    auth._authenticate(token)

    key = auth._auth_cache_key(token)
    expires_at, _claims = auth._auth_cache[key]
    assert expires_at <= time.time() + 1.01


def test_ttl_zero_disables_the_cache(gotrue, app_ctx, monkeypatch):
    monkeypatch.setattr(auth, '_AUTH_CACHE_TTL', 0.0)
    token = _token(exp=time.time() + 3600)

    auth._authenticate(token)
    auth._authenticate(token)

    assert gotrue.calls == 2


def test_a_raw_token_is_never_used_as_a_key(gotrue, app_ctx):
    token = _token(exp=time.time() + 3600)
    auth._authenticate(token)

    assert token not in auth._auth_cache
    assert all(token not in k for k in auth._auth_cache)
