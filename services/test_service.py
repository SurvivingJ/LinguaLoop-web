# services/test_service.py
"""
Test Service - Centralized business logic for test operations.
Extracted from routes/tests.py to maintain separation of concerns.
"""

import copy
import json
import hashlib
import logging
import threading
import time
import traceback
import weakref
from datetime import datetime, timezone, date
from uuid import UUID

from services.day_boundary import (
    local_day_start_utc, plan_row, plan_timezone, plan_today, plan_today_iso,
)
from typing import Optional, Dict, List, Any, Tuple

from config import Config
from services import request_cache
from services.concurrency import run_parallel
from services.supabase_factory import get_supabase, get_supabase_admin


def daily_load_row_key(user_id, language_id, load_date) -> tuple:
    """Request-cache key for today's daily_test_loads row (one per user/lang/day).

    Writers of that row inside a GET must call
    ``request_cache.invalidate('daily_load_row', str(user_id))``.
    """
    return ('daily_load_row', str(user_id), str(language_id), str(load_date))

# Re-export from dimension_service for backwards compatibility
from services.dimension_service import (
    DimensionService,
    parse_language_id,
    VALID_LANGUAGE_IDS,
    LANGUAGE_ID_TO_NAME,
    LANGUAGE_NAME_TO_ID,
)

logger = logging.getLogger(__name__)


#: Most recent attempts the legacy daily load looks at. Equal to PostgREST's
#: default row cap, which already truncated this read; now it is explicit.
DAILY_LOAD_ATTEMPT_WINDOW = 1000


class NoMatchingAttemptError(Exception):
    """daily-load/complete called for a test the user has not attempted today."""


# ============================================================================
# TEST LOOKUP AND STATIC CONTENT
# ============================================================================

def _is_uuid(value) -> bool:
    try:
        UUID(str(value))
        return True
    except (ValueError, AttributeError, TypeError):
        return False


def find_active_test(db, identifier, columns: str) -> Optional[Dict]:
    """Active test by slug, then by id when ``identifier`` is a uuid."""
    res = db.table('tests').select(columns).eq('slug', identifier).eq('is_active', True).execute()
    if not res.data and _is_uuid(identifier):
        res = db.table('tests').select(columns).eq('id', identifier).eq('is_active', True).execute()
    return res.data[0] if res.data else None


def find_active_test_by_slug(db, slug, columns: str = 'id, language_id') -> Optional[Dict]:
    """The single active test with this slug (submit paths)."""
    return db.table('tests').select(columns).eq('slug', slug).eq('is_active', True) \
        .single().execute().data


class TTLCache:
    """Small thread-safe cache: entries expire after ``ttl`` seconds and the
    oldest entry is dropped beyond ``maxsize``. Values are deep-copied in and
    out, so callers may mutate what they get."""

    def __init__(self, maxsize: int, ttl: float):
        self.maxsize, self.ttl = maxsize, ttl
        self._lock = threading.Lock()
        self._data: Dict[Any, Tuple[float, Any]] = {}

    def get(self, key):
        with self._lock:
            hit = self._data.get(key)
            if hit is None:
                return None
            if hit[0] < time.monotonic():
                self._data.pop(key, None)
                return None
            value = hit[1]
        return copy.deepcopy(value)

    def put(self, key, value) -> None:
        value = copy.deepcopy(value)
        with self._lock:
            self._data.pop(key, None)
            while len(self._data) >= self.maxsize:
                self._data.pop(next(iter(self._data)))
            self._data[key] = (time.monotonic() + self.ttl, value)

    def clear(self) -> None:
        with self._lock:
            self._data.clear()


#: Static content of a test as the test-open path reads it. Never holds
#: anything that depends on the caller. One cache per database client.
TEST_CONTENT_TTL_SECONDS = 120
TEST_CONTENT_MAX_ENTRIES = 128
_content_caches: "weakref.WeakKeyDictionary" = weakref.WeakKeyDictionary()
_content_caches_lock = threading.Lock()

TEST_OPEN_COLUMNS = (
    'id, slug, title, language_id, topic_id, difficulty, style, tier, transcript, '
    'audio_url, audio_generated, is_custom, is_featured, total_attempts, '
    'vocab_token_map, pinyin_payload, pitch_payload, furigana_payload, '
    'dim_languages(language_code, language_name)'
)
# TASK-882 / S14: the answer key (`answer`) and `answer_explanation` are
# deliberately NOT selected -- grading is server-side and both come back only
# in the submit response.
TEST_OPEN_QUESTION_COLUMNS = (
    'id, question_id, question_text, question_type_id, choices, '
    'points, audio_url'
)
TEST_OPEN_SENSE_COLUMNS = (
    'id, vocab_id, definition, pronunciation, sense_rank, definition_level, '
    'dim_vocabulary(lemma, part_of_speech, language_id)'
)


def _content_cache(db) -> Optional[TTLCache]:
    try:
        with _content_caches_lock:
            cache = _content_caches.get(db)
            if cache is None:
                cache = TTLCache(TEST_CONTENT_MAX_ENTRIES, TEST_CONTENT_TTL_SECONDS)
                _content_caches[db] = cache
            return cache
    except TypeError:  # a client that cannot be weakly referenced: no caching
        return None


def _load_test_questions(db, test_id) -> List[Dict]:
    # Ordered by question_id ("<slug>-qN", written in creation order) rather
    # than left unordered: the furigana payload is POSITIONAL — the page reads
    # furiganaPayload.questions[index] against this array's order — so an
    # unspecified row order lets readings drift onto the wrong question.
    return db.table('questions').select(TEST_OPEN_QUESTION_COLUMNS) \
        .eq('test_id', test_id).order('question_id').execute().data


def _load_test_sense_rows(db, token_map) -> List[Dict]:
    sense_ids = list(set(s for _, s in (token_map or []) if s))
    if not sense_ids:
        return []
    return db.table('dim_word_senses').select(TEST_OPEN_SENSE_COLUMNS) \
        .in_('id', sense_ids).execute().data or []


def get_test_content(db, identifier, also: Tuple = ()) -> Optional[Tuple]:
    """Static content for opening a test: ``(content, extras)`` or None.

    ``content`` is ``{'test': row, 'questions': rows, 'senses': rows}`` (the
    dim_word_senses rows behind the token map), cached in-process for
    TEST_CONTENT_TTL_SECONDS. ``also`` are callables taking the test row that
    return per-request data (ratings, per-user reads); they are never cached
    and run concurrently with whatever content still has to be read. Their
    results come back as ``extras``, in order. They run outside the request
    context.
    """
    cache = _content_cache(db)
    key = ('open', str(identifier))
    content = cache.get(key) if cache else None
    if content is not None:
        test = content['test']
        return content, run_parallel(*[(lambda f=f: f(test)) for f in also])

    test = find_active_test(db, identifier, TEST_OPEN_COLUMNS)
    if not test:
        return None
    results = run_parallel(
        lambda: _load_test_questions(db, test['id']),
        lambda: _load_test_sense_rows(db, test.get('vocab_token_map')),
        *[(lambda f=f: f(test)) for f in also],
    )
    content = {'test': test, 'questions': results[0], 'senses': results[1]}
    if cache:
        cache.put(key, content)
    return content, results[2:]


def get_test_skill_ratings(db, test_id) -> Dict[str, Dict]:
    """{type_code: {elo_rating, total_attempts}} for one test."""
    rows = db.table('test_skill_ratings').select(
        'test_type_id, elo_rating, total_attempts, dim_test_types(type_code)'
    ).eq('test_id', test_id).execute().data
    return {
        rating.get('dim_test_types', {}).get('type_code', 'unknown'): {
            'elo_rating': rating['elo_rating'],
            'total_attempts': rating['total_attempts'],
        }
        for rating in rows
    }


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
        if not self.admin:
            return []

        try:
            query = self.admin.table('tests').select(
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

        Returns formatted test data ready for the frontend. The answer key is
        never included (TASK-882 / S14); it is returned only by the submit
        endpoint. Reads use the service-role client so the `questions` /
        `tests` RLS policies can be tightened.
        """
        if not self.admin or not slug:
            return None

        try:
            # Fetch test
            # Active tests only: this is served without login. Explicit
            # columns: `tests` also carries the passage embedding and the
            # token/pinyin/pitch payloads, none of which this shape uses.
            t_res = self.admin.table('tests').select(
                'id, slug, language_id, difficulty, transcript, created_at'
            ).eq('slug', slug).eq('is_active', True).limit(1).execute()
            if not t_res.data:
                return None

            t = t_res.data[0]

            # Fetch questions. Ordered by question_id ("<slug>-qN", written in
            # creation order) to match the positional furigana payload — see the
            # equivalent fetch in routes/tests.py.
            q_res = self.admin.table('questions')\
                .select('id, question_text, choices')\
                .eq('test_id', t['id'])\
                .order('question_id')\
                .execute()

            q_rows = q_res.data or []

            # Parse questions
            questions = []
            for q in q_rows:
                questions.append({
                    'id': q['id'],
                    'question': q['question_text'],
                    'choices': self._parse_choices(q.get('choices')),
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
        if not self.admin:
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

            attempt_result = self.admin.table('test_attempts').insert(attempt_record).execute()
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
                self.admin.table('attempt_responses').insert(responses_to_insert).execute()

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

        Routing (Phase 13 — Study Plans):
          1. If today's load already exists in daily_test_loads, return it.
          2. Else if Config.STUDY_PLAN_ENABLED AND user has a user_study_plans
             row for (user, language_id), delegate to build_daily_session
             (Tier C resolver — see [[features/study-plans.tech]]). On
             success, the RPC has already UPSERTed daily_test_loads +
             daily_test_load_items; re-fetch and enrich.
          3. Else (or if build_daily_session returns E_NOPLAN / E_NOWEEK):
             fall back to legacy _compute_daily_load.

        Returns dict with load_date, tests (enriched), and progress.
        """
        # ADR-022 / TASK-716: "today" is the learner's LOCAL date, resolved
        # through user_study_plans.timezone by the one shared helper that
        # routes/study_session.py also calls. Unset / invalid zones fail safe
        # to UTC inside the helper, so this never raises.
        today = plan_today_iso(self.admin, user_id, language_id)

        # Check if today's load already exists. This short-circuit is also the
        # timezone-change policy (ADR-022): if a learner edits their timezone
        # so the local date moves BACKWARDS onto a date that already has a row,
        # we serve that row verbatim and never re-invoke the resolver — so
        # TASK-705's same-day-safe path is not exercised and no progress can be
        # disturbed. A forward move simply starts a new date.
        existing = self.admin.table('daily_test_loads')\
            .select('*')\
            .eq('user_id', user_id)\
            .eq('language_id', language_id)\
            .eq('load_date', today)\
            .execute()

        if existing.data:
            # GET /api/study-session reads this same row again for its targets
            # and completed blocks; hand it over (latency 2026-11, ADR-043 B).
            request_cache.put(daily_load_row_key(user_id, language_id, today), existing.data[0])
            return self._enrich_daily_load(existing.data[0])

        # ------------------------------------------------------------------
        # Phase 13 routing: try Study Plan resolver first if enabled.
        # ------------------------------------------------------------------
        if Config.STUDY_PLAN_ENABLED and self._user_has_study_plan(user_id, language_id):
            try:
                from services.study_plan_service import StudyPlanService, _monday_of
                svc = StudyPlanService(db=self.admin)
                # Pass the SAME local date the row lookup above used (ADR-022).
                # Letting the wrapper default to date.today() would reintroduce
                # a second, server-local derivation of "today".
                local_today = date.fromisoformat(today)
                resolver_result = svc.build_daily_session(
                    user_id, language_id, local_today,
                )

                # E_NOWEEK: no weekly_plan_states row exists for the target
                # week (a freshly-created plan, or the Sunday pacer has not
                # seeded it yet). Lazily compute the week once, then retry the
                # resolver. This is rate-guarded by construction — it only fires
                # on the absent-week code, never on a normal request — so the
                # retry either succeeds or we fall through to legacy below.
                if (isinstance(resolver_result, dict)
                        and resolver_result.get('code') == 'E_NOWEEK'):
                    raw_week = resolver_result.get('week_start')
                    try:
                        week_start = (
                            date.fromisoformat(raw_week) if raw_week
                            else _monday_of(local_today)
                        )
                    except (TypeError, ValueError):
                        week_start = _monday_of(local_today)
                    logger.info(
                        'build_daily_session E_NOWEEK for user=%s lang=%s; '
                        'lazily computing weekly plan for week=%s and retrying',
                        user_id, language_id, week_start,
                    )
                    svc.compute_weekly_plan(user_id, language_id, week_start)
                    resolver_result = svc.build_daily_session(
                        user_id, language_id, local_today,
                    )

                # Non-error result means the RPC UPSERTed; re-fetch + enrich.
                if isinstance(resolver_result, dict) and 'error' not in resolver_result:
                    self._log_hydration_shortfalls(user_id, language_id, resolver_result)
                    refetched = self.admin.table('daily_test_loads')\
                        .select('*')\
                        .eq('user_id', user_id)\
                        .eq('language_id', language_id)\
                        .eq('load_date', today)\
                        .execute()
                    if refetched.data:
                        request_cache.put(daily_load_row_key(user_id, language_id, today), refetched.data[0])
                        return self._enrich_daily_load(refetched.data[0])
                else:
                    # Logged error code (E_NOPLAN / E_NOWEEK / E_RPC); fall through.
                    logger.info(
                        'build_daily_session declined for user=%s lang=%s: %s; '
                        'falling back to legacy _compute_daily_load',
                        user_id, language_id, resolver_result,
                    )
            except Exception as e:
                logger.warning(
                    'build_daily_session crashed for user=%s lang=%s: %s; '
                    'falling back to legacy _compute_daily_load',
                    user_id, language_id, e,
                )

        # Legacy path
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

        request_cache.put(daily_load_row_key(user_id, language_id, today), record.data[0])
        return self._enrich_daily_load(record.data[0])

    @staticmethod
    def _log_hydration_shortfalls(user_id: str, language_id: int, resolver_result: Dict) -> None:
        """Emit a WARNING per skill where build_daily_session budgeted more test
        slots than it could hydrate (TASK-702).

        The resolver reports per-skill ``requested_counts`` (budgeted),
        ``hydrated_counts`` (never-attempted / primary fill only) and
        ``replay_counts`` (exhausted-pool fallback fill) in its return jsonb.
        ``hydrated < requested`` means the never-attempted pool ran dry — the F3
        failure class that silently dropped pinyin / pitch_accent /
        classifier_drill slots in production. We WARN on that regardless of
        whether replay covered the gap: replay is a band-aid, and a slot that
        can only be filled by replaying old tests still signals a content
        shortfall worth acting on. The message records how the gap resolved
        (replay-covered vs slots dropped). Best-effort: never raise into the
        daily-load path.
        """
        try:
            requested = resolver_result.get('requested_counts') or {}
            hydrated = resolver_result.get('hydrated_counts') or {}
            replay = resolver_result.get('replay_counts') or {}
            for skill, req in requested.items():
                got = hydrated.get(skill, 0)
                if got >= req:
                    continue
                covered = replay.get(skill, 0)
                dropped = req - got - covered
                if dropped > 0:
                    resolution = (
                        'replay covered %s, %s slot(s) DROPPED' % (covered, dropped)
                    )
                else:
                    resolution = 'replay covered the %s-slot gap' % (req - got)
                logger.warning(
                    'build_daily_session hydration shortfall for user=%s '
                    'lang=%s skill=%s: requested=%s hydrated=%s '
                    '(never-attempted pool exhausted; %s)',
                    user_id, language_id, skill, req, got, resolution,
                )
        except Exception as e:  # pragma: no cover - pure observability
            logger.debug('shortfall logging skipped: %s', e)

    def _user_has_study_plan(self, user_id: str, language_id: int) -> bool:
        """Cheap probe: does user_study_plans have a row for (user, language)?"""
        try:
            return plan_row(self.admin, user_id, language_id) is not None
        except Exception as e:
            logger.warning('user_study_plans probe failed: %s', e)
            return False

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

        # Session modules (ADR-032): a learner who switched a test type off in
        # the Study Plan must not get it from this legacy path either. No plan
        # row (or a failed read) means no exclusions.
        excluded = self._excluded_modules(user_id, language_id)

        # Build test_type id-to-code map
        id_to_type_code = {}
        if DimensionService._test_type_cache:
            id_to_type_code = {v: k for k, v in DimensionService._test_type_cache.items()}

        # Step 1: Find retry candidates (poorly performed tests)
        try:
            attempts_result = self.admin.table('test_attempts')\
                .select('test_id, percentage, test_type_id, created_at, user_elo_after')\
                .eq('user_id', user_id)\
                .eq('language_id', language_id)\
                .order('created_at', desc=True)\
                .limit(DAILY_LOAD_ATTEMPT_WINDOW)\
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
            if excluded and id_to_type_code.get(a['test_type_id'], 'listening') in excluded:
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
            try:
                recommended_result = self.admin.rpc('get_recommended_tests', {
                    'p_user_id': user_id,
                    'p_language_id': language_id
                }).execute()

                recommended = recommended_result.data or []

                # Filter out already-selected and already-attempted tests
                new_tests = [
                    t for t in recommended
                    if t.get('test_id') not in selected_test_ids
                    and t.get('test_id') not in latest_by_test
                    and t.get('test_type', 'listening') not in excluded
                ]

                # One test per topic per day: two tests on the same topic let
                # the first give away the second (a dictation and a reading
                # on the same T-shirt, 2026-11-11 walkthrough).
                topic_of = self._topics_for(
                    [t.get('test_id') for t in new_tests] + list(selected_test_ids))
                used_topics = {topic_of[tid] for tid in selected_test_ids if topic_of.get(tid)}

                for t in new_tests:
                    if num_new <= 0:
                        break
                    if t.get('test_id') in selected_test_ids:
                        continue
                    topic = topic_of.get(t.get('test_id'))
                    if topic and topic in used_topics:
                        continue
                    if topic:
                        used_topics.add(topic)
                    load_items.append({
                        'test_id': t['test_id'],
                        'slot_type': 'new',
                        'test_type': t.get('test_type', 'listening')
                    })
                    selected_test_ids.add(t['test_id'])
                    num_new -= 1

            except Exception as e:
                logger.error(f"Error fetching recommended tests for daily load: {e}")

        # Step 4: If still need more tests, fall back to a direct ELO-matched query.
        # The recommended-tests RPC can under-serve (skill gaps, exhausted pool), so
        # this last-resort query pulls active tests in the user's ELO band and — the
        # point of TASK-707 — carries each test's *real* skill type so the runner
        # mounts the correct player and rates the correct skill (F9). We read from
        # test_skill_ratings (not `tests`) because both ELO and skill type live there,
        # one row per (test, skill); the `tests!inner` embed scopes to the language and
        # active tests.
        if num_new > 0:
            try:
                # Approximate the user's ELO from their most recent attempt in this
                # language. user_elo_after is per-skill, but the latest value is a
                # good-enough centre for the band; unrated users default to 1200.
                user_elo = 1200
                for a in (attempts_result.data or []):
                    # attempts_result is ordered created_at desc — first is most recent
                    user_elo = a.get('user_elo_after') or 1200
                    break

                elo_min = max(400, user_elo - 200)
                elo_max = min(3000, user_elo + 200)

                fallback_result = self.admin.table('test_skill_ratings')\
                    .select('test_id, elo_rating, dim_test_types(type_code), '
                            'tests!inner(id, is_active, language_id)')\
                    .eq('tests.language_id', language_id)\
                    .eq('tests.is_active', True)\
                    .gte('elo_rating', elo_min)\
                    .lte('elo_rating', elo_max)\
                    .limit(50)\
                    .execute()

                for r in (fallback_result.data or []):
                    test_id = r['test_id']
                    if test_id in selected_test_ids or test_id in latest_by_test:
                        continue
                    type_code = (r.get('dim_test_types') or {}).get('type_code', 'listening')
                    if type_code in excluded:
                        continue
                    load_items.append({
                        'test_id': test_id,
                        'slot_type': 'new',
                        'test_type': type_code
                    })
                    selected_test_ids.add(test_id)
                    num_new -= 1
                    if num_new <= 0:
                        break

            except Exception as e:
                logger.error(f"Error in fallback test selection for daily load: {e}")

        return load_items

    def _excluded_modules(self, user_id: str, language_id: int) -> set:
        """The learner's ``user_study_plans.excluded_modules`` as a set.

        Empty when there is no plan row or the read fails (fail open: the legacy
        path must keep producing a load).
        """
        try:
            row = plan_row(self.admin, user_id, language_id)
            if row:
                return {m for m in (row.get('excluded_modules') or []) if isinstance(m, str)}
        except Exception as e:
            logger.warning(f"Could not read excluded_modules for daily load: {e}")
        return set()

    @staticmethod
    def _normalize_load_item(item):
        """Coerce one test_ids element to the canonical dict shape.

        Elements are dicts {test_id, test_type, slot_type, ...} from both the
        legacy _compute_daily_load and the current build_daily_session
        (phase13_build_daily_session_test_objs.sql). Defensively tolerate the
        pre-fix build_daily_session output (bare UUID strings) so an old cached
        row never 500s enrichment; bare strings lose the per-slot mode, so we
        default test_type='listening' / slot_type='new'.
        """
        if isinstance(item, str):
            return {'test_id': item, 'test_type': 'listening', 'slot_type': 'new'}
        return item

    def _enrich_daily_load(self, cached_record: Dict) -> Dict:
        """
        Take a raw daily_test_loads row and enrich with full test details.
        """
        test_ids_list = [
            self._normalize_load_item(i)
            for i in (cached_record.get('test_ids', []) or [])
        ]
        completed = cached_record.get('completed_test_ids', []) or []

        if not test_ids_list:
            return {
                'load_date': cached_record.get('load_date'),
                'tests': [],
                'progress': {'completed': 0, 'total': 0}
            }

        # Fetch full test details and their ELO ratings in ONE round trip
        # (embedded resource; latency 2026-11, ADR-043 B). Falls back to the
        # two separate queries below if the embed fails.
        ids = [item['test_id'] for item in test_ids_list]
        tests_map: Dict[str, Dict] = {}
        ratings_map: Dict[str, Dict] = {}
        embedded_ok = False
        try:
            tests_result = self.admin.table('tests').select(
                'id, slug, title, language_id, difficulty, style, tier, '
                'audio_url, audio_generated, is_custom, total_attempts, '
                'test_skill_ratings(test_type_id, elo_rating, dim_test_types(type_code))'
            ).in_('id', ids).execute()
            for t in (tests_result.data or []):
                ratings = t.pop('test_skill_ratings', None) or []
                tests_map[t['id']] = t
                for rating in ratings:
                    type_code = (rating.get('dim_test_types') or {}).get('type_code', 'unknown')
                    ratings_map.setdefault(t['id'], {})[type_code] = rating['elo_rating']
            embedded_ok = True
        except Exception as e:
            logger.warning(f"Embedded tests+ratings read failed, using two queries: {e}")

        if not embedded_ok:
            try:
                tests_result = self.admin.table('tests').select(
                    'id, slug, title, language_id, difficulty, style, tier, '
                    'audio_url, audio_generated, is_custom, total_attempts'
                ).in_('id', ids).execute()

                tests_map = {t['id']: t for t in (tests_result.data or [])}
            except Exception as e:
                logger.error(f"Error enriching daily load: {e}")
                tests_map = {}

        # Fetch ELO ratings for these tests (fallback path only)
        if ids and not embedded_ok:
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
        # Same local-date derivation as get_or_create_daily_load (ADR-022) —
        # if these two diverged, a learner could complete a slot against a row
        # that the GET never showed them.
        today = plan_today_iso(self.admin, user_id, language_id)

        # TASK-882 / S15: a slot is completed only if the caller really has a
        # test_attempts row for this test since the start of their local day.
        # Without this any user could mark any test complete via the API.
        day_start = local_day_start_utc(plan_timezone(self.admin, user_id, language_id))
        attempt = self.admin.table('test_attempts')\
            .select('id')\
            .eq('user_id', user_id)\
            .eq('test_id', test_id)\
            .gte('created_at', day_start.isoformat())\
            .limit(1)\
            .execute()
        if not attempt.data:
            raise NoMatchingAttemptError("No attempt recorded today for this test")

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

    def _topics_for(self, test_ids) -> Dict:
        """{test_id: topic_id} for these tests (missing/None topics omitted).
        Best effort: {} on failure, which simply skips the topic check."""
        ids = [t for t in dict.fromkeys(test_ids) if t]
        if not ids:
            return {}
        try:
            rows = self.admin.table('tests').select('id, topic_id').in_('id', ids).execute().data or []
        except Exception as e:
            logger.warning("topic lookup for daily load failed: %s", e)
            return {}
        return {r['id']: r.get('topic_id') for r in rows if r.get('topic_id')}

    def mark_daily_slot_complete_on_submit(self, user_id: str, language_id: int,
                                           test_id: str) -> bool:
        """Mark today's daily-load slot complete as soon as a test is submitted.

        Called by the submit routes right after the submission RPC recorded the
        attempt, so no attempt check is needed here. Before this, a slot was
        only marked complete when the learner pressed "Next" on the results
        card; closing the page there left the slot open, the session served the
        same test again and a re-submit was scored again.

        Only tests that are in today's load are marked; a test taken from
        Browse Tests that is not in the load changes nothing. Idempotent: the
        client's later POST to /daily-load/complete finds it already done.

        Returns True when the slot is (now) complete, False when there is no
        load today or the test is not in it.
        """
        today = plan_today_iso(self.admin, user_id, language_id)
        rows = self.admin.table('daily_test_loads')\
            .select('id, test_ids, completed_test_ids')\
            .eq('user_id', user_id)\
            .eq('language_id', language_id)\
            .eq('load_date', today)\
            .limit(1)\
            .execute().data or []
        if not rows:
            return False
        row = rows[0]
        # test_ids holds slot objects ({test_id, slot_type, test_type}) from
        # the Study Plan resolver, plain ids from the legacy path.
        scheduled = {str(t.get('test_id') if isinstance(t, dict) else t)
                     for t in (row.get('test_ids') or [])}
        if str(test_id) not in scheduled:
            return False
        completed = list(row.get('completed_test_ids') or [])
        if str(test_id) in {str(t) for t in completed}:
            return True
        completed.append(test_id)
        self.admin.table('daily_test_loads')\
            .update({'completed_test_ids': completed})\
            .eq('id', row['id'])\
            .execute()
        request_cache.invalidate('daily_load_row', str(user_id))
        return True

    # -------------------------------------------------------------------------
    # CONTENT MODERATION
    # -------------------------------------------------------------------------

    def record_flagged_input(self, user_email: str, content: str,
                             flagged_categories: List[str] = None) -> None:
        """Record flagged input for analytics."""
        if not self.admin:
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

            self.admin.table('flagged_inputs').insert(record).execute()
        except Exception as e:
            logger.warning(f"Failed to record flagged input: {e}")

    def get_user_elo_summary(self, user_id: str) -> Dict[str, Any]:
        """Aggregate ELO ratings across all languages and skills for a user.

        Returns a dict keyed by language code, each containing skill ratings.
        """
        skill_stats = self._skill_attempt_stats(user_id)
        if not skill_stats:
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

    def _skill_attempt_stats(self, user_id: str) -> Dict[tuple, Dict]:
        """{(language_id, test_type_id): {elo_rating, last_test_date,
        tests_taken}} from test_attempts, most recently attempted skill first.

        Reads one row and an exact count per skill the user has a rating row
        for, instead of the whole attempt history. A total-count check proves
        no attempt was missed (a skill without a rating row, a NULL key);
        if it does not add up, or any read fails, the full history is read
        as before.
        """
        try:
            pairs = self.admin.table('user_skill_ratings') \
                .select('language_id, test_type_id') \
                .eq('user_id', user_id) \
                .execute().data or []
            keys = list(dict.fromkeys((p['language_id'], p['test_type_id']) for p in pairs))
            if keys and len(keys) <= self._MAX_SKILL_READS:
                def latest(key):
                    return self.admin.table('test_attempts') \
                        .select('user_elo_after, created_at', count='exact') \
                        .eq('user_id', user_id) \
                        .eq('language_id', key[0]) \
                        .eq('test_type_id', key[1]) \
                        .order('created_at', desc=True) \
                        .limit(1) \
                        .execute()

                total, *per_skill = run_parallel(
                    lambda: self.admin.table('test_attempts')
                    .select('id', count='exact', head=True)
                    .eq('user_id', user_id).execute(),
                    *[(lambda k=k: latest(k)) for k in keys],
                )
                found = []
                counted = 0
                for key, res in zip(keys, per_skill):
                    if not res.data:
                        continue
                    if not isinstance(res.count, int):
                        raise ValueError('no exact count returned')
                    counted += res.count
                    found.append((key, {
                        'elo_rating': res.data[0]['user_elo_after'],
                        'last_test_date': res.data[0]['created_at'],
                        'tests_taken': res.count,
                    }))
                if isinstance(total.count, int) and counted == total.count:
                    found.sort(key=lambda kv: kv[1]['last_test_date'] or '', reverse=True)
                    return dict(found)
        except Exception as e:
            logger.info("per-skill attempt stats unavailable, reading full history: %s", e)

        attempts_result = self.admin.table('test_attempts') \
            .select('language_id, test_type_id, user_elo_after, created_at') \
            .eq('user_id', user_id) \
            .order('created_at', desc=True) \
            .execute()

        # Keep only the most recent attempt per (language, test_type)
        skill_stats: Dict[tuple, Dict] = {}
        for attempt in attempts_result.data or []:
            key = (attempt['language_id'], attempt['test_type_id'])
            if key not in skill_stats:
                skill_stats[key] = {
                    'elo_rating': attempt['user_elo_after'],
                    'last_test_date': attempt['created_at'],
                    'tests_taken': 1,
                }
            else:
                skill_stats[key]['tests_taken'] += 1
        return skill_stats

    _MAX_SKILL_READS = 14

    # -------------------------------------------------------------------------
    # DICTATION WITHHOLDING
    # -------------------------------------------------------------------------

    def has_pending_dictation_slot(self, user_id: str, language_id: int, test_id: str) -> bool:
        """True when today's daily load schedules this test as dictation and
        the slot is not completed yet. A failed read counts as not pending."""
        try:
            today = plan_today_iso(self.admin, user_id, language_id)
            rows = self.admin.table('daily_test_loads')\
                .select('test_ids, completed_test_ids')\
                .eq('user_id', user_id)\
                .eq('language_id', language_id)\
                .eq('load_date', today)\
                .limit(1)\
                .execute().data or []
        except Exception as e:
            logger.warning("dictation slot check failed for test %s: %s", test_id, e)
            return False
        if not rows:
            return False
        completed = {str(t) for t in (rows[0].get('completed_test_ids') or [])}
        if str(test_id) in completed:
            return False
        return any(
            isinstance(t, dict) and str(t.get('test_id')) == str(test_id)
            and t.get('test_type') == 'dictation'
            for t in (rows[0].get('test_ids') or [])
        )


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
