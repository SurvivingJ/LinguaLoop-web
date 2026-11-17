"""``dual`` write path behind ``store.write_sense`` (ADR-047 §4, §8, §9). TASK-979.

``store`` imports this module lazily, only when ``write_mode() == 'dual'``.

Contract with ``store``: ``store.write_sense`` has already

* validated the arguments without I/O in strict mode: ``sense_id`` and
  ``language_id`` are positive ints; every insert row is a dict with a
  canonical lowercase UUID ``id`` (unique in the call), ``word_sense_id`` equal
  to ``sense_id`` (int-like), ``language_id`` equal to ``language_id`` and a
  dict ``content``; every update id is a canonical UUID not inserted in the same
  call, with a dict value; ``max_retries >= 1``;
* normalised the arguments: ``insert_rows`` is a ``list``, ``delete_where`` a
  ``store.DeleteWhere`` (levels a sorted tuple of unique ints) or None,
  ``update_contents`` a ``dict`` (possibly empty);
* returned early, without calling this module, when there is nothing to do.

One attempt (ADR-047 §4), repeated up to ``max_retries`` times:

1. ``exercise_content_begin(p_sense_id)`` -> current version ``V``, a fresh
   version ``N`` and the sense's rows (ids + metadata).
2. Checks against those rows (``ValueError``, nothing uploaded): every update
   id belongs to the sense and is not deleted by ``delete_where``; no insert id
   is already a surviving row of the sense; every row's ``language_id`` equals
   ``language_id`` (the file folder is chosen from it).
3. The new file: the content of every surviving row that is not updated, read
   from file ``V`` (``store.backend().get`` + ``store.decode_sense_file``);
   ids missing from it (or every id, when there is no file ``V``) come from one
   ``select('id, content').in_('id', ...)`` per 200 ids on ``exercises``; an id
   still missing raises ``ContentStorageError`` (no upload, no commit). Then
   the updates and the inserted rows' content.
4. Upload ``{lang}/{sense}.v{N}.json`` (never overwrites). ``AlreadyExists`` ->
   ``ContentStorageError`` (unique sequence numbers make it impossible); any
   other backend failure -> ``ContentStorageError``.
5. ``exercise_content_commit(...)`` with sorted id arrays, the insert rows as
   given (JSON-safe; content included, so the column is still written before
   the drop and the RPC computes ``dedupe_key`` from it) and the updates
   ``{id: content}``. ``ok`` -> the file's bytes go into the read cache (when
   ``cache.py`` is present) and one INFO
   ``exercise_content.write sense=… version=… attempts=… inserted=… deleted=… updated=…``.
   ``version_conflict`` / ``rows_changed`` -> the writer deletes its own file
   (best effort) and retries from step 1 after a short jittered pause. If the
   commit call itself raises, the file is left for the sweep and the
   exception propagates.

After ``max_retries`` lost races: ``ContentWriteConflict`` (no rows were
changed by this writer). A call whose deletes match no row and that inserts
and updates nothing commits nothing and returns the current version. A call
that leaves the sense with no rows (e.g. ``DeleteWhere()`` and no inserts)
commits without uploading a file: no row will ever point at it.

Errors: ``ValueError`` (bad input, including rows that are not JSON-safe);
``ContentWriteConflict``; ``ContentStorageError`` (backend failure, missing
or corrupt base content); ``ExerciseContentError`` for an RPC response that
breaks the ADR-047 §8 contract; PostgREST errors from the RPCs propagate.
"""

from __future__ import annotations

import json
import logging
import random
import time
from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, Any

from services.exercise_content import store
from services.exercise_content.store import (
    AlreadyExists, ContentStorageError, ContentWriteConflict, ExerciseContentError, WriteResult,
)

if TYPE_CHECKING:
    from services.exercise_content.store import DeleteWhere

logger = logging.getLogger('services.exercise_content')

BEGIN_RPC = 'exercise_content_begin'
COMMIT_RPC = 'exercise_content_commit'
CONFLICT_REASONS = ('version_conflict', 'rows_changed')
BASE_SELECT_CHUNK = 200
MISSING_COLUMN_CODES = ('42703', 'PGRST204')
RETRY_BACKOFF_S = 0.02        # upper bound of the jittered pause per attempt number


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _check_json_safe(rows: list[dict], updates: dict[str, dict]) -> None:
    """The RPC params are sent as JSON: reject what PostgREST would reject, before any I/O."""
    for what, value in (('insert_rows', rows), ('update_contents', updates)):
        try:
            json.dumps(value, allow_nan=False)
        except (TypeError, ValueError) as exc:
            raise ValueError(f'write_sense: {what} must be JSON-serialisable: {exc}') from None


def _rpc(db, name: str, params: dict) -> dict:
    data = db.rpc(name, params).execute().data
    if isinstance(data, list) and len(data) == 1 and isinstance(data[0], dict):
        data = data[0]
    if not isinstance(data, dict):
        raise ExerciseContentError(f'{name} returned {type(data).__name__}, expected a JSON object')
    return data


def _begin(db, sense_id: int) -> tuple[int, int, list[dict]]:
    data = _rpc(db, BEGIN_RPC, {'p_sense_id': sense_id})
    current, new, rows = data.get('current_version'), data.get('new_version'), data.get('rows')
    if not store._is_int(current) or current < 0 or not store._is_int(new) \
            or not isinstance(rows, list):
        raise ExerciseContentError(f'{BEGIN_RPC}({sense_id}) returned a malformed response: '
                                   f'{str(data)[:200]}')
    if 'sense_id' in data and not store._same_id(data['sense_id'], sense_id):
        raise ExerciseContentError(f'{BEGIN_RPC}({sense_id}) answered for sense {data["sense_id"]!r}')
    if new <= current:
        raise ExerciseContentError(
            f'{BEGIN_RPC}({sense_id}): new_version {new} is not above current_version {current}; '
            f'exercise_content_version_seq is behind the data')
    clean = []
    for row in rows:
        if not isinstance(row, dict) or not row.get('id'):
            raise ExerciseContentError(f'{BEGIN_RPC}({sense_id}) returned a row without an id')
        clean.append({**row, 'id': str(row['id'])})
    return current, new, clean


def _matching_ids(rows: list[dict], where: DeleteWhere | None) -> list[str]:
    """Ids of ``rows`` the db-mode delete chain would remove (ADR-047 §9 ``DeleteWhere``)."""
    if where is None:
        return []
    levels = where.ladder_levels
    ids = []
    for row in rows:
        if where.require_word_asset and row.get('word_asset_id') is None:
            continue
        if levels is not None and store._as_int(row.get('ladder_level')) not in levels:
            continue
        ids.append(row['id'])
    return sorted(ids)


def _check_against_rows(sense_id: int, language_id: int, rows: list[dict], delete_ids: list[str],
                        insert_ids: list[str], updates: Mapping[str, dict]) -> None:
    in_sense = {row['id'] for row in rows}
    deleted = set(delete_ids)
    for exercise_id in updates:
        if exercise_id not in in_sense:
            raise ValueError(f'write_sense: update id {exercise_id} is not a row of sense {sense_id}')
        if exercise_id in deleted:
            raise ValueError(f'write_sense: update id {exercise_id} is deleted by delete_where')
    for exercise_id in insert_ids:
        if exercise_id in in_sense and exercise_id not in deleted:
            raise ValueError(f'write_sense: insert id {exercise_id} already exists in sense {sense_id}')
    for row in rows:
        row_language = row.get('language_id')
        if row_language is not None and not store._same_id(row_language, language_id):
            raise ValueError(f'write_sense: sense {sense_id} has rows in language {row_language!r}, '
                             f'not {language_id}')


def _is_missing_column(exc: BaseException) -> bool:
    codes = set(MISSING_COLUMN_CODES)
    if str(getattr(exc, 'code', '')) in codes:
        return True
    return any(isinstance(arg, dict) and str(arg.get('code', '')) in codes
               for arg in getattr(exc, 'args', ()))


def _read_base_file(backend, sense_id: int, language_id: int, version: int) -> dict[str, dict]:
    path = store.content_path(language_id, sense_id, version)
    try:
        data = backend.get(path)
    except ExerciseContentError:
        raise
    except Exception as exc:
        raise ContentStorageError(f'reading base file {path} failed: {type(exc).__name__}: '
                                  f'{exc}') from exc
    if data is None:
        return {}
    return store.decode_sense_file(data, sense_id=sense_id, version=version)


def _base_contents(db, backend, sense_id: int, language_id: int, version: int,
                   needed: list[str]) -> dict[str, dict]:
    """Current content of ``needed`` ids: file ``version``, then ``exercises.content``."""
    if not needed:
        return {}
    in_file = _read_base_file(backend, sense_id, language_id, version)
    found = {exercise_id: in_file[exercise_id] for exercise_id in needed if exercise_id in in_file}
    missing = [exercise_id for exercise_id in needed if exercise_id not in found]
    for start in range(0, len(missing), BASE_SELECT_CHUNK):
        chunk = missing[start:start + BASE_SELECT_CHUNK]
        try:
            response = db.table('exercises').select('id, content').in_('id', chunk).execute()
        except Exception as exc:
            if _is_missing_column(exc):
                break                  # after the column drop the file is the only source
            raise
        for row in getattr(response, 'data', None) or []:
            if isinstance(row, dict) and isinstance(row.get('content'), dict):
                found[str(row.get('id'))] = row['content']
    still = [exercise_id for exercise_id in needed if exercise_id not in found]
    if still:
        raise ContentStorageError(
            f'sense {sense_id}: no content for {len(still)} surviving exercise(s) in file '
            f'v{version} or exercises.content (first: {still[0]}); nothing was written')
    return found


def _upload(backend, path: str, data: bytes) -> None:
    try:
        backend.put(path, data)
    except AlreadyExists as exc:
        raise ContentStorageError(
            f'{path} already exists: content versions must be unique '
            f'(exercise_content_version_seq handed out a used number)') from exc
    except ExerciseContentError:
        raise
    except Exception as exc:
        raise ContentStorageError(f'upload of {path} failed: {type(exc).__name__}: {exc}') from exc


def _delete_quietly(backend, path: str) -> None:
    try:
        backend.delete([path])
    except Exception as exc:
        logger.warning('exercise_content.orphan_file path=%s (delete after a lost race failed: '
                       '%s: %s; the sweep removes it)', path, type(exc).__name__, exc)


def _warm_cache(language_id: int, sense_id: int, version: int, data: bytes) -> None:
    try:
        lru = store._content_cache()
        if lru is not None:
            lru.put(store._cache_key(language_id, sense_id, version), data)
    except Exception:
        logger.debug('exercise_content: warming the read cache failed', exc_info=True)


# ---------------------------------------------------------------------------
# entry point
# ---------------------------------------------------------------------------

def write_sense_dual(db, sense_id: int, language_id: int, *, insert_rows: Sequence[dict],
                     delete_where: DeleteWhere | None, update_contents: Mapping[str, dict],
                     max_retries: int, expected_version: int | None = None) -> WriteResult:
    """File first, then the rows by compare-and-swap (ADR-047 §4).

    ``expected_version``: the version the caller read the content it edited at. When begin
    reports another version, the caller's base is stale; retrying here would only rewrite the
    stale edit, so ContentWriteConflict is raised at once, before any upload."""
    rows = list(insert_rows)
    updates = {exercise_id: update_contents[exercise_id]
               for exercise_id in sorted(update_contents or {})}
    _check_json_safe(rows, updates)
    insert_ids = [str(row['id']) for row in rows]
    insert_contents = {str(row['id']): row['content'] for row in rows}
    backend = store.backend()

    attempts = 0
    reason: Any = None
    while attempts < max_retries:
        if attempts:
            time.sleep(random.uniform(0.0, RETRY_BACKOFF_S * attempts))
        attempts += 1
        current, new, current_rows = _begin(db, sense_id)
        if expected_version is not None and current != expected_version:
            logger.info('exercise_content.write_stale sense=%s expected_version=%s '
                        'current_version=%s attempt=%d', sense_id, expected_version, current,
                        attempts)
            raise ContentWriteConflict(
                f'sense {sense_id}: written by someone else since it was read (read at version '
                f'{expected_version}, now at {current}); re-read the sense and apply the change '
                f'again. No rows were changed by this write.')
        current_ids = sorted(row['id'] for row in current_rows)
        delete_ids = _matching_ids(current_rows, delete_where)
        _check_against_rows(sense_id, language_id, current_rows, delete_ids, insert_ids, updates)
        if not delete_ids and not rows and not updates:
            logger.info('exercise_content.write sense=%s version=%s attempts=%d inserted=0 '
                        'deleted=0 updated=0 (nothing matched; no new version)',
                        sense_id, current, attempts)
            return WriteResult(sense_id=sense_id, mode='dual', version=current, inserted_ids=[],
                               deleted_count=0, updated_ids=[], attempts=attempts)

        deleted = set(delete_ids)
        needed = [exercise_id for exercise_id in current_ids
                  if exercise_id not in deleted and exercise_id not in updates]
        exercises = _base_contents(db, backend, sense_id, language_id, current, needed)
        exercises.update(updates)
        exercises.update(insert_contents)
        data = store.encode_sense_file(sense_id, language_id, new, exercises)
        path = store.content_path(language_id, sense_id, new)
        uploaded = bool(exercises)     # no row survives: no reader will ever ask for file N
        if uploaded:
            _upload(backend, path, data)

        params = {
            'p_sense_id': sense_id,
            'p_expected_version': current,
            'p_expected_ids': current_ids,
            'p_new_version': new,
            'p_delete_ids': delete_ids,
            'p_insert_rows': rows,
            'p_update_contents': updates,
        }
        try:
            result = _rpc(db, COMMIT_RPC, params)
        except Exception as exc:
            logger.error('exercise_content.commit_failed sense=%s version=%s path=%s %s: %s '
                         '(file left for the sweep)', sense_id, new, path,
                         type(exc).__name__, exc)
            raise

        if result.get('ok') is True:
            if uploaded:
                _warm_cache(language_id, sense_id, new, data)
            deleted_count = result.get('deleted')
            if not store._is_int(deleted_count):
                deleted_count = len(delete_ids)
            logger.info('exercise_content.write sense=%s version=%s attempts=%d inserted=%d '
                        'deleted=%d updated=%d', sense_id, new, attempts, len(rows),
                        deleted_count, len(updates))
            return WriteResult(sense_id=sense_id, mode='dual', version=new,
                               inserted_ids=insert_ids, deleted_count=deleted_count,
                               updated_ids=list(updates), attempts=attempts)

        reason = result.get('reason')
        if result.get('ok') is False and reason in CONFLICT_REASONS:
            logger.info('exercise_content.write_conflict sense=%s attempt=%d reason=%s '
                        'expected_version=%s current_version=%s', sense_id, attempts, reason,
                        current, result.get('current_version'))
            if uploaded:
                _delete_quietly(backend, path)
            continue
        raise ExerciseContentError(f'{COMMIT_RPC}({sense_id}) returned a malformed response: '
                                   f'{str(result)[:200]} (file {path} left for the sweep)')

    raise ContentWriteConflict(
        f'sense {sense_id}: lost the content compare-and-swap {attempts} time(s) '
        f'(last: {reason}); no rows were changed by this write')
