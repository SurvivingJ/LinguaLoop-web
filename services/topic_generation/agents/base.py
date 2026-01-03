"""
Base Agent Class

Provides common functionality for all AI agents including:
- OpenAI/OpenRouter client management
- Retry logic with exponential backoff
- API call tracking
"""

import logging
from typing import Optional
from openai import OpenAI
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)

logger = logging.getLogger(__name__)


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
            model: Model identifier (e.g., 'google/gemini-2.0-flash-exp')
            api_key: API key for authentication
            base_url: Optional base URL (for OpenRouter, use 'https://openrouter.ai/api/v1')
            name: Agent name for logging
        """
        self.model = model
        self.name = name
        self.api_call_count = 0

        client_kwargs = {'api_key': api_key}
        if base_url:
            client_kwargs['base_url'] = base_url

        self.client = OpenAI(**client_kwargs)
        logger.debug(f"{name} initialized with model: {model}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((Exception,)),
        reraise=True
    )
    def _call_llm(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        json_mode: bool = False,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> str:
        """
        Make LLM API call with retry logic.

        Args:
            prompt: User message content
            system_prompt: Optional system message
            json_mode: Enable JSON response format
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Optional max tokens limit

        Returns:
            str: LLM response content

        Raises:
            Exception: On API failure after retries
        """
        messages = []

        if system_prompt:
            messages.append({'role': 'system', 'content': system_prompt})

        messages.append({'role': 'user', 'content': prompt})

        payload = {
            'model': self.model,
            'messages': messages,
            'temperature': temperature
        }

        if json_mode:
            payload['response_format'] = {'type': 'json_object'}

        if max_tokens:
            payload['max_tokens'] = max_tokens

        logger.debug(f"{self.name} calling LLM: model={self.model}, temp={temperature}")

        response = self.client.chat.completions.create(**payload)
        self.api_call_count += 1

        if not response.choices:
            raise ValueError("No choices returned from API")

        content = response.choices[0].message.content
        if content is None:
            raise ValueError("API returned None content")

        logger.debug(f"{self.name} received response: {len(content)} chars")
        return content

    def reset_call_count(self) -> None:
        """Reset the API call counter."""
        self.api_call_count = 0
