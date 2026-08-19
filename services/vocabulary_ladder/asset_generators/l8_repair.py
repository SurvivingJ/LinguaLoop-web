# services/vocabulary_ladder/asset_generators/l8_repair.py
"""L8 collocation repair — its own prompt, model and retry (TASK-520).

Split out of the P3 monolith for the reasons in ``_split_base``. L8 is the
other level the audit singled out (B3.4): it is the only P3 level with a hard
*input* precondition — the sense's ``primary_collocate`` must actually occur in
the sentence the item is built from — and the monolith could only express that
by dropping L8 from a shared call after the fact.

Here the precondition is the generator's own gate. ``_sentence_index`` scans
the pool for a sentence that attests the collocate and returns None when none
does, so the level is skipped cleanly instead of producing an exercise whose
blank cannot be cut.

The *semantic* question — is the planted ``error_collocate`` a genuine
non-collocate, or an also-correct answer? — stays with the collocation judge at
render time (``judges/collocation.judge_collocation_repair``). This module only
guarantees the inputs are sound and the shape is right.
"""

from __future__ import annotations

import re

from services.vocabulary_ladder.config import get_sentence_target
from services.vocabulary_ladder.asset_generators._split_base import SplitLevelGenerator

TASK_NAME = 'ladder_l8_collocation_repair_generation'

# Grounding tags from TASK-523. A collocate the corpus confirms is preferred;
# an LLM-asserted one still generates (the judge is the backstop) but is
# recorded so the batch report can show what fraction of L8 rests on evidence.
GROUNDING_CORPUS = 'corpus_validated'
GROUNDING_ASSERTED = 'llm_asserted'


def whole_word_match(text: str, word: str) -> bool:
    """Whether ``word`` occurs as a whole word in ``text`` (case-insensitive).

    Word boundaries only apply to ASCII: CJK has no spaces, so a contiguous
    substring is the best available test there — the same compromise
    ``validators.contains_target_whole_word`` makes.
    """
    if not text or not word:
        return False
    if not word.isascii():
        return word in text
    return re.search(rf'\b{re.escape(word)}\b', text, re.IGNORECASE) is not None


class CollocationRepairGenerator(SplitLevelGenerator):
    """Generates the L8 collocation-repair asset for one sense and variant."""

    TASK_NAME = TASK_NAME
    LEVEL = 8
    TYPE_CODE = 'collocation_repair'

    @staticmethod
    def collocate(core_asset: dict) -> str:
        """The sense's primary collocate, or '' when P1 declined to name one.

        P1 writes the literal string ``"null"`` when it has no collocate for a
        sense — a JSON-mode artefact that predates this generator and is
        cheaper to absorb here than to chase through the prompt corpus.
        """
        value = ((core_asset or {}).get('primary_collocate') or '').strip()
        return '' if value.lower() == 'null' else value

    def _sentence_index(
        self, core_asset: dict, sentence_assignments: dict[int, int],
    ) -> int | None:
        """A sentence that actually attests the collocate, or None.

        Prefers the variant's assigned index so A and B differ, then scans the
        rest of the pool. Returning None is the correct outcome for a sense
        whose collocate never co-occurs with it in the generated sentences —
        better no L8 than an L8 whose error word cannot be substituted in.
        """
        collocate = self.collocate(core_asset)
        if not collocate:
            return None

        sentences = self.sentences(core_asset)
        if not sentences:
            return None

        preferred = sentence_assignments.get(8, 4)
        order = [preferred] + [i for i in range(len(sentences)) if i != preferred]
        for index in order:
            if not (0 <= index < len(sentences)):
                continue
            if whole_word_match(sentences[index].get('text', ''), collocate):
                return index
        return None

    def _prompt_vars(
        self, core_asset: dict, sentence_index: int, used_distractors: list[str],
    ) -> dict:
        sentence = self.sentences(core_asset)[sentence_index]
        grounding = (core_asset or {}).get('collocate_grounding') or {}
        return {
            'word': self.lemma(core_asset),
            'pos': core_asset.get('pos', ''),
            'semantic_class': core_asset.get('semantic_class', ''),
            'definition': core_asset.get('definition', ''),
            'register': core_asset.get('register') or 'neutral',
            'sense_fingerprint': core_asset.get('sense_fingerprint') or '',
            'complexity_tier': self.tier(core_asset),
            'sentence_text': sentence.get('text', ''),
            'target_word': get_sentence_target(sentence) or self.lemma(core_asset),
            'primary_collocate': self.collocate(core_asset),
            'collocate_grounding': grounding.get('status') or GROUNDING_ASSERTED,
            'used_distractors_json': self.json_dump(used_distractors),
        }

    def _remap(self, raw: dict, sentence_index: int) -> dict:
        """Schema-valid output → the level_8 dict the renderer reads.

        Reads the numeric contract (0=options, 1=error_collocate) and emits
        descriptive keys. The schema has already established four well-formed
        options with one correct, and a non-empty error collocate distinct from
        all of them, so none of the monolith's shape-guessing branches survive
        here.
        """
        parts = self.options_to_content(self.option_array(raw))
        return {
            'options': parts['options'],
            'correct_collocate': parts['correct_text'],
            'error_collocate': self.field(raw, '1'),
            # Ours, not the model's: this is the index we verified attests the
            # collocate, and the renderer substitutes into that exact sentence.
            'sentence_index': sentence_index,
            'explanations': parts['explanations'],
        }
