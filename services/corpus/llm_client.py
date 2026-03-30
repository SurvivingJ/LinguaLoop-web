"""
Corpus Analysis LLM Client

Thin wrapper around the unified llm_service for corpus analysis calls.
Preserves the existing call signature so callers don't need to change.
"""

import logging

from services.llm_service import call_llm as _call_llm

logger = logging.getLogger(__name__)

DEFAULT_MODEL = 'google/gemini-2.0-flash-001'


def call_llm(
    prompt: str,
    *,
    model: str = DEFAULT_MODEL,
    system_prompt: str | None = None,
    temperature: float = 0.0,
    max_tokens: int = 4096,
) -> dict | list:
    """
    Call the LLM and return parsed JSON.

    Delegates to services.llm_service.call_llm with corpus defaults.
    """
    return _call_llm(
        prompt,
        model=model,
        system_prompt=system_prompt,
        temperature=temperature,
        max_tokens=max_tokens,
        response_format='json',
        provider='openrouter',
    )
