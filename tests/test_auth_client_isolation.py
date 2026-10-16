"""Login-flow calls must not demote the shared service-role data client.

supabase-py swaps a client's Authorization header to the signed-in user's JWT on
SIGNED_IN / TOKEN_REFRESHED. When AuthService ran verify_otp / refresh_session on
the shared service client, every later table/RPC call on that singleton ran as
`authenticated` and hit "permission denied for function ..." after the
function-grant hardening (TASK-877).
"""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from services import auth_service as auth_mod
from services.supabase_factory import SupabaseFactory

URL = "https://example.supabase.co"
# Shape-valid dummy JWTs; no network call is made at client construction.
ANON_KEY = "eyJhbGciOiJIUzI1NiJ9.eyJyb2xlIjoiYW5vbiJ9.sig"
SERVICE_KEY = "eyJhbGciOiJIUzI1NiJ9.eyJyb2xlIjoic2VydmljZV9yb2xlIn0.sig"


@pytest.fixture
def factory():
    SupabaseFactory.reset()
    SupabaseFactory.initialize(URL, ANON_KEY, SERVICE_KEY)
    yield SupabaseFactory
    SupabaseFactory.reset()


def _user_session():
    return SimpleNamespace(access_token="USER.JWT.TOKEN", refresh_token="r")


def test_auth_client_is_a_separate_instance(factory):
    assert factory.get_auth_client() is not None
    assert factory.get_auth_client() is not factory.get_service_client()
    assert factory.get_auth_client() is not factory.get_anon_client()


@pytest.mark.parametrize("event", ["SIGNED_IN", "TOKEN_REFRESHED"])
def test_login_event_on_auth_client_leaves_service_client_untouched(factory, event):
    service = factory.get_service_client()
    before = service.options.headers["Authorization"]
    assert before == f"Bearer {SERVICE_KEY}"

    factory.get_auth_client()._listen_to_auth_events(event, _user_session())

    assert service.options.headers["Authorization"] == before
    assert service.postgrest.session.headers["Authorization"] == before


def test_reset_clears_auth_client(factory):
    factory.reset()
    assert factory._auth_client is None


def test_auth_service_runs_login_calls_on_auth_client_only(monkeypatch):
    admin, auth = MagicMock(name="admin"), MagicMock(name="auth")
    monkeypatch.setattr(auth_mod, "get_supabase_admin", lambda: admin)
    monkeypatch.setattr(auth_mod, "get_supabase_auth", lambda: auth)
    svc = auth_mod.AuthService(MagicMock(name="anon"))

    auth.auth.refresh_session.return_value = SimpleNamespace(
        session=SimpleNamespace(access_token="a", refresh_token="b")
    )
    assert svc.refresh_session("rt")["success"] is True
    svc.send_otp("a@b.c")
    svc.verify_otp("a@b.c", "123456")

    auth.auth.refresh_session.assert_called_once_with("rt")
    auth.auth.sign_in_with_otp.assert_called_once()
    auth.auth.verify_otp.assert_called_once()
    admin.auth.refresh_session.assert_not_called()
    admin.auth.sign_in_with_otp.assert_not_called()
    admin.auth.verify_otp.assert_not_called()
