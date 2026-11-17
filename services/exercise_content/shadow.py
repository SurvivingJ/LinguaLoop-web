"""Background comparer for ``EXERCISE_CONTENT_SOURCE=shadow`` (ADR-047 §5-§6, TASK-978).

In shadow mode the response is still served from the database. ``reader``
snapshots ``store.canonical(content)`` per exercise for a sampled share of
``(language, sense, version)`` groups and calls ``submit(job)``; one daemon
thread (``exc-shadow``) reads the file for each job and compares. Nothing here
runs on the request thread except ``submit``, which never blocks: the queue
holds at most 256 jobs and an overflowing job is dropped and counted.

Log lines (logger ``services.exercise_content``):

* WARNING ``exercise_content.shadow_mismatch kind=<kind> sense=<id> version=<v> exercise=<id>``
  per exercise for ``missing_exercise`` (the file lacks it) and ``content_diff``
  (canonical JSON differs). For ``missing_file`` (no file) and ``fetch_error``
  (the GET failed or the file is unreadable/corrupt) one line per group with
  ``exercise=*`` and the group's exercise count ``n=<count>``.
* INFO ``exercise_content.shadow_summary compared=... ok=... missing_file=...
  missing_exercise=... content_diff=... dropped=... fetch_error=...`` each time
  another 500 exercises have been compared. Counters are per exercise
  (``compared`` is the sum of the four kinds plus ``ok``); ``dropped`` counts
  jobs lost to a full queue.

Each job carries the backend and caches that were current when it was queued,
so a job never builds a new backend. ``store.reset_state()`` stops the worker
and discards the queue and counters (``_on_reset('shadow', ...)``). Tests wait
for the worker with ``drain(timeout)``.
"""

from __future__ import annotations

import logging
import queue
import threading
import time
from collections import Counter
from dataclasses import dataclass
from typing import Any

from services.exercise_content import store
from services.exercise_content.store import ContentStorageError

logger = logging.getLogger('services.exercise_content')

QUEUE_MAX = 256
SUMMARY_EVERY = 500
WORKER_NAME = 'exc-shadow'
KINDS = ('missing_file', 'missing_exercise', 'content_diff', 'fetch_error')
_STOP = object()


@dataclass(frozen=True)
class ShadowJob:
    language_id: int
    sense_id: int
    version: int
    snapshot: dict[str, str]          # exercise id -> canonical(DB content)
    backend: Any                      # the StorageBackend current at submit time
    lru: Any = None                   # store._content_cache() at submit time (may be None)
    neg: Any = None                   # store._negative_cache() at submit time (may be None)


class _State:
    def __init__(self) -> None:
        self.queue: queue.Queue = queue.Queue(maxsize=QUEUE_MAX)
        self.stop = threading.Event()
        self.lock = threading.Lock()
        self.thread: threading.Thread | None = None
        self.counts: Counter = Counter()
        self.next_summary = SUMMARY_EVERY


_state_lock = threading.Lock()
_state = _State()


def _current() -> _State:
    with _state_lock:
        return _state


def _reset() -> None:
    """``store.reset_state()`` hook: stop the worker, drop the queue and counters."""
    global _state
    with _state_lock:
        old, _state = _state, _State()
    old.stop.set()
    try:
        old.queue.put_nowait(_STOP)
    except queue.Full:
        pass                           # the worker sees ``stop`` within its poll interval


store._on_reset('shadow', _reset)


def _ensure_worker(state: _State) -> None:
    with state.lock:
        if state.stop.is_set() or (state.thread is not None and state.thread.is_alive()):
            return
        thread = threading.Thread(target=_run, args=(state,), name=WORKER_NAME, daemon=True)
        thread.start()
        state.thread = thread


def submit(job: ShadowJob) -> bool:
    """Queue ``job`` for comparison without blocking; False (counted as dropped) when full."""
    state = _current()
    _ensure_worker(state)
    try:
        state.queue.put_nowait(job)
        return True
    except queue.Full:
        with state.lock:
            state.counts['dropped'] += 1
        return False


def stats() -> dict[str, int]:
    """Counters since the last reset, plus the current queue length."""
    state = _current()
    with state.lock:
        counts = {name: state.counts.get(name, 0)
                  for name in ('compared', 'ok', *KINDS, 'dropped')}
    counts['queued'] = state.queue.qsize()
    return counts


def drain(timeout: float = 5.0) -> bool:
    """Wait until every queued job has been compared; False on timeout (tests)."""
    state = _current()
    deadline = time.monotonic() + timeout
    with state.queue.all_tasks_done:
        while state.queue.unfinished_tasks:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return False
            state.queue.all_tasks_done.wait(remaining)
    return True


def _run(state: _State) -> None:
    while not state.stop.is_set():
        try:
            job = state.queue.get(timeout=0.5)
        except queue.Empty:
            continue
        try:
            if job is _STOP:
                return
            _compare(state, job)
        except Exception:
            logger.exception('exercise_content.shadow_worker_error')
        finally:
            state.queue.task_done()


def _read_file(job: ShadowJob) -> tuple[dict[str, dict] | None, str | None, str]:
    """(exercises, kind, detail): exercises when the file was read, else the group kind."""
    key = store._cache_key(job.language_id, job.sense_id, job.version)
    path = store.content_path(job.language_id, job.sense_id, job.version)
    lru, neg = job.lru, job.neg
    data = lru.get(key) if lru is not None else None
    if data is None:
        if neg is not None and neg.contains(key):
            return None, 'missing_file', ''
        try:
            data = job.backend.get(path)
        except Exception as exc:
            return None, 'fetch_error', f' error={type(exc).__name__}'
        if data is None:
            if neg is not None:
                neg.add(key)
            return None, 'missing_file', ''
        if lru is not None:
            lru.put(key, bytes(data))
    try:
        return store.decode_sense_file(data, sense_id=job.sense_id, version=job.version), None, ''
    except ContentStorageError as exc:
        logger.error('exercise_content.corrupt_file path=%s error=%s', path, exc)
        if lru is not None and hasattr(lru, 'discard'):
            lru.discard(key)
        if neg is not None:
            neg.add(key)
        return None, 'fetch_error', ' error=corrupt_file'


def _compare(state: _State, job: ShadowJob) -> None:
    exercises, group_kind, detail = _read_file(job)
    tally: Counter = Counter()
    if group_kind is not None:
        logger.warning('exercise_content.shadow_mismatch kind=%s sense=%s version=%s '
                       'exercise=* n=%d%s', group_kind, job.sense_id, job.version,
                       len(job.snapshot), detail)
        tally[group_kind] += len(job.snapshot)
    else:
        for exercise_id in sorted(job.snapshot):
            content = exercises.get(exercise_id)
            if content is None:
                kind = 'missing_exercise'
            elif store.canonical(content) != job.snapshot[exercise_id]:
                kind = 'content_diff'
            else:
                tally['ok'] += 1
                continue
            tally[kind] += 1
            logger.warning('exercise_content.shadow_mismatch kind=%s sense=%s version=%s '
                           'exercise=%s', kind, job.sense_id, job.version, exercise_id)
    tally['compared'] = len(job.snapshot)
    with state.lock:
        state.counts.update(tally)
        compared = state.counts['compared']
        if compared < state.next_summary:
            return
        state.next_summary = (compared // SUMMARY_EVERY + 1) * SUMMARY_EVERY
        counts = dict(state.counts)
    logger.info('exercise_content.shadow_summary compared=%d ok=%d missing_file=%d '
                'missing_exercise=%d content_diff=%d dropped=%d fetch_error=%d',
                counts.get('compared', 0), counts.get('ok', 0), counts.get('missing_file', 0),
                counts.get('missing_exercise', 0), counts.get('content_diff', 0),
                counts.get('dropped', 0), counts.get('fetch_error', 0))
