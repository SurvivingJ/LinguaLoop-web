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
    model: str = 'google/gemini-flash-1.5',
    response_format: str = 'json',
) -> dict | list | str:
    """
    Call the LLM via OpenRouter. Returns parsed JSON or raw text.

    Delegates to services.llm_service.call_llm with exercise defaults.
    """
    return _call_llm(
        prompt,
        model=model,
        temperature=0.7,
        response_format=response_format,
        provider='openrouter',
        timeout=30,
    )
