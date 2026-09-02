"""
Multi-item prompt batching — many rows per LLM call instead of one call per row.

Why
---
Backfills are row-shaped: one word, one call. Against a metered HTTP API that is
merely slow. Against a Claude subscription (services/claude_cli_client.py) it is
also *expensive in the currency that binds*: each call is a process spawn plus a
turn against a rate limit, so 5,000 words is 5,000 turns. Folding 200 words into
one prompt turns that into 25 turns.

The trade this makes
--------------------
Batching buys throughput and pays for it in blast radius: one malformed response
can lose 200 rows instead of 1. Every design choice below is about capping that.

* **Position keys, not domain ids.** Items are addressed as ``item_1 … item_N``
  and mapped back to real ids locally. The model never sees or invents a
  ``vocab_id``, and the outer keys cannot be confused with the 1-based numeric
  keys that the sense/ladder prompts already use *inside* each item
  (``{"1": simple, "2": standard, …}``).
* **Per-item validation.** A batch is not all-or-nothing. Items that parse are
  kept; only the missing and malformed ones are retried.
* **Bounded recursive retry.** The remainder is retried at a smaller batch size,
  halving until it reaches 1. A single poisonous item therefore costs a few
  extra small calls, not the batch and not the run.
* **The per-item prompt is unchanged.** Item bodies are rendered from the same
  ``prompt_templates`` rows as the single-item path, so batching does not fork
  the prompt corpus into a second, drifting copy.
"""

import json
import logging
import re
from typing import Any, Callable, Iterable, Iterator, Sequence, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar('T')

# Ceiling on items per call. Beyond this, output token limits start truncating
# the tail of the response — which reads as "the model skipped the last 40
# items" rather than as an error.
MAX_BATCH_SIZE = 500

_ITEM_KEY_RE = re.compile(r'item[_\s-]*(\d+)', re.IGNORECASE)

_BATCH_CONTRACT = """\
You are processing {n} independent items in a single request.

Each item below is delimited by a header line of the form `### item_<k>`. Treat
each item's instructions as if it were the only request you received. Items are
unrelated to each other: do not let one item's content influence another's, and
do not deduplicate, cross-reference, or summarise across items.

Return ONE JSON object whose keys are exactly the item labels `item_1` through
`item_{n}`, and whose values are the JSON payloads each item asks for.

Return all {n} keys. If an item cannot be completed, use the value null for that
key rather than omitting the key, shifting the other answers, or explaining.
Output the JSON object only — no preamble, no code fences.
"""


def chunked(items: Sequence[T], size: int) -> Iterator[list[T]]:
    """Yield ``items`` in lists of at most ``size``."""
    if size < 1:
        raise ValueError(f"batch size must be >= 1, got {size}")
    for start in range(0, len(items), size):
        yield list(items[start:start + size])


def build_batch_prompt(item_prompts: Sequence[str]) -> str:
    """Wrap per-item prompts into one multi-item request.

    ``item_prompts`` are rendered from the normal templates; this only adds the
    envelope and the response contract.
    """
    if not item_prompts:
        raise ValueError("build_batch_prompt requires at least one item")

    n = len(item_prompts)
    body = '\n\n'.join(
        f"### item_{i}\n{prompt.strip()}"
        for i, prompt in enumerate(item_prompts, start=1)
    )
    return f"{_BATCH_CONTRACT.format(n=n)}\n\n{body}"


def parse_batch_response(
    data: Any,
    expected: int,
) -> tuple[dict[int, Any], list[int]]:
    """Split a batch response into (position -> payload) and a list of failures.

    Accepts the tolerant range of shapes models actually return: ``item_3``,
    ``item 3``, ``ITEM_3`` and bare ``3`` all resolve to position 3. A null or
    absent value is reported as a failure rather than silently dropped, because
    the caller must know which rows still need work.

    Returns:
        (payloads, failed_positions) — positions are 1-based.
    """
    if not isinstance(data, dict):
        logger.warning(
            "Batch response was %s, expected an object of item_N keys",
            type(data).__name__,
        )
        return {}, list(range(1, expected + 1))

    payloads: dict[int, Any] = {}
    for raw_key, value in data.items():
        key = str(raw_key).strip()
        match = _ITEM_KEY_RE.fullmatch(key) or _ITEM_KEY_RE.fullmatch(f'item_{key}')
        if not match:
            continue
        position = int(match.group(1))
        if not (1 <= position <= expected):
            logger.debug("Ignoring out-of-range batch key %r", raw_key)
            continue
        if value is None:
            continue
        payloads[position] = value

    failed = [i for i in range(1, expected + 1) if i not in payloads]
    if failed:
        logger.warning(
            "Batch returned %d/%d items; positions missing or null: %s",
            len(payloads), expected,
            ','.join(str(i) for i in failed[:20]) + ('…' if len(failed) > 20 else ''),
        )
    return payloads, failed


def run_batched(
    items: Sequence[T],
    *,
    render: Callable[[T], str | None],
    call: Callable[[str], Any],
    batch_size: int,
    validate: Callable[[Any], Any | None] | None = None,
    _depth: int = 0,
) -> dict[int, Any]:
    """Process ``items`` in batches, returning {index in ``items`` -> payload}.

    Args:
        items:      The work list.
        render:     Item -> its prompt body, or None to skip the item entirely.
        call:       Prompt -> parsed JSON (normally a call_llm closure).
        batch_size: Items per request; clamped to MAX_BATCH_SIZE.
        validate:   Optional payload -> normalised payload, or None to reject.
                    Rejected items are retried like missing ones.

    Items that never succeed are simply absent from the result; the caller
    decides whether that is a skip or a failure. Indices are 0-based positions
    into ``items``, so callers can map straight back to their own rows.
    """
    if not items:
        return {}

    size = max(1, min(batch_size, MAX_BATCH_SIZE))
    results: dict[int, Any] = {}

    # Render once. An item whose prompt cannot be built is dropped here rather
    # than shifting every later item's position in the batch.
    renderable: list[tuple[int, str]] = []
    for idx, item in enumerate(items):
        try:
            prompt = render(item)
        except Exception as exc:
            logger.warning("Could not render item %d, skipping: %s", idx, exc)
            continue
        if prompt:
            renderable.append((idx, prompt))

    for chunk in chunked(renderable, size):
        indices = [idx for idx, _ in chunk]
        prompts = [p for _, p in chunk]

        if len(chunk) == 1:
            # A batch of one needs no envelope; sending the bare item keeps the
            # single-item path byte-identical to the unbatched pipeline.
            payloads, failed = _call_single(prompts[0], call)
        else:
            try:
                raw = call(build_batch_prompt(prompts))
            except Exception as exc:
                logger.warning(
                    "Batch of %d failed (%s); retrying in smaller batches",
                    len(chunk), exc,
                )
                payloads, failed = {}, list(range(1, len(chunk) + 1))
            else:
                payloads, failed = parse_batch_response(raw, len(chunk))

        for position, payload in payloads.items():
            checked = validate(payload) if validate else payload
            if checked is None:
                failed.append(position)
                continue
            results[indices[position - 1]] = checked

        if failed and len(chunk) > 1:
            # Halve and retry only the stragglers. Bounded by construction: the
            # size strictly decreases and bottoms out at 1, where each item is
            # sent alone and either works or is genuinely unprocessable.
            remainder = [items[indices[p - 1]] for p in sorted(set(failed))]
            remainder_idx = [indices[p - 1] for p in sorted(set(failed))]
            logger.info(
                "Retrying %d unresolved item(s) at batch size %d",
                len(remainder), max(1, size // 2),
            )
            sub = run_batched(
                remainder, render=render, call=call,
                batch_size=max(1, size // 2), validate=validate,
                _depth=_depth + 1,
            )
            for sub_pos, payload in sub.items():
                results[remainder_idx[sub_pos]] = payload

    return results


def _call_single(prompt: str, call: Callable[[str], Any]) -> tuple[dict[int, Any], list[int]]:
    """Send one item unbatched; shaped like parse_batch_response's return."""
    try:
        raw = call(prompt)
    except Exception as exc:
        logger.warning("Single-item call failed: %s", exc)
        return {}, [1]
    if raw is None:
        return {}, [1]
    return {1: raw}, []
