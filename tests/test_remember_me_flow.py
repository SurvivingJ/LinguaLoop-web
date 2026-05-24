"""RED reproducers for the "Remember me" regression.

Symptom: user ticks "Remember this device for 6 months", logs in, comes back
later with a valid HttpOnly trusted-device cookie — and is still forced to
re-login.

Root cause (frontend): the head-script in `templates/base.html` runs a
synchronous redirect to `/login` when localStorage/sessionStorage have no
`jwt_token`, BEFORE any code attempts `/api/auth/device-restore`. The
trusted-device cookie is HttpOnly, so JS cannot detect it; the cookie is
simply never exchanged.

Backend `/api/auth/device-restore` already works (covered as a sanity
check below). The fix lives in:
  1. base.html head-script — try device-restore first; bounce only on fail.
  2. login.html — also try silent device-restore on /login page load so
     bookmarked /login users don't have to OTP again.

These tests freeze the behaviour we want:
  - base.html source contains a fetch to /api/auth/device-restore before
    any /login redirect.
  - login.html source contains a device-restore attempt on page load.
  - The backend endpoint still honours a valid cookie end-to-end (sanity).
"""

import re
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock

import pytest

from config import Config


# ---------------------------------------------------------------------------
# Frontend bootstrap — head script must try device-restore before bouncing
# ---------------------------------------------------------------------------

class TestRememberMe_HeadScriptOrdering:
    """The head-script that redirects unauthenticated users to /login must
    try `/api/auth/device-restore` first. Today it does not.

    We assert on the rendered HTML, which is the only place this logic lives.
    """

    def _render_base(self, client):
        resp = client.get('/login')
        assert resp.status_code == 200
        return resp.get_data(as_text=True)

    def test_base_html_attempts_device_restore_before_redirect(self, client):
        html = self._render_base(client)

        assert '/api/auth/device-restore' in html, (
            "Rendered base.html must reference /api/auth/device-restore. "
            "Frontend bootstrap should call this endpoint on page load when "
            "no JWT is in storage."
        )

        # Textual ordering check: the FIRST device-restore reference must
        # precede the FIRST window.location.href = '/login' redirect.
        idx_restore = html.find('/api/auth/device-restore')
        idx_redirect = html.find("window.location.href = '/login'")
        assert idx_restore != -1 and idx_redirect != -1
        assert idx_restore < idx_redirect, (
            "Device-restore attempt must appear in the bootstrap BEFORE the "
            "first window.location.href = '/login' redirect. Today the "
            "redirect is the very first thing in <head>, defeating the "
            "trusted-device cookie."
        )

    def test_login_page_attempts_device_restore_on_load(self, client):
        """A user landing on /login with a valid trusted-device cookie should
        be auto-restored — they shouldn't have to OTP again.

        base.html already declares `_tryDeviceRestore()` and calls it once
        from inside `authFetch` (the on-401 path). For this test to pass we
        need MORE than that — login.html must add its own call so the
        restore happens at page load, before the user types anything.
        """
        resp = client.get('/login')
        assert resp.status_code == 200
        html = resp.get_data(as_text=True)

        # Count call sites, EXCLUDING the function declaration line.
        # Today base.html has exactly one call (inside authFetch). After
        # the fix, login.html or base.html should call it again on load.
        call_sites = re.findall(
            r'(?<!function\s)\b_tryDeviceRestore\s*\(\s*\)',
            html,
        )
        direct_fetches = re.findall(
            r'fetch\s*\(\s*[\'"`]/api/auth/device-restore',
            html,
        )
        total_invocations = len(call_sites) + len(direct_fetches)

        # The existing single call inside authFetch contributes 1.
        # We require at least one ADDITIONAL invocation on page-load.
        # (Direct fetches count too; whichever pattern the fix uses.)
        # base.html has 1 existing fetch + 1 existing call = 2 baseline
        # references today, and the test should still demand a third
        # (the on-load page invocation).
        assert total_invocations >= 3, (
            "login.html / base.html must invoke device-restore on page load "
            "(in addition to the existing on-401 retry inside authFetch). "
            f"Found {len(call_sites)} _tryDeviceRestore() calls + "
            f"{len(direct_fetches)} direct fetches = {total_invocations}; "
            "need >= 3."
        )


# ---------------------------------------------------------------------------
# Backend sanity — /api/auth/device-restore happy path
# ---------------------------------------------------------------------------

class TestRememberMe_BackendHappyPath:

    def test_device_restore_returns_jwt_with_valid_cookie(self, client, app):
        from routes.auth import auth_bp

        fake_device_service = MagicMock()
        fake_device_service.restore_from_token.return_value = {
            'user_id': 'user-abc',
            'user_email': 'jamesccmcb@gmail.com',
            'new_raw_token': 'new-rotated-raw-token',
            'expires_at': datetime.now(timezone.utc) + timedelta(days=180),
        }
        auth_bp.device_service = fake_device_service

        fake_auth_service = MagicMock()
        fake_auth_service.mint_session_for_user.return_value = {
            'success': True,
            'jwt_token': 'fresh.jwt.token',
            'refresh_token': 'fresh.refresh.token',
        }
        fake_auth_service.get_user_profile.return_value = {
            'success': True,
            'user': {
                'id': 'user-abc',
                'email': 'jamesccmcb@gmail.com',
                'subscription_tier': 'free',
                'token_balance': 0,
                'total_tests_taken': 0,
                'total_tests_generated': 0,
                'has_seen_welcome': True,
                'email_verified': True,
            },
        }
        auth_bp.auth_service = fake_auth_service

        client.set_cookie(
            domain='localhost',
            key=Config.DEVICE_COOKIE_NAME,
            value='some-raw-cookie-value',
            path=Config.DEVICE_COOKIE_PATH,
        )
        resp = client.post('/api/auth/device-restore')

        assert resp.status_code == 200, resp.get_data(as_text=True)
        body = resp.get_json()
        assert body['success'] is True
        assert body['jwt_token'] == 'fresh.jwt.token'
        assert body['user']['id'] == 'user-abc'

        set_cookie = resp.headers.get('Set-Cookie', '')
        assert Config.DEVICE_COOKIE_NAME in set_cookie, (
            "device-restore must rotate the cookie on success."
        )

    def test_device_restore_clears_cookie_on_invalid_token(self, client, app):
        from routes.auth import auth_bp

        fake_device_service = MagicMock()
        fake_device_service.restore_from_token.return_value = None
        auth_bp.device_service = fake_device_service

        client.set_cookie(
            domain='localhost',
            key=Config.DEVICE_COOKIE_NAME,
            value='stale-or-bad-token',
            path=Config.DEVICE_COOKIE_PATH,
        )
        resp = client.post('/api/auth/device-restore')

        assert resp.status_code == 401
        set_cookie = resp.headers.get('Set-Cookie', '')
        assert 'Max-Age=0' in set_cookie or 'expires=' in set_cookie.lower(), (
            "device-restore must clear the cookie on invalid-token responses "
            "so the browser stops sending it."
        )

    def test_device_restore_401_when_no_cookie(self, client, app):
        """No cookie → 401, NOT 500."""
        from routes.auth import auth_bp
        auth_bp.device_service = MagicMock()

        resp = client.post('/api/auth/device-restore')
        assert resp.status_code == 401
