"""services/language_registry.py: lookups, the browser copy, and a guard against new hard-coded language maps."""

import importlib.util
import os
import re

import pytest

from services import language_registry as lr

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ---- the registry itself ------------------------------------------------------

def test_active_languages_are_the_three_live_ones():
    assert lr.id_to_code() == {1: 'zh', 2: 'en', 3: 'ja'}
    assert lr.code_to_id() == {'zh': 1, 'en': 2, 'ja': 3}
    assert lr.ids() == [1, 2, 3] and lr.codes() == ['zh', 'en', 'ja']


def test_planned_languages_are_hidden_unless_asked_for():
    assert lr.find(4) is None and lr.find('it') is None
    assert lr.get('it', include_planned=True).id == 4
    assert lr.id_to_code(include_planned=True)[4] == 'it'
    with pytest.raises(KeyError, match='registered: 1=zh, 2=en, 3=ja'):
        lr.get(4)


def test_find_accepts_ids_codes_legacy_codes_and_digit_strings():
    zh = lr.get(1)
    assert lr.find('zh') is zh and lr.find('CN') is zh and lr.find(' zh ') is zh and lr.find('1') is zh
    assert lr.find(zh) is zh
    assert lr.find('jp').code == 'ja'
    for bad in (None, True, 0, 99, '', 'xx', 1.0, []):
        assert lr.find(bad) is None
    assert lr.code_of(3) == 'ja' and lr.code_of(99, 'en') == 'en' and lr.id_of('jp') == 3 and lr.id_of('xx') is None


def test_legacy_codes_only_on_request():
    assert 'cn' not in lr.code_to_id()
    assert lr.code_to_id(legacy=True) == {'zh': 1, 'cn': 1, 'en': 2, 'ja': 3, 'jp': 3}


def test_script_family_helpers():
    assert lr.cjk_ids() == [1, 3] and lr.cjk_codes() == ['zh', 'ja']
    assert lr.is_cjk(1) and lr.is_cjk('ja') and not lr.is_cjk(2) and not lr.is_cjk(99)
    assert lr.token_joiner(1) == '' and lr.token_joiner('en') == ' ' and lr.token_joiner(99) == ' '
    assert lr.token_joiner('it') == ' '
    assert lr.script_family('zh') == 'cjk' and lr.script_family('en') == 'latin' and lr.script_family('xx') == ''
    assert lr.get(1).needs_ime and not lr.get(2).needs_ime


def test_features():
    assert lr.ids_with('pinyin') == [1] and lr.ids_with('furigana') == [3]
    assert lr.ids_with('pronunciation_calibration') == [1, 3]
    assert lr.codes_with('classifier_drill') == ['zh'] and lr.codes_with('counter_drill') == ['ja']
    assert lr.has_feature('zh', 'tones') and not lr.has_feature('en', 'tones') and not lr.has_feature(99, 'tones')
    with pytest.raises(KeyError):
        lr.has_feature(1, 'no_such_feature')
    with pytest.raises(KeyError):
        lr.ids_with('no_such_feature')
    with pytest.raises(ValueError):
        lr.Language(id=9, code='xx', name='x', display='X', native_name='X', locale='xx', flag='', glyph='X', script='latin',
                    features=frozenset({'nope'}))


def test_external_library_maps():
    assert lr.wordfreq_codes() == {'zh': 'zh', 'en': 'en', 'ja': 'ja'}
    assert lr.wordfreq_codes(include_planned=True)['it'] == 'it'
    assert lr.langdetect_to_code() == {'zh-cn': 'zh', 'zh-tw': 'zh', 'zh': 'zh', 'en': 'en', 'ja': 'ja'}


def test_config_reads_the_registry():
    from config import Config
    assert Config.LANGUAGES == {
        1: {'code': 'zh', 'name': 'chinese', 'display': 'Chinese'},
        2: {'code': 'en', 'name': 'english', 'display': 'English'},
        3: {'code': 'ja', 'name': 'japanese', 'display': 'Japanese'},
    }
    assert Config.VALID_LANGUAGE_IDS == {1, 2, 3}
    assert Config.LANGUAGE_CODE_TO_ID == {'zh': 1, 'en': 2, 'ja': 3}


def test_duplicate_ids_and_codes_are_refused():
    zh = lr.get(1)
    twin = lr.Language(id=1, code='xx', name='x', display='X', native_name='X', locale='xx', flag='', glyph='X', script='latin')
    with pytest.raises(ValueError, match='id 1'):
        lr._check([zh, twin])
    clash = lr.Language(id=9, code='cn', name='x', display='X', native_name='X', locale='xx', flag='', glyph='X', script='latin')
    with pytest.raises(ValueError, match="'cn'"):
        lr._check([zh, clash])


# ---- the browser copy ---------------------------------------------------------

def test_browser_copy_is_up_to_date():
    spec = importlib.util.spec_from_file_location(
        'build_language_registry_js', os.path.join(ROOT, 'scripts', 'build_language_registry_js.py'))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert mod.main(['--check']) == 0, 'run: python scripts/build_language_registry_js.py'


def test_browser_payload_marks_planned_languages():
    langs = {x['code']: x for x in lr.browser_payload()['languages']}
    assert langs['it']['active'] is False and langs['zh']['active'] is True
    assert langs['ja']['legacyCodes'] == ['jp'] and langs['zh']['spaced'] is False


# ---- guard: no new copies of the language set ----------------------------------

# A literal that pairs a language code with its id, or lists the codes a CLI accepts,
# is a second registry. Read services/language_registry.py instead.
PY_PATTERNS = [
    re.compile(r"""\b[123]\s*:\s*['"](?:zh|en|ja|cn|jp)['"]"""),
    re.compile(r"""['"](?:zh|en|ja|cn|jp)['"]\s*:\s*[123]\b(?!\s*[.\d])"""),
    re.compile(r"""choices\s*=\s*[\[(][^\])\n]*['"](?:zh|ja)['"]"""),
]
JS_PATTERNS = [
    re.compile(r"""\b[123]\s*:\s*['"](?:zh|en|ja|cn|jp)['"]"""),
    re.compile(r"""(?:\b|['"])(?:zh|en|ja|cn|jp)['"]?\s*:\s*[123]\b(?!\s*[.\d])"""),
]
PY_ROOTS = ['app.py', 'config.py', 'wsgi.py', 'services', 'routes', 'utils', 'web', 'middleware', 'models',
            'scripts', 'scratch_offline', 'Corpuses']
JS_ROOTS = ['static/js']
EXEMPT = {
    'services/language_registry.py',
    'static/js/language-registry.js',
}
# path -> why this literal is not a copy of the registry. Keep it short; every entry is a debt.
ALLOWED: dict = {}


def _files(roots, suffix):
    for root in roots:
        path = os.path.join(ROOT, root)
        if os.path.isfile(path):
            yield root
            continue
        for base, dirs, names in os.walk(path):
            dirs[:] = [d for d in dirs if d not in ('node_modules', '__pycache__', 'vendor', 'snap', 'staging')]
            for name in names:
                if name.endswith(suffix):
                    yield os.path.relpath(os.path.join(base, name), ROOT).replace(os.sep, '/')


def _hits(roots, suffix, patterns):
    hits = []
    for rel in _files(roots, suffix):
        if rel in EXEMPT or rel in ALLOWED:
            continue
        with open(os.path.join(ROOT, rel), encoding='utf-8', errors='replace') as fh:
            for n, line in enumerate(fh, 1):
                if any(p.search(line) for p in patterns):
                    hits.append(f'{rel}:{n}: {line.strip()[:110]}')
    return hits


def test_no_hard_coded_language_maps_in_python():
    hits = _hits(PY_ROOTS, '.py', PY_PATTERNS)
    assert not hits, 'use services/language_registry.py instead of a literal language map:\n' + '\n'.join(hits)


def test_no_hard_coded_language_maps_in_javascript():
    hits = _hits(JS_ROOTS, '.js', JS_PATTERNS)
    assert not hits, 'use window.LinguaLanguages (static/js/language-registry.js):\n' + '\n'.join(hits)


def test_allowed_entries_still_exist():
    for rel in ALLOWED:
        assert os.path.exists(os.path.join(ROOT, rel)), f'{rel} is gone; remove it from ALLOWED'
