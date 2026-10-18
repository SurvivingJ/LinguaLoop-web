"""Practice extra rounds (practice-extra-rounds, ADR-036).

GET /api/practice/extra validation, and PracticeSessionService.get_extra_round:
new words past the daily quota, reviews (due first, then review-ahead).
"""

from unittest.mock import MagicMock

import pytest
from flask import Flask

from services import practice_session_service as pss
from services.practice_session_service import (
    EXTRA_NEW_WORDS_MAX, EXTRA_REVIEW_ITEMS, PracticeSessionService,
)


# ---------------------------------------------------------------------------
# route
# ---------------------------------------------------------------------------

class _FakeService:
    def __init__(self):
        self.kwargs = None

    def get_extra_round(self, **kw):
        self.kwargs = kw
        return {'items': [], 'tail': True, 'extra': {}}


@pytest.fixture
def client_and_service(monkeypatch):
    import middleware.auth as auth
    import routes.practice as practice

    svc = _FakeService()
    monkeypatch.setattr(auth, '_authenticate', lambda token: ({'sub': 'user-1'}, None))
    monkeypatch.setattr(pss, 'get_practice_session_service', lambda: svc)
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.register_blueprint(practice.practice_bp, url_prefix='/api/practice')
    client = app.test_client()
    client.environ_base['HTTP_AUTHORIZATION'] = 'Bearer fake'
    return client, svc


def test_extra_forwards_choice_and_exclude(client_and_service):
    client, svc = client_and_service
    resp = client.get('/api/practice/extra?language_id=1&reviews=1&new_words=5&exclude=4,x,7')
    assert resp.status_code == 200
    assert svc.kwargs == {
        'user_id': 'user-1', 'language_id': 1, 'reviews': True,
        'new_words': 5, 'exclude_sense_ids': [4, 7],
    }


@pytest.mark.parametrize('query', [
    'reviews=0&new_words=0',                       # nothing requested
    f'reviews=0&new_words={EXTRA_NEW_WORDS_MAX + 1}',
    'reviews=1&new_words=-1',
])
def test_extra_rejects_bad_choices(client_and_service, query):
    client, svc = client_and_service
    assert client.get(f'/api/practice/extra?language_id=1&{query}').status_code == 400
    assert svc.kwargs is None


def test_extra_requires_language(client_and_service):
    client, _ = client_and_service
    assert client.get('/api/practice/extra?reviews=1').status_code == 400


# ---------------------------------------------------------------------------
# service
# ---------------------------------------------------------------------------

def _item(sid, mode, eid=None):
    return {'exercise_id': eid or f'e{sid}-{mode}', 'sense_id': sid, 'mode': mode}


def _svc(state, rpc_data, admitted=()):
    """A service whose RPCs answer from ``rpc_data[name]`` (a callable of params)."""
    s = PracticeSessionService.__new__(PracticeSessionService)
    s.db = MagicMock()
    calls = []

    def rpc(name, params):
        calls.append((name, params))
        out = MagicMock()
        out.execute.return_value.data = rpc_data[name](params)
        return out

    s.db.rpc.side_effect = rpc
    s.new_word_state = lambda u, l: state
    s._subscribed_sense_ids = lambda u: set()
    s.nominated = []

    def nominate(u, l, want, exclude):
        s.nominated.append(want)
        return list(admitted)[:want]

    s._nominate_new_words = nominate
    s._insert_ladder_rows = lambda u, ids: True
    s._apply_script_variant = lambda *a, **k: None
    s._prepare_jumbled_items = lambda *a, **k: None
    s._most_overdue_first = lambda items, u: None
    s.calls = calls
    return s


def _state(unstarted=(), effective=5, started_today=0):
    return {'unstarted_sense_ids': list(unstarted), 'effective': effective,
            'started_today': started_today}


@pytest.fixture(autouse=True)
def _mpnw(monkeypatch):
    monkeypatch.setattr(pss._plan, 'get_minutes_per_new_word', lambda db, lang: 3.0)


def test_new_words_admit_past_the_quota_and_use_unstarted_first():
    acq = [_item(s, 'acquisition') for s in (9, 1, 2, 3, 4)]
    s = _svc(_state(unstarted=[1, 2], effective=5, started_today=5),
             {'get_practice_session': lambda p: {'items': acq}}, admitted=[3, 4, 5])
    out = s.get_extra_round('u', 1, reviews=False, new_words=4)
    assert s.nominated == [2]                       # 4 wanted - 2 already unstarted
    assert [i['sense_id'] for i in out['items']] == [1, 2, 3, 4]   # 9 is not a target
    assert out['extra']['new_words_admitted'] == 2
    assert out['extra']['new_words_beyond_quota'] == 4   # quota already used up
    assert out['tail'] is True


def test_no_admission_when_enough_words_are_unstarted():
    s = _svc(_state(unstarted=[1, 2, 3]),
             {'get_practice_session': lambda p: {'items': [_item(1, 'acquisition')]}})
    out = s.get_extra_round('u', 1, reviews=False, new_words=3)
    assert s.nominated == []
    assert out['extra']['new_words_beyond_quota'] == 0     # 3 <= 5 left today


def test_new_words_are_capped_per_round():
    s = _svc(_state(), {'get_practice_session': lambda p: {'items': []}}, admitted=range(50))
    out = s.get_extra_round('u', 1, reviews=False, new_words=99)
    assert out['extra']['requested_new_words'] == EXTRA_NEW_WORDS_MAX


def test_reviews_serve_due_first_then_review_ahead():
    due = [_item(1, 'maintenance'), _item(2, 'maintenance'), _item(3, 'acquisition')]
    ahead_params = {}

    def ahead(p):
        ahead_params.update(p)
        return [_item(2, 'maintenance', 'dup'), _item(8, 'maintenance')]

    s = _svc(_state(), {'get_practice_session': lambda p: {'items': due},
                        'get_review_ahead_items': ahead})
    out = s.get_extra_round('u', 1, reviews=True, new_words=0, exclude_sense_ids=[7])
    assert [i['sense_id'] for i in out['items']] == [1, 2, 8]   # fall-through acq dropped
    assert ahead_params['p_limit'] == EXTRA_REVIEW_ITEMS - 2
    assert ahead_params['p_exclude_sense_ids'] == [1, 2, 7]
    assert out['extra']['reviews_served'] == 3


def test_reviews_stop_at_the_round_size_without_review_ahead():
    due = [_item(i, 'maintenance') for i in range(1, EXTRA_REVIEW_ITEMS + 5)]
    s = _svc(_state(), {'get_practice_session': lambda p: {'items': due}})
    out = s.get_extra_round('u', 1, reviews=True, new_words=0)
    assert len(out['items']) == EXTRA_REVIEW_ITEMS
    assert all(name != 'get_review_ahead_items' for name, _ in s.calls)


def test_both_interleaves_reviews_and_new_words():
    def session(p):
        if p['p_mode'] == 'maintenance':
            return {'items': [_item(i, 'maintenance') for i in (1, 2, 3, 4)]}
        return {'items': [_item(9, 'acquisition', 'a1'), _item(9, 'acquisition', 'a2')]}

    s = _svc(_state(unstarted=[9]), {'get_practice_session': session,
                                     'get_review_ahead_items': lambda p: []})
    out = s.get_extra_round('u', 1, reviews=True, new_words=1)
    modes = [i['mode'] for i in out['items']]
    assert modes == ['maintenance', 'maintenance', 'acquisition',
                     'maintenance', 'maintenance', 'acquisition']   # spread, not appended


def test_nothing_requested_is_an_error():
    s = _svc(_state(), {})
    assert s.get_extra_round('u', 1, reviews=False, new_words=0)['code'] == 'E_EMPTY'


def test_empty_round_says_so():
    s = _svc(_state(), {'get_practice_session': lambda p: {'items': []},
                        'get_review_ahead_items': lambda p: []})
    out = s.get_extra_round('u', 1, reviews=True, new_words=0)
    assert out['items'] == [] and out['no_content_reason'] == 'all_complete'
