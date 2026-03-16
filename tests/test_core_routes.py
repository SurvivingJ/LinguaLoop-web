# tests/test_core_routes.py
"""Tests for core application routes (health, config, metadata, errors)."""

import json
import pytest


class TestHealthCheck:
    """GET /api/health"""

    def test_returns_200(self, client):
        resp = client.get('/api/health')
        assert resp.status_code == 200

    def test_contains_status_healthy(self, client):
        data = resp_json(client.get('/api/health'))
        assert data['status'] == 'healthy'

    def test_contains_services_dict(self, client):
        data = resp_json(client.get('/api/health'))
        assert 'services' in data
        assert isinstance(data['services'], dict)

    def test_contains_version(self, client):
        data = resp_json(client.get('/api/health'))
        assert 'version' in data


class TestConfig:
    """GET /api/config"""

    def test_returns_200(self, client):
        resp = client.get('/api/config')
        assert resp.status_code == 200

    def test_contains_features(self, client):
        data = resp_json(client.get('/api/config'))
        assert 'features' in data
        assert isinstance(data['features'], dict)


class TestMetadata:
    """GET /api/metadata"""

    def test_returns_200(self, client):
        resp = client.get('/api/metadata')
        assert resp.status_code == 200

    def test_contains_languages_and_test_types(self, client):
        data = resp_json(client.get('/api/metadata'))
        assert 'languages' in data
        assert 'test_types' in data


class TestErrorHandlers:
    """Global error handlers."""

    def test_404_api_returns_json(self, client):
        resp = client.get('/api/nonexistent-endpoint')
        assert resp.status_code == 404
        data = resp_json(resp)
        assert 'error' in data

    def test_405_returns_json(self, client):
        # POST to health which only allows GET
        resp = client.post('/api/health')
        assert resp.status_code == 405
        data = resp_json(resp)
        assert 'error' in data


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def resp_json(resp):
    """Extract JSON from a Flask test response."""
    return json.loads(resp.data)
