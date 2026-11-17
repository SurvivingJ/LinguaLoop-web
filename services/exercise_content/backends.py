"""Storage backends for exercise content files (ADR-047 §9). Internal.

Callers use ``store.backend()``; tests install an ``InMemoryBackend`` with
``store.set_backend(...)``.

* ``StorageBackend`` — the protocol every backend implements.
  ``get(path)`` returns the bytes or ``None`` when the object does not exist
  (any other failure raises ``ContentStorageError``); ``put(path, data)`` never
  overwrites (``AlreadyExists``); ``delete(paths)`` ignores missing paths;
  ``list(prefix)`` yields the objects directly inside the folder ``prefix``
  (``'zh/'`` and ``'zh'`` are the same folder; ``''`` is the bucket root),
  sorted by path, not recursing into sub-folders — the Supabase list API
  behaves the same way, so ``_archive/`` is never part of a language listing.
* ``InMemoryBackend`` — dict-backed, thread-safe, records every call; used by
  every package's tests.
* ``SupabaseStorageBackend`` — httpx against ``{SUPABASE_URL}/storage/v1`` with
  the service key (TASK-977). Constructing it does no I/O. Requests go
  through a module-level pooled ``httpx.Client`` (one per (timeout,
  concurrency) setting, in practice one per process), created lazily and
  shared by every instance, so connections stay alive across the fetch pool
  and across backend rebuilds. ``storage3`` is not used (ADR-047 §9 note).
  The service key never appears in ``repr``, log lines or exception text.
"""

from __future__ import annotations

import re
import threading
import time
from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Protocol, runtime_checkable
from urllib.parse import quote

import httpx

from config import Config
from services.exercise_content import store
from services.exercise_content.store import AlreadyExists, ContentStorageError

__all__ = [
    'AlreadyExists', 'ContentStorageError', 'StoredObject', 'StorageBackend',
    'InMemoryBackend', 'SupabaseStorageBackend',
]

OPS = ('get', 'put', 'delete', 'list')

DELETE_BATCH = 100          # paths per DELETE /object/{bucket} request
LIST_PAGE = 1000            # entries per POST /object/list/{bucket} request
IMMUTABLE_CACHE_CONTROL = 'max-age=31536000, immutable'


@dataclass(frozen=True)
class StoredObject:
    path: str                 # full path inside the bucket, e.g. 'zh/123.v0.json'
    size: int | None
    created_at: datetime | None


@runtime_checkable
class StorageBackend(Protocol):
    def get(self, path: str) -> bytes | None: ...         # None = not found; ContentStorageError otherwise
    def put(self, path: str, data: bytes) -> None: ...    # never overwrites: AlreadyExists
    def delete(self, paths: Sequence[str]) -> None: ...
    def list(self, prefix: str) -> Iterator[StoredObject]: ...


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _check_path(path: str) -> str:
    if not isinstance(path, str) or not path or path.startswith('/'):
        raise ValueError(f'storage path must be a non-empty relative str, got {path!r}')
    return path


def _as_bytes(data) -> bytes:
    if isinstance(data, bytes):
        return data
    if isinstance(data, (bytearray, memoryview)):
        return bytes(data)
    raise TypeError(f'storage data must be bytes, got {type(data).__name__}')


def _folder(prefix: str) -> str:
    if not isinstance(prefix, str):
        raise ValueError(f'list prefix must be a str, got {prefix!r}')
    return prefix.strip('/')


def _in_folder(path: str, folder: str) -> bool:
    if not folder:
        return '/' not in path
    head = folder + '/'
    return path.startswith(head) and '/' not in path[len(head):]


class InMemoryBackend:
    """Dict-backed ``StorageBackend`` for tests. Thread-safe.

    Test hooks:
      * ``calls`` — ``[(op, path), ...]`` in call order (``list`` records its
        prefix; ``delete`` records one entry per path); ``call_threads`` holds
        the calling thread's name for each entry; ``delete_batches`` holds the
        tuple of paths of each ``delete`` call.
      * ``fail_next(op, exc)`` — the next ``op`` call (after being recorded and
        after its latency) raises ``exc``; queued per op, used once each.
      * ``latency_s`` — seconds every call sleeps (outside the lock, so
        concurrent calls overlap); a mapping ``{op: seconds}`` sets it per op.
      * ``seed(path, data, created_at=None)`` — store an object without
        recording a call (overwrites); ``set_created_at(path, dt)``;
        ``exists``, ``paths``, ``objects``, ``calls_for(op)``, ``clear_calls``.
      * ``clock`` — returns ``created_at`` for ``put`` (default: now, UTC).
    """

    def __init__(self, *, latency_s: float | Mapping[str, float] = 0.0,
                 clock: Callable[[], datetime] | None = None):
        self._lock = threading.RLock()
        self._objects: dict[str, tuple[bytes, datetime | None]] = {}
        self._failures: dict[str, list[BaseException]] = {}
        self.calls: list[tuple[str, str]] = []
        self.call_threads: list[str] = []
        self.delete_batches: list[tuple[str, ...]] = []
        self.latency_s = latency_s
        self.clock = clock or _utcnow

    # -- test helpers -------------------------------------------------------

    def fail_next(self, op: str, exc: BaseException) -> None:
        if op not in OPS:
            raise ValueError(f'fail_next: op must be one of {OPS}, got {op!r}')
        with self._lock:
            self._failures.setdefault(op, []).append(exc)

    def seed(self, path: str, data: bytes, *, created_at: datetime | None = None) -> None:
        path = _check_path(path)
        payload = _as_bytes(data)
        with self._lock:
            self._objects[path] = (payload, created_at if created_at is not None else self.clock())

    def set_created_at(self, path: str, created_at: datetime | None) -> None:
        with self._lock:
            if path not in self._objects:
                raise KeyError(path)
            self._objects[path] = (self._objects[path][0], created_at)

    def exists(self, path: str) -> bool:
        with self._lock:
            return path in self._objects

    def paths(self) -> list[str]:
        with self._lock:
            return sorted(self._objects)

    def objects(self) -> dict[str, bytes]:
        with self._lock:
            return {path: entry[0] for path, entry in sorted(self._objects.items())}

    def calls_for(self, op: str) -> list[str]:
        with self._lock:
            return [path for call_op, path in self.calls if call_op == op]

    def clear_calls(self) -> None:
        with self._lock:
            self.calls.clear()
            self.call_threads.clear()
            self.delete_batches.clear()

    # -- protocol -----------------------------------------------------------

    def _latency(self, op: str) -> float:
        latency = self.latency_s
        if isinstance(latency, Mapping):
            latency = latency.get(op, 0.0)
        return float(latency or 0.0)

    def _enter(self, op: str, paths: Sequence[str]) -> None:
        thread_name = threading.current_thread().name
        with self._lock:
            for path in paths:
                self.calls.append((op, path))
                self.call_threads.append(thread_name)
        delay = self._latency(op)
        if delay > 0:
            time.sleep(delay)
        with self._lock:
            pending = self._failures.get(op)
            exc = pending.pop(0) if pending else None
        if exc is not None:
            raise exc

    def get(self, path: str) -> bytes | None:
        path = _check_path(path)
        self._enter('get', (path,))
        with self._lock:
            entry = self._objects.get(path)
        return None if entry is None else entry[0]

    def put(self, path: str, data: bytes) -> None:
        path = _check_path(path)
        payload = _as_bytes(data)
        self._enter('put', (path,))
        with self._lock:
            if path in self._objects:
                raise AlreadyExists(f'{path} already exists')
            self._objects[path] = (payload, self.clock())

    def delete(self, paths: Sequence[str]) -> None:
        if isinstance(paths, str):
            raise TypeError('delete takes a sequence of paths, not a str')
        batch = tuple(_check_path(path) for path in paths)
        if not batch:
            return
        with self._lock:
            self.delete_batches.append(batch)
        self._enter('delete', batch)
        with self._lock:
            for path in batch:
                self._objects.pop(path, None)

    def list(self, prefix: str) -> Iterator[StoredObject]:
        folder = _folder(prefix)
        self._enter('list', (prefix,))
        with self._lock:
            snapshot = sorted((path, entry) for path, entry in self._objects.items()
                              if _in_folder(path, folder))
        return iter([StoredObject(path=path, size=len(entry[0]), created_at=entry[1])
                     for path, entry in snapshot])


# ---------------------------------------------------------------------------
# Supabase Storage over httpx (TASK-977)
# ---------------------------------------------------------------------------

_clients_lock = threading.Lock()
_clients: dict[tuple[float, int], httpx.Client] = {}


def _new_client(timeout_s: float, concurrency: int,
                transport: httpx.BaseTransport | None = None) -> httpx.Client:
    """A pooled client: ``max_connections = concurrency + 4``, ``concurrency`` kept alive.

    ``trust_env`` stays on (proxy and CA bundle from the environment); no HTTP/2
    (there is no ``h2`` dependency). Constructing a client does no I/O.
    """
    return httpx.Client(
        timeout=timeout_s,
        limits=httpx.Limits(max_connections=concurrency + 4,
                            max_keepalive_connections=concurrency),
        transport=transport,
    )


def shared_client(timeout_s: float, concurrency: int) -> httpx.Client:
    """The module-level client for these settings, created on first use (thread-safe).

    Every ``SupabaseStorageBackend`` without an injected transport uses it, so a
    rebuilt backend keeps the warm connections. ``httpx.Client`` is thread-safe.
    In production there is one setting, hence one client per process.
    """
    key = (float(timeout_s), int(concurrency))
    client = _clients.get(key)
    if client is not None and not client.is_closed:
        return client
    with _clients_lock:
        client = _clients.get(key)
        if client is None or client.is_closed:
            client = _new_client(*key)
            _clients[key] = client
        return client


def close_shared_clients() -> None:
    """Close the module-level clients (process shutdown, tests); the next request
    builds a fresh one."""
    with _clients_lock:
        clients = list(_clients.values())
        _clients.clear()
    for client in clients:
        try:
            client.close()
        except Exception:  # pragma: no cover - closing is best effort
            pass


def _json_or_none(response: httpx.Response) -> Any:
    try:
        return response.json()
    except ValueError:          # JSONDecodeError and UnicodeDecodeError are ValueErrors
        return None


def _body_field(body: Any, name: str) -> str:
    if isinstance(body, dict) and body.get(name) is not None:
        return str(body[name]).strip()
    return ''


def _token(text: str) -> str:
    return text.strip().lower().replace(' ', '_')


def _is_not_found(response: httpx.Response) -> bool:
    """404, or the 400 Supabase Storage sends for a missing object
    (``{"statusCode": "404", "error": "not_found", ...}``)."""
    if response.status_code == 404:
        return True
    if response.status_code != 400:
        return False
    body = _json_or_none(response)
    return (_body_field(body, 'statusCode') == '404'
            or _token(_body_field(body, 'error')) == 'not_found')


def _is_duplicate(response: httpx.Response) -> bool:
    """409, or the 400 Supabase Storage sends for an existing object without upsert
    (``{"statusCode": "409", "error": "Duplicate", ...}``)."""
    if response.status_code == 409:
        return True
    if response.status_code != 400:
        return False
    body = _json_or_none(response)
    return (_body_field(body, 'statusCode') == '409'
            or _token(_body_field(body, 'error')) == 'duplicate')


_FRACTION = re.compile(r'\.(\d+)')
_SHORT_OFFSET = re.compile(r'([+-]\d{2})$')


def _parse_timestamp(value: Any) -> datetime | None:
    """ISO-8601 from the list API (``2026-11-17T13:37:53.123Z``) as an aware datetime
    (UTC when no offset is given); None when absent or unparseable."""
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str) and value.strip():
        text = value.strip()
        if text[-1:] in ('Z', 'z'):
            text = text[:-1] + '+00:00'
        # Older Pythons accept only 3 or 6 fractional digits and only +HH:MM offsets.
        text = _FRACTION.sub(lambda m: '.' + (m.group(1) + '000000')[:6], text, count=1)
        if text[10:11] in ('T', 't', ' '):
            text = text[:10] + 'T' + _SHORT_OFFSET.sub(r'\1:00', text[11:])
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError:
            return None
    else:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


class SupabaseStorageBackend:
    """Supabase Storage REST backend (httpx, service key; ADR-047 §9, TASK-977).

    * ``get``    ``GET  /object/{bucket}/{path}`` -> bytes; None when not found.
    * ``put``    ``POST /object/{bucket}/{path}`` with ``x-upsert: false``; ``AlreadyExists``.
    * ``delete`` ``DELETE /object/{bucket}`` ``{"prefixes": [...]}``, 100 paths per request.
    * ``list``   ``POST /object/list/{bucket}`` paged by 1,000, folders skipped, sorted by path.

    Constructing it stores configuration only (no client, no I/O). Requests use
    the module-level ``shared_client(http_timeout_s, concurrency)``; a test may
    pass ``transport=httpx.MockTransport(...)``, which gives the instance its own
    client with the same timeout and limits (``close()`` closes that one only).
    Every failure other than "not found" / "already exists" raises
    ``ContentStorageError`` naming the operation, the path and the HTTP status.
    The service key is kept private and never appears in ``repr`` or error text.
    """

    def __init__(self, url: str | None, service_key: str | None,
                 bucket: str = 'exercise-content', *, http_timeout_s: float = 2.0,
                 concurrency: int = 16, transport: httpx.BaseTransport | None = None):
        self.url = url.strip().rstrip('/') if isinstance(url, str) and url.strip() else None
        self.bucket = bucket
        self.http_timeout_s = http_timeout_s
        self.concurrency = concurrency
        self._service_key = service_key.strip() if isinstance(service_key, str) else service_key
        self._transport = transport
        self._private_client: httpx.Client | None = None
        self._client_lock = threading.Lock()

    @classmethod
    def from_config(cls) -> 'SupabaseStorageBackend':
        """Build from ``Config`` at call time (what ``store.backend()`` uses)."""
        return cls(
            getattr(Config, 'SUPABASE_URL', None),
            getattr(Config, 'SUPABASE_SERVICE_ROLE_KEY', None),
            store._setting_str('EXERCISE_CONTENT_BUCKET', 'exercise-content'),
            http_timeout_s=store._setting_float('EXERCISE_CONTENT_HTTP_TIMEOUT_S', 2.0,
                                                low=0.0, low_inclusive=False),
            concurrency=store._setting_int('EXERCISE_CONTENT_FETCH_CONCURRENCY', 16, minimum=1),
        )

    @property
    def base_url(self) -> str | None:
        """``{SUPABASE_URL}/storage/v1``, or None without a URL."""
        return f'{self.url}/storage/v1' if self.url else None

    def __repr__(self) -> str:
        return f'SupabaseStorageBackend(url={self.url!r}, bucket={self.bucket!r})'

    # -- plumbing -----------------------------------------------------------

    def _client(self) -> httpx.Client:
        if self._transport is None:
            return shared_client(self.http_timeout_s, self.concurrency)
        with self._client_lock:
            if self._private_client is None or self._private_client.is_closed:
                self._private_client = _new_client(self.http_timeout_s, self.concurrency,
                                                   self._transport)
            return self._private_client

    def close(self) -> None:
        """Close the instance's own client (injected transport). The module-level
        shared client stays open for the next backend (see ``close_shared_clients``)."""
        with self._client_lock:
            client, self._private_client = self._private_client, None
        if client is not None:
            client.close()

    def _scrub(self, text: str) -> str:
        key = self._service_key
        if isinstance(key, str) and key:
            text = text.replace(key, '***')
        return text

    def _headers(self, extra: Mapping[str, str] | None = None) -> dict[str, str]:
        if not self.url:
            raise ContentStorageError('exercise content storage: SUPABASE_URL is not configured')
        if not self._service_key:
            raise ContentStorageError(
                'exercise content storage: SUPABASE_SERVICE_ROLE_KEY is not configured')
        headers = {'Authorization': f'Bearer {self._service_key}', 'apikey': self._service_key}
        if extra:
            headers.update(extra)
        return headers

    def _bucket_url(self, *parts: str) -> str:
        return '/'.join((self.base_url or '', 'object', *parts, quote(self.bucket, safe='')))

    def _object_url(self, path: str) -> str:
        return f'{self._bucket_url()}/{quote(path, safe="/")}'

    def _request(self, op: str, target: str, method: str, url: str, *,
                 headers: Mapping[str, str] | None = None, **kwargs: Any) -> httpx.Response:
        request_headers = self._headers(headers)
        try:
            return self._client().request(method, url, headers=request_headers, **kwargs)
        except httpx.TimeoutException as exc:
            raise ContentStorageError(
                f'exercise content storage {op} {target!r} timed out after '
                f'{self.http_timeout_s}s ({type(exc).__name__})') from None
        except (httpx.HTTPError, httpx.InvalidURL) as exc:
            raise ContentStorageError(
                f'exercise content storage {op} {target!r} failed: {type(exc).__name__}: '
                f'{self._scrub(str(exc))[:300]}') from None

    def _failure(self, op: str, target: str, response: httpx.Response) -> ContentStorageError:
        body = _json_or_none(response)
        if isinstance(body, dict):
            detail = ' '.join(f'{name}={body[name]}' for name in ('statusCode', 'error', 'message')
                              if body.get(name) is not None)
        else:
            detail = response.text
        detail = self._scrub(' '.join(detail.split()))[:300]
        suffix = f' ({detail})' if detail else ''
        return ContentStorageError(
            f'exercise content storage {op} {target!r} failed: HTTP {response.status_code}{suffix}')

    # -- protocol -----------------------------------------------------------

    def get(self, path: str) -> bytes | None:
        path = _check_path(path)
        response = self._request('get', path, 'GET', self._object_url(path))
        if response.status_code == 200:
            return response.content
        if _is_not_found(response):
            return None
        raise self._failure('get', path, response)

    def put(self, path: str, data: bytes) -> None:
        path = _check_path(path)
        payload = _as_bytes(data)
        response = self._request(
            'put', path, 'POST', self._object_url(path), content=payload,
            headers={'x-upsert': 'false', 'content-type': 'application/json',
                     'cache-control': IMMUTABLE_CACHE_CONTROL})
        if 200 <= response.status_code < 300:
            return
        if _is_duplicate(response):
            raise AlreadyExists(f'{path} already exists')
        raise self._failure('put', path, response)

    def delete(self, paths: Sequence[str]) -> None:
        if isinstance(paths, str):
            raise TypeError('delete takes a sequence of paths, not a str')
        batch = [_check_path(path) for path in paths]
        for start in range(0, len(batch), DELETE_BATCH):
            chunk = batch[start:start + DELETE_BATCH]
            target = chunk[0] if len(chunk) == 1 else f'{chunk[0]} (+{len(chunk) - 1} more)'
            response = self._request('delete', target, 'DELETE', self._bucket_url(),
                                     json={'prefixes': chunk})
            if not 200 <= response.status_code < 300:
                raise self._failure('delete', target, response)

    def list(self, prefix: str) -> Iterator[StoredObject]:
        """Every object directly inside the folder ``prefix``, sorted by path.

        All pages are read before this returns (Storage's name order follows the
        database collation, so the result is sorted here), and a failure raises
        here: a caller never iterates a partial listing.
        """
        folder = _folder(prefix)
        target = folder + '/'
        found: dict[str, StoredObject] = {}
        offset = 0
        while True:
            response = self._request(
                'list', target, 'POST', self._bucket_url('list'),
                json={'prefix': folder, 'limit': LIST_PAGE, 'offset': offset,
                      'sortBy': {'column': 'name', 'order': 'asc'}})
            if response.status_code != 200:
                raise self._failure('list', target, response)
            page = _json_or_none(response)
            if not isinstance(page, list):
                raise ContentStorageError(
                    f'exercise content storage list {target!r} did not return a JSON array')
            before = len(found)
            for entry in page:
                if not isinstance(entry, dict) or entry.get('id') is None:
                    continue                                    # a folder entry
                name = entry.get('name')
                if not isinstance(name, str) or not name:
                    continue
                path = f'{folder}/{name}' if folder else name
                metadata = entry.get('metadata')
                size = metadata.get('size') if isinstance(metadata, dict) else None
                found[path] = StoredObject(
                    path=path, size=size if store._is_int(size) else None,
                    created_at=_parse_timestamp(entry.get('created_at')))
            if len(page) < LIST_PAGE or len(found) == before:
                break
            offset += len(page)
        return iter(sorted(found.values(), key=lambda obj: obj.path))
