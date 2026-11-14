"""LLM judge that validates (classifier, noun) idiomatic correctness.

Mirrors the generate -> judge pattern used elsewhere (e.g.
services/exercise_generation/judges/distractor_plausibility.py): a second model
pass scores each candidate noun on a 1-5 Likert scale for how idiomatic the
given measure word is for it. Fail-open (all 5) so a judge outage never blocks
the pipeline — the human review of the JSON is the real gate.
"""

from __future__ import annotations

from services.llm_service import call_llm
from services.measure_curation import judge_nouns as _judge_nouns

from .config import JUDGE_MODEL, PIPELINE

_JUDGE_SYSTEM = (
    "You are a strict Mandarin Chinese examiner. For each noun, judge whether the "
    "given measure word is genuinely the idiomatic classifier for it. Answer ONLY "
    "with valid JSON, no commentary."
)


_JUDGE_PROMPT = (
    "Measure word: 「{item}」{label}\n"
    "Rate how idiomatic 「{item}」 is as the classifier for each noun "
    "on a 1-5 scale (5 = standard/idiomatic, 4 = acceptable, 3 = marginal, "
    "2 = rare/forced, 1 = wrong). If 个 is the only natural classifier for a "
    "noun, rate it 1.\n\n"
    "Nouns:\n{numbered}\n\n"
    'Return JSON: {{"ratings": [int per noun, in order], '
    '"reasons": [short string per noun]}}'
)


def judge_nouns(hanzi: str, nouns: list[str], semantic_label: str = '') -> list[int]:
    """Return a Likert 1-5 rating per noun (5 = idiomatic, 1 = wrong/个-only).

    Order matches ``nouns``. On any failure returns all-5 (fail-open).
    """
    return _judge_nouns(
        call_llm, hanzi, nouns, semantic_label,
        prompt_template=_JUDGE_PROMPT, system_prompt=_JUDGE_SYSTEM,
        model=JUDGE_MODEL, pipeline=PIPELINE,
    )
