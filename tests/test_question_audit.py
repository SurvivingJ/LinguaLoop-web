"""services/question_audit.py — repeated and above-passage questions."""

from services.question_audit import audit_test, missing_quotes, near_duplicates, unseen_share

PRINTING = '在欧洲，印刷术发展很快。很多人用印刷术传播宗教。这种传播对宗教改革很重要。宗教改革让欧洲的宗教变了很多。印刷术让更多人知道新的宗教想法。'


def test_walkthrough_repeat_is_flagged():
    qs = [
        {'question_text': '根据文中信息，印刷术在欧洲的传播对哪方面产生了重要影响？', 'answer': '宗教改革'},
        {'question_text': '根据文中信息，印刷术在欧洲的传播对什么事件起到了重要作用？', 'answer': '宗教改革'},
        {'question_text': '这段文字的核心信息是什么？', 'answer': 'C'},
    ]
    assert [(i, j) for i, j, _ in near_duplicates(qs)] == [(0, 1)]


def test_different_questions_are_not_repeats():
    qs = [{'question_text': '作者为什么喜欢这件T恤？', 'answer': 'A'},
          {'question_text': '小猫在做什么？', 'answer': 'B'}]
    assert near_duplicates(qs) == []


def test_question_within_the_passage_is_not_above_it():
    q = {'question_text': '根据文中信息，印刷术让更多人知道什么？', 'choices': ['新的宗教想法', '欧洲']}
    assert unseen_share(q, PRINTING) <= 0.4


def test_question_in_harder_language_is_flagged():
    q = {'question_text': '作者对技术扩散与思想变迁之间因果机制的阐释体现了何种史观？',
         'choices': ['线性进化论', '技术决定论', '结构功能主义', '辩证唯物主义']}
    assert unseen_share(q, PRINTING) > 0.6
    assert audit_test({'id': 't', 'transcript': PRINTING}, [q])['flagged']


def test_spaced_scripts_use_words():
    q = {'question_text': 'What did the boy do with the car?', 'choices': ['rolled it', 'sold it']}
    assert unseen_share(q, 'The boy rolled the red car down the ramp.') < 0.5


def test_quoted_phrase_missing_from_passage():
    q = {'question_text': 'What does the phrase "turn a blind eye" mean in this passage?'}
    assert missing_quotes(q, 'Bees pollinate flowers in spring.') == ['turn a blind eye']
    assert missing_quotes(q, 'They chose to turn a  blind eye to it.') == []
    zh = {'question_text': '根据文中信息，短语“变了很多”最接近以下哪个意思？'}
    assert missing_quotes(zh, PRINTING) == []
    ja = {'question_text': '文中の「外傷」の意味として最も適切なものを選んでください。'}
    assert missing_quotes(ja, '応急手当の本を読んだ。') == ['外傷']


def test_same_template_about_different_words_is_not_a_repeat():
    qs = [{'question_text': '文中の「外傷」の意味として最も適切なものを選んでください。', 'answer': 'A'},
          {'question_text': '文中の「出ます」の意味として最も適切なものを選んでください。', 'answer': 'B'}]
    assert near_duplicates(qs) == []


def test_shared_template_with_different_answers_is_not_a_repeat():
    qs = [{'question_text': 'この文章における筆者の態度として最も適切なものはどれか。', 'answer': '冷静に分析しつつ高く評価している'},
          {'question_text': 'この文章における筆者の論の運び方として最も適切なものはどれか。', 'answer': '背景を説明した後に展開している'}]
    assert near_duplicates(qs) == []
