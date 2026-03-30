"""
Conversation Generation LLM Client

Thin wrapper around the unified llm_service for conversation generation calls.
Preserves the existing call signature so callers don't need to change.
Provider selection (OpenRouter vs Ollama) is driven by ConvGenConfig.
"""

import logging

from services.llm_service import call_llm as _call_llm
from .config import conv_gen_config

logger = logging.getLogger(__name__)


def get_model(task: str = 'conversation') -> str:
    """Get the model name for a given task, respecting provider config."""
    if conv_gen_config.llm_provider == 'ollama':
        return conv_gen_config.ollama_model

    if task == 'analysis':
        return conv_gen_config.analysis_model
    return conv_gen_config.conversation_model


def call_llm(
    prompt: str,
    model: str | None = None,
    system_prompt: str | None = None,
    response_format: str = 'json',
    temperature: float | None = None,
    max_tokens: int | None = None,
) -> dict | list | str:
    """
    Call the LLM via OpenRouter or Ollama. Returns parsed JSON or raw text.

    Delegates to services.llm_service.call_llm with conversation defaults.
    """
    return _call_llm(
        prompt,
        model=model or get_model(),
        system_prompt=system_prompt,
        temperature=temperature if temperature is not None else conv_gen_config.temperature,
        max_tokens=max_tokens,
        response_format=response_format,
        provider=conv_gen_config.llm_provider,
    )
