"""GET /api/dual-translation/next — the read bundle (TASK-990), re-serve
(TASK-989), start any time (untaken tests), open-submission reuse and retired
windows (TASK-991), and the recording of repeats at submit.

``_rpc_payload`` is a Python mirror of ``migrations/dt_next_inputs.sql`` over
the filtering fake DB of tests/test_dual_translation_next_selection.py, so the
selection is checked to be the same through the bundle and through the
per-table reads. (The SQL itself is checked against the live schema by
tests/sql/test_dt_next_inputs.sql.)
"""

import hashlib
import json

import pytest

import routes.dual_translation as dt_routes
from services.dimension_service import DimensionService
from tests.test_dual_translation_next_selection import (
    EN, JA, JA_TEST, UNTAKEN_JA_TEST, USER, ZH, _TableDB, _Query, _Result, _grade, _serve, _tables,
)

USABLE = ('pass', 'rewritten')


# ---------------------------------------------------------------------------
# Python mirror of dt_next_inputs
# ---------------------------------------------------------------------------

def _rpc_payload(t, user_id, l2, l1):
    attempts = [a for a in t.get('test_attempts', []) if a['user_id'] == user_id]
    if l2 is None:
        latest = sorted(attempts, key=lambda a: (a['created_at'], a['id']), reverse=True)
        l2 = latest[0]['language_id'] if latest else None
    if l1 is None:
        u = next((u for u in t.get('users', []) if u['id'] == user_id), None)
        l1 = (u or {}).get('native_language_id') or 2
    attempted = sorted({str(a['test_id']) for a in attempts})
    grades = {g['submission_id']: g for g in t.get('dt_grade', [])}
    passages = {p['id']: p for p in t.get('dt_passage', [])}
    hist = {}
    for s in [s for s in t.get('dt_submission', []) if s['user_id'] == user_id]:
        h = hist.setdefault(s['passage_id'], {'ls': '', 'g': False, 'lg': None, 'b': None, 'o': None})
        h['ls'] = max(h['ls'], s.get('created_at') or '')
        g = grades.get(s['id'])
        if g:
            h['g'] = True
            at = g.get('created_at') or ''
            if h['lg'] is None or at >= h['lg']:
                h['lg'], h['b'] = at, g.get('overall_band')
        elif not s.get('reproduction') and s.get('l1_language_id') == l1:
            h['o'] = max(h['o'] or 0, s['id'])
    history = []
    for pid, h in hist.items():
        p = passages.get(pid)
        if p:
            history.append({'p': pid, **h, 'l2': p['l2_language_id'], 'st': p['status'],
                            't': p['source_ref_id'], 's': p.get('sentence_start'),
                            'e': p.get('sentence_end'), 'a': p['age_tier']})
    refs = [r for r in t.get('test_sentence_references', [])
            if r['l1_language_id'] == l1 and r['is_active'] and r['review_verdict'] in USABLE]
    ref_by_sentence = {r['sentence_id']: r for r in refs}
    sentences = t.get('test_sentences', [])
    cand = [x for x in t.get('tests', []) if x['is_active'] and x['language_id'] == l2 and any(
        s['test_id'] == x['id'] and s['id'] in ref_by_sentence for s in sentences)]
    tests = []
    for c in cand:
        rows = []
        for s in sorted((s for s in sentences if s['test_id'] == c['id']), key=lambda s: s['idx']):
            r = ref_by_sentence.get(s['id'])
            fresh = not c.get('transcript_hash') or s.get('transcript_hash') == c['transcript_hash']
            rows.append([s['id'], s['idx'], fresh, r is not None,
                         round(r['tightness'], 3) if r and r.get('tightness') is not None else None,
                         len(s['l2_text'])])
        tests.append({'id': c['id'], 'h': c.get('transcript_hash'), 'd': c.get('difficulty'),
                      'at': c['id'] in attempted, 'elo': c.get('_elo'), 'rows': rows})
    legacy_refs = {(r['passage_id'], r['l1_language_id']): r for r in t.get('dt_passage_reference', [])}
    legacy = [{'id': p['id'], 't': p['source_ref_id'], 'a': p['age_tier'],
               'x': legacy_refs[(p['id'], l1)]['l1_text']}
              for p in t.get('dt_passage', [])
              if p['source_kind'] == 'test_transcript' and p['status'] == 'active'
              and p['l2_language_id'] == l2 and p.get('sentence_start') is None
              and (p['id'], l1) in legacy_refs]
    ranges = [{'id': p['id'], 't': p['source_ref_id'], 's': p['sentence_start'], 'e': p['sentence_end'],
               'st': p['status'], 'a': p['age_tier']}
              for p in t.get('dt_passage', [])
              if p.get('sentence_start') is not None and p['source_ref_id'] in {c['id'] for c in cand}]
    # prefetch: first 3 tests with 2+ usable unserved sentences in the default order
    salt = len(hist)
    served = {}
    for h in history:
        if h['s'] is not None:
            served.setdefault(h['t'], set()).update(range(h['s'], h['e'] + 1))

    def rot(tid):
        return hashlib.sha256(f"{user_id}|{tid}|{salt}".encode()).hexdigest()
    ranked = [x for x in tests if sum(1 for r in x['rows'] if r[2] and r[3]
                                      and r[1] not in served.get(x['id'], set())) >= 2]
    ranked.sort(key=lambda x: (not x['at'], (x['elo'] is None, x['elo'] or 0) if not x['at'] else (0, 0),
                               rot(x['id'])))
    prefetch = {x['id'] for x in ranked[:3]}
    texts = [[s['id'], s['l2_text'], ref_by_sentence[s['id']]['l1_text']]
             for s in sentences if s['test_id'] in prefetch and s['id'] in ref_by_sentence]
    return {'l1': l1, 'l2': l2, 'salt': salt, 'attempted': attempted, 'history': history,
            'legacy': legacy, 'tests': tests, 'ranges': ranges, 'texts': texts}


class _RpcCall:
    def __init__(self, db, name, params):
        self.db, self.name, self.params = db, name, params

    def execute(self):
        self.db.reads.append(f'rpc:{self.name}')
        if self.db.rpc_broken:
            raise RuntimeError('PGRST202 Could not find the function public.dt_next_inputs')
        p = self.params
        return _Result(json.loads(json.dumps(_rpc_payload(self.db.tables, p['p_user_id'], p['p_l2'], p['p_l1']))))


class _EmbedQuery(_Query):
    """test_sentence_references with test_sentences(l2_text) embedded."""

    def select(self, *a, **k):
        self.columns = a[0] if a else ''
        return self

    def execute(self):
        result = super().execute()
        if self.op == 'select' and 'test_sentences(' in getattr(self, 'columns', ''):
            by_id = {s['id']: s for s in self.db.tables.get('test_sentences', [])}
            for row in result.data:
                row['test_sentences'] = {'l2_text': by_id.get(row['sentence_id'], {}).get('l2_text')}
        return result


class _RpcDB(_TableDB):
    def __init__(self, tables, rpc_broken=False):
        super().__init__(tables)
        self.rpc_broken = rpc_broken

    def rpc(self, name, params):
        return _RpcCall(self, name, params)

    def table(self, name):
        return _EmbedQuery(self, name)

    def round_trips(self):
        return len(self.reads) + len(self.inserts)


@pytest.fixture(autouse=True)
def _fresh_bundle_state(monkeypatch):
    monkeypatch.setitem(dt_routes._next_inputs_state, 'unavailable_until', 0.0)
    monkeypatch.setitem(dt_routes._next_inputs_state, 'logged', False)


def _choose_via(db, l2, **kw):
    inputs = dt_routes._next_inputs(db, USER, l2)
    return dt_routes._choose_next(db, USER, inputs.l1, inputs.l2, None, inputs=inputs, **kw), inputs


# ---------------------------------------------------------------------------
# Same selection through the bundle and through the per-table reads
# ---------------------------------------------------------------------------

def _walk(db_cls, l2, tables, **kw):
    db = db_cls(tables)
    seen = []
    for _ in range(12):
        choice, inputs = _choose_via(db, l2, **kw)
        seen.append(choice)
        if choice['kind'] == 'none':
            break
        _grade(db, _serve(db, choice))
    return seen, db


@pytest.mark.parametrize('l2', [ZH, JA])
@pytest.mark.parametrize('variant', ['default', 'no_attempts', 'retired_window', 'stale_row'])
def test_bundle_and_table_reads_choose_the_same(l2, variant):
    tables = _tables()
    if variant == 'no_attempts':
        tables['test_attempts'] = []
    if variant == 'retired_window':
        tables['dt_passage'].append({'id': 77, 'l2_language_id': JA, 'source_kind': 'test_transcript',
                                     'source_ref_id': JA_TEST, 'l2_text': 'x', 'age_tier': 3,
                                     'status': 'retired', 'sentence_start': 0, 'sentence_end': 1})
    if variant == 'stale_row':
        for r in tables['test_sentences']:
            if r['id'] == 502:
                r['transcript_hash'] = 'old'
    via_rpc, rpc_db = _walk(_RpcDB, l2, json.loads(json.dumps(tables)))
    via_tables, _ = _walk(lambda t: _RpcDB(t, rpc_broken=True), l2, json.loads(json.dumps(tables)))
    assert via_rpc == via_tables
    assert via_rpc[-1]['kind'] == 'none'
    assert any(r.startswith('rpc:') for r in rpc_db.reads)


def test_untaken_order_follows_the_learner_level():
    """Two untaken tests: the one whose ELO is nearer the learner's comes first."""
    tables = _tables(test_attempts=[])
    near = 'dddddddd-0000-0000-0000-000000000004'
    tables['tests'].append({'id': near, 'language_id': JA, 'difficulty': 4, 'transcript_hash': 'hn',
                            'is_active': True, '_elo': 10})
    for t in tables['tests']:
        if t['id'] in (JA_TEST, UNTAKEN_JA_TEST):
            t['_elo'] = 300
    tables['test_sentences'] += [
        {'id': 800 + i, 'test_id': near, 'idx': i, 'l2_text': s, 'token_start': None, 'token_end': None,
         'transcript_hash': 'hn'} for i, s in enumerate(['近い。', 'テストです。'])]
    tables['test_sentence_references'] += [
        {'sentence_id': 800 + i, 'l1_language_id': EN, 'l1_text': s, 'tightness': 0.9,
         'review_verdict': 'pass', 'is_active': True} for i, s in enumerate(['Near.', 'A test.'])]
    choice, _ = _choose_via(_RpcDB(tables), JA)
    assert choice == {'kind': 'range', 'test_id': near, 'start': 0, 'end': 1, 'untaken': True}


# ---------------------------------------------------------------------------
# Route: round trips, open submission reuse, re-serve, scope, retired
# ---------------------------------------------------------------------------

@pytest.fixture
def rpc_app(app, monkeypatch):
    db = _RpcDB(_tables())
    app.supabase_service = db
    monkeypatch.setattr(dt_routes, '_should_serve_error_card', lambda: False)
    monkeypatch.setattr(DimensionService, 'get_language_code',
                        classmethod(lambda cls, lid: {1: 'zh', 2: 'en', 3: 'ja'}.get(lid)))
    monkeypatch.setattr(dt_routes, 'get_active_rubric', lambda db: {'band_descriptors': {}})
    return db


def _next(client, headers, query):
    resp = client.get(f'/api/dual-translation/next?{query}', headers=headers)
    return resp.status_code, json.loads(resp.data)


class TestRoundTrips:

    def test_new_window_is_three_round_trips(self, client, auth_headers, rpc_app):
        rpc_app.reads.clear()
        status, data = _next(client, auth_headers, 'language_id=3')
        assert status == 200 and data['source'] == 'sentence_refs'
        assert data['l1_text'] == 'It is sunny today. I went to the park.'
        # one bundle read, one dt_passage insert, one dt_submission insert
        assert rpc_app.reads == ['rpc:dt_next_inputs']
        assert [name for name, _ in rpc_app.inserts] == ['dt_passage', 'dt_submission']
        assert rpc_app.round_trips() == 3

    def test_legacy_passage_is_two_round_trips(self, client, auth_headers, rpc_app):
        status, data = _next(client, auth_headers, 'language_id=1')
        assert status == 200 and data['source'] == 'passage' and data['passage_id'] in (1, 2)
        assert rpc_app.round_trips() == 2

    def test_reopening_an_unstarted_passage_reuses_its_submission(self, client, auth_headers, rpc_app):
        """TASK-991: Try another / reload without submitting creates no new empty rows."""
        _, first = _next(client, auth_headers, 'language_id=1')
        _, second = _next(client, auth_headers, 'language_id=1')
        _, third = _next(client, auth_headers, 'language_id=1')
        subs = rpc_app.tables['dt_submission']
        assert len(subs) == 2  # one per distinct passage, not one per call
        assert third['submission_id'] == first['submission_id']
        assert second['submission_id'] != first['submission_id']
        assert rpc_app.round_trips() == 2 + 2 + 1  # the reuse needs only the bundle read

    def test_missing_function_falls_back_to_the_table_reads(self, client, auth_headers, rpc_app, caplog):
        rpc_app.rpc_broken = True
        with caplog.at_level('WARNING', logger='routes.dual_translation'):
            s1, d1 = _next(client, auth_headers, 'language_id=3')
            s2, _ = _next(client, auth_headers, 'language_id=3')
        assert (s1, s2) == (200, 200) and d1['source'] == 'sentence_refs'
        assert sum('dt_next_inputs unavailable' in r.getMessage() for r in caplog.records) == 1
        assert rpc_app.reads.count('rpc:dt_next_inputs') == 1  # not retried on every call


class TestReserve:

    def _finish_chinese(self, client, headers, db):
        served = []
        while True:
            status, data = _next(client, headers, 'language_id=1')
            if status == 404:
                return data, served
            sub = next(s for s in db.tables['dt_submission'] if s['id'] == data['submission_id'])
            served.append(sub['passage_id'])
            _grade(db, sub)

    def test_all_done_then_reserve_serves_the_least_recently_graded(self, client, auth_headers, rpc_app):
        data, served = self._finish_chinese(client, auth_headers, rpc_app)
        assert data['error_code'] == dt_routes.ALL_DONE and sorted(served) == [1, 2]
        status, again = _next(client, auth_headers, 'language_id=1&reserve=1')
        assert status == 200
        sub = next(s for s in rpc_app.tables['dt_submission'] if s['id'] == again['submission_id'])
        assert sub['passage_id'] == served[0]  # graded first -> least recently graded
        assert again['repeat_of']['band'] == 3
        # without reserve it is still all done
        assert _next(client, auth_headers, 'language_id=1')[1]['error_code'] == dt_routes.ALL_DONE

    def test_reserve_does_not_preempt_fresh_content(self, client, auth_headers, rpc_app):
        status, data = _next(client, auth_headers, 'language_id=1&reserve=1')
        assert status == 200 and 'repeat_of' not in data


class TestScopeAndUntaken:

    def test_untaken_test_is_flagged_in_the_answer(self, client, auth_headers, rpc_app):
        rpc_app.tables['test_attempts'] = []
        status, data = _next(client, auth_headers, 'language_id=3')
        assert status == 200 and data['from_untaken_test'] is True

    def test_test_id_limits_the_choice_to_that_test(self, client, auth_headers, rpc_app):
        status, data = _next(client, auth_headers, f'language_id=3&test_id={UNTAKEN_JA_TEST}')
        assert status == 200 and data['from_untaken_test'] is True
        passage = next(p for p in rpc_app.tables['dt_passage'] if p['id'] == data['passage_id'])
        assert passage['source_ref_id'] == UNTAKEN_JA_TEST

    @pytest.mark.parametrize('broken', [False, True])
    def test_scope_is_applied_before_the_per_call_cap(self, client, auth_headers, rpc_app, monkeypatch, broken):
        """A test outside the first max_tests candidates is still served when asked
        for by id (found on the real app: the cap dropped it -> NO_PASSAGES)."""
        monkeypatch.setattr(dt_routes._TableInputs, 'max_tests', 1)
        rpc_app.rpc_broken = broken
        rpc_app.tables['test_attempts'] = []
        status, data = _next(client, auth_headers, f'language_id=3&test_id={JA_TEST}')
        assert status == 200
        passage = next(p for p in rpc_app.tables['dt_passage'] if p['id'] == data['passage_id'])
        assert passage['source_ref_id'] == JA_TEST

    def test_test_id_must_be_a_uuid(self, client, auth_headers, rpc_app):
        assert _next(client, auth_headers, 'language_id=3&test_id=../x')[0] == 400

    def test_no_language_and_no_attempts_is_no_passages(self, client, auth_headers, rpc_app):
        rpc_app.tables['test_attempts'] = []
        status, data = _next(client, auth_headers, '')
        assert status == 404 and data['error_code'] == dt_routes.NO_PASSAGES


class TestRetiredWindows:

    def _retire(self, db, start, end):
        db.tables['dt_passage'].append({
            'id': 90, 'l2_language_id': JA, 'source_kind': 'test_transcript', 'source_ref_id': JA_TEST,
            'l2_text': '...', 'age_tier': 3, 'status': 'retired', 'sentence_start': start, 'sentence_end': end})

    def test_next_never_opens_a_retired_window(self, client, auth_headers, rpc_app):
        self._retire(rpc_app, 0, 1)
        status, data = _next(client, auth_headers, 'language_id=3')
        assert status == 200
        passage = next(p for p in rpc_app.tables['dt_passage'] if p['id'] == data['passage_id'])
        assert passage['status'] == 'active' and passage['sentence_start'] >= 2

    def test_passage_from_sentences_refuses_a_retired_range(self, client, auth_headers, rpc_app):
        self._retire(rpc_app, 0, 1)
        resp = client.post('/api/dual-translation/passage-from-sentences', headers=auth_headers, json={
            'test_id': JA_TEST, 'sentence_start': 0, 'sentence_end': 1, 'l1_language_id': EN})
        assert resp.status_code == 409
        assert json.loads(resp.data)['error_code'] == 'PASSAGE_RETIRED'
        assert rpc_app.tables['dt_submission'] == []


class TestTestAvailable:

    def test_available_for_a_test_with_a_window(self, client, auth_headers, rpc_app):
        resp = client.get(f'/api/dual-translation/test-available?test_id={UNTAKEN_JA_TEST}', headers=auth_headers)
        assert resp.status_code == 200
        assert json.loads(resp.data)['available'] is True

    def test_not_available_without_references(self, client, auth_headers, rpc_app):
        rpc_app.tables['test_sentence_references'] = []
        resp = client.get(f'/api/dual-translation/test-available?test_id={JA_TEST}', headers=auth_headers)
        assert json.loads(resp.data)['available'] is False

    def test_unknown_test_is_404(self, client, auth_headers, rpc_app):
        resp = client.get('/api/dual-translation/test-available?test_id=eeeeeeee-0000-0000-0000-000000000009',
                          headers=auth_headers)
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Submit: a repeat is graded but kept out of the aggregates
# ---------------------------------------------------------------------------

_CONTRACT = {
    'scores': {'accuracy': 3}, 'overall_band': 3, 'diff': [],
    'errors': [{'span_reproduction': [0, 1], 'span_reference': [0, 1], 'category': 'lexical',
                'subtype': 'word_choice', 'source': 'intralingual', 'severity': 'minor',
                'learner_form': '今', 'corrected_form': '今', 'explanation': 'why', 'confidence': 0.9,
                'is_mistake': False}],
    'grader_trace': {'tier': 'single_call', 'tokens': {'in': 1, 'out': 1}},
}


@pytest.fixture
def graded_app(rpc_app, monkeypatch):
    calls = {'repair': 0, 'bkt': 0}
    monkeypatch.setattr(dt_routes, 'grade_submission', lambda db, **kw: json.loads(json.dumps(_CONTRACT)))
    monkeypatch.setattr(dt_routes, '_tokens_used_today', lambda db, uid: 0)
    monkeypatch.setattr(dt_routes, 'credit_study_time', lambda *a, **k: None)

    def _repair(db, contract, **kw):
        calls['repair'] += 1
        return contract
    monkeypatch.setattr(dt_routes.repair_hooks, 'after_grade', _repair)
    monkeypatch.setattr(dt_routes, '_record_target_word_evidence',
                        lambda *a, **k: calls.__setitem__('bkt', calls['bkt'] + 1))
    rpc_app.calls = calls
    return rpc_app


def _submit(client, headers, sub_id, text='今日は晴れです。'):
    resp = client.post(f'/api/dual-translation/{sub_id}/submit', headers=headers, json={'reproduction': text})
    return resp.status_code, json.loads(resp.data)


class TestRepeatSubmission:

    def test_first_grade_is_aggregated_the_repeat_is_not(self, client, auth_headers, graded_app):
        db = graded_app
        _, first = _next(client, auth_headers, 'language_id=3')
        status, graded = _submit(client, auth_headers, first['submission_id'])
        assert status == 200 and 'repeat_of' not in graded
        assert len(db.tables['dt_error_instance']) == 1 and db.calls['repair'] == 1

        # Serve the same window again (as reserve would) and grade it.
        repeat = db.table('dt_submission').insert({
            'user_id': USER, 'passage_id': first['passage_id'], 'l1_language_id': EN, 'reproduction': '',
        }).execute().data[0]
        status, again = _submit(client, auth_headers, repeat['id'])

        assert status == 200
        assert again['repeat_of']['of_submission_id'] == first['submission_id']
        assert again['repeat_of']['band'] is None or isinstance(again['repeat_of']['band'], int)
        assert len(db.tables['dt_error_instance']) == 1  # no rows for the repeat
        assert db.calls['repair'] == 1                   # no guided-repair session
        grade = next(g for g in db.tables['dt_grade'] if g['submission_id'] == repeat['id'])
        assert grade['grader_trace']['repeat']['of_submission_id'] == first['submission_id']
        assert [e['subtype'] for e in grade['grader_trace']['repeat']['errors']] == ['word_choice']

        # The cached grade still shows the repeat's errors and marks it.
        _, cached = _submit(client, auth_headers, repeat['id'])
        assert cached['repeat_of']['of_submission_id'] == first['submission_id']
        assert [e['subtype'] for e in cached['errors']] == ['word_choice']
        assert 'repeat' not in cached['grader_trace']

    def test_reproduction_is_cleaned_and_capped(self, client, auth_headers, graded_app):
        _, first = _next(client, auth_headers, 'language_id=3')
        status, body = _submit(client, auth_headers, first['submission_id'], 'x' * 2001)
        assert status == 400 and body['error_code'] == 'REPRODUCTION_TOO_LONG'
        status, _ = _submit(client, auth_headers, first['submission_id'], '​\x00 ﻿')
        assert status == 400
        status, _ = _submit(client, auth_headers, first['submission_id'], '今日は\x00晴れです。')
        sub = next(s for s in graded_app.tables['dt_submission'] if s['id'] == first['submission_id'])
        assert status == 200 and sub['reproduction'] == '今日は晴れです。'

    def test_malformed_grade_is_not_stored(self, client, auth_headers, graded_app, monkeypatch):
        bad = json.loads(json.dumps(_CONTRACT))
        bad['overall_band'] = 6
        monkeypatch.setattr(dt_routes, 'grade_submission', lambda db, **kw: bad)
        _, first = _next(client, auth_headers, 'language_id=3')
        status, body = _submit(client, auth_headers, first['submission_id'])
        assert status == 200 and body['provisional'] is True
        assert graded_app.tables.get('dt_grade', []) == []
