"""Test prestudy: services/prestudy.py, the two /api/tests/<id>/prestudy routes,
and the prestudied flag on the submission RPC (wiki/features/test-prestudy.md).

Everything is mocked: a minimal fake query builder for the service, the Flask
client with the DB-touching helpers monkeypatched for the routes.
"""

import json
from unittest.mock import MagicMock

import routes.tests as test_routes
from routes.tests import _call_submission_rpc
from services import prestudy


def resp_json(resp):
    return json.loads(resp.data)


# ---------------------------------------------------------------------------
# Fake query builder: per-table rows, chainable no-op filters
# ---------------------------------------------------------------------------

class _FakeResult:
    def __init__(self, data):
        self.data = data


class _FakeQuery:
    def __init__(self, data):
        self._data = data

    def __getattr__(self, name):
        if name.startswith('_'):
            raise AttributeError(name)
        return lambda *a, **k: self

    def execute(self):
        return _FakeResult(self._data)


class _FakeDB:
    def __init__(self, tables):
        self._tables = tables

    def table(self, name):
        return _FakeQuery(self._tables.get(name, []))


TEST_ROW = {
    'id': 't1', 'slug': 'cats', 'title': '猫', 'language_id': 3,
    'transcript': '猫がいる。', 'audio_url': None, 'difficulty': 3, 'target_age_tier': 2,
    'vocab_sense_ids': [11, 12], 'vocab_token_map': [['猫', 11], ['が', None], ['いる', 12], ['。', None]],
    'furigana_payload': None, 'pinyin_payload': None,
}


# ---------------------------------------------------------------------------
# services/prestudy.py
# ---------------------------------------------------------------------------

class TestEvidenceRows:

    def test_majority_per_sense(self):
        answers = [
            {'sense_id': 11, 'correct': True}, {'sense_id': 11, 'correct': True},
            {'sense_id': 11, 'correct': False},
            {'sense_id': 12, 'correct': False}, {'sense_id': 12, 'correct': True},
        ]
        rows = prestudy.evidence_rows(answers, {11, 12})
        assert rows == [{'sense_id': 11, 'is_correct': True}, {'sense_id': 12, 'is_correct': False}]

    def test_idk_counts_as_wrong_even_if_flagged_correct(self):
        rows = prestudy.evidence_rows([{'sense_id': 11, 'correct': True, 'idk': True}], {11})
        assert rows == [{'sense_id': 11, 'is_correct': False}]

    def test_drops_senses_outside_the_test_and_bad_ids(self):
        answers = [{'sense_id': 99, 'correct': True}, {'sense_id': 'x'}, {'sense_id': None}, {}, {'sense_id': '11', 'correct': True}]
        assert prestudy.evidence_rows(answers, {11}) == [{'sense_id': 11, 'is_correct': True}]

    def test_empty(self):
        assert prestudy.evidence_rows([], {11}) == []
        assert prestudy.evidence_rows(None, {11}) == []


class TestTrimExercise:

    def test_keeps_only_renderer_fields(self):
        row = {'id': 5, 'exercise_type': 'cloze_completion', 'ladder_level': 3, 'content': {
            'sentence_with_blank': '__がいる。', 'options': ['猫', '犬'], 'correct_answer': '猫',
            'explanation': 'e', 'original_sentence': '猫がいる。', 'internal_notes': 'secret'}}
        out = prestudy.trim_exercise(row)
        assert out['type'] == 'cloze_completion' and out['group'] == 'use' and out['level'] == 3
        assert 'internal_notes' not in out['c']
        assert out['c']['correct_answer'] == '猫'

    def test_unknown_type_and_bad_content_are_dropped(self):
        assert prestudy.trim_exercise({'exercise_type': 'listening_flash', 'content': {}}) is None
        assert prestudy.trim_exercise({'exercise_type': 'cloze_completion', 'content': 'nope'}) is None

    def test_cloze_typed_keeps_only_accepted_answers(self):
        row = {'id': 1, 'exercise_type': 'cloze_typed', 'content': {
            'sentence_with_blank': '__', 'answer': {'accepted': ['猫'], 'grader': 'x'}}}
        assert prestudy.trim_exercise(row)['c']['answer'] == {'accepted': ['猫']}

    def test_group_exercises_caps_per_type(self):
        rows = [{'id': i, 'word_sense_id': 11, 'exercise_type': 'definition_match', 'content': {'word': 'w'}} for i in range(5)]
        rows.append({'id': 9, 'word_sense_id': 11, 'exercise_type': 'jumbled_sentence', 'content': {'chunks': []}})
        out = prestudy.group_exercises(rows)
        types = [e['type'] for e in out['11']]
        assert types.count('definition_match') == prestudy.MAX_EXERCISES_PER_TYPE
        assert types.count('jumbled_sentence') == 1


class TestBuildPayload:

    def _db(self):
        return _FakeDB({
            'questions': [{'sense_ids': [11], 'question_text': 'LEAK?', 'choices': ['a'], 'answer': 'a'}],
            'dim_word_senses': [
                {'id': 11, 'vocab_id': 1, 'sense_rank': 1, 'definition': 'cat', 'definition_language_id': 2,
                 'example_sentence': None, 'pronunciation': None,
                 'dim_vocabulary': {'lemma': '猫', 'part_of_speech': 'noun', 'frequency_rank': 4.8, 'reading': 'ねこ'}},
                {'id': 12, 'vocab_id': 2, 'sense_rank': 1, 'definition': 'to be', 'definition_language_id': 2,
                 'example_sentence': None, 'pronunciation': None,
                 'dim_vocabulary': {'lemma': 'いる', 'part_of_speech': 'verb', 'frequency_rank': 6.5, 'reading': 'いる'}},
            ],
            'user_vocabulary_knowledge': [{'sense_id': 12, 'p_known': 0.93, 'status': 'known', 'evidence_count': 7}],
            'exercises': [],
            'user_calibration_state': [{'ability_zipf': 5.4}],
        })

    def test_payload_shape_and_no_question_leak(self):
        out = prestudy.build_prestudy_payload(self._db(), TEST_ROW, 'u1', 2)
        assert out['questions'] == [{'sense_ids': [11]}]
        blob = json.dumps(out, ensure_ascii=False)
        assert 'LEAK?' not in blob and 'choices' not in blob
        assert out['senses']['11']['lemma'] == '猫'
        assert out['senses']['11']['glosses']['2']['def'] == 'cat'
        assert out['knowledge'] == {'12': {'p': 0.93, 'status': 'known', 'n': 7}}
        assert out['ability_zipf'] == 5.4
        assert out['gloss_language_id'] == 2
        assert out['test']['vocab_token_map'] == TEST_ROW['vocab_token_map']

    def test_falls_back_to_native_gloss_language(self):
        out = prestudy.build_prestudy_payload(self._db(), TEST_ROW, 'u1', None)
        assert out['gloss_language_id'] == 3


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

class TestPrestudyRoutes:

    def _wire(self, monkeypatch, test=TEST_ROW):
        monkeypatch.setattr(test_routes, '_find_test_for_prestudy', lambda db, ident: test)

    def test_get_requires_auth(self, client):
        assert client.get('/api/tests/cats/prestudy').status_code == 401

    def test_get_404(self, client, auth_headers, monkeypatch):
        self._wire(monkeypatch, test=None)
        assert client.get('/api/tests/nope/prestudy', headers=auth_headers).status_code == 404

    def test_get_200(self, client, auth_headers, monkeypatch):
        self._wire(monkeypatch)
        monkeypatch.setattr('services.vocabulary.gloss_lookup.get_user_definition_language_id', lambda db, uid: 2)
        monkeypatch.setattr('services.prestudy.build_prestudy_payload',
                            lambda db, test, uid, gl: {'test': {'id': test['id']}, 'gloss_language_id': gl})
        resp = client.get('/api/tests/cats/prestudy', headers=auth_headers)
        assert resp.status_code == 200
        data = resp_json(resp)
        assert data['status'] == 'success' and data['test'] == {'id': 't1'} and data['gloss_language_id'] == 2

    def test_evidence_requires_auth(self, client):
        assert client.post('/api/tests/cats/prestudy/evidence', json={'answers': []}).status_code == 401

    def test_evidence_400_on_bad_body(self, client, auth_headers, monkeypatch):
        self._wire(monkeypatch)
        assert client.post('/api/tests/cats/prestudy/evidence', headers=auth_headers, json={}).status_code == 400
        assert client.post('/api/tests/cats/prestudy/evidence', headers=auth_headers,
                           json={'answers': 'x'}).status_code == 400
        too_many = [{'sense_id': 11, 'correct': True}] * (test_routes._PRESTUDY_MAX_ANSWERS + 1)
        assert client.post('/api/tests/cats/prestudy/evidence', headers=auth_headers,
                           json={'answers': too_many}).status_code == 400

    def test_evidence_writes_one_row_per_test_sense_without_side_effects(self, client, auth_headers, monkeypatch):
        self._wire(monkeypatch)
        calls = []

        class _Svc:
            def __init__(self, db=None):
                pass

            def update_from_word_tests_batch(self, **kw):
                calls.append(kw)
                return [{'sense_id': r['sense_id']} for r in kw['results']]

        monkeypatch.setattr(test_routes, 'VocabularyKnowledgeService', _Svc)
        body = {'answers': [
            {'sense_id': 11, 'correct': True}, {'sense_id': 11, 'correct': True, 'idk': False},
            {'sense_id': 12, 'correct': False, 'idk': True},
            {'sense_id': 999, 'correct': True},   # not in this test: dropped
        ]}
        resp = client.post('/api/tests/cats/prestudy/evidence', headers=auth_headers, json=body)
        assert resp.status_code == 200
        assert resp_json(resp)['recorded'] == 2
        assert len(calls) == 1
        kw = calls[0]
        assert kw['side_effects'] is False and kw['language_id'] == 3
        assert kw['results'] == [{'sense_id': 11, 'is_correct': True}, {'sense_id': 12, 'is_correct': False}]


# ---------------------------------------------------------------------------
# Submission RPC: p_prestudied
# ---------------------------------------------------------------------------

def _rpc_client(side_effect):
    client = MagicMock()
    chain = MagicMock()
    chain.execute.side_effect = side_effect
    client.rpc.return_value = chain
    return client


class TestSubmissionPrestudiedFlag:

    def test_not_sent_on_ordinary_attempts(self, app):
        client = _rpc_client([MagicMock(data={'success': True, 'attempt_id': 'a'})])
        with app.app_context():
            _call_submission_rpc(client, 'u', 't', 1, 1, db_responses=[])
        params = client.rpc.call_args[0][1]
        assert 'p_prestudied' not in params

    def test_sent_when_prestudied(self, app):
        client = _rpc_client([MagicMock(data={'success': True, 'attempt_id': 'a'})])
        with app.app_context():
            result = _call_submission_rpc(client, 'u', 't', 1, 1, db_responses=[], prestudied=True)
        assert result['success'] is True
        assert client.rpc.call_args[0][1]['p_prestudied'] is True

    def test_falls_back_when_function_lacks_the_parameter(self, app):
        class _Missing(Exception):
            def json(self):
                return {'code': 'PGRST202', 'message': 'Could not find the function public.process_test_submission'}

        sent = []
        client = MagicMock()

        def _rpc(name, params):
            sent.append(dict(params))
            chain = MagicMock()
            if 'p_prestudied' in params:
                chain.execute.side_effect = _Missing('missing')
            else:
                chain.execute.return_value = MagicMock(data={'success': True, 'attempt_id': 'b'})
            return chain

        client.rpc.side_effect = _rpc
        with app.app_context():
            result = _call_submission_rpc(client, 'u', 't', 1, 1, db_responses=[], prestudied=True)
        assert result['attempt_id'] == 'b'
        assert 'p_prestudied' in sent[0] and 'p_prestudied' not in sent[1]

    def test_jsonb_success_quirk_is_not_mistaken_for_missing_function(self, app):
        class _Jsonb(Exception):
            def json(self):
                return {'success': True, 'attempt_id': 'c'}

        client = _rpc_client([_Jsonb('jsonb')])
        with app.app_context():
            result = _call_submission_rpc(client, 'u', 't', 1, 1, db_responses=[], prestudied=True)
        assert result['attempt_id'] == 'c'
        assert client.rpc.call_count == 1
