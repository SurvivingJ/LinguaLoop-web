"""``NewWordAdmissionMixin._gate_and_admit`` -- admitted list, starved list and
the supply-gate read volume, in both modes of the new-word drill.

Drill on  (``intro_drill.ENABLED``): ``admitted = head[:want]`` whatever the
supply; ``starved`` = the unsupplied senses among ``head[:want]``; supply is read
for those ``want`` senses only (a single chunk), not for the whole
``want * NOMINATION_OVERFETCH`` overfetch.
Drill off: ``admitted`` = the supplied senses of the whole overfetched head,
``starved`` = its unsupplied ones, so the whole head is read.

DB-free: a fake ``exercises`` table records every select; ``_request_generation``
is replaced by a recorder.
"""

import math

import pytest

from services import intro_drill
from services.practice.constants import (
    LADDER_MIN_EXERCISES_PER_SENSE, NOMINATION_OVERFETCH, SUPPLY_GATE_CHUNK,
)
from services.practice.new_word_admission import NewWordAdmissionMixin


class _Resp:
    def __init__(self, data):
        self.data = data


class _ExercisesQuery:
    def __init__(self, db):
        self._db = db
        self._ids = []

    def select(self, *_a, **_k):
        return self

    def in_(self, _col, ids):
        self._ids = list(ids)
        return self

    def eq(self, *_a, **_k):
        return self

    def limit(self, *_a, **_k):
        return self

    def execute(self):
        self._db.chunks.append(list(self._ids))
        rows = []
        for sid in self._ids:
            rows += [{'word_sense_id': sid}] * self._db.supply.get(sid, 0)
        return _Resp(rows)


class _FakeDB:
    def __init__(self, supply):
        self.supply = supply
        self.chunks = []

    def table(self, name):
        assert name == 'exercises'
        return _ExercisesQuery(self)


class _Svc(NewWordAdmissionMixin):
    def __init__(self, db):
        self.db = db
        self.generation_requests = []

    def _request_generation(self, sense_ids, language_id):
        self.generation_requests.append((list(sense_ids), language_id))
        return len(sense_ids)


def _run(candidates, want, supplied_ids, drill):
    db = _FakeDB({sid: LADDER_MIN_EXERCISES_PER_SENSE for sid in supplied_ids})
    svc = _Svc(db)
    old = intro_drill.ENABLED
    intro_drill.ENABLED = drill
    try:
        admitted = svc._gate_and_admit(candidates, want, language_id=1)
    finally:
        intro_drill.ENABLED = old
    return admitted, svc.generation_requests, db.chunks


CANDIDATES = list(range(1000, 1000 + 400))
# A mix of supplied and unsupplied senses, inside and beyond the first `want`.
SUPPLIED = set(CANDIDATES[1::3]) | set(CANDIDATES[150:170])


@pytest.mark.parametrize('want', [5, 10, 15])
def test_drill_on_admits_head_regardless_of_supply_and_reports_starved(want):
    admitted, requests, _ = _run(CANDIDATES, want, SUPPLIED, drill=True)

    assert admitted == CANDIDATES[:want]
    expected_starved = [s for s in CANDIDATES[:want] if s not in SUPPLIED]
    assert requests == ([(expected_starved, 1)] if expected_starved else [])


@pytest.mark.parametrize('want', [5, 10, 15])
def test_drill_on_reads_supply_for_the_admitted_senses_only(want):
    _, _, chunks = _run(CANDIDATES, want, SUPPLIED, drill=True)

    assert len(chunks) == 1
    assert chunks[0] == CANDIDATES[:want]


@pytest.mark.parametrize('want', [5, 10, 15])
def test_drill_off_admits_supplied_senses_of_the_whole_overfetch(want):
    admitted, requests, chunks = _run(CANDIDATES, want, SUPPLIED, drill=False)

    head = CANDIDATES[:want * NOMINATION_OVERFETCH]
    assert admitted == [s for s in head if s in SUPPLIED][:want]
    assert requests == [([s for s in head if s not in SUPPLIED], 1)]
    assert len(chunks) == math.ceil(len(head) / SUPPLY_GATE_CHUNK)


def test_drill_off_with_everything_supplied_requests_no_generation():
    admitted, requests, _ = _run(CANDIDATES, 5, set(CANDIDATES), drill=False)

    assert admitted == CANDIDATES[:5]
    assert requests == []


def test_drill_on_with_everything_supplied_requests_no_generation():
    admitted, requests, _ = _run(CANDIDATES, 5, set(CANDIDATES), drill=True)

    assert admitted == CANDIDATES[:5]
    assert requests == []


def test_fewer_candidates_than_want():
    for drill in (True, False):
        admitted, _, _ = _run([7, 8], 5, {8}, drill=drill)
        assert admitted == ([7, 8] if drill else [8])


def test_empty_candidates_or_zero_want_reads_nothing():
    for candidates, want in (([], 5), (CANDIDATES, 0)):
        for drill in (True, False):
            admitted, requests, chunks = _run(candidates, want, SUPPLIED, drill)
            assert (admitted, requests, chunks) == ([], [], [])
