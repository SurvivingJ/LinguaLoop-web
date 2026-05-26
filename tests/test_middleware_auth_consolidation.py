"""Tests for HI-01 + HI-02 + ADR-014.

HI-01 — `jwt_required`, `admin_required`, `tier_required` triplicate exception
        handling. The fix extracts a shared `_authenticate` helper.

HI-02 — Service-role JWT bypass only lived in `jwt_required`. Submitting the
        service-role key to an `@admin_required` or `@tier_required` endpoint
        used to 401 because Supabase rejects the service-role JWT shape. The
        first fix made the bypass symmetric. ADR-014 (2026-05-26) then
        *re-narrowed* the bypass to `jwt_required` only after introducing a
        dedicated `BATCH_SERVICE_TOKEN`, so admin/tier endpoints again refuse
        the service identity — but for a different reason (intentional
        scope-limiting, not a silent forwarding bug).
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
    """The three decorators must delegate to a single private helper."""

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
        importlib.reload(auth_mod)
        for name in ('jwt_required', 'admin_required'):
            src = inspect.getsource(getattr(auth_mod, name))
            line_count = len(src.splitlines())
            assert line_count <= 45, (
                f"{name} is {line_count} lines — consolidation should shrink "
                "it to ~30 lines or fewer."
            )


# ---------------------------------------------------------------------------
# ADR-014 — batch-service credential is independent of SUPABASE_SERVICE_ROLE_KEY
# and scoped to jwt_required only.
# ---------------------------------------------------------------------------

BATCH_TOKEN = 'batch-token-test-do-not-leak'
SERVICE_ROLE_KEY = 'service-role-test-key-do-not-leak'
VALID_USER_JWT = 'real-user-jwt-token-abc'


@pytest.fixture()
def app_with_decorators(monkeypatch):
    """Tiny Flask app that wires up the three decorators against a mock Supabase.

    Both `BATCH_SERVICE_TOKEN` and `SUPABASE_SERVICE_ROLE_KEY` are set so we
    can prove (a) the batch token unlocks `jwt_required`, (b) the service-role
    key does not unlock anything via HTTP after ADR-014.
    """
    monkeypatch.setenv('BATCH_SERVICE_TOKEN', BATCH_TOKEN)
    monkeypatch.setenv('SUPABASE_SERVICE_ROLE_KEY', SERVICE_ROLE_KEY)

    fake_supabase = MagicMock()

    def fake_get_user(token):
        from gotrue.errors import AuthApiError
        if token == VALID_USER_JWT:
            return SimpleNamespace(
                user=SimpleNamespace(id='user-abc', email='u@example.com')
            )
        raise AuthApiError('invalid jwt', 401, 'bad_jwt')

    fake_supabase.auth.get_user.side_effect = fake_get_user

    # users-table lookup: synthetic 'service-account' sub has no row, so
    # admin/tier checks return 403. Real users get 'admin' tier.
    def fake_table(_name):
        chain = MagicMock()
        sel = chain.select.return_value
        eq_obj = sel.eq.return_value

        def fake_execute():
            call = sel.eq.call_args
            sub = call.args[1] if call and len(call.args) > 1 else None
            if sub == 'service-account':
                return SimpleNamespace(data=[])
            return SimpleNamespace(data=[{'subscription_tier': 'admin'}])

        eq_obj.execute.side_effect = fake_execute
        return chain

    fake_supabase.table.side_effect = fake_table

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


class TestADR014_BatchServiceCredentialScoping:

    def _bearer(self, token):
        return {'Authorization': f'Bearer {token}'}

    def test_batch_token_unlocks_jwt_required(self, app_with_decorators):
        """ADR-014 — jwt_required still honours the bypass."""
        c = app_with_decorators.test_client()
        resp = c.get('/jwt-only', headers=self._bearer(BATCH_TOKEN))
        assert resp.status_code == 200
        assert resp.get_json()['sub'] == 'service-account'

    def test_batch_token_rejected_by_admin_required(self, app_with_decorators):
        """ADR-014 — admin_required rejects service identity (no users row → 403)."""
        c = app_with_decorators.test_client()
        resp = c.get('/admin-only', headers=self._bearer(BATCH_TOKEN))
        assert resp.status_code == 403, (
            "After ADR-014, BATCH_SERVICE_TOKEN must not unlock admin_required. "
            "Synthetic service-account sub has no users row, so the tier check "
            "403s — intentional re-narrowing of the HI-02 symmetric design."
        )

    def test_batch_token_rejected_by_tier_required(self, app_with_decorators):
        """ADR-014 — tier_required rejects service identity."""
        c = app_with_decorators.test_client()
        resp = c.get('/tier-only', headers=self._bearer(BATCH_TOKEN))
        assert resp.status_code == 403, (
            "After ADR-014, BATCH_SERVICE_TOKEN must not unlock tier_required."
        )

    def test_supabase_service_role_key_no_longer_grants_http_bypass(
        self, app_with_decorators
    ):
        """ADR-014 — the comparison against SUPABASE_SERVICE_ROLE_KEY was
        removed. Sending it as a bearer now 401s on every route."""
        c = app_with_decorators.test_client()
        for path in ('/jwt-only', '/admin-only', '/tier-only'):
            resp = c.get(path, headers=self._bearer(SERVICE_ROLE_KEY))
            assert resp.status_code == 401, (
                f"{path}: SUPABASE_SERVICE_ROLE_KEY must not bypass auth "
                f"after ADR-014; got {resp.status_code}"
            )

    def test_bogus_token_still_rejected(self, app_with_decorators):
        """Negative control — random tokens still 401, constant-time comparison preserved."""
        c = app_with_decorators.test_client()
        for path in ('/jwt-only', '/admin-only', '/tier-only'):
            resp = c.get(path, headers=self._bearer('not-the-batch-token'))
            assert resp.status_code in (401, 403), (
                f"{path} must still reject a non-matching token; got {resp.status_code}"
            )

    def test_real_user_jwt_still_works_on_admin_route(self, app_with_decorators):
        """Regression guard: removing the service_role short-circuit must not
        break real admin-user authentication."""
        c = app_with_decorators.test_client()
        resp = c.get('/admin-only', headers=self._bearer(VALID_USER_JWT))
        assert resp.status_code == 200


class TestADR014_FeatureOffWhenTokenUnset:
    """ADR-014 — `BATCH_SERVICE_TOKEN` unset = bypass branch inert."""

    def test_bypass_inert_when_env_var_missing(self, monkeypatch):
        monkeypatch.delenv('BATCH_SERVICE_TOKEN', raising=False)
        monkeypatch.delenv('SUPABASE_SERVICE_ROLE_KEY', raising=False)

        fake_supabase = MagicMock()
        from gotrue.errors import AuthApiError
        fake_supabase.auth.get_user.side_effect = AuthApiError(
            'invalid jwt', 401, 'bad_jwt'
        )

        with patch.object(
            auth_mod, '_get_supabase_client', return_value=fake_supabase
        ):
            app = Flask(__name__)

            @app.route('/protected')
            @auth_mod.jwt_required
            def protected():
                return jsonify({'ok': True})

            c = app.test_client()
            resp = c.get(
                '/protected',
                headers={'Authorization': f'Bearer {BATCH_TOKEN}'},
            )
            assert resp.status_code == 401
