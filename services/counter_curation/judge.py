"""LLM judge that validates (counter, noun) idiomatic correctness.

Mirrors services/classifier_curation/judge.py: a second model pass scores each
candidate noun 1-5 for how idiomatic the given counter is for it.

Fail-open (all 5) so a judge outage never blocks the pipeline — the human review
of the JSON is the real gate here, unlike the batch generation judges, which
fail closed because nothing downstream looks at their output before it ships.
"""

from __future__ import annotations

from services.llm_service import call_llm
from services.measure_curation import judge_nouns as _judge_nouns

from .config import JUDGE_MODEL, PIPELINE

_JUDGE_SYSTEM = (
    "You are a strict Japanese examiner. For each noun, judge whether the given "
    "counter is genuinely idiomatic for it. Answer ONLY with valid JSON, no "
    "commentary."
)


_JUDGE_PROMPT = (
    "Counter: 「{item}」{label}\n"
    "Rate how idiomatic 「{item}」 is as the counter for each noun on a "
    "1-5 scale (5 = standard/idiomatic, 4 = acceptable, 3 = marginal, "
    "2 = rare/forced, 1 = wrong). If つ or 個 is the only natural counter "
    "for a noun, rate it 1.\n\n"
    "A noun that also accepts a DIFFERENT counter is not thereby wrong — "
    "rate it on whether 「{item}」 itself is idiomatic, not on whether it "
    "is the only option.\n\n"
    "Nouns:\n{numbered}\n\n"
    'Return JSON: {{"ratings": [int per noun, in order], '
    '"reasons": [short string per noun]}}'
)


def judge_nouns(counter: str, nouns: list[str], semantic_label: str = '') -> list[int]:
    """Return a Likert 1-5 rating per noun (5 = idiomatic, 1 = wrong).

    Order matches ``nouns``. On any failure returns all-5 (fail-open).
    """
    return _judge_nouns(
        call_llm, counter, nouns, semantic_label,
        prompt_template=_JUDGE_PROMPT, system_prompt=_JUDGE_SYSTEM,
        model=JUDGE_MODEL, pipeline=PIPELINE,
    )
