"""
``definition_match`` — L2 form recognition, difficulty-matched (TASK-516 §5 #2).

Show the word, pick its definition from four. The existing renderer already did
this via the ``get_distractors`` RPC; what it did not do is care *where* the
wrong definitions came from. Sampling the whole language means an A1 word can
end up beside three C2 definitions, and the item becomes answerable from
register alone — the learner picks the simple-sounding one and is right, having
demonstrated nothing.

So distractors come from senses whose word frequency is close to the target's
and whose definition is about as long as the key, loosening stage by stage only
when the tight pool cannot fill four options (``Lexicon.definitions_near``).

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
_OVERSAMPLE = 12


# Dictionary headwords that are rare or archaic kanji spellings of words that
# are written in kana in ordinary text (JMdict "usually written in kana").
# dim_vocabulary.lemma keeps the dictionary spelling (為る, 軈て), which is
# right for lookup but wrong to show a learner beside four definitions. The
# kana form is hand-curated because dim_vocabulary.reading is not reliable for
# these (為る -> なる, 言う -> ゆう, 留まる -> とまる).
USUALLY_KANA_JA: dict[str, str] = {
    '為る': 'する', '因る': 'よる', '齎す': 'もたらす', '成る': 'なる',
    '先ず': 'まず', '有る': 'ある', '居る': 'いる', '為': 'ため',
    '無い': 'ない', '於く': 'おく', '軈て': 'やがて', '出来る': 'できる',
    '沢山': 'たくさん',
}


def display_word(headword: str, language_id: int) -> str:
    """The form of ``headword`` to show a learner (kana for rare ja spellings)."""
    if language_id == 3:
        return USUALLY_KANA_JA.get(headword, headword)
    return headword


def script_family(text: str) -> str:
    """Coarse language family of a definition: 'cjk' (Han/kana) or 'latin'.

    Decided by the majority of letter characters, so a Japanese definition
    that quotes a Latin acronym still counts as 'cjk' and an English one that
    quotes a kanji word still counts as 'latin'.
    """
    cjk = latin = 0
    for ch in text:
        o = ord(ch)
        if 0x3040 <= o <= 0x30FF or 0x3400 <= o <= 0x9FFF:
            cjk += 1
        elif ch.isalpha():
            latin += 1
    return 'cjk' if cjk > latin else 'latin'


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
    # Difficulty is matched on word frequency, not on ``ctx.tier``: the tier
    # is the first example sentence's complexity label (T1/T3/T6), which no
    # lexicon entry carries, so a tier match never fired.
    frequency = lexicon.frequency_of(ctx.sense_id, ctx.headword or ctx.lemma)
    # Oversample: the filters below can reject candidates, and a rejected one
    # must be replaced rather than leaving the item short.
    distractors = lexicon.definitions_near(
        frequency=frequency,
        key_definition=definition,
        exclude_sense_ids={ctx.sense_id},
        count=_OVERSAMPLE,
        rng=rng,
    )
    # Never let the key's own text back in as a "wrong" option: two senses of
    # the same lemma can carry near-identical definitions.
    distractors = [d for d in distractors if d.strip() != definition]
    # Belt and braces behind the lexicon's native-only filter: every option
    # must be in the same script family as the key, or the item is answerable
    # by language alone (or just looks broken).
    key_family = script_family(definition)
    distractors = [d for d in distractors if script_family(d) == key_family][:3]
    if len(distractors) < 3:
        skips.append(Skip(
            _TYPE,
            f'only {len(distractors)} comparable distractor definitions '
            f'available (frequency {frequency if frequency is not None else "?"})',
        ))
        return []

    options = [definition] + distractors
    rng.shuffle(options)

    # The word shown beside four definitions is the headword the definition
    # describes. A sentence's target is the inflected surface form for ja/en
    # verbs (描い, aggregated), which is not a word anyone would look up, so
    # prefer the dictionary form and only fall back to the sentence target.
    sentences = ctx.sentences
    word = get_sentence_target(sentences[0]) if sentences else ''

    return [wrap_nl(
        base={
            'word': display_word(ctx.headword or word or ctx.lemma, ctx.language_id),
            'pronunciation': ctx.pronunciation
            or (ctx.core or {}).get('pronunciation', ''),
            'tier': ctx.tier,
        },
        exercise_type=_TYPE,
        nl_code=ctx.nl_language_code,
        nl_values={'options': options, 'correct_answer': definition},
    )]
