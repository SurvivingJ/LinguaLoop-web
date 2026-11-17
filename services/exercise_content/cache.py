"""Process-wide caches of the exercise-content read path (ADR-047 §5). Internal.

``store._content_cache()`` builds one ``ByteLRU(EXERCISE_CONTENT_CACHE_MB MiB)``
and ``store._negative_cache()`` one ``NegativeCache(ttl_s=60.0)`` per process,
both keyed by ``store._cache_key(language_id, sense_id, version)``.

* ``ByteLRU`` holds the raw bytes of content files. Files are immutable and
  versioned, so there is no TTL and nothing to invalidate. Bytes, not parsed
  dicts: every reader parses its own copy, so no two callers ever share a
  mutable object (ADR-047 Context finding 3), and bytes are ~4x smaller.
* ``NegativeCache`` remembers that a file was missing so it is not fetched
  again for ``ttl_s`` seconds.

Both are thread-safe (one lock each, never held during I/O).
"""

from __future__ import annotations

import threading
import time
from collections import OrderedDict
from collections.abc import Callable, Hashable

__all__ = ['ByteLRU', 'NegativeCache']


def _check_bytes(data) -> bytes:
    if isinstance(data, bytes):
        return data
    if isinstance(data, (bytearray, memoryview)):
        return bytes(data)
    raise TypeError(f'ByteLRU stores bytes, got {type(data).__name__}')


class ByteLRU:
    """Least-recently-used map ``key -> bytes`` bounded by total size.

    * ``put`` evicts least-recently-used entries until ``bytes <= max_bytes``.
    * An entry larger than ``max_bytes // 4`` is never stored (one oversized
      file must not flush the whole cache); ``put`` returns False for it.
    * ``get`` refreshes recency and counts a hit or a miss.
    """

    def __init__(self, max_bytes: int):
        if isinstance(max_bytes, bool) or not isinstance(max_bytes, int) or max_bytes < 0:
            raise ValueError(f'ByteLRU: max_bytes must be an int >= 0, got {max_bytes!r}')
        self.max_bytes = max_bytes
        self.max_entry_bytes = max_bytes // 4
        self._lock = threading.Lock()
        self._entries: OrderedDict[Hashable, bytes] = OrderedDict()
        self._bytes = 0
        self._hits = 0
        self._misses = 0
        self._evictions = 0

    def get(self, key: Hashable) -> bytes | None:
        with self._lock:
            data = self._entries.get(key)
            if data is None:
                self._misses += 1
                return None
            self._entries.move_to_end(key)
            self._hits += 1
            return data

    def put(self, key: Hashable, data: bytes) -> bool:
        """Store ``data`` under ``key`` (replacing an existing entry); False when it is
        too large to cache."""
        payload = _check_bytes(data)
        size = len(payload)
        with self._lock:
            if self.max_bytes <= 0 or size > self.max_entry_bytes:
                return False
            old = self._entries.pop(key, None)
            if old is not None:
                self._bytes -= len(old)
            self._entries[key] = payload
            self._bytes += size
            while self._bytes > self.max_bytes and self._entries:
                _, evicted = self._entries.popitem(last=False)
                self._bytes -= len(evicted)
                self._evictions += 1
            return True

    def discard(self, key: Hashable) -> bool:
        """Remove ``key`` (e.g. bytes that turned out to be corrupt); True if present."""
        with self._lock:
            old = self._entries.pop(key, None)
            if old is None:
                return False
            self._bytes -= len(old)
            return True

    def clear(self) -> None:
        """Drop every entry and reset the counters."""
        with self._lock:
            self._entries.clear()
            self._bytes = 0
            self._hits = self._misses = self._evictions = 0

    def stats(self) -> dict[str, int]:
        with self._lock:
            return {'hits': self._hits, 'misses': self._misses, 'bytes': self._bytes,
                    'entries': len(self._entries), 'evictions': self._evictions}

    def __contains__(self, key: Hashable) -> bool:     # no recency change, no counters
        with self._lock:
            return key in self._entries

    def __len__(self) -> int:
        with self._lock:
            return len(self._entries)


class NegativeCache:
    """Keys known to be missing, each remembered for ``ttl_s`` seconds.

    ``contains(key)`` is True from ``add(key)`` until ``ttl_s`` has passed on
    ``clock`` (re-adding restarts the period). At most ``max_entries`` keys are
    kept: expired ones are pruned first, then the oldest.
    """

    def __init__(self, ttl_s: float = 60.0, clock: Callable[[], float] = time.monotonic,
                 max_entries: int = 100_000):
        if isinstance(ttl_s, bool) or not isinstance(ttl_s, (int, float)) or ttl_s < 0:
            raise ValueError(f'NegativeCache: ttl_s must be a number >= 0, got {ttl_s!r}')
        if isinstance(max_entries, bool) or not isinstance(max_entries, int) or max_entries < 1:
            raise ValueError(f'NegativeCache: max_entries must be an int >= 1, got {max_entries!r}')
        self.ttl_s = float(ttl_s)
        self.clock = clock
        self.max_entries = max_entries
        self._lock = threading.Lock()
        self._expiry: OrderedDict[Hashable, float] = OrderedDict()

    def add(self, key: Hashable) -> None:
        with self._lock:
            now = self.clock()
            self._expiry.pop(key, None)
            self._expiry[key] = now + self.ttl_s
            if len(self._expiry) > self.max_entries:
                for stale in [k for k, expires in self._expiry.items() if expires <= now]:
                    del self._expiry[stale]
                while len(self._expiry) > self.max_entries:
                    self._expiry.popitem(last=False)

    def contains(self, key: Hashable) -> bool:
        with self._lock:
            expires = self._expiry.get(key)
            if expires is None:
                return False
            if self.clock() >= expires:
                del self._expiry[key]
                return False
            return True

    def discard(self, key: Hashable) -> None:
        with self._lock:
            self._expiry.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._expiry.clear()

    def __len__(self) -> int:
        with self._lock:
            return len(self._expiry)
