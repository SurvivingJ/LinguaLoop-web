"""Tests for per-type context-free exercise caps (plan §3d, T3d.1 / T3d.2).

The measurement behind these: 做 (zuò) carried 33 active exercises across 12
types. That is not 33 redundant drills — it is ~2-3 variants of 12 genuinely
distinct skills. The waste is concentrated in the context-free types, where the
item is a property of the word itself:

    tone_id_word    x2  byte-identical
    hanzi_to_pinyin x2  same four options, order shuffled
    pinyin_to_hanzi x2  same four options, order shuffled

A word has one tone. The cap therefore belongs per *type*, not per word: a flat
cap of 6-8 per word would delete whole skill types.
"""

import pytest

from services.vocabulary_ladder.config import (
    CONTEXT_BEARING,
    CONTEXT_FREE,
    EXERCISE_TYPE_CONTEXT_CLASS,
    EXERCISE_TYPE_FAMILY,
    NOT_SENSE_ANCHORED,
    context_class,
    context_free_cap,
)
from services.vocabulary_ladder.exercise_caps import (
    anchor_of,
    apply_caps,
    cap_key,
    count_existing,
)


def _row(exercise_type, sense_id=1, **content):
    return {
        'exercise_type': exercise_type,
        'word_sense_id': sense_id,
        'content': dict(content),
    }


# ----------------------------------------------------------------------
# T3d.1 — the classification
# ----------------------------------------------------------------------

def test_every_known_exercise_type_is_classified():
    """A type that exists but is unclassified is the gap this task closes."""
    unclassified = set(EXERCISE_TYPE_FAMILY) - set(EXERCISE_TYPE_CONTEXT_CLASS)
    assert unclassified == set()


def test_classes_are_from_the_ratified_set():
    assert set(EXERCISE_TYPE_CONTEXT_CLASS.values()) <= {
        CONTEXT_FREE, CONTEXT_BEARING, NOT_SENSE_ANCHORED,
    }


@pytest.mark.parametrize('type_code', [
    'tone_id_word', 'hanzi_to_pinyin', 'pinyin_to_hanzi',
    'kanji_to_reading', 'reading_to_kanji', 'phonetic_recognition',
    'definition_match', 'classifier_match', 'counter_match',
    'synonym_antonym_match',
])
def test_word_property_types_are_context_free(type_code):
    assert context_class(type_code) == CONTEXT_FREE


@pytest.mark.parametrize('type_code', [
    'cloze_completion', 'cloze_typed', 'text_flashcard', 'listening_flashcard',
    'tl_nl_translation', 'nl_tl_translation', 'jumbled_sentence',
    'semantic_discrimination', 'spot_incorrect_sentence',
    'collocation_gap_fill', 'collocation_repair', 'morphology_slot',
    'particle_selection', 'word_family',
])
def test_sentence_anchored_types_are_context_bearing(type_code):
    """Each is mined from a different source passage, so each variant is a
    genuinely different question."""
    assert context_class(type_code) == CONTEXT_BEARING


def test_an_unknown_type_defaults_to_context_bearing():
    """Safe direction: 'leave it alone', not 'cap to one item per word'."""
    assert context_class('some_future_type') == CONTEXT_BEARING
    assert context_free_cap('some_future_type') is None


# ----------------------------------------------------------------------
# T3d.2 — the cap
# ----------------------------------------------------------------------

def test_context_free_types_are_capped_at_one():
    kept, dropped = apply_caps([
        _row('tone_id_word'), _row('tone_id_word'), _row('tone_id_word'),
    ])
    assert len(kept) == 1
    assert len(dropped) == 2


def test_definition_match_keeps_two():
    """Its variants differ in the distractor definitions they draw from other
    words, so a second item is a second question."""
    kept, dropped = apply_caps([_row('definition_match') for _ in range(5)])
    assert len(kept) == 2
    assert len(dropped) == 3


def test_context_bearing_types_are_never_capped():
    """Capping these would delete real questions — each is a different
    sentence from a different source passage."""
    kept, dropped = apply_caps([_row('cloze_completion') for _ in range(30)])
    assert len(kept) == 30
    assert dropped == []


def test_the_cap_is_per_type_not_per_word():
    """A flat per-word cap would delete whole skill types. 做 legitimately
    carries 12 distinct skills."""
    rows = [
        _row(t) for t in (
            'cloze_completion', 'cloze_typed', 'text_flashcard',
            'tl_nl_translation', 'nl_tl_translation', 'jumbled_sentence',
            'semantic_discrimination', 'spot_incorrect_sentence',
            'tone_id_word', 'hanzi_to_pinyin', 'pinyin_to_hanzi',
            'definition_match',
        )
    ]
    kept, dropped = apply_caps(rows)
    assert dropped == []
    assert len(kept) == 12


def test_the_cap_is_per_sense():
    kept, _ = apply_caps([
        _row('tone_id_word', sense_id=1),
        _row('tone_id_word', sense_id=2),
        _row('tone_id_word', sense_id=3),
    ])
    assert len(kept) == 3


def test_polyphonic_context_variants_both_survive():
    """A polyphonic word's reading genuinely depends on the sentence, so two
    readings in two sentences are two real questions."""
    kept, dropped = apply_caps([
        _row('hanzi_to_pinyin', context_sentence='他会读书'),
        _row('hanzi_to_pinyin', context_sentence='一会儿见'),
    ])
    assert len(kept) == 2
    assert dropped == []


def test_duplicates_within_one_polyphonic_context_are_still_capped():
    kept, dropped = apply_caps([
        _row('hanzi_to_pinyin', context_sentence='他会读书'),
        _row('hanzi_to_pinyin', context_sentence='他会读书'),
    ])
    assert len(kept) == 1
    assert len(dropped) == 1


def test_the_first_row_in_a_bucket_wins():
    """Order is preserved so a caller that renders its best variant first
    keeps it — the ladder renderer emits variant A before variant B."""
    first = _row('tone_id_word', options=['A'])
    kept, _ = apply_caps([first, _row('tone_id_word', options=['B'])])
    assert kept[0] is first


def test_rows_without_a_sense_are_passed_through():
    rows = [{'exercise_type': 'tone_id_word', 'content': {}} for _ in range(3)]
    kept, dropped = apply_caps(rows)
    assert len(kept) == 3
    assert dropped == []


# -- appending to already-stored content --

def test_existing_rows_count_towards_the_cap():
    """The LLM path appends to whatever a sense already has."""
    existing = count_existing([_row('tone_id_word')])
    kept, dropped = apply_caps([_row('tone_id_word')], existing)
    assert kept == []
    assert len(dropped) == 1


def test_existing_rows_in_a_different_context_do_not_consume_the_slot():
    existing = count_existing([
        _row('hanzi_to_pinyin', context_sentence='他会读书')
    ])
    kept, _ = apply_caps(
        [_row('hanzi_to_pinyin', context_sentence='一会儿见')], existing
    )
    assert len(kept) == 1


def test_existing_definition_match_leaves_room_for_one_more():
    existing = count_existing([_row('definition_match')])
    kept, dropped = apply_caps(
        [_row('definition_match'), _row('definition_match')], existing
    )
    assert len(kept) == 1
    assert len(dropped) == 1


# -- helpers --

def test_anchor_of_tolerates_a_missing_or_odd_content_blob():
    assert anchor_of({'content': None}) == ''
    assert anchor_of({'content': 'not a dict'}) == ''
    assert anchor_of({}) == ''


def test_cap_key_is_none_for_uncapped_rows():
    assert cap_key(_row('cloze_completion')) is None
    assert cap_key({'exercise_type': 'tone_id_word', 'content': {}}) is None
