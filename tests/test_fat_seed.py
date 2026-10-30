"""Fat-seed translation (services/vocabulary_ladder/fat_seed.py).

Offline: no database, no LLM. Each test runs the translated raw answer back
through the real remap / schema gate that upload_exercises.py uses, so the
named-field document is proven equivalent to a live-prompt answer.

Run: PYTHONPATH=. python -m pytest tests/test_fat_seed.py -q
"""

import pytest

from services.exercise_generation.schemas import validate_ladder_output
from services.vocabulary_ladder import fat_seed as fs
from services.vocabulary_ladder.asset_generators.prompt1_core import CoreAssetGenerator
from services.vocabulary_ladder.asset_generators.prompt2_exercises import ExerciseAssetGenerator
from services.vocabulary_ladder.asset_generators.prompt3_transforms import TransformAssetGenerator
from services.vocabulary_ladder.config import SENTENCE_ASSIGNMENTS_A
from services.vocabulary_ladder.validators import VocabAssetValidator


@pytest.fixture(autouse=True)
def _no_rule_skips(monkeypatch):
    """The suite must pass whatever FAT_SEED_LINT_SKIP is set to in the environment."""
    monkeypatch.setattr(fs, 'LINT_SKIP', frozenset())


def _bare(cls):
    """A generator without __init__ — the remap methods need no DB."""
    return object.__new__(cls)


def opts(correct='a', n=4, pos=False):
    out = []
    for i, t in enumerate([correct] + [f'd{i}' for i in range(1, n)]):
        o = {'text': t, 'is_correct': i == 0, 'explanation': f'{t} does not fit the meaning of this sentence'}
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
                'wrong_sentences': [{'text': f'w{i}', 'explanation': f'e{i}'} for i in range(3)]},
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
    assert p2['level_6']['wrong_sentences'][0] == {'text': 'w0', 'explanation': 'e0'}
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


def test_level_1_can_be_declined_and_is_then_not_required():
    variant = {**VARIANT, 'level_1': {'declined': 'no_minimal_pairs'}}
    answer, errors, _ = fs.variant_to_raw(variant, PLAN_VARIANT)
    assert errors == []
    assert answer['declined_levels'] == [1]
    assert '1' not in answer['p2']
    p2 = _bare(ExerciseAssetGenerator)._remap_output(answer['p2'], [1, 3, 6], SENTENCE_ASSIGNMENTS_A)
    assert 'level_1' not in p2
    ok, errs = VocabAssetValidator().validate_prompt2(p2, [3, 6])
    assert ok, errs
    # a declined level_1 never trips the A/B overlap lint
    declined = {'level_1': {'declined': 'no_minimal_pairs'}}
    assert fs.lint_variants({}, {'A': declined, 'B': declined}) == []


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


def _l1(*texts):
    return {'options': [{'text': 'X', 'is_correct': True, 'explanation': '.'}]
            + [{'text': t, 'is_correct': False, 'explanation': '.'} for t in texts]}


def test_lint_flags_copied_b_distractors_and_bad_level_7():
    doc = {'core': {'sentences': [{'text': '彼は来た。'}]}}
    variants = {
        'A': {'level_1': _l1('甲', '乙', '丙'),
              'level_7': {'incorrect_sentence': '彼は来た。', 'corrected_sentence': '彼が来た。'}},
        'B': {'level_1': _l1('丙', '乙', '甲'),
              'level_7': {'incorrect_sentence': 'x', 'corrected_sentence': 'x'}},
    }
    errs = fs.lint_variants(doc, variants)
    assert any('level_1' in e for e in errs)
    assert any('[A] level_7' in e and 'core' in e for e in errs)
    assert any('[B] level_7' in e and 'identical' in e for e in errs)


def test_lint_passes_independent_variants():
    variants = {'A': {'level_1': _l1('甲', '乙', '丙')}, 'B': {'level_1': _l1('丁', '戊', '己')}}
    assert fs.lint_variants({}, variants) == []


# ---------------------------------------------------------------------------
# Opt-in content lints (FAT_SEED_LINT_ALL_BLOCKS=1)
# ---------------------------------------------------------------------------

def _opts3(correct, distractors):
    """level_3 options: (text, explanation) pairs for the distractors."""
    return {'options': [{'text': correct, 'is_correct': True, 'explanation': '正解。文脈に合う。'}]
            + [{'text': t, 'is_correct': False, 'explanation': e} for t, e in distractors]}


GENERIC_L3 = _opts3('帯びる', [('食べる', '「食べる」は形は合うが意味が合わない。'),
                              ('洗う', '「洗う」は形は合うが意味が合わない。'),
                              ('聞く', '「聞く」は形は合うが意味が合わない。')])
SPECIFIC_L3 = _opts3('帯びる', [('走る', '「走る」は移動の動作で、色がつく意味にならない。'),
                               ('書く', '「書く」は文字を記す動作で、赤みが「つく」文脈に合わない。'),
                               ('泳ぐ', '「泳ぐ」は水中を進む動作で、空の色の変化を表せない。')])
OBI_DOC = {'lemma': '帯びる',
           'core': {'sentences': [{'text': '空が赤みを帯びる。', 'target_word': '帯びる'},
                                  {'text': '葉が黄色みを帯びました。', 'target_word': '帯びました'}],
                    'morphological_forms': [{'form': '帯びた', 'label': '活用'}]}}


def test_new_lints_stay_off_without_the_opt_in(monkeypatch):
    monkeypatch.setattr(fs, 'LINT_ALL', False)
    variants = {'A': {'level_3': GENERIC_L3,
                      'level_7': {'incorrect_sentence': 'この坂は急で大変だ。', 'corrected_sentence': 'この坂は急だ。'}},
                'B': {}}
    assert fs.lint_variants(OBI_DOC, variants) == []


def test_lint_all_flags_generic_level_3_explanations(monkeypatch):
    monkeypatch.setattr(fs, 'LINT_ALL', True)
    errs = fs.lint_variants(OBI_DOC, {'A': {'level_3': GENERIC_L3}, 'B': {'level_3': SPECIFIC_L3}})
    assert len(errs) == 1 and errs[0].startswith('[A] level_3') and '食べる' in errs[0] and '聞く' in errs[0]
    # a short restatement of the rule is generic even when worded differently
    short = _opts3('帯びる', [('食べる', '意味が合わない。'), ('洗う', '「洗う」は汚れを落とす動作で、色がつく意味にならない。'),
                           ('聞く', '「聞く」は音を受け取る動作で、空の色の変化を表せない。')])
    errs = fs.lint_variants(OBI_DOC, {'A': {'level_3': short}, 'B': {}})
    assert len(errs) == 1 and '「食べる」' in errs[0] and '洗う' not in errs[0]
    # long explanations that share wording are left alone (the judge does not mind them)
    same_long = _opts3('帯びる', [(t, f'「{t}」は形は合うが、空が赤みを帯びるという文脈では意味が合わない。')
                                for t in ('食べる', '洗う', '聞く')])
    assert fs.lint_variants(OBI_DOC, {'A': {'level_3': same_long}, 'B': {}}) == []


def test_lint_all_flags_shared_level_6_explanations(monkeypatch):
    monkeypatch.setattr(fs, 'LINT_ALL', True)

    def l6(tag, *expl):
        return {'correct_sentence_index': 0,
                'wrong_sentences': [{'text': f'{tag}{i}', 'explanation': e} for i, e in enumerate(expl)]}
    shared = fs.lint_variants(OBI_DOC, {'A': {'level_6': l6('a', '語義の誤り。', '語義の誤り。', '助詞の誤り。')}, 'B': {}})
    assert shared == ['[A] level_6: wrong sentences share one explanation — each needs its own, naming how '
                      'the target is misused in that sentence']
    copied = fs.lint_variants(OBI_DOC, {'A': {'level_6': l6('a', '大きさは色ではない。', 'x', 'y')},
                                        'B': {'level_6': l6('b', '大きさは色ではない。', 'p', 'q')}})
    assert copied == ['[B] level_6: explanations repeat A word for word — write B independently']
    assert fs.lint_variants(OBI_DOC, {'A': {'level_6': l6('a', 'a', 'b', 'c')}, 'B': {'level_6': l6('b', 'd', 'e', 'f')}}) == []


def test_lint_all_checks_level_7_pairs(monkeypatch):
    monkeypatch.setattr(fs, 'LINT_ALL', True)

    def l7(wrong, fixed):
        return {'A': {'level_7': {'incorrect_sentence': wrong, 'corrected_sentence': fixed}}, 'B': {}}
    doc = {'lemma': '急速', 'core': {'sentences': [{'text': '急速に広がる。', 'target_word': '急速に'}]}}
    [err] = fs.lint_variants(doc, l7('この坂は急で、歩くのが大変だ。', 'この坂は急だ。'))
    assert 'does not contain 「急速」' in err
    # the target in a wrong conjugation is still the target
    doc2 = {'lemma': '減らす', 'core': {'sentences': [{'text': '量を減らした。', 'target_word': '減らした'}]}}
    assert fs.lint_variants(doc2, l7('机の数を減れば、広く使える。', '机の数を減らせば、広く使える。')) == []
    assert fs.lint_variants({'lemma': 'プリント', 'core': {}}, l7('写真をプリンする。', '写真をプリントする。')) == []
    # one error, one fix: fine, even if the fix also moves a comma
    assert fs.lint_variants(OBI_DOC, l7('海が緑みが帯びる。', '海が緑みを帯びる。')) == []
    assert fs.lint_variants(OBI_DOC, l7('空は、赤みに帯びる。', '空は赤みを帯びる。')) == []
    [err] = fs.lint_variants(OBI_DOC, l7('彼は帯びをたくさん持ちたがる。', '彼は帯びをあまり持ちたがらない。'))
    assert 'changes 2 separate places' in err and '「たくさん→あまり」' in err
    # the single edit must be on the target or the word right next to it
    eki = {'lemma': '液', 'core': {'sentences': [{'text': '白い液が流れる。', 'target_word': '液'}]}}
    [err] = fs.lint_variants(eki, l7('白い液が机の上に咲いた。', '白い液が机の上に広がった。'))
    assert '「咲い→広がっ」' in err and 'away from 「液」' in err
    keii = {'lemma': '敬意', 'core': {'sentences': [{'text': '敬意を払う。', 'target_word': '敬意'}]}}
    assert fs.lint_variants(keii, l7('先生に敬意を食べる。', '先生に敬意を払う。')) == []   # one particle between
    assert fs.lint_variants(keii, l7('先生へ敬意を払う。', '先生に敬意を払う。')) == []   # error two characters before the target: へ敬 — adjacent enough
    [err] = fs.lint_variants(keii, l7('先生に深い敬意を毎日払いました。', '先生に深い敬意を毎日払います。'))
    assert 'away from 「敬意」' in err


def test_lint_all_checks_the_particle_slot_the_renderer_blanks(monkeypatch):
    monkeypatch.setattr(fs, 'LINT_ALL', True)
    spans = {'水に溶けると、塩はイオンになる。': [{'particle': 'に', 'index': 1}, {'particle': 'と', 'index': 5},
                                           {'particle': 'は', 'index': 8}, {'particle': 'に', 'index': 12}],
             '先生に敬意を払います。': [{'particle': 'に', 'index': 2}, {'particle': 'を', 'index': 5}],
             '敬意を深く持つ。': [{'particle': 'を', 'index': 2}]}
    monkeypatch.setattr(fs, '_tokenised_particles', lambda text: spans.get(text, []))

    def run(lemma, anchor, particle, target_word=None, pos='名詞'):
        doc = {'lemma': lemma, 'core': {'pos': pos, 'sentences': [{'text': anchor, 'target_word': target_word or lemma}]}}
        variants = {'A': {'particle_selection': {'blanked_particle': particle, 'options': [], 'error_tags': {}}}, 'B': {}}
        item = {'variants': {'A': {'typed': {'particle_selection': {'sentence_index': 0}}}, 'B': {}}}
        return fs.lint_variants(doc, variants, item)

    [err] = run('イオン', '水に溶けると、塩はイオンになる。', 'に')
    assert 'blanks the FIRST one' in err and '2 times' in err
    [err] = run('イオン', '水に溶けると、塩はイオンになる。', 'は')
    assert 'does not attach to 「イオン」' in err
    [err] = run('イオン', '水に溶けると、塩はイオンになる。', 'を')
    assert 'is not a particle of the anchor' in err and 'と／に／は' in err
    assert run('敬意', '先生に敬意を払います。', 'を') == []          # noun + particle
    assert run('払う', '先生に敬意を払います。', 'を', '払います', '動詞') == []  # particle right before the verb
    assert run('持つ', '敬意を深く持つ。', 'を', pos='動詞') == []            # a short adverb in between is fine
    [err] = run('敬意', '先生に敬意を払います。', 'に')                     # に marks 先生, not the noun target
    assert 'does not attach to 「敬意」' in err
    # no tokeniser output, or no plan item: the slot lint stays silent
    monkeypatch.setattr(fs, '_tokenised_particles', lambda text: [])
    assert run('イオン', '水に溶けると、塩はイオンになる。', 'は') == []
    doc = {'lemma': 'イオン', 'core': {'sentences': [{'text': '水に溶けると、塩はイオンになる。'}]}}
    assert fs.lint_variants(doc, {'A': {'particle_selection': {'blanked_particle': 'は'}}, 'B': {}}) == []


def test_lint_skip_demotes_single_rules(monkeypatch):
    monkeypatch.setattr(fs, 'LINT_ALL', True)
    variants = {'A': {'level_3': GENERIC_L3,
                      'level_7': {'incorrect_sentence': 'この坂は急で大変だ。', 'corrected_sentence': 'この坂は急だ。'}},
                'B': {}}
    assert len(fs.lint_variants(OBI_DOC, variants)) == 2
    monkeypatch.setattr(fs, 'LINT_SKIP', frozenset({'l3_generic_expl'}))
    [err] = fs.lint_variants(OBI_DOC, variants)
    assert err.startswith('[A] level_7')
    monkeypatch.setattr(fs, 'LINT_SKIP', frozenset({'l3_generic_expl', 'l7_target_absent'}))
    assert fs.lint_variants(OBI_DOC, variants) == []


def test_content_lints_are_available_as_tagged_warnings(monkeypatch):
    monkeypatch.setattr(fs, 'LINT_ALL', False)   # the warning view ignores the env gates
    monkeypatch.setattr(fs, 'LINT_SKIP', frozenset({'l3_generic_expl'}))
    variants = {'A': {'level_3': GENERIC_L3,
                      'level_7': {'incorrect_sentence': 'この坂は急で大変だ。', 'corrected_sentence': 'この坂は急だ。'}},
                'B': {}}
    assert fs.lint_variants(OBI_DOC, variants) == []
    rules = [r for r, _ in fs.content_lints(OBI_DOC, variants)]
    assert rules == ['l3_generic_expl', 'l7_target_absent']
