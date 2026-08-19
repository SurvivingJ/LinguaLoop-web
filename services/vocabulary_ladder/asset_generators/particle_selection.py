# services/vocabulary_ladder/asset_generators/particle_selection.py
"""``particle_selection`` — the Japanese L4 (TASK-527, §5 #7).

Japanese has no inflectional slot a morphology exercise can test the way
English does, so L4-JA is a *particle* exercise instead: one particle in a P1
sentence is blanked, and the learner picks it from four.

Division of labour
------------------
**The tokeniser chooses where the blank can go.** spaCy's ``ja_core_news_sm``
identifies particle spans (``pos_ == 'ADP'``, plus ``case``/``mark``
dependents), and only those offsets are offered to the model. Letting the
model pick the span freely produced blanks in the middle of content words —
the same class of error that the L8 collocate scan exists to prevent.

**The model chooses which of them is worth testing**, and supplies three
confusable particles with reasoning. "Pedagogically confusable" is a judgement
about learners, not about text, so it belongs to the model.

**The judge rules on uniqueness.** The failure that matters is the distractor
that also yields a natural sentence: に and へ are both grammatical with a
motion verb, differing only in nuance, so an item blanking one and offering
the other has two right answers. ``judges/particle`` asks precisely that.

Error tags
----------
Each distractor carries a confusion-class tag (``direction``,
``topic_vs_subject``, ``object_marking``, …). They ride on the item so the
practice engine can aggregate what a learner keeps getting wrong, rather than
only that they got particles wrong.
"""

from __future__ import annotations

import logging
import random

from services.vocabulary_ladder.asset_generators.typed_llm import (
    TypedLLMGenerator, register,
)
from services.vocabulary_ladder.config import get_sentence_target

logger = logging.getLogger(__name__)

TASK_NAME = 'ladder_particle_selection_generation'

LANGUAGE_JA = 3
REQUIRED_FOILS = 3

#: A sentence with no particle cannot host the exercise; one with a single
#: particle usually cannot host an interesting one (the blank is forced).
MIN_PARTICLES = 2


def particle_spans(text: str) -> list[dict]:
    """Particle occurrences in a Japanese sentence, as ``{particle, index}``.

    Delegates to the shared ``JapaneseProcessor`` so the tokeniser used here
    is the same one that chunks sentences for the jumbled exercise — two
    different notions of "particle" in one corpus would be worse than either.

    Returns ``[]`` when the processor cannot be built (spaCy model absent in a
    given environment), which makes the generator skip the sense rather than
    fall back to a regex over kana that would happily blank the ``に`` inside
    ``にんじん``.
    """
    if not text:
        return []
    try:
        from services.exercise_generation.language_processor import LanguageProcessor
        processor = LanguageProcessor.for_language(LANGUAGE_JA)
        return processor.particle_spans(text)
    except Exception as exc:
        logger.info('particle tokenisation unavailable (%s)', exc)
        return []


@register
class ParticleSelectionGenerator(TypedLLMGenerator):
    """Generates the ``particle_selection`` asset for one JA sense and variant."""

    TYPE_CODE = 'particle_selection'
    TASK_NAME = TASK_NAME
    LADDER_LEVEL = 4
    SENTENCE_SLOT = 4

    def _supports(self, core_asset: dict) -> bool:
        return bool(self.sentences(core_asset))

    def _sentence_index(
        self, core_asset: dict, sentence_assignments: dict[int, int],
    ) -> int | None:
        """The variant's L4 sentence if it carries enough particles, else a scan.

        Unlike morphology, this level's precondition is a property of the
        *sentence* rather than of the sense, so a sense whose assigned
        sentence happens to be particle-poor is still perfectly usable — just
        from a different sentence.
        """
        if not self._supports(core_asset):
            return None
        sentences = self.sentences(core_asset)
        preferred = sentence_assignments.get(self.SENTENCE_SLOT, 1)
        order = [preferred] + [i for i in range(len(sentences)) if i != preferred]
        for index in order:
            if not (0 <= index < len(sentences)):
                continue
            if len(particle_spans(sentences[index].get('text', ''))) >= MIN_PARTICLES:
                return index
        return None

    def _prompt_vars(
        self, core_asset: dict, sentence_index: int, used_distractors: list[str],
    ) -> dict:
        sentence = self.sentences(core_asset)[sentence_index]
        text = sentence.get('text', '')
        spans = particle_spans(text)
        return {
            'word': self.lemma(core_asset),
            'pos': core_asset.get('pos', ''),
            'semantic_class': core_asset.get('semantic_class', ''),
            'definition': core_asset.get('definition', ''),
            'sense_fingerprint': core_asset.get('sense_fingerprint') or '',
            'register': core_asset.get('register') or 'neutral',
            'complexity_tier': self.tier(core_asset),
            'sentence_text': text,
            'target_word': get_sentence_target(sentence),
            'particle_spans_json': self.json_dump(spans),
            'used_distractors_json': self.json_dump(used_distractors),
        }

    def _remap(self, raw: dict, sentence_index: int) -> dict:
        """Indexed output (0=options, 1=blanked_particle, 2=error_tags)
        → descriptive fragment."""
        parts = self.options_to_content(self.option_array(raw))
        return {
            'blanked_particle': self.field(raw, '1'),
            'options': parts['options'],
            'correct_answer': parts['correct_text'],
            'explanations': parts['explanations'],
            # Tag *values* stay as the model wrote them — they are a fixed
            # ASCII enum the practice engine aggregates on, not learner-facing
            # prose, so there is nothing to localise here.
            'error_tags': self.field(raw, '2') or {},
        }

    # ------------------------------------------------------------------
    # Render
    # ------------------------------------------------------------------

    def render(
        self, db, fragment: dict, core: dict, sense_id: int,
        language_id: int, nl_code: str,
    ) -> dict | None:
        from services.exercise_generation.judges.particle import filter_particle_foils
        from services.exercise_generation.schemas import wrap_nl

        correct = (fragment.get('blanked_particle') or '').strip()
        if not correct:
            return None

        sentence_index = fragment.get('sentence_index', 0)
        sentences = core.get('sentences') or []
        if not (0 <= sentence_index < len(sentences)):
            return None
        text = sentences[sentence_index].get('text', '')

        blanked = self.blank_particle(text, correct, fragment.get('particle_offset'))
        if blanked is None:
            logger.info(
                'particle_selection: %r has no tokenised span in its own sentence '
                'for sense %s', correct, sense_id,
            )
            return None

        foils = [
            (o.get('text') or '').strip()
            for o in fragment.get('options') or []
            if not o.get('is_correct') and (o.get('text') or '').strip()
        ]
        if len(foils) < REQUIRED_FOILS:
            return None

        kept, judge_meta = filter_particle_foils(
            db, blanked, correct, foils, language_id,
        )
        if len(kept) < REQUIRED_FOILS:
            logger.info(
                'particle_selection: %d/%d foils survived for sense %s; skipping variant',
                len(kept), len(foils), sense_id,
            )
            return None

        options = [correct, *kept[:REQUIRED_FOILS]]
        random.shuffle(options)

        error_tags = fragment.get('error_tags') or {}
        explanations = fragment.get('explanations') or {}
        base = {
            'sentence_with_blank': blanked,
            'original_sentence': text,
            'options': options,
            'correct_answer': correct,
            'target_word': get_sentence_target(sentences[sentence_index]),
            # Only for the distractors that survived — a tag for a dropped
            # foil would be an error class the learner can never trigger.
            'error_tags': {p: error_tags.get(p, '') for p in kept[:REQUIRED_FOILS]},
            '__judge_metas': {'particle': judge_meta},
        }
        return wrap_nl(
            base, self.TYPE_CODE, nl_code,
            {'explanation': explanations.get(correct, '')},
        )

    # ------------------------------------------------------------------

    @staticmethod
    def blank_particle(text: str, particle: str, offset: int | None = None) -> str | None:
        """Cut the blank at a tokeniser-confirmed particle span.

        Falls back to the first confirmed span for this particle when no
        offset was recorded. Returns None when the particle has no span in the
        sentence — a plain ``str.replace`` would happily blank the ``に``
        inside ``にんじん`` (carrot), producing an unanswerable item.
        """
        if not text or not particle:
            return None

        spans = [s for s in particle_spans(text) if s.get('particle') == particle]
        if not spans:
            return None

        target = None
        if offset is not None:
            target = next((s for s in spans if s.get('index') == offset), None)
        target = target or spans[0]

        start = target.get('index')
        if not isinstance(start, int) or not (0 <= start < len(text)):
            return None
        return text[:start] + '___' + text[start + len(particle):]
