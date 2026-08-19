"""Normalisation matrix for typed answers (TASK-532).

The acceptance criterion this covers, verbatim: "Normalisation tests:
full-width input, case, trailing space, traditional-typed ZH, EN inflection in
accepted set."

Why a matrix rather than a handful of cases
-------------------------------------------
Every rule here exists because some real keyboard produces a string a human
would call the same answer. The failure mode is not a crash — it is a learner
typing the right word and being told they are wrong, which is invisible in
aggregate metrics and corrosive to trust. So each rule gets its own row, and
the ZH/JA rows are written in the script a learner would actually be typing.

The negative cases matter as much as the positive ones: normalisation that
accepts *too* much silently stops testing the thing the item was built to test.
"""

import pytest

from services.vocabulary_ladder.deterministic.cloze_typed import grade
from utils.answer_normalization import (
    build_accepted, matches, normalization_spec, normalize,
)

ZH = 1
EN = 2
JA = 3


# ---------------------------------------------------------------------------
# normalize() — one rule per row
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('raw, language_id, expected, rule', [
    # Case folding (Latin only in effect; a no-op for CJK).
    ('Run', EN, 'run', 'case'),
    ('RUN', EN, 'run', 'case'),
    # Whitespace: leading, trailing, and internal runs.
    ('  run  ', EN, 'run', 'trailing space'),
    ('run\t', EN, 'run', 'trailing tab'),
    ('give  up', EN, 'give up', 'internal whitespace collapse'),
    # Full-width ASCII, which is what a CJK IME emits in ASCII mode.
    ('ｒｕｎ', EN, 'run', 'full-width latin'),
    ('１２３', EN, '123', 'full-width digits'),
    # Trailing punctuation, in both scripts' forms.
    ('run.', EN, 'run', 'trailing period'),
    ('run!', EN, 'run', 'trailing bang'),
    ('跑。', ZH, '跑', 'trailing ideographic period'),
    ('走る、', JA, '走る', 'trailing ideographic comma'),
    # Traditional -> Simplified, Chinese only.
    ('學習', ZH, '学习', 't2s'),
    ('電腦', ZH, '电脑', 't2s'),
])
def test_normalize_rules(raw, language_id, expected, rule):
    assert normalize(raw, language_id) == expected, f'rule: {rule}'


def test_t2s_is_chinese_only():
    """JA must not be folded to Simplified.

    Japanese uses shinjitai that overlap Traditional forms; folding them would
    rewrite correct Japanese into Chinese and reject the learner's answer.
    """
    assert normalize('學', JA) == '學'
    assert normalize('學', ZH) == '学'


def test_normalize_handles_empty_and_none():
    assert normalize(None, EN) == ''
    assert normalize('', EN) == ''
    assert normalize('   ', EN) == ''


# ---------------------------------------------------------------------------
# matches() — the comparison the grader actually uses
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('typed, accepted, language_id, ok, why', [
    ('run', ['run'], EN, True, 'exact'),
    ('Run', ['run'], EN, True, 'case-folded'),
    ('  run ', ['run'], EN, True, 'whitespace trimmed'),
    ('ｒｕｎ', ['run'], EN, True, 'full-width folded'),
    ('run.', ['run'], EN, True, 'trailing punctuation stripped'),
    ('ran', ['run', 'ran'], EN, True, 'inflection in accepted set'),
    ('學習', ['学习'], ZH, True, 'traditional typed, simplified keyed'),
    ('学习', ['学习'], ZH, True, 'simplified typed'),
    # Negatives — normalisation must not be so generous it stops testing.
    ('walk', ['run'], EN, False, 'different word'),
    ('ran', ['run'], EN, False, 'inflection NOT in accepted set'),
    ('', ['run'], EN, False, 'empty answer'),
    (None, ['run'], EN, False, 'missing answer'),
    ('run', [], EN, False, 'no accepted set'),
    ('runs', ['run'], EN, False, 'plural is a different form'),
])
def test_matches(typed, accepted, language_id, ok, why):
    assert matches(typed, accepted, language_id) is ok, f'case: {why}'


# ---------------------------------------------------------------------------
# build_accepted() — what gets stored on the item
# ---------------------------------------------------------------------------

def test_build_accepted_keeps_surface_forms():
    """Stored answers stay human-readable, not pre-normalised."""
    assert build_accepted('Run', ['Ran'], EN) == ['Run', 'Ran']


def test_build_accepted_dedupes_on_normalised_form():
    """`run` and `Run` are one accepted answer, not two."""
    assert build_accepted('run', ['Run', 'RUN', 'run.'], EN) == ['run']


def test_build_accepted_drops_empties():
    assert build_accepted('run', ['', None, '  '], EN) == ['run']


def test_normalization_spec_records_script_rule_per_language():
    assert normalization_spec(ZH)['script'] == 't2s'
    assert normalization_spec(EN)['script'] is None
    assert normalization_spec(JA)['script'] is None
    # The spec is stored on the item so a graded answer stays explainable.
    assert normalization_spec(EN)['unicode'] == 'NFKC'


# ---------------------------------------------------------------------------
# grade() — the server-side verdict the attempt route uses
# ---------------------------------------------------------------------------

def _item(accepted, target='run'):
    return {
        'schema_version': 2,
        'sentence_with_blank': 'Every morning I ___ to work.',
        'target_word': target,
        'answer': {'accepted': list(accepted)},
    }


def test_grade_accepts_normalised_variant():
    result = grade(_item(['run']), '  Run. ', EN)
    assert result['is_correct'] is True
    assert result['normalized'] == 'run'
    assert result['graded_by'] == 'server'


def test_grade_rejects_wrong_word_and_reports_accepted():
    result = grade(_item(['run']), 'walk', EN)
    assert result['is_correct'] is False
    # The accepted set comes back so a disputed answer can be explained
    # without re-deriving the rules from the grading code.
    assert result['accepted'] == ['run']


def test_grade_rejects_empty_answer():
    assert grade(_item(['run']), '', EN)['is_correct'] is False
    assert grade(_item(['run']), None, EN)['is_correct'] is False


def test_grade_falls_back_to_target_word_when_accepted_missing():
    """A pre-TASK-532 item has no answer.accepted; the key still grades."""
    assert grade({'target_word': 'run'}, 'Run', EN)['is_correct'] is True


def test_grade_traditional_typed_zh_matches_simplified_key():
    """The AC's ZH case, end to end through the server grader."""
    assert grade(_item(['学习'], target='学习'), '學習', ZH)['is_correct'] is True


def test_grade_does_not_fold_traditional_for_japanese():
    """Same characters, different language: JA must not be t2s-folded."""
    assert grade(_item(['学習'], target='学習'), '學習', JA)['is_correct'] is False


def test_importing_one_builder_does_not_disable_the_others():
    """Regression: the deterministic registry must load all seven builders.

    This module imports ``cloze_typed`` directly (so does routes/practice.py,
    to reach ``grade``). ``_load_builders`` used to short-circuit on
    ``if _REGISTRY:``, so that single import left the registry holding only
    cloze_typed and the other six builders silently unregistered — every sense
    would generate one exercise type instead of seven, with no skip reason to
    explain it. The guard is now a dedicated flag; this pins that.
    """
    from services.vocabulary_ladder import deterministic

    types = deterministic.registered_types()
    # One per builder module, so a module dropping out of the sweep is caught
    # rather than being masked by a sibling that happens to still be there.
    for expected in ('cloze_typed', 'definition_match', 'jumbled_sentence',
                     'classifier_match', 'counter_match', 'tone_id_word',
                     'kanji_to_reading'):
        assert expected in types, f'{expected} missing from {sorted(types)}'
