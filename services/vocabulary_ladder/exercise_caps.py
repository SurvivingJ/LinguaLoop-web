"""Per-type variant caps for context-free exercises (plan §3d, T3d.2).

A context-free exercise asks about a property of the word itself — a word has
one tone, one pinyin, one set of kanji readings. Two such items for the same
word are the same question with the options shuffled, and option order is a
render-time concern that costs nothing at serve time.

``LadderExerciseRenderer.build_rows`` renders the deterministic types once per
A/B asset variant, and both variants pick the same word, so every context-free
type came out doubled. Measured on live content: 245 surplus rows across ten
context-free types, of which 138 were ``definition_match`` alone.

The cap is per **(word_sense_id, exercise_type, context anchor)**, not per
word. Capping per word would delete whole skill types — 做 (zuò) carries 33
exercises across 12 genuinely distinct skills, and only the context-free
duplicates among them are waste. The anchor keeps the one legitimate exception
alive: a polyphonic word stores a ``context_sentence`` on its
hanzi_to_pinyin / kanji_to_reading items, and two readings in two sentences are
two real questions.

Applied at generation time by the renderer and by the LLM-path orchestrator,
and enforced again as a partial unique index in
``migrations/task743_context_free_exercise_caps.sql`` so a re-run cannot
reintroduce duplicates behind the application's back.
"""

from __future__ import annotations

import logging
from typing import Any, Iterable

from services.vocabulary_ladder.config import (
    CONTEXT_FREE_ANCHOR_KEY,
    context_free_cap,
)

logger = logging.getLogger(__name__)


def anchor_of(row: dict[str, Any]) -> str:
    """The context anchor for a row, or '' when it has none."""
    content = row.get('content') or {}
    if not isinstance(content, dict):
        return ''
    return str(content.get(CONTEXT_FREE_ANCHOR_KEY) or '')


def cap_key(row: dict[str, Any]) -> tuple | None:
    """The cap bucket a row falls in, or None when the row is uncapped."""
    exercise_type = row.get('exercise_type')
    sense_id = row.get('word_sense_id')
    if exercise_type is None or sense_id is None:
        return None
    if context_free_cap(exercise_type) is None:
        return None
    return (sense_id, exercise_type, anchor_of(row))


def apply_caps(
    rows: Iterable[dict[str, Any]],
    existing_counts: dict[tuple, int] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Split ``rows`` into (kept, dropped) by the per-type context-free caps.

    Order is preserved and the *earliest* rows in a bucket win, so a caller
    that renders its best variant first keeps it.

    Args:
        rows: candidate exercise rows, each with `exercise_type`,
            `word_sense_id` and `content`.
        existing_counts: how many rows already live in each bucket, as
            returned by :func:`count_existing`. Pass it when appending to a
            sense that already has content; omit when replacing it wholesale.

    Context-bearing rows and rows with no sense are passed through untouched —
    their supply is the limit, not a cap.
    """
    counts: dict[tuple, int] = dict(existing_counts or {})
    kept: list[dict[str, Any]] = []
    dropped: list[dict[str, Any]] = []

    for row in rows:
        key = cap_key(row)
        if key is None:
            kept.append(row)
            continue
        cap = context_free_cap(row['exercise_type'])
        if counts.get(key, 0) >= cap:
            dropped.append(row)
            continue
        counts[key] = counts.get(key, 0) + 1
        kept.append(row)

    return kept, dropped


def count_existing(rows: Iterable[dict[str, Any]]) -> dict[tuple, int]:
    """Bucket counts for rows already stored, for use as ``existing_counts``."""
    counts: dict[tuple, int] = {}
    for row in rows:
        key = cap_key(row)
        if key is not None:
            counts[key] = counts.get(key, 0) + 1
    return counts


def log_dropped(dropped: list[dict[str, Any]], context: str) -> None:
    """Report what the cap removed, grouped by type.

    Logged rather than silent: "this sense has fewer items than the generator
    produced" must always come with a reason a coverage check can read.
    """
    if not dropped:
        return
    by_type: dict[str, int] = {}
    for row in dropped:
        by_type[row.get('exercise_type', '?')] = (
            by_type.get(row.get('exercise_type', '?'), 0) + 1
        )
    logger.info(
        '%s: context-free cap dropped %d duplicate variant(s) (%s)',
        context, len(dropped),
        ', '.join(f'{t} x{n}' for t, n in sorted(by_type.items())),
    )
