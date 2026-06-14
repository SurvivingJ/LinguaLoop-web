"""Tokenizer-based CJK-safe whole-word matching (audit B4 / TASK-505).

LanguageProcessor.contains_whole_word must reject in-token substring false
positives for CJK (the whole point of B4: `\b` forms no boundaries between CJK
characters, and a naive ``word in sentence`` check matches 子 inside 椅子). The
token-run algorithm is exercised with a stub tokenizer for determinism, plus one
real jieba-backed Chinese check.
"""

import pytest

from services.exercise_generation.language_processor import (
    LanguageProcessor, ChineseProcessor,
)


class _StubProcessor(LanguageProcessor):
    """Processor whose tokenizer returns a fixed list — isolates the
    contains_whole_word token-run logic from any real tokeniser."""

    language_id = 0

    def __init__(self, tokens):
        self._tokens = list(tokens)

    def split_sentences(self, text):
        return [text]

    def chunk_sentence(self, sentence):
        return [sentence]

    def tokenize(self, sentence):
        return list(self._tokens)


# ---------------------------------------------------------------------------
# ASCII path: alphabetic word boundary (\b)
# ---------------------------------------------------------------------------

def test_ascii_whole_word_boundary():
    p = _StubProcessor([])  # ASCII path never calls tokenize
    assert p.contains_whole_word("a new car", "new") is True
    assert p.contains_whole_word("I knew the answer", "new") is False
    assert p.contains_whole_word("renewal plan", "new") is False
    assert p.contains_whole_word("NEW shoes", "new") is True  # case-insensitive


# ---------------------------------------------------------------------------
# CJK path: standalone token or contiguous token run only
# ---------------------------------------------------------------------------

def test_cjk_standalone_token_matches():
    p = _StubProcessor(["椅子", "が", "好き"])
    assert p.contains_whole_word("椅子が好き", "椅子") is True
    assert p.contains_whole_word("椅子が好き", "好き") is True


def test_cjk_in_token_substring_rejected():
    """子 must NOT match inside the single token 椅子 (the B4 false positive)."""
    p = _StubProcessor(["椅子", "が", "好き"])
    assert p.contains_whole_word("椅子が好き", "子") is False
    assert p.contains_whole_word("椅子が好き", "椅") is False


def test_cjk_contiguous_token_run_matches():
    """A lemma the tokenizer splits is accepted as an exact contiguous run."""
    p = _StubProcessor(["勉", "強", "する"])
    assert p.contains_whole_word("勉強する", "勉強") is True


def test_cjk_partial_spanning_run_rejected():
    p = _StubProcessor(["東", "京", "タワー"])
    # 京タワー is a valid run; 京タ spans into the middle of タワー -> reject.
    assert p.contains_whole_word("東京タワー", "京タワー") is True
    assert p.contains_whole_word("東京タワー", "京タ") is False


def test_empty_inputs():
    p = _StubProcessor(["x"])
    assert p.contains_whole_word("", "x") is False
    assert p.contains_whole_word("abc", "") is False


# ---------------------------------------------------------------------------
# Real tokeniser integration (jieba) — ZH corpus matching is CJK-safe
# ---------------------------------------------------------------------------

def test_chinese_processor_jieba_whole_word():
    p = ChineseProcessor()
    # jieba segments 椅子 as one token; 子 is never a standalone token here.
    assert p.contains_whole_word("我喜欢这把椅子", "椅子") is True
    assert p.contains_whole_word("我喜欢这把椅子", "子") is False
