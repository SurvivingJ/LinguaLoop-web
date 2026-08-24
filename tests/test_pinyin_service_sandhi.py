"""Unit tests for punctuation-aware pinyin tone sandhi.

Deterministic, pure-function tests -- no jieba dictionary surprises assumed
beyond single/duplicated-character segmentation, no DB, no network. Pins
down two things: (1) punctuation is a hard boundary for sandhi rules, and
(2) the existing in-chunk sandhi behavior is unchanged by the chunking
refactor.
"""

from services.pinyin_service import process_passage, _split_into_chunks, _parse_tone


def _tones_by_char(tokens, char):
    """Return the list of context_tone values for every occurrence of char."""
    return [t["context_tone"] for t in tokens if t["char"] == char]


def _token(char, base_tone, is_punctuation=False):
    return {
        "char": char,
        "word": char,
        "pinyin_text": "",
        "base_tone": base_tone,
        "context_tone": base_tone,
        "is_sandhi": False,
        "sandhi_rule": None,
        "is_punctuation": is_punctuation,
        "requires_review": False,
    }


def test_split_into_chunks_breaks_on_punctuation():
    tokens = [
        _token("你", 3), _token("好", 3),
        _token("，", 0, is_punctuation=True),
        _token("你", 3), _token("好", 3),
    ]
    chunks = _split_into_chunks(tokens)
    assert len(chunks) == 2
    assert [t["char"] for t in chunks[0]] == ["你", "好"]
    assert [t["char"] for t in chunks[1]] == ["你", "好"]


def test_split_into_chunks_ignores_leading_trailing_and_repeated_punctuation():
    tokens = [
        _token("，", 0, is_punctuation=True),
        _token("你", 3),
        _token("，", 0, is_punctuation=True),
        _token("，", 0, is_punctuation=True),
        _token("好", 3),
        _token("。", 0, is_punctuation=True),
    ]
    chunks = _split_into_chunks(tokens)
    assert [[t["char"] for t in c] for c in chunks] == [["你"], ["好"]]


def test_split_into_chunks_all_punctuation_yields_no_chunks():
    tokens = [_token("。", 0, is_punctuation=True), _token("！", 0, is_punctuation=True)]
    assert _split_into_chunks(tokens) == []


def test_third_tone_sandhi_fires_within_a_clause():
    # 你好你好 -- no punctuation, first 好 sits before 你 (tone 3) -> sandhi fires
    tokens = process_passage("你好你好")
    tones = _tones_by_char(tokens, "好")
    assert tones[0] == 2  # sandhi applied: 好 before a 3rd-tone 你
    assert tones[1] == 3  # last char of the string, nothing follows


def test_third_tone_sandhi_blocked_across_comma():
    # 你好，你好 -- comma separates the clauses; 好 before the comma must NOT
    # be treated as adjacent to 你 after the comma.
    tokens = process_passage("你好，你好")
    tones = _tones_by_char(tokens, "好")
    assert tones[0] == 3  # unchanged: comma blocks the cross-clause 3rd-tone rule
    assert tones[1] == 3  # last char, nothing follows


def test_third_tone_sandhi_blocked_across_full_stop():
    tokens = process_passage("你好。你好")
    tones = _tones_by_char(tokens, "好")
    assert tones[0] == 3
    assert tones[1] == 3


def test_yi_sandhi_blocked_across_punctuation():
    # 一，四 -- without the comma, 一 before a 4th tone (四) would become 2nd
    # tone. With the comma, 一 has no next_token in its own chunk.
    tokens = process_passage("一，四")
    yi_tone = _tones_by_char(tokens, "一")[0]
    assert yi_tone == 1  # default: no sandhi, end of its own clause


def test_yi_sandhi_still_fires_without_punctuation():
    tokens = process_passage("一四")
    yi_tone = _tones_by_char(tokens, "一")[0]
    assert yi_tone == 2  # 一 before a 4th tone -> 2nd tone


def test_bu_sandhi_blocked_across_punctuation():
    # 不，去 -- 去 is 4th tone; without the comma 不 would become 2nd tone.
    tokens = process_passage("不，去")
    bu_tone = _tones_by_char(tokens, "不")[0]
    assert bu_tone == 4  # default: no sandhi, end of its own clause


def test_bu_sandhi_still_fires_without_punctuation():
    tokens = process_passage("不去")
    bu_tone = _tones_by_char(tokens, "不")[0]
    assert bu_tone == 2  # 不 before a 4th tone -> 2nd tone


def test_a_bu_a_pattern_does_not_false_positive_across_boundary():
    # 好，不好 -- 不's prev_token is None (start of its own clause), so the
    # duplicate-verb A-不-A check must not match against 好 on the far side
    # of the comma.
    tokens = process_passage("好，不好")
    bu_token = next(t for t in tokens if t["char"] == "不")
    assert bu_token["sandhi_rule"] != "'不' becomes neutral tone in an A不A question pattern (e.g., 好不好)."


def test_punctuation_only_input_does_not_raise():
    tokens = process_passage("。！")
    assert all(t["is_punctuation"] for t in tokens)


def test_leading_and_trailing_punctuation_does_not_raise():
    tokens = process_passage("，你好，")
    chars = [t["char"] for t in tokens]
    assert chars == ["，", "你", "好", "，"]


def test_empty_input_returns_empty_list():
    assert process_passage("") == []
    assert process_passage("   ") == []


def test_parse_tone_rejects_non_ascii_digit_lookalikes():
    # '₄' (U+2084, subscript four) is str.isdigit() == True but int('₄')
    # raises ValueError -- must not crash tone parsing.
    assert _parse_tone("₄") == (5, "₄")
    assert _parse_tone("ni3") == (3, "ni")
    assert _parse_tone("ma5") == (5, "ma")
    assert _parse_tone("a") == (5, "a")
    assert _parse_tone("") == (5, "")


def test_process_passage_does_not_crash_on_embedded_subscript_digit():
    # Regression: a chemical formula fragment like H2O4-ish text embedded in
    # a transcript must not crash the whole pipeline.
    tokens = process_passage("水是 H₂O。")
    assert isinstance(tokens, list)
    assert len(tokens) > 0
