"""
Base Agent Class

Common functionality for the topic-generation agents: every completion goes
through services.llm_service.call_llm, which owns client pooling, retry on
transient errors, and llm_calls cost logging.
"""

import json
import logging
from typing import Optional

from services import llm_service

logger = logging.getLogger(__name__)

PIPELINE = 'topic_generation'


class BaseAgent:
    """Base class for AI agents with common utilities."""

    def __init__(
        self,
        model: str,
        api_key: str,
        base_url: Optional[str] = None,
        name: str = "BaseAgent"
    ):
        """
        Initialize the agent.

        Args:
            model: Model identifier (e.g., 'google/gemini-3.5-flash-lite')
            api_key: Kept for signature compatibility; the key is resolved
                by llm_service from the environment.
            base_url: Kept for signature compatibility.
            name: Agent name for logging and the llm_calls task tag
        """
        self.model = model
        self.name = name
        self.api_call_count = 0
        logger.debug(f"{name} initialized with model: {model}")

    @staticmethod
    def _provider() -> str:
        # Topic generation runs on OpenRouter unless the process default was
        # switched to the headless CLI transport.
        if llm_service.LLM_DEFAULT_PROVIDER == 'claude_cli':
            return 'claude_cli'
        return 'openrouter'

    def _call_llm(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        json_mode: bool = False,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        model: Optional[str] = None,
    ) -> str:
        """
        Make one LLM call and return the response text.

        With json_mode the API is asked for a JSON object and the parsed
        payload is re-serialised, so callers keep receiving a string. A
        malformed JSON reply raises json.JSONDecodeError (no hidden repair
        turn — callers run their own retry loop).

        Raises:
            Exception: On API failure after llm_service's retries
        """
        effective_model = model or self.model
        logger.debug(f"{self.name} calling LLM: model={effective_model}, temp={temperature}")

        result = llm_service.call_llm(
            prompt,
            model=effective_model,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format='json_object' if json_mode else 'text',
            provider=self._provider(),
            timeout=120,
            pipeline=PIPELINE,
            task_name=self.name.lower(),
            allow_internal_repair=False,
        )
        self.api_call_count += 1

        content = result if isinstance(result, str) else json.dumps(result, ensure_ascii=False)
        logger.debug(f"{self.name} received response: {len(content)} chars")
        return content

    def reset_call_count(self) -> None:
        """Reset the API call counter."""
        self.api_call_count = 0
