"""One display form for Chinese pronunciations: pinyin with tone marks.

Stored pronunciations come in three shapes (``dim_word_senses.pronunciation``,
``dim_classifiers.pinyin_display``): tone-marked (``zhāng``), numbered
(``bi3``, ``lu:3``) and both at once (``biàn dé (bian4 de2)``).
``format_pinyin`` turns any of them into the tone-marked form alone. Anything
that is not numbered pinyin (kana, English, an already-marked string) comes
back unchanged.

Mirror of static/js/session/pinyin-format.js; the shared cases in
tests/fixtures/pinyin_format/cases.json pin both. Display only: answer
checking keeps using the numbered form.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Optional

_MARKS = {
    'a': 'āáǎà', 'e': 'ēéěè', 'i': 'īíǐì', 'o': 'ōóǒò', 'u': 'ūúǔù', 'ü': 'ǖǘǚǜ',
    'A': 'ĀÁǍÀ', 'E': 'ĒÉĚÈ', 'I': 'ĪÍǏÌ', 'O': 'ŌÓǑÒ', 'U': 'ŪÚǓÙ', 'Ü': 'ǕǗǙǛ',
}
# Syllabic nasals (m2, n3, ng4, hm5) take a combining mark on the m / n.
_COMBINING = ('̄', '́', '̌', '̀')

_INITIAL = r'(?:zh|ch|sh|[bpmfdtnlgkhjqxrzcsyw])?'
_FINAL = (r'(?:iang|iong|uang|ueng|üan|ang|eng|ing|ong|ian|iao|uai|uan|üe|ai|ao|an|ei|en|er'
          r'|ia|ie|in|io|iu|ou|ua|ui|un|uo|ue|ün|ê|a|e|i|o|u|ü)')
_SYLLABLE = re.compile(rf'^(?:{_INITIAL}{_FINAL}|hng|hm|ng|m|n)$')
# A run of letters ending in a tone digit, optionally followed by an er-hua
# "r" ("dian3r"). Not preceded by a letter, so "mp3" / "Windows10" are matched
# whole and then rejected as non-pinyin.
_TOKEN = re.compile(r'(?<![A-Za-zÜüÊê:])([A-Za-zÜüÊê:]+)([0-5])(r(?![A-Za-z]))?')
_PAREN = re.compile(r'^(.*?)\s*\(([^()]*)\)$')


def _normalise_u(letters: str) -> str:
    return letters.replace('u:', 'ü').replace('v', 'ü').replace('U:', 'Ü').replace('V', 'Ü')


def _mark_syllable(syl: str, tone: int) -> str:
    if tone in (0, 5):
        return syl
    lower = syl.lower()
    m = re.search(r'[ae]', lower)
    idx = m.start() if m else lower.find('ou')
    if idx < 0:
        idx = next((i for i in range(len(lower) - 1, -1, -1) if lower[i] in 'iouü'), -1)
    if idx < 0:
        n = re.search(r'[mn]', lower)
        if not n:
            return syl
        k = n.start() + 1
        return unicodedata.normalize('NFC', syl[:k] + _COMBINING[tone - 1] + syl[k:])
    ch = syl[idx]
    marked = _MARKS[ch][tone - 1] if ch in _MARKS else ch
    return syl[:idx] + marked + syl[idx + 1:]


def _parse_syllable(letters: str) -> Optional[tuple[str, str]]:
    s = _normalise_u(letters)
    lower = s.lower()
    # A lone "r" is the er-hua suffix written as its own syllable ("r5").
    if lower == 'r' or _SYLLABLE.match(lower):
        return s, ''
    if len(lower) > 1 and lower.endswith('r') and _SYLLABLE.match(lower[:-1]):
        return s[:-1], s[-1]
    return None


def numbered_to_marked(text: Optional[str]) -> Optional[str]:
    """Numbered pinyin -> tone marks, in place, inside any string.

    Syllables may be separated by spaces or run together (``bian4de2``). A
    standalone er-hua ``r5`` joins the syllable before it. Non-pinyin text is
    left as it is.
    """
    if text is None:
        return None
    s = str(text)
    if not re.search(r'[0-5]', s):
        return s
    out: list[str] = []
    last = 0
    for m in _TOKEN.finditer(s):
        parsed = _parse_syllable(m.group(1))
        if not parsed:
            continue
        base, r = parsed
        head = s[last:m.start()]
        body = _mark_syllable(base, int(m.group(2))) + r + (m.group(3) or '')
        # "yi1 dian3 r5": the er-hua suffix belongs to the previous syllable.
        if base.lower() == 'r' and last > 0 and head and head.isspace():
            head, body = '', base
        out.append(head + body)
        last = m.end()
    out.append(s[last:])
    return ''.join(out)


def has_numbered_pinyin(text: Optional[str]) -> bool:
    """True when ``text`` has at least one numbered pinyin syllable."""
    return text is not None and numbered_to_marked(text) != str(text)


def format_pinyin(text: Optional[str]) -> str:
    """The one form a learner sees: tone-marked pinyin.

    ``biàn dé (bian4 de2)`` -> ``biàn dé``; ``bi3`` -> ``bǐ``; ``zhāng`` and
    ``きょう`` unchanged; None / '' -> ''.
    """
    if text is None:
        return ''
    s = str(text).strip()
    m = _PAREN.match(s)
    if m and has_numbered_pinyin(m.group(2)):
        return numbered_to_marked(m.group(1).strip() or m.group(2).strip()) or ''
    return numbered_to_marked(s) or ''


ZH_LANGUAGE_ID = 1


def display_pronunciation(text: Optional[str], language_id=None, language_code=None) -> str:
    """A stored pronunciation as a learner sees it, for any study language.

    Chinese (``language_id`` 1 or ``language_code`` 'zh') -> ``format_pinyin``;
    every other language (Japanese kana, English) is returned as stored.
    None -> ''. Display only: never feed this to answer checking.
    """
    # The word's own language id decides when it is known; the code (e.g. the
    # test's language) is only a fallback, so a non-Chinese word in a Chinese
    # test is never run through the pinyin formatter.
    if language_id not in (None, ''):
        is_zh = str(language_id) == str(ZH_LANGUAGE_ID)
    else:
        is_zh = language_code == 'zh'
    if is_zh:
        return format_pinyin(text)
    return '' if text is None else str(text)
