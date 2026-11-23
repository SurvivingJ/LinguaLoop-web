"""rebuild_token_maps, reset_test_user, run_topic_import, screen_sense_definition_mismatch,
validate_collocates and validate_sense_languages write only with --apply (TASK-1218).

Each is driven through its real ``main()`` against the recording fake Supabase
(tests/apply_convention_fakes.py): (i) no flag writes nothing, (ii) ``--dry-run``
writes nothing, (iii) ``--apply`` reaches the write path, (iv) ``--apply
--dry-run`` exits with code 2 and writes nothing. reset_test_user talks to the
REST API with ``requests``; its DELETE calls are the writes recorded here.

run_topic_import gets the weaker proof for (iii): its writes happen inside
TopicImportOrchestrator (LLM gatekeeper, embeddings, queueing), so the fake
orchestrator here writes only when the dry_run flag the script hands it is False.
"""

import importlib
import os
import tempfile
from types import SimpleNamespace

import pytest

from tests.apply_convention_fakes import RecordingDB, install, run_main

MODES = {'default': [], 'dry_run': ['--dry-run']}


def _mod(name):
    return importlib.import_module(f'scripts.{name}')


def _rebuild_token_maps(monkeypatch):
    mod = _mod('rebuild_token_maps')
    db = install(monkeypatch, RecordingDB(), mod)
    monkeypatch.setattr(mod, 'fetch_tests', lambda db_, lid: [
        {'id': 't1', 'slug': 's1', 'transcript': 'x', 'vocab_sense_ids': [1], 'vocab_token_map': None}])
    monkeypatch.setattr(mod, 'existing_sense_ids', lambda db_, ids: set())
    monkeypatch.setattr(mod, 'VocabIndex', lambda *a, **k: SimpleNamespace(resolve=lambda lemma: (None,)))
    monkeypatch.setattr(mod, 'lemma_sense_lookup', lambda db_, ids: {})
    monkeypatch.setattr(mod, 'build_token_map_with_fallback', lambda *a, **k: ([['x', 1]], []))
    monkeypatch.setattr(mod, 'assess_rebuild', lambda *a, **k: {
        'verdict': 'write', 'dangling_before': 0, 'dangling_after': 0, 'live_links_before': 0,
        'live_links_after': 1, 'tokens_before': 0, 'tokens_after': 1})
    return mod, db, ['--language', 'ja']


def _reset_test_user(monkeypatch):
    mod = _mod('reset_test_user')
    db = RecordingDB()
    monkeypatch.setenv('SUPABASE_URL', 'http://fake.invalid')
    monkeypatch.setenv('SUPABASE_SERVICE_ROLE_KEY', 'fake')
    monkeypatch.setenv('TEST_USER_EMAIL', 'test-user@example.invalid')
    monkeypatch.delenv('TEST_USER_ID', raising=False)

    def resp(status=200, json_data=None):
        return SimpleNamespace(status_code=status, headers={'content-range': '0-0/1'}, text='',
                               json=lambda: json_data, raise_for_status=lambda: None)

    monkeypatch.setattr(mod.requests, 'get', lambda *a, **k: resp(json_data=[{'id': 'u1'}]))
    monkeypatch.setattr(mod.requests, 'head', lambda *a, **k: resp())
    monkeypatch.setattr(mod.requests, 'delete', lambda url, **k:
                        db.writes.append(('delete', url, k.get('params'))) or resp(204))
    return mod, db, []


def _run_topic_import(monkeypatch):
    mod = _mod('run_topic_import')
    db = install(monkeypatch, RecordingDB(), mod)
    path = os.path.join(tempfile.mkdtemp(), 'topics.json')
    with open(path, 'w', encoding='utf-8') as fh:
        fh.write('{"topics": []}')
    monkeypatch.setattr(mod, 'setup_logging', lambda verbose=False: None)

    class Orchestrator:
        def __init__(self, *, dry_run, **kwargs):
            self.dry_run = dry_run

        def run(self):
            if not self.dry_run:  # the orchestrator's own gate, reduced to its contract
                db.table('topics').insert({'concept_english': 'x'}).execute()
            return SimpleNamespace(error_message=None, topics_imported=1, total_entries=1,
                                   queue_entries_created=1)

    monkeypatch.setattr('services.topic_generation.import_orchestrator.TopicImportOrchestrator',
                        Orchestrator)
    return mod, db, ['--file', path]


def _screen_sense_definition_mismatch(monkeypatch):
    mod = _mod('screen_sense_definition_mismatch')
    db = install(monkeypatch, RecordingDB(rows={'dim_word_senses': [
        {'id': 1, 'dim_vocabulary': {'lemma': '作る れる'}}]}), mod)
    return mod, db, ['--language', '3', '--tokenizer-artifacts']


def _validate_collocates(monkeypatch):
    mod = _mod('validate_collocates')
    db = install(monkeypatch, RecordingDB(rows={'word_assets': [
        {'id': 'a1', 'sense_id': 5, 'content': {'sentences': ['s'], 'primary_collocate': 'c'}}]}), mod)

    class Grounder:
        def __init__(self, db_):
            pass

        def validate(self, lemma, collocate, language_id):
            return SimpleNamespace(status=mod.GROUNDING_CORPUS, reason='', to_tag=lambda: {'s': 1})

    monkeypatch.setattr(mod, 'CollocationGrounder', Grounder)
    monkeypatch.setattr(mod, 'get_sentence_target', lambda s: 'lemma')
    monkeypatch.setattr(mod.CollocateValidationRun, '_report', lambda self: None)
    return mod, db, ['--language', 'en']


def _validate_sense_languages(monkeypatch):
    mod = _mod('validate_sense_languages')
    db = install(monkeypatch, RecordingDB(rows={'dim_word_senses': [
        {'id': 1, 'vocab_id': 1, 'definition': 'an English definition', 'example_sentence': '',
         'source': 'llm', 'dim_vocabulary': {'lemma': '书', 'language_id': 1}}]}), mod)
    monkeypatch.setattr('services.test_generation.database_client.TestDatabaseClient',
                        lambda *a, **k: SimpleNamespace(get_language_config_by_code=lambda c: None))
    monkeypatch.setattr(mod, 'check_text_language',
                        lambda text, code: (text == '新的定义', ''))
    monkeypatch.setattr(mod, 'get_openai_client', lambda: object())
    monkeypatch.setattr(mod, 'regenerate_definition', lambda *a: '新的定义')
    monkeypatch.setattr(mod, 'regenerate_example_sentence', lambda *a: None)
    return mod, db, ['--language', 'zh', '--fix']


SCRIPTS = {
    'rebuild_token_maps': _rebuild_token_maps,
    'reset_test_user': _reset_test_user,
    'run_topic_import': _run_topic_import,
    'screen_sense_definition_mismatch': _screen_sense_definition_mismatch,
    'validate_collocates': _validate_collocates,
    'validate_sense_languages': _validate_sense_languages,
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


def test_run_topic_import_short_dry_run_flag_still_works(monkeypatch):
    mod, db, argv = _run_topic_import(monkeypatch)
    assert run_main(monkeypatch, mod, argv + ['-d']) == 0
    assert run_main(monkeypatch, mod, argv + ['-d', '--apply']) == 2
    assert db.writes == []


def test_validate_sense_languages_fix_without_apply_writes_nothing(monkeypatch):
    mod, db, argv = _validate_sense_languages(monkeypatch)
    assert run_main(monkeypatch, mod, argv) in (0, None)
    assert db.writes == []
    assert run_main(monkeypatch, mod, argv + ['--apply']) in (0, None)
    assert [w[:2] for w in db.writes] == [('update', 'dim_word_senses')]


def test_reset_test_user_help_no_longer_runs_a_reset(monkeypatch, capsys):
    # Before: any argv without --dry-run (even --help) ran the deletes.
    mod, db, _ = _reset_test_user(monkeypatch)
    assert run_main(monkeypatch, mod, ['--help']) == 0
    assert db.writes == []
