"""
Plot Architect Agent

Generates a complete story bible for a murder mystery:
- Title and premise
- Suspects with motives and alibis
- The solution (who did it and why)
- Scene-by-scene outline with clue allocation
- Target vocabulary distribution across scenes

Supports per-language prompt templates from prompt_templates table.
When a template is provided, it is used as the user prompt with variable
substitution. Otherwise, the hardcoded English default is used.
"""

import json
import logging
from typing import Optional, List, Dict
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from services.llm_service import get_client

from ..config import mystery_gen_config

logger = logging.getLogger(__name__)

DEFAULT_SYSTEM_PROMPT = """You are a mystery plot architect for a language learning platform.
Generate a murder mystery story bible that will be used to create a 5-scene comprehension test.

Requirements:
- The mystery must be solvable from the clues provided across scenes
- Each scene reveals exactly one clue
- Suspects must have distinct personalities and motives
- The solution must be logically deducible from the 5 clues
- Vocabulary words should be naturally integrated into scene descriptions
- Keep the complexity appropriate for {complexity_tier} language learners

Output format: valid JSON only, no markdown."""

DEFAULT_USER_PROMPT = """Create a murder mystery story bible with these parameters:
- Language: {language_name}
- Complexity Tier: {complexity_tier}
- Archetype: {archetype}
- Target vocabulary words to include: {target_vocab}

Generate a JSON object with this exact structure:
{{
    "title": "Mystery title in {language_name}",
    "premise": "1-2 sentence setup in {language_name}",
    "suspects": [
        {{
            "name": "Character name (culturally appropriate for {language_name})",
            "description": "Brief character description in {language_name}",
            "motive": "Why they might have done it in {language_name}",
            "alibi": "Their claimed alibi in {language_name}"
        }}
    ],
    "solution": {{
        "suspect_name": "Name of the actual killer",
        "reasoning": "How the clues prove their guilt (2-3 sentences in {language_name})"
    }},
    "scenes": [
        {{
            "scene_number": 1,
            "title": "Scene title in {language_name}",
            "setting": "Where this scene takes place in {language_name}",
            "events": "What happens in this scene (3-4 sentences in {language_name})",
            "clue_type": "evidence|alibi|testimony|forensic",
            "clue_hint": "What clue is revealed here in {language_name}",
            "vocab_focus": ["word1", "word2"]
        }}
    ]
}}

Include exactly 3-4 suspects and exactly 5 scenes.
ALL text content must be written in {language_name}."""


class PlotArchitect:
    """Generates murder mystery story bibles."""

    OPENROUTER_BASE_URL = 'https://openrouter.ai/api/v1'

    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or mystery_gen_config.openrouter_api_key
        self.model = model or mystery_gen_config.plot_model
        self.client = get_client(base_url=self.OPENROUTER_BASE_URL, api_key=self.api_key)
        self.api_call_count = 0
        logger.info(f"PlotArchitect initialized with model: {self.model}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((Exception,)),
        reraise=True
    )
    def generate(
        self,
        language_name: str,
        complexity_tier: str,
        archetype: str = 'alibi_trick',
        target_vocab: Optional[List[str]] = None,
        model_override: Optional[str] = None,
        prompt_template: Optional[str] = None,
    ) -> Dict:
        """
        Generate a complete story bible.

        Args:
            prompt_template: Per-language template from prompt_templates table.
                             If provided, used as user prompt with {variable} substitution.

        Returns:
            Dict with title, premise, suspects, solution, scenes
        """
        vocab_str = ', '.join(target_vocab) if target_vocab else 'none specified'
        model = model_override or self.model

        system_msg = DEFAULT_SYSTEM_PROMPT.format(complexity_tier=complexity_tier)

        if prompt_template:
            user_msg = prompt_template.format(
                language_name=language_name,
                complexity_tier=complexity_tier,
                archetype=archetype,
                target_vocab=vocab_str,
            )
        else:
            user_msg = DEFAULT_USER_PROMPT.format(
                language_name=language_name,
                complexity_tier=complexity_tier,
                archetype=archetype,
                target_vocab=vocab_str,
            )

        response = self.client.chat.completions.create(
            model=model,
            messages=[
                {'role': 'system', 'content': system_msg},
                {'role': 'user', 'content': user_msg},
            ],
            temperature=mystery_gen_config.plot_temperature,
            max_tokens=4000,
        )
        self.api_call_count += 1

        raw = response.choices[0].message.content.strip()
        # Strip markdown code fences if present
        if raw.startswith('```'):
            raw = raw.split('\n', 1)[1] if '\n' in raw else raw[3:]
            if raw.endswith('```'):
                raw = raw[:-3]

        story_bible = json.loads(raw)

        # Validate structure
        required_keys = {'title', 'premise', 'suspects', 'solution', 'scenes'}
        if not required_keys.issubset(story_bible.keys()):
            missing = required_keys - story_bible.keys()
            raise ValueError(f"Story bible missing keys: {missing}")

        if len(story_bible['scenes']) != 5:
            raise ValueError(f"Expected 5 scenes, got {len(story_bible['scenes'])}")

        logger.info(f"Generated story bible: '{story_bible['title']}' with {len(story_bible['suspects'])} suspects")
        return story_bible
