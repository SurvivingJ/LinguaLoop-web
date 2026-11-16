"""GET /api/dual-translation/next — study language, no repeats, sentence-level
fallback (fix of investigation points 4, 5 and the code half of 8).

Selection runs against ``_TableDB``, a small in-memory stand-in for the
supabase-py query builder that APPLIES the filters (eq / in_ / gte / lte /
order / limit), so the tests exercise the real queries of
``routes.dual_translation._choose_next`` and ``open_range_passage`` rather than
canned per-table answers.
"""

import json

import pytest

import routes.dual_translation as dt_routes
from config import Config
from services.dimension_service import DimensionService

USER = 'test-user-id-123'  # conftest's mocked auth identity
ZH, EN, JA = 1, 2, 3


# ---------------------------------------------------------------------------
# A filtering fake DB
# ---------------------------------------------------------------------------

def _same(a, b):
    return a == b or str(a) == str(b)


class _Result:
    def __init__(self, data):
        self.data = data


class _Query:
    def __init__(self, db, table):
        self.db, self.table_name = db, table
        self.filters = []
        self.orders = []
        self.limit_n = None
        self.op = 'select'
        self.payload = None

    def select(self, *a, **k):
        return self

    def eq(self, col, val):
        self.filters.append(lambda r: _same(r.get(col), val))
        return self

    def in_(self, col, vals):
        vals = list(vals)
        self.filters.append(lambda r: any(_same(r.get(col), v) for v in vals))
        return self

    def gte(self, col, val):
        self.filters.append(lambda r: r.get(col) is not None and r.get(col) >= val)
        return self

    def lte(self, col, val):
        self.filters.append(lambda r: r.get(col) is not None and r.get(col) <= val)
        return self

    def or_(self, *a, **k):
        return self

    def order(self, col, desc=False):
        self.orders.append((col, desc))
        return self

    def limit(self, n):
        self.limit_n = n
        return self

    def range(self, start, end):
        # PostgREST offset paging; the response is also capped at db.row_cap
        # rows, as the real server's max-rows setting caps it.
        self.range_ = (start, end)
        return self

    def insert(self, payload):
        self.op, self.payload = 'insert', payload
        return self

    def update(self, payload):
        self.op, self.payload = 'update', payload
        return self

    def execute(self):
        rows = self.db.tables.setdefault(self.table_name, [])
        if self.op == 'insert':
            items = self.payload if isinstance(self.payload, list) else [self.payload]
            out = []
            for item in items:
                row = dict(item)
                row.setdefault('id', self.db.next_id())
                row.setdefault('created_at', self.db.tick())
                rows.append(row)
                out.append(row)
            self.db.inserts.append((self.table_name, items))
            return _Result(out)
        hits = [r for r in rows if all(f(r) for f in self.filters)]
        if self.op == 'update':
            for r in hits:
                r.update(self.payload)
            return _Result(hits)
        for col, desc in reversed(self.orders):
            hits.sort(key=lambda r: (r.get(col) is None, r.get(col)), reverse=desc)
        if self.limit_n is not None:
            hits = hits[:self.limit_n]
        if getattr(self, 'range_', None) is not None:
            start, end = self.range_
            hits = hits[start:end + 1]
        if self.db.row_cap is not None:
            hits = hits[:self.db.row_cap]
        self.db.reads.append(self.table_name)
        return _Result([dict(r) for r in hits])


class _TableDB:
    def __init__(self, tables):
        self.tables = {k: [dict(r) for r in v] for k, v in tables.items()}
        self.inserts = []
        self.reads = []
        self.row_cap = None
        self._id = 1000
        self._clock = 0

    def next_id(self):
        self._id += 1
        return self._id

    def tick(self):
        self._clock += 1
        return f'2026-11-16T12:{self._clock // 60:02d}:{self._clock % 60:02d}Z'

    def table(self, name):
        return _Query(self, name)


# ---------------------------------------------------------------------------
# Fixtures: a Chinese test with legacy passages, a Japanese test with
# sentence-level references only.
# ---------------------------------------------------------------------------

ZH_TEST = 'aaaaaaaa-0000-0000-0000-000000000001'
JA_TEST = 'bbbbbbbb-0000-0000-0000-000000000002'
UNTAKEN_JA_TEST = 'cccccccc-0000-0000-0000-000000000003'

JA_SENTENCES = ['今日は晴れです。', '公園に行きました。', '友達に会いました。', '一緒に昼ご飯を食べました。',
                'とても楽しかったです。', '夕方に家に帰りました。']
JA_REFS = ['It is sunny today.', 'I went to the park.', 'I met a friend.', 'We ate lunch together.',
           'It was a lot of fun.', 'I went home in the evening.']


def _tables(**overrides):
    tables = {
        'test_attempts': [
            {'id': 'a1', 'user_id': USER, 'test_id': ZH_TEST, 'language_id': ZH,
             'created_at': '2026-11-10T00:00:00Z'},
            {'id': 'a2', 'user_id': USER, 'test_id': JA_TEST, 'language_id': JA,
             'created_at': '2026-11-12T00:00:00Z'},
        ],
        'tests': [
            {'id': ZH_TEST, 'language_id': ZH, 'difficulty': 4, 'transcript_hash': 'hz',
             'is_active': True, 'vocab_token_map': None},
            {'id': JA_TEST, 'language_id': JA, 'difficulty': 4, 'transcript_hash': 'hj',
             'is_active': True, 'vocab_token_map': None},
            {'id': UNTAKEN_JA_TEST, 'language_id': JA, 'difficulty': 4, 'transcript_hash': 'hu',
             'is_active': True, 'vocab_token_map': None},
        ],
        'dt_passage': [
            {'id': 1, 'l2_language_id': ZH, 'source_kind': 'test_transcript', 'source_ref_id': ZH_TEST,
             'l2_text': '我们去公园。天气很好。', 'age_tier': 3, 'status': 'active',
             'sentence_start': None, 'sentence_end': None},
            {'id': 2, 'l2_language_id': ZH, 'source_kind': 'test_transcript', 'source_ref_id': ZH_TEST,
             'l2_text': '他喜欢看书。书很有意思。', 'age_tier': 3, 'status': 'active',
             'sentence_start': None, 'sentence_end': None},
        ],
        'dt_passage_reference': [
            {'passage_id': 1, 'l1_language_id': EN, 'l1_text': 'We go to the park. The weather is nice.'},
            {'passage_id': 2, 'l1_language_id': EN, 'l1_text': 'He likes reading. Books are interesting.'},
        ],
        'test_sentences': [
            {'id': 500 + i, 'test_id': JA_TEST, 'idx': i, 'l2_text': text, 'token_start': None,
             'token_end': None, 'transcript_hash': 'hj'}
            for i, text in enumerate(JA_SENTENCES)
        ] + [
            {'id': 600, 'test_id': UNTAKEN_JA_TEST, 'idx': 0, 'l2_text': '未受験です。', 'token_start': None,
             'token_end': None, 'transcript_hash': 'hu'},
            {'id': 601, 'test_id': UNTAKEN_JA_TEST, 'idx': 1, 'l2_text': '出してはいけません。',
             'token_start': None, 'token_end': None, 'transcript_hash': 'hu'},
        ],
        'test_sentence_references': [
            {'sentence_id': 500 + i, 'l1_language_id': EN, 'l1_text': text, 'tightness': 0.9,
             'review_verdict': 'pass', 'is_active': True}
            for i, text in enumerate(JA_REFS)
        ] + [
            {'sentence_id': sid, 'l1_language_id': EN, 'l1_text': 'Not taken.', 'tightness': 0.9,
             'review_verdict': 'pass', 'is_active': True}
            for sid in (600, 601)
        ],
        'dt_submission': [],
        'dt_grade': [],
        'users': [{'id': USER, 'native_language_id': None}],
    }
    tables.update(overrides)
    return tables


def _serve(db, choice, l1=EN):
    """What GET /next would record for this choice: a dt_submission row (for a
    range, the passage is found-or-created first, as open_range_passage does)."""
    if choice['kind'] == 'passage':
        pid = choice['passage']['passage_id']
    else:
        test = dt_routes._get_test_for_passage(db, choice['test_id'])
        sentences = dt_routes._get_sentence_range(db, choice['test_id'], choice['start'], choice['end'])
        pid = dt_routes._find_or_create_range_passage(
            db, test, choice['start'], choice['end'], l2_text=''.join(s['l2_text'] for s in sentences),
        )['id']
    return db.table('dt_submission').insert({
        'user_id': USER, 'passage_id': pid, 'l1_language_id': l1, 'reproduction': '',
    }).execute().data[0]


def _grade(db, submission):
    db.table('dt_grade').insert({'submission_id': submission['id'], 'overall_band': 3}).execute()


def _choose(db, l2, l1=EN):
    return dt_routes._choose_next(db, USER, l1, l2, dt_routes._attempted_tests(db, USER))


# ---------------------------------------------------------------------------
# _choose_next
# ---------------------------------------------------------------------------

class TestEligibility:

    def test_none_when_no_attempted_tests(self):
        db = _TableDB(_tables(test_attempts=[]))
        assert _choose(db, ZH) == {'kind': 'none', 'all_done': False}

    def test_legacy_passage_without_l1_reference_is_not_served(self):
        db = _TableDB(_tables(dt_passage_reference=[], test_sentences=[], test_sentence_references=[]))
        assert _choose(db, ZH) == {'kind': 'none', 'all_done': False}

    def test_returns_legacy_passage_with_l1_reference(self):
        db = _TableDB(_tables())
        choice = _choose(db, ZH)
        assert choice['kind'] == 'passage'
        passage = choice['passage']
        assert passage['passage_id'] in (1, 2)
        assert passage['l2_language_id'] == ZH
        assert passage['age_tier'] == 3
        expected = {1: 'We go to the park. The weather is nice.', 2: 'He likes reading. Books are interesting.'}
        assert passage['l1_text'] == expected[passage['passage_id']]

    def test_same_l1_as_l2_has_nothing(self):
        db = _TableDB(_tables())
        assert _choose(db, ZH, l1=ZH) == {'kind': 'none', 'all_done': False}


class TestStudyLanguage:

    def test_japanese_learner_never_gets_the_chinese_legacy_passages(self):
        db = _TableDB(_tables())
        for _ in range(3):
            choice = _choose(db, JA)
            assert choice['kind'] == 'range'
            assert choice['test_id'] == JA_TEST
            _grade(db, _serve(db, choice))

    def test_chinese_learner_never_gets_japanese_windows(self):
        db = _TableDB(_tables())
        seen = []
        while True:
            choice = _choose(db, ZH)
            if choice['kind'] == 'none':
                break
            assert choice['kind'] == 'passage'
            seen.append(choice['passage']['passage_id'])
            _grade(db, _serve(db, choice))
        assert sorted(seen) == [1, 2]

    def test_windows_only_from_attempted_tests(self):
        db = _TableDB(_tables())
        while True:
            choice = _choose(db, JA)
            if choice['kind'] == 'none':
                break
            assert choice['test_id'] != UNTAKEN_JA_TEST
            _grade(db, _serve(db, choice))


class TestNoRepeats:

    def test_graded_legacy_passage_is_not_served_again(self):
        db = _TableDB(_tables())
        first = _choose(db, ZH)['passage']['passage_id']
        _grade(db, _serve(db, _choose(db, ZH)))
        second = _choose(db, ZH)
        assert second['kind'] == 'passage'
        assert second['passage']['passage_id'] != first

    def test_unseen_passage_before_a_served_ungraded_one(self):
        db = _TableDB(_tables())
        first = _choose(db, ZH)
        _serve(db, first)  # served, abandoned (never graded)
        second = _choose(db, ZH)
        assert second['passage']['passage_id'] != first['passage']['passage_id']

    def test_windows_do_not_overlap_served_windows(self):
        db = _TableDB(_tables())
        covered = set()
        windows = []
        while True:
            choice = _choose(db, JA)
            if choice['kind'] == 'none':
                break
            span = set(range(choice['start'], choice['end'] + 1))
            assert not span & covered
            assert 2 <= len(span) <= 4
            covered |= span
            windows.append((choice['start'], choice['end']))
            _grade(db, _serve(db, choice))
        assert windows == [(0, 1), (2, 3), (4, 5)]

    def test_all_done_once_everything_is_graded(self):
        db = _TableDB(_tables())
        for _ in range(10):
            choice = _choose(db, ZH)
            if choice['kind'] == 'none':
                break
            _grade(db, _serve(db, choice))
        assert _choose(db, ZH) == {'kind': 'none', 'all_done': True}

    def test_served_but_ungraded_passage_comes_back_least_recent_first(self):
        db = _TableDB(_tables())
        first = _serve(db, _choose(db, ZH))      # served first, never graded
        second = _serve(db, _choose(db, ZH))     # served second, never graded
        assert first['passage_id'] != second['passage_id']
        again = _choose(db, ZH)
        assert again['kind'] == 'passage'
        assert again['passage']['passage_id'] == first['passage_id']

    def test_served_but_ungraded_window_comes_back_when_nothing_fresh_is_left(self):
        db = _TableDB(_tables())
        submissions = []
        while True:
            choice = _choose(db, JA)
            if choice['kind'] == 'none' or len(submissions) > 5:
                break
            submissions.append((choice, _serve(db, choice)))
            if len(submissions) == 3:
                break
        # three windows served, the first never graded
        for _, sub in submissions[1:]:
            _grade(db, sub)
        again = _choose(db, JA)
        assert again['kind'] == 'range'
        assert (again['start'], again['end']) == (submissions[0][0]['start'], submissions[0][0]['end'])

    def test_history_past_the_row_cap_still_counts_as_graded(self, monkeypatch):
        """dt_submission gains a row on every serve, so a long-time learner's
        history outgrows one PostgREST response (max-rows). A graded passage
        whose submission lies past the first page must still never come back."""
        monkeypatch.setattr(dt_routes, '_POSTGREST_ROW_CAP', 3)
        db = _TableDB(_tables())
        db.row_cap = 3
        for _ in range(7):  # passage 2 served (and skipped) seven times
            _serve(db, {'kind': 'passage', 'passage': {'passage_id': 2}})
        _grade(db, _serve(db, {'kind': 'passage', 'passage': {'passage_id': 1}}))  # 8th row
        choice = _choose(db, ZH)
        assert choice['kind'] == 'passage'
        assert choice['passage']['passage_id'] == 2

    def test_attempts_past_the_row_cap_are_all_read(self, monkeypatch):
        monkeypatch.setattr(dt_routes, '_POSTGREST_ROW_CAP', 2)
        db = _TableDB(_tables())
        db.row_cap = 2
        db.tables['test_attempts'] = [
            {'id': f'z{i}', 'user_id': USER, 'test_id': ZH_TEST, 'language_id': ZH,
             'created_at': f'2026-11-1{i}T00:00:00Z'}
            for i in range(5)
        ] + [{'id': 'old', 'user_id': USER, 'test_id': JA_TEST, 'language_id': JA,
              'created_at': '2026-10-01T00:00:00Z'}]
        attempts = dt_routes._attempted_tests(db, USER)
        assert len(attempts) == 6
        assert attempts[0]['created_at'] == '2026-11-14T00:00:00Z'
        assert {a['test_id'] for a in attempts} == {ZH_TEST, JA_TEST}

    def test_graded_work_in_another_language_is_not_all_done_here(self):
        """Every Chinese passage graded, nothing eligible in Japanese: Japanese is
        NO_PASSAGES (nothing to offer), not ALL_DONE (you finished everything)."""
        db = _TableDB(_tables(test_sentence_references=[]))
        while True:
            choice = _choose(db, ZH)
            if choice['kind'] == 'none':
                break
            _grade(db, _serve(db, choice))
        assert _choose(db, ZH) == {'kind': 'none', 'all_done': True}
        assert _choose(db, JA) == {'kind': 'none', 'all_done': False}

    def test_window_search_stops_at_the_first_batch_with_a_window(self, monkeypatch):
        """Sentences and references are read a batch of tests at a time and the
        search stops once a batch yields a window (latency of GET /next)."""
        monkeypatch.setattr(dt_routes, '_WINDOW_TEST_BATCH', 1)
        tables = _tables()
        tables['test_attempts'].append(
            {'id': 'a3', 'user_id': USER, 'test_id': UNTAKEN_JA_TEST, 'language_id': JA,
             'created_at': '2026-11-13T00:00:00Z'})
        tables['test_sentences'] += [
            {'id': 602, 'test_id': UNTAKEN_JA_TEST, 'idx': 2, 'l2_text': '三文目です。',
             'token_start': None, 'token_end': None, 'transcript_hash': 'hu'}]
        tables['test_sentence_references'].append(
            {'sentence_id': 602, 'l1_language_id': EN, 'l1_text': 'Third.', 'tightness': 0.9,
             'review_verdict': 'pass', 'is_active': True})
        db = _TableDB(tables)
        choice = _choose(db, JA)
        assert choice['kind'] == 'range'
        assert db.reads.count('test_sentences') == 1
        # Both tests still get used over successive calls.
        used = {choice['test_id']}
        _grade(db, _serve(db, choice))
        for _ in range(6):
            choice = _choose(db, JA)
            if choice['kind'] == 'none':
                break
            used.add(choice['test_id'])
            _grade(db, _serve(db, choice))
        assert used == {JA_TEST, UNTAKEN_JA_TEST}

    def test_selection_is_deterministic_for_a_given_state(self):
        a = _choose(_TableDB(_tables()), ZH)
        b = _choose(_TableDB(_tables()), ZH)
        assert a == b

    def test_rotation_key_varies_with_the_serve_count(self):
        keys = {dt_routes._rotation_key(USER, 7, salt) for salt in range(5)}
        assert len(keys) == 5
        assert dt_routes._rotation_key(USER, 7, 1) == dt_routes._rotation_key(USER, 7, 1)


class TestSentenceWindowQuality:

    def test_rejected_and_inactive_references_are_not_used(self):
        refs = _tables()['test_sentence_references']
        for r in refs:
            if r['sentence_id'] in (501, 503, 505):
                r['review_verdict'] = 'fail'
        db = _TableDB(_tables(test_sentence_references=refs))
        assert _choose(db, JA) == {'kind': 'none', 'all_done': False}

    def test_low_tightness_windows_are_skipped(self):
        refs = _tables()['test_sentence_references']
        for r in refs:
            if r['sentence_id'] < 600:
                r['tightness'] = 0.2  # below the Japanese floor (0.65)
        db = _TableDB(_tables(test_sentence_references=refs))
        assert _choose(db, JA) == {'kind': 'none', 'all_done': False}

    def test_references_must_be_in_the_learners_l1(self):
        refs = _tables()['test_sentence_references']
        for r in refs:
            r['l1_language_id'] = ZH
        db = _TableDB(_tables(test_sentence_references=refs))
        assert _choose(db, JA) == {'kind': 'none', 'all_done': False}

    def test_stale_sentence_rows_are_skipped(self):
        tests = _tables()['tests']
        for t in tests:
            if t['id'] == JA_TEST:
                t['transcript_hash'] = 'changed'
        db = _TableDB(_tables(tests=tests))
        assert _choose(db, JA) == {'kind': 'none', 'all_done': False}

    def test_a_window_never_straddles_a_stale_row(self):
        """One stale row in the middle breaks windows instead of being skipped
        over: (0, 2) would be refused by open_range_passage (SENTENCES_STALE)."""
        rows = _tables()['test_sentences']
        for r in rows:
            if r['id'] == 501:
                r['transcript_hash'] = 'old'
        db = _TableDB(_tables(test_sentences=rows))
        assert _choose(db, JA) == {'kind': 'range', 'test_id': JA_TEST, 'start': 2, 'end': 3}

    def test_a_window_never_straddles_a_missing_row(self):
        """A gap in idx breaks windows too: (0, 2) would be SENTENCES_MISSING."""
        rows = [r for r in _tables()['test_sentences'] if r['id'] != 501]
        db = _TableDB(_tables(test_sentences=rows))
        assert _choose(db, JA) == {'kind': 'range', 'test_id': JA_TEST, 'start': 2, 'end': 3}

    def test_inactive_test_is_skipped(self):
        tests = _tables()['tests']
        for t in tests:
            if t['id'] == JA_TEST:
                t['is_active'] = False
        db = _TableDB(_tables(tests=tests))
        assert _choose(db, JA) == {'kind': 'none', 'all_done': False}

    def test_window_materials_survive_a_capped_batch_read(self, monkeypatch):
        """A batch read that hits the PostgREST row cap is re-read test by test."""
        monkeypatch.setattr(dt_routes, '_POSTGREST_ROW_CAP', 3)
        db = _TableDB(_tables())
        tests = [{'id': JA_TEST, 'transcript_hash': 'hj'}, {'id': UNTAKEN_JA_TEST, 'transcript_hash': 'hu'}]
        materials = dt_routes._window_materials(db, tests, EN)
        rows, refs_ok, tightness = materials[JA_TEST]
        assert [r['idx'] for r in rows] == list(range(6))
        assert refs_ok == set(range(6)) and tightness[0] == 0.9
        assert [r['idx'] for r in materials[UNTAKEN_JA_TEST][0]] == [0, 1]

    def test_legacy_pool_first_then_sentence_windows(self):
        """A Chinese test with both legacy passages and sentence references: the
        legacy passages are served first, then the sentence windows."""
        tables = _tables()
        tables['test_sentences'] += [
            {'id': 700 + i, 'test_id': ZH_TEST, 'idx': i, 'l2_text': t, 'token_start': None,
             'token_end': None, 'transcript_hash': 'hz'}
            for i, t in enumerate(['我们去公园。', '天气很好。', '他喜欢看书。'])
        ]
        tables['test_sentence_references'] += [
            {'sentence_id': 700 + i, 'l1_language_id': EN, 'l1_text': t, 'tightness': 0.95,
             'review_verdict': 'rewritten', 'is_active': True}
            for i, t in enumerate(['We go to the park.', 'The weather is nice.', 'He likes reading.'])
        ]
        db = _TableDB(tables)
        kinds = []
        for _ in range(6):
            choice = _choose(db, ZH)
            if choice['kind'] == 'none':
                break
            kinds.append(choice['kind'])
            _grade(db, _serve(db, choice))
        assert kinds == ['passage', 'passage', 'range']


# ---------------------------------------------------------------------------
# Error cards follow the study language too
# ---------------------------------------------------------------------------

class TestErrorCardLanguage:

    def test_only_cards_of_the_study_language(self, monkeypatch):
        monkeypatch.setattr(dt_routes.dt_cards, 'generate_cards_for_queued_entries', lambda db, uid: None)
        monkeypatch.setattr(dt_routes, '_fetch_due_cards', lambda db, uid: [
            {'card_id': 11, 'card_type': 'cloze', 'subtype': 'a', 'prompt_payload': {}, 'state': 'new',
             'due_date': None},
            {'card_id': 12, 'card_type': 'cloze', 'subtype': 'b', 'prompt_payload': {}, 'state': 'new',
             'due_date': None},
        ])
        db = _TableDB({
            'dt_error_profile_entry': [
                {'id': 1, 'user_id': USER, 'l2_language_id': ZH},
                {'id': 2, 'user_id': USER, 'l2_language_id': JA},
            ],
            'dt_card': [
                {'id': 11, 'user_id': USER, 'profile_entry_id': 1},
                {'id': 12, 'user_id': USER, 'profile_entry_id': 2},
            ],
        })
        assert dt_routes._next_due_error_card(db, USER, JA)['card_id'] == 12
        assert dt_routes._next_due_error_card(db, USER, ZH)['card_id'] == 11
        assert dt_routes._next_due_error_card(db, USER, EN) is None


# ---------------------------------------------------------------------------
# Route: GET /next and the submit of a sentence-window passage
# ---------------------------------------------------------------------------

@pytest.fixture
def table_app(app, monkeypatch):
    db = _TableDB(_tables())
    app.supabase_service = db
    monkeypatch.setattr(dt_routes, '_should_serve_error_card', lambda: False)
    monkeypatch.setattr(DimensionService, 'get_language_code',
                        classmethod(lambda cls, lid: {1: 'zh', 2: 'en', 3: 'ja'}.get(lid)))

    def _no_active_rubric(db):
        raise RuntimeError("no active dt_rubric_version row")
    monkeypatch.setattr(dt_routes, 'get_active_rubric', _no_active_rubric)
    return db


def _body(resp):
    return json.loads(resp.data)


class TestNextRoute:

    def test_japanese_learner_gets_a_japanese_sentence_window(self, client, auth_headers, table_app):
        resp = client.get('/api/dual-translation/next?language_id=3', headers=auth_headers)
        assert resp.status_code == 200
        data = _body(resp)
        assert data['type'] == 'passage'
        assert data['source'] == 'sentence_refs'
        assert data['l1_text'] == 'It is sunny today. I went to the park.'
        assert 'l2_text' not in data
        passage = next(p for p in table_app.tables['dt_passage'] if p['id'] == data['passage_id'])
        assert passage['l2_language_id'] == JA
        assert (passage['sentence_start'], passage['sentence_end']) == (0, 1)
        sub = next(s for s in table_app.tables['dt_submission'] if s['id'] == data['submission_id'])
        assert sub['user_id'] == USER and sub['l1_language_id'] == EN

    def test_chinese_learner_gets_a_chinese_passage(self, client, auth_headers, table_app):
        resp = client.get('/api/dual-translation/next?language_id=1', headers=auth_headers)
        assert resp.status_code == 200
        data = _body(resp)
        assert data['source'] == 'passage'
        sub = next(s for s in table_app.tables['dt_submission'] if s['id'] == data['submission_id'])
        assert sub['passage_id'] in (1, 2)

    def test_no_language_falls_back_to_the_latest_attempt_language(self, client, auth_headers, table_app):
        # the Japanese attempt is the most recent one
        resp = client.get('/api/dual-translation/next', headers=auth_headers)
        assert resp.status_code == 200
        assert _body(resp)['source'] == 'sentence_refs'

    @pytest.mark.parametrize('raw', ['abc', '9', '-1'])
    def test_invalid_language_is_a_400(self, client, auth_headers, table_app, raw):
        resp = client.get(f'/api/dual-translation/next?language_id={raw}', headers=auth_headers)
        assert resp.status_code == 400

    def test_no_attempts_is_no_passages(self, client, auth_headers, table_app):
        table_app.tables['test_attempts'] = []
        resp = client.get('/api/dual-translation/next', headers=auth_headers)
        assert resp.status_code == 404
        assert _body(resp)['error_code'] == dt_routes.NO_PASSAGES

    def test_repeated_calls_after_grading_never_repeat_and_end_all_done(
        self, client, auth_headers, table_app,
    ):
        served = []
        for _ in range(6):
            resp = client.get('/api/dual-translation/next?language_id=1', headers=auth_headers)
            if resp.status_code == 404:
                assert _body(resp)['error_code'] == dt_routes.ALL_DONE
                break
            sub = next(s for s in table_app.tables['dt_submission']
                       if s['id'] == _body(resp)['submission_id'])
            served.append(sub['passage_id'])
            _grade(table_app, sub)
        assert sorted(served) == [1, 2]

    def test_window_submission_is_graded_like_any_other(self, client, auth_headers, table_app, monkeypatch):
        resp = client.get('/api/dual-translation/next?language_id=3', headers=auth_headers)
        data = _body(resp)
        seen = {}

        def _fake_grade(db, **kwargs):
            seen.update(kwargs)
            return {
                'scores': {'accuracy': 3}, 'overall_band': 3, 'diff': [], 'errors': [],
                'grader_trace': {'tier': 'tier1', 'tokens': {'in': 1, 'out': 1}},
            }
        monkeypatch.setattr(dt_routes, 'grade_submission', _fake_grade)
        monkeypatch.setattr(dt_routes, '_tokens_used_today', lambda db, uid: 0)
        monkeypatch.setattr(dt_routes.repair_hooks, 'after_grade',
                            lambda db, contract, **kw: contract)
        monkeypatch.setattr(dt_routes, 'credit_study_time', lambda *a, **k: None)

        resp = client.post(f"/api/dual-translation/{data['submission_id']}/submit",
                           headers=auth_headers, json={'reproduction': '今日は晴れです。公園に行った。'})

        assert resp.status_code == 200
        assert _body(resp)['overall_band'] == 3
        assert seen['gold_l2'] == '今日は晴れです。公園に行きました。'
        assert seen['l2_language_id'] == JA and seen['l1_language_id'] == EN
        assert [g['submission_id'] for g in table_app.tables['dt_grade']] == [data['submission_id']]
        # ...and that window is not served again.
        nxt = _body(client.get('/api/dual-translation/next?language_id=3', headers=auth_headers))
        nxt_passage = next(p for p in table_app.tables['dt_passage'] if p['id'] == nxt['passage_id'])
        assert nxt_passage['sentence_start'] >= 2

    def test_config_language_ids_are_the_accepted_set(self):
        assert Config.VALID_LANGUAGE_IDS == {1, 2, 3}
