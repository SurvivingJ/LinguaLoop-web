"""
Explorer Agent

Generates diverse topic candidates using structured lenses.
Uses LLM to brainstorm topics within a given category.
"""

import json
import logging
from typing import List, Optional

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
        num_candidates: int = 6,
        tier: Optional[int] = None,
        default_lens_code: str = 'practical',
        max_attempts: int = 3,
    ) -> List[TopicCandidate]:
        """
        Generate topic candidates for one category at one age tier.

        Each age tier (ADR-003) has its own DB prompt, so the tier is fixed by
        the caller and stamped onto every candidate as ``target_age_tier``
        rather than self-reported by the model. The model returns a numeric
        ``lens`` id (or null) per the global numeric-index JSON rule.

        Args:
            category_name: Category to generate topics for (e.g., "Agriculture")
            active_lenses: Active Lens objects, presented to the model with ids
            prompt_template: Tier prompt with {category} and {available_lenses}
            num_candidates: Max candidates to return
            tier: Age tier 1-6 stamped on every candidate (None = legacy)
            default_lens_code: Fallback lens when the model returns null

        Returns:
            List[TopicCandidate]: Up to num_candidates candidates

        Expected LLM Output Format:
            {
                "candidates": [
                    {
                        "concept": "A beekeeper inspecting a hive through the seasons",
                        "lens": 7,
                        "distinctive_vocabulary": ["hive", "comb", "smoker", "swarm",
                            "nectar", "brood", "requeening", "overwintering"],
                        "keywords": ["bees", "honey", "seasons"]
                    }
                ]
            }
        """
        lens_by_id = {lens.id: lens for lens in active_lenses}
        default_lens = next(
            (l for l in active_lenses
             if l.lens_code.lower() == default_lens_code.lower()),
            None,
        )

        # Present lenses with numeric ids so the model can return a numeric id.
        lens_descriptions = [
            f"{lens.id}. {lens.display_name}: "
            f"{lens.description or lens.prompt_hint or ''}"
            for lens in active_lenses
        ]
        available_lenses = "\n".join(lens_descriptions)

        # Format the prompt
        prompt = prompt_template.format(
            category=category_name,
            available_lenses=available_lenses
        )

        # gemini-flash-lite intermittently emits malformed JSON or an empty
        # candidate set; a single bad roll used to silently yield 0 topics for
        # the whole tier. Retry the call+parse+validate up to max_attempts and
        # return as soon as we have at least one valid candidate.
        last_error: Optional[Exception] = None
        for attempt in range(1, max_attempts + 1):
            try:
                raw_response = self._call_llm(
                    prompt=prompt,
                    json_mode=True,
                    temperature=topic_gen_config.llm_temperature
                )

                # Parse JSON response
                data = self._parse_json_response(raw_response)

                if not data:
                    logger.warning(
                        "Explorer JSON parse empty (tier=%s, attempt %d/%d)",
                        tier, attempt, max_attempts,
                    )
                    continue

                candidates = []
                for item in data.get('candidates', []):
                    if not self._validate_candidate(item):
                        continue

                    lens_id, lens_code = self._resolve_lens(
                        item.get('lens'), lens_by_id, default_lens
                    )

                    candidates.append(TopicCandidate(
                        concept=item['concept'].strip(),
                        lens_code=lens_code,
                        lens_id=lens_id,
                        keywords=[
                            kw.strip() for kw in item.get('keywords', [])
                            if kw and kw.strip()
                        ],
                        distinctive_vocabulary=[
                            w.strip() for w in item.get('distinctive_vocabulary', [])
                            if w and w.strip()
                        ],
                        target_age_tier=tier,
                    ))

                if candidates:
                    logger.info(
                        "Explorer generated %d candidates for '%s' "
                        "(tier=%s, attempt %d/%d)",
                        len(candidates), category_name, tier, attempt, max_attempts,
                    )
                    return candidates[:num_candidates]

                logger.warning(
                    "Explorer produced 0 valid candidates "
                    "(tier=%s, attempt %d/%d) — retrying",
                    tier, attempt, max_attempts,
                )

            except json.JSONDecodeError as e:
                last_error = e
                logger.warning(
                    "Explorer JSON decode failed (tier=%s, attempt %d/%d): %s",
                    tier, attempt, max_attempts, e,
                )
            except Exception as e:
                last_error = e
                logger.error(
                    "Explorer generation failed (tier=%s, attempt %d/%d): %s",
                    tier, attempt, max_attempts, e,
                )

        logger.error(
            "Explorer returned no candidates for '%s' (tier=%s) after %d attempts%s",
            category_name, tier, max_attempts,
            f"; last error: {last_error}" if last_error else "",
        )
        return []

    @staticmethod
    def _resolve_lens(raw_lens, lens_by_id: dict, default_lens):
        """Resolve the model's numeric lens id to ``(lens_id, lens_code)``.

        Accepts an int id, a numeric string, or null. Falls back to the neutral
        default lens when the model omits or mis-specifies the angle, so the
        semantic signature stays meaningful and topics.lens_id stays satisfied.
        """
        lens = None
        # bool is an int subclass — guard against True/False being treated as ids
        if isinstance(raw_lens, bool):
            raw_lens = None
        if isinstance(raw_lens, int):
            lens = lens_by_id.get(raw_lens)
        elif isinstance(raw_lens, str) and raw_lens.strip().isdigit():
            lens = lens_by_id.get(int(raw_lens.strip()))

        if lens is None:
            lens = default_lens
        if lens is None:
            return (None, None)
        return (lens.id, lens.lens_code)

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
        Validate a candidate has the required fields.

        Requires a non-trivial ``concept`` and a non-empty
        ``distinctive_vocabulary`` list (the lexical field). ``lens`` is
        optional (numeric id or null) and ``keywords`` is optional. The floor
        of 6 distinctive words (the prompt asks for 8-15) tolerates genuinely
        small toddler-tier fields without rejecting them.

        Args:
            item: Candidate dict from LLM

        Returns:
            bool: True if valid
        """
        concept = item.get('concept')
        if not concept or len(concept.strip()) < 10:
            logger.debug("Candidate rejected: concept missing or too short")
            return False

        dv = item.get('distinctive_vocabulary')
        if not isinstance(dv, list):
            logger.debug("Candidate rejected: distinctive_vocabulary not a list")
            return False
        dv_clean = [w for w in dv if isinstance(w, str) and w.strip()]
        if len(dv_clean) < 6:
            logger.debug(
                "Candidate rejected: distinctive_vocabulary too small (%d)",
                len(dv_clean),
            )
            return False

        return True
