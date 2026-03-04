"""
Gatekeeper Agent

Validates cultural and linguistic appropriateness of topics.
Ensures topics are suitable for each target language/culture.
"""

import logging
from typing import List

from .base import BaseAgent
from ..config import topic_gen_config
from ..database_client import TopicCandidate, Language

logger = logging.getLogger(__name__)


class GatekeeperAgent(BaseAgent):
    """Validates cultural and linguistic appropriateness of topics."""

    # OpenRouter base URL
    OPENROUTER_BASE_URL = 'https://openrouter.ai/api/v1'

    def __init__(self, api_key: str = None, model: str = None):
        """
        Initialize the Gatekeeper agent.

        Args:
            api_key: OpenRouter API key (defaults to config)
            model: LLM model to use (defaults to config)
        """
        super().__init__(
            model=model or topic_gen_config.llm_model,
            api_key=api_key or topic_gen_config.openrouter_api_key,
            base_url=self.OPENROUTER_BASE_URL,
            name="Gatekeeper"
        )
        self.rejection_count = 0

    def validate_for_language(
        self,
        candidate: TopicCandidate,
        language: Language,
        prompt_template: str
    ) -> bool:
        """
        Check if topic is appropriate for a target language.

        Args:
            candidate: TopicCandidate with concept, lens_code, keywords
            language: Language object with native_name, language_code
            prompt_template: Template with placeholders

        Returns:
            bool: True if approved, False if rejected

        Template Placeholders:
            - {topic_concept}: candidate.concept
            - {lens}: candidate.lens_code
            - {target_language}: language.native_name
            - {language_code}: language.language_code
            - {keywords}: comma-separated keywords
        """
        keywords_str = ', '.join(candidate.keywords[:5]) if candidate.keywords else 'none'

        prompt = prompt_template.format(
            topic_concept=candidate.concept,
            lens=candidate.lens_code,
            target_language=language.native_name,
            language_code=language.language_code,
            keywords=keywords_str
        )

        try:
            response = self._call_llm(
                prompt=prompt,
                json_mode=False,
                temperature=topic_gen_config.gatekeeper_temperature
            )

            # Parse response - look for YES or NO
            decision = self._parse_decision(response)

            logger.info(
                f"Gatekeeper: '{candidate.concept[:30]}...' "
                f"for {language.language_code}: {'APPROVED' if decision else 'REJECTED'}"
            )

            if not decision:
                self.rejection_count += 1

            return decision

        except Exception as e:
            logger.error(
                f"Gatekeeper validation failed for {language.language_code}: {e}"
            )
            # Fail safe: reject on error
            self.rejection_count += 1
            return False

    def _parse_decision(self, response: str) -> bool:
        """
        Parse YES/NO decision from LLM response.

        Args:
            response: Raw LLM response

        Returns:
            bool: True for YES, False for NO or ambiguous
        """
        response_lower = response.lower().strip()

        # Check for explicit YES at the start
        if response_lower.startswith('yes'):
            return True

        # Check for explicit NO at the start
        if response_lower.startswith('no'):
            return False

        # Check for YES anywhere (less strict)
        if 'yes' in response_lower and 'no' not in response_lower:
            return True

        # Default to rejection for ambiguous responses
        logger.debug(f"Ambiguous Gatekeeper response: {response[:100]}")
        return False

    def validate_for_all_languages(
        self,
        candidate: TopicCandidate,
        languages: List[Language],
        prompt_template: str,
        short_circuit_threshold: int = None
    ) -> List[Language]:
        """
        Validate topic across all languages with short-circuit logic.

        Args:
            candidate: Topic to validate
            languages: All active languages to check
            prompt_template: Gatekeeper prompt template
            short_circuit_threshold: Stop after N consecutive rejections

        Returns:
            List[Language]: Languages that approved the topic

        Short-Circuit Logic:
            If a topic gets rejected by N consecutive languages,
            it's likely fundamentally unsuitable and we stop early.
        """
        if short_circuit_threshold is None:
            short_circuit_threshold = topic_gen_config.gatekeeper_short_circuit_threshold

        approved = []
        consecutive_rejections = 0

        for lang in languages:
            # Check short-circuit
            if consecutive_rejections >= short_circuit_threshold:
                logger.info(
                    f"Short-circuit: {consecutive_rejections}+ rejections for "
                    f"'{candidate.concept[:30]}...'"
                )
                break

            is_approved = self.validate_for_language(
                candidate=candidate,
                language=lang,
                prompt_template=prompt_template
            )

            if is_approved:
                approved.append(lang)
                consecutive_rejections = 0
            else:
                consecutive_rejections += 1

        return approved

    def reset_counts(self) -> None:
        """Reset rejection counter."""
        self.rejection_count = 0
        self.reset_call_count()
