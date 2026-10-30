"""Offline Supabase stand-in: serves .table() reads from JSON snapshots
(snap/<table>.json, list of row dicts) and records writes to writes.jsonl.
Activate by importing before the target script; logs unknown tables."""
import json, os, sys

SNAP = os.environ.get('OFFLINE_SNAP', os.path.join(os.path.dirname(__file__), 'snap'))
LOG = os.path.join(SNAP, '_queries.log')
_cache = {}

def _rows(table):
    if table not in _cache:
        p = os.path.join(SNAP, f'{table}.json')
        if os.path.exists(p):
            _cache[table] = json.load(open(p, encoding='utf-8'))
        else:
            _cache[table] = []
            open(LOG, 'a').write(f'MISSING {table}\n')
    return _cache[table]

class _Res:
    def __init__(self, data, count=None):
        self.data, self.count = data, count

import re as _re
# (table, embedded) -> (local col, remote col, many?)
FKS = {('dim_word_senses', 'dim_vocabulary'): ('vocab_id', 'id', False),
       ('word_assets', 'dim_word_senses'): ('sense_id', 'id', False),
       ('exercises', 'dim_word_senses'): ('word_sense_id', 'id', False),
       ('dim_vocabulary', 'dim_word_senses'): ('id', 'vocab_id', True)}

def _parse_cols(cols):
    """Returns (plain cols or None for *, [(alias, table, subcols)])."""
    cols = (cols or '*').strip()
    embeds = []
    for m in _re.finditer(r'(?:(\w+):)?(\w+)(?:!\w+)?\(([^()]*)\)', cols):
        embeds.append((m.group(1) or m.group(2), m.group(2), m.group(3)))
    plain = _re.sub(r'(?:\w+:)?\w+(?:!\w+)?\([^()]*\)', '', cols)
    plain = [c.strip().split(':')[-1] for c in plain.split(',') if c.strip()]
    if '*' in plain or not plain and not embeds: plain = None
    return plain, embeds

def k_conf(q): return getattr(q, 'conf', None)

class Q:
    def __init__(self, table):
        self.table, self.f, self.cols, self.op = table, [], None, 'select'
        self._order, self._range, self._limit, self._single, self._count = [], None, None, None, None
        self.payload = None
    def select(self, cols='*', count=None, **k):
        self.cols, self.embeds = _parse_cols(cols); self._count = count
        open(LOG, 'a').write(f'SELECT {self.table} {cols}\n'); return self
    def _add(self, fn): self.f.append(fn); return self
    def eq(self, c, v):
        self.__dict__.setdefault('where', []).append((c, v)); return self._add(lambda r: r.get(c) == v)
    def neq(self, c, v): return self._add(lambda r: r.get(c) != v)
    def gt(self, c, v): return self._add(lambda r: r.get(c) is not None and r.get(c) > v)
    def gte(self, c, v): return self._add(lambda r: r.get(c) is not None and r.get(c) >= v)
    def lt(self, c, v): return self._add(lambda r: r.get(c) is not None and r.get(c) < v)
    def lte(self, c, v): return self._add(lambda r: r.get(c) is not None and r.get(c) <= v)
    def in_(self, c, vs):
        s = set(vs); return self._add(lambda r: r.get(c) in s)
    def is_(self, c, v):
        want = None if v in (None, 'null') else (v in (True, 'true'))
        return self._add(lambda r: r.get(c) is want if want is None else r.get(c) == want)
    @property
    def not_(self):
        outer = self
        class N:
            def is_(s, c, v): return outer._add(lambda r: r.get(c) is not None) if v in (None, 'null') else outer._add(lambda r: r.get(c) != v)
            def in_(s, c, vs):
                st = set(vs); return outer._add(lambda r: r.get(c) not in st)
            def eq(s, c, v): return outer.neq(c, v)
        return N()
    def ilike(self, c, p):
        p = p.strip('%').lower(); return self._add(lambda r: p in str(r.get(c) or '').lower())
    def like(self, c, p): return self.ilike(c, p)
    def contains(self, c, v):
        want = set(map(str, v)) if isinstance(v, (list, tuple)) else None
        if want is None: return self
        return self._add(lambda r: want <= set(map(str, r.get(c) or [])))
    def overlaps(self, c, v):
        want = set(map(str, v)); return self._add(lambda r: bool(want & set(map(str, r.get(c) or []))))
    def filter(self, *a, **k): open(LOG, 'a').write(f'FILTER? {self.table} {a}\n'); return self
    def or_(self, *a, **k): open(LOG, 'a').write(f'OR? {self.table} {a}\n'); return self
    def order(self, c, desc=False, **k): self._order.append((c, desc)); return self
    def range(self, a, b): self._range = (a, b); return self
    def limit(self, n): self._limit = n; return self
    def single(self): self._single = True; return self
    def maybe_single(self): self._single = 'maybe'; return self
    def insert(self, p, **k): self.op, self.payload = 'insert', p; return self
    def upsert(self, p, **k): self.op, self.payload, self.conf = 'upsert', p, k.get('on_conflict'); return self
    def update(self, p, **k): self.op, self.payload = 'update', p; return self
    def delete(self, **k): self.op = 'delete'; return self
    def execute(self):
        if self.op != 'select':
            with open(os.path.join(SNAP, 'writes.jsonl'), 'a', encoding='utf-8') as fh:
                fh.write(json.dumps({'op': self.op, 'table': self.table, 'payload': self.payload, 'where': getattr(self, 'where', []), 'on_conflict': k_conf(self)}, ensure_ascii=False, default=str) + '\n')
            return _Res(self.payload if isinstance(self.payload, list) else [self.payload or {}])
        rows = [r for r in _rows(self.table) if all(fn(r) for fn in self.f)]
        for c, d in reversed(self._order):
            rows.sort(key=lambda r: (r.get(c) is None, r.get(c)), reverse=d)
        total = len(rows)
        if self._range: rows = rows[self._range[0]:self._range[1] + 1]
        if self._limit is not None: rows = rows[:self._limit]
        emb = getattr(self, 'embeds', [])
        if self.cols is not None or emb:
            out = []
            for r in rows:
                o = dict(r) if self.cols is None else {k: r.get(k) for k in self.cols}
                for alias, t, sub in emb:
                    fk = FKS.get((self.table, t))
                    if not fk:
                        open(LOG, 'a').write(f'EMBED? {self.table}->{t}\n'); o[alias] = None; continue
                    lc, rc, many = fk
                    q = Q(t).select(sub or '*').eq(rc, r.get(lc))
                    d = q.execute().data
                    o[alias] = d if many else (d[0] if d else None)
                out.append(o)
            rows = out
        if self._single:
            return _Res(rows[0] if rows else None, total)
        return _Res(rows, total)

class Client:
    def table(self, t): return Q(t)
    from_ = table
    def rpc(self, name, params=None):
        open(LOG, 'a').write(f'RPC {name} {params}\n')
        class R:
            def execute(s): return _Res([])
        return R()

from services import supabase_factory as sf
_c = Client()
sf.SupabaseFactory.initialize = classmethod(lambda cls, *a, **k: None)
sf.SupabaseFactory.is_initialized = classmethod(lambda cls: True)
sf.SupabaseFactory.get_service_client = classmethod(lambda cls: _c)
sf.SupabaseFactory.get_anon_client = classmethod(lambda cls: _c)
sf.get_supabase_admin = lambda: _c
