"""Learners see Chinese pronunciations in one form: pinyin with tone marks.

The classifier drill payload (services/drill_service.py) and the post-test
vocab check payload (VocabularyKnowledgeService.build_quiz_with_distractors)
convert numbered pinyin ("bi3") and drop the parenthesised numbered duplicate
("biàn dé (bian4 de2)") before they reach the page. Japanese readings pass
through unchanged.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock

import services.drill_service as ds
from services.vocabulary.knowledge_service import VocabularyKnowledgeService


def _db(rows):
    db = MagicMock()
    chain = db.table.return_value.select.return_value.in_.return_value
    chain.execute.return_value = SimpleNamespace(data=rows)
    return db


def test_classifier_item_converts_noun_and_distractor_pinyin():
    item = ds._classifier_item({
        'out_noun_lemma': '变得',
        'out_noun_pronunciation': 'biàn dé (bian4 de2)',
        'out_distractor_hanzi': ['笔', '滴', '缕'],
        'out_distractor_pinyin': ['bi3', 'dī', 'lu:3'],
    })
    assert item['noun_pronunciation'] == 'biàn dé'
    assert item['distractor_pinyin'] == ['bǐ', 'dī', 'lǚ']


def test_classifier_item_missing_pronunciation_is_empty():
    item = ds._classifier_item({'out_noun_pronunciation': None, 'out_distractor_pinyin': None})
    assert item['noun_pronunciation'] == ''
    assert item['distractor_pinyin'] == []


def test_correct_classifier_pinyin_is_tone_marked():
    items = [{'correct_classifier_ids': [5, 7]}]
    ds._attach_correct_pinyin(_db([{'id': 5, 'pinyin_display': 'di1'},
                                   {'id': 7, 'pinyin_display': 'zhāng'}]), items)
    assert items[0]['correct_classifier_pinyin'] == ['dī', 'zhāng']


def test_counter_item_readings_untouched():
    item = ds._counter_item({
        'out_noun_pronunciation': 'ほん',
        'out_correct_counter_reading': ['ほん'],
        'out_distractor_reading': ['まい'],
    })
    assert item['noun_pronunciation'] == 'ほん'
    assert item['correct_counter_reading'] == ['ほん']
    assert item['distractor_reading'] == ['まい']


def _quiz_service(candidates):
    svc = VocabularyKnowledgeService.__new__(VocabularyKnowledgeService)
    svc.db = MagicMock()
    svc.get_word_quiz_candidates = lambda *a, **k: candidates
    svc._distractors_for = lambda requests, language_id: [
        [{'definition': 'x', 'lemma': 'a'}, {'definition': 'y', 'lemma': 'b'},
         {'definition': 'z', 'lemma': 'c'}]
        for _ in requests
    ]
    return svc


def test_word_quiz_pronunciation_tone_marks_only_for_chinese():
    svc = _quiz_service([
        {'out_sense_id': 1, 'out_lemma': '变得', 'out_definition': 'to become',
         'out_pronunciation': 'biàn dé (bian4 de2)', 'out_p_known': 0.5},
        {'out_sense_id': 2, 'out_lemma': '子', 'out_definition': 'suffix',
         'out_pronunciation': 'zi (zi5)', 'out_p_known': 0.5},
        {'out_sense_id': 3, 'out_lemma': '笔', 'out_definition': 'pen',
         'out_pronunciation': 'bi3', 'out_p_known': 0.5},
    ])
    items = svc.build_quiz_with_distractors('u', [1, 2, 3], language_id=1)
    assert [i['pronunciation'] for i in items] == ['biàn dé', 'zi', 'bǐ']


def test_word_quiz_japanese_reading_unchanged():
    svc = _quiz_service([
        {'out_sense_id': 1, 'out_lemma': '今日', 'out_definition': 'today',
         'out_pronunciation': 'きょう', 'out_p_known': 0.5},
    ])
    items = svc.build_quiz_with_distractors('u', [1], language_id=3)
    assert items[0]['pronunciation'] == 'きょう'
