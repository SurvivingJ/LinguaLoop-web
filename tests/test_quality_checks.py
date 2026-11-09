"""Tests for services/test_generation/quality_checks.py (TASK-912–918).

Fixtures are real strings from the 2026-11-09 Japanese review
(wiki/evaluations/ja-test-review-2026-11-09.md) where possible.
"""

import pytest

from services.test_generation import quality_checks as qc


@pytest.fixture(autouse=True)
def _calibrated(monkeypatch):
    monkeypatch.delenv('TEST_QC_MODES', raising=False)


JA, ZH, EN = qc.get_profile('ja'), qc.get_profile('zh'), qc.get_profile('en')


def codes(results):
    return [r.code for r in results]


def q(question='', choices=None, answer='', type_code='literal_detail'):
    return {'question': question, 'choices': choices or [], 'answer': answer, 'type_code': type_code}


# --- framework (912) -------------------------------------------------------

def test_profiles_and_unknown():
    assert JA.is_cjk and ZH.is_cjk and not EN.is_cjk
    with pytest.raises(KeyError):
        qc.get_profile('fr')


def test_tokenizers():
    assert JA.tokenize('文中の意味') == ['文中', '中の', 'の意', '意味']
    assert JA.tokenize('、。 「」') == []
    assert EN.tokenize("The writer's Point!") == ['the', "writer's", 'point']


def test_every_registered_code_has_a_mode():
    for registry in (qc._QUESTION_CHECKS, qc._TEST_CHECKS, qc._PASSAGE_CHECKS):
        for code, _ in registry:
            assert code in qc.CHECK_MODES


def test_mode_resolution(monkeypatch):
    assert qc.resolve_mode('type_mix') == 'flag'
    monkeypatch.setenv('TEST_QC_MODES', 'reject')
    assert qc.resolve_mode('type_mix') == 'reject'
    monkeypatch.setenv('TEST_QC_MODES', 'flag')
    monkeypatch.setitem(qc.CHECK_MODES, 'type_mix', 'reject')
    assert qc.resolve_mode('type_mix') == 'flag'
    monkeypatch.setenv('TEST_QC_MODES', 'calibrated')
    assert qc.resolve_mode('type_mix') == 'reject'
    monkeypatch.setitem(qc.CHECK_MODES, 'type_mix', 'off')
    monkeypatch.setenv('TEST_QC_MODES', 'reject')
    assert qc.resolve_mode('type_mix') == 'off'
    monkeypatch.setenv('TEST_QC_MODES', 'bogus')
    with pytest.raises(ValueError):
        qc.run_mode()


def test_clean_question_has_no_findings():
    passage = 'あたらしいロボットは、おうちでいろいろなてつだいをします。'
    item = q('ロボットはどこでてつだいをしますか？', ['がっこう', 'おうち', 'みせ', 'こうえん'], 'おうち')
    assert qc.run_question_checks(item, passage, JA, 1) == []


# --- script (913) ----------------------------------------------------------

def test_ja_simplified_characters():
    item = q('質問', ['質的变化', '纹理', '紋理', '変化'], '紋理')
    found = qc.run_question_checks(item, '', JA, 6)
    msgs = ' '.join(r.message for r in found if r.code == 'foreign_script')
    assert '变' in msgs and '纹' in msgs and '紋' not in msgs.split('script')[0]
    assert qc.foreign_chars('紋理と変化', JA) == []


def test_zh_traditional_and_kana():
    assert qc.foreign_chars('这个们', ZH) == []
    assert set(qc.foreign_chars('這個們', ZH)) == {'這', '個', '們'}
    assert qc.foreign_chars('他の人', ZH) == ['の']
    assert qc.foreign_chars('乾燥', ZH) == []   # allowlisted


def test_en_cjk():
    assert qc.foreign_chars('a café 中文', EN) == ['中', '文']


def test_latin_in_cjk():
    passage = 'AIとDNAについての文章。'
    item = q('質問', ['dramatize する', 'AIの役割', 'sandwich を作る', '普通'], '普通')
    found = [r.message for r in qc.run_question_checks(item, passage, JA, 6) if r.code == 'latin_in_cjk']
    assert len(found) == 2 and 'dramatize' in found[0]
    assert not [r for r in qc.run_question_checks(item, passage, EN, 6) if r.code == 'latin_in_cjk']


def test_script_above_level():
    passage = 'あたらしいロボットは、おうちでいろいろなてつだいをします。'
    item = q('「ともだち」のいみは？', ['同じ学校に通う子供', '心を許せる存在', 'いっしょにあそぶひと', 'ねこ'], '心を許せる存在')
    found = [r for r in qc.run_question_checks(item, passage, JA, 1) if r.code == 'script_above_level']
    assert [r.field for r in found] == ['choices[0]', 'choices[1]']
    assert not [r for r in qc.run_question_checks(item, '友達の話', JA, 1) if r.code == 'script_above_level']


# --- choice format (914) ---------------------------------------------------

def test_strip_label_prefixes():
    ch = ['A. 赤', 'B. 青', 'C. 白', 'D. 黒']
    new, ans, did = qc.strip_label_prefixes(ch, 'C. 白')
    assert did and new == ['赤', '青', '白', '黒'] and ans == '白'
    assert qc.strip_label_prefixes(['(A) x', '(B) y', '①z', 'Ｄ．w'], 'x')[0] == ['x', 'y', 'z', 'w']
    partial = ['A. 赤', '青', '白', '黒']
    assert qc.strip_label_prefixes(partial, '青') == (partial, '青', False)
    found = qc.run_question_checks(q('問', partial, '青'), '', JA, 3)
    assert 'choice_label_prefix' in codes(found)


def test_label_regex_leaves_ordinary_text():
    for text in ['1990年に', 'Apple pie', 'a lot', '2つの理由']:
        assert not qc.LABEL_PREFIX_RE.match(text)


def test_answer_length_outlier():
    long_ans = 'パラメトリックデザインの理論は、環境データを基に最適な街区配置を自動的に生成する手法を通じて重要な基盤となりつつある。'
    item = q('主旨は？', ['都市の歴史', '建築の費用', long_ans, '設計者の直感'], long_ans, 'main_idea')
    assert 'answer_length_outlier' in codes(qc.run_question_checks(item, '', JA, 6))
    even = q('問', ['山に登ること', '海で泳ぐこと', '川で釣ること', '町を歩くこと'], '海で泳ぐこと')
    assert 'answer_length_outlier' not in codes(qc.run_question_checks(even, '', JA, 6))


def test_absolute_distractors():
    item = q('態度は？', ['すべての建物を否定している', '完全に賞賛している', '多面的に評価している', '関心がない'],
             '多面的に評価している', 'author_purpose')
    assert 'absolute_distractors' in codes(qc.run_question_checks(item, '', JA, 6))
    both = dict(item, answer='すべての建物を否定している')
    assert 'absolute_distractors' not in codes(qc.run_question_checks(both, '', JA, 6))
    en = q('Tone?', ['It always fails', 'It never works', 'It is mixed', 'It is fun'], 'It is mixed', 'author_purpose')
    assert 'absolute_distractors' in codes(qc.run_question_checks(en, '', EN, 6))
    # whole-word in English: "overall" does not contain the absolute "all"
    en2 = dict(en, choices=['Overall it fails', 'It never works', 'It is mixed', 'It is fun'])
    assert 'absolute_distractors' not in codes(qc.run_question_checks(en2, '', EN, 6))


# --- copy (915) ------------------------------------------------------------

def test_answer_copies_passage():
    passage = '小さなオンラインショップでは、お客様が誰に何を求めているかを知ることが大切です。'
    copied = q('筆者の考えは？', ['店は大きいほうがよい', 'お客様が誰に何を求めているかを知ること', '値段を下げること', '広告を出すこと'],
               'お客様が誰に何を求めているかを知ること', 'supporting_detail')
    assert 'answer_copies_passage' in codes(qc.run_question_checks(copied, passage, JA, 4))
    para = dict(copied, choices=['店は大きいほうがよい', '客の望みを理解すること', '値段を下げること', '広告を出すこと'],
                answer='客の望みを理解すること')
    assert 'answer_copies_passage' not in codes(qc.run_question_checks(para, passage, JA, 4))
    literal = dict(copied, type_code='literal_detail')
    assert 'answer_copies_passage' not in codes(qc.run_question_checks(literal, passage, JA, 4))


def test_copy_check_skips_low_tiers():
    passage = '小さなオンラインショップでは、お客様が誰に何を求めているかを知ることが大切です。'
    copied = q('筆者の考えは？', ['店は大きいほうがよい', 'お客様が誰に何を求めているかを知ること', '値段を下げること', '広告を出すこと'],
               'お客様が誰に何を求めているかを知ること', 'supporting_detail')
    assert 'answer_copies_passage' not in codes(qc.run_question_checks(copied, passage, JA, 2))


def test_answer_copies_passage_english():
    passage = 'The garden project brings neighbours together and restores habitat for local birds.'
    item = q('Main idea?', ['It costs a lot', 'brings neighbours together and restores habitat for local birds',
                            'Birds are loud', 'Gardens are small'],
             'brings neighbours together and restores habitat for local birds', 'main_idea')
    assert 'answer_copies_passage' in codes(qc.run_question_checks(item, passage, EN, 4))


# --- duplicates (917) ------------------------------------------------------

def test_duplicate_answer_great_wall():
    a = q('むかしの人は何をつみましたか？', ['き', 'いし', 'つち', 'かみ'], 'いしをつみかさねてかべをつくった')
    b = q('かべは何でできていますか？', ['き', 'いし', 'つち', 'かみ'], 'いしをつみかさねてかべをつくった')
    found = qc.run_test_checks([a, b], '', JA, 1)
    dup = [r for r in found if r.code == 'duplicate_answer']
    assert dup and dup[0].question_index == 1      # the SECOND one is dropped


def test_duplicate_answer_author_purpose_pair():
    a = q('筆者の態度は？', [], 'ピーナッツバター作りの過程を通して素朴な食の価値を称えている', 'author_purpose')
    b = q('文章の調子は？', [], 'ピーナッツバター作りを通して素朴な食べ物の価値を称賛している', 'author_purpose')
    assert 'duplicate_answer' in codes(qc.run_test_checks([a, b], '', JA, 6))


def test_distinct_answers_not_duplicates():
    qs = [q('a', [], '駅の前で待っていた', 'literal_detail'),
          q('b', [], '雨が降ってきたから', 'supporting_detail'),
          q('c', [], '新しい生活への期待', 'main_idea')]
    assert 'duplicate_answer' not in codes(qc.run_test_checks(qs, '', JA, 3))


def test_duplicate_vocab_target_and_extract():
    assert qc.extract_vocab_target('文中の（他の人）の意味として') == '他の人'
    # sentence quoted, then the word: the word is the target
    assert qc.extract_vocab_target('在“他每天都坚持锻炼身体”中，“坚持”的意思是？') == '坚持'
    assert qc.extract_vocab_target('文中の「外交」の意味') == '外交'
    a = q('文中の「外交」の意味は？', [], 'x', 'vocabulary_context')
    b = q('「外交」とはどういう意味か？', [], 'y', 'vocabulary_context')
    assert 'duplicate_vocab_target' in codes(qc.run_test_checks([a, b], '', JA, 3))


def test_duplicate_stem_only_for_detail_types():
    a = q('この文章の主旨として最も適切なものはどれか。', [], 'x', 'main_idea')
    b = q('この文章の主旨として最も適切なものはどれか。', [], 'y', 'main_idea')
    assert 'duplicate_stem' not in codes(qc.run_test_checks([a, b], '', JA, 3))
    c = dict(a, type_code='literal_detail', answer='p')
    d = dict(b, type_code='literal_detail', answer='q')
    assert 'duplicate_stem' in codes(qc.run_test_checks([c, d], '', JA, 3))


def test_pairwise_helper():
    prev = [q('a', [], 'いしをつみかさねてかべをつくった')]
    cand = q('b', [], 'いしをつみかさねてかべをつくった')
    found = qc.pairwise_duplicate_checks(cand, prev, JA)
    assert [r.code for r in found] == ['duplicate_answer'] and found[0].question_index == 1


# --- shape (918) -----------------------------------------------------------

def test_type_mix():
    qs = [q(type_code=t) for t in ['literal_detail', 'main_idea', 'main_idea', 'supporting_detail']]
    assert any('main_idea' in r.message for r in qc.run_test_checks(qs, '', EN, 3) if r.code == 'type_mix')
    # two author_purpose with overlapping answers + no detail question at T4
    qs = [q(type_code='inference', answer='x'), q(type_code='vocabulary_context', answer='y'),
          q(type_code='author_purpose', answer='The writer admires the quiet craft of baking bread'),
          q(type_code='author_purpose', answer='The writer admires the craft of baking')]
    msgs = [r.message for r in qc.run_test_checks(qs, '', EN, 4) if r.code == 'type_mix']
    assert len(msgs) == 2
    # above T4 a missing detail question is fine; the AP pair still fires
    msgs = [r.message for r in qc.run_test_checks(qs, '', EN, 6) if r.code == 'type_mix']
    assert len(msgs) == 1 and 'author_purpose' in msgs[0]
    ok = [q(type_code=t) for t in ['main_idea', 'supporting_detail', 'inference', 'vocabulary_context', 'author_purpose']]
    assert 'type_mix' not in codes(qc.run_test_checks(ok, '', EN, 5))


def test_too_few_and_title():
    three = [q(type_code='literal_detail')] * 3
    assert 'too_few_questions' in codes(qc.run_test_checks(three, '', EN, 3))
    assert 'too_few_questions' not in codes(qc.run_test_checks(three, '', EN, 2))
    assert 'missing_title' in codes(qc.run_passage_checks('text', None, EN))
    assert 'missing_title' in codes(qc.run_passage_checks('text', '  ', EN))
    assert qc.run_passage_checks('text', 'A title', EN) == []


def test_passage_foreign_script():
    found = qc.run_passage_checks('Tシャツの纹理が美しい。', 'Tシャツ', JA)
    assert codes(found) == ['foreign_script'] and found[0].field == 'transcript'


def test_reject_mode_sets_severity(monkeypatch):
    monkeypatch.setenv('TEST_QC_MODES', 'reject')
    found = qc.run_passage_checks('text', None, EN)
    assert found[0].severity == 'reject'
