# tests/test_bundle_mapping.py
"""Mapping round-trip: bundle-shaped raw output -> EXISTING word_assets content.

Every ``build_*`` function in ``services.vocabulary_ladder.bundle.mapping``
is a thin dispatcher onto the SAME remap methods
(``ExerciseAssetGenerator._remap_output``, ``TransformAssetGenerator.
_remap_output``, ``MorphologySlotGenerator._remap``,
``CollocationRepairGenerator._remap``, ``TypedLLMGenerator.fragment_from_raw``)
and the SAME validators (``VocabAssetValidator.validate_prompt2`` /
``validate_prompt3`` / the per-type ``services.exercise_generation.schemas``
gate) the live per-generator pipeline already uses. These tests build raw
bundle blocks by hand, following the numeric-key contract documented in
``migrations/exercise_gen_bundle_prompts_draft.sql``, and assert the mapped
output is accepted by those SAME live functions — i.e. this is a contract
test against production code, not a reimplementation of it.

``tests/fixtures/bundle/baseline_{en,ja}_*_rows.json`` hold trimmed REAL
rendered exercise rows from the Phase 0 baseline eval run
(data/eval/runs/baseline_en/40142.json, baseline_ja/35001.json) — used here
to cross-check that the descriptive field names this module's output is
expected to carry (options / correct_answer / explanations / sentence_index
/ ...) match what a real, currently-shipping exercise actually contains, so
the "round trip against real asset shapes" isn't only self-referential
against the validator.
"""

import json
from pathlib import Path

import pytest

from services.vocabulary_ladder.bundle import mapping
from services.vocabulary_ladder.validators import VocabAssetValidator

FIXTURES = Path(__file__).parent / 'fixtures' / 'bundle'

LANG_EN, LANG_ZH, LANG_JA = 2, 1, 3

validator = VocabAssetValidator()


def _load_rows(name):
    data = json.loads((FIXTURES / name).read_text(encoding='utf-8'))
    return {(r['exercise_type'], r['tags'].get('variant')): r for r in data['exercise_rows']}


EN_ROWS = _load_rows('baseline_en_40142_rows.json')
JA_ROWS = _load_rows('baseline_ja_35001_rows.json')


# ---------------------------------------------------------------------------
# P2 family (levels 1, 3, 5, 6) — 1-based option contract
# ---------------------------------------------------------------------------

def _p2_option(text, correct, explanation):
    return {'1': text, '2': correct, '3': explanation}


def test_build_p2_content_l1_l3_l6_valid_and_matches_real_field_names():
    raw_variant = {
        '1': [
            _p2_option('cat', True, 'the target word'),
            _p2_option('cot', False, 'audio-confusable, wrong meaning'),
            _p2_option('cut', False, 'audio-confusable, wrong meaning'),
            _p2_option('cap', False, 'audio-confusable, wrong meaning'),
        ],
        '3': [
            _p2_option('run', True, 'fits the blank'),
            _p2_option('walk', False, 'wrong register'),
            _p2_option('jog', False, 'wrong aspect'),
            _p2_option('sprint', False, 'wrong valency'),
        ],
        '6': {
            '1': 3,
            '2': [
                {'1': 'He run to the store yesterday.', '2': 'subject-verb agreement error'},
                {'1': 'He runs to the store yesterday.', '2': 'tense mismatch with yesterday'},
                {'1': 'He running to the store yesterday.', '2': 'missing auxiliary'},
            ],
        },
    }
    sentence_assignments = {3: 0, 5: 2, 6: 3}
    content, errors = mapping.build_p2_content(
        raw_variant, [1, 3, 6], sentence_assignments, LANG_EN,
    )
    assert errors == []
    assert set(content) == {'level_1', 'level_3', 'level_6'}

    # Field-name parity with a REAL rendered L1 exercise (options/correct_answer
    # both appear pre- and post-render, just nested differently).
    real_l1 = EN_ROWS[('phonetic_recognition', 'A')]['content']
    assert 'options' in real_l1 and 'correct_answer' in real_l1
    assert content['level_1']['correct_answer'] == 'cat'
    assert len(content['level_1']['options']) == 4

    assert content['level_6']['correct_sentence_index'] == 3
    assert len(content['level_6']['wrong_sentences']) == 3

    valid, verrors = validator.validate_prompt2(content, [1, 3, 6])
    assert valid, verrors


def test_build_p2_content_missing_level_reports_validator_error():
    raw_variant = {'3': [_p2_option('run', True, 'ok')] * 4}  # L6 requested but absent
    content, errors = mapping.build_p2_content(raw_variant, [3, 6], {3: 0, 6: 3}, LANG_EN)
    assert any('level_6' in e for e in errors)


def test_build_p2_content_no_levels_requested_is_clean_skip():
    content, errors = mapping.build_p2_content({}, [], {}, LANG_EN)
    assert content == {}
    assert errors == []


# ---------------------------------------------------------------------------
# P3 monolith — level 7
# ---------------------------------------------------------------------------

def test_build_l7_fragment_valid():
    raw_variant = {
        '7': {
            '1': 'She go to school every day.',
            '2': 'She goes to school every day.',
            '3': 'subject-verb agreement error',
            '4': [0, 1, 2],
        },
    }
    fragment, errors = mapping.build_l7_fragment(raw_variant, LANG_EN)
    assert errors == []
    assert fragment['level_7']['incorrect_sentence'] == 'She go to school every day.'

    real_l7 = EN_ROWS[('spot_incorrect_sentence', 'A')]['content']
    assert 'sentences' in real_l7  # renderer's own shape; confirms L7 data survives to render


def test_build_l7_fragment_identical_sentences_is_invalid():
    raw_variant = {'7': {'1': 'same', '2': 'same', '3': 'x', '4': [0]}}
    fragment, errors = mapping.build_l7_fragment(raw_variant, LANG_EN)
    assert errors  # incorrect == corrected must be rejected


def test_build_l7_fragment_not_requested_is_clean_skip():
    fragment, errors = mapping.build_l7_fragment({}, LANG_EN)
    assert fragment == {}
    assert errors == []


# ---------------------------------------------------------------------------
# Split family — L4 morphology_slot, L8 collocation_repair (0-based contract)
# ---------------------------------------------------------------------------

def _split_option(text, correct, explanation, pos=None):
    opt = {'0': text, '1': correct, '2': explanation}
    if pos is not None:
        opt['3'] = pos
    return opt


def test_build_l4_fragment_valid():
    raw = {
        '0': [
            _split_option('ran', True, "past simple, matches 'yesterday'"),
            _split_option('run', False, 'present tense, wrong for yesterday'),
            _split_option('running', False, 'gerund, wrong slot'),
            _split_option('runned', False, 'not a real form'),
        ],
        '1': 'run',
        '2': 'past simple',
    }
    fragment, errors = mapping.build_l4_fragment(raw, sentence_index=1, language_id=LANG_EN)
    assert errors == []
    assert fragment['level_4']['correct_form'] == 'ran'
    assert fragment['level_4']['base_form'] == 'run'
    assert fragment['level_4']['sentence_index'] == 1


def test_build_l4_fragment_escape_is_clean_skip():
    fragment, errors = mapping.build_l4_fragment({'9': 'no_inflection'}, 1, LANG_ZH)
    assert fragment == {}
    assert errors == []


def test_build_l4_fragment_none_block_is_clean_skip():
    fragment, errors = mapping.build_l4_fragment(None, 1, LANG_EN)
    assert fragment == {}
    assert errors == []


def test_build_l4_fragment_schema_failure_falls_back():
    # Only 3 options instead of 4 -> schema-gate rejects, caller should fall back.
    raw = {'0': [_split_option('ran', True, 'ok')] * 3, '1': 'run', '2': 'past simple'}
    fragment, errors = mapping.build_l4_fragment(raw, 1, LANG_EN)
    assert fragment is None
    assert errors


def test_build_l8_fragment_valid():
    raw = {
        '0': [
            _split_option('brew', True, "'brew coffee' is idiomatic"),
            _split_option('boil', False, 'wrong collocate'),
            _split_option('fry', False, 'wrong collocate'),
            _split_option('bake', False, 'wrong collocate'),
        ],
        '1': 'cook',  # the word actually planted in the sentence — must not be one of the 4 options
    }
    fragment, errors = mapping.build_l8_fragment(raw, sentence_index=4, language_id=LANG_EN)
    assert errors == []
    assert fragment['level_8']['correct_collocate'] == 'brew'
    assert fragment['level_8']['error_collocate'] == 'cook'


def test_build_l8_fragment_error_collocate_duplicated_in_options_is_rejected():
    raw = {
        '0': [
            _split_option('brew', True, 'ok'),
            _split_option('brew', False, 'duplicate of the planted error'),
            _split_option('boil', False, 'ok'),
            _split_option('fry', False, 'ok'),
        ],
        '1': 'brew',  # same text as the correct option
    }
    fragment, errors = mapping.build_l8_fragment(raw, 4, LANG_EN)
    assert fragment is None
    assert errors


# ---------------------------------------------------------------------------
# Typed family — synonym_antonym_match, word_family, particle_selection
# ---------------------------------------------------------------------------

def test_build_typed_fragment_syn_ant_valid():
    raw = {
        '0': [
            _split_option('joyful', True, 'synonym of happy'),
            _split_option('sad', False, 'antonym, not synonym'),
            _split_option('angry', False, 'unrelated'),
            _split_option('tired', False, 'unrelated'),
        ],
        '1': 'synonym',
    }
    fragment, errors = mapping.build_typed_fragment(
        'synonym_antonym_match', raw, sentence_index=3, language_id=LANG_EN, sense_id=1,
    )
    assert errors == []
    assert fragment['synonym_antonym_match']['correct_answer'] == 'joyful'
    assert fragment['synonym_antonym_match']['relation'] == 'synonym'


def test_build_typed_fragment_word_family_requires_part_of_speech():
    raw = {
        '0': [
            _split_option('decisive', True, 'real derived word', pos='adjective'),
            _split_option('decisionment', False, 'invented', pos='noun'),
            _split_option('decideful', False, 'invented', pos='adjective'),
            _split_option('decisory', False, 'invented', pos='adjective'),
        ],
        '1': 'decide',
    }
    fragment, errors = mapping.build_typed_fragment(
        'word_family', raw, sentence_index=4, language_id=LANG_EN, sense_id=1,
    )
    assert errors == []
    assert fragment['word_family']['stem'] == 'decide'

    # Missing part_of_speech on an option must fail the schema gate.
    bad = {
        '0': [
            {'0': 'decisive', '1': True, '2': 'ok'},  # no '3' (part_of_speech)
            _split_option('decisionment', False, 'x', pos='noun'),
            _split_option('decideful', False, 'x', pos='adjective'),
            _split_option('decisory', False, 'x', pos='adjective'),
        ],
        '1': 'decide',
    }
    fragment, errors = mapping.build_typed_fragment(
        'word_family', bad, sentence_index=4, language_id=LANG_EN, sense_id=1,
    )
    assert fragment is None
    assert errors


def test_build_typed_fragment_particle_selection_ja_valid_matches_real_shape():
    raw = {
        '0': [
            _split_option('に', True, 'direction marker fits'),
            _split_option('へ', False, 'also natural — must not be offered as-is normally'),
            _split_option('で', False, 'wrong particle for this verb'),
            _split_option('を', False, 'wrong particle for this verb'),
        ],
        '1': 'に',
        '2': {'へ': 'direction', 'で': 'object_marking', 'を': 'object_marking'},
    }
    fragment, errors = mapping.build_typed_fragment(
        'particle_selection', raw, sentence_index=1, language_id=LANG_JA, sense_id=2,
    )
    assert errors == []
    assert fragment['particle_selection']['blanked_particle'] == 'に'
    assert fragment['particle_selection']['correct_answer'] == 'に'

    real_particle = JA_ROWS[('particle_selection', 'A')]['content']
    assert 'options' in real_particle and 'correct_answer' in real_particle
    assert set(fragment['particle_selection']) >= {'options', 'correct_answer', 'explanations'}


def test_build_typed_fragment_particle_mismatch_between_blank_and_correct_option_rejected():
    raw = {
        '0': [
            _split_option('に', True, 'ok'),  # marked correct, but blanked_particle says 'へ'
            _split_option('へ', False, 'ok'),
            _split_option('で', False, 'ok'),
            _split_option('を', False, 'ok'),
        ],
        '1': 'へ',
    }
    fragment, errors = mapping.build_typed_fragment(
        'particle_selection', raw, sentence_index=1, language_id=LANG_JA, sense_id=2,
    )
    assert fragment is None
    assert errors


def test_build_typed_fragment_escape_is_clean_skip():
    fragment, errors = mapping.build_typed_fragment(
        'synonym_antonym_match', {'9': 'no_relation'}, 3, LANG_EN, sense_id=1,
    )
    assert fragment == {}
    assert errors == []


def test_build_typed_fragment_none_block_is_clean_skip():
    fragment, errors = mapping.build_typed_fragment(
        'word_family', None, 4, LANG_EN, sense_id=1,
    )
    assert fragment == {}
    assert errors == []


def test_build_typed_fragment_unknown_type_code_fails():
    fragment, errors = mapping.build_typed_fragment(
        'not_a_real_type', {'0': [], '1': 'x'}, 0, LANG_EN, sense_id=1,
    )
    assert fragment is None
    assert errors
