"""Unit tests for services/word_list_import/upload_handler.py.

Step 3 of wiki/tasklist/word-list-import.plan.md. `process_word_list_upload`
sits between three already-tested building blocks
(`resolve_or_create_sense`, `VocabAssetPipeline`, `LadderExerciseRenderer`)
and a new `user_word_watchlist` table, so every collaborator is mocked here
— this file pins the *orchestration*, not their internals:

  * a brand-new word runs the full resolve -> generate -> render ->
    watchlist-insert pipeline;
  * a sense that already has exercises skips generate/render but still
    inserts a watchlist row (ladder_exercises_generated=True);
  * a (user, sense) pair that is already watchlisted skips the duplicate
    insert;
  * one word's resolver failure is recorded as an error and does not stop
    the rest of the batch from succeeding.

No real database, no LLM calls, no network: a minimal in-memory fake stands
in for the Supabase query-builder surface (same shape as
tests/test_word_resolver.py's FakeDB/_FakeQuery), and the three collaborators
are monkeypatched directly onto the module under test.
"""

import pytest

import services.word_list_import.upload_handler as uh
from services.exercise_generation.judges.base import JudgeUnavailable

# ---------------------------------------------------------------------------
# Fakes — minimal in-memory stand-in for the Supabase query-builder surface
# ---------------------------------------------------------------------------


class _Resp:
    def __init__(self, data):
        self.data = data


class _FakeQuery:
    """One chained Supabase query-builder call, backed by an in-memory list
    of row dicts shared with the owning FakeDB table."""

    def __init__(self, rows, next_id):
        self._rows = rows
        self._next_id = next_id  # single-item list used as a mutable box
        self._filters = []
        self._limit = None
        self._op = None

    def select(self, *_a, **_kw):
        return self

    def eq(self, col, val):
        self._filters.append((col, val))
        return self

    def limit(self, n):
        self._limit = n
        return self

    def insert(self, payload):
        self._op = ('insert', payload)
        return self

    def _match(self, row):
        return all(row.get(col) == val for col, val in self._filters)

    def execute(self):
        if self._op:
            kind, payload = self._op
            if kind == 'insert':
                items = payload if isinstance(payload, list) else [payload]
                written = []
                for item in items:
                    row = dict(item)
                    row['id'] = self._next_id[0]
                    self._next_id[0] += 1
                    self._rows.append(row)
                    written.append(row)
                return _Resp(written)

        matched = [r for r in self._rows if self._match(r)]
        if self._limit is not None:
            matched = matched[: self._limit]
        return _Resp(matched)


class FakeDB:
    """Minimal in-memory stand-in for the Supabase client surface used by
    _sense_has_ladder_exercises, _watchlist_row_exists and the watchlist
    insert."""

    def __init__(self):
        self._tables: dict = {}
        self._next_ids: dict = {}

    def seed(self, table, rows):
        self._tables[table] = [dict(r) for r in rows]
        self._next_ids[table] = [max([r.get('id', 0) for r in rows], default=0) + 1]

    def table(self, name):
        rows = self._tables.setdefault(name, [])
        next_id = self._next_ids.setdefault(name, [1])
        return _FakeQuery(rows, next_id)


class _LangConfig:
    def __init__(self, id_):
        self.id = id_


class FakeDBClient:
    """Duck-typed TestDatabaseClient: `.client`, `.get_language_config_by_code`
    — the only surface process_word_list_upload needs directly (it forwards
    the rest to the mocked resolve_or_create_sense)."""

    def __init__(self, db, language_id=2, language_code='en', configured=True):
        self.client = db
        self._language_id = language_id
        self._language_code = language_code
        self._configured = configured

    def get_language_config_by_code(self, code):
        if not self._configured or code != self._language_code:
            return None
        return _LangConfig(self._language_id)


# ---------------------------------------------------------------------------
# Fixtures — mock the three collaborators named in the task
# ---------------------------------------------------------------------------


@pytest.fixture
def resolver(monkeypatch):
    """Scriptable resolve_or_create_sense: word -> sense_id, or word -> raise."""
    sense_ids: dict = {}
    raises: dict = {}
    calls: list = []

    def fake_resolve(word, language_code, db_client, openai_client):
        calls.append(word)
        if word in raises:
            raise raises[word]
        return sense_ids[word]

    monkeypatch.setattr(uh, 'resolve_or_create_sense', fake_resolve)

    class _Handle:
        def set_sense(self, word, sense_id):
            sense_ids[word] = sense_id

        def set_raises(self, word, exc):
            raises[word] = exc

        @property
        def calls(self):
            return calls

    return _Handle()


@pytest.fixture
def pipeline(monkeypatch):
    """Scriptable VocabAssetPipeline.generate_for_sense: sense_id -> result dict."""
    results: dict = {}
    raises: dict = {}
    calls: list = []

    class _FakePipeline:
        def __init__(self, _db=None):
            pass

        def generate_for_sense(self, sense_id, language_id):
            calls.append((sense_id, language_id))
            if sense_id in raises:
                raise raises[sense_id]
            return results.get(sense_id, {'status': 'success', 'errors': []})

    monkeypatch.setattr(uh, 'VocabAssetPipeline', _FakePipeline)

    class _Handle:
        def set_result(self, sense_id, result):
            results[sense_id] = result

        def set_raises(self, sense_id, exc):
            raises[sense_id] = exc

        @property
        def calls(self):
            return calls

    return _Handle()


@pytest.fixture
def renderer(monkeypatch):
    """Scriptable LadderExerciseRenderer.render_all: sense_id -> [exercise_ids]."""
    exercise_ids: dict = {}
    raises: dict = {}
    calls: list = []

    class _FakeRenderer:
        def __init__(self, _db=None):
            pass

        def render_all(self, sense_id, language_id):
            calls.append((sense_id, language_id))
            if sense_id in raises:
                raise raises[sense_id]
            return exercise_ids.get(sense_id, ['ex-1', 'ex-2'])

    monkeypatch.setattr(uh, 'LadderExerciseRenderer', _FakeRenderer)

    class _Handle:
        def set_ids(self, sense_id, ids):
            exercise_ids[sense_id] = ids

        def set_raises(self, sense_id, exc):
            raises[sense_id] = exc

        @property
        def calls(self):
            return calls

    return _Handle()


# ---------------------------------------------------------------------------
# Brand-new word — full pipeline runs
# ---------------------------------------------------------------------------


def test_brand_new_word_runs_full_pipeline(resolver, pipeline, renderer):
    resolver.set_sense('run', 99)
    db = FakeDB()
    db_client = FakeDBClient(db)

    out = uh.process_word_list_upload('user-1', ['run'], 'en', db_client, None)

    assert len(pipeline.calls) == 1
    assert pipeline.calls[0] == (99, 2)
    assert len(renderer.calls) == 1
    assert renderer.calls[0] == (99, 2)

    result = out['results'][0]
    assert result == {
        'word': 'run', 'sense_id': 99, 'ladder_status': 'generated',
        'watchlist_status': 'inserted', 'error': None,
    }

    watchlist_rows = db._tables['user_word_watchlist']
    assert len(watchlist_rows) == 1
    row = watchlist_rows[0]
    assert row['user_id'] == 'user-1'
    assert row['sense_id'] == 99
    assert row['language_id'] == 2
    assert row['ladder_exercises_generated'] is True
    assert row['upload_batch_id'] == out['upload_batch_id']


def test_upload_batch_id_is_shared_across_words_in_one_call(resolver, pipeline, renderer):
    resolver.set_sense('run', 1)
    resolver.set_sense('walk', 2)
    db = FakeDB()
    db_client = FakeDBClient(db)

    out = uh.process_word_list_upload('user-1', ['run', 'walk'], 'en', db_client, None)

    rows = db._tables['user_word_watchlist']
    assert len(rows) == 2
    assert rows[0]['upload_batch_id'] == rows[1]['upload_batch_id']
    assert rows[0]['upload_batch_id'] == out['upload_batch_id']


# ---------------------------------------------------------------------------
# Sense already has ladder exercises — generation/render skipped
# ---------------------------------------------------------------------------


def test_sense_with_existing_exercises_skips_generation(resolver, pipeline, renderer):
    resolver.set_sense('run', 99)
    db = FakeDB()
    db.seed('exercises', [{'id': 1, 'word_sense_id': 99}])
    db_client = FakeDBClient(db)

    out = uh.process_word_list_upload('user-1', ['run'], 'en', db_client, None)

    assert pipeline.calls == []
    assert renderer.calls == []

    result = out['results'][0]
    assert result['ladder_status'] == 'already_existed'
    assert result['watchlist_status'] == 'inserted'

    row = db._tables['user_word_watchlist'][0]
    assert row['ladder_exercises_generated'] is True


# ---------------------------------------------------------------------------
# Watchlist row already exists for (user, sense) — duplicate insert skipped
# ---------------------------------------------------------------------------


def test_existing_watchlist_row_skips_duplicate_insert(resolver, pipeline, renderer):
    resolver.set_sense('run', 99)
    db = FakeDB()
    db.seed('user_word_watchlist', [
        {'id': 1, 'user_id': 'user-1', 'sense_id': 99, 'language_id': 2,
         'upload_batch_id': 'prior-batch', 'ladder_exercises_generated': True},
    ])
    db_client = FakeDBClient(db)

    out = uh.process_word_list_upload('user-1', ['run'], 'en', db_client, None)

    # Ladder generation still runs (this call found no exercises yet in the
    # fake `exercises` table) — only the watchlist insert is deduplicated.
    assert len(pipeline.calls) == 1

    result = out['results'][0]
    assert result['watchlist_status'] == 'already_watched'

    rows = db._tables['user_word_watchlist']
    assert len(rows) == 1  # nothing new inserted
    assert rows[0]['id'] == 1


def test_watchlist_dedup_is_scoped_to_user_and_sense(resolver, pipeline, renderer):
    """A different user (or a different sense) is NOT treated as a duplicate."""
    resolver.set_sense('run', 99)
    db = FakeDB()
    db.seed('user_word_watchlist', [
        {'id': 1, 'user_id': 'other-user', 'sense_id': 99, 'language_id': 2,
         'upload_batch_id': 'prior-batch', 'ladder_exercises_generated': True},
    ])
    db_client = FakeDBClient(db)

    out = uh.process_word_list_upload('user-1', ['run'], 'en', db_client, None)

    assert out['results'][0]['watchlist_status'] == 'inserted'
    assert len(db._tables['user_word_watchlist']) == 2


# ---------------------------------------------------------------------------
# One word errors, others still succeed
# ---------------------------------------------------------------------------


def test_one_word_resolution_error_does_not_abort_the_batch(resolver, pipeline, renderer):
    resolver.set_sense('run', 1)
    resolver.set_raises('xyzzy', RuntimeError('sense generation failed'))
    resolver.set_sense('walk', 2)
    db = FakeDB()
    db_client = FakeDBClient(db)

    out = uh.process_word_list_upload(
        'user-1', ['run', 'xyzzy', 'walk'], 'en', db_client, None,
    )

    results = out['results']
    assert len(results) == 3

    assert results[0]['word'] == 'run'
    assert results[0]['sense_id'] == 1
    assert results[0]['error'] is None

    assert results[1]['word'] == 'xyzzy'
    assert results[1]['sense_id'] is None
    assert results[1]['ladder_status'] is None
    assert results[1]['watchlist_status'] is None
    assert 'sense generation failed' in results[1]['error']

    assert results[2]['word'] == 'walk'
    assert results[2]['sense_id'] == 2
    assert results[2]['error'] is None

    # Only the two successfully-resolved words got watchlist rows.
    assert len(db._tables['user_word_watchlist']) == 2
    # The failing word never reached the pipeline/renderer.
    assert [c[0] for c in pipeline.calls] == [1, 2]
    assert [c[0] for c in renderer.calls] == [1, 2]


def test_asset_generation_failure_is_recorded_as_error_and_batch_continues(
    resolver, pipeline, renderer,
):
    resolver.set_sense('run', 1)
    resolver.set_sense('walk', 2)
    pipeline.set_result(1, {'status': 'failed', 'errors': ['Prompt 1 generation failed']})
    db = FakeDB()
    db_client = FakeDBClient(db)

    out = uh.process_word_list_upload('user-1', ['run', 'walk'], 'en', db_client, None)

    results = out['results']
    assert results[0]['ladder_status'] == 'error'
    assert 'Prompt 1 generation failed' in results[0]['error']
    # render_all must not be called when generation failed outright.
    assert renderer.calls == [(2, 2)]

    # The failing word still gets a watchlist row, but flagged as not-generated.
    row0 = next(r for r in db._tables['user_word_watchlist'] if r['sense_id'] == 1)
    assert row0['ladder_exercises_generated'] is False

    # The second word's pipeline still ran and succeeded normally.
    assert results[1]['ladder_status'] == 'generated'


def test_empty_render_result_is_recorded_as_error(resolver, pipeline, renderer):
    resolver.set_sense('run', 1)
    renderer.set_ids(1, [])
    db = FakeDB()
    db_client = FakeDBClient(db)

    out = uh.process_word_list_upload('user-1', ['run'], 'en', db_client, None)

    result = out['results'][0]
    assert result['ladder_status'] == 'error'
    assert 'no exercises' in result['error']
    row = db._tables['user_word_watchlist'][0]
    assert row['ladder_exercises_generated'] is False


def test_judge_unavailable_propagates_instead_of_being_swallowed(
    resolver, pipeline, renderer,
):
    """A systemic judge outage aborts the call rather than being recorded as
    a per-word error — matches VocabAssetPipeline.generate_batch's own
    fail-closed convention for the same exception."""
    resolver.set_sense('run', 1)
    pipeline.set_raises(1, JudgeUnavailable('ladder_l1_distractor_judge: dead slug'))
    db = FakeDB()
    db_client = FakeDBClient(db)

    with pytest.raises(JudgeUnavailable):
        uh.process_word_list_upload('user-1', ['run'], 'en', db_client, None)


# ---------------------------------------------------------------------------
# Unconfigured language — every word reported as an error, nothing written
# ---------------------------------------------------------------------------


def test_unconfigured_language_errors_every_word_without_touching_db(
    resolver, pipeline, renderer,
):
    db = FakeDB()
    db_client = FakeDBClient(db, configured=False)

    out = uh.process_word_list_upload(
        'user-1', ['run', 'walk'], 'zz', db_client, None,
    )

    assert len(out['results']) == 2
    for result in out['results']:
        assert result['sense_id'] is None
        assert 'zz' in result['error']
    assert resolver.calls == []
    assert pipeline.calls == []
    assert renderer.calls == []
    assert db._tables.get('user_word_watchlist', []) == []
