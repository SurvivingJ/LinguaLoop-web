# services/vocabulary_ladder/asset_generators/prompt1_core.py
"""
Prompt 1: Core Asset Generator

Calls configurable model (default Gemini Flash) to classify a word and
generate base assets: POS, semantic class, definition, pronunciation, IPA,
morphological forms, and 6 example sentences (corpus-first, generate rest).

This is the foundation — Prompts 2 and 3 depend on the output of Prompt 1.
"""

import json
import logging
from typing import Optional

from config import Config
from services.llm_service import call_llm
from services.vocabulary_ladder.config import (
    PROMPT1_KEY_MAP, SENTENCE_KEY_MAP, MORPH_FORM_KEY_MAP, remap_keys,
)

logger = logging.getLogger(__name__)


class CoreAssetGenerator:
    """Generates Prompt 1 assets: classification, definition, sentences."""

    def __init__(self, db, language_id: int, model: str | None = None):
        self.db = db
        self.language_id = language_id
        self.model = model or Config.VOCAB_PIPELINE_MODELS['prompt1']

    def generate(
        self,
        sense_id: int,
        corpus_sentences: list[dict],
    ) -> dict | None:
        """Generate core assets for a word sense.

        Args:
            sense_id: The dim_word_senses ID.
            corpus_sentences: Pre-existing sentences from tests/conversations.
                Each dict has keys: text, target_substring, source, complexity_tier.

        Returns:
            Descriptive-keyed dict ready for word_assets storage, or None on failure.
        """
        # Load word metadata from DB
        word_data = self._load_word_data(sense_id)
        if not word_data:
            logger.error("Cannot load word data for sense_id=%s", sense_id)
            return None

        lemma = word_data['lemma']
        existing_def = word_data.get('definition', '')
        complexity_tier = word_data.get('complexity_tier', 'T3')

        # Determine how many sentences to generate
        sentences_needed = max(0, Config.VOCAB_SENTENCES_PER_WORD - len(corpus_sentences))

        # Build and send prompt
        prompt_text = self._build_prompt(
            lemma, existing_def, complexity_tier,
            corpus_sentences, sentences_needed,
        )

        try:
            raw = call_llm(
                prompt_text,
                model=self.model,
                temperature=0.3,
                response_format='json',
            )
        except Exception as e:
            logger.error("Prompt 1 LLM call failed for '%s': %s", lemma, e)
            return None

        # Remap numeric keys to descriptive
        content = self._remap_output(raw)
        if content is None:
            logger.error("Prompt 1 key remapping failed for '%s'", lemma)
            return None

        return content

    def _load_word_data(self, sense_id: int) -> dict | None:
        """Fetch lemma, definition, and tier from DB."""
        try:
            resp = (
                self.db.table('dim_word_senses')
                .select('id, definition, pronunciation, vocab_id, '
                        'dim_vocabulary(lemma, part_of_speech, level_tag)')
                .eq('id', sense_id)
                .single()
                .execute()
            )
            row = resp.data
            if not row:
                return None

            vocab = row.get('dim_vocabulary') or {}
            return {
                'sense_id': sense_id,
                'lemma': vocab.get('lemma', ''),
                'pos': vocab.get('part_of_speech', ''),
                'definition': row.get('definition', ''),
                'pronunciation': row.get('pronunciation', ''),
                'complexity_tier': vocab.get('level_tag') or 'T3',
            }
        except Exception as e:
            logger.error("DB lookup failed for sense %s: %s", sense_id, e)
            return None

    def _build_prompt(
        self,
        lemma: str,
        existing_definition: str,
        complexity_tier: str,
        corpus_sentences: list[dict],
        sentences_needed: int,
    ) -> str:
        """Load prompt template and fill variables."""
        template = self._load_template()

        corpus_json = json.dumps(
            [{'1': s['text'], '2': s['target_substring']}
             for s in corpus_sentences],
            ensure_ascii=False,
        ) if corpus_sentences else '[]'

        return template.format(
            word=lemma,
            existing_definition=existing_definition or 'None provided',
            complexity_tier=complexity_tier,
            corpus_sentences_json=corpus_json,
            sentences_needed=sentences_needed,
        )

    def _load_template(self) -> str:
        """Fetch the active prompt template from the database."""
        try:
            resp = (
                self.db.table('prompt_templates')
                .select('template_text')
                .eq('task_name', 'vocab_prompt1_core')
                .eq('language_id', self.language_id)
                .eq('is_active', True)
                .order('version', desc=True)
                .limit(1)
                .execute()
            )
            if resp.data:
                return resp.data[0]['template_text']
        except Exception as e:
            logger.error("Failed to load prompt1 template: %s", e)

        raise RuntimeError("No active vocab_prompt1_core template found")

    def _remap_output(self, raw: dict) -> dict | None:
        """Transform numeric-keyed LLM output to descriptive keys."""
        try:
            content = {}
            for num_key, desc_key in PROMPT1_KEY_MAP.items():
                if num_key in raw:
                    content[desc_key] = raw[num_key]

            # Remap nested sentence objects
            if 'sentences' in content and isinstance(content['sentences'], list):
                content['sentences'] = [
                    remap_keys(s, SENTENCE_KEY_MAP)
                    if isinstance(s, dict) else s
                    for s in content['sentences']
                ]

            # Remap nested morphological form objects
            if 'morphological_forms' in content and isinstance(content['morphological_forms'], list):
                content['morphological_forms'] = [
                    remap_keys(f, MORPH_FORM_KEY_MAP)
                    if isinstance(f, dict) else f
                    for f in content['morphological_forms']
                ]

            # Ensure syllable_count is int
            if 'syllable_count' in content:
                content['syllable_count'] = int(content['syllable_count'])

            return content

        except Exception as e:
            logger.error("Prompt 1 output remapping error: %s", e)
            return None
