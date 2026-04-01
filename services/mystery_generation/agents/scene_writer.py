"""
Scene Writer Agent

Generates prose for each mystery scene in the target language,
adhering to complexity tier grammatical constraints and word count targets.

Supports per-language prompt templates from prompt_templates table.
"""

import logging
from typing import Optional, Dict
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from services.llm_service import get_client
from services.llm_output_cleaner import clean_text

from ..config import mystery_gen_config

logger = logging.getLogger(__name__)

DEFAULT_SYSTEM_PROMPT = """You are a language learning content writer specializing in mystery narratives.
Write scene text for a murder mystery comprehension exercise.

Requirements:
- Write entirely in {language_name}
- Use ONLY grammar and vocabulary appropriate for complexity tier {complexity_tier}
- Write between {min_words} and {max_words} words
- Include the specified vocabulary words naturally
- Build suspense while keeping language accessible
- Each scene should be self-contained but advance the plot

Output: ONLY the scene text in {language_name}. No English, no labels, no metadata."""

DEFAULT_USER_PROMPT = """Write Scene {scene_number} of a murder mystery.

Mystery title: {title}
Scene setting: {setting}
Events to cover: {events}
Vocabulary to include: {vocab_words}

Previous scenes summary: {previous_summary}

Write the scene text now in {language_name}:"""


class SceneWriter:
    """Generates prose content for mystery scenes."""

    OPENROUTER_BASE_URL = 'https://openrouter.ai/api/v1'

    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or mystery_gen_config.openrouter_api_key
        self.model = model or mystery_gen_config.scene_model
        self.client = get_client(base_url=self.OPENROUTER_BASE_URL, api_key=self.api_key)
        self.api_call_count = 0
        logger.info(f"SceneWriter initialized with model: {self.model}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((Exception,)),
        reraise=True
    )
    def generate(
        self,
        story_bible: Dict,
        scene_outline: Dict,
        language_name: str,
        complexity_tier: str,
        previous_summary: str = '',
        model_override: Optional[str] = None,
        prompt_template: Optional[str] = None,
    ) -> str:
        """
        Generate prose for a single mystery scene.

        Args:
            story_bible: Full plot outline
            scene_outline: This scene's outline from story_bible['scenes']
            language_name: Target language
            complexity_tier: Tier code (e.g., "T1", "T3")
            previous_summary: Brief summary of previous scenes
            model_override: Override model from dim_languages
            prompt_template: Per-language template from prompt_templates table

        Returns:
            str: Scene prose in target language
        """
        model = model_override or self.model
        vocab_words = ', '.join(scene_outline.get('vocab_focus', []))

        system_msg = DEFAULT_SYSTEM_PROMPT.format(
            language_name=language_name,
            complexity_tier=complexity_tier,
            min_words=mystery_gen_config.min_words_per_scene,
            max_words=mystery_gen_config.max_words_per_scene,
        )

        if prompt_template:
            user_msg = prompt_template.format(
                scene_number=scene_outline['scene_number'],
                title=story_bible['title'],
                setting=scene_outline.get('setting', ''),
                events=scene_outline.get('events', ''),
                vocab_words=vocab_words or 'none specified',
                previous_summary=previous_summary or 'This is the first scene.',
                language_name=language_name,
            )
        else:
            user_msg = DEFAULT_USER_PROMPT.format(
                scene_number=scene_outline['scene_number'],
                title=story_bible['title'],
                setting=scene_outline.get('setting', ''),
                events=scene_outline.get('events', ''),
                vocab_words=vocab_words or 'none specified',
                previous_summary=previous_summary or 'This is the first scene.',
                language_name=language_name,
            )

        response = self.client.chat.completions.create(
            model=model,
            messages=[
                {'role': 'system', 'content': system_msg},
                {'role': 'user', 'content': user_msg},
            ],
            temperature=mystery_gen_config.scene_temperature,
            max_tokens=1500,
        )
        self.api_call_count += 1

        text = clean_text(response.choices[0].message.content.strip()).cleaned
        logger.info(f"Generated scene {scene_outline['scene_number']} text ({len(text)} chars)")
        return text
