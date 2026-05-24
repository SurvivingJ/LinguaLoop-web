"""RED reproducers for HI-01 + HI-02.

HI-01 — `jwt_required`, `admin_required`, `tier_required` triplicate exception
        handling. The fix extracts a shared `_authenticate` helper.

HI-02 — Service-role JWT bypass only lives in `jwt_required`. Submitting the
        service role key to an `@admin_required` or `@tier_required` endpoint
        currently 401s because Supabase rejects the service-role JWT shape.
"""

import importlib
import inspect
from types import SimpleNamespace
from unittest.mock import patch, MagicMock

import pytest
from flask import Flask, jsonify, g

import middleware.auth as auth_mod


# ---------------------------------------------------------------------------
# HI-01 — duplication is removed via a shared helper
# ---------------------------------------------------------------------------

class TestHI01_AuthHelperConsolidation:
    """The three decorators must delegate to a single private helper.

    The helper name we agree on is `_authenticate(token) -> (claims, error_response)`.
    Tests assert (a) the helper exists, (b) every decorator references it,
    (c) the three decorator bodies are short, proving they no longer carry
    their own try/except triplet.
    """

    def test_authenticate_helper_exists(self):
        importlib.reload(auth_mod)
        assert hasattr(auth_mod, '_authenticate'), (
            "Expected a shared _authenticate() helper in middleware.auth "
            "after HI-01 consolidation."
        )

    def test_each_decorator_uses_the_helper(self):
        importlib.reload(auth_mod)
        for name in ('jwt_required', 'admin_required', 'tier_required'):
            src = inspect.getsource(getattr(auth_mod, name))
            assert '_authenticate(' in src, (
                f"{name} should call _authenticate() instead of duplicating "
                "the token-extract / get_user / except triplet."
            )

    def test_decorator_bodies_are_thin(self):
        """Each decorator's source should be << 70 lines after consolidation."""
        importlib.reload(auth_mod)
        for name in ('jwt_required', 'admin_required'):
            src = inspect.getsource(getattr(auth_mod, name))
            line_count = len(src.splitlines())
            assert line_count <= 45, (
                f"{name} is {line_count} lines — consolidation should shrink "
                "it to ~30 lines or fewer."
            )


# ---------------------------------------------------------------------------
# HI-02 — service-role bypass is symmetric across decorators
# ---------------------------------------------------------------------------

SERVICE_ROLE_KEY = 'service-role-test-key-do-not-leak'


@pytest.fixture()
def app_with_decorators(monkeypatch):
    """Tiny Flask app that wires up the three decorators against a mock Supabase.

    The mock Supabase rejects any service-role token (mirrors production
    Supabase behavior — service_role JWTs are not valid auth tokens).
    """
    monkeypatch.setenv('SUPABASE_SERVICE_ROLE_KEY', SERVICE_ROLE_KEY)

    fake_supabase = MagicMock()
    VALID_USER_JWT = 'real-user-jwt-token-abc'

    def fake_get_user(token):
        # Service-role token must NOT be passed through get_user.
        # If a decorator forgets the bypass, this is what production hits.
        if token == SERVICE_ROLE_KEY:
            from gotrue.errors import AuthApiError
            raise AuthApiError('bad_jwt: invalid token', 401, 'bad_jwt')
        if token == VALID_USER_JWT:
            return SimpleNamespace(
                user=SimpleNamespace(id='user-abc', email='u@example.com')
            )
        # Any other token: simulate Supabase rejecting it.
        from gotrue.errors import AuthApiError
        raise AuthApiError('invalid jwt', 401, 'bad_jwt')

    fake_supabase.auth.get_user.side_effect = fake_get_user
    fake_supabase.VALID_USER_JWT = VALID_USER_JWT

    # users-table lookup returns admin tier when the decorator actually queries.
    admin_chain = MagicMock()
    admin_chain.execute.return_value = SimpleNamespace(
        data=[{'subscription_tier': 'admin'}]
    )
    fake_supabase.table.return_value.select.return_value.eq.return_value = admin_chain

    with patch.object(auth_mod, '_get_supabase_client', return_value=fake_supabase), \
         patch.object(auth_mod, '_get_supabase_admin', return_value=fake_supabase):

        app = Flask(__name__)

        @app.route('/jwt-only')
        @auth_mod.jwt_required
        def jwt_only():
            return jsonify({'ok': True, 'sub': g.supabase_claims['sub']})

        @app.route('/admin-only')
        @auth_mod.admin_required
        def admin_only():
            return jsonify({'ok': True})

        @app.route('/tier-only')
        @auth_mod.tier_required(['premium', 'admin'])
        def tier_only():
            return jsonify({'ok': True})

        yield app


class TestHI02_ServiceRoleBypassSymmetric:

    def _bearer(self, token):
        return {'Authorization': f'Bearer {token}'}

    def test_jwt_required_accepts_service_role_token(self, app_with_decorators):
        """Sanity: the existing bypass still works."""
        c = app_with_decorators.test_client()
        resp = c.get('/jwt-only', headers=self._bearer(SERVICE_ROLE_KEY))
        assert resp.status_code == 200
        assert resp.get_json()['sub'] == 'service-account'

    def test_admin_required_accepts_service_role_token(self, app_with_decorators):
        """HI-02 reproducer — fails today (returns 401), passes after fix."""
        c = app_with_decorators.test_client()
        resp = c.get('/admin-only', headers=self._bearer(SERVICE_ROLE_KEY))
        assert resp.status_code == 200, (
            "Service-role token should bypass admin_required the same way it "
            "bypasses jwt_required. Current behavior returns 401 because the "
            "decorator forwards the service-role JWT to Supabase, which "
            "rejects it as malformed."
        )

    def test_tier_required_accepts_service_role_token(self, app_with_decorators):
        """HI-02 reproducer — fails today (returns 401), passes after fix."""
        c = app_with_decorators.test_client()
        resp = c.get('/tier-only', headers=self._bearer(SERVICE_ROLE_KEY))
        assert resp.status_code == 200, (
            "Service-role token should bypass tier_required the same way it "
            "bypasses jwt_required."
        )

    def test_bogus_token_still_rejected_after_consolidation(self, app_with_decorators):
        """Negative control: the bypass must remain hmac.compare_digest-strict."""
        c = app_with_decorators.test_client()
        for path in ('/jwt-only', '/admin-only', '/tier-only'):
            resp = c.get(path, headers=self._bearer('not-the-service-key'))
            assert resp.status_code in (401, 403), (
                f"{path} must still reject a non-matching token; got "
                f"{resp.status_code}"
            )
