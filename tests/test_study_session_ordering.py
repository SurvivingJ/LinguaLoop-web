"""TASK-703 — session-queue interleaving.

Unit-covers the pure ordering layer in ``routes/study_session.py``:

  * round-robin across test types (no two same-type adjacent while another
    type still has items),
  * practice split into ≤10-minute chunks placed mid-session,
  * deterministic per (user, load_date) so two GETs order identically and
    resume stays stable.

The route wiring (auth, DB reads) is exercised elsewhere; here we pin the
algorithm so a future refactor can't silently regress ordering.
"""

from routes.study_session import (
    _PRACTICE_CHUNK_MAX_MIN,
    _chunk_minutes,
    _build_practice_chunks,
    _valid_block_ids,
    _next_incomplete_index,
    build_session_queue,
)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _mk_tests(spec):
    """spec: list of (test_type, count) -> flat list of test dicts with ids."""
    out = []
    n = 0
    for test_type, count in spec:
        for _ in range(count):
            n += 1
            out.append({'id': f'{test_type}-{n}', 'test_type': test_type})
    return out


def _types(queue):
    return [q['test_type'] for q in queue if q['kind'] == 'test']


def _no_same_type_adjacent_when_alternatives(queue):
    """True unless two same-type tests are adjacent while, at that point, some
    other type still had unplaced items. Approximates the acceptance criterion:
    a same-type run is only OK when every other type is already exhausted by
    that position."""
    from collections import Counter
    seq = _types(queue)
    total = Counter(seq)
    seen = Counter()
    for k in range(len(seq) - 1):
        seen[seq[k]] += 1
        if seq[k] == seq[k + 1]:
            for other, cnt in total.items():
                if other != seq[k] and seen[other] < cnt:
                    return False
    return True


# ---------------------------------------------------------------------------
# _chunk_minutes
# ---------------------------------------------------------------------------

def test_chunk_minutes_splits_at_cap():
    assert _chunk_minutes(25) == [10, 10, 5]
    assert _chunk_minutes(10) == [10]
    assert _chunk_minutes(3) == [3]
    assert _chunk_minutes(20) == [10, 10]


def test_chunk_minutes_zero_and_negative():
    assert _chunk_minutes(0) == []
    assert _chunk_minutes(-5) == []


def test_chunk_minutes_never_exceeds_cap():
    for total in range(0, 200):
        assert all(c <= _PRACTICE_CHUNK_MAX_MIN for c in _chunk_minutes(total))
        assert sum(_chunk_minutes(total)) == max(total, 0)


# ---------------------------------------------------------------------------
# _build_practice_chunks / _valid_block_ids
# ---------------------------------------------------------------------------

def test_build_practice_chunks_ids_and_minutes():
    chunks = _build_practice_chunks(
        {'practice_acquisition_min': 25, 'practice_maintenance_min': 10}, []
    )
    ids = [c['id'] for c in chunks]
    assert ids == ['practice_acq_1', 'practice_acq_2', 'practice_acq_3', 'practice_maint_1']
    acq = [c for c in chunks if c['mode'] == 'acquisition']
    assert [c['minutes'] for c in acq] == [10, 10, 5]
    assert all(c['kind'] == 'practice' for c in chunks)


def test_build_practice_chunks_completion_flag():
    chunks = _build_practice_chunks(
        {'practice_acquisition_min': 20}, ['practice_acq_1']
    )
    done = {c['id']: c['is_completed'] for c in chunks}
    assert done == {'practice_acq_1': True, 'practice_acq_2': False}


def test_build_practice_chunks_empty_targets():
    assert _build_practice_chunks({}, []) == []


def test_valid_block_ids_match_served_ids():
    """Every budgeted chunk is accepted, and nothing over-budget is.

    This used to assert set equality with the served chunks. TASK-533 added the
    speed round, which /complete-block accepts but which is only *offered* when
    the learner has enough mastered words — so equality no longer holds by
    design. The invariant worth keeping is the one the last line always
    protected: a client cannot claim credit for a block the planner never
    budgeted.
    """
    targets = {'practice_acquisition_min': 15, 'practice_maintenance_min': 8}
    valid = _valid_block_ids(targets)
    served = {c['id'] for c in _build_practice_chunks(targets, [])}

    assert served, 'fixture should produce at least one chunk'
    assert served <= valid                       # every budgeted chunk accepted
    assert 'practice_acq_99' not in valid        # over-budget chunk rejected
    assert 'flashcards_99' not in valid          # over-budget surface rejected
    assert 'made_up_block' not in valid          # arbitrary id rejected

    # The speed round is the ONLY id allowed to be valid without being served.
    assert valid - served == {'speed_round_1'}


def test_speed_round_is_offered_only_when_available():
    """The bonus block appears in the queue solely on the availability flag."""
    targets = {'practice_acquisition_min': 10}

    without = build_session_queue([], targets, [], 'user-a', '2026-07-19')
    assert not any(i.get('kind') == 'speed_round' for i in without)

    with_round = build_session_queue(
        [], targets, [], 'user-a', '2026-07-19', speed_round_available=True,
    )
    bonus = [i for i in with_round if i.get('kind') == 'speed_round']
    assert len(bonus) == 1
    assert bonus[0]['id'] == 'speed_round_1'
    assert bonus[0]['is_bonus'] is True
    # Appended, never interleaved: the planned work comes first.
    assert with_round[-1]['kind'] == 'speed_round'


def test_speed_round_completion_flag_round_trips():
    targets = {'practice_acquisition_min': 10}
    queue = build_session_queue(
        [], targets, ['speed_round_1'], 'user-a', '2026-07-19',
        speed_round_available=True,
    )
    bonus = [i for i in queue if i.get('kind') == 'speed_round'][0]
    assert bonus['is_completed'] is True


# ---------------------------------------------------------------------------
# adjacency — no two same-type tests adjacent when an alternative exists
# ---------------------------------------------------------------------------

def test_no_same_type_adjacent_balanced():
    tests = _mk_tests([('listening', 3), ('reading', 3), ('cloze', 2)])
    q = build_session_queue(tests, {}, [], 'user-a', '2026-07-19')
    assert _no_same_type_adjacent_when_alternatives(q)


def test_no_same_type_adjacent_uneven():
    # one dominant type — its trailing run is only allowed once others exhaust
    tests = _mk_tests([('listening', 6), ('reading', 1)])
    q = build_session_queue(tests, {}, [], 'user-a', '2026-07-19')
    assert _no_same_type_adjacent_when_alternatives(q)


def test_no_same_type_adjacent_across_many_seeds():
    tests = _mk_tests([('listening', 4), ('reading', 3), ('cloze', 2), ('speaking', 1)])
    for uid in ('u1', 'u2', 'u3', 'longer-user-id', 'zzz'):
        q = build_session_queue(tests, {}, [], uid, '2026-07-19')
        assert _no_same_type_adjacent_when_alternatives(q), uid


def test_single_type_stays_together_no_error():
    tests = _mk_tests([('listening', 4)])
    q = build_session_queue(tests, {}, [], 'user-a', '2026-07-19')
    assert _types(q) == ['listening'] * 4  # only one type -> unavoidable run OK


# ---------------------------------------------------------------------------
# practice appears mid-session, not only at the end
# ---------------------------------------------------------------------------

def test_practice_chunks_land_mid_session():
    tests = _mk_tests([('listening', 4), ('reading', 4)])  # 8 tests
    targets = {'practice_acquisition_min': 20}  # -> 2 chunks
    q = build_session_queue(tests, targets, [], 'user-a', '2026-07-19')

    practice_idx = [i for i, x in enumerate(q) if x['kind'] == 'practice']
    assert len(practice_idx) == 2
    # neither chunk is the final item, and at least one sits before the midpoint
    assert practice_idx[-1] < len(q) - 1
    assert practice_idx[0] < len(q) / 2


def test_practice_only_when_no_tests():
    targets = {'practice_acquisition_min': 25}
    q = build_session_queue([], targets, [], 'user-a', '2026-07-19')
    assert [x['kind'] for x in q] == ['practice', 'practice', 'practice']


def test_tests_only_when_no_practice():
    tests = _mk_tests([('listening', 2), ('reading', 2)])
    q = build_session_queue(tests, {}, [], 'user-a', '2026-07-19')
    assert all(x['kind'] == 'test' for x in q)
    assert len(q) == 4


# ---------------------------------------------------------------------------
# determinism — two GETs, identical order
# ---------------------------------------------------------------------------

def test_deterministic_same_user_same_date():
    tests = _mk_tests([('listening', 4), ('reading', 3), ('cloze', 2)])
    targets = {'practice_acquisition_min': 25, 'practice_maintenance_min': 10}
    a = build_session_queue(tests, targets, [], 'user-a', '2026-07-19')
    b = build_session_queue(tests, targets, [], 'user-a', '2026-07-19')
    assert [x['id'] for x in a] == [x['id'] for x in b]


def test_order_stable_per_user():
    tests = _mk_tests([('listening', 3), ('reading', 3), ('cloze', 3)])
    a1 = [x['id'] for x in build_session_queue(tests, {}, [], 'user-a', '2026-07-19')]
    a2 = [x['id'] for x in build_session_queue(tests, {}, [], 'user-a', '2026-07-19')]
    assert a1 == a2  # stable per user; the contract is per-user stability


def test_full_queue_preserves_all_items():
    tests = _mk_tests([('listening', 4), ('reading', 3)])
    targets = {'practice_acquisition_min': 25, 'practice_maintenance_min': 10}
    q = build_session_queue(tests, targets, [], 'user-a', '2026-07-19')
    test_ids = {t['id'] for t in tests}
    assert {x['id'] for x in q if x['kind'] == 'test'} == test_ids
    practice_ids = {x['id'] for x in q if x['kind'] == 'practice'}
    assert practice_ids == {
        'practice_acq_1', 'practice_acq_2', 'practice_acq_3', 'practice_maint_1'
    }


# ---------------------------------------------------------------------------
# resume — next_index points at the first incomplete item, in the new order
# ---------------------------------------------------------------------------

def test_next_index_first_incomplete_in_interleaved_order():
    tests = _mk_tests([('listening', 3), ('reading', 3)])
    q = build_session_queue(tests, {}, [], 'user-a', '2026-07-19')
    q[0]['is_completed'] = True
    q[1]['is_completed'] = True
    assert _next_incomplete_index(q) == 2


def test_next_index_all_complete():
    tests = _mk_tests([('listening', 2)])
    q = build_session_queue(tests, {}, [], 'user-a', '2026-07-19')
    for item in q:
        item['is_completed'] = True
    assert _next_incomplete_index(q) == len(q)


def test_completed_practice_chunk_flag_survives_into_queue():
    tests = _mk_tests([('listening', 2), ('reading', 2)])
    targets = {'practice_acquisition_min': 20}
    q = build_session_queue(tests, targets, ['practice_acq_1'], 'user-a', '2026-07-19')
    by_id = {x['id']: x for x in q}
    assert by_id['practice_acq_1']['is_completed'] is True
    assert by_id['practice_acq_2']['is_completed'] is False
