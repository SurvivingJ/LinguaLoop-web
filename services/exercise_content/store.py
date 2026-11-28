"""Exercise content store: the one module callers import (ADR-049 §9).

    from services.exercise_content import store

Exercise ``content`` lives in one immutable JSON file per sense and version in
the private Storage bucket ``exercise-content``
(``{lang_code}/{sense_id}.v{version}.json``, ADR-049 §1-§2); the
``exercises.content`` column was dropped on 2026-11-19. Readers select
``store.select_columns(...)`` (which reads ``content_version`` where the
template says ``{content}``) / pass ``**store.rpc_content_args()`` and call
``store.hydrate(items)`` just before the payload leaves the server; writers call
``store.write_sense(...)`` for every insert into ``exercises`` and every content
change (ADR-049 §4).

There are no modes (TASK-1031 removed the ``db`` / ``shadow`` reads, the ``db``
writes, the DB fallback and their flags). ``hydrate`` reads the files through
``reader.py``; ``write_sense`` writes the file first and then the rows by
compare-and-swap through ``writer.py``. Both are imported lazily.

Storage credentials: the process backend is built from ``SUPABASE_URL`` and
``SUPABASE_SERVICE_ROLE_KEY``. Without them, and without a backend installed
with ``set_backend()`` (tests), ``hydrate`` treats every item that needs content
as missing (one ERROR per process, no network call), ``fetch_sense`` returns
None, and ``write_sense`` raises ``ContentStorageError`` before any call.

Choices made where ADR-049 §9 is silent or ambiguous (TASK-1008)
----------------------------------------------------------------
1. ``write_sense`` validation (``ValueError``, before any call): ``db`` must not
   be None; ``sense_id`` and ``language_id`` must be positive ints;
   ``delete_where`` a ``DeleteWhere`` or None; ``max_retries >= 1``; every
   insert row a dict with a canonical lowercase UUID ``id`` (unique in the
   call), ``word_sense_id`` equal to ``sense_id``, ``language_id`` equal to
   ``language_id`` and a dict ``content``; update ids canonical UUIDs not
   inserted in the same call, with dict values. Ids and sense/language values
   compare as ints when both sides are int-like (``5 == '5'``); bools never
   match.
2. A ``write_sense`` call with nothing to do (no insert rows, no
   ``delete_where``, no updates) makes no call and returns
   ``WriteResult(version=None, attempts=0, ...)``.
3. ``DeleteWhere.ladder_levels`` is normalised to a sorted tuple of unique
   ints (a list or set is accepted; a non-int level raises ``ValueError``).
   An empty tuple is kept and means "no level".
4. ``hydrate`` resolves ``max_senses`` / ``deadline_s`` of ``None`` to
   ``EXERCISE_CONTENT_MAX_SENSES_PER_CALL`` / ``EXERCISE_CONTENT_DEADLINE_S``
   before calling the reader. The reader owns "never raises"; an unexpected
   exception propagates. A ``language_id`` given as a digit string is accepted
   and converted. ``db`` is accepted and ignored (it fed the DB fallback,
   removed in TASK-1031), so callers need no change.
5. ``set_backend()`` also empties the byte and negative caches (their entries
   belong to the previous backend). ``reset_state()`` closes a backend it
   built itself (``close()`` when present), never one a test installed.
6. ``decode_sense_file`` accepts ``bytes`` / ``bytearray`` / ``memoryview`` /
   ``str`` and also rejects (``ContentStorageError``) a document whose
   ``language_id`` is not an int or whose exercise content is not an object.
   ``encode_sense_file`` raises ``ValueError`` for a non-string or empty key,
   a non-dict content or a value ``json.dumps`` cannot encode.

Internal plumbing for reader.py / writer.py / cache.py (not for callers)
-----------------------------------------------------------------------
* ``_setting_int / _setting_float / _setting_str(name, default, ...)`` read
  ``Config`` at call time and fall back to the default (one ERROR) on a bad
  value.
* ``_warn_once(key, level, msg, *args)``: one log line per key per process
  (cleared by ``reset_state()``).
* ``_on_reset(key, fn)``: register (or replace) a hook ``reset_state()`` calls,
  for state a module owns (the reader's executor).
* ``_storage_configured()``: a backend was installed with ``set_backend()``, or
  ``SUPABASE_URL`` and ``SUPABASE_SERVICE_ROLE_KEY`` are set.
* ``_content_cache()`` / ``_negative_cache()``: the process-wide
  ``cache.ByteLRU(EXERCISE_CONTENT_CACHE_MB MiB)`` and
  ``cache.NegativeCache(ttl_s=60.0)`` from TASK-1009, built lazily; ``None``
  while ``services/exercise_content/cache.py`` does not exist. ``reset_state()``
  and ``set_backend()`` drop them.
* ``_cache_key(language_id, sense_id, version)`` -> ``(lang_code, sense_id, version)``,
  the key both caches use (ADR-049 §5).
* ``_lang_code(language_id)``: ``LANGUAGE_CODES`` lookup, ``str(language_id)``
  for an unknown id.
"""

from __future__ import annotations

import importlib
import json
import logging
import math
import threading
import uuid
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from config import Config
from services import language_registry

if TYPE_CHECKING:
    from services.exercise_content.backends import StorageBackend

logger = logging.getLogger('services.exercise_content')

LANGUAGE_CODES = language_registry.id_to_code()   # same map as services/intro_drill.py LANG_CODE
FILE_FORMAT = 1
COMMIT_LOCK_NAMESPACE = 47047

CONTENT_PLACEHOLDER = '{content}'
CONTENT_COLUMNS = 'content_version'     # what select_columns puts where '{content}' was
NEGATIVE_CACHE_TTL_S = 60.0


# ---------------------------------------------------------------------------
# Errors and value types (ADR-049 §9)
# ---------------------------------------------------------------------------

class ExerciseContentError(Exception):
    """Base class of every error this package raises on purpose."""


class ContentStorageError(ExerciseContentError):
    """Write path: backend failure, unusable base file, corrupt file."""


class AlreadyExists(ContentStorageError):
    """``backend.put`` on a path that already exists (files are write-once)."""


class ContentWriteConflict(ExerciseContentError):
    """A write lost the compare-and-swap ``max_retries`` times, or its base was stale."""


@dataclass
class HydrationReport:
    items: int = 0            # items with an id that were considered
    groups: int = 0           # distinct (lang, sense, version) groups
    cache_hits: int = 0
    fetched: int = 0          # groups read from the backend
    over_cap: int = 0         # groups skipped by the per-call cap or deadline
    dropped: int = 0          # items removed (drop_missing=True)
    missing_ids: list[str] = field(default_factory=list)
    elapsed_ms: float = 0.0


@dataclass(frozen=True)
class DeleteWhere:
    require_word_asset: bool = False                  # only rows with word_asset_id IS NOT NULL
    ladder_levels: tuple[int, ...] | None = None      # only rows at these levels (None = any)

    def __post_init__(self) -> None:
        levels = self.ladder_levels
        if levels is None:
            return
        if isinstance(levels, (str, bytes, Mapping)):
            raise ValueError(f'DeleteWhere.ladder_levels must be ints, got {levels!r}')
        try:
            values = list(levels)
        except TypeError:
            raise ValueError(
                f'DeleteWhere.ladder_levels must be a tuple of ints or None, got {levels!r}'
            ) from None
        for level in values:
            if not _is_int(level):
                raise ValueError(f'DeleteWhere.ladder_levels: {level!r} is not an int')
        object.__setattr__(self, 'ladder_levels', tuple(sorted(set(values))))


@dataclass
class WriteResult:
    sense_id: int
    version: int | None       # committed content_version; None when there was nothing to do
    inserted_ids: list[str]
    deleted_count: int
    updated_ids: list[str]
    attempts: int


# ---------------------------------------------------------------------------
# Process state
# ---------------------------------------------------------------------------

_state_lock = threading.RLock()
_backend: StorageBackend | None = None
_backend_override = False               # True while a set_backend() backend is installed
_warned: set = set()
_reset_hooks: dict[str, Callable[[], None]] = {}
_UNAVAILABLE = object()                 # cache.py absent / unusable until reset_state()
_byte_cache: Any = None
_neg_cache: Any = None


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _as_int(value: Any) -> int | None:
    if _is_int(value):
        return value
    if isinstance(value, str):
        text = value.strip()
        if text.isdigit() or (text[:1] in '+-' and text[1:].isdigit()):
            return int(text)
    return None


def _same_id(value: Any, expected: Any) -> bool:
    if isinstance(value, bool) or isinstance(expected, bool):
        return False
    if value == expected:
        return True
    left, right = _as_int(value), _as_int(expected)
    return left is not None and left == right


def _is_canonical_uuid(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        return str(uuid.UUID(value)) == value
    except ValueError:
        return False


def _warn_once(key: Any, level: int, msg: str, *args: Any) -> bool:
    """Log ``msg`` once per ``key`` per process (until ``reset_state()``)."""
    with _state_lock:
        if key in _warned:
            return False
        _warned.add(key)
    logger.log(level, msg, *args)
    return True


def _on_reset(key: str, hook: Callable[[], None]) -> None:
    """Register (or replace, by ``key``) a hook that ``reset_state()`` calls."""
    with _state_lock:
        _reset_hooks[key] = hook


def _bad_setting(name: str, value: Any, default: Any) -> Any:
    _warn_once(('setting', name, repr(value)), logging.ERROR,
               'exercise_content.config %s=%r is invalid; using %r', name, value, default)
    return default


def _setting_int(name: str, default: int, *, minimum: int = 0) -> int:
    value = getattr(Config, name, default)
    parsed = _as_int(value)
    if parsed is not None and parsed >= minimum:
        return parsed
    return _bad_setting(name, value, default)


def _setting_float(name: str, default: float, *, low: float = 0.0, high: float = math.inf,
                   low_inclusive: bool = True) -> float:
    value = getattr(Config, name, default)
    parsed: float | None = None
    if _is_int(value) or isinstance(value, float):
        parsed = float(value)
    elif isinstance(value, str):
        try:
            parsed = float(value.strip())
        except ValueError:
            parsed = None
    if parsed is not None and math.isfinite(parsed) and parsed <= high and (
            parsed >= low if low_inclusive else parsed > low):
        return parsed
    return _bad_setting(name, value, default)


def _setting_str(name: str, default: str) -> str:
    value = getattr(Config, name, default)
    if isinstance(value, str) and value.strip():
        return value.strip()
    if value is None or (isinstance(value, str) and not value.strip()):
        return default
    return _bad_setting(name, value, default)


def _lang_code(language_id: Any) -> str:
    return LANGUAGE_CODES.get(language_id, str(language_id))


def _cache_key(language_id: int, sense_id: int, version: int) -> tuple[str, int, int]:
    """Key of the byte LRU and the negative cache: ``(lang_code, sense_id, version)``."""
    return (_lang_code(language_id), sense_id, version)


def _cache_module():
    name = 'services.exercise_content.cache'
    try:
        return importlib.import_module(name)
    except ModuleNotFoundError as exc:
        if exc.name == name:
            return None
        logger.exception('exercise_content.cache import failed')
        return None
    except Exception:
        logger.exception('exercise_content.cache import failed')
        return None


def _build_cache(factory_name: str, build: Callable[[Any], Any]) -> Any:
    module = _cache_module()
    if module is None or not hasattr(module, factory_name):
        return _UNAVAILABLE
    try:
        return build(module)
    except Exception:
        logger.exception('exercise_content.cache %s could not be built', factory_name)
        return _UNAVAILABLE


def _content_cache():
    """The process-wide byte LRU (``cache.ByteLRU``), or None without cache.py."""
    global _byte_cache
    current = _byte_cache
    if current is None:
        with _state_lock:
            if _byte_cache is None:
                megabytes = _setting_int('EXERCISE_CONTENT_CACHE_MB', 32, minimum=0)
                _byte_cache = _build_cache(
                    'ByteLRU', lambda module: module.ByteLRU(megabytes * 1024 * 1024))
            current = _byte_cache
    return None if current is _UNAVAILABLE else current


def _negative_cache():
    """The process-wide negative cache (``cache.NegativeCache``), or None without cache.py."""
    global _neg_cache
    current = _neg_cache
    if current is None:
        with _state_lock:
            if _neg_cache is None:
                _neg_cache = _build_cache(
                    'NegativeCache',
                    lambda module: module.NegativeCache(ttl_s=NEGATIVE_CACHE_TTL_S))
            current = _neg_cache
    return None if current is _UNAVAILABLE else current


# ---------------------------------------------------------------------------
# Storage credentials, select list and RPC arguments
# ---------------------------------------------------------------------------

def _credentials_present() -> bool:
    url = getattr(Config, 'SUPABASE_URL', None)
    key = getattr(Config, 'SUPABASE_SERVICE_ROLE_KEY', None)
    return bool(url and str(url).strip()) and bool(key and str(key).strip())


def _storage_configured() -> bool:
    """A backend installed with ``set_backend()``, or the Storage credentials."""
    return _backend_override or _credentials_present()


def _log_not_configured() -> None:
    _warn_once(('no_credentials',), logging.ERROR,
               'exercise_content.config SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are not '
               'set: exercise content cannot be read or written (items needing content are '
               'treated as missing)')


def select_columns(template: str) -> str:
    """PostgREST select list. `template` contains the literal '{content}' exactly once
    (ValueError otherwise); it becomes 'content_version' (exercises.content is gone).
    Rows to be hydrated must also select id and word_sense_id (or the caller sets them)."""
    if not isinstance(template, str):
        raise ValueError(f'select_columns: template must be a str, got {type(template).__name__}')
    count = template.count(CONTENT_PLACEHOLDER)
    if count != 1:
        raise ValueError(
            f"select_columns: template must contain '{CONTENT_PLACEHOLDER}' exactly once "
            f'(found {count}): {template!r}')
    return template.replace(CONTENT_PLACEHOLDER, CONTENT_COLUMNS)


def rpc_content_args() -> dict:
    """Extra args for get_practice_session / get_review_ahead_items: always
    {'p_include_content': False} (the live functions accept and ignore it; items carry
    content_version and are hydrated from the files)."""
    return {'p_include_content': False}


# ---------------------------------------------------------------------------
# Read path
# ---------------------------------------------------------------------------

def _language_arg(language_id: Any) -> int | None:
    if language_id is None:
        return None
    parsed = _as_int(language_id)
    if parsed is None:
        raise ValueError(f'hydrate: language_id must be an int or None, got {language_id!r}')
    return parsed


def hydrate(items: list[dict], *, language_id: int | None = None, id_key: str = 'id',
            sense_key: str = 'word_sense_id', drop_missing: bool = True,
            max_senses: int | None = None, deadline_s: float | None = None) -> HydrationReport:
    """Fill item['content'] in place from the content files.
    - Considers dicts with a truthy item[id_key]; others (DT error cards, gate/stress markers) are untouched.
    - Items whose 'content' is already non-None are skipped; the rest are grouped by
      (language, item[sense_key], item['content_version']); language = language_id or item['language_id'].
      Cache -> negative cache -> parallel backend GETs (own pool, per-call cap, deadline) ->
      drop (drop_missing=True; list mutated in place, order kept) or content=None.
      Every item receives an object shared with nothing else (one json parse per group per call;
      a repeated id in one call gets a deepcopy).
    - Without Storage credentials (and no set_backend() backend) every item that needs content
      is missing; one ERROR per process.
    - Never raises for storage or network problems; raises ValueError only for a bad argument."""
    if not isinstance(items, list):
        raise ValueError(f'hydrate: items must be a list, got {type(items).__name__}')
    for name, key in (('id_key', id_key), ('sense_key', sense_key)):
        if not isinstance(key, str) or not key:
            raise ValueError(f'hydrate: {name} must be a non-empty str, got {key!r}')
    language_id = _language_arg(language_id)
    if max_senses is not None and (not _is_int(max_senses) or max_senses < 0):
        raise ValueError(f'hydrate: max_senses must be an int >= 0 or None, got {max_senses!r}')
    if deadline_s is not None and (
            isinstance(deadline_s, bool) or not isinstance(deadline_s, (int, float))
            or not math.isfinite(deadline_s) or deadline_s <= 0):
        raise ValueError(f'hydrate: deadline_s must be a number > 0 or None, got {deadline_s!r}')

    if max_senses is None:
        max_senses = _setting_int('EXERCISE_CONTENT_MAX_SENSES_PER_CALL', 160, minimum=0)
    if deadline_s is None:
        deadline_s = _setting_float('EXERCISE_CONTENT_DEADLINE_S', 3.0, low=0.0,
                                    low_inclusive=False)
    from services.exercise_content import reader
    return reader.hydrate(items, language_id=language_id, id_key=id_key, sense_key=sense_key,
                          drop_missing=drop_missing, max_senses=max_senses,
                          deadline_s=float(deadline_s))


def fetch_sense(language_id: int, sense_id: int, version: int) -> dict[str, dict] | None:
    """exercise_id -> content of one file (fresh objects), via the cache. None when missing,
    unreadable or corrupt (logged), or without Storage credentials. Never raises."""
    from services.exercise_content import reader
    return reader.fetch_sense(language_id, sense_id, version)


# ---------------------------------------------------------------------------
# Write path
# ---------------------------------------------------------------------------

def _validate_write(db, sense_id, language_id, insert_rows, delete_where, update_contents,
                    max_retries) -> tuple[list[dict], dict[str, dict]]:
    if db is None:
        raise ValueError('write_sense: db is required')
    for name, value in (('sense_id', sense_id), ('language_id', language_id)):
        if not _is_int(value) or value <= 0:
            raise ValueError(f'write_sense: {name} must be a positive int, got {value!r}')
    if not _is_int(max_retries) or max_retries < 1:
        raise ValueError(f'write_sense: max_retries must be an int >= 1, got {max_retries!r}')
    if delete_where is not None and not isinstance(delete_where, DeleteWhere):
        raise ValueError(
            f'write_sense: delete_where must be a DeleteWhere or None, got {delete_where!r}')

    if insert_rows is None or isinstance(insert_rows, (str, bytes, Mapping)):
        raise ValueError('write_sense: insert_rows must be a sequence of row dicts')
    try:
        rows = list(insert_rows)
    except TypeError:
        raise ValueError('write_sense: insert_rows must be a sequence of row dicts') from None
    seen_ids: set[str] = set()
    for index, row in enumerate(rows):
        where = f'write_sense: insert_rows[{index}]'
        if not isinstance(row, dict):
            raise ValueError(f'{where} is not a dict')
        if not _same_id(row.get('word_sense_id'), sense_id):
            raise ValueError(
                f"{where}: word_sense_id {row.get('word_sense_id')!r} != sense_id {sense_id!r}")
        if not _same_id(row.get('language_id'), language_id):
            raise ValueError(
                f"{where}: language_id {row.get('language_id')!r} != language_id {language_id!r}")
        if not isinstance(row.get('content'), dict):
            raise ValueError(f"{where}: content must be a dict")
        row_id = row.get('id')
        if not _is_canonical_uuid(row_id):
            raise ValueError(f'{where}: id must be a canonical lowercase UUID str, got {row_id!r}')
        if row_id in seen_ids:
            raise ValueError(f'{where}: duplicate id {row_id}')
        seen_ids.add(row_id)

    updates: dict[str, dict] = {}
    if update_contents is not None:
        if not isinstance(update_contents, Mapping):
            raise ValueError('write_sense: update_contents must be a mapping of id -> content dict')
        for exercise_id, content in update_contents.items():
            if not isinstance(exercise_id, str) or not exercise_id:
                raise ValueError(f'write_sense: update id {exercise_id!r} is not a non-empty str')
            if not _is_canonical_uuid(exercise_id):
                raise ValueError(
                    f'write_sense: update id {exercise_id!r} is not a canonical lowercase UUID')
            if exercise_id in seen_ids:
                raise ValueError(
                    f'write_sense: update id {exercise_id} is also inserted in this call')
            if not isinstance(content, dict):
                raise ValueError(f'write_sense: update content for {exercise_id} must be a dict')
            updates[exercise_id] = content
    return rows, updates


def base_version(rows: Sequence[dict]) -> int | None:
    """The content version ``rows`` (one sense's rows, as read and hydrated) were read at:
    the highest ``content_version``, or None when any row lacks one (the caller did not
    select it). Pass it to ``write_sense(expected_version=...)`` for a read-modify-write."""
    versions = [_as_int(row.get('content_version')) if isinstance(row, dict) else None
                for row in rows]
    if not versions or any(v is None or v < 0 for v in versions):
        return None
    return max(versions)


def write_sense(db, sense_id: int, language_id: int, *, insert_rows: Sequence[dict] = (),
                delete_where: DeleteWhere | None = None,
                update_contents: Mapping[str, dict] | None = None,
                max_retries: int = 3, expected_version: int | None = None) -> WriteResult:
    """Validates first (ValueError, no I/O): every insert row has 'id' (uuid str),
    word_sense_id == sense_id, language_id == language_id and a dict 'content'.
    Then ADR-049 Decision 4 (writer.py): exercise_content_begin, the new file (the surviving
    rows' content from file V, then the updates and inserts) uploaded first, then
    exercise_content_commit by compare-and-swap, retried up to max_retries times on a lost
    race. update ids must belong to the sense and not be deleted (ValueError).
    expected_version (read-modify-write callers, e.g. ``base_version(rows)``): the write is
    refused with ContentWriteConflict, before any upload or row change and without a retry,
    when the sense is no longer at that version, i.e. someone wrote it after the caller read
    the content it edited. None: no check.
    Without Storage credentials (and no set_backend() backend): ContentStorageError, no call.
    Errors: ValueError; ContentWriteConflict; ContentStorageError; PostgREST APIError propagates.

    See the module docstring (choices 1-3) for what is validated and the nothing-to-do case."""
    rows, updates = _validate_write(db, sense_id, language_id, insert_rows, delete_where,
                                    update_contents, max_retries)
    if expected_version is not None and (not _is_int(expected_version) or expected_version < 0):
        raise ValueError(f'write_sense: expected_version must be an int >= 0 or None, '
                         f'got {expected_version!r}')
    if not rows and delete_where is None and not updates:
        return WriteResult(sense_id=sense_id, version=None, inserted_ids=[],
                           deleted_count=0, updated_ids=[], attempts=0)
    if not _storage_configured():
        _log_not_configured()
        raise ContentStorageError(
            f'sense {sense_id}: exercise content storage needs SUPABASE_URL and '
            f'SUPABASE_SERVICE_ROLE_KEY; nothing was written')
    from services.exercise_content import writer
    return writer.write_sense(db, sense_id, language_id, insert_rows=rows,
                              delete_where=delete_where, update_contents=updates,
                              max_retries=max_retries, expected_version=expected_version)


# ---------------------------------------------------------------------------
# Codec (pure; used by the sweep and tests)
# ---------------------------------------------------------------------------

def _check_non_negative_ints(where: str, **values: Any) -> None:
    for name, value in values.items():
        if not _is_int(value) or value < 0:
            raise ValueError(f'{where}: {name} must be an int >= 0, got {value!r}')


def content_path(language_id: int, sense_id: int, version: int) -> str:
    """'zh/123.v0.json'; an unknown language id is used as its own folder ('9/...')."""
    _check_non_negative_ints('content_path', language_id=language_id, sense_id=sense_id,
                             version=version)
    return f'{_lang_code(language_id)}/{sense_id}.v{version}.json'


def canonical(content) -> str:
    """json.dumps(sort_keys=True, ensure_ascii=False, separators=(',', ':'))."""
    return json.dumps(content, sort_keys=True, ensure_ascii=False, separators=(',', ':'))


def encode_sense_file(sense_id: int, language_id: int, version: int,
                      exercises: Mapping[str, dict]) -> bytes:
    """The ADR-049 §2 document as UTF-8 bytes:
    {"exercises": {<id>: <content>}, "format": 1, "language_id": L, "sense_id": S, "version": V}."""
    _check_non_negative_ints('encode_sense_file', sense_id=sense_id, language_id=language_id,
                             version=version)
    if not isinstance(exercises, Mapping):
        raise ValueError('encode_sense_file: exercises must be a mapping of id -> content dict')
    body: dict[str, dict] = {}
    for exercise_id, content in exercises.items():
        if not isinstance(exercise_id, str) or not exercise_id:
            raise ValueError(f'encode_sense_file: exercise id {exercise_id!r} is not a non-empty str')
        if not isinstance(content, dict):
            raise ValueError(f'encode_sense_file: content of {exercise_id} is not a dict')
        body[exercise_id] = content
    doc = {'format': FILE_FORMAT, 'sense_id': sense_id, 'language_id': language_id,
           'version': version, 'exercises': body}
    try:
        text = json.dumps(doc, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    except (TypeError, ValueError) as exc:
        raise ValueError(f'encode_sense_file: content is not JSON-serialisable: {exc}') from exc
    return text.encode('utf-8')


def decode_sense_file(data: bytes, *, sense_id: int, version: int) -> dict[str, dict]:
    """exercise_id -> content (fresh objects). ContentStorageError on mismatch/corrupt."""
    _check_non_negative_ints('decode_sense_file', sense_id=sense_id, version=version)
    where = f'exercise content file for sense {sense_id} v{version}'
    if isinstance(data, str):
        text = data
    elif isinstance(data, (bytes, bytearray, memoryview)):
        try:
            text = bytes(data).decode('utf-8')
        except UnicodeDecodeError as exc:
            raise ContentStorageError(f'{where} is not UTF-8') from exc
    else:
        raise ContentStorageError(f'{where}: expected bytes, got {type(data).__name__}')
    try:
        doc = json.loads(text)
    except ValueError as exc:
        raise ContentStorageError(f'{where} is not valid JSON: {exc}') from exc
    if not isinstance(doc, dict):
        raise ContentStorageError(f'{where} is not a JSON object')
    fmt = doc.get('format')
    if not _is_int(fmt) or fmt != FILE_FORMAT:
        raise ContentStorageError(f'{where} has unsupported format {fmt!r}')
    if not _is_int(doc.get('sense_id')) or doc['sense_id'] != sense_id:
        raise ContentStorageError(f"{where} names sense {doc.get('sense_id')!r}")
    if not _is_int(doc.get('version')) or doc['version'] != version:
        raise ContentStorageError(f"{where} names version {doc.get('version')!r}")
    if not _is_int(doc.get('language_id')):
        raise ContentStorageError(f"{where} has language_id {doc.get('language_id')!r}")
    exercises = doc.get('exercises')
    if not isinstance(exercises, dict):
        raise ContentStorageError(f'{where} has no exercises object')
    for exercise_id, content in exercises.items():
        if not isinstance(content, dict):
            raise ContentStorageError(f'{where}: content of {exercise_id} is not an object')
    return exercises


# ---------------------------------------------------------------------------
# Backend singleton and process state
# ---------------------------------------------------------------------------

def backend() -> 'StorageBackend':
    """Process singleton: ``SupabaseStorageBackend.from_config()`` (no I/O on construction),
    or the backend installed with ``set_backend()``."""
    global _backend
    current = _backend
    if current is not None:
        return current
    with _state_lock:
        if _backend is None:
            from services.exercise_content.backends import SupabaseStorageBackend
            _backend = SupabaseStorageBackend.from_config()
        return _backend


def _close_quietly(old: Any) -> None:
    close = getattr(old, 'close', None)
    if callable(close):
        try:
            close()
        except Exception:
            logger.debug('exercise_content: closing the previous backend failed', exc_info=True)


def set_backend(b: 'StorageBackend | None') -> None:
    """Install ``b`` as the process backend (tests); None = rebuild from Config on next use.
    Also empties the byte and negative caches."""
    global _backend, _backend_override, _byte_cache, _neg_cache
    with _state_lock:
        old, old_was_override = _backend, _backend_override
        _backend = b
        _backend_override = b is not None
        _byte_cache = None
        _neg_cache = None
    if old is not None and old is not b and not old_was_override:
        _close_quietly(old)


def reset_state() -> None:
    """Clears cache, negative cache, backend, warn-once flags and, through the hooks
    registered with ``_on_reset``, the reader's fetch pool."""
    global _backend, _backend_override, _byte_cache, _neg_cache
    with _state_lock:
        old, old_was_override = _backend, _backend_override
        _backend = None
        _backend_override = False
        _byte_cache = None
        _neg_cache = None
        _warned.clear()
        hooks = list(_reset_hooks.items())
    if old is not None and not old_was_override:
        _close_quietly(old)
    for key, hook in hooks:
        try:
            hook()
        except Exception:
            logger.exception('exercise_content.reset hook %s failed', key)
