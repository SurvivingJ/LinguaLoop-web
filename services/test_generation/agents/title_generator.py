"""
Title Generator Agent

Generates concise, difficulty-appropriate titles for listening comprehension tests.
Uses OpenRouter for LLM calls.
"""

import json
import logging
from typing import Optional
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from ..config import test_gen_config

logger = logging.getLogger(__name__)


class TitleGenerator:
    """Generates titles for tests using LLM."""

    # OpenRouter base URL
    OPENROUTER_BASE_URL = 'https://openrouter.ai/api/v1'

    def __init__(self, api_key: str = None, model: str = None):
        """
        Initialize the Title Generator.

        Args:
            api_key: OpenRouter API key (defaults to config)
            model: LLM model to use (defaults to config)
        """
        self.api_key = api_key or test_gen_config.openrouter_api_key
        self.model = model or test_gen_config.default_question_model  # Use lighter model
        self.api_call_count = 0

        # Initialize OpenAI client with OpenRouter base URL
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.OPENROUTER_BASE_URL
        )

        logger.info(f"TitleGenerator initialized with model: {self.model}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((Exception,)),
        reraise=True
    )
    def generate_title(
        self,
        prose: str,
        topic_concept: str,
        difficulty: int,
        cefr_level: str,
        language_name: str,
        language_code: str,
        prompt_template: Optional[str] = None,
        model_override: Optional[str] = None
    ) -> str:
        """
        Generate a title for a test based on its prose content.

        Args:
            prose: The prose/transcript text
            topic_concept: Topic concept (translated to target language)
            difficulty: Difficulty level 1-9
            cefr_level: CEFR level code (e.g., "A1", "B2")
            language_name: Target language name (e.g., "Spanish")
            language_code: ISO language code (e.g., "es")
            prompt_template: Custom prompt template (optional)
            model_override: Override model for this call

        Returns:
            str: Generated title text
        """
        model = model_override or self.model

        # Build prompt
        if prompt_template:
            # Use placeholder names that match database templates:
            # {prose}, {topic_concept}, {difficulty}, {cefr_level}, {language}, {language_code}
            prompt = prompt_template.format(
                prose=prose,
                topic_concept=topic_concept,
                difficulty=difficulty,
                cefr_level=cefr_level,
                language=language_name,
                language_code=language_code
            )
        else:
            prompt = self._build_default_prompt(
                prose,
                topic_concept,
                difficulty,
                cefr_level,
                language_name
            )

        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,  # Moderate creativity for titles
                timeout=30
            )

            self.api_call_count += 1

            if not response.choices:
                raise Exception("No response from LLM")

            content = response.choices[0].message.content
            if not content:
                raise Exception("Empty response from LLM")

            title = self._clean_response(content.strip())

            logger.info(f"Generated title: {title[:50]}...")
            return title

        except Exception as e:
            logger.error(f"Title generation failed: {e}")
            raise

    def _build_default_prompt(
        self,
        prose: str,
        topic_concept: str,
        difficulty: int,
        cefr_level: str,
        language_name: str
    ) -> str:
        """Build default title generation prompt."""

        # Define style guidance based on difficulty
        if difficulty <= 2:  # A1
            style_guidance = "very simple and short (3-6 words)"
        elif difficulty <= 4:  # A2
            style_guidance = "simple and concise (4-8 words)"
        elif difficulty <= 5:  # B1
            style_guidance = "clear and straightforward (5-10 words)"
        elif difficulty <= 6:  # B2
            style_guidance = "moderately descriptive (6-12 words)"
        elif difficulty <= 7:  # C1
            style_guidance = "sophisticated and nuanced (8-15 words)"
        else:  # C2
            style_guidance = "complex and detailed (10-18 words)"

        return f"""Generate a title for this listening comprehension passage in {language_name}.

PASSAGE:
{prose}

TOPIC: {topic_concept}
DIFFICULTY: {difficulty}/9 ({cefr_level} level)

Requirements:
- Write the title ONLY in {language_name}
- Make the title {style_guidance}
- The title should capture the main theme or subject of the passage
- Match the complexity to the {cefr_level} level:
  * Lower levels (A1-A2): Use simple vocabulary, basic sentence structure
  * Mid levels (B1-B2): Use clear but more varied vocabulary
  * Higher levels (C1-C2): Use sophisticated vocabulary and nuanced phrasing
- Make the title engaging and informative
- Do NOT include quotation marks, markdown, or additional formatting

Return ONLY the title text, nothing else.
"""

    def _clean_response(self, content: str) -> str:
        """Clean the LLM response to extract title."""
        # Remove any markdown code blocks
        if content.startswith('```'):
            content = content.replace('```', '', 2)

        # Remove any JSON wrapping
        if content.startswith('{') and content.endswith('}'):
            try:
                data = json.loads(content)
                if isinstance(data, dict):
                    # Try common keys
                    for key in ['title', 'Title', 'text', 'content']:
                        if key in data:
                            return data[key]
            except json.JSONDecodeError:
                pass

        # Remove leading/trailing quotes
        content = content.strip().strip('"\'')

        # Remove common prefixes that LLMs sometimes add
        prefixes_to_remove = [
            'Title: ',
            'title: ',
            'TITLE: ',
        ]
        for prefix in prefixes_to_remove:
            if content.startswith(prefix):
                content = content[len(prefix):]

        return content.strip()

    def reset_call_count(self) -> None:
        """Reset the API call counter."""
        self.api_call_count = 0
