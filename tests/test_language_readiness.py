"""services/language_readiness.py: the checklist of per-language plug-in points."""

import importlib.util
import os

from services import language_readiness as ready
from services import language_registry as lr

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_every_active_language_passes_every_required_check():
    for lang in lr.all_languages():
        assert ready.blockers(lang) == [], f'{lang.code}: {[(r.key, r.detail) for r in ready.blockers(lang)]}'


def test_no_check_errors_for_any_registered_language():
    for lang in lr.all_languages(include_planned=True):
        for r in ready.report(lang):
            assert not r.detail.startswith('check failed'), f'{lang.code} {r.key}: {r.detail}'


def test_a_planned_language_lists_what_it_still_needs():
    missing = {r.key for r in ready.blockers('it')}
    assert {'vocabulary_processor', 'nlp_metadata', 'exercise_processor', 'capabilities',
            'validation_profile', 'i18n_name'} <= missing
    assert 'wordfreq' not in missing and 'web_fonts' not in missing
    by_key = {r.key: r for r in ready.report('it')}
    assert by_key['cheat_sheet'].ok          # written by the Italian content pilot
    assert not by_key['tier_thresholds'].ok and by_key['tier_thresholds'].level == ready.OPTIONAL


def test_processor_registries_follow_the_registry_codes():
    from services.corpus.tokenizers import TOKENIZER_CLASSES
    from services.exercise_generation.language_processor import PROCESSOR_CLASSES
    assert set(PROCESSOR_CLASSES) == set(lr.codes()) == set(TOKENIZER_CLASSES)


def test_cli_exit_codes(capsys):
    spec = importlib.util.spec_from_file_location('check_language', os.path.join(ROOT, 'scripts', 'check_language.py'))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert mod.main([]) == 0
    assert 'it Italian' in capsys.readouterr().out
    assert mod.main(['ja']) == 0
    assert mod.main(['it']) == 1
    out = capsys.readouterr().out
    assert 'MISSING' in out and 'status=ACTIVE' in out
    assert mod.main(['xx']) == 2
