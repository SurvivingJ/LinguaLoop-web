"""In-memory stand-in for the supabase-py query builder, covering exactly the
calls services/word_list_import/queue.py makes: select / insert / upsert /
update with eq, in_, gte, not_.is_, order, limit, range. Rows are plain dicts;
`select` column lists are ignored (whole rows come back)."""

import copy
import itertools


class _Resp:
    def __init__(self, data):
        self.data = data


class _Not:
    def __init__(self, query):
        self._q = query

    def is_(self, col, value):
        assert value == 'null'
        self._q._filters.append(lambda r: r.get(col) is not None)
        return self._q


class _Query:
    def __init__(self, db, name):
        self._db = db
        self._name = name
        self._filters = []
        self._op = 'select'
        self._payload = None
        self._order = None
        self._limit = None
        self._range = None
        self._upsert = None

    # -- verbs
    def select(self, *_a, **_kw):
        self._op = 'select'
        return self

    def insert(self, rows):
        self._op, self._payload = 'insert', rows
        return self

    def upsert(self, rows, on_conflict='', ignore_duplicates=False):
        self._op, self._payload = 'upsert', rows
        self._upsert = ([c.strip() for c in on_conflict.split(',') if c.strip()], ignore_duplicates)
        return self

    def update(self, fields):
        self._op, self._payload = 'update', fields
        return self

    # -- filters
    def eq(self, col, val):
        self._filters.append(lambda r: r.get(col) == val)
        return self

    def in_(self, col, values):
        values = list(values)
        self._filters.append(lambda r: r.get(col) in values)
        return self

    def gte(self, col, val):
        self._filters.append(lambda r: r.get(col) is not None and r.get(col) >= val)
        return self

    @property
    def not_(self):
        return _Not(self)

    def order(self, col, desc=False):
        self._order = (col, desc)
        return self

    def limit(self, n):
        self._limit = n
        return self

    def range(self, start, end):
        self._range = (start, end)
        return self

    # -- run
    def _matching(self):
        return [r for r in self._db.tables.setdefault(self._name, [])
                if all(f(r) for f in self._filters)]

    def execute(self):
        if self._db.fail_tables and self._name in self._db.fail_tables:
            raise RuntimeError(f'table {self._name} unavailable')
        table = self._db.tables.setdefault(self._name, [])
        if self._op == 'select':
            rows = self._matching()
            if self._order:
                col, desc = self._order
                rows = sorted(rows, key=lambda r: (r.get(col) is None, r.get(col)), reverse=desc)
            if self._range:
                rows = rows[self._range[0]:self._range[1] + 1]
            if self._limit is not None:
                rows = rows[:self._limit]
            return _Resp(copy.deepcopy(rows))
        if self._op == 'update':
            rows = self._matching()
            for r in rows:
                r.update(copy.deepcopy(self._payload))
            return _Resp(copy.deepcopy(rows))
        payload = self._payload if isinstance(self._payload, list) else [self._payload]
        inserted = []
        for row in payload:
            row = copy.deepcopy(row)
            if self._op == 'upsert':
                keys, ignore = self._upsert
                clash = next((r for r in table if all(r.get(k) == row.get(k) for k in keys)), None)
                if clash is not None:
                    if not ignore:
                        clash.update(row)
                        inserted.append(copy.deepcopy(clash))
                    continue
            row.setdefault('id', next(self._db.ids))
            table.append(row)
            inserted.append(copy.deepcopy(row))
        return _Resp(inserted)


class FakeDB:
    def __init__(self, **tables):
        self.tables = {k: list(v) for k, v in tables.items()}
        self.ids = itertools.count(1000)
        self.fail_tables = set()

    def table(self, name):
        return _Query(self, name)
