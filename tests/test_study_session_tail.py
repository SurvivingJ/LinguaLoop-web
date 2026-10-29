"""TASK-872 / TASK-867 -- the optional tail, governor fields and speed-round gate
in ``routes/study_session.py``.

Pure helpers (``compute_governor_and_tail``, ``_build_tail_queue``,
``_tail_window_ids``) are tested directly; ``GET /api/study-session`` and
``POST /complete-block`` are driven through their undecorated functions with a
stub client, a stub practice service and a stub test service.
"""

import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from flask import Flask, g

from routes import study_session as ss
from routes.study_session import (
    _build_tail_queue, _is_main_complete, _tail_window_ids, _valid_block_ids,
    build_session_queue, compute_governor_and_tail,
)

CAP = ss._tail_offer_max_min()


def _state(**over):
    state = {
        'timezone': 'UTC', 'excluded': [], 'quota': 5, 'effective': 5,
        'level': 'normal', 'unstarted': 3, 'started_today': 2,
        'unstarted_sense_ids': [1, 2, 3],
        'governor': {'level': 'normal', 'overdue_items': 0, 'overdue_minutes': 0.0,
                     'threshold_minutes': 3.0, 'due_items': 6, 'item_seconds': 20.0},
    }
    state.update(over)
    return state


DONE = [{'kind': 'test', 'id': 't1', 'is_completed': True}]
OPEN = [{'kind': 'test', 'id': 't1', 'is_completed': False}]


# ---------------------------------------------------------------------------
# tail composition
# ---------------------------------------------------------------------------

def test_tail_is_null_until_every_required_item_is_complete():
    out = compute_governor_and_tail(_state(), OPEN, [], 3.0)
    assert out['tail'] is None and out['tail_queue'] == []
    assert out['governor'] is not None            # the banner does not wait


def test_bonus_items_do_not_hold_the_tail_back():
    queue = DONE + [{'kind': 'speed_round', 'id': 'speed_round_1', 'is_bonus': True,
                     'is_completed': False}]
    assert _is_main_complete(queue)
    assert compute_governor_and_tail(_state(), queue, [], 3.0)['tail'] is not None


def test_tail_counts_and_minutes():
    out = compute_governor_and_tail(_state(), DONE, [], 3.0)
    # reviews: 6 due items x 20s = 2 min; words: min(E - ST, U) = min(3, 3) = 3
    assert out['tail'] == {
        'reviews_left_items': 6, 'reviews_left_minutes': 2.0,
        'new_words_left': 3, 'new_words_left_minutes': 9,
    }


def test_new_words_left_is_bounded_by_unstarted_and_quota():
    assert compute_governor_and_tail(
        _state(unstarted=1), DONE, [], 3.0)['tail']['new_words_left'] == 1
    assert compute_governor_and_tail(
        _state(started_today=5, unstarted=4), DONE, [], 3.0)['tail']['new_words_left'] == 0


def test_tail_is_null_when_nothing_is_left():
    state = _state(unstarted=0, governor=dict(_state()['governor'], due_items=0))
    out = compute_governor_and_tail(state, DONE, [], 3.0)
    assert out['tail'] is None and out['tail_queue'] == []


def test_reviews_come_before_new_words_and_ids_are_namespaced():
    out = compute_governor_and_tail(_state(), DONE, [], 3.0)
    ids = [i['id'] for i in out['tail_queue']]
    assert ids == ['tail_maint_1', 'tail_acq_1']
    modes = [i['mode'] for i in out['tail_queue']]
    assert modes == ['maintenance', 'acquisition']
    for item in out['tail_queue']:
        assert item['kind'] == 'practice'
        assert item['is_bonus'] is True and item['is_tail'] is True
        assert item['is_completed'] is False
        assert item['minutes'] <= ss._PRACTICE_CHUNK_MAX_MIN


def test_at_most_the_cap_is_offered_per_round_reviews_first():
    big = _state(governor=dict(_state()['governor'], due_items=300), unstarted=10,
                 effective=10, started_today=0)
    queue = compute_governor_and_tail(big, DONE, [], 3.0)['tail_queue']
    assert sum(i['minutes'] for i in queue) == CAP
    assert {i['mode'] for i in queue} == {'maintenance'}     # reviews fill the round
    # 20 min of reviews = two 10-minute chunks
    assert [i['id'] for i in queue] == ['tail_maint_1', 'tail_maint_2']


def test_words_get_the_remainder_of_the_round():
    queue = _build_tail_queue(12, 30, [])
    mins = {i['mode']: 0 for i in queue}
    for i in queue:
        mins[i['mode']] += i['minutes']
    assert mins == {'maintenance': 12, 'acquisition': CAP - 12}


def test_ids_continue_across_rounds_without_colliding():
    done = ['tail_maint_1', 'tail_maint_2', 'tail_acq_1', 'practice_acq_1']
    queue = _build_tail_queue(5, 5, done)
    assert [i['id'] for i in queue] == ['tail_maint_3', 'tail_acq_2']


def test_progress_ignores_tail_items():
    queue = build_session_queue([], {'practice_acquisition_min': 10}, [], 'u', '2026-10-13')
    assert all(not str(i.get('id', '')).startswith('tail_') for i in queue)
    assert not any(i.get('is_tail') for i in queue)


def test_governor_fields_match_the_spec():
    out = compute_governor_and_tail(
        _state(level='reduced', effective=2,
               governor={'level': 'reduced', 'overdue_items': 9, 'overdue_minutes': 3.0,
                         'threshold_minutes': 2.0, 'due_items': 9, 'item_seconds': 20.0}),
        OPEN, [], 3.0)
    assert out['governor'] == {
        'level': 'reduced', 'overdue_items': 9, 'overdue_minutes': 3.0,
        'threshold_minutes': 2.0, 'new_words_quota': 5, 'new_words_effective': 2,
    }


def test_no_plan_state_means_no_governor_and_no_tail():
    assert compute_governor_and_tail(None, DONE, [], 3.0) == {
        'governor': None, 'tail': None, 'tail_queue': []}


def test_tests_only_puts_all_vocabulary_in_the_tail():
    """Under tests_only the main queue holds no practice chunks, so once the tests
    and surfaces are done every due review and new word is offered here."""
    targets = {'practice_acquisition_min': 0, 'practice_maintenance_min': 0}
    queue = build_session_queue([], targets, [], 'u', '2026-10-13')
    assert not [i for i in queue if i['kind'] == 'practice']
    out = compute_governor_and_tail(_state(), queue, [], 3.0)
    assert out['tail']['reviews_left_items'] == 6 and out['tail']['new_words_left'] == 3


def test_practice_excluded_means_no_review_tail_and_a_normal_governor():
    state = _state(excluded=['practice'], level='normal',
                   governor={'level': 'normal'})
    out = compute_governor_and_tail(state, DONE, [], 3.0)
    assert out['tail']['reviews_left_items'] == 0
    assert [i['mode'] for i in out['tail_queue']] == ['acquisition']


# ---------------------------------------------------------------------------
# complete-block validity
# ---------------------------------------------------------------------------

def test_valid_block_ids_are_unchanged_without_tail_ids():
    targets = {'practice_acquisition_min': 15}
    assert not {i for i in _valid_block_ids(targets) if i.startswith('tail_')}


def test_tail_window_accepts_current_and_completed_rejects_stale_ids():
    done = ['tail_maint_1', 'tail_maint_2']
    window = _tail_window_ids(done)
    assert {'tail_maint_3', 'tail_maint_4', 'tail_acq_1', 'tail_acq_2'} <= window
    assert 'tail_maint_1' in window                  # idempotent re-POST
    assert 'tail_maint_9' not in window              # beyond a round: stale / invented
    assert 'tail_acq_9' not in window
    ids = _valid_block_ids({}, extra_ids=window)
    assert 'tail_acq_1' in ids and 'tail_acq_9' not in ids


# ---------------------------------------------------------------------------
# route plumbing
# ---------------------------------------------------------------------------

class _Q:
    def __init__(self, data):
        self._data = data

    def __getattr__(self, _n):
        return lambda *a, **k: self

    def execute(self):
        return SimpleNamespace(data=self._data)


class _DB:
    def __init__(self, targets, completed=()):
        self.row = {'id': 7, 'daily_session_targets': targets,
                    'completed_blocks': list(completed)}
        self.updates = []

    def table(self, name):
        if name == 'daily_test_loads':
            q = _Q([self.row])
            q.update = lambda payload: (self.updates.append(payload) or q)
            return q
        return _Q([])

    def rpc(self, *a, **k):
        return _Q(None)


class _Practice:
    def __init__(self, state, intake=None):
        self.state = state
        self.intake = intake or {'admitted': [], 'needs_rebuild': False}
        self.admit_calls = 0

    def admit_daily_new_words(self, user_id, language_id):
        self.admit_calls += 1
        return self.intake

    def new_word_state(self, user_id, language_id):
        return self.state


@pytest.fixture
def app():
    return Flask(__name__)


def _call_get(app, monkeypatch, db, practice, speed=True, tests=(), query=''):
    test_service = MagicMock()
    test_service.get_or_create_daily_load.return_value = {
        'tests': list(tests), 'load_date': '2026-10-13'}
    monkeypatch.setattr(ss, 'get_test_service', lambda: test_service)
    monkeypatch.setattr(ss, 'get_supabase_admin', lambda: db)
    monkeypatch.setattr(ss, '_practice_service', lambda: practice)
    monkeypatch.setattr(ss, '_today_iso', lambda *a: '2026-10-13')
    monkeypatch.setattr(ss, '_mpnw', lambda db, lang: 3.0)
    composer = MagicMock()
    composer.has_enough_mastered.return_value = speed
    import services.vocabulary_ladder.speed_round as sr
    monkeypatch.setattr(sr, 'get_speed_round_composer', lambda: composer)
    with app.test_request_context('/api/study-session?language_id=1' + query):
        g.current_user_id = 'user-1'
        resp = ss.get_study_session.__wrapped__()
    resp = resp[0] if isinstance(resp, tuple) else resp
    body = json.loads(resp.get_data())
    return body.get('data', body), test_service


def test_get_returns_governor_tail_and_tail_queue(app, monkeypatch):
    db = _DB({'practice_acquisition_min': 0, 'practice_maintenance_min': 0},
             completed=[])
    data, _ = _call_get(app, monkeypatch, db, _Practice(_state()), speed=False)
    assert data['governor']['new_words_effective'] == 5
    assert data['tail']['reviews_left_items'] == 6
    assert [i['id'] for i in data['tail_queue']] == ['tail_maint_1', 'tail_acq_1']
    assert data['progress'] == {'completed': 0, 'total': 0}      # tail is not in queue
    assert data['queue'] == []


def test_get_without_plan_state_still_serves_the_session(app, monkeypatch):
    db = _DB({'practice_acquisition_min': 5})
    data, _ = _call_get(app, monkeypatch, db, _Practice(None), speed=False)
    assert data['governor'] is None and data['tail'] is None and data['tail_queue'] == []
    assert data['queue']


def test_speed_round_is_suppressed_when_practice_is_excluded(app, monkeypatch):
    db = _DB({'excluded_modules': ['practice']})
    data, _ = _call_get(app, monkeypatch, db, _Practice(None), speed=True)
    assert not [i for i in data['queue'] if i['kind'] == 'speed_round']


def test_speed_round_still_offered_when_practice_is_included(app, monkeypatch):
    db = _DB({'excluded_modules': ['flashcards']})
    data, _ = _call_get(app, monkeypatch, db, _Practice(None), speed=True)
    assert [i for i in data['queue'] if i['kind'] == 'speed_round']


def test_intake_runs_before_targets_and_rebuilds_once(app, monkeypatch):
    db = _DB({})
    rebuilt = []
    monkeypatch.setattr(
        ss._plan, 'StudyPlanService',
        lambda d: SimpleNamespace(rebuild_today=lambda u, l: rebuilt.append((u, l))))
    practice = _Practice(None, intake={'admitted': [1], 'needs_rebuild': True})
    _, test_service = _call_get(app, monkeypatch, db, practice)
    assert practice.admit_calls == 1
    assert rebuilt == [('user-1', 1)]
    assert test_service.get_or_create_daily_load.call_count == 2   # re-read after rebuild


def test_no_rebuild_when_intake_does_not_ask(app, monkeypatch):
    rebuilt = []
    monkeypatch.setattr(
        ss._plan, 'StudyPlanService',
        lambda d: SimpleNamespace(rebuild_today=lambda u, l: rebuilt.append(1)))
    _call_get(app, monkeypatch, _DB({}), _Practice(None))
    assert rebuilt == []


def test_an_intake_failure_does_not_break_the_session(app, monkeypatch):
    class Boom(_Practice):
        def admit_daily_new_words(self, *a):
            raise RuntimeError('db down')
    data, _ = _call_get(app, monkeypatch, _DB({'practice_acquisition_min': 5}), Boom(None))
    assert data['queue']


def _post_complete(app, monkeypatch, db, block_id):
    monkeypatch.setattr(ss, 'get_supabase_admin', lambda: db)
    monkeypatch.setattr(ss, '_today_iso', lambda *a: '2026-10-13')
    with app.test_request_context(
            '/api/study-session/complete-block', method='POST',
            json={'language_id': 1, 'block_id': block_id}):
        g.current_user_id = 'user-1'
        resp = ss.complete_block.__wrapped__()
    if isinstance(resp, tuple):
        return SimpleNamespace(status_code=resp[1]), db
    return resp, db


def test_complete_block_accepts_a_current_tail_id(app, monkeypatch):
    resp, db = _post_complete(app, monkeypatch, _DB({}), 'tail_maint_1')
    assert resp.status_code == 200
    assert db.updates == [{'completed_blocks': ['tail_maint_1']}]


def test_complete_block_rejects_a_stale_tail_id(app, monkeypatch):
    resp, db = _post_complete(app, monkeypatch, _DB({}), 'tail_maint_9')
    assert resp.status_code == 400 and db.updates == []


def test_complete_block_tail_ids_advance_with_completed_rounds(app, monkeypatch):
    done = ['tail_maint_1', 'tail_maint_2']
    resp, _ = _post_complete(app, monkeypatch, _DB({}, completed=done), 'tail_maint_3')
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Tail gate ignores tests: offered once the practice part is done, even with
# skipped tests, in both the daily session and Practice mode
# ---------------------------------------------------------------------------

_OPEN_TEST = [{'id': 't1', 'test_type': 'reading', 'is_completed': False}]


def test_open_test_does_not_hide_the_tail_in_the_daily_session(app, monkeypatch):
    db = _DB({'practice_acquisition_min': 0, 'practice_maintenance_min': 0}, completed=[])
    data, _ = _call_get(app, monkeypatch, db, _Practice(_state()), speed=False,
                        tests=_OPEN_TEST)
    assert data['tail']['new_words_left'] == 3
    assert data['progress'] == {'completed': 0, 'total': 1}     # test still required


def test_open_practice_block_still_hides_the_tail(app, monkeypatch):
    db = _DB({'practice_acquisition_min': 5, 'practice_maintenance_min': 0}, completed=[])
    data, _ = _call_get(app, monkeypatch, db, _Practice(_state()), speed=False,
                        tests=_OPEN_TEST)
    assert data['tail'] is None


def test_scope_practice_offers_the_tail_despite_an_open_test(app, monkeypatch):
    db = _DB({'practice_acquisition_min': 0, 'practice_maintenance_min': 0}, completed=[])
    data, _ = _call_get(app, monkeypatch, db, _Practice(_state()), speed=False,
                        tests=_OPEN_TEST, query='&scope=practice')
    assert data['tail']['new_words_left'] == 3
    assert data['progress'] == {'completed': 0, 'total': 1}     # queue itself unchanged
