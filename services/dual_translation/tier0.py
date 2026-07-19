"""Tier 0 deterministic grading pre-pass for dual-translation (TASK-605).

The cheapest, always-first step of the grading cascade
(wiki/algorithms/translation-grading-cascade.tech.md — "Tier 0 — deterministic
pre-pass"). Never calls a model. Pipeline:

  1. Normalize reproduction + gold L2 text — width (full/half) + kana, on top
     of services.dictation.tokenizer.normalize (lowercase/diacritics/punct/
     whitespace), which doesn't cover either.
  2. Diff via services.dictation.grader.grade_dictation — reused as-is, not
     reimplemented. Its WordDiff opcode list (equal/replace/insert/delete) is
     exactly the "token opcode array" shape dt_grade.diff wants.
  3. Full-marks gate (TASK-623): resolve to full marks, no errors, only when
     the reproduction is identical to the gold *modulo normalization*. Both
     texts are already folded (step 1's _normalize_l2, plus grade_dictation's
     own services.dictation.tokenizer.normalize) before the diff is computed,
     so a normalization-only difference — punctuation / full-half width / kana —
     never survives as a non-'equal' opcode. Full marks therefore holds iff
     every diff opcode is 'equal'; any surviving replace/insert/delete — a real
     word swapped, dropped or added — escalates to the cascade. The gate keys
     on the opcode CLASS, not on grade_dictation's accuracy: its Levenshtein
     fuzzy tolerance marks a >=4-char, edit-distance-1 replace as "correct"
     (accuracy 1.0) while still emitting a 'replace' opcode, so a strict,
     non-fuzzy opcode check is what stops a real single-character edit from
     sailing through. This retires the old NEAR_EXACT_MISMATCH_RATIO proxy,
     which resolved any submission whose token-mismatch ratio sat under 5% and
     thereby silently awarded full marks to single-token errors in multi-
     sentence passages (the leniency hole the v1 baseline exposed).
  4. Result cache, keyed hash(passage_id, normalized_reproduction) — a plain
     in-process dict matching this repo's existing convention for
     low-cardinality lookup caches (services.dual_translation.router's
     `_cfg_cache`, services.prompt_service.PromptService._prompt_cache):
     no DB-backed cache exists for anything this shape, so this doesn't
     invent a new layer.

Submissions Tier 0 cannot resolve (`Tier0Result.resolved=False`) are handed
to the cascade (services.dual_translation.grader_cascade, TASK-606) along
with the diff already computed, so the cascade never re-diffs.
"""

from __future__ import annotations

import hashlib
import logging
import unicodedata
from dataclasses import dataclass, field, replace
from typing import Optional

import jaconv

from services.dictation.grader import GradingResult, grade_dictation

logger = logging.getLogger(__name__)

# Matches the rubric's five analytic dimensions (dual-translation.tech.md
# "Rubric (Feature 1)"). Weighting into overall_band lives in
# dt_rubric_version, not here — at a flat all-4 score the weighted mean is
# trivially 4 regardless of weights.
RUBRIC_DIMENSIONS = ("accuracy", "understandability", "fidelity", "range", "naturalness")
MAX_BAND = 4


@dataclass
class Tier0Result:
    """Tier 0 grading outcome.

    `resolved=True`: Tier 0 produced the final grade; no model call happens
    for this submission, ever. `resolved=False`: the diff was too large for
    Tier 0's deterministic check or the gate stub; `scores`/`overall_band`
    are None and the caller must escalate to the cascade.
    """

    resolved: bool
    diff: list[dict]
    grader_trace: dict
    mismatch_ratio: float = 0.0
    scores: Optional[dict[str, int]] = None
    overall_band: Optional[int] = None
    errors: list = field(default_factory=list)
    cache_hit: bool = False


_result_cache: dict[str, Tier0Result] = {}


def grade_tier0(
    passage_id: int,
    gold_l2: str,
    reproduction: str,
    language_code: str,
) -> Tier0Result:
    """Run the Tier 0 deterministic pre-pass for one submission.

    Args:
        passage_id: dt_passage.id — part of the cache key (the gold text
            itself is implied by the passage, so it isn't hashed separately).
        gold_l2: the passage's gold L2 reference text.
        reproduction: the learner's L2 attempt.
        language_code: ISO 639-1 ('zh', 'en', 'ja', ...) — controls width/kana
            normalization here and tokenization inside grade_dictation.
    """
    normalized_reproduction = _normalize_l2(reproduction, language_code)

    cache_key = _cache_key(passage_id, normalized_reproduction)
    cached = _result_cache.get(cache_key)
    if cached is not None:
        return replace(cached, cache_hit=True, grader_trace={**cached.grader_trace, "cache_hit": True})

    normalized_gold = _normalize_l2(gold_l2, language_code)
    grading = grade_dictation(normalized_gold, normalized_reproduction, language_code)
    mismatch_ratio = 1.0 - grading.accuracy

    if _resolves_full_marks(grading):
        result = _full_marks_result(grading, mismatch_ratio)
    else:
        result = Tier0Result(
            resolved=False,
            diff=grading.diff_payload(),
            mismatch_ratio=mismatch_ratio,
            grader_trace=_trace(deterministic_prefilter=False),
        )

    _result_cache[cache_key] = result
    return result


def clear_cache() -> None:
    """Test/ops hook: drop all cached Tier 0 results."""
    _result_cache.clear()


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------

def _resolves_full_marks(grading: GradingResult) -> bool:
    """Tier 0 awards full marks only when reproduction == gold modulo
    normalization: every diff opcode must be 'equal'.

    grade_tier0 folds both texts through _normalize_l2 (width/kana) and
    grade_dictation folds them again through services.dictation.tokenizer.
    normalize (case/diacritics/punct/whitespace) *before* tokenizing, so a
    normalization-only difference never survives as a non-'equal' opcode in the
    first place — the diff spans are drawn straight from that fully-folded token
    stream. Full marks therefore holds iff there are no non-'equal' opcodes; an
    exact match satisfies this vacuously.

    Keys on the opcode CLASS, never on is_correct / accuracy — grade_dictation's
    fuzzy tolerance inflates accuracy to 1.0 for a >=4-char edit-distance-1
    replace while still emitting a 'replace' opcode, so this strict, non-fuzzy
    check is what keeps a real single-character edit from resolving here
    (TASK-623; replaces NEAR_EXACT_MISMATCH_RATIO).
    """
    return all(entry.op == "equal" for entry in grading.diff)


def _normalize_l2(text: str, language_code: str) -> str:
    """Width + kana normalization layer, applied before grade_dictation's own
    normalize() (which only handles lowercase/diacritics/punct/whitespace).

    NFKC folds full-width Latin/digit forms to half-width (critical for ZH/JA
    source text, which mixes both). For Japanese specifically, kata2hira
    folds katakana to hiragana so a learner's katakana rendering of a word
    matches a hiragana gold (or vice versa) — same NFKC + jaconv.kata2hira
    pairing services.furigana_service already uses for reading comparisons.
    """
    out = unicodedata.normalize("NFKC", text or "")
    if (language_code or "").lower() == "ja":
        out = jaconv.kata2hira(out)
    return out


def _full_marks_result(grading: GradingResult, mismatch_ratio: float) -> Tier0Result:
    return Tier0Result(
        resolved=True,
        diff=grading.diff_payload(),
        mismatch_ratio=mismatch_ratio,
        scores={dim: MAX_BAND for dim in RUBRIC_DIMENSIONS},
        overall_band=MAX_BAND,
        errors=[],
        grader_trace=_trace(deterministic_prefilter=True),
    )


def _trace(*, deterministic_prefilter: bool) -> dict:
    return {
        "tier": "tier0",
        "deterministic_prefilter": deterministic_prefilter,
        "cache_hit": False,
        "tokens": {"in": 0, "out": 0},
        "slugs": [],
    }


def _cache_key(passage_id: int, normalized_reproduction: str) -> str:
    raw = f"{passage_id}:{normalized_reproduction}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()
