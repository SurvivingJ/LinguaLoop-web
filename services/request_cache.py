"""Per-request memoisation for reads that one GET repeats many times.

Measured 2026-11-11 ([[evaluations/latency-2026-11-11]]): building a learner's
daily session read the same ``user_study_plans`` row up to six times and
recomputed the new-word state (two RPCs) up to three times, each a separate
round trip to Supabase. Every round trip costs 50-100 ms from production.

Scope rules, chosen so a cached value can never be stale:

* Only inside a Flask request whose method is GET (or HEAD). A PUT/POST that
  writes a plan and then reads it back always goes to the database.
* The cache lives on ``flask.g``, so it dies with the request.
* Exceptions are never cached: a failed read is retried by the next caller,
  exactly as before.
* A GET that writes something a cached value depends on must call
  ``invalidate`` (e.g. admitting new ladder words changes the new-word state).

Outside a request (scripts, scheduler, tests without a request context) every
call goes straight to the loader.
"""

from __future__ import annotations

from typing import Any, Callable, Hashable

from flask import g, has_request_context, request

_MISSING = object()


def _store():
    if not has_request_context() or request.method not in ('GET', 'HEAD'):
        return None
    store = getattr(g, '_request_cache', None)
    if store is None:
        store = {}
        g._request_cache = store
    return store


def memo(key: Hashable, loader: Callable[[], Any], *, cache_none: bool = True) -> Any:
    """Return ``loader()``, computed at most once per GET request for ``key``."""
    store = _store()
    if store is None:
        return loader()
    hit = store.get(key, _MISSING)
    if hit is not _MISSING:
        return hit
    value = loader()
    if value is not None or cache_none:
        store[key] = value
    return value


def put(key: Hashable, value: Any) -> None:
    """Store a value a loader would have fetched (e.g. a row read for another
    purpose earlier in the same GET). No-op outside a GET request."""
    store = _store()
    if store is not None:
        store[key] = value


def invalidate(*prefix: Any) -> None:
    """Drop every cached entry whose key is a tuple starting with ``prefix``."""
    if not has_request_context():
        return
    store = getattr(g, '_request_cache', None)
    if not store:
        return
    n = len(prefix)
    for key in [k for k in store if isinstance(k, tuple) and k[:n] == prefix]:
        store.pop(key, None)
