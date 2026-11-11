"""services.pagination.fetch_all and the exercise reads that page with it.

PostgREST caps every response at 1000 rows without saying so; these fakes do
the same, so a read that does not page loses rows here exactly as it did live
(2026-11-11: 2,588 active exercises for 200 senses came back as 1,000, and
prestudy counted 231 senses with exercises instead of 423).
"""

from types import SimpleNamespace

from services import pagination, prestudy

CAP = 1000


class _CappedQuery:
    def __init__(self, rows):
        self._rows, self._filters, self._order, self._range = rows, [], None, None

    def select(self, *a, **k):
        return self

    def eq(self, col, val):
        self._filters.append(lambda r, c=col, v=val: r.get(c) == v)
        return self

    def in_(self, col, vals):
        vals = set(vals)
        self._filters.append(lambda r, c=col: r.get(c) in vals)
        return self

    def order(self, col):
        self._order = col
        return self

    def range(self, start, end):
        assert self._range is None, 'range() called twice on one builder'
        self._range = (start, end)
        return self

    def execute(self):
        rows = [r for r in self._rows if all(f(r) for f in self._filters)]
        if self._order:
            rows.sort(key=lambda r: r[self._order])
        if self._range:
            rows = rows[self._range[0]:self._range[1] + 1]
        return SimpleNamespace(data=rows[:CAP])          # the server's silent cap


class _CappedDB:
    def __init__(self, tables):
        self.tables, self.calls = tables, 0

    def table(self, name):
        self.calls += 1
        return _CappedQuery(self.tables.get(name, []))


def _exercises(n_senses, per_sense, inactive_every=0):
    rows, i = [], 0
    for s in range(1, n_senses + 1):
        for k in range(per_sense):
            i += 1
            rows.append({'id': i, 'word_sense_id': s, 'exercise_type': 'cloze_completion',
                         'content': {}, 'ladder_level': 1,
                         'is_active': not (inactive_every and i % inactive_every == 0)})
    return rows


class TestFetchAll:
    def test_pages_past_the_cap_and_stops_on_a_short_page(self):
        db = _CappedDB({'t': [{'id': i} for i in range(2500)]})
        rows = pagination.fetch_all(lambda: db.table('t').select('id').order('id'))
        assert [r['id'] for r in rows] == list(range(2500))
        assert db.calls == 3

    def test_exact_multiple_of_page_needs_one_empty_page(self):
        db = _CappedDB({'t': [{'id': i} for i in range(2000)]})
        assert len(pagination.fetch_all(lambda: db.table('t').select('id').order('id'))) == 2000
        assert db.calls == 3

    def test_small_result_is_one_request(self):
        db = _CappedDB({'t': [{'id': 1}]})
        assert pagination.fetch_all(lambda: db.table('t').select('id').order('id')) == [{'id': 1}]
        assert db.calls == 1


class TestExerciseReadsPastTheCap:
    def test_senses_with_exercises_sees_every_sense(self):
        # 200 senses x 13 active exercises = 2,600 rows in one 200-sense chunk.
        db = _CappedDB({'exercises': _exercises(200, 13)})
        assert prestudy.senses_with_exercises(db, list(range(1, 201))) == set(range(1, 201))

    def test_senses_with_exercises_ignores_inactive(self):
        rows = _exercises(3, 1)
        rows[1]['is_active'] = False
        db = _CappedDB({'exercises': rows})
        assert prestudy.senses_with_exercises(db, [1, 2, 3]) == {1, 3}

    def test_load_exercises_returns_every_sense(self):
        db = _CappedDB({'exercises': _exercises(200, 13)})
        out = prestudy._load_exercises(db, list(range(1, 201)))
        assert set(out) == {str(s) for s in range(1, 201)}
