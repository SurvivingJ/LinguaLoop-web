"""QuestionGenerator._build_waves and ._shuffle_choices.

Both exist because the claude-cli transport has no sampling control: two
same-type calls in one wave return the same question, and the writer puts the
answer in the same position every time.
"""

from services.test_generation.agents.question_generator import QuestionGenerator


def _codes(waves):
    return [[code for _, code in wave] for wave in waves]


def test_waves_never_repeat_a_type():
    mix = ['literal_detail', 'literal_detail', 'vocabulary_context',
           'vocabulary_context', 'main_idea']
    waves = QuestionGenerator._build_waves(mix, 2)
    assert _codes(waves) == [
        ['literal_detail', 'vocabulary_context'],
        ['literal_detail', 'vocabulary_context'],
        ['main_idea'],
    ]
    for wave in waves:
        codes = [code for _, code in wave]
        assert len(codes) == len(set(codes))


def test_waves_cover_every_index_once():
    mix = ['a', 'a', 'a', 'b', 'c', 'b']
    waves = QuestionGenerator._build_waves(mix, 2)
    indices = sorted(idx for wave in waves for idx, _ in wave)
    assert indices == list(range(len(mix)))
    assert all(1 <= len(w) <= 2 for w in waves)


def test_waves_of_distinct_types_match_plain_chunking():
    mix = ['a', 'b', 'c', 'd', 'e']
    assert _codes(QuestionGenerator._build_waves(mix, 2)) == [['a', 'b'], ['c', 'd'], ['e']]


def test_waves_empty_mix():
    assert QuestionGenerator._build_waves([], 2) == []


def _entry(question='Q?', answer='right'):
    return {
        'question': question,
        'choices': [answer, 'w1', 'w2', 'w3'],
        'answer': answer,
        'correct_answer_index': 0,
        'distractor_types': [None, 'semantic', 'grammatical', 'contextual'],
        'type_code': 'literal_detail',
    }


def test_shuffle_keeps_answer_index_and_types_aligned():
    out = QuestionGenerator._shuffle_choices(_entry())
    assert sorted(out['choices']) == sorted(_entry()['choices'])
    assert out['choices'][out['correct_answer_index']] == 'right'
    assert out['distractor_types'][out['correct_answer_index']] is None
    original = dict(zip(_entry()['choices'], _entry()['distractor_types']))
    assert dict(zip(out['choices'], out['distractor_types'])) == original


def test_shuffle_is_deterministic_and_does_not_mutate_input():
    entry = _entry()
    first = QuestionGenerator._shuffle_choices(entry)
    second = QuestionGenerator._shuffle_choices(_entry())
    assert first['choices'] == second['choices']
    assert entry['choices'] == _entry()['choices']


def test_shuffle_spreads_answer_positions():
    positions = {
        QuestionGenerator._shuffle_choices(_entry(question=f'Q{i}?'))['correct_answer_index']
        for i in range(40)
    }
    assert positions == {0, 1, 2, 3}


def test_shuffle_leaves_entry_alone_when_answer_not_in_choices():
    entry = _entry()
    entry['answer'] = 'missing'
    assert QuestionGenerator._shuffle_choices(entry) is entry
