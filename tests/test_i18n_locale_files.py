"""The locale files must stay a flat map of dotted keys to strings.

`i18n-manager.js` assigns the parsed JSON straight to `translations` and looks
keys up flat — `translations["common.nav.calibration"]` — with no flattening
pass. So a block written nested:

    "calibration": { "title": "Calibration" }

parses fine, ships fine, and then renders the literal text
`calibration.title` on the page, because the flat lookup misses. The only
runtime signal is a `console.warn` nobody sees. That shipped once (the
calibration page and its nav tab, every string in all four locales); this
pins the invariant so it cannot ship again.
"""

import glob
import json
import os

import pytest

LOCALE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                          'static', 'i18n')
LOCALE_FILES = sorted(glob.glob(os.path.join(LOCALE_DIR, '*.json')))


def _load(path):
    with open(path, encoding='utf-8') as fh:
        return json.load(fh)


def test_locale_files_are_discovered():
    """Guard the glob itself — an empty parametrisation passes vacuously."""
    assert LOCALE_FILES, f'no locale files found under {LOCALE_DIR}'


@pytest.mark.parametrize('path', LOCALE_FILES, ids=os.path.basename)
def test_every_value_is_a_flat_string(path):
    nested = sorted(k for k, v in _load(path).items() if not isinstance(v, str))
    assert not nested, (
        f'{os.path.basename(path)} has nested key(s) {nested}; the loader does a '
        'flat lookup, so these render as their own key text. Flatten them to '
        'dotted keys (e.g. "calibration.title").'
    )
