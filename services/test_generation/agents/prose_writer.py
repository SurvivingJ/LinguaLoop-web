"""
Prose Writer Agent

Generates prose/transcript content for listening comprehension tests.
Routes through the unified llm_service so calls are logged to llm_calls.
"""

import json
import logging
from typing import Optional

from services.llm_service import call_llm, get_client
from services.llm_output_cleaner import clean_text
from services.conversation_generation.categorical_maps import DIFFICULTY_TO_TIER

from ..config import test_gen_config

logger = logging.getLogger(__name__)


class ProseWriter:
    """Generates prose content for tests using LLM."""

    # OpenRouter base URL — used by the back-compat self.client shim consumed
    # by VocabularyExtractionPipeline (see orchestrator). Prose generation
    # itself routes through services.llm_service.call_llm.
    OPENROUTER_BASE_URL = 'https://openrouter.ai/api/v1'

    def __init__(self, api_key: str = None, model: str = None):
        """Initialize the Prose Writer.

        api_key is retained for backwards-compatible callers; the unified
        llm_service uses OPENROUTER_API_KEY from the environment.
        """
        self.api_key = api_key or test_gen_config.openrouter_api_key
        self.model = model or test_gen_config.default_prose_model
        self.api_call_count = 0

        # Back-compat: VocabularyExtractionPipeline reads
        # `prose_writer.client` as its OpenAI client. Construct it via the
        # shared pool to avoid duplicating connection state.
        self.client = get_client(
            base_url=self.OPENROUTER_BASE_URL,
            api_key=self.api_key,
        )

        logger.info(f"ProseWriter initialized with model: {self.model}")

    def generate_prose(
        self,
        topic_concept: str,
        language_name: str,
        language_code: str,
        difficulty: int,
        word_count_min: int,
        word_count_max: int,
        keywords: Optional[list] = None,
        complexity_tier: Optional[str] = None,
        prompt_template: Optional[str] = None,
        model_override: Optional[str] = None,
        seed: Optional[int] = None,
        template_version: Optional[int] = None,
    ) -> str:
        """Generate prose content for a test.

        Returns the cleaned prose string. Raises on empty / errored response;
        the unified llm_service handles its own retry on transient API errors.
        """
        model = model_override or self.model

        # Format keywords for template
        keywords_str = ', '.join(keywords) if keywords else ''

        # Determine tier if not provided
        if not complexity_tier:
            complexity_tier = DIFFICULTY_TO_TIER.get(difficulty, 'T3')

        if prompt_template:
            # Placeholder names match the active DB templates:
            # {topic_concept}, {keywords}, {complexity_tier}, {min_words}, {max_words}
            prompt = prompt_template.format(
                topic_concept=topic_concept,
                keywords=keywords_str,
                complexity_tier=complexity_tier,
                min_words=word_count_min,
                max_words=word_count_max,
                language=language_name,
                language_code=language_code,
                difficulty=difficulty,
            )
        else:
            prompt = self._build_default_prompt(
                topic_concept,
                language_name,
                difficulty,
                word_count_min,
                word_count_max,
            )

        try:
            content = call_llm(
                prompt,
                model=model,
                temperature=test_gen_config.prose_temperature,
                response_format='text',
                seed=seed,
                timeout=60,
                pipeline='test_gen',
                task_name='prose_generation',
                template_version=template_version,
            )
        except Exception as e:
            logger.error(f"Prose generation failed: {e}")
            raise

        self.api_call_count += 1

        prose = clean_text(content.strip()).cleaned
        char_count = len(prose)
        word_count_estimate = len(prose.split())
        logger.info(
            f"Generated prose: {char_count} chars, ~{word_count_estimate} words "
            f"(target: {word_count_min}-{word_count_max} words)"
        )
        return prose

    def _build_default_prompt(
        self,
        topic: str,
        language: str,
        difficulty: int,
        word_count_min: int,
        word_count_max: int,
    ) -> str:
        """Build default prose generation prompt (legacy fallback).

        Only used when no DB template is supplied. The active code path passes
        a template from prompt_templates via the orchestrator.
        """
        tier = DIFFICULTY_TO_TIER.get(difficulty, 'T3')

        return f"""Generate a natural, engaging prose passage in {language} for language learners.

TOPIC: {topic}
TARGET LEVEL: {tier}
DIFFICULTY: {difficulty}/9
WORD COUNT: {word_count_min}-{word_count_max} words

Requirements:
- Write ONLY in {language}
- Use vocabulary and grammar appropriate for complexity tier {tier}
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
        """Clean the LLM response to extract prose (legacy helper, unused).

        Retained for backwards compatibility with any external caller; new code
        relies on services.llm_output_cleaner.clean_text instead.
        """
        if content.startswith('```'):
            content = content.replace('```', '', 2)

        if content.startswith('{') and content.endswith('}'):
            try:
                data = json.loads(content)
                if isinstance(data, dict):
                    for key in ['prose', 'transcript', 'text', 'content']:
                        if key in data:
                            return data[key]
            except json.JSONDecodeError:
                pass

        content = content.strip().strip('"\'')
        return content

    def reset_call_count(self) -> None:
        """Reset the API call counter."""
        self.api_call_count = 0
