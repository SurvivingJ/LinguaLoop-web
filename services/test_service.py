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

from config import Config
from services.supabase_factory import get_supabase, get_supabase_admin

# Re-export from dimension_service for backwards compatibility
from services.dimension_service import (
    DimensionService,
    parse_language_id,
    VALID_LANGUAGE_IDS,
    LANGUAGE_ID_TO_NAME,
    LANGUAGE_NAME_TO_ID,
)

logger = logging.getLogger(__name__)


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

    def _create_skill_ratings(self, test_id: int, initial_elo: int = Config.DEFAULT_ELO_RATING) -> None:
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

    # -------------------------------------------------------------------------
    # DAILY TEST LOAD
    # -------------------------------------------------------------------------

    def get_or_create_daily_load(self, user_id: str, language_id: int) -> Dict:
        """
        Get today's daily test load, or compute and cache it if not yet created.

        Returns dict with load_date, tests (enriched), and progress.
        """
        today = datetime.now(timezone.utc).date().isoformat()

        # Check if today's load already exists
        existing = self.admin.table('daily_test_loads')\
            .select('*')\
            .eq('user_id', user_id)\
            .eq('language_id', language_id)\
            .eq('load_date', today)\
            .execute()

        if existing.data:
            return self._enrich_daily_load(existing.data[0])

        # Compute new daily load
        load_items = self._compute_daily_load(user_id, language_id)

        if not load_items:
            return {
                'load_date': today,
                'tests': [],
                'progress': {'completed': 0, 'total': 0}
            }

        # Persist
        record = self.admin.table('daily_test_loads').insert({
            'user_id': user_id,
            'language_id': language_id,
            'load_date': today,
            'test_ids': load_items,
            'completed_test_ids': []
        }).execute()

        return self._enrich_daily_load(record.data[0])

    def _compute_daily_load(self, user_id: str, language_id: int) -> List[Dict]:
        """
        Core algorithm for selecting up to 3 daily tests.

        Strategy:
        - 1-2 slots: tests the user performed poorly on (<70%) and haven't retried in 24h
        - Remaining slots: new ELO-matched tests via the recommended RPC
        """
        MAX_TESTS = Config.MAX_DAILY_TESTS
        POOR_THRESHOLD = Config.POOR_PERFORMANCE_THRESHOLD
        COOLDOWN_SECONDS = Config.DAILY_TEST_COOLDOWN_SECONDS

        now = datetime.now(timezone.utc)

        # Build test_type id-to-code map
        id_to_type_code = {}
        if DimensionService._test_type_cache:
            id_to_type_code = {v: k for k, v in DimensionService._test_type_cache.items()}

        # Step 1: Find retry candidates (poorly performed tests)
        try:
            attempts_result = self.admin.table('test_attempts')\
                .select('test_id, percentage, test_type_id, created_at')\
                .eq('user_id', user_id)\
                .eq('language_id', language_id)\
                .order('created_at', desc=True)\
                .execute()
        except Exception as e:
            logger.error(f"Error fetching attempts for daily load: {e}")
            attempts_result = type('obj', (object,), {'data': []})()

        # Group by test_id, keep only the latest attempt per test
        latest_by_test = {}
        for a in (attempts_result.data or []):
            if a['test_id'] not in latest_by_test:
                latest_by_test[a['test_id']] = a

        # Filter for retry candidates
        retry_pool = []
        for test_id, a in latest_by_test.items():
            if a['percentage'] is None or a['percentage'] >= POOR_THRESHOLD:
                continue
            # Check cooldown: latest attempt must be older than 24 hours
            try:
                attempt_time = datetime.fromisoformat(a['created_at'].replace('Z', '+00:00'))
                if (now - attempt_time).total_seconds() < COOLDOWN_SECONDS:
                    continue
            except (ValueError, TypeError):
                continue
            retry_pool.append(a)

        # Sort by percentage ascending (worst performance first)
        retry_pool.sort(key=lambda a: a['percentage'])

        # Step 2: Select 1-2 retry tests
        num_retries = min(2, len(retry_pool))
        retry_tests = retry_pool[:num_retries]
        num_new = MAX_TESTS - num_retries

        # Build the load items from retries
        load_items = []
        selected_test_ids = set()

        for r in retry_tests:
            type_code = id_to_type_code.get(r['test_type_id'], 'listening')
            load_items.append({
                'test_id': r['test_id'],
                'slot_type': 'retry',
                'test_type': type_code,
                'original_percentage': round(r['percentage'], 1)
            })
            selected_test_ids.add(r['test_id'])

        # Step 3: Fill remaining slots with new ELO-matched tests
        if num_new > 0:
            language_name = LANGUAGE_ID_TO_NAME.get(language_id, 'chinese')
            try:
                recommended_result = self.admin.rpc('get_recommended_tests', {
                    'p_user_id': user_id,
                    'p_language': language_name
                }).execute()

                recommended = recommended_result.data or []

                # Filter out already-selected and already-attempted tests
                new_tests = [
                    t for t in recommended
                    if t.get('test_id') not in selected_test_ids
                    and t.get('test_id') not in latest_by_test
                ]

                for t in new_tests:
                    if num_new <= 0:
                        break
                    if t.get('test_id') in selected_test_ids:
                        continue
                    load_items.append({
                        'test_id': t['test_id'],
                        'slot_type': 'new',
                        'test_type': t.get('test_type', 'listening')
                    })
                    selected_test_ids.add(t['test_id'])
                    num_new -= 1

            except Exception as e:
                logger.error(f"Error fetching recommended tests for daily load: {e}")

        # Step 4: If still need more tests, fallback to direct query
        if num_new > 0:
            try:
                # Get user's approximate ELO for this language
                user_elo = 1200
                for a in (attempts_result.data or []):
                    # First entry is most recent
                    user_elo = a.get('user_elo_after', 1200) or 1200
                    break

                elo_min = max(400, user_elo - 200)
                elo_max = min(3000, user_elo + 200)

                # Query tests in ELO range that user hasn't attempted
                fallback_query = self.admin.table('tests')\
                    .select('id, slug')\
                    .eq('language_id', language_id)\
                    .eq('is_active', True)\
                    .limit(num_new + len(selected_test_ids))

                fallback_result = fallback_query.execute()

                for t in (fallback_result.data or []):
                    if t['id'] not in selected_test_ids and t['id'] not in latest_by_test:
                        load_items.append({
                            'test_id': t['id'],
                            'slot_type': 'new',
                            'test_type': 'listening'
                        })
                        selected_test_ids.add(t['id'])
                        num_new -= 1
                        if num_new <= 0:
                            break

            except Exception as e:
                logger.error(f"Error in fallback test selection for daily load: {e}")

        return load_items

    def _enrich_daily_load(self, cached_record: Dict) -> Dict:
        """
        Take a raw daily_test_loads row and enrich with full test details.
        """
        test_ids_list = cached_record.get('test_ids', [])
        completed = cached_record.get('completed_test_ids', []) or []

        if not test_ids_list:
            return {
                'load_date': cached_record.get('load_date'),
                'tests': [],
                'progress': {'completed': 0, 'total': 0}
            }

        # Fetch full test details
        ids = [item['test_id'] for item in test_ids_list]
        try:
            tests_result = self.admin.table('tests').select(
                'id, slug, title, language_id, difficulty, style, tier, '
                'audio_url, audio_generated, is_custom, total_attempts'
            ).in_('id', ids).execute()

            tests_map = {t['id']: t for t in (tests_result.data or [])}
        except Exception as e:
            logger.error(f"Error enriching daily load: {e}")
            tests_map = {}

        # Fetch ELO ratings for these tests
        ratings_map = {}
        if ids:
            try:
                ratings_result = self.admin.table('test_skill_ratings').select(
                    'test_id, test_type_id, elo_rating, dim_test_types(type_code)'
                ).in_('test_id', ids).execute()

                for rating in (ratings_result.data or []):
                    test_id = rating['test_id']
                    type_code = rating.get('dim_test_types', {}).get('type_code', 'unknown')
                    if test_id not in ratings_map:
                        ratings_map[test_id] = {}
                    ratings_map[test_id][type_code] = rating['elo_rating']
            except Exception as e:
                logger.error(f"Error fetching ratings for daily load: {e}")

        enriched_tests = []
        for item in test_ids_list:
            test_id = item['test_id']
            test_detail = tests_map.get(test_id)
            if not test_detail:
                continue  # Skip if test was deactivated

            test_type = item.get('test_type', 'listening')
            test_ratings = ratings_map.get(test_id, {})
            elo_rating = test_ratings.get(test_type, Config.DEFAULT_ELO_RATING)

            enriched_tests.append({
                **test_detail,
                'slot_type': item['slot_type'],
                'test_type': test_type,
                'elo_rating': elo_rating,
                'original_percentage': item.get('original_percentage'),
                'is_completed': test_id in completed
            })

        return {
            'load_date': cached_record.get('load_date'),
            'tests': enriched_tests,
            'progress': {
                'completed': len(completed),
                'total': len(test_ids_list)
            }
        }

    def mark_daily_test_complete(self, user_id: str, language_id: int, test_id: str) -> Dict:
        """Mark a specific test as completed in today's daily load."""
        today = datetime.now(timezone.utc).date().isoformat()

        record = self.admin.table('daily_test_loads')\
            .select('id, completed_test_ids, test_ids')\
            .eq('user_id', user_id)\
            .eq('language_id', language_id)\
            .eq('load_date', today)\
            .single()\
            .execute()

        if not record.data:
            raise Exception("No daily load found for today")

        completed = record.data.get('completed_test_ids', []) or []
        if test_id not in completed:
            completed.append(test_id)

        self.admin.table('daily_test_loads')\
            .update({'completed_test_ids': completed})\
            .eq('id', record.data['id'])\
            .execute()

        total = len(record.data.get('test_ids', []))
        return {
            'completed': len(completed),
            'total': total,
            'all_complete': len(completed) >= total
        }

    # -------------------------------------------------------------------------
    # CONTENT MODERATION
    # -------------------------------------------------------------------------

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

    def get_user_elo_summary(self, user_id: str) -> Dict[str, Any]:
        """Aggregate ELO ratings across all languages and skills for a user.

        Returns a dict keyed by language code, each containing skill ratings.
        """
        attempts_result = self.admin.table('test_attempts') \
            .select('language_id, test_type_id, user_elo_after, created_at') \
            .eq('user_id', user_id) \
            .order('created_at', desc=True) \
            .execute()

        if not attempts_result.data:
            return {}

        # Build language lookup (Config -> DimensionService override)
        lang_map: Dict[int, Dict] = {}
        for lid, data in Config.LANGUAGES.items():
            lang_map[lid] = {
                'code': data.get('code', f'lang_{lid}'),
                'name': data.get('display', f'Language {lid}'),
            }
        for lang in DimensionService.get_all_languages():
            lang_id = lang.get('id')
            if lang_id is not None:
                lang_map[int(lang_id)] = {
                    'code': lang.get('language_code', f'lang_{lang_id}'),
                    'name': lang.get('language_name', f'Language {lang_id}'),
                    'native_name': lang.get('native_name') or lang.get('language_name', f'Language {lang_id}'),
                }

        # Build test-type lookup with static fallbacks
        type_map: Dict[int, Dict] = {
            1: {'code': 'listening', 'name': 'Listening'},
            2: {'code': 'reading', 'name': 'Reading'},
            3: {'code': 'dictation', 'name': 'Dictation'},
        }
        for tt in DimensionService.get_all_test_types():
            tt_id = tt.get('id')
            if tt_id is not None:
                type_map[int(tt_id)] = {
                    'code': tt.get('type_code', f'type_{tt_id}'),
                    'name': tt.get('type_name', f'Type {tt_id}'),
                }

        # Aggregate: keep only the most recent attempt per (language, test_type)
        skill_stats: Dict[tuple, Dict] = {}
        for attempt in attempts_result.data:
            key = (attempt['language_id'], attempt['test_type_id'])
            if key not in skill_stats:
                skill_stats[key] = {
                    'elo_rating': attempt['user_elo_after'],
                    'last_test_date': attempt['created_at'],
                    'tests_taken': 1,
                }
            else:
                skill_stats[key]['tests_taken'] += 1

        # Build structured response
        ratings: Dict[str, Any] = {}
        for (language_id, test_type_id), stats in skill_stats.items():
            lang_id_int = int(language_id) if language_id is not None else None
            type_id_int = int(test_type_id) if test_type_id is not None else None

            lang_info = lang_map.get(lang_id_int, {
                'code': str(language_id), 'name': f'Language {language_id}',
            })
            type_info = type_map.get(type_id_int, {
                'code': str(test_type_id), 'name': f'Type {test_type_id}',
            })

            language_code = lang_info['code']
            if language_code not in ratings:
                ratings[language_code] = {
                    'language_name': lang_info['name'],
                    'native_name': lang_info.get('native_name', lang_info['name']),
                    'language_id': language_id,
                    'skills': {},
                }

            ratings[language_code]['skills'][type_info['code']] = {
                'elo_rating': stats['elo_rating'],
                'tests_taken': stats['tests_taken'],
                'last_test_date': stats['last_test_date'],
                'volatility': Config.DEFAULT_VOLATILITY,
                'skill_name': type_info['name'],
                'test_type_id': test_type_id,
            }

        return ratings


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
