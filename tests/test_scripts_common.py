"""scripts/_common.py: the shared start-up helpers, and the dry-run default of the two
scripts that used to write without asking."""

import json
import os
import sys

import pytest

from scripts import _common


class _Query:
    def __init__(self, rows, calls):
        self.rows, self.calls = rows, calls

    def range(self, start, end):
        self.calls.append((start, end))
        self.window = self.rows[start:end + 1]
        return self

    def execute(self):
        return type('Result', (), {'data': self.window})()


@pytest.mark.parametrize('total', [0, 4, 5, 6, 10, 11])
def test_paginate_yields_every_row_and_stops_on_a_short_page(total):
    rows, calls = list(range(total)), []
    assert list(_common.paginate(lambda: _Query(rows, calls), page_size=5)) == rows
    assert calls == [(i * 5, i * 5 + 4) for i in range(total // 5 + 1)]


def test_paginate_builds_a_fresh_query_per_page():
    built = []

    def make():
        built.append(_Query(list(range(7)), []))
        return built[-1]

    list(_common.paginate(make, page_size=3))
    assert len(built) == 3 and len({id(q) for q in built}) == 3


def test_base_parser_is_dry_run_unless_apply_is_passed():
    parser = _common.base_parser('demo')
    assert parser.parse_args([]).apply is False
    assert parser.parse_args(['--apply']).apply is True


def test_bootstrap_puts_repo_root_on_path_and_can_leave_logging_alone(monkeypatch):
    import logging
    monkeypatch.setattr(sys, 'path', [p for p in sys.path if p != _common.ROOT])
    configured = []
    monkeypatch.setattr(logging, 'basicConfig', lambda **kw: configured.append(kw))
    assert _common.bootstrap(log_level=None) == _common.ROOT
    assert sys.path[0] == _common.ROOT and configured == []
    _common.bootstrap()
    assert configured == [{'level': logging.INFO, 'format': _common.LOG_FORMAT}]
    assert os.path.isdir(os.path.join(_common.ROOT, 'scripts'))


def test_admin_db_initialises_the_factory_once_and_returns_the_admin_client(monkeypatch):
    from services import supabase_factory
    state = {'ready': False, 'inits': 0}

    def initialize():
        state['inits'] += 1
        state['ready'] = True

    monkeypatch.setattr(supabase_factory.SupabaseFactory, 'is_initialized', lambda: state['ready'])
    monkeypatch.setattr(supabase_factory.SupabaseFactory, 'initialize', initialize)
    monkeypatch.setattr(supabase_factory, 'get_supabase_admin', lambda: 'client')
    assert _common.admin_db() == 'client' and _common.admin_db() == 'client'
    assert state['inits'] == 1


class _RecordingDB:
    def __init__(self):
        self.writes = []

    def table(self, name):
        db = self

        class _T:
            def update(self, payload):
                db.writes.append((name, payload))
                return self

            def eq(self, *a):
                return self

            def execute(self):
                return type('Result', (), {'data': []})()
        return _T()


def _token_map_runner(monkeypatch, apply):
    pytest.importorskip('jieba')
    from scripts import backfill_token_maps as mod
    runner = mod.TokenMapBackfillRunner.__new__(mod.TokenMapBackfillRunner)
    runner.apply, runner.language_code, runner.language_id = apply, 'zh', 1
    runner.limit, runner.force, runner.create_missing = 0, False, True
    runner.sense_generator = None
    runner.db = _RecordingDB()
    runner.stats = {'processed': 0, 'skipped': 0, 'failed': 0, 'matched_reverse': 0,
                    'matched_cache': 0, 'unmatched': 0, 'created': 0}
    created = []
    monkeypatch.setattr(runner, '_preload_caches', lambda: None)
    monkeypatch.setattr(runner, '_get_tests', lambda: [
        {'id': 't1', 'slug': 's1', 'transcript': 'abc', 'vocab_sense_ids': []}])
    monkeypatch.setattr(runner, '_build_token_map', lambda transcript, ids: ([['abc', 0]], [(0, 'abc')]))
    monkeypatch.setattr(runner, '_create_vocab_and_sense', lambda lemma, transcript: created.append(lemma) or 7)
    return runner, created


def test_backfill_token_maps_writes_nothing_without_apply(monkeypatch):
    runner, created = _token_map_runner(monkeypatch, apply=False)
    assert runner.run() is True
    assert runner.db.writes == [] and created == []
    assert runner.stats['processed'] == 1


def test_backfill_token_maps_writes_with_apply(monkeypatch):
    runner, created = _token_map_runner(monkeypatch, apply=True)
    assert runner.run() is True
    assert created == ['abc']
    assert runner.db.writes == [('tests', {'vocab_token_map': [['abc', 7]]})]


def test_upload_tests_dry_run_needs_no_credentials_and_creates_no_client(monkeypatch, tmp_path, capsys):
    from scripts import upload_tests_to_supabase as mod
    path = tmp_path / 'tests.json'
    path.write_text(json.dumps([{'slug': 'a', 'language': 'en', 'difficulty': 3, 'topic': 't',
                                 'transcript': 'x', 'questions': [{}, {}]}]), encoding='utf-8')
    monkeypatch.setattr(mod, 'SUPABASE_URL', None)
    monkeypatch.setattr(mod, 'GEN_USER_ID', None)
    monkeypatch.setitem(sys.modules, 'supabase', None)  # importing it would raise
    monkeypatch.setattr(sys, 'argv', ['upload_tests_to_supabase.py', str(path)])
    mod.main()
    out = capsys.readouterr().out
    assert '1 tests would be inserted' in out and '2 questions' in out
