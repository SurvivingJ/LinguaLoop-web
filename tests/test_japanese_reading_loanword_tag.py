"""Loanword readings must not carry UniDic's source-word tag (スピード-speed)."""

import pytest

from services.vocabulary.processors.japanese import _to_hiragana
from services.intro_drill import _reading


@pytest.mark.parametrize("kana, expected", [
    ("スピード-speed", "すぴーど"),
    ("ライト-light（光）", "らいと"),
    ("フェア-fair(見本市)", "ふぇあ"),
    ("スタートアップ-start-up", "すたーとあっぷ"),
    ("ボランティア-volunteerカツドウ", "ぼらんてぃあかつどう"),
    ("ハシル", "はしる"),
])
def test_to_hiragana_strips_loanword_tag(kana, expected):
    assert _to_hiragana(kana) == expected


def test_intro_drill_reading_strips_legacy_tag():
    assert _reading({"reading": "こみゅにてぃー-communityつくり"}, "ja")["shown"] == "こみゅにてぃーつくり"
