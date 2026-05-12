"""
Exercise Session Service — daily exercise scheduling

Builds personalised exercise sessions by combining:
- FSRS due flashcards (spaced repetition reviews)
- BKT uncertainty-zone words (active learning)
- New/encountered words (introduction)
- Vocabulary ladder content (delegated to get_ladder_session)
- Supplementary grammar/collocation exercises
- Virtual jumbled sentences from past test transcripts (Python-only,
  depends on language-specific tokenisation)

Session selection lives entirely in the SQL RPC `get_exercise_session`
(migrations/phase9_get_exercise_session.sql). This service orchestrates:
RPC call → append virtual picks → cache → enrich for frontend.
Per-attempt updates (BKT, FSRS, lapse penalty) remain Python.

Follows the TestService singleton pattern.
"""

import logging
import random
from datetime import date, datetime, timezone
from typing import Dict, List, Optional
from uuid import uuid4

from config import Config
from services.supabase_factory import get_supabase_admin
from services.vocabulary.knowledge_service import VocabularyKnowledgeService
from services.vocabulary.fsrs import CardState, schedule_review, AGAIN, GOOD, EASY

logger = logging.getLogger(__name__)


class ExerciseSessionService:
    """Builds and manages daily exercise sessions."""

    def __init__(self, db=None):
        self.db = db or get_supabase_admin()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_or_create_daily_session(
        self, user_id: str, language_id: int
    ) -> Dict:
        """Get today's exercise session, computing if needed."""
        today = date.today().isoformat()

        # Check for cached session
        existing = (
            self.db.table('user_exercise_sessions')
            .select('*')
            .eq('user_id', user_id)
            .eq('language_id', language_id)
            .execute()
        )

        if existing.data:
            row = existing.data[0]
            if row.get('load_date') == today:
                return self._enrich_session(row)

        # Compute new session
        session_size = self._get_user_session_size(user_id)
        exercise_items = self._compute_session(user_id, language_id, session_size)

        if not exercise_items:
            return {
                'load_date': today,
                'exercises': [],
                'progress': {'completed': 0, 'total': 0},
                'session_size': session_size,
            }

        # Upsert into cache
        record = {
            'user_id': user_id,
            'language_id': language_id,
            'load_date': today,
            'exercise_ids': exercise_items,
            'completed_ids': [],
            'session_size': session_size,
            'created_at': datetime.now(timezone.utc).isoformat(),
        }

        self.db.table('user_exercise_sessions').upsert(
            record, on_conflict='user_id,language_id'
        ).execute()

        return self._enrich_session(record)

    def mark_exercise_complete(
        self, user_id: str, language_id: int, exercise_id: str
    ) -> Dict:
        """Mark an exercise as completed in the cached session."""
        existing = (
            self.db.table('user_exercise_sessions')
            .select('*')
            .eq('user_id', user_id)
            .eq('language_id', language_id)
            .execute()
        )

        if not existing.data:
            return {'error': 'No active session'}

        row = existing.data[0]
        completed = row.get('completed_ids', []) or []

        if exercise_id not in completed:
            completed.append(exercise_id)

        self.db.table('user_exercise_sessions').update(
            {'completed_ids': completed}
        ).eq('user_id', user_id).eq('language_id', language_id).execute()

        total = len(row.get('exercise_ids', []))
        return {
            'progress': {'completed': len(completed), 'total': total},
        }

    def record_attempt_with_updates(
        self,
        user_id: str,
        exercise_id: str,
        is_correct: bool,
        user_response: dict = None,
        time_taken_ms: int = None,
    ) -> Dict:
        """Record an exercise attempt and trigger BKT + FSRS updates.

        Returns dict with attempt result and any knowledge updates.
        """
        # 1. Look up the exercise to get metadata
        exercise = (
            self.db.table('exercises')
            .select('id, exercise_type, word_sense_id, grammar_pattern_id, '
                    'corpus_collocation_id, attempt_count, correct_count')
            .eq('id', exercise_id)
            .single()
            .execute()
            .data
        )

        if not exercise:
            return {'error': 'Exercise not found'}

        exercise_type = exercise.get('exercise_type')
        sense_id = exercise.get('word_sense_id')

        # Determine whether this is the user's first attempt at this exercise.
        # BKT is gated on first attempts only — repeat attempts on the same
        # exercise would double-count evidence and inflate p_known. This
        # mirrors the gating in LadderService.record_attempt().
        prior_resp = (
            self.db.table('exercise_attempts')
            .select('id')
            .eq('user_id', user_id)
            .eq('exercise_id', exercise_id)
            .limit(1)
            .execute()
        )
        is_first_attempt = not bool(prior_resp.data)

        # 2. Insert attempt with denormalized columns
        attempt_row = {
            'user_id': user_id,
            'exercise_id': exercise_id,
            'user_response': user_response or {},
            'is_correct': is_correct,
            'time_taken_ms': time_taken_ms,
            'exercise_type': exercise_type,
            'sense_id': sense_id,
            'created_at': datetime.now(timezone.utc).isoformat(),
        }
        self.db.table('exercise_attempts').insert(attempt_row).execute()

        # 3. Update exercise-level stats
        updates = {
            'attempt_count': (exercise.get('attempt_count') or 0) + 1,
        }
        if is_correct:
            updates['correct_count'] = (exercise.get('correct_count') or 0) + 1
        self.db.table('exercises').update(updates).eq('id', exercise_id).execute()

        result = {
            'is_correct': is_correct,
            'exercise_type': exercise_type,
            'is_first_attempt': is_first_attempt,
        }

        # 4. BKT + FSRS updates for vocabulary exercises
        if sense_id:
            # Fetch language_id from the exercise or the user's flashcard
            lang_resp = (
                self.db.table('exercises')
                .select('language_id')
                .eq('id', exercise_id)
                .single()
                .execute()
            )
            language_id = lang_resp.data.get('language_id') if lang_resp.data else None

            if language_id:
                # BKT update — first attempts only, to avoid inflating p_known on retries.
                if is_first_attempt:
                    knowledge_svc = VocabularyKnowledgeService(self.db)
                    bkt_result = knowledge_svc.update_from_word_test(
                        user_id=user_id,
                        sense_id=sense_id,
                        is_correct=is_correct,
                        language_id=language_id,
                        exercise_type=exercise_type,
                    )
                    if bkt_result:
                        result['bkt_update'] = bkt_result

                # FSRS schedule update — every attempt is legitimate scheduling signal,
                # so this runs regardless of is_first_attempt.
                self._update_fsrs_for_exercise(
                    user_id, sense_id, is_correct, time_taken_ms
                )

        return result

    # ------------------------------------------------------------------
    # Internal: session computation
    # ------------------------------------------------------------------

    def _compute_session(
        self, user_id: str, language_id: int, session_size: int
    ) -> List[Dict]:
        """Build today's session via the get_exercise_session SQL RPC.

        Steps:
          1. Call the RPC for vocab / ladder / supplementary picks.
          2. Append up to 3 virtual jumbled sentences from the user's past
             test transcripts (Python-side because tokenisation is
             language-specific).
          3. Shuffle so the session isn't grouped by bucket.
        """
        picks: List[Dict] = []

        try:
            from services.irt.calibrator import compute_user_theta_for_selection
            user_theta = compute_user_theta_for_selection(self.db, user_id, language_id)
        except Exception as e:
            logger.warning(f"Theta lookup failed; defaulting to 0.0: {e}")
            user_theta = 0.0

        try:
            resp = self.db.rpc('get_exercise_session', {
                'p_user_id': user_id,
                'p_language_id': language_id,
                'p_session_size': session_size,
                'p_user_theta': user_theta,
            }).execute()

            for row in (resp.data or []):
                picks.append({
                    'exercise_id': row['out_exercise_id'],
                    'sense_id': row.get('out_sense_id'),
                    'exercise_type': row['out_exercise_type'],
                    'slot_type': row['out_slot_type'],
                    'phase': row.get('out_phase') or '',
                    'is_virtual': False,
                })
        except Exception as e:
            logger.error(f"get_exercise_session RPC failed: {e}")

        # Append up to 3 virtual jumbled sentences from past tests.
        # Capped at 3 historically; never displace real exercises.
        virtual_slots = min(3, max(0, session_size - len(picks)))
        if virtual_slots > 0:
            test_sentences = self._get_user_test_sentences(
                user_id, language_id, virtual_slots
            )
            for sent in test_sentences:
                picks.append({
                    'exercise_id': f"virtual-jumbled-{uuid4()}",
                    'sense_id': None,
                    'exercise_type': 'jumbled_sentence',
                    'slot_type': 'user_test',
                    'phase': 'B',
                    'is_virtual': True,
                    'virtual_content': {
                        'original_sentence': sent['sentence'],
                        'source_test_id': sent['test_id'],
                    },
                })

        random.shuffle(picks)
        return picks

    def _get_user_test_sentences(
        self, user_id: str, language_id: int, count: int
    ) -> List[Dict]:
        """Pull sentences from tests the user scored >50% on.

        Stays in Python because tokenisation is language-specific
        (jieba for Chinese, etc.) via LanguageProcessor.
        """
        try:
            resp = (
                self.db.table('test_attempts')
                .select('test_id, percentage')
                .eq('user_id', user_id)
                .gt('percentage', 50)
                .order('created_at', desc=True)
                .limit(20)
                .execute()
            )
            test_ids = list(set(row['test_id'] for row in (resp.data or [])))
            if not test_ids:
                return []

            test_resp = (
                self.db.table('tests')
                .select('id, transcript, language_id')
                .in_('id', test_ids)
                .eq('language_id', language_id)
                .execute()
            )

            from services.exercise_generation.language_processor import LanguageProcessor
            processor = LanguageProcessor.for_language(language_id)
            sentences = []
            for test in (test_resp.data or []):
                if not test.get('transcript'):
                    continue
                for sent in processor.split_sentences(test['transcript']):
                    if len(sent.strip()) < 5:
                        continue
                    words = processor.tokenize(sent)
                    if len(words) >= 3:
                        sentences.append({
                            'sentence': sent,
                            'test_id': test['id'],
                        })

            random.shuffle(sentences)
            return sentences[:count]
        except Exception as e:
            logger.error(f"Error fetching user test sentences: {e}")
            return []

    # ------------------------------------------------------------------
    # Internal: FSRS update
    # ------------------------------------------------------------------

    def _update_fsrs_for_exercise(
        self, user_id: str, sense_id: int,
        is_correct: bool, time_taken_ms: int = None,
    ):
        """Update FSRS flashcard scheduling after an exercise attempt."""
        try:
            card_resp = (
                self.db.table('user_flashcards')
                .select('id, stability, difficulty, due_date, last_review, '
                        'reps, lapses, state')
                .eq('user_id', user_id)
                .eq('sense_id', sense_id)
                .execute()
            )

            if not card_resp.data:
                return  # No flashcard for this sense

            row = card_resp.data[0]

            last_review = None
            if row.get('last_review'):
                last_review = datetime.fromisoformat(
                    row['last_review'].replace('Z', '+00:00')
                ).date()

            card = CardState(
                stability=row.get('stability', 0),
                difficulty=row.get('difficulty', 0.3),
                due_date=(
                    date.fromisoformat(row['due_date'])
                    if row.get('due_date') else None
                ),
                last_review=last_review,
                reps=row.get('reps', 0),
                lapses=row.get('lapses', 0),
                state=row.get('state', 'new'),
            )

            # Derive rating from correctness and speed
            if not is_correct:
                rating = AGAIN
            elif time_taken_ms is not None and time_taken_ms < 5000:
                rating = EASY
            else:
                rating = GOOD

            new_card = schedule_review(card, rating)

            self.db.table('user_flashcards').update({
                'stability': new_card.stability,
                'difficulty': new_card.difficulty,
                'due_date': (
                    new_card.due_date.isoformat() if new_card.due_date else None
                ),
                'last_review': date.today().isoformat(),
                'reps': new_card.reps,
                'lapses': new_card.lapses,
                'state': new_card.state,
                'updated_at': 'now()',
            }).eq('id', row['id']).execute()

            # FSRS lapse → BKT penalty: if lapses increased, penalize p_known
            if new_card.lapses > card.lapses:
                try:
                    self.db.rpc('bkt_apply_lapse_penalty', {
                        'p_user_id': user_id,
                        'p_sense_id': sense_id,
                    }).execute()
                    logger.debug(f"BKT lapse penalty applied for sense {sense_id}")
                except Exception as lapse_err:
                    logger.error(f"BKT lapse penalty failed for sense {sense_id}: {lapse_err}")

        except Exception as e:
            logger.error(f"FSRS update failed for sense {sense_id}: {e}")

    # ------------------------------------------------------------------
    # Internal: helpers
    # ------------------------------------------------------------------

    def _get_user_session_size(self, user_id: str) -> int:
        """Read session size from user preferences."""
        try:
            resp = (
                self.db.table('users')
                .select('exercise_preferences')
                .eq('id', user_id)
                .single()
                .execute()
            )
            prefs = resp.data.get('exercise_preferences') or {}
            size = prefs.get('session_size', Config.DEFAULT_EXERCISE_SESSION_SIZE)
            return max(
                Config.MIN_EXERCISE_SESSION_SIZE,
                min(Config.MAX_EXERCISE_SESSION_SIZE, int(size)),
            )
        except Exception:
            return Config.DEFAULT_EXERCISE_SESSION_SIZE

    def _enrich_session(self, cached_record: Dict) -> Dict:
        """Take a cached session row and enrich with full exercise content."""
        exercise_items = cached_record.get('exercise_ids', [])
        completed = cached_record.get('completed_ids', []) or []

        if not exercise_items:
            return {
                'load_date': cached_record.get('load_date'),
                'exercises': [],
                'progress': {'completed': 0, 'total': 0},
                'session_size': cached_record.get('session_size', 0),
            }

        # Fetch full exercise content
        exercise_ids = [item['exercise_id'] for item in exercise_items]
        try:
            resp = (
                self.db.table('exercises')
                .select('id, exercise_type, source_type, content, complexity_tier, '
                        'word_sense_id, difficulty_static')
                .in_('id', exercise_ids)
                .execute()
            )
            exercise_map = {row['id']: row for row in (resp.data or [])}
        except Exception as e:
            logger.error(f"Error fetching exercises for enrichment: {e}")
            exercise_map = {}

        # Fetch word sense definitions for vocabulary exercises
        sense_ids = [
            item['sense_id'] for item in exercise_items
            if item.get('sense_id')
        ]
        sense_lookup = {}
        if sense_ids:
            try:
                unique_ids = list(set(sense_ids))
                sense_resp = (
                    self.db.table('dim_word_senses')
                    .select('id, definition, pronunciation, dim_vocabulary(lemma)')
                    .in_('id', unique_ids)
                    .execute()
                )
                sense_lookup = {
                    row['id']: row for row in (sense_resp.data or [])
                }
            except Exception as e:
                logger.error(f"Error fetching sense definitions: {e}")

        # Build enriched exercise list
        from services.exercise_generation.language_processor import prepare_jumbled_content
        lang_id = cached_record.get('language_id')

        exercises = []
        for item in exercise_items:
            eid = item['exercise_id']

            # Virtual exercises (e.g. from user test sentences) have inline content
            if item.get('is_virtual'):
                try:
                    content = prepare_jumbled_content(item['virtual_content'], lang_id)
                except Exception as e:
                    logger.error(f"Failed to prepare virtual jumbled content: {e}")
                    continue
                exercises.append({
                    'exercise_id': eid,
                    'exercise_type': item.get('exercise_type', ''),
                    'source_type': 'user_test',
                    'content': content,
                    'complexity_tier': None,
                    'phase': item.get('phase', ''),
                    'slot_type': item.get('slot_type', ''),
                    'is_completed': eid in completed,
                    'sense_id': None,
                    'lemma': '',
                    'definition': '',
                    'pronunciation': '',
                })
                continue

            ex_data = exercise_map.get(eid, {})
            sense_id = item.get('sense_id')
            sense_data = sense_lookup.get(sense_id, {}) if sense_id else {}
            vocab = sense_data.get('dim_vocabulary') or {}

            content = ex_data.get('content', {})
            exercise_type = item.get('exercise_type', ex_data.get('exercise_type', ''))
            if exercise_type == 'jumbled_sentence' and 'chunks' not in content:
                try:
                    content = prepare_jumbled_content(content, lang_id)
                except Exception as e:
                    logger.error(f"Failed to prepare jumbled content for {eid}: {e}")

            exercises.append({
                'exercise_id': eid,
                'exercise_type': exercise_type,
                'source_type': ex_data.get('source_type', ''),
                'content': content,
                'complexity_tier': ex_data.get('complexity_tier'),
                'phase': item.get('phase', ''),
                'slot_type': item.get('slot_type', ''),
                'is_completed': eid in completed,
                'sense_id': sense_id,
                'lemma': vocab.get('lemma', ''),
                'definition': sense_data.get('definition', ''),
                'pronunciation': sense_data.get('pronunciation', ''),
            })

        return {
            'load_date': cached_record.get('load_date'),
            'exercises': exercises,
            'progress': {'completed': len(completed), 'total': len(exercise_items)},
            'session_size': cached_record.get('session_size', len(exercise_items)),
        }


# -- Singleton -----------------------------------------------------------

_instance: Optional[ExerciseSessionService] = None


def get_exercise_session_service() -> ExerciseSessionService:
    """Get the singleton ExerciseSessionService instance."""
    global _instance
    if _instance is None:
        _instance = ExerciseSessionService()
    return _instance
