"""
Embedding Service

Generates text embeddings using OpenAI's embedding models.
Supports batch embedding for efficiency.
"""

import logging
from typing import List
from openai import OpenAI
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)

from ..config import topic_gen_config

logger = logging.getLogger(__name__)


class EmbeddingService:
    """OpenAI embedding generation with batch support."""

    def __init__(self, api_key: str = None, model: str = None):
        """
        Initialize the embedding service.

        Args:
            api_key: OpenAI API key (defaults to config)
            model: Embedding model (defaults to config)
        """
        self.api_key = api_key or topic_gen_config.openai_api_key
        self.model = model or topic_gen_config.embedding_model
        self.dimensions = topic_gen_config.embedding_dimensions

        if not self.api_key:
            raise ValueError("OpenAI API key is required for embeddings")

        self.client = OpenAI(api_key=self.api_key)
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
