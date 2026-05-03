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
from services.prompt_service import get_template_config
from services.vocabulary_ladder.config import (
    PROMPT2_LEVELS, OPTION_KEY_MAP, DEFAULT_SENTENCE_ASSIGNMENTS,
    SENTENCE_ASSIGNMENTS_A, get_sentence_target, remap_keys,
)
from services.vocabulary_ladder.asset_generators._renderer import render_template

logger = logging.getLogger(__name__)

TASK_NAME = 'vocab_prompt2_exercises'


class ExerciseAssetGenerator:
    """Generates Prompt 2 assets: phonetic, cloze, collocation gap, semantic."""

    def __init__(self, db, language_id: int):
        self.db = db
        self.language_id = language_id
        self._cfg: dict | None = None

    @property
    def model(self) -> str:
        if self._cfg is None:
            self._cfg = get_template_config(self.db, TASK_NAME, self.language_id)
        return self._cfg['model']

    def generate(
        self,
        sense_id: int,
        core_asset: dict,
        active_levels: list[int],
        sentence_assignments: dict[int, int] | None = None,
        used_distractors: list[str] | None = None,
    ) -> dict | None:
        """Generate exercise assets for Prompt 2 levels.

        Args:
            sense_id: The dim_word_senses ID.
            core_asset: Output from Prompt 1 (descriptive keys).
            active_levels: Which ladder levels are active for this word.
            sentence_assignments: Map of level → sentence index to use.
                Defaults to SENTENCE_ASSIGNMENTS_A for backward compat.
            used_distractors: Distractor texts already assigned elsewhere in
                this item set; passed to the LLM so it doesn't repeat them.
                Defaults to [].

        Returns:
            Descriptive-keyed dict with level_1, level_3, level_5, level_6 keys,
            or None on failure.
        """
        if sentence_assignments is None:
            sentence_assignments = SENTENCE_ASSIGNMENTS_A
        if used_distractors is None:
            used_distractors = []

        # Filter to only P2 levels that are active
        p2_active = sorted(lv for lv in active_levels if lv in PROMPT2_LEVELS)
        if not p2_active:
            logger.warning("No Prompt 2 levels active for sense %s", sense_id)
            return {}

        prompt_text = self._build_prompt(
            core_asset, p2_active, sentence_assignments, used_distractors,
        )
        cfg = self._cfg

        raw = self._call_with_retry(prompt_text, cfg, p2_active, sense_id)
        if raw is None:
            return None

        return self._remap_output(raw, p2_active, sentence_assignments)

    def _call_with_retry(
        self, prompt_text: str, cfg: dict, p2_active: list[int], sense_id: int,
    ) -> dict | None:
        """Single LLM call, retry once if any active level is missing or call fails."""
        for attempt in (1, 2):
            try:
                raw = call_llm(
                    prompt_text,
                    model=cfg['model'],
                    provider=cfg['provider'],
                    temperature=0.4,
                    max_tokens=8192,
                    response_format='json',
                )
            except Exception as e:
                logger.warning(
                    "Prompt 2 LLM call attempt %d failed for sense %s: %s",
                    attempt, sense_id, e,
                )
                if attempt == 2:
                    logger.error("Prompt 2 gave up for sense %s after 2 attempts", sense_id)
                    return None
                continue

            missing = [lv for lv in p2_active if str(lv) not in (raw or {})]
            if not missing:
                return raw
            if attempt == 1:
                logger.warning(
                    "Prompt 2 missing levels %s for sense %s — retrying once",
                    missing, sense_id,
                )
            else:
                logger.error(
                    "Prompt 2 still missing levels %s for sense %s after retry — accepting partial",
                    missing, sense_id,
                )
                return raw
        return None

    def _build_prompt(
        self, core_asset: dict, active_levels: list[int],
        sentence_assignments: dict[int, int],
        used_distractors: list[str],
    ) -> str:
        """Load prompt template and fill variables."""
        template = self._load_template()

        sentences = core_asset.get('sentences', [])
        sentences_json = json.dumps(
            [{'index': i, 'text': s.get('text', ''), 'target': get_sentence_target(s)}
             for i, s in enumerate(sentences)],
            ensure_ascii=False,
        )

        return render_template(
            template,
            word=self._extract_lemma(core_asset),
            pos=core_asset.get('pos', ''),
            semantic_class=core_asset.get('semantic_class', ''),
            complexity_tier=self._extract_tier(core_asset),
            definition=core_asset.get('definition', ''),
            primary_collocate=core_asset.get('primary_collocate') or 'null',
            register=core_asset.get('register') or 'neutral',
            sense_fingerprint=core_asset.get('sense_fingerprint') or '',
            sentences_json=sentences_json,
            active_levels_json=json.dumps([str(lv) for lv in active_levels]),
            used_distractors_json=json.dumps(used_distractors, ensure_ascii=False),
            level_3_sentence_index=sentence_assignments.get(3, 0),
            level_5_sentence_index=sentence_assignments.get(5, 2),
            level_6_sentence_index=sentence_assignments.get(6, 3),
        )

    def _load_template(self) -> str:
        """Fetch the active prompt template from the database (Supabase-driven)."""
        if self._cfg is None:
            self._cfg = get_template_config(self.db, TASK_NAME, self.language_id)
        return self._cfg['template']

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
            return get_sentence_target(sentences[0])
        return ''

    def _extract_tier(self, core_asset: dict) -> str:
        """Extract complexity tier from first sentence or default."""
        sentences = core_asset.get('sentences', [])
        if sentences:
            return sentences[0].get('complexity_tier', 'T3')
        return 'T3'
