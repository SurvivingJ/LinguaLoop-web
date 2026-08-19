"""
Phonological confusion sets for reading and tone distractors (TASK-516 §5).

A reading exercise is only as good as its wrong answers. "What is the pinyin
for 张?" with options *zhāng / apple / 我 / xyz* tests nothing. The distractors
have to be things a learner might actually produce, which for these languages
means a short, well-understood list of confusions:

**Chinese** — ranked, most confusable first:

  1. *tone variants* — same segments, different tone (``zhāng`` vs ``zhǎng``).
     This is the single most common Mandarin error and the whole point of the
     exercise, so it outranks everything.
  2. *near initials* — the retroflex/alveolar pairs (zh/z, ch/c, sh/s), the
     n/l merger, aspirated/unaspirated stops (b/p, d/t, g/k, j/q).
  3. *near finals* — the nasal codas (an/ang, en/eng, in/ing) and the rounded
     pairs (u/ü), which is where most northern/southern variation lands.

**Japanese** — same idea, different inventory:

  1. *voicing* — dakuten/handakuten (か/が, は/ば/ぱ). Minimal pairs everywhere.
  2. *vowel length* — おじさん vs おじいさん. Length is phonemic and learners
     routinely drop it.
  3. *sokuon* — the geminating っ (きて vs きって).

Design notes
------------
Everything here is pure string manipulation over an inventory declared in this
module. No dictionary lookup, no network, no model. That matters because these
functions run once per sense per language in a 3,000-sense batch.

Generated candidates are *phonotactically plausible* by construction (we only
ever substitute one segment for another attested segment), but they are not
guaranteed to be real words. For the reading direction that is correct — the
learner is choosing a pronunciation, and a plausible non-word pronunciation is
a fair distractor. For the *reverse* direction (``pinyin_to_hanzi``) the
distractors must be real characters, so that generator sources them from the
corpus instead — see ``readings.py``.

Distinct from ``services/pinyin_service.py``, which segments text and applies
sandhi for the Tone Trainer. That module answers "what is this actually
pronounced?"; this one answers "what might a learner wrongly think it is?".
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Chinese: pinyin inventory
# ---------------------------------------------------------------------------

# Longest-first so 'zh' wins over 'z' when both could match.
_INITIALS: tuple[str, ...] = (
    'zh', 'ch', 'sh',
    'b', 'p', 'm', 'f', 'd', 't', 'n', 'l', 'g', 'k', 'h',
    'j', 'q', 'x', 'r', 'z', 'c', 's', 'y', 'w',
)

_FINALS: frozenset[str] = frozenset({
    'a', 'o', 'e', 'i', 'u', 'v', 'er',
    'ai', 'ei', 'ao', 'ou', 'an', 'en', 'ang', 'eng', 'ong',
    'ia', 'ie', 'iao', 'iu', 'ian', 'in', 'iang', 'ing', 'iong',
    'ua', 'uo', 'uai', 'ui', 'uan', 'un', 'uang', 'ueng',
    've', 'van', 'vn',
})

# Symmetric confusion pairs, in descending confusability.
_INITIAL_PAIRS: tuple[tuple[str, str], ...] = (
    ('zh', 'z'), ('ch', 'c'), ('sh', 's'),
    ('n', 'l'), ('l', 'r'),
    ('b', 'p'), ('d', 't'), ('g', 'k'), ('j', 'q'),
    ('f', 'h'), ('x', 's'), ('j', 'zh'), ('q', 'ch'), ('x', 'sh'),
)

_FINAL_PAIRS: tuple[tuple[str, str], ...] = (
    ('an', 'ang'), ('en', 'eng'), ('in', 'ing'),
    ('ian', 'iang'), ('uan', 'uang'), ('ong', 'eng'),
    ('u', 'v'), ('ai', 'ei'), ('ao', 'ou'), ('ie', 'ei'),
    ('uo', 'ou'), ('ia', 'ie'),
)

# Tone-marked vowel -> (bare vowel, tone number).
_TONE_MARKS: dict[str, tuple[str, int]] = {}
for _bare, _marked in (
    ('a', 'āáǎà'), ('o', 'ōóǒò'), ('e', 'ēéěè'),
    ('i', 'īíǐì'), ('u', 'ūúǔù'), ('v', 'ǖǘǚǜ'),
):
    for _idx, _char in enumerate(_marked):
        _TONE_MARKS[_char] = (_bare, _idx + 1)
_TONE_MARKS['ü'] = ('v', 0)

_MARKED_VOWEL: dict[tuple[str, int], str] = {
    ('a', 1): 'ā', ('a', 2): 'á', ('a', 3): 'ǎ', ('a', 4): 'à', ('a', 0): 'a',
    ('o', 1): 'ō', ('o', 2): 'ó', ('o', 3): 'ǒ', ('o', 4): 'ò', ('o', 0): 'o',
    ('e', 1): 'ē', ('e', 2): 'é', ('e', 3): 'ě', ('e', 4): 'è', ('e', 0): 'e',
    ('i', 1): 'ī', ('i', 2): 'í', ('i', 3): 'ǐ', ('i', 4): 'ì', ('i', 0): 'i',
    ('u', 1): 'ū', ('u', 2): 'ú', ('u', 3): 'ǔ', ('u', 4): 'ù', ('u', 0): 'u',
    ('v', 1): 'ǖ', ('v', 2): 'ǘ', ('v', 3): 'ǚ', ('v', 4): 'ǜ', ('v', 0): 'ü',
}

_NUMBERED_RE = re.compile(r'^([a-zü]+?)([1-5])?$')


@dataclass(frozen=True)
class Syllable:
    """One pinyin syllable, decomposed.

    ``tone`` is 0 for neutral/unmarked. ``final`` uses ``v`` for ü internally
    so it is ASCII-safe for pair lookups; :meth:`marked` puts the umlaut back.
    """

    initial: str
    final: str
    tone: int

    @property
    def base(self) -> str:
        """Segments without the tone, e.g. ``zhang``."""
        return f'{self.initial}{self.final}'.replace('v', 'ü')

    def numbered(self) -> str:
        return f'{self.base}{self.tone}' if self.tone else self.base

    def marked(self) -> str:
        """Render with a tone mark, e.g. ``zhāng``."""
        return _mark_syllable(self.initial, self.final, self.tone)


def _mark_syllable(initial: str, final: str, tone: int) -> str:
    """Place the tone mark per the standard rule.

    a/o/e take it; otherwise the *last* vowel does — which is what makes
    ``iu`` -> ``iù`` and ``ui`` -> ``uì`` come out right without special-casing
    either.
    """
    if not final:
        return initial
    target = -1
    for vowel in ('a', 'o', 'e'):
        idx = final.find(vowel)
        if idx >= 0:
            target = idx
            break
    if target < 0:
        for idx in range(len(final) - 1, -1, -1):
            if final[idx] in 'iuv':
                target = idx
                break
    if target < 0:
        return f'{initial}{final}'.replace('v', 'ü')
    marked = _MARKED_VOWEL.get((final[target], tone), final[target])
    out = final[:target] + marked + final[target + 1:]
    return f'{initial}{out}'.replace('v', 'ü')


def _split_syllable(raw: str) -> Syllable | None:
    """Split one bare or numbered syllable (``zhang1``, ``zhāng``) into parts."""
    text = (raw or '').strip().lower()
    if not text:
        return None

    # Tone marks -> bare letters + tone number.
    tone = 0
    bare_chars: list[str] = []
    for char in unicodedata.normalize('NFC', text):
        if char in _TONE_MARKS:
            base, mark_tone = _TONE_MARKS[char]
            bare_chars.append(base)
            if mark_tone:
                tone = mark_tone
        else:
            bare_chars.append(char)
    text = ''.join(bare_chars)

    match = _NUMBERED_RE.match(text)
    if not match:
        return None
    body, digit = match.group(1), match.group(2)
    if digit:
        tone = int(digit) % 5          # 5 is the neutral tone in some schemes

    for initial in _INITIALS:
        if body.startswith(initial):
            final = body[len(initial):]
            if final in _FINALS:
                return Syllable(initial, final, tone)
            break
    if body in _FINALS:
        return Syllable('', body, tone)
    return None


def parse_pinyin(pronunciation: str | None) -> list[Syllable]:
    """Parse a stored ZH ``pronunciation`` into syllables.

    The corpus stores both notations in one string —
    ``"suān dīng èr zhǐ (suan1 ding1 er4 zhi3)"``. The parenthesised numbered
    form is preferred because it is unambiguous ASCII; the marked form is the
    fallback for rows written before that convention. Returns ``[]`` for
    anything unparseable, which callers must treat as "skip this exercise"
    rather than "emit an item with no distractors".
    """
    if not pronunciation:
        return []

    numbered = re.search(r'\(([^)]*)\)', pronunciation)
    candidates: list[str] = []
    if numbered:
        candidates.append(numbered.group(1))
    candidates.append(re.sub(r'\([^)]*\)', ' ', pronunciation))

    for candidate in candidates:
        parts = [p for p in re.split(r'[\s·\-]+', candidate.strip()) if p]
        parsed = [_split_syllable(p) for p in parts]
        if parsed and all(s is not None for s in parsed):
            return [s for s in parsed if s is not None]
    return []


def format_pinyin(syllables: list[Syllable]) -> str:
    """Space-separated tone-marked rendering of a whole word."""
    return ' '.join(s.marked() for s in syllables)


def _pairs_for(segment: str, pairs: tuple[tuple[str, str], ...]) -> list[str]:
    """Confusion partners for one segment, in declaration order."""
    out: list[str] = []
    for left, right in pairs:
        if segment == left:
            out.append(right)
        elif segment == right:
            out.append(left)
    return out


def pinyin_distractors(syllables: list[Syllable], count: int = 3) -> list[str]:
    """Ranked wrong pronunciations for a whole word, tone-marked.

    Tone variants first (rule 1), then one-segment substitutions on initials,
    then on finals. Deduplicated against the key and against each other;
    returns fewer than ``count`` if the inventory cannot supply that many,
    which the caller must handle by skipping the item rather than padding with
    noise.
    """
    if not syllables:
        return []

    key = format_pinyin(syllables)
    seen = {key}
    out: list[str] = []

    def add(variant: list[Syllable]) -> bool:
        text = format_pinyin(variant)
        if text not in seen:
            seen.add(text)
            out.append(text)
        return len(out) >= count

    # 1. Tone variants. Position order puts the last syllable first — that is
    #    where Mandarin tone errors concentrate in polysyllables — but the
    #    loops are nested tone-outermost so a four-option item perturbs a
    #    *different* syllable each time before returning to one it has already
    #    used. Three variants of the final syllable and nothing else would let
    #    the learner ignore the rest of the word.
    order = [len(syllables) - 1] + list(range(len(syllables) - 1))
    for tone in (1, 2, 3, 4):
        for idx in order:
            if tone == syllables[idx].tone:
                continue
            variant = list(syllables)
            variant[idx] = Syllable(
                syllables[idx].initial, syllables[idx].final, tone,
            )
            if add(variant):
                return out[:count]

    # 2. Near initials, 3. near finals — one substitution at a time.
    for pairs, attr in ((_INITIAL_PAIRS, 'initial'), (_FINAL_PAIRS, 'final')):
        for idx, syllable in enumerate(syllables):
            for partner in _pairs_for(getattr(syllable, attr), pairs):
                initial = partner if attr == 'initial' else syllable.initial
                final = partner if attr == 'final' else syllable.final
                if final not in _FINALS:
                    continue
                variant = list(syllables)
                variant[idx] = Syllable(initial, final, syllable.tone)
                if add(variant):
                    return out[:count]

    return out[:count]


def tone_pattern(syllables: list[Syllable]) -> str:
    """The word's tone sequence as a digit string, e.g. ``"14"``."""
    return ''.join(str(s.tone) for s in syllables)


def tone_pattern_distractors(syllables: list[Syllable], count: int = 3) -> list[str]:
    """Wrong tone sequences of the same length as the key.

    Single-tone perturbations only. A pattern differing in every position is a
    giveaway; the exercise is worth something only when the learner has to hear
    which syllable moved.
    """
    if not syllables:
        return []
    key = tone_pattern(syllables)
    seen = {key}
    out: list[str] = []
    order = [len(syllables) - 1] + list(range(len(syllables) - 1))
    for idx in order:
        for tone in (1, 2, 3, 4):
            digits = [str(s.tone) for s in syllables]
            if digits[idx] == str(tone):
                continue
            digits[idx] = str(tone)
            candidate = ''.join(digits)
            if candidate not in seen:
                seen.add(candidate)
                out.append(candidate)
            if len(out) >= count:
                return out
    return out


# ---------------------------------------------------------------------------
# Japanese: kana confusion
# ---------------------------------------------------------------------------

# Voicing pairs. Handakuten (は/ぱ) is listed alongside dakuten (は/ば) so both
# are reachable from the plain kana.
_VOICING: tuple[tuple[str, str], ...] = tuple(
    zip(
        'かきくけこさしすせそたちつてとはひふへほはひふへほ',
        'がぎぐげござじずぜぞだぢづでどばびぶべぼぱぴぷぺぽ',
    )
)

_VOWEL_OF: dict[str, str] = {}
for _row, _vowel in (
    ('あかさたなはまやらわがざだばぱ', 'あ'),
    ('いきしちにひみりぎじぢびぴ', 'い'),
    ('うくすつぬふむゆるぐずづぶぷ', 'う'),
    ('えけせてねへめれげぜでべぺ', 'え'),
    ('おこそとのほもよろをごぞどぼぽ', 'お'),
):
    for _kana in _row:
        _VOWEL_OF[_kana] = _vowel

# Which kana lengthens which vowel, for the long/short pair. え and お lengthen
# with い and う respectively in native orthography (えい, おう).
_LENGTHENER: dict[str, str] = {
    'あ': 'あ', 'い': 'い', 'う': 'う', 'え': 'い', 'お': 'う',
}

_SOKUON = 'っ'

# っ geminates the following consonant, which is only phonotactically possible
# before a voiceless obstruent. Anything else (っ before a vowel, な-row, or a
# voiced consonant) is unpronounceable rather than confusable.
_SOKUON_FOLLOWERS: frozenset[str] = frozenset(
    'かきくけこさしすせそたちつてとぱぴぷぺぽはひふへほ'
)


def kana_distractors(reading: str | None, count: int = 3) -> list[str]:
    """Ranked wrong readings for a Japanese word.

    Order mirrors the module docstring: voicing, then vowel length, then
    sokuon. Only kana input is meaningful — a reading containing kanji means
    the pronunciation column was never backfilled for this sense, and the
    caller should skip rather than build an exercise around a half-reading.
    """
    text = (reading or '').strip()
    if not text or not is_kana(text):
        return []

    seen = {text}
    out: list[str] = []

    def add(candidate: str) -> bool:
        if candidate and candidate != text and candidate not in seen:
            seen.add(candidate)
            out.append(candidate)
        return len(out) >= count

    # 1. Voicing — flip one mora, later morae first (word-medial rendaku is
    #    where learners hesitate).
    for idx in range(len(text) - 1, -1, -1):
        for partner in _pairs_for(text[idx], _VOICING):
            if add(text[:idx] + partner + text[idx + 1:]):
                return out[:count]

    # 2. Vowel length. *Shortening* runs as its own pass first: if the word
    #    already has a long vowel, dropping it is the error a learner actually
    #    makes (がっこう -> がっこ), and a single right-to-left pass that can
    #    lengthen would reach the trailing う and emit がっこうう instead.
    for idx in range(len(text) - 1):
        vowel = _VOWEL_OF.get(text[idx])
        lengthener = _LENGTHENER.get(vowel or '')
        if lengthener and text[idx + 1] == lengthener:
            if add(text[:idx + 1] + text[idx + 2:]):
                return out[:count]

    # Then lengthening, left-to-right: おじさん -> おじいさん reads as a word,
    # おじさあん does not, and the earlier morae are where the real minimal
    # pairs live.
    for idx in range(len(text)):
        vowel = _VOWEL_OF.get(text[idx])
        lengthener = _LENGTHENER.get(vowel or '')
        if not lengthener or text[idx + 1: idx + 2] == lengthener:
            continue
        if add(text[:idx + 1] + lengthener + text[idx + 1:]):
            return out[:count]

    # 3. Sokuon — insert or remove the geminating っ. Insertion is only legal
    #    before a voiceless obstruent (か/さ/た/ぱ rows); っ before a vowel,
    #    nasal, or voiced consonant is not a mistake a learner makes because it
    #    is not pronounceable Japanese.
    if _SOKUON in text:
        if add(text.replace(_SOKUON, '', 1)):
            return out[:count]
    for idx in range(1, len(text)):
        if text[idx] not in _SOKUON_FOLLOWERS or text[idx - 1] == _SOKUON:
            continue
        if add(text[:idx] + _SOKUON + text[idx:]):
            return out[:count]

    return out[:count]


def is_kana(text: str) -> bool:
    """True when every character is hiragana, katakana, or a length mark."""
    if not text:
        return False
    for char in text:
        if char in 'ー 　':
            continue
        code = ord(char)
        if not (0x3040 <= code <= 0x309F or 0x30A0 <= code <= 0x30FF):
            return False
    return True


def has_kanji(text: str | None) -> bool:
    """Whether the string contains any CJK ideograph."""
    return any(0x4E00 <= ord(c) <= 0x9FFF for c in (text or ''))
