"""
``jumbled_sentence`` — L9 production from a P1 sentence (TASK-516 §5).

The previous renderer stored only ``original_sentence`` and chunked at serve
time. That deferral had two costs. It put a spaCy/jieba/fugashi parse in the
request path for every jumbled item served, and — worse — it meant nothing ever
checked whether a sentence *could* be chunked. A sentence the chunker splits
into two pieces is not an exercise, and we only found out in front of a learner.

Chunking here moves both the cost and the verdict offline: a sentence that
cannot yield 3-6 chunks is skipped with a reason, and what reaches the corpus
is known-renderable.

``original_sentence`` is still written so serve-side code that re-chunks (or
displays the solution) keeps working unchanged.
"""

from __future__ import annotations

import logging
import random

from services.vocabulary_ladder.config import get_sentence_target
from services.vocabulary_ladder.deterministic import SenseContext, Skip, register

logger = logging.getLogger(__name__)

_TYPE = 'jumbled_sentence'
_MIN_CHUNKS = 3
_MAX_CHUNKS = 6


@register(_TYPE)
def build(ctx: SenseContext, skips: list[Skip]) -> list[dict]:
    sentence = ctx.sentence_for_level(9, default=5)
    if not sentence:
        skips.append(Skip(_TYPE, 'no P1 sentence available'))
        return []

    text = (sentence.get('text') or '').strip()
    if not text:
        skips.append(Skip(_TYPE, 'assigned P1 sentence is empty'))
        return []

    chunks = _chunk(text, ctx.language_id)
    if chunks is None:
        skips.append(Skip(_TYPE, 'no language processor available for chunking'))
        return []
    if len(chunks) < _MIN_CHUNKS:
        skips.append(Skip(
            _TYPE,
            f'sentence chunks into {len(chunks)} pieces (min {_MIN_CHUNKS}) — '
            f'too short to jumble',
        ))
        return []
    if len(chunks) > _MAX_CHUNKS:
        # Not a failure: a long sentence is still usable, it just has to be
        # merged down or the exercise becomes a memory test rather than a
        # syntax one.
        chunks = _merge_to(chunks, _MAX_CHUNKS)

    # A shuffle that happens to reproduce the answer is not an exercise.
    shuffled = list(chunks)
    rng = random.Random(f'{_TYPE}:{ctx.sense_id}:{ctx.variant}')
    for _ in range(8):
        rng.shuffle(shuffled)
        if shuffled != chunks:
            break
    else:
        shuffled = list(reversed(chunks))

    return [{
        'schema_version': 2,
        'original_sentence': text,
        'chunks': chunks,
        'shuffled_chunks': shuffled,
        'target_word': get_sentence_target(sentence),
        'chunk_count': len(chunks),
    }]


def _chunk(text: str, language_id: int) -> list[str] | None:
    """Chunk via the language's processor. None means no processor at all."""
    from services.exercise_generation.language_processor import LanguageProcessor
    try:
        processor = LanguageProcessor.for_language(language_id)
    except Exception as exc:
        logger.warning('no language processor for %s: %s', language_id, exc)
        return None
    try:
        return [c.strip() for c in processor.chunk_sentence(text) if c and c.strip()]
    except Exception as exc:
        # EnglishProcessor.chunk_sentence raises on a too-short sentence; that
        # is a legitimate "cannot chunk", not an outage.
        logger.debug('chunking failed for %r: %s', text[:60], exc)
        return []


def _merge_to(chunks: list[str], limit: int) -> list[str]:
    """Fold the shortest adjacent pair repeatedly until within ``limit``.

    Merging the *shortest* neighbours keeps the chunks roughly even, which
    matters because a one-word chunk beside a nine-word chunk gives the answer
    away by shape alone.
    """
    out = list(chunks)
    while len(out) > limit:
        idx = min(
            range(len(out) - 1),
            key=lambda i: len(out[i]) + len(out[i + 1]),
        )
        joiner = '' if _is_cjk(out[idx]) else ' '
        out[idx: idx + 2] = [f'{out[idx]}{joiner}{out[idx + 1]}']
    return out


def _is_cjk(text: str) -> bool:
    """Whether the chunk is CJK, which is written without inter-word spaces."""
    return any(
        0x3040 <= ord(c) <= 0x30FF or 0x4E00 <= ord(c) <= 0x9FFF
        for c in text
    )
