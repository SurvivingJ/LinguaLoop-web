"""A recording Supabase fake for the script write-convention tests.

Every script that can write is driven through its real ``main()`` against a
``RecordingDB``: selects return the rows a test seeds per table, and every
insert / upsert / update / delete, every RPC not declared read-only and every
Storage upload / remove is recorded in ``db.writes``. A dry run must leave
``db.writes`` empty; ``--apply`` must not.

Helpers:

* ``install(monkeypatch, db, *modules)`` makes ``db`` the service-role client
  for the factory, ``scripts._common.admin_db`` and every given module that
  imported ``get_supabase_admin`` / ``admin_db`` / ``SupabaseFactory`` by name.
* ``run_main(monkeypatch, mod, argv)`` runs ``mod.main()`` with ``sys.argv``
  set, returning the exit code (``SystemExit`` included).
"""

from __future__ import annotations

import sys

WRITE_OPS = ('insert', 'upsert', 'update', 'delete')


class Result:
    def __init__(self, data=None, count=None):
        self.data = data
        self.count = count


class _Not:
    def __init__(self, query):
        self._query = query

    def __getattr__(self, name):
        return lambda *a, **k: self._query


class Query:
    """A postgrest-style builder: filters chain, ``execute()`` reads or records."""

    def __init__(self, db, table: str, rpc: str | None = None, params=None):
        self.db, self.table, self.rpc_name, self.params = db, table, rpc, params
        self.op, self.payload, self.start = 'select', None, 0
        self.filters: list[tuple] = []

    # writes ---------------------------------------------------------------
    def _write(self, op, payload=None, **kwargs):
        self.op, self.payload = op, payload
        return self

    def insert(self, payload, **kwargs):
        return self._write('insert', payload)

    def upsert(self, payload, **kwargs):
        return self._write('upsert', payload)

    def update(self, payload, **kwargs):
        return self._write('update', payload)

    def delete(self, **kwargs):
        return self._write('delete')

    # reads ----------------------------------------------------------------
    def select(self, *a, **k):
        return self

    def range(self, start, end):
        self.start = start
        return self

    @property
    def not_(self):
        return _Not(self)

    def __getattr__(self, name):
        if name.startswith('__'):
            raise AttributeError(name)

        def chain(*args, **kwargs):
            self.filters.append((name, args))
            return self
        return chain

    def execute(self):
        if self.rpc_name is not None:
            return self.db._run_rpc(self)
        if self.op in WRITE_OPS:
            self.db.writes.append((self.op, self.table, self.payload))
            payload = self.payload
            rows = payload if isinstance(payload, list) else ([payload] if payload else [])
            return Result([{'id': i + 1, **r} if isinstance(r, dict) else r
                           for i, r in enumerate(rows)])
        if self.start:
            return Result([], 0)
        rows = self.db.rows.get(self.table, [])
        if callable(rows):
            rows = rows(self)
        return Result(list(rows), len(rows))


class _Bucket:
    def __init__(self, db, name):
        self.db, self.name = db, name

    def upload(self, path, *a, **k):
        self.db.writes.append(('storage.upload', self.name, path))
        return {'Key': path}

    def update(self, path, *a, **k):
        self.db.writes.append(('storage.update', self.name, path))
        return {'Key': path}

    def remove(self, paths):
        self.db.writes.append(('storage.remove', self.name, paths))
        return []

    def list(self, *a, **k):
        return self.db.storage_files.get(self.name, [])

    def download(self, path):
        return self.db.storage_blobs.get((self.name, path), b'')


class _Storage:
    def __init__(self, db):
        self.db = db

    def from_(self, bucket):
        return _Bucket(self.db, bucket)


class RecordingDB:
    """``rows``: table -> list of rows (or a callable taking the Query).

    ``rpc_rows``: rpc name -> data (or callable taking the params).
    ``read_rpcs``: RPC names that only read; any other RPC is recorded as a write.
    """

    def __init__(self, rows=None, rpc_rows=None, read_rpcs=()):
        self.rows = dict(rows or {})
        self.rpc_rows = dict(rpc_rows or {})
        self.read_rpcs = set(read_rpcs)
        self.writes: list[tuple] = []
        self.rpc_calls: list[tuple] = []
        self.storage = _Storage(self)
        self.storage_files: dict = {}
        self.storage_blobs: dict = {}

    def table(self, name):
        return Query(self, name)

    from_ = table

    def rpc(self, name, params=None, **kwargs):
        return Query(self, None, rpc=name, params=params)

    def _run_rpc(self, query):
        name, params = query.rpc_name, query.params
        self.rpc_calls.append((name, params))
        if name not in self.read_rpcs:
            self.writes.append(('rpc', name, params))
        data = self.rpc_rows.get(name, [])
        if callable(data):
            data = data(params)
        return Result(data)


def install(monkeypatch, db, *modules):
    """Make ``db`` the only Supabase client the given script modules can reach."""
    from services import supabase_factory
    from scripts import _common
    monkeypatch.setattr(supabase_factory.SupabaseFactory, 'is_initialized',
                        classmethod(lambda cls: True))
    monkeypatch.setattr(supabase_factory.SupabaseFactory, 'initialize',
                        classmethod(lambda cls, *a, **k: None))
    monkeypatch.setattr(supabase_factory, 'get_supabase_admin', lambda: db)
    monkeypatch.setattr(supabase_factory, 'get_supabase', lambda: db, raising=False)
    monkeypatch.setattr(_common, 'admin_db', lambda: db)
    for mod in modules:
        for name, value in (('get_supabase_admin', lambda: db), ('admin_db', lambda: db),
                            ('get_supabase', lambda: db)):
            if hasattr(mod, name):
                monkeypatch.setattr(mod, name, value)
    return db


def run_main(monkeypatch, mod, argv, main='main'):
    """Run ``mod.main()`` as ``python <script> argv``; returns its exit code."""
    monkeypatch.setattr(sys, 'argv', [mod.__name__] + list(argv))
    try:
        rc = getattr(mod, main)()
    except SystemExit as exc:
        return exc.code
    return rc
