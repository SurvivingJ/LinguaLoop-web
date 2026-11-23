"""Scripts that were already dry-run-by-default, now on the shared --apply helper (TASK-1218).

Before: upload_sentence_references.py and build_test_sentences.py took
``--apply --dry-run`` together and applied; rescore_dt_grades.py took both and
dry-ran. Now the pair is an error (exit 2) everywhere, and the scripts that
make the caller name the mode still do.
"""

import importlib

import pytest

from tests.apply_convention_fakes import RecordingDB, install, run_main

SCRIPTS = {
    'upload_sentence_references': ['RUN'],
    'build_test_sentences': [],
    'rescore_dt_grades': ['--rubric-version', '5'],
    'audit_transcript_preambles': [],
    'build_classifier_dictionary': [],
}


def _load(name):
    return importlib.import_module(f'scripts.{name}')


@pytest.mark.parametrize('script', sorted(SCRIPTS))
def test_apply_with_dry_run_is_an_error(monkeypatch, script):
    mod = _load(script)
    db = install(monkeypatch, RecordingDB(), mod)
    assert run_main(monkeypatch, mod, SCRIPTS[script] + ['--apply', '--dry-run']) == 2
    assert db.writes == [] and db.rpc_calls == []


@pytest.mark.parametrize('script', ['upload_sentence_references', 'build_test_sentences',
                                    'audit_transcript_preambles'])
def test_mode_must_be_named(monkeypatch, script):
    mod = _load(script)
    db = install(monkeypatch, RecordingDB(), mod)
    assert run_main(monkeypatch, mod, SCRIPTS[script]) == 2
    assert db.writes == []


def test_build_test_sentences_passes_apply_through(monkeypatch):
    mod = _load('build_test_sentences')
    seen = []
    monkeypatch.setattr(mod, 'run_db', lambda apply, test_id: seen.append(apply) or 0)
    assert run_main(monkeypatch, mod, ['--dry-run']) == 0
    assert run_main(monkeypatch, mod, ['--apply']) == 0
    assert seen == [False, True]
