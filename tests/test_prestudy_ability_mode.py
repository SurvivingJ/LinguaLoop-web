"""The prestudy prior reads the definition-mode calibration ability (C-02).

``user_calibration_state`` is keyed (user_id, language_id, mode). A
pronunciation-mode ability measures reading, not definition knowledge, so it
must never become the prior for "does the learner know this word".
"""

from types import SimpleNamespace

from services import prestudy
from services.calibration_service import MODE_DEFINITION


class _Q:
    def __init__(self, rows):
        self.rows, self.filters = rows, {}

    def select(self, *_a, **_k):
        return self

    def eq(self, col, val):
        self.filters[col] = val
        return self

    def limit(self, _n):
        return self

    def execute(self):
        out = [r for r in self.rows
               if all(r.get(c) == v for c, v in self.filters.items())]
        return SimpleNamespace(data=out)


class _DB:
    def __init__(self, rows):
        self.rows = rows

    def table(self, name):
        assert name == 'user_calibration_state'
        return _Q(self.rows)


ROW = {'user_id': 'u', 'language_id': 3}


def test_pronunciation_ability_is_not_the_definition_prior():
    # The live shape: only the pronunciation row has an ability.
    db = _DB([dict(ROW, mode='pronunciation', ability_zipf=5.49),
              dict(ROW, mode=MODE_DEFINITION, ability_zipf=None)])
    assert prestudy._ability_zipf(db, 'u', 3) == prestudy.DEFAULT_ABILITY_ZIPF


def test_pronunciation_row_alone_falls_back_to_the_default():
    db = _DB([dict(ROW, mode='pronunciation', ability_zipf=5.49)])
    assert prestudy._ability_zipf(db, 'u', 3) == prestudy.DEFAULT_ABILITY_ZIPF


def test_definition_ability_is_used():
    db = _DB([dict(ROW, mode='pronunciation', ability_zipf=5.49),
              dict(ROW, mode=MODE_DEFINITION, ability_zipf=4.2)])
    assert prestudy._ability_zipf(db, 'u', 3) == 4.2


def test_lookup_failure_falls_back_to_the_default():
    class Boom:
        def table(self, _n):
            raise RuntimeError('down')
    assert prestudy._ability_zipf(Boom(), 'u', 3) == prestudy.DEFAULT_ABILITY_ZIPF
