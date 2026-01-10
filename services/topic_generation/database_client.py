"""
Topic Generation Database Client

Handles all database interactions for the topic generation system.
Uses the existing SupabaseFactory for client management.
"""

import logging
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from uuid import UUID
from dataclasses import dataclass

from ..supabase_factory import get_supabase_admin

logger = logging.getLogger(__name__)


# ============================================================
# Data Models
# ============================================================

@dataclass
class Category:
    """Represents a row from categories table."""
    id: int
    name: str
    status_id: int
    target_language_id: Optional[int]
    last_used_at: Optional[datetime]
    cooldown_days: int


@dataclass
class Language:
    """Represents a row from dim_languages table."""
    id: int
    language_code: str
    language_name: str
    native_name: str


@dataclass
class Lens:
    """Represents a row from dim_lens table."""
    id: int
    lens_code: str
    display_name: str
    description: Optional[str]
    prompt_hint: Optional[str]


@dataclass
class TopicCandidate:
    """Explorer agent output structure."""
    concept: str
    lens_code: str
    keywords: List[str]


@dataclass
class GenerationMetrics:
    """Metrics for topic_generation_runs table."""
    run_date: datetime
    category_id: int
    category_name: str
    topics_generated: int = 0
    topics_rejected_similarity: int = 0
    topics_rejected_gatekeeper: int = 0
    candidates_proposed: int = 0
    api_calls_llm: int = 0
    api_calls_embedding: int = 0
    total_cost_usd: float = 0.0
    execution_time_seconds: Optional[int] = None
    error_message: Optional[str] = None


# ============================================================
# Database Client
# ============================================================

class TopicDatabaseClient:
    """Supabase database client with typed methods for topic generation."""

    def __init__(self):
        self.client = get_supabase_admin()
        if not self.client:
            raise RuntimeError("Supabase admin client not available")

        self._lens_cache: Optional[Dict[int, Lens]] = None
        self._language_cache: Optional[Dict[int, Language]] = None
        self._status_cache: Optional[Dict[str, int]] = None

    # ============================================================
    # DIMENSION TABLE QUERIES
    # ============================================================

    def get_active_languages(self) -> List[Language]:
        """
        Fetch all active target languages.

        Returns:
            List[Language]: Active languages sorted by display_order
        """
        if self._language_cache is not None:
            return list(self._language_cache.values())

        response = self.client.rpc('get_active_languages').execute()

        if not response.data:
            logger.warning("No active languages found")
            return []

        languages = [
            Language(
                id=row['id'],
                language_code=row['language_code'],
                language_name=row['language_name'],
                native_name=row['native_name']
            )
            for row in response.data
        ]

        self._language_cache = {lang.id: lang for lang in languages}
        logger.info(f"Loaded {len(languages)} active languages")
        return languages

    def get_active_lenses(self) -> List[Lens]:
        """
        Fetch all active lenses for topic generation.

        Returns:
            List[Lens]: Active lenses sorted by sort_order
        """
        if self._lens_cache is not None:
            return list(self._lens_cache.values())

        response = self.client.table('dim_lens') \
            .select('id, lens_code, display_name, description, prompt_hint') \
            .eq('is_active', True) \
            .order('sort_order') \
            .execute()

        if not response.data:
            logger.warning("No active lenses found")
            return []

        lenses = [
            Lens(
                id=row['id'],
                lens_code=row['lens_code'],
                display_name=row['display_name'],
                description=row.get('description'),
                prompt_hint=row.get('prompt_hint')
            )
            for row in response.data
        ]

        self._lens_cache = {lens.id: lens for lens in lenses}
        logger.info(f"Loaded {len(lenses)} active lenses")
        return lenses

    def get_lens_by_code(self, lens_code: str) -> Optional[Lens]:
        """
        Lookup lens by code using cached data.

        Args:
            lens_code: Lens code (e.g., 'historical')

        Returns:
            Lens object or None if not found
        """
        if self._lens_cache is None:
            self.get_active_lenses()

        for lens in self._lens_cache.values():
            if lens.lens_code.lower() == lens_code.lower():
                return lens
        return None

    def _get_status_id(self, status_code: str) -> int:
        """Get status ID by code with caching."""
        if self._status_cache is None:
            response = self.client.table('dim_status') \
                .select('id, status_code') \
                .execute()
            self._status_cache = {
                row['status_code']: row['id']
                for row in response.data
            }

        return self._status_cache.get(status_code, 1)  # Default to 'pending'

    # ============================================================
    # CATEGORY QUERIES
    # ============================================================

    def get_next_category(self) -> Optional[Category]:
        """
        Fetch next eligible category for topic generation.

        Uses RPC function that handles cooldown logic.

        Returns:
            Category object or None if no eligible categories
        """
        response = self.client.rpc('get_next_category').execute()

        if not response.data:
            logger.warning("No eligible categories found")
            return None

        row = response.data[0]
        category = Category(
            id=row['id'],
            name=row['name'],
            status_id=row['status_id'],
            target_language_id=row.get('target_language_id'),
            last_used_at=datetime.fromisoformat(row['last_used_at'].replace('Z', '+00:00'))
                if row.get('last_used_at') else None,
            cooldown_days=row['cooldown_days']
        )

        logger.info(f"Selected category: {category.name} (id={category.id})")
        return category

    def update_category_usage(self, category_id: int) -> None:
        """
        Update last_used_at timestamp for a category.

        Args:
            category_id: Category primary key
        """
        self.client.table('categories') \
            .update({
                'last_used_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat()
            }) \
            .eq('id', category_id) \
            .execute()

        logger.info(f"Updated category usage: id={category_id}")

    def increment_category_topics(self, category_id: int, count: int = 1) -> None:
        """Increment the total_topics_generated counter for a category."""
        # Fetch current count
        response = self.client.table('categories') \
            .select('total_topics_generated') \
            .eq('id', category_id) \
            .single() \
            .execute()

        current = response.data.get('total_topics_generated', 0) or 0

        self.client.table('categories') \
            .update({'total_topics_generated': current + count}) \
            .eq('id', category_id) \
            .execute()

    # ============================================================
    # TOPIC QUERIES
    # ============================================================

    def find_similar_topics(
        self,
        category_id: int,
        embedding: List[float],
        threshold: float = 0.85
    ) -> List[Dict]:
        """
        Vector similarity search within a category.

        Args:
            category_id: Category to search within
            embedding: 1536-dimensional vector
            threshold: Cosine similarity threshold (default 0.85)

        Returns:
            List of dicts with keys: id, concept_english, similarity
        """
        response = self.client.rpc('match_topics', {
            'query_category': category_id,
            'query_embedding': embedding,
            'match_threshold': threshold,
            'match_count': 5
        }).execute()

        if response.data:
            logger.debug(f"Found {len(response.data)} similar topics")

        return response.data or []

    def insert_topic(
        self,
        category_id: int,
        concept: str,
        lens_id: int,
        keywords: List[str],
        embedding: List[float],
        semantic_signature: str
    ) -> UUID:
        """
        Insert new topic into topics table.

        Args:
            category_id: FK to categories
            concept: English description
            lens_id: FK to dim_lens
            keywords: List of strings
            embedding: 1536-dim vector
            semantic_signature: Human-readable signature

        Returns:
            UUID: Generated topic ID
        """
        data = {
            'category_id': category_id,
            'concept_english': concept,
            'lens_id': lens_id,
            'keywords': keywords,
            'embedding': embedding,
            'semantic_signature': semantic_signature
        }

        response = self.client.table('topics') \
            .insert(data) \
            .execute()

        topic_id = UUID(response.data[0]['id'])
        logger.info(f"Inserted topic: id={topic_id}, concept={concept[:50]}...")
        return topic_id

    # ============================================================
    # QUEUE QUERIES
    # ============================================================

    def batch_insert_queue(self, items: List[Tuple[UUID, int]]) -> int:
        """
        Batch insert topic-language pairs into production queue.

        Args:
            items: List of (topic_id, language_id) tuples

        Returns:
            int: Number of rows inserted
        """
        if not items:
            return 0

        pending_status_id = self._get_status_id('pending')

        rows = [
            {
                'topic_id': str(topic_id),
                'language_id': lang_id,
                'status_id': pending_status_id
            }
            for topic_id, lang_id in items
        ]

        response = self.client.table('production_queue') \
            .insert(rows) \
            .execute()

        count = len(response.data)
        logger.info(f"Queued {count} topic-language pairs")
        return count

    # ============================================================
    # PROMPT QUERIES
    # ============================================================

    def get_prompt_template(self, task_name: str, language_id: int = 2) -> Optional[str]:
        """
        Fetch prompt template by task name and language ID.

        Uses language_id (integer) to match actual prompt_templates table structure.
        Falls back to English (language_id=2) if not found for specific language.

        Args:
            task_name: 'explorer_ideation' or 'gatekeeper_check'
            language_id: Language ID from dim_languages (1=Chinese, 2=English, 3=Japanese)

        Returns:
            str: Template text with {placeholders}, or None if not found
        """
        # Try language-specific template first
        response = self.client.table('prompt_templates') \
            .select('template_text') \
            .eq('task_name', task_name) \
            .eq('language_id', language_id) \
            .eq('is_active', True) \
            .order('version', desc=True) \
            .limit(1) \
            .execute()

        if response.data:
            logger.debug(f"Loaded prompt template: {task_name} for language_id={language_id}")
            return response.data[0]['template_text']

        # Fallback to English (language_id=2) if not found
        if language_id != 2:
            response = self.client.table('prompt_templates') \
                .select('template_text') \
                .eq('task_name', task_name) \
                .eq('language_id', 2) \
                .eq('is_active', True) \
                .order('version', desc=True) \
                .limit(1) \
                .execute()

            if response.data:
                logger.debug(f"Loaded fallback English prompt template: {task_name}")
                return response.data[0]['template_text']

        logger.warning(f"Prompt template not found: {task_name} for language_id={language_id}")
        return None

    # ============================================================
    # METRICS QUERIES
    # ============================================================

    def insert_generation_run(self, metrics: GenerationMetrics) -> None:
        """
        Insert daily run metrics for monitoring.

        Args:
            metrics: GenerationMetrics dataclass
        """
        data = {
            'run_date': metrics.run_date.date().isoformat(),
            'category_id': metrics.category_id,
            'category_name': metrics.category_name,
            'topics_generated': metrics.topics_generated,
            'topics_rejected_similarity': metrics.topics_rejected_similarity,
            'topics_rejected_gatekeeper': metrics.topics_rejected_gatekeeper,
            'candidates_proposed': metrics.candidates_proposed,
            'api_calls_llm': metrics.api_calls_llm,
            'api_calls_embedding': metrics.api_calls_embedding,
            'total_cost_usd': float(metrics.total_cost_usd),
            'execution_time_seconds': metrics.execution_time_seconds,
            'error_message': metrics.error_message
        }

        self.client.table('topic_generation_runs') \
            .insert(data) \
            .execute()

        logger.info(f"Logged generation run metrics: {metrics.topics_generated} topics")

    # ============================================================
    # UTILITY METHODS
    # ============================================================

    def clear_caches(self) -> None:
        """Clear all cached dimension data."""
        self._lens_cache = None
        self._language_cache = None
        self._status_cache = None
        logger.debug("Cleared database caches")
