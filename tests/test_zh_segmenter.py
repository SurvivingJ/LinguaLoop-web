"""services/vocabulary/zh_segmenter.py — jieba's guessed words are checked
against CC-CEDICT before they can become vocabulary (2026-11-12)."""

import pytest

jieba = pytest.importorskip('jieba')

from services.vocabulary import zh_segmenter as z  # noqa: E402


def words(text):
    return [w for w, _ in z.cut_with_tags(text)]


def test_fake_guess_is_split():
    # jieba alone yields 很多 / 人用 / 印刷术 …
    assert words('很多人用印刷术传播宗教。')[:4] == ['很多', '人', '用', '印刷术']


def test_reviewed_non_words_in_jiebas_dictionary_are_split():
    assert '会用' not in words('他们会用电脑。')
    assert '变好' not in words('天气变好了。')


def test_real_words_are_kept():
    assert '禁塑' in words('各国推行禁塑政策。')          # allow-list (not in CC-CEDICT)
    assert '共情' in words('我常听播客，培养共情能力。')  # CC-CEDICT
    assert '印刷术' in words('印刷术改变了世界。')         # jieba dictionary


def test_text_is_preserved():
    text = '老师会用蜡板和笔来教他们写字。风一吹，叶子就飞到地上。'
    assert ''.join(words(text)) == text


def test_word_lists_load():
    assert len(z.known_words()) > 100_000
    assert '人用' in z.forced_splits() and '禁塑' in z.known_words()


def test_chinese_processor_uses_the_checked_splitter():
    from services.vocabulary.processors.chinese import ChineseProcessor
    p = ChineseProcessor.__new__(ChineseProcessor)
    lemmas = [t.lemma for t in p.extract_lemma_tokens('很多人用印刷术传播宗教。')]
    assert '人用' not in lemmas and '人' in lemmas
    assert '人用' not in [lem for _, lem, _, _ in p.tokenize_full('很多人用印刷术。')]


def test_our_labels_correct_jiebas_tags_without_changing_the_split(monkeypatch):
    monkeypatch.setattr(z, 'pos_overrides', lambda: {'印刷术': 'v'})
    out = list(z.cut_with_tags('很多人用印刷术。'))
    assert ('印刷术', 'v') in out and ''.join(w for w, _ in out) == '很多人用印刷术。'


def test_override_file_has_only_multi_character_words():
    z.pos_overrides.cache_clear()
    ov = z.pos_overrides()
    assert ov and all(len(w) >= 2 for w in ov)
    assert ov.get('研发') == 'v'


def test_split_unlinked_makes_unlinked_compounds_clickable():
    senses = {'器官': 1, '移植': 2, '书桌': 3, '医疗': 4, '系统': 5, '只': 6, '来': 7, '说': 8, '蓝': 9}
    token_map = [['他看', 0], ['器官移植', 0], ['和', 0], ['书桌上', 0], ['，', 0], ['医疗系统', 0],
                 ['一只', 0], ['对我', 0], ['来说', 0], ['蓝蓝', 0], ['可以', 0], ['好', 42]]
    out, n = z.split_unlinked(token_map, lambda p: senses.get(p, 0))
    assert ''.join(s for s, _ in out) == ''.join(s for s, _ in token_map)
    assert ['器官', 1] in out and ['移植', 2] in out
    assert ['书桌', 3] in out and ['上', 0] in out          # 上 is not a content word
    assert ['医疗', 4] in out and ['系统', 5] in out        # jieba's best path, not 医疗系 / 统
    for kept in (['一只', 0], ['来说', 0], ['蓝蓝', 0], ['可以', 0], ['好', 42]):
        assert kept in out                                  # measure, particle, name, dictionary word, linked
    assert n == 3


def test_best_split_never_returns_the_word_itself():
    assert z._best_split('几星期') == ['几', '星期']
    assert z._best_split('换衣服') == ['换', '衣服']
