"""
Unified LLM Service

Single entry point for all LLM calls in the application.
Supports simultaneous use of multiple providers (OpenRouter, Ollama).
Both use the OpenAI-compatible API, so the same client class works
with different base_url/api_key combinations.

Usage:
    from services.llm_service import call_llm

    # OpenRouter with explicit model
    result = call_llm("Translate this", model="google/gemini-3.5-flash-lite")

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

import contextvars
import csv
import hashlib
import json
import logging
import os
import re
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Iterator, Optional

import httpx
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

# Headless Claude Code transport (subscription-billed, not per-token).
# Sentinel rather than a real URL — see services/claude_cli_client.py. Declared
# here rather than imported so provider resolution stays import-cheap for the
# majority of callers that never use it.
CLAUDE_CLI_BASE_URL = 'claude-cli://local'
# Last-resort fallback: used by _resolve_model only when the caller supplies
# neither an explicit model nor a language. google/gemini-3.5-flash-lite since
# 2026-08-16 -- one gemini slug system-wide, per
# migrations/consolidate_gemini_on_3_5_flash_lite.sql. This is a code default,
# not a prompt_templates row, so the nightly slug-health probe cannot see it;
# re-check it by hand when a slug rotates.
LLM_DEFAULT_MODEL = os.getenv('LLM_DEFAULT_MODEL', 'google/gemini-3.5-flash-lite')

# Sense-dictionary generation runs on a cheap hosted model, separate from the
# test/prose model. DeepSeek V4 Flash was validated head-to-head (10/10 valid
# JSON, zero language bleed); Qwen3.6 Flash is the fallback used only when the
# primary returns invalid JSON. Both are OpenRouter slugs and stay swappable
# (e.g. a local Ollama model) via env without code changes.
SENSE_MODEL_DEFAULT = os.getenv('SENSE_MODEL', 'deepseek/deepseek-v4-flash')
SENSE_MODEL_FALLBACK = os.getenv('SENSE_MODEL_FALLBACK', 'qwen/qwen3.6-flash')

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

# Values are OpenAI clients, or a ClaudeCliClient for the headless transport.
_clients: dict[tuple[str, str], object] = {}


def _resolve_provider(provider: str | None) -> tuple[str, str]:
    """Map a provider name to (base_url, api_key)."""
    provider = provider or LLM_DEFAULT_PROVIDER

    if provider == 'openrouter':
        return (OPENROUTER_BASE_URL, OPENROUTER_API_KEY)
    elif provider == 'ollama':
        return (OLLAMA_BASE_URL, 'ollama')
    elif provider == 'claude_cli':
        # Not an HTTP endpoint — a sentinel that routes get_client to the
        # headless `claude -p` subprocess transport. Keyed like any other
        # provider so the client pool, and every caller that resolves a client
        # by base_url, works unchanged.
        return (CLAUDE_CLI_BASE_URL, 'subscription')
    else:
        raise ValueError(
            f"Unknown LLM provider: {provider!r}. "
            "Use 'openrouter', 'ollama' or 'claude_cli'."
        )


def set_default_provider(provider: str) -> None:
    """Switch the process-wide default LLM provider at runtime.

    Backfill CLIs use this to route a whole run to the headless Claude Code
    transport with one flag. Both the module global and the environment variable
    are set: ``_resolve_provider`` reads the global, while
    ``exercise_generation.llm_client`` reads the env var to size its timeout.

    Raises:
        ValueError: on an unknown provider — fails before the run starts rather
            than on the first LLM call, hours in.
    """
    global LLM_DEFAULT_PROVIDER
    _resolve_provider(provider)  # validate; raises on an unknown name
    LLM_DEFAULT_PROVIDER = provider
    os.environ['LLM_DEFAULT_PROVIDER'] = provider
    logger.info("Default LLM provider set to %r for this process", provider)


def get_client(
    provider: str | None = None,
    *,
    base_url: str | None = None,
    api_key: str | None = None,
):
    """Get or create a singleton client.

    Either pass a provider name ('openrouter'/'ollama'/'claude_cli') or explicit
    base_url + api_key for custom endpoints.

    Returns an ``OpenAI`` instance for HTTP providers, or a ``ClaudeCliClient``
    for the headless Claude Code transport. Both expose the same
    ``chat.completions.create`` surface, so callers do not branch.
    """
    if base_url and api_key:
        key = (base_url, api_key)
    else:
        key = _resolve_provider(provider)

    if key not in _clients:
        if key[0] == CLAUDE_CLI_BASE_URL:
            # Imported lazily: the module shells out and probes the filesystem
            # for the CLI, which should not happen at import time for the many
            # callers that never touch this provider.
            from services.claude_cli_client import ClaudeCliClient
            _clients[key] = ClaudeCliClient()
            logger.info("Created Claude Code headless client (subscription auth)")
        else:
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
    1. claude_cli → always the Claude model the CLI actually serves
    2. Explicit model param
    3. Language-based lookup (OpenRouter → Config.AI_MODELS, Ollama → OLLAMA_MODELS)
    4. Provider default
    """
    if (provider or LLM_DEFAULT_PROVIDER) == 'claude_cli':
        # The CLI serves Claude models only, so the OpenRouter slug named by
        # prompt_templates (qwen/…, google/…, deepseek/…) cannot be honoured and
        # becomes advisory. Returning the real model — rather than echoing the
        # requested slug — keeps llm_calls.model honest: otherwise every eval,
        # judge-flag-rate run and A/B in scripts/measure_*.py would pool Claude
        # output under a qwen or gemini label and compare two models as one.
        from services.claude_cli_client import CLAUDE_CLI_MODEL
        if model:
            logger.debug(
                "claude_cli provider: ignoring requested model %r, serving %r",
                model, CLAUDE_CLI_MODEL,
            )
        return f'claude-cli:{CLAUDE_CLI_MODEL}'

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
# Observability — every LLM round-trip writes one row to llm_calls (DB) and
# one row to a local daily CSV. Both are guarded so an outage in either sink
# never breaks a generation pipeline.
# ---------------------------------------------------------------------------

# Generation-batch context (Phase 0 cost instrumentation). ``sense_id`` and
# ``generation_batch_id`` are set ONCE at the top of a unit of work — e.g.
# VocabAssetPipeline._generate_for_sense_impl — and every call_llm() nested
# underneath (P1, P2, P3, split levels, typed generators, judges) picks them
# up automatically via these contextvars rather than every call site having to
# thread two extra parameters through several layers of generator classes.
#
# Contextvars propagate down a normal call stack for free, but NOT into a
# ``ThreadPoolExecutor`` worker by default — the pipeline fans P2/P3/split/
# typed generation out across threads (see judges.base.BatchModeThreadPoolExecutor).
# That executor's ``submit`` is extended (see judges/base.py) to capture
# ``contextvars.copy_context()`` at submit time and run the worker inside it,
# so a sense_id set on the calling thread is still visible inside the pool
# thread that actually places the OpenRouter call.
_ctx_sense_id: contextvars.ContextVar[int | None] = contextvars.ContextVar(
    'llm_service_sense_id', default=None,
)
_ctx_generation_batch_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    'llm_service_generation_batch_id', default=None,
)


@contextmanager
def generation_context(
    *, sense_id: int | None = None, generation_batch_id: str | None = None,
) -> Iterator[None]:
    """Bind ``sense_id``/``generation_batch_id`` for every llm_calls row logged
    within this block (and any thread that inherits this context — see the
    module docstring above ``_ctx_sense_id``).

    Either argument may be omitted; omitting both makes this a no-op scope.
    Values are restored on exit, so nested/re-entrant use is safe.
    """
    tokens = []
    if sense_id is not None:
        tokens.append((_ctx_sense_id, _ctx_sense_id.set(sense_id)))
    if generation_batch_id is not None:
        tokens.append(
            (_ctx_generation_batch_id, _ctx_generation_batch_id.set(generation_batch_id))
        )
    try:
        yield
    finally:
        for var, tok in tokens:
            var.reset(tok)


# Allowed values for llm_calls.call_role — mirrors the CHECK constraint in
# migrations/llm_calls_cost_instrumentation.sql. Keep the two in sync.
CALL_ROLE_PRIMARY = 'primary'
CALL_ROLE_JSON_REPAIR = 'json_repair'
CALL_ROLE_RETRY = 'retry'
CALL_ROLE_SALVAGE = 'salvage'
CALL_ROLE_REPAIR = 'repair'
_VALID_CALL_ROLES = frozenset({
    CALL_ROLE_PRIMARY, CALL_ROLE_JSON_REPAIR, CALL_ROLE_RETRY,
    CALL_ROLE_SALVAGE, CALL_ROLE_REPAIR,
})

# TASK-813: models that REQUIRE reasoning mode to function at all — sending
# `reasoning: {exclude: True}` to one of these would break it, not just leave
# it unaffected (the "qwen3.8-max is a reasoning model" finding: it needs
# ~16k max_tokens and 100-330s/call, and must never have reasoning disabled).
# A denylist, not an allowlist: every other model is assumed to tolerate an
# unrecognised/no-op `reasoning` key the way OpenRouter tolerates unknown
# `extra_body` fields for most providers. Pattern-based (not just the one
# known slug) so a future qwen — or any other family's — reasoning-only
# variant doesn't silently slip through un-denied.
_REASONING_ONLY_MODEL_PATTERNS: tuple[re.Pattern, ...] = (
    re.compile(r'qwen3\.8-max', re.IGNORECASE),
    re.compile(r'-thinking(?:[:@-]|$)', re.IGNORECASE),
    re.compile(r'-reasoning(?:[:@-]|$)', re.IGNORECASE),
)

# TASK-813: pipelines whose calls default to `provider_routing={'sort':
# 'price'}` when the caller does not specify one. Scoped rather than global
# because "cheapest provider for this model" is a cost lever for the
# high-volume vocab_ladder generation/judge traffic ADR-028 targets, not a
# blanket policy this change should impose on every pipeline in one step.
_PRICE_ROUTED_PIPELINES: frozenset[str] = frozenset({'vocab_ladder'})


def _is_reasoning_only_model(model: str | None) -> bool:
    """True for a model that must never have reasoning mode disabled.

    Checked before sending `reasoning: {exclude: True}` — see
    `_REASONING_ONLY_MODEL_PATTERNS` for why this is a denylist rather than
    an allowlist.
    """
    if not model:
        return False
    return any(p.search(model) for p in _REASONING_ONLY_MODEL_PATTERNS)


# ADR-028 Phase 1 rollout finding (2026-09-27): sending `reasoning:
# {exclude: True}` together with `provider: {'sort': 'price'}` to a qwen
# model reproducibly makes the cheapest OpenRouter provider for that model
# return an EMPTY completion for structurally demanding vocab_ladder steps —
# confirmed live via A/B on EN `ladder_l4_morphology_generation` /
# `ladder_word_family_generation` on qwen/qwen3.7-plus: price-routing OFF
# (reasoning still disabled) succeeds; reasoning-disable OFF (price-routing
# still on) succeeds; both flags on together reproduces "LLM returned empty
# content" every time. The cheapest provider apparently needs its own
# reasoning pass to produce a well-formed answer for these prompts and
# returns nothing when reasoning is explicitly excluded. Scoped to the qwen
# family (not pulled out of price-routing entirely) so the ADR-028 cost win
# from `sort: price` is kept for every other model; revisit per-provider if
# a non-qwen model shows the same interaction.
#
# ADR-028 continuation (2026-09-28): the finding above described a
# WORKAROUND (leave reasoning ON for these calls), not a fix — Phase 1 then
# showed leaving reasoning ON is expensive: 85-90% of qwen/qwen3.7-plus
# completion tokens on every vocab_ladder task, in every language, were
# reasoning_tokens. `_unsafe_to_disable_reasoning_when_price_routed` still
# correctly identifies the qwen family this interaction applies to; the
# call site (`_make_one_call`) no longer uses it to skip disabling reasoning
# — it uses it to pick the ACTUAL fix, `reasoning: {'enabled': False}` +
# `provider.require_parameters: True`, instead. See
# `_use_enabled_false_reasoning_param`.
_PRICE_ROUTING_UNSAFE_TO_DISABLE_REASONING_PATTERNS: tuple[re.Pattern, ...] = (
    re.compile(r'^qwen/', re.IGNORECASE),
)


def _unsafe_to_disable_reasoning_when_price_routed(model: str | None) -> bool:
    """True when naively sending `reasoning: {'exclude': True}` to `model`
    while the call is also using price-based provider routing reproducibly
    returns empty content from the cheapest provider (see the ADR-028 note
    above). Not "must be left on" any more — see `_use_enabled_false_reasoning_param`
    for the actual fix this now gates."""
    if not model:
        return False
    return any(
        p.search(model)
        for p in _PRICE_ROUTING_UNSAFE_TO_DISABLE_REASONING_PATTERNS
    )


# ADR-028 continuation (2026-09-28): models where `reasoning: {'enabled':
# False}` (paired with `provider.require_parameters: True` when the call is
# also price-routed) is the validated way to fully disable reasoning, in
# place of the default `{'exclude': True}` (see `_make_one_call`). Reuses
# the qwen price-routing-unsafe pattern rather than a new one — same model
# family, same interaction, now resolved instead of avoided. Not extended to
# every model yet: `enabled: False` + `require_parameters: True` together
# produced a live 404 ("no endpoints found") for an unrelated non-qwen model
# during this investigation, so this stays a per-model allowlist rather than
# a global default until other families are validated individually.
_ENABLED_FALSE_REASONING_MODEL_PATTERNS = _PRICE_ROUTING_UNSAFE_TO_DISABLE_REASONING_PATTERNS


def _use_enabled_false_reasoning_param(model: str | None) -> bool:
    """True when `model` should get `reasoning: {'enabled': False}` (the
    parameter that actually stops reasoning generation) instead of the
    default `{'exclude': True}` (which only hides it from the response but
    still generates and bills it)."""
    if not model:
        return False
    return any(p.search(model) for p in _ENABLED_FALSE_REASONING_MODEL_PATTERNS)

# CSV sink: a plain, greppable, always-available record of every call this
# process makes — independent of Supabase, and (unlike llm_calls.cost_usd)
# never silently NULL just because a call errored or the provider omitted
# usage accounting. One file per UTC day under logs/llm_usage/, so a single
# day's log stays a manageable size even with full prompt/response text in
# every row. Writes are lock-guarded: pipelines share this module's process
# and can call concurrently (see the shared-client-pool note below).
_CSV_LOG_LOCK = threading.Lock()

_CSV_FIELDS = [
    'timestamp', 'pipeline', 'task_name', 'template_version', 'model',
    'provider', 'language_code', 'temperature', 'seed', 'max_tokens',
    'timeout_s', 'latency_ms', 'cost_usd',
    'input_tokens', 'output_tokens', 'cached_tokens', 'reasoning_tokens',
    'sense_id', 'call_role', 'generation_batch_id',
    'parsed_ok', 'schema_ok', 'judge_verdict', 'judge_confidence',
    'artifact_id', 'error', 'input_text', 'output_text',
]


def _csv_log_path(when: datetime) -> str:
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    directory = os.path.join(root, 'logs', 'llm_usage')
    os.makedirs(directory, exist_ok=True)
    return os.path.join(directory, f'llm_calls_{when:%Y-%m-%d}.csv')


def _log_llm_call_csv(row: dict) -> None:
    """Append one row to the daily LLM-usage CSV. Best-effort; never raises."""
    try:
        when = datetime.now(timezone.utc)
        path = _csv_log_path(when)
        full_row = {**row, 'timestamp': when.isoformat()}
        with _CSV_LOG_LOCK:
            write_header = not os.path.exists(path)
            with open(path, 'a', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=_CSV_FIELDS, extrasaction='ignore')
                if write_header:
                    writer.writeheader()
                writer.writerow(full_row)
    except Exception as exc:
        logger.warning("llm_calls CSV logging failed: %s", exc)


# Columns added by migrations/llm_calls_cost_instrumentation.sql. Until that
# migration is applied to a given environment, an insert carrying them fails
# (PostgREST reports the column as unknown / not in its schema cache) — this
# is expected during the window between deploying this code and the user
# applying the migration, and must degrade to the pre-migration column set
# rather than lose the row. See ``_insert_llm_call_row``.
_NEW_LLM_CALLS_COLUMNS = (
    'prompt_tokens', 'completion_tokens', 'cached_tokens', 'reasoning_tokens',
    'sense_id', 'call_role', 'generation_batch_id',
)

# Warn once per process on the degrade path, not once per call — a batch of
# thousands of senses would otherwise flood the log with the same message.
_warned_missing_llm_calls_columns = False


def _insert_llm_call_row(client, row: dict) -> None:
    """Insert one llm_calls row, degrading gracefully if the new instrumentation
    columns (``_NEW_LLM_CALLS_COLUMNS``) don't exist yet in this environment.

    Raises on any failure that is NOT plausibly "unknown column" — the caller
    (``_log_llm_call``) already wraps this in a broad try/except, but keeping
    that distinction here means a genuine outage still logs its real error
    rather than being masked by a fallback retry that also fails.
    """
    global _warned_missing_llm_calls_columns
    try:
        client.table('llm_calls').insert(row).execute()
        return
    except Exception as exc:
        msg = str(exc)
        looks_like_missing_column = (
            'schema cache' in msg
            or 'column' in msg.lower()
            or any(col in msg for col in _NEW_LLM_CALLS_COLUMNS)
        )
        if not looks_like_missing_column:
            raise
        if not _warned_missing_llm_calls_columns:
            logger.warning(
                "llm_calls insert failed — likely missing the cost-instrumentation "
                "columns (migrations/llm_calls_cost_instrumentation.sql not yet "
                "applied). Retrying without them for the rest of this process. "
                "Original error: %s", exc,
            )
            _warned_missing_llm_calls_columns = True
        fallback_row = {k: v for k, v in row.items() if k not in _NEW_LLM_CALLS_COLUMNS}
        client.table('llm_calls').insert(fallback_row).execute()


# ---------------------------------------------------------------------------
# In-process cost-hook subscribers (ADR-028 Phase 0)
# ---------------------------------------------------------------------------
#
# `_log_llm_call` always writes `llm_calls` through `get_supabase_admin()`
# directly (see below) — a caller that injects its OWN Supabase client into a
# pipeline (e.g. scripts/run_exercise_gen_eval.py's InterceptingClient) never
# sees that write, because it never goes through the injected client at all.
# That made `--max-cost-usd` inert: the harness's cost ledger only counted
# writes that passed through the client IT controlled, and this one never
# does.
#
# The fix is a plain in-process observer list, independent of Supabase
# entirely: any caller can subscribe a callback that fires synchronously,
# right after every `_log_llm_call`, with a small dict describing the call
# (task_name, model, cost_usd, prompt_tokens, completion_tokens,
# cached_tokens, reasoning_tokens, call_role, sense_id, latency_ms — plus a
# few convenience fields). This works whether or not the DB write itself
# succeeds, and whether or not the `llm_calls` cost-instrumentation columns
# (migrations/llm_calls_cost_instrumentation.sql) have been applied yet.
_cost_hook_subscribers: list[Callable[[dict], None]] = []
_cost_hook_lock = threading.Lock()


def subscribe_llm_cost_hook(callback: Callable[[dict], None]) -> Callable[[], None]:
    """Register `callback` to be invoked after every logged LLM call.

    Fires synchronously and in-process, from whichever thread placed the
    call — including a worker thread inside
    ``judges.base.BatchModeThreadPoolExecutor`` (contextvars, and therefore
    ``sense_id``/``generation_batch_id`` attribution, propagate into that pool
    the same way they do for the DB/CSV sinks; see the ``generation_context``
    docstring above). Independent of whether the `llm_calls` Supabase write
    succeeds — this is the whole point: it observes what really happened,
    not what a particular injected DB client happened to see.

    Returns an ``unsubscribe`` callable; callers that subscribe for the
    duration of a single run (e.g. a harness) MUST call it when done, or the
    subscriber leaks into every later call in this process.

    Exceptions raised by `callback` are caught and logged — a broken
    subscriber must never break a generation pipeline (same fail-soft
    contract as the DB/CSV sinks).
    """
    with _cost_hook_lock:
        _cost_hook_subscribers.append(callback)

    def _unsubscribe() -> None:
        with _cost_hook_lock:
            if callback in _cost_hook_subscribers:
                _cost_hook_subscribers.remove(callback)

    return _unsubscribe


def _notify_cost_hooks(event: dict) -> None:
    with _cost_hook_lock:
        subscribers = list(_cost_hook_subscribers)
    for callback in subscribers:
        try:
            callback(event)
        except Exception as exc:  # fail-soft: never break the caller
            logger.warning("llm cost-hook subscriber raised: %s", exc)


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
    cost_usd: float | None = None,
    language_code: str | None = None,
    provider: str | None = None,
    max_tokens: int | None = None,
    timeout_s: int | None = None,
    input_text: str | None = None,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
    cached_tokens: int | None = None,
    reasoning_tokens: int | None = None,
    sense_id: int | None = None,
    call_role: str | None = None,
    generation_batch_id: str | None = None,
    error: str | None = None,
) -> None:
    """Record one LLM round-trip: a row in llm_calls (DB) and a row in the
    daily CSV log. Both sinks are best-effort — neither can raise back into
    the calling pipeline.

    ``sense_id``/``generation_batch_id`` fall back to the ``generation_context``
    contextvars when not passed explicitly; ``call_role`` defaults to
    ``'primary'`` — every logged call has a role, even one only a caller that
    predates this instrumentation forgot to name.
    """
    effective_sense_id = sense_id if sense_id is not None else _ctx_sense_id.get()
    effective_batch_id = (
        generation_batch_id if generation_batch_id is not None
        else _ctx_generation_batch_id.get()
    )
    effective_call_role = call_role if call_role in _VALID_CALL_ROLES else CALL_ROLE_PRIMARY

    # Cost-hook notification happens unconditionally and first — independent
    # of whether the DB/CSV sinks below succeed. See subscribe_llm_cost_hook.
    _notify_cost_hooks({
        'pipeline': pipeline,
        'task_name': task_name,
        'model': model,
        'cost_usd': cost_usd,
        'prompt_tokens': input_tokens,
        'completion_tokens': output_tokens,
        'cached_tokens': cached_tokens,
        'reasoning_tokens': reasoning_tokens,
        'call_role': effective_call_role,
        'sense_id': effective_sense_id,
        'generation_batch_id': effective_batch_id,
        'language_code': language_code,
        'latency_ms': latency_ms,
    })

    try:
        from services.supabase_factory import get_supabase_admin, get_supabase
        admin_client = get_supabase_admin()
        if admin_client:
            client = admin_client
        else:
            logger.warning("Supabase service role key not available; observability fallback to anon client (RLS-restricted)")
            client = get_supabase()
        if client is None:
            raise RuntimeError("no supabase client available")
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
            'cost_usd': cost_usd,
            'language_code': language_code,
            'prompt_tokens': input_tokens,
            'completion_tokens': output_tokens,
            'cached_tokens': cached_tokens,
            'reasoning_tokens': reasoning_tokens,
            'sense_id': effective_sense_id,
            'call_role': effective_call_role,
            'generation_batch_id': effective_batch_id,
        }
        _insert_llm_call_row(client, row)
    except Exception as exc:
        # Observability must never break the calling pipeline.
        logger.warning("llm_calls logging failed: %s", exc)

    _log_llm_call_csv({
        'pipeline': pipeline,
        'task_name': task_name,
        'template_version': template_version,
        'model': model,
        'provider': provider,
        'language_code': language_code,
        'temperature': temperature,
        'seed': seed,
        'max_tokens': max_tokens,
        'timeout_s': timeout_s,
        'latency_ms': latency_ms,
        'cost_usd': cost_usd,
        'input_tokens': input_tokens,
        'output_tokens': output_tokens,
        'cached_tokens': cached_tokens,
        'reasoning_tokens': reasoning_tokens,
        'sense_id': effective_sense_id,
        'call_role': effective_call_role,
        'generation_batch_id': effective_batch_id,
        'parsed_ok': parsed_ok,
        'schema_ok': schema_ok,
        'judge_verdict': judge_verdict,
        'judge_confidence': judge_confidence,
        'artifact_id': artifact_id,
        'error': error,
        'input_text': input_text,
        'output_text': raw_response,
    })


# ---------------------------------------------------------------------------
# Retryable errors
# ---------------------------------------------------------------------------

_RETRYABLE = (
    APIConnectionError, RateLimitError, APITimeoutError, ConnectionError,
    TimeoutError,
    # TASK-737: raised bare as "Server disconnected" — not wrapped into
    # APIConnectionError by the SDK on every code path. Went unnoticed while
    # every call to this client was serial (one request at a time never
    # stresses a keep-alive connection pool); making the vocab-sense and
    # test-gen loops concurrent (all sharing get_client()'s cached per-process
    # OpenAI client) surfaced it as a real, non-retried failure — a shared
    # keep-alive connection recycled/closed by the server right as a
    # concurrent request reused it. Transient by nature: retrying the request
    # opens a fresh connection.
    httpx.RemoteProtocolError,
    # Same family of transient network fault, same fix.
    httpx.ConnectError,
    httpx.ReadError,
    httpx.WriteError,
)


def _retryable_types() -> tuple:
    """Retryable exceptions, including the headless CLI's failure type.

    ClaudeCliError covers a subprocess timeout, a non-zero exit and a transient
    API error surfaced through the envelope — all of which are worth one more
    roll, exactly like the HTTP providers' transient faults. Resolved lazily so
    importing llm_service never pulls in the subprocess module.
    """
    try:
        from services.claude_cli_client import ClaudeCliError
        return _RETRYABLE + (ClaudeCliError,)
    except Exception:  # pragma: no cover - defensive
        return _RETRYABLE


# ---------------------------------------------------------------------------
# Core call_llm
# ---------------------------------------------------------------------------

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(_retryable_types()),
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
    language_code: str | None = None,
    call_role: str | None = None,
    sense_id: int | None = None,
    generation_batch_id: str | None = None,
    allow_internal_repair: bool = True,
    provider_routing: dict | None = None,
    disable_reasoning: bool = True,
) -> dict | list | str | BaseModel:
    """Universal LLM call. Returns parsed JSON dict/list, raw text, or a
    validated Pydantic model instance.

    Args:
        prompt:          User message content.
        model:           Explicit model name (e.g. 'google/gemini-3.5-flash-lite').
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
        language_code:   Study-language code (zh | en | ja) for the llm_calls
                         log row, when the caller knows it. Purely an
                         observability tag — does not affect model
                         resolution (that's `language`/`model_override`).
                         Optional; NULL when omitted.
        call_role:       One of 'primary' (default) | 'json_repair' | 'retry' |
                         'salvage' | 'repair' — what kind of call this is
                         within a generation attempt. The internal repair
                         paths (malformed-JSON repair, schema-validation
                         repair) set this themselves; a caller with its own
                         retry/repair branch (e.g. a generator's second
                         attempt) should pass it explicitly. Defaults to
                         'primary' when omitted or not a recognised value.
        sense_id:        dim_word_senses.id this call is generating/judging
                         for, when known. Falls back to the
                         ``generation_context`` contextvar (set once per
                         sense by VocabAssetPipeline) when omitted — most
                         callers never need to pass this explicitly.
        generation_batch_id: word_assets.generation_batch_id for the batch
                         this call belongs to. Same contextvar fallback as
                         ``sense_id``.
        allow_internal_repair: When False, a malformed-JSON/empty response
                         (json.JSONDecodeError or RuntimeError from
                         ``_make_one_call``) is re-raised immediately instead
                         of triggering the internal ``_repair_malformed_json``
                         turn. Set this False when the caller already runs its
                         own outer retry loop (e.g. a generator's own
                         attempt-2) so a single bad completion costs exactly
                         one call here, not two. Defaults True to preserve
                         existing behaviour for callers with no outer retry.
        provider_routing: OpenRouter ``provider`` routing preference (e.g.
                         ``{'sort': 'price'}``), forwarded verbatim as
                         ``extra_body['provider']``. ``None`` (default)
                         resolves to ``{'sort': 'price'}`` automatically for
                         ``pipeline='vocab_ladder'`` calls (ADR-028) and to no
                         preference for every other pipeline. Ignored for a
                         non-OpenRouter client. Pass an explicit dict to
                         override either default.
        disable_reasoning: When True (the default, for every pipeline) and
                         the resolved model is not a known reasoning-only
                         model (see ``_is_reasoning_only_model``), sends a
                         ``extra_body['reasoning']`` payload so a
                         reasoning-capable model does not silently burn
                         reasoning tokens/latency on a call that never asked
                         for it. Never sent to a reasoning-only model (e.g.
                         ``qwen3.8-max``), which needs reasoning mode to
                         function at all. Ignored for a non-OpenRouter
                         client. The payload shape is per-model (see
                         ``_use_enabled_false_reasoning_param``): most models
                         get ``{'exclude': True}`` (hides reasoning from the
                         response; the provider may still generate and bill
                         it — an OpenRouter API property, not a bug here).
                         Validated qwen-family models get ``{'enabled':
                         False}`` instead, which actually stops generation
                         (ADR-028 continuation, 2026-09-28: this was silently
                         costing 85-90% of completion tokens on qwen/
                         qwen3.7-plus vocab_ladder tasks); when the call is
                         also price-routed, that model also gets
                         ``provider.require_parameters = True`` to avoid the
                         cheapest-provider-returns-empty-content failure (see
                         ``_unsafe_to_disable_reasoning_when_price_routed``).

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

    # TASK-813: resolve the effective provider-routing preference once. An
    # explicit caller value always wins; otherwise a price-routed pipeline
    # (today: vocab_ladder) gets `{'sort': 'price'}` by default so ladder
    # traffic lands on the cheapest provider serving the pinned model without
    # every one of its ~15 call sites needing this threaded through by hand.
    effective_provider_routing = provider_routing
    if (
        effective_provider_routing is None
        and log_pipeline in _PRICE_ROUTED_PIPELINES
        # Diagnostic-only A/B kill switch for the ADR-028 Phase 1 rollout
        # investigation (empty-content reports on qwen/qwen3.7-plus for EN
        # L4/word_family). Not read anywhere else; unset in every normal
        # deployment. Remove once TASK-813's routing default is confirmed
        # safe or replaced by a permanent per-model rule.
        and os.environ.get('LLM_AB_NO_PRICE_ROUTING') != '1'
    ):
        effective_provider_routing = {'sort': 'price'}

    effective_disable_reasoning = (
        disable_reasoning and os.environ.get('LLM_AB_NO_DISABLE_REASONING') != '1'
    )

    logger.debug(
        "LLM call: provider=%s model=%s temp=%.2f fmt=%s pipeline=%s task=%s",
        provider or LLM_DEFAULT_PROVIDER, resolved_model, temperature,
        response_format, log_pipeline, log_task,
    )

    try:
        call_result = _make_one_call(
            client=client,
            model=resolved_model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format=response_format,
            seed=seed,
            timeout=timeout,
            provider_routing=effective_provider_routing,
            disable_reasoning=effective_disable_reasoning,
        )
    except (json.JSONDecodeError, RuntimeError) as exc:
        # Malformed JSON or empty/missing content. The schema repair below only
        # fires on ValidationError (JSON already parsed), and tenacity only
        # retries transient API errors — so without this a single bad-JSON roll
        # silently loses the call. Route JSON callers through ONE deterministic
        # repair turn (text callers have no JSON to repair → re-raise).
        if response_format == 'text' or not allow_internal_repair:
            raise
        return _repair_malformed_json(
            client=client,
            model=resolved_model,
            original_messages=messages,
            bad_content=getattr(exc, 'raw_content', None),
            error=exc,
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
            language_code=language_code,
            sense_id=sense_id,
            generation_batch_id=generation_batch_id,
            provider_routing=effective_provider_routing,
            disable_reasoning=effective_disable_reasoning,
        )

    # Prefer the model the provider actually served (relevant for aliased
    # slugs / auto-routing) over the one requested, so llm_calls.model reflects
    # reality; fall back to the requested slug when the response omits it.
    logged_model = call_result.actual_model or resolved_model

    # Text path — short-circuit before any schema work.
    if response_format == 'text':
        _log_llm_call(
            pipeline=log_pipeline, task_name=log_task,
            template_version=template_version, model=logged_model,
            temperature=temperature, seed=seed, prompt_hash=prompt_hash,
            raw_response=call_result.raw_content, parsed_ok=call_result.parsed_ok,
            schema_ok=None,
            judge_verdict=None, judge_confidence=None,
            latency_ms=call_result.latency_ms, artifact_id=artifact_id,
            cost_usd=call_result.cost_usd,
            language_code=language_code, provider=provider, max_tokens=max_tokens,
            timeout_s=timeout, input_text=prompt, input_tokens=call_result.prompt_tokens,
            output_tokens=call_result.completion_tokens,
            cached_tokens=call_result.cached_tokens,
            reasoning_tokens=call_result.reasoning_tokens,
            call_role=call_role, sense_id=sense_id,
            generation_batch_id=generation_batch_id,
        )
        return call_result.parsed  # raw text

    # Schema path — validate, repair once on failure.
    if schema is not None:
        try:
            validated = schema.model_validate(call_result.parsed)
            _log_llm_call(
                pipeline=log_pipeline, task_name=log_task,
                template_version=template_version, model=logged_model,
                temperature=temperature, seed=seed, prompt_hash=prompt_hash,
                raw_response=call_result.raw_content, parsed_ok=call_result.parsed_ok,
                schema_ok=True,
                judge_verdict=None, judge_confidence=None,
                latency_ms=call_result.latency_ms, artifact_id=artifact_id,
                cost_usd=call_result.cost_usd,
                language_code=language_code, provider=provider, max_tokens=max_tokens,
                timeout_s=timeout, input_text=prompt, input_tokens=call_result.prompt_tokens,
                output_tokens=call_result.completion_tokens,
                cached_tokens=call_result.cached_tokens,
                reasoning_tokens=call_result.reasoning_tokens,
                call_role=call_role, sense_id=sense_id,
                generation_batch_id=generation_batch_id,
            )
            return validated
        except ValidationError as exc:
            # Log the failed initial attempt before retrying.
            _log_llm_call(
                pipeline=log_pipeline, task_name=log_task,
                template_version=template_version, model=logged_model,
                temperature=temperature, seed=seed, prompt_hash=prompt_hash,
                raw_response=call_result.raw_content, parsed_ok=call_result.parsed_ok,
                schema_ok=False,
                judge_verdict=None, judge_confidence=None,
                latency_ms=call_result.latency_ms, artifact_id=artifact_id,
                cost_usd=call_result.cost_usd,
                language_code=language_code, provider=provider, max_tokens=max_tokens,
                timeout_s=timeout, input_text=prompt, input_tokens=call_result.prompt_tokens,
                output_tokens=call_result.completion_tokens,
                cached_tokens=call_result.cached_tokens,
                reasoning_tokens=call_result.reasoning_tokens,
                call_role=call_role, sense_id=sense_id,
                generation_batch_id=generation_batch_id,
                error=str(exc),
            )
            return _repair_and_retry(
                client=client,
                model=resolved_model,
                original_messages=messages,
                invalid_parsed=call_result.parsed,
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
                language_code=language_code,
                sense_id=sense_id,
                generation_batch_id=generation_batch_id,
                provider_routing=effective_provider_routing,
                disable_reasoning=effective_disable_reasoning,
            )

    # JSON path, no schema — log and return.
    _log_llm_call(
        pipeline=log_pipeline, task_name=log_task,
        template_version=template_version, model=logged_model,
        temperature=temperature, seed=seed, prompt_hash=prompt_hash,
        raw_response=call_result.raw_content, parsed_ok=call_result.parsed_ok,
        schema_ok=None,
        judge_verdict=None, judge_confidence=None,
        latency_ms=call_result.latency_ms, artifact_id=artifact_id,
        cost_usd=call_result.cost_usd,
        language_code=language_code, provider=provider, max_tokens=max_tokens,
        timeout_s=timeout, input_text=prompt, input_tokens=call_result.prompt_tokens,
        output_tokens=call_result.completion_tokens,
        cached_tokens=call_result.cached_tokens,
        reasoning_tokens=call_result.reasoning_tokens,
        call_role=call_role, sense_id=sense_id,
        generation_batch_id=generation_batch_id,
    )
    return call_result.parsed


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------

@dataclass
class _CallResult:
    """Everything one API round-trip yields, for logging and for the caller.

    Replaces a growing positional tuple (it was up to 8 fields and about to
    grow to 10) — a dataclass means a new field doesn't force every unpacking
    call site to change, and named access at each usage is self-documenting.
    """
    parsed: dict | list | str
    raw_content: str
    parsed_ok: bool
    latency_ms: int
    cost_usd: float | None
    prompt_tokens: int | None
    completion_tokens: int | None
    cached_tokens: int | None
    reasoning_tokens: int | None
    actual_model: str | None


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
    provider_routing: dict | None = None,
    disable_reasoning: bool = False,
) -> _CallResult:
    """Execute a single API round-trip.

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
    if _is_openrouter(client):
        # Ask OpenRouter to return what the call actually cost. Without this the
        # response carries token counts but no price, and llm_calls.cost_usd
        # stays NULL — which silently disarms every budget ceiling that reads it
        # (run_generation_batch's --ceiling projects from exactly this column).
        extra_body: dict = {'usage': {'include': True}}
        # TASK-813: provider price routing + reasoning disabled. Both are
        # OpenRouter-only (a non-OpenRouter client, e.g. Ollama, never reaches
        # this branch) and both are safety-gated by the caller/model, not
        # unconditional: `provider_routing` is None unless the caller (or
        # call_llm's pipeline-scoped default) asked for one, and `reasoning`
        # is never sent to a model that needs reasoning mode to function
        # (`_is_reasoning_only_model`) — sending it there would break the
        # call, not just leave it unaffected.
        if provider_routing:
            # Copied, not aliased: a model-specific branch below may add
            # `require_parameters` to this dict, and `provider_routing` can
            # be a literal the caller (or call_llm's pipeline-scoped
            # default) reuses across calls for different models.
            extra_body['provider'] = dict(provider_routing)
        send_reasoning_exclude = (
            disable_reasoning
            and not _is_reasoning_only_model(model)
        )
        if send_reasoning_exclude:
            if _use_enabled_false_reasoning_param(model):
                # ADR-028 continuation (2026-09-28 live A/B, 2 zh + 2 ja
                # senses, full generate-for-sense pipeline): `reasoning:
                # {'exclude': True}` only HIDES reasoning from the response
                # -- OpenRouter still generates and bills the tokens (see
                # OpenRouter's reasoning-tokens docs). Phase 1 measured
                # 85-90% of qwen/qwen3.7-plus completion tokens as
                # reasoning_tokens on every vocab_ladder task in every
                # language -- that silent cost. `reasoning: {'enabled':
                # False}` is the parameter that actually stops generation;
                # confirmed live at 0 reasoning_tokens (down from ~85-90%),
                # 0% invalid-asset rate, full success, and roughly 5x lower
                # $/sense than the `exclude: True` baseline on the same
                # senses. When the call is also price-routed, pairing it
                # with `provider.require_parameters: True` is what actually
                # fixes the "cheapest provider returns empty content"
                # failure this file previously worked around by leaving
                # reasoning ON for a price-routed qwen call (see
                # `_unsafe_to_disable_reasoning_when_price_routed`) --
                # require_parameters makes OpenRouter skip providers that
                # don't support the reasoning param instead of silently
                # mishandling it. Scoped to the qwen pattern, not a global
                # default: this exact combination has not been validated
                # for other model families, and sending both unconditionally
                # to an unrelated (non-qwen) judge call during this A/B
                # produced a live 404 "no endpoints found" (require_parameters
                # filtered every provider for that model).
                extra_body['reasoning'] = {'enabled': False}
                if 'provider' in extra_body:
                    extra_body['provider']['require_parameters'] = True
            else:
                extra_body['reasoning'] = {'exclude': True}
        payload['extra_body'] = extra_body

    start = time.perf_counter()
    response = client.chat.completions.create(**payload)
    latency_ms = int((time.perf_counter() - start) * 1000)

    cost_usd = _extract_cost(response)
    (prompt_tokens, completion_tokens,
     cached_tokens, reasoning_tokens) = _extract_usage_tokens(response)
    # The model actually served, when the provider echoes it — OpenRouter can
    # route an aliased/`:free`-suffixed slug to a different underlying model,
    # and llm_calls.model should reflect what ran, not just what was asked
    # for. None (not the requested slug) when the response omits it; the
    # caller falls back to the requested slug itself.
    actual_model = getattr(response, 'model', None) or None

    if not response.choices:
        raise RuntimeError("LLM returned no choices")

    content = response.choices[0].message.content
    if not content:
        raise RuntimeError("LLM returned empty content")

    if response_format == 'text':
        return _CallResult(
            content, content, True, latency_ms, cost_usd,
            prompt_tokens, completion_tokens, cached_tokens, reasoning_tokens,
            actual_model,
        )

    try:
        parsed = json.loads(clean_json_response(content))
    except json.JSONDecodeError as exc:
        # Carry the raw content so the caller can echo it into a repair turn.
        exc.raw_content = content  # type: ignore[attr-defined]
        raise
    return _CallResult(
        parsed, content, True, latency_ms, cost_usd,
        prompt_tokens, completion_tokens, cached_tokens, reasoning_tokens,
        actual_model,
    )


def _is_openrouter(client) -> bool:
    """True when this client points at OpenRouter.

    Keyed off base_url rather than the provider name because the client pool is
    itself keyed by base_url, and callers may build one via explicit
    base_url/api_key without naming a provider.
    """
    try:
        return 'openrouter' in str(getattr(client, 'base_url', '')).lower()
    except Exception:
        return False


def _extract_cost(response) -> float | None:
    """USD cost of one call, as reported by the provider.

    OpenRouter puts it on ``usage.cost`` when usage accounting is requested. The
    OpenAI SDK's Usage model does not declare that field, so it lands in
    ``model_extra`` rather than as an attribute — both are checked. Returns None
    when the provider reports nothing, which is the honest answer: a fabricated
    per-token estimate would go stale the next time pricing moved, and a
    ceiling built on it would be wrong in the direction of overspending.
    """
    usage = getattr(response, 'usage', None)
    if usage is None:
        return None
    cost = getattr(usage, 'cost', None)
    if cost is None:
        extra = getattr(usage, 'model_extra', None) or {}
        cost = extra.get('cost')
    if cost is None:
        return None
    try:
        return float(cost)
    except (TypeError, ValueError):
        return None


def _extract_usage_tokens(
    response,
) -> tuple[int | None, int | None, int | None, int | None]:
    """(prompt_tokens, completion_tokens, cached_tokens, reasoning_tokens).

    Reasoning tokens live under ``completion_tokens_details.reasoning_tokens``
    on OpenAI-compatible responses (o1/qwen-reasoning style); absent for
    non-reasoning models, in which case it's simply None.

    Cached tokens live under ``prompt_tokens_details.cached_tokens`` — the
    portion of the prompt served from the provider's cache (OpenRouter passes
    this through from providers that support prompt caching). Checked both as
    a declared attribute and via ``model_extra``, same reasoning as
    ``_extract_cost``: the OpenAI SDK's ``PromptTokensDetails`` does declare
    ``cached_tokens``, but a provider-specific response can still surface it
    only in the pydantic extras bag.
    """
    usage = getattr(response, 'usage', None)
    if usage is None:
        return None, None, None, None
    prompt_tokens = getattr(usage, 'prompt_tokens', None)
    completion_tokens = getattr(usage, 'completion_tokens', None)

    reasoning_tokens = None
    completion_details = getattr(usage, 'completion_tokens_details', None)
    if completion_details is not None:
        reasoning_tokens = getattr(completion_details, 'reasoning_tokens', None)

    cached_tokens = None
    prompt_details = getattr(usage, 'prompt_tokens_details', None)
    if prompt_details is not None:
        cached_tokens = getattr(prompt_details, 'cached_tokens', None)
        if cached_tokens is None:
            extra = getattr(prompt_details, 'model_extra', None) or {}
            cached_tokens = extra.get('cached_tokens')

    return prompt_tokens, completion_tokens, cached_tokens, reasoning_tokens


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
    language_code: str | None = None,
    sense_id: int | None = None,
    generation_batch_id: str | None = None,
    provider_routing: dict | None = None,
    disable_reasoning: bool = True,
) -> BaseModel:
    """Single deterministic repair turn at temperature 0.0.

    Re-raises ValidationError if the repair output also fails validation.
    Logs its own llm_calls row with ``call_role='repair'``.
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

    call_result = _make_one_call(
        client=client,
        model=model,
        messages=repair_messages,
        temperature=0.0,
        max_tokens=max_tokens,
        response_format=response_format,
        seed=seed,
        timeout=timeout,
        provider_routing=provider_routing,
        disable_reasoning=disable_reasoning,
    )

    try:
        validated = schema.model_validate(call_result.parsed)
        schema_ok = True
        result: BaseModel = validated
        err: ValidationError | None = None
    except ValidationError as e:
        schema_ok = False
        result = None  # type: ignore[assignment]
        err = e

    _log_llm_call(
        pipeline=log_pipeline, task_name=f"{log_task}__repair",
        template_version=template_version,
        model=call_result.actual_model or model,
        temperature=0.0, seed=seed, prompt_hash=prompt_hash,
        raw_response=call_result.raw_content, parsed_ok=call_result.parsed_ok,
        schema_ok=schema_ok,
        judge_verdict=None, judge_confidence=None,
        latency_ms=call_result.latency_ms, artifact_id=artifact_id,
        cost_usd=call_result.cost_usd,
        language_code=language_code, max_tokens=max_tokens, timeout_s=timeout,
        input_text=repair_prompt, input_tokens=call_result.prompt_tokens,
        output_tokens=call_result.completion_tokens,
        cached_tokens=call_result.cached_tokens,
        reasoning_tokens=call_result.reasoning_tokens,
        call_role=CALL_ROLE_REPAIR, sense_id=sense_id,
        generation_batch_id=generation_batch_id,
        error=str(err) if err else None,
    )

    if err is not None:
        raise err
    return result


def _repair_malformed_json(
    *,
    client: OpenAI,
    model: str,
    original_messages: list[dict[str, str]],
    bad_content: str | None,
    error: Exception,
    schema: type[BaseModel] | None,
    response_format: str,
    max_tokens: int | None,
    timeout: int,
    seed: int | None,
    log_pipeline: str,
    log_task: str,
    template_version: int | None,
    artifact_id: str | None,
    prompt_hash: bytes,
    language_code: str | None = None,
    sense_id: int | None = None,
    generation_batch_id: str | None = None,
    provider_routing: dict | None = None,
    disable_reasoning: bool = True,
) -> dict | list | BaseModel:
    """Single deterministic repair turn for a malformed-JSON / empty response.

    Sibling of ``_repair_and_retry`` for a different trigger: there the JSON
    parsed but failed *schema* validation; here ``json.loads`` itself failed (or
    the model returned empty content), which the schema path never sees. One
    temp-0 turn re-asks for valid JSON; the (optional) schema is then validated.
    Re-raises if the repair output still cannot be parsed or validated.
    Logs its own llm_calls row(s) with ``call_role='json_repair'``.
    """
    repair_prompt = (
        "Your previous reply was not valid JSON: "
        f"{error}.\n"
        "Return the SAME content as a single valid JSON object — no markdown "
        "fences, no commentary, just the JSON."
    )
    repair_messages = list(original_messages)
    if bad_content:
        repair_messages.append({'role': 'assistant', 'content': bad_content})
    repair_messages.append({'role': 'user', 'content': repair_prompt})

    try:
        call_result = _make_one_call(
            client=client,
            model=model,
            messages=repair_messages,
            temperature=0.0,
            max_tokens=max_tokens,
            response_format=response_format,
            seed=seed,
            timeout=timeout,
            provider_routing=provider_routing,
            disable_reasoning=disable_reasoning,
        )
    except (json.JSONDecodeError, RuntimeError) as exc:
        # Repair turn ALSO failed to produce parseable JSON. Surface the
        # ORIGINAL error so the caller sees the root cause, not the retry's.
        _log_llm_call(
            pipeline=log_pipeline, task_name=f"{log_task}__json_repair",
            template_version=template_version, model=model,
            temperature=0.0, seed=seed, prompt_hash=prompt_hash,
            raw_response=None, parsed_ok=False, schema_ok=None,
            judge_verdict=None, judge_confidence=None,
            latency_ms=None, artifact_id=artifact_id,
            language_code=language_code, max_tokens=max_tokens, timeout_s=timeout,
            input_text=repair_prompt, error=str(exc),
            call_role=CALL_ROLE_JSON_REPAIR, sense_id=sense_id,
            generation_batch_id=generation_batch_id,
        )
        raise error

    schema_ok: bool | None = None
    result: dict | list | BaseModel = call_result.parsed
    schema_err: ValidationError | None = None
    if schema is not None:
        try:
            result = schema.model_validate(call_result.parsed)
            schema_ok = True
        except ValidationError as e:
            schema_ok = False
            schema_err = e

    _log_llm_call(
        pipeline=log_pipeline, task_name=f"{log_task}__json_repair",
        template_version=template_version,
        model=call_result.actual_model or model,
        temperature=0.0, seed=seed, prompt_hash=prompt_hash,
        raw_response=call_result.raw_content, parsed_ok=call_result.parsed_ok,
        schema_ok=schema_ok,
        judge_verdict=None, judge_confidence=None,
        latency_ms=call_result.latency_ms, artifact_id=artifact_id,
        cost_usd=call_result.cost_usd,
        language_code=language_code, max_tokens=max_tokens, timeout_s=timeout,
        input_text=repair_prompt, input_tokens=call_result.prompt_tokens,
        output_tokens=call_result.completion_tokens,
        cached_tokens=call_result.cached_tokens,
        reasoning_tokens=call_result.reasoning_tokens,
        call_role=CALL_ROLE_JSON_REPAIR, sense_id=sense_id,
        generation_batch_id=generation_batch_id,
        error=str(schema_err) if schema_err else None,
    )

    if schema_err is not None:
        raise schema_err
    return result
