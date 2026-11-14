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

    def embed_signatures(self, signatures: List[str]) -> List[List[float]]:
        """Embed many signatures in one API call, in input order."""
        if not signatures:
            return []
        vectors = self.embedder.embed_batch(signatures)
        if len(vectors) != len(signatures):
            raise ValueError(
                f"Embedding batch returned {len(vectors)} vectors "
                f"for {len(signatures)} signatures"
            )
        return vectors

    def check_novelty(
        self,
        category_id: Optional[int],
        semantic_signature: str,
        threshold: float = None,
        scope: str = 'category',
        embedding: Optional[List[float]] = None,
    ) -> Tuple[bool, Optional[str], List[float]]:
        """
        Check if a topic is semantically novel.

        Args:
            category_id: Category FK. Required when scope='category' (the
                search is scoped to it); optional under scope='global' — kept
                only for logging/diagnostics there, since match_topics_global
                searches across ALL categories (topics has no language_id
                column, so there is no language-scoped variant to worry about).
            semantic_signature: Formatted topic signature
            threshold: Cosine similarity threshold (defaults to config)
            embedding: Precomputed embedding of the signature (see
                embed_signatures); generated here when omitted.
            scope: 'category' (default, unchanged behavior) or 'global' —
                see TASK-740 finding #1: a near-duplicate topic can sail
                through as "novel" under category scope if it was previously
                filed under a different category (e.g. the recurring
                "cat t-shirt" topic).

        Returns:
            Tuple of:
                - is_novel: bool - True if topic is sufficiently different
                - rejection_reason: Optional[str] - Reason if rejected
                - embedding: List[float] - The generated embedding (for reuse)

        Process:
            1. Generate embedding for signature
            2. Query database for similar topics (category-scoped or global)
            3. If max similarity > threshold, reject

        Example:
            is_novel, reason, embedding = archivist.check_novelty(
                1, "Horses: Farrier [Historical]...", scope='global'
            )
            if not is_novel:
                print(f"Rejected: {reason}")
        """
        if threshold is None:
            threshold = topic_gen_config.similarity_threshold

        if scope == 'category' and category_id is None:
            raise ValueError("category_id is required when scope='category'")

        if embedding is None:
            embedding = self.embedder.embed_single(semantic_signature)

        if not embedding:
            logger.error("Failed to generate embedding for signature")
            return (False, "Embedding generation failed", [])

        # Query for similar topics (category_id is diagnostics-only under
        # scope='global' — the RPC itself ignores it)
        similar_topics = self.db.find_similar_topics(
            category_id=category_id,
            embedding=embedding,
            threshold=threshold,
            scope=scope
        )

        if similar_topics:
            # Get the most similar topic
            most_similar = similar_topics[0]
            similarity = most_similar.get('similarity', 0)
            existing_concept = most_similar.get('concept_english', 'unknown')
            existing_category = most_similar.get('category_id')

            reason = (
                f"Too similar to existing topic "
                f"(similarity: {similarity:.2%}): '{existing_concept[:50]}...'"
            )
            if scope == 'global' and existing_category is not None:
                reason += f" [category_id={existing_category}]"

            logger.info(
                f"Topic rejected (duplicate, scope={scope}, category_id={category_id}): "
                f"{semantic_signature[:40]}... "
                f"-> similar to: {existing_concept[:40]}... ({similarity:.2%})"
            )

            return (False, reason, embedding)

        logger.debug(f"Topic is novel: {semantic_signature[:50]}...")
        return (True, None, embedding)
