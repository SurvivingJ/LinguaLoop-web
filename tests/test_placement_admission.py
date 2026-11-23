"""Placement evidence reaches practice (TASK-1081, ADR-059): the placement ledger, A2 / A2r on the native
rank-1 sense, the status veto, alternation with A2, A1 subtraction, and the fail-soft read."""
from datetime import datetime, timedelta, timezone

from services.practice import new_word_admission as nwa


class _Resp:
    def __init__(self, data):
        self.data = data


class _Q:
    """A permissive PostgREST chain over a list of rows: eq/in_/is_ filters on top-level keys only."""

    def __init__(self, rows, raise_on_execute=False):
        self.rows, self.f, self.raise_ = rows, [], raise_on_execute
        self.not_ = self

    def select(self, *_a, **_k):
        return self

    def eq(self, col, val):
        if '.' not in col:
            self.f.append(lambda r, c=col, v=val: r.get(c) == v)
        return self

    def in_(self, col, vals):
        vals = set(vals)
        self.f.append(lambda r, c=col: r.get(c) in vals)
        return self

    def is_(self, *_a):
        return self

    def limit(self, *_a):
        return self

    def execute(self):
        if self.raise_:
            raise RuntimeError('column calibration_responses.item_kind does not exist')
        return _Resp([r for r in self.rows if all(f(r) for f in self.f)])


class _DB:
    def __init__(self, tables, broken=()):
        self.tables, self.broken = tables, set(broken)

    def table(self, name):
        return _Q(self.tables.get(name, []), raise_on_execute=name in self.broken)


class _Svc(nwa.NewWordAdmissionMixin):
    def __init__(self, db):
        self.db = db

    def _sense_frequency(self, sense_ids):
        return {s: 5.0 for s in sense_ids}


NOW = datetime.now(timezone.utc)
APPLIED = {'mode': 'placement', 'word_language_id': 1, 'bkt_applied_at': NOW.isoformat()}


def _rows():
    at = (NOW - timedelta(days=1)).isoformat()
    meaning = lambda i, v, ok: dict(id=i, anchor_sense_id=v * 10 + 2, anchor_vocab_id=v, item_kind='meaning',  # noqa: E731
                                    is_correct=ok, answered_at=at, pair_response_id=None, session_id='s1',
                                    calibration_sessions=APPLIED, user_id='u')
    reading = lambda i, pair, ok: dict(id=i, anchor_sense_id=0, anchor_vocab_id=None, item_kind='reading',  # noqa: E731
                                       is_correct=ok, answered_at=at, pair_response_id=pair, session_id='s1',
                                       calibration_sessions=APPLIED, user_id='u')
    return [meaning(1, 100, False),            # A2
            meaning(2, 101, True), reading(3, 2, False),   # A2r (tone or reading miss)
            meaning(4, 102, True), reading(5, 4, True),    # both: no admission
            meaning(6, 103, True),                          # exempt or incomplete: counts as written
            meaning(7, 104, True), reading(8, 7, False)]   # A2r, vetoed below


def _native():
    return [dict(id=v * 10 + 1, vocab_id=v, definition_language_id=1, definition_level='standard', sense_rank=1)
            for v in (100, 101, 102, 104)]


def test_ledger_kinds_and_written_counts():
    svc = _Svc(_DB({'calibration_responses': _rows()}))
    led = svc._placement_ledger('u', 1)
    assert set(led['a2']) == {100} and set(led['a2r']) == {101, 104}
    assert led['written'] == {1002: 1, 1022: 1, 1032: 1}       # A2 and "both" and exempt write; A2r does not


def test_candidates_use_native_senses_and_veto():
    db = _DB({'calibration_responses': _rows(), 'dim_word_senses': _native(),
              'user_vocabulary_knowledge': [dict(user_id='u', sense_id=1041, status='known')]})
    svc = _Svc(db)
    a2, a2r = svc._placement_candidates('u', 1, set(), svc._placement_ledger('u', 1))
    assert a2 == [1001] and a2r == [1011]                         # 104's native sense is vetoed (known)


def test_old_answers_are_not_admitted():
    rows = _rows()
    old = (NOW - timedelta(days=400)).isoformat()
    for r in rows:
        r['answered_at'] = old
    svc = _Svc(_DB({'calibration_responses': rows, 'dim_word_senses': _native()}))
    assert svc._placement_candidates('u', 1, set(), svc._placement_ledger('u', 1)) == ([], [])


def test_unapplied_sessions_are_ignored_and_reads_fail_soft():
    rows = _rows()
    for r in rows:
        r['calibration_sessions'] = dict(APPLIED, bkt_applied_at=None)
    assert _Svc(_DB({'calibration_responses': rows}))._placement_ledger('u', 1) == {'a2': {}, 'a2r': {}, 'written': {}}
    broken = _Svc(_DB({}, broken={'calibration_responses'}))
    assert broken._placement_ledger('u', 1) == {'a2': {}, 'a2r': {}, 'written': {}}


def test_interleave():
    assert nwa._interleave([1, 2, 3], [9]) == [1, 9, 2, 3]
    assert nwa._interleave([], [5, 6]) == [5, 6]
    assert nwa._interleave([1, 2], [2, 3]) == [1, 2, 3]


def test_a1_subtracts_placement_writes():
    svc = _Svc(_DB({}))
    row = dict(sense_id=1002, p_known=0.5, status='learning', evidence_count=1, word_test_wrong=0,
               comprehension_wrong=0, last_evidence_at=NOW.isoformat())
    out = svc._evidence_candidates('u', 1, wrong_by_question={}, ledger={}, rows=[row],
                                   placement_written={1002: 1})
    assert out == []                                              # placement-only evidence is A2's job
    out = svc._evidence_candidates('u', 1, wrong_by_question={}, ledger={}, rows=[dict(row, evidence_count=3, p_known=0.2)],
                                   placement_written={1002: 1})
    assert [c['sense_id'] for c in out] == [1002]
