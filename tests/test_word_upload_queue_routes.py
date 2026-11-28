"""routes/word_list_import.py in queue mode (the default, ADR-069):
POST /api/word-list/submit stores the words in word_upload_queue and calls no
LLM; GET /api/word-list/watchlist also returns the learner's open queue rows.
The inline path is covered by tests/test_word_list_import_routes.py."""

import pytest

import routes.word_list_import as wli
from services.word_list_import import batch_limits
from tests._word_queue_fakes import FakeDB
from tests.test_word_list_import_routes import AUTH_HEADERS

USER = 'test-user-id-123'   # what the auth fixture puts in g.current_user_id


class _Lang:
    id = 3


class _Client:
    def __init__(self, db, languages=('ja',)):
        self.client = db
        self._languages = languages

    def get_language_config_by_code(self, code):
        return _Lang() if code in self._languages else None


class _Pool:
    def __init__(self):
        self.jobs = []

    def submit(self, job):
        self.jobs.append(job)
        return True


@pytest.fixture(autouse=True)
def _queue_mode(monkeypatch):
    from config import Config
    monkeypatch.setattr(Config, 'WORD_LIST_INLINE_GENERATION', False)
    monkeypatch.setattr(wli, '_limiter', batch_limits.BatchLimiter())
    pool = _Pool()
    monkeypatch.setattr(wli, '_pool', pool)
    monkeypatch.setattr(wli, 'process_word_list_upload',
                        lambda *a, **k: pytest.fail('inline pipeline ran in queue mode'))
    return pool


@pytest.fixture
def db(monkeypatch):
    fake = FakeDB(users=[{'id': USER, 'native_language_id': 2}])
    monkeypatch.setattr(wli, '_get_db_client', lambda: _Client(fake))
    return fake


def _submit(client, words, language='ja'):
    return client.post('/api/word-list/submit', json={'words': words, 'language': language},
                       headers=AUTH_HEADERS)


def test_submit_queues_the_words_and_answers_202(client, db, _queue_mode):
    resp = _submit(client, ['食べた', '走る', '走る'])
    assert resp.status_code == 202
    body = resp.get_json()
    assert body['mode'] == 'queue' and body['queued'] == 2 and body['already_queued'] == 0
    rows = db.tables['word_upload_queue']
    assert [r['raw_word'] for r in rows] == ['食べた', '走る']
    assert {r['upload_batch_id'] for r in rows} == {body['upload_batch_id']}
    assert all(r['user_id'] == USER and r['language_id'] == 3 and r['gloss_language_id'] == 2
               for r in rows)
    # one lookup-only advance job for the batch
    assert len(_queue_mode.jobs) == 1


def test_background_job_advances_only_this_batch(client, db, _queue_mode, monkeypatch):
    calls = []
    monkeypatch.setattr(wli.upload_queue, 'advance',
                        lambda d, **kw: calls.append(kw) or {})
    body = _submit(client, ['走る']).get_json()
    _queue_mode.jobs[0]()
    assert calls[0]['upload_batch_id'] == body['upload_batch_id']
    assert calls[0].get('create_vocab', False) is False


def test_resubmitting_queued_words_reports_them(client, db, _queue_mode):
    _submit(client, ['走る'])
    body = _submit(client, ['走る']).get_json()
    assert body['queued'] == 0 and body['already_queued'] == 1
    assert len(_queue_mode.jobs) == 1          # nothing new to advance


def test_daily_cap_counts_queued_batches_from_the_table(client, db, monkeypatch):
    monkeypatch.setattr(wli, '_limiter', batch_limits.BatchLimiter(max_per_day=2))
    for n in range(2):
        db.tables.setdefault('word_upload_queue', []).append({
            'id': n, 'user_id': USER, 'upload_batch_id': f'old-{n}', 'language_id': 3,
            'raw_word': f'w{n}', 'status': 'pending',
            'requested_at': '2999-01-01T00:00:00+00:00'})
    resp = _submit(client, ['走る'])
    assert resp.status_code == 429


def test_a_second_batch_is_not_blocked_by_the_first(client, db):
    assert _submit(client, ['走る']).status_code == 202
    assert _submit(client, ['食べる']).status_code == 202


def test_queue_table_unavailable_answers_503_and_refunds(client, db):
    db.fail_tables.add('word_upload_queue')
    resp = _submit(client, ['走る'])
    assert resp.status_code == 503
    assert resp.get_json()['error_code'] == 'WORD_QUEUE_UNAVAILABLE'
    assert wli._limiter.reserve(USER) is None   # slot refunded, not held


def test_invalid_words_are_rejected_before_anything_is_queued(client, db):
    assert _submit(client, ['hello'], 'ja').status_code == 400
    assert not db.tables.get('word_upload_queue')


def test_watchlist_includes_open_queue_rows(client, db):
    _submit(client, ['走る', '食べた'])
    db.tables['word_upload_queue'][1]['status'] = 'done'
    db.tables['user_word_watchlist'] = []
    body = client.get('/api/word-list/watchlist', headers=AUTH_HEADERS).get_json()
    assert body['watchlist'] == []
    assert [r['raw_word'] for r in body['queue']] == ['走る']


def test_watchlist_survives_a_missing_queue_table(client, db):
    db.tables['user_word_watchlist'] = []
    db.fail_tables.add('word_upload_queue')
    resp = client.get('/api/word-list/watchlist', headers=AUTH_HEADERS)
    assert resp.status_code == 200 and resp.get_json()['queue'] == []
