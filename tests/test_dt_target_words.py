"""TASK-910 — grader target words -> per-word production evidence.

Mirrors tests/test_dual_translation_grader_cascade.py (every DB / model
boundary mocked). Covers:
  * classify_target_words: produced (exact surface), variant (lemma present,
    surface absent), omitted, and an error-instance span covering the surface
    -> variant with the error subtype attached;
  * grade_submission attaches ``target_words`` only when asked;
  * the route writes one BKT evidence row per sense via the batch path with
    side_effects=False, and rejects a forged/mismatched primed token.
"""

import json

import pytest

import routes.dual_translation as dt_routes
from services.dimension_service import DimensionService
from services.dual_translation import grader_cascade, primed_token
from services.dual_translation.grader_cascade import classify_target_words


@pytest.fixture(autouse=True)
def _lang(monkeypatch):
    monkeypatch.setattr(
        DimensionService, 'get_language_code',
        classmethod(lambda cls, lid: {1: 'zh', 2: 'en', 3: 'ja'}.get(lid)),
    )


# Gold window: two en sentences joined with a single space (join_sentences).
TOKEN_MAP = [
    ['The', None], [' ', None], ['cat', 11], [' ', None], ['sat', 12], ['.', None],
    ['It', None], [' ', None], ['purred', 13], [' ', None], ['loudly', 14], ['.', None],
]
GOLD = 'The cat sat. It purred loudly.'
LEMMAS = {11: 'cat', 12: 'sit', 13: 'purr', 14: 'loudly'}


def _rows(repro, errors=(), ids=(11, 12, 13, 14)):
    out = classify_target_words(
        list(ids), token_map=TOKEN_MAP, gold=GOLD, reproduction=repro,
        errors=list(errors), l2_code='en', lemmas=LEMMAS,
    )
    return {r['sense_id']: r for r in out}


class TestClassify:

    def test_produced_exact_surface(self):
        rows = _rows('The cat sat. It purred loudly.')
        assert all(r['status'] == 'produced' for r in rows.values())
        assert rows[11]['in_gold'] == 'cat' and rows[11]['in_yours'] == 'cat'
        assert rows[11]['is_correct'] is True

    def test_produced_is_case_and_width_insensitive(self):
        rows = _rows('the CAT ｓat.')
        assert rows[11]['status'] == 'produced'
        assert rows[12]['status'] == 'produced'

    def test_variant_when_lemma_present_surface_absent(self):
        rows = _rows('The cat will sit. It will purr.')
        assert rows[12]['status'] == 'variant'
        assert rows[12]['in_yours'] == 'sit'
        assert rows[12]['error_subtype'] is None
        assert rows[12]['is_correct'] is True
        assert rows[13]['status'] == 'variant'

    def test_omitted(self):
        rows = _rows('The cat sat.')
        assert rows[13]['status'] == 'omitted'
        assert rows[13]['in_gold'] == 'purred'
        assert rows[13]['in_yours'] is None
        assert rows[13]['is_correct'] is False

    def test_error_span_covering_surface_is_variant_with_subtype(self):
        # 'purred' sits at [16, 22) in GOLD; the learner wrote 'purrs'.
        err = {
            'span_reference': [16, 22], 'span_reproduction': [16, 21],
            'subtype': 'verb_tense', 'learner_form': 'purrs', 'corrected_form': 'purred',
        }
        rows = _rows('The cat sat. It purrs loudly.', errors=[err])
        assert rows[13]['status'] == 'variant'
        assert rows[13]['error_subtype'] == 'verb_tense'
        assert rows[13]['learner_form'] == 'purrs'
        assert rows[13]['in_yours'] == 'purrs'
        assert rows[13]['is_correct'] is False

    def test_error_span_elsewhere_does_not_rescue_omission(self):
        err = {'span_reference': [0, 3], 'subtype': 'article', 'learner_form': 'A'}
        rows = _rows('A cat sat.', errors=[err])
        assert rows[13]['status'] == 'omitted'

    def test_sense_outside_window_reported_as_omitted_with_no_gold(self):
        rows = _rows('The cat sat.', ids=(11, 99))
        assert rows[99]['status'] == 'omitted'
        assert rows[99]['in_gold'] is None

    def test_cjk_surface_match_ignores_whitespace_and_kana_width(self):
        tm = [['猫', 21], ['が', None], ['ネコ', 22], ['。', None]]
        out = classify_target_words(
            [21, 22], token_map=tm, gold='猫がネコ。', reproduction='猫 が ねこ。',
            errors=[], l2_code='ja', lemmas={},
        )
        assert [r['status'] for r in out] == ['produced', 'produced']

    def test_order_and_dedupe_follow_target_list(self):
        out = classify_target_words(
            [13, 11, 13], token_map=TOKEN_MAP, gold=GOLD, reproduction='',
            errors=[], l2_code='en', lemmas={},
        )
        assert [r['sense_id'] for r in out] == [13, 11]


class TestGradeSubmissionWrapper:

    _CONTRACT = {'scores': {'accuracy': 4}, 'overall_band': 4, 'diff': [],
                 'errors': [], 'grader_trace': {'tier': 'tier0'}}

    def test_no_target_words_key_without_targets(self, monkeypatch):
        monkeypatch.setattr(grader_cascade, '_grade_cascade', lambda db, **kw: dict(self._CONTRACT))
        contract = grader_cascade.grade_submission(
            None, passage_id=1, gold_l2=GOLD, reproduction=GOLD,
            l2_language_id=2, l1_language_id=1, age_tier=3,
        )
        assert 'target_words' not in contract

    def test_attaches_rows_and_passes_cascade_kwargs_through(self, monkeypatch):
        seen = {}

        def _fake(db, **kw):
            seen.update(kw)
            return dict(self._CONTRACT)
        monkeypatch.setattr(grader_cascade, '_grade_cascade', _fake)

        contract = grader_cascade.grade_submission(
            None, passage_id=1, gold_l2=GOLD, reproduction='The cat sat.',
            l2_language_id=2, l1_language_id=1, age_tier=3, max_tier='tier1',
            target_sense_ids=[11, 13], target_token_map=TOKEN_MAP, target_lemmas=LEMMAS,
        )
        assert seen['max_tier'] == 'tier1'
        assert 'target_sense_ids' not in seen
        statuses = {r['sense_id']: r['status'] for r in contract['target_words']}
        assert statuses == {11: 'produced', 13: 'omitted'}


# ---------------------------------------------------------------------------
# Route: primed token -> evidence write
# ---------------------------------------------------------------------------

class _FakeResult:
    def __init__(self, data):
        self.data = data


class _FakeRpcDB:
    def __init__(self):
        self.rpc_calls = []

    def rpc(self, name, params):
        self.rpc_calls.append((name, params))
        db = self

        class _Q:
            def execute(self_inner):
                return _FakeResult([{'sense_id': r['sense_id']} for r in params['p_results']])
        return _Q()


class TestRecordTargetWordEvidence:

    def test_one_bkt_row_per_sense_with_no_side_effects(self, monkeypatch):
        db = _FakeRpcDB()
        captured = {}
        orig = dt_routes.VocabularyKnowledgeService.update_from_word_tests_batch

        def _spy(self, user_id, language_id, results, side_effects=True):
            captured['side_effects'] = side_effects
            return orig(self, user_id, language_id, results, side_effects=side_effects)
        monkeypatch.setattr(dt_routes.VocabularyKnowledgeService, 'update_from_word_tests_batch', _spy)

        rows = [
            {'sense_id': 11, 'status': 'produced', 'is_correct': True},
            {'sense_id': 12, 'status': 'variant', 'is_correct': True},
            {'sense_id': 13, 'status': 'variant', 'is_correct': False, 'error_subtype': 'verb_tense'},
            {'sense_id': 14, 'status': 'omitted', 'is_correct': False},
        ]
        dt_routes._record_target_word_evidence(db, 'u1', 2, 5, rows)

        assert captured['side_effects'] is False
        assert len(db.rpc_calls) == 1
        name, params = db.rpc_calls[0]
        assert name == 'update_vocabulary_from_word_tests_batch'
        assert params['p_user_id'] == 'u1' and params['p_language_id'] == 2
        assert params['p_results'] == [
            {'sense_id': 11, 'is_correct': True}, {'sense_id': 12, 'is_correct': True},
            {'sense_id': 13, 'is_correct': False}, {'sense_id': 14, 'is_correct': False},
        ]

    def test_no_rows_no_rpc(self):
        db = _FakeRpcDB()
        dt_routes._record_target_word_evidence(db, 'u1', 2, 5, [])
        assert db.rpc_calls == []

    def test_rpc_failure_is_swallowed(self):
        class _Boom:
            def rpc(self, *a, **k):
                raise RuntimeError('down')
        dt_routes._record_target_word_evidence(_Boom(), 'u1', 2, 5, [{'sense_id': 1, 'is_correct': True}])


class TestSubmitWithPrimedToken:

    _OWNER = 'test-user-id-123'
    _CONTRACT = {'scores': {'accuracy': 3}, 'overall_band': 3, 'diff': [], 'errors': [],
                 'grader_trace': {'tier': 'tier1', 'tokens': {'in': 1, 'out': 1}}}

    def _wire(self, monkeypatch, grade_calls, evidence_calls):
        monkeypatch.setattr(dt_routes, '_get_submission', lambda db, sid: {
            'id': 5, 'user_id': self._OWNER, 'passage_id': 9, 'l1_language_id': 2})
        monkeypatch.setattr(dt_routes, '_cached_grade', lambda db, sid: None)
        monkeypatch.setattr(dt_routes, '_get_passage', lambda db, pid: {
            'id': 9, 'l2_text': GOLD, 'l2_language_id': 2, 'age_tier': 3, 'status': 'active',
            'source_ref_id': 't1', 'sentence_start': 0, 'sentence_end': 1})
        monkeypatch.setattr(dt_routes, '_tokens_used_today', lambda db, uid: 0)
        monkeypatch.setattr(dt_routes, '_target_word_context', lambda db, passage, ids: {
            'target_sense_ids': ids, 'target_token_map': TOKEN_MAP, 'target_lemmas': LEMMAS})

        def _grade(db, **kw):
            grade_calls.append(kw)
            c = dict(self._CONTRACT)
            if kw.get('target_sense_ids'):
                c['target_words'] = classify_target_words(
                    kw['target_sense_ids'], token_map=kw['target_token_map'], gold=kw['gold_l2'],
                    reproduction=kw['reproduction'], errors=[], l2_code='en', lemmas=kw['target_lemmas'])
            return c
        monkeypatch.setattr(dt_routes, 'grade_submission', _grade)
        monkeypatch.setattr(dt_routes, '_persist_grade', lambda *a, **k: None)
        monkeypatch.setattr(dt_routes, 'credit_study_time', lambda *a, **k: None)
        monkeypatch.setattr(
            dt_routes, '_record_target_word_evidence',
            lambda db, uid, lid, sid, rows: evidence_calls.append((uid, lid, sid, rows)))

    def test_token_senses_become_target_words_and_evidence(self, client, app, auth_headers, monkeypatch):
        grade_calls, evidence_calls = [], []
        self._wire(monkeypatch, grade_calls, evidence_calls)
        with app.app_context():
            token = primed_token.issue(self._OWNER, 9, [11, 13])

        resp = client.post('/api/dual-translation/5/submit', headers=auth_headers,
                           json={'reproduction': 'The cat sat.', 'primed_token': token})

        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert grade_calls[0]['target_sense_ids'] == [11, 13]
        assert {r['sense_id']: r['status'] for r in data['target_words']} == {11: 'produced', 13: 'omitted'}
        assert len(evidence_calls) == 1
        uid, lid, sid, rows = evidence_calls[0]
        assert (uid, lid, sid) == (self._OWNER, 2, 5)
        assert [r['is_correct'] for r in rows] == [True, False]

    def test_token_for_other_passage_is_400(self, client, app, auth_headers, monkeypatch):
        grade_calls, evidence_calls = [], []
        self._wire(monkeypatch, grade_calls, evidence_calls)
        with app.app_context():
            token = primed_token.issue(self._OWNER, 8, [11])

        resp = client.post('/api/dual-translation/5/submit', headers=auth_headers,
                           json={'reproduction': 'The cat sat.', 'primed_token': token})

        assert resp.status_code == 400
        assert grade_calls == []

    def test_without_token_plain_dt_is_unchanged(self, client, auth_headers, monkeypatch):
        grade_calls, evidence_calls = [], []
        self._wire(monkeypatch, grade_calls, evidence_calls)

        resp = client.post('/api/dual-translation/5/submit', headers=auth_headers,
                           json={'reproduction': 'The cat sat.'})

        assert resp.status_code == 200
        assert 'target_sense_ids' not in grade_calls[0]
        assert 'target_words' not in json.loads(resp.data)
        assert evidence_calls == []
