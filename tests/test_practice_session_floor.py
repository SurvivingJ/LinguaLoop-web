"""Tests for the practice session-size floor (plan §4, T4.6).

``get_practice_session`` budgets by *time*, not by item count, so a learner
whose acquisition pool is thin gets a three-item session — indistinguishable,
to them, from a broken engine. The floor tops such a session up from the
maintenance pool (review work they have already met), so a short day reads as
a short day rather than as "there is nothing here".

What the floor must NOT do: invent material, duplicate an item already in the
session, or turn a genuinely empty session into a fake one.
"""

import pytest

from services.practice_session_service import (
    PRACTICE_SESSION_MIN_ITEMS,
    PracticeSessionService,
)


class _Response:
    def __init__(self, data):
        self.data = data


class _Rpc:
    def __init__(self, response):
        self._response = response

    def execute(self):
        return self._response


class _StubDB:
    """Answers one maintenance top-up call with ``maintenance_items``."""

    def __init__(self, maintenance_items=(), fail=False):
        self.maintenance_items = list(maintenance_items)
        self.fail = fail
        self.calls = []

    def rpc(self, name, args):
        assert name == 'get_practice_session'
        self.calls.append(args)
        if self.fail:
            raise RuntimeError('rpc exploded')
        return _Rpc(_Response({'items': self.maintenance_items}))


def _items(prefix, n, mode='acquisition'):
    return [
        {'exercise_id': '%s-%d' % (prefix, i), 'mode': mode}
        for i in range(n)
    ]


def _apply(payload, db, target_minutes=15):
    svc = PracticeSessionService.__new__(PracticeSessionService)
    svc.db = db
    svc._apply_session_floor(payload, 'user-1', 1, target_minutes)
    return payload


def test_short_session_is_topped_up_to_the_floor():
    db = _StubDB(maintenance_items=_items('m', 50, mode='maintenance'))
    payload = _apply({'items': _items('a', 3)}, db)
    assert len(payload['items']) == PRACTICE_SESSION_MIN_ITEMS
    assert payload['floor_backfilled'] == PRACTICE_SESSION_MIN_ITEMS - 3


def test_acquisition_items_keep_their_position_and_order():
    db = _StubDB(maintenance_items=_items('m', 50, mode='maintenance'))
    payload = _apply({'items': _items('a', 3)}, db)
    assert [i['exercise_id'] for i in payload['items'][:3]] == [
        'a-0', 'a-1', 'a-2'
    ]
    assert all(i['mode'] == 'maintenance' for i in payload['items'][3:])


def test_a_full_session_is_left_alone():
    db = _StubDB(maintenance_items=_items('m', 50))
    payload = _apply({'items': _items('a', PRACTICE_SESSION_MIN_ITEMS)}, db)
    assert len(payload['items']) == PRACTICE_SESSION_MIN_ITEMS
    assert 'floor_backfilled' not in payload
    assert db.calls == [], 'no second RPC round-trip when already at the floor'


def test_the_floor_never_duplicates_an_item_already_in_the_session():
    """The maintenance pool overlaps acquisition — the same exercise can be in
    both, and serving it twice in one session is worse than a short session."""
    shared = _items('a', 3)
    db = _StubDB(maintenance_items=shared + _items('m', 50))
    payload = _apply({'items': list(shared)}, db)
    ids = [i['exercise_id'] for i in payload['items']]
    assert len(ids) == len(set(ids))


def test_a_dry_maintenance_pool_leaves_the_session_short():
    """Honest shortness. The floor tops up from real review work or not at all."""
    db = _StubDB(maintenance_items=[])
    payload = _apply({'items': _items('a', 2)}, db)
    assert len(payload['items']) == 2
    assert 'floor_backfilled' not in payload


def test_a_partial_top_up_is_reported_accurately():
    db = _StubDB(maintenance_items=_items('m', 4, mode='maintenance'))
    payload = _apply({'items': _items('a', 2)}, db)
    assert len(payload['items']) == 6
    assert payload['floor_backfilled'] == 4


def test_no_content_reason_is_cleared_once_the_floor_finds_material():
    db = _StubDB(maintenance_items=_items('m', 30, mode='maintenance'))
    payload = _apply(
        {'items': [], 'no_content_reason': 'no_eligible_words'}, db
    )
    assert payload['no_content_reason'] is None
    assert len(payload['items']) == PRACTICE_SESSION_MIN_ITEMS


def test_no_content_reason_survives_a_dry_maintenance_pool():
    db = _StubDB(maintenance_items=[])
    payload = _apply(
        {'items': [], 'no_content_reason': 'no_eligible_words'}, db
    )
    assert payload['no_content_reason'] == 'no_eligible_words'


def test_the_floor_asks_for_the_full_time_budget():
    """The RPC spends minutes, not items: asking for the deficit in minutes
    would come back with roughly that many items regardless of what is due."""
    db = _StubDB(maintenance_items=_items('m', 50, mode='maintenance'))
    _apply({'items': _items('a', 3)}, db, target_minutes=30)
    assert db.calls[0]['p_target_minutes'] == 30
    assert db.calls[0]['p_mode'] == 'maintenance'


def test_an_rpc_failure_is_not_fatal():
    db = _StubDB(fail=True)
    payload = _apply({'items': _items('a', 2)}, db)
    assert len(payload['items']) == 2


def test_an_rpc_error_payload_is_not_treated_as_items():
    class _ErrDB(_StubDB):
        def rpc(self, name, args):
            self.calls.append(args)
            return _Rpc(_Response({'error': 'rpc_failed', 'code': 'E_RPC'}))

    payload = _apply({'items': _items('a', 2)}, _ErrDB())
    assert len(payload['items']) == 2
    assert 'floor_backfilled' not in payload
