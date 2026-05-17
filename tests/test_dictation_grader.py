"""Unit tests for services.dictation.grader.

Pure-Python tests — no Supabase, no Flask, no DB. Verify the alignment,
fuzzy tolerance, normalization, and edge cases of grade_dictation.
"""

import pytest

from services.dictation.grader import grade_dictation, _levenshtein, _fuzzy_equal
from services.dictation.tokenizer import normalize, tokenize


# ---------------------------------------------------------------------------
# Levenshtein helper
# ---------------------------------------------------------------------------

def test_levenshtein_identical_is_zero():
    assert _levenshtein("hello", "hello") == 0


def test_levenshtein_single_substitution():
    assert _levenshtein("hello", "hallo") == 1


def test_levenshtein_single_insertion():
    assert _levenshtein("hello", "helllo") == 1


def test_levenshtein_single_deletion():
    assert _levenshtein("hello", "hllo") == 1


def test_levenshtein_two_edits_returns_above_budget():
    # Budget is _FUZZY_MAX_DISTANCE=1; "receive" vs "recieve" is two edits.
    assert _levenshtein("receive", "recieve") >= 2


def test_levenshtein_length_diff_above_budget_short_circuits():
    # Long diff in lengths → exceeds budget without full computation.
    assert _levenshtein("a", "abcdefg") > 1


# ---------------------------------------------------------------------------
# Fuzzy equality
# ---------------------------------------------------------------------------

def test_fuzzy_equal_exact():
    assert _fuzzy_equal("the", "the") is True


def test_fuzzy_equal_short_words_strict():
    # 3-char words don't get tolerance — "cat" != "bat"
    assert _fuzzy_equal("cat", "bat") is False


def test_fuzzy_equal_long_words_tolerant():
    # 5-char words, 1 edit → counts as correct
    assert _fuzzy_equal("hello", "helllo") is True


def test_fuzzy_equal_long_words_beyond_tolerance():
    # 7-char words, 2 edits → fails
    assert _fuzzy_equal("receive", "recieve") is False


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------

def test_normalize_strips_punctuation_and_case():
    assert normalize("Hello, World!") == "hello world"


def test_normalize_strips_diacritics():
    assert normalize("café naïve über") == "cafe naive uber"


def test_normalize_keeps_word_internal_apostrophe():
    assert normalize("don't stop") == "don't stop"


def test_normalize_keeps_word_internal_hyphen():
    assert normalize("well-known") == "well-known"


def test_normalize_collapses_whitespace():
    assert normalize("hello   \t  world\n") == "hello world"


def test_normalize_empty_returns_empty():
    assert normalize("") == ""
    assert normalize(None) == ""


def test_normalize_preserves_chinese_characters():
    # NFKD on CJK should keep ideographs intact.
    assert normalize("我喜欢学习") == "我喜欢学习"


# ---------------------------------------------------------------------------
# Tokenizer
# ---------------------------------------------------------------------------

def test_tokenize_english_whitespace():
    assert tokenize("the quick brown fox", "en") == ["the", "quick", "brown", "fox"]


def test_tokenize_strips_edge_apostrophes_but_keeps_internal():
    # Edge apostrophe trim, internal stays.
    assert tokenize("'hello' don't", "en") == ["hello", "don't"]


def test_tokenize_empty_returns_empty_list():
    assert tokenize("", "en") == []


# ---------------------------------------------------------------------------
# grade_dictation — happy paths
# ---------------------------------------------------------------------------

def test_perfect_match_scores_100():
    r = grade_dictation("the cat sat on the mat", "the cat sat on the mat", "en")
    assert r.word_correct == 6
    assert r.word_total == 6
    assert r.accuracy == pytest.approx(1.0)
    assert all(d.op == "equal" and d.is_correct for d in r.diff)


def test_all_wrong_scores_0():
    r = grade_dictation(
        "the cat sat on the mat",
        "zzz yyy www vvv uuu ttt",
        "en",
    )
    # Same token count, all unequal, all replace, none fuzzy-match
    assert r.word_correct == 0
    assert r.word_total == 6
    assert r.accuracy == 0.0


def test_typo_within_tolerance_counts_correct():
    # "helo" vs "hello": both ≥ 4 chars (helo=4, hello=5), Lev=1 → correct
    r = grade_dictation("hello world today", "helo world today", "en")
    assert r.word_correct == 3
    assert r.word_total == 3


def test_typo_beyond_tolerance_counts_wrong():
    # "recieve" vs "receive": Lev=2 → fails
    r = grade_dictation("please receive the gift", "please recieve the gift", "en")
    # 3 of 4 right (please, the, gift); receive replaced fails
    assert r.word_correct == 3
    assert r.word_total == 4


def test_short_word_typo_not_forgiven():
    # "cat" vs "bat": both < 4 chars, strict equality
    r = grade_dictation("the cat ran", "the bat ran", "en")
    assert r.word_correct == 2
    assert r.word_total == 3


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

def test_extra_user_word_inserts_dont_inflate_total():
    r = grade_dictation("the cat sat", "the big cat sat", "en")
    # canonical = 3 words, user added "big"; insert is display-only
    assert r.word_total == 3
    assert r.word_correct == 3
    # diff should include exactly one 'insert' op
    inserts = [d for d in r.diff if d.op == "insert"]
    assert len(inserts) == 1
    assert inserts[0].user == "big"


def test_missing_user_word_counts_against_total():
    r = grade_dictation("the big cat sat", "the cat sat", "en")
    # canonical = 4 words, user wrote 3; 1 'delete' op
    assert r.word_total == 4
    assert r.word_correct == 3
    deletes = [d for d in r.diff if d.op == "delete"]
    assert len(deletes) == 1
    assert deletes[0].correct == "big"


def test_empty_user_transcript_scores_0():
    r = grade_dictation("the cat sat", "", "en")
    assert r.word_correct == 0
    assert r.word_total == 3
    assert r.accuracy == 0.0
    # all opcodes are 'delete'
    assert all(d.op == "delete" for d in r.diff)


def test_punctuation_only_diff_scores_100():
    r = grade_dictation("Hello, world!", "hello world", "en")
    assert r.word_correct == 2
    assert r.word_total == 2
    assert r.accuracy == pytest.approx(1.0)


def test_casing_diff_scores_100():
    r = grade_dictation("Hello WORLD", "hello world", "en")
    assert r.word_correct == 2
    assert r.word_total == 2


def test_diacritics_diff_scores_100():
    r = grade_dictation("café naïve", "cafe naive", "en")
    assert r.word_correct == 2
    assert r.word_total == 2


def test_chinese_round_trip_via_jieba_or_char_fallback():
    # Identical input should produce identical tokenization, regardless of
    # whether jieba is installed (char-fallback also produces identical
    # token streams). All tokens must be marked correct.
    r = grade_dictation("我喜欢学习", "我喜欢学习", "cn")
    assert r.word_total > 0
    assert r.word_correct == r.word_total
    assert r.accuracy == pytest.approx(1.0)


def test_diff_payload_serializes_to_dicts():
    r = grade_dictation("hello world", "hello world", "en")
    payload = r.diff_payload()
    assert isinstance(payload, list)
    assert all(isinstance(p, dict) for p in payload)
    assert all("op" in p and "is_correct" in p for p in payload)


def test_grader_accuracy_field_matches_counts():
    r = grade_dictation("a b c d e", "a b c x x", "en")
    assert r.word_correct == 3
    assert r.word_total == 5
    assert r.accuracy == pytest.approx(0.6)
