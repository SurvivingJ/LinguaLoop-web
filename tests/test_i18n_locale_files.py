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


# ---------------------------------------------------------------------------
# Vocabulary placement (wiki/features/vocab-placement.tech.md §16, TASK-1084)
# ---------------------------------------------------------------------------

PLACEMENT_PREFIXES = ('placement.', 'onboarding.studied_')

#: The keys §16 names. The page uses a few more (all `placement.*`); parity
#: below covers those too.
PLACEMENT_SPEC_KEYS = [
    'placement.' + k for k in (
        'title', 'intro_time_cjk', 'intro_time_en', 'intro_idk_hint', 'start',
        'choose_meaning', 'choose_pinyin', 'choose_reading_ja', 'idk', 'best_guess',
        'probe_badge', 'sound_pair_prompt', 'next',
        'stop_here', 'end_confirm', 'not_enough', 'minutes_left', 'reveal_meaning',
        'reveal_reading',
        'answers_heading', 'group_both', 'group_tones_not_yet', 'group_meaning_only',
        'group_not_yet', 'group_recognised_en', 'practise_readings', 'learn_these',
        'up_to_today', 'result_mr', 'result_m', 'result_m_en', 'result_fewer',
        'result_tone_gap', 'result_gap', 'retake_this', 'retake_previous', 'retake_up',
        'retake_down', 'retake_same', 'retake_combined', 'ended_early', 'fast_flag',
        'next_session', 'next_check', 'how_title', 'how_body_cjk', 'how_body_en',
        'unavailable',
    )
] + ['onboarding.studied_' + k for k in ('before', 'yes', 'few', 'no')]


def _placement_keys(path):
    return {k for k in _load(path) if k.startswith(PLACEMENT_PREFIXES)}


def _locale(code):
    return os.path.join(LOCALE_DIR, f'{code}.json')


@pytest.mark.parametrize('code', ['en', 'es', 'ja', 'zh'])
def test_placement_spec_keys_exist_in_every_locale(code):
    data = _load(_locale(code))
    missing = [k for k in PLACEMENT_SPEC_KEYS if not data.get(k)]
    assert not missing, f'{code}.json lacks {missing}'


@pytest.mark.parametrize('code', ['es', 'ja', 'zh'])
def test_placement_keys_match_english(code):
    en, other = _placement_keys(_locale('en')), _placement_keys(_locale(code))
    assert other == en, (
        f'{code}.json differs from en.json: missing {sorted(en - other)}, '
        f'extra {sorted(other - en)}'
    )


@pytest.mark.parametrize('code', ['en', 'es', 'ja', 'zh'])
def test_placement_placeholders_match_english(code):
    """A translation keeps every {placeholder} of the English string."""
    import re
    en, other = _load(_locale('en')), _load(_locale(code))
    for key in sorted(_placement_keys(_locale('en'))):
        want = set(re.findall(r'\{(\w+)\}', en[key]))
        got = set(re.findall(r'\{(\w+)\}', other[key]))
        assert got == want, f'{code}.json {key}: placeholders {sorted(got)} != {sorted(want)}'


def test_placement_copy_says_recognised_not_know():
    """§16 copy rule: "recognised", never "know" on its own. The "I don't know"
    answer label is the one allowed use; any other "know" (known, knowledge…)
    must sit in a string that also says "recognis…"."""
    import re
    en = _load(_locale('en'))
    offenders = []
    for key in sorted(_placement_keys(_locale('en'))):
        text = re.sub(r"I don['’]t know", '', en[key])
        if re.search(r'know', text, re.I) and not re.search(r'recogni[sz]', text, re.I):
            offenders.append((key, en[key]))
    assert not offenders, offenders


def test_placement_copy_has_no_exam_level_or_verdict():
    """§16: no exam level (PQ2), no pass/fail or readiness, no praise."""
    import re
    en = _load(_locale('en'))
    banned = re.compile(
        r'\b(HSK|JLPT|N[1-5]|CEFR|level|pass(ed)?|fail(ed)?|ready|great|well done|'
        r'excellent|congratulations)\b', re.I)
    offenders = [(k, en[k]) for k in sorted(_placement_keys(_locale('en')))
                 if banned.search(en[k])]
    assert not offenders, offenders
