"""The four uploaders the content skills call write only with --apply (TASK-1218).

Each is driven through its real ``main()`` against a recording fake Supabase
(tests/apply_convention_fakes.py). For every script:
(i) no flag writes nothing, (ii) ``--dry-run`` writes nothing, (iii) ``--apply``
reaches the real write path (at least one write on the fake), and
(iv) ``--apply --dry-run`` exits with code 2 before anything is read or written.
File validation (the answer-file shape checks) is replaced by a canned
result where it needs large fixtures; the write path itself is the real one.
"""

import json

import pytest

from tests.apply_convention_fakes import RecordingDB, install, run_main

MODES = {'default': [], 'dry_run': ['--dry-run'], 'apply': ['--apply']}


def _write_json(tmp_path, name, data):
    path = tmp_path / name
    path.write_text(json.dumps(data), encoding='utf-8')
    return str(path)


# ------------------------------------------------------------ upload_exercises

def _upload_exercises(monkeypatch, tmp_path):
    from scripts import upload_exercises as mod
    db = install(monkeypatch, RecordingDB(), mod)
    monkeypatch.setattr(mod, 'load_json', lambda path: {'language_id': 3, 'items': []})
    monkeypatch.setattr(mod, 'index_answers', lambda answers, batch, stage: {})
    content = {'pos': 'noun', 'semantic_class': 'object', 'sentences': []}
    monkeypatch.setattr(mod, 'prepare_core', lambda db_, batch, answers: (
        [{'sense_id': 11, 'lemma': 'x', 'content': content, 'warnings': []}], []))
    monkeypatch.setattr(mod.VocabAssetPipeline, '_update_vocabulary_metadata',
                        lambda self, sid, content: self.db.table('dim_vocabulary')
                        .update({'pos': content['pos']}).eq('id', sid).execute())
    argv = ['--stage', 'core', '--batch-file', 'b.json', '--answers-file', 'a.json']
    return mod, db, argv


# --------------------------------------------------------------- upload_senses

def _upload_senses(monkeypatch, tmp_path):
    from scripts import upload_senses as mod
    db = install(monkeypatch, RecordingDB(), mod)
    batch = _write_json(tmp_path, 'batch.json',
                        {'language_code': 'ja', 'language_id': 3, 'batch': 1, 'of': 1})
    monkeypatch.setattr(mod, 'load_senses', lambda path: [])
    monkeypatch.setattr(mod, 'validate', lambda senses, batch: (
        [{'vocab_id': 5, 'lemma': 'x', 'simple': 's', 'standard': 'std'}], [], []))
    monkeypatch.setattr(mod, 'fetch_standard_senses', lambda db_, ids, lid: {})
    monkeypatch.setattr('services.test_generation.database_client.TestDatabaseClient',
                        lambda *a, **k: object())

    class Gen:
        def __init__(self, *, db, dry_run, **kwargs):
            self.db, self.dry_run = db, dry_run

        def _write_two_levels(self, vocab_id, lemma, fields, rank):
            # SenseGenerator._write_two_levels' own dry-run gate, reduced to its contract.
            if self.dry_run:
                return -1
            self.db.table('dim_word_senses').insert({'vocab_id': vocab_id}).execute()
            return 1

    monkeypatch.setattr(mod, 'SenseGenerator', Gen)
    return mod, db, ['--batch-file', batch, '--senses-file', 'unused.json']


# -------------------------------------------------------------- upload_glosses

def _upload_glosses(monkeypatch, tmp_path):
    from scripts import upload_glosses as mod
    db = install(monkeypatch, RecordingDB(), mod)
    batch = _write_json(tmp_path, 'batch.json',
                        {'target_language_ids': {'zh': 1}, 'batch': 1, 'of': 1})
    monkeypatch.setattr(mod, 'load_glosses', lambda path: [])
    monkeypatch.setattr(mod, 'validate', lambda glosses, batch: ([{
        'vocab_id': 5, 'sense_rank': 1, 'lemma': 'x',
        'glosses': {'zh': {'simple': 'a', 'standard': 'b'}}}], [], []))
    return mod, db, ['--batch-file', batch, '--glosses-file', 'unused.json']


# ---------------------------------------------------------- upload_test_senses

def _upload_test_senses(monkeypatch, tmp_path):
    from scripts import upload_test_senses as mod
    db = install(monkeypatch, RecordingDB(rows={'tests': [
        {'id': 't1', 'slug': 's1', 'vocab_sense_ids': [], 'vocab_token_map': [['a', 7], ['b', 0]]},
    ]}), mod)
    return mod, db, ['--from-token-map', '--language', 'en']


SCRIPTS = {
    'upload_exercises': _upload_exercises,
    'upload_senses': _upload_senses,
    'upload_glosses': _upload_glosses,
    'upload_test_senses': _upload_test_senses,
}


@pytest.mark.parametrize('script', sorted(SCRIPTS))
@pytest.mark.parametrize('mode', ['default', 'dry_run'])
def test_without_apply_nothing_is_written(monkeypatch, tmp_path, script, mode):
    mod, db, argv = SCRIPTS[script](monkeypatch, tmp_path)
    assert run_main(monkeypatch, mod, argv + MODES[mode]) in (0, None)
    assert db.writes == []


@pytest.mark.parametrize('script', sorted(SCRIPTS))
def test_apply_reaches_the_write_path(monkeypatch, tmp_path, script):
    mod, db, argv = SCRIPTS[script](monkeypatch, tmp_path)
    assert run_main(monkeypatch, mod, argv + ['--apply']) in (0, None)
    assert db.writes, f'{script} --apply wrote nothing'


@pytest.mark.parametrize('script', sorted(SCRIPTS))
def test_apply_with_dry_run_is_an_error(monkeypatch, tmp_path, script):
    mod, db, argv = SCRIPTS[script](monkeypatch, tmp_path)
    assert run_main(monkeypatch, mod, argv + ['--apply', '--dry-run']) == 2
    assert db.writes == []


def test_upload_exercises_apply_stores_the_core_asset(monkeypatch, tmp_path):
    mod, db, argv = _upload_exercises(monkeypatch, tmp_path)
    run_main(monkeypatch, mod, argv + ['--apply'])
    assert ('upsert', 'word_assets') in {(op, table) for op, table, _ in db.writes}


# -------------------------------------------- exercise_stage_runner render
# The runner's one writing sub-command. cmd_render's own write path (one
# store.write_sense per sense, none when args.dry_run) is pinned by
# tests/test_exercise_content_writers_render.py; here, the flag it receives.

@pytest.mark.parametrize('argv, dry_run', [
    ([], True), (['--dry-run'], True), (['--apply'], False)])
def test_stage_runner_render_is_a_dry_run_unless_apply(monkeypatch, argv, dry_run):
    from scripts import exercise_stage_runner as esr
    seen = []
    monkeypatch.setattr(esr, 'cmd_render', lambda args: seen.append(args.dry_run) or 0)
    assert run_main(monkeypatch, esr, ['render', 'RUN'] + argv) == 0
    assert seen == [dry_run]


def test_stage_runner_render_apply_with_dry_run_is_an_error(monkeypatch):
    from scripts import exercise_stage_runner as esr
    seen = []
    monkeypatch.setattr(esr, 'cmd_render', lambda args: seen.append(args) or 0)
    assert run_main(monkeypatch, esr, ['render', 'RUN', '--apply', '--dry-run']) == 2
    assert seen == []


def test_stage_runner_other_commands_take_no_write_flag(monkeypatch):
    from scripts import exercise_stage_runner as esr
    assert run_main(monkeypatch, esr, ['status', 'RUN', '--apply']) == 2


def test_offline_assembly_runs_the_uploader_with_apply():
    # scratch_offline/assemble_all.py captures upload_exercises.py's writes through
    # the offline shim; without --apply the uploader would capture nothing.
    import os
    src = open(os.path.join(os.path.dirname(__file__), '..', 'scratch_offline',
                            'assemble_all.py'), encoding='utf-8').read()
    assert "'scripts/upload_exercises.py'" in src and "'--apply'" in src
