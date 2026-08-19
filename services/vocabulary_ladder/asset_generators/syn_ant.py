# services/vocabulary_ladder/asset_generators/syn_ant.py
"""``synonym_antonym_match`` — sense-anchored relation MCQ (TASK-522, §5 #17).

The learner is shown a word and a relation ("which of these means the same as
X?") and picks from four options. The exercise trains semantic discrimination,
which is why the capability matrix files it at L6.

Everything here exists to defend against one failure: **the foil that is right
for a different sense**. Ask a model for three non-synonyms of *bank* and it
will offer *shore*, which is a perfectly good non-synonym of the financial
sense and a perfectly good synonym of the geographic one. A learner who reads
the second sense answers *shore* and is marked wrong.

Three defences, in increasing cost:

1. **The prompt** carries the sense definition and fingerprint, and asks for
   the relation to *that sense*, never to the spelling.
2. **The embedding band** (``sense_neighbours``) drops foils that are either
   unrelated filler or near-duplicates of the answer. Free, deterministic, and
   silent when the embedding backfill has not run.
3. **The relation judge** rules on each surviving foil.

Only three clean foils are needed. If fewer survive, the variant is skipped —
the same contract the L3 cloze and L5 collocation renderers use, and the right
one: an item with two correct answers is worse than a missing item.
"""

from __future__ import annotations

import logging
import random

from services.vocabulary_ladder.asset_generators.typed_llm import (
    TypedLLMGenerator, register,
)
from services.vocabulary_ladder.config import SEMANTIC_CLASSES, get_sentence_target

logger = logging.getLogger(__name__)

TASK_NAME = 'ladder_syn_ant_generation'

#: Semantic classes with relations worth testing. A concrete noun's "synonym"
#: is usually a hypernym or a regional variant, which teaches the wrong thing;
#: the capability matrix already restricts the rows, and this mirrors it so
#: the generator is safe when driven directly.
ELIGIBLE_CLASSES = frozenset({'abstract', 'action', 'property'})

REQUIRED_FOILS = 3


@register
class SynonymAntonymGenerator(TypedLLMGenerator):
    """Generates the ``synonym_antonym_match`` asset for one sense and variant."""

    TYPE_CODE = 'synonym_antonym_match'
    TASK_NAME = TASK_NAME
    LADDER_LEVEL = 6
    #: Uses the sense definition rather than a sentence, but takes one along
    #: as context so variants A and B can differ in the example shown.
    SENTENCE_SLOT = 6

    def _supports(self, core_asset: dict) -> bool:
        semantic_class = (core_asset or {}).get('semantic_class')
        if semantic_class in SEMANTIC_CLASSES and semantic_class not in ELIGIBLE_CLASSES:
            return False
        # A relation question with no definition to anchor it is exactly the
        # polysemy failure this module exists to avoid.
        return bool((core_asset or {}).get('definition'))

    def _prompt_vars(
        self, core_asset: dict, sentence_index: int, used_distractors: list[str],
    ) -> dict:
        return {
            'word': self.lemma(core_asset),
            'pos': core_asset.get('pos', ''),
            'semantic_class': core_asset.get('semantic_class', ''),
            'definition': core_asset.get('definition', ''),
            'sense_fingerprint': core_asset.get('sense_fingerprint') or '',
            'register': core_asset.get('register') or 'neutral',
            'complexity_tier': self.tier(core_asset),
            'relation': self.relation_for(sentence_index),
            'example_sentence': self.sentence_text(core_asset, sentence_index),
            'used_distractors_json': self.json_dump(used_distractors),
        }

    @staticmethod
    def relation_for(sentence_index: int) -> str:
        """Which relation this variant asks about.

        Variant A draws sentence 3 and variant B sentence 9 (the L6 slots), so
        deriving the relation from the index makes the two variants genuinely
        different questions rather than two samples of the same one.
        """
        return 'synonym' if sentence_index % 2 == 0 else 'antonym'

    def _remap(self, raw: dict, sentence_index: int) -> dict:
        """Indexed output (0=options, 1=relation) → descriptive fragment."""
        parts = self.options_to_content(self.option_array(raw))
        return {
            'relation': self.field(raw, '1'),
            'options': parts['options'],
            'correct_answer': parts['correct_text'],
            'explanations': parts['explanations'],
        }

    # ------------------------------------------------------------------
    # Render
    # ------------------------------------------------------------------

    def render(
        self, db, fragment: dict, core: dict, sense_id: int,
        language_id: int, nl_code: str,
    ) -> dict | None:
        from services.exercise_generation.judges.relation import filter_relation_foils
        from services.exercise_generation.schemas import wrap_nl
        from services.vocabulary_ladder.sense_neighbours import band_check_foils

        correct = (fragment.get('correct_answer') or '').strip()
        relation = fragment.get('relation') or 'synonym'
        if not correct:
            return None

        foils = [
            (o.get('text') or '').strip()
            for o in fragment.get('options') or []
            if not o.get('is_correct') and (o.get('text') or '').strip()
        ]
        if len(foils) < REQUIRED_FOILS:
            return None

        definition = core.get('definition', '')
        sentences = core.get('sentences') or []
        word = get_sentence_target(sentences[0]) if sentences else ''

        # Band check first: free, and it shrinks what the judge is billed for.
        bands = band_check_foils(db, sense_id, language_id, foils)
        in_band = [f for f in foils if bands[f].in_band is not False]
        band_dropped = [f for f in foils if bands[f].in_band is False]
        if band_dropped:
            logger.info(
                'syn_ant: embedding band dropped %s for sense %s (%s)',
                band_dropped, sense_id,
                '; '.join(bands[f].reason for f in band_dropped),
            )

        kept, judge_meta = filter_relation_foils(
            db, word or self.lemma(core), definition, relation, correct,
            in_band, language_id,
        )
        if len(kept) < REQUIRED_FOILS:
            logger.info(
                'syn_ant: %d/%d foils survived for sense %s; skipping variant',
                len(kept), len(foils), sense_id,
            )
            return None

        options = [correct, *kept[:REQUIRED_FOILS]]
        random.shuffle(options)

        explanations = fragment.get('explanations') or {}
        base = {
            'word': word or self.lemma(core),
            'relation': relation,
            'options': options,
            'correct_answer': correct,
            '__judge_metas': {
                'relation': {
                    **judge_meta,
                    'band_rejected': band_dropped,
                    'band_scores': {
                        f: bands[f].similarity for f in foils
                        if bands[f].similarity is not None
                    },
                },
            },
        }
        return wrap_nl(
            base, self.TYPE_CODE, nl_code,
            {
                'word_definition': definition,
                'explanation': explanations.get(correct, ''),
            },
        )
