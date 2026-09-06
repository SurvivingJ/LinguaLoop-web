"""Tests for routes/word_list_import.py — Step 7 of
wiki/tasklist/word-list-import.plan.md.

`POST /api/word-list/submit` must return an `upload_batch_id` promptly
without blocking on the (slow, LLM-backed) upload pipeline — proven here by
making the mocked `process_word_list_upload` block on an Event and asserting
the HTTP response comes back before that Event is ever set.

`GET /api/word-list/watchlist` must scope results to the authenticated
user — proven with two different users' rows seeded into a fake table and
asserting only the current user's rows come back.

Auth follows routes/test_intros.py's own convention exactly (`@jwt_required`,
`g.current_user_id`) — a missing/invalid token must behave identically to
that decorator's own behavior (401, `{'error': ...}` shape from
middleware.auth._authenticate), not a custom shape invented here.

`process_word_list_upload`, the db-client factory, and the openai-client
factory are all mocked — no real database, no real LLM calls, no network.
"""

import threading
import time

import pytest
from gotrue.errors import AuthApiError

import routes.word_list_import as wli


# ---------------------------------------------------------------------------
# Minimal fake db client — controls get_language_config_by_code() and the
# `user_word_watchlist` table query surface, matching the fake shapes already
# established in tests/test_word_list_upload_handler.py.
# ---------------------------------------------------------------------------


class _Resp:
    def __init__(self, data):
        self.data = data


class _FakeWatchlistQuery:
    def __init__(self, rows):
        self._rows = rows
        self._filters = []

    def select(self, *_a, **_kw):
        return self

    def eq(self, col, val):
        self._filters.append((col, val))
        return self

    def execute(self):
        matched = [
            r for r in self._rows
            if all(r.get(c) == v for c, v in self._filters)
        ]
        return _Resp(matched)


class _FakeLookupQuery:
    """Minimal fake for the `dim_word_senses`/`dim_vocabulary` reverse-lookup
    queries `_resolve_lemmas()` issues — supports only the `.select().in_()
    .execute()` chain those queries actually use, matching the shape
    established by `_FakeWatchlistQuery` above."""

    def __init__(self, rows):
        self._rows = rows
        self._in_filter = None

    def select(self, *_a, **_kw):
        return self

    def in_(self, col, values):
        self._in_filter = (col, set(values))
        return self

    def execute(self):
        if self._in_filter is None:
            return _Resp(self._rows)
        col, values = self._in_filter
        return _Resp([r for r in self._rows if r.get(col) in values])


class _FakeSupabase:
    def __init__(self, watchlist_rows=None, sense_rows=None, vocab_rows=None):
        self._watchlist_rows = watchlist_rows or []
        self._sense_rows = sense_rows or []
        self._vocab_rows = vocab_rows or []

    def table(self, name):
        if name == 'user_word_watchlist':
            return _FakeWatchlistQuery(self._watchlist_rows)
        if name == 'dim_word_senses':
            return _FakeLookupQuery(self._sense_rows)
        if name == 'dim_vocabulary':
            return _FakeLookupQuery(self._vocab_rows)
        raise AssertionError(f'unexpected table: {name}')


class _LangConfig:
    def __init__(self, id_):
        self.id = id_


class FakeDBClient:
    def __init__(self, configured_languages=('en',), watchlist_rows=None,
                 sense_rows=None, vocab_rows=None):
        self.client = _FakeSupabase(watchlist_rows, sense_rows, vocab_rows)
        self._configured_languages = set(configured_languages)

    def get_language_config_by_code(self, code):
        if code not in self._configured_languages:
            return None
        return _LangConfig(2)


AUTH_HEADERS = {'Authorization': 'Bearer fake-jwt-token-for-testing'}


# ---------------------------------------------------------------------------
# POST /api/word-list/submit
# ---------------------------------------------------------------------------


def test_submit_returns_batch_id_promptly_without_blocking(client, monkeypatch):
    """The HTTP response must come back before the (mocked) slow upload
    pipeline finishes — proves the background-thread dispatch actually
    happens instead of running inline."""
    fake_db = FakeDBClient(configured_languages=('en',))
    monkeypatch.setattr(wli, '_get_db_client', lambda: fake_db)
    monkeypatch.setattr(wli, '_get_openai_client', lambda: None)

    started = threading.Event()
    release = threading.Event()
    calls = []

    def slow_upload(user_id, words, language_code, db_client, openai_client,
                     upload_batch_id=None):
        calls.append((user_id, words, language_code, upload_batch_id))
        started.set()
        release.wait(timeout=5)
        return {'upload_batch_id': upload_batch_id, 'results': []}

    monkeypatch.setattr(wli, 'process_word_list_upload', slow_upload)

    t0 = time.time()
    resp = client.post(
        '/api/word-list/submit',
        json={'words': ['run', 'walk'], 'language': 'en'},
        headers=AUTH_HEADERS,
    )
    elapsed = time.time() - t0

    assert resp.status_code == 202
    body = resp.get_json()
    assert body['status'] == 'success'
    assert 'upload_batch_id' in body and body['upload_batch_id']
    # The response must not have waited for `release` to be set.
    assert elapsed < 2.0, f'submit blocked on the upload pipeline ({elapsed}s)'

    # Now let the background call actually happen and confirm it was
    # dispatched with the batch id already handed back to the client.
    assert started.wait(timeout=5), 'background upload never started'
    release.set()
    time.sleep(0.05)
    assert len(calls) == 1
    assert calls[0][3] == body['upload_batch_id']


def test_submit_rejects_empty_words_list(client, monkeypatch):
    fake_db = FakeDBClient(configured_languages=('en',))
    monkeypatch.setattr(wli, '_get_db_client', lambda: fake_db)

    resp = client.post(
        '/api/word-list/submit',
        json={'words': [], 'language': 'en'},
        headers=AUTH_HEADERS,
    )
    assert resp.status_code == 400
    assert 'error' in resp.get_json()


def test_submit_rejects_missing_words_key(client, monkeypatch):
    fake_db = FakeDBClient(configured_languages=('en',))
    monkeypatch.setattr(wli, '_get_db_client', lambda: fake_db)

    resp = client.post(
        '/api/word-list/submit',
        json={'language': 'en'},
        headers=AUTH_HEADERS,
    )
    assert resp.status_code == 400


def test_submit_rejects_non_string_word_entries(client, monkeypatch):
    fake_db = FakeDBClient(configured_languages=('en',))
    monkeypatch.setattr(wli, '_get_db_client', lambda: fake_db)

    resp = client.post(
        '/api/word-list/submit',
        json={'words': ['run', 123], 'language': 'en'},
        headers=AUTH_HEADERS,
    )
    assert resp.status_code == 400


def test_submit_rejects_oversized_word_list(client, monkeypatch):
    fake_db = FakeDBClient(configured_languages=('en',))
    monkeypatch.setattr(wli, '_get_db_client', lambda: fake_db)

    too_many = [f'word{i}' for i in range(wli.MAX_WORDS_PER_SUBMIT + 1)]
    resp = client.post(
        '/api/word-list/submit',
        json={'words': too_many, 'language': 'en'},
        headers=AUTH_HEADERS,
    )
    assert resp.status_code == 400


def test_submit_rejects_unconfigured_language(client, monkeypatch):
    fake_db = FakeDBClient(configured_languages=('en', 'zh', 'ja'))
    monkeypatch.setattr(wli, '_get_db_client', lambda: fake_db)

    resp = client.post(
        '/api/word-list/submit',
        json={'words': ['run'], 'language': 'zz'},
        headers=AUTH_HEADERS,
    )
    assert resp.status_code == 400
    assert 'zz' in resp.get_json()['error']


def test_submit_rejects_missing_language(client, monkeypatch):
    fake_db = FakeDBClient(configured_languages=('en',))
    monkeypatch.setattr(wli, '_get_db_client', lambda: fake_db)

    resp = client.post(
        '/api/word-list/submit',
        json={'words': ['run']},
        headers=AUTH_HEADERS,
    )
    assert resp.status_code == 400


def test_submit_rejects_missing_auth(client, monkeypatch):
    fake_db = FakeDBClient(configured_languages=('en',))
    monkeypatch.setattr(wli, '_get_db_client', lambda: fake_db)

    resp = client.post(
        '/api/word-list/submit',
        json={'words': ['run'], 'language': 'en'},
    )
    assert resp.status_code == 401
    assert resp.get_json()['error'] == 'Token missing'


def test_submit_rejects_invalid_auth(client, app, monkeypatch):
    """The shared `mock_supabase` fixture accepts any token by default, so
    an invalid-token case must explicitly arrange for auth.get_user() to
    fail the way real Supabase does for a bad JWT."""
    fake_db = FakeDBClient(configured_languages=('en',))
    monkeypatch.setattr(wli, '_get_db_client', lambda: fake_db)
    app.mock_supabase.auth.get_user.side_effect = AuthApiError(
        'invalid jwt', 401, 'bad_jwt',
    )

    resp = client.post(
        '/api/word-list/submit',
        json={'words': ['run'], 'language': 'en'},
        headers={'Authorization': 'Bearer not-a-real-token'},
    )
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET /api/word-list/watchlist
# ---------------------------------------------------------------------------


def test_watchlist_returns_only_current_users_rows(client, monkeypatch):
    rows = [
        {
            'id': 1, 'user_id': 'test-user-id-123', 'sense_id': 10,
            'language_id': 2, 'upload_batch_id': 'batch-a',
            'created_at': '2026-09-01T00:00:00Z',
            'ladder_exercises_generated': True,
            'last_matched_test_id': None, 'last_matched_at': None,
            'active': True,
        },
        {
            'id': 2, 'user_id': 'some-other-user', 'sense_id': 11,
            'language_id': 2, 'upload_batch_id': 'batch-b',
            'created_at': '2026-09-01T00:00:00Z',
            'ladder_exercises_generated': False,
            'last_matched_test_id': None, 'last_matched_at': None,
            'active': True,
        },
    ]
    fake_db = FakeDBClient(watchlist_rows=rows)
    monkeypatch.setattr(wli, '_get_db_client', lambda: fake_db)

    resp = client.get('/api/word-list/watchlist', headers=AUTH_HEADERS)

    assert resp.status_code == 200
    body = resp.get_json()
    assert body['status'] == 'success'
    assert len(body['watchlist']) == 1
    assert body['watchlist'][0]['id'] == 1
    assert body['watchlist'][0]['sense_id'] == 10
    # The other user's row (sense_id=11) must never leak into this response.
    assert all(row['sense_id'] != 11 for row in body['watchlist'])


def test_watchlist_rows_include_resolved_lemma_text(client, monkeypatch):
    """Each row must carry the actual word text (e.g. '拖延'), resolved via
    sense_id -> dim_word_senses.vocab_id -> dim_vocabulary.lemma, batched in
    one query per table rather than per row -- not just a bare sense_id the
    frontend can't render anything meaningful from."""
    rows = [
        {
            'id': 1, 'user_id': 'test-user-id-123', 'sense_id': 10,
            'language_id': 2, 'upload_batch_id': 'batch-a',
            'created_at': '2026-09-01T00:00:00Z',
            'ladder_exercises_generated': True,
            'last_matched_test_id': None, 'last_matched_at': None,
            'active': True,
        },
        {
            'id': 2, 'user_id': 'test-user-id-123', 'sense_id': 20,
            'language_id': 2, 'upload_batch_id': 'batch-a',
            'created_at': '2026-09-01T00:00:00Z',
            'ladder_exercises_generated': False,
            'last_matched_test_id': None, 'last_matched_at': None,
            'active': True,
        },
    ]
    sense_rows = [
        {'id': 10, 'vocab_id': 100},
        {'id': 20, 'vocab_id': 200},
    ]
    vocab_rows = [
        {'id': 100, 'lemma': '拖延'},
        {'id': 200, 'lemma': 'procrastinate'},
    ]
    fake_db = FakeDBClient(
        watchlist_rows=rows, sense_rows=sense_rows, vocab_rows=vocab_rows,
    )
    monkeypatch.setattr(wli, '_get_db_client', lambda: fake_db)

    resp = client.get('/api/word-list/watchlist', headers=AUTH_HEADERS)

    assert resp.status_code == 200
    body = resp.get_json()
    by_sense_id = {row['sense_id']: row for row in body['watchlist']}
    assert by_sense_id[10]['lemma'] == '拖延'
    assert by_sense_id[20]['lemma'] == 'procrastinate'


def test_watchlist_row_lemma_is_none_when_join_unresolvable(client, monkeypatch):
    """A sense_id with no matching dim_word_senses row (deleted sense,
    orphaned watchlist row, etc.) must not error the whole endpoint -- the
    row's `lemma` is simply None so the frontend can fall back to the
    sense-id display."""
    rows = [
        {
            'id': 1, 'user_id': 'test-user-id-123', 'sense_id': 999,
            'language_id': 2, 'upload_batch_id': 'batch-a',
            'created_at': '2026-09-01T00:00:00Z',
            'ladder_exercises_generated': True,
            'last_matched_test_id': None, 'last_matched_at': None,
            'active': True,
        },
    ]
    fake_db = FakeDBClient(watchlist_rows=rows, sense_rows=[], vocab_rows=[])
    monkeypatch.setattr(wli, '_get_db_client', lambda: fake_db)

    resp = client.get('/api/word-list/watchlist', headers=AUTH_HEADERS)

    assert resp.status_code == 200
    body = resp.get_json()
    assert body['watchlist'][0]['lemma'] is None


def test_watchlist_empty_for_user_with_no_rows(client, monkeypatch):
    rows = [
        {
            'id': 2, 'user_id': 'some-other-user', 'sense_id': 11,
            'language_id': 2, 'upload_batch_id': 'batch-b',
            'created_at': '2026-09-01T00:00:00Z',
            'ladder_exercises_generated': False,
            'last_matched_test_id': None, 'last_matched_at': None,
            'active': True,
        },
    ]
    fake_db = FakeDBClient(watchlist_rows=rows)
    monkeypatch.setattr(wli, '_get_db_client', lambda: fake_db)

    resp = client.get('/api/word-list/watchlist', headers=AUTH_HEADERS)

    assert resp.status_code == 200
    assert resp.get_json()['watchlist'] == []


def test_watchlist_rejects_missing_auth(client):
    resp = client.get('/api/word-list/watchlist')
    assert resp.status_code == 401
    assert resp.get_json()['error'] == 'Token missing'


def test_watchlist_rejects_invalid_auth(client, app):
    app.mock_supabase.auth.get_user.side_effect = AuthApiError(
        'invalid jwt', 401, 'bad_jwt',
    )
    resp = client.get(
        '/api/word-list/watchlist',
        headers={'Authorization': 'Bearer not-a-real-token'},
    )
    assert resp.status_code == 401
