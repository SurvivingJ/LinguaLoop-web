"""
Embedding Service

Generates text embeddings with OpenAI's embedding models, served through
OpenRouter (same model, same vectors as calling OpenAI directly, so stored
embeddings stay comparable). Supports batch embedding for efficiency.
"""

import logging
from typing import List
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)

from services.llm_service import get_client, OPENROUTER_BASE_URL
from ..config import topic_gen_config

logger = logging.getLogger(__name__)


class EmbeddingService:
    """OpenAI-model embedding generation via OpenRouter, with batch support."""

    def __init__(self, api_key: str = None, model: str = None):
        """
        Initialize the embedding service.

        Args:
            api_key: OpenRouter API key (defaults to config)
            model: Embedding model (defaults to config)
        """
        self.api_key = api_key or topic_gen_config.openrouter_api_key
        model = model or topic_gen_config.embedding_model
        # OpenRouter names OpenAI's models with an "openai/" prefix; accept a
        # bare OpenAI name (e.g. an old TOPIC_EMBEDDING_MODEL value) too.
        self.model = model if '/' in model else f'openai/{model}'
        self.dimensions = topic_gen_config.embedding_dimensions

        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY is required for embeddings")

        # Explicit base_url rather than get_client('openrouter'): the global
        # provider can be switched to claude_cli/ollama, neither of which
        # serves embeddings, and that switch must not move this client.
        self.client = get_client(base_url=OPENROUTER_BASE_URL, api_key=self.api_key)
        self.api_call_count = 0

        logger.debug(f"EmbeddingService initialized: model={self.model}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((Exception,)),
        reraise=True
    )
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts in a single API call.

        Args:
            texts: List of strings to embed (max 2048 items per call)

        Returns:
            List[List[float]]: List of embedding vectors (each 1536-dimensional)

        Example:
            texts = ["Horses: Farrier [Historical]", "Horses: Racing [Economic]"]
            vectors = embedder.embed_batch(texts)
        """
        if not texts:
            return []

        # Sanitize input: remove newlines and truncate long texts
        cleaned = [
            text.replace('\n', ' ').strip()[:8000]
            for text in texts
        ]

        response = self.client.embeddings.create(
            input=cleaned,
            model=self.model
        )

        self.api_call_count += 1

        # Extract embeddings in order
        vectors = [item.embedding for item in response.data]

        logger.debug(f"Generated {len(vectors)} embeddings")
        return vectors

    def embed_single(self, text: str) -> List[float]:
        """
        Convenience wrapper for single embedding.

        Args:
            text: String to embed

        Returns:
            List[float]: 1536-dimensional embedding vector
        """
        results = self.embed_batch([text])
        return results[0] if results else []

    def reset_call_count(self) -> None:
        """Reset the API call counter."""
        self.api_call_count = 0
