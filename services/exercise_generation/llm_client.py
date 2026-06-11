"""
Exercise Generation LLM Client

Thin wrapper around the unified llm_service for exercise generation calls.
Preserves the existing call signature so callers don't need to change.
"""

import logging

from services.llm_service import call_llm as _call_llm

logger = logging.getLogger(__name__)


def call_llm(
    prompt: str,
    model: str,
    response_format: str = 'json',
    task_name: str = 'exercise_generation',
    pipeline: str = 'exercise_gen',
    template_version: int | None = None,
) -> dict | list | str:
    """
    Call the LLM via OpenRouter. Returns parsed JSON or raw text.

    Delegates to services.llm_service.call_llm with exercise defaults.

    ``model`` is required — every model must be resolved from prompt_templates
    (the single source of truth); there is no hardcoded fallback slug. Passing
    an unresolved/empty model fast-fails rather than silently calling a
    delisted default.

    ``task_name``/``pipeline``/``template_version`` are threaded into llm_calls
    so generation rows are queryable (no longer logged as task_name='unknown').
    """
    if not model:
        raise ValueError(
            "call_llm requires a model resolved from prompt_templates; "
            "no hardcoded default is permitted."
        )
    return _call_llm(
        prompt,
        model=model,
        temperature=0.7,
        response_format=response_format,
        provider='openrouter',
        timeout=30,
        task_name=task_name,
        pipeline=pipeline,
        template_version=template_version,
    )
