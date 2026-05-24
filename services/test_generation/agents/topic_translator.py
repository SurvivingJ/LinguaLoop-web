"""
Topic Translator Agent

Translates topic concepts and keywords to target language before prose generation.
This ensures prompts are in the target language for non-English content.
Routes through the unified llm_service so calls are logged to llm_calls.
"""

import logging
from typing import List, Tuple, Optional

from pydantic import ValidationError

from services.llm_service import call_llm

from ..config import test_gen_config
from ..schemas import TopicTranslation

logger = logging.getLogger(__name__)


class TopicTranslator:
    """Translates topics to target language before prose generation."""

    def __init__(self, api_key: str = None, model: str = None):
        """Initialize the Topic Translator.

        api_key is retained for backwards-compatible callers; the unified
        llm_service uses OPENROUTER_API_KEY from the environment.
        """
        self.api_key = api_key or test_gen_config.openrouter_api_key
        self.model = model or test_gen_config.default_prose_model
        self.api_call_count = 0
        logger.info(f"TopicTranslator initialized with model: {self.model}")

    def translate(
        self,
        topic_concept: str,
        keywords: List[str],
        target_language: str,
        model_override: Optional[str] = None,
        seed: Optional[int] = None,
    ) -> Tuple[str, List[str]]:
        """Translate topic and keywords to target language.

        Returns (translated_concept, translated_keywords). On schema failure
        after the repair retry, falls back to the original English values and
        logs a warning — translation is best-effort; the downstream prose
        generator can still work in the target language because the prompt
        templates carry full target-language instructions.
        """
        model = model_override or self.model
        keywords_str = ', '.join(keywords) if keywords else ''

        prompt = f"""Translate the following topic and keywords to {target_language}.

Topic: {topic_concept}
Keywords: {keywords_str}

Requirements:
- Translate naturally, not word-for-word
- Keep the meaning and intent clear
- Use appropriate vocabulary for general adult learners

Return ONLY valid JSON in this exact format:
{{
    "topic": "translated topic in {target_language}",
    "keywords": ["keyword1", "keyword2", ...]
}}"""

        try:
            result = call_llm(
                prompt,
                model=model,
                temperature=0.2,
                response_format='json_object',
                schema=TopicTranslation,
                seed=seed,
                timeout=30,
                pipeline='test_gen',
                task_name='topic_translation',
            )
        except ValidationError as e:
            first = e.errors()[0]['msg'] if e.errors() else str(e)
            logger.warning(
                f"Topic translation schema validation failed (after repair) "
                f"for {target_language}: {first}. Falling back to English."
            )
            return (topic_concept, keywords)
        except Exception as e:
            logger.error(f"Topic translation failed: {e}")
            raise

        self.api_call_count += 1

        translated_topic = result.topic or topic_concept
        translated_keywords = result.keywords or keywords

        logger.info(
            f"Translated topic to {target_language}: {translated_topic[:50]}..."
        )
        return (translated_topic, translated_keywords)

    def should_translate(self, language_code: str) -> bool:
        """Determine if translation is needed for a language (non-English)."""
        english_codes = ['en', 'en-us', 'en-gb', 'english']
        return language_code.lower() not in english_codes

    def reset_call_count(self) -> None:
        """Reset the API call counter."""
        self.api_call_count = 0
