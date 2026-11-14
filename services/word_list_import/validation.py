"""Validation for user-submitted vocabulary words.

Uploaded words end up as rows in the shared dictionary tables and as input to
LLM generation, so anything that is not plausibly a word or short phrase in
the target language is refused before it gets that far.
"""

import re
import unicodedata
from typing import Optional

MAX_WORD_LENGTH = 40

# Joiners that legitimately appear inside a word or short phrase.
_JOINERS = frozenset(" -'’·・")

_HAN = re.compile(
    '[々〇㐀-䶿一-鿿豈-﫿'
    '\U00020000-\U0002ebef]'
)
_KANA = re.compile('[぀-ゟ゠-ヿㇰ-ㇿｦ-ﾟ]')


def _is_latin(ch: str) -> bool:
    return unicodedata.name(ch, '').startswith('LATIN')


def _is_han(ch: str) -> bool:
    return bool(_HAN.match(ch))


def _is_kana(ch: str) -> bool:
    return bool(_KANA.match(ch))


# language code -> (scripts a word must draw on, scripts additionally allowed)
_SCRIPT_RULES = {
    'en': ((_is_latin,), ()),
    'zh': ((_is_han,), (_is_latin,)),
    'ja': ((_is_han, _is_kana), (_is_latin,)),
}


def clean_word(raw: str, language_code: str) -> tuple[Optional[str], Optional[str]]:
    """Normalise one submitted word. Returns ``(word, None)`` or ``(None, reason)``."""
    if not isinstance(raw, str):
        return None, 'must be a string'
    word = ' '.join(unicodedata.normalize('NFC', raw).split())
    if not word:
        return None, 'must not be empty'
    if len(word) > MAX_WORD_LENGTH:
        return None, f'must be at most {MAX_WORD_LENGTH} characters'

    required, extra = _SCRIPT_RULES.get(language_code, ((), ()))
    has_required = False
    for ch in word:
        if ch in _JOINERS:
            continue
        category = unicodedata.category(ch)
        if category[0] == 'M':
            continue
        if category[0] != 'L':
            return None, 'may only contain letters, spaces, hyphens and apostrophes'
        if not required:
            has_required = True
        elif any(check(ch) for check in required):
            has_required = True
        elif not any(check(ch) for check in extra):
            return None, f'contains characters outside the {language_code!r} writing system'
    if not has_required:
        return None, f'is not written in the {language_code!r} writing system'
    return word, None


def clean_words(raw_words: list, language_code: str) -> tuple[list[str], Optional[str]]:
    """Normalise and de-duplicate a submission. Returns ``(words, None)`` or
    ``([], message)`` naming the first offending entry by position."""
    cleaned: list[str] = []
    seen = set()
    for index, raw in enumerate(raw_words, start=1):
        word, reason = clean_word(raw, language_code)
        if word is None:
            return [], f'word {index} {reason}'
        key = word.casefold()
        if key not in seen:
            seen.add(key)
            cleaned.append(word)
    return cleaned, None
