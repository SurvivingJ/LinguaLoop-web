"""Regression tests for ladder intake: the top-up floor and the supply gate.

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
        pack_sense_ids:  senses reachable through the pack bridge.
        already:         sense_ids already on the ladder.
        pack_bridge_missing: raise undefined_table on the bridge read.
    """

    def __init__(
        self,
        eligible_count=0,
        eligible_supply=None,
        supply=None,
        evidence=(),
        wrong_questions=(),
        pack_sense_ids=(),
        already=(),
        packs_selected=True,
        pack_bridge_missing=False,
    ):
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
        self.pack_sense_ids = list(pack_sense_ids)
        self.already = list(already)
        self.packs_selected = packs_selected
        self.pack_bridge_missing = pack_bridge_missing
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

    def rpc(self, name, _args):
        if name != 'get_packs_with_user_selection':
            raise AssertionError('unexpected rpc: %s' % name)
        data = [{'id': 1, 'is_selected': True}] if self.packs_selected else []
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
        # daily_minutes=15 -> target_active_pool == 15
        return _Response(data=[{'daily_minutes': 15}])

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

    def _h_pack_key_words(self, _q):
        if self.pack_bridge_missing:
            raise RuntimeError(
                '{"code":"PGRST205","message":"Could not find the table '
                "'public.pack_key_words' in the schema cache\"}"
            )
        return _Response(data=[{'sense_id': s} for s in self.pack_sense_ids])


def _service(db):
    svc = PracticeSessionService.__new__(PracticeSessionService)
    svc.db = db
    return svc


def _supply_for(sense_ids, n=LADDER_MIN_EXERCISES_PER_SENSE):
    return {s: n for s in sense_ids}


def _top_up(**kwargs):
    db = _StubDB(**kwargs)
    return _service(db)._maybe_top_up_ladder('user-1', 1), db


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
        pack_sense_ids=senses,
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
        pack_sense_ids=senses,
        supply=_supply_for(senses),
    )
    assert len(fresh) == 5, 'a non-empty ladder must still be topped up'
    assert len(db.inserted) == 5


def test_pool_at_floor_is_left_alone():
    """Top-up is a floor, not an unconditional drip — no runaway growth."""
    fresh, db = _top_up(eligible_count=15, pack_sense_ids=range(1, 101))
    assert fresh == []
    assert db.inserted == []


def test_pool_above_floor_is_left_alone():
    fresh, _ = _top_up(eligible_count=40, pack_sense_ids=range(1, 101))
    assert fresh == []


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
        pack_sense_ids=senses,
        supply=_supply_for(senses),
    )
    assert len(fresh) == expected


def test_already_subscribed_senses_are_not_reinserted():
    fresh, _ = _top_up(
        eligible_count=12,
        pack_sense_ids=[1, 2, 3, 4, 5],
        supply=_supply_for([1, 2, 3, 4, 5]),
        already=[1, 2],
    )
    assert set(fresh).isdisjoint({1, 2})
    assert len(fresh) == 3


def test_no_selected_packs_and_no_evidence_returns_empty():
    fresh, db = _top_up(eligible_count=0, packs_selected=False)
    assert fresh == []
    assert db.inserted == []


# ----------------------------------------------------------------------
# 2. The supply gate (T4.1)
# ----------------------------------------------------------------------

def test_senses_without_exercises_are_never_subscribed():
    """THE DEAD END: 21 of 24 live subscriptions had zero exercises."""
    fresh, db = _top_up(
        eligible_count=0,
        pack_sense_ids=[1, 2, 3, 4],
        supply={1: 0, 2: 0, 3: 0, 4: 0},
    )
    assert fresh == []
    assert db.inserted == []


def test_supply_gate_admits_only_covered_senses():
    fresh, _ = _top_up(
        eligible_count=0,
        pack_sense_ids=[1, 2, 3, 4],
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
    db = _StubDB(eligible_count=0, pack_sense_ids=[1, 2, 3])

    def _boom(_q):
        raise RuntimeError('connection reset')

    db._h_exercises = _boom
    assert _service(db)._maybe_top_up_ladder('user-1', 1) == []
    assert db.inserted == []


# ----------------------------------------------------------------------
# 3. The evidence queue (T4.2)
# ----------------------------------------------------------------------

def test_evidence_queue_is_drained_before_packs():
    """A learner who is testing gets their own missed words, not pack filler."""
    fresh, _ = _top_up(
        eligible_count=14,                      # deficit of 1
        evidence=[_known(50, word_test_wrong=3)],
        pack_sense_ids=[1, 2, 3],
        supply=_supply_for([1, 2, 3, 50]),
    )
    assert fresh == [50]


def test_packs_backfill_only_what_evidence_could_not_fill():
    fresh, _ = _top_up(
        eligible_count=12,                      # deficit of 3
        evidence=[_known(50, word_test_wrong=3)],
        pack_sense_ids=[1, 2, 3],
        supply=_supply_for([1, 2, 3, 50]),
    )
    assert fresh[0] == 50, 'evidence first'
    assert len(fresh) == 3
    assert set(fresh[1:]) <= {1, 2, 3}


def test_single_wrong_answer_does_not_subscribe():
    """One miss is a careless click or a bad distractor, not a knowledge gap."""
    fresh, _ = _top_up(
        eligible_count=14,
        evidence=[_known(50, evidence_count=1, p_known=0.9, word_test_wrong=1)],
        supply=_supply_for([50]),
        packs_selected=False,
    )
    assert fresh == []


def test_confident_low_p_known_subscribes_on_thin_evidence():
    fresh, _ = _top_up(
        eligible_count=14,
        evidence=[_known(50, evidence_count=1, p_known=0.05)],
        supply=_supply_for([50]),
        packs_selected=False,
    )
    assert fresh == [50]


def test_repeated_wrong_answers_qualify_without_a_knowledge_row():
    """The wrong-answer signal is evidence in its own right."""
    fresh, _ = _top_up(
        eligible_count=14,
        wrong_questions=[('q1', [77]), ('q2', [77])],
        supply=_supply_for([77]),
        packs_selected=False,
    )
    assert fresh == [77]


def test_one_wrong_question_is_not_enough_without_a_knowledge_row():
    fresh, _ = _top_up(
        eligible_count=14,
        wrong_questions=[('q1', [77])],
        supply=_supply_for([77]),
        packs_selected=False,
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
        packs_selected=False,
    )
    assert fresh == [11]


def test_starved_evidence_falls_through_to_packs():
    """The words the learner actually missed have no exercises — the live case."""
    fresh, _ = _top_up(
        eligible_count=14,
        evidence=[_known(50, word_test_wrong=9)],
        supply={50: 0, 1: LADDER_MIN_EXERCISES_PER_SENSE},
        pack_sense_ids=[1],
    )
    assert fresh == [1]


# ----------------------------------------------------------------------
# 4. The pack bridge must be loud when it is missing (T4.5)
# ----------------------------------------------------------------------

def test_missing_pack_bridge_is_logged_as_an_error_not_swallowed(caplog):
    """A bare `except: logger.warning` is how a table that never existed
    stayed a silent no-op for the whole lifetime of pack-based intake."""
    with caplog.at_level('ERROR', logger='services.practice_session_service'):
        fresh, _ = _top_up(
            eligible_count=0,
            pack_bridge_missing=True,
            packs_selected=True,
        )
    assert fresh == []
    assert any(
        'CONTENT PIPELINE FAULT' in r.getMessage() for r in caplog.records
    ), 'a missing pack->sense bridge must surface as an ERROR'


def test_missing_pack_bridge_does_not_block_the_evidence_queue():
    """Queue A is the priority path; a broken Queue B must not disarm it."""
    fresh, _ = _top_up(
        eligible_count=14,
        evidence=[_known(50, word_test_wrong=3)],
        supply=_supply_for([50]),
        pack_bridge_missing=True,
    )
    assert fresh == [50]


# ----------------------------------------------------------------------
# 5. Demand-driven generation (T4.3)
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
        packs_selected=False,
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
        packs_selected=False,
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
        packs_selected=False,
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
        packs_selected=False,
    )
    assert fresh == [51], 'a queue outage must not cost the servable sense'


# ----------------------------------------------------------------------
# 6. The pool floor counts servable rows, not rows
# ----------------------------------------------------------------------

def test_unservable_subscriptions_do_not_hold_pool_slots():
    """THE LIVE CASE: 24 ladder rows, 3 of them servable, against a floor of
    15. Counting rows says "already full" forever, so the supply gate alone
    would stop new dead rows without ever unblocking the learner who has 21."""
    senses = list(range(1, 101))
    fresh, _ = _top_up(
        eligible_count=24,
        eligible_supply={-1: 3, -2: 3, -3: 3},   # 3 servable of 24
        pack_sense_ids=senses,
        supply=_supply_for(senses),
    )
    assert len(fresh) == LADDER_TOPUP_MAX_PER_CALL, (
        'a pool of unservable words must not count as a full pool'
    )


def test_a_fully_servable_pool_at_the_floor_is_still_left_alone():
    fresh, db = _top_up(eligible_count=15, pack_sense_ids=range(1, 101))
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
        eligible_count=5,
        eligible_supply={-1: 3},                 # 1 servable of 5
        pack_sense_ids=[1],
        supply=_supply_for([1]),
    )
    assert set(queued) == {-2, -3, -4, -5}
