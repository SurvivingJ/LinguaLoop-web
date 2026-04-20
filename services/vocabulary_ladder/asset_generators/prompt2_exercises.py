# services/vocabulary_ladder/asset_generators/prompt2_exercises.py
"""
Prompt 2: Lexical & Semantic Exercise Generator

Calls configurable model (default Claude Sonnet) to generate exercise content
for levels 1 (phonetic), 3 (cloze), 5 (collocation gap), and 6 (semantic
discrimination). Single LLM call for all included levels.

Only includes instructions for active levels — if L5 is skipped for a
concrete noun, the prompt simply omits Level 5 entirely.
"""

import json
import logging

from config import Config
from services.llm_service import call_llm
from services.vocabulary_ladder.config import (
    PROMPT2_LEVELS, OPTION_KEY_MAP, DEFAULT_SENTENCE_ASSIGNMENTS,
    SENTENCE_ASSIGNMENTS_A, remap_keys,
)

logger = logging.getLogger(__name__)


class ExerciseAssetGenerator:
    """Generates Prompt 2 assets: phonetic, cloze, collocation gap, semantic."""

    def __init__(self, db, language_id: int, model: str | None = None):
        self.db = db
        self.language_id = language_id
        self.model = model or Config.VOCAB_PIPELINE_MODELS['prompt2']

    def generate(
        self,
        sense_id: int,
        core_asset: dict,
        active_levels: list[int],
        sentence_assignments: dict[int, int] | None = None,
    ) -> dict | None:
        """Generate exercise assets for Prompt 2 levels.

        Args:
            sense_id: The dim_word_senses ID.
            core_asset: Output from Prompt 1 (descriptive keys).
            active_levels: Which ladder levels are active for this word.
            sentence_assignments: Map of level → sentence index to use.
                Defaults to SENTENCE_ASSIGNMENTS_A for backward compat.

        Returns:
            Descriptive-keyed dict with level_1, level_3, level_5, level_6 keys,
            or None on failure.
        """
        if sentence_assignments is None:
            sentence_assignments = SENTENCE_ASSIGNMENTS_A

        # Filter to only P2 levels that are active
        p2_active = sorted(lv for lv in active_levels if lv in PROMPT2_LEVELS)
        if not p2_active:
            logger.warning("No Prompt 2 levels active for sense %s", sense_id)
            return {}

        prompt_text = self._build_prompt(core_asset, p2_active, sentence_assignments)

        try:
            raw = call_llm(
                prompt_text,
                model=self.model,
                temperature=0.4,
                response_format='json',
            )
        except Exception as e:
            logger.error("Prompt 2 LLM call failed for sense %s: %s", sense_id, e)
            return None

        return self._remap_output(raw, p2_active, sentence_assignments)

    def _build_prompt(
        self, core_asset: dict, active_levels: list[int],
        sentence_assignments: dict[int, int],
    ) -> str:
        """Load prompt template and fill variables."""
        template = self._load_template()

        sentences = core_asset.get('sentences', [])
        sentences_json = json.dumps(
            [{'index': i, 'text': s.get('text', ''), 'target': s.get('target_substring', '')}
             for i, s in enumerate(sentences)],
            ensure_ascii=False,
        )

        return template.format(
            word=self._extract_lemma(core_asset),
            pos=core_asset.get('pos', ''),
            semantic_class=core_asset.get('semantic_class', ''),
            complexity_tier=self._extract_tier(core_asset),
            definition=core_asset.get('definition', ''),
            primary_collocate=core_asset.get('primary_collocate') or 'null',
            sentences_json=sentences_json,
            active_levels_json=json.dumps([str(lv) for lv in active_levels]),
            level_3_sentence_index=sentence_assignments.get(3, 0),
            level_5_sentence_index=sentence_assignments.get(5, 2),
            level_6_sentence_index=sentence_assignments.get(6, 3),
        )

    def _load_template(self) -> str:
        """Fetch the active prompt template."""
        try:
            resp = (
                self.db.table('prompt_templates')
                .select('template_text')
                .eq('task_name', 'vocab_prompt2_exercises')
                .eq('language_id', self.language_id)
                .eq('is_active', True)
                .order('version', desc=True)
                .limit(1)
                .execute()
            )
            if resp.data:
                return resp.data[0]['template_text']
        except Exception as e:
            logger.error("Failed to load prompt2 template: %s", e)

        raise RuntimeError("No active vocab_prompt2_exercises template found")

    def _remap_output(
        self, raw: dict, active_levels: list[int],
        sentence_assignments: dict[int, int],
    ) -> dict:
        """Transform numeric-keyed LLM output to descriptive level keys."""
        result = {}

        for level in active_levels:
            level_key = str(level)
            if level_key not in raw:
                logger.warning("Prompt 2 missing level %s in output", level)
                continue

            level_data = raw[level_key]

            if level == 6:
                result[f'level_{level}'] = self._remap_level_6(
                    level_data, sentence_assignments)
            else:
                if isinstance(level_data, list):
                    result[f'level_{level}'] = self._remap_options(
                        level_data, level, sentence_assignments)
                else:
                    result[f'level_{level}'] = level_data

        return result

    def _remap_options(
        self, options: list, level: int,
        sentence_assignments: dict[int, int],
    ) -> dict:
        """Remap a list of option objects for L1, L3, L5."""
        remapped = [remap_keys(opt, OPTION_KEY_MAP) for opt in options]

        correct = [o for o in remapped if o.get('is_correct')]

        explanations = {}
        for opt in remapped:
            text = opt.get('text', '')
            if text:
                explanations[text] = opt.get('explanation', '')

        result = {
            'options': remapped,
            'explanations': explanations,
            'sentence_index': sentence_assignments.get(level),
        }

        if correct:
            result['correct_answer'] = correct[0].get('text', '')
        if level == 5 and correct:
            result['correct_collocate'] = correct[0].get('text', '')

        return result

    def _remap_level_6(
        self, level_data: dict | list,
        sentence_assignments: dict[int, int],
    ) -> dict:
        """Remap Level 6 semantic discrimination output."""
        if isinstance(level_data, dict):
            correct_idx = level_data.get('1', sentence_assignments.get(6, 3))
            wrong_sentences = level_data.get('2', [])
            if isinstance(wrong_sentences, list):
                wrong_sentences = [
                    {'text': s.get('1', ''), 'explanation': s.get('2', '')}
                    if isinstance(s, dict) else s
                    for s in wrong_sentences
                ]
            return {
                'correct_sentence_index': correct_idx,
                'wrong_sentences': wrong_sentences,
            }
        return {'correct_sentence_index': sentence_assignments.get(6, 3), 'wrong_sentences': []}

    def _extract_lemma(self, core_asset: dict) -> str:
        """Extract the word text from core asset sentences."""
        sentences = core_asset.get('sentences', [])
        if sentences:
            return sentences[0].get('target_substring', '')
        return ''

    def _extract_tier(self, core_asset: dict) -> str:
        """Extract complexity tier from first sentence or default."""
        sentences = core_asset.get('sentences', [])
        if sentences:
            return sentences[0].get('complexity_tier', 'T3')
        return 'T3'
