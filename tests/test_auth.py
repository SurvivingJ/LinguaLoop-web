# tests/test_auth.py
"""Tests for authentication enforcement on protected routes."""

import json
import pytest

# A sample of JWT-protected endpoints and their methods
PROTECTED_ENDPOINTS = [
    ('GET', '/api/users/elo?language_id=1'),
    ('GET', '/api/flashcards/due?language_id=1'),
    ('GET', '/api/flashcards/stats?language_id=1'),
    ('POST', '/api/flashcards/review'),
    ('POST', '/api/flashcards/skip'),
    ('POST', '/api/vocabulary/word-quiz'),
    ('POST', '/api/reports/submit'),
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

    def test_users_preferences_with_token(self, client, auth_headers):
        """A protected route should pass auth and hit the Supabase mock."""
        resp = client.get('/api/users/preferences', headers=auth_headers)
        # Should not be 401 — auth passed
        assert resp.status_code != 401

    def test_health_does_not_require_auth(self, client):
        """Health check is public — no token needed."""
        resp = client.get('/api/health')
        assert resp.status_code == 200
