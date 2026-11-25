"""Dictionary importers and test-payload generators write only with --apply (TASK-1218).

build_counter_dictionary, import_character_components, import_cedict_classifiers,
cleanup_classifier_data and batch_generate_{furigana,pinyin,pitch_accent}, each
driven through its real ``main()`` against the recording fake Supabase
(tests/apply_convention_fakes.py) with a minimal fixture: (i) no flag writes
nothing, (ii) ``--dry-run`` writes nothing, (iii) ``--apply`` reaches the real
write path, (iv) ``--apply --dry-run`` exits with code 2 and writes nothing.
Downloads, curated-file merges and tokenizers are replaced by fakes.
"""

import importlib

import pytest

from tests.apply_convention_fakes import RecordingDB, install, run_main

MODES = {'default': [], 'dry_run': ['--dry-run']}


def _mod(name):
    return importlib.import_module(f'scripts.{name}')


def _counter_dictionary(monkeypatch):
    mod = _mod('build_counter_dictionary')
    db = install(monkeypatch, RecordingDB(), mod)
    monkeypatch.setattr(mod, 'load_dotenv', lambda *a, **k: None)
    monkeypatch.setattr(mod, '_merge_approved_curation', lambda: None)
    return mod, db, []


def _character_components(monkeypatch):
    mod = _mod('import_character_components')
    db = install(monkeypatch, RecordingDB(), mod)
    monkeypatch.setattr(mod, 'load_dotenv', lambda *a, **k: None)
    monkeypatch.setattr(mod, 'build_rows', lambda **kw: [
        {'character': '掌', 'components': ['手'], 'radical': None, 'stroke_count': None}])
    return mod, db, []


def _cedict_classifiers(monkeypatch):
    mod = _mod('import_cedict_classifiers')
    db = install(monkeypatch, RecordingDB(), mod)
    monkeypatch.setattr(mod, '_ensure_cedict_file', lambda: None)
    monkeypatch.setattr(mod, '_load_existing_state', lambda db_: (
        {'个': {'id': 1, 'hanzi': '个', 'frequency_rank': 1}}, set(), set(), 1))
    monkeypatch.setattr(mod, 'parse_cedict', lambda: iter([('苹果', None, None, [('个', 'ge4')])]))
    return mod, db, []


def _cleanup_classifier_data(monkeypatch):
    mod = _mod('cleanup_classifier_data')
    db = install(monkeypatch, RecordingDB(), mod)
    rows = {
        'dim_classifiers': [{'id': 1, 'hanzi': '個', 'pinyin': 'ge4', 'pinyin_display': 'ge4',
                             'example_nouns': []}],
        'dim_classifier_noun_pairs': [],
    }
    monkeypatch.setattr(mod, '_fetch_all', lambda db_, table, cols, lid: rows[table])
    monkeypatch.setattr(mod, 'to_simp', lambda s: {'個': '个'}.get(s, s))
    monkeypatch.setattr(mod, 'to_diacritic', lambda s: s)
    return mod, db, []


def _tests_payload(name, service_attr, payload):
    def setup(monkeypatch):
        mod = _mod(name)
        db = install(monkeypatch, RecordingDB(rows={
            'tests': [{'id': 't1', 'slug': 's1', 'transcript': '文'}],
            'questions': [],
        }), mod)
        monkeypatch.setattr(mod, service_attr, lambda *a, **k: payload)
        return mod, db, []
    return setup


SCRIPTS = {
    'build_counter_dictionary': _counter_dictionary,
    'import_character_components': _character_components,
    'import_cedict_classifiers': _cedict_classifiers,
    'cleanup_classifier_data': _cleanup_classifier_data,
    'batch_generate_furigana': _tests_payload(
        'batch_generate_furigana', 'process_test_payload', {'transcript': [], 'questions': []}),
    'batch_generate_pinyin': _tests_payload(
        'batch_generate_pinyin', 'process_passage',
        [{'is_punctuation': False, 'is_sandhi': False, 'requires_review': False}]),
    'batch_generate_pitch_accent': _tests_payload(
        'batch_generate_pitch_accent', 'process_passage',
        [{'is_punctuation': False, 'pattern_class': 'heiban', 'requires_review': False}]),
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
