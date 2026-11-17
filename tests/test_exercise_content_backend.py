"""TASK-1009 — SupabaseStorageBackend over httpx (ADR-049 §9).

Every request goes to an ``httpx.MockTransport``: no network, no Supabase.
Covers the four protocol methods (URLs, headers, bodies, status mapping,
paging, batching), error text that never carries the service key, the
module-level pooled client and ``from_config``.
"""

from __future__ import annotations

import json
import threading
from datetime import datetime, timezone

import httpx
import pytest

from config import Config
from services.exercise_content import backends, store
from services.exercise_content.backends import (
    StorageBackend, StoredObject, SupabaseStorageBackend,
)
from services.exercise_content.store import AlreadyExists, ContentStorageError

URL = 'https://abc.supabase.co'
KEY = 'service-role-secret-key-123'
BASE = f'{URL}/storage/v1'


@pytest.fixture(autouse=True)
def _fresh_shared_clients(monkeypatch):
    """Each test sees an empty module-level client table and leaves none behind."""
    monkeypatch.setattr(backends, '_clients', {})
    yield
    backends.close_shared_clients()


class Recorder:
    """MockTransport handler: records requests, answers from a queue or a function."""

    def __init__(self, *responses, handler=None):
        self.requests: list[httpx.Request] = []
        self.responses = list(responses)
        self.handler = handler

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if self.handler is not None:
            return self.handler(request)
        if not self.responses:
            raise AssertionError(f'unexpected request {request.method} {request.url}')
        response = self.responses.pop(0)
        if isinstance(response, BaseException):
            raise response
        return response


def _backend(recorder: Recorder, **kwargs) -> SupabaseStorageBackend:
    kwargs.setdefault('transport', httpx.MockTransport(recorder))
    return SupabaseStorageBackend(URL + '/', KEY, 'exercise-content', **kwargs)


def _json(status: int, body) -> httpx.Response:
    return httpx.Response(status, json=body)


def _assert_auth(request: httpx.Request) -> None:
    assert request.headers['authorization'] == f'Bearer {KEY}'
    assert request.headers['apikey'] == KEY


# ---------------------------------------------------------------------------
# construction
# ---------------------------------------------------------------------------

def test_is_a_storage_backend_and_repr_hides_the_key():
    backend = SupabaseStorageBackend(URL, KEY)
    assert isinstance(backend, StorageBackend)
    assert KEY not in repr(backend)
    assert backend.base_url == BASE


def test_from_config_reads_config_and_does_no_io(monkeypatch):
    monkeypatch.setattr(Config, 'SUPABASE_URL', URL + '/')
    monkeypatch.setattr(Config, 'SUPABASE_SERVICE_ROLE_KEY', KEY)
    monkeypatch.setattr(Config, 'EXERCISE_CONTENT_BUCKET', 'other-bucket')
    monkeypatch.setattr(Config, 'EXERCISE_CONTENT_HTTP_TIMEOUT_S', 1.5)
    monkeypatch.setattr(Config, 'EXERCISE_CONTENT_FETCH_CONCURRENCY', 8)

    backend = SupabaseStorageBackend.from_config()

    assert backend.base_url == BASE
    assert backend.bucket == 'other-bucket'
    assert backend.http_timeout_s == 1.5 and backend.concurrency == 8
    assert backends._clients == {}, 'construction must not build a client'
    assert store.backend().base_url == BASE


def test_missing_url_or_key_raises_without_a_request():
    recorder = Recorder()
    for backend in (SupabaseStorageBackend(None, KEY, transport=httpx.MockTransport(recorder)),
                    SupabaseStorageBackend(URL, None, transport=httpx.MockTransport(recorder)),
                    SupabaseStorageBackend(URL, '  ', transport=httpx.MockTransport(recorder))):
        with pytest.raises(ContentStorageError):
            backend.get('zh/1.v0.json')
    assert recorder.requests == []


# ---------------------------------------------------------------------------
# get
# ---------------------------------------------------------------------------

def test_get_returns_the_bytes():
    recorder = Recorder(httpx.Response(200, content=b'{"x":1}'))
    assert _backend(recorder).get('zh/123.v0.json') == b'{"x":1}'

    (request,) = recorder.requests
    assert request.method == 'GET'
    assert str(request.url) == f'{BASE}/object/exercise-content/zh/123.v0.json'
    _assert_auth(request)


@pytest.mark.parametrize('response', [
    httpx.Response(404, json={'statusCode': '404', 'error': 'not_found'}),
    httpx.Response(404),
    httpx.Response(400, json={'statusCode': '404', 'error': 'not_found',
                              'message': 'Object not found'}),
    httpx.Response(400, json={'statusCode': 404, 'error': 'Not Found'}),
    httpx.Response(400, json={'error': 'not_found'}),
])
def test_get_not_found_is_none(response):
    assert _backend(Recorder(response)).get('zh/1.v0.json') is None


@pytest.mark.parametrize('response', [
    httpx.Response(500, text='upstream exploded'),
    httpx.Response(401, json={'statusCode': '401', 'error': 'Unauthorized'}),
    httpx.Response(400, json={'statusCode': '400', 'error': 'InvalidRequest'}),
    httpx.Response(400, text='not json'),
    httpx.Response(403, json={'statusCode': '403', 'error': 'Unauthorized',
                              'message': f'bad key {KEY}'}),
])
def test_get_other_statuses_raise_with_status_but_not_the_key(response):
    with pytest.raises(ContentStorageError) as info:
        _backend(Recorder(response)).get('zh/1.v0.json')
    text = str(info.value)
    assert str(response.status_code) in text
    assert 'zh/1.v0.json' in text
    assert KEY not in text
    assert not isinstance(info.value, AlreadyExists)


@pytest.mark.parametrize('exc', [
    httpx.ReadTimeout('read timed out'),
    httpx.ConnectTimeout('connect timed out'),
    httpx.ConnectError(f'connection refused for {KEY}'),
    httpx.RemoteProtocolError('peer closed'),
])
def test_get_transport_errors_raise_content_storage_error(exc):
    with pytest.raises(ContentStorageError) as info:
        _backend(Recorder(exc)).get('zh/1.v0.json')
    assert KEY not in str(info.value)
    assert info.value.__cause__ is None
    assert info.value.__suppress_context__


def test_get_rejects_bad_paths_without_a_request():
    recorder = Recorder()
    backend = _backend(recorder)
    for bad in ('', '/zh/1.v0.json', None):
        with pytest.raises(ValueError):
            backend.get(bad)
    assert recorder.requests == []


def test_bucket_and_path_are_quoted():
    recorder = Recorder(httpx.Response(200, content=b'x'))
    backend = SupabaseStorageBackend(URL, KEY, 'my bucket',
                                     transport=httpx.MockTransport(recorder))
    backend.get('zh/a b.json')
    assert recorder.requests[0].url.raw_path == b'/storage/v1/object/my%20bucket/zh/a%20b.json'


# ---------------------------------------------------------------------------
# put
# ---------------------------------------------------------------------------

def test_put_posts_bytes_without_upsert():
    recorder = Recorder(_json(200, {'Key': 'exercise-content/zh/5.v3.json'}))
    _backend(recorder).put('zh/5.v3.json', b'{"a":1}')

    (request,) = recorder.requests
    assert request.method == 'POST'
    assert str(request.url) == f'{BASE}/object/exercise-content/zh/5.v3.json'
    _assert_auth(request)
    assert request.headers['x-upsert'] == 'false'
    assert request.headers['content-type'] == 'application/json'
    assert request.headers['cache-control'] == 'max-age=31536000, immutable'
    assert request.content == b'{"a":1}'


def test_put_accepts_bytearray_and_rejects_str():
    recorder = Recorder(_json(200, {}))
    backend = _backend(recorder)
    backend.put('zh/5.v3.json', bytearray(b'x'))
    with pytest.raises(TypeError):
        backend.put('zh/5.v4.json', 'text')
    assert len(recorder.requests) == 1


@pytest.mark.parametrize('response', [
    httpx.Response(409, json={'statusCode': '409', 'error': 'Duplicate'}),
    httpx.Response(409),
    httpx.Response(400, json={'statusCode': '409', 'error': 'Duplicate',
                              'message': 'The resource already exists'}),
    httpx.Response(400, json={'error': 'Duplicate'}),
])
def test_put_existing_object_raises_already_exists(response):
    with pytest.raises(AlreadyExists):
        _backend(Recorder(response)).put('zh/5.v3.json', b'x')


@pytest.mark.parametrize('response', [
    httpx.Response(500, text='boom'),
    httpx.Response(413, json={'statusCode': '413', 'error': 'Payload too large'}),
    httpx.Response(400, json={'statusCode': '400', 'error': 'InvalidKey'}),
])
def test_put_other_failures_raise_content_storage_error(response):
    with pytest.raises(ContentStorageError) as info:
        _backend(Recorder(response)).put('zh/5.v3.json', b'x')
    assert not isinstance(info.value, AlreadyExists)
    assert str(response.status_code) in str(info.value)
    assert KEY not in str(info.value)


def test_put_timeout_raises_content_storage_error():
    with pytest.raises(ContentStorageError):
        _backend(Recorder(httpx.WriteTimeout('slow'))).put('zh/5.v3.json', b'x')


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------

def test_delete_batches_by_100():
    recorder = Recorder(handler=lambda request: _json(200, []))
    paths = [f'zh/{i}.v1.json' for i in range(250)]
    _backend(recorder).delete(paths)

    assert [r.method for r in recorder.requests] == ['DELETE'] * 3
    bodies = [json.loads(r.content) for r in recorder.requests]
    assert [len(b['prefixes']) for b in bodies] == [100, 100, 50]
    assert [p for b in bodies for p in b['prefixes']] == paths
    for request in recorder.requests:
        assert str(request.url) == f'{BASE}/object/exercise-content'
        _assert_auth(request)


def test_delete_of_nothing_makes_no_request():
    recorder = Recorder()
    _backend(recorder).delete([])
    _backend(recorder).delete(())
    assert recorder.requests == []


def test_delete_rejects_a_bare_string():
    with pytest.raises(TypeError):
        _backend(Recorder()).delete('zh/1.v0.json')


def test_delete_failure_raises():
    recorder = Recorder(_json(200, []), httpx.Response(500, text='nope'))
    with pytest.raises(ContentStorageError) as info:
        _backend(recorder).delete([f'zh/{i}.v1.json' for i in range(150)])
    assert '500' in str(info.value)
    assert len(recorder.requests) == 2


# ---------------------------------------------------------------------------
# list
# ---------------------------------------------------------------------------

def _entry(name, size=10, created='2026-11-17T13:37:53.123Z'):
    return {'name': name, 'id': f'id-{name}', 'created_at': created,
            'updated_at': created, 'metadata': {'size': size, 'mimetype': 'application/json'}}


def _folder_entry(name):
    return {'name': name, 'id': None, 'updated_at': None, 'created_at': None,
            'last_accessed_at': None, 'metadata': None}


def test_list_pages_until_a_short_page_and_sorts_by_path():
    first = [_entry(f'{i}.v0.json', size=i) for i in range(1000)]
    second = [_entry('1000.v0.json', size=5), _folder_entry('sub')]
    recorder = Recorder(_json(200, first), _json(200, second))

    objects = list(_backend(recorder).list('zh/'))

    bodies = [json.loads(r.content) for r in recorder.requests]
    assert bodies == [
        {'prefix': 'zh', 'limit': 1000, 'offset': 0,
         'sortBy': {'column': 'name', 'order': 'asc'}},
        {'prefix': 'zh', 'limit': 1000, 'offset': 1000,
         'sortBy': {'column': 'name', 'order': 'asc'}},
    ]
    for request in recorder.requests:
        assert request.method == 'POST'
        assert str(request.url) == f'{BASE}/object/list/exercise-content'
        _assert_auth(request)

    assert len(objects) == 1001
    assert [o.path for o in objects] == sorted(f'zh/{i}.v0.json' for i in range(1001))
    by_path = {o.path: o for o in objects}
    assert by_path['zh/7.v0.json'] == StoredObject(
        path='zh/7.v0.json', size=7,
        created_at=datetime(2026, 11, 17, 13, 37, 53, 123000, tzinfo=timezone.utc))


def test_list_skips_folders_and_handles_root_and_missing_fields():
    page = [_folder_entry('zh'), _folder_entry('_archive'),
            {'name': 'loose.json', 'id': 'x', 'created_at': None, 'metadata': None},
            {'name': 'odd.json', 'id': 'y', 'created_at': 'not a date',
             'metadata': {'size': 'big'}}]
    recorder = Recorder(_json(200, page))
    objects = list(_backend(recorder).list(''))
    assert json.loads(recorder.requests[0].content)['prefix'] == ''
    assert objects == [StoredObject('loose.json', None, None),
                       StoredObject('odd.json', None, None)]


def test_list_prefix_with_and_without_slash_is_the_same_folder():
    recorder = Recorder(handler=lambda request: _json(200, [_entry('1.v0.json')]))
    backend = _backend(recorder)
    assert [o.path for o in backend.list('ja')] == ['ja/1.v0.json']
    assert [o.path for o in backend.list('ja/')] == ['ja/1.v0.json']
    assert [json.loads(r.content)['prefix'] for r in recorder.requests] == ['ja', 'ja']


def test_list_failure_raises_at_call_time():
    recorder = Recorder(httpx.Response(500, text='down'))
    with pytest.raises(ContentStorageError):
        _backend(recorder).list('zh/')
    with pytest.raises(ContentStorageError):
        _backend(Recorder(_json(200, {'not': 'a list'}))).list('zh/')


def test_list_stops_when_a_full_page_adds_nothing_new():
    page = [_entry(f'{i}.v0.json') for i in range(1000)]
    recorder = Recorder(handler=lambda request: _json(200, page))
    assert len(list(_backend(recorder).list('zh'))) == 1000
    assert len(recorder.requests) == 2


@pytest.mark.parametrize('raw, expected', [
    ('2026-11-17T13:37:53Z', datetime(2026, 11, 17, 13, 37, 53, tzinfo=timezone.utc)),
    ('2026-11-17T13:37:53.1+00:00',
     datetime(2026, 11, 17, 13, 37, 53, 100000, tzinfo=timezone.utc)),
    ('2026-11-17T13:37:53.123456789+00:00',
     datetime(2026, 11, 17, 13, 37, 53, 123456, tzinfo=timezone.utc)),
    ('2026-11-17 13:37:53+00', datetime(2026, 11, 17, 13, 37, 53, tzinfo=timezone.utc)),
    ('2026-11-17T13:37:53', datetime(2026, 11, 17, 13, 37, 53, tzinfo=timezone.utc)),
    ('garbage', None), ('', None), (None, None), (17, None),
])
def test_parse_timestamp(raw, expected):
    assert backends._parse_timestamp(raw) == expected


# ---------------------------------------------------------------------------
# the module-level pooled client
# ---------------------------------------------------------------------------

def test_shared_client_is_module_level_lazy_and_shared(monkeypatch):
    built = []
    real_client = httpx.Client

    def recording_client(**kwargs):
        built.append(kwargs)
        return real_client(**kwargs)

    monkeypatch.setattr(backends.httpx, 'Client', recording_client)
    first = SupabaseStorageBackend(URL, KEY, http_timeout_s=2.0, concurrency=16)
    second = SupabaseStorageBackend(URL, KEY, http_timeout_s=2.0, concurrency=16)
    assert built == []

    client = first._client()
    assert second._client() is client
    assert len(built) == 1
    kwargs = built[0]
    assert kwargs['timeout'] == 2.0
    assert kwargs['limits'] == httpx.Limits(max_connections=20, max_keepalive_connections=16)
    assert kwargs.get('transport') is None
    assert 'http2' not in kwargs and 'trust_env' not in kwargs   # httpx defaults: trust_env on
    assert client.trust_env is True
    assert client.timeout == httpx.Timeout(2.0)

    first.close()                                   # shared client survives a backend close
    assert not client.is_closed and second._client() is client


def test_shared_client_is_built_once_under_50_threads(monkeypatch):
    built = []
    real_client = httpx.Client
    gate = threading.Barrier(50)

    def slow_client(**kwargs):
        built.append(kwargs)
        return real_client(**kwargs)

    monkeypatch.setattr(backends.httpx, 'Client', slow_client)
    seen = []

    def worker():
        gate.wait()
        seen.append(backends.shared_client(2.0, 16))

    threads = [threading.Thread(target=worker) for _ in range(50)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert len(built) == 1
    assert len({id(client) for client in seen}) == 1


def test_close_shared_clients_rebuilds_on_next_use():
    client = backends.shared_client(2.0, 16)
    backends.close_shared_clients()
    assert client.is_closed
    fresh = backends.shared_client(2.0, 16)
    assert fresh is not client and not fresh.is_closed


def test_injected_transport_client_closes_with_the_backend():
    recorder = Recorder(handler=lambda request: httpx.Response(200, content=b'x'))
    backend = _backend(recorder)
    backend.get('zh/1.v0.json')
    private = backend._private_client
    assert private is not None and private.timeout == httpx.Timeout(2.0)
    backend.close()
    assert private.is_closed
    assert backend.get('zh/1.v0.json') == b'x'     # a closed private client is rebuilt


def test_concurrent_gets_share_one_client():
    lock = threading.Lock()
    paths = []

    def handler(request):
        with lock:
            paths.append(request.url.path)
        return httpx.Response(200, content=request.url.path.encode())

    backend = _backend(Recorder(handler=handler), concurrency=4)
    results = {}

    def worker(i):
        results[i] = backend.get(f'zh/{i}.v0.json')

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(50)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert len(paths) == 50
    assert all(results[i].endswith(f'zh/{i}.v0.json'.encode()) for i in range(50))


def test_store_uses_the_backend_end_to_end(monkeypatch):
    """put -> get -> list -> delete through store.backend() with a fake bucket."""
    objects: dict[str, bytes] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        prefix = '/storage/v1/object/'
        path = request.url.path[len(prefix):]
        if request.method == 'POST' and path == 'list/exercise-content':
            folder = json.loads(request.content)['prefix']
            names = sorted(p.split('/', 1)[1] for p in objects if p.startswith(folder + '/'))
            return _json(200, [_entry(n, size=len(objects[f'{folder}/{n}'])) for n in names])
        if request.method == 'DELETE':
            for p in json.loads(request.content)['prefixes']:
                objects.pop(p, None)
            return _json(200, [])
        key = path[len('exercise-content/'):]
        if request.method == 'POST':
            if key in objects:
                return _json(400, {'statusCode': '409', 'error': 'Duplicate'})
            objects[key] = request.content
            return _json(200, {'Key': key})
        if key in objects:
            return httpx.Response(200, content=objects[key])
        return _json(400, {'statusCode': '404', 'error': 'not_found'})

    store.set_backend(_backend(Recorder(handler=handler)))
    data = store.encode_sense_file(5, 1, 0, {'a': {'q': 1}})
    store.backend().put(store.content_path(1, 5, 0), data)
    with pytest.raises(AlreadyExists):
        store.backend().put(store.content_path(1, 5, 0), data)
    assert store.decode_sense_file(store.backend().get('zh/5.v0.json'), sense_id=5,
                                   version=0) == {'a': {'q': 1}}
    assert store.backend().get('zh/6.v0.json') is None
    assert [o.path for o in store.backend().list('zh/')] == ['zh/5.v0.json']
    store.backend().delete(['zh/5.v0.json'])
    assert objects == {}
