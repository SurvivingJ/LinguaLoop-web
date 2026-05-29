"""
Title Generator Agent

Generates concise, difficulty-appropriate titles for listening comprehension tests.
Routes through the unified llm_service so calls are logged to llm_calls.
"""

import json
import logging
from typing import Optional

from services.llm_service import call_llm
from services.llm_output_cleaner import clean_text

from ..config import get_test_gen_config

logger = logging.getLogger(__name__)


class TitleGenerator:
    """Generates titles for tests using LLM."""

    def __init__(self, api_key: str = None, model: str = None):
        """Initialize the Title Generator.

        api_key is retained for backwards-compatible callers; the unified
        llm_service uses OPENROUTER_API_KEY from the environment.
        """
        cfg = get_test_gen_config()
        self.api_key = api_key or cfg.openrouter_api_key
        self.model = model or cfg.default_question_model  # use the lighter model
        self.api_call_count = 0
        logger.info(f"TitleGenerator initialized with model: {self.model}")

    def generate_title(
        self,
        prose: str,
        topic_concept: str,
        difficulty: int,
        complexity_tier: str,
        language_name: str,
        language_code: str,
        prompt_template: Optional[str] = None,
        model_override: Optional[str] = None,
        seed: Optional[int] = None,
        template_version: Optional[int] = None,
    ) -> str:
        """Generate a title for a test based on its prose content.

        Returns the cleaned title string. Raises on empty / errored response;
        the unified llm_service handles its own retry on transient API errors.
        """
        model = model_override or self.model

        if prompt_template:
            # Placeholder names match active DB templates:
            # {prose}, {topic_concept}, {difficulty}, {complexity_tier},
            # {language}, {language_code}
            prompt = prompt_template.format(
                prose=prose,
                topic_concept=topic_concept,
                difficulty=difficulty,
                complexity_tier=complexity_tier,
                language=language_name,
                language_code=language_code,
            )
        else:
            prompt = self._build_default_prompt(
                prose,
                topic_concept,
                difficulty,
                complexity_tier,
                language_name,
            )

        try:
            content = call_llm(
                prompt,
                model=model,
                temperature=0.5,
                response_format='text',
                seed=seed,
                timeout=30,
                pipeline='test_gen',
                task_name='title_generation',
                template_version=template_version,
            )
        except Exception as e:
            logger.error(f"Title generation failed: {e}")
            raise

        self.api_call_count += 1
        title = clean_text(content.strip()).cleaned
        logger.info(f"Generated title: {title[:50]}...")
        return title

    def _build_default_prompt(
        self,
        prose: str,
        topic_concept: str,
        difficulty: int,
        complexity_tier: str,
        language_name: str,
    ) -> str:
        """Build default title generation prompt (legacy fallback).

        Only used when no DB template is supplied. The active code path passes
        a template from prompt_templates via the orchestrator.
        """
        if difficulty <= 2:
            style_guidance = "very simple and short (3-6 words)"
        elif difficulty <= 4:
            style_guidance = "simple and concise (4-8 words)"
        elif difficulty <= 5:
            style_guidance = "clear and straightforward (5-10 words)"
        elif difficulty <= 6:
            style_guidance = "moderately descriptive (6-12 words)"
        elif difficulty <= 7:
            style_guidance = "sophisticated and nuanced (8-15 words)"
        else:
            style_guidance = "complex and detailed (10-18 words)"

        return f"""Generate a title for this listening comprehension passage in {language_name}.

PASSAGE:
{prose}

TOPIC: {topic_concept}
DIFFICULTY: {difficulty}/9 (tier {complexity_tier})

Requirements:
- Write the title ONLY in {language_name}
- Make the title {style_guidance}
- The title should capture the main theme or subject of the passage
- Match the complexity to tier {complexity_tier}:
  * T1-T2 (lower): Use simple vocabulary, basic sentence structure
  * T3-T4 (mid): Use clear but more varied vocabulary
  * T5-T6 (higher): Use sophisticated vocabulary and nuanced phrasing
- Make the title engaging and informative
- Do NOT include quotation marks, markdown, or additional formatting

Return ONLY the title text, nothing else.
"""

    def _clean_response(self, content: str) -> str:
        """Legacy helper retained for backwards compatibility.

        Title cleanup now relies on services.llm_output_cleaner.clean_text;
        external callers (if any) that still invoke this helper get the
        same behaviour as before.
        """
        if content.startswith('```'):
            content = content.replace('```', '', 2)

        if content.startswith('{') and content.endswith('}'):
            try:
                data = json.loads(content)
                if isinstance(data, dict):
                    for key in ['title', 'Title', 'text', 'content']:
                        if key in data:
                            return data[key]
            except json.JSONDecodeError:
                pass

        content = content.strip().strip('"\'')

        prefixes_to_remove = ['Title: ', 'title: ', 'TITLE: ']
        for prefix in prefixes_to_remove:
            if content.startswith(prefix):
                content = content[len(prefix):]

        return content.strip()

    def reset_call_count(self) -> None:
        """Reset the API call counter."""
        self.api_call_count = 0
