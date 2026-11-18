"""Display diff for Japanese dual-translation grades: word cells, script-blind.

The diff shown under a grade (``contract['diff']``, stored in ``dt_grade.diff``)
used to be Tier 0's character diff. For Japanese that marks a correct answer
written in kanji as changed wherever the reference is in kana (わたし → 私,
くま → 熊, すき → 好き), although the grader itself never counts kana/kanji
spelling as an error. This module rebuilds the diff for display only:

  1. Both texts are split into words with fugashi (UniDic), punctuation dropped.
  2. The word sequences are aligned on dictionary form (lemma), so 私 lines up
     with わたし and 熊 with くま.
  3. An aligned pair counts as the same word when the surfaces are equal, or the
     readings are equal (熊/くま, 食べる/たべる, 下さい/ください), or one side is
     all kanji and the other all kana (私, whose dictionary reading わたくし is not
     the わたし of the reference). Same lemma with a different reading is a
     different form (食べ / たべる) and stays a change.
  4. Where the lemmas do not line up but the reference stretch is all kana and
     the learner's words read the same (がくせい / 学生, かいます / 飼います), it
     is a match: a kana reference gives sounds, not kanji, and the tokenizer's
     lemma for bare kana is a guess.

Grading is untouched: Tier 0's full-marks check, the model's diff-region hints
and every score still use Tier 0's character diff. A wrong homophone kanji for a
kana reference therefore shows as a match here; the grader's ``kanji_choice``
error type is what reports it. Where the reference itself has kanji, a
different kanji is a different lemma and stays a change.

Fails safe: any tokenizer problem returns the diff it was given.
"""

from __future__ import annotations

import logging
import unicodedata
from dataclasses import dataclass
from difflib import SequenceMatcher

import jaconv

from services.furigana_service import _get_tagger, _is_kanji

logger = logging.getLogger(__name__)

_PUNCTUATION_POS = ("補助記号", "空白")


@dataclass(frozen=True)
class _Word:
    surface: str
    lemma: str
    reading: str

    @property
    def all_kanji(self) -> bool:
        return bool(self.surface) and all(_is_kanji(c) for c in self.surface)

    @property
    def all_kana(self) -> bool:
        return bool(self.surface) and all(_is_kana(c) for c in self.surface)


def _is_kana(ch: str) -> bool:
    cp = ord(ch)
    return 0x3041 <= cp <= 0x309F or 0x30A0 <= cp <= 0x30FF


def display_diff(gold: str, reproduction: str, l2_code: str, fallback: list) -> list:
    """The diff to show for this grade: word cells for Japanese (see module
    docstring), ``fallback`` (Tier 0's diff) for every other language or when
    tokenizing fails. Same cell shape as Tier 0:
    ``{op, correct, user, is_correct, sense_id}``."""
    if (l2_code or "").lower() != "ja":
        return fallback
    try:
        return _word_diff(_words(gold), _words(reproduction))
    except Exception as exc:  # noqa: BLE001 — display only; never break a grade
        logger.warning("dual_translation.display_diff: falling back to the character diff: %s", exc)
        return fallback


def _words(text: str) -> list[_Word]:
    tagger = _get_tagger()
    words = []
    for w in tagger(unicodedata.normalize("NFKC", text or "")):
        surface = w.surface
        if not surface.strip():
            continue
        feature = w.feature
        if getattr(feature, "pos1", None) in _PUNCTUATION_POS:
            continue
        lemma = (getattr(feature, "lemma", None) or "").split("-")[0] or surface
        reading = jaconv.kata2hira(getattr(feature, "kana", None) or surface)
        words.append(_Word(surface=surface, lemma=lemma, reading=reading))
    return words


def _same_word(gold: _Word, user: _Word) -> bool:
    """Called only for a pair already aligned on lemma."""
    if gold.surface == user.surface or gold.reading == user.reading:
        return True
    return (gold.all_kanji and user.all_kana) or (gold.all_kana and user.all_kanji)


def _kana_reference_read_alike(gold: list[_Word], user: list[_Word]) -> bool:
    """A stretch the lemmas could not line up, where the reference is written
    only in kana and the learner's words read the same. A kana reference gives
    sounds, not kanji, and the tokenizer's lemma for bare kana is a guess
    (がくせい may split as がく + せい; かいます is read as 買う even after ねこを),
    so the learner's kanji for the same sounds is shown as a match."""
    return (bool(gold) and bool(user) and all(w.all_kana for w in gold)
            and "".join(w.reading for w in gold) == "".join(w.reading for w in user))


def _cell(op: str, gold: _Word | None, user: _Word | None) -> dict:
    return {
        "op": op,
        "correct": gold.surface if gold else None,
        "user": user.surface if user else None,
        "is_correct": op == "equal",
        "sense_id": None,
    }


def _word_diff(gold: list[_Word], user: list[_Word]) -> list[dict]:
    matcher = SequenceMatcher(None, [w.lemma for w in gold], [w.lemma for w in user], autojunk=False)
    cells: list[dict] = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        g, u = gold[i1:i2], user[j1:j2]
        if tag == "equal":
            for gw, uw in zip(g, u):
                cells.append(_cell("equal" if _same_word(gw, uw) else "replace", gw, uw))
            continue
        if tag == "replace" and _kana_reference_read_alike(g, u):
            cells.append({
                "op": "equal",
                "correct": "".join(w.surface for w in g),
                "user": "".join(w.surface for w in u),
                "is_correct": True,
                "sense_id": None,
            })
            continue
        for gw, uw in zip(g, u):
            cells.append(_cell("replace", gw, uw))
        for gw in g[len(u):]:
            cells.append(_cell("delete", gw, None))
        for uw in u[len(g):]:
            cells.append(_cell("insert", None, uw))
    return cells
