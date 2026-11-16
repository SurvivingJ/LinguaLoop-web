"""Prestudy fixes from end-to-end testing (2026-11-16):

* one definition of a test's "share of key words that are new", used by the
  daily session's prestudy card (plan_for_tests) and the prestudy page payload;
* a "Produce available" signal computed with the produce route's own rule
  (choose_produce_window), in the payload and a small GET route, and the
  produce route's reference-language rule shared with it;
* sentence rows from an older transcript never make a Produce window eligible
  (the passage route would answer 409 SENTENCES_STALE).
"""

import json

import pytest

import routes.tests.prestudy as test_routes
from services import prestudy
from tests.test_prestudy_session import _DB


T1 = '00000000-0000-0000-0000-0000000000a1'


def resp_json(resp):
    return json.loads(resp.data)


# ---------------------------------------------------------------------------
# One definition of the unknown share
# ---------------------------------------------------------------------------

class TestSharePlan:

    def test_counts_linked_senses_below_half(self):
        p = {1: 0.9, 2: 0.1, 3: 0.49, 4: 0.5}.get
        plan = prestudy.share_plan([1, 2, 3, 4, 4, None], p)
        assert plan == {'unknown_share': 0.5, 'unknown': 2, 'n': 4, 'plan_mode': 'full'}

    def test_empty(self):
        assert prestudy.share_plan([], lambda s: 0.0) == {
            'unknown_share': 0.0, 'unknown': 0, 'n': 0, 'plan_mode': 'none'}

    @pytest.mark.parametrize('share,mode', [(0.26, 'full'), (0.25, 'light'), (0.05, 'light'), (0.049, 'none')])
    def test_plan_mode_thresholds(self, share, mode):
        assert prestudy.plan_mode_for_share(share) == mode

    def _db(self):
        # sense 1 known, 2 unknown by evidence; 3 common and 4 rare by prior;
        # 5 has no frequency (prior 0.3 -> new); 6 has no sense row at all
        vocab = {3: 7.0, 4: 2.0, 5: None}
        return _DB({
            'tests': [{'id': T1, 'vocab_sense_ids': [1, 2, 3, 4, 5, 6]}],
            'questions': [],
            'user_vocabulary_knowledge': [
                {'user_id': 'u', 'sense_id': 1, 'p_known': 0.9, 'status': 'known', 'evidence_count': 3},
                {'user_id': 'u', 'sense_id': 2, 'p_known': 0.1, 'status': 'unknown', 'evidence_count': 3}],
            'dim_word_senses': [
                {'id': s, 'vocab_id': 100 + s, 'sense_rank': 1, 'definition': f'd{s}', 'definition_language_id': 3,
                 'example_sentence': None, 'pronunciation': None,
                 'dim_vocabulary': {'lemma': f'w{s}', 'part_of_speech': 'noun', 'frequency_rank': f, 'reading': None}}
                for s, f in [(1, 5.0), (2, 5.0)] + list(vocab.items())],
            'user_calibration_state': [{'ability_zipf': 5.0}],
            'exercises': [],
            'test_sentences': [],
        })

    def test_payload_share_equals_the_daily_session_card_share(self):
        """The 29% vs 53% report: both figures now come from share_plan over
        the same inputs, so on the same data they are equal."""
        db = self._db()
        test = {'id': T1, 'language_id': 3, 'vocab_sense_ids': [1, 2, 3, 4, 5, 6]}
        card = prestudy.plan_for_tests(db, 'u', 3, [{'id': T1, 'test_type': 'reading'}])[T1]
        page = prestudy.build_prestudy_payload(db, test, 'u', 2)['plan']
        assert page['unknown_share'] == card['unknown_share']
        assert page['unknown'] == card['unknown'] == 4      # 2, 4, 5, 6
        assert page['n'] == card['n'] == 6
        assert page['plan_mode'] == card['plan_mode']


# ---------------------------------------------------------------------------
# Produce availability
# ---------------------------------------------------------------------------

def _sentences(n=4, hash_='h1'):
    return [{'id': i, 'idx': i, 'l2_text': 'x' * 10, 'test_id': T1, 'token_start': 2 * i,
             'token_end': 2 * i + 2, 'transcript_hash': hash_} for i in range(n)]


def _refs(ids, tight=0.9, l1=2):
    return [{'sentence_id': i, 'tightness': tight, 'review_verdict': 'pass', 'l1_language_id': l1,
             'is_active': True} for i in ids]


class TestProduceAvailable:

    test = {'id': T1, 'language_id': 3, 'transcript_hash': 'h1', 'vocab_token_map': []}

    def test_resolve_l1(self):
        assert prestudy.resolve_produce_l1(3, 2) == 2
        assert prestudy.resolve_produce_l1(3, None) == 2          # unset -> English
        assert prestudy.resolve_produce_l1(3, 1) == 1
        assert prestudy.resolve_produce_l1(3, 3) == 2             # never the test's own language
        assert prestudy.resolve_produce_l1(2, 2) is None          # English test, English learner
        assert prestudy.resolve_produce_l1(2, 'x') is None        # bad input -> English, = test language

    def test_true_when_a_window_has_references(self):
        db = _DB({'test_sentences': _sentences(), 'test_sentence_references': _refs([0, 1])})
        assert prestudy.produce_available(db, self.test, 2) is True

    def test_false_without_two_consecutive_references(self):
        db = _DB({'test_sentences': _sentences(), 'test_sentence_references': _refs([0, 2])})
        assert prestudy.produce_available(db, self.test, 2) is False

    def test_false_for_other_reference_language_or_low_tightness(self):
        assert prestudy.produce_available(
            _DB({'test_sentences': _sentences(), 'test_sentence_references': _refs([0, 1], l1=1)}),
            self.test, 2) is False
        assert prestudy.produce_available(
            _DB({'test_sentences': _sentences(), 'test_sentence_references': _refs([0, 1], tight=0.3)}),
            self.test, 2) is False

    def test_false_without_l1_or_on_read_failure(self):
        db = _DB({'test_sentences': _sentences(), 'test_sentence_references': _refs([0, 1])})
        assert prestudy.produce_available(db, self.test, None) is False
        failing = _DB({'test_sentences': _sentences()}, fail={'test_sentence_references': 'boom'})
        assert prestudy.produce_available(failing, self.test, 2) is False

    def test_stale_sentence_rows_are_not_eligible(self):
        db = _DB({'test_sentences': _sentences(hash_='old'), 'test_sentence_references': _refs([0, 1, 2, 3])})
        assert prestudy.choose_produce_window(db, self.test, 2, [], []) is None
        assert prestudy.produce_available(db, self.test, 2) is False
        # a test row without a stored hash cannot be checked: rows count as current
        assert prestudy.produce_available(db, {**self.test, 'transcript_hash': None}, 2) is True

    def test_availability_matches_the_route_rule_for_any_primed_set(self):
        """Primed / wrong senses only rank eligible windows."""
        db = _DB({'test_sentences': _sentences(), 'test_sentence_references': _refs([1, 2])})
        assert prestudy.produce_available(db, self.test, 2) is True
        assert prestudy.choose_produce_window(db, self.test, 2, [999], [998]) == (1, 2)

    def test_payload_carries_the_flag(self):
        db = _DB({'questions': [], 'test_sentences': _sentences(),
                  'test_sentence_references': _refs([0, 1])})
        test = {**self.test, 'vocab_sense_ids': []}
        out = prestudy.build_prestudy_payload(db, test, 'u', 2)
        assert out['produce_available'] is True and out['produce_l1_language_id'] == 2
        out = prestudy.build_prestudy_payload(_DB({'questions': []}), test, 'u', 2)
        assert out['produce_available'] is False


class TestProduceRoutes:

    ROW = {'id': T1, 'slug': 'cats', 'language_id': 3, 'vocab_sense_ids': [11], 'transcript_hash': 'h1'}

    def test_produce_available_route(self, client, auth_headers, monkeypatch):
        monkeypatch.setattr(test_routes, '_find_test_for_prestudy', lambda db, i: self.ROW)
        monkeypatch.setattr('services.vocabulary.gloss_lookup.get_user_definition_language_id', lambda db, u: 3)
        seen = {}
        monkeypatch.setattr(prestudy, 'choose_produce_window',
                            lambda db, t, l1, primed, wrong: seen.update(l1=l1, primed=primed) or (0, 1))
        data = resp_json(client.get('/api/tests/cats/prestudy/produce-available', headers=auth_headers))
        assert data['produce_available'] is True and data['l1_language_id'] == 2
        assert seen == {'l1': 2, 'primed': []}
        monkeypatch.setattr(prestudy, 'choose_produce_window', lambda *a: None)
        data = resp_json(client.get('/api/tests/cats/prestudy/produce-available', headers=auth_headers))
        assert data['produce_available'] is False

    def test_produce_available_route_auth_and_404(self, client, auth_headers, monkeypatch):
        assert client.get('/api/tests/cats/prestudy/produce-available').status_code == 401
        monkeypatch.setattr(test_routes, '_find_test_for_prestudy', lambda db, i: None)
        assert client.get('/api/tests/x/prestudy/produce-available', headers=auth_headers).status_code == 404

    def test_produce_route_uses_the_shared_l1_rule(self, client, auth_headers, monkeypatch):
        monkeypatch.setattr(test_routes, '_find_test_for_prestudy',
                            lambda db, i: {**self.ROW, 'language_id': 2})
        monkeypatch.setattr('services.vocabulary.gloss_lookup.get_user_definition_language_id', lambda db, u: 2)
        resp = client.post('/api/tests/cats/prestudy/produce', headers=auth_headers, json={})
        assert resp.status_code == 422 and resp_json(resp)['error_code'] == 'NO_WINDOW'

    def test_prestudy_columns_include_the_transcript_hash(self):
        assert 'transcript_hash' in test_routes._PRESTUDY_TEST_COLUMNS
