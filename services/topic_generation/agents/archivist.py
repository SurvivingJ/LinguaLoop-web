"""
Archivist Agent

Manages topic memory and semantic deduplication using vector similarity.
Ensures new topics are sufficiently different from existing ones.
"""

import logging
from typing import List, Tuple, Optional, Dict

from .embedder import EmbeddingService
from ..database_client import TopicDatabaseClient, Lens
from ..config import topic_gen_config

logger = logging.getLogger(__name__)


class ArchivistAgent:
    """Manages topic memory and deduplication via vector similarity."""

    def __init__(
        self,
        db_client: TopicDatabaseClient,
        embedder: EmbeddingService
    ):
        """
        Initialize the Archivist agent.

        Args:
            db_client: Database client for topic queries
            embedder: Embedding service for vector generation
        """
        self.db = db_client
        self.embedder = embedder

        # Cache lens lookup for performance
        self._lens_cache: Dict[int, Lens] = {}
        self._load_lens_cache()

    def _load_lens_cache(self) -> None:
        """Load lens data into cache."""
        lenses = self.db.get_active_lenses()
        self._lens_cache = {lens.id: lens for lens in lenses}

    def get_lens_by_id(self, lens_id: int) -> Optional[Lens]:
        """Get lens by ID from cache."""
        return self._lens_cache.get(lens_id)

    def construct_semantic_signature(
        self,
        category_name: str,
        concept: str,
        lens: Lens,
        keywords: List[str]
    ) -> str:
        """
        Build signature string for embedding.

        The signature captures the semantic essence of a topic in a format
        optimized for embedding comparison.

        Format: "{category}: {concept} [{lens_display}] ({comma_keywords})"

        Args:
            category_name: Category name
            concept: Topic concept description
            lens: Lens object
            keywords: List of keyword strings

        Returns:
            str: Formatted signature for embedding

        Example:
            "Horses: The history of farriery [Historical] (blacksmith, iron, medieval)"
        """
        # Limit keywords to prevent overly long signatures
        kw_str = ', '.join(keywords[:5]) if keywords else ''

        signature = f"{category_name}: {concept} [{lens.display_name}]"

        if kw_str:
            signature += f" ({kw_str})"

        return signature

    def check_novelty(
        self,
        category_id: int,
        semantic_signature: str,
        threshold: float = None
    ) -> Tuple[bool, Optional[str], List[float]]:
        """
        Check if a topic is semantically novel within its category.

        Args:
            category_id: Category FK to search within
            semantic_signature: Formatted topic signature
            threshold: Cosine similarity threshold (defaults to config)

        Returns:
            Tuple of:
                - is_novel: bool - True if topic is sufficiently different
                - rejection_reason: Optional[str] - Reason if rejected
                - embedding: List[float] - The generated embedding (for reuse)

        Process:
            1. Generate embedding for signature
            2. Query database for similar topics in category
            3. If max similarity > threshold, reject

        Example:
            is_novel, reason, embedding = archivist.check_novelty(
                1, "Horses: Farrier [Historical]..."
            )
            if not is_novel:
                print(f"Rejected: {reason}")
        """
        if threshold is None:
            threshold = topic_gen_config.similarity_threshold

        # Generate embedding for the signature
        embedding = self.embedder.embed_single(semantic_signature)

        if not embedding:
            logger.error("Failed to generate embedding for signature")
            return (False, "Embedding generation failed", [])

        # Query for similar topics
        similar_topics = self.db.find_similar_topics(
            category_id=category_id,
            embedding=embedding,
            threshold=threshold
        )

        if similar_topics:
            # Get the most similar topic
            most_similar = similar_topics[0]
            similarity = most_similar.get('similarity', 0)
            existing_concept = most_similar.get('concept_english', 'unknown')

            reason = (
                f"Too similar to existing topic "
                f"(similarity: {similarity:.2%}): '{existing_concept[:50]}...'"
            )

            logger.info(
                f"Topic rejected (duplicate): {semantic_signature[:40]}... "
                f"-> similar to: {existing_concept[:40]}... ({similarity:.2%})"
            )

            return (False, reason, embedding)

        logger.debug(f"Topic is novel: {semantic_signature[:50]}...")
        return (True, None, embedding)

    def batch_check_novelty(
        self,
        category_id: int,
        category_name: str,
        candidates: List[dict],
        lenses: Dict[str, Lens]
    ) -> List[Tuple[dict, bool, Optional[str], List[float]]]:
        """
        Check novelty for multiple candidates.

        This is more efficient than individual checks when processing
        multiple candidates, as it can batch embedding generation.

        Args:
            category_id: Category FK
            category_name: Category name for signature
            candidates: List of candidate dicts with concept, lens_code, keywords
            lenses: Dict mapping lens_code to Lens objects

        Returns:
            List of tuples: (candidate, is_novel, rejection_reason, embedding)
        """
        results = []

        for candidate in candidates:
            lens = lenses.get(candidate.get('lens_code', '').lower())
            if not lens:
                results.append((
                    candidate,
                    False,
                    f"Unknown lens: {candidate.get('lens_code')}",
                    []
                ))
                continue

            signature = self.construct_semantic_signature(
                category_name=category_name,
                concept=candidate.get('concept', ''),
                lens=lens,
                keywords=candidate.get('keywords', [])
            )

            is_novel, reason, embedding = self.check_novelty(
                category_id=category_id,
                semantic_signature=signature
            )

            results.append((candidate, is_novel, reason, embedding))

        return results
