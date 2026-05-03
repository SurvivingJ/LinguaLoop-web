"""
Shared in-memory task runner for local admin blueprints.

Provides background-thread execution with log queue capture and a
thread-local `task_id` so worker code can poll `is_task_stopped()`.
SSE streaming and task-stop endpoints live in `routes/admin_local.py`
and read from the same `TASKS` dict.
"""

import logging
import queue
import threading
import time

logger = logging.getLogger(__name__)

# task_id -> {status, log_queue, result, error, started_at, stop_event}
TASKS: dict = {}

# Per-thread current task_id, used by is_task_stopped()
_thread_task_id = threading.local()


def is_task_stopped() -> bool:
    """Check if the currently executing background task has been asked to stop."""
    task_id = getattr(_thread_task_id, 'value', None)
    if task_id and task_id in TASKS:
        return TASKS[task_id]['stop_event'].is_set()
    return False


class QueueLogHandler(logging.Handler):
    """Logging handler that pushes formatted records into a queue."""

    def __init__(self, log_queue: queue.Queue):
        super().__init__()
        self.log_queue = log_queue

    def emit(self, record):
        try:
            self.log_queue.put(self.format(record))
        except Exception:
            pass


def _prune_old_tasks(max_age_seconds: int = 3600) -> None:
    """Remove tasks older than `max_age_seconds`."""
    cutoff = time.time() - max_age_seconds
    stale = [tid for tid, t in TASKS.items() if t['started_at'] < cutoff]
    for tid in stale:
        del TASKS[tid]


def run_in_thread(task_id: str, fn, *args, **kwargs) -> None:
    """Run `fn(*args, **kwargs)` in a daemon thread, capturing logs to a queue."""
    _prune_old_tasks()

    log_queue: queue.Queue = queue.Queue()
    handler = QueueLogHandler(log_queue)
    handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(name)s: %(message)s'))

    stop_event = threading.Event()

    TASKS[task_id] = {
        'status': 'running',
        'log_queue': log_queue,
        'result': None,
        'error': None,
        'started_at': time.time(),
        'stop_event': stop_event,
    }

    def target():
        _thread_task_id.value = task_id
        root_logger = logging.getLogger()
        root_logger.addHandler(handler)
        try:
            result = fn(*args, **kwargs)
            if stop_event.is_set():
                TASKS[task_id]['status'] = 'stopped'
                TASKS[task_id]['result'] = result
            else:
                TASKS[task_id]['result'] = result
                TASKS[task_id]['status'] = 'completed'
        except Exception as exc:
            if stop_event.is_set():
                TASKS[task_id]['status'] = 'stopped'
            else:
                TASKS[task_id]['error'] = str(exc)
                TASKS[task_id]['status'] = 'failed'
                logger.exception(f"Task {task_id} failed: {exc}")
        finally:
            root_logger.removeHandler(handler)

    thread = threading.Thread(target=target, daemon=True)
    thread.start()
