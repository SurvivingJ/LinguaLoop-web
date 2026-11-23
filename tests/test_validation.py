# tests/test_validation.py
"""Tests for Pydantic request validation on key endpoints."""

import json


def resp_json(resp):
    return json.loads(resp.data)


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
