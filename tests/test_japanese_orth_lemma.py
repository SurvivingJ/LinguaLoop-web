"""JapaneseProcessor._orth_lemma must never emit UniDic's loanword lexeme id.

UniDic spells a loanword's lemma as katakana + '-' + source word
(ノブ-knob, ライト-light（光）). 344 such strings reached dim_vocabulary as
headwords. The ライト case survived the orthBase fix because its homograph
gloss （光） contains kanji, which tripped the kana-only -> kanji-lemma
preference.
"""
from types import SimpleNamespace

import pytest

from services.vocabulary.processors.japanese import JapaneseProcessor


def _word(surface, orth, lemma):
    return SimpleNamespace(surface=surface,
                           feature=SimpleNamespace(orthBase=orth, lemma=lemma))


@pytest.mark.parametrize('surface, orth, lemma, expected', [
    ('ノブ', 'ノブ', 'ノブ-knob', 'ノブ'),
    # gloss carries kanji — the case that still leaked
    ('ライト', 'ライト', 'ライト-light（光）', 'ライト'),
    ('ロック', 'ロック', 'ロック-rock（音楽）', 'ロック'),
    ('フェア', 'フェア', 'フェア-fair(見本市)', 'フェア'),
    # no orthBase: fall back to the surface, not the loanword lemma
    ('ノブ', '*', 'ノブ-knob', 'ノブ'),
    ('ノブ', None, 'ノブ-knob', 'ノブ'),
])
def test_loanword_lemma_never_returned(surface, orth, lemma, expected):
    assert JapaneseProcessor._orth_lemma(_word(surface, orth, lemma)) == expected


def test_kana_surface_still_prefers_kanji_lemma():
    assert JapaneseProcessor._orth_lemma(_word('しろ', 'しろ', '城')) == '城'


def test_kanji_orth_still_preferred_over_lexeme():
    assert JapaneseProcessor._orth_lemma(_word('速い', '速い', '早い')) == '速い'


def test_real_tagger_emits_no_latin_lemmas():
    pytest.importorskip('fugashi')
    tokens = JapaneseProcessor().tokenize_full(
        'ドアのノブを回してライトをつけ、ロックを聴いてファッションを楽しむ')
    lemmas = [lemma for _s, lemma, _c, _r in tokens]
    assert not [lemma for lemma in lemmas if any('a' <= ch.lower() <= 'z' for ch in lemma)]
    assert {'ノブ', 'ライト', 'ロック', 'ファッション'} <= set(lemmas)
