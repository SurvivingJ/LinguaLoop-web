"""Run independent blocking calls (Supabase round trips) concurrently."""
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, List

_pool = ThreadPoolExecutor(max_workers=16, thread_name_prefix='io')


def run_parallel(*calls: Callable[[], Any]) -> List[Any]:
    """Run zero-argument callables concurrently; return results in call order.

    The first exception raised by any call propagates. Callables run outside
    the Flask request context, so capture clients and ids before calling
    (do not read ``g``, ``request`` or ``current_app`` inside them).
    """
    if len(calls) <= 1:
        return [c() for c in calls]
    futures = [_pool.submit(c) for c in calls]
    return [f.result() for f in futures]
