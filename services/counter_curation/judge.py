"""LLM judge that validates (counter, noun) idiomatic correctness.

Mirrors services/classifier_curation/judge.py: a second model pass scores each
candidate noun 1-5 for how idiomatic the given counter is for it.

Fail-open (all 5) so a judge outage never blocks the pipeline — the human review
of the JSON is the real gate here, unlike the batch generation judges, which
fail closed because nothing downstream looks at their output before it ships.
"""

from __future__ import annotations

import logging

from services.llm_service import call_llm

from .config import JUDGE_MODEL, PIPELINE
from .schemas import JudgeRatings

logger = logging.getLogger(__name__)

_JUDGE_SYSTEM = (
    "You are a strict Japanese examiner. For each noun, judge whether the given "
    "counter is genuinely idiomatic for it. Answer ONLY with valid JSON, no "
    "commentary."
)


def judge_nouns(counter: str, nouns: list[str], semantic_label: str = '') -> list[int]:
    """Return a Likert 1-5 rating per noun (5 = idiomatic, 1 = wrong).

    Order matches ``nouns``. On any failure returns all-5 (fail-open).
    """
    if not nouns:
        return []

    numbered = '\n'.join(f"{i + 1}. {n}" for i, n in enumerate(nouns))
    label = f" ({semantic_label})" if semantic_label else ""
    prompt = (
        f"Counter: 「{counter}」{label}\n"
        f"Rate how idiomatic 「{counter}」 is as the counter for each noun on a "
        "1-5 scale (5 = standard/idiomatic, 4 = acceptable, 3 = marginal, "
        "2 = rare/forced, 1 = wrong). If つ or 個 is the only natural counter "
        "for a noun, rate it 1.\n\n"
        "A noun that also accepts a DIFFERENT counter is not thereby wrong — "
        f"rate it on whether 「{counter}」 itself is idiomatic, not on whether it "
        "is the only option.\n\n"
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
        logger.warning("judge_nouns failed for %s, fail-open: %s", counter, exc)
        return [5] * len(nouns)

    ratings = out.ratings
    if len(ratings) != len(nouns):
        logger.warning(
            "judge_nouns length mismatch for %s (%d ratings vs %d nouns), fail-open",
            counter, len(ratings), len(nouns),
        )
        return [5] * len(nouns)

    return [max(1, min(5, int(r))) for r in ratings]
