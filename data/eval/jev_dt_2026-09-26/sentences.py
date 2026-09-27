# -*- coding: utf-8 -*-
"""Sentence splitting + alignment for the A2 (sentence-level-with-context) arm.

Splits reference/reproduction into sentences on 。！？!?. plus newlines,
keeping character offsets into the ORIGINAL string. Aligns the two sentence
lists index-by-index when counts match; otherwise falls back to a
difflib.SequenceMatcher alignment over the sentence-text lists, merging any
insert/delete/replace block into a single pair (concatenating the sentences
in that block) so every character of both texts ends up in exactly one pair
and none is dropped. Any fallback (or an equal-count-but-imperfect ratio
alignment) is reported so run.py/results can flag it.

Then maps each gold `expected_errors[i]` to the sentence pair whose
reproduction span contains `span_repro`, by start offset.
"""
from __future__ import annotations

import difflib
import re
from dataclasses import dataclass, field

_DELIMS = "。！？!?."
_DELIM_RE = re.compile(f"[{re.escape(_DELIMS)}]|\n+")


@dataclass
class Sentence:
    text: str
    start: int
    end: int  # half-open, into the original string


def split_sentences(text: str) -> list[Sentence]:
    """Split `text` into sentences on delimiter chars (kept as part of the
    preceding sentence) or newline runs (dropped, sentence boundary only).
    Keeps exact offsets; consecutive delimiters / trailing whitespace are
    absorbed into the sentence that precedes them so spans never overlap and
    always tile the full original string when reassembled."""
    sentences: list[Sentence] = []
    n = len(text)
    start = 0
    i = 0
    while i < n:
        ch = text[i]
        if ch in _DELIMS:
            # Absorb a run of trailing delimiters/whitespace (e.g. "?!" or
            # ". \n") into the same sentence.
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
            if j > start:  # non-empty content before the newline run
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


@dataclass
class SentencePair:
    ref: Sentence  # start/end may span a merged block; .text is the join
    repro: Sentence
    merged: bool = False  # true if this pair merges >1 source sentence on either side


@dataclass
class AlignmentResult:
    pairs: list[SentencePair]
    ok: bool
    reason: str = ""


def _join(seq: list[Sentence]) -> Sentence:
    if len(seq) == 1:
        return seq[0]
    return Sentence(text="".join(s.text for s in seq), start=seq[0].start, end=seq[-1].end)


def align_pairs(ref_sents: list[Sentence], repro_sents: list[Sentence]) -> AlignmentResult:
    """Align ref/repro sentence lists. Equal counts -> index-for-index pairing
    (the common case; still checked for a reasonable per-pair text similarity
    and flagged, not rejected, if it looks poor). Unequal counts -> a
    difflib.SequenceMatcher alignment over sentence texts, merging every
    non-'equal' opcode block into one pair per side so nothing is lost."""
    if len(ref_sents) == len(repro_sents) and len(ref_sents) > 0:
        pairs = [SentencePair(ref=r, repro=p) for r, p in zip(ref_sents, repro_sents)]
        # Sanity check: flag (don't fail) if same-index pairing looks like a
        # bad alignment (very low character-level similarity) -- a signal
        # the split heuristic diverged from the natural sentence count match.
        bad = 0
        for pr in pairs:
            ratio = difflib.SequenceMatcher(None, pr.ref.text, pr.repro.text).ratio()
            if ratio < 0.3:
                bad += 1
        if bad:
            return AlignmentResult(pairs=pairs, ok=False,
                                    reason=f"equal sentence counts ({len(ref_sents)}) but {bad} pair(s) have <0.3 text similarity")
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
        # replace/insert/delete: merge the whole block into one pair per
        # side. An empty side (insert/delete) gets a zero-length sentence
        # anchored at the boundary so error-span containment still works.
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


def map_errors_to_pairs(expected_errors: list[dict], pairs: list[SentencePair]) -> list[int | None]:
    """For each expected_error, return the index into `pairs` whose repro
    span contains span_repro[0] (start offset), or None if no pair contains
    it (alignment failure for that error -- reported by the caller)."""
    out: list[int | None] = []
    for err in expected_errors:
        start = err["span_repro"][0]
        found = None
        for idx, pr in enumerate(pairs):
            if pr.repro.start <= start < pr.repro.end:
                found = idx
                break
            # zero-length (merged-away) repro sentence: allow exact boundary match
            if pr.repro.start == pr.repro.end == start:
                found = idx
                break
        out.append(found)
    return out


def build_sentence_pairs(reference: str, reproduction: str) -> AlignmentResult:
    ref_sents = split_sentences(reference)
    repro_sents = split_sentences(reproduction)
    return align_pairs(ref_sents, repro_sents)
