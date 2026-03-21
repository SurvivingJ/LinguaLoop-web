"""
Conversation Generation LLM Client

OpenRouter (default) and Ollama-compatible LLM client.
Ollama exposes an OpenAI-compatible API, so the same client class
works with a different base_url.
"""

import json
import logging
import os
from openai import OpenAI

from .config import conv_gen_config

logger = logging.getLogger(__name__)

# Module-level singleton clients (one per provider)
_openrouter_client: OpenAI | None = None
_ollama_client: OpenAI | None = None


def _get_client() -> OpenAI:
    """Get the appropriate OpenAI client based on config."""
    global _openrouter_client, _ollama_client

    if conv_gen_config.llm_provider == 'ollama':
        if _ollama_client is None:
            _ollama_client = OpenAI(
                api_key='ollama',
                base_url=conv_gen_config.ollama_base_url,
            )
        return _ollama_client
    else:
        if _openrouter_client is None:
            api_key = conv_gen_config.openrouter_api_key or os.getenv('OPENROUTER_API_KEY', '')
            _openrouter_client = OpenAI(
                api_key=api_key,
                base_url='https://openrouter.ai/api/v1',
            )
        return _openrouter_client


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

    Args:
        prompt:          user message content
        model:           LLM model string (defaults to config)
        system_prompt:   optional system message
        response_format: 'json' or 'text'
        temperature:     sampling temperature (defaults to config)
        max_tokens:      optional max tokens limit

    Returns:
        Parsed JSON dict/list for 'json' format, or raw text string for 'text'.
    """
    client = _get_client()
    model = model or get_model()
    temperature = temperature if temperature is not None else conv_gen_config.temperature

    messages = []
    if system_prompt:
        messages.append({'role': 'system', 'content': system_prompt})
    messages.append({'role': 'user', 'content': prompt})

    payload = {
        'model': model,
        'messages': messages,
        'temperature': temperature,
        'timeout': 60,
    }
    if max_tokens:
        payload['max_tokens'] = max_tokens

    logger.debug("LLM call: model=%s, provider=%s", model, conv_gen_config.llm_provider)

    response = client.chat.completions.create(**payload)

    if not response.choices:
        raise RuntimeError("No response from LLM")

    content = response.choices[0].message.content
    if not content:
        raise RuntimeError("Empty response from LLM")

    if response_format == 'text':
        return content

    # Parse JSON — strip markdown code fences if present
    text = content.strip()
    if text.startswith('```'):
        text = text.replace('```json', '', 1).replace('```', '', 1)
    if text.endswith('```'):
        text = text.rsplit('```', 1)[0]
    text = text.strip()

    return json.loads(text)
