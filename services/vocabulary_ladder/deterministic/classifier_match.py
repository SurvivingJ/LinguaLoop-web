"""
``classifier_match`` — ZH classifiers as ladder L4 (TASK-528).

Chinese concrete nouns have no morphology, so ``morphology_slot`` — L4 for
English and Japanese — has nothing to work with. The capability matrix routes
ZH ``concrete`` L4 to this type instead, which asks the productive question
Chinese actually poses: which classifier does this noun take?

The standalone classifier drill is untouched. What is new is that these items
carry ``sense_id`` and ``ladder_level=4``, so answering one feeds
``form_production`` family confidence through ``ladder_record_attempt`` like
any other ladder exercise. The drill trains classifiers as a topic; this trains
*this noun's* classifier as part of learning the noun.

Nouns absent from the dictionary produce nothing and say so — the matrix's
``requires: classifier_dict`` token cannot be evaluated at planning time, so
the skip has to happen here.
"""

from __future__ import annotations

import random

from services.vocabulary_ladder.deterministic import SenseContext, Skip, register
from services.vocabulary_ladder.deterministic.dictionaries import get_index

_TYPE = 'classifier_match'


@register(_TYPE)
def build(ctx: SenseContext, skips: list[Skip]) -> list[dict]:
    index = get_index(ctx.db, 'classifier', ctx.language_id)
    if not index.is_loaded:
        skips.append(Skip(_TYPE, 'classifier dictionary unavailable'))
        return []

    answers = index.answers_for(ctx.lemma, ctx.sense_id)
    if not answers:
        skips.append(Skip(
            _TYPE, f'{ctx.lemma!r} is not in the classifier dictionary'))
        return []

    rng = random.Random(f'{_TYPE}:{ctx.sense_id}:{ctx.variant}')
    distractors = index.distractors_for(answers, count=3, rng=rng)
    if len(distractors) < 3:
        skips.append(Skip(
            _TYPE,
            f'only {len(distractors)} group distractors for classifier '
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
        # The stem is a measure phrase with the classifier blanked, which is
        # how the structure is actually used — asking "which classifier?" in
        # the abstract tests recall of a table, not of the language.
        'stem': f'一___{ctx.lemma}',
        'options': options,
        'correct_answer': key.form,
        # Multi-acceptable is normal (书 takes 本 and 册). The grader must
        # accept any of these, not only the primary.
        'accepted_answers': [w.form for w in answers],
        'option_readings': {
            w.form: w.reading for w in [*answers, *distractors] if w.reading
        },
        'semantic_label': key.semantic_label,
        'distractor_group': key.group_label,
    }]
