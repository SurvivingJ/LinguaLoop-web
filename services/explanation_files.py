"""Pre-written exercise explanations kept as Storage files (ADR-064, 2026-11-27).

Why
---
ADR-064 writes the per-option explanation of a spot-the-error /
pick-the-sentence item the first time it is served and keeps it in the table
``exercise_explanations``. The owner wants every Japanese explanation written
ahead of time by a batch. At ~1.9 KB per item that is ~35 MB for ja alone, and
the database stood at 473 MB of the Free plan's 500 MB on 2026-11-27, while
Storage had 166 MB of 1 GB in use (wiki/evaluations/explanation-storage-2026-11-27.md).
So the pre-written explanations live in Storage files beside the exercise
content files (bucket ``exercise-content``, ADR-049), not in the table.

Layout
------
One immutable file per target language, sense, learner language and prompt
version::

    explanations/{lang}/{sense_id}.{nl}.p{prompt_version}.json   e.g. explanations/ja/35443.en.p2.json

    {"format": 1, "language_id": 3, "sense_id": 35443, "nl_language_id": 2,
     "prompt_version": 2,
     "exercises": {"<exercise_id>": {"content_version": 0, "model": "...",
                                     "payload": {"sentences": [...], "prompt_version": 2}}}}

``payload`` is exactly what a table row keeps; ``content_version`` is the
version of the exercise content it was written for, and the reader serves an
entry only to an item at that version (``exercise_explanations`` applies the
same rule as for table rows). A new prompt version is a new path, so files of
an older prompt are simply never read.

Files are written once: ``write_file`` never overwrites (``backend.put`` raises
``AlreadyExists`` and ``write_file`` answers ``'exists'``) and nothing here
deletes. The ``explanations/`` prefix is outside every ``{lang}/`` folder that
``scripts/sweep_exercise_content.py`` lists (Storage lists one folder level),
so the orphan sweep never sees these files.

Reading
-------
``read_for_senses`` fetches the files of a request's senses concurrently on
this module's own pool (``thread_name_prefix='explain-file'``; never
``services.concurrency``'s pool, whose callers may already be waiting on it,
see ``services/exercise_content/reader.py``), through a process-wide byte LRU
(files are immutable, so no TTL) and a negative cache (a missing file is not
asked for again for ``NEGATIVE_TTL_S``; files only ever appear, so a short
period is safe). The call waits at most ``deadline_s``; files still in flight
count as missing (their fetch goes on and warms the cache for the next call).
Bytes, not parsed objects, are cached, so every call returns objects shared
with nothing else. It never raises for storage or network problems (one
WARNING per call) and returns {} when Storage is not configured.
"""

from __future__ import annotations

import json
import logging
import math
import threading
import time
from collections.abc import Iterable, Mapping
from concurrent.futures import Future, ThreadPoolExecutor, wait
from typing import Any

from services.exercise_content import store
from services.exercise_content.cache import ByteLRU, NegativeCache
from services.exercise_content.store import AlreadyExists, ContentStorageError

logger = logging.getLogger(__name__)

FORMAT = 1
PREFIX = 'explanations'
FETCH_THREAD_PREFIX = 'explain-file'
DEFAULT_DEADLINE_S = 2.0
CACHE_BYTES = 8 * 1024 * 1024          # ~8 MB of files, a few thousand senses
NEGATIVE_TTL_S = 600.0
MAX_SENSES_PER_CALL = 160              # the content reader's per-call cap
_WORKERS = 6                           # beside the content reader's 16 on the same HTTP pool
_LOG_PATHS = 5

_state_lock = threading.Lock()
_lru: ByteLRU | None = None
_neg: NegativeCache | None = None
_cache_backend: Any = None             # the backend the two caches hold files of
_executor: ThreadPoolExecutor | None = None


def _now() -> float:
    return time.monotonic()


# ---------------------------------------------------------------------------
# Path and codec (pure)
# ---------------------------------------------------------------------------

def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _check_int(name: str, value: Any) -> int:
    if not _is_int(value) or value < 0:
        raise ValueError(f'{name} must be an int >= 0, got {value!r}')
    return value


def _code(name: str, language_id: Any) -> str:
    code = store.LANGUAGE_CODES.get(language_id) if _is_int(language_id) else None
    if code is None:
        raise ValueError(f'{name}: unknown language id {language_id!r} '
                         f'(known: {sorted(store.LANGUAGE_CODES)})')
    return code


def file_path(language_id: int, sense_id: int, nl_language_id: int, prompt_version: int) -> str:
    """``explanations/{lang}/{sense_id}.{nl}.p{prompt_version}.json``; ValueError for an
    unknown language id or a sense id / prompt version that is not an int >= 0."""
    lang = _code('language_id', language_id)
    nl = _code('nl_language_id', nl_language_id)
    _check_int('sense_id', sense_id)
    _check_int('prompt_version', prompt_version)
    return f'{PREFIX}/{lang}/{sense_id}.{nl}.p{prompt_version}.json'


def encode(language_id: int, sense_id: int, nl_language_id: int, prompt_version: int,
           exercises: Mapping[str, Mapping]) -> bytes:
    """The file as UTF-8 JSON (compact, ``ensure_ascii=False``, exercises in id order, so
    the same input always gives the same bytes).

    ``exercises``: ``{exercise_id: {"content_version": int, "model": str | None,
    "payload": {...}}}``; other keys of an entry are dropped. ValueError, before anything
    is written, for: bad ids (``file_path``), no exercises (an empty file could never be
    replaced), an exercise id that is not a non-empty str, a ``content_version`` that is
    not an int >= 0, a ``model`` that is neither str nor None, or a payload that is not an
    object with a non-empty ``sentences`` list and this file's ``prompt_version`` (any
    other payload would never be served from it).
    """
    file_path(language_id, sense_id, nl_language_id, prompt_version)
    if not isinstance(exercises, Mapping) or not exercises:
        raise ValueError('encode: exercises must be a non-empty mapping of id -> entry')
    body: dict[str, dict] = {}
    for exercise_id in exercises:
        if not isinstance(exercise_id, str) or not exercise_id:
            raise ValueError(f'encode: exercise id {exercise_id!r} is not a non-empty str')
    for exercise_id in sorted(exercises):
        entry = exercises[exercise_id]
        where = f'encode: exercise {exercise_id}'
        if not isinstance(entry, Mapping):
            raise ValueError(f'{where}: entry is not an object')
        version, model, payload = (entry.get('content_version'), entry.get('model'),
                                   entry.get('payload'))
        _check_int(f'{where}: content_version', version)
        if model is not None and not isinstance(model, str):
            raise ValueError(f'{where}: model must be a str or None, got {model!r}')
        if not isinstance(payload, dict):
            raise ValueError(f'{where}: payload is not an object')
        if not isinstance(payload.get('sentences'), list) or not payload['sentences']:
            raise ValueError(f'{where}: payload has no sentences')
        if payload.get('prompt_version') != prompt_version:
            raise ValueError(f"{where}: payload prompt_version {payload.get('prompt_version')!r} "
                             f'!= file prompt_version {prompt_version}')
        body[exercise_id] = {'content_version': version, 'model': model, 'payload': payload}
    doc = {'format': FORMAT, 'language_id': language_id, 'sense_id': sense_id,
           'nl_language_id': nl_language_id, 'prompt_version': prompt_version,
           'exercises': body}
    try:
        text = json.dumps(doc, ensure_ascii=False, separators=(',', ':'))
    except (TypeError, ValueError) as exc:
        raise ValueError(f'encode: payload is not JSON-serialisable: {exc}') from exc
    return text.encode('utf-8')


def _problem(doc: Any) -> str | None:
    """Why ``doc`` is not a usable file, or None."""
    if not isinstance(doc, dict):
        return 'not a JSON object'
    if not _is_int(doc.get('format')) or doc['format'] != FORMAT:
        return f"unsupported format {doc.get('format')!r}"
    for name in ('language_id', 'nl_language_id'):
        if not _is_int(doc.get(name)) or doc[name] not in store.LANGUAGE_CODES:
            return f'bad {name} {doc.get(name)!r}'
    for name in ('sense_id', 'prompt_version'):
        if not _is_int(doc.get(name)) or doc[name] < 0:
            return f'bad {name} {doc.get(name)!r}'
    exercises = doc.get('exercises')
    if not isinstance(exercises, dict):
        return 'no exercises object'
    for exercise_id, entry in exercises.items():
        if not isinstance(entry, dict):
            return f'entry {exercise_id} is not an object'
        version = entry.get('content_version')
        if not _is_int(version) or version < 0:
            return f'entry {exercise_id} has content_version {version!r}'
        if entry.get('model') is not None and not isinstance(entry['model'], str):
            return f'entry {exercise_id} has model {entry["model"]!r}'
        if not isinstance(entry.get('payload'), dict):
            return f'entry {exercise_id} has no payload object'
    return None


def _parse(data: Any) -> tuple[dict | None, str | None]:
    """(doc, None), or (None, why it is malformed)."""
    if isinstance(data, str):
        text = data
    elif isinstance(data, (bytes, bytearray, memoryview)):
        try:
            text = bytes(data).decode('utf-8')
        except UnicodeDecodeError:
            return None, 'not UTF-8'
    else:
        return None, f'expected bytes, got {type(data).__name__}'
    try:
        doc = json.loads(text)
    except ValueError as exc:
        return None, f'not valid JSON: {exc}'
    problem = _problem(doc)
    return (None, problem) if problem else (doc, None)


def decode(data: bytes) -> dict | None:
    """The file as a dict (``format``, the four ids, ``exercises``), or None with one
    WARNING when it is malformed (not UTF-8 JSON, another format, a bad id, an entry
    without an int ``content_version`` or a ``payload`` object)."""
    doc, problem = _parse(data)
    if doc is None:
        logger.warning('explanation_files.malformed %s', problem)
    return doc


# ---------------------------------------------------------------------------
# Process state
# ---------------------------------------------------------------------------

def _caches(backend: Any) -> tuple[ByteLRU, NegativeCache]:
    """The byte LRU and negative cache of ``backend``'s files; a different backend
    (``store.set_backend``) gets fresh ones, since the entries belong to the old one."""
    global _lru, _neg, _cache_backend
    with _state_lock:
        if _lru is None or _neg is None or _cache_backend is not backend:
            _lru = ByteLRU(CACHE_BYTES)
            _neg = NegativeCache(ttl_s=NEGATIVE_TTL_S, clock=lambda: _now())
            _cache_backend = backend
        return _lru, _neg


def _fetch_executor() -> ThreadPoolExecutor:
    global _executor
    with _state_lock:
        if _executor is None:
            _executor = ThreadPoolExecutor(max_workers=_WORKERS,
                                           thread_name_prefix=FETCH_THREAD_PREFIX)
        return _executor


def reset_cache() -> None:
    """Forget every cached file and missing-file mark (tests; also run by
    ``store.reset_state()``). The fetch pool is kept: its threads hold no state."""
    global _lru, _neg, _cache_backend
    with _state_lock:
        _lru = _neg = _cache_backend = None


store._on_reset('explanation_files', reset_cache)


# ---------------------------------------------------------------------------
# Write
# ---------------------------------------------------------------------------

def write_file(language_id: int, sense_id: int, nl_language_id: int, prompt_version: int,
               exercises: Mapping[str, Mapping]) -> str:
    """Upload one sense's file with ``store.backend().put``: ``'written'``, or ``'exists'``
    when a file is already at that path (it is left exactly as it was: files are never
    overwritten or deleted). ValueError from ``encode`` before any call; every other
    backend error (``ContentStorageError``: no credentials, network, HTTP) propagates."""
    path = file_path(language_id, sense_id, nl_language_id, prompt_version)
    data = encode(language_id, sense_id, nl_language_id, prompt_version, exercises)
    backend = store.backend()
    try:
        backend.put(path, data)
        result = 'written'
    except AlreadyExists:
        result = 'exists'
    lru, neg = _caches(backend)
    neg.discard(path)                     # it exists now, whoever wrote it
    if result == 'written':
        lru.put(path, data)
    return result


# ---------------------------------------------------------------------------
# Read
# ---------------------------------------------------------------------------

def _sense_list(sense_ids: Iterable[Any]) -> list[int]:
    """Unique sense ids (ints or digit strings, >= 0), first-seen order."""
    seen: dict[int, None] = {}
    for value in sense_ids or ():
        sense = store._as_int(value)
        if sense is not None and sense >= 0:
            seen.setdefault(sense, None)
    return list(seen)


def _deadline(deadline_s: Any) -> float:
    if deadline_s is None:
        return DEFAULT_DEADLINE_S
    if isinstance(deadline_s, bool) or not isinstance(deadline_s, (int, float)) \
            or not math.isfinite(deadline_s) or deadline_s <= 0:
        logger.warning('explanation_files: deadline_s=%r is invalid; using %s',
                       deadline_s, DEFAULT_DEADLINE_S)
        return DEFAULT_DEADLINE_S
    return float(deadline_s)


def _fetch_one(backend: Any, path: str, lru: ByteLRU, neg: NegativeCache) -> bytes | None:
    """Runs on the fetch pool and fills the caches itself, so a GET that finishes after
    the caller's deadline still serves the next call. A failed GET is retried once (as in
    the content reader: a cold GET can be lost); "not found" is not a failure."""
    try:
        data = backend.get(path)
    except ContentStorageError as exc:
        logger.info('explanation_files.fetch_retry path=%s %s', path, exc)
        data = backend.get(path)
    if data is None:
        neg.add(path)
        return None
    if not isinstance(data, bytes):
        data = bytes(data)
    lru.put(path, data)
    return data


def read_for_senses(language_id: int, sense_ids: Iterable[int], nl_language_id: int,
                    prompt_version: int, *, deadline_s: float | None = None) -> dict[str, dict]:
    """``{exercise_id: {"content_version", "model", "payload"}}`` from the files of these
    senses, merged (an exercise id belongs to one sense, so nothing collides).

    Missing, late (past ``deadline_s``, default ``DEFAULT_DEADLINE_S``), unreadable or
    malformed files, and senses past ``MAX_SENSES_PER_CALL``, contribute nothing. {} when
    Storage is not configured (``store._storage_configured()``), for an unknown language
    id, or when nothing applies. Never raises; one WARNING per call for what went wrong.
    """
    try:
        return _read(language_id, sense_ids, nl_language_id, prompt_version, deadline_s)
    except Exception as exc:              # a bug, or the pool shut down under us
        logger.warning('explanation_files.read_failed %s: %s', type(exc).__name__, exc)
        return {}


def _read(language_id: Any, sense_ids: Iterable[Any], nl_language_id: Any,
          prompt_version: Any, deadline_s: Any) -> dict[str, dict]:
    started = time.monotonic()
    senses = _sense_list(sense_ids)
    if not senses:
        return {}
    try:
        paths = {sense: file_path(language_id, sense, nl_language_id, prompt_version)
                 for sense in senses}
    except ValueError as exc:
        logger.warning('explanation_files.bad_arguments %s', exc)
        return {}
    if not store._storage_configured():
        store._warn_once(('explanation_files', 'not_configured'), logging.WARNING,
                         'explanation_files: Storage is not configured (SUPABASE_URL / '
                         'SUPABASE_SERVICE_ROLE_KEY); pre-written explanations are not read')
        return {}
    problems: list[str] = []
    if len(senses) > MAX_SENSES_PER_CALL:
        problems.append(f'over_cap={len(senses) - MAX_SENSES_PER_CALL}')
        senses = senses[:MAX_SENSES_PER_CALL]

    backend = store.backend()
    lru, neg = _caches(backend)
    found: dict[int, bytes] = {}
    to_fetch: list[int] = []
    for sense in senses:
        data = lru.get(paths[sense])
        if data is not None:
            found[sense] = data
        elif not neg.contains(paths[sense]):
            to_fetch.append(sense)

    if to_fetch:
        executor = _fetch_executor()
        futures: dict[Future, int] = {
            executor.submit(_fetch_one, backend, paths[sense], lru, neg): sense
            for sense in to_fetch}
        budget = _deadline(deadline_s) - (time.monotonic() - started)
        done, not_done = wait(futures, timeout=max(0.0, budget))
        late = [futures[f] for f in not_done]
        for future in not_done:
            future.cancel()
        failed: list[tuple[int, BaseException]] = []
        for future in done:
            sense = futures[future]
            if future.cancelled():
                late.append(sense)
                continue
            exc = future.exception()
            if exc is not None:
                failed.append((sense, exc))
                continue
            data = future.result()
            if data is not None:
                found[sense] = data
        if late:
            problems.append(f'late={len(late)} first={paths[late[0]]}')
        if failed:
            sense, exc = failed[0]
            problems.append(f'failed={len(failed)} first={paths[sense]} '
                            f'{type(exc).__name__}: {exc}')

    out: dict[str, dict] = {}
    bad: list[str] = []
    for sense in senses:
        data = found.get(sense)
        if data is None:
            continue
        path = paths[sense]
        doc, problem = _parse(data)
        if doc is not None and (doc['language_id'], doc['sense_id'], doc['nl_language_id'],
                                doc['prompt_version']) != (language_id, sense, nl_language_id,
                                                           prompt_version):
            doc, problem = None, 'names another sense, language or prompt version'
        if doc is None:
            bad.append(f'{path} ({problem})')
            lru.discard(path)
            neg.add(path)                 # not asked for again until the period ends
            continue
        for exercise_id, entry in doc['exercises'].items():
            out[str(exercise_id)] = entry
    if bad:
        problems.append(f'malformed={len(bad)} ' + ', '.join(bad[:_LOG_PATHS]))
    if problems:
        logger.warning('explanation_files.read senses=%d %s', len(senses), ' '.join(problems))
    return out
