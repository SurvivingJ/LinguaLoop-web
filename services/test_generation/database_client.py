"""
Test Generation Database Client

Handles all database interactions for the test generation system.
Uses the existing SupabaseFactory for client management.
"""

import json
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional, Any
from uuid import UUID, uuid4
from dataclasses import dataclass, field

from ..supabase_factory import get_supabase_admin
from ..dictation.cap import passage_word_range_for_tier

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
    # ADR-003 age tier 1-6 (None = legacy/untiered -> full difficulty schedule)
    target_age_tier: Optional[int] = None
    distinctive_vocabulary: List[str] = field(default_factory=list)


@dataclass
class LanguageConfig:
    """Extended language configuration for test generation."""
    id: int
    language_code: str
    language_name: str
    native_name: str
    # Dataclass defaults only: _build_language_config always overwrites both
    # from prompt_templates via _resolve_models. Kept in sync with the one-gemini
    # -slug policy (migrations/consolidate_gemini_on_3_5_flash_lite.sql) so a
    # hand-built LanguageConfig cannot resurrect a dead slug.
    prose_model: str = 'google/gemini-3.5-flash-lite'
    question_model: str = 'google/gemini-3.5-flash-lite'
    tts_voice_ids: List[str] = field(default_factory=lambda: ['alloy'])
    tts_speed: float = 1.0
    grammar_check_enabled: bool = False


@dataclass
class TierConfig:
    """Complexity tier configuration."""
    id: int
    tier_code: str
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
    seeded_elo: Optional[int] = None  # lexical-complexity-derived seed, see difficulty_scorer
    # dim_complexity_tiers.id (1-6) — sole level axis going forward, TASK-740.
    # difficulty above is kept only for legacy readers; new inserts always set
    # this from the topic's mandatory target_age_tier.
    target_age_tier: Optional[int] = None
    # TASK-740 Phase 5: dedup fields, see services/test_generation/dedup.py.
    passage_hash: Optional[str] = None
    passage_embedding: Optional[List[float]] = None


@dataclass
class GeneratedQuestion:
    """Data for inserting a generated question."""
    test_id: UUID
    question_id: str
    question_text: str
    choices: List[str]
    answer: str
    question_type_id: Optional[int] = None
    distractor_types: Optional[List[str]] = None
    # Pre-set by callers that need to reference the row UUID before insert
    # (e.g. orchestrator writing generation_review_queue rows).
    # If None, insert_questions generates a fresh uuid4().
    id: Optional[UUID] = None


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
        self._tier_cache: Optional[Dict[int, TierConfig]] = None
        self._question_type_cache: Optional[Dict[str, QuestionType]] = None
        self._tier_distribution_cache: Optional[Dict[int, List[str]]] = None
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
            'processed_at': datetime.now(timezone.utc).isoformat()
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
            .select('id, category_id, concept_english, lens_id, keywords, '
                    'semantic_signature, target_age_tier, distinctive_vocabulary') \
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
            semantic_signature=row.get('semantic_signature'),
            target_age_tier=row.get('target_age_tier'),
            distinctive_vocabulary=row.get('distinctive_vocabulary', []) or [],
        )

    def get_category_name(self, category_id: int) -> str:
        """Get category name by ID."""
        response = self.client.table('categories') \
            .select('name') \
            .eq('id', category_id) \
            .single() \
            .execute()

        return response.data.get('name', 'Unknown') if response.data else 'Unknown'

    def count_recent_tests_for_topic(self, topic_id: UUID, window_days: int) -> int:
        """
        Count tests generated for a topic within the last `window_days` days.

        TASK-740 Phase 4 (finding #2): backs the per-topic generation cap —
        callers compare this against config.max_tests_per_topic before
        generating another test for the same topic. Uses `count='exact',
        head=True` so this is a count-only query with no row payload.

        Args:
            topic_id: Topic UUID
            window_days: How many days back to look (from now)

        Returns:
            int: Number of tests for this topic created within the window
        """
        cutoff = (datetime.now(timezone.utc) - timedelta(days=window_days)).isoformat()

        response = self.client.table('tests') \
            .select('id', count='exact', head=True) \
            .eq('topic_id', str(topic_id)) \
            .gte('created_at', cutoff) \
            .execute()

        return response.count or 0

    # ============================================================
    # LANGUAGE CONFIGURATION
    # ============================================================

    def _resolve_models(self, language_id: int) -> tuple[str, str]:
        """Resolve (prose_model, question_model) for a language.

        Reads from prompt_templates.model — the single source of truth.
        Picks representative tasks: 'prose_generation' for the prose model
        and 'question_literal_detail' for the question model. All six
        question_* tasks share one model in the seed data, so any of them
        gives the same answer.
        """
        from services.prompt_service import get_template_config
        prose_cfg = get_template_config(self.client, 'prose_generation', language_id)
        question_cfg = get_template_config(
            self.client, 'question_literal_detail', language_id,
        )
        return prose_cfg['model'], question_cfg['model']

    def _build_language_config(self, row: dict) -> LanguageConfig:
        """Construct a LanguageConfig from a dim_languages row.

        Shared by get_language_config and get_language_config_by_code: parses
        the (possibly JSONB-stringified) tts_voice_ids, resolves the prose /
        question models from prompt_templates, and assembles the dataclass.
        """
        # Parse TTS voice IDs from JSONB
        tts_voice_ids = row.get('tts_voice_ids', ['alloy'])
        if isinstance(tts_voice_ids, str):
            try:
                tts_voice_ids = json.loads(tts_voice_ids)
            except Exception:
                tts_voice_ids = ['alloy']

        prose_model, question_model = self._resolve_models(row['id'])

        return LanguageConfig(
            id=row['id'],
            language_code=row['language_code'],
            language_name=row['language_name'],
            native_name=row.get('native_name') or row['language_name'],
            prose_model=prose_model,
            question_model=question_model,
            tts_voice_ids=tts_voice_ids,
            tts_speed=float(row.get('tts_speed', 1.0)),
            grammar_check_enabled=row.get('grammar_check_enabled', False)
        )

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

        config = self._build_language_config(response.data)

        # Cache the result
        if self._language_cache is None:
            self._language_cache = {}
        self._language_cache[language_id] = config

        return config

    def get_language_config_by_code(self, language_code: str) -> Optional[LanguageConfig]:
        """
        Fetch language configuration by language code (ISO 639-1: 'en', 'zh', 'ja').

        Checks the existing cache first, then queries by code.

        Args:
            language_code: ISO language code

        Returns:
            LanguageConfig object or None
        """
        # Check existing cache
        if self._language_cache:
            for config in self._language_cache.values():
                if config.language_code == language_code:
                    return config

        response = self.client.table('dim_languages') \
            .select('*') \
            .eq('language_code', language_code) \
            .eq('is_active', True) \
            .single() \
            .execute()

        if not response.data:
            logger.warning(f"Language not found for code: {language_code}")
            return None

        config = self._build_language_config(response.data)

        # Cache by ID (consistent with get_language_config)
        if self._language_cache is None:
            self._language_cache = {}
        self._language_cache[config.id] = config

        return config

    # ============================================================
    # TIER CONFIGURATION
    # ============================================================

    def get_tier_config(self, tier_id: int) -> TierConfig:
        """Get complexity tier configuration by ``dim_complexity_tiers.id``.

        TASK-740: target_age_tier is the sole level axis for test generation
        now — this is a direct id lookup, not a difficulty->tier range scan.
        A miss raises rather than silently degrading (finding #4): a topic
        pointing at an unknown tier is a data-integrity bug, not something to
        paper over with a guessed config.

        Args:
            tier_id: dim_complexity_tiers.id (1-6)

        Returns:
            TierConfig object.

        Raises:
            KeyError: no dim_complexity_tiers row for tier_id.
        """
        if self._tier_cache is None:
            self._load_tier_cache()

        tier = self._tier_cache.get(tier_id)
        if tier is None:
            raise KeyError(
                f"No dim_complexity_tiers row for tier_id={tier_id!r}. "
                "target_age_tier is the sole level axis now — a lookup miss "
                "must raise, not fall back to a guessed config."
            )
        return tier

    def _load_tier_cache(self) -> None:
        """Load all complexity tiers into cache, keyed by id."""
        response = self.client.table('dim_complexity_tiers') \
            .select('*') \
            .execute()

        self._tier_cache = {}
        if response.data:
            for row in response.data:
                tier = TierConfig(
                    id=row['id'],
                    tier_code=row['tier_code'],
                    difficulty_min=row['difficulty_min'],
                    difficulty_max=row['difficulty_max'],
                    word_count_min=row['word_count_min'],
                    word_count_max=row['word_count_max'],
                    initial_elo=row['initial_elo']
                )
                self._tier_cache[tier.id] = tier

        logger.info(f"Loaded {len(self._tier_cache)} complexity tiers")

    def get_tier_word_count_range(self, tier_id: int) -> tuple:
        """Passage length range (min_words, max_words) for a tier.

        Reads from ``services.dictation.cap.passage_word_range_for_tier``,
        whose upper bound is that tier's dictation cap — see the module
        docstring there for why word_count_max on dim_complexity_tiers itself
        (a vocabulary size, not a passage length) is not usable here.

        Raises:
            KeyError: no dim_complexity_tiers row for tier_id (via
                get_tier_config).
        """
        tier = self.get_tier_config(tier_id)
        return passage_word_range_for_tier(tier.tier_code)

    def get_tier_initial_elo(self, tier_id: int) -> int:
        """Get initial ELO rating for a tier. Raises on an unknown tier_id —
        no hardcoded difficulty->ELO fallback (finding #4)."""
        return self.get_tier_config(tier_id).initial_elo

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

    def get_tier_question_distribution(self, tier_id: int) -> List[str]:
        """
        Get question type distribution for a complexity tier.

        Reads ``question_type_distributions_by_tier`` (TASK-740 Phase 1) — one
        fixed mix per tier, seeded from the legacy difficulty-keyed table so
        day-1 behavior is unchanged.

        Args:
            tier_id: dim_complexity_tiers.id (1-6)

        Returns:
            List of question type codes (e.g., ['literal_detail', 'main_idea', ...])
        """
        if self._tier_distribution_cache is None:
            self._load_tier_distribution_cache()

        if tier_id in self._tier_distribution_cache:
            return self._tier_distribution_cache[tier_id]

        # Fallback to default distribution — the tier itself is real (callers
        # already validated tier_id via get_tier_config); a missing
        # distribution row is a seed-data gap, not a reason to raise.
        logger.warning(f"No question distribution found for tier {tier_id}, using default")
        return ['literal_detail', 'literal_detail', 'main_idea', 'main_idea', 'inference']

    def _load_tier_distribution_cache(self) -> None:
        """Load tier-keyed question type distributions into cache."""
        response = self.client.table('question_type_distributions_by_tier') \
            .select('*') \
            .execute()

        self._tier_distribution_cache = {}
        if response.data:
            for row in response.data:
                tier_id = row['tier_id']
                types = []
                for i in range(1, 6):
                    type_code = row.get(f'question_type_{i}')
                    if type_code:
                        types.append(type_code)
                if types:
                    self._tier_distribution_cache[tier_id] = types

        logger.info(f"Loaded distributions for {len(self._tier_distribution_cache)} tiers")

    def get_recent_question_stems(
        self,
        language_id: int,
        type_codes: List[str],
        limit_per_type: int = 8,
    ) -> Dict[str, List[str]]:
        """Recently written question stems per type, newest first (T1.2).

        Fed to the question prompt as a do-not-reuse list. A stem-rotation pool
        of six still repeats every sixth test; this is what stops a learner
        meeting the same phrasing twice in a row.

        Scoped by language because the stems ARE the language. Returns ``{}``
        on any failure — a missing recency list degrades variety, and refusing
        to generate a test over it would be a much worse trade.
        """
        if not type_codes:
            return {}

        type_ids = {}
        for code in set(type_codes):
            type_id = self.get_question_type_id(code)
            if type_id is not None:
                type_ids[type_id] = code
        if not type_ids:
            return {}

        try:
            response = (
                self.client.table('questions')
                .select('question_text, question_type_id, tests!inner(language_id)')
                .in_('question_type_id', list(type_ids))
                .eq('tests.language_id', language_id)
                .order('created_at', desc=True)
                # Over-fetch: the rows come back interleaved across types, so
                # a per-type limit is not expressible in one PostgREST call.
                .limit(limit_per_type * len(type_ids) * 6)
                .execute()
            )
        except Exception as e:
            logger.warning(f"Could not read recent question stems: {e}")
            return {}

        out: Dict[str, List[str]] = {code: [] for code in type_ids.values()}
        for row in (response.data or []):
            code = type_ids.get(row.get('question_type_id'))
            text = (row.get('question_text') or '').strip()
            if not code or not text:
                continue
            bucket = out[code]
            if len(bucket) < limit_per_type and text not in bucket:
                bucket.append(text)
        return {code: stems for code, stems in out.items() if stems}

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
        language_id: int,
        required: bool = True
    ) -> Optional[str]:
        """
        Fetch prompt template by task name and language ID.

        Uses language_id (integer) to match actual prompt_templates table structure.
        Falls back to English (language_id=2) if not found for specific language.

        Args:
            task_name: Template name (e.g., 'prose_generation', 'question_literal_detail')
            language_id: Language ID from dim_languages (1=Chinese, 2=English, 3=Japanese)
            required: When True (default), a missing template raises RuntimeError —
                matching prompt_service.get_template_config, so a misconfigured
                table fails loudly instead of silently falling back to hardcoded
                legacy prompts. Pass required=False for genuinely optional
                templates (e.g. opt-in vocab validation / phrase detection) where
                absence is an expected "skip this step" signal.

        Returns:
            Template text, or None only when required=False and no template exists.

        Raises:
            RuntimeError: required=True and no active template for the task in the
                requested language or the English fallback.
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

        if required:
            raise RuntimeError(
                f"No active prompt_templates row for task_name={task_name!r} "
                f"language_id={language_id} (and no English fallback). "
                f"Populate the table; there is no hardcoded prompt fallback."
            )

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

        if test.target_age_tier is not None:
            data['target_age_tier'] = test.target_age_tier

        # Add title if provided (NULL if not generated)
        if test.title:
            data['title'] = test.title

        if test.seeded_elo is not None:
            data['seeded_elo'] = test.seeded_elo

        if test.passage_hash is not None:
            data['passage_hash'] = test.passage_hash

        if test.passage_embedding is not None:
            data['passage_embedding'] = test.passage_embedding

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
                'id': str(q.id) if q.id else str(uuid4()),
                'test_id': str(q.test_id),
                'question_id': q.question_id,
                'question_text': q.question_text,
                'choices': q.choices,
                'answer': q.answer
            }
            if q.question_type_id:
                row['question_type_id'] = q.question_type_id
            if q.distractor_types:
                row['distractor_types'] = q.distractor_types
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
        has_audio: bool = True,
        language_id: int = None
    ) -> None:
        """
        Insert initial skill ratings for a test.

        Args:
            test_id: Test UUID
            initial_elo: Starting ELO rating
            has_audio: Whether the test has audio
            language_id: Language ID (1=Chinese) — pinyin type only for Chinese
        """
        # Get active test types from dim_test_types
        active_types = self.get_active_test_types()

        # Filter based on audio availability and language
        types_to_create = []
        for t in active_types:
            if t['requires_audio'] and not has_audio:
                continue
            # Pinyin type is Chinese-only
            if t['type_code'] == 'pinyin' and language_id != 1:
                continue
            types_to_create.append(t)

        if not types_to_create:
            logger.warning(f"No skill ratings to create for test {test_id}")
            return

        # No 'volatility' column: the dual-ELO design (V3, wire_volatility_and_
        # _exclude_attempted, 2026-05-08) deliberately gives tests no volatility
        # ("tests don't go rusty"), and the column was dropped from the live
        # schema. process_test_submission reads only elo_rating/total_attempts.
        rows = [
            {
                'test_id': str(test_id),
                'test_type_id': t['id'],
                'elo_rating': initial_elo,
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

        if status_code not in self._status_cache:
            raise KeyError(f"Unknown status code: {status_code!r}")
        return self._status_cache[status_code]

    def clear_caches(self) -> None:
        """Clear all cached data."""
        self._language_cache = None
        self._tier_cache = None
        self._question_type_cache = None
        self._tier_distribution_cache = None
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
        # Clean topic concept for slug
        snippet = topic_concept[:30].lower()
        snippet = re.sub(r'[^a-z0-9]+', '-', snippet)
        snippet = snippet.strip('-')

        # Add timestamp for uniqueness
        timestamp = datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')

        slug = f"{language_code}-d{difficulty}-{snippet}-{timestamp}"
        return slug
