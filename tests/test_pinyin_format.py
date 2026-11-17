"""services/pinyin_format.py: numbered pinyin -> tone marks for display.

The cases are shared with tests/unit/pinyin-format.test.js so the Python and
JS helpers cannot drift apart.
"""

import json
from pathlib import Path

import pytest

from services.pinyin_format import format_pinyin, has_numbered_pinyin, numbered_to_marked

CASES = json.loads(
    (Path(__file__).parent / 'fixtures' / 'pinyin_format' / 'cases.json').read_text(encoding='utf-8')
)['format']


@pytest.mark.parametrize('raw,expected', CASES)
def test_format_pinyin_shared_cases(raw, expected):
    assert format_pinyin(raw) == expected


@pytest.mark.parametrize('raw,expected', CASES)
def test_format_pinyin_is_idempotent(raw, expected):
    assert format_pinyin(expected) == expected


def test_numbered_to_marked_keeps_none_and_surrounding_text():
    assert numbered_to_marked(None) is None
    assert numbered_to_marked('一 bi3 笔') == '一 bǐ 笔'
    assert numbered_to_marked('bi3, di1') == 'bǐ, dī'


def test_has_numbered_pinyin():
    assert has_numbered_pinyin('bian4 de2')
    assert has_numbered_pinyin('lu:3')
    assert not has_numbered_pinyin('biàn dé')
    assert not has_numbered_pinyin('mp3')
    assert not has_numbered_pinyin('きょう')
    assert not has_numbered_pinyin(None)


def test_paren_kept_when_it_is_not_numbered_pinyin():
    # Only a parenthesised NUMBERED duplicate is dropped.
    assert format_pinyin('zhāng (classifier)') == 'zhāng (classifier)'
