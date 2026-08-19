"""TASK-707 — legacy _compute_daily_load step-4 fallback correctness.

The last-resort fallback used to hardcode ``test_type='listening'`` and mount the
wrong player / rate the wrong skill (F9), and it computed an ELO band from a
``user_elo_after`` column it never selected (so the band was always 1000-1400).

These tests pin the fix without a live DB by driving ``_compute_daily_load`` with
a fake Supabase admin:

  * fallback items carry each test's *real* skill type (from the
    test_skill_ratings / dim_test_types join), not a hardcoded 'listening';
  * the ELO band is actually applied to the fallback query and is centred on the
    user's most recent ``user_elo_after`` (proving the dead computation is live).

Server-side filtering (gte/lte, tests!inner language/active scope) is exercised
against the real DB; here we assert the query *issued* the right band.
"""

from types import SimpleNamespace

from services.test_service import TestService


class _FakeQuery:
    """Chainable stand-in for a PostgREST query builder.

    Every filter method returns self and records (method, args) into ``calls``
    so a test can assert what the query asked for. ``execute`` returns the canned
    rows for this table.
    """

    def __init__(self, rows, calls):
        self._rows = rows
        self.calls = calls

    def _record(self, name, *args):
        self.calls.append((name, args))
        return self

    def select(self, *a, **k):
        return self._record('select', *a)

    def eq(self, *a, **k):
        return self._record('eq', *a)

    def order(self, *a, **k):
        return self._record('order', *a)

    def gte(self, *a, **k):
        return self._record('gte', *a)

    def lte(self, *a, **k):
        return self._record('lte', *a)

    def limit(self, *a, **k):
        return self._record('limit', *a)

    def execute(self):
        return SimpleNamespace(data=self._rows)


class _FakeAdmin:
    """Serves canned rows per table and records each table's query calls."""

    def __init__(self, tables, rpc_data):
        self._tables = tables
        self._rpc_data = rpc_data
        self.calls = {}  # table/rpc name -> list of (method, args)

    def table(self, name):
        calls = self.calls.setdefault(name, [])
        return _FakeQuery(self._tables.get(name, []), calls)

    def rpc(self, name, params):
        calls = self.calls.setdefault(f'rpc:{name}', [])
        calls.append(('params', (params,)))
        return _FakeQuery(self._rpc_data.get(name, []), calls)


def _skill_rating(test_id, type_code, elo=1200):
    return {
        'test_id': test_id,
        'elo_rating': elo,
        'dim_test_types': {'type_code': type_code},
        'tests': {'id': test_id, 'is_active': True, 'language_id': 1},
    }


def test_fallback_labels_items_with_real_type_dictation_only():
    """A dictation-only skill-ratings pool must yield fallback items labeled
    'dictation' — never the old hardcoded 'listening'."""
    admin = _FakeAdmin(
        tables={
            'test_attempts': [],  # no attempts -> straight to fallback
            'test_skill_ratings': [
                _skill_rating('t1', 'dictation'),
                _skill_rating('t2', 'dictation'),
                _skill_rating('t3', 'dictation'),
            ],
        },
        rpc_data={'get_recommended_tests': []},  # RPC under-serves -> fallback
    )
    svc = TestService(supabase_admin=admin)

    items = svc._compute_daily_load('user-1', 1)

    assert len(items) == 3
    assert all(i['test_type'] == 'dictation' for i in items), items
    assert all(i['slot_type'] == 'new' for i in items)
    assert {i['test_id'] for i in items} == {'t1', 't2', 't3'}


def test_fallback_queries_test_skill_ratings_not_tests():
    """The fallback must read from test_skill_ratings (where type + ELO live),
    not the bare `tests` table it used to hardcode 'listening' against."""
    admin = _FakeAdmin(
        tables={
            'test_attempts': [],
            'test_skill_ratings': [_skill_rating('t1', 'reading')],
        },
        rpc_data={'get_recommended_tests': []},
    )
    svc = TestService(supabase_admin=admin)

    svc._compute_daily_load('user-1', 1)

    assert 'test_skill_ratings' in admin.calls
    # The old code issued a `tests` table query in the fallback; it must not.
    assert 'tests' not in admin.calls


def test_fallback_applies_default_elo_band_when_unrated():
    """No attempts -> user_elo defaults to 1200 -> band [1000, 1400] applied to
    the fallback query (band is live, not dead)."""
    admin = _FakeAdmin(
        tables={
            'test_attempts': [],
            'test_skill_ratings': [_skill_rating('t1', 'listening')],
        },
        rpc_data={'get_recommended_tests': []},
    )
    svc = TestService(supabase_admin=admin)

    svc._compute_daily_load('user-1', 1)

    ratings_calls = admin.calls['test_skill_ratings']
    gte = [args for name, args in ratings_calls if name == 'gte']
    lte = [args for name, args in ratings_calls if name == 'lte']
    assert ('elo_rating', 1000) in gte
    assert ('elo_rating', 1400) in lte


def test_fallback_band_centres_on_recent_user_elo():
    """A recent attempt with user_elo_after=1500 must shift the band to
    [1300, 1700] — proving user_elo_after is actually selected and read."""
    admin = _FakeAdmin(
        tables={
            # High percentage so this is NOT a retry candidate; it only supplies
            # the user's ELO for the band.
            'test_attempts': [{
                'test_id': 'attempted',
                'percentage': 95,
                'test_type_id': 1,
                'created_at': '2026-07-19T00:00:00+00:00',
                'user_elo_after': 1500,
            }],
            'test_skill_ratings': [_skill_rating('t1', 'listening', elo=1500)],
        },
        rpc_data={'get_recommended_tests': []},
    )
    svc = TestService(supabase_admin=admin)

    svc._compute_daily_load('user-1', 1)

    ratings_calls = admin.calls['test_skill_ratings']
    gte = [args for name, args in ratings_calls if name == 'gte']
    lte = [args for name, args in ratings_calls if name == 'lte']
    assert ('elo_rating', 1300) in gte
    assert ('elo_rating', 1700) in lte
