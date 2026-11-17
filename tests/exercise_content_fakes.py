"""Shared fakes for the ADR-049 exercise-content tests (TASK-1011; used by TASK-1025).

``FakeContentDB`` emulates, in memory, the slice of Supabase the exercise
content store talks to:

* ``rpc(name, params).execute().data`` for the three write-side RPCs of
  ADR-049 §8 — ``exercise_content_begin``, ``exercise_content_commit`` (the
  version / row-id-set compare-and-swap, deletes -> inserts -> content
  updates -> version stamp, all or nothing) and
  ``exercise_content_live_versions`` — plus any handler a test registers in
  ``rpc_handlers`` (``fn(db, params) -> data``).
* ``table('exercises')`` with ``select / insert / update / delete`` and the
  filters ``eq / neq / in_ / is_ / gt / gte / lt / lte`` (``not_`` negates the
  next one), ``order / range / limit``, ``execute()``. Other table names are
  schemaless lists of dicts (``db.tables[name]``) for integration fixtures.
* ``has_content_column``: ``False`` emulates the database after the cut-over
  migration (``exercises.content`` dropped): selecting ``content`` raises
  code ``42703``, writing it raises ``PGRST204``, ``*`` omits it, and the
  commit RPC no longer stores content (``dedupe_key`` is still computed from
  the JSON passed in).

Errors are raised as ``FakeDBError`` (a ``ValueError`` carrying a PostgreSQL /
PostgREST ``code``): ``22023`` for bad commit input (ADR-049 §8), ``23505`` for
a duplicate id or a duplicate context-free variant
(``uq_exercises_context_free_variant``; ``enforce_unique=False`` turns that
check off), ``42703`` / ``PGRST204`` for the dropped column.

Concurrency: every call runs under one lock (the advisory lock of the real
commit serialises per sense; a global lock is stricter and enough here).
Hooks run before the lock is taken, so a hook can inject a concurrent change:

    db.on('before:exercise_content_commit', lambda db, params: ...)   # once by default
    db.on('after:exercise_content_begin', fn, once=False)
    db.on('before:exercises.insert', fn)        # table events: '<when>:<table>.<op>'

Every call is recorded in ``db.calls`` (``FakeCall``); ``rpc_calls(name)`` and
``table_calls(op)`` filter them.
"""

from __future__ import annotations

import copy
import hashlib
import json
import threading
import uuid
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from services.exercise_content.backends import InMemoryBackend

__all__ = ['FakeContentDB', 'FakeDBError', 'FakeCall', 'FakeResponse', 'InMemoryBackend',
           'CONTEXT_FREE_TYPES', 'dedupe_key_for', 'EXERCISE_COLUMNS']

# The 8 types of uq_exercises_context_free_variant (migrations/task743_context_free_exercise_caps.sql)
CONTEXT_FREE_TYPES = frozenset({
    'tone_id_word', 'hanzi_to_pinyin', 'pinyin_to_hanzi',
    'kanji_to_reading', 'reading_to_kanji', 'phonetic_recognition',
    'classifier_match', 'counter_match',
})

# Columns and defaults of public.exercises (wiki/database/schema.tech.md + ADR-049 §7).
EXERCISE_COLUMNS: dict[str, Any] = {
    'id': None, 'language_id': None, 'exercise_type': None, 'source_type': None,
    'word_sense_id': None, 'corpus_collocation_id': None, 'word_asset_id': None,
    'content': None, 'tags': {}, 'difficulty_static': None, 'irt_difficulty': 0.0,
    'irt_discrimination': 1.0, 'irt_n_attempts': 0, 'irt_calibrated_at': None,
    'irt_se_difficulty': None, 'complexity_tier': None, 'ladder_level': None,
    'pattern_code': None, 'attempt_count': 0, 'correct_count': 0, 'is_active': True,
    'generation_batch_id': None, 'created_at': None, 'content_version': 0, 'dedupe_key': None,
}

# exercise_content_commit insert column list (ADR-049 §8); everything else takes its default.
COMMIT_INSERT_COLUMNS = (
    'id', 'language_id', 'exercise_type', 'source_type', 'word_sense_id',
    'corpus_collocation_id', 'word_asset_id', 'content', 'tags', 'difficulty_static',
    'complexity_tier', 'ladder_level', 'pattern_code', 'is_active', 'generation_batch_id',
)

BEGIN_ROW_COLUMNS = ('id', 'language_id', 'exercise_type', 'ladder_level', 'word_asset_id',
                     'is_active', 'content_version')


class FakeDBError(ValueError):
    """A PostgREST / PostgreSQL error with a ``code`` (``22023``, ``23505``, ``42703``, ...)."""

    def __init__(self, code: str, message: str):
        super().__init__({'code': code, 'message': message})
        self.code = code
        self.message = message

    def __str__(self) -> str:
        return f"{{'code': '{self.code}', 'message': {self.message!r}}}"


@dataclass
class FakeResponse:
    data: Any
    count: int | None = None


@dataclass
class FakeCall:
    kind: str                       # 'rpc' | 'table'
    name: str                       # rpc name or table name
    op: str = ''                    # table: select | insert | update | delete
    params: Any = None              # rpc params / insert rows / update values
    columns: str | None = None      # select list
    filters: list = field(default_factory=list)   # [(op, column, value, negated)]


def _text(value: Any) -> str:
    """``->>`` of a JSON value: strings unquoted, null as SQL NULL (None)."""
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, bool):
        return 'true' if value else 'false'
    return json.dumps(value, ensure_ascii=False, separators=(', ', ': '))


def dedupe_key_for(exercise_type: Any, content: Any) -> str | None:
    """``md5(coalesce(content->>'context_sentence',''))`` for the 8 context-free types."""
    if exercise_type not in CONTEXT_FREE_TYPES:
        return None
    sentence = _text(content.get('context_sentence')) if isinstance(content, dict) else None
    return hashlib.md5((sentence or '').encode('utf-8')).hexdigest()


def _norm(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, bool):
        return 'true' if value else 'false'
    return str(value)


def _same(left: Any, right: Any) -> bool:
    return left is not None and right is not None and _norm(left) == _norm(right)


def _cmp_value(value: Any) -> Any:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return value
    try:
        return float(value)
    except (TypeError, ValueError):
        return str(value)


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


class _Query:
    """A PostgREST-style builder over one in-memory table."""

    def __init__(self, db: 'FakeContentDB', table: str):
        self._db = db
        self.table = table
        self.op: str | None = None
        self.payload: Any = None
        self.columns: str | None = None
        self.filters: list[tuple[str, str, Any, bool]] = []
        self.ordering: list[tuple[str, bool]] = []
        self.window: tuple[int, int] | None = None
        self.max_rows: int | None = None
        self.count: str | None = None
        self._negate = False

    # -- operations ---------------------------------------------------------

    def _set_op(self, op: str, payload: Any = None) -> '_Query':
        if self.op is not None:
            raise AssertionError(f'{self.table}: {op} after {self.op}')
        self.op, self.payload = op, payload
        return self

    def select(self, columns: str = '*', count: str | None = None, **_: Any) -> '_Query':
        if self.op is None:
            self._set_op('select')
        self.columns = columns
        self.count = count
        return self

    def insert(self, rows: Any, **_: Any) -> '_Query':
        return self._set_op('insert', copy.deepcopy(rows))

    def update(self, values: Mapping, **_: Any) -> '_Query':
        return self._set_op('update', copy.deepcopy(dict(values)))

    def delete(self, **_: Any) -> '_Query':
        return self._set_op('delete')

    def upsert(self, *args: Any, **kwargs: Any) -> '_Query':
        raise AssertionError('exercises must never be upserted (ADR-049 §4)')

    # -- filters ------------------------------------------------------------

    @property
    def not_(self) -> '_Query':
        self._negate = True
        return self

    def _filter(self, op: str, column: str, value: Any) -> '_Query':
        self.filters.append((op, column, copy.deepcopy(value), self._negate))
        self._negate = False
        return self

    def eq(self, column: str, value: Any) -> '_Query':
        return self._filter('eq', column, value)

    def neq(self, column: str, value: Any) -> '_Query':
        return self._filter('neq', column, value)

    def in_(self, column: str, values: Iterable) -> '_Query':
        return self._filter('in', column, list(values))

    def is_(self, column: str, value: Any) -> '_Query':
        return self._filter('is', column, value)

    def gt(self, column: str, value: Any) -> '_Query':
        return self._filter('gt', column, value)

    def gte(self, column: str, value: Any) -> '_Query':
        return self._filter('gte', column, value)

    def lt(self, column: str, value: Any) -> '_Query':
        return self._filter('lt', column, value)

    def lte(self, column: str, value: Any) -> '_Query':
        return self._filter('lte', column, value)

    def order(self, column: str, desc: bool = False, **_: Any) -> '_Query':
        self.ordering.append((column, bool(desc)))
        return self

    def range(self, start: int, end: int) -> '_Query':
        self.window = (start, end)
        return self

    def limit(self, size: int, **_: Any) -> '_Query':
        self.max_rows = size
        return self

    def matches(self, row: Mapping) -> bool:
        for op, column, value, negated in self.filters:
            cell = row.get(column)
            if op == 'eq':
                ok = _same(cell, value)
            elif op == 'neq':
                ok = cell is not None and not _same(cell, value)
            elif op == 'in':
                ok = any(_same(cell, v) for v in value)
            elif op == 'is':
                word = _norm(value).lower() if value is not None else 'null'
                ok = (cell is None) if word == 'null' else (_norm(cell) == word)
            else:
                if cell is None:
                    ok = False
                else:
                    left, right = _cmp_value(cell), _cmp_value(value)
                    try:
                        ok = {'gt': left > right, 'gte': left >= right,
                              'lt': left < right, 'lte': left <= right}[op]
                    except TypeError:
                        ok = {'gt': str(left) > str(right), 'gte': str(left) >= str(right),
                              'lt': str(left) < str(right), 'lte': str(left) <= str(right)}[op]
            if ok == negated:
                return False
        return True

    def execute(self) -> FakeResponse:
        return self._db._execute(self)


class _RpcCall:
    def __init__(self, db: 'FakeContentDB', name: str, params: dict):
        self._db, self._name, self._params = db, name, params

    def execute(self) -> FakeResponse:
        return FakeResponse(self._db._call_rpc(self._name, self._params))


class FakeContentDB:
    """In-memory ``exercises`` table + the ADR-049 §8 RPCs (see the module docstring)."""

    def __init__(self, rows: Iterable[Mapping] = (), *, has_content_column: bool = True,
                 enforce_unique: bool = True, next_version: int = 1):
        self.lock = threading.RLock()
        self._exercises: dict[str, dict] = {}
        self.tables: dict[str, list[dict]] = {}
        self._has_content_column = has_content_column
        self.enforce_unique = enforce_unique
        self.next_version = next_version
        self.calls: list[FakeCall] = []
        self.rpc_handlers: dict[str, Callable[['FakeContentDB', dict], Any]] = {
            'exercise_content_begin': FakeContentDB._rpc_begin,
            'exercise_content_commit': FakeContentDB._rpc_commit,
            'exercise_content_live_versions': FakeContentDB._rpc_live_versions,
        }
        self._hooks: list[tuple[str, Callable, bool]] = []
        if rows:
            self.seed(rows)

    # -- test helpers -------------------------------------------------------

    @property
    def has_content_column(self) -> bool:
        return self._has_content_column

    @has_content_column.setter
    def has_content_column(self, value: bool) -> None:
        with self.lock:
            self._has_content_column = bool(value)
            for row in self._exercises.values():
                if value:
                    row.setdefault('content', None)
                else:
                    row.pop('content', None)

    def seed(self, rows: Iterable[Mapping], **defaults: Any) -> list[str]:
        """Insert rows directly (no hooks, no call record, no checks); returns their ids.
        A row without ``id`` gets a uuid4; missing columns take their defaults."""
        ids = []
        with self.lock:
            for source in rows:
                row = self._new_row({**defaults, **copy.deepcopy(dict(source))})
                self._exercises[row['id']] = row
                ids.append(row['id'])
        return ids

    def rows(self, sense_id: Any = None) -> list[dict]:
        """Deep copies of the exercise rows (of one sense), in insertion order."""
        with self.lock:
            return [copy.deepcopy(r) for r in self._exercises.values()
                    if sense_id is None or _same(r.get('word_sense_id'), sense_id)]

    def row(self, exercise_id: str) -> dict | None:
        with self.lock:
            found = self._exercises.get(str(exercise_id))
            return copy.deepcopy(found) if found is not None else None

    def content_of(self, sense_id: Any) -> dict[str, Any]:
        """``{id: content}`` of a sense's rows (column content; pre-drop only)."""
        return {r['id']: r.get('content') for r in self.rows(sense_id)}

    def versions(self, sense_id: Any) -> list[int]:
        return sorted({r['content_version'] for r in self.rows(sense_id)})

    def on(self, event: str, fn: Callable[['FakeContentDB', Any], Any], *,
           once: bool = True) -> None:
        """Run ``fn(db, payload)`` at ``event`` (``before:``/``after:`` + an rpc name or
        ``<table>.<op>``), before the call takes the lock. ``payload`` is the rpc params
        (``after:`` rpc hooks get ``(params, result)``) or the table query."""
        with self.lock:
            self._hooks.append((event, fn, once))

    def rpc_calls(self, name: str | None = None) -> list[dict]:
        return [c.params for c in self.calls if c.kind == 'rpc' and (name is None or c.name == name)]

    def table_calls(self, op: str | None = None, table: str = 'exercises') -> list[FakeCall]:
        return [c for c in self.calls
                if c.kind == 'table' and c.name == table and (op is None or c.op == op)]

    # -- client surface -----------------------------------------------------

    def table(self, name: str) -> _Query:
        return _Query(self, name)

    def from_(self, name: str) -> _Query:
        return self.table(name)

    def rpc(self, name: str, params: Mapping | None = None, **_: Any) -> _RpcCall:
        return _RpcCall(self, name, dict(params or {}))

    # -- internals ----------------------------------------------------------

    def _run_hooks(self, event: str, payload: Any) -> None:
        with self.lock:
            due = [hook for hook in self._hooks if hook[0] == event]
            self._hooks = [hook for hook in self._hooks if not (hook[0] == event and hook[2])]
        for _, fn, _ in due:
            fn(self, payload)

    def _call_rpc(self, name: str, params: dict) -> Any:
        params = copy.deepcopy(params)
        self._run_hooks(f'before:{name}', params)
        handler = self.rpc_handlers.get(name)
        if handler is None:
            raise FakeDBError('PGRST202', f'Could not find the function public.{name}')
        with self.lock:
            self.calls.append(FakeCall(kind='rpc', name=name, params=copy.deepcopy(params)))
            result = handler(self, params)
        result = copy.deepcopy(result)
        self._run_hooks(f'after:{name}', (params, result))
        return result

    def _execute(self, query: _Query) -> FakeResponse:
        if query.op is None:
            raise AssertionError(f'{query.table}: execute() without an operation')
        event = f'{query.table}.{query.op}'
        self._run_hooks(f'before:{event}', query)
        with self.lock:
            self.calls.append(FakeCall(
                kind='table', name=query.table, op=query.op,
                params=copy.deepcopy(query.payload), columns=query.columns,
                filters=list(query.filters)))
            if query.table == 'exercises':
                data = getattr(self, f'_exercises_{query.op}')(query)
            else:
                data = self._generic(query)
            response = FakeResponse(copy.deepcopy(data),
                                    count=len(data) if query.count else None)
        self._run_hooks(f'after:{event}', query)
        return response

    # exercises -------------------------------------------------------------

    def _new_row(self, values: Mapping) -> dict:
        row = copy.deepcopy(EXERCISE_COLUMNS)
        row['created_at'] = datetime.now(timezone.utc).isoformat()
        row.update(values)
        if row.get('id') is None:
            row['id'] = str(uuid.uuid4())
        row['id'] = str(row['id'])
        if row.get('tags') is None:
            row['tags'] = {}
        if not self._has_content_column:
            row.pop('content', None)
        return row

    def _check_columns(self, names: Iterable[str], *, writing: bool) -> None:
        for name in names:
            if name == 'content' and not self._has_content_column:
                if writing:
                    raise FakeDBError('PGRST204', "Could not find the 'content' column of "
                                                  "'exercises' in the schema cache")
                raise FakeDBError('42703', 'column exercises.content does not exist')
            if name not in EXERCISE_COLUMNS:
                if writing:
                    raise FakeDBError('PGRST204', f"Could not find the '{name}' column of "
                                                  f"'exercises' in the schema cache")
                raise FakeDBError('42703', f'column exercises.{name} does not exist')

    def _selected(self, columns: str | None) -> list[str] | None:
        text = (columns or '*').strip()
        if text == '*':
            return None
        names = [part.strip() for part in text.split(',') if part.strip()]
        if any('(' in name or ':' in name for name in names):
            raise AssertionError(f'FakeContentDB does not support embedded selects: {columns!r}')
        self._check_columns(names, writing=False)
        return names

    def _project(self, rows: list[dict], columns: str | None) -> list[dict]:
        names = self._selected(columns)
        if names is None:
            return [dict(row) for row in rows]
        return [{name: row.get(name) for name in names} for row in rows]

    def _window(self, query: _Query, rows: list[dict]) -> list[dict]:
        for column, desc in reversed(query.ordering):
            present = [r for r in rows if r.get(column) is not None]
            missing = [r for r in rows if r.get(column) is None]
            present.sort(key=lambda r: _cmp_value(r[column]), reverse=desc)
            rows = (missing + present) if desc else (present + missing)
        if query.window is not None:
            start, end = query.window
            rows = rows[start:end + 1]
        if query.max_rows is not None:
            rows = rows[:query.max_rows]
        return rows

    def _unique_key(self, row: Mapping) -> tuple | None:
        if not (row.get('is_active') and row.get('word_sense_id') is not None
                and row.get('exercise_type') in CONTEXT_FREE_TYPES):
            return None
        if self._has_content_column:
            key = dedupe_key_for(row.get('exercise_type'), row.get('content') or {})
        else:
            key = row.get('dedupe_key')
            if key is None:
                return None
        return (_norm(row['word_sense_id']), row['exercise_type'], key)

    def _check_unique(self, table: Mapping[str, dict]) -> None:
        if not self.enforce_unique:
            return
        seen: set = set()
        for row in table.values():
            key = self._unique_key(row)
            if key is None:
                continue
            if key in seen:
                raise FakeDBError('23505', 'duplicate key value violates unique constraint '
                                           '"uq_exercises_context_free_variant"')
            seen.add(key)

    def _exercises_select(self, query: _Query) -> list[dict]:
        self._selected(query.columns)
        rows = [r for r in self._exercises.values() if query.matches(r)]
        return self._project(self._window(query, rows), query.columns)

    def _exercises_insert(self, query: _Query) -> list[dict]:
        payload = query.payload
        rows = [payload] if isinstance(payload, Mapping) else list(payload)
        staged = dict(self._exercises)
        inserted = []
        for source in rows:
            self._check_columns(source.keys(), writing=True)
            row = self._new_row(source)
            if row['id'] in staged:
                raise FakeDBError('23505', 'duplicate key value violates unique constraint '
                                           '"exercises_pkey"')
            staged[row['id']] = row
            inserted.append(row)
        self._check_unique(staged)
        self._exercises = staged
        return inserted

    def _exercises_update(self, query: _Query) -> list[dict]:
        self._check_columns(query.payload.keys(), writing=True)
        staged = {key: dict(row) for key, row in self._exercises.items()}
        updated = []
        for key, row in staged.items():
            if query.matches(row):
                row.update(copy.deepcopy(query.payload))
                updated.append(row)
        self._check_unique(staged)
        self._exercises = staged
        return updated

    def _exercises_delete(self, query: _Query) -> list[dict]:
        deleted = [row for row in self._exercises.values() if query.matches(row)]
        for row in deleted:
            del self._exercises[row['id']]
        return deleted

    def _generic(self, query: _Query) -> list[dict]:
        table = self.tables.setdefault(query.table, [])
        if query.op == 'select':
            rows = [r for r in table if query.matches(r)]
            rows = self._window(query, rows)
            names = None if (query.columns or '*').strip() == '*' else [
                c.strip() for c in query.columns.split(',') if c.strip()]
            return [dict(r) if names is None else {n: r.get(n) for n in names} for r in rows]
        if query.op == 'insert':
            payload = query.payload
            rows = [payload] if isinstance(payload, Mapping) else list(payload)
            table.extend(dict(r) for r in rows)
            return [dict(r) for r in rows]
        if query.op == 'update':
            updated = [r for r in table if query.matches(r)]
            for row in updated:
                row.update(query.payload)
            return [dict(r) for r in updated]
        deleted = [r for r in table if query.matches(r)]
        self.tables[query.table] = [r for r in table if not query.matches(r)]
        return deleted

    # rpcs ------------------------------------------------------------------

    def _sense_rows(self, sense_id: Any) -> list[dict]:
        return sorted((r for r in self._exercises.values() if _same(r.get('word_sense_id'), sense_id)),
                      key=lambda r: r['id'])

    @staticmethod
    def _require_int(params: Mapping, name: str) -> int:
        value = params.get(name)
        if not _is_int(value):
            raise FakeDBError('22023', f'{name} must be an integer, got {value!r}')
        return value

    def _rpc_begin(self, params: dict) -> dict:
        sense_id = self._require_int(params, 'p_sense_id')
        rows = self._sense_rows(sense_id)
        current = max((r['content_version'] for r in rows), default=0) or 0
        new = self.next_version
        self.next_version += 1
        return {'sense_id': sense_id, 'current_version': current, 'new_version': new,
                'rows': [{name: r.get(name) for name in BEGIN_ROW_COLUMNS} for r in rows]}

    def _rpc_commit(self, params: dict) -> dict:
        sense_id = self._require_int(params, 'p_sense_id')
        expected = self._require_int(params, 'p_expected_version')
        new = self._require_int(params, 'p_new_version')
        expected_ids = {str(i) for i in (params.get('p_expected_ids') or [])}
        delete_ids = [str(i) for i in (params.get('p_delete_ids') or [])]
        insert_rows = params.get('p_insert_rows') or []
        updates = params.get('p_update_contents') or {}
        if not isinstance(insert_rows, list) or not isinstance(updates, Mapping):
            raise FakeDBError('22023', 'p_insert_rows must be an array, p_update_contents an object')
        # Static input checks, before the compare-and-swap, as in
        # migrations/exercise_content_storage.sql (TASK-1025 alignment): bad input
        # raises 22023 whatever the table holds; a missing source_type is the
        # NOT NULL violation (23502) the real INSERT raises.
        for row in insert_rows:
            if not isinstance(row, Mapping) or not row.get('id'):
                raise FakeDBError('22023', f'insert row without id: {row!r:.120}')
            if not _same(row.get('word_sense_id'), sense_id):
                raise FakeDBError('22023', f'insert row for another sense: {row!r:.120}')
            if not isinstance(row.get('content'), Mapping):
                raise FakeDBError('22023', f'insert row {row.get("id")} has no JSON object '
                                           f'under "content"')
            if row.get('source_type') is None:
                raise FakeDBError('23502', 'null value in column "source_type" of relation '
                                           '"exercises" violates not-null constraint')
        for exercise_id, content in updates.items():
            if not isinstance(content, Mapping):
                raise FakeDBError('22023', f'the update for {exercise_id} is not a JSON object')

        rows = self._sense_rows(sense_id)
        current = max((r['content_version'] for r in rows), default=0) or 0
        if current != expected:
            return {'ok': False, 'reason': 'version_conflict', 'current_version': current}
        if {r['id'] for r in rows} != expected_ids:
            return {'ok': False, 'reason': 'rows_changed', 'current_version': current}
        if new <= current:
            raise FakeDBError('22023', f'p_new_version {new} must be greater than the current '
                                       f'version {current}')
        in_sense = {r['id'] for r in rows}
        for exercise_id in delete_ids:
            if exercise_id not in in_sense:
                raise FakeDBError('22023', f'delete id {exercise_id} is not in sense {sense_id}')
        for exercise_id in updates:
            if str(exercise_id) not in in_sense:
                raise FakeDBError('22023', f'update id {exercise_id} is not in sense {sense_id}')
            if str(exercise_id) in delete_ids:
                raise FakeDBError('22023', f'update id {exercise_id} is also deleted')

        staged = {key: dict(row) for key, row in self._exercises.items()}
        deleted = 0
        for exercise_id in delete_ids:
            if staged.pop(exercise_id, None) is not None:
                deleted += 1
        for source in insert_rows:
            values = {name: copy.deepcopy(source[name]) for name in COMMIT_INSERT_COLUMNS
                      if name in source and source[name] is not None}
            if not self._has_content_column:
                values.pop('content', None)
            values.setdefault('tags', {})
            values.setdefault('is_active', True)
            values['content_version'] = new
            values['dedupe_key'] = dedupe_key_for(source.get('exercise_type'),
                                                  source.get('content'))
            row = self._new_row(values)
            if row['id'] in staged:
                raise FakeDBError('23505', 'duplicate key value violates unique constraint '
                                           '"exercises_pkey"')
            staged[row['id']] = row
        updated = 0
        for exercise_id, content in updates.items():
            row = staged.get(str(exercise_id))
            if row is None:
                continue
            if self._has_content_column:
                row['content'] = copy.deepcopy(content)
            row['dedupe_key'] = dedupe_key_for(row.get('exercise_type'), content)
            updated += 1
        for row in staged.values():
            if _same(row.get('word_sense_id'), sense_id) and row['content_version'] != new:
                row['content_version'] = new
        self._check_unique(staged)
        self._exercises = staged
        return {'ok': True, 'version': new, 'deleted': deleted, 'inserted': len(insert_rows),
                'updated': updated}

    def _rpc_live_versions(self, params: dict) -> dict:
        language_id = self._require_int(params, 'p_language_id')
        live: dict[str, set] = {}
        for row in self._exercises.values():
            if _same(row.get('language_id'), language_id) and row.get('word_sense_id') is not None:
                live.setdefault(str(row['word_sense_id']), set()).add(row['content_version'])
        return {sense: sorted(versions) for sense, versions in sorted(live.items(),
                                                                      key=lambda kv: int(kv[0]))}
