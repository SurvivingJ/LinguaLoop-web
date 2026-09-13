"""TASK-769/770/771 — the calibration hot path is one round trip per action.

These are latency-shaped regressions, so what they pin is the SHAPE of the
service's traffic, not arithmetic:

  * grading an answer makes exactly ONE Supabase call, and does not call the
    ability estimator (that was 47 ms of SQL plus a round trip to read two
    integers);
  * an invariant failure comes back from the RPC as `{"error": ...}` and is
    re-raised as CalibrationError, so the route still answers 400 with the same
    text as before;
  * a skip is still graded incorrect rather than dropped;
  * building N items makes exactly ONE call, and `exhausted` means the
    dictionary is finished — not merely that a batch built nothing.

The SQL behaviour itself (option shuffling, skipped anchors, counters) lives in
the database and is exercised against it; what can regress silently in Python is
the call count, which is what these hold.
"""

from unittest.mock import MagicMock

import pytest

from services import calibration_service as cs

USER = 'user-1'


def _session(mode='definition'):
    return {'id': 'session-1', 'word_language_id': 3,
            'definition_language_id': 2, 'mode': mode,
            'items_served': 0, 'items_answered': 0, 'items_correct': 0}


@pytest.fixture
def db(monkeypatch):
    """A fake admin client that records every rpc() and table() call."""
    client = MagicMock()
    client.rpc_calls = []
    client.table_calls = []

    def rpc(name, params):
        client.rpc_calls.append((name, params))
        handle = MagicMock()
        handle.execute.return_value.data = client.rpc_data.get(name)
        return handle

    def table(name):
        client.table_calls.append(name)
        return MagicMock()

    client.rpc_data = {}
    client.rpc.side_effect = rpc
    client.table.side_effect = table
    monkeypatch.setattr(cs, 'get_supabase_admin', lambda: client)
    return client


# --------------------------------------------------------------------------
# TASK-769 — grading
# --------------------------------------------------------------------------

def test_grading_is_one_call_and_never_touches_the_estimator(db, monkeypatch):
    db.rpc_data['calibration_record_answer'] = {
        'is_correct': True, 'correct_position': 2, 'skipped': False,
        'answered': 7, 'correct': 5,
    }
    monkeypatch.setattr(cs, 'ability', lambda *a, **k: pytest.fail(
        'the reveal path must not compute the ability curve'))

    session = _session()
    result = cs.record_answer(USER, session, 42, 2, latency_ms=900)

    assert [name for name, _ in db.rpc_calls] == ['calibration_record_answer']
    assert db.table_calls == []
    assert result == {'is_correct': True, 'correct_position': 2,
                      'skipped': False, 'answered': 7, 'correct': 5}
    # The caller's session dict is brought up to date from the RPC's own counts,
    # rather than incremented from a possibly stale local copy.
    assert session['items_answered'] == 7
    assert session['items_correct'] == 5


@pytest.mark.parametrize('message', [
    'unknown item',
    'item does not belong to this session',
    'item already answered',
    'no such option',
    'item has no recorded options',
])
def test_rpc_errors_become_calibration_errors_verbatim(db, message):
    db.rpc_data['calibration_record_answer'] = {'error': message}

    with pytest.raises(cs.CalibrationError) as exc:
        cs.record_answer(USER, _session(), 42, 0)

    assert str(exc.value) == message


def test_a_skip_is_graded_incorrect_not_dropped(db):
    db.rpc_data['calibration_record_answer'] = {
        'is_correct': False, 'correct_position': 1, 'skipped': True,
        'answered': 1, 'correct': 0,
    }

    result = cs.record_answer(USER, _session(), 42, None)

    assert db.rpc_calls[0][1]['p_position'] is None
    assert result['skipped'] is True
    assert result['is_correct'] is False


def test_a_transport_failure_is_a_calibration_error(db):
    db.rpc.side_effect = RuntimeError('connection reset')

    with pytest.raises(cs.CalibrationError):
        cs.record_answer(USER, _session(), 42, 0)


# --------------------------------------------------------------------------
# TASK-770 — batch item building
# --------------------------------------------------------------------------

def _items(n):
    return [{'response_id': i, 'lemma': 'w%d' % i, 'options': []} for i in range(n)]


def test_a_batch_of_twenty_is_one_call(db):
    db.rpc_data['calibration_build_items'] = {
        'items': _items(20), 'built': 20, 'skipped': 0, 'filled': 0,
        'exhausted': False,
    }
    session = _session()

    batch = cs.build_items(USER, session, count=20)

    assert [name for name, _ in db.rpc_calls] == ['calibration_build_items']
    assert db.table_calls == []
    assert batch['built'] == 20 and len(batch['items']) == 20
    assert session['items_served'] == 20


def test_the_batch_size_is_clamped_to_what_the_sql_will_honour(db):
    db.rpc_data['calibration_build_items'] = {
        'items': [], 'built': 0, 'exhausted': False}

    cs.build_items(USER, _session(), count=10_000)

    assert db.rpc_calls[0][1]['p_count'] == cs.MAX_BATCH


def test_exhausted_means_the_dictionary_is_finished(db):
    db.rpc_data['calibration_build_items'] = {
        'items': [], 'built': 0, 'skipped': 0, 'exhausted': True}

    assert cs.next_item(USER, _session()) is None


def test_a_batch_that_built_nothing_is_not_exhaustion(db):
    # Anchors existed; every one of them had to be skipped. Reporting that as
    # "you have seen the whole dictionary" would be a lie the UI shows the user.
    db.rpc_data['calibration_build_items'] = {
        'items': [], 'built': 0, 'skipped': 9, 'exhausted': False}

    with pytest.raises(cs.CalibrationError):
        cs.next_item(USER, _session())


def test_next_item_returns_the_first_of_the_batch(db):
    db.rpc_data['calibration_build_items'] = {
        'items': _items(1), 'built': 1, 'exhausted': False}

    item = cs.next_item(USER, _session())

    assert item['response_id'] == 0
    assert db.rpc_calls[0][1]['p_count'] == 1
    # The key is never part of an item the client is handed.
    assert 'is_key' not in item and 'correct_position' not in item


def test_discarding_prefetched_items_is_never_fatal(db):
    db.rpc.side_effect = RuntimeError('connection reset')

    assert cs.discard_unanswered(USER, _session()) == 0
