"""Japanese mora tokenizer + JMdict-simplified reader.

See ``.claude/reviews/l1-phonetic-trie-architecture.md`` §2 for the design.
Two independent pieces:

* ``to_morae`` — deterministic mora segmentation of a kana reading. Standard
  mora-counting rules (the same ones behind haiku meter), not invented for
  this task.
* ``iter_jmdict_entries`` — reads a JMdict-simplified JSON dump (see
  https://github.com/scriptin/jmdict-simplified) and yields
  ``(mora_sequence, surface_form, reading)`` for real headwords.
"""

from __future__ import annotations

import json
import unicodedata
from typing import Iterator

import jaconv

# Small kana that fuse with the *preceding* kana into a single mora rather
# than counting as a beat of their own: the yōon digraphs (きゃ, しゅ, ちょ,
# ...) plus the small vowels used in katakana loanword combinations (ファ,
# ティ, ウィ, ...). The architecture doc's table names ゃ/ゅ/ょ specifically
# for hiragana Japanese words; JMdict readings for gairaigo are katakana and
# routinely need the small-vowel extension too (フォーク = フォ・ー・ク, 3
# morae, not 4) — omitting it would mis-segment every loanword with a small
# vowel in its reading, so it's included here as a deliberate, documented
# extension of the same underlying convention rather than a second rule.
_FUSING_SMALL_KANA = frozenset(
    "ゃゅょぁぃぅぇぉゎ"       # hiragana
    "ャュョァィゥェォヮ"       # katakana
)

# Chōon (ー) and small tsu / sokuon (っ/ッ) are each their own mora — they
# need no special casing beyond "don't fuse them", since that's the default
# behavior for anything not in _FUSING_SMALL_KANA.


def to_morae(reading: str) -> list[str]:
    """Segment a kana reading into morae.

    NFKC-normalizes first (folds half-width katakana etc. into standard
    forms) so a reading pulled from any source lines up with JMdict's own
    encoding. Does not fold katakana to hiragana — callers that want a
    single canonical case (this module's JMdict reader does) do that before
    calling this, so ``to_morae`` stays a pure segmentation function usable
    on either kana script.
    """
    if not reading:
        return []
    normalized = unicodedata.normalize("NFKC", reading)
    morae: list[str] = []
    for ch in normalized:
        if ch in _FUSING_SMALL_KANA and morae:
            morae[-1] = morae[-1] + ch
        else:
            morae.append(ch)
    return morae


# JMdict part-of-speech tags that mark a sense as a bound morpheme rather
# than a standalone word: prefixes, suffixes, and counters can't stand alone
# as an L1 distractor a learner reads as its own word. A word is only
# excluded if *every* sense is exclusively one of these — a word that is
# also a standalone noun/verb in some other sense stays in, per the
# architecture doc's "don't over-engineer on the first pass" instruction.
_NON_LEMMA_POS = frozenset({"pref", "n-pref", "suf", "n-suf", "ctr"})


def _is_real_headword(entry: dict) -> bool:
    sense_pos_sets = [
        set(sense.get("partOfSpeech") or ()) for sense in entry.get("sense", ())
    ]
    if not sense_pos_sets:
        return True  # no POS data at all — keep rather than guess
    return not all(pos and pos <= _NON_LEMMA_POS for pos in sense_pos_sets)


def _spellings_for_kana(kana: dict, kanji_by_text: dict[str, dict]) -> list[str]:
    """The surface form(s) a kana reading should be indexed under.

    If this reading applies only to specific kanji spellings
    (``appliesToKanji``), use those. If it applies to all of them (``["*"]``)
    or there are no kanji forms on this entry at all, fall back to indexing
    the kana text itself as the surface form — the correct behavior for
    words conventionally written in kana alone (JMdict tags these ``uk``,
    but plenty of entries have no kanji field at all, e.g. gairaigo).
    """
    if not kanji_by_text:
        return [kana.get("text", "")]
    applies_to = kana.get("appliesToKanji") or []
    if applies_to == ["*"]:
        return list(kanji_by_text.keys())
    spellings = [t for t in applies_to if t in kanji_by_text]
    return spellings or [kana.get("text", "")]


def iter_jmdict_entries(path: str) -> Iterator[tuple[list[str], str, str]]:
    """Yield ``(mora_sequence, surface_form, reading)`` for real ja headwords.

    ``reading`` is the original kana text as JMdict stored it (hiragana or
    katakana); ``mora_sequence`` is computed from a hiragana-folded copy of
    it, so that a hiragana target reading and a katakana dictionary entry
    (or vice versa) land in the same trie path — the trie's unit space is
    "mora regardless of kana script", not "mora in one specific script".
    """
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)

    for entry in data.get("words", ()):
        if not _is_real_headword(entry):
            continue
        kanji_by_text = {k["text"]: k for k in entry.get("kanji", ()) if k.get("text")}
        for kana in entry.get("kana", ()):
            reading = kana.get("text") or ""
            if not reading:
                continue
            hira = jaconv.kata2hira(unicodedata.normalize("NFKC", reading))
            morae = to_morae(hira)
            if not morae:
                continue
            for spelling in _spellings_for_kana(kana, kanji_by_text):
                if spelling:
                    yield morae, spelling, reading
