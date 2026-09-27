"""
Client for OpenRouter's Decisions API (``typesafe/jev-1.13``).

jev is not a chat-completions model, so ``services.llm_service.call_llm`` cannot
reach it: it is a structured decision model behind

    POST https://openrouter.ai/api/alpha/decisions
    {"model": ..., "state": {...}, "questions": {key: {type, instructions, criteria}}}

and answers with typed values + probabilities, never text. This module is the
one place that knows that wire format. Judges build the ``state``/``questions``
and read the typed answers back.

Behaviour
---------
* Retries network errors, 429 (honouring ``Retry-After``), 5xx, and the
  *transient* 402 (``limit_source == 'openrouter_in_flight_budget'``). Any
  other 4xx -- including a permanent 402 (credits/key limit exhausted) -- raises
  ``JevError`` immediately; retrying it cannot help and would just delay the
  caller's fallback.
* Concurrency is capped process-wide (``JEV_MAX_CONCURRENCY``, default 8) so a
  worker pool that fans out judge calls cannot stampede the endpoint.
* Every call writes one ``llm_calls`` row (best effort) carrying
  ``cost_usd`` from the response's ``usage.cost``. The whole point of that
  column is cost accounting: several incumbent judges logged it as NULL for
  weeks, silently disarming every budget ceiling, so a response with no
  ``usage.cost`` logs a warning rather than passing unnoticed.
* The API key is read from the environment at *call* time. ``llm_service``
  freezes ``OPENROUTER_API_KEY`` at import, so a script that imports it before
  ``load_dotenv()`` runs with an empty key; this client does not share that trap
  (scripts should still ``load_dotenv()`` first for everything else).

Errors are all ``JevError``; callers own the fail-open / fail-closed decision.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from dataclasses import dataclass, field

from typing import Callable, Optional

import requests

logger = logging.getLogger(__name__)

DECISIONS_URL = 'https://openrouter.ai/api/alpha/decisions'
DEFAULT_MODEL = 'typesafe/jev-1.13'

_MAX_BACKOFF_S = 20.0
_MAX_RETRY_AFTER_S = 30.0

_semaphore = threading.BoundedSemaphore(
    max(1, int(os.environ.get('JEV_MAX_CONCURRENCY', '8')))
)

# Indirection so tests can run the retry loop without real sleeps.
_sleep = time.sleep

# llm_calls writes share one HTTP/2 Supabase client; with eight threads inserting
# at once ~2% of rows were dropped ("Server disconnected") in the 305-test
# re-tier. Serialising the (fast) insert keeps the ledger whole.
_log_lock = threading.Lock()


class JevError(RuntimeError):
    """A Decisions request failed for good (after retries, or non-retryable).

    ``status`` is the last HTTP status seen, or None for network/shape errors.
    """

    def __init__(self, message: str, status: Optional[int] = None):
        super().__init__(message)
        self.status = status


@dataclass
class JevResult:
    """One successful Decisions response."""
    answers: dict
    model: str                       # dated snapshot actually served
    cost_usd: float | None           # usage.cost; None if the response omitted it
    input_tokens: int | None
    output_tokens: int | None
    latency_ms: int
    raw: dict = field(repr=False, default_factory=dict)


def _api_key() -> str:
    key = os.environ.get('OPENROUTER_API_KEY', '')
    if not key:
        raise JevError('OPENROUTER_API_KEY is not set')
    return key


def _retry_after(resp: requests.Response, attempt: int) -> float:
    try:
        wait = float(resp.headers.get('Retry-After', ''))
    except (TypeError, ValueError):
        wait = 2.0 ** attempt
    return min(max(wait, 0.0), _MAX_RETRY_AFTER_S)


def call_jev(
    state: dict,
    questions: dict,
    *,
    model: str = DEFAULT_MODEL,
    pipeline: str = 'test_gen',
    task_name: str = 'jev_decision',
    language_code: str | None = None,
    template_version: int | None = None,
    max_retries: int = 4,
    timeout: float = 30.0,
    log: bool = True,
    summarize: Optional[Callable[[dict], tuple]] = None,
) -> JevResult:
    """One Decisions request. Raises ``JevError`` on any unrecoverable failure.

    ``summarize`` maps the answers to ``(verdict, confidence)`` for the
    llm_calls ``judge_verdict`` / ``judge_confidence`` columns.
    """
    headers = {
        'Authorization': f'Bearer {_api_key()}',
        'Content-Type': 'application/json',
    }
    body = {'model': model, 'state': state, 'questions': questions}

    attempt = 0
    with _semaphore:
        while True:
            attempt += 1
            t0 = time.monotonic()
            try:
                resp = requests.post(
                    DECISIONS_URL, headers=headers, json=body, timeout=timeout,
                )
            except requests.RequestException as exc:
                if attempt > max_retries:
                    raise JevError(f'network error after {attempt} attempts: {exc}') from exc
                _sleep(min(2.0 ** attempt, _MAX_BACKOFF_S))
                continue
            latency_ms = int((time.monotonic() - t0) * 1000)

            status = resp.status_code
            if status == 429 or status >= 500:
                if attempt > max_retries:
                    raise JevError(f'HTTP {status} after {attempt} attempts', status)
                _sleep(_retry_after(resp, attempt) if status == 429
                       else min(2.0 ** attempt, _MAX_BACKOFF_S))
                continue
            if status == 402:
                try:
                    limit_source = resp.json().get('limit_source')
                except ValueError:
                    limit_source = None
                if limit_source == 'openrouter_in_flight_budget' and attempt <= max_retries:
                    _sleep(_retry_after(resp, attempt))
                    continue
                raise JevError(
                    f'HTTP 402 (credits or key limit exhausted; '
                    f'limit_source={limit_source})',
                    402,
                )
            if status >= 400:
                raise JevError(f'HTTP {status}: {resp.text[:300]}', status)

            try:
                data = resp.json()
            except ValueError as exc:
                raise JevError(f'non-JSON 200 response: {exc}') from exc
            answers = data.get('answers')
            if not isinstance(answers, dict):
                raise JevError(f'response has no answers object: {str(data)[:300]}')
            break

    usage = data.get('usage') or {}
    cost = usage.get('cost')
    cost = float(cost) if isinstance(cost, (int, float)) else None
    if cost is None:
        logger.warning(
            'jev: response carried no usage.cost (task=%s) -- cost_usd will be NULL',
            task_name,
        )
    result = JevResult(
        answers=answers,
        model=data.get('model') or model,
        cost_usd=cost,
        input_tokens=usage.get('input_tokens'),
        output_tokens=usage.get('output_tokens'),
        latency_ms=latency_ms,
        raw=data,
    )
    if log:
        _log_call(result, pipeline, task_name, language_code, template_version,
                  summarize)
    return result


def _log_call(
    result: JevResult, pipeline: str, task_name: str,
    language_code: str | None, template_version: int | None,
    summarize: Optional[Callable[[dict], tuple]] = None,
) -> None:
    """Best-effort llm_calls row. Observability must never break the caller."""
    try:
        import json
        from services.llm_service import _log_llm_call

        verdict = confidence = None
        if summarize is not None:
            try:
                verdict, confidence = summarize(result.answers)
            except Exception as exc:  # noqa: BLE001
                logger.warning('jev: summarize hook failed (%s): %s', task_name, exc)

        with _log_lock:
            _log_llm_call(
                pipeline=pipeline, task_name=task_name,
                template_version=template_version, model=result.model,
                temperature=None, seed=None, prompt_hash=None,
                raw_response=json.dumps(result.answers, ensure_ascii=False),
                parsed_ok=True, schema_ok=True,
                judge_verdict=verdict, judge_confidence=confidence,
                latency_ms=result.latency_ms, artifact_id=None,
                cost_usd=result.cost_usd, language_code=language_code,
                provider='TypeSafe',
                input_tokens=result.input_tokens,
                output_tokens=result.output_tokens,
            )
    except Exception as exc:  # noqa: BLE001
        logger.warning('jev: llm_calls logging failed: %s', exc)
