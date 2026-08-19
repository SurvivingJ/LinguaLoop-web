"""
Per-attempt BKT outcome capture (TASK-534).

vw_exercise_type_effectiveness can only measure what gets written down.
user_vocabulary_knowledge keeps a single current p_known and there is no
history table, so once the next attempt on a sense lands, the delta this one
produced is gone for good. The BKT RPC already returns both values; these tests
pin that they reach exercise_attempts, and that a capture failure never costs a
learner their submission.
"""

from unittest.mock import MagicMock

import pytest

from services.practice_session_service import PracticeSessionService


class _Table:
    def __init__(self, recorder, name):
        self._recorder = recorder
        self._name = name
        self._payload = None

    def update(self, payload):
        self._payload = payload
        return self

    def eq(self, column, value):
        self._recorder.append((self._name, self._payload, column, value))
        return self

    def execute(self):
        return MagicMock(data=[])


class _DB:
    def __init__(self, raises=None):
        self.updates = []
        self._raises = raises

    def table(self, name):
        if self._raises:
            raise self._raises
        return _Table(self.updates, name)


@pytest.fixture
def service():
    return PracticeSessionService(_DB())


def _bkt(before, after):
    return {'out_p_known_before': before, 'out_p_known_after': after,
            'out_status': 'learning'}


# ---------------------------------------------------------------------------

def test_captures_both_values_onto_the_attempt(service):
    service._capture_knowledge_outcome('attempt-1', _bkt(0.42, 0.57))

    assert len(service.db.updates) == 1
    table, payload, column, value = service.db.updates[0]
    assert table == 'exercise_attempts'
    assert payload == {'p_known_before': 0.42, 'p_known_after': 0.57}
    assert (column, value) == ('id', 'attempt-1')


def test_captures_a_decrease(service):
    """A wrong first attempt lowers p_known; that is data, not an error."""
    service._capture_knowledge_outcome('attempt-2', _bkt(0.60, 0.48))
    _, payload, _, _ = service.db.updates[0]
    assert payload['p_known_after'] < payload['p_known_before']


def test_zero_valued_before_is_still_captured(service):
    """0.0 is a real starting point — a truthiness check would drop it."""
    service._capture_knowledge_outcome('attempt-3', _bkt(0.0, 0.15))
    _, payload, _, _ = service.db.updates[0]
    assert payload == {'p_known_before': 0.0, 'p_known_after': 0.15}


@pytest.mark.parametrize('bkt_result', [
    None,
    {},
    {'out_p_known_before': 0.4},                    # after missing
    {'out_p_known_after': 0.4},                     # before missing
    {'out_p_known_before': None, 'out_p_known_after': 0.4},
    'not-a-dict',
])
def test_incomplete_bkt_results_write_nothing(service, bkt_result):
    """Half a pair is worse than none: the view would read a bogus delta."""
    service._capture_knowledge_outcome('attempt-4', bkt_result)
    assert service.db.updates == []


def test_missing_attempt_id_writes_nothing(service):
    service._capture_knowledge_outcome(None, _bkt(0.42, 0.57))
    assert service.db.updates == []


def test_a_capture_failure_does_not_propagate():
    """Analytics must never fail a learner's submission."""
    service = PracticeSessionService(_DB(raises=RuntimeError('db down')))
    service._capture_knowledge_outcome('attempt-5', _bkt(0.42, 0.57))   # no raise
