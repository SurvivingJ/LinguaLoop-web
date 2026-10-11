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

import re

from services.vocabulary_ladder.config import blank_target, get_sentence_target
from services.vocabulary_ladder.deterministic import SenseContext, Skip, register
from utils.answer_normalization import (
    build_accepted, matches, normalization_spec, normalize,
)

_TYPE = 'cloze_typed'

# `morphological_forms` labels that mark an entry as something OTHER than an
# inflection of the same word — a measure-word counter or a derived/compound
# word. Both have shown up in the `accepted` list for real cloze_typed items
# (助数詞 "台" offered for a bare-noun slot; 派生 compounds like 発明家/世界観
# offered as substitutes for their root noun) because every entry in
# `morphological_forms` was trusted as a safe substitute for the bare lemma.
# ja uses the coarse category labels; the English equivalents are included in
# case a future P1 prompt revision adopts the same vocabulary.
_NON_INFLECTION_LABELS = frozenset({
    '派生', '助数詞', 'derivation', 'counter', 'compound',
})

# A kana/katakana character (incl. the long-vowel mark) immediately after the
# target's occurrence means the sentence bakes in more of the conjugation
# right after the blank (て-form + auxiliary, ichidan stem + ます, ...). In
# that situation NO other `morphological_forms` entry is a safe substitute —
# every one of them is a *different complete* conjugation of the same verb,
# not a drop-in replacement for this stem, and splicing one in either
# duplicates the sentence's own suffix ('増え' + 'ています' template +
# accepted '増えています' -> doubled 'ています') or produces a mismatched
# conjugation ('不可欠' blanked out of '___な...', accepted '不可欠な' ->
# doubled 'な'). Returning nothing is the safe direction here, per the module
# docstring: a missing variant marks one right answer wrong; an over-broad
# set marks a wrong answer right.
_KANA_CONTINUATION = re.compile(r'^[぀-ヿㇰ-ㇿ]')


@register(_TYPE)
def build(ctx: SenseContext, skips: list[Skip]) -> list[dict]:
    source = _cloze_source(ctx)
    if source is None:
        skips.append(Skip(_TYPE, 'no cloze-capable sentence to derive from'))
        return []

    text, target = source
    blanked = blank_target(text, target, ctx.language_id)
    if blanked is None:
        # The blank is cut by replacing the target in the sentence; if there
        # is no clean word-boundary occurrence, the asset is internally
        # inconsistent (or `target` is only a fused substring of a longer
        # word, which would glue a stray suffix onto the blank marker).
        skips.append(Skip(
            _TYPE,
            f'target {target!r} has no clean word-boundary occurrence in its '
            f'own sentence',
        ))
        return []

    accepted = build_accepted(
        target, _interchangeable_variants(ctx, text, target), ctx.language_id,
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


def _interchangeable_variants(ctx: SenseContext, text: str, target: str) -> list[str]:
    """Morphological forms that may substitute for ``target`` in this blank.

    Empty unless the slot is uninflected — see the module docstring. Three
    checks gate what used to be a blind ``morph_form_texts(ctx.core)``:

    1. The existing bare-lemma guard: nothing is admitted unless ``target``
       is itself the dictionary-plain form.
    2. ``morphological_forms`` entries labelled as a derivation or counter
       (:data:`_NON_INFLECTION_LABELS`) are dropped outright — they are a
       different word, not an inflection, and substituting one produces a
       counter in a bare-noun slot or a compound noun standing in for its
       root (see the module-level constant's docstring for real examples).
    3. If the sentence continues the inflection immediately after the blank
       (:data:`_KANA_CONTINUATION`), the slot is conjugation-fixed: no
       variant is admitted at all, because every remaining
       ``morphological_forms`` entry is a different *complete* conjugation of
       the verb, not a substitute for this stem.
    """
    if normalize(target, ctx.language_id) != normalize(ctx.lemma, ctx.language_id):
        return []

    idx = text.find(target)
    if idx != -1:
        after = text[idx + len(target):]
        if _KANA_CONTINUATION.match(after):
            return []

    out: list[str] = []
    for form in (ctx.core or {}).get('morphological_forms') or []:
        if isinstance(form, dict):
            label = (form.get('label') or '').strip()
            if label in _NON_INFLECTION_LABELS:
                continue
            value = (form.get('form') or form.get('text') or '').strip()
        else:
            value = str(form or '').strip()
        if value and value != target:
            out.append(value)
    return out
