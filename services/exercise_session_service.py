"""
Exercise Session Service — daily exercise scheduling

Builds personalised exercise sessions by combining:
- FSRS due flashcards (spaced repetition reviews)
- BKT uncertainty-zone words (active learning)
- New/encountered words (introduction)

Follows the TestService singleton pattern.
"""

import logging
import random
from datetime import date, datetime, timezone
from typing import Dict, List, Optional, Tuple
from uuid import uuid4

from config import Config
from services.supabase_factory import get_supabase_admin
from services.vocabulary.knowledge_service import VocabularyKnowledgeService
from services.vocabulary.fsrs import CardState, schedule_review, AGAIN, GOOD, EASY
from services.exercise_generation.config import PHASE_MAP

logger = logging.getLogger(__name__)

# Phase thresholds: p_known → phase letter
_PHASE_THRESHOLDS = [
    (0.30, 'A'),
    (0.55, 'B'),
    (0.80, 'C'),
]

# CEFR → phase mapping for grammar/collocation exercises
_CEFR_TO_PHASE = {
    'A1': 'A', 'A2': 'A',
    'B1': 'B', 'B2': 'C',
    'C1': 'D', 'C2': 'D',
}


def _determine_phase(p_known: float) -> str:
    """Map a p_known probability to a cognitive phase (A-D)."""
    for threshold, phase in _PHASE_THRESHOLDS:
        if p_known < threshold:
            return phase
    return 'D'


def _get_eligible_types_weighted(phase: str) -> Tuple[List[str], List[float]]:
    """Return (exercise_types, weights) using weighted cumulative phases.

    Primary phase gets 70% weight, one phase below gets 30%.
    Phase A words get 100% phase A.
    """
    phase_order = ['A', 'B', 'C', 'D']
    idx = phase_order.index(phase)
    primary_types = PHASE_MAP[phase]

    if idx == 0:
        weights = [1.0 / len(primary_types)] * len(primary_types)
        return primary_types, weights

    secondary_types = PHASE_MAP[phase_order[idx - 1]]
    all_types = primary_types + secondary_types
    weights = (
        [0.70 / len(primary_types)] * len(primary_types)
        + [0.30 / len(secondary_types)] * len(secondary_types)
    )
    return all_types, weights


def _pick_weighted_type(types: List[str], weights: List[float]) -> str:
    """Pick a single exercise type using weighted random selection."""
    return random.choices(types, weights=weights, k=1)[0]


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

        result = {'is_correct': is_correct, 'exercise_type': exercise_type}

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
                # BKT update
                knowledge_svc = VocabularyKnowledgeService(self.db)
                bkt_result = knowledge_svc.update_from_word_test(
                    user_id=user_id,
                    sense_id=sense_id,
                    is_correct=is_correct,
                    language_id=language_id,
                )
                if bkt_result:
                    result['bkt_update'] = bkt_result

                # FSRS update if flashcard exists
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
        """Core scheduling algorithm: select exercises for today's session."""

        dist = Config.EXERCISE_SLOT_DISTRIBUTION
        due_slots = round(session_size * dist['due_review'])
        learning_slots = round(session_size * dist['active_learning'])
        new_slots = session_size - due_slots - learning_slots

        cooldown_days = Config.EXERCISE_COOLDOWN_DAYS
        recent_ids = self._get_recent_exercise_ids(user_id, cooldown_days)

        # --- Bucket 1: FSRS due reviews ---
        due_senses = self._get_due_senses(user_id, language_id, due_slots * 3)
        due_picks = self._select_exercises_for_senses(
            due_senses, language_id, recent_ids, due_slots, 'due_review'
        )

        picked_sense_ids = {item['sense_id'] for item in due_picks if item.get('sense_id')}

        # --- Bucket 2: Active learning (uncertainty zone) ---
        learning_senses = self._get_active_learning_senses(
            user_id, language_id, learning_slots * 3, exclude_senses=picked_sense_ids
        )
        learning_picks = self._select_exercises_for_senses(
            learning_senses, language_id, recent_ids, learning_slots, 'active_learning'
        )

        picked_sense_ids.update(
            item['sense_id'] for item in learning_picks if item.get('sense_id')
        )

        # --- Bucket 3: New/encountered words ---
        new_senses = self._get_new_senses(
            user_id, language_id, new_slots * 3, exclude_senses=picked_sense_ids
        )
        new_picks = self._select_exercises_for_senses(
            new_senses, language_id, recent_ids, new_slots, 'new_word'
        )

        # --- Overflow redistribution ---
        all_picks = due_picks + learning_picks + new_picks
        remaining = session_size - len(all_picks)

        if remaining > 0:
            # Try to fill from whichever bucket has leftover candidates
            picked_exercise_ids = {item['exercise_id'] for item in all_picks}
            picked_sense_ids.update(
                item['sense_id'] for item in new_picks if item.get('sense_id')
            )

            # Pull more from each bucket in priority order
            for bucket_senses, slot_type in [
                (due_senses, 'due_review'),
                (learning_senses, 'active_learning'),
                (new_senses, 'new_word'),
            ]:
                if remaining <= 0:
                    break
                overflow = self._select_exercises_for_senses(
                    [s for s in bucket_senses
                     if s['sense_id'] not in picked_sense_ids],
                    language_id,
                    recent_ids | picked_exercise_ids,
                    remaining,
                    slot_type,
                )
                all_picks.extend(overflow)
                picked_exercise_ids.update(item['exercise_id'] for item in overflow)
                picked_sense_ids.update(
                    item['sense_id'] for item in overflow if item.get('sense_id')
                )
                remaining = session_size - len(all_picks)

        # --- Grammar/collocation supplementary fill ---
        remaining = session_size - len(all_picks)
        if remaining > 0:
            picked_exercise_ids = {item['exercise_id'] for item in all_picks}
            supplementary = self._get_supplementary_exercises(
                user_id, language_id, remaining,
                recent_ids | picked_exercise_ids
            )
            all_picks.extend(supplementary)

        # --- Bucket 5: User test sentence jumbled exercises ---
        remaining = session_size - len(all_picks)
        user_test_slots = min(remaining, 3)
        if user_test_slots > 0:
            test_sentences = self._get_user_test_sentences(
                user_id, language_id, user_test_slots
            )
            for sent in test_sentences:
                all_picks.append({
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

        # Shuffle so session isn't grouped by bucket
        random.shuffle(all_picks)
        return all_picks

    def _get_due_senses(
        self, user_id: str, language_id: int, limit: int
    ) -> List[Dict]:
        """Fetch senses with FSRS due flashcards."""
        today = date.today().isoformat()
        try:
            resp = (
                self.db.table('user_flashcards')
                .select('sense_id, due_date, state')
                .eq('user_id', user_id)
                .eq('language_id', language_id)
                .lte('due_date', today)
                .in_('state', ['review', 'relearning'])
                .order('due_date')
                .limit(limit)
                .execute()
            )
            flashcard_senses = [row['sense_id'] for row in (resp.data or [])]
        except Exception as e:
            logger.error(f"Error fetching due senses: {e}")
            return []

        if not flashcard_senses:
            return []

        # Fetch p_known for these senses
        try:
            knowledge = (
                self.db.table('user_vocabulary_knowledge')
                .select('sense_id, p_known')
                .eq('user_id', user_id)
                .in_('sense_id', flashcard_senses)
                .execute()
            )
            p_known_map = {
                row['sense_id']: float(row['p_known'])
                for row in (knowledge.data or [])
            }
        except Exception as e:
            logger.error(f"Error fetching p_known for due senses: {e}")
            p_known_map = {}

        return [
            {'sense_id': sid, 'p_known': p_known_map.get(sid, 0.5)}
            for sid in flashcard_senses
        ]

    def _get_active_learning_senses(
        self, user_id: str, language_id: int, limit: int,
        exclude_senses: set = None,
    ) -> List[Dict]:
        """Fetch senses in the BKT uncertainty zone (0.25-0.75)."""
        try:
            query = (
                self.db.table('user_vocabulary_knowledge')
                .select('sense_id, p_known')
                .eq('user_id', user_id)
                .eq('language_id', language_id)
                .gte('p_known', 0.25)
                .lte('p_known', 0.75)
                .not_.in_('status', ['user_marked_unknown', 'unknown'])
                .order('p_known')  # will sort in Python for uncertainty
                .limit(limit * 2)  # fetch extra to filter
            )
            resp = query.execute()
            results = resp.data or []
        except Exception as e:
            logger.error(f"Error fetching active learning senses: {e}")
            return []

        exclude = exclude_senses or set()
        candidates = [
            {'sense_id': row['sense_id'], 'p_known': float(row['p_known'])}
            for row in results
            if row['sense_id'] not in exclude
        ]

        # Sort by uncertainty (highest entropy first): p*(1-p)
        candidates.sort(key=lambda x: x['p_known'] * (1 - x['p_known']), reverse=True)
        return candidates[:limit]

    def _get_new_senses(
        self, user_id: str, language_id: int, limit: int,
        exclude_senses: set = None,
    ) -> List[Dict]:
        """Fetch new/encountered senses with low p_known."""
        try:
            resp = (
                self.db.table('user_vocabulary_knowledge')
                .select('sense_id, p_known, last_evidence_at')
                .eq('user_id', user_id)
                .eq('language_id', language_id)
                .lt('p_known', 0.30)
                .in_('status', ['encountered', 'unknown'])
                .order('last_evidence_at', desc=True)
                .limit(limit * 2)
                .execute()
            )
            results = resp.data or []
        except Exception as e:
            logger.error(f"Error fetching new senses: {e}")
            return []

        exclude = exclude_senses or set()
        candidates = [
            {'sense_id': row['sense_id'], 'p_known': float(row['p_known'])}
            for row in results
            if row['sense_id'] not in exclude
        ]

        # Also try flashcards with state='new' as fallback
        if len(candidates) < limit:
            try:
                fc_resp = (
                    self.db.table('user_flashcards')
                    .select('sense_id')
                    .eq('user_id', user_id)
                    .eq('language_id', language_id)
                    .eq('state', 'new')
                    .limit(limit)
                    .execute()
                )
                existing_ids = {c['sense_id'] for c in candidates}
                for row in (fc_resp.data or []):
                    sid = row['sense_id']
                    if sid not in exclude and sid not in existing_ids:
                        candidates.append({'sense_id': sid, 'p_known': 0.10})
            except Exception as e:
                logger.error(f"Error fetching new flashcard senses: {e}")

        return candidates[:limit]

    def _select_exercises_for_senses(
        self,
        senses: List[Dict],
        language_id: int,
        exclude_ids: set,
        max_count: int,
        slot_type: str,
    ) -> List[Dict]:
        """For each sense, select one exercise using phase-gated weighted types."""
        picks = []

        for sense in senses:
            if len(picks) >= max_count:
                break

            sense_id = sense['sense_id']
            p_known = sense['p_known']
            phase = _determine_phase(p_known)
            eligible_types, weights = _get_eligible_types_weighted(phase)

            # Try to find an exercise matching a weighted-random type
            # Shuffle type order by weight to try preferred types first
            type_indices = list(range(len(eligible_types)))
            random.shuffle(type_indices)
            # Sort by weight descending so we try high-weight types first
            type_indices.sort(key=lambda i: weights[i], reverse=True)

            found = False
            for idx in type_indices:
                etype = eligible_types[idx]
                try:
                    resp = (
                        self.db.table('exercises')
                        .select('id, exercise_type, content')
                        .eq('word_sense_id', sense_id)
                        .eq('language_id', language_id)
                        .eq('exercise_type', etype)
                        .eq('is_active', True)
                        .limit(5)
                        .execute()
                    )
                    candidates = [
                        row for row in (resp.data or [])
                        if row['id'] not in exclude_ids
                    ]
                    if candidates:
                        chosen = random.choice(candidates)
                        picks.append({
                            'exercise_id': chosen['id'],
                            'sense_id': sense_id,
                            'exercise_type': chosen['exercise_type'],
                            'slot_type': slot_type,
                            'phase': phase,
                        })
                        exclude_ids.add(chosen['id'])
                        found = True
                        break
                except Exception as e:
                    logger.error(f"Error selecting exercise for sense {sense_id}: {e}")

            if not found:
                # Try any exercise for this sense regardless of type
                try:
                    resp = (
                        self.db.table('exercises')
                        .select('id, exercise_type, content')
                        .eq('word_sense_id', sense_id)
                        .eq('language_id', language_id)
                        .eq('is_active', True)
                        .limit(5)
                        .execute()
                    )
                    candidates = [
                        row for row in (resp.data or [])
                        if row['id'] not in exclude_ids
                    ]
                    if candidates:
                        chosen = random.choice(candidates)
                        picks.append({
                            'exercise_id': chosen['id'],
                            'sense_id': sense_id,
                            'exercise_type': chosen['exercise_type'],
                            'slot_type': slot_type,
                            'phase': phase,
                        })
                        exclude_ids.add(chosen['id'])
                except Exception as e:
                    logger.error(f"Error in fallback exercise selection: {e}")

        return picks

    def _get_supplementary_exercises(
        self, user_id: str, language_id: int, count: int,
        exclude_ids: set,
    ) -> List[Dict]:
        """Fill remaining slots with grammar/collocation exercises by CEFR level."""
        # Estimate user's CEFR level from average p_known
        try:
            avg_resp = (
                self.db.table('user_vocabulary_knowledge')
                .select('p_known')
                .eq('user_id', user_id)
                .eq('language_id', language_id)
                .limit(100)
                .execute()
            )
            p_values = [float(r['p_known']) for r in (avg_resp.data or [])]
            avg_p = sum(p_values) / len(p_values) if p_values else 0.3
        except Exception:
            avg_p = 0.3

        # Map avg p_known to CEFR
        if avg_p < 0.20:
            cefr_levels = ['A1', 'A2']
        elif avg_p < 0.40:
            cefr_levels = ['A2', 'B1']
        elif avg_p < 0.60:
            cefr_levels = ['B1', 'B2']
        elif avg_p < 0.80:
            cefr_levels = ['B2', 'C1']
        else:
            cefr_levels = ['C1', 'C2']

        picks = []
        try:
            resp = (
                self.db.table('exercises')
                .select('id, exercise_type, cefr_level, grammar_pattern_id, '
                        'corpus_collocation_id')
                .eq('language_id', language_id)
                .eq('is_active', True)
                .in_('cefr_level', cefr_levels)
                .is_('word_sense_id', 'null')  # non-vocabulary exercises
                .limit(count * 3)
                .execute()
            )

            candidates = [
                row for row in (resp.data or [])
                if row['id'] not in exclude_ids
            ]
            random.shuffle(candidates)

            for row in candidates[:count]:
                cefr = row.get('cefr_level', 'B1')
                phase = _CEFR_TO_PHASE.get(cefr, 'B')
                picks.append({
                    'exercise_id': row['id'],
                    'sense_id': None,
                    'exercise_type': row['exercise_type'],
                    'slot_type': 'supplementary',
                    'phase': phase,
                })

        except Exception as e:
            logger.error(f"Error fetching supplementary exercises: {e}")

        return picks

    def _get_user_test_sentences(
        self, user_id: str, language_id: int, count: int
    ) -> List[Dict]:
        """Pull sentences from tests the user scored >50% on."""
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

    def _get_recent_exercise_ids(self, user_id: str, days: int) -> set:
        """Get exercise IDs the user has seen within the cooldown window."""
        try:
            cutoff = datetime.now(timezone.utc)
            # Approximate by fetching recent attempts
            resp = (
                self.db.table('exercise_attempts')
                .select('exercise_id')
                .eq('user_id', user_id)
                .order('created_at', desc=True)
                .limit(500)
                .execute()
            )
            return {row['exercise_id'] for row in (resp.data or [])}
        except Exception as e:
            logger.error(f"Error fetching recent exercise IDs: {e}")
            return set()

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
                .select('id, exercise_type, source_type, content, cefr_level, '
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
                    'cefr_level': None,
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
                'cefr_level': ex_data.get('cefr_level'),
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
