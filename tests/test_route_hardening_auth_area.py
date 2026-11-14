"""Corpus URL fetch restrictions, word-quiz attempt ownership, and removal of
the retired vocab-dojo and model-arena routes."""

import importlib
import socket
from types import SimpleNamespace
from unittest.mock import MagicMock

import httpx
import pytest

from services.corpus import ingestion
from services.corpus.ingestion import CorpusIngestionService, UnsafeURLError


def _resolver(mapping):
    def getaddrinfo(host, port, *args, **kwargs):
        if host not in mapping:
            raise socket.gaierror('unknown host')
        return [(socket.AF_INET6 if ':' in ip else socket.AF_INET,
                 socket.SOCK_STREAM, 6, '', (ip, port)) for ip in mapping[host]]
    return getaddrinfo


HOSTS = {
    'public.example': ['93.184.216.34'],
    'other.example': ['8.8.8.8'],
    'loopback.example': ['127.0.0.1'],
    'private.example': ['10.1.2.3'],
    'linklocal.example': ['169.254.169.254'],
    'mixed.example': ['93.184.216.34', '192.168.1.10'],
    'v6loop.example': ['::1'],
    'v6mapped.example': ['::ffff:10.0.0.1'],
    'cgnat.example': ['100.64.0.1'],
    '127.0.0.1': ['127.0.0.1'],
    '169.254.169.254': ['169.254.169.254'],
}


@pytest.fixture
def dns(monkeypatch):
    monkeypatch.setattr(ingestion.socket, 'getaddrinfo', _resolver(HOSTS))


@pytest.mark.parametrize('url', [
    'http://public.example/page',
    'ftp://public.example/page',
    'file:///etc/passwd',
    'https://loopback.example/',
    'https://private.example/',
    'https://linklocal.example/latest/meta-data/',
    'https://mixed.example/',
    'https://v6loop.example/',
    'https://v6mapped.example/',
    'https://cgnat.example/',
    'https://127.0.0.1/',
    'https://169.254.169.254/',
    'https://unresolvable.example/',
    'https://user:pw@public.example/',
    'https://public.example:8443/',
    'https://public.example:notaport/',
    'https:///nohost',
    '',
])
def test_unsafe_urls_are_refused(dns, url):
    with pytest.raises(UnsafeURLError):
        ingestion._assert_public_https_url(url)


def test_public_https_url_is_allowed(dns):
    ingestion._assert_public_https_url('https://public.example/article?id=1')
    ingestion._assert_public_https_url('https://public.example:443/article')


def _fake_get(responses, seen):
    def get(url, **kwargs):
        seen.append((url, kwargs))
        status, headers = responses[url]
        return httpx.Response(status, headers=headers, text='<html><body>hi</body></html>',
                              request=httpx.Request('GET', url))
    return get


def test_fetch_never_lets_httpx_follow_redirects_itself(dns, monkeypatch):
    seen = []
    monkeypatch.setattr(ingestion.httpx, 'get', _fake_get(
        {'https://public.example/a': (200, {})}, seen))

    response = CorpusIngestionService(db=MagicMock())._fetch_public_url('https://public.example/a')

    assert response.status_code == 200
    assert seen[0][1]['follow_redirects'] is False


def test_redirect_to_a_public_host_is_followed_after_validation(dns, monkeypatch):
    seen = []
    monkeypatch.setattr(ingestion.httpx, 'get', _fake_get({
        'https://public.example/a': (302, {'location': 'https://other.example/b'}),
        'https://other.example/b': (301, {'location': '/c'}),
        'https://other.example/c': (200, {}),
    }, seen))

    CorpusIngestionService(db=MagicMock())._fetch_public_url('https://public.example/a')

    assert [u for u, _ in seen] == [
        'https://public.example/a', 'https://other.example/b', 'https://other.example/c']


@pytest.mark.parametrize('location', [
    'https://private.example/admin',
    'http://public.example/plain',
    'https://169.254.169.254/latest/meta-data/',
    '//loopback.example/x',
])
def test_redirect_to_an_unsafe_target_is_refused_before_fetching_it(dns, monkeypatch, location):
    seen = []
    monkeypatch.setattr(ingestion.httpx, 'get', _fake_get({
        'https://public.example/a': (302, {'location': location}),
    }, seen))

    with pytest.raises(UnsafeURLError):
        CorpusIngestionService(db=MagicMock())._fetch_public_url('https://public.example/a')

    assert [u for u, _ in seen] == ['https://public.example/a']


def test_redirect_loops_are_bounded(dns, monkeypatch):
    seen = []
    monkeypatch.setattr(ingestion.httpx, 'get', _fake_get({
        'https://public.example/a': (302, {'location': 'https://public.example/a'}),
    }, seen))

    with pytest.raises(UnsafeURLError):
        CorpusIngestionService(db=MagicMock())._fetch_public_url('https://public.example/a')

    assert len(seen) == CorpusIngestionService.MAX_REDIRECTS + 1


def test_ingest_route_reports_unsafe_urls_and_hides_internal_errors(client, auth_headers, monkeypatch):
    import routes.corpus as corpus_routes
    monkeypatch.setattr('middleware.auth._user_has_tier', lambda *_a: True)

    service = MagicMock()
    monkeypatch.setattr(corpus_routes, 'CorpusIngestionService', lambda db: service)
    body = {'source_type': 'url', 'language_id': 2, 'url': 'http://x'}

    service.ingest_url.side_effect = UnsafeURLError('Only https URLs can be ingested')
    resp = client.post('/api/corpus/ingest', json=body, headers=auth_headers)
    assert resp.status_code == 400
    assert resp.get_json()['error'] == 'Only https URLs can be ingested'

    service.ingest_url.side_effect = RuntimeError('password=hunter2 at db.internal')
    resp = client.post('/api/corpus/ingest', json=body, headers=auth_headers)
    assert resp.status_code == 502
    assert 'hunter2' not in resp.get_data(as_text=True)


# -- word quiz ----------------------------------------------------------------

QUIZ_RESULT = {'sense_id': 1, 'selected_answer': 'a', 'correct_answer': 'a', 'is_correct': True}
ATTEMPT_ID = '0b9e6c6e-3f3a-4f0e-9a51-0d7f5c1f2a11'


@pytest.fixture
def knowledge(monkeypatch):
    svc = MagicMock()
    svc.record_word_quiz_results.return_value = []
    monkeypatch.setattr(
        'services.vocabulary.knowledge_service.VocabularyKnowledgeService', lambda: svc)
    return svc


def _attempt_lookup(app, rows):
    query = MagicMock()
    for name in ('select', 'eq', 'limit'):
        getattr(query, name).return_value = query
    query.execute.return_value = SimpleNamespace(data=rows)
    app.mock_supabase.table.return_value = query
    return query


def _post_quiz(client, auth_headers, **extra):
    return client.post('/api/vocabulary/word-quiz', headers=auth_headers,
                       json={'language_id': 1, 'results': [QUIZ_RESULT], **extra})


def test_word_quiz_rejects_an_attempt_the_caller_does_not_own(client, app, auth_headers, knowledge):
    query = _attempt_lookup(app, [])

    resp = _post_quiz(client, auth_headers, attempt_id=ATTEMPT_ID)

    assert resp.status_code == 404
    knowledge.record_word_quiz_results.assert_not_called()
    app.mock_supabase.table.assert_called_with('test_attempts')
    filters = [c.args for c in query.eq.call_args_list]
    assert ('id', ATTEMPT_ID) in filters
    assert ('user_id', 'test-user-id-123') in filters


def test_word_quiz_accepts_the_callers_own_attempt(client, app, auth_headers, knowledge):
    _attempt_lookup(app, [{'id': ATTEMPT_ID}])

    resp = _post_quiz(client, auth_headers, attempt_id=ATTEMPT_ID)

    assert resp.status_code == 200
    assert knowledge.record_word_quiz_results.call_args.kwargs['attempt_id'] == ATTEMPT_ID


def test_word_quiz_rejects_a_malformed_attempt_id(client, app, auth_headers, knowledge):
    resp = _post_quiz(client, auth_headers, attempt_id='not-a-uuid')
    assert resp.status_code == 400
    knowledge.record_word_quiz_results.assert_not_called()


def test_word_quiz_without_an_attempt_skips_the_lookup(client, app, auth_headers, knowledge):
    app.mock_supabase.table.reset_mock()
    resp = _post_quiz(client, auth_headers)
    assert resp.status_code == 200
    app.mock_supabase.table.assert_not_called()
    assert knowledge.record_word_quiz_results.call_args.kwargs['attempt_id'] is None


# -- removed surfaces ---------------------------------------------------------

@pytest.mark.parametrize('method,path', [
    ('get', '/api/vocab-dojo/session?language_id=1'),
    ('post', '/api/vocab-dojo/attempt'),
    ('get', '/api/vocab-dojo/word/1/exercises?language_id=1'),
])
def test_retired_vocab_dojo_routes_are_gone(client, auth_headers, method, path):
    resp = getattr(client, method)(path, headers=auth_headers)
    assert resp.status_code in (404, 405)


def test_vocab_dojo_no_longer_exposes_generation_assets():
    source = open(importlib.import_module('routes.vocab_dojo').__file__).read()
    assert 'word_assets' not in source and 'model_used' not in source
    assert 'enqueue' not in source


@pytest.mark.parametrize('module', ['routes.model_arena', 'middleware.local_only'])
def test_unregistered_local_tooling_modules_are_removed(module):
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module(module)
