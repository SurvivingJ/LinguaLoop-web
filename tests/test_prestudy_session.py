"""Test prestudy workflow beyond the page itself (wiki/features/test-prestudy.md):
session blocks and honest minutes in the daily queue, the measurement record,
server-verified prestudied attempts, next-day review, Produce, and the
study-plan setting. Everything is mocked.
"""

import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from flask import Flask, g

import routes.tests as test_routes
from routes import study_session as ss
from routes.study_session import _today_prestudy_ids, apply_prestudy, prestudy_block_id
from services import prestudy


def resp_json(resp):
    return json.loads(resp.data)


# ---------------------------------------------------------------------------
# A fake query builder that applies eq / in_ filters and records writes
# ---------------------------------------------------------------------------

class _Q:
    def __init__(self, db, table):
        self.db, self.table, self.filters, self.op, self.payload = db, table, [], 'select', None

    def select(self, *a, **k):
        return self

    def eq(self, col, val):
        self.filters.append((col, lambda v, val=val: v == val))
        return self

    def in_(self, col, vals):
        vals = list(vals)
        self.filters.append((col, lambda v, vals=vals: v in vals))
        return self

    def __getattr__(self, name):
        if name.startswith('_'):
            raise AttributeError(name)
        return lambda *a, **k: self

    def insert(self, payload):
        self.op, self.payload = 'insert', payload
        return self

    def update(self, payload):
        self.op, self.payload = 'update', payload
        return self

    def upsert(self, payload, **k):
        self.op, self.payload = 'upsert', payload
        return self

    def execute(self):
        if self.db.fail.get(self.table):
            raise RuntimeError(self.db.fail[self.table])
        if self.op != 'select':
            self.db.writes.append((self.table, self.op, self.payload))
            if self.op == 'insert':
                return SimpleNamespace(data=[{'id': 'new-id', **(self.payload if isinstance(self.payload, dict) else {})}])
            return SimpleNamespace(data=[])
        rows = [r for r in self.db.tables.get(self.table, [])
                if all(f(r.get(c)) for c, f in self.filters)]
        return SimpleNamespace(data=rows)


class _DB:
    def __init__(self, tables=None, fail=None):
        self.tables = tables or {}
        self.fail = fail or {}
        self.writes = []
        self.rpcs = []

    def table(self, name):
        return _Q(self, name)

    def rpc(self, name, params):
        self.rpcs.append((name, params))
        return SimpleNamespace(execute=lambda: SimpleNamespace(data=True))


T1, T2, T3 = ('11111111-1111-1111-1111-111111111111', '22222222-2222-2222-2222-222222222222',
              '33333333-3333-3333-3333-333333333333')


# ---------------------------------------------------------------------------
# apply_prestudy (pure)
# ---------------------------------------------------------------------------

def _test(tid, slot='new', done=False, ttype='listening'):
    return {'kind': 'test', 'id': tid, 'slug': f's-{tid[:4]}', 'test_type': ttype,
            'title': 't', 'slot_type': slot, 'is_completed': done}


def _plan(share, minutes, mode=None):
    mode = mode or ('full' if share > 0.25 else 'light' if share >= 0.05 else 'none')
    return {'unknown_share': share, 'unknown': 5, 'n': 10, 'plan_mode': mode, 'minutes_est': minutes}


class TestApplyPrestudy:

    def test_auto_inserts_blocks_before_hard_and_retry_tests_only(self):
        queue = [_test(T1), _test(T2, slot='retry'), _test(T3)]
        plans = {T1: _plan(0.6, 6), T2: _plan(0.02, 2), T3: _plan(0.01, 2)}
        out = apply_prestudy(queue, plans, [], 'auto', 0)
        kinds = [(q['kind'], q.get('test_id') or q['id']) for q in out]
        assert kinds == [('prestudy', T1), ('test', T1), ('prestudy', T2), ('test', T2), ('test', T3)]
        retry_block = out[2]
        assert retry_block['trigger'] == 'retry' and retry_block['plan_mode'] == 'full'
        assert out[0]['id'] == prestudy_block_id(T1) and out[0]['trigger'] == 'auto'
        assert all('prestudy_offer' in q for q in out if q['kind'] == 'test')

    def test_light_block_for_in_band_tests(self):
        out = apply_prestudy([_test(T1)], {T1: _plan(0.1, 1)}, [], 'auto', 0)
        assert out[0]['kind'] == 'prestudy' and out[0]['plan_mode'] == 'light' and out[0]['minutes_est'] == 1

    def test_ask_and_off_insert_nothing(self):
        for mode, rec in (('ask', True), ('off', False)):
            queue = [_test(T1), _test(T2, slot='retry')]
            out = apply_prestudy(queue, {T1: _plan(0.6, 6), T2: _plan(0.1, 2)}, [], mode, 30)
            assert [q['kind'] for q in out] == ['test', 'test']
            assert out[0]['prestudy_offer']['recommended'] is rec
            assert out[1]['prestudy_offer']['recommended'] is rec

    def test_no_block_for_a_completed_test_and_completed_blocks_stay_completed(self):
        out = apply_prestudy([_test(T1, done=True), _test(T2)], {T1: _plan(0.6, 6), T2: _plan(0.6, 6)},
                             [prestudy_block_id(T2)], 'auto', 0)
        blocks = [q for q in out if q['kind'] == 'prestudy']
        assert [b['test_id'] for b in blocks] == [T2] and blocks[0]['is_completed'] is True

    def test_blocks_that_cost_a_test_slot_defer_the_last_plain_new_test(self):
        queue = [_test(T1), _test(T2), _test(T3), {'kind': 'speed_round', 'id': 'speed_round_1'}]
        plans = {T1: _plan(0.6, 8)}
        out = apply_prestudy(queue, plans, [], 'auto', 15)      # 5 min per test, 8 min of study
        assert [q.get('test_id') or q['id'] for q in out] == [T1, T1, T2, T3, 'speed_round_1']
        deferred = next(q for q in out if q.get('id') == T3)
        assert deferred['is_bonus'] and deferred['deferred_for_prestudy']
        assert out[0]['tests_dropped_today'] == 1
        assert not out[2].get('is_bonus')

    def test_never_defers_every_test(self):
        out = apply_prestudy([_test(T1)], {T1: _plan(0.9, 10)}, [], 'auto', 2)
        assert not any(q.get('is_bonus') for q in out)

    def test_tests_without_a_plan_are_untouched(self):
        q = [_test(T1)]
        assert apply_prestudy(q, {}, [], 'auto', 30) == q
        assert 'prestudy_offer' not in q[0]

    def test_complete_block_accepts_todays_prestudy_ids(self):
        ids = _today_prestudy_ids([{'test_id': T1}, {'test_id': T2}])
        assert ids == {prestudy_block_id(T1), prestudy_block_id(T2)}


# ---------------------------------------------------------------------------
# services/prestudy.py
# ---------------------------------------------------------------------------

class TestServiceHelpers:

    def test_followups_from_answers(self):
        answers = [
            {'sense_id': 1, 'idk': True}, {'sense_id': 1, 'idk': True},          # idk twice
            {'sense_id': 2, 'idk': True},                                        # once: no
            {'sense_id': 3, 'correct': False, 'stage': 'readiness'},             # readiness miss
            {'sense_id': 4, 'correct': True, 'stage': 'readiness'},              # readiness ok
            {'sense_id': 9, 'idk': True}, {'sense_id': 9, 'idk': True},          # not in test
        ]
        assert prestudy.followups_from_answers(answers, {1, 2, 3, 4}) == {1: 'idk_twice', 3: 'readiness_missed'}

    def test_primed_missed(self):
        out = prestudy.primed_missed([1, 2], [{'sense_id': 2}, {'sense_id': 3}], {1, 2, 3})
        assert out == {2: 'primed_missed_in_test'}

    def test_estimate_minutes(self):
        assert prestudy.estimate_minutes(8, 4, 'full') == 10
        assert prestudy.estimate_minutes(3, 0, 'full') == 4
        assert prestudy.estimate_minutes(0, 0, 'full') == 2
        assert prestudy.estimate_minutes(9, 9, 'light') == 1

    def test_plan_for_tests_uses_knowledge_then_the_zipf_prior(self):
        db = _DB({
            'tests': [{'id': T1, 'vocab_sense_ids': [1, 2, 3, 4]}],
            'user_vocabulary_knowledge': [{'user_id': 'u', 'sense_id': 1, 'p_known': 0.9, 'status': 'known', 'evidence_count': 3},
                                          {'user_id': 'u', 'sense_id': 2, 'p_known': 0.1, 'status': 'unknown', 'evidence_count': 3}],
            'dim_word_senses': [{'id': 3, 'dim_vocabulary': {'frequency_rank': 7.0}},    # common -> known
                                {'id': 4, 'dim_vocabulary': {'frequency_rank': 2.0}}],   # rare -> unknown
            'user_calibration_state': [{'ability_zipf': 5.0}],
            'exercises': [{'word_sense_id': 2, 'is_active': True}],
        })
        plans = prestudy.plan_for_tests(db, 'u', 3, [{'id': T1, 'test_type': 'listening'},
                                                     {'id': T2, 'test_type': 'dictation'}])
        assert set(plans) == {T1}
        assert plans[T1]['unknown'] == 2 and plans[T1]['unknown_share'] == 0.5
        assert plans[T1]['plan_mode'] == 'full'

    def test_start_session_returns_none_without_the_table(self):
        db = _DB(fail={'prestudy_sessions': "PGRST205 Could not find the table 'public.prestudy_sessions'"})
        assert prestudy.start_session(db, 'u', {'id': T1, 'language_id': 3}) is None

    def test_start_session_clamps_and_tags_session_blocks(self):
        db = _DB()
        sid = prestudy.start_session(db, 'u', {'id': T1, 'language_id': 3}, trigger='bogus',
                                     unknown_share=1.7, session_block_id='prestudy_x', load_date='2026-10-31')
        assert sid == 'new-id'
        (_, op, row), = db.writes
        assert row['trigger'] == 'opt_in' and row['unknown_share_at_open'] == 1.0
        assert row['minutes_source'] == 'tests_share'

    def test_verification_falls_back_only_when_the_table_is_missing(self):
        missing = _DB(fail={'prestudy_sessions': 'relation "public.prestudy_sessions" does not exist'})
        assert prestudy.find_prestudy_for_attempt(missing, 'u', T1) == (None, False)
        empty = _DB({'prestudy_sessions': []})
        assert prestudy.find_prestudy_for_attempt(empty, 'u', T1) == (None, True)
        found = _DB({'prestudy_sessions': [{'id': 'ps1', 'user_id': 'u', 'test_id': T1, 'mode': 'prime',
                                            'status': 'completed', 'completed_at': 'x'}]})
        assert prestudy.find_prestudy_for_attempt(found, 'u', T1) == ('ps1', True)

    def test_complete_session_restricts_senses_credits_minutes_and_adds_followups(self, monkeypatch):
        credits = []
        monkeypatch.setattr('services.study_time.credit_study_time',
                            lambda db, u, lang, kind, secs, table, sid: credits.append((kind, secs, table, sid)) or True)
        monkeypatch.setattr(prestudy, '_tomorrow_iso', lambda db, u, l: '2026-11-01')
        db = _DB()
        session = {'id': 'ps1', 'status': 'open', 'mode': 'prime', 'language_id': 3}
        out = prestudy.complete_session(db, 'u', session, {
            'words_quizzed': [1, 2, 999], 'words_shown': ['1', 'x'], 'exposures': 40,
            'active_seconds': 99999, 'readiness_score': 9, 'readiness_n': 5, 'ready': True,
            'next_day_review_senses': [2, 999],
        }, {1, 2}, {1: 'idk_twice'})
        upd = next(p for t, op, p in db.writes if t == 'prestudy_sessions')
        assert upd['words_quizzed'] == [1, 2] and upd['words_shown'] == [1]
        assert upd['active_seconds'] == prestudy.MAX_ACTIVE_SECONDS
        assert upd['readiness_score'] == 5 and upd['status'] == 'completed'
        assert upd['next_day_review_senses'] == [1, 2]
        assert credits == [('prestudy', prestudy.MAX_ACTIVE_SECONDS, 'prestudy_sessions', 'ps1')]
        follow = next(p for t, op, p in db.writes if t == 'prestudy_followups')
        assert follow == [{'user_id': 'u', 'language_id': 3, 'sense_id': 1, 'session_id': 'ps1',
                           'reason': 'idk_twice', 'due_date': '2026-11-01'}]
        assert out['followups'] == 1

    def test_record_produce_sends_omitted_words_to_review(self, monkeypatch):
        monkeypatch.setattr(prestudy, '_tomorrow_iso', lambda db, u, l: '2026-11-01')
        db = _DB({'prestudy_sessions': [{'id': 'ps1', 'user_id': 'u', 'test_id': T1, 'mode': 'prime',
                                         'status': 'consumed', 'words_quizzed': [1, 2]}]})
        n = prestudy.record_produce(db, 'u', T1, 3, 77, [
            {'sense_id': 1, 'status': 'produced'}, {'sense_id': 2, 'status': 'omitted'}])
        assert n == 1
        produce = next(p for t, op, p in db.writes if t == 'prestudy_sessions')['produce']
        assert produce['produced'] == 1 and produce['omitted'] == 1 and produce['submission_id'] == 77
        (row,) = next(p for t, op, p in db.writes if t == 'prestudy_followups')
        assert row['reason'] == 'omitted_in_produce' and row['sense_id'] == 2

    def test_wrong_question_senses(self):
        db = _DB({
            'test_attempts': [{'id': 'a1', 'user_id': 'u', 'test_id': T1}],
            'question_attempt_results': [{'attempt_id': 'a1', 'user_id': 'u', 'question_id': 'q1', 'is_correct': False},
                                         {'attempt_id': 'a1', 'user_id': 'u', 'question_id': 'q2', 'is_correct': True}],
            'questions': [{'id': 'q1', 'sense_ids': [5, 6]}, {'id': 'q2', 'sense_ids': [7]}],
        })
        assert prestudy.wrong_question_senses(db, 'u', T1) == ('a1', [5, 6])

    def test_choose_produce_window_needs_references_over_the_floor(self):
        db = _DB({
            'test_sentences': [{'id': i, 'idx': i, 'l2_text': 'x' * 10, 'test_id': T1,
                                'token_start': 2 * i, 'token_end': 2 * i + 2} for i in range(4)],
            'test_sentence_references': [
                {'sentence_id': i, 'tightness': 0.9, 'review_verdict': 'pass', 'l1_language_id': 2,
                 'is_active': True} for i in range(4)],
        })
        test = {'id': T1, 'language_id': 3,
                'vocab_token_map': [['a', 0], ['b', 0], ['c', 5], ['d', 0], ['e', 0], ['f', 0], ['g', 6], ['h', 0]]}
        assert prestudy.choose_produce_window(db, test, 2, [5, 6], []) == (1, 3)
        low = _DB({**db.tables, 'test_sentence_references': [
            {**r, 'tightness': 0.3} for r in db.tables['test_sentence_references']]})
        assert prestudy.choose_produce_window(low, test, 2, [5, 6], []) is None


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

TEST_ROW = {'id': T1, 'slug': 'cats', 'language_id': 3, 'vocab_sense_ids': [11, 12]}


class TestRoutes:

    def test_session_start(self, client, auth_headers, monkeypatch):
        monkeypatch.setattr(test_routes, '_find_test_for_prestudy', lambda db, i: TEST_ROW)
        seen = {}
        monkeypatch.setattr(prestudy, 'start_session', lambda db, u, t, **kw: seen.update(kw) or 'ps1')
        resp = client.post('/api/tests/cats/prestudy/session', headers=auth_headers,
                           json={'trigger': 'auto', 'unknown_share': 0.4, 'plan_mode': 'full'})
        assert resp.status_code == 200 and resp_json(resp)['session_id'] == 'ps1'
        assert seen['trigger'] == 'auto' and seen['unknown_share'] == 0.4

    def test_evidence_completes_the_session_and_records_exercises(self, client, auth_headers, monkeypatch):
        monkeypatch.setattr(test_routes, '_find_test_for_prestudy', lambda db, i: TEST_ROW)
        monkeypatch.setattr(prestudy, 'test_sense_ids', lambda db, t: {11, 12})
        monkeypatch.setattr(prestudy, 'get_session', lambda db, u, sid: {
            'id': sid, 'test_id': T1, 'status': 'open', 'mode': 'prime', 'language_id': 3})
        completed = []
        monkeypatch.setattr(prestudy, 'complete_session',
                            lambda db, u, s, m, allowed, reasons: completed.append((m, reasons)) or {'session_id': s['id']})
        monkeypatch.setattr(prestudy, 'senses_with_exercises', lambda db, ids: {11})
        queued = []
        monkeypatch.setattr(prestudy, 'request_generation', lambda db, ids, lang, have: queued.append((ids, set(have))) or 1)
        recorded = []
        monkeypatch.setattr(test_routes, '_record_prestudy_exercises',
                            lambda db, u, ex, allowed: recorded.append(ex) or len(ex))

        class _Svc:
            def __init__(self, db=None):
                pass

            def update_from_word_tests_batch(self, **kw):
                assert kw['side_effects'] is False
                return []
        monkeypatch.setattr(test_routes, 'VocabularyKnowledgeService', _Svc)
        body = {'session_id': 'ps1',
                'answers': [{'sense_id': 11, 'idk': True}, {'sense_id': 11, 'idk': True}],
                'exercise_answers': [{'exercise_id': 'e1', 'correct': True}],
                'metrics': {'words_quizzed': [11, 12]}}
        resp = client.post('/api/tests/cats/prestudy/evidence', headers=auth_headers, json=body)
        assert resp.status_code == 200
        data = resp_json(resp)
        assert data['exercises_recorded'] == 1 and data['session'] == {'session_id': 'ps1'}
        assert completed[0][1] == {11: 'idk_twice'}
        assert queued == [([11, 12], {'11'})]

    def test_followup_evidence_writes_with_side_effects(self, client, auth_headers, monkeypatch):
        monkeypatch.setattr(test_routes, '_find_test_for_prestudy', lambda db, i: TEST_ROW)
        monkeypatch.setattr(prestudy, 'test_sense_ids', lambda db, t: {11, 12})
        monkeypatch.setattr(prestudy, 'get_session', lambda db, u, sid: None)
        calls = []

        class _Svc:
            def __init__(self, db=None):
                pass

            def update_from_word_tests_batch(self, **kw):
                calls.append(kw['side_effects'])
                return []
        monkeypatch.setattr(test_routes, 'VocabularyKnowledgeService', _Svc)
        resp = client.post('/api/tests/cats/prestudy/evidence', headers=auth_headers,
                           json={'mode': 'followup', 'answers': [{'sense_id': 11, 'correct': True}]})
        assert resp.status_code == 200 and calls == [True]

    def test_followup_payload_requires_an_attempt(self, client, auth_headers, monkeypatch):
        monkeypatch.setattr(test_routes, '_find_test_for_prestudy', lambda db, i: TEST_ROW)
        monkeypatch.setattr('services.vocabulary.gloss_lookup.get_user_definition_language_id', lambda db, u: 2)
        monkeypatch.setattr(prestudy, 'build_prestudy_payload', lambda db, t, u, gl: {'test': {}})
        monkeypatch.setattr(prestudy, 'wrong_question_senses', lambda db, u, t: (None, []))
        assert client.get('/api/tests/cats/prestudy?mode=followup', headers=auth_headers).status_code == 400
        monkeypatch.setattr(prestudy, 'wrong_question_senses', lambda db, u, t: ('a1', [11]))
        monkeypatch.setattr(prestudy, 'latest_prime_session', lambda db, u, t: {'words_quizzed': [11]})
        data = resp_json(client.get('/api/tests/cats/prestudy?mode=followup', headers=auth_headers))
        assert data['followup_sense_ids'] == [11] and data['primed_sense_ids'] == [11]

    def test_produce_requires_an_attempt_and_a_window(self, client, auth_headers, monkeypatch):
        monkeypatch.setattr(test_routes, '_find_test_for_prestudy', lambda db, i: TEST_ROW)
        monkeypatch.setattr('services.vocabulary.gloss_lookup.get_user_definition_language_id', lambda db, u: 2)
        monkeypatch.setattr(prestudy, 'wrong_question_senses', lambda db, u, t: (None, []))
        assert client.post('/api/tests/cats/prestudy/produce', headers=auth_headers, json={}).status_code == 403
        monkeypatch.setattr(prestudy, 'wrong_question_senses', lambda db, u, t: ('a1', [12]))
        monkeypatch.setattr(prestudy, 'latest_prime_session', lambda db, u, t: {'words_quizzed': [11, 99]})
        monkeypatch.setattr(prestudy, 'test_sense_ids', lambda db, t: {11, 12})
        monkeypatch.setattr(prestudy, 'choose_produce_window', lambda *a: None)
        resp = client.post('/api/tests/cats/prestudy/produce', headers=auth_headers, json={})
        assert resp.status_code == 422 and resp_json(resp)['error_code'] == 'NO_WINDOW'
        seen = {}
        monkeypatch.setattr(prestudy, 'choose_produce_window', lambda db, t, l1, primed, wrong: seen.update(
            primed=primed, wrong=wrong, l1=l1) or (1, 2))
        import routes.dual_translation as dt_routes
        from utils.responses import api_success
        monkeypatch.setattr(dt_routes, 'open_range_passage',
                            lambda db, u, tid, a, b, l1, primed, extra=None: api_success({**extra, 'submission_id': 5, 'primed': primed}))
        data = resp_json(client.post('/api/tests/cats/prestudy/produce', headers=auth_headers, json={}))
        assert data['submission_id'] == 5 and data['sentence_start'] == 1 and data['sentence_end'] == 2
        assert seen == {'primed': [11], 'wrong': [12], 'l1': 2} and data['primed'] == [11]


class TestSubmitVerification:

    def _wire(self, monkeypatch, session, verifiable=True):
        consumed = []
        monkeypatch.setattr(prestudy, 'find_prestudy_for_attempt', lambda db, u, t: (session, verifiable))
        monkeypatch.setattr(prestudy, 'consume_session', lambda db, sid, aid: consumed.append((sid, aid)))
        sent = {}

        def _rpc(client, *a, **kw):
            sent.update(kw)
            return {'success': True, 'attempt_id': 'att-1', 'score': 1, 'total_questions': 2}
        monkeypatch.setattr(test_routes, '_call_submission_rpc', _rpc)
        monkeypatch.setattr(test_routes, '_apply_timing_and_progress', lambda *a, **k: None)
        monkeypatch.setattr(test_routes, '_update_vocabulary_tracking', lambda *a, **k: None)
        monkeypatch.setattr(test_routes, '_attach_explanations', lambda *a, **k: None)
        return consumed, sent

    def _post(self, client, auth_headers, app, prestudied):
        app.mock_supabase.table.return_value.execute.return_value = MagicMock(data={'id': T1, 'language_id': 3})
        return client.post('/api/tests/cats/submit', headers=auth_headers, json={
            'test_mode': 'reading', 'prestudied': prestudied,
            'responses': [{'question_id': 'q1', 'selected_answer': 'a'}]})

    def test_server_session_wins_over_a_missing_client_flag(self, client, auth_headers, app, monkeypatch):
        consumed, sent = self._wire(monkeypatch, 'ps1')
        resp = self._post(client, auth_headers, app, False)
        assert resp.status_code == 200
        assert sent['prestudied'] is True and consumed == [('ps1', 'att-1')]
        assert resp_json(resp)['result']['prestudied'] is True

    def test_client_flag_without_a_session_is_ignored(self, client, auth_headers, app, monkeypatch):
        consumed, sent = self._wire(monkeypatch, None)
        self._post(client, auth_headers, app, True)
        assert sent['prestudied'] is False and consumed == []

    def test_client_flag_counts_until_the_table_exists(self, client, auth_headers, app, monkeypatch):
        consumed, sent = self._wire(monkeypatch, None, verifiable=False)
        self._post(client, auth_headers, app, True)
        assert sent['prestudied'] is True and consumed == []


# ---------------------------------------------------------------------------
# Next-day review in the Maintenance pool
# ---------------------------------------------------------------------------

class TestFollowupInjection:

    def test_injects_one_exercise_per_due_sense_and_marks_served(self, monkeypatch):
        from services.practice_session_service import PracticeSessionService
        db = _DB({
            'prestudy_followups': [{'sense_id': 5, 'user_id': 'u', 'language_id': 3},
                                   {'sense_id': 6, 'user_id': 'u', 'language_id': 3},
                                   {'sense_id': 7, 'user_id': 'u', 'language_id': 3}],
            'exercises': [{'id': 'e5a', 'word_sense_id': 5, 'exercise_type': 'cloze_completion', 'content': {},
                           'ladder_level': 1, 'is_active': True},
                          {'id': 'e5b', 'word_sense_id': 5, 'exercise_type': 'definition_match', 'content': {},
                           'ladder_level': 2, 'is_active': True}],
        })
        monkeypatch.setattr('services.day_boundary.plan_today_iso', lambda db, u, l: '2026-11-01')
        svc = PracticeSessionService(db)
        payload = {'items': [{'exercise_id': 'x', 'sense_id': 6}]}
        n = svc._inject_prestudy_followups(payload, 'u', 3)
        assert n == 1
        added = [i for i in payload['items'] if i.get('prestudy_followup')]
        assert [(i['exercise_id'], i['mode']) for i in added] == [('e5a', 'maintenance')]
        served = [p for t, op, p in db.writes if t == 'prestudy_followups']
        assert served and 'served_at' in served[0]

    def test_no_table_means_no_change(self, monkeypatch):
        from services.practice_session_service import PracticeSessionService
        db = _DB(fail={'prestudy_followups': 'relation "public.prestudy_followups" does not exist'})
        monkeypatch.setattr('services.day_boundary.plan_today_iso', lambda db, u, l: '2026-11-01')
        payload = {'items': []}
        assert PracticeSessionService(db)._inject_prestudy_followups(payload, 'u', 3) == 0
        assert payload == {'items': []}


# ---------------------------------------------------------------------------
# Study plan setting
# ---------------------------------------------------------------------------

class TestStudyPlanSetting:

    def test_rejects_unknown_modes(self, client, auth_headers):
        resp = client.put('/api/study-plan', headers=auth_headers,
                          json={'language_id': 1, 'prestudy_mode': 'sometimes'})
        assert resp.status_code == 400

    def test_complete_block_accepts_a_prestudy_block(self, monkeypatch):
        app = Flask(__name__)
        row = {'id': 7, 'daily_session_targets': {}, 'completed_blocks': [],
               'test_ids': [{'test_id': T1, 'slot_type': 'new'}]}
        updates = []

        class _LoadsDB:
            def table(self, name):
                q = MagicMock()
                q.select.return_value = q
                q.eq.return_value = q
                q.limit.return_value = q
                q.execute.return_value = SimpleNamespace(data=[row])
                q.update.side_effect = lambda payload: updates.append(payload) or q
                return q
        monkeypatch.setattr(ss, 'get_supabase_admin', lambda: _LoadsDB())
        monkeypatch.setattr(ss, '_today_iso', lambda *a: '2026-10-31')
        with app.test_request_context('/api/study-session/complete-block', method='POST',
                                      json={'language_id': 1, 'block_id': prestudy_block_id(T1)}):
            g.current_user_id = 'u'
            resp = ss.complete_block.__wrapped__()
        status = resp[1] if isinstance(resp, tuple) else resp.status_code
        assert status == 200 and updates == [{'completed_blocks': [prestudy_block_id(T1)]}]
