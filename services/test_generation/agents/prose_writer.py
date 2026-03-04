"""
Prose Writer Agent

Generates prose/transcript content for listening comprehension tests.
Uses OpenRouter for LLM calls.
"""

import json
import logging
from typing import Optional
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from ..config import test_gen_config

logger = logging.getLogger(__name__)


class ProseWriter:
    """Generates prose content for tests using LLM."""

    # OpenRouter base URL
    OPENROUTER_BASE_URL = 'https://openrouter.ai/api/v1'

    def __init__(self, api_key: str = None, model: str = None):
        """
        Initialize the Prose Writer.

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

        logger.info(f"ProseWriter initialized with model: {self.model}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((Exception,)),
        reraise=True
    )
    def generate_prose(
        self,
        topic_concept: str,
        language_name: str,
        language_code: str,
        difficulty: int,
        word_count_min: int,
        word_count_max: int,
        keywords: Optional[list] = None,
        cefr_level: Optional[str] = None,
        prompt_template: Optional[str] = None,
        model_override: Optional[str] = None
    ) -> str:
        """
        Generate prose content for a test.

        Args:
            topic_concept: Topic/subject of the prose (in target language)
            language_name: Target language name (e.g., "Spanish")
            language_code: ISO language code (e.g., "es")
            difficulty: Difficulty level 1-9
            word_count_min: Minimum word count
            word_count_max: Maximum word count
            keywords: List of keywords related to topic (in target language)
            cefr_level: CEFR level code (e.g., "A1", "B2")
            prompt_template: Custom prompt template (optional)
            model_override: Override model for this call

        Returns:
            str: Generated prose text
        """
        model = model_override or self.model

        # Format keywords for template
        keywords_str = ', '.join(keywords) if keywords else ''

        # Determine CEFR level if not provided
        if not cefr_level:
            cefr_map = {
                1: 'A1', 2: 'A1',
                3: 'A2', 4: 'A2',
                5: 'B1',
                6: 'B2',
                7: 'C1',
                8: 'C2', 9: 'C2'
            }
            cefr_level = cefr_map.get(difficulty, 'B1')

        # Build prompt
        if prompt_template:
            # Use placeholder names that match actual database templates:
            # {topic_concept}, {keywords}, {cefr_level}, {min_words}, {max_words}
            prompt = prompt_template.format(
                topic_concept=topic_concept,
                keywords=keywords_str,
                cefr_level=cefr_level,
                min_words=word_count_min,
                max_words=word_count_max,
                language=language_name,
                language_code=language_code,
                difficulty=difficulty
            )
        else:
            prompt = self._build_default_prompt(
                topic_concept,
                language_name,
                difficulty,
                word_count_min,
                word_count_max
            )

        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=test_gen_config.prose_temperature,
                timeout=60
            )

            self.api_call_count += 1

            if not response.choices:
                raise Exception("No response from LLM")

            content = response.choices[0].message.content
            if not content:
                raise Exception("Empty response from LLM")

            prose = self._clean_response(content.strip())

            # Log prose length (character count works better for CJK languages)
            # Don't validate word count since Chinese/Japanese don't use spaces
            char_count = len(prose)
            word_count_estimate = len(prose.split())
            logger.info(
                f"Generated prose: {char_count} chars, ~{word_count_estimate} words "
                f"(target: {word_count_min}-{word_count_max} words)"
            )

            return prose

        except Exception as e:
            logger.error(f"Prose generation failed: {e}")
            raise

    def _build_default_prompt(
        self,
        topic: str,
        language: str,
        difficulty: int,
        word_count_min: int,
        word_count_max: int
    ) -> str:
        """Build default prose generation prompt."""
        # Map difficulty to CEFR
        cefr_map = {
            1: 'A1', 2: 'A1',
            3: 'A2', 4: 'A2',
            5: 'B1',
            6: 'B2',
            7: 'C1',
            8: 'C2', 9: 'C2'
        }
        cefr = cefr_map.get(difficulty, 'B1')

        return f"""Generate a natural, engaging prose passage in {language} for language learners.

TOPIC: {topic}
TARGET LEVEL: {cefr} (CEFR)
DIFFICULTY: {difficulty}/9
WORD COUNT: {word_count_min}-{word_count_max} words

Requirements:
- Write ONLY in {language}
- Use vocabulary and grammar appropriate for {cefr} level
- Create natural, flowing prose suitable for listening comprehension
- Include clear main ideas with supporting details
- Avoid overly complex or technical vocabulary for lower levels
- For higher levels, include nuanced expressions and complex structures

Style:
- Conversational but informative
- Clear paragraph structure
- Varied sentence lengths
- Culturally appropriate content

Return ONLY the prose text, with no additional commentary or formatting.
"""

    def _clean_response(self, content: str) -> str:
        """Clean the LLM response to extract prose."""
        # Remove any markdown code blocks
        if content.startswith('```'):
            content = content.replace('```', '', 2)

        # Remove any JSON wrapping
        if content.startswith('{') and content.endswith('}'):
            try:
                data = json.loads(content)
                if isinstance(data, dict):
                    # Try common keys
                    for key in ['prose', 'transcript', 'text', 'content']:
                        if key in data:
                            return data[key]
            except json.JSONDecodeError:
                pass

        # Remove leading/trailing quotes
        content = content.strip().strip('"\'')

        return content

    def reset_call_count(self) -> None:
        """Reset the API call counter."""
        self.api_call_count = 0
