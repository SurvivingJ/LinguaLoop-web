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
  the service key. TASK-976 ships the constructor and ``from_config()``
  (which ``store.backend()`` calls; no I/O on construction); TASK-977
  implements the four methods.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol, runtime_checkable

from config import Config
from services.exercise_content import store
from services.exercise_content.store import AlreadyExists, ContentStorageError

__all__ = [
    'AlreadyExists', 'ContentStorageError', 'StoredObject', 'StorageBackend',
    'InMemoryBackend', 'SupabaseStorageBackend',
]

OPS = ('get', 'put', 'delete', 'list')


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


class SupabaseStorageBackend:
    """Supabase Storage REST backend (httpx, service key). Methods: TASK-977.

    Constructing it stores configuration only (no client, no I/O). The service
    key is kept private and never appears in ``repr`` or error text.
    """

    def __init__(self, url: str | None, service_key: str | None,
                 bucket: str = 'exercise-content', *, http_timeout_s: float = 2.0,
                 concurrency: int = 16):
        self.url = url.strip().rstrip('/') if isinstance(url, str) and url.strip() else None
        self.bucket = bucket
        self.http_timeout_s = http_timeout_s
        self.concurrency = concurrency
        self._service_key = service_key

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

    def get(self, path: str) -> bytes | None:
        raise NotImplementedError('TASK-977')

    def put(self, path: str, data: bytes) -> None:
        raise NotImplementedError('TASK-977')

    def delete(self, paths: Sequence[str]) -> None:
        raise NotImplementedError('TASK-977')

    def list(self, prefix: str) -> Iterator[StoredObject]:
        raise NotImplementedError('TASK-977')
