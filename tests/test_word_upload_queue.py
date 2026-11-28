"""services/word_list_import/queue.py — the word-upload work queue (ADR-069).

No database, no tokeniser model, no LLM: tables are tests/_word_queue_fakes.FakeDB
and the tokeniser is replaced by a dict lookup.
"""

import pytest

from services.word_list_import import queue as q
from tests._word_queue_fakes import FakeDB

USER = 'u-1'
OTHER = 'u-2'
BATCH = '11111111-1111-1111-1111-111111111111'
JA, EN = 3, 2

# Kept before the autouse fixture below replaces it for every other test.
_REAL_MISSING_AUDIO = q._senses_missing_audio


class _FakeTokenizer:
    LEMMAS = {'食べた': '食べる', '走る': '走る', 'ran': 'run', 'run': 'run', 'zzz': 'zzz'}

    def lemma_item(self, word, language_code):
        if word == 'boom':
            raise ValueError('no tokens')
        if word == 'お茶':
            return {'lemma': '御 茶', 'pos': '名詞', 'is_phrase': True, 'phrase_type': None,
                    'components': ['御', '茶'], 'reading': ''}
        return {'lemma': self.LEMMAS.get(word, word), 'pos': 'v', 'is_phrase': False,
                'phrase_type': None, 'components': None, 'reading': ''}


@pytest.fixture(autouse=True)
def _no_models(monkeypatch):
    monkeypatch.setattr(q, '_Tokenizer', _FakeTokenizer)
    monkeypatch.setattr(q, '_senses_missing_audio', lambda db, ids: set())


def _queue_row(word, language_id=JA, user=USER, gloss=EN, **kw):
    row = {'user_id': user, 'upload_batch_id': BATCH, 'language_id': language_id,
           'raw_word': word, 'gloss_language_id': gloss, 'vocab_id': None,
           'sense_id': None, 'status': 'pending', 'missing': [], 'detail': None,
           'requested_at': '2026-11-28T00:00:00+00:00'}
    row.update(kw)
    return row


def _complete_word(db, vocab_id, lemma, sense_id, language_id=JA, gloss=EN):
    """Every asset of the checklist present for one word."""
    db.tables.setdefault('dim_vocabulary', []).append(
        {'id': vocab_id, 'lemma': lemma, 'language_id': language_id})
    senses = db.tables.setdefault('dim_word_senses', [])
    senses += [
        {'id': sense_id, 'vocab_id': vocab_id, 'definition_language_id': language_id,
         'definition_level': 'standard', 'sense_rank': 1, 'source': 'llm',
         'pronunciation': 'たべる', 'embedding': [0.1]},
        {'id': sense_id + 1, 'vocab_id': vocab_id, 'definition_language_id': language_id,
         'definition_level': 'simple', 'sense_rank': 1, 'pronunciation': None, 'embedding': None},
    ]
    if gloss:
        senses += [
            {'id': sense_id + 2, 'vocab_id': vocab_id, 'definition_language_id': gloss,
             'definition_level': 'simple', 'sense_rank': 1},
            {'id': sense_id + 3, 'vocab_id': vocab_id, 'definition_language_id': gloss,
             'definition_level': 'standard', 'sense_rank': 1},
        ]
    db.tables.setdefault('word_assets', []).append(
        {'id': sense_id, 'sense_id': sense_id, 'asset_type': 'prompt1_core', 'is_valid': True})
    db.tables.setdefault('exercises', []).append(
        {'id': f'ex-{sense_id}', 'word_sense_id': sense_id, 'is_active': True,
         'exercise_type': 'cloze'})


# -- enqueue ------------------------------------------------------------------

def test_enqueue_inserts_one_pending_row_per_word_and_skips_requeued_words():
    db = FakeDB()
    assert q.enqueue_words(db, USER, JA, ['食べた', '走る'], BATCH, EN) == 2
    assert q.enqueue_words(db, USER, JA, ['走る', '飲む'], 'b2', EN) == 1
    rows = db.tables['word_upload_queue']
    assert [r['raw_word'] for r in rows] == ['食べた', '走る', '飲む']
    assert all(r['status'] == 'pending' and r['gloss_language_id'] == EN for r in rows)
    # The re-submitted word keeps its original batch.
    assert rows[1]['upload_batch_id'] == BATCH


def test_same_word_from_two_learners_is_two_rows():
    db = FakeDB()
    q.enqueue_words(db, USER, JA, ['走る'], BATCH, EN)
    q.enqueue_words(db, OTHER, JA, ['走る'], 'b2', EN)
    assert len(db.tables['word_upload_queue']) == 2


@pytest.mark.parametrize('native,language_id,expected', [
    (1, JA, 1),        # zh reader studying ja -> zh gloss
    (None, JA, EN),    # unset -> English
    (None, EN, None),  # unset, studying English -> no gloss
    (EN, EN, None),    # native == word language -> no gloss
])
def test_gloss_language_follows_the_learners_native_language(native, language_id, expected):
    db = FakeDB(users=[{'id': USER, 'native_language_id': native}])
    assert q.gloss_language_for(db, USER, language_id) == expected


def test_recent_queue_batches_are_counted_per_batch():
    db = FakeDB()
    q.enqueue_words(db, USER, JA, ['a', 'b'], 'b1', EN)
    q.enqueue_words(db, USER, JA, ['c'], 'b2', EN)
    q.enqueue_words(db, OTHER, JA, ['d'], 'b3', EN)
    assert q.count_recent_queue_batches(db, USER, '2000-01-01') == 2


# -- resolve --------------------------------------------------------------------

def test_resolve_is_lookup_only_by_default():
    db = FakeDB(word_upload_queue=[_queue_row('走る', id=1)])
    rows = q.load_open_rows(db)
    q.resolve_rows(db, rows)
    row = db.tables['word_upload_queue'][0]
    assert row['status'] == 'pending' and row['missing'] == ['vocab']
    assert row['detail'] == {'lemma': '走る'}
    assert 'dim_vocabulary' not in db.tables or not db.tables['dim_vocabulary']


def test_resolve_with_create_vocab_creates_the_dictionary_row(monkeypatch):
    created = []

    def fake_create(db, item, language_id, code, **_kw):
        created.append((item['lemma'], language_id, code))
        return 77

    monkeypatch.setattr('services.vocabulary.word_resolver.get_or_create_vocab_id', fake_create)
    db = FakeDB(word_upload_queue=[_queue_row('食べた', id=1)])
    q.resolve_rows(db, q.load_open_rows(db), create_vocab=True)
    row = db.tables['word_upload_queue'][0]
    assert created == [('食べる', JA, 'ja')]
    assert row['status'] == 'building' and row['vocab_id'] == 77


def test_split_cjk_word_is_looked_up_and_created_under_what_was_typed(monkeypatch):
    created = []
    monkeypatch.setattr('services.vocabulary.word_resolver.get_or_create_vocab_id',
                        lambda db, item, *a, **k: created.append(item['lemma']) or 8)
    db = FakeDB(word_upload_queue=[_queue_row('お茶', id=1)])
    q.resolve_rows(db, q.load_open_rows(db), create_vocab=True)
    assert created == ['お茶']
    assert db.tables['word_upload_queue'][0]['detail'] == {'lemma': 'お茶'}


def test_raw_word_is_tried_when_the_lemma_is_not_in_the_dictionary():
    db = FakeDB(word_upload_queue=[_queue_row('ran', language_id=EN, gloss=None, id=1)],
                dim_vocabulary=[{'id': 4, 'lemma': 'ran', 'language_id': EN}])
    q.resolve_rows(db, q.load_open_rows(db))
    assert db.tables['word_upload_queue'][0]['vocab_id'] == 4


def test_untokenisable_word_fails_with_a_reason():
    db = FakeDB(word_upload_queue=[_queue_row('boom', id=1)])
    q.resolve_rows(db, q.load_open_rows(db))
    row = db.tables['word_upload_queue'][0]
    assert row['status'] == 'failed'
    assert 'tokenise' in row['detail']['reason']


# -- checklist ------------------------------------------------------------------

def test_new_word_is_missing_everything_after_vocab():
    db = FakeDB(dim_vocabulary=[{'id': 5, 'lemma': 'zzz', 'language_id': JA}])
    row = _queue_row('zzz', id=1, vocab_id=5, status='building')
    check = q.check_assets(db, [row])[1]
    assert check == {'sense_id': None, 'missing': [
        'sense', 'embedding', 'pronunciation', 'gloss', 'core', 'exercises', 'audio']}


def test_english_word_without_gloss_skips_pronunciation_and_gloss():
    db = FakeDB(dim_vocabulary=[{'id': 5, 'lemma': 'zzz', 'language_id': EN}])
    row = _queue_row('zzz', language_id=EN, gloss=None, id=1, vocab_id=5, status='building')
    assert q.check_assets(db, [row])[1]['missing'] == ['sense', 'embedding', 'core',
                                                      'exercises', 'audio']


def test_complete_word_has_nothing_missing():
    db = FakeDB()
    _complete_word(db, 5, '走る', 50)
    row = _queue_row('走る', id=1, vocab_id=5, status='building')
    assert q.check_assets(db, [row])[1] == {'sense_id': 50, 'missing': []}


def test_each_missing_asset_is_reported():
    db = FakeDB()
    _complete_word(db, 5, '走る', 50)
    standard = db.tables['dim_word_senses'][0]
    standard['embedding'] = None
    standard['pronunciation'] = None
    db.tables['dim_word_senses'] = [s for s in db.tables['dim_word_senses']
                                    if s['definition_language_id'] != EN]
    db.tables['word_assets'][0]['is_valid'] = False
    row = _queue_row('走る', id=1, vocab_id=5, status='building')
    assert q.check_assets(db, [row])[1]['missing'] == ['embedding', 'pronunciation',
                                                      'gloss', 'core']


def test_inactive_exercises_do_not_count():
    db = FakeDB()
    _complete_word(db, 5, '走る', 50)
    db.tables['exercises'][0]['is_active'] = False
    row = _queue_row('走る', id=1, vocab_id=5, status='building')
    assert q.check_assets(db, [row])[1]['missing'] == ['exercises', 'audio']


def test_missing_audio_is_reported(monkeypatch):
    monkeypatch.setattr(q, '_senses_missing_audio', lambda db, ids: {50})
    db = FakeDB()
    _complete_word(db, 5, '走る', 50)
    row = _queue_row('走る', id=1, vocab_id=5, status='building')
    assert q.check_assets(db, [row])[1]['missing'] == ['audio']


def test_audio_check_reads_each_types_own_url_field(monkeypatch):
    from services.exercise_content import store
    contents = {
        'e1': {'audio_url': 'https://a/1.mp3'},
        'e2': {'audio_url': 'https://a/2.mp3'},   # wrong key for a flashcard
        'e3': {'front_audio_url': 'https://a/3.mp3'},
    }

    def fake_hydrate(rows, **_kw):
        for r in rows:
            r['content'] = contents[r['id']]

    monkeypatch.setattr(store, 'hydrate', fake_hydrate)
    monkeypatch.setattr(store, 'select_columns', lambda t: t.replace('{content}', 'content_version'))
    db = FakeDB(exercises=[
        {'id': 'e1', 'word_sense_id': 1, 'is_active': True, 'exercise_type': 'phonetic_recognition'},
        {'id': 'e2', 'word_sense_id': 2, 'is_active': True, 'exercise_type': 'listening_flashcard'},
        {'id': 'e3', 'word_sense_id': 3, 'is_active': True, 'exercise_type': 'listening_flashcard'},
    ])
    assert _REAL_MISSING_AUDIO(db, [1, 2, 3]) == {2}


# -- advance --------------------------------------------------------------------

def test_advance_finishes_a_complete_word_and_writes_the_watchlist_row():
    db = FakeDB(word_upload_queue=[_queue_row('走る', id=1)])
    _complete_word(db, 5, '走る', 50)
    summary = q.advance(db)
    row = db.tables['word_upload_queue'][0]
    assert row['status'] == 'done' and row['sense_id'] == 50 and row['completed_at']
    watch = db.tables['user_word_watchlist']
    assert len(watch) == 1
    assert watch[0]['sense_id'] == 50 and watch[0]['upload_batch_id'] == BATCH
    assert watch[0]['ladder_exercises_generated'] is True
    assert summary['done'] == 1 and summary['watchlist_rows'] == 1


def test_advance_records_whats_missing_and_keeps_building():
    db = FakeDB(word_upload_queue=[_queue_row('走る', id=1)],
                dim_vocabulary=[{'id': 5, 'lemma': '走る', 'language_id': JA}])
    q.advance(db)
    row = db.tables['word_upload_queue'][0]
    assert row['status'] == 'building' and row['vocab_id'] == 5
    assert row['missing'][0] == 'sense'
    assert not db.tables.get('user_word_watchlist')


def test_advance_does_not_duplicate_an_existing_watchlist_row():
    db = FakeDB(word_upload_queue=[_queue_row('走る', id=1)],
                user_word_watchlist=[{'id': 9, 'user_id': USER, 'sense_id': 50}])
    _complete_word(db, 5, '走る', 50)
    q.advance(db)
    assert db.tables['word_upload_queue'][0]['status'] == 'done'
    assert len(db.tables['user_word_watchlist']) == 1


def test_a_row_another_run_already_finished_is_not_finished_twice():
    db = FakeDB(word_upload_queue=[_queue_row('走る', id=1, vocab_id=5, status='building')])
    _complete_word(db, 5, '走る', 50)
    rows = q.load_open_rows(db)
    db.tables['word_upload_queue'][0]['status'] = 'done'   # the other worker won
    assert q._finish(db, rows[0], 50) is None
    assert not db.tables.get('user_word_watchlist')


def test_advance_scopes_to_one_batch():
    db = FakeDB(word_upload_queue=[_queue_row('走る', id=1),
                                   _queue_row('走る', id=2, user=OTHER, upload_batch_id='b2')])
    _complete_word(db, 5, '走る', 50)
    q.advance(db, upload_batch_id=BATCH)
    statuses = {r['id']: r['status'] for r in db.tables['word_upload_queue']}
    assert statuses == {1: 'done', 2: 'pending'}


def test_advance_runs_the_match_sweep_for_new_watchlist_rows(monkeypatch):
    swept = []
    monkeypatch.setattr('services.word_list_import.match_sweep.sweep_immediate_matches',
                        lambda rows, client: swept.append(rows) or {})
    db = FakeDB(word_upload_queue=[_queue_row('走る', id=1)])
    _complete_word(db, 5, '走る', 50)
    q.advance(db, db_client=object())
    assert len(swept) == 1 and swept[0][0]['sense_id'] == 50


def test_advance_with_nothing_open_writes_nothing():
    db = FakeDB(word_upload_queue=[_queue_row('走る', id=1, status='done')])
    assert q.advance(db)['open'] == 0


def test_open_rows_for_user_hides_done_rows():
    db = FakeDB(word_upload_queue=[
        _queue_row('a', id=1), _queue_row('b', id=2, status='done'),
        _queue_row('c', id=3, status='failed'), _queue_row('d', id=4, user=OTHER)])
    assert sorted(r['raw_word'] for r in q.open_rows_for_user(db, USER)) == ['a', 'c']
