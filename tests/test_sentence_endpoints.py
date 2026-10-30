"""TASK-909 — GET /api/tests/<slug>/sentences and POST /api/dual-translation/passage-from-sentences.

Same two layers as tests/test_dual_translation_routes.py: helper-level tests
against a minimal fake query builder, route-level tests through the Flask
client with the DB-touching helpers monkeypatched on the route modules. The
new tables (test_sentences, test_sentence_references, dt_passage range
columns) do not exist live yet; everything here is mocked.
"""

import json

import pytest

import routes.dual_translation as dt_routes
import routes.tests as test_routes
from services.dual_translation import primed_token


def resp_json(resp):
    return json.loads(resp.data)


# ---------------------------------------------------------------------------
# Fake query builder
# ---------------------------------------------------------------------------

class _FakeResult:
    def __init__(self, data):
        self.data = data


class _FakeQuery:
    def __init__(self, data, recorder, table_name, fail_insert=False):
        self._data = data
        self._recorder = recorder
        self._table_name = table_name
        self._fail_insert = fail_insert

    def __getattr__(self, name):
        # select/eq/gte/lte/in_/order/limit/... are chainable no-ops
        if name.startswith('_'):
            raise AttributeError(name)
        return lambda *a, **k: self

    def insert(self, payload):
        self._recorder.append((self._table_name, 'insert', payload))
        if self._fail_insert:
            raise RuntimeError('duplicate key value violates unique constraint')
        return self

    def execute(self):
        return _FakeResult(self._data)


class _FakeDB:
    def __init__(self, tables, fail_insert_tables=()):
        self._tables = tables
        self._fail = set(fail_insert_tables)
        self.calls = []

    def table(self, name):
        return _FakeQuery(self._tables.get(name, []), self.calls, name, name in self._fail)


SENTENCES = [
    {'id': 101, 'idx': 0, 'l2_text': '猫がいる。', 'char_start': 0, 'char_end': 5,
     'token_start': 0, 'token_end': 4, 'transcript_hash': 'h1'},
    {'id': 102, 'idx': 1, 'l2_text': '犬もいる。', 'char_start': 5, 'char_end': 10,
     'token_start': 4, 'token_end': 8, 'transcript_hash': 'h1'},
]
TEST = {'id': 't1', 'slug': 'cats', 'language_id': 3, 'difficulty': 4, 'transcript_hash': 'h1'}


# ---------------------------------------------------------------------------
# GET /api/tests/<slug>/sentences
# ---------------------------------------------------------------------------

class TestBuildSentencePayload:

    def test_shapes_rows_with_and_without_reference(self):
        refs = {101: {'l1_text': 'There is a cat.', 'tightness': 0.9}}
        out = test_routes.build_sentence_payload(SENTENCES, refs, withhold_l2=False)
        assert out[0] == {
            'idx': 0, 'l2_text': '猫がいる。', 'char_start': 0, 'char_end': 5,
            'token_start': 0, 'token_end': 4,
            'reference': {'l1_text': 'There is a cat.', 'tightness': 0.9},
        }
        assert out[1]['reference'] is None

    def test_withholds_l2_text(self):
        out = test_routes.build_sentence_payload(SENTENCES, {}, withhold_l2=True)
        assert all('l2_text' not in row for row in out)
        assert out[0]['char_start'] == 0 and out[0]['token_end'] == 4


class TestSentenceHelpers:

    def test_resolve_l1_from_code(self):
        assert test_routes._resolve_sentence_l1(_FakeDB({}), 'u1', 'en') == 2
        assert test_routes._resolve_sentence_l1(_FakeDB({}), 'u1', 'ZH') == 1
        assert test_routes._resolve_sentence_l1(_FakeDB({}), 'u1', 'xx') is None

    def test_resolve_l1_defaults_to_native_then_english(self):
        assert test_routes._resolve_sentence_l1(_FakeDB({'users': [{'native_language_id': 1}]}), 'u1', None) == 1
        assert test_routes._resolve_sentence_l1(_FakeDB({'users': []}), 'u1', None) == 2

    def test_has_attempt_today(self):
        assert test_routes._has_attempt_today(_FakeDB({'test_attempts': [{'id': 'a'}]}), 'u1', 't1', 3) is True
        assert test_routes._has_attempt_today(_FakeDB({'test_attempts': []}), 'u1', 't1', 3) is False

    def test_load_active_references_maps_by_sentence(self):
        db = _FakeDB({'test_sentence_references': [
            {'sentence_id': 101, 'l1_text': 'x', 'tightness': 0.8, 'review_verdict': 'pass'}]})
        assert set(test_routes._load_active_references(db, [101, 102], 2)) == {101}
        assert test_routes._load_active_references(db, [], 2) == {}


class TestGetSentencesRoute:

    def _wire(self, monkeypatch, *, test=TEST, rows=SENTENCES, refs=None, attempted=True):
        monkeypatch.setattr(test_routes, '_find_test_for_sentences', lambda db, ident: test)
        monkeypatch.setattr(test_routes, '_resolve_sentence_l1', lambda db, uid, code: 2)
        monkeypatch.setattr(test_routes, '_load_sentence_rows', lambda db, tid: rows)
        monkeypatch.setattr(test_routes, '_load_active_references', lambda db, ids, l1: refs or {})
        monkeypatch.setattr(test_routes, '_has_attempt_today', lambda db, uid, tid, lid: attempted)

    def test_401_without_jwt(self, client):
        assert client.get('/api/tests/cats/sentences').status_code == 401

    def test_404_unknown_test(self, client, auth_headers, monkeypatch):
        self._wire(monkeypatch, test=None)
        assert client.get('/api/tests/nope/sentences', headers=auth_headers).status_code == 404

    def test_200_returns_spans_and_references(self, client, auth_headers, monkeypatch):
        self._wire(monkeypatch, refs={101: {'l1_text': 'There is a cat.', 'tightness': 0.9}})
        resp = client.get('/api/tests/cats/sentences?l1=en', headers=auth_headers)
        assert resp.status_code == 200
        data = resp_json(resp)
        assert data['l2_withheld'] is False
        assert [s['l2_text'] for s in data['sentences']] == ['猫がいる。', '犬もいる。']
        assert data['sentences'][0]['reference']['l1_text'] == 'There is a cat.'
        assert data['sentences'][1]['reference'] is None
        # spans reproduce the transcript
        transcript = '猫がいる。犬もいる。'
        for s in data['sentences']:
            assert transcript[s['char_start']:s['char_end']] == s['l2_text']

    def test_produce_withholds_l2_before_attempt(self, client, auth_headers, monkeypatch):
        self._wire(monkeypatch, attempted=False)
        resp = client.get('/api/tests/cats/sentences?mode=produce', headers=auth_headers)
        data = resp_json(resp)
        assert resp.status_code == 200
        assert data['l2_withheld'] is True
        assert all('l2_text' not in s for s in data['sentences'])

    def test_produce_returns_l2_after_attempt(self, client, auth_headers, monkeypatch):
        self._wire(monkeypatch, attempted=True)
        data = resp_json(client.get('/api/tests/cats/sentences?mode=produce', headers=auth_headers))
        assert data['l2_withheld'] is False
        assert data['sentences'][0]['l2_text'] == '猫がいる。'

    def test_other_modes_never_withhold(self, client, auth_headers, monkeypatch):
        self._wire(monkeypatch, attempted=False)
        data = resp_json(client.get('/api/tests/cats/sentences?mode=preview', headers=auth_headers))
        assert data['sentences'][0]['l2_text'] == '猫がいる。'

    def test_409_when_hash_stale(self, client, auth_headers, monkeypatch):
        stale = [dict(SENTENCES[0], transcript_hash='old'), SENTENCES[1]]
        self._wire(monkeypatch, rows=stale)
        resp = client.get('/api/tests/cats/sentences', headers=auth_headers)
        assert resp.status_code == 409
        assert resp_json(resp)['error_code'] == 'SENTENCES_STALE'

    def test_200_empty_when_no_rows(self, client, auth_headers, monkeypatch):
        self._wire(monkeypatch, rows=[])
        resp = client.get('/api/tests/cats/sentences', headers=auth_headers)
        assert resp.status_code == 200
        assert resp_json(resp)['sentences'] == []

    def test_400_unknown_l1(self, client, auth_headers, monkeypatch):
        self._wire(monkeypatch)
        monkeypatch.setattr(test_routes, '_resolve_sentence_l1', lambda db, uid, code: None)
        assert client.get('/api/tests/cats/sentences?l1=xx', headers=auth_headers).status_code == 400


# ---------------------------------------------------------------------------
# POST /api/dual-translation/passage-from-sentences
# ---------------------------------------------------------------------------

REFS = {
    101: {'sentence_id': 101, 'l1_text': 'There is a cat.', 'tightness': 0.9, 'review_verdict': 'pass'},
    102: {'sentence_id': 102, 'l1_text': 'There is a dog too.', 'tightness': 0.8, 'review_verdict': 'rewritten'},
}


class TestFindOrCreateRangePassage:

    def test_reuses_existing_row_without_insert(self):
        db = _FakeDB({'dt_passage': [{'id': 7, 'age_tier': 2, 'l2_language_id': 3, 'status': 'active'}]})
        row = dt_routes._find_or_create_range_passage(db, TEST, 0, 1, l2_text='猫がいる。犬もいる。')
        assert row['id'] == 7
        assert not any(m == 'insert' for _, m, _ in db.calls)

    def test_inserts_with_range_columns(self):
        class _DB(_FakeDB):
            def table(self, name):
                q = super().table(name)
                if name == 'dt_passage':
                    # select -> none; insert().execute() -> the new row
                    q._data = [{'id': 8, 'age_tier': 2, 'l2_language_id': 3, 'status': 'active'}]
                    q.execute = lambda: _FakeResult(q._data if any(m == 'insert' for _, m, _ in self.calls) else [])
                return q
        db = _DB({})
        row = dt_routes._find_or_create_range_passage(db, TEST, 0, 1, l2_text='猫がいる。犬もいる。')
        assert row['id'] == 8
        payload = next(p for n, m, p in db.calls if n == 'dt_passage' and m == 'insert')
        assert payload['sentence_start'] == 0 and payload['sentence_end'] == 1
        assert payload['source_ref_id'] == 't1' and payload['source_kind'] == 'test_transcript'
        assert payload['l2_text'] == '猫がいる。犬もいる。'
        assert payload['age_tier'] == 2  # difficulty 4 -> T2
        assert payload['status'] == 'active'

    def test_lost_race_rereads_winner(self):
        db = _FakeDB({'dt_passage': []}, fail_insert_tables=('dt_passage',))
        # second select (after the failed insert) finds the winner
        reads = {'n': 0}
        winner = {'id': 9, 'age_tier': 2, 'l2_language_id': 3, 'status': 'active'}

        def _select(db_, ref, s, e):
            reads['n'] += 1
            return None if reads['n'] == 1 else winner
        orig = dt_routes._select_range_passage
        try:
            dt_routes._select_range_passage = _select
            row = dt_routes._find_or_create_range_passage(db, TEST, 0, 1, l2_text='x')
        finally:
            dt_routes._select_range_passage = orig
        assert row == winner


class TestUsableReferences:

    def test_filters_to_pass_and_rewritten(self):
        db = _FakeDB({'test_sentence_references': [
            REFS[101], dict(REFS[102], review_verdict='fail')]})
        out = dt_routes._get_usable_references(db, [101, 102], 2)
        assert set(out) == {101}


class TestPassageFromSentencesRoute:

    _OWNER = 'test-user-id-123'

    def _body(self, **over):
        body = {'test_id': 't1', 'sentence_start': 0, 'sentence_end': 1,
                'l1_language_id': 2, 'primed_sense_ids': [11, 12]}
        body.update(over)
        return body

    def _wire(self, app, monkeypatch, *, attempted=True, test=TEST, sentences=SENTENCES, refs=REFS,
              passage=None):
        from unittest.mock import MagicMock
        monkeypatch.setattr(dt_routes, '_user_has_attempted', lambda db, uid, tid: attempted)
        monkeypatch.setattr(dt_routes, '_get_test_for_passage', lambda db, tid: test)
        monkeypatch.setattr(dt_routes, '_get_sentence_range',
                            lambda db, tid, s, e: [r for r in sentences if s <= r['idx'] <= e])
        monkeypatch.setattr(dt_routes, '_get_usable_references',
                            lambda db, ids, l1: {k: v for k, v in refs.items() if k in ids})
        created = []

        def _foc(db, t, s, e, *, l2_text):
            created.append({'start': s, 'end': e, 'l2_text': l2_text})
            return passage or {'id': 7, 'age_tier': 2, 'l2_language_id': 3, 'status': 'active'}
        monkeypatch.setattr(dt_routes, '_find_or_create_range_passage', _foc)
        monkeypatch.setattr(dt_routes, '_rubric_descriptors_for', lambda db, tier, code: {})
        app.mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[{'id': 42}])
        return created

    def test_401_without_jwt(self, client):
        assert client.post('/api/dual-translation/passage-from-sentences', json=self._body()).status_code == 401

    def test_400_bad_body(self, client, auth_headers):
        resp = client.post('/api/dual-translation/passage-from-sentences', headers=auth_headers,
                           json={'test_id': 't1'})
        assert resp.status_code == 400

    def test_400_range_too_wide(self, client, app, auth_headers, monkeypatch):
        self._wire(app, monkeypatch)
        resp = client.post('/api/dual-translation/passage-from-sentences', headers=auth_headers,
                           json=self._body(sentence_end=4))
        assert resp.status_code == 400

    def test_403_when_not_attempted(self, client, app, auth_headers, monkeypatch):
        self._wire(app, monkeypatch, attempted=False)
        resp = client.post('/api/dual-translation/passage-from-sentences', headers=auth_headers, json=self._body())
        assert resp.status_code == 403

    def test_404_unknown_test(self, client, app, auth_headers, monkeypatch):
        self._wire(app, monkeypatch, test=None)
        resp = client.post('/api/dual-translation/passage-from-sentences', headers=auth_headers, json=self._body())
        assert resp.status_code == 404

    def test_422_when_sentence_lacks_reference(self, client, app, auth_headers, monkeypatch):
        self._wire(app, monkeypatch, refs={101: REFS[101]})
        resp = client.post('/api/dual-translation/passage-from-sentences', headers=auth_headers, json=self._body())
        assert resp.status_code == 422
        data = resp_json(resp)
        assert data['error_code'] == 'REFERENCE_MISSING'
        assert data['details']['missing_idx'] == [1]

    def test_422_when_no_sentence_rows(self, client, app, auth_headers, monkeypatch):
        self._wire(app, monkeypatch, sentences=[])
        resp = client.post('/api/dual-translation/passage-from-sentences', headers=auth_headers, json=self._body())
        assert resp.status_code == 422
        assert resp_json(resp)['error_code'] == 'SENTENCES_MISSING'

    def test_409_when_hash_stale(self, client, app, auth_headers, monkeypatch):
        stale = [dict(SENTENCES[0], transcript_hash='old'), SENTENCES[1]]
        self._wire(app, monkeypatch, sentences=stale)
        resp = client.post('/api/dual-translation/passage-from-sentences', headers=auth_headers, json=self._body())
        assert resp.status_code == 409

    def test_200_returns_passage_l1_and_signed_token_never_l2(self, client, app, auth_headers, monkeypatch):
        created = self._wire(app, monkeypatch)
        resp = client.post('/api/dual-translation/passage-from-sentences', headers=auth_headers, json=self._body())
        assert resp.status_code == 200
        data = resp_json(resp)
        assert data['passage_id'] == 7
        assert data['n_sentences'] == 2
        assert data['submission_id'] == 42
        # L1 = English -> single-space join; L2 (ja) gold joined with no separator
        assert data['l1_text'] == 'There is a cat. There is a dog too.'
        assert created == [{'start': 0, 'end': 1, 'l2_text': '猫がいる。犬もいる。'}]
        assert 'l2_text' not in data
        assert '猫' not in resp.data.decode('utf-8')
        with app.app_context():
            assert primed_token.load(data['primed_token'], self._OWNER, 7) == [11, 12]
        insert_payload = app.mock_supabase.table.return_value.insert.call_args[0][0]
        assert insert_payload['passage_id'] == 7 and insert_payload['l1_language_id'] == 2

    def test_same_range_twice_returns_same_passage_id(self, client, app, auth_headers, monkeypatch):
        self._wire(app, monkeypatch)
        ids = set()
        for _ in range(2):
            resp = client.post('/api/dual-translation/passage-from-sentences', headers=auth_headers,
                               json=self._body())
            ids.add(resp_json(resp)['passage_id'])
        assert ids == {7}

    def test_token_bound_to_user_and_passage(self, app):
        with app.app_context():
            tok = primed_token.issue('u1', 7, [1, 2, 2, 'x', 0])
            assert primed_token.load(tok, 'u1', 7) == [1, 2]
            with pytest.raises(primed_token.PrimedTokenError):
                primed_token.load(tok, 'u2', 7)
            with pytest.raises(primed_token.PrimedTokenError):
                primed_token.load(tok, 'u1', 8)
            with pytest.raises(primed_token.PrimedTokenError):
                primed_token.load('garbage', 'u1', 7)
