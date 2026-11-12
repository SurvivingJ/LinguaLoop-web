"""Chinese word splitting for vocabulary: jieba, with its guesses checked.

jieba guesses words its dictionary does not have (its HMM mode). Half of the
guesses in our tests were real modern words (播客 podcast, 共情 empathy), half
were fragments that became fake vocabulary (人用 from 很多人用, 很强, 风一吹):
see wiki/evaluations/zh-tagger-stanza-vs-jieba-2026-11-12.md. A guessed word
is kept only when it is in CC-CEDICT (data/lexicon/cc_cedict_headwords.txt.gz,
CC BY-SA 4.0) or in the reviewed allow-list (data/lexicon/zh_extra_words.txt);
otherwise it is split again without guessing (人用 -> 人 / 用).

A word is "guessed" when jieba's own dictionary does not list it with a
frequency. jieba's dictionary also holds a few non-words (会用, 变好, 土里);
the reviewed ones in data/lexicon/zh_split_words.txt are always split.
Checking every jieba word against CC-CEDICT was measured and rejected: 863
words in our tests are in jieba's dictionary but not CC-CEDICT, and most are
fine for learners (打哈欠, 水资源, 可持续性). Single characters are never
re-split. Deterministic.
"""

from __future__ import annotations

import gzip
import logging
from functools import lru_cache
from pathlib import Path
from typing import Iterator

logger = logging.getLogger(__name__)

_DATA = Path(__file__).resolve().parents[2] / 'data' / 'lexicon'


def _read_words(path: Path) -> set[str]:
    opener = gzip.open if path.suffix == '.gz' else open
    try:
        with opener(path, 'rt', encoding='utf-8') as fh:
            return {line.strip() for line in fh if line.strip() and not line.startswith('#')}
    except FileNotFoundError:
        logger.warning('zh_segmenter: %s missing; guessed words are not checked', path)
        return set()


@lru_cache(maxsize=1)
def known_words() -> frozenset[str]:
    """CC-CEDICT headwords plus the reviewed allow-list."""
    return frozenset(_read_words(_DATA / 'cc_cedict_headwords.txt.gz')
                     | _read_words(_DATA / 'zh_extra_words.txt'))


@lru_cache(maxsize=1)
def forced_splits() -> frozenset[str]:
    """Reviewed non-words to split even when jieba's dictionary has them."""
    return frozenset(_read_words(_DATA / 'zh_split_words.txt'))


def _jieba_freq() -> dict:
    import jieba
    jieba.initialize()
    return jieba.dt.FREQ


def is_unverified_guess(word: str) -> bool:
    """True when jieba invented ``word`` and no dictionary we trust has it."""
    w = word.strip()
    if len(w) < 2:
        return False
    if _jieba_freq().get(w, 0) > 0:
        return False
    return w not in known_words()


def _needs_split(word: str) -> bool:
    w = word.strip()
    return len(w) >= 2 and (w in forced_splits() or is_unverified_guess(w))


def _max_match(word: str) -> list[str]:
    """Split by longest known word (CC-CEDICT, allow-list, jieba dictionary),
    never producing a word that itself needs splitting; else one character."""
    known, freq, out, i = known_words(), _jieba_freq(), [], 0
    while i < len(word):
        for j in range(len(word), i, -1):
            piece = word[i:j]
            if j - i == 1 or ((piece in known or freq.get(piece, 0) > 0)
                              and piece != word and not _needs_split(piece)):
                out.append(piece)
                i = j
                break
    return out


def _resplit(word: str) -> Iterator[tuple[str, str]]:
    import jieba.posseg as pseg
    pieces = [(p, f) for p, f in pseg.cut(word, HMM=False)]
    if len(pieces) == 1 or any(_needs_split(p) for p, _ in pieces):
        tags = pseg.dt.word_tag_tab
        pieces = [(p, tags.get(p, 'x')) for p in _max_match(word)]
    yield from pieces


def cut_with_tags(text: str) -> Iterator[tuple[str, str]]:
    """jieba.posseg.cut, with unverified guesses and reviewed non-words split."""
    import jieba.posseg as pseg
    for word, flag in pseg.cut(text):
        if _needs_split(word):
            yield from _resplit(word)
        else:
            yield word, flag
