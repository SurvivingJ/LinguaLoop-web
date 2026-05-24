"""RED reproducers for HI-07.

`send_otp`, `get_profile`, `logout` (and any sibling) currently call
`request.get_json()` without an `or {}` fallback. A request with no body
(or wrong Content-Type) returns `data = None`, which crashes the next
`.get(...)` call. The crash is caught by a broad `except Exception` that
logs nothing useful — the user sees a generic "Server error occurred" and
the operator sees no traceback.

After the fix:
  - missing-body requests on `send_otp` return a 400 validation error,
    NOT a 500.
  - the route's broad `except` logs with `exc_info=True` so we can see the
    traceback in tests via caplog.
"""

import json
import logging
from unittest.mock import MagicMock

import pytest


# ---------------------------------------------------------------------------
# HI-07a — send_otp must not 500 on a missing JSON body
# ---------------------------------------------------------------------------

class TestHI07_SendOtpMissingBody:

    def test_send_otp_no_body_returns_400_not_500(self, client, app):
        """`POST /api/auth/send-otp` with no body should be a 400, not a 500.

        Today it returns 500 because `request.get_json()` is None and
        `data.get(...)` raises AttributeError. Caught by the broad except,
        which returns the generic 500.
        """
        resp = client.post('/api/auth/send-otp')  # no body, no Content-Type
        assert resp.status_code == 400, (
            f"Expected 400 for missing body, got {resp.status_code}. "
            "send_otp must handle `data is None` instead of crashing."
        )
        data = json.loads(resp.data)
        assert 'error' in data

    def test_send_otp_empty_json_returns_400(self, client):
        """`POST /api/auth/send-otp` with `{}` is also a validation 400."""
        resp = client.post(
            '/api/auth/send-otp',
            data='{}',
            content_type='application/json',
        )
        assert resp.status_code == 400
        data = json.loads(resp.data)
        assert 'error' in data

    def test_send_otp_invalid_content_type_returns_400(self, client):
        """Non-JSON Content-Type must also be handled cleanly."""
        resp = client.post(
            '/api/auth/send-otp',
            data='email=foo@bar.com',
            content_type='application/x-www-form-urlencoded',
        )
        assert resp.status_code in (400, 415), (
            f"Form-urlencoded body should be rejected with 400/415, "
            f"got {resp.status_code}."
        )


# ---------------------------------------------------------------------------
# HI-07b — broad except must log with exc_info so diagnostics survive
# ---------------------------------------------------------------------------

class TestHI07_ExcInfoOnBroadExcept:
    """The broad `except Exception` in send_otp / get_profile / logout must
    log with `exc_info=True` (matching the verify_otp / refresh_token pattern).

    We force an exception inside the route by making the underlying service
    raise, then assert caplog captured the traceback.
    """

    def test_send_otp_logs_traceback_when_service_raises(self, client, app, caplog):
        from routes.auth import auth_bp
        auth_bp.auth_service = MagicMock()
        auth_bp.auth_service.send_otp.side_effect = RuntimeError(
            'simulated_send_otp_failure'
        )

        with caplog.at_level(logging.ERROR, logger='routes.auth'):
            resp = client.post(
                '/api/auth/send-otp',
                data=json.dumps({'email': 'jamesccmcb@gmail.com'}),
                content_type='application/json',
            )

        assert resp.status_code == 500
        traceback_logged = any(
            rec.exc_info is not None for rec in caplog.records
        )
        assert traceback_logged, (
            "send_otp's broad `except` must call logger.error(..., exc_info=True) "
            "so the traceback survives in production logs. Today it logs "
            "nothing — operator sees only 'Server error occurred'."
        )

    def test_get_profile_logs_traceback_when_service_raises(
        self, client, app, auth_headers, caplog
    ):
        from routes.auth import auth_bp
        auth_bp.auth_service = MagicMock()
        auth_bp.auth_service.get_user_profile.side_effect = RuntimeError(
            'simulated_profile_failure'
        )

        with caplog.at_level(logging.ERROR, logger='routes.auth'):
            resp = client.get('/api/auth/profile', headers=auth_headers)

        assert resp.status_code == 500
        assert any(rec.exc_info is not None for rec in caplog.records), (
            "get_profile's broad `except` must log with exc_info=True."
        )

    def test_logout_logs_traceback_when_service_raises(
        self, client, app, auth_headers, caplog
    ):
        from routes.auth import auth_bp
        auth_bp.auth_service = MagicMock()
        auth_bp.auth_service.logout.side_effect = RuntimeError(
            'simulated_logout_failure'
        )

        with caplog.at_level(logging.ERROR, logger='routes.auth'):
            resp = client.post('/api/auth/logout', headers=auth_headers)

        assert resp.status_code == 500
        assert any(rec.exc_info is not None for rec in caplog.records), (
            "logout's broad `except` must log with exc_info=True."
        )
