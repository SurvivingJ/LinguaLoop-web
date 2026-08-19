# services/vocabulary_ladder/asset_generators/word_family.py
"""``word_family`` — derived-form slot exercises (TASK-522, §5 #18).

English only, and for a reason: the exercise asks a learner to produce the
right *derivation* of a stem for a grammatical slot ("Her ___ was final" →
**decision**, from *decide*), which presupposes a productive derivational
morphology the analytic languages in this corpus do not have.

The defect to defend against
----------------------------
Distractors here are deliberately **invented** derivations — "decidement",
"decisionment" — because a learner who has half-learnt the family will
recognise the shape but not the word. That makes the generator's failure mode
unusually sharp: if the model invents something that turns out to be a real
word ("decisive" offered as a foil for a noun slot), the item has two
defensible answers.

Two checks catch that, cheapest first:

1. a **dictionary probe** over the sense's own attested ``morphological_forms``
   — certain, free, and it needs no model call;
2. the **word_family judge**, which rules on whether each survivor is a
   non-word.

Both are wired through ``judges/relation.filter_invented_derivations``, which
lets the certain signal veto the fuzzy one.
"""

from __future__ import annotations

import logging
import random

from services.vocabulary_ladder.asset_generators.typed_llm import (
    TypedLLMGenerator, register,
)
from services.vocabulary_ladder.config import get_sentence_target

logger = logging.getLogger(__name__)

TASK_NAME = 'ladder_word_family_generation'

MIN_MORPHOLOGICAL_FORMS = 2
REQUIRED_FOILS = 3


@register
class WordFamilyGenerator(TypedLLMGenerator):
    """Generates the ``word_family`` asset for one sense and variant."""

    TYPE_CODE = 'word_family'
    TASK_NAME = TASK_NAME
    LADDER_LEVEL = 4
    SENTENCE_SLOT = 4

    def _supports(self, core_asset: dict) -> bool:
        forms = (core_asset or {}).get('morphological_forms') or []
        if len(forms) < MIN_MORPHOLOGICAL_FORMS:
            return False
        return bool(self.sentences(core_asset))

    def _prompt_vars(
        self, core_asset: dict, sentence_index: int, used_distractors: list[str],
    ) -> dict:
        sentence = self.sentences(core_asset)[sentence_index]
        return {
            'word': self.lemma(core_asset),
            'pos': core_asset.get('pos', ''),
            'semantic_class': core_asset.get('semantic_class', ''),
            'definition': core_asset.get('definition', ''),
            'sense_fingerprint': core_asset.get('sense_fingerprint') or '',
            'register': core_asset.get('register') or 'neutral',
            'complexity_tier': self.tier(core_asset),
            'sentence_text': sentence.get('text', ''),
            'target_word': get_sentence_target(sentence),
            'morphological_forms_json': self.json_dump(
                core_asset.get('morphological_forms') or []
            ),
            'used_distractors_json': self.json_dump(used_distractors),
        }

    def _remap(self, raw: dict, sentence_index: int) -> dict:
        """Indexed output (0=options, 1=stem; option key 3=part_of_speech)
        → descriptive fragment."""
        parts = self.options_to_content(self.option_array(raw))
        return {
            'stem': self.field(raw, '1'),
            'options': parts['options'],
            'correct_answer': parts['correct_text'],
            'explanations': parts['explanations'],
            # Built from the remapped options, so the part-of-speech index is
            # translated exactly once rather than here and in the base class.
            'parts_of_speech': {
                (o.get('text') or ''): (o.get('part_of_speech') or '')
                for o in parts['options']
            },
        }

    # ------------------------------------------------------------------
    # Render
    # ------------------------------------------------------------------

    def render(
        self, db, fragment: dict, core: dict, sense_id: int,
        language_id: int, nl_code: str,
    ) -> dict | None:
        from services.exercise_generation.judges.relation import (
            filter_invented_derivations,
        )
        from services.exercise_generation.schemas import wrap_nl

        correct = (fragment.get('correct_answer') or '').strip()
        stem = (fragment.get('stem') or '').strip()
        if not correct or not stem:
            return None

        foils = [
            (o.get('text') or '').strip()
            for o in fragment.get('options') or []
            if not o.get('is_correct') and (o.get('text') or '').strip()
        ]
        if len(foils) < REQUIRED_FOILS:
            return None

        kept, judge_meta = filter_invented_derivations(
            db, stem, correct, foils, language_id,
            dictionary_check=self._dictionary_probe(core, correct),
        )
        if len(kept) < REQUIRED_FOILS:
            logger.info(
                'word_family: %d/%d foils survived for sense %s; skipping variant',
                len(kept), len(foils), sense_id,
            )
            return None

        sentence_index = fragment.get('sentence_index', 0)
        sentences = core.get('sentences') or []
        sentence_text = (
            sentences[sentence_index].get('text', '')
            if 0 <= sentence_index < len(sentences) else ''
        )
        target = (
            get_sentence_target(sentences[sentence_index])
            if 0 <= sentence_index < len(sentences) else ''
        )
        blanked = sentence_text.replace(target, '___', 1) if target else sentence_text

        options = [correct, *kept[:REQUIRED_FOILS]]
        random.shuffle(options)

        pos_map = fragment.get('parts_of_speech') or {}
        explanations = fragment.get('explanations') or {}
        base = {
            'stem': stem,
            'sentence_with_blank': blanked,
            'original_sentence': sentence_text,
            'required_pos': pos_map.get(correct, ''),
            'options': options,
            'correct_answer': correct,
            '__judge_metas': {'word_family': judge_meta},
        }
        return wrap_nl(
            base, self.TYPE_CODE, nl_code,
            {'explanation': explanations.get(correct, '')},
        )

    # ------------------------------------------------------------------

    @staticmethod
    def _dictionary_probe(core: dict, correct: str):
        """A ``callable(word) -> bool | None`` over what we already know.

        Returns True only for words we can *positively* attest — the sense's
        own morphological forms. Everything else is None ("no opinion") and
        goes to the judge: this corpus has no exhaustive English lexicon, and
        answering False for an unlisted word would let the certain-signal path
        wave through real words it simply had not heard of.
        """
        attested = {
            (form.get('form') or '').strip().casefold()
            for form in (core or {}).get('morphological_forms') or []
            if isinstance(form, dict) and (form.get('form') or '').strip()
        }
        attested.discard((correct or '').strip().casefold())

        def probe(word: str) -> bool | None:
            key = (word or '').strip().casefold()
            return True if key in attested else None

        return probe
