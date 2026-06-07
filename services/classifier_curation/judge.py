"""LLM judge that validates (classifier, noun) idiomatic correctness.

Mirrors the generate -> judge pattern used elsewhere (e.g.
services/exercise_generation/judges/distractor_plausibility.py): a second model
pass scores each candidate noun on a 1-5 Likert scale for how idiomatic the
given measure word is for it. Fail-open (all 5) so a judge outage never blocks
the pipeline — the human review of the JSON is the real gate.
"""

from __future__ import annotations

import logging

from services.llm_service import call_llm

from .config import JUDGE_MODEL, PIPELINE
from .schemas import JudgeRatings

logger = logging.getLogger(__name__)

_JUDGE_SYSTEM = (
    "You are a strict Mandarin Chinese examiner. For each noun, judge whether the "
    "given measure word is genuinely the idiomatic classifier for it. Answer ONLY "
    "with valid JSON, no commentary."
)


def judge_nouns(hanzi: str, nouns: list[str], semantic_label: str = '') -> list[int]:
    """Return a Likert 1-5 rating per noun (5 = idiomatic, 1 = wrong/个-only).

    Order matches ``nouns``. On any failure returns all-5 (fail-open).
    """
    if not nouns:
        return []

    numbered = '\n'.join(f"{i + 1}. {n}" for i, n in enumerate(nouns))
    label = f" ({semantic_label})" if semantic_label else ""
    prompt = (
        f"Measure word: 「{hanzi}」{label}\n"
        f"Rate how idiomatic 「{hanzi}」 is as the classifier for each noun "
        "on a 1-5 scale (5 = standard/idiomatic, 4 = acceptable, 3 = marginal, "
        "2 = rare/forced, 1 = wrong). If 个 is the only natural classifier for a "
        "noun, rate it 1.\n\n"
        f"Nouns:\n{numbered}\n\n"
        'Return JSON: {"ratings": [int per noun, in order], '
        '"reasons": [short string per noun]}'
    )

    try:
        out: JudgeRatings = call_llm(
            prompt,
            model=JUDGE_MODEL,
            temperature=0.0,
            response_format='json_object',
            schema=JudgeRatings,
            provider='openrouter',
            system_prompt=_JUDGE_SYSTEM,
            pipeline=PIPELINE,
            task_name='judge_nouns',
        )
    except Exception as exc:
        logger.warning("judge_nouns failed for %s, fail-open: %s", hanzi, exc)
        return [5] * len(nouns)

    ratings = out.ratings
    if len(ratings) != len(nouns):
        logger.warning(
            "judge_nouns length mismatch for %s (%d ratings vs %d nouns), fail-open",
            hanzi, len(ratings), len(nouns),
        )
        return [5] * len(nouns)

    return [max(1, min(5, int(r))) for r in ratings]
