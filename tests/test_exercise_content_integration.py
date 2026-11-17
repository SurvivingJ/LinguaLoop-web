"""TASK-993 (ADR-047): the exercise-content store end to end, offline.

The real store, reader, writer, shadow comparer, backfill and sweep run
together over ``FakeContentDB`` (the ``exercises`` table and the ADR-047 §8
RPCs, tests/exercise_content_fakes.py) and an ``InMemoryBackend``. Nothing
here touches the network: every non-db mode runs with
``store.set_backend(InMemoryBackend())`` installed, which is also what lets a
non-db mode resolve without Supabase credentials.

Scenarios (wiki/tasklist/exercise-content-storage.tasks.md, TASK-993):

1. ``WRITE=dual``: ``render_all`` on a new sense writes one file; the rows sit
   at that version; the column content equals the file.
2. Backfill export over legacy version-0 rows writes v0 files; ``--verify``
   passes.
3. ``queue_drain`` scoped regen (level 4) in dual mode: a new version; the other
   levels' content is byte-identical; the sweep (grace 0) deletes exactly the
   superseded file.
4. / 8. For each flag combination (db/db, shadow/dual, storage/dual): a sense
   is written through ``store.write_sense`` and served through ``get_session``,
   ``get_extra_round`` (fake ``get_practice_session`` / ``get_review_ahead_items``
   that honour ``p_include_content``), the prestudy payload and on-demand
   endpoint, and the speed round. Every payload equals the ``db``-mode payload
   on the same data, and ``db`` mode issues exactly the pre-ADR-047 calls.
5. ``SOURCE=shadow`` with one tampered file: exactly one ``content_diff``
   WARNING; the payload equals ``db`` mode.
6. Two threads updating different exercises of one sense: the final file holds
   both edits.
7. A missing file in ``storage``: fallback on, served from the column with a
   WARNING; fallback off, the item is dropped and an emptied session says
   ``content_unavailable``; after the column drop the fallback switches off.
"""

from __future__ import annotations

import copy
import dataclasses
import json
import logging
import random
import threading
import uuid
from datetime import datetime, timedelta, timezone

import pytest

from config import Config
from scripts import backfill_exercise_content as bf
from scripts import sweep_exercise_content as sweep
from services import intro_drill, prestudy
from services.exercise_content import shadow, store
from services.practice import session_assembly
from services.practice_session_service import PracticeSessionService
from services.vocabulary_ladder import queue_drain as qd
from services.vocabulary_ladder.exercise_renderer import LadderExerciseRenderer
from services.vocabulary_ladder.speed_round import SpeedRoundComposer
from tests.exercise_content_fakes import FakeContentDB, InMemoryBackend

ZH = 1
USER = 'user-1'
NOW = datetime(2026, 11, 17, 12, 0, tzinfo=timezone.utc)

# The flag combinations TASK-993 runs: (EXERCISE_CONTENT_SOURCE, EXERCISE_CONTENT_WRITE).
COMBOS = [('db', 'db'), ('shadow', 'dual'), ('storage', 'dual')]

# Senses of the serving fixture.
SESSION_SENSES = (101, 102)      # get_practice_session items
FOLLOWUP_SENSE = 103             # prestudy next-day review (injected follow-up)
AHEAD_SENSE = 104                # get_review_ahead_items
SPEED_SENSES = tuple(range(401, 413))   # 12 mastered senses, one L1 row each

# Pre-ADR-047 calls (c3cb106 and before), which db mode must keep issuing.
TODAYS_SESSION_PARAMS = {'p_user_id', 'p_language_id', 'p_mode', 'p_target_minutes',
                         'p_user_theta'}
TODAYS_AHEAD_PARAMS = {'p_user_id', 'p_language_id', 'p_limit', 'p_exclude_recent_minutes',
                       'p_exclude_sense_ids'}
TODAYS_EXERCISE_SELECTS = {
    'id, word_sense_id, exercise_type, content, ladder_level',          # follow-ups, prestudy
    'id, exercise_type, content, ladder_level, word_sense_id, complexity_tier',   # speed round
    'word_sense_id',                                                     # senses_with_exercises
}


# ---------------------------------------------------------------------------
# Fixture data
# ---------------------------------------------------------------------------

def eid(n: int) -> str:
    return str(uuid.UUID(int=n))


def definition(word: str, hant: str) -> dict:
    return {'word': word, 'options': ['this', 'that', 'which'], 'correct_definition': 'this',
            'pronunciation': 'zhè ge', 'sentence': f'{word}很好',
            'hant': {'word': hant, 'options': ['this', 'that', 'which'],
                     'correct_definition': 'this', 'pronunciation': 'zhè ge',
                     'sentence': f'{hant}很好'}}


def cloze(n: int) -> dict:
    return {'sentence_with_blank': '我___去', 'options': ['要', '会', '能'],
            'correct_answer': '要', 'explanation': f'reason {n}', 'original_sentence': '我要去',
            'hant': {'sentence_with_blank': '我___去', 'options': ['要', '會', '能'],
                     'correct_answer': '要', 'explanation': f'reason {n}',
                     'original_sentence': '我要去'}}


def jumbled() -> dict:
    return {'chunks': ['我们', '一起', '去'], 'original_sentence': '我们一起去',
            'hant': {'chunks': ['我們', '一起', '去'], 'original_sentence': '我們一起去'}}


def ex_row(n: int, sense: int, ex_type: str, level: int, content: dict, *,
           asset: int | None = 900) -> dict:
    return {'id': eid(n), 'language_id': ZH, 'exercise_type': ex_type,
            'source_type': 'vocabulary', 'word_sense_id': sense, 'word_asset_id': asset,
            'ladder_level': level, 'complexity_tier': 'T2', 'is_active': True,
            'tags': {'variant': 'A'}, 'content': content}


def serving_rows() -> dict[int, list[dict]]:
    """Rows per sense for the serving scenarios (one write_sense call per sense)."""
    rows = {
        101: [ex_row(1, 101, 'definition_match', 1, definition('这个', '這個')),
              ex_row(2, 101, 'cloze_completion', 3, cloze(2))],
        102: [ex_row(3, 102, 'jumbled_sentence', 5, jumbled()),
              ex_row(4, 102, 'definition_match', 1, definition('那个', '那個'))],
        103: [ex_row(5, 103, 'cloze_completion', 3, cloze(5))],
        104: [ex_row(6, 104, 'definition_match', 2, definition('哪个', '哪個'))],
    }
    for k, sense in enumerate(SPEED_SENSES):
        rows[sense] = [ex_row(100 + k, sense, 'definition_match', 1,
                              definition(f'词{k}', f'詞{k}'))]
    return rows


# ---------------------------------------------------------------------------
# Fake session RPCs (the TASK-985 shape: content_version always, content only
# when p_include_content, which defaults to true)
# ---------------------------------------------------------------------------

def _rpc_item(row: dict, include: bool, mode: str) -> dict:
    item = {'exercise_id': row['id'], 'sense_id': row['word_sense_id'],
            'exercise_type': row['exercise_type'], 'family': None,
            'ladder_level': row['ladder_level'], 'p_known': 0.6, 'expected_seconds': 20,
            'mode': mode, 'content_version': row['content_version']}
    if include and 'content' in row:
        item['content'] = row['content']
    return item


def _rows_of(db: FakeContentDB, senses, language_id) -> list[dict]:
    return sorted((r for r in db.rows() if r['word_sense_id'] in senses and r['is_active']
                   and r['language_id'] == language_id),
                  key=lambda r: (r['word_sense_id'], r['ladder_level'], r['id']))


def fake_get_practice_session(db: FakeContentDB, params: dict) -> dict:
    include = params.get('p_include_content', True)
    rows = _rows_of(db, SESSION_SENSES, params['p_language_id'])
    return {'items': [_rpc_item(r, include, 'maintenance') for r in rows],
            'mode': params['p_mode']}


def fake_get_review_ahead_items(db: FakeContentDB, params: dict) -> list[dict]:
    include = params.get('p_include_content', True)
    excluded = set(params.get('p_exclude_sense_ids') or [])
    rows = [r for r in _rows_of(db, (AHEAD_SENSE,), params['p_language_id'])
            if r['word_sense_id'] not in excluded]
    return [_rpc_item(r, include, 'review_ahead') for r in rows][:params['p_limit']]


def make_db(**kwargs) -> FakeContentDB:
    db = FakeContentDB(**kwargs)
    db.rpc_handlers['get_practice_session'] = fake_get_practice_session
    db.rpc_handlers['get_review_ahead_items'] = fake_get_review_ahead_items
    db.tables['questions'] = [{'test_id': 't1', 'sense_ids': [101]}]
    return db


# ---------------------------------------------------------------------------
# Fixtures and helpers
# ---------------------------------------------------------------------------

@pytest.fixture
def backend():
    mem = InMemoryBackend()
    store.set_backend(mem)
    return mem


@pytest.fixture
def modes(monkeypatch):
    def set_modes(source: str | None = None, write: str | None = None) -> None:
        if source is not None:
            monkeypatch.setattr(Config, 'EXERCISE_CONTENT_SOURCE', source)
        if write is not None:
            monkeypatch.setattr(Config, 'EXERCISE_CONTENT_WRITE', write)
    return set_modes


@pytest.fixture
def serve_env(monkeypatch):
    """The session's side reads: one prestudy follow-up, no intro drill, no DT cards,
    the prestudy page's word/knowledge reads."""
    monkeypatch.setattr(session_assembly, 'plan_today_iso', lambda db, u, lang: '2026-11-17')
    monkeypatch.setattr(prestudy, 'due_followup_senses', lambda *a, **k: [FOLLOWUP_SENSE])
    monkeypatch.setattr(prestudy, 'mark_followups', lambda *a, **k: None)
    monkeypatch.setattr(intro_drill, 'ENABLED', False)
    monkeypatch.setattr('services.dual_translation.cards.select_error_exercises_for_practice',
                        lambda *a, **k: [])
    # prestudy: 101 (p 0.2) and 103 (no row, no frequency -> prior 0.3) are drilled;
    # 102 (p 0.9) and 104 (p 0.8) are not.
    knowledge = {'101': {'p': 0.2, 'status': 'learning', 'n': 2},
                 '102': {'p': 0.9, 'status': 'known', 'n': 5},
                 '104': {'p': 0.8, 'status': 'known', 'n': 4}}
    monkeypatch.setattr(prestudy, '_load_senses', lambda db, ids, gloss: {
        str(s): {'lemma': f'w{s}', 'pos': 'n', 'freq': None, 'reading': None, 'glosses': {}}
        for s in ids})
    monkeypatch.setattr(prestudy, '_load_knowledge', lambda db, user, ids: {
        str(s): dict(knowledge[str(s)]) for s in ids if str(s) in knowledge})
    monkeypatch.setattr(prestudy, '_ability_zipf', lambda db, user, lang: 5.0)


TEST_ROW = {'id': 't1', 'slug': 'test-1', 'title': 'T', 'language_id': ZH,
            'transcript': '这个那个', 'audio_url': None, 'difficulty': 3,
            'target_age_tier': None, 'vocab_sense_ids': [101, 102, 103, 104],
            'vocab_token_map': [], 'furigana_payload': None, 'pinyin_payload': None}


def make_service(db) -> PracticeSessionService:
    s = PracticeSessionService.__new__(PracticeSessionService)
    s.db = db
    s._maybe_top_up_ladder = lambda u, lang: []
    s._order_items = lambda *a, **k: None
    s._most_overdue_first = lambda items, u: None
    s._exercise_preferences = lambda u: {'script_variant': 'traditional'}
    return s


def write_all(db: FakeContentDB, rows_by_sense: dict[int, list[dict]]) -> dict[int, store.WriteResult]:
    return {sense: store.write_sense(db, sense, ZH, insert_rows=copy.deepcopy(rows))
            for sense, rows in rows_by_sense.items()}


def cold(mem: InMemoryBackend) -> None:
    """A fresh worker: empty byte and negative caches (the files stay)."""
    store.set_backend(mem)
    mem.clear_calls()


def serve_session(db) -> dict:
    return make_service(db).get_session(USER, ZH, mode='maintenance')


def serve_all(db) -> dict:
    """Every serve path of the fixture, as plain data."""
    s = make_service(db)
    composer = SpeedRoundComposer(db)
    composer.mastered_sense_ids = lambda user, lang: list(SPEED_SENSES)
    random.seed(47047)
    battery = composer.compose(USER, ZH, size=10)
    served, on_demand = prestudy.on_demand_exercises(db, TEST_ROW, [102, 999])
    return {
        'session': s.get_session(USER, ZH, mode='maintenance'),
        'extra': s.get_extra_round(USER, ZH, reviews=True, new_words=0),
        'prestudy': prestudy.build_prestudy_payload(db, dict(TEST_ROW), USER, None),
        'on_demand': {'sense_ids': served, 'exercises': on_demand},
        'speed_round': dataclasses.asdict(battery),
    }


def exercise_selects(db: FakeContentDB, since: int) -> set[str]:
    return {c.columns for c in db.calls[since:]
            if c.kind == 'table' and c.name == 'exercises' and c.op == 'select'}


def rpc_params(db: FakeContentDB, name: str, since: int) -> list[dict]:
    return [c.params for c in db.calls[since:] if c.kind == 'rpc' and c.name == name]


def file_of(mem: InMemoryBackend, sense: int, version: int) -> dict[str, dict]:
    return store.decode_sense_file(mem.objects()[store.content_path(ZH, sense, version)],
                                   sense_id=sense, version=version)


def assert_column_matches_file(db: FakeContentDB, mem: InMemoryBackend, sense: int) -> int:
    versions = db.versions(sense)
    assert len(versions) == 1, versions
    (version,) = versions
    exercises = file_of(mem, sense, version)
    assert set(exercises) == {r['id'] for r in db.rows(sense)}
    for exercise_id, content in db.content_of(sense).items():
        assert store.canonical(exercises[exercise_id]) == store.canonical(content)
    return version


def differences(got, want, path: str = '') -> list[str]:
    """Readable paths where two JSON-like values differ (empty when equal)."""
    if isinstance(got, dict) and isinstance(want, dict):
        out = []
        for key in sorted(set(got) | set(want), key=str):
            if key not in want:
                out.append(f'{path}.{key}: unexpected')
            elif key not in got:
                out.append(f'{path}.{key}: missing')
            else:
                out += differences(got[key], want[key], f'{path}.{key}')
        return out
    if isinstance(got, list) and isinstance(want, list):
        if len(got) != len(want):
            return [f'{path}: {len(got)} items != {len(want)}']
        return [d for k, (g, w) in enumerate(zip(got, want)) for d in differences(g, w, f'{path}[{k}]')]
    return [] if got == want else [f'{path}: {got!r} != {want!r}']


def without_followup_versions(served: dict) -> dict:
    """``served`` with ``content_version`` removed from prestudy follow-up items.

    The one intended difference between modes: a follow-up item is built from an
    ``exercises`` select, and only the shadow / storage select reads
    ``content_version`` (db mode keeps today's select string), so only those
    modes copy it onto the item (TASK-987). Session RPC items carry it in every
    mode once TASK-985's migration is applied.
    """
    served = copy.deepcopy(served)
    for key in ('session', 'extra'):
        for item in (served.get(key) or {}).get('items') or []:
            if item.get('prestudy_followup'):
                item.pop('content_version', None)
    return served


def warnings_with(caplog, text: str) -> list[str]:
    return [r.getMessage() for r in caplog.records
            if r.levelno == logging.WARNING and text in r.getMessage()]


# ---------------------------------------------------------------------------
# 4 / 8. Write through the store, serve in every flag combination
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('source, write', COMBOS, ids=[f'{s}-{w}' for s, w in COMBOS])
def test_written_senses_serve_the_same_payloads_in_every_mode(source, write, backend, modes,
                                                              serve_env, caplog):
    modes(source='db', write=write)
    db = make_db()
    results = write_all(db, serving_rows())

    if write == 'dual':
        for sense, result in results.items():
            assert result.mode == 'dual' and result.version is not None
            assert assert_column_matches_file(db, backend, sense) == result.version
    else:
        assert backend.paths() == []                       # db writes touch no file
        assert all(r.mode == 'db' and r.version is None for r in results.values())

    # The db-mode reference, on the same data: exactly today's calls, no file I/O.
    cold(backend)
    mark = len(db.calls)
    reference = serve_all(db)
    assert backend.calls == []
    assert exercise_selects(db, mark) <= TODAYS_EXERCISE_SELECTS
    assert {frozenset(p) for p in rpc_params(db, 'get_practice_session', mark)} == \
        {frozenset(TODAYS_SESSION_PARAMS)}
    assert [set(p) for p in rpc_params(db, 'get_review_ahead_items', mark)] == \
        [TODAYS_AHEAD_PARAMS]

    # The reference itself is the content that was written (and was rewritten in place
    # by the script swap / jumbled prep, so a shared object would show up below).
    session = reference['session']
    assert sorted(i['exercise_id'] for i in session['items']) == \
        [eid(1), eid(2), eid(3), eid(4), eid(5)]
    assert session['script_variant'] == 'traditional'
    by_id = {i['exercise_id']: i for i in session['items']}
    assert by_id[eid(1)]['content']['word'] == '這個'
    assert by_id[eid(3)]['content']['chunks'] == ['我們', '一起', '去']
    assert by_id[eid(5)]['prestudy_followup'] is True
    assert {i['exercise_id'] for i in reference['extra']['items']} == \
        {eid(1), eid(4), eid(5), eid(6)}
    assert sorted(reference['prestudy']['exercises']) == ['101', '103']      # drill only
    assert reference['prestudy']['has_exercises'] == [101, 102, 103, 104]
    assert reference['on_demand']['sense_ids'] == [102]
    assert sorted(reference['on_demand']['exercises']) == ['102']
    assert len(reference['speed_round']['items']) == 10

    # The flag combination under test: cold (a restarted worker), then warm.
    modes(source=source)
    cold(backend)
    mark = len(db.calls)
    first = serve_all(db)
    first_gets = list(backend.calls_for('get'))
    warm_mark = len(backend.calls)
    second = serve_all(db)

    assert differences(without_followup_versions(first), reference) == []
    assert differences(without_followup_versions(second), reference) == []
    followups = [i for key in ('session', 'extra') for i in first[key]['items']
                 if i.get('prestudy_followup')]
    assert len(followups) == 2
    for item in followups:
        if source == 'db':
            assert 'content_version' not in item
        else:
            assert item['content_version'] == db.versions(FOLLOWUP_SENSE)[0]
    assert not [c for c in db.calls[mark:] if c.kind == 'table' and c.columns == 'id, content'], \
        'no DB fallback read when every file is present'

    if source == 'db':
        assert backend.calls == []
        return

    expected_flag = source == 'shadow'
    for params in rpc_params(db, 'get_practice_session', mark):
        assert params['p_include_content'] is expected_flag
    for params in rpc_params(db, 'get_review_ahead_items', mark):
        assert params['p_include_content'] is expected_flag

    if source == 'storage':
        assert first_gets, 'storage mode reads the files'
        assert backend.calls[warm_mark:] == [], 'a warm worker does no Storage I/O'
        # The speed round picks before it hydrates: 10 of the 12 mastered senses' files.
        speed_paths = {p for p in first_gets if int(p.split('/')[1].split('.')[0]) in SPEED_SENSES}
        assert len(speed_paths) == 10
        # Prestudy reads the drill senses' files only (ADR-047 open question 1);
        # the on-demand endpoint reads the one it was asked for.
        version = {s: db.versions(s)[0] for s in (101, 102, 103, 104)}
        assert store.content_path(ZH, 104, version[104]) in first_gets      # review-ahead item
        assert {store.content_path(ZH, s, version[s]) for s in (101, 102, 103)} <= set(first_gets)
    else:
        assert shadow.drain(5.0)
        stats = shadow.stats()
        assert stats['compared'] > 0
        assert stats['compared'] == stats['ok']
        assert not warnings_with(caplog, 'shadow_mismatch')


def test_prestudy_storage_mode_fetches_only_the_drill_senses(backend, modes, serve_env):
    modes(source='db', write='dual')
    db = make_db()
    write_all(db, {s: r for s, r in serving_rows().items() if s in (101, 102, 103, 104)})
    modes(source='storage')
    cold(backend)
    payload = prestudy.build_prestudy_payload(db, dict(TEST_ROW), USER, None)
    assert sorted(payload['exercises']) == ['101', '103']
    assert sorted(backend.calls_for('get')) == sorted(
        store.content_path(ZH, s, db.versions(s)[0]) for s in (101, 103))
    # A word the learner marks "I don't know this" loads on demand, from its own file only.
    backend.clear_calls()
    served, exercises = prestudy.on_demand_exercises(db, TEST_ROW, [102])
    assert served == [102] and sorted(exercises) == ['102']
    assert backend.calls_for('get') == [store.content_path(ZH, 102, db.versions(102)[0])]


# ---------------------------------------------------------------------------
# 1. render_all in dual mode
# ---------------------------------------------------------------------------

def test_render_all_on_a_new_sense_writes_one_file_and_stamps_the_rows(backend, modes):
    modes(write='dual')
    db = make_db()
    rows = [ex_row(11, 301, 'definition_match', 1, definition('这', '這')),
            ex_row(12, 301, 'cloze_completion', 3, cloze(12)),
            ex_row(13, 301, 'jumbled_sentence', 5, jumbled())]
    renderer = LadderExerciseRenderer(db)
    renderer.build_rows = lambda sense_id, language_id, levels=None: copy.deepcopy(rows)

    assert renderer.render_all(301, ZH) == [eid(11), eid(12), eid(13)]

    assert len(backend.calls_for('put')) == 1
    (path,) = backend.paths()
    version = assert_column_matches_file(db, backend, 301)
    assert path == store.content_path(ZH, 301, version) == f'zh/301.v{version}.json'
    assert backend.objects()[path] == store.encode_sense_file(
        301, ZH, version, {r['id']: r['content'] for r in rows})
    assert [c['p_expected_version'] for c in db.rpc_calls('exercise_content_commit')] == [0]


# ---------------------------------------------------------------------------
# 2. Backfill export of legacy rows, then verify
# ---------------------------------------------------------------------------

def _legacy_rows() -> list[dict]:
    return [ex_row(21, 201, 'definition_match', 1, definition('一', '一')),
            ex_row(22, 201, 'cloze_completion', 2, cloze(22)),
            ex_row(23, 201, 'cloze_completion', 3, cloze(23)),
            ex_row(24, 201, 'cloze_completion', 4, cloze(24)),
            ex_row(25, 201, 'cloze_completion', 4, cloze(25), asset=None),   # no word asset
            ex_row(26, 201, 'jumbled_sentence', 5, jumbled()),
            ex_row(27, 202, 'definition_match', 1, definition('二', '二'))]


def _backfill(db, tmp_path, *extra: str) -> tuple[int, dict]:
    report = tmp_path / f'report-{len(list(tmp_path.iterdir()))}.json'
    code = bf.main(['--language', 'zh', '--state-file', str(tmp_path / 'state.json'),
                    '--report', str(report), *extra], db=db, now=lambda: NOW)
    return code, json.loads(report.read_text(encoding='utf-8'))


def test_backfill_exports_legacy_rows_as_v0_files_and_verify_passes(backend, modes, tmp_path):
    modes(write='dual')
    db = make_db(rows=_legacy_rows())
    db.seed([{'id': eid(29), 'language_id': ZH, 'exercise_type': 'collocation_gap',
              'source_type': 'collocation', 'word_sense_id': None, 'content': {'x': 1}}])

    code, report = _backfill(db, tmp_path)
    assert code == 0 and report['files_written'] == 2
    assert backend.paths() == ['zh/201.v0.json', 'zh/202.v0.json']
    for sense in (201, 202):
        assert backend.objects()[f'zh/{sense}.v0.json'] == store.encode_sense_file(
            sense, ZH, 0, db.content_of(sense))
        assert store.fetch_sense(ZH, sense, 0) == db.content_of(sense)
    assert eid(29) not in json.dumps({p: b.decode() for p, b in backend.objects().items()})

    code, report = _backfill(db, tmp_path, '--verify')
    assert code == 0 and report['mismatches'] == []

    # A re-run writes nothing (state file + existing v0 files).
    backend.clear_calls()
    code, report = _backfill(db, tmp_path)
    assert code == 0 and backend.calls_for('put') == []


# ---------------------------------------------------------------------------
# 3. Scoped regeneration in dual mode, then the sweep
# ---------------------------------------------------------------------------

class _Pipeline:
    def __init__(self, db):
        self.db = db

    def generate_for_sense(self, sense_id, language_id, force=True, levels=None):
        return {'status': 'success', 'errors': []}


def test_scoped_regen_writes_a_new_version_and_the_sweep_removes_the_old_file(
        backend, modes, monkeypatch, tmp_path):
    import services.vocabulary_ladder.asset_pipeline as pipeline_mod
    import services.vocabulary_ladder.config as config_mod
    import services.vocabulary_ladder.exercise_renderer as renderer_mod

    modes(write='dual')
    db = make_db(rows=[r for r in _legacy_rows() if r['word_sense_id'] == 201])
    assert _backfill(db, tmp_path)[0] == 0
    v0 = file_of(backend, 201, 0)

    new_rows = [ex_row(31, 201, 'cloze_completion', 4, cloze(31)),
                ex_row(32, 201, 'cloze_completion', 4, cloze(32))]

    class _Renderer:
        def __init__(self, db):
            self.last_skips = []

        def build_rows(self, sense_id, language_id, levels=None):
            assert levels == {4}
            return copy.deepcopy(new_rows)

    monkeypatch.setattr(pipeline_mod, 'VocabAssetPipeline', _Pipeline)
    monkeypatch.setattr(renderer_mod, 'LadderExerciseRenderer', _Renderer)
    monkeypatch.setattr(config_mod, 'families_to_levels', lambda *a: {4})
    monkeypatch.setattr(qd, '_semantic_class_for_sense', lambda db, sense_id: 'action')
    monkeypatch.setattr(qd, 'coverage_gaps', lambda db, sense_ids=None, language_id=None: [])

    ok, detail = qd._regenerate(db, {'sense_id': 201, 'language_id': ZH,
                                     'reason': qd.REASON_COVERAGE_GAP,
                                     'detail': {'missing_families': ['form_production']}})
    assert ok, detail
    assert detail['rendered'] == 2 and detail['scoped_levels'] == [4]

    version = assert_column_matches_file(db, backend, 201)
    assert version > 0
    new_file = file_of(backend, 201, version)
    # The asset-linked level-4 row is gone; the asset-less level-4 row and every other
    # level are byte-identical; the two new rows are in.
    assert eid(24) not in new_file
    assert set(new_file) == {eid(21), eid(22), eid(23), eid(25), eid(26), eid(31), eid(32)}
    for exercise_id in (eid(21), eid(22), eid(23), eid(25), eid(26)):
        assert store.canonical(new_file[exercise_id]) == store.canonical(v0[exercise_id])

    sweep_report = tmp_path / 'sweep.json'
    code = sweep.main(['--language', 'zh', '--apply', '--grace-hours', '0',
                       '--report', str(sweep_report)], db=db,
                      now=lambda: datetime.now(timezone.utc) + timedelta(minutes=1))
    assert code == 0
    assert backend.paths() == [store.content_path(ZH, 201, version)]
    report = json.loads(sweep_report.read_text(encoding='utf-8'))
    assert report['deleted_paths'] == ['zh/201.v0.json']


# ---------------------------------------------------------------------------
# 5. Shadow mode with one tampered file
# ---------------------------------------------------------------------------

def test_shadow_reports_exactly_one_content_diff_and_serves_the_db_payload(
        backend, modes, serve_env, caplog):
    modes(source='db', write='dual')
    db = make_db()
    write_all(db, {s: r for s, r in serving_rows().items() if s in (101, 102, 103)})
    reference = serve_session(db)

    version = db.versions(101)[0]
    exercises = file_of(backend, 101, version)
    exercises[eid(2)] = {**exercises[eid(2)], 'correct_answer': '会'}       # the tamper
    backend.seed(store.content_path(ZH, 101, version),
                 store.encode_sense_file(101, ZH, version, exercises))

    modes(source='shadow')
    cold(backend)
    with caplog.at_level(logging.WARNING, logger='services.exercise_content'):
        payload = serve_session(db)
        assert shadow.drain(5.0)

    assert differences(without_followup_versions({'session': payload}),
                       {'session': reference}) == []
    diffs = warnings_with(caplog, 'kind=content_diff')
    assert len(diffs) == 1
    assert f'sense=101 version={version} exercise={eid(2)}' in diffs[0]
    assert not warnings_with(caplog, 'kind=missing')
    assert shadow.stats()['content_diff'] == 1


# ---------------------------------------------------------------------------
# 6. Two writers, one sense
# ---------------------------------------------------------------------------

def test_two_threads_updating_different_exercises_keep_both_edits(backend, modes):
    modes(write='dual')
    db = make_db()
    rows = [ex_row(41, 501, 'cloze_completion', 3, cloze(41)),
            ex_row(42, 501, 'cloze_completion', 4, cloze(42))]
    store.write_sense(db, 501, ZH, insert_rows=rows)

    barrier = threading.Barrier(2, timeout=5)
    begins = []

    def both_begin_before_either_commits(db_, payload):
        begins.append(payload)
        if len(begins) <= 2:
            barrier.wait()

    db.on('after:exercise_content_begin', both_begin_before_either_commits, once=False)
    errors, results = [], {}

    def edit(exercise_id, text):
        try:
            content = {**cloze(0), 'explanation': text}
            results[exercise_id] = store.write_sense(db, 501, ZH,
                                                     update_contents={exercise_id: content})
        except Exception as exc:          # pragma: no cover - reported below
            errors.append(exc)

    threads = [threading.Thread(target=edit, args=(eid(41), 'first edit')),
               threading.Thread(target=edit, args=(eid(42), 'second edit'))]
    for t in threads:
        t.start()
    for t in threads:
        t.join(10)
    assert errors == []
    assert sorted(r.attempts for r in results.values()) == [1, 2]   # one lost the race once

    version = assert_column_matches_file(db, backend, 501)
    final = file_of(backend, 501, version)
    assert final[eid(41)]['explanation'] == 'first edit'
    assert final[eid(42)]['explanation'] == 'second edit'
    # The loser's first file was deleted; the winner's intermediate version is still a
    # file until the sweep (it is no longer live).
    live = {store.content_path(ZH, 501, version)}
    assert live <= set(backend.paths())
    assert len(backend.paths()) == 3                  # first write, winner, final


# ---------------------------------------------------------------------------
# 7. A missing file in storage mode
# ---------------------------------------------------------------------------

def test_missing_file_falls_back_to_the_column_then_drops(backend, modes, serve_env,
                                                          monkeypatch, caplog):
    modes(source='db', write='dual')
    db = make_db()
    write_all(db, {s: r for s, r in serving_rows().items() if s in (101, 102, 103)})
    reference = serve_session(db)
    backend.delete([store.content_path(ZH, 101, db.versions(101)[0])])

    # Fallback on: served from exercises.content, with one WARNING.
    modes(source='storage')
    cold(backend)
    with caplog.at_level(logging.WARNING, logger='services.exercise_content'):
        payload = serve_session(db)
    assert differences(without_followup_versions({'session': payload}),
                       {'session': reference}) == []
    fallback = warnings_with(caplog, 'exercise_content.db_fallback')
    assert len(fallback) == 1 and 'n=2' in fallback[0]

    # Fallback off: the two items of sense 101 are dropped, the rest is served.
    monkeypatch.setattr(Config, 'EXERCISE_CONTENT_DB_FALLBACK', False)
    cold(backend)
    payload = serve_session(db)
    assert [i['exercise_id'] for i in payload['items']] == \
        [i['exercise_id'] for i in reference['items'] if i['sense_id'] != 101]
    assert 'no_content_reason' not in payload or payload['no_content_reason'] is None

    # Nothing left: the session says why.
    for sense in (102, 103):
        backend.delete([store.content_path(ZH, sense, db.versions(sense)[0])])
    cold(backend)
    payload = serve_session(db)
    assert payload['items'] == []
    assert payload['no_content_reason'] == 'content_unavailable'


def test_after_the_column_drop_the_fallback_switches_itself_off(backend, modes, serve_env,
                                                                caplog):
    modes(source='db', write='dual')
    db = make_db()
    write_all(db, {s: r for s, r in serving_rows().items() if s in (101, 102, 103)})
    backend.delete([store.content_path(ZH, 101, db.versions(101)[0])])
    db.has_content_column = False

    modes(source='storage')
    cold(backend)
    with caplog.at_level(logging.ERROR, logger='services.exercise_content'):
        payload = serve_session(db)
        again = serve_session(db)
    assert {i['sense_id'] for i in payload['items']} == {102, 103}
    assert again == payload
    disabled = [r for r in caplog.records if 'db_fallback_disabled' in r.getMessage()]
    assert len(disabled) == 1 and disabled[0].levelno == logging.ERROR
    # Only the first call tried the column.
    assert len([c for c in db.calls if c.kind == 'table' and c.columns == 'id, content']) == 1
