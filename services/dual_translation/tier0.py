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
  3. Exact / fuzzy-equal (grading.accuracy == 1.0) -> full marks, no errors.
  4. Embedding-similarity gate: STUB. The embedding provider is an explicit
     OPEN decision (see the cascade doc), so this routes purely on diff
     mismatch ratio as a stand-in for semantic closeness. TODO(embedding-
     provider): replace NEAR_EXACT_MISMATCH_RATIO with a real similarity
     score once a provider is chosen; until then this is a deliberately
     coarse proxy and is not expected to be the final word on borderline
     submissions.
  5. Result cache, keyed hash(passage_id, normalized_reproduction) — a plain
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

# STUB for the embedding-similarity gate (point 4 above). A mismatch ratio at
# or below this is treated as close enough to resolve at Tier 0 without a
# model call, same as a true fuzzy-equal match.
NEAR_EXACT_MISMATCH_RATIO = 0.05


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

    if grading.accuracy == 1.0 or mismatch_ratio <= NEAR_EXACT_MISMATCH_RATIO:
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
