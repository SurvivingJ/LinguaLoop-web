"""The backfill scripts write only with --apply (TASK-1218).

Each is driven through its real ``main()`` against the recording fake Supabase
(tests/apply_convention_fakes.py) with a minimal fixture that the script would
write for: (i) no flag writes nothing, (ii) ``--dry-run`` writes nothing,
(iii) ``--apply`` reaches the write path (at least one write on the fake), and
(iv) ``--apply --dry-run`` exits with code 2 and writes nothing. Model, TTS,
tokenizer and Storage calls are replaced by fakes; a TTS upload or a Storage
content write counts as a write.

backfill_senses gets the weaker proof for (iii): its writes happen inside
SenseGenerator (tested on its own), so the fake generator here writes only when
the dry_run flag the script hands it is False.
"""

import importlib

import pytest

from tests.apply_convention_fakes import RecordingDB, install, run_main

MODES = {'default': [], 'dry_run': ['--dry-run']}


def _mod(name):
    return importlib.import_module(f'scripts.{name}')


def _exercise_audio(monkeypatch):
    mod = _mod('backfill_exercise_audio')
    db = install(monkeypatch, RecordingDB(), mod)
    row = {'id': 'e1', 'exercise_type': 'phonetic_recognition', 'word_sense_id': 10,
           'language_id': 3, 'content_version': 0, 'content': {'word': 'ねこ'}}
    monkeypatch.setattr(mod.AudioBackfillRun, 'fetch_pending', lambda self: [dict(row)])
    monkeypatch.setattr(mod.AudioBackfillRun, 'report_coverage', lambda self: None)
    monkeypatch.setattr(mod, 'pick_voice', lambda db_, language_id: ('ja-voice', 1.0))

    class Synth:
        def generate_and_upload(self, text, file_id, voice, speed):
            db.writes.append(('tts.upload', file_id, text))
            return f'https://r2.example/{file_id}.mp3'

    monkeypatch.setattr(mod.AudioBackfillRun, 'synthesizer', property(lambda self: Synth()))
    monkeypatch.setattr(mod.store, 'write_sense', lambda db_, sense_id, language_id, **kw:
                        db.writes.append(('store.write_sense', sense_id, kw)))
    monkeypatch.setattr(mod.queue_drain, 'enqueue', lambda *a, **k:
                        db.writes.append(('queue_drain.enqueue', a)) or True)
    return mod, db, ['--language', 'ja']


def _hant_mirrors(monkeypatch):
    mod = _mod('backfill_hant_mirrors')
    db = install(monkeypatch, RecordingDB(rows={'dim_vocabulary': [
        {'id': 1, 'lemma': '书', 'lemma_traditional': None}]}), mod)

    class Conv:
        def convert(self, text):
            return '書'

    monkeypatch.setattr(mod.ScriptConverter, 'from_db', classmethod(lambda cls, db_: Conv()))
    return mod, db, ['--target', 'lemmas']


def _pronunciations(monkeypatch):
    mod = _mod('backfill_pronunciations')
    db = install(monkeypatch, RecordingDB(), mod)
    monkeypatch.setattr(mod, 'fetch_senses', lambda db_, language_id, force, limit: [
        {'id': 7, 'dim_vocabulary': {'lemma': '书'}}])
    monkeypatch.setattr(mod, 'zh_pronunciation', lambda lemma: 'shū')
    return mod, db, ['--language', 'zh']


def _question_sense_ids(monkeypatch):
    mod = _mod('backfill_question_sense_ids')
    db = install(monkeypatch, RecordingDB(rows={
        'tests': [{'id': 't1', 'slug': 's1', 'vocab_sense_ids': [5]}],
        'questions': [{'id': 'q1-uuid-0000', 'question_text': 'x', 'choices': [],
                       'answer': 'x', 'sense_ids': []}],
    }), mod)
    monkeypatch.setattr(mod, 'build_sense_lookup', lambda db_, ids: {'x': 5})
    return mod, db, ['--language', 'zh']


def _semantic_class(monkeypatch):
    mod = _mod('backfill_semantic_class')
    db = install(monkeypatch, RecordingDB(), mod)
    monkeypatch.setattr(mod, 'resolve_template', lambda db_, lid: ('m', 'tpl', 1))
    monkeypatch.setattr(mod, 'fetch_lemmas', lambda db_, lid, force, limit: [{'id': 1}])
    monkeypatch.setattr(mod, 'build_prompt', lambda tpl, batch: ('p', {}))
    monkeypatch.setattr(mod, 'classify_batch', lambda model, version, prompt: {})
    monkeypatch.setattr(mod, 'apply_result', lambda stats, id_map, parsed, thr: [(1, 'object', 0.9)])
    return mod, db, ['--language', 'zh']


def _sense_embeddings(monkeypatch):
    mod = _mod('backfill_sense_embeddings')
    db = install(monkeypatch, RecordingDB(), mod)
    monkeypatch.setattr(mod, 'fetch_pending', lambda db_, lid, force: [{'id': 1, 'text': 'x'}])
    monkeypatch.setattr(mod, 'sense_vector', lambda v: v)

    class Embedder:
        def embed_batch(self, texts):
            return [[0.1, 0.2] for _ in texts]

    monkeypatch.setattr('services.topic_generation.agents.embedder.EmbeddingService', Embedder)
    return mod, db, ['--language', '2']


def _senses(monkeypatch):
    mod = _mod('backfill_senses')
    db = install(monkeypatch, RecordingDB(), mod)
    monkeypatch.setattr(mod, '_load_worklist', lambda db_, lid: ([(1, 'x')], 0))
    monkeypatch.setattr('services.test_generation.database_client.TestDatabaseClient',
                        lambda *a, **k: object())
    monkeypatch.setattr(mod, 'apply_provider', lambda provider: None)

    class Gen:
        def __init__(self, *, db, dry_run, **kwargs):
            self.db, self.dry_run, self.stats = db, dry_run, {}

        def seed_word(self, vocab_id, lemma, sentence):
            if not self.dry_run:  # SenseGenerator's own gate, reduced to its contract
                self.db.table('dim_word_senses').insert({'vocab_id': vocab_id}).execute()

    monkeypatch.setattr(mod, 'SenseGenerator', Gen)
    return mod, db, ['--language', 'zh', '--concurrency', '1']


def _topic_tiers(monkeypatch):
    mod = _mod('backfill_topic_tiers')
    db = install(monkeypatch, RecordingDB(rows={
        'dim_languages': [{'id': 1, 'language_code': 'zh'}],
        'dim_status': [{'id': 9, 'status_code': 'pending'}],
        'topics': [{'id': 't1', 'concept_english': 'c', 'target_age_tier': 3}],
        'production_queue': [],
    }), mod)
    return mod, db, ['--queue-tiers', '3']


def _vocab(monkeypatch):
    mod = _mod('backfill_vocab')
    db = install(monkeypatch, RecordingDB(), mod)

    class Pipeline:
        def extract_detailed(self, transcript, language_code):
            return [{'lemma': 'x', 'pos': 'noun'}]

    class SenseGen:
        stats = {'senses_created': 0, 'senses_reused': 0, 'senses_skipped': 0,
                 'senses_failed': 0}

        def generate_sense(self, **kwargs):
            return 5

    monkeypatch.setattr(mod.VocabBackfillRunner, '_init_pipeline',
                        lambda self: (Pipeline(), SenseGen()))
    monkeypatch.setattr(mod.VocabBackfillRunner, '_get_tests_to_process', lambda self: [
        {'id': 't1', 'slug': 's1', 'transcript': 'x y'}])
    monkeypatch.setattr(mod.VocabBackfillRunner, '_build_token_map',
                        lambda self, transcript, ids: ([['x', 5]], []))
    monkeypatch.setattr(mod, 'compute_zipf_for_vocab_item', lambda item, code: None)
    monkeypatch.setattr(mod, 'apply_provider', lambda provider: None)
    return mod, db, ['--language', 'zh', '--delay', '0']


def _vocab_reading(monkeypatch):
    mod = _mod('backfill_vocab_reading')
    db = install(monkeypatch, RecordingDB(rows={'dim_vocabulary': [{'id': 1, 'lemma': '猫'}]}), mod)

    class Processor:
        def reading_for(self, lemma):
            return 'ねこ'

    monkeypatch.setattr(mod, 'JapaneseProcessor', Processor)
    return mod, db, []


def _zipf_scores(monkeypatch):
    mod = _mod('backfill_zipf_scores')
    db = install(monkeypatch, RecordingDB(), mod)
    monkeypatch.setattr(mod.ZipfBackfillRunner, '_fetch_null_rows', lambda self: [
        {'id': 1, 'lemma': 'x'}])
    monkeypatch.setattr(mod.ZipfBackfillRunner, '_compute_score', lambda self, row: 4.2)
    return mod, db, ['--language', 'en']


def _relink_deferred_vocab(monkeypatch):
    mod = _mod('relink_deferred_vocab')
    db = install(monkeypatch, RecordingDB(), mod)
    monkeypatch.setattr(mod, '_tests_with_deferrals', lambda db_, lid, limit: [
        {'id': 't1', 'language_id': 1, 'vocab_sense_ids': [1],
         'vocab_sense_stats': {'deferred_lemmas': ['x'], 'words_attempted': 2}}])
    monkeypatch.setattr(mod, '_senses_for_lemmas', lambda db_, lemmas, lid: {'x': 2})
    return mod, db, []


SCRIPTS = {
    'backfill_exercise_audio': _exercise_audio,
    'backfill_hant_mirrors': _hant_mirrors,
    'backfill_pronunciations': _pronunciations,
    'backfill_question_sense_ids': _question_sense_ids,
    'backfill_semantic_class': _semantic_class,
    'backfill_sense_embeddings': _sense_embeddings,
    'backfill_senses': _senses,
    'backfill_topic_tiers': _topic_tiers,
    'backfill_vocab': _vocab,
    'backfill_vocab_reading': _vocab_reading,
    'backfill_zipf_scores': _zipf_scores,
    'relink_deferred_vocab': _relink_deferred_vocab,
}


@pytest.mark.parametrize('script', sorted(SCRIPTS))
@pytest.mark.parametrize('mode', sorted(MODES))
def test_without_apply_nothing_is_written(monkeypatch, script, mode):
    mod, db, argv = SCRIPTS[script](monkeypatch)
    assert run_main(monkeypatch, mod, argv + MODES[mode]) in (0, None)
    assert db.writes == []


@pytest.mark.parametrize('script', sorted(SCRIPTS))
def test_apply_reaches_the_write_path(monkeypatch, script):
    mod, db, argv = SCRIPTS[script](monkeypatch)
    assert run_main(monkeypatch, mod, argv + ['--apply']) in (0, None)
    assert db.writes, f'{script} --apply wrote nothing'


@pytest.mark.parametrize('script', sorted(SCRIPTS))
def test_apply_with_dry_run_is_an_error(monkeypatch, script):
    mod, db, argv = SCRIPTS[script](monkeypatch)
    assert run_main(monkeypatch, mod, argv + ['--apply', '--dry-run']) == 2
    assert db.writes == []
