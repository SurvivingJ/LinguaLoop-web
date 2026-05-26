"""
Answer entailment judge.

Verifies that the passage actually supports the proposed correct answer.
Catches the "answer hallucination" failure mode that Pydantic schema
validation cannot catch — the model invents a correct answer that the
passage does not actually state or imply.

Usage::

    from services.exercise_generation.judges.answer_entailment import (
        judge_answer_entailment,
    )
    outcome = judge_answer_entailment(
        db=db,
        passage="...",
        question_text="What did the author say about X?",
        answer="Y",
        language_id=2,
    )
    # outcome.verdict in ('accept', 'flag', 'reject')
    # outcome.confidence  — raw LLM score 0.0–1.0
    # outcome.reason      — explanation in the target language

Verdict thresholds (from base.py):
    confidence >= 0.8  → accept
    0.6 <= conf < 0.8  → flag   (persist + enqueue review)
    confidence <  0.6  → reject (drop question)
"""

from __future__ import annotations

import logging

from services.llm_service import call_llm
from services.prompt_service import get_template_config

from services.test_generation.schemas import AnswerEntailmentVerdict
from .base import JudgeOutcome, classify, safe_accept, log_judge_verdict

logger = logging.getLogger(__name__)

_TASK_NAME = 'judge_answer_entailment'   # label in llm_calls (judge_ prefix)
_PT_NAME   = 'test_answer_entailment'    # task_name in prompt_templates
_PIPELINE  = 'test_gen'

_cfg_cache: dict[int, dict] = {}         # language_id → cfg dict


def judge_answer_entailment(
    db,
    passage: str,
    question_text: str,
    answer: str,
    language_id: int,
) -> JudgeOutcome:
    """Run the answer-entailment judge and return a single JudgeOutcome.

    On any error (missing template, LLM failure, schema validation error)
    returns ``safe_accept()`` and logs a warning — failure mode is "let it
    through", not "block the whole pipeline".
    """
    try:
        cfg = _load_cfg(db, language_id)
    except Exception as exc:
        logger.warning(
            "answer_entailment: failed to load template for lang=%d, safe-accept: %s",
            language_id, exc,
        )
        return safe_accept(f'template load error: {exc}')

    prompt = cfg['template'].format(passage, question_text, answer)

    try:
        verdict_obj: AnswerEntailmentVerdict = call_llm(
            prompt,
            model=cfg['model'],
            temperature=0.0,
            response_format='json_object',
            schema=AnswerEntailmentVerdict,
            provider='openrouter',
            pipeline=_PIPELINE,
            task_name=_TASK_NAME,
            template_version=cfg['version'],
        )
    except Exception as exc:
        logger.warning(
            "answer_entailment: LLM call failed for lang=%d, safe-accept: %s",
            language_id, exc,
        )
        return safe_accept(f'llm call error: {exc}')

    outcome = JudgeOutcome(
        verdict=classify(verdict_obj.confidence),
        confidence=verdict_obj.confidence,
        reason=verdict_obj.reason,
    )

    # Write a compact verdict row so the smoke-test can count
    # accept/flag/reject distributions by task_name LIKE 'judge_%'.
    log_judge_verdict(
        task_name=_TASK_NAME,
        model=cfg['model'],
        verdict=outcome.verdict,
        confidence=outcome.confidence,
        pipeline=_PIPELINE,
    )

    return outcome


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------

def _load_cfg(db, language_id: int) -> dict:
    if language_id not in _cfg_cache:
        _cfg_cache[language_id] = get_template_config(db, _PT_NAME, language_id)
    return _cfg_cache[language_id]
