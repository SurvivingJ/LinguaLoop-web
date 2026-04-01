"""
Scenario Planner Agent

Creates conversation scenarios with context descriptions and per-persona goals.
"""

import json
import logging
from typing import Dict, Optional

from services.topic_generation.agents.base import BaseAgent
from ..config import conv_gen_config

logger = logging.getLogger(__name__)

OPENROUTER_BASE_URL = 'https://openrouter.ai/api/v1'


class ScenarioPlanner(BaseAgent):
    """Generates conversation scenarios with context and goals."""

    def __init__(self, api_key: str = None, model: str = None):
        if conv_gen_config.llm_provider == 'ollama':
            super().__init__(
                model=model or conv_gen_config.ollama_model,
                api_key='ollama',
                base_url=conv_gen_config.ollama_base_url,
                name="ScenarioPlanner",
            )
        else:
            super().__init__(
                model=model or conv_gen_config.conversation_model,
                api_key=api_key or conv_gen_config.openrouter_api_key,
                base_url=OPENROUTER_BASE_URL,
                name="ScenarioPlanner",
            )

    def plan_scenario(
        self,
        prompt_template: str,
        language_name: str,
        domain_name: str,
        domain_description: str,
        persona_a_summary: str,
        persona_b_summary: str,
        relationship_type: str,
        register: str,
        complexity_tier: str,
    ) -> Dict:
        """
        Generate a scenario outline via LLM.

        Args:
            prompt_template: Template with placeholders for all fields
            language_name: Target language name
            domain_name: Domain name
            domain_description: Domain description
            persona_a_summary: Brief summary of persona A
            persona_b_summary: Brief summary of persona B
            relationship_type: Relationship type between personas
            register: Required register
            complexity_tier: Target complexity tier (T1-T6)

        Returns:
            Dict with scenario fields: title, context_description, goals, keywords, cultural_note
        """
        prompt = prompt_template.format(
            language_name=language_name,
            domain_name=domain_name,
            domain_description=domain_description or domain_name,
            persona_a_summary=persona_a_summary,
            persona_b_summary=persona_b_summary,
            relationship_type=relationship_type,
            register=register,
            complexity_tier=complexity_tier,
        )

        response_text = self._call_llm(
            prompt=prompt,
            json_mode=True,
            temperature=0.8,
        )

        scenario = json.loads(response_text) if isinstance(response_text, str) else response_text
        logger.info("Planned scenario: %s", scenario.get('title'))
        return scenario

    @staticmethod
    def build_persona_summary(persona: Dict) -> str:
        """Build a concise persona summary for the scenario prompt."""
        parts = [persona.get('name', 'Unknown')]
        if persona.get('age'):
            parts.append(f"age {persona['age']}")
        if persona.get('occupation'):
            parts.append(persona['occupation'])
        if persona.get('archetype'):
            parts.append(f"({persona['archetype']})")
        traits = persona.get('personality', {}).get('traits', [])
        if traits:
            parts.append(f"traits: {', '.join(traits[:3])}")
        return ', '.join(parts)
