# services/vocabulary_ladder/asset_generators/prompt3_transforms.py
"""
Prompt 3: Grammar & Structure Exercise Generator

Calls configurable model (default Claude Sonnet) to generate exercise content
for levels 4 (morphology slot), 7 (spot incorrect sentence), and 8 (collocation
repair). Single LLM call for all included levels.
"""

import json
import logging

from config import Config
from services.llm_service import call_llm
from services.vocabulary_ladder.config import (
    PROMPT3_LEVELS, OPTION_KEY_MAP, DEFAULT_SENTENCE_ASSIGNMENTS,
    SENTENCE_ASSIGNMENTS_A, L7_CORRECT_INDICES_A, remap_keys,
)

logger = logging.getLogger(__name__)


class TransformAssetGenerator:
    """Generates Prompt 3 assets: morphology, spot-incorrect, collocation repair."""

    def __init__(self, db, language_id: int, model: str | None = None):
        self.db = db
        self.language_id = language_id
        self.model = model or Config.VOCAB_PIPELINE_MODELS['prompt3']

    def generate(
        self,
        sense_id: int,
        core_asset: dict,
        active_levels: list[int],
        sentence_assignments: dict[int, int] | None = None,
        l7_correct_indices: list[int] | None = None,
    ) -> dict | None:
        """Generate exercise assets for Prompt 3 levels.

        Args:
            sense_id: The dim_word_senses ID.
            core_asset: Output from Prompt 1 (descriptive keys).
            active_levels: Which ladder levels are active for this word.
            sentence_assignments: Map of level → sentence index.
                Defaults to SENTENCE_ASSIGNMENTS_A.
            l7_correct_indices: Sentence indices for L7 correct sentences.
                Defaults to L7_CORRECT_INDICES_A.

        Returns:
            Descriptive-keyed dict with level_4, level_7, level_8 keys,
            or None on failure.
        """
        if sentence_assignments is None:
            sentence_assignments = SENTENCE_ASSIGNMENTS_A
        if l7_correct_indices is None:
            l7_correct_indices = L7_CORRECT_INDICES_A

        p3_active = sorted(lv for lv in active_levels if lv in PROMPT3_LEVELS)
        if not p3_active:
            logger.warning("No Prompt 3 levels active for sense %s", sense_id)
            return {}

        prompt_text = self._build_prompt(
            core_asset, p3_active, sentence_assignments, l7_correct_indices)

        try:
            raw = call_llm(
                prompt_text,
                model=self.model,
                temperature=0.4,
                response_format='json',
            )
        except Exception as e:
            logger.error("Prompt 3 LLM call failed for sense %s: %s", sense_id, e)
            return None

        return self._remap_output(raw, p3_active, sentence_assignments)

    def _build_prompt(
        self, core_asset: dict, active_levels: list[int],
        sentence_assignments: dict[int, int],
        l7_correct_indices: list[int],
    ) -> str:
        """Load prompt template and fill variables."""
        template = self._load_template()

        sentences = core_asset.get('sentences', [])
        sentences_json = json.dumps(
            [{'index': i, 'text': s.get('text', ''), 'target': s.get('target_substring', '')}
             for i, s in enumerate(sentences)],
            ensure_ascii=False,
        )

        morphological_forms = core_asset.get('morphological_forms', [])
        morph_json = json.dumps(morphological_forms, ensure_ascii=False)

        return template.format(
            word=self._extract_lemma(core_asset),
            pos=core_asset.get('pos', ''),
            semantic_class=core_asset.get('semantic_class', ''),
            complexity_tier=self._extract_tier(core_asset),
            primary_collocate=core_asset.get('primary_collocate') or 'null',
            sentences_json=sentences_json,
            morphological_forms_json=morph_json,
            active_levels_json=json.dumps([str(lv) for lv in active_levels]),
            level_4_sentence_index=sentence_assignments.get(4, 1),
            level_7_correct_indices=json.dumps(l7_correct_indices),
            level_8_sentence_index=sentence_assignments.get(8, 4),
        )

    def _load_template(self) -> str:
        """Fetch the active prompt template."""
        try:
            resp = (
                self.db.table('prompt_templates')
                .select('template_text')
                .eq('task_name', 'vocab_prompt3_transforms')
                .eq('language_id', self.language_id)
                .eq('is_active', True)
                .order('version', desc=True)
                .limit(1)
                .execute()
            )
            if resp.data:
                return resp.data[0]['template_text']
        except Exception as e:
            logger.error("Failed to load prompt3 template: %s", e)

        raise RuntimeError("No active vocab_prompt3_transforms template found")

    def _remap_output(
        self, raw: dict, active_levels: list[int],
        sentence_assignments: dict[int, int],
    ) -> dict:
        """Transform numeric-keyed LLM output to descriptive level keys."""
        result = {}

        for level in active_levels:
            level_key = str(level)
            if level_key not in raw:
                logger.warning("Prompt 3 missing level %s in output", level)
                continue

            level_data = raw[level_key]

            if level == 4:
                result['level_4'] = self._remap_level_4(level_data, sentence_assignments)
            elif level == 7:
                result['level_7'] = self._remap_level_7(level_data)
            elif level == 8:
                result['level_8'] = self._remap_level_8(level_data, sentence_assignments)

        return result

    def _remap_level_4(self, data: dict | list, sentence_assignments: dict[int, int]) -> dict:
        """Remap Level 4 morphology slot output."""
        if isinstance(data, list):
            options = [remap_keys(opt, OPTION_KEY_MAP) for opt in data]
            correct = [o for o in options if o.get('is_correct')]
            explanations = {o.get('text', ''): o.get('explanation', '') for o in options}

            return {
                'options': options,
                'correct_form': correct[0].get('text', '') if correct else '',
                'explanations': explanations,
                'sentence_index': sentence_assignments.get(4, 1),
                'base_form': data.get('4', '') if isinstance(data, dict) else '',
                'form_label': data.get('5', '') if isinstance(data, dict) else '',
            }

        if isinstance(data, dict):
            options = []
            if isinstance(data.get('options'), list):
                options = [remap_keys(o, OPTION_KEY_MAP) for o in data['options']]
            elif any(isinstance(data.get(str(i)), dict) for i in range(4)):
                options = [remap_keys(data[str(i)], OPTION_KEY_MAP) for i in range(4) if str(i) in data]

            correct = [o for o in options if o.get('is_correct')]
            explanations = {o.get('text', ''): o.get('explanation', '') for o in options}

            return {
                'options': options,
                'correct_form': correct[0].get('text', '') if correct else '',
                'base_form': data.get('4', ''),
                'form_label': data.get('5', ''),
                'sentence_index': int(data.get('6', sentence_assignments.get(4, 1))),
                'explanations': explanations,
            }

        return {}

    def _remap_level_7(self, data: dict) -> dict:
        """Remap Level 7 spot-incorrect sentence output."""
        if not isinstance(data, dict):
            return {}

        return {
            'incorrect_sentence': data.get('1', ''),
            'corrected_sentence': data.get('2', ''),
            'error_description': data.get('3', ''),
            'correct_sentence_indices': data.get('4', [0, 1, 2]),
        }

    def _remap_level_8(self, data: dict | list, sentence_assignments: dict[int, int]) -> dict:
        """Remap Level 8 collocation repair output."""
        if isinstance(data, list):
            options = [remap_keys(opt, OPTION_KEY_MAP) for opt in data]
            correct = [o for o in options if o.get('is_correct')]
            explanations = {o.get('text', ''): o.get('explanation', '') for o in options}

            return {
                'options': options,
                'correct_collocate': correct[0].get('text', '') if correct else '',
                'explanations': explanations,
                'sentence_index': sentence_assignments.get(8, 4),
            }

        if isinstance(data, dict):
            options = []
            if isinstance(data.get('options'), list):
                options = [remap_keys(o, OPTION_KEY_MAP) for o in data['options']]

            correct = [o for o in options if o.get('is_correct')]
            return {
                'options': options,
                'correct_collocate': correct[0].get('text', '') if correct else '',
                'error_collocate': data.get('5', ''),
                'sentence_index': int(data.get('4', sentence_assignments.get(8, 4))),
                'explanations': {o.get('text', ''): o.get('explanation', '') for o in options},
            }

        return {}

    def _extract_lemma(self, core_asset: dict) -> str:
        sentences = core_asset.get('sentences', [])
        if sentences:
            return sentences[0].get('target_substring', '')
        return ''

    def _extract_tier(self, core_asset: dict) -> str:
        sentences = core_asset.get('sentences', [])
        if sentences:
            return sentences[0].get('complexity_tier', 'T3')
        return 'T3'
