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

    def in_(self, *a, **k):
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
                'severity': 'local', 'learner_form': 'a', 'corrected_form': 'b',
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
            'subtype': 'x', 'source': 'interlingual', 'severity': 'local',
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
            'subtype': 'article_omission', 'source': 'interlingual', 'severity': 'local',
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
