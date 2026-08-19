"""
Corpus Analysis LLM Client

Thin wrapper around the unified llm_service for corpus analysis calls.
Preserves the existing call signature so callers don't need to change.
"""

import logging

from services.llm_service import call_llm as _call_llm

logger = logging.getLogger(__name__)

# One gemini slug system-wide, per
# migrations/consolidate_gemini_on_3_5_flash_lite.sql (2026-08-16).
DEFAULT_MODEL = 'google/gemini-3.5-flash-lite'


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
