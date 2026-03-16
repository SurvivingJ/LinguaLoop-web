# tests/test_flashcards.py
"""Tests for flashcard endpoints (due, review, stats, skip)."""

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


class TestGetDueCards:
    """GET /api/flashcards/due"""

    def test_requires_language_id(self, client, auth_headers):
        resp = client.get('/api/flashcards/due', headers=auth_headers)
        assert resp.status_code == 400
        data = resp_json(resp)
        assert 'error' in data

    def test_returns_empty_list(self, client, auth_headers, app):
        db_mock = MagicMock()
        db_mock.table.return_value = _make_chain([])
        with patch('routes.flashcards.get_supabase_admin', return_value=db_mock):
            resp = client.get('/api/flashcards/due?language_id=1', headers=auth_headers)
        assert resp.status_code == 200
        data = resp_json(resp)
        assert data['cards'] == []
        assert data['total'] == 0

    def test_returns_cards(self, client, auth_headers, app):
        db_mock = MagicMock()
        db_mock.table.return_value = _make_chain([{
            'id': 1,
            'sense_id': 42,
            'stability': 5.0,
            'difficulty': 0.3,
            'due_date': '2026-03-17',
            'last_review': '2026-03-16',
            'reps': 3,
            'lapses': 0,
            'state': 'review',
            'example_sentence': 'Hola mundo',
            'audio_url': None,
            'dim_word_senses': {
                'id': 42,
                'definition': 'hello',
                'pronunciation': '/ola/',
                'example_sentence': 'Hola amigo',
                'dim_vocabulary': {
                    'lemma': 'hola',
                    'language_id': 1,
                    'frequency_rank': 10,
                },
            },
        }])
        with patch('routes.flashcards.get_supabase_admin', return_value=db_mock):
            resp = client.get('/api/flashcards/due?language_id=1', headers=auth_headers)
        assert resp.status_code == 200
        data = resp_json(resp)
        assert data['total'] == 1
        assert data['cards'][0]['lemma'] == 'hola'
        assert data['cards'][0]['definition'] == 'hello'


class TestSubmitReview:
    """POST /api/flashcards/review"""

    def test_rejects_missing_card_id(self, client, auth_headers):
        resp = client.post('/api/flashcards/review',
                           json={'rating': 3},
                           headers=auth_headers)
        assert resp.status_code == 400

    def test_rejects_invalid_rating(self, client, auth_headers):
        resp = client.post('/api/flashcards/review',
                           json={'card_id': 1, 'rating': 5},
                           headers=auth_headers)
        assert resp.status_code == 400

    def test_rejects_rating_zero(self, client, auth_headers):
        resp = client.post('/api/flashcards/review',
                           json={'card_id': 1, 'rating': 0},
                           headers=auth_headers)
        assert resp.status_code == 400


class TestSkipCard:
    """POST /api/flashcards/skip"""

    def test_rejects_missing_card_id(self, client, auth_headers):
        resp = client.post('/api/flashcards/skip',
                           json={},
                           headers=auth_headers)
        assert resp.status_code == 400

    def test_accepts_valid_skip(self, client, auth_headers, app):
        db_mock = MagicMock()
        db_mock.table.return_value = _make_chain([])
        with patch('routes.flashcards.get_supabase_admin', return_value=db_mock):
            resp = client.post('/api/flashcards/skip',
                               json={'card_id': 99},
                               headers=auth_headers)
        assert resp.status_code == 200


class TestFlashcardStats:
    """GET /api/flashcards/stats"""

    def test_requires_language_id(self, client, auth_headers):
        resp = client.get('/api/flashcards/stats', headers=auth_headers)
        assert resp.status_code == 400
