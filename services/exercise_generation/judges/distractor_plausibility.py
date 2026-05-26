"""
Distractor plausibility judge.

Verifies that the three distractors are plausible-but-clearly-wrong.
Catches two failure modes Pydantic cannot see:
- A distractor is also a valid correct answer ("oversharp distractors").
- A distractor is so absurd no learner would pick it ("weak distractors").

Usage::

    from services.exercise_generation.judges.distractor_plausibility import (
        judge_distractor_plausibility,
    )
    outcomes = judge_distractor_plausibility(
        db=db,
        passage="...",
        question_text="...",
        answer="correct answer text",
        distractors=["wrong1", "wrong2", "wrong3"],
        language_id=2,
    )
    # outcomes[i].verdict    in ('accept', 'flag', 'reject')
    # outcomes[i].confidence — per-distractor LLM score 0.0–1.0
    # outcomes[i].reason     — explanation in the target language

The judge prompt asks the LLM to rate ALL distractors in a single call and
return one confidence per distractor.  The overall verdict for the question
(used by question_generator.py) is the worst verdict across all distractors.

Verdict thresholds (from base.py):
    confidence >= 0.8  → accept
    0.6 <= conf < 0.8  → flag   (persist + enqueue review)
    confidence <  0.6  → reject (drop question)
"""

from __future__ import annotations

import logging

from services.llm_service import call_llm
from services.prompt_service import get_template_config

from services.test_generation.schemas import DistractorPlausibilityVerdict
from .base import JudgeOutcome, classify, safe_accept, log_judge_verdict

logger = logging.getLogger(__name__)

_TASK_NAME = 'judge_distractor_plausibility'   # label in llm_calls
_PT_NAME   = 'test_distractor_plausibility'    # task_name in prompt_templates
_PIPELINE  = 'test_gen'

_cfg_cache: dict[int, dict] = {}               # language_id → cfg dict

_VERDICT_ORDER = {'reject': 0, 'flag': 1, 'accept': 2}  # lower = worse


def judge_distractor_plausibility(
    db,
    passage: str,
    question_text: str,
    answer: str,
    distractors: list[str],
    language_id: int,
) -> list[JudgeOutcome]:
    """Run the distractor-plausibility judge, one JudgeOutcome per distractor.

    Returns a list of ``len(distractors)`` JudgeOutcome objects in the same
    order as ``distractors``.

    On any error (missing template, LLM failure, schema error, length
    mismatch) returns ``[safe_accept() for _ in distractors]`` and logs a
    warning — failure mode is "let them all through", not "block the pipeline".
    """
    if not distractors:
        return []

    n = len(distractors)

    try:
        cfg = _load_cfg(db, language_id)
    except Exception as exc:
        logger.warning(
            "distractor_plausibility: failed to load template for lang=%d, safe-accept: %s",
            language_id, exc,
        )
        return [safe_accept(f'template load error: {exc}') for _ in distractors]

    distractors_numbered = '\n'.join(
        f'{i + 1}. {d}' for i, d in enumerate(distractors)
    )
    prompt = cfg['template'].format(
        passage, question_text, answer, distractors_numbered,
    )

    try:
        verdict_obj: DistractorPlausibilityVerdict = call_llm(
            prompt,
            model=cfg['model'],
            temperature=0.0,
            response_format='json_object',
            schema=DistractorPlausibilityVerdict,
            provider='openrouter',
            pipeline=_PIPELINE,
            task_name=_TASK_NAME,
            template_version=cfg['version'],
        )
    except Exception as exc:
        logger.warning(
            "distractor_plausibility: LLM call failed for lang=%d, safe-accept: %s",
            language_id, exc,
        )
        return [safe_accept(f'llm call error: {exc}') for _ in distractors]

    # Guard against length mismatch (schema validator should catch this,
    # but be defensive in case of a repair-retry edge case).
    if len(verdict_obj.per_distractor) != n:
        logger.warning(
            "distractor_plausibility: length mismatch — got %d confidences for "
            "%d distractors, safe-accept all",
            len(verdict_obj.per_distractor), n,
        )
        return [safe_accept('length mismatch in judge response') for _ in distractors]

    outcomes = [
        JudgeOutcome(
            verdict=classify(conf),
            confidence=conf,
            reason=verdict_obj.reasons[i] if i < len(verdict_obj.reasons) else '',
        )
        for i, conf in enumerate(verdict_obj.per_distractor)
    ]

    # Log the worst-case verdict for the batch (binding constraint for the
    # question as a whole) so the smoke-test query sees one row per call.
    worst = min(outcomes, key=lambda o: _VERDICT_ORDER.get(o.verdict, 2))
    log_judge_verdict(
        task_name=_TASK_NAME,
        model=cfg['model'],
        verdict=worst.verdict,
        confidence=worst.confidence,
        pipeline=_PIPELINE,
    )

    return outcomes


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------

def _load_cfg(db, language_id: int) -> dict:
    if language_id not in _cfg_cache:
        _cfg_cache[language_id] = get_template_config(db, _PT_NAME, language_id)
    return _cfg_cache[language_id]
