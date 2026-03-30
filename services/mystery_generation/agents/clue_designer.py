"""
Clue Designer Agent

Generates the clue text revealed to the learner when they correctly
answer a scene's comprehension questions. Clues must be:
- Concise (1-2 sentences)
- Relevant to solving the mystery
- Written in the target language for immersion

Supports per-language prompt templates from prompt_templates table.
"""

import json
import logging
from typing import Optional, Dict, List
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from services.llm_service import get_client

from ..config import mystery_gen_config

logger = logging.getLogger(__name__)

DEFAULT_SYSTEM_PROMPT = """You are designing clues for a murder mystery language learning game.
Each clue should be:
- Concise (1-2 sentences)
- A piece of evidence that helps identify the killer
- Together, 5 clues should make the solution deducible

Output format: valid JSON only."""

DEFAULT_USER_PROMPT = """Design the clue for Scene {scene_number} of this mystery:

Mystery: {title}
Scene events: {events}
Clue type: {clue_type}
Clue hint from outline: {clue_hint}
Solution: {solution_suspect} did it because: {solution_reasoning}

Previous clues revealed:
{previous_clues}

Generate JSON:
{{
    "clue_text": "The clue text (1-2 sentences)",
    "clue_type": "{clue_type}"
}}"""


class ClueDesigner:
    """Designs clue reveals for mystery scenes."""

    OPENROUTER_BASE_URL = 'https://openrouter.ai/api/v1'

    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or mystery_gen_config.openrouter_api_key
        self.model = model or mystery_gen_config.plot_model
        self.client = get_client(base_url=self.OPENROUTER_BASE_URL, api_key=self.api_key)
        self.api_call_count = 0
        logger.info(f"ClueDesigner initialized with model: {self.model}")

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
        previous_clues: List[str] = None,
        model_override: Optional[str] = None,
        prompt_template: Optional[str] = None,
    ) -> Dict:
        """
        Generate clue text for a scene.

        Returns:
            Dict with clue_text and clue_type
        """
        model = model_override or self.model
        solution = story_bible.get('solution', {})

        prev_clues_str = '\n'.join(
            f"- Scene {i+1}: {c}" for i, c in enumerate(previous_clues or [])
        ) or 'None yet (this is Scene 1)'

        if prompt_template:
            user_msg = prompt_template.format(
                scene_number=scene_outline['scene_number'],
                title=story_bible['title'],
                events=scene_outline.get('events', ''),
                clue_type=scene_outline.get('clue_type', 'evidence'),
                clue_hint=scene_outline.get('clue_hint', ''),
                solution_suspect=solution.get('suspect_name', ''),
                solution_reasoning=solution.get('reasoning', ''),
                previous_clues=prev_clues_str,
            )
        else:
            user_msg = DEFAULT_USER_PROMPT.format(
                scene_number=scene_outline['scene_number'],
                title=story_bible['title'],
                events=scene_outline.get('events', ''),
                clue_type=scene_outline.get('clue_type', 'evidence'),
                clue_hint=scene_outline.get('clue_hint', ''),
                solution_suspect=solution.get('suspect_name', ''),
                solution_reasoning=solution.get('reasoning', ''),
                previous_clues=prev_clues_str,
            )

        response = self.client.chat.completions.create(
            model=model,
            messages=[
                {'role': 'system', 'content': DEFAULT_SYSTEM_PROMPT},
                {'role': 'user', 'content': user_msg},
            ],
            temperature=0.7,
            max_tokens=500,
        )
        self.api_call_count += 1

        raw = response.choices[0].message.content.strip()
        if raw.startswith('```'):
            raw = raw.split('\n', 1)[1] if '\n' in raw else raw[3:]
            if raw.endswith('```'):
                raw = raw[:-3]

        result = json.loads(raw)
        logger.info(f"Generated clue for scene {scene_outline['scene_number']}: {result.get('clue_text', '')[:60]}...")
        return result
