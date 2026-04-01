"""
Persona Designer Agent

Generates persona profiles via LLM and scores persona pair compatibility.
"""

import json
import logging
from typing import List, Dict, Optional

from services.topic_generation.agents.base import BaseAgent
from ..config import conv_gen_config

logger = logging.getLogger(__name__)

OPENROUTER_BASE_URL = 'https://openrouter.ai/api/v1'


class PersonaDesigner(BaseAgent):
    """Generates AI persona profiles for conversation generation."""

    def __init__(self, api_key: str = None, model: str = None):
        if conv_gen_config.llm_provider == 'ollama':
            super().__init__(
                model=model or conv_gen_config.ollama_model,
                api_key='ollama',
                base_url=conv_gen_config.ollama_base_url,
                name="PersonaDesigner",
            )
        else:
            super().__init__(
                model=model or conv_gen_config.conversation_model,
                api_key=api_key or conv_gen_config.openrouter_api_key,
                base_url=OPENROUTER_BASE_URL,
                name="PersonaDesigner",
            )

    def design_persona(
        self,
        prompt_template: str,
        language_name: str,
        domain_name: str,
        register: str,
        complexity_tier: str,
    ) -> Dict:
        """
        Generate a persona profile via LLM.

        Args:
            prompt_template: Prompt template with placeholders
            language_name: Target language name
            domain_name: Domain for the persona's expertise
            register: Required register (formal/semi-formal/informal)
            complexity_tier: Target complexity tier (T1-T6)

        Returns:
            Dict with persona fields ready for DB insertion.
        """
        prompt = prompt_template.format(
            language_name=language_name,
            domain_name=domain_name,
            register=register,
            complexity_tier=complexity_tier,
        )

        response_text = self._call_llm(
            prompt=prompt,
            json_mode=True,
            temperature=0.9,
        )

        persona = json.loads(response_text) if isinstance(response_text, str) else response_text
        logger.info("Designed persona: %s (%s)", persona.get('name'), persona.get('archetype'))
        return persona

    def design_personas_batch(
        self,
        prompt_template: str,
        language_name: str,
        domain_name: str,
        register: str,
        complexity_tier: str,
        count: int = 4,
    ) -> List[Dict]:
        """Generate multiple personas for a domain."""
        personas = []
        for i in range(count):
            try:
                persona = self.design_persona(
                    prompt_template=prompt_template,
                    language_name=language_name,
                    domain_name=domain_name,
                    register=register,
                    complexity_tier=complexity_tier,
                )
                personas.append(persona)
            except Exception as exc:
                logger.error("Failed to design persona %d/%d: %s", i + 1, count, exc)
        return personas

    def design_persona_from_archetype(
        self,
        archetype_key: str,
        archetype_info: dict,
        language_id: int,
        language_name: str,
        prompt_template: str,
    ) -> Dict:
        """
        Generate a persona via LLM, constrained to a specific archetype.

        Args:
            archetype_key: Archetype slug (e.g. 'protective_parent')
            archetype_info: Archetype dict from ARCHETYPES
            language_id: Target language ID
            language_name: Target language name for prompt
            prompt_template: Prompt template with placeholders

        Returns:
            Dict with persona fields ready for DB insertion.
        """
        prompt = prompt_template.format(
            language_name=language_name,
            archetype_key=archetype_key,
            archetype_label=archetype_info['label'],
            archetype_description=archetype_info['description'],
            category=archetype_info['category'],
            typical_registers=', '.join(archetype_info['typical_registers']),
            typical_relationship_types=', '.join(archetype_info['typical_relationship_types']),
            age_min=archetype_info['age_range'][0],
            age_max=archetype_info['age_range'][1],
        )

        response_text = self._call_llm(
            prompt=prompt,
            json_mode=True,
            temperature=0.9,
        )

        parsed = json.loads(response_text) if isinstance(response_text, str) else response_text

        # LLM sometimes returns a list — extract first element
        if isinstance(parsed, list):
            if not parsed:
                raise ValueError("LLM returned an empty list")
            parsed = parsed[0]

        if not isinstance(parsed, dict):
            raise ValueError(f"LLM returned unexpected type: {type(parsed).__name__}")

        persona = parsed

        # Ensure required fields are set
        persona.setdefault('archetype', archetype_key)
        persona.setdefault('language_id', language_id)
        persona.setdefault('generation_method', 'llm')
        persona.setdefault('register', archetype_info['typical_registers'][0])
        persona.setdefault('relationship_types', archetype_info['typical_relationship_types'])

        logger.info(
            "LLM-designed persona: %s (%s) for archetype %s",
            persona.get('name'), persona.get('occupation'), archetype_key,
        )
        return persona

    def score_pair(
        self,
        persona_a: Dict,
        persona_b: Dict,
    ) -> float:
        """Deprecated: Use pairing.score_pair() directly."""
        from ..pairing import score_pair as _score_pair
        score, _ = _score_pair(persona_a, persona_b)
        return score
