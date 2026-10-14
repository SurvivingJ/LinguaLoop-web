"""TASK-871 / TASK-873 -- ladder intake driven by the per-local-day started quota.

Covers ``admit_daily_new_words`` / ``_maybe_top_up_ladder``:

  * ``local_day_start_utc`` (local midnight as a UTC instant);
  * ``want_raw = E - (U + ST)`` with the review governor at each level, carry-over
    of admitted-but-unstarted words, idempotent repeat calls, the per-call cap;
  * nomination order: Queue A1 (recent test + word-quiz unknowns, recency ranked)
    -> A2 (calibration wrongs, one wrong answer is enough) -> Queue B stub;
  * the supply gate, generation requests for the starved, the shortfall write and
    the one-off rebuild flag.

Same stub-client approach as tests/test_ladder_topup.py: the decisions are
asserted, not the query syntax. SQL RPCs (``ladder_new_word_state``,
``review_governor_state``, ``set_new_words_shortfall``) are stubbed.
"""

from datetime import datetime, timezone

import pytest

from services import day_boundary
from services import practice_session_service as pss
from services import study_plan_service as plan
from services.practice_session_service import (
    LADDER_MIN_EXERCISES_PER_SENSE,
    LADDER_TOPUP_MAX_PER_CALL,
)
from tests.test_ladder_topup import (
    _Query, _Response, _StubDB, _known, _missed, _service, _supply_for,
)

UTC = timezone.utc
RECENT_ISO = '2026-10-10T12:00:00+00:00'
CAL_AT = '2026-10-01T12:00:00+00:00'


# ---------------------------------------------------------------------------
# local_day_start_utc
# ---------------------------------------------------------------------------

def test_local_day_start_resets_at_local_midnight_tokyo():
    before = datetime(2026, 10, 13, 14, 59, tzinfo=UTC)   # 23:59 JST on the 13th
    after = datetime(2026, 10, 13, 15, 1, tzinfo=UTC)     # 00:01 JST on the 14th
    assert day_boundary.local_day_start_utc('Asia/Tokyo', before) == \
        datetime(2026, 10, 12, 15, 0, tzinfo=UTC)
    assert day_boundary.local_day_start_utc('Asia/Tokyo', after) == \
        datetime(2026, 10, 13, 15, 0, tzinfo=UTC)


def test_local_day_start_across_dst_changes():
    # US fall-back day (25 hours): local midnight is still EDT (UTC-4).
    fall = datetime(2026, 11, 1, 12, 0, tzinfo=UTC)
    assert day_boundary.local_day_start_utc('America/New_York', fall) == \
        datetime(2026, 11, 1, 4, 0, tzinfo=UTC)
    # Spring-forward day: midnight is still EST (UTC-5), the jump is at 02:00.
    spring = datetime(2026, 3, 8, 20, 0, tzinfo=UTC)
    assert day_boundary.local_day_start_utc('America/New_York', spring) == \
        datetime(2026, 3, 8, 5, 0, tzinfo=UTC)


@pytest.mark.parametrize('bad', ['Not/AZone', '', None, 'es'])
def test_local_day_start_bad_zone_falls_back_to_utc(bad):
    now = datetime(2026, 10, 13, 14, 59, tzinfo=UTC)
    assert day_boundary.local_day_start_utc(bad, now) == \
        datetime(2026, 10, 13, 0, 0, tzinfo=UTC)


# ---------------------------------------------------------------------------
# harness
# ---------------------------------------------------------------------------

class QuotaDB(_StubDB):
    """_StubDB plus a live quota state and recording of the RPCs intake makes."""

    def __init__(self, shape=None, tz='UTC', has_plan=True, targets=None,
                 calibration=(), **kw):
        super().__init__(**kw)
        self.shape = shape or [1.0] * 7
        self.tz = tz
        self.has_plan = has_plan
        self.targets = targets
        self.calibration = list(calibration)
        self.state_calls = []
        self.calibration_reads = 0
        self.gte_calls = []

    def _insert(self, table, rows):
        if table is not None and getattr(table, '_is_ladder', False):
            self.unstarted += len(rows)
        return super()._insert(table, rows)

    def table(self, name):
        q = super().table(name)
        q._is_ladder = (name == 'user_word_ladder')
        q.gte = lambda col, val: (self.gte_calls.append((name, col, val)) or q)
        return q

    def rpc(self, name, args):
        if name == 'ladder_new_word_state':
            self.state_calls.append(args)
        return super().rpc(name, args)

    def _h_user_study_plans(self, _q):
        if not self.has_plan:
            return _Response(data=[])
        return _Response(data=[{
            'new_words_per_day': self.npd, 'weekday_shape': self.shape,
            'timezone': self.tz, 'excluded_modules': [],
        }])

    def _h_daily_test_loads(self, _q):
        if self.targets is None:
            return _Response(data=[])
        return _Response(data=[{'daily_session_targets': self.targets}])

    def _h_calibration_responses(self, _q):
        self.calibration_reads += 1
        return _Response(data=self.calibration)


def _cal(sense_id, correct, session='s1', at=CAL_AT, applied=True):
    return {
        'anchor_sense_id': sense_id, 'is_correct': correct, 'answered_at': at,
        'session_id': session,
        'calibration_sessions': {
            'mode': 'definition', 'word_language_id': 1,
            'bkt_applied_at': CAL_AT if applied else None,
        },
    }


@pytest.fixture
def governor(monkeypatch):
    """Control the governor level the intake sees."""
    box = {'level': 'normal'}
    monkeypatch.setattr(
        plan, 'get_review_governor',
        lambda db, u, l, d: {'level': box['level'], 'overdue_items': 0},
    )
    return box


def _admit(db, **kw):
    return _service(db).admit_daily_new_words('user-1', 1)


SENSES = list(range(1, 101))


def _full(**kw):
    return QuotaDB(evidence=_missed(SENSES), supply=_supply_for(SENSES), **kw)


# ---------------------------------------------------------------------------
# quota arithmetic
# ---------------------------------------------------------------------------

def test_day_start_boundary_is_passed_to_the_quota_rpc(monkeypatch, governor):
    fixed = datetime(2026, 10, 13, 15, 1, tzinfo=UTC)           # 00:01 JST the 14th
    monkeypatch.setattr(pss, 'local_date', lambda tz: day_boundary.local_date(tz, fixed))
    monkeypatch.setattr(
        pss, 'local_day_start_utc',
        lambda tz: day_boundary.local_day_start_utc(tz, fixed))
    db = _full(tz='Asia/Tokyo', npd=5)
    _admit(db)
    assert db.state_calls[0]['p_day_start'] == '2026-10-13T15:00:00+00:00'


@pytest.mark.parametrize('level,expected', [('normal', 5), ('reduced', 2), ('paused', 0)])
def test_governor_scales_the_quota(governor, level, expected):
    governor['level'] = level
    db = _full(npd=5)
    assert len(_admit(db)['admitted']) == expected


def test_carried_over_unstarted_words_reduce_intake_one_for_one(governor):
    db = _full(npd=5, unstarted=3)
    assert len(_admit(db)['admitted']) == 2


def test_intake_stops_once_unstarted_plus_started_reaches_the_quota(governor):
    db = _full(npd=5, unstarted=1, started_today=4)
    assert _admit(db)['admitted'] == []
    db = _full(npd=5, unstarted=0, started_today=2)
    assert len(_admit(db)['admitted']) == 3


def test_a_repeat_call_the_same_day_admits_nothing(governor):
    db = _full(npd=5)
    first = _admit(db)['admitted']
    second = _admit(db)['admitted']
    assert len(first) == 5 and second == []


def test_per_call_cap_is_a_safety_ceiling(governor):
    db = _full(npd=50)
    assert len(_admit(db)['admitted']) == LADDER_TOPUP_MAX_PER_CALL


def test_no_plan_row_admits_nothing(governor):
    assert _admit(_full(has_plan=False)) == {'admitted': [], 'needs_rebuild': False}


def test_zero_quota_and_rest_days_admit_nothing(governor):
    assert _admit(_full(npd=0))['admitted'] == []
    assert _admit(_full(npd=5, shape=[0.0] * 7))['admitted'] == []


def test_state_rpc_failure_admits_nothing(governor):
    db = _full(npd=5)

    def boom(name, args):
        raise RuntimeError('rpc down')
    db.rpc = boom
    assert _admit(db)['admitted'] == []


def test_maybe_top_up_ladder_delegates_to_admit(governor):
    db = _full(npd=3)
    assert len(_service(db)._maybe_top_up_ladder('user-1', 1)) == 3


# ---------------------------------------------------------------------------
# nomination queues
# ---------------------------------------------------------------------------

def test_queue_a1_is_restricted_to_the_recent_test_window(governor):
    db = QuotaDB(
        npd=10, evidence=_missed([1, 2, 3, 4]), supply=_supply_for([1, 2, 3, 4]),
        recent=[2, 4],
    )
    assert sorted(_admit(db)['admitted']) == [2, 4]


def test_queue_a1_is_recency_ranked(governor):
    db = QuotaDB(
        npd=1,
        evidence=[
            _known(10, word_test_wrong=9, last_evidence_at='2026-08-01T00:00:00+00:00'),
            _known(11, word_test_wrong=1, last_evidence_at='2026-10-01T00:00:00+00:00'),
        ],
        supply=_supply_for([10, 11]),
    )
    assert _admit(db)['admitted'] == [11]


def test_recent_test_window_is_applied_to_the_attempts_read(governor):
    db = QuotaDB(npd=5, evidence=_missed([1]), supply=_supply_for([1]))
    before = datetime.now(UTC)
    _admit(db)
    (table, col, cutoff), = [c for c in db.gte_calls if c[0] == 'test_attempts']
    assert col == 'created_at'
    age = before - datetime.fromisoformat(cutoff)
    assert abs(age.total_seconds() - pss.RECENT_TEST_WINDOW_DAYS * 86400) < 60


def test_a_failed_recent_test_read_admits_nothing(governor):
    db = QuotaDB(npd=5, evidence=_missed([1, 2]), supply=_supply_for([1, 2]))

    def boom(_q):
        raise RuntimeError('boom')
    db._h_test_attempts = boom
    assert _admit(db)['admitted'] == []


def test_a2_admits_one_wrong_calibration_answer_with_no_other_evidence(governor):
    db = QuotaDB(
        npd=5, supply=_supply_for([40]), recent=[],
        calibration=[_cal(40, False)],
    )
    assert _admit(db)['admitted'] == [40]


def test_an_explicit_skip_counts_as_wrong(governor):
    # A skip is stored as is_correct False with answered_at set: same shape.
    db = QuotaDB(npd=5, supply=_supply_for([41]), recent=[], calibration=[_cal(41, False)])
    assert _admit(db)['admitted'] == [41]


def test_a2_ignores_correct_unapplied_out_of_window_and_unanswered(governor):
    rows = [
        _cal(1, True),                                      # latest answer correct
        _cal(2, False, applied=False),                      # evidence never applied
        _cal(3, False, at='2020-01-01T00:00:00+00:00'),     # too old
        dict(_cal(4, False), answered_at=None),             # never answered
        dict(_cal(5, False), is_correct=None),              # no grade
    ]
    db = QuotaDB(npd=5, supply=_supply_for([1, 2, 3, 4, 5]), recent=[], calibration=rows)
    assert _admit(db)['admitted'] == []


def test_a2_skips_known_status_and_excluded_senses(governor):
    db = QuotaDB(
        npd=5, supply=_supply_for([50, 51, 52]), recent=[],
        calibration=[_cal(50, False), _cal(51, False), _cal(52, False)],
        evidence=[{'sense_id': 50, 'status': 'known', 'p_known': 0.99,
                   'evidence_count': 0, 'word_test_wrong': 0,
                   'comprehension_wrong': 0, 'last_evidence_at': ''}],
        already=[52],
    )
    assert _admit(db)['admitted'] == [51]


def test_a2_latest_answer_decides(governor):
    rows = [_cal(60, False, session='s1', at='2026-09-01T00:00:00+00:00'),
            _cal(60, True, session='s2', at='2026-10-01T00:00:00+00:00')]
    db = QuotaDB(npd=5, supply=_supply_for([60]), recent=[], calibration=rows)
    assert _admit(db)['admitted'] == []


def test_a2_orders_by_frequency_then_recency(governor):
    # frequency rank in the stub falls with the sense id: lower id = more frequent
    rows = [_cal(72, False), _cal(70, False), _cal(71, False)]
    db = QuotaDB(npd=3, supply=_supply_for([70, 71, 72]), recent=[], calibration=rows)
    assert _admit(db)['admitted'] == [70, 71, 72]


def test_a1_outranks_a2(governor):
    db = QuotaDB(
        npd=1, evidence=_missed([5]), supply=_supply_for([5, 40]),
        recent=[5], calibration=[_cal(40, False)],
    )
    assert _admit(db)['admitted'] == [5]


def test_a2_is_consulted_only_when_a1_is_short(governor):
    db = QuotaDB(
        npd=2, evidence=_missed([5, 6]), supply=_supply_for([5, 6]),
        recent=[5, 6], calibration=[],
    )
    svc = _service(db)
    calls = []
    orig = svc._calibration_wrong_candidates
    svc._calibration_wrong_candidates = lambda *a, **k: (calls.append(1) or orig(*a, **k))
    assert len(svc.admit_daily_new_words('user-1', 1)['admitted']) == 2
    assert calls == []


def test_a1_ignores_the_calibration_contribution(governor):
    """One calibration wrong bumped evidence_count and word_test_wrong; after the
    subtraction it is no test evidence at all, so A1 must not admit it."""
    row = _known(80, evidence_count=2, p_known=0.9, word_test_wrong=2)
    db = QuotaDB(
        npd=5, evidence=[row], supply={80: 0}, recent=[80],
        calibration=[_cal(80, False), _cal(80, False, session='s2')],
    )
    cands = _service(db)._evidence_candidates('user-1', 1, recency_first=True)
    assert cands == []


def test_a1_keeps_real_test_evidence_beyond_the_calibration_part(governor):
    row = _known(81, evidence_count=3, p_known=0.9, word_test_wrong=3)
    db = QuotaDB(npd=5, evidence=[row], recent=[81], calibration=[_cal(81, False)])
    cands = _service(db)._evidence_candidates('user-1', 1)
    assert [c['sense_id'] for c in cands] == [81]
    assert cands[0]['wrongs'] == 2          # 3 - 1 calibration wrong


def test_queue_b_stub_is_consulted_last_and_returns_nothing(governor):
    db = QuotaDB(npd=3, supply=_supply_for([40]), recent=[], calibration=[_cal(40, False)])
    svc = _service(db)
    asked = []

    def fake_b(user_id, language_id, want, exclude):
        asked.append((want, set(exclude)))
        return []
    svc._nominate_from_lookahead = fake_b
    assert svc.admit_daily_new_words('user-1', 1)['admitted'] == [40]
    assert asked and asked[0][0] == 2             # A1 + A2 left two slots
    assert _service(QuotaDB(npd=1))._nominate_from_lookahead('u', 1, 1, set()) == []


def test_cold_start_without_any_evidence_admits_nothing(governor):
    assert _admit(QuotaDB(npd=5))['admitted'] == []


# ---------------------------------------------------------------------------
# supply gate, generation, shortfall, rebuild
# ---------------------------------------------------------------------------

def test_starved_nominations_reach_generation(governor, monkeypatch):
    from services.vocabulary_ladder import queue_drain
    queued = []
    monkeypatch.setattr(
        queue_drain, 'enqueue',
        lambda db, sense_id, language_id, reason, detail=None: (
            queued.append(sense_id) or True),
    )
    db = QuotaDB(npd=5, evidence=_missed([1, 2]), supply={1: 0, 2: 0})
    assert _admit(db)['admitted'] == []
    assert set(queued) == {1, 2}


def test_shortfall_is_recorded_with_the_unmet_count(governor):
    db = QuotaDB(npd=5, evidence=_missed([1, 2]), supply=_supply_for([1, 2]))
    assert len(_admit(db)['admitted']) == 2
    assert db.shortfalls == [3]


def test_shortfall_failure_never_raises(governor):
    db = QuotaDB(npd=5, evidence=_missed([1]), supply=_supply_for([1]))
    orig = db.rpc

    def rpc(name, args):
        if name == 'set_new_words_shortfall':
            raise RuntimeError('rpc missing')
        return orig(name, args)
    db.rpc = rpc
    assert _admit(db)['admitted'] == [1]


def test_needs_rebuild_only_on_the_first_supply_check(governor):
    base = {'new_words_in_budget': 4, 'new_words_supply_checked': False}
    # Tier C planned 4 inside the budget; only 1 word can be served.
    db = QuotaDB(npd=5, evidence=_missed([1]), supply=_supply_for([1]), targets=dict(base))
    assert _admit(db)['needs_rebuild'] is True
    checked = dict(base, new_words_supply_checked=True)
    db = QuotaDB(npd=5, evidence=_missed([1]), supply=_supply_for([1]), targets=checked)
    assert _admit(db)['needs_rebuild'] is False


def test_no_rebuild_when_the_plan_can_be_served(governor):
    targets = {'new_words_in_budget': 1, 'new_words_supply_checked': False}
    db = QuotaDB(npd=5, evidence=_missed([1, 2]), supply=_supply_for([1, 2]), targets=targets)
    assert _admit(db)['needs_rebuild'] is False
