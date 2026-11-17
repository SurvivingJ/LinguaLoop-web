"""TASK-977 — the read path's byte LRU and negative cache (ADR-047 §5)."""

from __future__ import annotations

import random
import threading

import pytest

from config import Config
from services.exercise_content import cache, store
from services.exercise_content.cache import ByteLRU, NegativeCache


class FakeClock:
    def __init__(self, now: float = 1000.0):
        self.now = now

    def __call__(self) -> float:
        return self.now


# ---------------------------------------------------------------------------
# ByteLRU
# ---------------------------------------------------------------------------

def test_get_put_and_stats():
    lru = ByteLRU(1000)
    assert lru.get('a') is None
    assert lru.put('a', b'x' * 10) is True
    assert lru.get('a') == b'x' * 10
    assert lru.get('a') == b'x' * 10
    assert lru.stats() == {'hits': 2, 'misses': 1, 'bytes': 10, 'entries': 1, 'evictions': 0}
    assert 'a' in lru and len(lru) == 1


def test_evicts_least_recently_used_until_within_budget():
    lru = ByteLRU(400)                      # entries up to 100 bytes
    for key in 'abcd':
        lru.put(key, key.encode() * 100)
    assert lru.stats()['bytes'] == 400
    lru.get('a')                            # a is now most recent; b is the oldest
    lru.put('e', b'e' * 100)
    assert lru.get('b') is None
    assert all(lru.get(k) is not None for k in 'acde')
    stats = lru.stats()
    assert stats['bytes'] == 400 and stats['entries'] == 4 and stats['evictions'] == 1

    lru.put('f', b'f' * 100)
    lru.put('g', b'g' * 100)
    assert lru.get('c') is None and lru.get('a') is None
    assert lru.stats()['bytes'] <= 400


def test_eviction_frees_enough_for_a_large_entry():
    lru = ByteLRU(400)
    for key in 'abcd':
        lru.put(key, b'.' * 40)             # 160 bytes
    lru.put('big', b'!' * 100)              # 260
    lru.put('big2', b'!' * 100)             # 360
    lru.put('big3', b'!' * 100)             # 460 -> evict a, b (40 each) -> 380
    stats = lru.stats()
    assert stats['bytes'] == 380 and stats['evictions'] == 2
    assert lru.get('a') is None and lru.get('b') is None and lru.get('c') is not None


def test_never_stores_an_entry_larger_than_a_quarter():
    lru = ByteLRU(400)
    lru.put('small', b's' * 10)
    assert lru.put('huge', b'h' * 101) is False
    assert lru.get('huge') is None
    assert lru.put('edge', b'e' * 100) is True
    assert lru.get('small') == b's' * 10
    assert lru.stats()['evictions'] == 0


def test_replacing_a_key_adjusts_bytes():
    lru = ByteLRU(1000)
    lru.put('a', b'x' * 100)
    lru.put('a', b'y' * 50)
    assert lru.get('a') == b'y' * 50
    assert lru.stats()['bytes'] == 50 and lru.stats()['entries'] == 1


def test_discard_and_clear():
    lru = ByteLRU(1000)
    lru.put('a', b'x' * 10)
    lru.put('b', b'y' * 20)
    assert lru.discard('a') is True and lru.discard('a') is False
    assert lru.stats()['bytes'] == 20
    lru.get('b')
    lru.clear()
    assert lru.stats() == {'hits': 0, 'misses': 0, 'bytes': 0, 'entries': 0, 'evictions': 0}
    assert lru.get('b') is None


def test_zero_budget_stores_nothing():
    lru = ByteLRU(0)
    assert lru.put('a', b'') is False
    assert lru.put('b', b'x') is False
    assert lru.stats()['entries'] == 0


def test_accepts_bytearray_and_memoryview_and_rejects_other_types():
    lru = ByteLRU(1000)
    lru.put('a', bytearray(b'abc'))
    lru.put('b', memoryview(b'def'))
    assert lru.get('a') == b'abc' and isinstance(lru.get('a'), bytes)
    assert lru.get('b') == b'def' and isinstance(lru.get('b'), bytes)
    with pytest.raises(TypeError):
        lru.put('c', 'text')
    with pytest.raises(TypeError):
        lru.put('c', {'a': 1})


@pytest.mark.parametrize('bad', [-1, 1.5, '10', None, True])
def test_rejects_a_bad_budget(bad):
    with pytest.raises(ValueError):
        ByteLRU(bad)


def test_correct_under_50_concurrent_threads():
    lru = ByteLRU(20_000)                    # entries up to 5,000 bytes
    gate = threading.Barrier(50)
    gets = [0] * 50
    errors = []

    def worker(index):
        rng = random.Random(index)
        gate.wait()
        try:
            for _ in range(400):
                key = ('zh', rng.randrange(60), 0)
                if rng.random() < 0.5:
                    lru.put(key, bytes([key[1] % 256]) * rng.randrange(1, 4000))
                else:
                    gets[index] += 1
                    data = lru.get(key)
                    if data is not None and data[:1] != bytes([key[1] % 256]):
                        errors.append(('wrong bytes', key))
                if rng.random() < 0.05:
                    lru.discard(key)
        except Exception as exc:  # pragma: no cover - surfaced below
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(50)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert errors == []
    stats = lru.stats()
    assert stats['hits'] + stats['misses'] == sum(gets)
    assert stats['bytes'] <= 20_000
    assert stats['bytes'] == sum(len(v) for v in lru._entries.values())
    assert stats['entries'] == len(lru._entries)


# ---------------------------------------------------------------------------
# NegativeCache
# ---------------------------------------------------------------------------

def test_negative_cache_expires_after_the_ttl():
    clock = FakeClock()
    neg = NegativeCache(ttl_s=60.0, clock=clock)
    key = ('zh', 5, 0)
    assert neg.contains(key) is False
    neg.add(key)
    assert neg.contains(key) is True
    clock.now += 59.9
    assert neg.contains(key) is True
    clock.now += 0.1
    assert neg.contains(key) is False
    assert len(neg) == 0


def test_negative_cache_default_ttl_and_clock():
    neg = NegativeCache()
    assert neg.ttl_s == 60.0
    neg.add('k')
    assert neg.contains('k')


def test_re_adding_restarts_the_period_and_discard_clear():
    clock = FakeClock()
    neg = NegativeCache(ttl_s=10, clock=clock)
    neg.add('a')
    clock.now += 8
    neg.add('a')
    clock.now += 8
    assert neg.contains('a')
    neg.discard('a')
    assert not neg.contains('a')
    neg.add('b')
    neg.clear()
    assert not neg.contains('b')


def test_negative_cache_is_bounded():
    clock = FakeClock()
    neg = NegativeCache(ttl_s=10, clock=clock, max_entries=3)
    for key in 'abc':
        neg.add(key)
    clock.now += 11                           # a, b, c expired
    neg.add('d')
    assert len(neg) == 1                      # pruned to the live one ... then
    for key in 'efg':
        neg.add(key)
    assert len(neg) == 3                      # ... the oldest live key is dropped
    assert not neg.contains('d') and all(neg.contains(k) for k in 'efg')


@pytest.mark.parametrize('kwargs', [{'ttl_s': -1}, {'ttl_s': 'x'}, {'max_entries': 0}])
def test_negative_cache_rejects_bad_arguments(kwargs):
    with pytest.raises(ValueError):
        NegativeCache(**kwargs)


def test_negative_cache_under_threads():
    neg = NegativeCache(ttl_s=60)
    gate = threading.Barrier(50)

    def worker(index):
        gate.wait()
        for i in range(200):
            neg.add((index, i))
            assert neg.contains((index, i))

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(50)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert len(neg) == 50 * 200


# ---------------------------------------------------------------------------
# store wiring
# ---------------------------------------------------------------------------

def test_store_builds_the_real_caches_from_config(monkeypatch):
    monkeypatch.setattr(Config, 'EXERCISE_CONTENT_CACHE_MB', 4)
    lru = store._content_cache()
    neg = store._negative_cache()
    assert isinstance(lru, cache.ByteLRU) and lru.max_bytes == 4 * 1024 * 1024
    assert isinstance(neg, cache.NegativeCache) and neg.ttl_s == 60.0
    assert store._content_cache() is lru and store._negative_cache() is neg
    store.reset_state()
    assert store._content_cache() is not lru
