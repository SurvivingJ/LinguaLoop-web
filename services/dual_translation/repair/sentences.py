"""Sentence model for guided repair (tech 3.1).

``build_sentence_pairs(gold_l2, reproduction)`` is the pairing the single-call
grader numbered, so ``dt_error_instance.sentence_index`` indexes it. Only offsets
are kept; sentences are re-sliced from ``dt_submission.reproduction`` and
``dt_passage.l2_text`` whenever they are needed.

Pure except ``l1_prompts(db, ...)``.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from services.dual_translation.passage_builder import join_sentences
from services.dual_translation.sentence_pairs import build_sentence_pairs, split_sentences

logger = logging.getLogger(__name__)

_USABLE_VERDICTS = ("pass", "rewritten")


@dataclass(frozen=True)
class PairModel:
    index: int
    repro_start: int
    repro_end: int
    ref_start: int
    ref_end: int
    # Raw (unstripped) pair bounds, used to place merged reference sentences.
    raw_ref_start: int
    raw_ref_end: int


def stripped(text: str, start: int, end: int) -> tuple[int, int]:
    """[start, end) moved inward past leading/trailing whitespace (may be empty)."""
    while start < end and text[start].isspace():
        start += 1
    while end > start and text[end - 1].isspace():
        end -= 1
    return start, end


def sentence_model(gold_l2: str, reproduction: str) -> list[PairModel]:
    """One PairModel per sentence pair, with stripped offsets."""
    pairs = build_sentence_pairs(gold_l2 or "", reproduction or "").pairs
    out = []
    for i, pair in enumerate(pairs):
        rs, re_ = stripped(reproduction or "", pair.repro.start, pair.repro.end)
        fs, fe = stripped(gold_l2 or "", pair.ref.start, pair.ref.end)
        out.append(PairModel(i, rs, re_, fs, fe, pair.ref.start, pair.ref.end))
    return out


def local_span(span, start: int, end: int) -> Optional[tuple[int, int]]:
    """An absolute [s, e] span -> local offsets inside [start, end), clamped to the
    sentence. None when the span is unusable or does not lie inside the sentence
    after clamping (then it is not locatable)."""
    if not isinstance(span, (list, tuple)) or len(span) != 2:
        return None
    try:
        s, e = int(span[0]), int(span[1])
    except (TypeError, ValueError):
        return None
    if e < s:
        return None
    length = end - start
    ls, le = s - start, e - start
    if le < 0 or ls > length:
        return None  # wholly outside the sentence
    ls, le = max(0, min(ls, length)), max(0, min(le, length))
    return ls, le


def l1_prompts(db, *, passage: dict, gold_l2: str, l1_language_id: int, l1_code: str,
               model: list[PairModel], l1_passage_text: Optional[str]) -> list[Optional[str]]:
    """The L1 prompt sentence for each pair, or None (tech 3.1 rules 1-3)."""
    return l1_context(db, passage=passage, gold_l2=gold_l2, l1_language_id=l1_language_id,
                      l1_code=l1_code, model=model, l1_passage_text=l1_passage_text)[0]


def l1_context(db, *, passage: dict, gold_l2: str, l1_language_id: int, l1_code: str,
               model: list[PairModel], l1_passage_text: Optional[str]):
    """-> (per-pair L1 prompts, whole L1 passage text or None). The whole text is
    ``dt_passage_reference.l1_text`` when there is one, else the joined range
    references (range passages have no passage-level reference)."""
    gold_sentences = split_sentences(gold_l2 or "")
    l1_texts: Optional[list[str]] = None
    range_texts: Optional[list[str]] = None
    if passage.get("sentence_start") is not None and passage.get("sentence_end") is not None \
            and passage.get("source_ref_id"):
        try:
            l1_texts = _range_l1_texts(db, str(passage["source_ref_id"]),
                                       int(passage["sentence_start"]), int(passage["sentence_end"]),
                                       l1_language_id)
        except Exception as exc:  # noqa: BLE001 - prompts are optional; rule 2/3 still apply
            logger.warning("dt_repair: range-passage L1 lookup failed: %s", exc)
            l1_texts = None
        range_texts = l1_texts
        if l1_texts is not None and len(l1_texts) != len(gold_sentences):
            l1_texts = None
    if l1_texts is None and l1_passage_text:
        split = [s.text.strip() for s in split_sentences(l1_passage_text)]
        if len(split) == len(gold_sentences):
            l1_texts = split
    whole = l1_passage_text or (join_sentences(range_texts, l1_code) if range_texts else None)
    if l1_texts is None:
        return [None] * len(model), whole
    return positional_prompts(gold_sentences, l1_texts, model, l1_code), whole


def positional_prompts(gold_sentences, l1_texts: list, model: list[PairModel],
                       l1_code: str) -> list[Optional[str]]:
    """Join the L1 texts of every gold sentence lying inside each pair's raw
    reference span (handles merged pairs)."""
    out: list[Optional[str]] = []
    for pm in model:
        parts = [l1_texts[i] for i, s in enumerate(gold_sentences)
                 if s.start >= pm.raw_ref_start and s.end <= pm.raw_ref_end and l1_texts[i]]
        out.append(join_sentences(parts, l1_code) if parts else None)
    return out


def _range_l1_texts(db, test_id: str, start: int, end: int, l1_language_id: int) -> Optional[list[str]]:
    """The usable L1 reference texts of test_sentences idx in [start, end], in idx
    order; None when any sentence lacks one. Same query as
    routes/dual_translation._get_usable_references (copied, not imported: services
    must not import route modules)."""
    rows = (
        db.table("test_sentences").select("id, idx")
        .eq("test_id", test_id).gte("idx", start).lte("idx", end).order("idx").execute()
    ).data or []
    if not rows:
        return None
    ids = [r["id"] for r in rows]
    refs = (
        db.table("test_sentence_references")
        .select("sentence_id, l1_text, review_verdict")
        .in_("sentence_id", ids)
        .eq("l1_language_id", l1_language_id)
        .eq("is_active", True)
        .in_("review_verdict", list(_USABLE_VERDICTS))
        .execute()
    ).data or []
    by_id = {r["sentence_id"]: r for r in refs if r.get("review_verdict") in _USABLE_VERDICTS}
    texts = []
    for row in rows:
        ref = by_id.get(row["id"])
        if not ref or not (ref.get("l1_text") or "").strip():
            return None
        texts.append(ref["l1_text"].strip())
    return texts
