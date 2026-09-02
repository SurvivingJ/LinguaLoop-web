"""
Exercise Generation LLM Client

Thin wrapper around the unified llm_service for exercise generation calls.
Preserves the existing call signature so callers don't need to change.
"""

import logging
import os

from services.llm_service import call_llm as _call_llm

logger = logging.getLogger(__name__)


def call_llm(
    prompt: str,
    model: str,
    response_format: str = 'json',
    task_name: str = 'exercise_generation',
    pipeline: str = 'exercise_gen',
    template_version: int | None = None,
    provider: str | None = None,
) -> dict | list | str:
    """
    Call the LLM. Returns parsed JSON or raw text.

    Delegates to services.llm_service.call_llm with exercise defaults.

    ``model`` is required — every model must be resolved from prompt_templates
    (the single source of truth); there is no hardcoded fallback slug. Passing
    an unresolved/empty model fast-fails rather than silently calling a
    delisted default.

    ``task_name``/``pipeline``/``template_version`` are threaded into llm_calls
    so generation rows are queryable (no longer logged as task_name='unknown').

    ``provider`` defaults to None so ``LLM_DEFAULT_PROVIDER`` applies. This used
    to be hardcoded to 'openrouter', which made exercise generation the one
    pipeline that could not be routed to the headless Claude Code transport
    (services/claude_cli_client.py) — every other caller already leaves the
    provider unset. Behaviour is unchanged while LLM_DEFAULT_PROVIDER stays
    'openrouter'.

    The 30s timeout is raised for the CLI transport: a headless call spawns a
    process and has no streaming keep-alive, so it routinely exceeds a budget
    tuned for a hosted HTTP endpoint.
    """
    if not model:
        raise ValueError(
            "call_llm requires a model resolved from prompt_templates; "
            "no hardcoded default is permitted."
        )
    is_cli = (provider or os.getenv('LLM_DEFAULT_PROVIDER', 'openrouter')) == 'claude_cli'
    return _call_llm(
        prompt,
        model=model,
        temperature=0.7,
        response_format=response_format,
        provider=provider,
        timeout=600 if is_cli else 30,
        task_name=task_name,
        pipeline=pipeline,
        template_version=template_version,
    )
