"""scripts/word_upload_queue.py — stage routing and the export plan. No DB:
FakeDB tables; exporter subprocesses are not run (dry run)."""

import os

import pytest

from scripts import word_upload_queue as wuq
from services.word_list_import import queue as q
from tests._word_queue_fakes import FakeDB


def _row(id_, missing, sense_id=50, vocab_id=5, gloss=2, status='building'):
    return {'id': id_, 'status': status, 'missing': missing, 'sense_id': sense_id,
            'vocab_id': vocab_id, 'gloss_language_id': gloss, 'language_id': 3,
            'raw_word': f'w{id_}', 'detail': None, 'user_id': 'u', 'upload_batch_id': 'b'}


def test_stage_groups_hand_out_only_stages_whose_inputs_exist():
    rows = [
        _row(1, ['sense', 'embedding', 'core', 'exercises', 'audio'], sense_id=None),
        _row(2, ['embedding', 'gloss', 'core', 'exercises', 'audio'], sense_id=51, vocab_id=6),
        _row(3, ['exercises', 'audio'], sense_id=52, vocab_id=7),
        _row(4, ['audio'], sense_id=53, vocab_id=8),
        _row(5, ['vocab'], status='pending', sense_id=None, vocab_id=None),
    ]
    groups = wuq.stage_groups(rows)
    ids = {k: [r['id'] for r in v] for k, v in groups.items()}
    assert ids == {
        'sense': [1],
        'embedding': [2], 'gloss': [2], 'core': [2],
        'exercises': [3],
        'audio': [4],
    }


def test_plan_passes_the_queued_ids_to_each_exporter(tmp_path):
    groups = wuq.stage_groups([
        _row(1, ['sense', 'core', 'exercises', 'audio'], sense_id=None, vocab_id=5),
        _row(2, ['gloss', 'core', 'exercises', 'audio'], sense_id=51, vocab_id=6),
        _row(3, ['gloss', 'core', 'exercises', 'audio'], sense_id=52, vocab_id=7, gloss=1),
        _row(4, ['exercises', 'audio'], sense_id=53, vocab_id=8),
    ])
    commands, lines = wuq.build_plan('ja', 3, groups, 'RUN')
    flat = [' '.join(c) for c in commands]
    assert any('export_sense_seed_worklist.py' in c and '--vocab-ids 5 ' in c for c in flat)
    assert any('export_gloss_worklist.py' in c and '--target-languages en' in c
               and '--vocab-ids 6 ' in c for c in flat)
    assert any('--target-languages zh' in c and '--vocab-ids 7 ' in c for c in flat)
    assert any('--stage core --sense-ids 51,52 ' in c for c in flat)
    assert any('--stage exercises --sense-ids 53 ' in c for c in flat)
    text = '\n'.join(lines)
    assert 'batch-sense-generation' in text and 'cross-language-glosses' in text
    assert 'batch-exercise-generation' in text
    assert 'word_upload_queue.py advance --language ja' in text


def test_plan_with_nothing_to_build_says_so():
    commands, lines = wuq.build_plan('ja', 3, {}, 'RUN')
    assert commands == []
    assert any('Nothing to build' in line for line in lines)


def test_fail_and_requeue_round_trip():
    db = FakeDB(word_upload_queue=[_row(1, ['sense'], status='building')])
    wuq.cmd_fail(db, type('A', (), {'ids': '1', 'reason': 'not a word'}))
    row = db.tables['word_upload_queue'][0]
    assert row['status'] == 'failed' and row['detail']['reason'] == 'not a word'
    wuq.cmd_requeue(db, type('A', (), {'ids': '1'}))
    assert row['status'] == 'pending' and row['vocab_id'] is None
    assert 'reason' not in row['detail']


def test_export_dry_run_writes_nothing(tmp_path, monkeypatch):
    db = FakeDB(word_upload_queue=[_row(1, ['core', 'exercises', 'audio'], sense_id=51)])
    monkeypatch.setattr(wuq, '_run', lambda cmd: pytest.fail('exporter ran in a dry run'))
    monkeypatch.setattr(q, 'check_assets',
                        lambda db, rows: {1: {'sense_id': 51, 'missing': ['core', 'exercises', 'audio']}})
    args = type('A', (), {'language': 'ja', 'out_dir': str(tmp_path / 'run'),
                          'no_create_vocab': False, 'dry_run': True})
    assert wuq.cmd_export(db, args) == 0
    assert not os.path.exists(tmp_path / 'run')
    assert db.tables['word_upload_queue'][0]['missing'] == ['core', 'exercises', 'audio']


def test_export_apply_runs_the_exporters_and_writes_the_plan(tmp_path, monkeypatch):
    db = FakeDB(word_upload_queue=[_row(1, ['core', 'exercises', 'audio'], sense_id=51)])
    ran = []
    monkeypatch.setattr(wuq, '_run', lambda cmd: ran.append(cmd) or True)
    monkeypatch.setattr(wuq, '_db_client', lambda: None)
    monkeypatch.setattr(q, 'check_assets',
                        lambda db, rows: {1: {'sense_id': 51, 'missing': ['core', 'exercises', 'audio']}})
    args = type('A', (), {'language': 'ja', 'out_dir': str(tmp_path / 'run'),
                          'no_create_vocab': False, 'dry_run': False})
    assert wuq.cmd_export(db, args) == 0
    assert any('--stage' in c and 'core' in c for c in ran)
    assert os.path.exists(tmp_path / 'run' / 'plan.md')
    assert os.path.exists(tmp_path / 'run' / 'queue.json')


def test_fail_dry_run_changes_nothing():
    db = FakeDB(word_upload_queue=[_row(1, ['sense'], status='building')])
    wuq.cmd_fail(db, type('A', (), {'ids': '1', 'reason': 'x', 'dry_run': True}))
    assert db.tables['word_upload_queue'][0]['status'] == 'building'
