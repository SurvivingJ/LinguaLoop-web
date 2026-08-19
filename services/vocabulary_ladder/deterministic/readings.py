"""
Script ↔ sound exercises, both directions (TASK-516 §5 #14/#16, TASK-529 §5 #15).

Four types, two languages, two directions:

  script → sound    ``hanzi_to_pinyin`` (zh)   ``kanji_to_reading`` (ja)
  sound → script    ``pinyin_to_hanzi`` (zh)   ``reading_to_kanji`` (ja)

The directions are not mirror images, and the difference is where their
distractors come from.

**Script → sound.** The learner picks a *pronunciation*, so a plausible wrong
pronunciation is a fair option even if no word happens to have it. Distractors
come from the phonological confusion sets in ``phonology.py``: tone variants
first for Chinese, voicing first for Japanese.

**Sound → script.** The learner picks a *character*, and a made-up character is
not a distractor — it is noise the eye discards instantly. So these draw from
the corpus, in priority order (TASK-529):

  1. same reading, different characters — true homophones, the real confusion
  2. shared character component — the 张/章/掌 class, for when a syllable has
     too few homophones to fill four options
  3. frequency-band filler — same length, comparable Zipf, so the answer can't
     be picked out by looking obscure

Contextual readings
-------------------
For a polyphone (行 xíng/háng, 重 zhòng/chóng; 本 ほん/もと) the question "what
is the reading?" has no single right answer out of context. When the corpus
records more than one reading for the lemma, the item carries the sense's P1
sentence and the stem asks for the reading *in that sentence*. The key is the
sense's own ``pronunciation``, which is per-sense and therefore already the
contextual reading — the fix is to show the learner the context we were
implicitly relying on.
"""

from __future__ import annotations

import random

from services.vocabulary_ladder.config import get_sentence_target
from services.vocabulary_ladder.deterministic import SenseContext, Skip, register
from services.vocabulary_ladder.deterministic.lexicon import get_lexicon
from services.vocabulary_ladder.deterministic.phonology import (
    format_pinyin, has_kanji, is_kana, kana_distractors,
    parse_pinyin, pinyin_distractors,
)


# ---------------------------------------------------------------------------
# script -> sound
# ---------------------------------------------------------------------------

@register('hanzi_to_pinyin')
def build_hanzi_to_pinyin(ctx: SenseContext, skips: list[Skip]) -> list[dict]:
    """Show the characters, pick the pinyin."""
    type_code = 'hanzi_to_pinyin'
    syllables = parse_pinyin(_pronunciation(ctx))
    if not syllables:
        skips.append(Skip(type_code, 'pronunciation missing or unparseable as pinyin'))
        return []

    distractors = pinyin_distractors(syllables, count=3)
    if len(distractors) < 3:
        skips.append(Skip(
            type_code, f'only {len(distractors)} pinyin confusions available'))
        return []

    return [_mcq(ctx, type_code, prompt=ctx.lemma,
                 key=format_pinyin(syllables), distractors=distractors)]


@register('kanji_to_reading')
def build_kanji_to_reading(ctx: SenseContext, skips: list[Skip]) -> list[dict]:
    """Show the written form, pick the kana reading."""
    type_code = 'kanji_to_reading'
    reading = _pronunciation(ctx)
    if not reading or not is_kana(reading):
        skips.append(Skip(type_code, 'pronunciation missing or not kana'))
        return []
    if not has_kanji(ctx.lemma):
        # A word already written in kana has nothing to read off. Not a
        # failure — most function words land here.
        skips.append(Skip(type_code, 'lemma contains no kanji — reading is trivial'))
        return []

    distractors = kana_distractors(reading, count=3)
    if len(distractors) < 3:
        skips.append(Skip(
            type_code, f'only {len(distractors)} kana confusions available'))
        return []

    return [_mcq(ctx, type_code, prompt=ctx.lemma,
                 key=reading, distractors=distractors)]


# ---------------------------------------------------------------------------
# sound -> script (TASK-529)
# ---------------------------------------------------------------------------

@register('pinyin_to_hanzi')
def build_pinyin_to_hanzi(ctx: SenseContext, skips: list[Skip]) -> list[dict]:
    """Show the pinyin, pick the characters."""
    type_code = 'pinyin_to_hanzi'
    syllables = parse_pinyin(_pronunciation(ctx))
    if not syllables:
        skips.append(Skip(type_code, 'pronunciation missing or unparseable as pinyin'))
        return []
    return _reverse(ctx, skips, type_code, prompt=format_pinyin(syllables))


@register('reading_to_kanji')
def build_reading_to_kanji(ctx: SenseContext, skips: list[Skip]) -> list[dict]:
    """Show the kana, pick the written form."""
    type_code = 'reading_to_kanji'
    reading = _pronunciation(ctx)
    if not reading or not is_kana(reading):
        skips.append(Skip(type_code, 'pronunciation missing or not kana'))
        return []
    if not has_kanji(ctx.lemma):
        skips.append(Skip(type_code, 'lemma contains no kanji — nothing to choose'))
        return []
    return _reverse(ctx, skips, type_code, prompt=reading)


def _reverse(
    ctx: SenseContext, skips: list[Skip], type_code: str, prompt: str,
) -> list[dict]:
    """Shared sound→script body: real-word distractors in priority order."""
    lexicon = get_lexicon(ctx.db, ctx.language_id)
    if not lexicon.entries:
        skips.append(Skip(
            type_code, 'lexicon unavailable — cannot source real-word foils'))
        return []

    key = ctx.lemma
    # The key itself must never appear as a foil: for a polyphone the corpus
    # holds the same lemma under two reading keys, and offering it as a wrong
    # answer would make the item unanswerable.
    exclude = {key}
    rng = random.Random(f'{type_code}:{ctx.sense_id}:{ctx.variant}')

    picked: list[str] = []
    sources: list[str] = []

    def take(source: str, candidates: list[str]) -> None:
        for candidate in candidates:
            if len(picked) >= 3:
                return
            if candidate in exclude or candidate in picked:
                continue
            picked.append(candidate)
            sources.append(source)

    take('homophone', lexicon.homophones(_pronunciation(ctx), exclude, count=3))
    if len(picked) < 3:
        take('component',
             lexicon.component_neighbours(key, exclude | set(picked), count=3))
    if len(picked) < 3:
        take('frequency', lexicon.frequency_band_fillers(
            key, exclude | set(picked), count=3 - len(picked), rng=rng,
        ))

    if len(picked) < 3:
        skips.append(Skip(
            type_code,
            f'only {len(picked)} real-word foils for reading {prompt!r} '
            f'(sparse homophone set, no component-table match)',
        ))
        return []

    item = _mcq(ctx, type_code, prompt=prompt, key=key, distractors=picked[:3])
    item['distractor_sources'] = dict(zip(picked[:3], sources[:3]))
    return [item]


# ---------------------------------------------------------------------------
# Shared
# ---------------------------------------------------------------------------

def _pronunciation(ctx: SenseContext) -> str:
    return (ctx.pronunciation or (ctx.core or {}).get('pronunciation') or '').strip()


def _mcq(
    ctx: SenseContext, type_code: str, prompt: str, key: str, distractors: list[str],
) -> dict:
    """Assemble the four-option item, with context when the lemma is polyphonic.

    All four types are TL-only — pinyin, kana and hanzi are all target-language
    strings — so there is no ``nl`` block to build. The gloss is deliberately
    omitted rather than added under an nl key: showing the meaning would turn a
    reading exercise into a recognition exercise.
    """
    rng = random.Random(f'{type_code}:{ctx.sense_id}:{ctx.variant}:shuffle')
    options = [key] + list(distractors[:3])
    rng.shuffle(options)

    content: dict = {
        'schema_version': 2,
        'prompt': prompt,
        'options': options,
        'correct_answer': key,
        'word': ctx.lemma,
        'direction': type_code,
    }

    lexicon = get_lexicon(ctx.db, ctx.language_id)
    if lexicon.is_polyphonic(ctx.lemma):
        sentence = ctx.sentence_for_level(1, default=0) or {}
        text = (sentence.get('text') or '').strip()
        if text:
            content['context_sentence'] = text
            content['context_target'] = get_sentence_target(sentence)
        content['is_polyphonic'] = True

    return content
