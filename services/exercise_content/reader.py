"""Read path behind ``store.hydrate`` and ``store.fetch_sense`` (ADR-049 §5, §9).

TASK-1010; the ``shadow`` comparison and the DB fallback were removed in
TASK-1031 (``exercises.content`` was dropped on 2026-11-19). ``store`` imports
this module lazily.

Contract with ``store``: ``store.hydrate`` validates the arguments and calls
``hydrate(items, ...)`` with ``language_id`` already an int or None,
``max_senses`` an int >= 0 and ``deadline_s`` a float > 0 (``None`` resolved
from ``EXERCISE_CONTENT_MAX_SENSES_PER_CALL`` / ``EXERCISE_CONTENT_DEADLINE_S``).
A direct call may still pass ``None`` for either; it is treated the same way.
Exceptions propagate, so ``hydrate`` does not raise for storage, network or
data problems.

Hydration, per call:

1. Items considered: dicts with a truthy ``item[id_key]`` (``report.items``
   counts all of them). Items whose ``content`` is already non-None are left
   alone. The rest are grouped by ``(language, sense, version)``: language is
   the ``language_id`` argument, else ``item['language_id']``; sense is
   ``item[sense_key]``; version is ``item['content_version']``. An item without
   a usable int for any of the three cannot be grouped and is missing.
2. Per-call cap: the first ``max_senses`` groups (in item order) are served;
   the rest count in ``over_cap`` and are treated as missing.
3. Without Storage credentials (``store._storage_configured()`` false) every
   group is missing, with one ERROR per process and no network call.
   Otherwise: byte LRU (``cache_hits``) -> negative cache (a file known to be
   missing in the last 60 s is not fetched) -> parallel ``backend.get`` on this
   module's own ``ThreadPoolExecutor`` (``thread_name_prefix='exc-fetch'``,
   never ``services.concurrency``'s pool, ADR-049 Context finding 7). The call
   waits at most until ``deadline_s`` after it started; groups still in flight
   count in ``over_cap`` and are treated as missing (the fetch keeps running and
   warms the cache for the next call). ``fetched`` counts GETs that returned a
   file; a GET that finds nothing adds the key to the negative cache; a GET
   that fails is retried once, then logged (one WARNING per call) and retried
   by the next call.
4. Each file is parsed once per call (``store.decode_sense_file``); a corrupt
   file is logged at ERROR, dropped from the byte cache, negative-cached and
   treated as missing. Every item receives an object shared with nothing else:
   a repeated id in one call gets a ``deepcopy``.
5. Missing: removed from ``items`` in place, order kept (``drop_missing=True``,
   counted in ``dropped``) or given ``content=None``; either way listed in
   ``missing_ids`` (unique, in item order) and logged with one WARNING per call.
"""

from __future__ import annotations

import copy
import logging
import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor, wait
from dataclasses import dataclass, field
from typing import Any

from services.exercise_content import store
from services.exercise_content.store import ContentStorageError, HydrationReport

logger = logging.getLogger('services.exercise_content')

FETCH_THREAD_PREFIX = 'exc-fetch'
_LOG_IDS = 10            # ids quoted in a WARNING line

_executor_lock = threading.Lock()
_executor: ThreadPoolExecutor | None = None


def _fetch_executor() -> ThreadPoolExecutor:
    """The store's own fetch pool, built lazily (``EXERCISE_CONTENT_FETCH_CONCURRENCY``)."""
    global _executor
    with _executor_lock:
        if _executor is None:
            workers = store._setting_int('EXERCISE_CONTENT_FETCH_CONCURRENCY', 16, minimum=1)
            _executor = ThreadPoolExecutor(max_workers=workers,
                                           thread_name_prefix=FETCH_THREAD_PREFIX)
        return _executor


def _reset() -> None:
    """``store.reset_state()`` hook: drop the pool."""
    global _executor
    with _executor_lock:
        old, _executor = _executor, None
    if old is not None:
        old.shutdown(wait=False, cancel_futures=True)


store._on_reset('reader', _reset)


# ---------------------------------------------------------------------------
# Grouping
# ---------------------------------------------------------------------------

@dataclass
class _Group:
    language_id: int
    sense_id: int
    version: int
    key: tuple
    indexes: list[int] = field(default_factory=list)
    data: bytes | None = None
    state: str = 'pending'     # hit | fetched | missing | over_cap | error | corrupt

    @property
    def path(self) -> str:
        return store.content_path(self.language_id, self.sense_id, self.version)


def _non_negative_int(value: Any) -> int | None:
    parsed = store._as_int(value)
    return parsed if parsed is not None and parsed >= 0 else None


def _route(item: dict, language_id: Any, sense_key: str) -> tuple[int, int, int] | None:
    """``(language_id, sense_id, version)`` of an item, or None when one is unusable."""
    language = _non_negative_int(language_id if language_id is not None
                                 else item.get('language_id'))
    sense = _non_negative_int(item.get(sense_key))
    version = _non_negative_int(item.get('content_version'))
    if language is None or sense is None or version is None:
        return None
    return language, sense, version


def _resolve_limits(max_senses: Any, deadline_s: Any) -> tuple[int, float]:
    if max_senses is None:
        max_senses = store._setting_int('EXERCISE_CONTENT_MAX_SENSES_PER_CALL', 160, minimum=0)
    if deadline_s is None:
        deadline_s = store._setting_float('EXERCISE_CONTENT_DEADLINE_S', 3.0, low=0.0,
                                          low_inclusive=False)
    return max_senses, float(deadline_s)


# ---------------------------------------------------------------------------
# Public entry points
# ---------------------------------------------------------------------------

def hydrate(items: list[dict], *, language_id: int | None, id_key: str, sense_key: str,
            drop_missing: bool, max_senses: int | None,
            deadline_s: float | None) -> HydrationReport:
    """Hydration of ``items`` in place from the content files (ADR-049 §9 ``hydrate``)."""
    if not isinstance(items, list):
        raise ValueError(f'hydrate: items must be a list, got {type(items).__name__}')
    if language_id is not None and store._as_int(language_id) is None:
        raise ValueError(f'hydrate: language_id must be an int or None, got {language_id!r}')
    language_id = store._as_int(language_id) if language_id is not None else None
    max_senses, deadline_s = _resolve_limits(max_senses, deadline_s)
    return _hydrate_storage(items, language_id=language_id, id_key=id_key,
                            sense_key=sense_key, drop_missing=drop_missing,
                            max_senses=max_senses, deadline_s=deadline_s)


def fetch_sense(language_id: int, sense_id: int, version: int) -> dict[str, dict] | None:
    """exercise_id -> content of one file (fresh objects), via the cache; None when
    missing, unreadable or corrupt (logged), or without Storage credentials. Never raises."""
    try:
        if not store._storage_configured():
            store._log_not_configured()
            return None
        language = _non_negative_int(language_id)
        sense = _non_negative_int(sense_id)
        ver = _non_negative_int(version)
        if language is None or sense is None or ver is None:
            logger.warning('exercise_content.fetch_sense bad arguments language_id=%r '
                           'sense_id=%r version=%r', language_id, sense_id, version)
            return None
        key = store._cache_key(language, sense, ver)
        path = store.content_path(language, sense, ver)
        lru, neg = store._content_cache(), store._negative_cache()
        data = lru.get(key) if lru is not None else None
        if data is None:
            if neg is not None and neg.contains(key):
                return None
            data = store.backend().get(path)
            if data is None:
                if neg is not None:
                    neg.add(key)
                logger.warning('exercise_content.missing_file path=%s', path)
                return None
            if lru is not None:
                lru.put(key, data)
        try:
            return store.decode_sense_file(data, sense_id=sense, version=ver)
        except ContentStorageError as exc:
            _forget_corrupt(key, path, exc, lru, neg)
            return None
    except Exception as exc:
        logger.warning('exercise_content.fetch_sense_error language_id=%r sense_id=%r '
                       'version=%r %s: %s', language_id, sense_id, version,
                       type(exc).__name__, exc)
        return None


# ---------------------------------------------------------------------------
# hydration
# ---------------------------------------------------------------------------

def _forget_corrupt(key: tuple, path: str, exc: Exception, lru, neg) -> None:
    logger.error('exercise_content.corrupt_file path=%s error=%s', path, exc)
    if lru is not None and hasattr(lru, 'discard'):
        lru.discard(key)
    if neg is not None:
        neg.add(key)


def _fetch_one(backend, key: tuple, path: str, lru, neg) -> bytes | None:
    """Runs on the fetch pool. Fills the caches itself, so a GET that finishes
    after the caller's deadline still warms the next call.

    A failed GET (timeout, connection error, 5xx: ``ContentStorageError``) is
    retried once. A not-found answer is not an error and is never retried.
    Production 2026-11-18: one of seven cold GETs from Railway never reached
    Supabase, and only the DB fallback (since removed) hid it.
    """
    try:
        data = backend.get(path)
    except ContentStorageError as exc:
        logger.warning('exercise_content.fetch_retry path=%s %s', path, exc)
        data = backend.get(path)
    if data is None:
        if neg is not None:
            neg.add(key)
        return None
    if not isinstance(data, bytes):
        data = bytes(data)
    if lru is not None:
        lru.put(key, data)
    return data


def _fetch_groups(groups: list[_Group], deadline_at: float, lru, neg,
                  report: HydrationReport, errors: list[tuple[_Group, BaseException]]) -> None:
    try:
        backend = store.backend()
        executor = _fetch_executor()
    except Exception as exc:          # no backend: every group is missing for this call
        for group in groups:
            group.state = 'error'
            errors.append((group, exc))
        return
    futures: dict[Future, _Group] = {}
    for group in groups:
        try:
            futures[executor.submit(_fetch_one, backend, group.key, group.path, lru, neg)] = group
        except RuntimeError as exc:   # pool shut down by a concurrent reset_state()
            group.state = 'error'
            errors.append((group, exc))
    if not futures:
        return
    done, not_done = wait(futures, timeout=max(0.0, deadline_at - time.monotonic()))
    for future in not_done:
        future.cancel()
        futures[future].state = 'over_cap'
        report.over_cap += 1
    for future in done:
        group = futures[future]
        if future.cancelled():
            group.state = 'over_cap'
            report.over_cap += 1
            continue
        exc = future.exception()
        if exc is not None:
            group.state = 'error'
            errors.append((group, exc))
            continue
        data = future.result()
        if data is None:
            group.state = 'missing'
        else:
            group.data = data
            group.state = 'fetched'
            report.fetched += 1


def _assign(item: dict, content: Any, id_key: str, used: set[str]) -> None:
    exercise_id = str(item[id_key])
    item['content'] = copy.deepcopy(content) if exercise_id in used else content
    used.add(exercise_id)


def _hydrate_storage(items: list, *, language_id: int | None, id_key: str, sense_key: str,
                     drop_missing: bool, max_senses: int,
                     deadline_s: float) -> HydrationReport:
    started = time.monotonic()
    deadline_at = started + deadline_s
    report = HydrationReport()

    groups: dict[tuple, _Group] = {}
    missing: list[int] = []                       # item indexes still without content
    for index, item in enumerate(items):
        if not isinstance(item, dict) or not item.get(id_key):
            continue
        report.items += 1
        if item.get('content') is not None:
            continue
        route = _route(item, language_id, sense_key)
        if route is None:
            missing.append(index)
            continue
        key = store._cache_key(*route)
        group = groups.get(key)
        if group is None:
            group = groups[key] = _Group(*route, key=key)
        group.indexes.append(index)
    report.groups = len(groups)

    ordered = list(groups.values())
    served, skipped = ordered[:max_senses], ordered[max_senses:]
    for group in skipped:
        group.state = 'over_cap'
    report.over_cap += len(skipped)

    lru, neg = store._content_cache(), store._negative_cache()
    to_fetch: list[_Group] = []
    if served and not store._storage_configured():
        store._log_not_configured()
        for group in served:
            group.state = 'missing'
        served = []
    for group in served:
        data = lru.get(group.key) if lru is not None else None
        if data is not None:
            group.data, group.state = data, 'hit'
            report.cache_hits += 1
        elif neg is not None and neg.contains(group.key):
            group.state = 'missing'
        else:
            to_fetch.append(group)

    errors: list[tuple[_Group, BaseException]] = []
    if to_fetch:
        _fetch_groups(to_fetch, deadline_at, lru, neg, report, errors)
    if errors:
        group, exc = errors[0]
        logger.warning('exercise_content.fetch_error n=%d first=%s %s: %s', len(errors),
                       group.path, type(exc).__name__, exc)

    for group in ordered:
        if group.data is None:
            missing.extend(group.indexes)
            continue
        try:
            exercises = store.decode_sense_file(group.data, sense_id=group.sense_id,
                                                version=group.version)
        except ContentStorageError as exc:
            group.state = 'corrupt'
            _forget_corrupt(group.key, group.path, exc, lru, neg)
            missing.extend(group.indexes)
            continue
        used: set[str] = set()
        for index in group.indexes:
            item = items[index]
            content = exercises.get(str(item[id_key]))
            if content is None:
                missing.append(index)
            else:
                _assign(item, content, id_key, used)

    missing.sort()
    if missing:
        report.missing_ids = list(dict.fromkeys(str(items[i][id_key]) for i in missing))
        if drop_missing:
            drop = set(missing)
            items[:] = [item for index, item in enumerate(items) if index not in drop]
            report.dropped = len(drop)
        else:
            for index in missing:
                items[index]['content'] = None
        logger.warning('exercise_content.missing n=%d dropped=%d ids=%s',
                       len(report.missing_ids), report.dropped,
                       ','.join(report.missing_ids[:_LOG_IDS]))
    report.elapsed_ms = (time.monotonic() - started) * 1000.0
    return report
