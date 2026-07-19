"""Unit tests for the dual-translation routes (TASK-607).

Two layers, mirroring the established convention from
test_dual_translation_grader_cascade.py (mock every DB/OpenRouter boundary,
not the raw Supabase chain):

  1. Helper-level tests exercise the small DB-touching functions
     (``_resolve_l1_language_id``, ``_select_next_passage``,
     ``_rubric_descriptors_for``, ``_cached_grade``, ``_persist_grade``)
     against a minimal fake query-builder (``_FakeDB``), not a live DB.
  2. Route-level tests exercise ``get_next``/``submit`` through the Flask
     test client with every helper *and* ``grade_submission`` monkeypatched
     directly on the ``routes.dual_translation`` module namespace — the same
     pattern test_listening_lab_routes.py uses for its service singleton.

This repo doesn't spin up a live DB for these tests; live verification
against a real seeded passage is blocked on TASK-603/604 (see the tasklist
notes) and is explicitly out of scope here.
"""

import json

import pytest

import routes.dual_translation as dt_routes
from config import Config
from services.dimension_service import DimensionService


def resp_json(resp):
    return json.loads(resp.data)


# ---------------------------------------------------------------------------
# Minimal fake Supabase query-builder for helper-level tests
# ---------------------------------------------------------------------------

class _FakeResult:
    def __init__(self, data):
        self.data = data


class _FakeQuery:
    """Chainable stand-in for supabase-py's query builder. Filter/projection
    methods are no-ops that return self; insert/update record their payload
    on the owning _FakeDB so tests can assert on them; execute() returns the
    canned data configured for this table."""

    def __init__(self, data, recorder, table_name):
        self._data = data
        self._recorder = recorder
        self._table_name = table_name

    def select(self, *a, **k):
        return self

    def eq(self, *a, **k):
        return self

    def gte(self, *a, **k):
        return self

    def in_(self, *a, **k):
        return self

    def or_(self, *a, **k):
        return self

    def order(self, *a, **k):
        return self

    def limit(self, *a, **k):
        return self

    def insert(self, payload):
        self._recorder.append((self._table_name, 'insert', payload))
        return self

    def update(self, payload):
        self._recorder.append((self._table_name, 'update', payload))
        return self

    def execute(self):
        return _FakeResult(self._data)


class _FakeDB:
    def __init__(self, tables: dict):
        self._tables = tables
        self.calls = []

    def table(self, name):
        return _FakeQuery(self._tables.get(name, []), self.calls, name)


class _FailingInsertQuery(_FakeQuery):
    """_FakeQuery whose insert() raises for one target table, standing in for
    a Supabase insert that hits a constraint/transient error at write time."""

    def __init__(self, data, recorder, table_name, fail_table):
        super().__init__(data, recorder, table_name)
        self._fail_table = fail_table

    def insert(self, payload):
        super().insert(payload)
        if self._table_name == self._fail_table:
            raise RuntimeError(f"simulated insert failure on {self._table_name}")
        return self


class _FailingInsertDB(_FakeDB):
    """_FakeDB where inserts into ``fail_table`` raise (TASK-633 partial-failure
    simulation). All other calls behave like the plain fake."""

    def __init__(self, tables: dict, fail_table: str):
        super().__init__(tables)
        self._fail_table = fail_table

    def table(self, name):
        return _FailingInsertQuery(
            self._tables.get(name, []), self.calls, name, self._fail_table
        )


# ---------------------------------------------------------------------------
# _resolve_l1_language_id
# ---------------------------------------------------------------------------

class TestResolveL1LanguageId:

    def test_uses_native_language_when_set(self):
        db = _FakeDB({'users': [{'native_language_id': 3}]})
        assert dt_routes._resolve_l1_language_id(db, 'u1') == 3

    def test_falls_back_to_english_when_null(self):
        db = _FakeDB({'users': [{'native_language_id': None}]})
        assert dt_routes._resolve_l1_language_id(db, 'u1') == dt_routes.DEFAULT_L1_LANGUAGE_ID

    def test_falls_back_to_english_when_no_row(self):
        db = _FakeDB({'users': []})
        assert dt_routes._resolve_l1_language_id(db, 'u1') == dt_routes.DEFAULT_L1_LANGUAGE_ID


# ---------------------------------------------------------------------------
# _select_next_passage
# ---------------------------------------------------------------------------

class TestSelectNextPassage:

    def test_none_when_no_completed_tests(self):
        db = _FakeDB({'test_attempts': []})
        assert dt_routes._select_next_passage(db, 'u1', 2) is None

    def test_none_when_candidate_has_no_l1_reference(self):
        db = _FakeDB({
            'test_attempts': [{'test_id': 't1'}],
            'dt_passage': [{'id': 7, 'l2_text': 'gold', 'age_tier': 3, 'l2_language_id': 1}],
            'dt_passage_reference': [],
        })
        assert dt_routes._select_next_passage(db, 'u1', 2) is None

    def test_returns_passage_with_l1_reference(self):
        db = _FakeDB({
            'test_attempts': [{'test_id': 't1'}],
            'dt_passage': [{'id': 7, 'l2_text': 'gold', 'age_tier': 3, 'l2_language_id': 1}],
            'dt_passage_reference': [{'l1_text': 'hello world'}],
        })
        result = dt_routes._select_next_passage(db, 'u1', 2)
        assert result == {
            'passage_id': 7, 'l1_text': 'hello world', 'age_tier': 3, 'l2_language_id': 1,
        }


# ---------------------------------------------------------------------------
# _rubric_descriptors_for
# ---------------------------------------------------------------------------

class TestRubricDescriptorsFor:

    def test_empty_when_no_active_rubric(self, monkeypatch):
        def _boom(db):
            raise RuntimeError("no active dt_rubric_version row")
        monkeypatch.setattr(dt_routes, 'get_active_rubric', _boom)

        assert dt_routes._rubric_descriptors_for(db=None, age_tier=3, l2_code='ja') == {}

    def test_extracts_l2_descriptors_and_hides_naturalness_at_low_tier(self, monkeypatch):
        cfg = {
            'band_descriptors': {
                '1': {
                    'accuracy': {'ja': {'1': 'a1', '2': 'a2', '3': 'a3', '4': 'a4'}},
                    'naturalness': {'ja': {'1': 'n1', '2': 'n2', '3': 'n3', '4': 'n4'}},
                },
            },
        }
        monkeypatch.setattr(dt_routes, 'get_active_rubric', lambda db: cfg)

        result = dt_routes._rubric_descriptors_for(db=None, age_tier=1, l2_code='ja')

        assert 'naturalness' not in result
        assert result['accuracy'] == {'1': 'a1', '2': 'a2', '3': 'a3', '4': 'a4'}

    def test_keeps_naturalness_above_low_tiers(self, monkeypatch):
        cfg = {
            'band_descriptors': {
                '3': {'naturalness': {'ja': {'1': 'n1', '2': 'n2', '3': 'n3', '4': 'n4'}}},
            },
        }
        monkeypatch.setattr(dt_routes, 'get_active_rubric', lambda db: cfg)

        result = dt_routes._rubric_descriptors_for(db=None, age_tier=3, l2_code='ja')

        assert 'naturalness' in result


# ---------------------------------------------------------------------------
# _cached_grade / _persist_grade
# ---------------------------------------------------------------------------

class TestCachedGrade:

    def test_none_when_no_grade_persisted(self):
        db = _FakeDB({'dt_grade': []})
        assert dt_routes._cached_grade(db, 5) is None

    def test_reconstructs_contract_from_persisted_rows(self):
        db = _FakeDB({
            'dt_grade': [{
                'scores': {'accuracy': 4}, 'overall_band': 4, 'diff': [],
                'grader_trace': {'tier': 'tier0'},
            }],
            'dt_error_instance': [{
                'span_reproduction': [0, 1], 'span_reference': [0, 1],
                'category': 'lexical', 'subtype': 'x', 'source': 'interlingual',
                'severity': 'minor', 'learner_form': 'a', 'corrected_form': 'b',
                'explanation': 'why', 'confidence': 0.9, 'is_mistake': False,
            }],
        })

        result = dt_routes._cached_grade(db, 5)

        assert result['scores'] == {'accuracy': 4}
        assert result['overall_band'] == 4
        assert result['grader_trace'] == {'tier': 'tier0'}
        assert len(result['errors']) == 1
        assert result['errors'][0]['corrected_form'] == 'b'


class TestPersistGrade:

    _CONTRACT = {
        'scores': {'accuracy': 3}, 'overall_band': 3, 'diff': [], 'grader_trace': {'tier': 'tier1'},
        'errors': [{
            'span_reproduction': [0, 1], 'span_reference': [0, 1], 'category': 'lexical',
            'subtype': 'x', 'source': 'interlingual', 'severity': 'minor',
            'learner_form': 'a', 'corrected_form': 'b', 'explanation': 'why',
            'confidence': 0.9, 'is_mistake': False,
        }],
    }

    def test_writes_submission_grade_and_errors(self):
        db = _FakeDB({})

        dt_routes._persist_grade(db, 5, 'my repro', 'key-1', self._CONTRACT)

        kinds = [(name, method) for name, method, _ in db.calls]
        assert ('dt_submission', 'update') in kinds
        assert ('dt_grade', 'insert') in kinds
        assert ('dt_error_instance', 'insert') in kinds

        sub_update = next(p for n, m, p in db.calls if n == 'dt_submission' and m == 'update')
        assert sub_update == {'reproduction': 'my repro', 'idempotency_key': 'key-1'}

        grade_insert = next(p for n, m, p in db.calls if n == 'dt_grade' and m == 'insert')
        assert grade_insert['submission_id'] == 5
        assert grade_insert['scores'] == {'accuracy': 3}

        error_insert = next(p for n, m, p in db.calls if n == 'dt_error_instance' and m == 'insert')
        assert error_insert[0]['submission_id'] == 5
        assert error_insert[0]['learner_form'] == 'a'

    def test_skips_error_insert_when_no_errors(self):
        db = _FakeDB({})
        contract = {'scores': {}, 'overall_band': 4, 'diff': [], 'grader_trace': {}, 'errors': []}

        dt_routes._persist_grade(db, 5, 'repro', None, contract)

        assert not any(name == 'dt_error_instance' for name, _, _ in db.calls)

    def test_error_insert_failure_leaves_no_cache_satisfying_grade(self):
        """TASK-633: if the dt_error_instance insert raises (e.g. a severity
        CHECK, a transient error), the dt_grade row — which ``_cached_grade``
        keys off and never re-grades once present — must NOT have been written.
        Otherwise the cache serves this submission forever with errors: [],
        silently and permanently losing all evidence (ADR-019)."""
        db = _FailingInsertDB({}, fail_table='dt_error_instance')

        with pytest.raises(RuntimeError):
            dt_routes._persist_grade(db, 5, 'my repro', 'key-1', self._CONTRACT)

        assert not any(
            name == 'dt_grade' and method == 'insert' for name, method, _ in db.calls
        )

    def test_retry_regrades_after_partial_failure(self):
        """TASK-633: because the failed persist above wrote no dt_grade row,
        a retried submission finds an empty cache and re-grades rather than
        returning the poisoned errors: [] grade."""
        db = _FakeDB({'dt_grade': []})

        assert dt_routes._cached_grade(db, 5) is None


# ---------------------------------------------------------------------------
# _tokens_used_today (TASK-601 budget guardrail)
# ---------------------------------------------------------------------------

class TestTokensUsedToday:

    def test_zero_when_no_submissions_today(self):
        db = _FakeDB({'dt_submission': [], 'dt_grade': []})
        assert dt_routes._tokens_used_today(db, 'u1') == 0

    def test_sums_in_and_out_tokens_across_todays_grades(self):
        db = _FakeDB({
            'dt_submission': [{'id': 5}, {'id': 6}],
            'dt_grade': [
                {'grader_trace': {'tokens': {'in': 100, 'out': 40}}},
                {'grader_trace': {'tokens': {'in': 20, 'out': 10}}},
            ],
        })
        assert dt_routes._tokens_used_today(db, 'u1') == 170

    def test_tolerates_missing_grader_trace_tokens(self):
        db = _FakeDB({
            'dt_submission': [{'id': 5}],
            'dt_grade': [{'grader_trace': {}}, {'grader_trace': None}],
        })
        assert dt_routes._tokens_used_today(db, 'u1') == 0


# ---------------------------------------------------------------------------
# GET /api/dual-translation/next
# ---------------------------------------------------------------------------

class TestGetNext:

    def test_404_when_no_passage_available(self, client, auth_headers, monkeypatch):
        monkeypatch.setattr(dt_routes, '_resolve_l1_language_id', lambda db, uid: 2)
        monkeypatch.setattr(dt_routes, '_select_next_passage', lambda db, uid, l1: None)

        resp = client.get('/api/dual-translation/next', headers=auth_headers)

        assert resp.status_code == 404

    def test_200_creates_submission_and_returns_payload(self, client, app, auth_headers, monkeypatch):
        from unittest.mock import MagicMock

        # Force one arm (TASK-617) so the stamped value is deterministic here.
        monkeypatch.setattr(Config, 'DT_CORRECTION_STYLE', 'flag_only')
        monkeypatch.setattr(dt_routes, '_resolve_l1_language_id', lambda db, uid: 2)
        monkeypatch.setattr(dt_routes, '_select_next_passage', lambda db, uid, l1: {
            'passage_id': 7, 'l1_text': 'Hello world', 'age_tier': 3, 'l2_language_id': 3,
        })
        monkeypatch.setattr(DimensionService, 'get_language_code', classmethod(lambda cls, lid: 'ja'))

        def _no_active_rubric(db):
            raise RuntimeError("no active dt_rubric_version row")
        monkeypatch.setattr(dt_routes, 'get_active_rubric', _no_active_rubric)

        app.mock_supabase.table.return_value.insert.return_value.execute.return_value = (
            MagicMock(data=[{'id': 42}])
        )

        resp = client.get('/api/dual-translation/next', headers=auth_headers)

        assert resp.status_code == 200
        data = resp_json(resp)
        assert data['submission_id'] == 42
        assert data['l1_text'] == 'Hello world'
        assert data['age_tier'] == 3
        assert data['rubric_descriptors'] == {}
        # The assigned arm is returned to the client...
        assert data['correction_style'] == 'flag_only'
        # ...and stamped onto the dt_submission row for later analysis.
        insert_payload = app.mock_supabase.table.return_value.insert.call_args[0][0]
        assert insert_payload['correction_style'] == 'flag_only'


# ---------------------------------------------------------------------------
# POST /api/dual-translation/<id>/submit
# ---------------------------------------------------------------------------

class TestSubmit:

    _OWNER_ID = 'test-user-id-123'  # matches conftest's mocked auth identity

    _CONTRACT = {
        'scores': {'accuracy': 3, 'understandability': 4, 'fidelity': 3, 'range': 3, 'naturalness': 2},
        'overall_band': 3,
        'diff': [{'op': 'equal', 'a': [0, 5], 'b': [0, 5]}],
        'errors': [{
            'span_reproduction': [0, 3], 'span_reference': [0, 4], 'category': 'lexical',
            'subtype': 'article_omission', 'source': 'interlingual', 'severity': 'minor',
            'learner_form': 'cat', 'corrected_form': 'the cat', 'explanation': 'why',
            'confidence': 0.8, 'is_mistake': False,
        }],
        'grader_trace': {'tier': 'tier2', 'tokens': {'in': 10, 'out': 5}},
    }

    def _submission_row(self, user_id=_OWNER_ID):
        return {'id': 5, 'user_id': user_id, 'passage_id': 9, 'l1_language_id': 2}

    def _passage_row(self, status='active'):
        return {'id': 9, 'l2_text': 'gold text', 'l2_language_id': 1, 'age_tier': 4, 'status': status}

    def test_400_when_reproduction_missing(self, client, auth_headers):
        resp = client.post(
            '/api/dual-translation/5/submit', headers=auth_headers,
            json={'idempotency_key': 'k1'},
        )
        assert resp.status_code == 400

    def test_404_when_submission_not_found(self, client, auth_headers, monkeypatch):
        monkeypatch.setattr(dt_routes, '_get_submission', lambda db, sid: None)

        resp = client.post(
            '/api/dual-translation/5/submit', headers=auth_headers,
            json={'reproduction': 'my attempt'},
        )
        assert resp.status_code == 404

    def test_403_when_not_owner(self, client, auth_headers, monkeypatch):
        monkeypatch.setattr(
            dt_routes, '_get_submission', lambda db, sid: self._submission_row(user_id='someone-else'),
        )

        resp = client.post(
            '/api/dual-translation/5/submit', headers=auth_headers,
            json={'reproduction': 'my attempt'},
        )
        assert resp.status_code == 403

    def test_400_passage_retired(self, client, auth_headers, monkeypatch):
        monkeypatch.setattr(dt_routes, '_get_submission', lambda db, sid: self._submission_row())
        monkeypatch.setattr(dt_routes, '_cached_grade', lambda db, sid: None)
        monkeypatch.setattr(dt_routes, '_get_passage', lambda db, pid: self._passage_row(status='retired'))

        resp = client.post(
            '/api/dual-translation/5/submit', headers=auth_headers,
            json={'reproduction': 'my attempt'},
        )

        assert resp.status_code == 400
        assert resp_json(resp)['error_code'] == 'PASSAGE_RETIRED'

    def test_200_returns_full_contract_and_persists(self, client, auth_headers, monkeypatch):
        grade_calls = []
        persist_calls = []

        monkeypatch.setattr(dt_routes, '_get_submission', lambda db, sid: self._submission_row())
        monkeypatch.setattr(dt_routes, '_cached_grade', lambda db, sid: None)
        monkeypatch.setattr(dt_routes, '_get_passage', lambda db, pid: self._passage_row())

        def _fake_grade_submission(db, **kwargs):
            grade_calls.append(kwargs)
            return self._CONTRACT
        monkeypatch.setattr(dt_routes, 'grade_submission', _fake_grade_submission)

        def _fake_persist(db, submission_id, reproduction, idempotency_key, contract):
            persist_calls.append((submission_id, reproduction, idempotency_key, contract))
        monkeypatch.setattr(dt_routes, '_persist_grade', _fake_persist)

        resp = client.post(
            '/api/dual-translation/5/submit', headers=auth_headers,
            json={'reproduction': 'my attempt', 'idempotency_key': 'abc-123'},
        )

        assert resp.status_code == 200
        data = resp_json(resp)
        assert data['scores'] == self._CONTRACT['scores']
        assert data['overall_band'] == self._CONTRACT['overall_band']
        assert data['diff'] == self._CONTRACT['diff']
        assert data['errors'] == self._CONTRACT['errors']
        assert data['grader_trace'] == self._CONTRACT['grader_trace']

        assert len(grade_calls) == 1
        assert grade_calls[0]['passage_id'] == 9
        assert grade_calls[0]['gold_l2'] == 'gold text'
        assert grade_calls[0]['reproduction'] == 'my attempt'
        assert grade_calls[0]['l2_language_id'] == 1
        assert grade_calls[0]['l1_language_id'] == 2
        assert grade_calls[0]['age_tier'] == 4

        assert persist_calls == [(5, 'my attempt', 'abc-123', self._CONTRACT)]

    def test_max_tier_2_when_under_budget(self, client, auth_headers, monkeypatch):
        grade_calls = []

        monkeypatch.setattr(dt_routes, '_get_submission', lambda db, sid: self._submission_row())
        monkeypatch.setattr(dt_routes, '_cached_grade', lambda db, sid: None)
        monkeypatch.setattr(dt_routes, '_get_passage', lambda db, pid: self._passage_row())
        monkeypatch.setattr(dt_routes, '_tokens_used_today', lambda db, uid: 0)
        monkeypatch.setattr(dt_routes, '_persist_grade', lambda *a, **k: None)
        monkeypatch.setattr(Config, 'DT_DAILY_TOKEN_BUDGET', 20000)

        def _fake_grade_submission(db, **kwargs):
            grade_calls.append(kwargs)
            return self._CONTRACT
        monkeypatch.setattr(dt_routes, 'grade_submission', _fake_grade_submission)

        resp = client.post(
            '/api/dual-translation/5/submit', headers=auth_headers,
            json={'reproduction': 'my attempt'},
        )

        assert resp.status_code == 200
        assert grade_calls[0]['max_tier'] == 'tier2'

    def test_max_tier_1_when_over_budget(self, client, auth_headers, monkeypatch):
        grade_calls = []

        monkeypatch.setattr(dt_routes, '_get_submission', lambda db, sid: self._submission_row())
        monkeypatch.setattr(dt_routes, '_cached_grade', lambda db, sid: None)
        monkeypatch.setattr(dt_routes, '_get_passage', lambda db, pid: self._passage_row())
        monkeypatch.setattr(dt_routes, '_tokens_used_today', lambda db, uid: 25000)
        monkeypatch.setattr(dt_routes, '_persist_grade', lambda *a, **k: None)
        monkeypatch.setattr(Config, 'DT_DAILY_TOKEN_BUDGET', 20000)

        def _fake_grade_submission(db, **kwargs):
            grade_calls.append(kwargs)
            return self._CONTRACT
        monkeypatch.setattr(dt_routes, 'grade_submission', _fake_grade_submission)

        resp = client.post(
            '/api/dual-translation/5/submit', headers=auth_headers,
            json={'reproduction': 'my attempt'},
        )

        # Never hard-failed: still 200 with a grade, just capped to tier1.
        assert resp.status_code == 200
        assert grade_calls[0]['max_tier'] == 'tier1'

    def test_budget_zero_always_caps_to_tier1(self, client, auth_headers, monkeypatch):
        grade_calls = []

        monkeypatch.setattr(dt_routes, '_get_submission', lambda db, sid: self._submission_row())
        monkeypatch.setattr(dt_routes, '_cached_grade', lambda db, sid: None)
        monkeypatch.setattr(dt_routes, '_get_passage', lambda db, pid: self._passage_row())
        monkeypatch.setattr(dt_routes, '_tokens_used_today', lambda db, uid: 0)
        monkeypatch.setattr(dt_routes, '_persist_grade', lambda *a, **k: None)
        monkeypatch.setattr(Config, 'DT_DAILY_TOKEN_BUDGET', 0)

        def _fake_grade_submission(db, **kwargs):
            grade_calls.append(kwargs)
            return self._CONTRACT
        monkeypatch.setattr(dt_routes, 'grade_submission', _fake_grade_submission)

        resp = client.post(
            '/api/dual-translation/5/submit', headers=auth_headers,
            json={'reproduction': 'my attempt'},
        )

        assert resp.status_code == 200
        assert grade_calls[0]['max_tier'] == 'tier1'

    def test_duplicate_idempotency_key_returns_cached_grade_without_regrading(self, client, auth_headers, monkeypatch):
        cached_contract = {**self._CONTRACT, 'overall_band': 2}

        monkeypatch.setattr(dt_routes, '_get_submission', lambda db, sid: self._submission_row())
        monkeypatch.setattr(dt_routes, '_cached_grade', lambda db, sid: cached_contract)

        def _boom(db, **kwargs):
            raise AssertionError("should not re-grade a submission that already has a cached grade")
        monkeypatch.setattr(dt_routes, 'grade_submission', _boom)

        resp = client.post(
            '/api/dual-translation/5/submit', headers=auth_headers,
            json={'reproduction': 'my attempt', 'idempotency_key': 'abc-123'},
        )

        assert resp.status_code == 200
        data = resp_json(resp)
        assert data['overall_band'] == 2


# ---------------------------------------------------------------------------
# _fetch_profile_entries (TASK-611)
# ---------------------------------------------------------------------------

class TestFetchProfileEntries:

    def test_maps_rows_and_resolves_language_codes(self, monkeypatch):
        db = _FakeDB({
            'dt_error_profile_entry': [{
                'l1_language_id': 2, 'l2_language_id': 3, 'subtype': 'article_omission',
                'count': 5, 'severity_rank': 8.0,
                'trend': {'window_days': 30, 'current_count': 5, 'previous_count': 8, 'delta_pct': -37.5},
                'remediation_status': 'queued',
            }],
        })
        monkeypatch.setattr(
            DimensionService, 'get_language_code',
            classmethod(lambda cls, lid: {2: 'en', 3: 'ja'}[lid]),
        )

        result = dt_routes._fetch_profile_entries(db, 'u1')

        assert result == [{
            'subtype': 'article_omission',
            'l1_language': 'en',
            'l2_language': 'ja',
            'count': 5,
            'severity_rank': 8.0,
            'remediation_status': 'queued',
            'trend': {'window_days': 30, 'current_count': 5, 'previous_count': 8, 'delta_pct': -37.5},
        }]

    def test_empty_when_no_rows(self):
        db = _FakeDB({'dt_error_profile_entry': []})
        assert dt_routes._fetch_profile_entries(db, 'u1') == []


# ---------------------------------------------------------------------------
# GET /api/dual-translation/profile
# ---------------------------------------------------------------------------

class TestGetProfile:

    def test_200_returns_entries_from_helper(self, client, auth_headers, monkeypatch):
        entries = [
            {
                'subtype': 'article_omission', 'l1_language': 'en', 'l2_language': 'ja',
                'count': 5, 'severity_rank': 8.0, 'remediation_status': 'queued',
                'trend': {'delta_pct': -37.5},
            },
            {
                'subtype': 'tone_confusion', 'l1_language': 'en', 'l2_language': 'zh',
                'count': 1, 'severity_rank': 1.0, 'remediation_status': 'resolved',
                'trend': None,
            },
        ]
        monkeypatch.setattr(dt_routes, '_fetch_profile_entries', lambda db, uid: entries)

        resp = client.get('/api/dual-translation/profile', headers=auth_headers)

        assert resp.status_code == 200
        data = resp_json(resp)
        assert data['entries'] == entries

    def test_200_empty_list_when_no_profile_yet(self, client, auth_headers, monkeypatch):
        monkeypatch.setattr(dt_routes, '_fetch_profile_entries', lambda db, uid: [])

        resp = client.get('/api/dual-translation/profile', headers=auth_headers)

        assert resp.status_code == 200
        assert resp_json(resp)['entries'] == []

    def test_500_when_db_not_configured(self, client, app, auth_headers):
        app.supabase_service = None

        resp = client.get('/api/dual-translation/profile', headers=auth_headers)

        assert resp.status_code == 500


# ---------------------------------------------------------------------------
# _fetch_due_cards / _get_card / _apply_card_review (TASK-614)
# ---------------------------------------------------------------------------

class TestFetchDueCards:

    def test_maps_rows_into_card_dicts(self):
        db = _FakeDB({
            'dt_card': [{
                'id': 11, 'card_type': 'cloze', 'subtype': 'article',
                'prompt_payload': {'prompt': '____ cat', 'answer': 'the'},
                'state': 'new', 'due_date': None,
            }],
        })

        result = dt_routes._fetch_due_cards(db, 'u1')

        assert result == [{
            'card_id': 11, 'card_type': 'cloze', 'subtype': 'article',
            'prompt_payload': {'prompt': '____ cat', 'answer': 'the'},
            'state': 'new', 'due_date': None,
        }]

    def test_empty_when_no_due_cards(self):
        db = _FakeDB({'dt_card': []})
        assert dt_routes._fetch_due_cards(db, 'u1') == []


class TestGetCard:

    def test_returns_row_when_found(self):
        db = _FakeDB({'dt_card': [{'id': 11, 'user_id': 'u1', 'state': 'new'}]})
        assert dt_routes._get_card(db, 11) == {'id': 11, 'user_id': 'u1', 'state': 'new'}

    def test_none_when_not_found(self):
        db = _FakeDB({'dt_card': []})
        assert dt_routes._get_card(db, 11) is None


class TestApplyCardReview:

    def test_new_card_good_rating_graduates_to_review_state(self):
        row = {
            'stability': None, 'difficulty': None, 'due_date': None,
            'last_review': None, 'reps': 0, 'lapses': 0, 'state': 'new',
        }

        new_card = dt_routes._apply_card_review(row, 3)  # GOOD

        assert new_card.state == 'review'
        assert new_card.reps == 1
        assert new_card.due_date is not None

    def test_again_rating_increments_lapses(self):
        row = {
            'stability': 5.0, 'difficulty': 4.0, 'due_date': '2026-07-10',
            'last_review': '2026-07-01T00:00:00+00:00', 'reps': 3, 'lapses': 0,
            'state': 'review',
        }

        new_card = dt_routes._apply_card_review(row, 1)  # AGAIN

        assert new_card.state == 'relearning'
        assert new_card.lapses == 1


# ---------------------------------------------------------------------------
# GET /api/dual-translation/cards/due
# ---------------------------------------------------------------------------

class TestGetDueCards:

    def test_200_returns_interleaved_due_cards(self, client, auth_headers, monkeypatch):
        due = [
            {'card_id': 1, 'card_type': 'cloze', 'subtype': 'article',
             'prompt_payload': {}, 'state': 'new', 'due_date': None},
            {'card_id': 2, 'card_type': 'cloze', 'subtype': 'classifier',
             'prompt_payload': {}, 'state': 'new', 'due_date': None},
        ]
        monkeypatch.setattr(dt_routes.dt_cards, 'generate_cards_for_queued_entries', lambda db, uid: 0)
        monkeypatch.setattr(dt_routes, '_fetch_due_cards', lambda db, uid: due)

        resp = client.get('/api/dual-translation/cards/due', headers=auth_headers)

        assert resp.status_code == 200
        data = resp_json(resp)
        assert data['total'] == 2
        assert {c['card_id'] for c in data['cards']} == {1, 2}

    def test_200_empty_when_nothing_due(self, client, auth_headers, monkeypatch):
        monkeypatch.setattr(dt_routes.dt_cards, 'generate_cards_for_queued_entries', lambda db, uid: 0)
        monkeypatch.setattr(dt_routes, '_fetch_due_cards', lambda db, uid: [])

        resp = client.get('/api/dual-translation/cards/due', headers=auth_headers)

        assert resp.status_code == 200
        data = resp_json(resp)
        assert data['cards'] == []
        assert data['total'] == 0

    def test_500_when_db_not_configured(self, client, app, auth_headers):
        app.supabase_service = None

        resp = client.get('/api/dual-translation/cards/due', headers=auth_headers)

        assert resp.status_code == 500


# ---------------------------------------------------------------------------
# POST /api/dual-translation/cards/<id>/review
# ---------------------------------------------------------------------------

class TestSubmitCardReview:

    _OWNER_ID = 'test-user-id-123'  # matches conftest's mocked auth identity

    def _card_row(self, user_id=_OWNER_ID):
        return {
            'id': 11, 'user_id': user_id, 'stability': None, 'difficulty': None,
            'due_date': None, 'last_review': None, 'reps': 0, 'lapses': 0, 'state': 'new',
        }

    def test_400_when_rating_missing_or_invalid(self, client, auth_headers):
        resp = client.post(
            '/api/dual-translation/cards/11/review', headers=auth_headers, json={'rating': 9},
        )
        assert resp.status_code == 400

    def test_404_when_card_not_found(self, client, auth_headers, monkeypatch):
        monkeypatch.setattr(dt_routes, '_get_card', lambda db, cid: None)

        resp = client.post(
            '/api/dual-translation/cards/11/review', headers=auth_headers, json={'rating': 3},
        )
        assert resp.status_code == 404

    def test_403_when_not_owner(self, client, auth_headers, monkeypatch):
        monkeypatch.setattr(dt_routes, '_get_card', lambda db, cid: self._card_row(user_id='someone-else'))

        resp = client.post(
            '/api/dual-translation/cards/11/review', headers=auth_headers, json={'rating': 3},
        )
        assert resp.status_code == 403

    def test_200_updates_fsrs_state_and_logs_review(self, client, app, auth_headers, monkeypatch):
        monkeypatch.setattr(dt_routes, '_get_card', lambda db, cid: self._card_row())

        resp = client.post(
            '/api/dual-translation/cards/11/review', headers=auth_headers, json={'rating': 3},
        )

        assert resp.status_code == 200
        data = resp_json(resp)
        assert data['new_state'] == 'review'
        assert data['next_due'] is not None

        calls = app.mock_supabase.table.return_value
        card_update = calls.update.call_args_list
        # last update() call on the shared mock chain is dt_card's FSRS state write
        assert any(c.args[0].get('state') == 'review' for c in card_update)

        review_insert = calls.insert.call_args[0][0]
        assert review_insert == {'card_id': 11, 'rating': 3, 'was_correct': True}

    def test_was_correct_inferred_false_on_again_rating(self, client, app, auth_headers, monkeypatch):
        monkeypatch.setattr(dt_routes, '_get_card', lambda db, cid: self._card_row())

        resp = client.post(
            '/api/dual-translation/cards/11/review', headers=auth_headers, json={'rating': 1},
        )

        assert resp.status_code == 200
        review_insert = app.mock_supabase.table.return_value.insert.call_args[0][0]
        assert review_insert['was_correct'] is False

    def test_explicit_was_correct_overrides_inference(self, client, app, auth_headers, monkeypatch):
        monkeypatch.setattr(dt_routes, '_get_card', lambda db, cid: self._card_row())

        resp = client.post(
            '/api/dual-translation/cards/11/review', headers=auth_headers,
            json={'rating': 3, 'was_correct': False},
        )

        assert resp.status_code == 200
        review_insert = app.mock_supabase.table.return_value.insert.call_args[0][0]
        assert review_insert['was_correct'] is False


# ---------------------------------------------------------------------------
# GET /next error-card interleaving (TASK-614)
# ---------------------------------------------------------------------------

class TestNextInterleavesErrorCards:

    def test_serves_error_card_when_selected_and_due(self, client, auth_headers, monkeypatch):
        monkeypatch.setattr(dt_routes, '_should_serve_error_card', lambda: True)
        monkeypatch.setattr(dt_routes, '_next_due_error_card', lambda db, uid: {
            'card_id': 11, 'card_type': 'cloze', 'subtype': 'article',
            'prompt_payload': {'prompt': '____ cat', 'answer': 'the'},
            'state': 'new', 'due_date': None,
        })

        resp = client.get('/api/dual-translation/next', headers=auth_headers)

        assert resp.status_code == 200
        data = resp_json(resp)
        assert data['type'] == 'error_card'
        assert data['card_id'] == 11

    def test_falls_through_to_passage_when_selected_but_none_due(
        self, client, app, auth_headers, monkeypatch,
    ):
        from unittest.mock import MagicMock

        monkeypatch.setattr(dt_routes, '_should_serve_error_card', lambda: True)
        monkeypatch.setattr(dt_routes, '_next_due_error_card', lambda db, uid: None)
        monkeypatch.setattr(dt_routes, '_resolve_l1_language_id', lambda db, uid: 2)
        monkeypatch.setattr(dt_routes, '_select_next_passage', lambda db, uid, l1: {
            'passage_id': 7, 'l1_text': 'Hello world', 'age_tier': 3, 'l2_language_id': 3,
        })
        monkeypatch.setattr(DimensionService, 'get_language_code', classmethod(lambda cls, lid: 'ja'))

        def _no_active_rubric(db):
            raise RuntimeError("no active dt_rubric_version row")
        monkeypatch.setattr(dt_routes, 'get_active_rubric', _no_active_rubric)

        app.mock_supabase.table.return_value.insert.return_value.execute.return_value = (
            MagicMock(data=[{'id': 42}])
        )

        resp = client.get('/api/dual-translation/next', headers=auth_headers)

        assert resp.status_code == 200
        data = resp_json(resp)
        assert data['type'] == 'passage'
        assert data['submission_id'] == 42

    def test_serves_passage_when_not_selected(self, client, app, auth_headers, monkeypatch):
        from unittest.mock import MagicMock

        monkeypatch.setattr(dt_routes, '_should_serve_error_card', lambda: False)

        def _boom(db, uid):
            raise AssertionError("should not check for due cards when not interleaving this call")
        monkeypatch.setattr(dt_routes, '_next_due_error_card', _boom)

        monkeypatch.setattr(dt_routes, '_resolve_l1_language_id', lambda db, uid: 2)
        monkeypatch.setattr(dt_routes, '_select_next_passage', lambda db, uid, l1: {
            'passage_id': 7, 'l1_text': 'Hello world', 'age_tier': 3, 'l2_language_id': 3,
        })
        monkeypatch.setattr(DimensionService, 'get_language_code', classmethod(lambda cls, lid: 'ja'))

        def _no_active_rubric(db):
            raise RuntimeError("no active dt_rubric_version row")
        monkeypatch.setattr(dt_routes, 'get_active_rubric', _no_active_rubric)

        app.mock_supabase.table.return_value.insert.return_value.execute.return_value = (
            MagicMock(data=[{'id': 42}])
        )

        resp = client.get('/api/dual-translation/next', headers=auth_headers)

        assert resp.status_code == 200
        assert resp_json(resp)['type'] == 'passage'
