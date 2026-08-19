"""
``tone_id_word`` — identify a Chinese word's tone contour (TASK-516 §5 #13).

Distinct from ``hanzi_to_pinyin``, which asks for the whole pronunciation. This
asks only for the *tones*, presented as a contour (e.g. 1-4), so the segments
give nothing away and the learner has to hear pitch alone. That isolation is
the point: a learner who reliably reads the segments but guesses the tones
scores well on the pinyin item and badly here, which is the diagnosis worth
having.

Distractors are single-tone perturbations of the key — see
``phonology.tone_pattern_distractors``. A contour differing in every position
is answerable by elimination.
"""

from __future__ import annotations

import random

from services.vocabulary_ladder.deterministic import SenseContext, Skip, register
from services.vocabulary_ladder.deterministic.phonology import (
    format_pinyin, parse_pinyin, tone_pattern, tone_pattern_distractors,
)

_TYPE = 'tone_id_word'

# Learner-facing tone names, keyed by tone digit. 0 is the neutral tone, which
# is written as a light dot rather than a number in most textbooks.
_TONE_NAMES: dict[str, str] = {
    '1': 'high level (1)',
    '2': 'rising (2)',
    '3': 'dipping (3)',
    '4': 'falling (4)',
    '0': 'neutral',
}


@register(_TYPE)
def build(ctx: SenseContext, skips: list[Skip]) -> list[dict]:
    syllables = parse_pinyin(
        ctx.pronunciation or (ctx.core or {}).get('pronunciation') or ''
    )
    if not syllables:
        skips.append(Skip(_TYPE, 'pronunciation missing or unparseable as pinyin'))
        return []

    key = tone_pattern(syllables)
    if not key or set(key) <= {'0'}:
        # An all-neutral word has no contour to identify.
        skips.append(Skip(_TYPE, 'no marked tones — nothing to identify'))
        return []

    distractors = tone_pattern_distractors(syllables, count=3)
    if len(distractors) < 3:
        skips.append(Skip(_TYPE, f'only {len(distractors)} contrasting tone contours'))
        return []

    options = [key] + distractors
    random.Random(f'{_TYPE}:{ctx.sense_id}:{ctx.variant}').shuffle(options)

    return [{
        'schema_version': 2,
        'word': ctx.lemma,
        # Segments without tone marks: showing the marked pinyin would print
        # the answer next to the question.
        'toneless_pinyin': ' '.join(s.base for s in syllables),
        'full_pinyin': format_pinyin(syllables),
        'options': options,
        'correct_answer': key,
        'option_labels': {
            option: ' + '.join(_TONE_NAMES.get(digit, digit) for digit in option)
            for option in options
        },
        'syllable_count': len(syllables),
    }]
