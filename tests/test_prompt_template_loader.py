"""Shared prompt-template loader: English fallback, TTL cache, required flag."""

import pytest

import services.prompt_service as ps


class _Query:
    def __init__(self, db):
        self._db = db
        self._filters = {}

    def select(self, *_a):
        return self

    def eq(self, col, val):
        self._filters[col] = val
        return self

    def order(self, *_a, **_kw):
        return self

    def limit(self, _n):
        return self

    def execute(self):
        self._db.queries += 1
        key = (self._filters['task_name'], self._filters['language_id'])
        text = self._db.rows.get(key)

        class _Resp:
            data = [{'template_text': text}] if text is not None else []
        return _Resp()


class _DB:
    def __init__(self, rows):
        self.rows = dict(rows)
        self.queries = 0

    def table(self, name):
        assert name == 'prompt_templates'
        return _Query(self)


def test_language_row_wins_and_is_cached_until_ttl(monkeypatch):
    db = _DB({('task', 3): 'ja v1', ('task', 2): 'en'})
    now = [1000.0]
    monkeypatch.setattr(ps.time, 'monotonic', lambda: now[0])

    assert ps.load_template_text(db, 'task', 3, ttl=60) == 'ja v1'
    db.rows[('task', 3)] = 'ja v2'
    assert ps.load_template_text(db, 'task', 3, ttl=60) == 'ja v1'
    assert db.queries == 1

    now[0] += 61
    assert ps.load_template_text(db, 'task', 3, ttl=60) == 'ja v2'


def test_falls_back_to_english():
    db = _DB({('task', 2): 'en'})
    assert ps.load_template_text(db, 'task', 1) == 'en'


def test_missing_required_raises_and_optional_returns_none():
    db = _DB({})
    with pytest.raises(RuntimeError, match="task_name='nope'"):
        ps.load_template_text(db, 'nope', 1)
    assert ps.load_template_text(db, 'nope', 1, required=False) is None
    db.rows[('nope', 1)] = 'now present'
    assert ps.load_template_text(db, 'nope', 1) == 'now present'  # misses are not cached


def test_cache_is_per_client_and_clearable():
    a, b = _DB({('task', 2): 'A'}), _DB({('task', 2): 'B'})
    assert ps.load_template_text(a, 'task', 2) == 'A'
    assert ps.load_template_text(b, 'task', 2) == 'B'
    a.rows[('task', 2)] = 'A2'
    ps.clear_template_cache()
    assert ps.load_template_text(a, 'task', 2) == 'A2'


def test_ttl_zero_disables_caching():
    db = _DB({('task', 2): 'en'})
    ps.load_template_text(db, 'task', 2, ttl=0)
    ps.load_template_text(db, 'task', 2, ttl=0)
    assert db.queries == 2
