# tests/test_users.py
"""Tests for user-related endpoints (profile, tokens, ELO)."""

import json
import pytest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch


def resp_json(resp):
    return json.loads(resp.data)


def _make_chain(data, count=None):
    """Build a MagicMock where every chained method returns self,
    and .execute() returns SimpleNamespace(data=data, count=count)."""
    chain = MagicMock()
    result = SimpleNamespace(data=data, count=count or 0)
    chain.execute.return_value = result
    for m in ('select', 'eq', 'neq', 'lte', 'single', 'order', 'or_',
              'limit', 'offset', 'insert', 'update', 'delete', 'filter'):
        getattr(chain, m).return_value = chain
    return chain


class TestGetUserProfile:
    """GET /api/users/profile"""

    def test_returns_profile(self, client, auth_headers, app):
        app.mock_supabase.table.return_value = _make_chain({
            'id': 'test-user-id-123',
            'email': 'test@example.com',
            'display_name': 'Test User',
            'email_verified': True,
            'total_tests_taken': 10,
            'total_tests_generated': 5,
            'last_activity_at': None,
            'subscription_tier_id': 1,
            'created_at': '2025-01-01',
            'last_login': '2026-03-01',
        })

        resp = client.get('/api/users/profile', headers=auth_headers)
        assert resp.status_code == 200
        data = resp_json(resp)
        assert data['status'] == 'success'
        assert data['profile']['display_name'] == 'Test User'

    def test_returns_404_when_user_not_found(self, client, auth_headers, app):
        app.mock_supabase.table.return_value = _make_chain(None)

        resp = client.get('/api/users/profile', headers=auth_headers)
        assert resp.status_code == 404

    def test_profile_does_not_leak_password_hash(self, client, auth_headers, app):
        app.mock_supabase.table.return_value = _make_chain({
            'id': 'test-user-id-123',
            'email': 'test@example.com',
            'display_name': 'Tester',
            'email_verified': True,
            'total_tests_taken': 0,
            'total_tests_generated': 0,
            'last_activity_at': None,
            'subscription_tier_id': 1,
            'created_at': '2025-01-01',
            'last_login': None,
        })

        resp = client.get('/api/users/profile', headers=auth_headers)
        data = resp_json(resp)
        assert 'password_hash' not in json.dumps(data)


class TestGetTokenBalance:
    """GET /api/users/tokens"""

    def test_returns_token_balance(self, client, auth_headers, app):
        # Mock the RPC call
        rpc_chain = MagicMock()
        rpc_chain.execute.return_value = SimpleNamespace(data={})
        app.mock_supabase.rpc.return_value = rpc_chain

        # Mock the table query — single() means data is a dict
        app.mock_supabase.table.return_value = _make_chain({
            'tokens': 50,
            'last_free_token_date': '2026-03-17',
        })

        resp = client.get('/api/users/tokens', headers=auth_headers)
        assert resp.status_code == 200
        data = resp_json(resp)
        assert data['status'] == 'success'
        assert data['total_tokens'] == 50

    def test_returns_404_when_user_missing(self, client, auth_headers, app):
        rpc_chain = MagicMock()
        rpc_chain.execute.return_value = SimpleNamespace(data={})
        app.mock_supabase.rpc.return_value = rpc_chain

        app.mock_supabase.table.return_value = _make_chain(None)

        resp = client.get('/api/users/tokens', headers=auth_headers)
        assert resp.status_code == 404


class TestNativeLanguage:
    """GET / PATCH /api/users/native-language (TASK-619)"""

    def test_get_returns_set_value(self, client, auth_headers, app):
        app.mock_supabase.table.return_value = _make_chain({'native_language_id': 3})

        resp = client.get('/api/users/native-language', headers=auth_headers)
        assert resp.status_code == 200
        data = resp_json(resp)
        assert data['status'] == 'success'
        assert data['native_language_id'] == 3

    def test_get_returns_null_when_unset(self, client, auth_headers, app):
        # NULL is a legitimate state for every pre-TASK-619 user.
        app.mock_supabase.table.return_value = _make_chain({'native_language_id': None})

        resp = client.get('/api/users/native-language', headers=auth_headers)
        assert resp.status_code == 200
        assert resp_json(resp)['native_language_id'] is None

    def test_get_returns_null_when_no_row(self, client, auth_headers, app):
        app.mock_supabase.table.return_value = _make_chain(None)

        resp = client.get('/api/users/native-language', headers=auth_headers)
        assert resp.status_code == 200
        assert resp_json(resp)['native_language_id'] is None

    def test_patch_sets_supported_language(self, client, auth_headers, app):
        chain = _make_chain([{'native_language_id': 1}])
        app.mock_supabase.table.return_value = chain

        resp = client.patch(
            '/api/users/native-language', headers=auth_headers,
            json={'language_id': 1},
        )
        assert resp.status_code == 200
        assert resp_json(resp)['native_language_id'] == 1

        # Wrote the plain column directly, scoped to the authed user.
        chain.update.assert_called_once_with({'native_language_id': 1})
        chain.eq.assert_called_once_with('id', 'test-user-id-123')

    def test_patch_accepts_numeric_string(self, client, auth_headers, app):
        # parse_language_id coerces "2" -> 2 (still a supported id).
        app.mock_supabase.table.return_value = _make_chain([{'native_language_id': 2}])

        resp = client.patch(
            '/api/users/native-language', headers=auth_headers,
            json={'language_id': '2'},
        )
        assert resp.status_code == 200
        assert resp_json(resp)['native_language_id'] == 2

    def test_patch_rejects_unsupported_id(self, client, auth_headers, app):
        chain = _make_chain([])
        app.mock_supabase.table.return_value = chain

        resp = client.patch(
            '/api/users/native-language', headers=auth_headers,
            json={'language_id': 99},
        )
        assert resp.status_code == 400
        # Rejected before any write.
        chain.update.assert_not_called()

    def test_patch_rejects_non_integer(self, client, auth_headers, app):
        chain = _make_chain([])
        app.mock_supabase.table.return_value = chain

        resp = client.patch(
            '/api/users/native-language', headers=auth_headers,
            json={'language_id': 'english'},
        )
        assert resp.status_code == 400
        chain.update.assert_not_called()

    def test_patch_rejects_missing_field(self, client, auth_headers, app):
        chain = _make_chain([])
        app.mock_supabase.table.return_value = chain

        resp = client.patch(
            '/api/users/native-language', headers=auth_headers, json={},
        )
        assert resp.status_code == 400
        chain.update.assert_not_called()

    def test_get_requires_auth(self, client):
        assert client.get('/api/users/native-language').status_code == 401

    def test_patch_requires_auth(self, client):
        resp = client.patch('/api/users/native-language', json={'language_id': 1})
        assert resp.status_code == 401


class TestGetUserElo:
    """GET /api/users/elo"""

    def test_requires_auth(self, client):
        resp = client.get('/api/users/elo')
        assert resp.status_code == 401

    def test_returns_ratings_with_auth(self, client, auth_headers, app):
        with patch('routes.users.get_test_service') as mock_ts:
            mock_ts.return_value.get_user_elo_summary.return_value = {
                'ratings': [],
                'languages': {},
            }
            resp = client.get('/api/users/elo', headers=auth_headers)
            assert resp.status_code == 200
            data = resp_json(resp)
            assert data['status'] == 'success'
            assert 'ratings' in data
