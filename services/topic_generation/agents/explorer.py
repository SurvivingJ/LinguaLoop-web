"""
Explorer Agent

Generates diverse topic candidates using structured lenses.
Uses LLM to brainstorm topics within a given category.
"""

import json
import logging
from typing import List

from .base import BaseAgent
from ..config import topic_gen_config
from ..database_client import TopicCandidate, Lens

logger = logging.getLogger(__name__)


class ExplorerAgent(BaseAgent):
    """Generates diverse topic candidates using lens methodology."""

    # OpenRouter base URL
    OPENROUTER_BASE_URL = 'https://openrouter.ai/api/v1'

    def __init__(self, api_key: str = None, model: str = None):
        """
        Initialize the Explorer agent.

        Args:
            api_key: OpenRouter API key (defaults to config)
            model: LLM model to use (defaults to config)
        """
        super().__init__(
            model=model or topic_gen_config.llm_model,
            api_key=api_key or topic_gen_config.openrouter_api_key,
            base_url=self.OPENROUTER_BASE_URL,
            name="Explorer"
        )

    def generate_candidates(
        self,
        category_name: str,
        active_lenses: List[Lens],
        prompt_template: str,
        num_candidates: int = 10
    ) -> List[TopicCandidate]:
        """
        Generate topic candidates for a category.

        Args:
            category_name: Category to generate topics for (e.g., "Agriculture")
            active_lenses: List of Lens objects available for use
            prompt_template: Template with {category} and {available_lenses} placeholders
            num_candidates: Target number of candidates (default 10)

        Returns:
            List[TopicCandidate]: Up to num_candidates candidates

        Expected LLM Output Format:
            {
                "candidates": [
                    {
                        "concept": "The economic impact of precision farming drones",
                        "lens": "economic",
                        "keywords": ["automation", "technology", "investment"]
                    }
                ]
            }
        """
        # Build lens descriptions for the prompt
        lens_descriptions = []
        for lens in active_lenses:
            desc = f"- {lens.display_name}: {lens.description or lens.prompt_hint or ''}"
            lens_descriptions.append(desc)

        available_lenses = "\n".join(lens_descriptions)

        # Format the prompt
        prompt = prompt_template.format(
            category=category_name,
            available_lenses=available_lenses
        )

        try:
            raw_response = self._call_llm(
                prompt=prompt,
                json_mode=True,
                temperature=topic_gen_config.llm_temperature
            )

            # Parse JSON response
            data = self._parse_json_response(raw_response)

            if not data:
                logger.error("Failed to parse Explorer response as JSON")
                return []

            candidates = []
            for item in data.get('candidates', []):
                if self._validate_candidate(item):
                    candidates.append(TopicCandidate(
                        concept=item['concept'].strip(),
                        lens_code=item['lens'].lower().strip(),
                        keywords=[kw.strip() for kw in item.get('keywords', [])]
                    ))

            logger.info(
                f"Explorer generated {len(candidates)} candidates for '{category_name}'"
            )

            return candidates[:num_candidates]

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Explorer JSON: {e}")
            return []
        except Exception as e:
            logger.error(f"Explorer generation failed: {e}")
            return []

    def _parse_json_response(self, content: str) -> dict:
        """
        Parse JSON from LLM response, handling common formatting issues.

        Args:
            content: Raw LLM response

        Returns:
            dict: Parsed JSON or empty dict on failure
        """
        content = content.strip()

        # Remove markdown code blocks if present
        if content.startswith('```'):
            content = content.replace('```json', '', 1)
            content = content.replace('```', '', 1)
        if content.endswith('```'):
            content = content.rsplit('```', 1)[0]

        content = content.strip()

        # Find JSON object boundaries
        start_idx = content.find('{')
        end_idx = content.rfind('}')

        if start_idx != -1 and end_idx != -1 and start_idx < end_idx:
            json_str = content[start_idx:end_idx + 1]
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                pass

        # Try parsing as-is
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return {}

    def _validate_candidate(self, item: dict) -> bool:
        """
        Validate a candidate has required fields.

        Args:
            item: Candidate dict from LLM

        Returns:
            bool: True if valid
        """
        required_fields = ['concept', 'lens']

        for field in required_fields:
            if field not in item or not item[field]:
                logger.debug(f"Candidate missing required field: {field}")
                return False

        # Concept should be reasonably long
        if len(item.get('concept', '')) < 10:
            logger.debug("Candidate concept too short")
            return False

        return True
