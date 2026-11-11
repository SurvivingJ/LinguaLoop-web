"""Measure Words: the correct option gets its pinyin like the wrong ones (it
was the only option without, a giveaway), and the "(imported)" placeholder is
not shown as a meaning label."""

from types import SimpleNamespace
from unittest.mock import MagicMock

import services.classifier_drill_service as cds


def _db(rows):
    db = MagicMock()
    chain = db.table.return_value.select.return_value.in_.return_value
    chain.execute.return_value = SimpleNamespace(data=rows)
    return db


def test_correct_pinyin_attached_in_id_order():
    items = [{'correct_classifier_ids': [5, 7]}, {'correct_classifier_ids': [9]}, {}]
    cds._attach_correct_pinyin(_db([{'id': 7, 'pinyin_display': 'zhī'},
                                    {'id': 5, 'pinyin_display': 'tiáo'},
                                    {'id': 9, 'pinyin_display': 'zé'}]), items)
    assert items[0]['correct_classifier_pinyin'] == ['tiáo', 'zhī']
    assert items[1]['correct_classifier_pinyin'] == ['zé']
    assert items[2]['correct_classifier_pinyin'] == []


def test_lookup_failure_leaves_empty_pinyin():
    db = MagicMock()
    db.table.side_effect = RuntimeError('down')
    items = [{'correct_classifier_ids': [5]}]
    cds._attach_correct_pinyin(db, items)
    assert items[0]['correct_classifier_pinyin'] == ['']


def test_placeholder_label_hidden():
    assert cds._clean_label('(imported)') is None
    assert cds._clean_label('  ') is None
    assert cds._clean_label(None) is None
    assert cds._clean_label('small / medium animals') == 'small / medium animals'
