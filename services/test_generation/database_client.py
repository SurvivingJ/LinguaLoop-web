"""
Test Generation Database Client

Handles all database interactions for the test generation system.
Uses the existing SupabaseFactory for client management.
"""

import logging
from datetime import datetime
from typing import List, Dict, Optional, Any
from uuid import UUID, uuid4
from dataclasses import dataclass, field

from ..supabase_factory import get_supabase_admin

logger = logging.getLogger(__name__)


# ============================================================
# Data Models
# ============================================================

@dataclass
class QueueItem:
    """Represents a row from production_queue table."""
    id: UUID
    topic_id: UUID
    language_id: int
    status_id: int
    created_at: datetime
    tests_generated: int = 0
    error_log: Optional[str] = None


@dataclass
class Topic:
    """Represents a row from topics table."""
    id: UUID
    category_id: int
    concept_english: str
    lens_id: int
    keywords: List[str]
    semantic_signature: Optional[str] = None


@dataclass
class LanguageConfig:
    """Extended language configuration for test generation."""
    id: int
    language_code: str
    language_name: str
    native_name: str
    prose_model: str = 'google/gemini-2.0-flash-exp'
    question_model: str = 'google/gemini-2.0-flash-exp'
    tts_voice_ids: List[str] = field(default_factory=lambda: ['alloy'])
    tts_speed: float = 1.0
    grammar_check_enabled: bool = False


@dataclass
class CEFRConfig:
    """CEFR level configuration."""
    id: int
    cefr_code: str
    difficulty_min: int
    difficulty_max: int
    word_count_min: int
    word_count_max: int
    initial_elo: int


@dataclass
class QuestionType:
    """Question type definition."""
    id: int
    type_code: str
    type_name: str
    description: Optional[str]
    cognitive_level: int


@dataclass
class GeneratedTest:
    """Data for inserting a generated test."""
    id: UUID
    slug: str
    language_id: int
    language_name: str
    topic_id: UUID
    topic_name: str
    difficulty: int
    transcript: str
    gen_user: str
    initial_elo: int
    audio_url: str
    title: Optional[str] = None


@dataclass
class GeneratedQuestion:
    """Data for inserting a generated question."""
    test_id: UUID
    question_id: str
    question_text: str
    choices: List[str]
    answer: str
    question_type_id: Optional[int] = None


@dataclass
class TestGenMetrics:
    """Metrics for test_generation_runs table."""
    run_date: datetime
    queue_items_processed: int = 0
    tests_generated: int = 0
    tests_failed: int = 0
    execution_time_seconds: Optional[int] = None
    error_message: Optional[str] = None


# ============================================================
# Database Client
# ============================================================

class TestDatabaseClient:
    """Supabase database client for test generation."""

    def __init__(self):
        self.client = get_supabase_admin()
        if not self.client:
            raise RuntimeError("Supabase admin client not available")

        # Caches
        self._language_cache: Optional[Dict[int, LanguageConfig]] = None
        self._cefr_cache: Optional[Dict[int, CEFRConfig]] = None
        self._question_type_cache: Optional[Dict[str, QuestionType]] = None
        self._distribution_cache: Optional[Dict[int, List[str]]] = None
        self._status_cache: Optional[Dict[str, int]] = None
        self._config_cache: Optional[Dict[str, str]] = None

    # ============================================================
    # QUEUE OPERATIONS
    # ============================================================

    def get_pending_queue_items(self, limit: int = 50) -> List[QueueItem]:
        """
        Fetch pending items from production_queue for active languages only.

        Args:
            limit: Maximum number of items to fetch

        Returns:
            List[QueueItem]: Pending queue items ordered by created_at
        """
        pending_status_id = self._get_status_id('pending')

        # Get active language IDs first
        active_langs = self.client.table('dim_languages') \
            .select('id') \
            .eq('is_active', True) \
            .execute()

        active_lang_ids = [lang['id'] for lang in active_langs.data] if active_langs.data else []

        if not active_lang_ids:
            logger.warning("No active languages found - skipping test generation")
            return []

        logger.info(f"Active language IDs: {active_lang_ids}")

        response = self.client.table('production_queue') \
            .select('*') \
            .eq('status_id', pending_status_id) \
            .in_('language_id', active_lang_ids) \
            .order('created_at') \
            .limit(limit) \
            .execute()

        if not response.data:
            logger.info("No pending queue items found for active languages")
            return []

        items = [
            QueueItem(
                id=UUID(row['id']),
                topic_id=UUID(row['topic_id']),
                language_id=row['language_id'],
                status_id=row['status_id'],
                created_at=datetime.fromisoformat(
                    row['created_at'].replace('Z', '+00:00')
                ),
                tests_generated=row.get('tests_generated', 0) or 0,
                error_log=row.get('error_log')
            )
            for row in response.data
        ]

        logger.info(f"Found {len(items)} pending queue items")
        return items

    def update_queue_item_status(
        self,
        queue_id: UUID,
        status_code: str,
        tests_generated: int = 0,
        error_log: Optional[str] = None
    ) -> None:
        """
        Update queue item status and tracking fields.

        Args:
            queue_id: Queue item UUID
            status_code: New status ('processing', 'active', 'rejected')
            tests_generated: Number of tests generated
            error_log: Error message if any
        """
        status_id = self._get_status_id(status_code)

        update_data = {
            'status_id': status_id,
            'tests_generated': tests_generated,
            'processed_at': datetime.utcnow().isoformat()
        }

        if error_log:
            update_data['error_log'] = error_log

        self.client.table('production_queue') \
            .update(update_data) \
            .eq('id', str(queue_id)) \
            .execute()

        logger.debug(f"Updated queue item {queue_id} to status '{status_code}'")

    def mark_queue_processing(self, queue_id: UUID) -> None:
        """Mark queue item as processing."""
        self.update_queue_item_status(queue_id, 'processing')

    def mark_queue_completed(self, queue_id: UUID, tests_generated: int) -> None:
        """Mark queue item as completed (active)."""
        self.update_queue_item_status(
            queue_id,
            'active',
            tests_generated=tests_generated
        )

    def mark_queue_failed(self, queue_id: UUID, error_message: str) -> None:
        """Mark queue item as failed (rejected)."""
        self.update_queue_item_status(
            queue_id,
            'rejected',
            error_log=error_message
        )

    # ============================================================
    # TOPIC QUERIES
    # ============================================================

    def get_topic(self, topic_id: UUID) -> Optional[Topic]:
        """
        Fetch topic details by ID.

        Args:
            topic_id: Topic UUID

        Returns:
            Topic object or None
        """
        response = self.client.table('topics') \
            .select('id, category_id, concept_english, lens_id, keywords, semantic_signature') \
            .eq('id', str(topic_id)) \
            .single() \
            .execute()

        if not response.data:
            logger.warning(f"Topic not found: {topic_id}")
            return None

        row = response.data
        return Topic(
            id=UUID(row['id']),
            category_id=row['category_id'],
            concept_english=row['concept_english'],
            lens_id=row['lens_id'],
            keywords=row.get('keywords', []) or [],
            semantic_signature=row.get('semantic_signature')
        )

    def get_category_name(self, category_id: int) -> str:
        """Get category name by ID."""
        response = self.client.table('categories') \
            .select('name') \
            .eq('id', category_id) \
            .single() \
            .execute()

        return response.data.get('name', 'Unknown') if response.data else 'Unknown'

    # ============================================================
    # LANGUAGE CONFIGURATION
    # ============================================================

    def get_language_config(self, language_id: int) -> Optional[LanguageConfig]:
        """
        Fetch language configuration with model settings.

        Args:
            language_id: Language ID

        Returns:
            LanguageConfig object or None
        """
        if self._language_cache and language_id in self._language_cache:
            return self._language_cache[language_id]

        response = self.client.table('dim_languages') \
            .select('*') \
            .eq('id', language_id) \
            .single() \
            .execute()

        if not response.data:
            logger.warning(f"Language not found: {language_id}")
            return None

        row = response.data

        # Parse TTS voice IDs from JSONB
        tts_voice_ids = row.get('tts_voice_ids', ['alloy'])
        if isinstance(tts_voice_ids, str):
            import json
            try:
                tts_voice_ids = json.loads(tts_voice_ids)
            except Exception:
                tts_voice_ids = ['alloy']

        config = LanguageConfig(
            id=row['id'],
            language_code=row['language_code'],
            language_name=row['language_name'],
            native_name=row.get('native_name') or row['language_name'],
            prose_model=row.get('prose_model', 'google/gemini-2.0-flash-exp'),
            question_model=row.get('question_model', 'google/gemini-2.0-flash-exp'),
            tts_voice_ids=tts_voice_ids,
            tts_speed=float(row.get('tts_speed', 1.0)),
            grammar_check_enabled=row.get('grammar_check_enabled', False)
        )

        # Cache the result
        if self._language_cache is None:
            self._language_cache = {}
        self._language_cache[language_id] = config

        return config

    # ============================================================
    # CEFR CONFIGURATION
    # ============================================================

    def get_cefr_config(self, difficulty: int) -> Optional[CEFRConfig]:
        """
        Get CEFR configuration for a difficulty level.

        Args:
            difficulty: Difficulty level 1-9

        Returns:
            CEFRConfig object or None
        """
        if self._cefr_cache is None:
            self._load_cefr_cache()

        # Find matching CEFR level
        for cefr in self._cefr_cache.values():
            if cefr.difficulty_min <= difficulty <= cefr.difficulty_max:
                return cefr

        logger.warning(f"No CEFR config found for difficulty {difficulty}")
        return None

    def _load_cefr_cache(self) -> None:
        """Load all CEFR levels into cache."""
        response = self.client.table('dim_cefr_levels') \
            .select('*') \
            .execute()

        self._cefr_cache = {}
        if response.data:
            for row in response.data:
                cefr = CEFRConfig(
                    id=row['id'],
                    cefr_code=row['cefr_code'],
                    difficulty_min=row['difficulty_min'],
                    difficulty_max=row['difficulty_max'],
                    word_count_min=row['word_count_min'],
                    word_count_max=row['word_count_max'],
                    initial_elo=row['initial_elo']
                )
                self._cefr_cache[cefr.id] = cefr

        logger.info(f"Loaded {len(self._cefr_cache)} CEFR levels")

    def get_initial_elo(self, difficulty: int) -> int:
        """Get initial ELO rating for a difficulty level."""
        cefr = self.get_cefr_config(difficulty)
        if cefr:
            return cefr.initial_elo

        # Fallback to hardcoded values
        difficulty_to_elo = {
            1: 800, 2: 950, 3: 1100,
            4: 1250, 5: 1400, 6: 1550,
            7: 1700, 8: 1850, 9: 2000
        }
        return difficulty_to_elo.get(difficulty, 1400)

    def get_active_test_types(self) -> List[dict]:
        """
        Fetch active test types from dim_test_types.

        Returns:
            List of dicts with keys: id, type_code, requires_audio
        """
        response = self.client.table('dim_test_types') \
            .select('id, type_code, requires_audio') \
            .eq('is_active', True) \
            .execute()

        return response.data if response.data else []

    def get_word_count_range(self, difficulty: int) -> tuple:
        """Get word count range for a difficulty level."""
        cefr = self.get_cefr_config(difficulty)
        if cefr:
            return (cefr.word_count_min, cefr.word_count_max)

        # Fallback defaults
        defaults = {
            1: (80, 150), 2: (80, 150),
            3: (120, 200), 4: (120, 200),
            5: (200, 300),
            6: (300, 400),
            7: (400, 600),
            8: (600, 900), 9: (600, 900)
        }
        return defaults.get(difficulty, (200, 300))

    # ============================================================
    # QUESTION TYPE DISTRIBUTION
    # ============================================================

    def get_question_types(self) -> Dict[str, QuestionType]:
        """Get all active question types."""
        if self._question_type_cache is not None:
            return self._question_type_cache

        response = self.client.table('dim_question_types') \
            .select('*') \
            .eq('is_active', True) \
            .order('display_order') \
            .execute()

        self._question_type_cache = {}
        if response.data:
            for row in response.data:
                qt = QuestionType(
                    id=row['id'],
                    type_code=row['type_code'],
                    type_name=row['type_name'],
                    description=row.get('description'),
                    cognitive_level=row['cognitive_level']
                )
                self._question_type_cache[qt.type_code] = qt

        logger.info(f"Loaded {len(self._question_type_cache)} question types")
        return self._question_type_cache

    def get_question_distribution(self, difficulty: int) -> List[str]:
        """
        Get question type distribution for a difficulty level.

        Args:
            difficulty: Difficulty level 1-9

        Returns:
            List of question type codes (e.g., ['literal_detail', 'main_idea', ...])
        """
        if self._distribution_cache is None:
            self._load_distribution_cache()

        if difficulty in self._distribution_cache:
            return self._distribution_cache[difficulty]

        # Fallback to default distribution
        logger.warning(f"No distribution found for difficulty {difficulty}, using default")
        return ['literal_detail', 'literal_detail', 'main_idea', 'main_idea', 'inference']

    def _load_distribution_cache(self) -> None:
        """Load question type distributions into cache."""
        response = self.client.table('question_type_distributions') \
            .select('*') \
            .execute()

        self._distribution_cache = {}
        if response.data:
            for row in response.data:
                difficulty = row['difficulty']
                types = []
                for i in range(1, 6):
                    type_code = row.get(f'question_type_{i}')
                    if type_code:
                        types.append(type_code)
                if types:
                    self._distribution_cache[difficulty] = types

        logger.info(f"Loaded distributions for {len(self._distribution_cache)} difficulty levels")

    def get_question_type_id(self, type_code: str) -> Optional[int]:
        """Get question type ID by code."""
        types = self.get_question_types()
        if type_code in types:
            return types[type_code].id
        return None

    # ============================================================
    # PROMPT TEMPLATES
    # ============================================================

    def get_prompt_template(
        self,
        task_name: str,
        language_id: int
    ) -> Optional[str]:
        """
        Fetch prompt template by task name and language ID.

        Uses language_id (integer) to match actual prompt_templates table structure.
        Falls back to English (language_id=2) if not found for specific language.

        Args:
            task_name: Template name (e.g., 'prose_generation', 'question_literal_detail')
            language_id: Language ID from dim_languages (1=Chinese, 2=English, 3=Japanese)

        Returns:
            Template text or None
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
    # TEST INSERTION
    # ============================================================

    def insert_test(self, test: GeneratedTest) -> str:
        """
        Insert a new test into the tests table.

        Args:
            test: GeneratedTest data

        Returns:
            str: The test slug
        """
        data = {
            'id': str(test.id),
            'slug': test.slug,
            'language_id': test.language_id,
            'topic_id': str(test.topic_id),
            'difficulty': test.difficulty,
            'transcript': test.transcript,
            'gen_user': test.gen_user,
            'audio_url': test.audio_url
        }

        # Add title if provided (NULL if not generated)
        if test.title:
            data['title'] = test.title

        self.client.table('tests') \
            .insert(data) \
            .execute()

        logger.info(f"Inserted test: {test.slug}")
        return test.slug

    def insert_questions(self, questions: List[GeneratedQuestion]) -> int:
        """
        Insert questions for a test.

        Args:
            questions: List of GeneratedQuestion objects

        Returns:
            int: Number of questions inserted
        """
        if not questions:
            return 0

        rows = []
        for q in questions:
            row = {
                'id': str(uuid4()),
                'test_id': str(q.test_id),
                'question_id': q.question_id,
                'question_text': q.question_text,
                'choices': q.choices,
                'answer': q.answer
            }
            if q.question_type_id:
                row['question_type_id'] = q.question_type_id
            rows.append(row)

        response = self.client.table('questions') \
            .insert(rows) \
            .execute()

        count = len(response.data) if response.data else 0
        logger.info(f"Inserted {count} questions for test {questions[0].test_id}")
        return count

    def insert_test_skill_ratings(
        self,
        test_id: UUID,
        initial_elo: int,
        has_audio: bool = True
    ) -> None:
        """
        Insert initial skill ratings for a test.

        Args:
            test_id: Test UUID
            initial_elo: Starting ELO rating
            has_audio: Whether the test has audio
        """
        # Get active test types from dim_test_types
        active_types = self.get_active_test_types()

        # Filter based on audio availability
        types_to_create = [
            t for t in active_types
            if not t['requires_audio'] or has_audio
        ]

        if not types_to_create:
            logger.warning(f"No skill ratings to create for test {test_id}")
            return

        rows = [
            {
                'test_id': str(test_id),
                'test_type_id': t['id'],
                'elo_rating': initial_elo,
                'volatility': 1.0,
                'total_attempts': 0
            }
            for t in types_to_create
        ]

        self.client.table('test_skill_ratings') \
            .insert(rows) \
            .execute()

        type_codes = [t['type_code'] for t in types_to_create]
        logger.debug(f"Inserted skill ratings for test {test_id}: {type_codes}")

    # ============================================================
    # METRICS
    # ============================================================

    def insert_generation_run(self, metrics: TestGenMetrics) -> None:
        """
        Insert test generation run metrics.

        Args:
            metrics: TestGenMetrics dataclass
        """
        data = {
            'run_date': metrics.run_date.date().isoformat(),
            'queue_items_processed': metrics.queue_items_processed,
            'tests_generated': metrics.tests_generated,
            'tests_failed': metrics.tests_failed,
            'execution_time_seconds': metrics.execution_time_seconds,
            'error_message': metrics.error_message
        }

        self.client.table('test_generation_runs') \
            .insert(data) \
            .execute()

        logger.info(
            f"Logged test generation run: {metrics.tests_generated} tests, "
            f"{metrics.tests_failed} failed"
        )

    # ============================================================
    # CONFIG TABLE
    # ============================================================

    def get_config_value(self, key: str, default: str = None) -> Optional[str]:
        """Get runtime config value from database."""
        if self._config_cache is None:
            self._load_config_cache()

        return self._config_cache.get(key, default)

    def _load_config_cache(self) -> None:
        """Load config values into cache."""
        response = self.client.table('test_generation_config') \
            .select('config_key, config_value') \
            .execute()

        self._config_cache = {}
        if response.data:
            for row in response.data:
                self._config_cache[row['config_key']] = row['config_value']

        logger.info(f"Loaded {len(self._config_cache)} config values")

    # ============================================================
    # UTILITY METHODS
    # ============================================================

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

    def clear_caches(self) -> None:
        """Clear all cached data."""
        self._language_cache = None
        self._cefr_cache = None
        self._question_type_cache = None
        self._distribution_cache = None
        self._status_cache = None
        self._config_cache = None
        logger.debug("Cleared database caches")

    def generate_test_slug(
        self,
        language_code: str,
        difficulty: int,
        topic_concept: str
    ) -> str:
        """
        Generate a unique test slug.

        Format: {lang}-d{difficulty}-{topic_snippet}-{timestamp}

        Args:
            language_code: ISO language code
            difficulty: Difficulty level
            topic_concept: Topic concept for slug

        Returns:
            str: Generated slug
        """
        import re
        from datetime import datetime

        # Clean topic concept for slug
        snippet = topic_concept[:30].lower()
        snippet = re.sub(r'[^a-z0-9]+', '-', snippet)
        snippet = snippet.strip('-')

        # Add timestamp for uniqueness
        timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')

        slug = f"{language_code}-d{difficulty}-{snippet}-{timestamp}"
        return slug
