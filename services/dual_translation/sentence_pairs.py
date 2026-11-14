"""Sentence splitting + alignment for the DT single-call grader (ADR-044).

Ported unchanged in behaviour from the experiment harness
(``data/eval/jev_dt_2026-09-26/sentences.py``), because the validated single-call
prompt numbers its sentence pairs with exactly this pairing: a different splitter
would send a different prompt than the one that was measured.

Splits reference / reproduction on ``。！？!?.`` and newline runs, keeping character
offsets into the ORIGINAL string. Equal sentence counts pair index-for-index;
otherwise a ``difflib.SequenceMatcher`` alignment over the sentence texts merges
every non-equal block into one pair per side, so every character of both texts lands
in exactly one pair. Pure — no I/O.
"""

from __future__ import annotations

import difflib
from dataclasses import dataclass

_DELIMS = "。！？!?."


@dataclass
class Sentence:
    text: str
    start: int
    end: int  # half-open, into the original string


@dataclass
class SentencePair:
    ref: Sentence  # start/end may span a merged block; .text is the join
    repro: Sentence
    merged: bool = False  # True if this pair merges >1 source sentence on either side


@dataclass
class AlignmentResult:
    pairs: list[SentencePair]
    ok: bool
    reason: str = ""


def split_sentences(text: str) -> list[Sentence]:
    """Split ``text`` into sentences on delimiter chars (kept with the preceding
    sentence) or newline runs. A run of trailing delimiters/whitespace is absorbed
    into the sentence it follows, so spans never overlap and tile the string."""
    sentences: list[Sentence] = []
    n = len(text)
    start = 0
    i = 0
    while i < n:
        ch = text[i]
        if ch in _DELIMS:
            j = i + 1
            while j < n and (text[j] in _DELIMS or text[j].isspace()):
                j += 1
            sentences.append(Sentence(text=text[start:j], start=start, end=j))
            start = j
            i = j
        elif ch == "\n":
            j = i
            while j < n and text[j] == "\n":
                j += 1
            if j > start:
                seg = text[start:j]
                if seg.strip():
                    sentences.append(Sentence(text=seg, start=start, end=j))
            start = j
            i = j
        else:
            i += 1
    if start < n:
        tail = text[start:n]
        if tail.strip():
            sentences.append(Sentence(text=tail, start=start, end=n))
    return sentences


def _join(seq: list[Sentence]) -> Sentence:
    if len(seq) == 1:
        return seq[0]
    return Sentence(text="".join(s.text for s in seq), start=seq[0].start, end=seq[-1].end)


def align_pairs(ref_sents: list[Sentence], repro_sents: list[Sentence]) -> AlignmentResult:
    """Align the two sentence lists (see module docstring). ``ok`` is False when the
    pairing is doubtful: equal counts but a pair with < 0.3 text similarity, or an
    unequal-count alignment that had to merge a block."""
    if len(ref_sents) == len(repro_sents) and len(ref_sents) > 0:
        pairs = [SentencePair(ref=r, repro=p) for r, p in zip(ref_sents, repro_sents)]
        bad = 0
        for pr in pairs:
            if difflib.SequenceMatcher(None, pr.ref.text, pr.repro.text).ratio() < 0.3:
                bad += 1
        if bad:
            return AlignmentResult(
                pairs=pairs, ok=False,
                reason=f"equal sentence counts ({len(ref_sents)}) but {bad} pair(s) have <0.3 text similarity",
            )
        return AlignmentResult(pairs=pairs, ok=True)

    ref_texts = [s.text for s in ref_sents]
    repro_texts = [s.text for s in repro_sents]
    sm = difflib.SequenceMatcher(None, ref_texts, repro_texts, autojunk=False)
    pairs: list[SentencePair] = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        ref_block = ref_sents[i1:i2]
        repro_block = repro_sents[j1:j2]
        if tag == "equal":
            for r, p in zip(ref_block, repro_block):
                pairs.append(SentencePair(ref=r, repro=p, merged=False))
            continue
        # replace/insert/delete: merge the whole block into one pair per side. An
        # empty side gets a zero-length sentence anchored at the boundary.
        if ref_block:
            ref_joined = _join(ref_block)
        else:
            anchor = ref_sents[i1 - 1].end if i1 > 0 else 0
            ref_joined = Sentence(text="", start=anchor, end=anchor)
        if repro_block:
            repro_joined = _join(repro_block)
        else:
            anchor = repro_sents[j1 - 1].end if j1 > 0 else 0
            repro_joined = Sentence(text="", start=anchor, end=anchor)
        pairs.append(SentencePair(ref=ref_joined, repro=repro_joined, merged=True))

    n_merged = sum(1 for p in pairs if p.merged)
    reason = (f"unequal sentence counts (ref={len(ref_sents)}, repro={len(repro_sents)}); "
              f"difflib alignment produced {len(pairs)} pairs, {n_merged} merged")
    return AlignmentResult(pairs=pairs, ok=(n_merged == 0), reason=reason)


def build_sentence_pairs(reference: str, reproduction: str) -> AlignmentResult:
    return align_pairs(split_sentences(reference or ""), split_sentences(reproduction or ""))
