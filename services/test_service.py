# services/test_service.py
"""
Test Service - Centralized business logic for test operations.
Extracted from routes/tests.py to maintain separation of concerns.
"""

import json
import hashlib
import logging
import traceback
from datetime import datetime, timezone
from typing import Optional, Dict, List, Any, Tuple
from uuid import uuid4

from .supabase_factory import get_supabase, get_supabase_admin

logger = logging.getLogger(__name__)


# ============================================================================
# CONSTANTS - Import from Config (single source of truth)
# ============================================================================
from ..config import Config

VALID_LANGUAGE_IDS = Config.VALID_LANGUAGE_IDS
LANGUAGE_ID_TO_NAME = Config.LANGUAGE_ID_TO_NAME
LANGUAGE_NAME_TO_ID = {v: k for k, v in LANGUAGE_ID_TO_NAME.items()}


# ============================================================================
# DIMENSION TABLE HELPERS
# ============================================================================

class DimensionService:
    """Handles dimension table lookups with caching."""

    _language_cache: Dict[str, int] = {}
    _test_type_cache: Dict[str, int] = {}
    _languages_metadata: List[Dict] = []
    _test_types_metadata: List[Dict] = []
    _initialized: bool = False

    @classmethod
    def initialize(cls, supabase_client=None) -> None:
        """Pre-load dimension tables into cache."""
        client = supabase_client or get_supabase()
        if not client:
            return

        try:
            # Cache languages with full metadata
            langs = client.table('dim_languages')\
                .select('id, language_code, language_name, native_name')\
                .eq('is_active', True)\
                .order('display_order')\
                .execute()
            cls._languages_metadata = langs.data or []
            cls._language_cache = {r['language_code']: r['id'] for r in cls._languages_metadata}

            # Cache test types with full metadata
            types = client.table('dim_test_types')\
                .select('id, type_code, type_name, requires_audio')\
                .eq('is_active', True)\
                .order('display_order')\
                .execute()
            cls._test_types_metadata = types.data or []
            cls._test_type_cache = {r['type_code']: r['id'] for r in cls._test_types_metadata}

            cls._initialized = True
            logger.info(f"DimensionService initialized: {len(cls._language_cache)} languages, {len(cls._test_type_cache)} test types")

        except Exception as e:
            logger.error(f"Failed to initialize DimensionService: {e}")

    @classmethod
    def get_all_languages(cls) -> List[Dict]:
        """Return cached language metadata for /api/metadata endpoint."""
        return cls._languages_metadata

    @classmethod
    def get_all_test_types(cls) -> List[Dict]:
        """Return cached test type metadata for /api/metadata endpoint."""
        return cls._test_types_metadata

    @classmethod
    def get_language_id(cls, language_code: str, supabase_client=None) -> Optional[int]:
        """Get language ID from code (cn, en, jp)."""
        if not language_code:
            return None

        code = language_code.lower()

        # Check cache first
        if code in cls._language_cache:
            return cls._language_cache[code]

        # Query database if not cached
        client = supabase_client or get_supabase()
        if not client:
            return None

        try:
            result = client.table('dim_languages')\
                .select('id')\
                .eq('language_code', code)\
                .eq('is_active', True)\
                .limit(1)\
                .execute()
            if result.data:
                cls._language_cache[code] = result.data[0]['id']
                return result.data[0]['id']
        except Exception as e:
            logger.error(f"Error fetching language ID for '{code}': {e}")

        return None

    @classmethod
    def get_test_type_id(cls, type_code: str, supabase_client=None) -> Optional[int]:
        """Get test type ID from code (listening, reading, dictation)."""
        if not type_code:
            return None

        code = type_code.lower()

        # Check cache first
        if code in cls._test_type_cache:
            return cls._test_type_cache[code]

        # Query database if not cached
        client = supabase_client or get_supabase()
        if not client:
            return None

        try:
            result = client.table('dim_test_types')\
                .select('id')\
                .eq('type_code', code)\
                .eq('is_active', True)\
                .limit(1)\
                .execute()
            if result.data:
                cls._test_type_cache[code] = result.data[0]['id']
                return result.data[0]['id']
        except Exception as e:
            logger.error(f"Error fetching test type ID for '{code}': {e}")

        return None

    @classmethod
    def get_all_test_types(cls, supabase_client=None) -> Tuple[Dict[str, int], Dict[int, str]]:
        """Get all test type mappings."""
        if cls._test_type_cache:
            id_to_code = {v: k for k, v in cls._test_type_cache.items()}
            return cls._test_type_cache.copy(), id_to_code

        client = supabase_client or get_supabase()
        if not client:
            return {}, {}

        try:
            result = client.table('dim_test_types')\
                .select('id, type_code')\
                .eq('is_active', True)\
                .execute()

            code_to_id = {row['type_code']: row['id'] for row in result.data}
            id_to_code = {row['id']: row['type_code'] for row in result.data}
            cls._test_type_cache = code_to_id
            return code_to_id, id_to_code
        except Exception as e:
            logger.error(f"Error fetching test types: {e}")
            return {}, {}


def parse_language_id(language_id_input) -> Optional[int]:
    """Parse and validate language_id - only accepts integer IDs."""
    if language_id_input is None:
        return None

    try:
        lang_id = int(language_id_input)
        return lang_id if lang_id in VALID_LANGUAGE_IDS else None
    except (ValueError, TypeError):
        return None


# ============================================================================
# TEST SERVICE
# ============================================================================

class TestService:
    """
    Centralized service for test operations.
    Handles CRUD, generation support, and attempt recording.
    """

    def __init__(self, supabase_client=None, supabase_admin=None):
        """
        Initialize TestService.

        Args:
            supabase_client: Anon client (RLS-protected)
            supabase_admin: Service role client (bypasses RLS)
        """
        self._client = supabase_client
        self._admin = supabase_admin

    @property
    def client(self):
        """Get the anon Supabase client."""
        if self._client is None:
            self._client = get_supabase()
        return self._client

    @property
    def admin(self):
        """Get the admin Supabase client."""
        if self._admin is None:
            self._admin = get_supabase_admin()
        return self._admin

    # -------------------------------------------------------------------------
    # TEST RETRIEVAL
    # -------------------------------------------------------------------------

    def get_tests(self, language_id: int = None, difficulty: int = None,
                  test_type: str = 'reading', limit: int = 50) -> List[Dict]:
        """
        Fetch tests list with optional filters.

        Args:
            language_id: Filter by language
            difficulty: Filter by difficulty level
            test_type: Order by this test type's ELO rating
            limit: Maximum number of tests to return
        """
        if not self.client:
            return []

        try:
            query = self.client.table('tests').select(
                'id, slug, language_id, topic, difficulty, '
                'listening_rating, reading_rating, dictation_rating, created_at'
            )

            if language_id:
                lang_id = parse_language_id(language_id)
                if lang_id:
                    query = query.eq('language_id', lang_id)

            if difficulty is not None:
                query = query.eq('difficulty', str(int(difficulty)))

            # Order by the appropriate rating column
            type_key = (test_type or 'reading').lower()
            order_col = 'reading_rating'
            if type_key in ('listening', 'reading', 'dictation'):
                order_col = f'{type_key}_rating'

            query = query.order(order_col, desc=True).limit(limit)
            result = query.execute()
            data = result.data or []

            # Ensure difficulty is int
            for t in data:
                if t.get('difficulty') is not None:
                    try:
                        t['difficulty'] = int(t['difficulty'])
                    except (ValueError, TypeError):
                        pass

            return data

        except Exception as e:
            logger.error(f"Error fetching tests: {e}")
            return []

    def get_test_by_slug(self, slug: str) -> Optional[Dict]:
        """
        Get a single test by slug with its questions.

        Returns formatted test data ready for the frontend.
        """
        if not self.client or not slug:
            return None

        try:
            # Fetch test
            t_res = self.client.table('tests').select('*').eq('slug', slug).limit(1).execute()
            if not t_res.data:
                return None

            t = t_res.data[0]

            # Fetch questions
            q_res = self.client.table('questions')\
                .select('*')\
                .eq('test_id', t['id'])\
                .execute()

            q_rows = q_res.data or []

            # Parse questions
            questions = []
            for q in q_rows:
                questions.append({
                    'id': q['id'],
                    'question': q['question_text'],
                    'choices': self._parse_choices(q.get('choices')),
                    'answer': q.get('correct_answer', ''),
                })

            # Format response
            difficulty_value = t.get('difficulty', 1)
            try:
                difficulty_value = int(difficulty_value)
            except (ValueError, TypeError):
                difficulty_value = 1

            language_id = t.get('language_id')
            language_name = LANGUAGE_ID_TO_NAME.get(language_id, 'unknown')

            return {
                'id': t['id'],
                'slug': t['slug'],
                'language_id': language_id,
                'language': language_name,
                'topic': t.get('topic') or '',
                'title': t.get('topic') or f"{language_name.capitalize()} Test (Level {difficulty_value})",
                'difficulty': difficulty_value,
                'transcript': t.get('transcript') or '',
                'questions': questions,
                'created_at': t.get('created_at'),
            }

        except Exception as e:
            logger.error(f"Error fetching test by slug: {e}")
            logger.error(traceback.format_exc())
            return None

    def _parse_choices(self, raw) -> List[str]:
        """Parse choices from various formats."""
        if isinstance(raw, list):
            return raw
        if isinstance(raw, str):
            try:
                parsed = json.loads(raw)
                return parsed if isinstance(parsed, list) else [raw]
            except json.JSONDecodeError:
                return [raw]
        return []

    # -------------------------------------------------------------------------
    # TEST CREATION
    # -------------------------------------------------------------------------

    def save_test(self, test_data: Dict, user_id: str = None) -> int:
        """
        Save a generated test to the database.

        Args:
            test_data: Test data including questions
            user_id: The user who generated the test

        Returns:
            The created test ID

        Raises:
            Exception: If save fails
        """
        if not self.admin:
            raise Exception("Supabase service client not initialized")

        logger.debug(f"Saving test: {test_data.get('slug')}")

        try:
            # Validate language_id
            language_id = parse_language_id(test_data.get("language_id"))
            if not language_id:
                # Try to get from language name
                lang_name = test_data.get('language', '').lower()
                language_id = LANGUAGE_NAME_TO_ID.get(lang_name, 1)

            # Build test row
            tests_row = {
                "slug": test_data["slug"],
                "language_id": language_id,
                "topic": test_data.get("topic", ""),
                "difficulty": int(test_data.get("difficulty", 1)),
                "style": test_data.get("style", ""),
                "tier": test_data.get("tier", "free"),
                "title": test_data.get("title") or test_data.get("topic") or "Language Test",
                "transcript": test_data.get("transcript", ""),
                "audio_url": test_data.get("audio_url", ""),
                "total_attempts": test_data.get("total_attempts", 0),
                "is_active": test_data.get("is_active", True),
                "is_featured": test_data.get("is_featured", False),
                "is_custom": test_data.get("is_custom", False),
                "generation_model": test_data.get("generation_model", "gpt-4"),
                "audio_generated": test_data.get("audio_generated", False),
                "gen_user": test_data.get("gen_user", user_id or ""),
            }

            # Insert test
            test_result = self.admin.table('tests').insert(tests_row).execute()
            if not test_result.data:
                raise Exception("No data returned from test insert")

            test_id = test_result.data[0]['id']

            # Insert questions
            question_rows = []
            for i, q in enumerate(test_data.get('questions', []), start=1):
                choices = q.get('choices', [])
                if isinstance(choices, str):
                    try:
                        choices = json.loads(choices)
                    except json.JSONDecodeError:
                        choices = [choices]

                question_row = {
                    'test_id': test_id,
                    'question_id': q.get('id') or str(uuid4()),
                    'question_text': q.get('question', ''),
                    'question_type': q.get('question_type', 'multiple_choice'),
                    'choices': choices,
                    'correct_answer': q.get('answer', ''),
                    'answer_explanation': q.get('explanation', ''),
                    'points': q.get('points', 1),
                    'audio_url': q.get('audio_url', ''),
                }
                question_rows.append(question_row)

            if question_rows:
                self.admin.table('questions').insert(question_rows).execute()

            # Create initial skill ratings
            self._create_skill_ratings(test_id)

            return test_id

        except Exception as e:
            logger.error(f"Error saving test to database: {e}")
            logger.error(traceback.format_exc())
            raise

    def _create_skill_ratings(self, test_id: int, initial_elo: int = 1400) -> None:
        """Create initial skill ratings for all test types."""
        listening_id = DimensionService.get_test_type_id('listening', self.admin)
        reading_id = DimensionService.get_test_type_id('reading', self.admin)
        dictation_id = DimensionService.get_test_type_id('dictation', self.admin)

        now = datetime.now(timezone.utc).isoformat()

        skill_ratings = [
            {
                'test_id': test_id,
                'test_type_id': type_id,
                'elo_rating': initial_elo,
                'volatility': 1.0,
                'total_attempts': 0,
                'created_at': now,
                'updated_at': now,
            }
            for type_id in [listening_id, reading_id, dictation_id]
            if type_id is not None
        ]

        if skill_ratings:
            self.admin.table('test_skill_ratings').insert(skill_ratings).execute()

    def update_audio(self, test_id: int, audio_url: str) -> None:
        """Update test with generated audio URL."""
        if not self.admin:
            return

        self.admin.table('tests').update({
            'audio_generated': True,
            'audio_url': audio_url,
            'updated_at': datetime.now(timezone.utc).isoformat()
        }).eq('id', test_id).execute()

    # -------------------------------------------------------------------------
    # TEST ATTEMPTS
    # -------------------------------------------------------------------------

    def record_attempt(self, user_id: str, test_id: int, responses: List[Dict],
                       test_mode: str, time_taken: int = None) -> Dict:
        """
        Record a user's test attempt and individual responses.

        Args:
            user_id: The user taking the test
            test_id: The test being taken
            responses: List of {question_id, selected_answer, is_correct}
            test_mode: The test mode (reading, listening, dictation)
            time_taken: Time taken in seconds

        Returns:
            Dict with attempt_id, score, total_questions, percentage
        """
        if not self.client:
            raise Exception("Supabase client not initialized")

        try:
            total_questions = len(responses)
            correct_count = sum(1 for r in responses if r['is_correct'])

            # Default ELO values (will be calculated by RPC)
            user_elo_before = 1200
            user_elo_after = 1200

            attempt_record = {
                'user_id': user_id,
                'test_id': test_id,
                'score': correct_count,
                'total_questions': total_questions,
                'test_mode': test_mode,
                'time_taken_seconds': time_taken,
                'user_elo_before': user_elo_before,
                'user_elo_after': user_elo_after
            }

            attempt_result = self.client.table('test_attempts').insert(attempt_record).execute()
            attempt_id = attempt_result.data[0]['id']

            # Insert individual responses
            responses_to_insert = []
            for response in responses:
                responses_to_insert.append({
                    'attempt_id': attempt_id,
                    'question_id': response['question_id'],
                    'selected_answer': response['selected_answer'],
                    'is_correct': response['is_correct'],
                    'response_time_ms': response.get('response_time_ms')
                })

            if responses_to_insert:
                self.client.table('attempt_responses').insert(responses_to_insert).execute()

            return {
                'attempt_id': attempt_id,
                'score': correct_count,
                'total_questions': total_questions,
                'percentage': (correct_count / total_questions) * 100 if total_questions > 0 else 0
            }

        except Exception as e:
            logger.error(f"Error recording test attempt: {e}")
            raise

    def record_flagged_input(self, user_email: str, content: str,
                             flagged_categories: List[str] = None) -> None:
        """Record flagged input for analytics."""
        if not self.client:
            return

        try:
            record = {
                'user_email': user_email,
                'content_hash': hashlib.sha256(content.encode()).hexdigest()[:32],
                'flagged_at': datetime.now(timezone.utc).isoformat(),
                'content_type': 'test_generation',
                'flagged_categories': json.dumps(flagged_categories or []),
                'content_length': len(content),
            }

            self.client.table('flagged_inputs').insert(record).execute()
        except Exception as e:
            logger.warning(f"Failed to record flagged input: {e}")


# ============================================================================
# SINGLETON INSTANCE
# ============================================================================

_test_service_instance: TestService = None


def get_test_service() -> TestService:
    """Get the singleton TestService instance."""
    global _test_service_instance
    if _test_service_instance is None:
        _test_service_instance = TestService()
    return _test_service_instance
