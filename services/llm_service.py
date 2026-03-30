"""
Unified LLM Service

Single entry point for all LLM calls in the application.
Supports simultaneous use of multiple providers (OpenRouter, Ollama).
Both use the OpenAI-compatible API, so the same client class works
with different base_url/api_key combinations.

Usage:
    from services.llm_service import call_llm

    # OpenRouter with explicit model
    result = call_llm("Translate this", model="google/gemini-2.0-flash-001")

    # Ollama with language-based model selection
    result = call_llm("Translate this", provider="ollama", language="chinese")

    # Raw text response
    text = call_llm("Write a story", response_format="text", temperature=0.9)
"""

import json
import logging
import os
from typing import Optional

from openai import OpenAI, APIConnectionError, RateLimitError, APITimeoutError
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)

from services.llm_output_cleaner import clean_json_response

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Provider configuration
# ---------------------------------------------------------------------------

OPENROUTER_BASE_URL = os.getenv('OPENROUTER_BASE_URL', 'https://openrouter.ai/api/v1')
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY', '')

OLLAMA_BASE_URL = os.getenv('OLLAMA_BASE_URL', os.getenv('CONV_GEN_OLLAMA_URL', 'http://localhost:11434/v1'))
OLLAMA_DEFAULT_MODEL = os.getenv('OLLAMA_DEFAULT_MODEL', os.getenv('CONV_GEN_OLLAMA_MODEL', 'qwen2.5:7b-instruct-q4_K_M'))

LLM_DEFAULT_PROVIDER = os.getenv('LLM_DEFAULT_PROVIDER', 'openrouter')
LLM_DEFAULT_MODEL = os.getenv('LLM_DEFAULT_MODEL', 'google/gemini-2.0-flash-001')

# Language → model mapping for Ollama (local models may differ per language)
OLLAMA_MODELS: dict[str, str] = {
    'default': OLLAMA_DEFAULT_MODEL,
    # Add language-specific overrides here as needed, e.g.:
    # 'chinese': 'qwen2.5:7b-instruct-q4_K_M',
    # 'japanese': 'qwen2.5:7b-instruct-q4_K_M',
}

# ---------------------------------------------------------------------------
# Client pool  — singleton OpenAI instances keyed by (base_url, api_key)
# ---------------------------------------------------------------------------

_clients: dict[tuple[str, str], OpenAI] = {}


def _resolve_provider(provider: str | None) -> tuple[str, str]:
    """Map a provider name to (base_url, api_key)."""
    provider = provider or LLM_DEFAULT_PROVIDER

    if provider == 'openrouter':
        return (OPENROUTER_BASE_URL, OPENROUTER_API_KEY)
    elif provider == 'ollama':
        return (OLLAMA_BASE_URL, 'ollama')
    else:
        raise ValueError(f"Unknown LLM provider: {provider!r}. Use 'openrouter' or 'ollama'.")


def get_client(
    provider: str | None = None,
    *,
    base_url: str | None = None,
    api_key: str | None = None,
) -> OpenAI:
    """Get or create a singleton OpenAI client.

    Either pass a provider name ('openrouter'/'ollama') or explicit
    base_url + api_key for custom endpoints.
    """
    if base_url and api_key:
        key = (base_url, api_key)
    else:
        key = _resolve_provider(provider)

    if key not in _clients:
        _clients[key] = OpenAI(api_key=key[1], base_url=key[0])
        logger.debug("Created LLM client for %s", key[0])

    return _clients[key]


def _resolve_model(
    model: str | None,
    language: str | None,
    provider: str | None,
) -> str:
    """Resolve which model to use.

    Priority:
    1. Explicit model param
    2. Language-based lookup (OpenRouter → Config.AI_MODELS, Ollama → OLLAMA_MODELS)
    3. Provider default
    """
    if model:
        return model

    provider = provider or LLM_DEFAULT_PROVIDER

    if language and provider == 'openrouter':
        from config import Config
        return Config.get_model_for_language(language)

    if language and provider == 'ollama':
        return OLLAMA_MODELS.get(language.lower(), OLLAMA_MODELS['default'])

    if provider == 'ollama':
        return OLLAMA_DEFAULT_MODEL

    return LLM_DEFAULT_MODEL


# ---------------------------------------------------------------------------
# Retryable errors
# ---------------------------------------------------------------------------

_RETRYABLE = (APIConnectionError, RateLimitError, APITimeoutError, ConnectionError, TimeoutError)


# ---------------------------------------------------------------------------
# Core call_llm
# ---------------------------------------------------------------------------

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(_RETRYABLE),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
def call_llm(
    prompt: str,
    *,
    model: str | None = None,
    language: str | None = None,
    system_prompt: str | None = None,
    temperature: float = 0.7,
    max_tokens: int | None = None,
    response_format: str = 'json',
    provider: str | None = None,
    timeout: int = 60,
) -> dict | list | str:
    """Universal LLM call. Returns parsed JSON dict/list or raw text string.

    Args:
        prompt:          User message content.
        model:           Explicit model name (e.g. 'google/gemini-2.0-flash-001').
                         When None, resolved from language + provider.
        language:        Target language (e.g. 'chinese'). Drives model selection
                         when model is None.
        system_prompt:   Optional system message prepended to messages.
        temperature:     Sampling temperature (default 0.7).
        max_tokens:      Max completion tokens (optional).
        response_format: 'json'  — parse response as JSON via clean_json_response.
                         'text'  — return raw text string.
                         'json_object' — request structured JSON from the API.
        provider:        'openrouter', 'ollama', or None (uses LLM_DEFAULT_PROVIDER).
        timeout:         Request timeout in seconds.

    Returns:
        Parsed JSON (dict | list) when response_format is 'json' or 'json_object',
        or a raw string when response_format is 'text'.

    Raises:
        RuntimeError: On empty/missing LLM response.
        json.JSONDecodeError: On malformed JSON (only for json formats).
        Various OpenAI/network errors after 3 retries.
    """
    client = get_client(provider)
    resolved_model = _resolve_model(model, language, provider)

    messages: list[dict[str, str]] = []
    if system_prompt:
        messages.append({'role': 'system', 'content': system_prompt})
    messages.append({'role': 'user', 'content': prompt})

    payload: dict = {
        'model': resolved_model,
        'messages': messages,
        'temperature': temperature,
        'timeout': timeout,
    }
    if max_tokens:
        payload['max_tokens'] = max_tokens
    if response_format == 'json_object':
        payload['response_format'] = {'type': 'json_object'}

    logger.debug(
        "LLM call: provider=%s model=%s temp=%.2f fmt=%s",
        provider or LLM_DEFAULT_PROVIDER, resolved_model, temperature, response_format,
    )

    response = client.chat.completions.create(**payload)

    if not response.choices:
        raise RuntimeError("LLM returned no choices")

    content = response.choices[0].message.content
    if not content:
        raise RuntimeError("LLM returned empty content")

    if response_format == 'text':
        return content

    return json.loads(clean_json_response(content))
