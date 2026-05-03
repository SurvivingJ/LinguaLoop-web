"""Thin wrapper around OpenRouter that captures token usage + latency."""

import logging
import time
from typing import Optional

from services.llm_service import get_client

logger = logging.getLogger(__name__)


def call_model_with_usage(
    model: str,
    prompt: str,
    *,
    temperature: float = 0.9,
    timeout: int = 120,
    system_prompt: Optional[str] = None,
    max_tokens: Optional[int] = None,
) -> tuple[str, int, int, float]:
    """Call an OpenRouter model and return (content, prompt_tokens, completion_tokens, latency_seconds).

    Uses the shared OpenAI-compatible client pool from `services.llm_service`.
    `response.usage` is normally discarded by `call_llm()`; this wrapper preserves it.
    """
    client = get_client(provider='openrouter')

    messages: list[dict] = []
    if system_prompt:
        messages.append({'role': 'system', 'content': system_prompt})
    messages.append({'role': 'user', 'content': prompt})

    payload: dict = {
        'model': model,
        'messages': messages,
        'temperature': temperature,
        'timeout': timeout,
    }
    if max_tokens:
        payload['max_tokens'] = max_tokens

    start = time.time()
    response = client.chat.completions.create(**payload)
    latency = time.time() - start

    content = ''
    if response.choices:
        content = response.choices[0].message.content or ''

    usage = getattr(response, 'usage', None)
    prompt_tokens = getattr(usage, 'prompt_tokens', 0) or 0
    completion_tokens = getattr(usage, 'completion_tokens', 0) or 0

    return content, prompt_tokens, completion_tokens, latency
