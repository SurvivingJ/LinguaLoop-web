"""TASK-1021 (ADR-049 open question 1): prestudy loads exercise content only for
the words it will drill, plus an on-demand endpoint for words added later.

Covers the server drill rule (shared fixture with the page's JS twin), the
payload (content for drill senses only, ``has_exercises`` for every linked
sense with exercises), the ``GET /api/tests/<id>/prestudy/exercises`` endpoint,
the exercise-content store calls (the select string, one ``hydrate`` with the
test's language) and that a hydration miss or an unloaded sense never queues
generation. ``_tables()`` puts every exercise's content in its sense's file in
the conftest's ``InMemoryBackend`` (the rows carry no content, as live);
``store.hydrate`` is monkeypatched where the call shape is asserted. No network,
no Supabase.
"""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path
from types import SimpleNamespace

import pytest

import routes.tests.prestudy as test_routes
from services import prestudy
from services.exercise_content import store

ROOT = Path(__file__).resolve().parent.parent
DRILL_FIXTURE = json.loads((ROOT / 'tests/unit/fixtures/prestudy-drill-rule.json').read_text(encoding='utf-8'))
PRESTUDY_JS = (ROOT / 'static/js/prestudy/prestudy.js').read_text(encoding='utf-8')

LANG = 3
SELECT_STORAGE = 'id, word_sense_id, exercise_type, content_version, ladder_level'


def resp_json(resp):
    return json.loads(resp.data)


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------

class _Query:
    """PostgREST builder stand-in: applies eq / in_ filters, order and range
    (so fetch_all pages), projects ``exercises`` rows onto the selected columns
    and records every executed query."""

    def __init__(self, db, table):
        self.db, self.table = db, table
        self.columns, self.filters, self._order, self._range = None, [], None, None

    def select(self, columns, **_kw):
        self.columns = columns
        return self

    def eq(self, col, val):
        self.filters.append(('eq', col, val))
        return self

    def in_(self, col, vals):
        self.filters.append(('in', col, tuple(vals)))
        return self

    def order(self, col, **_kw):
        self._order = col
        return self

    def range(self, start, end):
        self._range = (start, end)
        return self

    def limit(self, _n):
        return self

    def _match(self, row):
        for op, col, val in self.filters:
            if op == 'eq' and row.get(col) != val:
                return False
            if op == 'in' and row.get(col) not in val:
                return False
        return True

    def execute(self):
        self.db.queries.append({'table': self.table, 'columns': self.columns,
                                'filters': list(self.filters)})
        rows = [copy.deepcopy(r) for r in self.db.tables.get(self.table, []) if self._match(r)]
        if self.table == 'exercises' and self.columns:
            wanted = [c.strip() for c in self.columns.split(',')]
            rows = [{c: r[c] for c in wanted if c in r} for r in rows]
        if self._order:
            rows.sort(key=lambda r: str(r.get(self._order)))
        if self._range:
            rows = rows[self._range[0]:self._range[1] + 1]
        return SimpleNamespace(data=rows)


class FakeDB:
    def __init__(self, tables):
        self.tables = tables
        self.queries: list[dict] = []

    def table(self, name):
        return _Query(self, name)

    def content_queries(self):
        """Executed exercises selects that read content (or its version)."""
        return [q for q in self.queries if q['table'] == 'exercises'
                and ('content' in (q['columns'] or ''))]

    @staticmethod
    def filter_value(query, col):
        return next((v for op, c, v in query['filters'] if op == 'in' and c == col), None)


class FakeHydrate:
    """``store.hydrate`` stand-in following ADR-049 section 9: fills content from
    ``contents[item[id_key]]``; ``missing`` ids are dropped (or None)."""

    def __init__(self, contents, missing=()):
        self.contents, self.missing, self.calls = contents, set(missing), []

    def __call__(self, items, *, language_id=None, id_key='id', sense_key='word_sense_id',
                 db=None, drop_missing=True, max_senses=None, deadline_s=None):
        self.calls.append({'ids': [i.get(id_key) for i in items], 'senses': [i.get(sense_key) for i in items],
                           'language_id': language_id, 'db': db, 'drop_missing': drop_missing})
        report = store.HydrationReport(mode='storage')
        keep = []
        for item in items:
            if not (isinstance(item, dict) and item.get(id_key)):
                keep.append(item)
                continue
            report.items += 1
            if item.get('content') is not None:
                keep.append(item)
                continue
            if item[id_key] in self.missing or item[id_key] not in self.contents:
                report.missing_ids.append(item[id_key])
                if drop_missing:
                    report.dropped += 1
                    continue
                item['content'] = None
            else:
                item['content'] = copy.deepcopy(self.contents[item[id_key]])
            keep.append(item)
        items[:] = keep
        return report


def _cloze(word):
    return {'sentence_with_blank': f'__{word}', 'options': [word, 'x'], 'correct_answer': word,
            'explanation': 'e', 'original_sentence': f'{word}!', 'internal_notes': 'secret'}


def _defmatch(word):
    return {'word': word, 'options': ['a', 'b'], 'correct_definition': 'a', 'pronunciation': 'p'}


CONTENT = {
    'e11a': _cloze('猫'), 'e11b': _defmatch('猫'), 'e12a': _cloze('犬'),
    'e14a': {'audio': 'x'}, 'e15a': _cloze('鳥'), 'e16a': _defmatch('魚'),
}

EXERCISE_ROWS = [
    {'id': 'e11a', 'word_sense_id': 11, 'exercise_type': 'cloze_completion', 'ladder_level': 3},
    {'id': 'e11b', 'word_sense_id': 11, 'exercise_type': 'definition_match', 'ladder_level': 1},
    {'id': 'e12a', 'word_sense_id': 12, 'exercise_type': 'cloze_completion', 'ladder_level': 3},
    {'id': 'e14a', 'word_sense_id': 14, 'exercise_type': 'listening_flash', 'ladder_level': 1},
    {'id': 'e15a', 'word_sense_id': 15, 'exercise_type': 'cloze_completion', 'ladder_level': 3},
    {'id': 'e16a', 'word_sense_id': 16, 'exercise_type': 'definition_match', 'ladder_level': 1},
    {'id': 'e11x', 'word_sense_id': 11, 'exercise_type': 'cloze_completion', 'ladder_level': 3,
     'is_active': False},
]

# 11: unknown, has exercises            -> drilled, content loaded
# 12: known (p 0.9), has exercises      -> not drilled: has_exercises only
# 13: no row, no frequency (prior 0.3)  -> drilled, no exercises
# 14: p 0.5, only a type the prime cannot render -> drilled, not in has_exercises
# 15: question-only sense, unknown      -> neither (not linked)
# 16: linked, common word (prior 0.99)  -> not drilled: has_exercises only
TEST_ROW = {
    'id': 't1', 'slug': 'cats', 'title': '猫', 'language_id': LANG, 'transcript': '猫が犬といる。',
    'audio_url': None, 'difficulty': 3, 'target_age_tier': 2,
    'vocab_sense_ids': [11, 12, 13, 14, 16],
    'vocab_token_map': [['猫', 11], ['が', None], ['犬', 12], ['と', None], ['いる', 13], ['。', None]],
    'furigana_payload': None, 'pinyin_payload': None,
}


def _sense(sid, lemma, freq):
    return {'id': sid, 'vocab_id': sid, 'sense_rank': 1, 'definition': f'def {lemma}',
            'definition_language_id': 2, 'example_sentence': None, 'pronunciation': None,
            'dim_vocabulary': {'lemma': lemma, 'part_of_speech': 'noun', 'frequency_rank': freq,
                               'reading': lemma}}


def _content_of(exercise_id):
    return copy.deepcopy(CONTENT.get(exercise_id, {'k': exercise_id}))


def _tables(rows=None):
    """The fixture tables; each exercise's content goes into its sense's v0 file."""
    exercises, files = [], {}
    for r in (EXERCISE_ROWS if rows is None else rows):
        row = {'is_active': True, 'language_id': LANG, 'content_version': 0, **r}
        exercises.append(row)
        files.setdefault(row['word_sense_id'], {})[row['id']] = _content_of(row['id'])
    for sense, contents in files.items():
        store.backend().seed(store.content_path(LANG, sense, 0),
                             store.encode_sense_file(sense, LANG, 0, contents))
    return {
        'questions': [{'test_id': 't1', 'sense_ids': [11, 15], 'question_text': 'LEAK?'}],
        'dim_word_senses': [_sense(11, '猫', 4.0), _sense(12, '犬', 3.0), _sense(13, 'いる', None),
                            _sense(14, 'と', 3.0), _sense(15, '鳥', 2.0), _sense(16, '魚', 9.0)],
        'user_vocabulary_knowledge': [
            {'user_id': 'u1', 'sense_id': 11, 'p_known': 0.1, 'status': 'unknown', 'evidence_count': 2},
            {'user_id': 'u1', 'sense_id': 12, 'p_known': 0.9, 'status': 'known', 'evidence_count': 8},
            {'user_id': 'u1', 'sense_id': 14, 'p_known': 0.5, 'status': 'learning', 'evidence_count': 3},
            {'user_id': 'u1', 'sense_id': 15, 'p_known': 0.1, 'status': 'unknown', 'evidence_count': 1},
        ],
        'user_calibration_state': [{'user_id': 'u1', 'language_id': LANG, 'ability_zipf': 5.0}],
        'exercises': exercises,
    }


# ---------------------------------------------------------------------------
# The drill rule (one function, the page's twin)
# ---------------------------------------------------------------------------

class TestDrillRule:

    @pytest.mark.parametrize('case', DRILL_FIXTURE['cases'], ids=[c['name'] for c in DRILL_FIXTURE['cases']])
    def test_shared_fixture(self, case):
        """The same cases tests/unit/prestudy-ondemand.test.js runs through the JS rule."""
        p = case['payload']
        ability = p['ability_zipf'] if p['ability_zipf'] is not None else prestudy.DEFAULT_ABILITY_ZIPF
        assert prestudy.drill_sense_ids(p['test']['vocab_sense_ids'], p['senses'], p['knowledge'],
                                        ability) == case['drill']

    def test_boundary_is_strictly_below_probably_known(self):
        senses = {'1': {'freq': None}, '2': {'freq': None}}
        assert prestudy.DRILL_MAX_P == 0.75
        assert prestudy.drill_sense_ids([1, 2], senses, {'1': {'p': 0.75}, '2': {'p': 0.7499999}}, 5.0) == [2]

    def test_prior_boundary_and_missing_frequency(self):
        # prior(4.576, 5.0) = 0.749998 < 0.75 <= prior(4.5761, 5.0) = 0.750026
        senses = {'1': {'freq': 4.576}, '2': {'freq': 4.5761}, '3': {'freq': None}, '4': {'freq': 0}}
        assert prestudy.drill_sense_ids([1, 2, 3, 4], senses, {}, 5.0) == [1, 3, 4]

    def test_the_learner_row_beats_the_prior(self):
        senses = {'1': {'freq': 9.0}, '2': {'freq': 1.0}}
        knowledge = {'1': {'p': 0.0}, '2': {'p': 0.99}}
        assert prestudy.drill_sense_ids([1, 2], senses, knowledge, 5.0) == [1]

    def test_only_linked_senses_with_a_senses_entry(self):
        senses = {'1': {'freq': 1.0}, '3': {'freq': 1.0}}
        knowledge = {'2': {'p': 0.1}, '3': {'p': 0.1}}
        assert prestudy.drill_sense_ids([1, 2, 'x', None, '1'], senses, knowledge, 5.0) == [1]

    def test_js_constants_and_cross_references_match(self):
        assert re.search(r'const DRILL_MAX_P = ([0-9.]+);', PRESTUDY_JS).group(1) == str(prestudy.DRILL_MAX_P)
        assert int(re.search(r'const MAX_FETCH_SENSES = (\d+);', PRESTUDY_JS).group(1)) \
            == prestudy.MAX_ON_DEMAND_SENSES == 20
        assert 'services/prestudy.py drill_sense_ids()' in PRESTUDY_JS
        assert 'drillSenseIds' in prestudy.drill_sense_ids.__doc__
        assert 'prestudy-drill-rule.json' in prestudy.drill_sense_ids.__doc__

    def test_plan_for_tests_uses_the_same_rule(self, monkeypatch):
        calls = []
        real = prestudy.drill_sense_ids
        monkeypatch.setattr(prestudy, 'drill_sense_ids', lambda *a: calls.append(a) or real(*a))
        bundle = {
            'tests': [{'id': 't1', 'vocab_sense_ids': [1, 2, 3, 4]}],
            'knowledge': [{'sense_id': 1, 'p_known': 0.9, 'status': 'known', 'evidence_count': 3},
                          {'sense_id': 2, 'p_known': 0.3, 'status': 'encountered', 'evidence_count': 3}],
            'freq': [{'id': 3, 'frequency_rank': 7.0}, {'id': 4, 'frequency_rank': 2.0}],
            'ability_zipf': 5.0, 'with_exercises': [2],
        }

        class _BundleDB:
            def rpc(self, name, params):
                return SimpleNamespace(execute=lambda: SimpleNamespace(data=bundle))

        from services import optional_rpc
        optional_rpc.reset()
        plans = prestudy.plan_for_tests(_BundleDB(), 'u1', LANG, [{'id': 't1', 'test_type': 'reading'}])
        assert len(calls) == 1 and real(*calls[0]) == [2, 4]
        # 2 drill words, 1 with exercises: (60 + 2*5*8 + 1*2*20 + 40) / 60 = 3.67 -> 4
        assert plans['t1']['minutes_est'] == 4


# ---------------------------------------------------------------------------
# The payload
# ---------------------------------------------------------------------------

class TestPayload:

    def test_content_only_for_drill_senses_and_has_exercises_for_all(self):
        db = FakeDB(_tables())
        out = prestudy.build_prestudy_payload(db, TEST_ROW, 'u1', 2)
        assert set(out['exercises']) == {'11'}
        assert {e['id'] for e in out['exercises']['11']} == {'e11a', 'e11b'}
        # 12 and 16 have exercises but are not drilled; 14 has only a type the prime cannot render
        assert out['has_exercises'] == [11, 12, 16]
        blob = json.dumps(out, ensure_ascii=False)
        assert '犬!' not in blob and 'internal_notes' not in blob and 'LEAK?' not in blob
        # one content read, for the drill senses that have exercises only
        (content_q,) = db.content_queries()
        assert content_q['columns'] == SELECT_STORAGE
        assert FakeDB.filter_value(content_q, 'word_sense_id') == (11,)
        assert FakeDB.filter_value(content_q, 'exercise_type') == tuple(prestudy.EXERCISE_FIELDS)
        # has_exercises reads row ids only, for every linked sense, renderable types only
        (ids_q,) = [q for q in db.queries if q['table'] == 'exercises' and q['columns'] == 'word_sense_id']
        assert FakeDB.filter_value(ids_q, 'word_sense_id') == (11, 12, 13, 14, 16)
        assert FakeDB.filter_value(ids_q, 'exercise_type') == tuple(prestudy.EXERCISE_FIELDS)

    def test_question_only_senses_still_get_words_and_knowledge(self):
        out = prestudy.build_prestudy_payload(FakeDB(_tables()), TEST_ROW, 'u1', 2)
        assert out['senses']['15']['lemma'] == '鳥'
        assert out['knowledge']['15']['p'] == 0.1
        assert '15' not in out['exercises'] and 15 not in out['has_exercises']
        assert set(out['senses']) == {'11', '12', '13', '14', '15', '16'}

    def test_real_store_hydrates_once_from_the_files(self, monkeypatch):
        calls = []
        real = store.hydrate
        monkeypatch.setattr(store, 'hydrate', lambda items, **kw: calls.append((list(items), kw)) or real(items, **kw))
        db = FakeDB(_tables())
        out = prestudy.build_prestudy_payload(db, TEST_ROW, 'u1', 2)
        assert [q['columns'] for q in db.content_queries()] == [SELECT_STORAGE]
        assert len(calls) == 1 and calls[0][1] == {'language_id': LANG, 'db': db}
        assert out['exercises']['11'][0]['c']   # content from the sense's file
        assert store.backend().calls_for('get') == ['ja/11.v0.json']

    def test_hydrates_once_with_the_language(self, monkeypatch):
        fake = FakeHydrate(CONTENT)
        monkeypatch.setattr(store, 'hydrate', fake)
        db = FakeDB(_tables())
        out = prestudy.build_prestudy_payload(db, TEST_ROW, 'u1', 2)
        (content_q,) = db.content_queries()
        assert content_q['columns'] == SELECT_STORAGE
        assert len(fake.calls) == 1
        call = fake.calls[0]
        assert call['language_id'] == LANG and call['db'] is db and call['drop_missing'] is True
        assert sorted(call['ids']) == ['e11a', 'e11b'] and set(call['senses']) == {11}
        by_id = {e['id']: e for e in out['exercises']['11']}
        assert by_id['e11a']['c']['correct_answer'] == '猫'
        assert 'internal_notes' not in by_id['e11a']['c']
        assert by_id['e11b']['type'] == 'definition_match' and by_id['e11b']['group'] == 'use'

    def test_hydration_miss_drops_content_keeps_has_exercises_and_queues_nothing(self, monkeypatch):
        fake = FakeHydrate(CONTENT, missing={'e11a', 'e11b'})
        monkeypatch.setattr(store, 'hydrate', fake)
        queued = []
        monkeypatch.setattr('services.vocabulary_ladder.queue_drain.enqueue', lambda *a, **k: queued.append(a) or True)
        out = prestudy.build_prestudy_payload(FakeDB(_tables()), TEST_ROW, 'u1', 2)
        assert out['exercises'] == {}
        assert out['has_exercises'] == [11, 12, 16]
        assert queued == []

    def test_no_drill_senses_no_content_read(self, monkeypatch):
        tables = _tables()
        for k in tables['user_vocabulary_knowledge']:
            k['p_known'] = 0.95
        tables['dim_word_senses'] = [s for s in tables['dim_word_senses'] if s['id'] != 13]
        calls = []
        monkeypatch.setattr(store, 'hydrate', lambda items, **kw: calls.append(items))
        db = FakeDB(tables)
        out = prestudy.build_prestudy_payload(db, TEST_ROW, 'u1', 2)
        assert out['exercises'] == {} and out['has_exercises'] == [11, 12, 16]
        assert db.content_queries() == [] and calls == []

    def test_load_exercises_keeps_its_two_argument_form(self):
        db = FakeDB(_tables())
        # Without a language the rows (no language_id in the select) name no file, so
        # nothing is served; every caller passes the test's language.
        assert prestudy._load_exercises(db, [11, 12]) == {}
        assert [q['columns'] for q in db.content_queries()] == [SELECT_STORAGE]
        out = prestudy._load_exercises(db, [11, 12], language_id=LANG)
        assert set(out) == {'11', '12'}


# ---------------------------------------------------------------------------
# GET /api/tests/<id>/prestudy/exercises
# ---------------------------------------------------------------------------

class TestOnDemandEndpoint:

    URL = '/api/tests/cats/prestudy/exercises'

    def _wire(self, monkeypatch, db=None, test=TEST_ROW):
        db = db or FakeDB(_tables())
        monkeypatch.setattr(test_routes, 'get_db', lambda: db)
        monkeypatch.setattr(test_routes, '_find_test_for_prestudy', lambda _db, ident: test)
        return db

    def test_requires_auth(self, client):
        assert client.get(self.URL + '?sense_ids=11').status_code == 401

    def test_404_for_an_unknown_test(self, client, auth_headers, monkeypatch):
        self._wire(monkeypatch, test=None)
        assert client.get(self.URL + '?sense_ids=11', headers=auth_headers).status_code == 404

    def test_400_without_ids_or_over_the_cap(self, client, auth_headers, monkeypatch):
        db = self._wire(monkeypatch)
        assert client.get(self.URL, headers=auth_headers).status_code == 400
        assert client.get(self.URL + '?sense_ids=', headers=auth_headers).status_code == 400
        assert client.get(self.URL + '?sense_ids=,,', headers=auth_headers).status_code == 400
        too_many = ','.join(str(i) for i in range(1, 22))
        assert client.get(self.URL + '?sense_ids=' + too_many, headers=auth_headers).status_code == 400
        assert db.queries == []   # rejected before any read

    def test_twenty_distinct_ids_are_accepted(self, client, auth_headers, monkeypatch):
        self._wire(monkeypatch)
        # 5 linked + 15 foreign = 20 distinct; a repeated id counts once
        twenty = '11,12,13,14,16,' + ','.join(str(i) for i in range(200, 215)) + ',12'
        resp = client.get(self.URL + '?sense_ids=' + twenty, headers=auth_headers)
        assert resp.status_code == 200
        assert resp_json(resp)['sense_ids'] == [11, 12, 13, 14, 16]

    def test_filters_ids_outside_the_test(self, client, auth_headers, monkeypatch):
        db = self._wire(monkeypatch)
        resp = client.get(self.URL + '?sense_ids=12,15,99,abc,-3,%C2%B2,16', headers=auth_headers)
        assert resp.status_code == 200
        data = resp_json(resp)
        assert data['sense_ids'] == [12, 16]          # 15 is a question-only sense, 99 foreign
        assert set(data['exercises']) == {'12', '16'}
        (content_q,) = db.content_queries()
        assert FakeDB.filter_value(content_q, 'word_sense_id') == (12, 16)

    def test_nothing_linked_means_no_read(self, client, auth_headers, monkeypatch):
        db = self._wire(monkeypatch)
        data = resp_json(client.get(self.URL + '?sense_ids=15,99', headers=auth_headers))
        assert data['sense_ids'] == [] and data['exercises'] == {}
        assert db.content_queries() == []

    def test_same_shape_as_the_payload(self, client, auth_headers, monkeypatch):
        self._wire(monkeypatch)
        data = resp_json(client.get(self.URL + '?sense_ids=12', headers=auth_headers))
        rows = [{**{k: r[k] for k in ('id', 'word_sense_id', 'exercise_type', 'ladder_level')},
                 'content': _content_of(r['id'])}
                for r in _tables()['exercises'] if r['word_sense_id'] == 12]
        assert data['exercises'] == prestudy.group_exercises(rows)
        assert data['exercises']['12'][0] == {
            'id': 'e12a', 'type': 'cloze_completion', 'group': 'use', 'level': 3,
            'c': {k: CONTENT['e12a'][k] for k in prestudy.EXERCISE_FIELDS['cloze_completion']}}

    def test_hydrates_once_with_the_language(self, client, auth_headers, monkeypatch):
        fake = FakeHydrate(CONTENT)
        monkeypatch.setattr(store, 'hydrate', fake)
        db = self._wire(monkeypatch)
        data = resp_json(client.get(self.URL + '?sense_ids=12,16', headers=auth_headers))
        assert [q['columns'] for q in db.content_queries()] == [SELECT_STORAGE]
        assert len(fake.calls) == 1 and fake.calls[0]['language_id'] == LANG and fake.calls[0]['db'] is db
        assert data['exercises']['16'][0]['c']['correct_definition'] == 'a'

    def test_a_miss_returns_no_exercises_and_queues_nothing(self, client, auth_headers, monkeypatch):
        monkeypatch.setattr(store, 'hydrate', FakeHydrate({}))
        queued = []
        monkeypatch.setattr('services.vocabulary_ladder.queue_drain.enqueue', lambda *a, **k: queued.append(a) or True)
        self._wire(monkeypatch)
        data = resp_json(client.get(self.URL + '?sense_ids=12,16', headers=auth_headers))
        assert data == {'status': 'success', 'sense_ids': [12, 16], 'exercises': {}}
        assert queued == []

    def test_service_caps_at_twenty(self):
        test = dict(TEST_ROW, vocab_sense_ids=list(range(100, 130)))
        db = FakeDB({'exercises': []})
        served, out = prestudy.on_demand_exercises(db, test, list(range(100, 130)))
        assert served == list(range(100, 120)) and out == {}
        (content_q,) = db.content_queries()
        assert FakeDB.filter_value(content_q, 'word_sense_id') == tuple(range(100, 120))


# ---------------------------------------------------------------------------
# Generation requests keep reading database rows
# ---------------------------------------------------------------------------

class TestGenerationUsesRowIds:

    def _post(self, client, auth_headers, monkeypatch, db, quizzed):
        monkeypatch.setattr(test_routes, 'get_db', lambda: db)
        monkeypatch.setattr(test_routes, '_find_test_for_prestudy', lambda _db, ident: TEST_ROW)
        monkeypatch.setattr(prestudy, 'test_sense_ids', lambda _db, t: {11, 12, 13, 14, 15, 16})
        monkeypatch.setattr(prestudy, 'get_session', lambda _db, u, sid: {
            'id': sid, 'test_id': 't1', 'status': 'open', 'mode': 'prime', 'language_id': LANG})
        monkeypatch.setattr(prestudy, 'complete_session', lambda *a: {'session_id': 'ps1'})
        monkeypatch.setattr('services.intro_drill.admit_prestudy', lambda *a, **k: None)

        class _Svc:
            def __init__(self, db=None):
                pass

            def update_from_word_tests_batch(self, **kw):
                return []
        monkeypatch.setattr(test_routes, 'VocabularyKnowledgeService', _Svc)
        queued = []
        monkeypatch.setattr('services.vocabulary_ladder.queue_drain.enqueue',
                            lambda _db, sid, lang, reason, **k: queued.append(sid) or True)
        body = {'session_id': 'ps1', 'answers': [{'sense_id': s, 'correct': True} for s in quizzed],
                'metrics': {'words_quizzed': quizzed}}
        resp = client.post('/api/tests/cats/prestudy/evidence', headers=auth_headers, json=body)
        assert resp.status_code == 200
        return resp_json(resp), queued

    def test_hydration_miss_and_unloaded_senses_never_queue_generation(self, client, auth_headers, monkeypatch):
        # 11 is a drill sense whose files are missing, 12 and 16 were never loaded
        # on the page; all have exercise rows, so none is queued.
        monkeypatch.setattr(store, 'hydrate', FakeHydrate({}))
        data, queued = self._post(client, auth_headers, monkeypatch, FakeDB(_tables()), [11, 12, 16])
        assert queued == [] and data['generation_queued'] == 0

    def test_a_sense_without_rows_is_still_queued(self, client, auth_headers, monkeypatch):
        data, queued = self._post(client, auth_headers, monkeypatch, FakeDB(_tables()), [11, 13])
        assert queued == [13] and data['generation_queued'] == 1
