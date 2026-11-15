"""Anthropic Messages API transport for ``llm_service.call_llm``.

Selected with provider ``anthropic`` (``--provider anthropic`` on the scripts
that take ``scripts/provider_arg.py``). Calls go through the official
``anthropic`` SDK with the key in ``CLAUDE_API`` (or ``ANTHROPIC_API_KEY``),
and come back in the OpenAI ``chat.completions`` shape ``_make_one_call``
reads -- the same facade ``claude_cli_client.ClaudeCliClient`` provides -- so
logging, repair turns and retries are unchanged.

Model: a caller that names a Claude model (``claude-…``) gets it. Any other
slug (the ``deepseek/…`` / ``qwen/…`` defaults the pipelines pass) is replaced
by ``ANTHROPIC_API_MODEL`` (default ``claude-sonnet-5-5``), and the model
actually served is what ``llm_calls.model`` records.

Effort: ``ANTHROPIC_API_EFFORT`` (default ``low``). These pipelines make short
structured-output calls; thinking happens at every level on current models and
is billed as output, so a higher effort mainly buys cost.

Dropped request fields: ``temperature`` and ``seed`` (non-default sampling is
rejected on current Claude models), ``response_format`` (the prompts already
ask for JSON and ``_make_one_call`` parses it), and ``extra_body`` (OpenRouter
routing/reasoning settings).

Cost: the Messages API reports tokens, not dollars, so ``usage.cost`` is the
token counts priced at the list rates below. Keep ``_PRICES`` in step with
Anthropic's pricing page; a model missing from it reports no cost (None)
rather than a guess.
"""

from __future__ import annotations

import os
from typing import Any

# Sentinel base_url. Must not contain "openrouter": llm_service._is_openrouter
# keys OpenRouter-only request fields off it.
ANTHROPIC_API_BASE_URL = 'anthropic-api://messages'
ANTHROPIC_API_MODEL = os.getenv('ANTHROPIC_API_MODEL', 'claude-sonnet-5-5')
ANTHROPIC_API_EFFORT = os.getenv('ANTHROPIC_API_EFFORT', 'low')

# USD per million tokens: input, output, cache read, cache write (5 min).
_PRICES: dict[str, tuple[float, float, float, float]] = {
    'claude-haiku-5-5': (0.10, 0.50, 0.01, 0.125),
    'claude-sonnet-5-5': (2.00, 10.00, 0.10, 2.50),
    'claude-opus-5-5': (4.00, 20.00, 0.20, 5.00),
}


def api_key() -> str:
    return os.environ.get('CLAUDE_API') or os.environ.get('ANTHROPIC_API_KEY') or ''


def served_model(requested: str | None) -> str:
    """The Claude model a request for ``requested`` is served by."""
    if requested and requested.startswith('claude-'):
        return requested
    return ANTHROPIC_API_MODEL


def _price(model: str, usage) -> float | None:
    rates = _PRICES.get(model)
    if rates is None:
        return None
    pin, pout, pread, pwrite = rates
    read = getattr(usage, 'cache_read_input_tokens', None) or 0
    write = getattr(usage, 'cache_creation_input_tokens', None) or 0
    return (usage.input_tokens * pin + usage.output_tokens * pout
            + read * pread + write * pwrite) / 1e6


class _Message:
    def __init__(self, content: str):
        self.content = content
        self.role = 'assistant'


class _Choice:
    def __init__(self, content: str, finish_reason: str):
        self.message = _Message(content)
        self.finish_reason = finish_reason
        self.index = 0


class _PromptTokensDetails:
    def __init__(self, cached_tokens: int):
        self.cached_tokens = cached_tokens


class _Usage:
    def __init__(self, usage, cost: float | None):
        self.prompt_tokens = usage.input_tokens
        self.completion_tokens = usage.output_tokens
        self.total_tokens = self.prompt_tokens + self.completion_tokens
        self.prompt_tokens_details = _PromptTokensDetails(
            getattr(usage, 'cache_read_input_tokens', None) or 0)
        self.completion_tokens_details = None
        self.cost = cost
        self.model_extra: dict[str, Any] = {}


class AnthropicApiResponse:
    """Minimal stand-in for openai.types.chat.ChatCompletion."""

    def __init__(self, message):
        text = ''.join(b.text for b in message.content if b.type == 'text')
        finish = {'max_tokens': 'length', 'refusal': 'content_filter'}.get(
            message.stop_reason, 'stop')
        self.choices = [_Choice(text, finish)]
        self.usage = _Usage(message.usage, _price(message.model, message.usage))
        self.model = message.model
        self.id = message.id


class _Completions:
    def __init__(self, client: 'AnthropicApiClient'):
        self._client = client

    def create(self, **payload) -> AnthropicApiResponse:
        return self._client._invoke(payload)


class _Chat:
    def __init__(self, client: 'AnthropicApiClient'):
        self.completions = _Completions(client)


class AnthropicApiClient:
    """OpenAI-compatible facade over the Anthropic Messages API.

    Implements only what ``llm_service._make_one_call`` touches:
    ``base_url`` and ``chat.completions.create``.
    """

    def __init__(self, key: str | None = None):
        import anthropic
        self.base_url = ANTHROPIC_API_BASE_URL
        self._sdk = anthropic.Anthropic(
            api_key=key or api_key(),
            # Explicit: ANTHROPIC_BASE_URL can point at a local proxy in some
            # environments; this transport always means the public API.
            base_url='https://api.anthropic.com',
            # The SDK retries 408/409/429/5xx and connection errors itself
            # (call_llm's tenacity list only knows the OpenAI SDK's types).
            max_retries=4,
        )
        self.chat = _Chat(self)

    @staticmethod
    def _split(messages: list[dict]) -> tuple[str | None, list[dict]]:
        """OpenAI messages -> (system prompt, Anthropic messages)."""
        system = [m.get('content') or '' for m in messages if m.get('role') == 'system']
        convo = [{'role': m['role'], 'content': m.get('content') or ''}
                 for m in messages if m.get('role') in ('user', 'assistant')]
        return ('\n\n'.join(system) or None), convo

    def _invoke(self, payload: dict) -> AnthropicApiResponse:
        system, messages = self._split(payload.get('messages') or [])
        kwargs: dict[str, Any] = {
            'model': served_model(payload.get('model')),
            'max_tokens': payload.get('max_tokens') or 16000,
            'messages': messages,
            'output_config': {'effort': ANTHROPIC_API_EFFORT},
        }
        if system:
            kwargs['system'] = system
        timeout = payload.get('timeout')
        sdk = self._sdk.with_options(timeout=timeout) if timeout else self._sdk
        return AnthropicApiResponse(sdk.messages.create(**kwargs))
