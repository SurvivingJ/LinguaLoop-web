# tests/test_validation.py
"""Tests for Pydantic request validation on key endpoints."""

import json
import pytest


def resp_json(resp):
    return json.loads(resp.data)


class TestVocabularyExtractValidation:
    """POST /api/vocabulary/extract — Pydantic validation."""

    def test_rejects_empty_body(self, client, auth_headers):
        resp = client.post('/api/vocabulary/extract', json={}, headers=auth_headers)
        assert resp.status_code == 400

    def test_rejects_missing_text(self, client, auth_headers):
        resp = client.post('/api/vocabulary/extract',
                           json={'language_code': 'es'},
                           headers=auth_headers)
        assert resp.status_code == 400

    def test_rejects_missing_language_code(self, client, auth_headers):
        resp = client.post('/api/vocabulary/extract',
                           json={'text': 'Hola mundo'},
                           headers=auth_headers)
        assert resp.status_code == 400


class TestErrorLogValidation:
    """POST /api/errors/log — Pydantic validation."""

    def test_rejects_empty_body(self, client, auth_headers):
        resp = client.post('/api/errors/log', json={}, headers=auth_headers)
        assert resp.status_code == 400

    def test_rejects_missing_error_type(self, client, auth_headers):
        resp = client.post('/api/errors/log',
                           json={'error_message': 'something broke'},
                           headers=auth_headers)
        assert resp.status_code == 400

    def test_rejects_oversized_metadata(self, client, auth_headers):
        huge_metadata = {'data': 'x' * 11000}
        resp = client.post('/api/errors/log',
                           json={
                               'error_type': 'js_error',
                               'error_message': 'test',
                               'metadata': huge_metadata,
                           },
                           headers=auth_headers)
        assert resp.status_code == 400

    def test_accepts_valid_error_log(self, client, auth_headers, app):
        # Mock the DB insert
        chain = app.mock_supabase.table.return_value
        chain.execute.return_value = type('R', (), {'data': [{'id': 1}]})()

        resp = client.post('/api/errors/log',
                           json={
                               'error_type': 'js_error',
                               'error_message': 'Uncaught TypeError',
                               'url': '/tests',
                           },
                           headers=auth_headers)
        assert resp.status_code == 201


class TestWordQuizValidation:
    """POST /api/vocabulary/word-quiz — Pydantic validation."""

    def test_rejects_empty_results(self, client, auth_headers):
        resp = client.post('/api/vocabulary/word-quiz',
                           json={'language_id': 1, 'results': []},
                           headers=auth_headers)
        assert resp.status_code == 400

    def test_rejects_missing_language_id(self, client, auth_headers):
        resp = client.post('/api/vocabulary/word-quiz',
                           json={'results': [{'sense_id': 1, 'selected_answer': 'a',
                                              'correct_answer': 'a', 'is_correct': True}]},
                           headers=auth_headers)
        assert resp.status_code == 400


class TestReportSubmitValidation:
    """POST /api/reports/submit"""

    def test_rejects_invalid_category(self, client, auth_headers):
        resp = client.post('/api/reports/submit',
                           json={'report_category': 'invalid', 'description': 'a' * 20},
                           headers=auth_headers)
        assert resp.status_code == 400

    def test_rejects_short_description(self, client, auth_headers):
        resp = client.post('/api/reports/submit',
                           json={'report_category': 'other', 'description': 'hi'},
                           headers=auth_headers)
        assert resp.status_code == 400
