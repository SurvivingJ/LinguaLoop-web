"""TASK-891: flashcard + dual-translation endpoints credit clamped ``active_ms``."""

from types import SimpleNamespace
from unittest.mock import patch

import pytest

import routes.dual_translation as dt_routes

USER = 'test-user-id-123'
EVT = '7b9e1d8e-4c1a-4f0a-9d6e-0a1b2c3d4e5f'
EVT2 = '11111111-2222-4333-8444-555555555555'


class _Q:
    def __init__(self, data):
        self._data = data

    def __getattr__(self, _n):
        return lambda *a, **k: self

    def execute(self):
        return SimpleNamespace(data=self._data, count=0)


class LedgerDB:
    def __init__(self, tables=None):
        self.tables, self.rpcs, self.seen = tables or {}, [], set()

    def table(self, name):
        return _Q(self.tables.get(name, []))

    def rpc(self, name, params):
        self.rpcs.append((name, params))
        data = {}
        if name == 'credit_study_time':
            key = (params['p_kind'], params['p_source_table'], params['p_source_id'])
            data = key not in self.seen
            self.seen.add(key)
        return _Q(data)

    def credits(self):
        return [p for n, p in self.rpcs if n == 'credit_study_time']


CARD = {'id': 1, 'sense_id': 5, 'language_id': 3, 'stability': 2.0, 'difficulty': 0.3,
        'due_date': '2026-10-10', 'last_review': '2026-10-01T00:00:00Z', 'reps': 2,
        'lapses': 0, 'state': 'review'}


# ---------------------------------------------------------------- flashcards

class TestFlashcardReview:
    def _post(self, client, auth_headers, db, **extra):
        with patch('routes.flashcards.get_supabase_admin', return_value=db), \
             patch('routes.flashcards.VocabularyKnowledgeService'):
            return client.post('/api/flashcards/review', headers=auth_headers,
                               json={'card_id': 1, 'rating': 3, **extra})

    def test_credits_clamped_seconds(self, client, auth_headers):
        db = LedgerDB({'user_flashcards': CARD})
        r = self._post(client, auth_headers, db, active_ms=8_700, client_event_id=EVT)
        assert r.status_code == 200
        (c,) = db.credits()
        assert c == {'p_user_id': USER, 'p_language_id': 3, 'p_kind': 'flashcard',
                     'p_seconds': 8, 'p_source_table': 'flashcard_review', 'p_source_id': EVT}

    def test_clamped_to_120(self, client, auth_headers):
        db = LedgerDB({'user_flashcards': CARD})
        self._post(client, auth_headers, db, active_ms=10**12, client_event_id=EVT)
        assert db.credits()[0]['p_seconds'] == 120

    def test_same_event_id_twice_credits_once(self, client, auth_headers):
        db = LedgerDB({'user_flashcards': CARD})
        self._post(client, auth_headers, db, active_ms=5000, client_event_id=EVT)
        self._post(client, auth_headers, db, active_ms=5000, client_event_id=EVT)
        assert len(db.seen) == 1
        self._post(client, auth_headers, db, active_ms=5000, client_event_id=EVT2)
        assert len(db.seen) == 2

    @pytest.mark.parametrize('extra', [
        {}, {'active_ms': 5000}, {'client_event_id': EVT},
        {'active_ms': 5000, 'client_event_id': 'not-a-uuid'},
        {'active_ms': 'x', 'client_event_id': EVT}, {'active_ms': -50, 'client_event_id': EVT},
        {'active_ms': True, 'client_event_id': EVT},
    ])
    def test_missing_or_invalid_fields_credit_nothing_and_never_400(self, client, auth_headers, extra):
        db = LedgerDB({'user_flashcards': CARD})
        r = self._post(client, auth_headers, db, **extra)
        assert r.status_code == 200
        assert db.credits() == []

    def test_credit_failure_does_not_fail_review(self, client, auth_headers):
        db = LedgerDB({'user_flashcards': CARD})
        db.rpc = lambda *a, **k: (_ for _ in ()).throw(RuntimeError('down'))
        r = self._post(client, auth_headers, db, active_ms=5000, client_event_id=EVT)
        assert r.status_code == 200


# ---------------------------------------------------------- DT submit (grading)

class TestDtSubmit:
    CONTRACT = {'scores': {'accuracy': 3}, 'overall_band': 3, 'diff': [], 'errors': [],
                'grader_trace': {}}

    def _wire(self, app, monkeypatch, cached=None, contract=None):
        db = LedgerDB()
        app.supabase_service = db
        monkeypatch.setattr(dt_routes, '_get_submission',
                            lambda d, s: {'id': s, 'user_id': USER, 'passage_id': 9, 'l1_language_id': 2})
        monkeypatch.setattr(dt_routes, '_cached_grade', lambda d, s: cached)
        monkeypatch.setattr(dt_routes, '_get_passage', lambda d, p: {
            'id': 9, 'l2_text': 'gold', 'l2_language_id': 3, 'age_tier': 4, 'status': 'active'})
        monkeypatch.setattr(dt_routes, '_tokens_used_today', lambda d, u: 0)
        monkeypatch.setattr(dt_routes, '_persist_grade', lambda *a, **k: None)
        monkeypatch.setattr(dt_routes, 'grade_submission', lambda d, **k: contract or self.CONTRACT)
        return db

    def test_first_grading_credits_with_submission_id(self, client, app, auth_headers, monkeypatch):
        db = self._wire(app, monkeypatch)
        r = client.post('/api/dual-translation/5/submit', headers=auth_headers,
                        json={'reproduction': 'x', 'active_ms': 95_000})
        assert r.status_code == 200
        (c,) = db.credits()
        assert (c['p_kind'], c['p_source_table'], c['p_source_id'], c['p_language_id'],
                c['p_seconds']) == ('dual_translation', 'dt_submission', '5', 3, 95)

    def test_clamped_to_900(self, client, app, auth_headers, monkeypatch):
        db = self._wire(app, monkeypatch)
        client.post('/api/dual-translation/5/submit', headers=auth_headers,
                    json={'reproduction': 'x', 'active_ms': 10**10})
        assert db.credits()[0]['p_seconds'] == 900

    def test_cached_path_does_not_credit(self, client, app, auth_headers, monkeypatch):
        db = self._wire(app, monkeypatch, cached=dict(self.CONTRACT))
        r = client.post('/api/dual-translation/5/submit', headers=auth_headers,
                        json={'reproduction': 'x', 'active_ms': 60_000})
        assert r.status_code == 200 and db.credits() == []

    def test_provisional_ungraded_does_not_credit(self, client, app, auth_headers, monkeypatch):
        db = self._wire(app, monkeypatch, contract={'overall_band': None, 'scores': None})
        client.post('/api/dual-translation/5/submit', headers=auth_headers,
                    json={'reproduction': 'x', 'active_ms': 60_000})
        assert db.credits() == []

    @pytest.mark.parametrize('extra', [{}, {'active_ms': None}, {'active_ms': 'abc'}, {'active_ms': -1}])
    def test_absent_or_junk_active_ms_changes_nothing(self, client, app, auth_headers, monkeypatch, extra):
        db = self._wire(app, monkeypatch)
        r = client.post('/api/dual-translation/5/submit', headers=auth_headers,
                        json={'reproduction': 'x', **extra})
        assert r.status_code == 200 and db.credits() == []


# --------------------------------------------------------- DT card review

class TestDtCardReview:
    def _card(self, **kw):
        return {'id': 11, 'user_id': USER, 'profile_entry_id': 4, 'stability': None,
                'difficulty': None, 'due_date': None, 'last_review': None, 'reps': 0,
                'lapses': 0, 'state': 'new', **kw}

    def _wire(self, app, monkeypatch, card=None, profile=None):
        db = LedgerDB({'dt_error_profile_entry': [{'l2_language_id': 3}] if profile is None else profile})
        app.supabase_service = db
        monkeypatch.setattr(dt_routes, '_get_card', lambda d, c: card or self._card())
        return db

    def _post(self, client, auth_headers, **extra):
        return client.post('/api/dual-translation/cards/11/review', headers=auth_headers,
                           json={'rating': 3, **extra})

    def test_credits_card_review(self, client, app, auth_headers, monkeypatch):
        db = self._wire(app, monkeypatch)
        r = self._post(client, auth_headers, active_ms=14_000, client_event_id=EVT)
        assert r.status_code == 200
        (c,) = db.credits()
        assert (c['p_kind'], c['p_source_table'], c['p_source_id'], c['p_language_id'],
                c['p_seconds'], c['p_user_id']) == \
            ('dual_translation', 'dt_card_review', EVT, 3, 14, USER)

    def test_clamped_to_120(self, client, app, auth_headers, monkeypatch):
        db = self._wire(app, monkeypatch)
        self._post(client, auth_headers, active_ms=10**9, client_event_id=EVT)
        assert db.credits()[0]['p_seconds'] == 120

    def test_same_event_id_twice_credits_once(self, client, app, auth_headers, monkeypatch):
        db = self._wire(app, monkeypatch)
        self._post(client, auth_headers, active_ms=9000, client_event_id=EVT)
        self._post(client, auth_headers, active_ms=9000, client_event_id=EVT)
        assert len(db.seen) == 1

    @pytest.mark.parametrize('extra', [
        {}, {'active_ms': 9000}, {'client_event_id': EVT},
        {'active_ms': 9000, 'client_event_id': 'zzz'},
    ])
    def test_missing_or_invalid_fields_no_credit_no_400(self, client, app, auth_headers, monkeypatch, extra):
        db = self._wire(app, monkeypatch)
        assert self._post(client, auth_headers, **extra).status_code == 200
        assert db.credits() == []

    def test_card_without_resolvable_language_no_credit(self, client, app, auth_headers, monkeypatch):
        db = self._wire(app, monkeypatch, card=self._card(profile_entry_id=None))
        assert self._post(client, auth_headers, active_ms=9000, client_event_id=EVT).status_code == 200
        assert db.credits() == []
        db2 = self._wire(app, monkeypatch, profile=[])
        assert self._post(client, auth_headers, active_ms=9000, client_event_id=EVT).status_code == 200
        assert db2.credits() == []
