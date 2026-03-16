# tests/test_auth.py
"""Tests for authentication enforcement on protected routes."""

import json
import pytest

# A sample of JWT-protected endpoints and their methods
PROTECTED_ENDPOINTS = [
    ('GET', '/api/users/elo?language_id=1'),
    ('GET', '/api/users/tokens'),
    ('GET', '/api/users/profile'),
    ('GET', '/api/flashcards/due?language_id=1'),
    ('GET', '/api/flashcards/stats?language_id=1'),
    ('POST', '/api/flashcards/review'),
    ('POST', '/api/flashcards/skip'),
    ('POST', '/api/vocabulary/word-quiz'),
    ('POST', '/api/reports/submit'),
    ('POST', '/api/vocabulary/extract'),
]


class TestAuthEnforcement:
    """Protected endpoints must return 401 without a token."""

    @pytest.mark.parametrize("method,path", PROTECTED_ENDPOINTS)
    def test_returns_401_without_token(self, client, method, path):
        if method == 'GET':
            resp = client.get(path)
        else:
            resp = client.post(path, json={})
        assert resp.status_code == 401, f"{method} {path} should require auth"
        data = json.loads(resp.data)
        assert 'error' in data


class TestAuthWithToken:
    """Protected endpoints accept a valid token and do not return 401."""

    def test_users_profile_with_token(self, client, auth_headers, app):
        """Profile endpoint should pass auth and hit the Supabase mock."""
        # Configure mock to return a user profile
        chain = app.mock_supabase.table.return_value
        chain.single.return_value = chain
        chain.execute.return_value = _mock_response([{
            'id': 'test-user-id-123',
            'email': 'test@example.com',
            'display_name': 'Test User',
            'email_verified': True,
            'total_tests_taken': 5,
            'total_tests_generated': 3,
            'last_activity_at': '2026-01-01T00:00:00Z',
            'subscription_tier_id': 1,
            'created_at': '2025-06-01T00:00:00Z',
            'last_login': '2026-01-01T00:00:00Z',
        }])

        resp = client.get('/api/users/profile', headers=auth_headers)
        # Should not be 401 — auth passed
        assert resp.status_code != 401

    def test_health_does_not_require_auth(self, client):
        """Health check is public — no token needed."""
        resp = client.get('/api/health')
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_response(data, count=None):
    from types import SimpleNamespace
    r = SimpleNamespace(data=data, count=count if count is not None else len(data))
    return r
