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

    # Pydantic-validated structured output (with one-shot repair retry)
    from pydantic import BaseModel
    class MCQuestion(BaseModel):
        question: str
        options: list[str]
        correct_answer_index: int
    q = call_llm(prompt, schema=MCQuestion, response_format='json_object',
                 pipeline='test_gen', task_name='question_generator')
"""

import hashlib
import json
import logging
import os
import time
from typing import Optional

from openai import OpenAI, APIConnectionError, RateLimitError, APITimeoutError
from pydantic import BaseModel, ValidationError
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
# Observability — every LLM round-trip writes one row to llm_calls.
# Guarded so a DB outage never breaks a generation pipeline.
# ---------------------------------------------------------------------------

def _log_llm_call(
    *,
    pipeline: str,
    task_name: str,
    template_version: int | None,
    model: str,
    temperature: float | None,
    seed: int | None,
    prompt_hash: bytes | None,
    raw_response: str | None,
    parsed_ok: bool | None,
    schema_ok: bool | None,
    judge_verdict: str | None,
    judge_confidence: float | None,
    latency_ms: int | None,
    artifact_id: str | None,
) -> None:
    """Insert one row into llm_calls. Best-effort; never raises."""
    try:
        from services.supabase_factory import get_supabase_admin, get_supabase
        client = get_supabase_admin() or get_supabase()
        if client is None:
            return
        row = {
            'pipeline': pipeline,
            'task_name': task_name,
            'template_version': template_version,
            'model': model,
            'temperature': temperature,
            'seed': seed,
            'prompt_hash': prompt_hash.hex() if prompt_hash else None,
            'raw_response': raw_response,
            'parsed_ok': parsed_ok,
            'schema_ok': schema_ok,
            'judge_verdict': judge_verdict,
            'judge_confidence': judge_confidence,
            'latency_ms': latency_ms,
            'artifact_id': artifact_id,
        }
        client.table('llm_calls').insert(row).execute()
    except Exception as exc:
        # Observability must never break the calling pipeline.
        logger.debug("llm_calls logging failed: %s", exc)


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
    temperature: float = 0.2,
    max_tokens: int | None = None,
    response_format: str = 'json',
    provider: str | None = None,
    timeout: int = 60,
    schema: type[BaseModel] | None = None,
    seed: int | None = None,
    pipeline: str | None = None,
    task_name: str | None = None,
    template_version: int | None = None,
    artifact_id: str | None = None,
) -> dict | list | str | BaseModel:
    """Universal LLM call. Returns parsed JSON dict/list, raw text, or a
    validated Pydantic model instance.

    Args:
        prompt:          User message content.
        model:           Explicit model name (e.g. 'google/gemini-2.0-flash-001').
                         When None, resolved from language + provider.
        language:        Target language (e.g. 'chinese'). Drives model selection
                         when model is None.
        system_prompt:   Optional system message prepended to messages.
        temperature:     Sampling temperature (default 0.2 — tightened from the
                         legacy 0.7 default for reproducibility; callers that
                         need higher creativity pass it explicitly).
        max_tokens:      Max completion tokens (optional).
        response_format: 'json'  — parse response as JSON via clean_json_response.
                         'text'  — return raw text string.
                         'json_object' — request structured JSON from the API.
        provider:        'openrouter', 'ollama', or None (uses LLM_DEFAULT_PROVIDER).
        timeout:         Request timeout in seconds.
        schema:          Optional Pydantic model. When provided and response_format
                         is not 'text', the parsed JSON is validated against the
                         schema. On ValidationError a one-shot repair turn runs at
                         temperature 0.0; if that also fails, the ValidationError
                         propagates.
        seed:            Optional deterministic-sampling seed. Forwarded as the
                         OpenAI `seed` parameter (best-effort; provider support
                         varies).
        pipeline:        Pipeline tag for the llm_calls log row (e.g. 'test_gen',
                         'vocab_ladder'). Defaults to 'unknown'.
        task_name:       Task tag for the llm_calls log row. Should match the
                         prompt_templates.task_name when applicable. Defaults to
                         'unknown'.
        template_version: prompt_templates.version when applicable.
        artifact_id:     Optional UUID of the artifact produced by this call
                         (exercise_id, test_id, etc.) for trace-back.

    Returns:
        - schema given + validation passes → schema instance (BaseModel).
        - response_format == 'text' → raw string.
        - otherwise → parsed dict | list.

    Raises:
        RuntimeError:        Empty / missing LLM response.
        json.JSONDecodeError: Malformed JSON.
        ValidationError:     Schema mismatch persisting after the repair retry.
        Various OpenAI/network errors after 3 retries.
    """
    client = get_client(provider)
    resolved_model = _resolve_model(model, language, provider)

    messages: list[dict[str, str]] = []
    if system_prompt:
        messages.append({'role': 'system', 'content': system_prompt})
    messages.append({'role': 'user', 'content': prompt})

    log_pipeline = pipeline or 'unknown'
    log_task = task_name or 'unknown'
    prompt_hash = hashlib.sha256(
        ((system_prompt or '') + '\n' + prompt).encode('utf-8')
    ).digest()

    logger.debug(
        "LLM call: provider=%s model=%s temp=%.2f fmt=%s pipeline=%s task=%s",
        provider or LLM_DEFAULT_PROVIDER, resolved_model, temperature,
        response_format, log_pipeline, log_task,
    )

    parsed, raw_content, parsed_ok, latency_ms = _make_one_call(
        client=client,
        model=resolved_model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        response_format=response_format,
        seed=seed,
        timeout=timeout,
    )

    # Text path — short-circuit before any schema work.
    if response_format == 'text':
        _log_llm_call(
            pipeline=log_pipeline, task_name=log_task,
            template_version=template_version, model=resolved_model,
            temperature=temperature, seed=seed, prompt_hash=prompt_hash,
            raw_response=raw_content, parsed_ok=parsed_ok, schema_ok=None,
            judge_verdict=None, judge_confidence=None,
            latency_ms=latency_ms, artifact_id=artifact_id,
        )
        return parsed  # raw text

    # Schema path — validate, repair once on failure.
    if schema is not None:
        try:
            validated = schema.model_validate(parsed)
            _log_llm_call(
                pipeline=log_pipeline, task_name=log_task,
                template_version=template_version, model=resolved_model,
                temperature=temperature, seed=seed, prompt_hash=prompt_hash,
                raw_response=raw_content, parsed_ok=parsed_ok, schema_ok=True,
                judge_verdict=None, judge_confidence=None,
                latency_ms=latency_ms, artifact_id=artifact_id,
            )
            return validated
        except ValidationError as exc:
            # Log the failed initial attempt before retrying.
            _log_llm_call(
                pipeline=log_pipeline, task_name=log_task,
                template_version=template_version, model=resolved_model,
                temperature=temperature, seed=seed, prompt_hash=prompt_hash,
                raw_response=raw_content, parsed_ok=parsed_ok, schema_ok=False,
                judge_verdict=None, judge_confidence=None,
                latency_ms=latency_ms, artifact_id=artifact_id,
            )
            return _repair_and_retry(
                client=client,
                model=resolved_model,
                original_messages=messages,
                invalid_parsed=parsed,
                validation_error=exc,
                schema=schema,
                response_format=response_format,
                max_tokens=max_tokens,
                timeout=timeout,
                seed=seed,
                log_pipeline=log_pipeline,
                log_task=log_task,
                template_version=template_version,
                artifact_id=artifact_id,
                prompt_hash=prompt_hash,
            )

    # JSON path, no schema — log and return.
    _log_llm_call(
        pipeline=log_pipeline, task_name=log_task,
        template_version=template_version, model=resolved_model,
        temperature=temperature, seed=seed, prompt_hash=prompt_hash,
        raw_response=raw_content, parsed_ok=parsed_ok, schema_ok=None,
        judge_verdict=None, judge_confidence=None,
        latency_ms=latency_ms, artifact_id=artifact_id,
    )
    return parsed


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------

def _make_one_call(
    *,
    client: OpenAI,
    model: str,
    messages: list[dict[str, str]],
    temperature: float,
    max_tokens: int | None,
    response_format: str,
    seed: int | None,
    timeout: int,
) -> tuple[dict | list | str, str, bool, int]:
    """Execute a single API round-trip.

    Returns (parsed_or_text, raw_content, parsed_ok, latency_ms).
    Raises RuntimeError on empty response or json.JSONDecodeError on malformed
    JSON; both are logged as parsed_ok=False by the caller via the finally-style
    log emission path.
    """
    payload: dict = {
        'model': model,
        'messages': messages,
        'temperature': temperature,
        'timeout': timeout,
    }
    if max_tokens:
        payload['max_tokens'] = max_tokens
    if seed is not None:
        payload['seed'] = seed
    if response_format == 'json_object':
        payload['response_format'] = {'type': 'json_object'}

    start = time.perf_counter()
    response = client.chat.completions.create(**payload)
    latency_ms = int((time.perf_counter() - start) * 1000)

    if not response.choices:
        raise RuntimeError("LLM returned no choices")

    content = response.choices[0].message.content
    if not content:
        raise RuntimeError("LLM returned empty content")

    if response_format == 'text':
        return content, content, True, latency_ms

    parsed = json.loads(clean_json_response(content))
    return parsed, content, True, latency_ms


def _repair_and_retry(
    *,
    client: OpenAI,
    model: str,
    original_messages: list[dict[str, str]],
    invalid_parsed: dict | list,
    validation_error: ValidationError,
    schema: type[BaseModel],
    response_format: str,
    max_tokens: int | None,
    timeout: int,
    seed: int | None,
    log_pipeline: str,
    log_task: str,
    template_version: int | None,
    artifact_id: str | None,
    prompt_hash: bytes,
) -> BaseModel:
    """Single deterministic repair turn at temperature 0.0.

    Re-raises ValidationError if the repair output also fails validation.
    Logs its own llm_calls row.
    """
    repair_prompt = (
        "Your previous response failed schema validation. Return ONLY corrected "
        "JSON that matches the required schema.\n\n"
        "Validation errors:\n"
        f"{validation_error}\n\n"
        "Your previous (invalid) response:\n"
        f"{json.dumps(invalid_parsed, ensure_ascii=False)}\n"
    )
    repair_messages = original_messages + [
        {'role': 'assistant', 'content': json.dumps(invalid_parsed, ensure_ascii=False)},
        {'role': 'user', 'content': repair_prompt},
    ]

    parsed, raw_content, parsed_ok, latency_ms = _make_one_call(
        client=client,
        model=model,
        messages=repair_messages,
        temperature=0.0,
        max_tokens=max_tokens,
        response_format=response_format,
        seed=seed,
        timeout=timeout,
    )

    try:
        validated = schema.model_validate(parsed)
        schema_ok = True
        result: BaseModel = validated
        err: ValidationError | None = None
    except ValidationError as e:
        schema_ok = False
        result = None  # type: ignore[assignment]
        err = e

    _log_llm_call(
        pipeline=log_pipeline, task_name=f"{log_task}__repair",
        template_version=template_version, model=model,
        temperature=0.0, seed=seed, prompt_hash=prompt_hash,
        raw_response=raw_content, parsed_ok=parsed_ok, schema_ok=schema_ok,
        judge_verdict=None, judge_confidence=None,
        latency_ms=latency_ms, artifact_id=artifact_id,
    )

    if err is not None:
        raise err
    return result
