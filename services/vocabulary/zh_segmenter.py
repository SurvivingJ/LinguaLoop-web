"""Chinese word splitting for vocabulary: jieba, with its guesses checked.

jieba guesses words its dictionary does not have (its HMM mode). Half of the
guesses in our tests were real modern words (播客 podcast, 共情 empathy), half
were fragments that became fake vocabulary (人用 from 很多人用, 很强, 风一吹):
see wiki/evaluations/zh-tagger-stanza-vs-jieba-2026-11-12.md. A guessed word
is kept only when it is in CC-CEDICT (data/lexicon/cc_cedict_headwords.txt.gz,
CC BY-SA 4.0) or in the reviewed allow-list (data/lexicon/zh_extra_words.txt);
otherwise it is split again without guessing (人用 -> 人 / 用). Tags then
take our own label where it corrects jieba's dictionary
(data/lexicon/zh_pos_overrides.tsv, scripts/build_zh_pos_overrides.py).

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
from typing import Callable, Iterator

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


@lru_cache(maxsize=1)
def pos_overrides() -> dict[str, str]:
    """word -> jieba tag from data/lexicon/zh_pos_overrides.tsv: our own
    labels where they correct jieba's dictionary tag (built by
    scripts/build_zh_pos_overrides.py). Only the tag changes, never the split."""
    out: dict[str, str] = {}
    try:
        with open(_DATA / 'zh_pos_overrides.tsv', encoding='utf-8') as fh:
            for line in fh:
                if line.startswith('#') or not line.strip():
                    continue
                parts = line.rstrip('\n').split('\t')
                if len(parts) >= 2 and parts[0] and parts[1]:
                    out[parts[0]] = parts[1]
    except FileNotFoundError:
        logger.warning('zh_segmenter: zh_pos_overrides.tsv missing; jieba tags used as-is')
    return out


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
    """jieba.posseg.cut, with unverified guesses and reviewed non-words split,
    and our own tag where it corrects jieba's dictionary (pos_overrides)."""
    import jieba.posseg as pseg
    overrides = pos_overrides()

    def tagged(pairs):
        for w, f in pairs:
            yield w, overrides.get(w, f)

    for word, flag in pseg.cut(text):
        if _needs_split(word):
            yield from tagged(_resplit(word))
        else:
            yield from tagged([(word, flag)])


# Tags ChineseProcessor treats as content words (kept in step with
# services/vocabulary/processors/chinese.py, which imports these).
CONTENT_TAGS = frozenset({"n", "v", "a", "d", "i", "l", "vn", "an"})


def is_content_tag(tag: str) -> bool:
    return tag in CONTENT_TAGS or (len(tag) > 0 and tag[0] in {'n', 'v', 'a'})


# Whole-token jieba tags never split for linking: numerals and measure
# phrases (一只: 只 would link to "only"), pronoun phrases (这时候), particles
# and conjunction phrases (来说, 是因为) and personal names (蓝蓝).
_NO_SPLIT_TAGS = ('m', 'q', 'r', 'u', 'c', 'nr')


def _best_split(word: str) -> list[str]:
    """jieba's own best path through `word` (max summed log frequency over
    dictionary pieces), with the whole word itself excluded as a piece and
    never using a piece that needs splitting. Single characters are always
    allowed. 医疗系统 -> 医疗 / 系统, 几星期 -> 几 / 星期."""
    import math
    freq, known = _jieba_freq(), known_words()
    import jieba
    log_total = math.log(jieba.dt.total)
    n = len(word)
    best: list[tuple[float, int]] = [(0.0, n)] * (n + 1)
    for i in range(n - 1, -1, -1):
        options = []
        for j in range(i + 1, n + 1):
            piece = word[i:j]
            if piece == word:
                continue
            if j - i > 1 and not ((freq.get(piece, 0) > 0 or piece in known) and not _needs_split(piece)):
                continue
            options.append((math.log(freq.get(piece) or 1) - log_total + best[j][0], j))
        best[i] = max(options)
    out, i = [], 0
    while i < n:
        j = best[i][1]
        out.append(word[i:j])
        i = j
    return out


def split_unlinked(token_map: list, sense_for: Callable[[str], int]) -> tuple[list, int]:
    """Split word-map tokens that link to nothing into dictionary words that do.

    jieba's dictionary holds many compounds and phrases our dictionary has no
    entry for (器官移植, 书桌上, 记录下来, 闪烁着). Such a token renders as plain
    text. Each multi-character Chinese token with sense 0 that no dictionary
    lists (CC-CEDICT or the allow-list; 可以, 没有 stay whole even when they
    are unlinked grammar words) and is not a number, measure, pronoun,
    particle, conjunction or name phrase (一只, 来说, 是因为, 这时候) is split
    the way jieba itself would cut it without that one entry (_best_split:
    医疗系统 -> 医疗 / 系统), and each content-word piece is linked with
    `sense_for(piece)` (0 when it has none). The token is replaced only when at
    least one piece gets a link; linked tokens are never touched, and the
    surfaces still concatenate to the same text. Returns (map, tokens split).
    """
    import jieba.posseg as pseg
    tags, overrides = pseg.dt.word_tag_tab, pos_overrides()
    out: list = []
    split = 0
    for entry in token_map or []:
        surf, sid = entry[0], entry[1]
        word = surf.strip()
        tag = overrides.get(word, tags.get(word)) or ''
        if (sid or len(word) < 2 or word in known_words() or tag.startswith(_NO_SPLIT_TAGS)
                or not all('一' <= ch <= '鿿' for ch in word)):
            out.append([surf, sid])
            continue
        pieces = _best_split(word)
        linked = [[p, sense_for(p) if is_content_tag(overrides.get(p, tags.get(p, 'x'))) else 0]
                  for p in pieces]
        if len(pieces) < 2 or not any(s for _, s in linked):
            out.append([surf, sid])
            continue
        lead = surf[:len(surf) - len(surf.lstrip())]
        trail = surf[len(surf.rstrip()):]
        linked[0][0] = lead + linked[0][0]
        linked[-1][0] = linked[-1][0] + trail
        out += linked
        split += 1
    return out, split
