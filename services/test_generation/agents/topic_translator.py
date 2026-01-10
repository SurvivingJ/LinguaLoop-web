"""
Topic Translator Agent

Translates topic concepts and keywords to target language before prose generation.
This ensures prompts are in the target language for non-English content.
"""

import json
import logging
from typing import List, Tuple, Optional
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from ..config import test_gen_config

logger = logging.getLogger(__name__)


class TopicTranslator:
    """Translates topics to target language before prose generation."""

    OPENROUTER_BASE_URL = 'https://openrouter.ai/api/v1'

    def __init__(self, api_key: str = None, model: str = None):
        """
        Initialize the Topic Translator.

        Args:
            api_key: OpenRouter API key (defaults to config)
            model: LLM model to use (defaults to config)
        """
        self.api_key = api_key or test_gen_config.openrouter_api_key
        self.model = model or test_gen_config.default_prose_model
        self.api_call_count = 0

        # Initialize OpenAI client with OpenRouter base URL
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.OPENROUTER_BASE_URL
        )

        logger.info(f"TopicTranslator initialized with model: {self.model}")

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=1, max=5),
        retry=retry_if_exception_type((Exception,)),
        reraise=True
    )
    def translate(
        self,
        topic_concept: str,
        keywords: List[str],
        target_language: str,
        model_override: str = None
    ) -> Tuple[str, List[str]]:
        """
        Translate topic and keywords to target language.

        Args:
            topic_concept: English topic concept (from topics.concept_english)
            keywords: List of English keywords
            target_language: Target language name (e.g., "Chinese", "Japanese")
            model_override: Optional model override for this call

        Returns:
            Tuple of (translated_concept, translated_keywords)
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
            response = self.client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                timeout=30
            )
            self.api_call_count += 1

            if not response.choices:
                raise Exception("No response from LLM")

            content = response.choices[0].message.content
            if not content:
                raise Exception("Empty response from LLM")

            content = content.strip()

            # Parse JSON response
            if content.startswith('```'):
                content = content.replace('```json', '', 1).replace('```', '')
                content = content.strip()

            # Find JSON object
            start_idx = content.find('{')
            end_idx = content.rfind('}')

            if start_idx != -1 and end_idx != -1 and start_idx < end_idx:
                json_str = content[start_idx:end_idx + 1]
                data = json.loads(json_str)
            else:
                raise ValueError(f"No JSON found in response: {content[:100]}...")

            translated_topic = data.get('topic', topic_concept)
            translated_keywords = data.get('keywords', keywords)

            # Validate types
            if not isinstance(translated_topic, str):
                translated_topic = str(translated_topic)
            if not isinstance(translated_keywords, list):
                translated_keywords = keywords

            logger.info(
                f"Translated topic to {target_language}: "
                f"{translated_topic[:50]}..."
            )

            return (translated_topic, translated_keywords)

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse translation response: {e}")
            # Return original values on parse error
            return (topic_concept, keywords)
        except Exception as e:
            logger.error(f"Topic translation failed: {e}")
            raise

    def should_translate(self, language_code: str) -> bool:
        """
        Determine if translation is needed for a language.

        Args:
            language_code: ISO language code

        Returns:
            bool: True if translation is needed (non-English)
        """
        english_codes = ['en', 'en-us', 'en-gb', 'english']
        return language_code.lower() not in english_codes

    def reset_call_count(self) -> None:
        """Reset the API call counter."""
        self.api_call_count = 0
