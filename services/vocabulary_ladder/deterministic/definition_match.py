"""
``definition_match`` — L2 form recognition, tier-guarded (TASK-516 §5 #2).

Show the word, pick its definition from four. The existing renderer already did
this via the ``get_distractors`` RPC; what it did not do is care *where* the
wrong definitions came from. Sampling the whole language means an A1 word can
end up beside three C2 definitions, and the item becomes answerable from
register alone — the learner picks the simple-sounding one and is right, having
demonstrated nothing.

So distractors come from senses at the same complexity tier, falling back to
the wider pool only when the tier is too thin to fill four options.

nl handling: a learner studying Chinese from English sees English definitions —
native-language text — so the options and the key live under ``content.nl.<code>``
per the schema-v2 envelope (TASK-519). The word itself is TL and stays flat.
"""

from __future__ import annotations

import random

from services.exercise_generation.schemas.envelope import wrap_nl
from services.vocabulary_ladder.config import get_sentence_target
from services.vocabulary_ladder.deterministic import SenseContext, Skip, register
from services.vocabulary_ladder.deterministic.lexicon import get_lexicon

_TYPE = 'definition_match'


@register(_TYPE)
def build(ctx: SenseContext, skips: list[Skip]) -> list[dict]:
    """One MCQ per sense, or none with a recorded reason."""
    definition = (ctx.definition or (ctx.core or {}).get('definition') or '').strip()
    if not definition:
        skips.append(Skip(_TYPE, 'no definition on the P1 asset'))
        return []

    lexicon = get_lexicon(ctx.db, ctx.language_id)
    if not lexicon.entries:
        skips.append(Skip(_TYPE, 'lexicon unavailable — cannot source distractors'))
        return []

    rng = random.Random(f'{_TYPE}:{ctx.sense_id}:{ctx.variant}')
    distractors = lexicon.definitions_at_tier(
        tier=ctx.tier,
        exclude_sense_ids={ctx.sense_id},
        count=3,
        rng=rng,
    )
    # Never let the key's own text back in as a "wrong" option: two senses of
    # the same lemma can carry near-identical definitions.
    distractors = [d for d in distractors if d.strip() != definition][:3]
    if len(distractors) < 3:
        skips.append(Skip(
            _TYPE,
            f'only {len(distractors)} tier-{ctx.tier or "?"} distractor '
            f'definitions available',
        ))
        return []

    options = [definition] + distractors
    rng.shuffle(options)

    sentences = ctx.sentences
    word = get_sentence_target(sentences[0]) if sentences else ''

    return [wrap_nl(
        base={
            'word': word or ctx.lemma,
            'pronunciation': ctx.pronunciation
            or (ctx.core or {}).get('pronunciation', ''),
            'tier': ctx.tier,
        },
        exercise_type=_TYPE,
        nl_code=ctx.nl_language_code,
        nl_values={'options': options, 'correct_answer': definition},
    )]
