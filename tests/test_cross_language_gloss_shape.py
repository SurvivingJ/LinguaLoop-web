"""
Cross-language glosses must be equivalents, not prose (TASK: cross-language
gloss format fix).

Why this file exists: services/vocabulary/gloss_generator.py's hosted prompt
asked for "a natural {target} definition ... about the same length as the
source definition" and got exactly that literally -- a 145-character English
paragraph for 緊張 instead of "tension; nervousness". Nothing errored; the
column just quietly grew two formats (ja->ja short definitions, ja->en prose
"definitions" of the same word). No test caught it because no test existed.

Two things guard against that recurring silently:

1. The hosted prompt path is retired outright (build_gloss_prompt /
   translate_definition raise). If a future change reintroduces that prompt
   without reading why it was removed, these tests fail loudly.
2. scripts/upload_glosses.py's `check_gloss_shape` is the fail-closed gate on
   the replacement (in-session) path: `simple` must be short, `standard` must
   be longer but still not a paragraph. These tests pin real examples from the
   investigation (both good and bad) against that gate.
"""

import pytest

from services.vocabulary import gloss_generator
from scripts.upload_glosses import check_gloss_shape, validate


# ---------------------------------------------------------------------------
# The hosted path stays disabled
# ---------------------------------------------------------------------------

def test_build_gloss_prompt_is_retired():
    with pytest.raises(NotImplementedError):
        gloss_generator.build_gloss_prompt('緊張', 'ja', 'en', 'some definition')


def test_translate_definition_is_retired():
    with pytest.raises(NotImplementedError):
        gloss_generator.translate_definition('緊張', 'ja', 'en', 'some definition', None, 'any-model')


# ---------------------------------------------------------------------------
# check_gloss_shape: real good examples from the target-format spec
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('simple,standard', [
    # 緊張 -- has a clean equivalent set; standard adds nuance
    ('tension', 'tension; nervousness; strain — being keyed up or on edge'),
    # 場所 -- has one clean equivalent, no clarifier needed
    ('place', 'place; location; spot'),
    # 気 -- no single equivalent; standard's clarifier is doing real work
    ('spirit', 'spirit; mind; feeling — no single English equivalent; covers '
               'mood, attention and intention'),
])
def test_good_examples_pass_the_shape_gate(simple, standard):
    assert check_gloss_shape(simple, standard) is None


# ---------------------------------------------------------------------------
# check_gloss_shape: the actual regression this exists to catch
# ---------------------------------------------------------------------------

def test_rejects_the_original_bloated_prose():
    # The real 緊張 -> en output the old hosted prompt produced.
    simple = 'A state of being tense or nervous.'
    standard = (
        "A state of being mentally or emotionally tense, with one's feelings "
        "or mind drawn taut. It describes the feeling of being keyed up or on "
        "edge."
    )
    error = check_gloss_shape(simple, standard)
    assert error is not None
    assert 'simple' in error or 'standard' in error


def test_rejects_a_one_sentence_definition_dressed_up_as_simple():
    # A `simple` that is itself a sentence, not a single equivalent.
    error = check_gloss_shape(
        'A specific point or area where people are active or things are located.',
        'A specific point or area where people are active or things are located, '
        'used generally for places.',
    )
    assert error is not None


def test_rejects_standard_not_longer_than_simple():
    # Duplicate answer -- both levels identical is exactly the standard-only
    # drift the two-level treatment exists to prevent, just disguised as a pair.
    error = check_gloss_shape('tension', 'tension')
    assert error is not None
    assert 'longer' in error


# ---------------------------------------------------------------------------
# validate(): the source-word-leak check must not fire across shared script
# ---------------------------------------------------------------------------

def _batch(source_lang, targets, items):
    ids = {'zh': 1, 'en': 2, 'ja': 3}
    return {
        'source_language_code': source_lang,
        'target_languages': targets,
        'target_language_ids': {t: ids[t] for t in targets},
        'items': items,
    }


def test_identical_kanji_hanzi_is_not_a_word_leak_ja_to_zh():
    # 十 ("ten") is written identically in Japanese and Chinese -- the
    # correct zh gloss legitimately contains the ja lemma verbatim.
    batch = _batch('ja', ['zh'], [
        {'vocab_id': 1, 'sense_rank': 1, 'lemma': '十', 'target_languages': ['zh']},
    ])
    glosses = [
        {'vocab_id': 1, 'sense_rank': 1, 'glosses': {
            'zh': {'simple': '十', 'standard': '十；数字十'},
        }},
    ]
    writable, skipped, errors = validate(glosses, batch)
    assert errors == []
    assert len(writable) == 1


def test_source_word_left_untranslated_into_english_is_still_a_leak():
    # Crossing into en is a real script boundary -- the ja lemma surviving
    # verbatim there means it didn't get translated.
    batch = _batch('ja', ['en'], [
        {'vocab_id': 2, 'sense_rank': 1, 'lemma': '緊張', 'target_languages': ['en']},
    ])
    glosses = [
        {'vocab_id': 2, 'sense_rank': 1, 'glosses': {
            'en': {'simple': '緊張', 'standard': '緊張; a state of tension'},
        }},
    ]
    writable, skipped, errors = validate(glosses, batch)
    assert len(errors) == 1
    assert '緊張' in errors[0]


def test_bare_numeral_lemma_is_not_a_word_leak_in_any_target():
    # "10" the digit string is shared notation, not source-language
    # vocabulary -- it belongs verbatim in a gloss of itself in any language.
    batch = _batch('ja', ['en'], [
        {'vocab_id': 3, 'sense_rank': 1, 'lemma': '10', 'target_languages': ['en']},
    ])
    glosses = [
        {'vocab_id': 3, 'sense_rank': 1, 'glosses': {
            'en': {'simple': 'ten', 'standard': 'ten; the numeral 10'},
        }},
    ]
    writable, skipped, errors = validate(glosses, batch)
    assert errors == []
    assert len(writable) == 1
