"""TASK-1022 (ADR-049): the route readers and the reference-set script read
exercise content through the store.

Appendix A rows 10-12: the server-side ``cloze_typed`` re-grade on
``POST /api/practice/attempt`` (``_grade_typed_if_needed``), the admin word
preview (``preview_word``) and the offline reference-set snapshot
(``scripts/build_exercise_gen_reference_set.fetch_exercise_snapshot``), each in
``db`` and ``storage`` mode. ``store.read_mode`` / ``store.hydrate`` are
monkeypatched (the storage reader is TASK-1010); no network, no Supabase.
"""

from __future__ import annotations

import copy
from types import SimpleNamespace

import pytest

import routes.practice as practice_routes
import routes.vocab_admin as vocab_admin_routes
from scripts import build_exercise_gen_reference_set as refset
from services.exercise_content import store

LANG_EN, LANG_JA = 2, 3


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------

class _Query:
    """Builder stand-in: eq / is_ / not_.is_ filters, order, limit, single;
    ``exercises`` rows are projected onto the selected columns (so storage
    mode really has no content until hydrated); every select is recorded."""

    def __init__(self, db, table):
        self.db, self.table = db, table
        self.columns, self.filters, self._single, self._negate = None, [], False, False

    def select(self, columns, **_kw):
        self.columns = columns
        self.db.selects.append((self.table, columns))
        return self

    def eq(self, col, val):
        self.filters.append(lambda r, c=col, v=val: r.get(c) == v)
        return self

    @property
    def not_(self):
        self._negate = True
        return self

    def is_(self, col, val):
        negate, self._negate = self._negate, False
        want_null = val == 'null'
        self.filters.append(lambda r, c=col: (r.get(c) is None) == want_null if not negate
                            else (r.get(c) is None) != want_null)
        return self

    def order(self, col, **_kw):
        self._order = col
        return self

    def limit(self, _n):
        return self

    def single(self):
        self._single = True
        return self

    def execute(self):
        if self.db.fail:
            raise RuntimeError(self.db.fail)
        rows = [copy.deepcopy(r) for r in self.db.tables.get(self.table, []) if all(f(r) for f in self.filters)]
        if self.table == 'exercises' and self.columns:
            wanted = [c.strip() for c in self.columns.split(',')]
            rows = [{c: r[c] for c in wanted if c in r} for r in rows]
        if getattr(self, '_order', None):
            rows.sort(key=lambda r: (r.get(self._order) is None, r.get(self._order)))
        if self._single:
            return SimpleNamespace(data=rows[0] if rows else None)
        return SimpleNamespace(data=rows)


class FakeDB:
    def __init__(self, tables, fail=None):
        self.tables, self.fail, self.selects = tables, fail, []

    def table(self, name):
        return _Query(self, name)

    def exercise_selects(self):
        return [cols for table, cols in self.selects if table == 'exercises']


class FakeHydrate:
    """``store.hydrate`` stand-in (ADR-049 section 9): content from
    ``contents[item[id_key]]``; anything else is missing (dropped, or None
    with drop_missing=False). Records every call."""

    def __init__(self, contents, raises=None):
        self.contents, self.raises, self.calls = contents, raises, []

    def __call__(self, items, *, language_id=None, id_key='id', sense_key='word_sense_id',
                 db=None, drop_missing=True, max_senses=None, deadline_s=None):
        self.calls.append({'ids': [i.get(id_key) for i in items], 'language_id': language_id,
                           'db': db, 'drop_missing': drop_missing,
                           'had_content': [i.get('content') is not None for i in items]})
        if self.raises is not None:
            raise self.raises
        keep = []
        for item in items:
            if item.get('content') is None:
                if item.get(id_key) in self.contents:
                    item['content'] = copy.deepcopy(self.contents[item[id_key]])
                elif drop_missing:
                    continue
                else:
                    item['content'] = None
            keep.append(item)
        items[:] = keep
        return store.HydrationReport(mode='storage')


class RecordingHydrate:
    """Wraps the real ``store.hydrate`` (db mode: no I/O, no mutation)."""

    def __init__(self):
        self.calls, self._real = [], store.hydrate

    def __call__(self, items, **kw):
        self.calls.append({'ids': [i.get('id') for i in items], **kw})
        return self._real(items, **kw)


@pytest.fixture
def storage_mode(monkeypatch):
    monkeypatch.setattr(store, 'read_mode', lambda: 'storage')


# ---------------------------------------------------------------------------
# routes/practice.py::_grade_typed_if_needed
# ---------------------------------------------------------------------------

TYPED_CONTENT = {'sentence_with_blank': 'I am __ home.', 'answer': {'accepted': ['walking']},
                 'target_word': 'walk'}
TYPED_ROWS = [
    {'id': 'ex-typed', 'exercise_type': 'cloze_typed', 'language_id': LANG_EN, 'word_sense_id': 7,
     'content_version': 4, 'content': TYPED_CONTENT},
    {'id': 'ex-mc', 'exercise_type': 'cloze_completion', 'language_id': LANG_EN, 'word_sense_id': 7,
     'content_version': 4, 'content': {'options': ['a']}},
]
TYPED_DATA = {'language_id': LANG_EN, 'user_response': {'typed': 'Walking'}}


class TestTypedRegrade:

    def _db(self, monkeypatch, fail=None):
        db = FakeDB({'exercises': TYPED_ROWS}, fail=fail)
        monkeypatch.setattr(practice_routes, 'get_db', lambda: db)
        return db

    def test_db_mode_select_and_grade(self, monkeypatch):
        db = self._db(monkeypatch)
        rec = RecordingHydrate()
        monkeypatch.setattr(store, 'hydrate', rec)
        out = practice_routes._grade_typed_if_needed('ex-typed', TYPED_DATA)
        # db mode: today's select string byte-for-byte (review finding 2026-11-17).
        assert db.exercise_selects() == ['exercise_type, content, language_id']
        assert out['is_correct'] is True and out['graded_by'] == 'server'
        assert rec.calls == [{'ids': ['ex-typed'], 'language_id': LANG_EN, 'drop_missing': False, 'db': db}]

    def test_storage_mode_hydrates_the_row(self, monkeypatch, storage_mode):
        db = self._db(monkeypatch)
        fake = FakeHydrate({'ex-typed': TYPED_CONTENT})
        monkeypatch.setattr(store, 'hydrate', fake)
        out = practice_routes._grade_typed_if_needed('ex-typed', TYPED_DATA)
        assert db.exercise_selects() == ['exercise_type, content_version, language_id, word_sense_id']
        assert fake.calls == [{'ids': ['ex-typed'], 'language_id': LANG_EN, 'db': db,
                               'drop_missing': False, 'had_content': [False]}]
        assert out['is_correct'] is True and out['accepted'] == ['walking']
        wrong = practice_routes._grade_typed_if_needed(
            'ex-typed', {'language_id': LANG_EN, 'user_response': {'typed': 'running'}})
        assert wrong['is_correct'] is False

    def test_storage_miss_fails_open(self, monkeypatch, storage_mode):
        self._db(monkeypatch)
        monkeypatch.setattr(store, 'hydrate', FakeHydrate({}))
        graded = []
        monkeypatch.setattr('services.vocabulary_ladder.deterministic.cloze_typed.grade',
                            lambda *a: graded.append(a))
        assert practice_routes._grade_typed_if_needed('ex-typed', TYPED_DATA) is None
        assert graded == []

    def test_hydrate_error_fails_open(self, monkeypatch, storage_mode):
        self._db(monkeypatch)
        monkeypatch.setattr(store, 'hydrate', FakeHydrate({}, raises=ValueError('bad language')))
        assert practice_routes._grade_typed_if_needed('ex-typed', TYPED_DATA) is None

    @pytest.mark.parametrize('mode', ['db', 'storage'])
    def test_other_types_and_untyped_answers_never_hydrate(self, monkeypatch, mode):
        monkeypatch.setattr(store, 'read_mode', lambda: mode)
        db = self._db(monkeypatch)
        fake = FakeHydrate({})
        monkeypatch.setattr(store, 'hydrate', fake)
        assert practice_routes._grade_typed_if_needed('ex-mc', TYPED_DATA) is None
        assert practice_routes._grade_typed_if_needed('missing-id', TYPED_DATA) is None
        assert practice_routes._grade_typed_if_needed('ex-typed', {'user_response': {'choice': 'a'}}) is None
        assert fake.calls == []
        assert len(db.exercise_selects()) == 2        # the untyped answer made no query

    def test_lookup_failure_still_fails_open(self, monkeypatch):
        self._db(monkeypatch, fail='connection reset')
        assert practice_routes._grade_typed_if_needed('ex-typed', TYPED_DATA) is None


# ---------------------------------------------------------------------------
# routes/vocab_admin.py::preview_word
# ---------------------------------------------------------------------------

JUMBLED_STORED = {'original_sentence': 'The cat sleeps.'}
PREVIEW_CONTENT = {
    'pv-1': {'options': ['cat', 'dog'], 'correct_answer': 'cat', 'sentence_with_blank': 'A __.'},
    'pv-2': JUMBLED_STORED,
}
PREVIEW_ROWS = [
    {'id': 'pv-1', 'exercise_type': 'cloze_completion', 'complexity_tier': 'T2', 'ladder_level': 3,
     'word_sense_id': 5, 'language_id': LANG_EN, 'is_active': True, 'content_version': 9,
     'content': PREVIEW_CONTENT['pv-1']},
    {'id': 'pv-2', 'exercise_type': 'jumbled_sentence', 'complexity_tier': 'T2', 'ladder_level': 5,
     'word_sense_id': 5, 'language_id': LANG_EN, 'is_active': True, 'content_version': 9,
     'content': JUMBLED_STORED},
    {'id': 'pv-x', 'exercise_type': 'cloze_completion', 'complexity_tier': 'T2', 'ladder_level': None,
     'word_sense_id': 5, 'language_id': LANG_EN, 'is_active': True, 'content_version': 9,
     'content': {'not': 'on the ladder'}},
]
PREVIEW_URL = f'/api/admin/vocab/word/5/preview?language_id={LANG_EN}'


class TestAdminPreview:

    def _wire(self, monkeypatch):
        db = FakeDB({
            'dim_word_senses': [{'id': 5, 'definition': 'a cat', 'pronunciation': None, 'ipa_pronunciation': None,
                                 'morphological_forms': None,
                                 'dim_vocabulary': {'lemma': 'cat', 'semantic_class': '', 'part_of_speech': 'noun',
                                                    'level_tag': 'T2'}}],
            'word_assets': [],
            'exercises': PREVIEW_ROWS,
        })
        monkeypatch.setattr(vocab_admin_routes, 'get_db', lambda: db)
        monkeypatch.setattr('middleware.auth._user_has_tier', lambda *_a: True)
        prepared = []
        monkeypatch.setattr('services.exercise_generation.language_processor.prepare_jumbled_content',
                            lambda content, lang: prepared.append(copy.deepcopy(content))
                            or {**content, 'chunks': ['The cat', 'sleeps.'], 'correct_ordering': [0, 1]})
        return db, prepared

    def test_requires_admin(self, client, auth_headers, monkeypatch):
        monkeypatch.setattr('middleware.auth._user_has_tier', lambda *_a: False)
        assert client.get(PREVIEW_URL, headers=auth_headers).status_code == 403

    def test_db_mode(self, client, auth_headers, monkeypatch):
        db, prepared = self._wire(monkeypatch)
        rec = RecordingHydrate()
        monkeypatch.setattr(store, 'hydrate', rec)
        resp = client.get(PREVIEW_URL, headers=auth_headers)
        assert resp.status_code == 200
        exercises = resp.get_json()['exercises']
        assert db.exercise_selects() == ['id, exercise_type, content, complexity_tier, ladder_level, word_sense_id']
        assert [e['id'] for e in exercises] == ['pv-1', 'pv-2']
        assert all(e['word_sense_id'] == 5 for e in exercises)
        assert exercises[0]['content'] == PREVIEW_CONTENT['pv-1']
        assert exercises[1]['content']['chunks'] == ['The cat', 'sleeps.']
        assert prepared == [JUMBLED_STORED]
        assert rec.calls == [{'ids': ['pv-1', 'pv-2'], 'language_id': LANG_EN, 'db': db}]

    def test_storage_mode_hydrates_before_the_jumbled_preparation(self, client, auth_headers, monkeypatch,
                                                                   storage_mode):
        db, prepared = self._wire(monkeypatch)
        fake = FakeHydrate(PREVIEW_CONTENT)
        monkeypatch.setattr(store, 'hydrate', fake)
        resp = client.get(PREVIEW_URL, headers=auth_headers)
        assert resp.status_code == 200
        exercises = resp.get_json()['exercises']
        assert db.exercise_selects() == [
            'id, exercise_type, content_version, complexity_tier, ladder_level, word_sense_id']
        assert len(fake.calls) == 1
        assert fake.calls[0]['ids'] == ['pv-1', 'pv-2'] and fake.calls[0]['language_id'] == LANG_EN
        assert fake.calls[0]['had_content'] == [False, False] and fake.calls[0]['db'] is db
        assert prepared == [JUMBLED_STORED]          # prep saw the hydrated content
        assert exercises[0]['content'] == PREVIEW_CONTENT['pv-1'] and exercises[0]['word_sense_id'] == 5
        assert exercises[1]['content']['correct_ordering'] == [0, 1]

    def test_storage_miss_drops_the_exercise(self, client, auth_headers, monkeypatch, storage_mode):
        self._wire(monkeypatch)
        monkeypatch.setattr(store, 'hydrate', FakeHydrate({'pv-1': PREVIEW_CONTENT['pv-1']}))
        exercises = client.get(PREVIEW_URL, headers=auth_headers).get_json()['exercises']
        assert [e['id'] for e in exercises] == ['pv-1']


# ---------------------------------------------------------------------------
# scripts/build_exercise_gen_reference_set.py::fetch_exercise_snapshot
# ---------------------------------------------------------------------------

SNAP_CONTENT = {'s-1': {'word': 'neko'}, 's-2': {'sentence_with_blank': '__ ga iru'}}
SNAP_ROWS = [
    {'id': 's-2', 'word_sense_id': 9, 'language_id': LANG_JA, 'exercise_type': 'cloze_completion',
     'ladder_level': 3, 'complexity_tier': 'T3', 'tags': {'variant': 'B', 'judge': 'pass'},
     'content_version': 2, 'content': SNAP_CONTENT['s-2']},
    {'id': 's-1', 'word_sense_id': 9, 'language_id': LANG_JA, 'exercise_type': 'definition_match',
     'ladder_level': 1, 'complexity_tier': 'T3', 'tags': None,
     'content_version': 2, 'content': SNAP_CONTENT['s-1']},
    {'id': 's-other', 'word_sense_id': 10, 'language_id': LANG_JA, 'exercise_type': 'definition_match',
     'ladder_level': 1, 'complexity_tier': 'T1', 'tags': {}, 'content_version': 0, 'content': {'word': 'x'}},
]
SNAP_EXPECTED = [
    {'type': 'definition_match', 'level': 1, 'variant': None, 'complexity_tier': 'T3',
     'payload': SNAP_CONTENT['s-1']},
    {'type': 'cloze_completion', 'level': 3, 'variant': 'B', 'complexity_tier': 'T3',
     'payload': SNAP_CONTENT['s-2']},
]
SNAP_TEMPLATE = 'id, word_sense_id, language_id, exercise_type, ladder_level, complexity_tier, tags, {content}'


class TestReferenceSetSnapshot:

    def test_db_mode_output_unchanged(self, monkeypatch):
        rec = RecordingHydrate()
        monkeypatch.setattr(store, 'hydrate', rec)
        db = FakeDB({'exercises': SNAP_ROWS})
        assert refset.fetch_exercise_snapshot(db, 9) == SNAP_EXPECTED
        # db mode: today's select string byte-for-byte (review finding 2026-11-17).
        assert db.exercise_selects() == ['exercise_type,ladder_level,complexity_tier,tags,content']
        assert len(rec.calls) == 1 and rec.calls[0]['db'] is db

    def test_storage_mode_hydrates_with_each_rows_language(self, monkeypatch, storage_mode):
        fake = FakeHydrate(SNAP_CONTENT)
        monkeypatch.setattr(store, 'hydrate', fake)
        db = FakeDB({'exercises': SNAP_ROWS})
        assert refset.fetch_exercise_snapshot(db, 9) == SNAP_EXPECTED
        assert db.exercise_selects() == [SNAP_TEMPLATE.replace('{content}', 'content_version')]
        assert len(fake.calls) == 1
        assert fake.calls[0]['language_id'] is None and fake.calls[0]['db'] is db
        assert fake.calls[0]['had_content'] == [False, False]

    def test_storage_miss_leaves_the_exercise_out(self, monkeypatch, storage_mode):
        monkeypatch.setattr(store, 'hydrate', FakeHydrate({'s-2': SNAP_CONTENT['s-2']}))
        assert refset.fetch_exercise_snapshot(FakeDB({'exercises': SNAP_ROWS}), 9) == SNAP_EXPECTED[1:]
