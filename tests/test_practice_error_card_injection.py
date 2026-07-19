"""Practice Engine ← Dual-Translation error-card injection (TASK-618).

Covers the session-assembler half of TASK-618: PracticeSessionService.get_session
interleaves due, non-sense-linked error cards into the RPC's normal items, capped
so remediation never crowds out normal practice, best-effort so a remediation
failure never breaks the session. Fakes the Supabase client (RPC + dt tables) in
the "mock every boundary" style of the other dual-translation suites.
"""

import pytest

from services.practice_session_service import PracticeSessionService
from services.dual_translation import cards as dt_cards


class _FakeResult:
    def __init__(self, data):
        self.data = data


class _FakeQuery:
    """Chainable no-op query builder; filters are ignored, execute() returns the
    canned data for this table (matches the other DT suites' fakes)."""

    def __init__(self, data):
        self._data = data

    def select(self, *a, **k):
        return self

    def eq(self, *a, **k):
        return self

    def in_(self, *a, **k):
        return self

    def or_(self, *a, **k):
        return self

    def order(self, *a, **k):
        return self

    def limit(self, *a, **k):
        return self

    def insert(self, *a, **k):
        return self

    def update(self, *a, **k):
        return self

    def execute(self):
        return _FakeResult(self._data)


class _FakeDB:
    def __init__(self, rpc_payload, tables=None):
        self._rpc_payload = rpc_payload
        self._tables = tables or {}

    def rpc(self, name, params):
        return _FakeQuery(self._rpc_payload)

    def table(self, name):
        return _FakeQuery(self._tables.get(name, []))


def _normal_items(n):
    return [
        {'id': f'ex{i}', 'exercise_type': 'mc', 'word_sense_id': i}
        for i in range(1, n + 1)
    ]


def _due_card(card_id, subtype='article'):
    return {
        'id': card_id,
        'card_type': 'cloze',
        'subtype': subtype,
        'prompt_payload': {'prompt': f'p{card_id}', 'answer': f'a{card_id}'},
        'state': 'review',
        'due_date': '2026-07-01',
        'profile_entry_id': 100,
    }


def _dt_tables(due_cards):
    # One profile entry in L2=3 marks these cards as already carded (so the
    # internal generate_cards pass is a no-op) AND satisfies language scoping.
    return {
        'dt_error_profile_entry': [{'id': 100, 'l2_language_id': 3, 'subtype': 'article'}],
        'dt_card': due_cards,
    }


# ---------------------------------------------------------------------------
# End-to-end injection through get_session
# ---------------------------------------------------------------------------

class TestGetSessionInjection:

    def test_due_cards_are_interleaved_into_a_real_session(self):
        payload = {'items': _normal_items(6)}
        due = [_due_card(i, subtype=f's{i % 2}') for i in range(1, 5)]
        svc = PracticeSessionService(db=_FakeDB(payload, _dt_tables(due)))

        out = svc.get_session('u1', language_id=3, mode='maintenance')

        # Cap = min(MAX=3, ceil(6 * 0.34)=3) = 3.
        assert out['error_cards_injected'] == 3
        assert len(out['items']) == 9
        # All six normal items survived.
        normal_ids = {f'ex{i}' for i in range(1, 7)}
        assert normal_ids <= {it['id'] for it in out['items']}
        # Injected items are marked and NOT sense-linked.
        errs = [it for it in out['items'] if it.get('is_error_exercise')]
        assert len(errs) == 3
        assert all(it['word_sense_id'] is None for it in errs)
        assert all(it['type'] == 'error_card' for it in errs)

    def test_empty_normal_session_gets_no_injection(self):
        payload = {'items': []}
        svc = PracticeSessionService(db=_FakeDB(payload, _dt_tables([_due_card(1)])))

        out = svc.get_session('u1', language_id=3, mode='maintenance')

        assert out['items'] == []
        assert 'error_cards_injected' not in out

    def test_injection_failure_is_non_fatal(self, monkeypatch):
        payload = {'items': _normal_items(4)}
        svc = PracticeSessionService(db=_FakeDB(payload, _dt_tables([_due_card(1)])))

        def boom(*a, **k):
            raise RuntimeError('remediation lookup exploded')

        monkeypatch.setattr(dt_cards, 'select_error_exercises_for_practice', boom)

        out = svc.get_session('u1', language_id=3, mode='maintenance')

        # Session still returns, unmodified, with its normal items intact.
        assert len(out['items']) == 4
        assert 'error_cards_injected' not in out

    def test_rpc_error_short_circuits_before_injection(self):
        # A malformed / error RPC payload is returned as-is; nothing is injected.
        svc = PracticeSessionService(db=_FakeDB({'error': 'boom', 'code': 'E_RPC'}))
        out = svc.get_session('u1', language_id=3, mode='maintenance')
        assert out.get('error') == 'boom'
        assert 'error_cards_injected' not in out


# ---------------------------------------------------------------------------
# _interleave_extras (pure spread helper)
# ---------------------------------------------------------------------------

class TestInterleaveExtras:

    def test_extras_are_spread_not_clumped_at_end(self):
        normal = [{'id': f'n{i}'} for i in range(8)]
        extras = [{'id': 'e0'}, {'id': 'e1'}]
        out = PracticeSessionService._interleave_extras(normal, extras)
        ids = [x['id'] for x in out]
        assert len(out) == 10
        # First item is a normal item (extras land AFTER a normal item).
        assert ids[0] == 'n0'
        # Extras are not both jammed at the tail.
        assert ids[-1] != 'e0'
        pos_e0, pos_e1 = ids.index('e0'), ids.index('e1')
        assert pos_e0 < pos_e1
        assert pos_e1 - pos_e0 >= 3  # genuinely spaced apart

    def test_no_extras_returns_copy_of_normal(self):
        normal = [{'id': 'a'}, {'id': 'b'}]
        out = PracticeSessionService._interleave_extras(normal, [])
        assert out == normal
        assert out is not normal

    def test_no_normal_returns_copy_of_extras(self):
        extras = [{'id': 'e'}]
        out = PracticeSessionService._interleave_extras([], extras)
        assert out == extras
        assert out is not extras

    def test_preserves_internal_order_of_both_lists(self):
        normal = [{'id': f'n{i}'} for i in range(3)]
        extras = [{'id': f'e{i}'} for i in range(3)]
        out = PracticeSessionService._interleave_extras(normal, extras)
        ids = [x['id'] for x in out]
        assert [i for i in ids if i.startswith('n')] == ['n0', 'n1', 'n2']
        assert [i for i in ids if i.startswith('e')] == ['e0', 'e1', 'e2']
