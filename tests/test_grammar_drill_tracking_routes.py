"""Routes /api/grammar-drill/round and /progress (TASK-1259, ADR-066) through
the Flask test client, over an in-memory stand-in for the two tables and
``record_grammar_drill_round`` (same rules as migrations/grammar_drill_tracking.sql)."""

import copy
import json
from datetime import datetime, timezone

import pytest

from services import grammar_drill_tracking as tracking

ME = 'test-user-id-123'
OTHER = 'someone-else'
KEY1 = '11111111-1111-4111-8111-111111111111'
KEY2 = '22222222-2222-4222-8222-222222222222'
ROUND = '/api/grammar-drill/round'
PROGRESS = '/api/grammar-drill/progress'


class _Result:
    def __init__(self, data):
        self.data = data


class _Query:
    def __init__(self, db, table):
        self.db, self.table, self.filters, self.window = db, table, [], None

    def select(self, *_):
        return self

    def eq(self, col, val):
        self.filters.append(lambda r, c=col, v=val: r[c] == v)
        return self

    def gte(self, col, val):
        self.filters.append(lambda r, c=col, v=val: r[c] >= v)
        return self

    def order(self, *_a, **_k):
        return self

    def range(self, start, end):
        self.window = (start, end)
        return self

    def execute(self):
        if self.db.missing:
            raise Exception("{'code': 'PGRST205', 'message': \"Could not find the table "
                            f"'public.{self.table}' in the schema cache\"}}")
        rows = [copy.deepcopy(r) for r in self.db.rows[self.table] if all(f(r) for f in self.filters)]
        rows.sort(key=lambda r: (r.get('practice_day', ''), r['topic']))
        if self.window:
            rows = rows[self.window[0]:self.window[1] + 1]
        return _Result(rows)


class _Rpc:
    def __init__(self, db, name, params):
        self.db, self.name, self.params = db, name, params

    def execute(self):
        if self.db.missing:
            raise Exception("{'code': 'PGRST202', 'message': 'Could not find the function "
                            "public.record_grammar_drill_round in the schema cache'}")
        assert self.name == 'record_grammar_drill_round'
        return _Result(self.db.record(**self.params))


class FakeDb:
    """The two tables as lists of dicts, and the function's behaviour."""

    def __init__(self):
        self.rows = {'grammar_drill_daily': [], 'grammar_drill_state': []}
        self.missing = False
        self.calls = []

    def table(self, name):
        return _Query(self, name)

    def rpc(self, name, params):
        self.calls.append((name, copy.deepcopy(params)))
        return _Rpc(self, name, params)

    def _find(self, table, **key):
        for row in self.rows[table]:
            if all(row[k] == v for k, v in key.items()):
                return row
        return None

    def record(self, p_user_id, p_language_id, p_round_key, p_practice_day, p_topics):
        recorded = replayed = 0
        for t in sorted(p_topics, key=lambda x: x['topic']):
            key = {'user_id': p_user_id, 'language_id': p_language_id, 'topic': t['topic']}
            state = self._find('grammar_drill_state', **key)
            if state is None:
                state = dict(key, state={}, last_round_key=None)
                self.rows['grammar_drill_state'].append(state)
            if state['last_round_key'] == p_round_key:
                replayed += 1
                continue
            if t['answers'] > 0:
                day = self._find('grammar_drill_daily', practice_day=p_practice_day, **key)
                if day is None:
                    day = dict(key, practice_day=p_practice_day, answers=0, correct=0, timed=0,
                               ms_sum=0, stage=1, instant=False, sub_misses={})
                    self.rows['grammar_drill_daily'].append(day)
                for col in ('answers', 'correct', 'timed', 'ms_sum'):
                    day[col] += t[col]
                day['stage'] = max(day['stage'], t['stage'])
                day['instant'] = t['instant']
                for sub, n in t['sub_misses'].items():
                    day['sub_misses'][sub] = day['sub_misses'].get(sub, 0) + n
            old, new = state['state'], t.get('state')
            merged = dict(old if new is None or old.get('l', 0) > new.get('l', 0) else new)
            merged['u'] = min(4, max(old.get('u', 1), (new or {}).get('u', 1), t['stage']))
            state['state'], state['last_round_key'] = merged, p_round_key
            recorded += 1
        return {'success': True, 'recorded': recorded, 'replayed': replayed}


@pytest.fixture
def db(app, monkeypatch):
    fake = FakeDb()
    tracking.reset()
    monkeypatch.setattr('routes.grammar_drill.get_db', lambda: fake)
    yield fake
    tracking.reset()


@pytest.fixture(scope='module')
def topic():
    """A real topic of the shipped manifest with at least two sub-points."""
    with tracking.MANIFEST_PATH.open(encoding='utf-8') as fh:
        manifest = json.load(fh)
    t = next(t for t in manifest['topics'] if len(t['subs']) >= 2)
    return {'slug': t['slug'], 'subs': [s['key'] for s in t['subs']],
            'other': next(o['slug'] for o in manifest['topics'] if o['slug'] != t['slug'])}


def _state(u=1, last=1_700_000_000, results='1200,-800,950'):
    return {'u': u, 'r': [results, '', '', ''], 'q': 3, 'e': [0, 0, 0], 'l': last}


def _entry(topic, **over):
    entry = {'topic': topic['slug'], 'answers': 20, 'correct': 16, 'timed': 16, 'ms_sum': 40000,
             'stage': 1, 'instant': False, 'sub_misses': {topic['subs'][0]: 3, topic['subs'][1]: 1},
             'state': _state()}
    entry.update(over)
    return entry


def _body(topic, key=KEY1, mode='round', **over):
    return {'language_id': 1, 'round_key': key, 'mode': mode, 'topics': [_entry(topic, **over)]}


def j(resp):
    return json.loads(resp.data)


# ------------------------------------------------------------------------- happy path
def test_round_is_recorded_and_read_back(client, auth_headers, db, topic):
    r = client.post(ROUND, json=_body(topic), headers=auth_headers)
    assert r.status_code == 200, r.data
    assert j(r)['status'] == 'success' and j(r)['recorded'] == 1 and j(r)['replayed'] == 0
    name, params = db.calls[0]
    assert name == 'record_grammar_drill_round'
    assert params['p_user_id'] == ME and params['p_language_id'] == 1
    assert params['p_round_key'] == KEY1
    assert params['p_practice_day'] == j(r)['practice_day']

    got = j(client.get(f'{PROGRESS}?language_id=1', headers=auth_headers))
    assert got['status'] == 'success' and got['days'] == 180
    assert got['today'] == tracking.review_today().isoformat()
    assert got['states'] == {topic['slug']: _state()}
    assert got['daily'] == [{
        'topic': topic['slug'], 'day': j(r)['practice_day'], 'answers': 20, 'correct': 16,
        'timed': 16, 'ms_sum': 40000, 'stage': 1, 'instant': False,
        'sub_misses': {topic['subs'][0]: 3, topic['subs'][1]: 1},
    }]


def test_same_round_key_is_not_counted_twice(client, auth_headers, db, topic):
    first = client.post(ROUND, json=_body(topic), headers=auth_headers)
    again = client.post(ROUND, json=_body(topic), headers=auth_headers)
    assert first.status_code == again.status_code == 200
    assert j(again)['recorded'] == 0 and j(again)['replayed'] == 1
    assert db.rows['grammar_drill_daily'][0]['answers'] == 20

    more = client.post(ROUND, json=_body(topic, key=KEY2, correct=20, sub_misses={}, stage=2,
                                         state=_state(u=2, last=1_700_000_500)),
                       headers=auth_headers)
    assert j(more)['recorded'] == 1
    day = db.rows['grammar_drill_daily'][0]
    assert (day['answers'], day['correct'], day['stage']) == (40, 36, 2)
    assert db.rows['grammar_drill_state'][0]['state']['u'] == 2


def test_sync_uploads_state_without_a_daily_row(client, auth_headers, db, topic):
    body = _body(topic, mode='sync', answers=0, correct=0, timed=0, ms_sum=0, sub_misses={},
                 stage=3, state=_state(u=3))
    r = client.post(ROUND, json=body, headers=auth_headers)
    assert r.status_code == 200 and j(r)['recorded'] == 1
    assert db.rows['grammar_drill_daily'] == []
    assert db.rows['grammar_drill_state'][0]['state']['u'] == 3


def test_older_state_does_not_replace_fresher_results_or_lower_the_stage(client, auth_headers, db, topic):
    client.post(ROUND, json=_body(topic, stage=3, state=_state(u=3, last=2000, results='900')),
                headers=auth_headers)
    client.post(ROUND, json=_body(topic, key=KEY2, state=_state(u=1, last=1000, results='-5000')),
                headers=auth_headers)
    state = db.rows['grammar_drill_state'][0]['state']
    assert state['u'] == 3 and state['r'][0] == '900' and state['l'] == 2000


def test_played_at_sets_the_practice_day_within_a_week(topic):
    now = datetime(2026, 11, 27, 3, 0, tzinfo=timezone.utc)   # 14:00 in Sydney
    stamp = int(datetime(2026, 11, 25, 13, 30, tzinfo=timezone.utc).timestamp())  # 00:30 on the 26th
    assert tracking.practice_day(None, now).isoformat() == '2026-11-27'
    assert tracking.practice_day(stamp, now).isoformat() == '2026-11-26'
    assert tracking.practice_day(stamp - 30 * 86400, now).isoformat() == '2026-11-27'
    assert tracking.practice_day(int(now.timestamp()) + 86400, now).isoformat() == '2026-11-27'
    assert tracking.practice_day(True, now).isoformat() == '2026-11-27'


# ------------------------------------------------------------------------- validation
def _bad_bodies(topic):
    def good(**over):
        return _body(topic, **over)

    def top(**over):
        return dict(_body(topic), **over)

    return {
        'wrong language': top(language_id=3),
        'language as bool': top(language_id=True),
        'no round key': top(round_key=None),
        'round key not a uuid': top(round_key='abc'),
        'unknown mode': top(mode='practice'),
        'no topics': top(topics=[]),
        'topics not a list': top(topics={'a': 1}),
        'too many topics': top(topics=[_entry(topic)] * 11),
        'topic twice': top(topics=[_entry(topic), _entry(topic)]),
        'unknown topic': dict(_body(topic), topics=[dict(_entry(topic), topic='no-such-topic')]),
        'unknown field': dict(_body(topic), topics=[dict(_entry(topic), user_id=OTHER)]),
        'zero answers in a round': good(answers=0, correct=0, timed=0, ms_sum=0, sub_misses={}),
        'too many answers': good(answers=501),
        'answers as float': good(answers=20.0),
        'answers as bool': good(answers=True),
        'correct over answers': good(correct=21),
        'negative correct': good(correct=-1),
        'timed over answers': good(timed=21),
        'ms over the cap': good(timed=2, ms_sum=60001),
        'negative ms': good(ms_sum=-1),
        'stage 0': good(stage=0),
        'stage 5': good(stage=5),
        'instant not bool': good(instant=1),
        'instant below stage 4': good(instant=True, stage=3),
        'unknown sub-point': good(sub_misses={'no-such-sub': 1}),
        'sub misses not an object': good(sub_misses=[1]),
        'sub miss of zero': good(sub_misses={topic['subs'][0]: 0}),
        'more misses than missed': good(sub_misses={topic['subs'][0]: 5}),
        'state not an object': good(state=[1]),
        'state missing a field': good(state={'u': 1}),
        'state unknown field': good(state=dict(_state(), i={'01-001': [1, 2]})),
        'state stage out of range': good(state=_state(u=7)),
        'state results not strings': good(state=dict(_state(), r=[[1], [], [], []])),
        'state results malformed': good(state=dict(_state(), r=['1200;drop', '', '', ''])),
        'state results too long': good(state=dict(_state(), r=[','.join(['1000'] * 31), '', '', ''])),
        'state three stages': good(state=dict(_state(), r=['', '', ''])),
        'state last answer far ahead': good(state=_state(last=99_999_999_999)),
        'state endless shape': good(state=dict(_state(), e=[1, 2])),
        'sync with answers': good(mode='sync'),
        'sync without state': good(mode='sync', answers=0, correct=0, timed=0, ms_sum=0,
                                   sub_misses={}, state=None),
    }


def test_invalid_bodies_are_rejected_before_any_write(client, auth_headers, db, topic):
    for label, body in _bad_bodies(topic).items():
        r = client.post(ROUND, json=body, headers=auth_headers)
        assert r.status_code == 400, f'{label}: {r.status_code} {r.data!r}'
        assert j(r)['status'] == 'error' and j(r)['error_code'] == 'BAD_REQUEST', label
    assert db.calls == []
    assert client.post(ROUND, data='[1]', headers=auth_headers,
                       content_type='application/json').status_code == 400


def test_ten_topics_are_accepted_and_cleaned(client, auth_headers, db, topic):
    slugs = list(tracking.topic_subs())[:10]
    topics = [{'topic': s, 'answers': 2, 'correct': 2, 'timed': 2, 'ms_sum': 60000, 'stage': 4,
               'instant': True} for s in slugs]
    r = client.post(ROUND, json={'language_id': 1, 'round_key': KEY1.upper(), 'mode': 'mixed',
                                 'topics': topics, 'user_id': OTHER}, headers=auth_headers)
    assert r.status_code == 200 and j(r)['recorded'] == 10
    _, params = db.calls[0]
    assert params['p_round_key'] == KEY1 and params['p_user_id'] == ME
    assert set(params['p_topics'][0]) == {'topic', 'answers', 'correct', 'timed', 'ms_sum',
                                         'stage', 'instant', 'sub_misses', 'state'}


def test_progress_validation(client, auth_headers, db):
    assert client.get(PROGRESS, headers=auth_headers).status_code == 400
    assert client.get(f'{PROGRESS}?language_id=3', headers=auth_headers).status_code == 400
    assert client.get(f'{PROGRESS}?language_id=1&days=0', headers=auth_headers).status_code == 400
    capped = j(client.get(f'{PROGRESS}?language_id=1&days=9999', headers=auth_headers))
    assert capped['days'] == 365 and capped['daily'] == [] and capped['states'] == {}


# --------------------------------------------------------------- auth and isolation
def test_both_routes_need_a_token(client, db, topic):
    assert client.post(ROUND, json=_body(topic)).status_code == 401
    assert client.get(f'{PROGRESS}?language_id=1').status_code == 401
    assert db.calls == []


def test_a_learner_sees_and_writes_only_their_own_rows(client, auth_headers, db, topic):
    today = tracking.review_today().isoformat()
    db.rows['grammar_drill_state'].append(
        {'user_id': OTHER, 'language_id': 1, 'topic': topic['other'], 'state': _state(u=4),
         'last_round_key': KEY2})
    db.rows['grammar_drill_daily'].append(
        {'user_id': OTHER, 'language_id': 1, 'topic': topic['other'], 'practice_day': today,
         'answers': 99, 'correct': 99, 'timed': 99, 'ms_sum': 99, 'stage': 4, 'instant': True,
         'sub_misses': {}})
    client.post(ROUND, json=dict(_body(topic), user_id=OTHER), headers=auth_headers)
    got = j(client.get(f'{PROGRESS}?language_id=1&user_id={OTHER}', headers=auth_headers))
    assert list(got['states']) == [topic['slug']]
    assert [d['topic'] for d in got['daily']] == [topic['slug']]
    assert {r['user_id'] for r in db.rows['grammar_drill_daily']} == {ME, OTHER}
    assert [r['answers'] for r in db.rows['grammar_drill_daily'] if r['user_id'] == OTHER] == [99]


def test_progress_leaves_out_days_before_the_window(client, auth_headers, db, topic):
    row = {'user_id': ME, 'language_id': 1, 'topic': topic['slug'], 'answers': 5, 'correct': 5,
           'timed': 5, 'ms_sum': 5000, 'stage': 1, 'instant': False, 'sub_misses': {}}
    db.rows['grammar_drill_daily'] += [dict(row, practice_day='2020-01-01'),
                                       dict(row, practice_day=tracking.review_today().isoformat())]
    got = j(client.get(f'{PROGRESS}?language_id=1&days=30', headers=auth_headers))
    assert [d['day'] for d in got['daily']] == [tracking.review_today().isoformat()]


# ------------------------------------------------------- migration not applied yet
def test_missing_tables_and_function_answer_503_and_are_logged(client, auth_headers, db, topic, caplog):
    db.missing = True
    with caplog.at_level('WARNING', logger='services.grammar_drill_tracking'):
        r = client.post(ROUND, json=_body(topic), headers=auth_headers)
    assert r.status_code == 503 and j(r)['error_code'] == 'GRAMMAR_TRACKING_UNAVAILABLE'
    assert 'grammar_drill_tracking.sql' in caplog.text
    # Remembered: the next requests do not pay a failing round trip.
    g = client.get(f'{PROGRESS}?language_id=1', headers=auth_headers)
    assert g.status_code == 503 and j(g)['error_code'] == 'GRAMMAR_TRACKING_UNAVAILABLE'
    assert len(db.calls) == 1

    tracking.reset()
    g = client.get(f'{PROGRESS}?language_id=1', headers=auth_headers)
    assert g.status_code == 503
    # Applied later: works without a restart once the remembered state expires.
    tracking.reset()
    db.missing = False
    assert client.post(ROUND, json=_body(topic), headers=auth_headers).status_code == 200


def test_other_database_errors_are_500(client, auth_headers, db, topic, monkeypatch):
    def boom(*_a, **_k):
        raise RuntimeError('connection reset')
    monkeypatch.setattr(db, 'rpc', boom)
    r = client.post(ROUND, json=_body(topic), headers=auth_headers)
    assert r.status_code == 500 and j(r)['status'] == 'error'
    assert 'connection reset' not in r.data.decode()


def test_rate_limits_and_blueprint_are_registered(app):
    from web.rate_limits import ENDPOINT_LIMITS
    for endpoint in ('grammar_drill.record_round', 'grammar_drill.get_progress'):
        assert endpoint in app.view_functions and endpoint in ENDPOINT_LIMITS
    rules = {r.rule for r in app.url_map.iter_rules() if r.rule.startswith('/api/grammar-drill')}
    assert rules == {'/api/grammar-drill/round', '/api/grammar-drill/progress'}


def test_migration_matches_the_route_contract():
    sql = (tracking.MANIFEST_PATH.parents[4] / 'migrations' / 'grammar_drill_tracking.sql').read_text()
    assert 'public.record_grammar_drill_round(' in sql
    for param in ('p_user_id', 'p_language_id', 'p_round_key', 'p_practice_day', 'p_topics'):
        assert param in sql
    for table in (tracking.DAILY_TABLE, tracking.STATE_TABLE):
        assert f'ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY' in sql
    assert 'review_today(' not in sql.split('BEGIN;', 1)[1]   # the day is passed in
