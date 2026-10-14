"""Regression tests for ladder intake: the daily quota and the supply gate.

Session-budget-settings (TASK-871) replaced the pool-floor trigger with a
per-local-day started quota (``want = E - (unstarted + started today)``). The
tests below keep their original intent; the stub now models the quota state
(``unstarted``, ``started_today``) instead of a pool floor, and
``eligible_count`` only drives the servable-pool side effect (demand-driven
generation for subscribed-but-unservable rows). By default ``unstarted``
equals ``eligible_count``, so "N rows already waiting" reduces intake one for
one. Quota-specific cases live in tests/test_ladder_new_word_quota.py.

Two bugs are pinned here.

1. THE STALL. ``_maybe_auto_subscribe_from_packs`` used to return early if the
   user had ANY eligible ladder row. The rows it inserts are state='new', which
   is itself in the eligible set, so the first cold-start seed permanently
   disarmed all later intake — a ladder that stalled at a few untouched words
   never got another word. Live state when found: 24 rows, all 'new', 3
   exercise attempts ever, against ~12k active exercises.

2. THE DEAD END. Even once intake resumed, it subscribed senses with no
   exercises behind them: 21 of those 24 live rows had zero. A subscribed word
   the engine cannot serve is worse than no word, because it occupies a pool
   slot that the floor then refuses to refill.

The tests drive the real methods against a stub Supabase client rather than
asserting on generated SQL, so they stay honest about the *decision* (which
senses get subscribed, and how many) without pinning query syntax.
"""

import pytest

from services.practice_session_service import (
    LADDER_EVIDENCE_MIN_COUNT,
    LADDER_MIN_EXERCISES_PER_SENSE,
    LADDER_TOPUP_MAX_PER_CALL,
    PracticeSessionService,
)


class _Response:
    def __init__(self, data=None, count=None):
        self.data = data
        self.count = count


class _Query:
    """Chainable query stub. Records filters; defers the answer to a handler.

    ``handler`` receives the accumulated filter state so a test can assert on
    *what was asked for*, not just on what came back.
    """

    def __init__(self, handler):
        self._handler = handler
        self.columns = ''
        self.eq_filters = {}
        self.in_values = {}
        self.or_filter = None

    # -- filter capture --
    def select(self, columns, **_kwargs):
        self.columns = columns
        return self

    def eq(self, column, value):
        self.eq_filters[column] = value
        return self

    def in_(self, column, values):
        self.in_values[column] = list(values)
        return self

    def or_(self, expr):
        self.or_filter = expr
        return self

    def __getattr__(self, _name):
        # limit / order / single / ... are all no-ops for these tests.
        return lambda *a, **k: self

    def execute(self):
        return self._handler(self)


class _StubDB:
    """Minimal stand-in for the Supabase client used by the service.

    Args:
        eligible_count:  rows counted by the eligibility read.
        supply:          sense_id -> number of active exercises.
        evidence:        rows the user_vocabulary_knowledge read returns.
        wrong_questions: list of (question_id, [sense_id, ...]) missed.
        already:         sense_ids already on the ladder.
        unstarted:       admitted-but-never-attempted words (default: eligible_count).
        started_today:   words whose first attempt is today.
        npd:             new_words_per_day (weekday shape is all ones).
        recent:          senses carried by recent tests (default: every sense
                         that has any evidence, so evidence alone decides).
    """

    def __init__(
        self,
        eligible_count=0,
        eligible_supply=None,
        supply=None,
        evidence=(),
        wrong_questions=(),
        already=(),
        unstarted=None,
        started_today=0,
        npd=15,
        recent=None,
    ):
        self.unstarted = eligible_count if unstarted is None else unstarted
        self.started_today = started_today
        self.npd = npd
        self.shortfalls = []
        if recent is None:
            recent = [r['sense_id'] for r in evidence]
            for _qid, sids in wrong_questions:
                recent.extend(sids)
        self.recent = list(recent)
        self.eligible_count = eligible_count
        # Senses standing in for the existing eligible pool. By default every
        # one of them is servable, so `eligible_count` still means what the
        # tests below assume; pass eligible_supply to model a pool that is
        # full of rows the engine cannot serve (the live case).
        self.eligible_senses = list(range(-1, -(eligible_count + 1), -1))
        self.eligible_supply = (
            dict(eligible_supply) if eligible_supply is not None
            else {s: LADDER_MIN_EXERCISES_PER_SENSE
                  for s in self.eligible_senses}
        )
        self.supply = dict(supply or {})
        self.evidence = list(evidence)
        self.wrong_questions = list(wrong_questions)
        self.already = list(already)
        self.inserted = []
        self.supply_gate_calls = []

    def table(self, name):
        handler = getattr(self, '_h_' + name, None)
        if handler is None:
            raise AssertionError('unexpected table: %s' % name)
        table = _Query(handler)
        table.insert = lambda rows: self._insert(table, rows)
        return table

    def _insert(self, table, rows):
        self.inserted.extend(rows)
        table._handler = lambda _q: _Response(data=rows)
        return table

    def rpc(self, name, args):
        if name == 'ladder_new_word_state':
            data = {
                'unstarted': self.unstarted,
                'started_today': self.started_today,
                'unstarted_sense_ids': [],
            }
        elif name == 'review_governor_state':
            data = {'level': 'normal', 'overdue_items': 0, 'due_items': 0}
        elif name == 'set_new_words_shortfall':
            self.shortfalls.append(args['p_shortfall'])
            data = True
        else:
            raise AssertionError('unexpected rpc: %s' % name)
        return _Query(lambda _q: _Response(data=data))

    # -- per-table handlers --

    def _h_user_word_ladder(self, q):
        # The eligibility read joins through dim_word_senses and asks for an
        # exact count; the subscribed-ids read selects sense_id alone.
        if 'dim_word_senses' in q.columns:
            return _Response(
                data=[{'sense_id': s} for s in self.eligible_senses]
            )
        return _Response(data=[{'sense_id': s} for s in self.already])

    def _h_user_study_plans(self, _q):
        return _Response(data=[{
            'daily_minutes': 15,
            'new_words_per_day': self.npd,
            'weekday_shape': [1.0] * 7,
            'timezone': 'UTC',
            'excluded_modules': [],
        }])

    def _h_daily_test_loads(self, _q):
        return _Response(data=[])

    def _h_test_attempts(self, _q):
        return _Response(data=[{'test_id': 1}])

    def _h_tests(self, _q):
        return _Response(data=[{'id': 1, 'vocab_sense_ids': self.recent}])

    def _h_questions(self, _q):
        return _Response(data=[])

    def _h_calibration_responses(self, _q):
        return _Response(data=[])

    def _h_user_vocabulary_knowledge(self, _q):
        return _Response(data=self.evidence)

    def _h_question_attempt_results(self, _q):
        return _Response(data=[
            {'question_id': qid, 'questions': {'sense_ids': sids}}
            for qid, sids in self.wrong_questions
        ])

    def _h_exercises(self, q):
        asked = q.in_values.get('word_sense_id', [])
        self.supply_gate_calls.append(list(asked))
        rows = []
        for sid in asked:
            n = self.eligible_supply.get(sid, self.supply.get(sid, 0))
            rows.extend([{'word_sense_id': sid}] * n)
        return _Response(data=rows)

    def _h_dim_word_senses(self, q):
        # Frequency descends with sense_id so ordering is predictable.
        return _Response(data=[
            {'id': sid, 'dim_vocabulary': {'frequency_rank': 100.0 - sid}}
            for sid in q.in_values.get('id', [])
        ])

def _service(db):
    svc = PracticeSessionService.__new__(PracticeSessionService)
    svc.db = db
    return svc


def _supply_for(sense_ids, n=LADDER_MIN_EXERCISES_PER_SENSE):
    return {s: n for s in sense_ids}


def _top_up(**kwargs):
    db = _StubDB(**kwargs)
    return _service(db)._maybe_top_up_ladder('user-1', 1), db


def _missed(sense_ids):
    """Evidence rows that clearly qualify: each sense missed three times."""
    return [_known(s, word_test_wrong=3) for s in sense_ids]


def _known(sense_id, evidence_count=LADDER_EVIDENCE_MIN_COUNT, **over):
    row = {
        'sense_id': sense_id,
        'p_known': 0.9,
        'status': 'learning',
        'evidence_count': evidence_count,
        'word_test_wrong': 0,
        'comprehension_wrong': 0,
        'last_evidence_at': '2026-08-01T00:00:00+00:00',
    }
    row.update(over)
    return row


# ----------------------------------------------------------------------
# 1. The floor (regression: intake used to disarm itself)
# ----------------------------------------------------------------------

def test_empty_ladder_fills_up_to_the_per_call_cap():
    """Cold start still works — and is capped, not target_new_rate-sized."""
    senses = list(range(1, 101))
    fresh, db = _top_up(
        eligible_count=0,
        evidence=_missed(senses),
        supply=_supply_for(senses),
    )
    assert len(fresh) == LADDER_TOPUP_MAX_PER_CALL
    assert len(db.inserted) == LADDER_TOPUP_MAX_PER_CALL
    assert all(r['word_state'] == 'new' for r in db.inserted)


def test_partially_stalled_ladder_still_receives_words():
    """THE REGRESSION: 24 rows all 'new' used to return [] forever.

    With a floor of 15 and 10 eligible the deficit is 5 — the old code
    returned [] the moment eligible_count was non-zero.
    """
    senses = list(range(1, 101))
    fresh, db = _top_up(
        eligible_count=10,
        evidence=_missed(senses),
        supply=_supply_for(senses),
    )
    assert len(fresh) == 5, 'a non-empty ladder must still be topped up'
    assert len(db.inserted) == 5


def test_quota_already_met_is_left_alone():
    """Intake tops up to the quota; it is not an unconditional drip."""
    fresh, db = _top_up(eligible_count=15, evidence=_missed(range(1, 101)))
    assert fresh == []
    assert db.inserted == []


def test_waiting_words_above_quota_are_left_alone():
    fresh, _ = _top_up(eligible_count=40, evidence=_missed(range(1, 101)))
    assert fresh == []


def test_a_large_existing_pool_no_longer_suppresses_admission():
    """The pool-floor trigger is gone: 40 servable ladder rows used to mean
    "already full" forever. Only unstarted + started-today words count now."""
    senses = list(range(1, 101))
    fresh, _ = _top_up(
        eligible_count=40, unstarted=0, started_today=0,
        evidence=_missed(senses), supply=_supply_for(senses),
    )
    assert len(fresh) == LADDER_TOPUP_MAX_PER_CALL


@pytest.mark.parametrize('eligible,expected', [
    (0, LADDER_TOPUP_MAX_PER_CALL),  # capped
    (5, 10),
    (14, 1),
    (15, 0),
])
def test_deficit_arithmetic(eligible, expected):
    senses = list(range(1, 101))
    fresh, _ = _top_up(
        eligible_count=eligible,
        evidence=_missed(senses),
        supply=_supply_for(senses),
    )
    assert len(fresh) == expected


def test_already_subscribed_senses_are_not_reinserted():
    fresh, _ = _top_up(
        eligible_count=12,
        evidence=_missed([1, 2, 3, 4, 5]),
        supply=_supply_for([1, 2, 3, 4, 5]),
        already=[1, 2],
    )
    assert set(fresh).isdisjoint({1, 2})
    assert len(fresh) == 3


def test_no_evidence_returns_empty():
    fresh, db = _top_up(eligible_count=0)
    assert fresh == []
    assert db.inserted == []


# ----------------------------------------------------------------------
# 2. The supply gate (T4.1)
# ----------------------------------------------------------------------

def test_senses_without_exercises_are_never_subscribed():
    """THE DEAD END: 21 of 24 live subscriptions had zero exercises."""
    fresh, db = _top_up(
        eligible_count=0,
        evidence=_missed([1, 2, 3, 4]),
        supply={1: 0, 2: 0, 3: 0, 4: 0},
    )
    assert fresh == []
    assert db.inserted == []


def test_supply_gate_admits_only_covered_senses():
    fresh, _ = _top_up(
        eligible_count=0,
        evidence=_missed([1, 2, 3, 4]),
        supply={
            1: LADDER_MIN_EXERCISES_PER_SENSE,
            2: LADDER_MIN_EXERCISES_PER_SENSE - 1,   # one short
            3: LADDER_MIN_EXERCISES_PER_SENSE + 9,
            4: 0,
        },
    )
    assert sorted(fresh) == [1, 3]


def test_supply_gate_fails_closed_when_the_lookup_breaks():
    """An unverifiable sense must not be admitted — that is the dead end."""
    db = _StubDB(eligible_count=0, evidence=_missed([1, 2, 3]))

    def _boom(_q):
        raise RuntimeError('connection reset')

    db._h_exercises = _boom
    assert _service(db)._maybe_top_up_ladder('user-1', 1) == []
    assert db.inserted == []


# ----------------------------------------------------------------------
# 3. The evidence queue (T4.2)
# ----------------------------------------------------------------------

def test_single_wrong_answer_does_not_subscribe():
    """One miss is a careless click or a bad distractor, not a knowledge gap."""
    fresh, _ = _top_up(
        eligible_count=14,
        evidence=[_known(50, evidence_count=1, p_known=0.9, word_test_wrong=1)],
        supply=_supply_for([50]),
    )
    assert fresh == []


def test_confident_low_p_known_subscribes_on_thin_evidence():
    fresh, _ = _top_up(
        eligible_count=14,
        evidence=[_known(50, evidence_count=1, p_known=0.05)],
        supply=_supply_for([50]),
    )
    assert fresh == [50]


def test_repeated_wrong_answers_qualify_without_a_knowledge_row():
    """The wrong-answer signal is evidence in its own right."""
    fresh, _ = _top_up(
        eligible_count=14,
        wrong_questions=[('q1', [77]), ('q2', [77])],
        supply=_supply_for([77]),
    )
    assert fresh == [77]


def test_one_wrong_question_is_not_enough_without_a_knowledge_row():
    fresh, _ = _top_up(
        eligible_count=14,
        wrong_questions=[('q1', [77])],
        supply=_supply_for([77]),
    )
    assert fresh == []


def test_evidence_is_ranked_by_wrong_count():
    fresh, _ = _top_up(
        eligible_count=14,                      # deficit of 1
        evidence=[
            _known(10, word_test_wrong=1),
            _known(11, word_test_wrong=5),
            _known(12, word_test_wrong=2),
        ],
        supply=_supply_for([10, 11, 12]),
    )
    assert fresh == [11]


# ----------------------------------------------------------------------
# 4. Demand-driven generation (T4.3)
# ----------------------------------------------------------------------

def test_starved_nominations_are_queued_for_generation(monkeypatch):
    """This is what inverts generation from speculative to demand-driven: the
    budget goes to words the learner has demonstrably failed, not to a 31st
    variant of a word that already has 33 exercises."""
    from services.vocabulary_ladder import queue_drain

    queued = []
    monkeypatch.setattr(
        queue_drain, 'enqueue',
        lambda db, sense_id, language_id, reason, detail=None: (
            queued.append((sense_id, reason)) or True
        ),
    )
    _top_up(
        eligible_count=14,
        evidence=[
            _known(50, word_test_wrong=9),
            _known(51, word_test_wrong=8),
        ],
        supply={50: 0, 51: 0},
    )
    assert {sid for sid, _ in queued} == {50, 51}
    assert all(r == queue_drain.REASON_SUBSCRIBE_TOPUP for _, r in queued)


def test_supplied_senses_are_not_queued_for_generation(monkeypatch):
    from services.vocabulary_ladder import queue_drain

    queued = []
    monkeypatch.setattr(
        queue_drain, 'enqueue',
        lambda db, sense_id, language_id, reason, detail=None: (
            queued.append(sense_id) or True
        ),
    )
    fresh, _ = _top_up(
        eligible_count=14,
        evidence=[_known(50, word_test_wrong=9)],
        supply=_supply_for([50]),
    )
    assert fresh == [50]
    assert queued == []


def test_generation_requests_are_capped_per_call(monkeypatch):
    """At ~3% coverage an unbounded pass would enqueue a learner's whole
    vocabulary history on their first session request."""
    from services.practice_session_service import DEMAND_GENERATION_MAX_PER_CALL
    from services.vocabulary_ladder import queue_drain

    queued = []
    monkeypatch.setattr(
        queue_drain, 'enqueue',
        lambda db, sense_id, language_id, reason, detail=None: (
            queued.append(sense_id) or True
        ),
    )
    _top_up(
        eligible_count=14,
        evidence=[_known(i, word_test_wrong=3) for i in range(100, 160)],
        supply={},
    )
    assert len(queued) == DEMAND_GENERATION_MAX_PER_CALL


def test_a_broken_generation_queue_does_not_break_the_session(monkeypatch):
    from services.vocabulary_ladder import queue_drain

    def _boom(*a, **k):
        raise RuntimeError('generation_queue is down')

    monkeypatch.setattr(queue_drain, 'enqueue', _boom)
    fresh, _ = _top_up(
        eligible_count=14,
        evidence=[_known(50, word_test_wrong=9), _known(51)],
        supply={50: 0, 51: LADDER_MIN_EXERCISES_PER_SENSE},
    )
    assert fresh == [51], 'a queue outage must not cost the servable sense'


# ----------------------------------------------------------------------
# 5. The pool floor counts servable rows, not rows
# ----------------------------------------------------------------------

def test_unservable_subscriptions_do_not_block_intake():
    """THE LIVE CASE: 24 ladder rows, 3 of them servable. Intake is driven by the
    quota state, not by the pool, so dead rows never hold intake shut."""
    senses = list(range(1, 101))
    fresh, _ = _top_up(
        eligible_count=24, unstarted=0,
        eligible_supply={-1: 3, -2: 3, -3: 3},   # 3 servable of 24
        evidence=_missed(senses),
        supply=_supply_for(senses),
    )
    assert len(fresh) == LADDER_TOPUP_MAX_PER_CALL


def test_a_quota_met_by_waiting_words_is_still_left_alone():
    fresh, db = _top_up(eligible_count=15, evidence=_missed(range(1, 101)))
    assert fresh == []
    assert db.inserted == []


def test_unservable_subscriptions_are_queued_for_generation(monkeypatch):
    """A learner already subscribed and getting nothing is the strongest
    demand-driven generation candidate there is."""
    from services.vocabulary_ladder import queue_drain

    queued = []
    monkeypatch.setattr(
        queue_drain, 'enqueue',
        lambda db, sense_id, language_id, reason, detail=None: (
            queued.append(sense_id) or True
        ),
    )
    _top_up(
        eligible_count=5, unstarted=0,
        eligible_supply={-1: 3},                 # 1 servable of 5
        evidence=_missed([1]),
        supply=_supply_for([1]),
    )
    assert set(queued) == {-2, -3, -4, -5}
