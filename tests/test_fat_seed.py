"""Fat-seed translation (services/vocabulary_ladder/fat_seed.py).

Offline: no database, no LLM. Each test runs the translated raw answer back
through the real remap / schema gate that upload_exercises.py uses, so the
named-field document is proven equivalent to a live-prompt answer.

Run: PYTHONPATH=. python -m pytest tests/test_fat_seed.py -q
"""

from services.exercise_generation.schemas import validate_ladder_output
from services.vocabulary_ladder import fat_seed as fs
from services.vocabulary_ladder.asset_generators.prompt1_core import CoreAssetGenerator
from services.vocabulary_ladder.asset_generators.prompt2_exercises import ExerciseAssetGenerator
from services.vocabulary_ladder.asset_generators.prompt3_transforms import TransformAssetGenerator
from services.vocabulary_ladder.config import SENTENCE_ASSIGNMENTS_A
from services.vocabulary_ladder.validators import VocabAssetValidator


def _bare(cls):
    """A generator without __init__ — the remap methods need no DB."""
    return object.__new__(cls)


def opts(correct='a', n=4, pos=False):
    out = []
    for i, t in enumerate([correct] + [f'd{i}' for i in range(1, n)]):
        o = {'text': t, 'is_correct': i == 0, 'explanation': f'why {t}'}
        if pos:
            o['part_of_speech'] = 'noun'
        out.append(o)
    return out


CORE = {
    'pos': 'verb', 'semantic_class': 'action', 'definition': 'to move fast',
    'primary_collocate': 'race', 'pronunciation': 'run', 'ipa': 'rʌn',
    'syllable_count': 1, 'register': 'neutral', 'sense_fingerprint': 'verb | move fast',
    'morphological_forms': [{'form': 'ran', 'label': 'past'},
                            {'form': 'running', 'label': 'progressive'}],
    'sentences': [{'text': f'I run {i}.', 'target_word': 'run', 'complexity_tier': 'T2',
                   'sentence_source': 'mined'} for i in range(10)],
    'unknown_field': 'dropped',
}

PLAN_VARIANT = {
    'sentence_assignments': {str(k): v for k, v in SENTENCE_ASSIGNMENTS_A.items()},
    'p2': {'levels': [1, 3, 6]},
    'p3': {'levels': [7], 'l7_correct_indices': [0, 1, 2]},
    'l4': {'sentence_index': 1, 'prompt_version': 2},
    'l8': {'sentence_index': 4, 'prompt_version': 2},
    'typed': {'synonym_antonym_match': {'sentence_index': 3, 'prompt_version': 2},
              'word_family': {'sentence_index': 4, 'prompt_version': 2}},
}

VARIANT = {
    'level_1': {'options': opts('run', n=6)},
    'level_3': {'options': opts('run')},
    'level_6': {'correct_sentence_index': 3,
                'wrong_sentences': [{'text': f'w{i}', 'explanation': 'e'} for i in range(3)]},
    'level_7': {'incorrect_sentence': 'I runned.', 'corrected_sentence': 'I ran.',
                'error_description': 'irregular past', 'correct_sentence_indices': [0, 1, 2]},
    'level_4': {'options': opts('ran'), 'base_form': 'run', 'form_label': 'past'},
    'level_8': {'declined': 'no_collocation'},
    'synonym_antonym_match': {'relation': 'synonym', 'options': opts('sprint')},
    'word_family': {'stem': 'run', 'options': opts('runner', pos=True)},
    'level_9': {'surplus': True},
}


def test_core_round_trips_through_the_p1_remap():
    raw = fs.core_to_raw(CORE)
    assert set(raw) == {str(k) for k in range(1, 12)}
    content = _bare(CoreAssetGenerator)._remap_output(raw)
    expected = {k: v for k, v in CORE.items() if k != 'unknown_field'}
    # sentence_source is derived on upload, never taken from the author
    expected['sentences'] = [{k: v for k, v in s.items() if k != 'sentence_source'}
                             for s in CORE['sentences']]
    assert content == expected
    ok, errors, _ = VocabAssetValidator().validate_prompt1(content, 2)
    assert ok, errors


def test_variant_translates_to_every_live_contract():
    answer, errors, surplus = fs.variant_to_raw(VARIANT, PLAN_VARIANT)
    assert errors == []
    assert surplus == ['level_9']

    p2 = _bare(ExerciseAssetGenerator)._remap_output(answer['p2'], [1, 3, 6], SENTENCE_ASSIGNMENTS_A)
    assert p2['level_3']['correct_answer'] == 'run'
    assert len(p2['level_1']['options']) == 6
    assert p2['level_6']['wrong_sentences'][0] == {'text': 'w0', 'explanation': 'e'}
    ok, errs = VocabAssetValidator().validate_prompt2(p2, [1, 3, 6])
    assert ok, errs

    p3 = _bare(TransformAssetGenerator)._remap_output(answer['p3'], [7])
    assert p3['level_7']['corrected_sentence'] == 'I ran.'

    assert answer['l4']['3'] == 1  # sentence index fixed by the plan, not the author
    assert validate_ladder_output('morphology_slot', 2, answer['l4']) == []
    assert answer['l8'] == {'9': 'no_collocation'}
    assert validate_ladder_output('collocation_repair', 2, answer['l8']) == []
    for code in ('synonym_antonym_match', 'word_family'):
        assert validate_ladder_output(code, 2, answer['typed'][code]) == [], code


def test_missing_and_undeclinable_blocks_are_errors():
    variant = {k: v for k, v in VARIANT.items() if k not in ('level_3', 'word_family')}
    variant['level_6'] = {'declined': True}
    _, errors, _ = fs.variant_to_raw(variant, PLAN_VARIANT)
    assert 'level_3: missing' in errors
    assert 'word_family: missing' in errors
    assert any(e.startswith('level_6: cannot be declined') for e in errors)


def test_wrong_escape_token_is_an_error():
    variant = {**VARIANT, 'level_4': {'declined': 'no_collocation'}}
    _, errors, _ = fs.variant_to_raw(variant, PLAN_VARIANT)
    assert any("level_4: declined token must be 'no_inflection'" in e for e in errors)


def test_expected_blocks_follow_the_plan():
    assert fs.expected_blocks(PLAN_VARIANT) == [
        'level_1', 'level_3', 'level_6', 'level_7', 'level_4', 'level_8',
        'synonym_antonym_match', 'word_family']


def test_exercise_answer_prefixes_variants():
    item = {'sense_id': 7, 'variants': {'A': PLAN_VARIANT, 'B': PLAN_VARIANT}}
    entry, errors, _ = fs.exercise_answer({'variants': {'A': VARIANT}}, item)
    assert entry['sense_id'] == 7 and set(entry) == {'sense_id', 'A', 'B'}
    assert errors and all(e.startswith('[B] ') for e in errors)


def test_changed_paths_names_leaves():
    before = {'core': {'definition': 'x', 'sentences': [{'text': 'a'}, {'text': 'b'}]}}
    after = {'core': {'definition': 'x', 'sentences': [{'text': 'a'}, {'text': 'c'}]}}
    assert fs.changed_paths(before, after) == ['core.sentences[1].text']
    assert fs.changed_paths(before, before) == []
