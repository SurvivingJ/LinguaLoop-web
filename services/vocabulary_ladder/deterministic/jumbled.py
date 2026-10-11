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
import re

from services.vocabulary_ladder.config import get_sentence_target
from services.vocabulary_ladder.deterministic import SenseContext, Skip, register

logger = logging.getLogger(__name__)

_TYPE = 'jumbled_sentence'
_MIN_CHUNKS = 3
_MAX_CHUNKS = 6

# Dropped from both sides before comparing a reconstruction against the
# source sentence — the chunker's tokens never carry punctuation (is_punct
# tokens are filtered out before chunks are built), so a literal
# `joiner.join(chunks) == original_sentence` would fail on every sentence
# that ends in a period. What has to match is the *words*, not the
# punctuation nobody is asked to reproduce in this exercise.
_PUNCT_RE = re.compile(r'[^\w\s]', re.UNICODE)


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

    target = get_sentence_target(sentence)

    chunks = _chunk(text, ctx.language_id)
    if chunks is None:
        skips.append(Skip(_TYPE, 'no language processor available for chunking'))
        return []
    if not chunks or any(not c for c in chunks):
        skips.append(Skip(_TYPE, 'chunker returned empty or blank chunks'))
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
        # syntax one. CJK-only, never let that merge fuse the target word
        # into a neighbouring chunk (TASK bug #1: '一' merged into '一二'
        # alongside an adjacent number, with no space to keep them apart) —
        # if every remaining merge candidate would do that, the sentence
        # isn't usable at this chunk count. A Latin-script merge has no such
        # risk (the target stays a space-separated word inside the bigger
        # chunk), so it is left unrestricted there.
        protect_target = target if ctx.language_id in (1, 3) else None
        merged = _merge_to(chunks, _MAX_CHUNKS, protect_target)
        if merged is None:
            skips.append(Skip(
                _TYPE,
                f'cannot merge {len(chunks)} chunks down to {_MAX_CHUNKS} '
                f'without fusing the target word into a neighbour',
            ))
            return []
        chunks = merged

    # TASK bug #1: verify the chunks the learner is told are "correct order"
    # actually reconstruct the source sentence. Chunking bugs upstream (a
    # non-contiguous dependency-parse grouping, a chunk that silently drops a
    # word) previously reached the corpus undetected because nothing checked
    # this; the fix here is to check it and skip rather than to repair the
    # chunker's internals.
    joiner = '' if ctx.language_id in (1, 3) else ' '
    if _normalize_for_check(joiner.join(chunks)) != _normalize_for_check(text):
        skips.append(Skip(
            _TYPE,
            'chunk reconstruction does not match the source sentence — '
            f'chunks={chunks!r}',
        ))
        return []

    # TASK bug #1: the target word must be recoverable as a clean token
    # within its chunk, not fused into an unrelated neighbour (the '一二'
    # failure mode where a one-character target got merged with an adjacent
    # number and the result reads as a different token entirely). CJK-only:
    # a Latin-script chunk like 'will quickly waterlog' legitimately contains
    # its target as one of several space-separated words — that is the whole
    # point of a multi-word phrase chunk, not a fusion bug. Without
    # whitespace, CJK has no such separator, so a target merged into a chunk
    # there really does become unreadable as its own word.
    if target and ctx.language_id in (1, 3) and not _target_is_isolated(chunks, target, ctx.language_id):
        skips.append(Skip(
            _TYPE,
            f'target word {target!r} is fused into a neighbouring chunk — '
            f'chunks={chunks!r}',
        ))
        return []

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
        # `chunks` is in answer order; the renderer grades against this.
        'correct_ordering': list(range(len(chunks))),
        'shuffled_chunks': shuffled,
        'target_word': target,
        'chunk_count': len(chunks),
    }]


def _normalize_for_check(text: str) -> str:
    """Collapse whitespace and drop punctuation for the reconstruction check.

    The chunker never preserves punctuation (it filters ``is_punct`` tokens
    before building chunks), so comparing raw strings would reject every
    sentence that ends in '.', '。', etc. What must match is the sequence of
    words/characters the learner reorders, not the punctuation around them.
    """
    return re.sub(r'\s+', ' ', _PUNCT_RE.sub('', text)).strip()


def _target_is_isolated(chunks: list[str], target: str, language_id: int) -> bool:
    """Whether ``target`` survived chunking as its own standalone chunk.

    Deliberately an *exact* membership check rather than a "whole word inside
    a bigger chunk" one: CJK word-segmentation is too coarse a signal for that
    distinction (jieba merges a verb with its object into a single token —
    '喝咖啡' — so target '咖啡' would never pass a "whole token" test despite
    being a perfectly ordinary occurrence; it gives no way to tell that case
    apart from the real bug, '一' fused into '一二'). What this function
    actually guards against is narrower and checkable exactly: `_merge_to`
    above refuses to merge the target's own chunk with a neighbour, so as
    long as the target started out as its own chunk, it is still its own
    chunk here. If it is not, either the upstream `chunk_sentence()` call
    itself produced a chunk that already fused it (unrelated to this
    builder's own merge step and not something it can safely repair), and the
    honest thing is to skip rather than ship an item where the target cannot
    be pointed to.
    """
    return any(c == target for c in chunks)


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


def _merge_to(chunks: list[str], limit: int, target: str | None = None) -> list[str] | None:
    """Fold the shortest adjacent pair repeatedly until within ``limit``.

    Merging the *shortest* neighbours keeps the chunks roughly even, which
    matters because a one-word chunk beside a nine-word chunk gives the answer
    away by shape alone.

    ``target``, when given, is never one side of a merge: a one-character
    target chunk is exactly the kind of "shortest neighbour" this function
    would otherwise pick, and fusing it into an adjacent chunk (the '一二'
    failure mode — the target '一' merged with an adjacent '二') makes the
    target unrecoverable as its own token. Returns ``None`` if every
    remaining adjacent pair touches the target chunk, i.e. there is no way to
    merge further without fusing it.
    """
    out = list(chunks)
    while len(out) > limit:
        candidates = [
            i for i in range(len(out) - 1)
            if target is None or (out[i] != target and out[i + 1] != target)
        ]
        if not candidates:
            return None
        idx = min(candidates, key=lambda i: len(out[i]) + len(out[i + 1]))
        joiner = '' if _is_cjk(out[idx]) else ' '
        out[idx: idx + 2] = [f'{out[idx]}{joiner}{out[idx + 1]}']
    return out


def _is_cjk(text: str) -> bool:
    """Whether the chunk is CJK, which is written without inter-word spaces."""
    return any(
        0x3040 <= ord(c) <= 0x30FF or 0x4E00 <= ord(c) <= 0x9FFF
        for c in text
    )
