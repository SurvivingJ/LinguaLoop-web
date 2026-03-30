"""
LLM-based Phrase Detection Service

Calls the LLM to identify multi-word expressions (phrasal verbs,
compound nouns, collocations, idioms) from a lemma list.

Only runs when NLPMetadata.phrase_detection_enabled is True.
Uses the 'vocab_phrase_detection' prompt from prompt_templates table.
"""

import json
import logging
from typing import Optional

from services.vocabulary.processors.base import LemmaToken

logger = logging.getLogger(__name__)


class PhraseDetector:
    """
    Detects multi-word expressions via LLM.

    Returns phrases in format:
        [{"phrase": "throw up", "components": ["throw", "up"], "phrase_type": "phrasal_verb"}]
    """

    def __init__(self, openai_client, db_client):
        """
        Args:
            openai_client: OpenAI client instance (direct or via OpenRouter)
            db_client: TestDatabaseClient for loading prompt templates
        """
        self._client = openai_client
        self._db = db_client

    def detect(
        self,
        lemma_tokens: list[LemmaToken],
        original_text: str,
        language_id: int,
        model: str,
    ) -> list[dict]:
        """
        Detect phrases in lemma list.

        Args:
            lemma_tokens: All lemmas from processor
            original_text: Original raw text (for LLM context)
            language_id: Language ID for prompt lookup
            model: LLM model to use (from LanguageConfig.prose_model)

        Returns:
            List of phrase dicts, or empty list on failure
        """
        template = self._db.get_prompt_template(
            'vocab_phrase_detection',
            language_id,
        )

        if not template:
            logger.warning(
                f"No vocab_phrase_detection prompt for language_id={language_id}. "
                f"Skipping phrase detection."
            )
            return []

        lemma_list = " | ".join(t.lemma for t in lemma_tokens)

        try:
            prompt = template.format(
                lemma_list=lemma_list,
                original_text=original_text,
            )
        except KeyError as e:
            logger.error(f"Prompt template missing variable: {e}")
            return []

        try:
            response = self._client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=1200,
                response_format={"type": "json_object"},
            )

            if not response.choices:
                logger.error("Phrase detection returned no choices")
                return []

            raw = response.choices[0].message.content
            if not raw:
                logger.error("Phrase detection returned empty content")
                return []

            data = json.loads(self._clean_json(raw))
            phrases = data.get("phrases", [])

            if not isinstance(phrases, list):
                logger.error(f"Expected 'phrases' to be a list, got {type(phrases)}")
                return []

            # Validate structure of each phrase
            valid = []
            for p in phrases:
                if (
                    isinstance(p, dict)
                    and isinstance(p.get("phrase"), str)
                    and isinstance(p.get("components"), list)
                    and len(p["components"]) >= 2
                ):
                    valid.append(p)

            return valid

        except json.JSONDecodeError as e:
            logger.error(f"Phrase detection JSON parse error: {e}")
            return []
        except Exception as e:
            logger.error(f"Phrase detection failed: {e}")
            return []

    @staticmethod
    def _clean_json(content: str) -> str:
        """Strip markdown code fences from LLM response."""
        from services.llm_output_cleaner import clean_json_response
        return clean_json_response(content)
