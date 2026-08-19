"""
``cloze_typed`` — productive cloze with free input (TASK-532 §5 #4).

Same blank as L3's ``cloze_completion``, minus the options. Recognising the
right word among four is a different skill from producing it, and the ladder
wants both: L3 sits in ``meaning_recall``, this in ``form_production``.

Deriving rather than generating
-------------------------------
This builder makes no new content. It reuses the cloze the LLM already
produced — same sentence, same blank, same key — and drops the distractors.
The two items are then describably the same question in two modes, at no
extra cost.

Grading
-------
Exact match after normalisation, no LLM (operator decision). The accepted set
is the key plus, in the narrow case below, the sense's morphological variants;
the normalisation rules are *stored on the item* rather than assumed, so a
disputed answer can be explained after the fact. See
``utils/answer_normalization``.

Morphological variants are admitted only when the blank is not itself testing
the inflection. "Yesterday I ___ home" fixes the form, and accepting both *run*
and *ran* there would quietly teach the learner that the inflection does not
matter. The conservative rule: variants join the accepted set only when the
sentence's own target is the bare lemma, i.e. the slot is uninflected.
"""

from __future__ import annotations

from services.vocabulary_ladder.config import get_sentence_target
from services.vocabulary_ladder.deterministic import SenseContext, Skip, register
from services.vocabulary_ladder.tier_gate import morph_form_texts
from utils.answer_normalization import (
    build_accepted, matches, normalization_spec, normalize,
)

_TYPE = 'cloze_typed'


@register(_TYPE)
def build(ctx: SenseContext, skips: list[Skip]) -> list[dict]:
    source = _cloze_source(ctx)
    if source is None:
        skips.append(Skip(_TYPE, 'no cloze-capable sentence to derive from'))
        return []

    text, target = source
    if target not in text:
        # The blank is cut by replacing the target in the sentence; if it is
        # not there, the asset is internally inconsistent.
        skips.append(Skip(
            _TYPE, f'target {target!r} does not occur in its own sentence'))
        return []

    blanked = text.replace(target, '___', 1)
    accepted = build_accepted(
        target, _interchangeable_variants(ctx, target), ctx.language_id,
    )

    return [{
        'schema_version': 2,
        'sentence_with_blank': blanked,
        'original_sentence': text,
        'target_word': target,
        'word': ctx.lemma,
        'answer': {
            'accepted': accepted,
            # The comparison form, so a mismatch can be debugged without
            # re-deriving the rules from the grading code.
            'accepted_normalized': [
                normalize(a, ctx.language_id) for a in accepted
            ],
        },
        'normalization': normalization_spec(ctx.language_id),
        'input_mode': 'ime' if ctx.language_id in (1, 3) else 'text',
    }]


def grade(content: dict, typed: str | None, language_id: int | None = None) -> dict:
    """Grade a typed answer against an item's stored accepted set.

    Lives here, beside the builder that decided what ``accepted`` contains, so
    the two cannot drift apart — the same reason ``build_text`` is shared
    between the embedding backfill and its on-create hook.

    **The server is the authority for this type.** Every other renderer grades
    in the browser because the correct option is already in the payload and
    hiding it would buy nothing. Typed input is different: the comparison is a
    normalisation rule (NFKC, t2s, case, punctuation), and a rule implemented
    twice in two languages is a rule that will eventually disagree with itself.
    The client's verdict is treated as a hint and overwritten.

    Returns a dict rather than a bool so the caller can report *why* — an
    unexpectedly rejected answer is the main support question this type will
    generate.
    """
    answer = (content or {}).get('answer') or {}
    accepted = answer.get('accepted') or []
    if not accepted:
        target = (content or {}).get('target_word')
        accepted = [target] if target else []

    given = (typed or '').strip()
    is_correct = bool(given) and matches(given, accepted, language_id)
    return {
        'is_correct': is_correct,
        'typed': given,
        'normalized': normalize(given, language_id),
        'accepted': list(accepted),
        'graded_by': 'server',
    }


def _cloze_source(ctx: SenseContext) -> tuple[str, str] | None:
    """The sentence and target this item blanks.

    Uses the variant's L4 sentence assignment, so A and B blank different
    sentences and a learner meeting both does not answer the second from
    memory of the first.
    """
    sentence = ctx.sentence_for_level(4, default=1)
    if not sentence:
        return None
    text = (sentence.get('text') or '').strip()
    target = (get_sentence_target(sentence) or '').strip()
    if not text or not target:
        return None
    return text, target


def _interchangeable_variants(ctx: SenseContext, target: str) -> list[str]:
    """Morphological forms that may substitute for ``target`` in this blank.

    Empty unless the slot is uninflected — see the module docstring. Returning
    nothing is the safe direction: a missing variant marks one correct answer
    wrong, whereas an over-broad set marks a wrong answer correct.
    """
    if normalize(target, ctx.language_id) != normalize(ctx.lemma, ctx.language_id):
        return []
    return morph_form_texts(ctx.core)
