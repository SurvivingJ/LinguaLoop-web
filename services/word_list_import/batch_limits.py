"""Admission control for word-list uploads.

Each accepted batch drives minutes of LLM generation per new word, so uploads
are bounded three ways: one in-flight batch per user, a per-user daily batch
cap, and a fixed worker pool with a bounded queue.

State is in-process and lock-protected. No table records a batch as such
(``user_word_watchlist`` only gains rows for words that resolved, and nothing
marks a batch as still running), so with several gunicorn workers the limits
apply per worker. ``count_recent_batches`` adds a best-effort cross-worker
floor for the daily cap from the watchlist rows that do exist.
"""

import logging
import os
import queue
import threading
import time
from collections import deque
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

DAY_SECONDS = 24 * 60 * 60


def _env_int(name: str, default: int) -> int:
    try:
        return max(1, int(os.getenv(name, default)))
    except (TypeError, ValueError):
        return default


MAX_BATCHES_PER_DAY = _env_int('WORD_LIST_MAX_BATCHES_PER_DAY', 5)
MAX_WORKERS = _env_int('WORD_LIST_IMPORT_WORKERS', 2)
MAX_QUEUED_BATCHES = _env_int('WORD_LIST_MAX_QUEUED_BATCHES', 20)

REJECT_IN_FLIGHT = 'in_flight'
REJECT_DAILY_CAP = 'daily_cap'
REJECT_BUSY = 'busy'


class BatchLimiter:
    """Per-user in-flight and daily-count tracker."""

    def __init__(self, max_per_day: int = MAX_BATCHES_PER_DAY, clock=time.time):
        self.max_per_day = max_per_day
        self._clock = clock
        self._lock = threading.Lock()
        self._in_flight: set = set()
        self._history: dict = {}

    def _recent(self, user_id) -> deque:
        stamps = self._history.get(user_id)
        if stamps is None:
            return deque()
        cutoff = self._clock() - DAY_SECONDS
        while stamps and stamps[0] <= cutoff:
            stamps.popleft()
        if not stamps:
            self._history.pop(user_id, None)
        return stamps

    def reserve(self, user_id, known_batches_today: int = 0):
        """Claim a slot. Returns None when admitted, else a REJECT_* reason."""
        with self._lock:
            if user_id in self._in_flight:
                return REJECT_IN_FLIGHT
            used = max(len(self._recent(user_id)), known_batches_today)
            if used >= self.max_per_day:
                return REJECT_DAILY_CAP
            self._in_flight.add(user_id)
            self._history.setdefault(user_id, deque()).append(self._clock())
            return None

    def release(self, user_id, refund: bool = False):
        """Mark the user's batch finished. ``refund`` returns the daily slot
        for a batch that was never actually started."""
        with self._lock:
            self._in_flight.discard(user_id)
            if refund:
                stamps = self._history.get(user_id)
                if stamps:
                    stamps.pop()
                    if not stamps:
                        self._history.pop(user_id, None)

    def reset(self):
        with self._lock:
            self._in_flight.clear()
            self._history.clear()


class WorkerPool:
    """Fixed number of daemon workers draining a bounded queue."""

    def __init__(self, max_workers: int = MAX_WORKERS,
                 max_queued: int = MAX_QUEUED_BATCHES):
        self.max_workers = max_workers
        self._queue: queue.Queue = queue.Queue(maxsize=max_queued)
        self._lock = threading.Lock()
        self._threads: list = []

    def _worker(self):
        while True:
            job = self._queue.get()
            try:
                job()
            except Exception:
                logger.exception('word-list worker job failed')
            finally:
                self._queue.task_done()

    def submit(self, job) -> bool:
        """Queue a job. Returns False when the queue is full."""
        try:
            self._queue.put_nowait(job)
        except queue.Full:
            return False
        with self._lock:
            if len(self._threads) < self.max_workers:
                thread = threading.Thread(
                    target=self._worker, daemon=True,
                    name=f'word-list-import-{len(self._threads)}',
                )
                self._threads.append(thread)
                thread.start()
        return True


def count_recent_batches(db, user_id) -> int:
    """Distinct upload batches this user has watchlist rows for in the last
    24 hours. Best-effort: returns 0 when the lookup fails."""
    try:
        since = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        resp = (
            db.table('user_word_watchlist')
            .select('upload_batch_id')
            .eq('user_id', user_id)
            .gte('created_at', since)
            .execute()
        )
        return len({
            row.get('upload_batch_id') for row in (resp.data or [])
            if row.get('upload_batch_id')
        })
    except Exception as exc:
        logger.debug('recent word-list batch lookup failed: %s', exc)
        return 0
