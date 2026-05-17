"""Normalization + tokenization for dictation grading.

Normalization rules (configurable per-language later if needed):
- Lowercase
- Strip Unicode combining marks (NFKD decompose + drop Mn category)
  → café == cafe, naïve == naive, üben == uben
- Strip punctuation (keep word-internal apostrophes and hyphens)
- Collapse whitespace

Tokenization:
- Chinese ('cn'): jieba.lcut for word-segmented matching
- Japanese ('jp'): char-level fallback (no MeCab dependency)
- Everything else: whitespace split
"""

from __future__ import annotations

import logging
import re
import unicodedata
from typing import List

logger = logging.getLogger(__name__)


# Punctuation regex: drop everything that isn't a word char, whitespace,
# apostrophe, or hyphen. Apostrophes and hyphens are kept for words like
# "don't" or "well-known".
_PUNCT_RE = re.compile(r"[^\w\s'\-]", flags=re.UNICODE)

# Trim apostrophes/hyphens that are at the start or end of a token (e.g.
# leftover quote marks that survived the punct strip as ').
_EDGE_TRIM_RE = re.compile(r"^['\-]+|['\-]+$")


def normalize(text: str) -> str:
    """Apply lowercase + diacritic-strip + punctuation-strip + whitespace collapse."""
    if not text:
        return ""

    # 1. Lowercase
    out = text.lower()

    # 2. Decompose Unicode then drop combining marks (Mn category).
    # This preserves base characters (e.g. 'a' from 'á', and any CJK
    # ideograph base form) but removes accents.
    decomposed = unicodedata.normalize("NFKD", out)
    out = "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")

    # 3. Strip punctuation (but keep apostrophes and hyphens in-word)
    out = _PUNCT_RE.sub(" ", out)

    # 4. Collapse whitespace
    out = " ".join(out.split())

    return out


def _is_chinese(language_code: str) -> bool:
    return language_code in {"cn", "zh", "zh-cn", "zh-hans", "zh-hant"}


def _is_japanese(language_code: str) -> bool:
    return language_code in {"jp", "ja"}


def _tokenize_chinese(text: str) -> List[str]:
    """jieba-segmented tokens for Chinese.

    Lazily imported because jieba has a non-trivial startup cost; many app
    workers never grade Chinese dictation.
    """
    try:
        import jieba

        return [t for t in jieba.lcut(text) if t.strip()]
    except ImportError:
        logger.warning("jieba not installed; falling back to char-level for Chinese")
        return _tokenize_chars(text)


def _tokenize_chars(text: str) -> List[str]:
    """Character-level tokenization for scripts without word boundaries."""
    return [ch for ch in text if ch.strip()]


def tokenize(text: str, language_code: str) -> List[str]:
    """Tokenize normalized text into comparison units.

    Args:
        text: Already-normalized text (output of normalize()).
        language_code: e.g. 'cn', 'en', 'es', 'jp'.

    Returns:
        List of tokens. Each token has its edge apostrophes/hyphens trimmed.
        Empty tokens are excluded.
    """
    if not text:
        return []

    code = (language_code or "").lower()
    if _is_chinese(code):
        raw = _tokenize_chinese(text)
    elif _is_japanese(code):
        raw = _tokenize_chars(text)
    else:
        raw = text.split()

    cleaned: List[str] = []
    for tok in raw:
        trimmed = _EDGE_TRIM_RE.sub("", tok)
        if trimmed:
            cleaned.append(trimmed)
    return cleaned
