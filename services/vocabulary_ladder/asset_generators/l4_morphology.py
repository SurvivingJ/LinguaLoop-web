# services/vocabulary_ladder/asset_generators/l4_morphology.py
"""L4 morphology slot — its own prompt, model and retry (TASK-520).

Split out of the P3 monolith. L4 is the level most sensitive to the model's
grammatical knowledge of the target language: it asks for real inflected forms
of a lemma and three wrong-but-plausible forms alongside them. Sharing a
``task_name`` with spot-incorrect meant sharing a model chosen for a much
easier judgement, and sharing a retry meant a missing morphology block cost a
regeneration of two other levels.

The prompt now sees ONE sentence rather than the whole pool, which is also why
``sentence_index`` is authoritative on our side: the model is answering about a
specific blank, so letting it nominate a different index (as the monolith's
remap did, via numeric key ``"6"``) could only ever point the renderer at a
sentence the model never read.
"""

from __future__ import annotations

from services.vocabulary_ladder.config import get_sentence_target
from services.vocabulary_ladder.asset_generators._split_base import SplitLevelGenerator

TASK_NAME = 'ladder_l4_morphology_generation'

# The capability row for morphology_slot requires morph_forms>=2. Re-checked
# here because the generator can also be driven directly (queue drain, admin
# regen of a single level) without going through the pipeline's planning gate.
MIN_MORPHOLOGICAL_FORMS = 2


class MorphologySlotGenerator(SplitLevelGenerator):
    """Generates the L4 morphology-slot asset for one sense and variant."""

    TASK_NAME = TASK_NAME
    LEVEL = 4
    TYPE_CODE = 'morphology_slot'

    def _sentence_index(
        self, core_asset: dict, sentence_assignments: dict[int, int],
    ) -> int | None:
        """The variant's assigned sentence, if the sense can support L4 at all."""
        forms = (core_asset or {}).get('morphological_forms') or []
        if len(forms) < MIN_MORPHOLOGICAL_FORMS:
            return None

        sentences = self.sentences(core_asset)
        if not sentences:
            return None

        index = sentence_assignments.get(4, 1)
        if index >= len(sentences):
            index = len(sentences) - 1
        if index < 0:
            return None

        # The renderer cuts the blank by replacing the target in the sentence,
        # so a sentence with no recorded target is unusable however well the
        # model answers.
        if not get_sentence_target(sentences[index]):
            return None
        return index

    def _prompt_vars(
        self, core_asset: dict, sentence_index: int, used_distractors: list[str],
    ) -> dict:
        sentence = self.sentences(core_asset)[sentence_index]
        return {
            'word': self.lemma(core_asset),
            'pos': core_asset.get('pos', ''),
            'semantic_class': core_asset.get('semantic_class', ''),
            'definition': core_asset.get('definition', ''),
            'register': core_asset.get('register') or 'neutral',
            'sense_fingerprint': core_asset.get('sense_fingerprint') or '',
            'complexity_tier': self.tier(core_asset),
            'sentence_text': sentence.get('text', ''),
            'target_word': get_sentence_target(sentence),
            'morphological_forms_json': self.json_dump(
                core_asset.get('morphological_forms') or []
            ),
            'used_distractors_json': self.json_dump(used_distractors),
        }

    def _remap(self, raw: dict, sentence_index: int) -> dict:
        """Schema-valid output → the level_4 dict the renderer reads.

        Reads the numeric contract (0=options, 1=base_form, 2=form_label) and
        emits descriptive keys. No shape guessing: the schema gate has already
        established that key 0 is a four-entry array with exactly one correct
        entry, and that keys 1 and 2 are non-empty strings.
        """
        parts = self.options_to_content(self.option_array(raw))
        return {
            'options': parts['options'],
            'correct_form': parts['correct_text'],
            'base_form': self.field(raw, '1'),
            'form_label': self.field(raw, '2'),
            # Ours, not the model's — see the module docstring.
            'sentence_index': sentence_index,
            'explanations': parts['explanations'],
        }
