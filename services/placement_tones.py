"""Chinese pinyin tones for placement: parse, re-mark, numbered form, tone variants.

Pure functions, no I/O. Spec: wiki/features/vocab-placement.tech.md §2 rule 4 and §14
(``calibration_zh_tone_variants``, ``calibration_refresh_zh_tone_inventory``, the zh normaliser
fix); ADR-060. Ported from the research script
wiki/evaluations/vocab-placement-research-2026-11-18/tones/tone_cover.py.

Two SQL functions mirror this module and must agree with it exactly:

* ``to_numbered`` with spaces removed equals ``calibration_normalise_pronunciation(r, 1)`` for
  a reading with no ``(…)`` numbered part (migrations/calibration_zh_normaliser_fix.sql);
* ``variants`` returns the same list as ``calibration_zh_tone_variants``
  (migrations/calibration_zh_tones.sql), checked by scripts/verify_zh_tone_variants.py.

Terms:

* A **display reading** is tone-marked pinyin as stored, e.g. ``'yuán xíng'``, possibly followed
  by a numbered part ``'(yuan2 xing2)'``, which is dropped (as
  ``calibration_display_pronunciation`` does).
* A **token** is a run of characters between separators (whitespace, ``'``, ``-``, ``·``). A token
  is a **syllable** when, after NFD and lower-casing, it has at most one tone mark and its letters
  are ``[a-z]`` with at most one ``ü``. Its **base** is the toneless letters with ü written
  ``u:`` (``lǜ`` → ``lu:``); its **tone** is 1–4 from the mark (U+0304, U+0301, U+030C, U+0300)
  or 5 when there is none. Any other token (``yíhuìr`` has two marks) is kept as written, never
  changed, and has tone 0 here.
"""
from __future__ import annotations

import hashlib
import itertools
import re
import unicodedata
from dataclasses import dataclass
from typing import Dict, FrozenSet, Iterable, List, Mapping, Optional, Sequence, Tuple

TONE_OF_MARK = {'\u0304': 1, '\u0301': 2, '\u030c': 3, '\u0300': 4}
MARK_OF_TONE = {t: m for m, t in TONE_OF_MARK.items()}
DIAERESIS = '\u0308'
FULL_TONES = (1, 2, 3, 4)
NEUTRAL = 5
NOT_A_SYLLABLE = 0
VARIANT_CAP = 16
# Syllables written with these characters keep their tone (一/不 sandhi), when the lemma's
# character count equals the reading's syllable count.
FIXED_CHARS = frozenset('一不')

# The same pattern as calibration_display_pronunciation(p, 1).
_NUMBERED_PART_RE = re.compile(r'\s*\([^)]*\)\s*')
_SEPARATORS = r"[\s'·-]"
_SEGMENT_RE = re.compile(rf"{_SEPARATORS}+|[^\s'·-]+")
_SEPARATOR_RE = re.compile(rf"{_SEPARATORS}+")
_BASE_RE = re.compile(r'[a-z]*(?:u:)?[a-z]*')
_MARKS_RE = re.compile('[\u0300\u0301\u0304\u030c]')
# After a tone mark (NFD): the rest of that syllable. Following vowels (ü is u + U+0308), then
# the coda n / ng (g for ńg) unless a vowel follows (then it starts the next syllable), then
# an er-hua r unless a vowel follows. The SQL normaliser uses the same pattern.
_AFTER_MARK = r'((?:[aeiou]\u0308?)*(?:(?:ng|n|g)(?![aeiou]))?(?:r(?![aeiou]))?)'
_TONE_PLACEMENT = [(re.compile(MARK_OF_TONE[t] + _AFTER_MARK), t) for t in FULL_TONES]
_NEUTRAL_END_RE = re.compile(rf"([a-zü])(?={_SEPARATORS}|\Z)")
_SYLLABLE_BREAK_RE = re.compile(r'(?<=[1-5])(?=[a-zü])')


@dataclass(frozen=True)
class Syllable:
    text: str              # the token as written (NFC)
    base: Optional[str]    # toneless letters, ü as 'u:'; None when not a syllable
    tone: int              # 1-4, 5 neutral, 0 not a syllable

    @property
    def is_syllable(self) -> bool:
        return self.base is not None

    @property
    def frame(self) -> str:
        """The toneless identity of the token: its base, or '?' + text for a non-syllable."""
        return self.base if self.base is not None else '?' + self.text.lower()


def display_form(reading: Optional[str]) -> str:
    """The tone-marked part of a stored zh reading (numbered ``(…)`` part dropped), NFC."""
    if not reading:
        return ''
    return unicodedata.normalize('NFC', _NUMBERED_PART_RE.sub('', reading).strip(' '))


def parse_syllable(token: str) -> Syllable:
    """One token -> Syllable (see the module docstring)."""
    text = unicodedata.normalize('NFC', token)
    d = unicodedata.normalize('NFD', token.lower())
    marks = _MARKS_RE.findall(d)
    base = _MARKS_RE.sub('', d).replace(DIAERESIS, ':')
    if len(marks) > 1 or not base or not _BASE_RE.fullmatch(base):
        return Syllable(text, None, NOT_A_SYLLABLE)
    return Syllable(text, base, TONE_OF_MARK[marks[0]] if marks else NEUTRAL)


def segments(reading: Optional[str]) -> List[Tuple[str, Optional[Syllable]]]:
    """The display form split into (text, Syllable) for tokens and (text, None) for separators."""
    out: List[Tuple[str, Optional[Syllable]]] = []
    for m in _SEGMENT_RE.finditer(display_form(reading)):
        seg = m.group(0)
        out.append((seg, None) if _SEPARATOR_RE.fullmatch(seg) else (seg, parse_syllable(seg)))
    return out


def parse(reading: Optional[str]) -> List[Syllable]:
    """The tokens of a display reading, in order (separators dropped)."""
    return [s for _, s in segments(reading) if s is not None]


def reading_key(reading: Optional[str]) -> Tuple[str, Tuple[int, ...]]:
    """(frame, tones): two readings are the same reading when both parts are equal."""
    syls = parse(reading)
    return ' '.join(s.frame for s in syls), tuple(s.tone for s in syls)


def mark_syllable(base: str, tone: int) -> str:
    """Toneless base ('u:' for ü) + tone -> tone-marked syllable (NFC, lower case).

    The mark goes on a, else e, else the o of "ou", else the last vowel (ü included); a
    syllable with no vowel (m, n, ng, hm, hng) takes it on its first m or n. Tone 5 or 0:
    no mark.
    """
    letters = base.replace('u:', 'ü')
    if tone not in MARK_OF_TONE:
        return letters
    i = _mark_index(letters)
    if i < 0:
        return letters
    return unicodedata.normalize('NFC', letters[:i + 1] + MARK_OF_TONE[tone] + letters[i + 1:])


def _mark_index(letters: str) -> int:
    for target in ('a', 'e', 'ou'):
        i = letters.find(target)
        if i >= 0:
            return i
    for i in range(len(letters) - 1, -1, -1):
        if letters[i] in 'iouü':
            return i
    for i, c in enumerate(letters):
        if c in 'mn':
            return i
    return -1


def to_numbered(reading: Optional[str]) -> str:
    """Display reading -> numbered pinyin, space-separated ('yuán xíng' -> 'yuan2 xing2').

    Tone 1-4 from the mark, 5 for an unmarked syllable; ü stays ü (the form the stored
    numbered parts use, '(lü4 mai4)'). The digit goes after the syllable's coda, so a token
    holding two syllables splits ('yíhuìr' -> 'yi2 huir4'). Already-numbered syllables pass
    through. Mirrors the zh branch of calibration_normalise_pronunciation for readings with
    no numbered part (the SQL removes the spaces).
    """
    s = display_form(reading)
    if not s:
        return ''
    d = unicodedata.normalize('NFD', s.lower())
    for pattern, tone in _TONE_PLACEMENT:
        d = pattern.sub(lambda m, t=tone: m.group(1) + str(t), d)
    d = unicodedata.normalize('NFC', d)
    d = _NEUTRAL_END_RE.sub(r'\g<1>5', d)
    tokens = [t for t in _SEPARATOR_RE.split(d) if t]
    return ' '.join(_SYLLABLE_BREAK_RE.sub(' ', t) for t in tokens)


def build_inventory(readings: Iterable[Optional[str]]) -> Dict[str, FrozenSet[int]]:
    """base -> attested full tones (1-4), from zh dictionary readings.

    Every syllable base that occurs is listed, also one only ever seen neutral (empty set),
    as calibration_refresh_zh_tone_inventory() stores it.
    """
    inv: Dict[str, set] = {}
    for r in readings:
        for s in parse(r):
            if s.base is None:
                continue
            tones = inv.setdefault(s.base, set())
            if s.tone in FULL_TONES:
                tones.add(s.tone)
    return {b: frozenset(t) for b, t in inv.items()}


def _combo_digest(tones: Sequence[int]) -> Tuple[str, str]:
    digits = ''.join(str(t) for t in tones)
    return hashlib.md5(digits.encode('ascii')).hexdigest(), digits


def variants(display: Optional[str], lemma: Optional[str],
             inventory: Mapping[str, Iterable[int]],
             own_readings: Iterable[Optional[str]] = (),
             cap: int = VARIANT_CAP) -> List[str]:
    """Every valid tone variant of a zh reading under rule 4 (ADR-060), at most ``cap``.

    * Only full-tone syllables change, and only to full tones the inventory lists for their
      base (the syllable's own tone always counts as attested). Neutral syllables, tokens
      that are not syllables, and syllables written 一 or 不 (aligned by position when the
      lemma's character count equals the syllable count) keep their tone.
    * A combination whose only changes are tone 3 -> 2 before an original tone-3 syllable is
      a sandhi form and is dropped, as is the original itself.
    * A variant never equals any of ``own_readings`` (the lemma's readings: polyphones).
    * Order: md5 of the tone digits (a fixed pseudo-random order, so the first ``cap`` are a
      uniform-looking sample), then the digits. The display keeps every separator and
      unchanged token as written; changed syllables are re-marked (``mark_syllable``).
    """
    segs = segments(display)
    syls = [s for _, s in segs if s is not None]
    n = len(syls)
    if n == 0:
        return []
    aligned = lemma is not None and len(lemma) == n
    options: List[Tuple[int, ...]] = []
    for k, s in enumerate(syls):
        if s.base is None or s.tone == NEUTRAL or (aligned and lemma[k] in FIXED_CHARS):
            options.append((s.tone,))
        else:
            attested = {t for t in inventory.get(s.base, ()) if t in FULL_TONES}
            options.append(tuple(sorted(attested | {s.tone})))
    original = tuple(s.tone for s in syls)
    frame = ' '.join(s.frame for s in syls)
    own = {tones for f, tones in map(reading_key, own_readings) if f == frame}

    def real_change(combo: Tuple[int, ...]) -> bool:
        return any(
            combo[k] != original[k]
            and not (original[k] == 3 and combo[k] == 2 and k + 1 < n and original[k + 1] == 3)
            for k in range(n))

    picked = sorted((c for c in itertools.product(*options)
                     if real_change(c) and c not in own), key=_combo_digest)[:max(cap, 0)]
    out = []
    for combo in picked:
        it = iter(zip(syls, combo))
        parts = []
        for text, syl in segs:
            if syl is None:
                parts.append(text)
                continue
            s, t = next(it)
            parts.append(s.text if t == s.tone else mark_syllable(s.base, t))
        out.append(unicodedata.normalize('NFC', ''.join(parts)))
    return out
