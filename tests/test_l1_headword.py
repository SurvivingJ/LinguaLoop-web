"""TASK-803: ja L1 must be built from the dictionary form, not the sentence stem.

P1 sentences carry the target as it stands in the sentence (超え, かけ) while
P1's ``pronunciation`` is the dictionary reading (こえる, かける). The phonetic
trie is keyed on that reading, so handing the judge and the learner the stem
put every candidate two morae from a form that was never the answer and the
L1 item was dropped. Offline: a hand-built trie, a fake db, a stubbed judge.
"""

import pytest

from services.vocabulary_ladder import exercise_renderer, l1_lookup
from services.vocabulary_ladder.phonetic_trie.ja_mora import to_morae
from services.vocabulary_ladder.phonetic_trie.trie import PhoneticTrie


class _Resp:
    def __init__(self, data):
        self.data = data


class _FakeDb:
    """Answers the one query the renderer makes: dim_word_senses -> lemma."""

    def __init__(self, lemma=None, fail=False):
        self._lemma = lemma
        self._fail = fail

    def table(self, _name):
        return self

    def select(self, *_a):
        return self

    def eq(self, *_a):
        return self

    def single(self):
        return self

    def execute(self):
        if self._fail:
            raise RuntimeError('db down')
        return _Resp({'dim_vocabulary': {'lemma': self._lemma}})


def _trie():
    return PhoneticTrie().build([
        (to_morae('こえる'), '超える'),
        (to_morae('きえる'), '消える'),      # 1 mora from こえる
        (to_morae('こける'), '転ける'),      # 1 mora from こえる
        (to_morae('こえた'), '肥えた'),      # 1 mora from こえる
        (to_morae('かける'), '掛ける'),
        (to_morae('かけろ'), '欠けろ'),      # 1 mora from かける
        (to_morae('かげる'), '陰る'),        # 1 mora from かける
        (to_morae('あける'), '開ける'),      # 1 mora from かける
        (to_morae('こえ'), '声'),            # 2 morae shorter -- the stem's own neighbourhood
    ])


@pytest.fixture
def judged(monkeypatch):
    """Route the L1 trie to the hand-built one and record what the judge is asked."""
    monkeypatch.setattr(l1_lookup, '_get_trie', lambda language_id, path: _trie())
    monkeypatch.setattr(l1_lookup, 'zipf_frequency', lambda word, lang: 5.0)
    monkeypatch.setattr(l1_lookup, 'tier_for_lemma', lambda lemma, language_id: 'T3')
    monkeypatch.setattr(l1_lookup, 'profile_for_tier', lambda tier: {'hard_floor': 0.0})
    seen = {}

    def fake_judge(db, correct, candidates, language_id):
        seen['correct'] = correct
        seen['candidates'] = list(candidates)
        return list(candidates), {'judged': True}

    import services.exercise_generation.judges.l1_distractor as judge_module
    monkeypatch.setattr(judge_module, 'filter_l1_distractors', fake_judge)
    return seen


def _core(reading, stem):
    return {
        'pronunciation': reading,
        'definition': 'x',
        'sentences': [{'text': f'ここで{stem}た。', 'target_word': stem}],
    }


@pytest.mark.parametrize('lemma,stem,reading,neighbours', [
    ('超える', '超え', 'こえる', {'消える', '転ける', '肥えた'}),
    ('掛ける', 'かけ', 'かける', {'欠けろ', '陰る', '開ける', '転ける'}),
])
def test_l1_uses_dictionary_form_not_sentence_stem(judged, lemma, stem, reading, neighbours):
    renderer = exercise_renderer.LadderExerciseRenderer(db=_FakeDb(lemma))

    row = renderer._render_phonetic(_core(reading, stem), {}, {}, 1, 3, None)

    assert judged['correct'] == lemma
    assert row is not None
    assert row['correct_answer'] == lemma
    assert row['word'] == lemma
    assert row['distractor_source'] == 'phonetic_trie'
    assert stem not in row['options']
    assert set(judged['candidates']) == neighbours
    assert '声' not in judged['candidates']


def test_stem_lemma_is_left_alone_for_sentence_level_consumers(judged):
    """_lemma still returns the sentence target: cloze_typed and the lexicon
    types compare against it, so only L1 switches to the headword."""
    renderer = exercise_renderer.LadderExerciseRenderer(db=_FakeDb('超える'))
    assert renderer._lemma(_core('こえる', '超え'), 1) == '超え'
    assert renderer._headword(_core('こえる', '超え'), 1) == '超える'


def test_headword_falls_back_to_sentence_target_when_vocab_row_unreadable():
    core = _core('こえる', '超え')
    assert exercise_renderer.LadderExerciseRenderer(db=_FakeDb(fail=True))._headword(core, 1) == '超え'
    assert exercise_renderer.LadderExerciseRenderer(db=_FakeDb(lemma=''))._headword(core, 1) == '超え'


def test_headword_for_a_noun_is_unchanged():
    core = _core('さぎょう', '作業')
    renderer = exercise_renderer.LadderExerciseRenderer(db=_FakeDb('作業'))
    assert renderer._headword(core, 1) == renderer._lemma(core, 1) == '作業'
