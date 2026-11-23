"""The four locale files carry the same keys, and each key the same {placeholders}.

`i18n-manager.js` falls back to English for a key missing from the current locale, and it leaves a
`{param}` the translation dropped (or misspelled) as literal text in the UI. Both have been easy to
ship when a feature adds keys to en.json first; Knowledge Report (TASK-1040) adds ~100 at once.
Plural strings ("1 word|{count} words") are compared as one string: every form must use the same
placeholders as English overall.
"""

import glob
import json
import os
import re

import pytest

LOCALE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                          'static', 'i18n')
LOCALES = sorted(os.path.splitext(os.path.basename(p))[0]
                 for p in glob.glob(os.path.join(LOCALE_DIR, '*.json')))
PLACEHOLDER = re.compile(r'\{([A-Za-z0-9_]+)\}')


def _load(lang):
    with open(os.path.join(LOCALE_DIR, f'{lang}.json'), encoding='utf-8') as fh:
        return json.load(fh)


def test_the_four_locales_exist():
    assert LOCALES == ['en', 'es', 'ja', 'zh']


@pytest.mark.parametrize('lang', [lang for lang in LOCALES if lang != 'en'])
def test_same_keys_as_english(lang):
    en, other = set(_load('en')), set(_load(lang))
    assert not sorted(en - other), f'{lang}.json is missing {sorted(en - other)[:20]}'
    assert not sorted(other - en), f'{lang}.json has keys en.json lacks: {sorted(other - en)[:20]}'


@pytest.mark.parametrize('lang', [lang for lang in LOCALES if lang != 'en'])
def test_same_placeholders_as_english(lang):
    en, other = _load('en'), _load(lang)
    bad = []
    for key, text in en.items():
        if key not in other:
            continue
        want, have = set(PLACEHOLDER.findall(text)), set(PLACEHOLDER.findall(other[key]))
        if want != have:
            bad.append(f'{key}: en {sorted(want)} vs {lang} {sorted(have)}')
    assert not bad, '\n'.join(bad[:30])


def test_knowledge_report_keys_avoid_the_report_namespace():
    """`report.*` belongs to "Report an issue" (knowledge-report tech F15)."""
    en = _load('en')
    assert any(k.startswith('knowledge.') for k in en)
    assert not [k for k in en if k.startswith('report.knowledge')]
