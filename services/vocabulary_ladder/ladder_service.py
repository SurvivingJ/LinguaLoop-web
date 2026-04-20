# services/vocabulary_ladder/ladder_service.py
"""
Ladder Service — Vocabulary ladder progression engine.

Thin Python wrapper around Supabase RPCs that handle all progression
logic atomically in PostgreSQL:
  - ladder_record_attempt: family BKT, momentum bands, ring advancement
  - ladder_pass_gate: threshold gate pass/fail
  - ladder_graduate: stress test → mastery → FSRS initialization

Session building is handled by the get_ladder_session RPC (called from
the vocab_dojo route) or by ExerciseSessionService (daily mixed session).

This class provides:
  - record_attempt(): one-liner RPC call
  - init_ladder(): initialize user_word_ladder for a new word
  - assemble_gate(): build a gate battery from exercises
  - assemble_stress_test(): build a stress test battery
  - pass_gate() / graduate(): thin RPC wrappers
"""

import logging
from datetime import datetime, timezone

from services.supabase_factory import get_supabase_admin
from services.vocabulary_ladder.config import (
    LADDER_LEVELS, GATES, STRESS_TEST, RINGS,
    bkt_to_starting_level, compute_active_levels,
    get_family_for_level, get_levels_for_family,
)

logger = logging.getLogger(__name__)


class LadderService:
    """Manages vocabulary ladder progression for users."""

    def __init__(self, db=None):
        self.db = db or get_supabase_admin()

    # ------------------------------------------------------------------
    # Attempt recording (atomic RPC)
    # ------------------------------------------------------------------

    def record_attempt(
        self,
        user_id: str,
        sense_id: int,
        exercise_id: str,
        is_correct: bool,
        is_first_attempt: bool,
        time_taken_ms: int | None = None,
        language_id: int | None = None,
        exercise_type: str | None = None,
        ladder_level: int | None = None,
        exercise_context: str = 'standard',
    ) -> dict:
        """Record an exercise attempt via the ladder_record_attempt RPC.

        All progression logic (family BKT, momentum band scheduling,
        ring advancement, lapse handling) is handled atomically in SQL.

        Returns dict with keys: is_correct, family, family_confidence,
        p_known_overall, current_ring, word_state, review_due_at,
        requeue, gate_pending, stress_test_ready, bkt_p_known, is_lapse.
        """
        try:
            resp = self.db.rpc('ladder_record_attempt', {
                'p_user_id': user_id,
                'p_sense_id': sense_id,
                'p_exercise_id': exercise_id,
                'p_is_correct': is_correct,
                'p_is_first_attempt': is_first_attempt,
                'p_time_taken_ms': time_taken_ms,
                'p_language_id': language_id,
                'p_exercise_type': exercise_type,
                'p_ladder_level': ladder_level,
                'p_exercise_context': exercise_context,
            }).execute()
            return resp.data if resp.data else {}
        except Exception as e:
            logger.error("ladder_record_attempt failed: user=%s sense=%s: %s",
                         user_id, sense_id, e)
            return {
                'is_correct': is_correct,
                'requeue': not is_correct and is_first_attempt,
                'error': str(e),
            }

    # ------------------------------------------------------------------
    # Gate orchestration
    # ------------------------------------------------------------------

    def assemble_gate(
        self, user_id: str, sense_id: int, language_id: int, gate_name: str
    ) -> list[dict]:
        """Assemble a gate battery (3 exercises) for a threshold gate.

        Draws exercises from the ring being unlocked, preferring unseen
        variants. Returns a list of exercise dicts ready for the frontend.
        """
        gate_config = GATES.get(gate_name)
        if not gate_config:
            logger.error("Unknown gate: %s", gate_name)
            return []

        target_ring = gate_config['unlocks_ring']
        battery_size = gate_config['battery_size']

        # Get active levels for this word
        ladder_row = self._get_ladder_row(user_id, sense_id)
        active_levels = ladder_row['active_levels'] if ladder_row else list(range(1, 10))

        # Get ring levels that exist in active_levels
        ring_info = RINGS.get(target_ring, {})
        ring_levels = [lv for lv in ring_info.get('levels', []) if lv in active_levels]

        if not ring_levels:
            logger.warning("No ring levels available for gate %s, sense %s",
                           gate_name, sense_id)
            return []

        # If gate requires production, ensure at least one production-family level
        exercises = self._fetch_exercises_for_levels(
            sense_id, language_id, ring_levels, battery_size
        )

        return exercises

    def pass_gate(self, user_id: str, sense_id: int, gate_name: str) -> dict:
        """Mark a threshold gate as passed via the ladder_pass_gate RPC."""
        try:
            resp = self.db.rpc('ladder_pass_gate', {
                'p_user_id': user_id,
                'p_sense_id': sense_id,
                'p_gate_name': gate_name,
            }).execute()
            return resp.data if resp.data else {}
        except Exception as e:
            logger.error("ladder_pass_gate failed: %s", e)
            return {'error': str(e)}

    # ------------------------------------------------------------------
    # Stress test orchestration
    # ------------------------------------------------------------------

    def assemble_stress_test(
        self, user_id: str, sense_id: int, language_id: int
    ) -> list[dict]:
        """Assemble a stress test battery (8 exercises).

        Composition from STRESS_TEST config:
          2 form_production, 1 meaning_recall, 1 form_recognition,
          1 collocation, 1 semantic_discrimination, 2 contextual_use.

        Draws from both variants (A/B) to prevent memorization.
        Falls back to highest available exercises if contextual_use
        levels don't exist yet.
        """
        composition = STRESS_TEST['composition']
        ladder_row = self._get_ladder_row(user_id, sense_id)
        active_levels = ladder_row['active_levels'] if ladder_row else list(range(1, 10))

        all_needed_levels = []
        for family, count in composition.items():
            family_levels = get_levels_for_family(family, active_levels)
            if not family_levels:
                # Fall back: use highest available level for missing families
                if active_levels:
                    family_levels = [active_levels[-1]]
            # Take up to `count` levels, cycling if needed
            for i in range(count):
                if family_levels:
                    all_needed_levels.append(family_levels[i % len(family_levels)])

        return self._fetch_exercises_for_levels(
            sense_id, language_id, all_needed_levels, len(all_needed_levels)
        )

    def graduate(
        self, user_id: str, sense_id: int,
        stress_test_score: float, language_id: int
    ) -> dict:
        """Graduate a word to mastered via the ladder_graduate RPC.

        Initializes FSRS for long-term maintenance scheduling.
        """
        try:
            resp = self.db.rpc('ladder_graduate', {
                'p_user_id': user_id,
                'p_sense_id': sense_id,
                'p_stress_test_score': stress_test_score,
                'p_language_id': language_id,
            }).execute()
            return resp.data if resp.data else {}
        except Exception as e:
            logger.error("ladder_graduate failed: %s", e)
            return {'error': str(e)}

    # ------------------------------------------------------------------
    # Ladder initialization
    # ------------------------------------------------------------------

    def init_ladder(
        self, user_id: str, sense_id: int, language_id: int
    ) -> dict:
        """Initialize a user_word_ladder row based on BKT p_known."""
        p_known = 0.10
        try:
            bkt_resp = (
                self.db.table('user_vocabulary_knowledge')
                .select('p_known')
                .eq('user_id', user_id)
                .eq('sense_id', sense_id)
                .execute()
            )
            if bkt_resp.data:
                p_known = float(bkt_resp.data[0]['p_known'])
        except Exception:
            pass

        active_levels = self._get_active_levels_for_sense(sense_id)
        starting_level = bkt_to_starting_level(p_known, active_levels)

        row = {
            'user_id': user_id,
            'sense_id': sense_id,
            'current_level': starting_level,
            'active_levels': active_levels,
            'word_state': 'new',
            'current_ring': 1,
            'updated_at': datetime.now(timezone.utc).isoformat(),
        }

        try:
            self.db.table('user_word_ladder').upsert(
                row, on_conflict='user_id,sense_id'
            ).execute()
        except Exception as e:
            logger.error("Failed to init ladder for user=%s sense=%s: %s",
                         user_id, sense_id, e)

        return row

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _get_ladder_row(self, user_id: str, sense_id: int) -> dict | None:
        """Get the user_word_ladder row."""
        try:
            resp = (
                self.db.table('user_word_ladder')
                .select('*')
                .eq('user_id', user_id)
                .eq('sense_id', sense_id)
                .execute()
            )
            if resp.data:
                return resp.data[0]
        except Exception:
            pass
        return None

    def _get_active_levels_for_sense(self, sense_id: int) -> list[int]:
        """Compute active levels from the word's semantic class."""
        try:
            resp = (
                self.db.table('dim_word_senses')
                .select('dim_vocabulary(semantic_class)')
                .eq('id', sense_id)
                .single()
                .execute()
            )
            vocab = (resp.data or {}).get('dim_vocabulary') or {}
            sc = vocab.get('semantic_class', '')
            return compute_active_levels(sc)
        except Exception:
            return list(range(1, 10))

    def _fetch_exercises_for_levels(
        self, sense_id: int, language_id: int,
        levels: list[int], limit: int
    ) -> list[dict]:
        """Fetch exercises for specific levels, preferring variant diversity."""
        if not levels:
            return []
        try:
            resp = (
                self.db.table('exercises')
                .select('id, exercise_type, content, complexity_tier, '
                        'ladder_level, tags, word_sense_id')
                .eq('language_id', language_id)
                .eq('word_sense_id', sense_id)
                .eq('is_active', True)
                .in_('ladder_level', list(set(levels)))
                .execute()
            )

            # Group by level, pick exercises respecting variant diversity
            by_level: dict[int, list[dict]] = {}
            for row in (resp.data or []):
                lv = row['ladder_level']
                by_level.setdefault(lv, []).append(row)

            result = []
            variant_used = set()
            for lv in levels:
                candidates = by_level.get(lv, [])
                if not candidates:
                    continue
                # Prefer the variant not yet used
                picked = None
                for c in candidates:
                    v = (c.get('tags') or {}).get('variant', 'A')
                    if v not in variant_used:
                        picked = c
                        variant_used.add(v)
                        break
                if not picked:
                    picked = candidates[0]

                level_info = LADDER_LEVELS.get(lv, {})
                result.append({
                    'exercise_id': picked['id'],
                    'exercise_type': picked['exercise_type'],
                    'source_type': 'vocabulary',
                    'content': picked['content'],
                    'complexity_tier': picked.get('complexity_tier'),
                    'ladder_level': lv,
                    'ladder_name': level_info.get('name', ''),
                    'family': level_info.get('family', ''),
                    'sense_id': sense_id,
                })

                if len(result) >= limit:
                    break

            return result
        except Exception as e:
            logger.error("Exercise fetch failed for sense %s: %s", sense_id, e)
            return []
