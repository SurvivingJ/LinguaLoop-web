"""POST /api/dual-translation/<id>/submit under a concurrent double submit
(review A-01 / B-06 / A-03) and the pre-grade read wave (A-28 / B-15).

A stateful fake Supabase stands in for PostgREST: it filters on ``eq``/``in_``,
projects the selected columns, gives inserted rows an ``id``, supports
``delete`` and enforces the live UNIQUE(dt_grade.submission_id) constraint
(``dt_grade_submission_id_key``) with a 23505 error, as PostgREST reports it.
"""

import json
import threading
import time

import pytest

import routes.dual_translation as dt_routes
from services.dual_translation.repair import hooks as repair_hooks

OWNER = 'test-user-id-123'  # conftest's mocked auth identity
SID = 5


class UniqueViolation(Exception):
    """Shape of postgrest.exceptions.APIError for a UNIQUE violation."""

    def __init__(self, constraint):
        self.code = '23505'
        super().__init__(f'duplicate key value violates unique constraint "{constraint}"')


class FakeStore:
    def __init__(self, tables):
        self.tables = {name: [dict(r) for r in rows] for name, rows in tables.items()}
        self._next_id = 1000
        self.lock = threading.Lock()
        self.fail_grade_insert = None  # an Exception to raise on the next dt_grade insert
        self.on_execute = None         # hook(query) run before each execute

    def table(self, name):
        return FakeQuery(self, name)

    def rows(self, name):
        return self.tables.setdefault(name, [])

    def new_id(self):
        self._next_id += 1
        return self._next_id


class FakeQuery:
    def __init__(self, store, name):
        self.store, self.name = store, name
        self.op, self.payload, self.columns, self.filters = 'select', None, None, []
        self._limit = None

    def select(self, columns='*', **_):
        self.columns = None if columns.strip() == '*' else [c.strip() for c in columns.split(',')]
        return self

    def eq(self, col, val):
        self.filters.append(lambda r: r.get(col) == val)
        return self

    def in_(self, col, vals):
        vals = list(vals)
        self.filters.append(lambda r: r.get(col) in vals)
        return self

    def gte(self, col, val):
        self.filters.append(lambda r: str(r.get(col) or '') >= str(val))
        return self

    def limit(self, n):
        self._limit = n
        return self

    def order(self, *a, **k):
        return self

    def insert(self, payload):
        self.op, self.payload = 'insert', payload
        return self

    def update(self, payload):
        self.op, self.payload = 'update', payload
        return self

    def delete(self):
        self.op = 'delete'
        return self

    def _match(self):
        return [r for r in self.store.rows(self.name) if all(f(r) for f in self.filters)]

    def execute(self):
        if self.store.on_execute:
            self.store.on_execute(self)
        with self.store.lock:
            return type('R', (), {'data': self._execute()})()

    def _execute(self):
        rows = self.store.rows(self.name)
        if self.op == 'insert':
            new = self.payload if isinstance(self.payload, list) else [self.payload]
            if self.name == 'dt_grade':
                if self.store.fail_grade_insert is not None:
                    err, self.store.fail_grade_insert = self.store.fail_grade_insert, None
                    raise err
                taken = {r['submission_id'] for r in rows}
                if any(r['submission_id'] in taken for r in new):
                    raise UniqueViolation('dt_grade_submission_id_key')
            out = [{**r, 'id': self.store.new_id()} for r in new]
            rows.extend(out)
            return [dict(r) for r in out]
        if self.op == 'update':
            hit = self._match()
            for r in hit:
                r.update(self.payload)
            return [dict(r) for r in hit]
        if self.op == 'delete':
            hit = self._match()
            self.store.tables[self.name] = [r for r in rows if r not in hit]
            return [dict(r) for r in hit]
        hit = self._match()
        if self._limit is not None:
            hit = hit[:self._limit]
        if self.columns is None:
            return [dict(r) for r in hit]
        return [{c: r.get(c) for c in self.columns if c in r} for r in hit]


def _error(form):
    return {
        'span_reproduction': [0, 3], 'span_reference': [0, 4], 'category': 'lexical',
        'subtype': 'article_omission', 'source': 'interlingual', 'severity': 'minor',
        'learner_form': form, 'corrected_form': 'the ' + form, 'explanation': 'why',
        'confidence': 0.8, 'is_mistake': False,
    }


def _contract(band, form):
    return {
        'scores': {'accuracy': band}, 'overall_band': band, 'diff': [],
        'errors': [_error(form)], 'grader_trace': {'tier': 'tier2', 'tokens': {'in': 10, 'out': 5}},
    }


def _store():
    return FakeStore({
        'dt_submission': [{'id': SID, 'user_id': OWNER, 'passage_id': 9, 'l1_language_id': 2,
                           'created_at': '2026-11-23T00:00:01+00:00', 'reproduction': ''}],
        'dt_passage': [{'id': 9, 'l2_text': 'gold text', 'l2_language_id': 1, 'age_tier': 4,
                        'status': 'active', 'source_ref_id': None,
                        'sentence_start': 0, 'sentence_end': 1}],
        'dt_grade': [], 'dt_error_instance': [], 'dt_repair_event': [],
    })


def _winner_persists(store):
    """What a concurrent request that finished first leaves behind."""
    store.rows('dt_error_instance').append({**_error('WINNER'), 'submission_id': SID,
                                            'id': store.new_id()})
    c = _contract(2, 'WINNER')
    store.rows('dt_grade').append({'submission_id': SID, 'scores': c['scores'],
                                   'overall_band': 2, 'diff': [], 'grader_trace': c['grader_trace'],
                                   'id': store.new_id()})


@pytest.fixture
def wired(app, monkeypatch):
    """The submit route on a FakeStore. Repair hooks tag which path answered."""
    store = _store()
    app.supabase_service = store
    state = {'store': store, 'grade_calls': 0, 'during_grade': None}

    def _grade(db, **kwargs):
        state['grade_calls'] += 1
        if state['during_grade']:
            state['during_grade']()
        return _contract(3, 'LOSER')

    monkeypatch.setattr(dt_routes, 'grade_submission', _grade)
    monkeypatch.setattr(dt_routes, 'credit_study_time', lambda *a, **k: None)
    monkeypatch.setattr(repair_hooks, 'for_cached',
                        lambda db, uid, sid, c: {**c, 'answered_by': 'cached'})
    monkeypatch.setattr(repair_hooks, 'after_grade',
                        lambda db, **kw: {**kw['contract'], 'answered_by': 'fresh'})
    return state


def _post(client, headers):
    return client.post(f'/api/dual-translation/{SID}/submit', headers=headers,
                       json={'reproduction': 'my attempt'})


def _forms(store):
    return sorted(r['learner_form'] for r in store.rows('dt_error_instance'))


class TestLosingConcurrentSubmit:

    def test_loser_returns_the_stored_grade_like_a_cached_resubmit(self, client, auth_headers, wired):
        """Both requests passed the cache check; the other one stored its grade
        while this one was grading. This one's dt_grade insert then hits the
        UNIQUE constraint: it must answer the stored grade, not a 500."""
        store = wired['store']
        wired['during_grade'] = lambda: _winner_persists(store)

        loser = _post(client, auth_headers)

        assert loser.status_code == 200, loser.data
        wired['during_grade'] = None
        resubmit = _post(client, auth_headers)  # a plain cached re-submit
        assert resubmit.status_code == 200
        assert json.loads(loser.data) == json.loads(resubmit.data)
        assert json.loads(loser.data)['overall_band'] == 2
        assert json.loads(loser.data)['answered_by'] == 'cached'
        assert wired['grade_calls'] == 1  # the re-submit did not grade

    def test_loser_leaves_no_error_rows_behind(self, client, auth_headers, wired):
        store = wired['store']
        wired['during_grade'] = lambda: _winner_persists(store)

        _post(client, auth_headers)

        assert _forms(store) == ['WINNER']
        assert len(store.rows('dt_grade')) == 1

    def test_failed_grade_insert_cleans_up_so_retry_does_not_accumulate(self, client, auth_headers, wired):
        """TASK-633 kept: a failed grade insert leaves no grade, so the retry
        re-grades. A-03: and it leaves no orphan error rows either."""
        store = wired['store']
        store.fail_grade_insert = RuntimeError('connection reset')

        first = _post(client, auth_headers)

        assert first.status_code == 500
        assert store.rows('dt_grade') == []
        assert store.rows('dt_error_instance') == []

        retry = _post(client, auth_headers)

        assert retry.status_code == 200
        assert json.loads(retry.data)['answered_by'] == 'fresh'
        assert wired['grade_calls'] == 2
        assert _forms(store) == ['LOSER']
        assert len(store.rows('dt_grade')) == 1


class TestPersistGradeCleanup:

    def test_unique_violation_removes_only_this_requests_rows(self):
        store = _store()
        _winner_persists(store)

        with pytest.raises(UniqueViolation):
            dt_routes._persist_grade(store, SID, 'r', None, _contract(3, 'LOSER'))

        assert _forms(store) == ['WINNER']

    def test_ambiguous_failure_with_a_grade_present_keeps_the_rows(self):
        """A non-UNIQUE failure (e.g. a timeout) while a grade exists may mean
        this request's own grade committed: its error rows are then evidence
        and must not be deleted."""
        store = _store()
        _winner_persists(store)
        store.rows('dt_error_instance').clear()
        store.fail_grade_insert = TimeoutError('read timed out')

        with pytest.raises(TimeoutError):
            dt_routes._persist_grade(store, SID, 'r', None, _contract(3, 'MINE'))

        assert _forms(store) == ['MINE']


class TestSameProcessDoubleClick:

    def test_second_concurrent_submit_waits_and_is_answered_from_the_cache(
            self, app, auth_headers, wired):
        store = wired['store']
        release = threading.Event()
        wired['during_grade'] = lambda: release.wait(10)
        results = {}

        def _run(name):
            results[name] = _post(app.test_client(), auth_headers)

        first = threading.Thread(target=_run, args=('first',))
        first.start()
        deadline = time.monotonic() + 10
        while wired['grade_calls'] == 0 and time.monotonic() < deadline:
            time.sleep(0.005)
        second = threading.Thread(target=_run, args=('second',))
        second.start()
        while (dt_routes._submit_lock_waiters(SID) < 2) and time.monotonic() < deadline:
            time.sleep(0.005)
        release.set()
        first.join(10)
        second.join(10)

        assert results['first'].status_code == 200
        assert results['second'].status_code == 200
        assert wired['grade_calls'] == 1  # the grader was paid once
        assert json.loads(results['second'].data)['answered_by'] == 'cached'
        assert json.loads(results['second'].data)['overall_band'] == 3
        assert _forms(store) == ['LOSER']


class TestPreGradeReads:

    def test_reads_give_grading_the_same_inputs(self, client, auth_headers, app, monkeypatch):
        """The passage, repeat and budget reads run as one concurrent wave;
        grading still gets exactly the inputs they produce."""
        store = _store()
        # An earlier graded attempt on the same passage -> this is a repeat.
        store.rows('dt_submission').append({'id': 4, 'user_id': OWNER, 'passage_id': 9,
                                            'l1_language_id': 2, 'created_at': '2026-11-22T10:00:00+00:00'})
        store.rows('dt_grade').append({'submission_id': 4, 'overall_band': 1, 'scores': {},
                                       'diff': [], 'created_at': '2026-11-22T10:05:00+00:00',
                                       'grader_trace': {'tokens': {'in': 7, 'out': 3}}})
        app.supabase_service = store
        monkeypatch.setattr(dt_routes.Config, 'DT_DAILY_TOKEN_BUDGET', 1)
        monkeypatch.setattr(dt_routes.repair_budget, '_start_of_utc_day',
                            lambda: '2026-11-22T00:00:00+00:00')
        seen = {}

        def _grade(db, **kwargs):
            seen.update(kwargs)
            return _contract(3, 'X')

        threads = set()
        real_get_passage = dt_routes._get_passage

        def _spy_passage(db, pid):
            threads.add(threading.current_thread().name)
            return real_get_passage(db, pid)

        monkeypatch.setattr(dt_routes, '_get_passage', _spy_passage)
        monkeypatch.setattr(dt_routes, 'grade_submission', _grade)
        monkeypatch.setattr(dt_routes, 'credit_study_time', lambda *a, **k: None)

        resp = _post(client, auth_headers)

        assert resp.status_code == 200, resp.data
        assert seen == {
            'passage_id': 9, 'gold_l2': 'gold text', 'reproduction': 'my attempt',
            'l2_language_id': 1, 'l1_language_id': 2, 'age_tier': 4,
            'max_tier': 'tier1',  # 10 tokens today >= budget 1
        }
        body = json.loads(resp.data)
        assert body['repeat_of'] == {'of_submission_id': 4, 'graded_at': '2026-11-22T10:05:00+00:00',
                                     'band': 1}
        assert all(name.startswith('io') for name in threads)  # read off the request thread

    def test_passage_read_error_still_surfaces_as_the_catch_all_500(
            self, client, auth_headers, app, monkeypatch):
        app.supabase_service = _store()

        def _boom(db, pid):
            raise RuntimeError('db down')

        monkeypatch.setattr(dt_routes, '_get_passage', _boom)
        monkeypatch.setattr(dt_routes, '_tokens_used_today',
                            lambda db, uid: (_ for _ in ()).throw(AssertionError('second error')))

        resp = _post(client, auth_headers)

        assert resp.status_code == 500
        assert json.loads(resp.data)['error'] == 'Failed to submit reproduction'

    def test_missing_passage_message_wins_over_a_budget_read_error(
            self, client, auth_headers, app, monkeypatch):
        """Today the passage check runs before the budget read, so a missing
        passage answers its own 500 message even if the budget read would fail."""
        store = _store()
        store.rows('dt_passage').clear()
        app.supabase_service = store

        def _boom(db, uid):
            raise RuntimeError('budget read failed')

        monkeypatch.setattr(dt_routes, '_tokens_used_today', _boom)

        resp = _post(client, auth_headers)

        assert resp.status_code == 500
        assert json.loads(resp.data)['error'] == 'Passage for this submission no longer exists'
