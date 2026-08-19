"""
``counter_match`` — JA counters (助数詞) as ladder L4 (TASK-530).

The Japanese half of the measure-word pair. Structurally identical to
``classifier_match`` — same index, same group-based distractors, same
multi-acceptable handling — and deliberately so: the two languages pose the
same problem, and there is no reason for the learner-facing item or the code
behind it to differ.

One Japanese-specific wrinkle: counters fuse phonologically with the numeral
(一本 = いっぽん, not いちほん). The item is built around the counter *form*, with
the dictionary's reading carried alongside when present, so the front end can
show what the phrase actually sounds like without this generator having to
model rendaku.

When the noun is absent from the counter dictionary this emits nothing — not a
``particle_selection`` item. The §6.10 fallback is a *routing* decision owned
by the capability matrix; emitting a different type from here would make the
matrix a lie about what produced the row.
"""

from __future__ import annotations

import random

from services.vocabulary_ladder.deterministic import SenseContext, Skip, register
from services.vocabulary_ladder.deterministic.dictionaries import get_index

_TYPE = 'counter_match'


@register(_TYPE)
def build(ctx: SenseContext, skips: list[Skip]) -> list[dict]:
    index = get_index(ctx.db, 'counter', ctx.language_id)
    if not index.is_loaded:
        skips.append(Skip(_TYPE, 'counter dictionary unavailable'))
        return []

    answers = index.answers_for(ctx.lemma, ctx.sense_id)
    if not answers:
        skips.append(Skip(
            _TYPE, f'{ctx.lemma!r} is not in the counter dictionary'))
        return []

    rng = random.Random(f'{_TYPE}:{ctx.sense_id}:{ctx.variant}')
    distractors = index.distractors_for(answers, count=3, rng=rng)
    if len(distractors) < 3:
        skips.append(Skip(
            _TYPE,
            f'only {len(distractors)} group distractors for counter '
            f'{answers[0].form!r}',
        ))
        return []

    key = answers[0]
    options = [key.form] + [d.form for d in distractors]
    rng.shuffle(options)

    return [{
        'schema_version': 2,
        'word': ctx.lemma,
        'pronunciation': ctx.pronunciation or '',
        'stem': f'{ctx.lemma}を一___',
        'options': options,
        'correct_answer': key.form,
        'accepted_answers': [w.form for w in answers],
        'option_readings': {
            w.form: w.reading for w in [*answers, *distractors] if w.reading
        },
        'semantic_label': key.semantic_label,
        'distractor_group': key.group_label,
    }]
