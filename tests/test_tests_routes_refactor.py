"""Test routes after the latency/security pass: batched ladder seeding, one
questions read per submit, distractor fetching, explicit columns, the content
cache, server-side withholding and self-scored count validation."""

from types import SimpleNamespace
from unittest.mock import patch

import pytest
from flask import Flask

import services.test_service as ts
from services import attempts
from services.test_service import TestService as _TestService
from services.vocabulary.knowledge_service import VocabularyKnowledgeService
from services.vocabulary_ladder.ladder_service import LadderService


class FakeDB:
    """Chainable fake: ``rows[table]`` is a list, or a callable taking the
    recorded query. Every executed query is appended to ``queries``."""

    def __init__(self, rows=None, rpcs=None):
        self.rows, self.rpcs = rows or {}, rpcs or {}
        self.queries, self.rpc_calls = [], []

    def table(self, name):
        return _Query(self, name)

    def rpc(self, name, params):
        self.rpc_calls.append((name, params))
        handler = self.rpcs.get(name)
        if isinstance(handler, Exception):
            raise handler
        data = handler(params) if callable(handler) else handler
        return SimpleNamespace(execute=lambda: SimpleNamespace(data=data))


class _Query:
    def __init__(self, db, table):
        self.db, self.table, self.ops, self.single_row = db, table, [], False
        self.write = None

    def __getattr__(self, name):
        if name.startswith('_'):
            raise AttributeError(name)

        def op(*args, **kwargs):
            self.ops.append((name, args, kwargs))
            if name == 'single':
                self.single_row = True
            if name in ('insert', 'upsert', 'update'):
                self.write = (name, args[0])
            return self
        return op

    def filters(self, op_name):
        return {a[0]: a[1] for n, a, _ in self.ops if n == op_name}

    def execute(self):
        self.db.queries.append(self)
        source = self.db.rows.get(self.table, [])
        data = source(self) if callable(source) else source
        if self.single_row and isinstance(data, list):
            data = data[0] if data else None
        count = len(data) if isinstance(data, list) else None
        return SimpleNamespace(data=data, count=count)


def reads(db, table):
    return [q for q in db.queries if q.table == table and q.write is None]


# ---------------------------------------------------------------- ladder
class TestInitLadders:
    def _db(self, **extra):
        rows = {
            'user_vocabulary_knowledge': [{'sense_id': 1, 'p_known': 0.8}],
            'dim_word_senses': [
                {'id': 1, 'dim_vocabulary': {'semantic_class': 'concrete_noun'}},
                {'id': 2, 'dim_vocabulary': {'semantic_class': ''}},
            ],
            'user_word_ladder': [],
        }
        rows.update(extra)
        return FakeDB(rows)

    def _single_rows(self, sense_ids):
        """What one init_ladder call per sense writes."""
        out = []
        for sid in sense_ids:
            db = FakeDB({
                'user_vocabulary_knowledge':
                    [{'p_known': 0.8}] if sid == 1 else [],
                'dim_word_senses': (
                    [{'dim_vocabulary': {'semantic_class': 'concrete_noun' if sid == 1 else ''}}]
                    if sid in (1, 2) else []),
            })
            if sid not in (1, 2):
                db.rows['dim_word_senses'] = lambda q: (_ for _ in ()).throw(RuntimeError('no row'))
            out.append(LadderService(db).init_ladder('u', sid, 1))
        return out

    @staticmethod
    def _strip(rows):
        return [{k: v for k, v in r.items() if k != 'updated_at'} for r in rows]

    def test_same_rows_as_one_call_per_sense(self):
        with patch('services.intro_drill.ENABLED', False):
            db = self._db()
            rows = LadderService(db).init_ladders('u', [1, 2, 3], 1)
            assert self._strip(rows) == self._strip(self._single_rows([1, 2, 3]))

    def test_two_reads_and_one_upsert(self):
        with patch('services.intro_drill.ENABLED', False):
            db = self._db()
            LadderService(db).init_ladders('u', [1, 2, 3], 1)
        assert len(db.queries) == 3
        writes = [q.write for q in db.queries if q.write]
        assert len(writes) == 1 and writes[0][0] == 'upsert'
        assert [r['sense_id'] for r in writes[0][1]] == [1, 2, 3]

    def test_failed_bulk_upsert_writes_rows_one_by_one(self):
        def ladder(q):
            if isinstance(q.write[1], list) or q.write[1]['sense_id'] == 2:
                raise RuntimeError('boom')
            return []
        with patch('services.intro_drill.ENABLED', False):
            db = self._db(user_word_ladder=ladder)
            rows = LadderService(db).init_ladders('u', [1, 2, 3], 1)
        assert [r['sense_id'] for r in rows] == [1, 3]

    def test_seed_ladder_skips_existing_and_batches(self):
        db = FakeDB({'user_word_ladder': [{'sense_id': 1}]})
        svc = VocabularyKnowledgeService(db)
        with patch.object(LadderService, 'init_ladders', return_value=[{}]) as init:
            svc.seed_ladder('u', 1, [
                {'out_sense_id': 1, 'out_status': 'learning'},
                {'out_sense_id': 2, 'out_status': 'encountered'},
                {'out_sense_id': 3, 'out_status': 'known'},
            ])
        init.assert_called_once_with('u', [2], 1)


# ---------------------------------------------------------- distractors
class TestDistractors:
    CANDIDATES = [
        {'out_sense_id': 1, 'out_lemma': 'a', 'out_definition': 'def a', 'out_p_known': 0.5},
        {'out_sense_id': 2, 'out_lemma': 'b', 'out_definition': 'def b', 'out_p_known': 0.5},
    ]

    @staticmethod
    def _single(params):
        return [{'out_definition': f"d{params['p_sense_id']}-{i}", 'out_lemma': f'l{i}'}
                for i in range(3)]

    def test_per_word_path_is_default(self, monkeypatch):
        monkeypatch.delenv('QUIZ_DISTRACTORS_BATCH', raising=False)
        db = FakeDB(rpcs={'get_word_quiz_candidates': self.CANDIDATES,
                          'get_quiz_distractors': self._single})
        quiz = VocabularyKnowledgeService(db).build_quiz_with_distractors('u', [1, 2], 1)
        names = [n for n, _ in db.rpc_calls]
        assert names.count('get_quiz_distractors') == 2
        assert 'get_quiz_distractors_batch' not in names
        assert [q['sense_id'] for q in quiz] == [1, 2]
        assert all(o.startswith(('def', f"d{q['sense_id']}-")) for q in quiz for o in q['options'])

    def test_batch_flag_uses_one_call(self, monkeypatch):
        monkeypatch.setenv('QUIZ_DISTRACTORS_BATCH', '1')
        batch = [{'out_position': pos, 'out_sense_id': pos, 'out_definition': f'd{pos}-{i}',
                  'out_lemma': f'l{i}'} for pos in (1, 2) for i in range(3)]
        db = FakeDB(rpcs={'get_word_quiz_candidates': self.CANDIDATES,
                          'get_quiz_distractors_batch': batch})
        quiz = VocabularyKnowledgeService(db).build_quiz_with_distractors('u', [1, 2], 1)
        names = [n for n, _ in db.rpc_calls]
        assert names == ['get_word_quiz_candidates', 'get_quiz_distractors_batch']
        assert db.rpc_calls[1][1]['p_sense_ids'] == [1, 2]
        assert [len(q['options']) for q in quiz] == [4, 4]
        assert all(o.startswith(('def', f"d{q['sense_id']}-")) for q in quiz for o in q['options'])

    def test_batch_failure_falls_back_to_per_word(self, monkeypatch):
        monkeypatch.setenv('QUIZ_DISTRACTORS_BATCH', '1')
        db = FakeDB(rpcs={'get_word_quiz_candidates': self.CANDIDATES,
                          'get_quiz_distractors_batch': RuntimeError('PGRST202'),
                          'get_quiz_distractors': self._single})
        quiz = VocabularyKnowledgeService(db).build_quiz_with_distractors('u', [1, 2], 1)
        assert len(quiz) == 2


# -------------------------------------------------- vocabulary tracking
class TestTrackVocabulary:
    def _run(self, updates, pending):
        db = FakeDB(
            rows={'users': [{'native_language_id': 2}]},
            rpcs={'update_vocabulary_from_test': updates, 'get_word_quiz_candidates': []},
        )
        svc = VocabularyKnowledgeService(db)
        order = []
        svc._auto_create_flashcards = lambda *a: order.append('flashcards')
        svc._seed_ladder_for_new_words = lambda *a: order.append('ladder')
        svc._trigger_frequency_inference = lambda *a: order.append('frequency')
        svc.apply_contextual_inference = lambda **k: order.append(('contextual', k['question_rows'])) or 0
        rpc_result = {'question_results': [{'question_id': 'q1', 'is_correct': True}],
                      'score': 1, 'total_questions': 1, 'attempt_id': 'a'}
        rows = [{'id': 'q1', 'sense_ids': [5], 'answer_explanation': 'x'}]
        with patch.object(attempts, 'VocabularyKnowledgeService', return_value=svc):
            out = attempts.track_vocabulary('u', 't', 1, rpc_result,
                                            question_rows=rows, pending=pending)
        if pending:
            attempts.join(pending)
        return out, order, db, rows

    def test_questions_are_not_read_again(self):
        _, order, db, rows = self._run([{'out_sense_id': 5, 'out_status': 'learning'}], [])
        assert reads(db, 'questions') == []
        assert ('contextual', rows) in order

    def test_side_effects_run_when_deferred(self):
        _, order, _, _ = self._run([{'out_sense_id': 5, 'out_status': 'learning'}], [])
        assert 'flashcards' in order and 'ladder' in order and 'frequency' not in order

    def test_original_order_when_a_word_becomes_known(self):
        updates = [{'out_sense_id': 5, 'out_status': 'known',
                    'out_p_known_before': 0.5, 'out_p_known_after': 0.95}]
        _, order, _, _ = self._run(updates, [])
        assert order[:3] == ['flashcards', 'ladder', 'frequency']
        assert order[3][0] == 'contextual'

    def test_explanations_come_from_the_same_rows(self):
        result = {'question_results': [{'question_id': 'q1'}, {'question_id': 'q2'}]}
        attempts.attach_explanations(result, [{'id': 'q1', 'answer_explanation': 'because'}])
        assert [q['answer_explanation'] for q in result['question_results']] == ['because', None]


# ------------------------------------------------- lookups and columns
class TestLookups:
    def test_slug_payload_selects_explicit_columns_of_active_tests(self):
        db = FakeDB({
            'tests': [{'id': 1, 'slug': 's', 'language_id': 1, 'difficulty': 2,
                       'transcript': 'T', 'created_at': 'c'}],
            'questions': [{'id': 'q', 'question_text': 'Q', 'choices': '["a"]'}],
        })
        out = _TestService(supabase_admin=db).get_test_by_slug('s')
        test_q, question_q = db.queries
        assert '*' not in test_q.ops[0][1][0] and '*' not in question_q.ops[0][1][0]
        assert ('eq', ('is_active', True), {}) in test_q.ops
        assert out['transcript'] == 'T' and out['questions'] == [
            {'id': 'q', 'question': 'Q', 'choices': ['a']}]
        assert set(out) == {'id', 'slug', 'language_id', 'language', 'topic', 'title',
                            'difficulty', 'transcript', 'questions', 'created_at'}

    def test_non_uuid_identifier_is_not_looked_up_by_id(self):
        db = FakeDB({'tests': []})
        assert ts.find_active_test(db, 'no-such-slug', 'id') is None
        assert len(db.queries) == 1

    def test_uuid_identifier_falls_back_to_id(self):
        uid = '123e4567-e89b-12d3-a456-426614174000'
        db = FakeDB({'tests': lambda q: [{'id': uid}] if 'id' in q.filters('eq') else []})
        assert ts.find_active_test(db, uid, 'id') == {'id': uid}


class TestContentCache:
    def test_second_open_reads_no_static_content(self):
        db = FakeDB({
            'tests': [{'id': 't1', 'slug': 's', 'vocab_token_map': [['w', 7]]}],
            'questions': [{'id': 'q1'}],
            'dim_word_senses': [{'id': 7}],
        })
        first, _ = ts.get_test_content(db, 's')
        n = len(db.queries)
        first['test']['slug'] = 'mutated'
        second, extras = ts.get_test_content(db, 's', also=(lambda t: t['id'],))
        assert len(db.queries) == n and extras == ['t1']
        assert second['test']['slug'] == 's' and second['questions'] == [{'id': 'q1'}]

    def test_unknown_test_is_not_cached(self):
        db = FakeDB({'tests': []})
        assert ts.get_test_content(db, 's') is None
        db.rows['tests'] = [{'id': 't1', 'slug': 's'}]
        assert ts.get_test_content(db, 's')[0]['test']['id'] == 't1'

    def test_ttl_and_size_bound(self, monkeypatch):
        cache = ts.TTLCache(maxsize=2, ttl=10)
        now = [100.0]
        monkeypatch.setattr(ts.time, 'monotonic', lambda: now[0])
        cache.put('a', 1), cache.put('b', 2), cache.put('c', 3)
        assert cache.get('a') is None and cache.get('c') == 3
        now[0] += 11
        assert cache.get('c') is None


# ------------------------------------------------------------ history
class TestHistoryAndElo:
    ATTEMPT = {'id': 'a1', 'test_id': 't1', 'score': 1, 'total_questions': 2, 'percentage': 50,
               'user_elo_after': 1210, 'created_at': 'c', 'test_type_id': 2}

    def test_type_names_come_from_the_dimension_cache(self, monkeypatch):
        monkeypatch.setattr(ts.DimensionService, '_test_types_metadata',
                            [{'id': 2, 'type_code': 'reading', 'type_name': 'Reading'}])
        db = FakeDB({'test_attempts': [self.ATTEMPT],
                     'tests': [{'id': 't1', 'title': 'T', 'slug': 's'}]})
        out = attempts.list_test_history(db, db, 'u')
        assert out[0]['test_type'] == 'Reading' and out[0]['test_slug'] == 's'
        assert reads(db, 'dim_test_types') == []

    def test_type_missing_from_cache_reads_the_table(self, monkeypatch):
        monkeypatch.setattr(ts.DimensionService, '_test_types_metadata', [])
        db = FakeDB({'test_attempts': [self.ATTEMPT], 'tests': [],
                     'dim_test_types': [{'id': 2, 'type_name': 'Reading'}]})
        assert attempts.list_test_history(db, db, 'u')[0]['test_type'] == 'Reading'

    @staticmethod
    def _history_db(ratings, attempts_rows):
        def test_attempts(q):
            eq = q.filters('eq')
            rows = [a for a in attempts_rows
                    if all(a.get(k) == v for k, v in eq.items() if k != 'user_id')]
            rows = sorted(rows, key=lambda a: a['created_at'], reverse=True)
            if any(n == 'limit' for n, _, _ in q.ops):
                return _Counted(rows[:1], len(rows))
            return _Counted(rows, len(rows))
        return FakeDB({'user_skill_ratings': ratings, 'test_attempts': test_attempts})

    ROWS = [
        {'language_id': 1, 'test_type_id': 2, 'user_elo_after': 1300, 'created_at': '2026-03'},
        {'language_id': 1, 'test_type_id': 2, 'user_elo_after': 1250, 'created_at': '2026-01'},
        {'language_id': 3, 'test_type_id': 1, 'user_elo_after': 1100, 'created_at': '2026-02'},
    ]

    def _full(self):
        db = self._history_db([], self.ROWS)
        return _TestService(supabase_admin=db)._skill_attempt_stats('u')

    def test_per_skill_reads_match_the_full_history(self):
        db = self._history_db(
            [{'language_id': 1, 'test_type_id': 2}, {'language_id': 3, 'test_type_id': 1}],
            self.ROWS)
        stats = _TestService(supabase_admin=db)._skill_attempt_stats('u')
        assert stats == self._full() and list(stats) == list(self._full())
        assert stats[(1, 2)] == {'elo_rating': 1300, 'last_test_date': '2026-03', 'tests_taken': 2}
        assert all(any(n == 'limit' for n, _, _ in q.ops) or q.ops[0][2].get('head')
                   for q in reads(db, 'test_attempts'))

    def test_skill_without_rating_row_falls_back_to_full_history(self):
        db = self._history_db([{'language_id': 1, 'test_type_id': 2}], self.ROWS)
        assert _TestService(supabase_admin=db)._skill_attempt_stats('u') == self._full()


class _Counted(list):
    """A row list whose FakeDB count is the unlimited total."""

    def __init__(self, rows, total):
        super().__init__(rows)
        self.total = total

    def __len__(self):
        return self.total


# -------------------------------------------------------------- routes
PINYIN = [{'char': c, 'is_punctuation': c == '。'} for c in '你好吗。']
PITCH = [
    {'surface': 'a', 'is_punctuation': False, 'mora_count': 2, 'pattern_class': 'heiban'},
    {'surface': 'b', 'is_punctuation': False, 'mora_count': 0, 'pattern_class': 'heiban'},
    {'surface': 'c', 'is_punctuation': False, 'mora_count': 2, 'pattern_class': 'unknown'},
    {'surface': '。', 'is_punctuation': True, 'mora_count': 0, 'pattern_class': 'unknown'},
]


def test_item_counts_match_the_players():
    assert attempts.pinyin_item_count(PINYIN) == 3
    assert attempts.pitch_item_count(PITCH) == 1
    assert attempts.pinyin_item_count(None) == 0 and attempts.pitch_item_count('x') == 0


@pytest.fixture
def app(monkeypatch):
    import middleware.auth as auth
    monkeypatch.setattr(auth, '_authenticate',
                        lambda token: ({'sub': 'user-1'}, None) if token == 'good' else (None, 'bad'))
    from routes.tests import tests_bp
    a = Flask(__name__)
    a.config.update(TESTING=True, SECRET_KEY='k')
    a.register_blueprint(tests_bp, url_prefix='/api/tests')
    return a


AUTH = {'Authorization': 'Bearer good'}


def _rpc_ok():
    return {'success': True, 'attempt_id': 'att-1', 'user_elo_before': 1200,
            'user_elo_after': 1210, 'user_elo_change': 10}


class TestCountedSubmits:
    def _post(self, app, route, body, row):
        app.supabase_service = FakeDB({'tests': [row]})
        with patch('routes.tests.submit._call_pinyin_submission_rpc', return_value=_rpc_ok()) as pin, \
             patch('routes.tests.submit._call_pitch_accent_submission_rpc', return_value=_rpc_ok()) as pitch, \
             patch('routes.tests.submit._apply_timing_and_progress'), \
             patch('routes.tests.submit._complete_daily_slot'), \
             patch('routes.tests.DimensionService.get_test_type_id', return_value=9):
            r = app.test_client().post(f'/api/tests/s/{route}', json=body, headers=AUTH)
        return r, pin, pitch

    def test_pinyin_total_above_real_count_is_rejected(self, app):
        row = {'id': 't', 'language_id': 1, 'pinyin_payload': PINYIN}
        r, pin, _ = self._post(app, 'submit-pinyin', {'correct_chars': 4, 'total_chars': 4}, row)
        assert r.status_code == 400
        pin.assert_not_called()

    def test_pinyin_within_real_count_is_accepted(self, app):
        row = {'id': 't', 'language_id': 1, 'pinyin_payload': PINYIN}
        r, pin, _ = self._post(app, 'submit-pinyin', {'correct_chars': 2, 'total_chars': 3}, row)
        assert r.status_code == 200, r.data
        result = r.get_json()['result']
        assert (result['accuracy'], result['correct_chars'], result['total_chars']) == (66.7, 2, 3)
        assert result['test_mode'] == 'pinyin' and result['attempt_id'] == 'att-1'
        assert result['user_elo_change'] == {'before': 1200, 'after': 1210, 'change': 10}
        assert pin.call_args.args[5:] == (2, 3)

    def test_test_without_payload_is_rejected(self, app):
        row = {'id': 't', 'language_id': 1, 'pinyin_payload': None}
        r, pin, _ = self._post(app, 'submit-pinyin', {'correct_chars': 1, 'total_chars': 1}, row)
        assert r.status_code == 400
        pin.assert_not_called()

    def test_pitch_counts_only_drillable_phrases(self, app):
        row = {'id': 't', 'language_id': 3, 'pitch_payload': PITCH}
        r, _, pitch = self._post(app, 'submit-pitch-accent',
                                 {'correct_units': 1, 'total_units': 2}, row)
        assert r.status_code == 400
        pitch.assert_not_called()
        r, _, pitch = self._post(app, 'submit-pitch-accent',
                                 {'correct_units': 1, 'total_units': 1, 'furigana_used': True}, row)
        assert r.status_code == 200, r.data
        assert pitch.call_args.kwargs['furigana_used'] is True
        assert r.get_json()['result']['test_mode'] == 'pitch_accent'


class TestOpenRoutes:
    TEST_ROW = {'id': 't1', 'slug': 's', 'language_id': 1, 'transcript': 'secret text',
                'vocab_token_map': [['secret', 7]], 'dim_languages': {'language_code': 'zh'}}

    def _db(self, load_rows):
        return FakeDB({
            'tests': [dict(self.TEST_ROW)],
            'questions': [{'id': 'q1', 'question_text': 'Q'}],
            'test_skill_ratings': [],
            'dim_word_senses': [],
            'user_study_plans': [],
            'users': [{'native_language_id': 1}],
            'daily_test_loads': load_rows,
        })

    DICTATION_LOAD = [{'test_ids': [{'test_id': 't1', 'test_type': 'dictation'}],
                       'completed_test_ids': []}]

    def test_inactive_test_is_not_served_by_slug(self, app):
        db = FakeDB({'tests': lambda q: [] if q.filters('eq').get('is_active') else
                     [{'id': 1, 'slug': 's', 'language_id': 1, 'difficulty': 1}]})
        app.supabase_service = db
        with patch('routes.tests.catalog.get_test_service', return_value=_TestService(supabase_admin=db)):
            assert app.test_client().get('/api/tests/s').status_code == 404

    def test_anonymous_open_is_cacheable_and_has_transcript(self, app):
        app.supabase_service = self._db([])
        r = app.test_client().get('/api/tests/test/s')
        assert r.status_code == 200
        assert r.headers['Cache-Control'] == 'private, max-age=60'
        assert r.get_json()['test_data']['transcript'] == 'secret text'

    def test_signed_in_open_is_not_marked_cacheable(self, app):
        app.supabase_service = self._db([])
        r = app.test_client().get('/api/tests/test/s', headers=AUTH)
        assert r.status_code == 200 and 'max-age' not in r.headers.get('Cache-Control', '')
        assert r.get_json()['test_data']['transcript'] == 'secret text'

    def test_pending_dictation_slot_withholds_whatever_the_mode(self, app):
        app.supabase_service = self._db(self.DICTATION_LOAD)
        for url in ('/api/tests/test/s', '/api/tests/test/s?mode=reading'):
            body = app.test_client().get(url, headers=AUTH).get_json()
            assert 'transcript' not in body['test_data']
            assert body['vocab_token_map'] == [] and body['definitions'] == {}
            assert 'secret' not in str(body)

    def test_completed_dictation_slot_releases_the_transcript(self, app):
        load = [{**self.DICTATION_LOAD[0], 'completed_test_ids': ['t1']}]
        app.supabase_service = self._db(load)
        body = app.test_client().get('/api/tests/test/s', headers=AUTH).get_json()
        assert body['test_data']['transcript'] == 'secret text'

    def test_mode_dictation_still_withholds(self, app):
        app.supabase_service = self._db([])
        body = app.test_client().get('/api/tests/test/s?mode=dictation').get_json()
        assert 'transcript' not in body['test_data']

    def test_unknown_non_uuid_identifier_is_404(self, app):
        app.supabase_service = FakeDB({'tests': []})
        assert app.test_client().get('/api/tests/test/nope').status_code == 404

    def test_submit_reads_questions_once(self, app):
        db = FakeDB(
            rows={'tests': [{'id': 't1', 'language_id': 1}],
                  'questions': [{'id': 'q1', 'sense_ids': [5], 'answer_explanation': 'why'}],
                  'prestudy_sessions': []},
        )
        app.supabase_service = db
        rpc = {'success': True, 'attempt_id': 'a1', 'score': 1, 'total_questions': 1,
               'question_results': [{'question_id': 'q1', 'is_correct': True}]}
        knowledge_db = FakeDB(rows={'users': [], 'user_flashcards': [], 'user_word_ladder': [],
                                    'tests': [{'vocab_sense_ids': []}]},
                              rpcs={'update_vocabulary_from_test': [],
                                    'get_word_quiz_candidates': []})
        with patch('routes.tests.submit._call_submission_rpc', return_value=rpc), \
             patch('routes.tests.submit._apply_timing_and_progress') as timing, \
             patch('routes.tests.submit._complete_daily_slot') as slot, \
             patch('routes.tests.DimensionService.get_test_type_id', return_value=1), \
             patch.object(attempts, 'VocabularyKnowledgeService',
                          return_value=VocabularyKnowledgeService(knowledge_db)):
            r = app.test_client().post('/api/tests/s/submit', headers=AUTH, json={
                'responses': [{'question_id': 'q1', 'selected_answer': 'a'}]})
        assert r.status_code == 200, r.data
        assert len(reads(db, 'questions')) == 1 and reads(knowledge_db, 'questions') == []
        assert r.get_json()['result']['question_results'][0]['answer_explanation'] == 'why'
        timing.assert_called_once()
        slot.assert_called_once()
