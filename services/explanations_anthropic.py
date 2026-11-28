"""Exercise explanations written with the Anthropic API on the owner's key.

The owner chose (2026-11-27) to pay for the ahead-of-time Japanese batch with
their own Anthropic API key, held in the environment as ``CLAUDE_API`` (the key
the N1/N2 authoring used through ``scratch_offline/bin/claude``). The app's
live path stays on OpenRouter (``exercise_explanations.generate``); this module
is for batch scripts only and reuses that module's prompt (``build_prompt``)
and validation (``parse``), so an explanation written here is the same shape,
checked the same way, and served by the same code.

Calls go to https://api.anthropic.com explicitly: this environment sets
``ANTHROPIC_BASE_URL`` for its own use, which the SDK would otherwise follow.
Every call is appended to the owner's ledger (``CLAUDE_API_LEDGER``, default
``~/.claude_api_ledger.jsonl``) with its request id, tokens and cost, as the
shim does.
"""

from __future__ import annotations

import json
import os
import threading
import time
from dataclasses import dataclass
from typing import Any, Optional

from services import exercise_explanations as xe

API_BASE_URL = 'https://api.anthropic.com'
KEY_ENV = 'CLAUDE_API'
LEDGER = os.environ.get('CLAUDE_API_LEDGER') or os.path.expanduser('~/.claude_api_ledger.jsonl')
MAX_TOKENS = 16000

# Standard per-million-token prices (input, output), from the claude-api
# reference cached 2026-11-03. The Message Batches API bills half of these.
PRICES: dict[str, tuple[float, float]] = {
    'claude-opus-5-5': (4.00, 20.00),
    'claude-sonnet-5-5': (2.00, 10.00),
    'claude-haiku-5-5': (0.10, 0.50),
}

_ledger_lock = threading.Lock()


def make_client():
    """An SDK client on the owner's key (raises KeyError when it is not set)."""
    import anthropic
    return anthropic.Anthropic(api_key=os.environ[KEY_ENV], base_url=API_BASE_URL,
                               max_retries=4, timeout=180.0)


def cost_usd(model: str, input_tokens: int, output_tokens: int, *, batch: bool = False) -> float:
    pin, pout = PRICES[model]
    cost = (input_tokens * pin + output_tokens * pout) / 1_000_000
    return cost / 2 if batch else cost


def request_params(content: dict, tl_language_id: int, nl_language_id: int, exercise_type: str,
                   corrected: Optional[str], model: str, effort: str) -> Optional[dict]:
    """Messages API parameters for one item (None when it is not explainable)."""
    sents = xe.sentences_of(content, exercise_type)
    if sents is None:
        return None
    system, user = xe.build_prompt(sents, tl_language_id, nl_language_id, exercise_type,
                                   (content or {}).get('target_word'), corrected, content)
    return {
        'model': model,
        'max_tokens': MAX_TOKENS,
        'system': system,
        'messages': [{'role': 'user', 'content': user}],
        'output_config': {'effort': effort},
    }


def payload_from_message(msg: Any, content: dict, nl_language_id: int, exercise_type: str,
                         corrected: Optional[str]) -> Optional[dict]:
    """The validated payload in a Messages API response, or None when unusable."""
    if getattr(msg, 'stop_reason', None) not in ('end_turn', 'stop_sequence'):
        return None
    text = ''.join(b.text for b in msg.content if getattr(b, 'type', '') == 'text')
    sents = xe.sentences_of(content, exercise_type)
    if sents is None:
        return None
    # The model now and then writes its JSON, notices a slip and writes a
    # corrected JSON after it ("Wait, ... Here is the corrected JSON:", pilot
    # 2026-11-27): the last object that validates is its final answer.
    for raw in reversed(json_objects(text)):
        entries = xe.parse(raw, sents, nl_language_id, exercise_type, corrected)
        if entries is not None:
            return {'sentences': entries, 'prompt_version': xe.prompt_version(exercise_type)}
    return None


def json_objects(text: str) -> list:
    """Every top-level JSON object in ``text``, in order (code fences and prose between them ignored)."""
    decoder = json.JSONDecoder()
    out, pos = [], 0
    text = text or ''
    while True:
        start = text.find('{', pos)
        if start < 0:
            return out
        try:
            obj, end = decoder.raw_decode(text, start)
        except ValueError:
            pos = start + 1
            continue
        if isinstance(obj, dict):
            out.append(obj)
        pos = end


@dataclass
class Result:
    payload: Optional[dict]
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    seconds: float
    stop_reason: Optional[str]
    request_id: Optional[str]
    error: Optional[str] = None


def _ledger(entry: dict) -> None:
    try:
        with _ledger_lock, open(LEDGER, 'a', encoding='utf-8') as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + '\n')
    except OSError:
        pass


def generate(client, content: dict, tl_language_id: int, nl_language_id: int, exercise_type: str,
             corrected: Optional[str], model: str, effort: str = 'medium',
             exercise_id: Optional[str] = None) -> Result:
    """One synchronous call (standard price), with its tokens, cost and outcome."""
    import anthropic
    params = request_params(content, tl_language_id, nl_language_id, exercise_type, corrected,
                            model, effort)
    if params is None:
        return Result(None, model, 0, 0, 0.0, 0.0, None, None, 'not explainable')
    started = time.monotonic()
    try:
        msg = client.messages.create(**params)
    except anthropic.APIStatusError as exc:
        _ledger({'ts': time.time(), 'model': model, 'error': str(exc)[:300],
                 'artifact_id': exercise_id, 'via': 'explanations_anthropic'})
        return Result(None, model, 0, 0, 0.0, time.monotonic() - started, None, None,
                      f'{exc.status_code}: {str(exc)[:200]}')
    except anthropic.APIConnectionError as exc:
        return Result(None, model, 0, 0, 0.0, time.monotonic() - started, None, None,
                      f'connection: {exc}')
    seconds = time.monotonic() - started
    usage = msg.usage
    cost = cost_usd(model, usage.input_tokens, usage.output_tokens)
    _ledger({'ts': time.time(), 'model': msg.model, 'request_id': getattr(msg, '_request_id', None),
             'input_tokens': usage.input_tokens, 'output_tokens': usage.output_tokens,
             'cost_usd': round(cost, 6), 'artifact_id': exercise_id,
             'via': 'explanations_anthropic'})
    payload = payload_from_message(msg, content, nl_language_id, exercise_type, corrected)
    return Result(payload, model, usage.input_tokens, usage.output_tokens, cost, seconds,
                  msg.stop_reason, getattr(msg, '_request_id', None),
                  None if payload else 'unusable answer')
