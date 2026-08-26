"""
Practice Session Service — unified vocabulary practice surface.

Module-level factory:
  get_practice_session_service()  → returns a process-wide singleton.

Back-compat methods retained on PracticeSessionService:
  get_or_create_daily_session(...)   ← legacy daily-mixed shape
  mark_exercise_complete(...)        ← no-op under the merged engine


Replaces the split between the legacy daily-mixed-session and vocab-dojo
session RPCs with a single mode-dispatched RPC `get_practice_session`.
See [[features/practice-engine.tech]] and ADR-007.

Modes:
  - acquisition  : word-anchored loop (one word → K family-targeted items →
                   inline gate / stress markers)
  - maintenance  : batch-anchored over FSRS-due / BKT-decayed senses, falls
                   through to acquisition if pool empties before time-up
  - auto         : dispatcher (FSRS+decayed >= ladder-active → maintenance)

This service:
  1. Wraps the RPC for `/api/practice/session` handlers.
  2. Implements cold-ladder auto-subscription from selected packs (R4.9)
     before calling the RPC, since the RPC itself cannot know about packs.
  3. Records attempts via record_attempt_with_updates — same logic as
     legacy ExerciseSessionService but with an added session_mode parameter
     that propagates to record_session_progress for weekly counter updates.

Renamed from services/exercise_session_service.py (TASK-106). The legacy
class/factory aliases and the compatibility shim were removed in TASK-220
once the deprecation window elapsed.

Follows the singleton pattern used by TestService / VocabularyKnowledgeService.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional

from config import Config
from services.supabase_factory import get_supabase_admin
from services.vocabulary.knowledge_service import VocabularyKnowledgeService
from services.vocabulary.fsrs import CardState, schedule_review, AGAIN, GOOD, EASY

logger = logging.getLogger(__name__)

# TASK-701: practice time accrues at seconds granularity. An attempt whose
# measured elapsed exceeds this (a tab left open, a coffee break) is treated as
# absurd and falls back to the exercise's expected_seconds estimate.
PRACTICE_ATTEMPT_MAX_SECONDS = 300      # 5 minutes
# Final fallback when the item carries no expected_seconds estimate — matches
# the seed default in get_practice_session (COALESCE(..., 45)).
DEFAULT_EXPECTED_SECONDS = 45


class PracticeSessionService:
    """Unified Practice surface. Wraps get_practice_session + attempt recording."""

    def __init__(self, db=None):
        self.db = db or get_supabase_admin()

    # ------------------------------------------------------------------
    # Public API — session retrieval
    # ------------------------------------------------------------------

    def get_session(
        self,
        user_id: str,
        language_id: int,
        mode: str = 'auto',
        target_minutes: int = 15,
        user_theta: Optional[float] = None,
        debug: bool = False,
    ) -> Dict[str, Any]:
        """Return today's Practice session in the requested mode.

        Args:
            user_id: authenticated user UUID
            language_id: dim_languages.id
            mode: 'acquisition' | 'maintenance' | 'auto'
            target_minutes: time budget; 1..180
            user_theta: optional pre-computed IRT theta; RPC computes if None
            debug: when True, includes score_breakdown on each item

        Returns the RPC jsonb verbatim, augmented with `cold_subscribed`
        (list of senses auto-subscribed before the call) if any.

        Cold-ladder fallback (R4.9):
          When acquisition is requested and the user has no eligible ladder
          words, auto-subscribe up to target_new_rate senses from the user's
          selected packs (highest-frequency unsubscribed first). If no packs
          are selected, do nothing — the RPC will return
          no_content_reason='no_eligible_words' which the FE surfaces as a
          "select a pack" nudge.
        """
        if mode not in ('acquisition', 'maintenance', 'auto'):
            return {'error': 'invalid_mode', 'code': 'E_MODE'}
        if not (1 <= target_minutes <= 180):
            return {'error': 'target_minutes_out_of_range', 'code': 'E_RANGE'}

        cold_subscribed: List[int] = []

        # Cold-ladder pre-step (acquisition mode only).
        if mode in ('acquisition', 'auto'):
            try:
                cold_subscribed = self._maybe_auto_subscribe_from_packs(
                    user_id, language_id
                )
            except Exception as e:
                logger.warning(
                    'cold-ladder auto-subscribe failed for user=%s lang=%s: %s',
                    user_id, language_id, e,
                )

        try:
            resp = self.db.rpc('get_practice_session', {
                'p_user_id':        user_id,
                'p_language_id':    language_id,
                'p_mode':           mode,
                'p_target_minutes': target_minutes,
                'p_user_theta':     user_theta,
            }).execute()
            payload = resp.data
        except Exception as e:
            logger.error('get_practice_session RPC failed: %s', e)
            return {'error': 'rpc_failed', 'code': 'E_RPC', 'detail': str(e)}

        if not isinstance(payload, dict):
            logger.error('get_practice_session returned non-dict: %r', payload)
            return {'error': 'malformed_response', 'code': 'E_SHAPE'}

        if 'error' in payload:
            return payload

        # Strip score_breakdown when not in debug mode (it's verbose and
        # only useful for telemetry / parity tests).
        if not debug:
            for item in payload.get('items', []):
                item.pop('score_breakdown', None)

        if cold_subscribed:
            payload['cold_subscribed'] = cold_subscribed

        # TASK-526: serve the Traditional mirror to learners who asked for it.
        # Pure field selection over content.hant, which TASK-509 dual-stored at
        # generation time — no OpenCC on the request path. Best-effort: a
        # learner who prefers Traditional should get Simplified rather than an
        # error if anything here goes wrong.
        try:
            self._apply_script_variant(payload, user_id, language_id)
        except Exception as e:
            logger.warning(
                'script-variant selection failed (non-fatal) for user=%s lang=%s: %s',
                user_id, language_id, e,
            )

        # TASK-618: interleave due Dual-Translation error-remediation cards into
        # the session as a separate, non-sense-linked stream — capped so it never
        # crowds out normal practice, and best-effort so a remediation hiccup
        # never breaks the practice session. An empty normal session stays empty
        # (see cards.select_error_exercises_for_practice); GET /next remains the
        # surface for a due queue with no accompanying practice.
        try:
            from services.dual_translation import cards as dt_cards
            normal_items = payload.get('items', []) or []
            error_items = dt_cards.select_error_exercises_for_practice(
                self.db,
                user_id,
                language_id=language_id,
                normal_item_count=len(normal_items),
            )
            if error_items:
                payload['items'] = self._interleave_extras(normal_items, error_items)
                payload['error_cards_injected'] = len(error_items)
        except Exception as e:
            logger.warning(
                'DT error-card injection failed (non-fatal) for user=%s lang=%s: %s',
                user_id, language_id, e,
            )

        return payload

    def _apply_script_variant(
        self, payload: Dict[str, Any], user_id: str, language_id: int,
    ) -> None:
        """Swap ZH item content for its Traditional mirror, in place.

        No-op for every language but Chinese and for every learner who has not
        set the preference, and the preference is only read once the language
        could possibly need it — a Japanese session must not pay for a
        ``users`` round-trip to answer a question about Han script.
        """
        from services.vocabulary_ladder import script_serving

        if language_id not in script_serving.SCRIPT_VARIANT_LANGUAGES:
            return

        variant = script_serving.variant_from_preferences(
            self._exercise_preferences(user_id)
        )
        if not script_serving.applies_to(language_id, variant):
            return

        flagged = script_serving.apply_to_items(
            payload.get('items'), variant, language_id,
        )
        payload['script_variant'] = variant
        if flagged:
            # A mirror that has drifted behind its content serves Simplified
            # for the affected fields. Surfaced rather than swallowed so it
            # shows up as a backfill task, not as a confused learner.
            payload['script_fallback_items'] = flagged
            logger.info(
                'script variant %s: %d item(s) fell back to Simplified on at '
                'least one field (user=%s lang=%s)',
                variant, flagged, user_id, language_id,
            )

    def _exercise_preferences(self, user_id: str) -> dict:
        """The user's ``exercise_preferences`` JSONB, or ``{}``."""
        try:
            resp = (
                self.db.table('users')
                .select('exercise_preferences')
                .eq('id', user_id)
                .single()
                .execute()
            )
            return (resp.data or {}).get('exercise_preferences') or {}
        except Exception as e:
            logger.warning('could not read preferences for user=%s: %s', user_id, e)
            return {}

    @staticmethod
    def _interleave_extras(
        normal: List[Dict[str, Any]], extras: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Spread ``extras`` roughly evenly through ``normal`` (never clumped at
        the end), preserving each list's internal order. Each extra lands AFTER
        a normal item, so an assembled session still opens on a normal item.
        """
        if not extras:
            return list(normal)
        if not normal:
            return list(extras)
        result: List[Dict[str, Any]] = []
        interval = len(normal) / len(extras)
        ei = 0
        next_threshold = interval
        for i, item in enumerate(normal):
            result.append(item)
            while ei < len(extras) and (i + 1) >= next_threshold:
                result.append(extras[ei])
                ei += 1
                next_threshold += interval
        while ei < len(extras):
            result.append(extras[ei])
            ei += 1
        return result

    # ------------------------------------------------------------------
    # Public API — attempt recording (carried over from legacy service)
    # ------------------------------------------------------------------

    def record_attempt_with_updates(
        self,
        user_id: str,
        exercise_id: str,
        is_correct: bool,
        user_response: Optional[dict] = None,
        time_taken_ms: Optional[int] = None,
        session_mode: Optional[str] = None,
        language_id: Optional[int] = None,
        expected_seconds: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Record an attempt and propagate BKT / FSRS / Tier-B progress.

        Args mirror the legacy ExerciseSessionService.record_attempt_with_updates
        with THREE new optional fields:

          session_mode  : 'acquisition' | 'maintenance' | None
              If provided, record_session_progress is called with
              kind = 'practice_' + session_mode so weekly_plan_states counters
              stay live. None means "don't increment Study Plan counters"
              (e.g., admin tooling / virtual items).
          language_id   : optional override; otherwise looked up from
              exercises.language_id. Required if session_mode is set so the
              progress call routes to the right weekly_plan_states row.
          expected_seconds : the item's p50 time estimate (as served on the
              session item). Used as the credited fallback when time_taken_ms
              is missing/zero or absurdly large (TASK-701).
        """
        # 1. Look up exercise metadata
        exercise = (
            self.db.table('exercises')
            .select(
                'id, exercise_type, word_sense_id, grammar_pattern_id, '
                'corpus_collocation_id, attempt_count, correct_count, language_id'
            )
            .eq('id', exercise_id)
            .single()
            .execute()
            .data
        )
        if not exercise:
            return {'error': 'Exercise not found'}

        exercise_type = exercise.get('exercise_type')
        sense_id = exercise.get('word_sense_id')
        eff_language_id = language_id or exercise.get('language_id')

        # 2. First-attempt detection (gates BKT)
        prior_resp = (
            self.db.table('exercise_attempts')
            .select('id')
            .eq('user_id', user_id)
            .eq('exercise_id', exercise_id)
            .limit(1)
            .execute()
        )
        is_first_attempt = not bool(prior_resp.data)

        # 3. Insert attempt row
        attempt_row = {
            'user_id':       user_id,
            'exercise_id':   exercise_id,
            'user_response': user_response or {},
            'is_correct':    is_correct,
            'time_taken_ms': time_taken_ms,
            'exercise_type': exercise_type,
            'sense_id':      sense_id,
            'created_at':    datetime.now(timezone.utc).isoformat(),
        }
        inserted = (
            self.db.table('exercise_attempts')
            .insert(attempt_row)
            .execute()
        )
        attempt_id = (inserted.data or [{}])[0].get('id')

        # 4. Exercise-level stats
        updates = {'attempt_count': (exercise.get('attempt_count') or 0) + 1}
        if is_correct:
            updates['correct_count'] = (exercise.get('correct_count') or 0) + 1
        self.db.table('exercises').update(updates).eq('id', exercise_id).execute()

        result: Dict[str, Any] = {
            'attempt_id':      attempt_id,
            'is_correct':      is_correct,
            'exercise_type':   exercise_type,
            'is_first_attempt': is_first_attempt,
        }

        # 5. BKT + FSRS for sense-linked items
        if sense_id and eff_language_id:
            if is_first_attempt:
                try:
                    knowledge_svc = VocabularyKnowledgeService(self.db)
                    bkt_result = knowledge_svc.update_from_word_test(
                        user_id=user_id,
                        sense_id=sense_id,
                        is_correct=is_correct,
                        language_id=eff_language_id,
                        exercise_type=exercise_type,
                    )
                    if bkt_result:
                        result['bkt_update'] = bkt_result
                        self._capture_knowledge_outcome(attempt_id, bkt_result)
                except Exception as e:
                    logger.error('BKT update failed for sense %s: %s', sense_id, e)

            self._update_fsrs_for_exercise(
                user_id, sense_id, is_correct, time_taken_ms
            )

        # 6. Study Plan progress (if session_mode given and Plan enabled)
        if (
            Config.STUDY_PLAN_ENABLED
            and session_mode in ('acquisition', 'maintenance')
            and attempt_id
            and eff_language_id
        ):
            try:
                delta_seconds = self._effective_practice_seconds(
                    time_taken_ms, expected_seconds
                )
                self.db.rpc('record_session_progress', {
                    'p_user_id':       user_id,
                    'p_language_id':   eff_language_id,
                    'p_attempt_id':    attempt_id,
                    'p_kind':          'practice_acq' if session_mode == 'acquisition'
                                       else 'practice_maint',
                    'p_skill':         None,
                    'p_delta_count':   0,
                    'p_delta_seconds': delta_seconds,
                }).execute()
            except Exception as e:
                # Non-fatal: progress tracking is best-effort.
                logger.warning(
                    'record_session_progress failed (non-fatal) for attempt=%s: %s',
                    attempt_id, e,
                )

        return result

    # ------------------------------------------------------------------
    # Internal: knowledge-outcome capture (TASK-534)
    # ------------------------------------------------------------------

    def _capture_knowledge_outcome(self, attempt_id, bkt_result) -> None:
        """Persist the BKT before/after onto the attempt row.

        The attempt is inserted before BKT runs (BKT needs the row to exist to
        decide first-attempt-ness), so this is a follow-up UPDATE rather than
        part of the insert.

        Both values come from the BKT RPC, which already computed them — this
        does not re-derive anything. Without the capture the delta is gone: only
        the current p_known is stored anywhere, so after the next attempt on the
        same sense there is no way back to what this one changed.

        Best-effort. Analytics capture must never fail a learner's submission,
        and a missing pair reads correctly downstream as "not captured" rather
        than as a zero delta.
        """
        if not attempt_id or not isinstance(bkt_result, dict):
            return
        before = bkt_result.get('out_p_known_before')
        after = bkt_result.get('out_p_known_after')
        if before is None or after is None:
            return
        try:
            (self.db.table('exercise_attempts')
                 .update({'p_known_before': before, 'p_known_after': after})
                 .eq('id', attempt_id)
                 .execute())
        except Exception as e:
            logger.warning(
                'p_known capture failed for attempt %s (non-fatal): %s',
                attempt_id, e,
            )

    # ------------------------------------------------------------------
    # Internal: practice time accounting (TASK-701)
    # ------------------------------------------------------------------

    @staticmethod
    def _effective_practice_seconds(
        time_taken_ms: Optional[int], expected_seconds: Optional[int]
    ) -> int:
        """Effective per-attempt seconds to credit toward weekly practice time.

        - Missing / zero / negative ms  → credit the item's expected_seconds
          estimate (never nothing).
        - Absurd elapsed (> 5 min, e.g. a tab left open) → same estimate.
        - Otherwise → measured elapsed, rounded to whole seconds.

        The estimate itself is clamped to [1, PRACTICE_ATTEMPT_MAX_SECONDS] and
        defaults to DEFAULT_EXPECTED_SECONDS when the item carries none.
        """
        try:
            est = int(expected_seconds) if expected_seconds else DEFAULT_EXPECTED_SECONDS
        except (TypeError, ValueError):
            est = DEFAULT_EXPECTED_SECONDS
        if est <= 0:
            est = DEFAULT_EXPECTED_SECONDS
        est = min(est, PRACTICE_ATTEMPT_MAX_SECONDS)

        if not time_taken_ms or time_taken_ms <= 0:
            return est
        secs = time_taken_ms / 1000.0
        if secs > PRACTICE_ATTEMPT_MAX_SECONDS:
            return est
        return max(1, round(secs))

    # ------------------------------------------------------------------
    # Internal: cold-ladder auto-subscribe
    # ------------------------------------------------------------------

    def _maybe_auto_subscribe_from_packs(
        self, user_id: str, language_id: int
    ) -> List[int]:
        """Auto-subscribe top-N senses from selected packs when ladder empty.

        Returns the list of newly-subscribed sense_ids (may be empty).

        Behavior:
          - If user has any eligible ladder rows (states: new/active/gated/
            pre_mastery/relearning, review_due_at ≤ now), do nothing.
          - Else: find the user's selected packs; pull the top
            target_new_rate(daily_minutes) highest-frequency senses not
            already in user_word_ladder; INSERT them with state='new',
            current_ring=1, family_confidence all 0.10.
          - If no selected packs: return [] (RPC will return no_content).
        """
        # Eligible ladder count, scoped to this language. user_word_ladder has
        # no language_id column of its own (a learner studying two languages
        # would otherwise get cold-start suppressed for a brand-new language
        # by an eligible word left over in another) — go through the embedded
        # dim_word_senses -> dim_vocabulary join instead, same pattern as
        # vocabulary_ladder.speed_round.mastered_sense_ids.
        existing = (
            self.db.table('user_word_ladder')
            .select(
                'sense_id, '
                'dim_word_senses!inner(dim_vocabulary!inner(language_id))',
                count='exact',
            )
            .eq('user_id', user_id)
            .in_('word_state', ['new', 'active', 'gated', 'pre_mastery', 'relearning'])
            .eq('dim_word_senses.dim_vocabulary.language_id', language_id)
            .limit(1)
            .execute()
        )
        if existing.count and existing.count > 0:
            return []

        # daily_minutes drives target_new_rate per R3.1
        plan_resp = (
            self.db.table('user_study_plans')
            .select('daily_minutes')
            .eq('user_id', user_id)
            .eq('language_id', language_id)
            .limit(1)
            .execute()
        )
        if plan_resp.data:
            daily_minutes = plan_resp.data[0].get(
                'daily_minutes', Config.STUDY_PLAN_DEFAULT_DAILY_MINUTES
            )
        else:
            daily_minutes = Config.STUDY_PLAN_DEFAULT_DAILY_MINUTES
        target_new_rate = max(1, daily_minutes // 6)

        # Find selected packs for this user/language.
        try:
            packs_resp = self.db.rpc('get_packs_with_user_selection', {
                'p_language_id': language_id,
                'p_user_id':     user_id,
            }).execute()
        except Exception as e:
            logger.warning('get_packs_with_user_selection failed: %s', e)
            return []
        selected_pack_ids = [
            row['id'] for row in (packs_resp.data or [])
            if row.get('is_selected')
        ]
        if not selected_pack_ids:
            return []

        # Pull top-N highest-frequency unsubscribed senses from selected packs.
        # We rely on a generic JOIN through pack→senses; the exact bridge
        # table is documented in [[features/language-packs.tech]].
        # For V1 we use a simple SELECT and trust the index on word_sense_id.
        try:
            candidate_resp = (
                self.db.table('pack_key_words')   # name per language-packs.tech
                .select('sense_id')
                .in_('pack_id', selected_pack_ids)
                .limit(target_new_rate * 5)       # over-fetch; filter below
                .execute()
            )
            candidate_sense_ids = list({
                row['sense_id'] for row in (candidate_resp.data or [])
            })
        except Exception as e:
            logger.warning('pack senses query failed: %s', e)
            return []

        if not candidate_sense_ids:
            return []

        # Exclude already-subscribed senses
        already_resp = (
            self.db.table('user_word_ladder')
            .select('sense_id')
            .eq('user_id', user_id)
            .in_('sense_id', candidate_sense_ids)
            .execute()
        )
        already = {row['sense_id'] for row in (already_resp.data or [])}
        fresh = [s for s in candidate_sense_ids if s not in already][:target_new_rate]
        if not fresh:
            return []

        # Seed ladder rows. user_word_ladder has no language_id or created_at
        # column (see the eligibility query above) — including either here
        # makes the whole insert fail against PostgREST's schema cache, which
        # was silently swallowed by the except below and defeated cold-start
        # auto-subscription entirely.
        rows = [
            {
                'user_id':           user_id,
                'sense_id':          sid,
                'word_state':        'new',
                'current_ring':      1,
                'family_confidence': {
                    'form_recognition': 0.10,
                    'meaning_recall': 0.10,
                    'form_production': 0.10,
                    'collocation': 0.10,
                    'semantic_discrimination': 0.10,
                    'contextual_use': 0.10,
                },
                'gates_passed':      {'gate_a': False, 'gate_b': False},
                'review_due_at':     datetime.now(timezone.utc).isoformat(),
            }
            for sid in fresh
        ]
        try:
            self.db.table('user_word_ladder').insert(rows).execute()
        except Exception as e:
            logger.error('auto-subscribe insert failed: %s', e)
            return []
        logger.info(
            'cold-ladder auto-subscribed %d senses for user=%s lang=%s',
            len(fresh), user_id, language_id,
        )
        return fresh

    # ------------------------------------------------------------------
    # Speed round (TASK-533)
    # ------------------------------------------------------------------

    def record_speed_round_attempt(
        self,
        user_id: str,
        exercise_id: str,
        is_correct: bool,
        time_taken_ms: Optional[int] = None,
        timed_out: bool = False,
    ) -> Dict[str, Any]:
        """Record one timed-battery answer: FSRS only, never the ladder.

        A speed round draws exclusively on already-mastered words, so its
        signal is about *retrieval speed*, not about knowledge. Feeding a slow
        answer into family confidence would push a mastered word back down the
        ladder for being answered in seven seconds instead of four, which is
        not what the ladder measures. FSRS, by contrast, genuinely wants to
        know that a recall was fast and correct — so that half runs.

        Running out of the clock is recorded as incorrect: the learner did not
        retrieve the word in time, which is exactly the thing being trained.
        """
        if timed_out:
            is_correct = False

        try:
            resp = (
                self.db.table('exercises')
                .select('word_sense_id, language_id, exercise_type')
                .eq('id', exercise_id)
                .single()
                .execute()
            )
            row = resp.data or {}
        except Exception as e:
            logger.error('speed-round attempt: exercise lookup failed: %s', e)
            return {'error': 'exercise_not_found'}

        sense_id = row.get('word_sense_id')
        if not sense_id:
            return {'error': 'exercise_has_no_sense'}

        self._update_fsrs_for_exercise(
            user_id, sense_id, is_correct, time_taken_ms,
        )

        from services.vocabulary_ladder.speed_round import UPDATES_FAMILY_CONFIDENCE
        return {
            'is_correct': is_correct,
            'timed_out': timed_out,
            'exercise_type': row.get('exercise_type'),
            'sense_id': sense_id,
            'time_taken_ms': time_taken_ms,
            'fsrs_updated': True,
            'family_confidence_updated': UPDATES_FAMILY_CONFIDENCE,
        }

    # ------------------------------------------------------------------
    # Internal: FSRS update (verbatim from legacy service)
    # ------------------------------------------------------------------

    def _update_fsrs_for_exercise(
        self,
        user_id: str,
        sense_id: int,
        is_correct: bool,
        time_taken_ms: Optional[int] = None,
    ) -> None:
        try:
            card_resp = (
                self.db.table('user_flashcards')
                .select(
                    'id, stability, difficulty, due_date, last_review, '
                    'reps, lapses, state'
                )
                .eq('user_id', user_id)
                .eq('sense_id', sense_id)
                .execute()
            )
            if not card_resp.data:
                return

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

            if not is_correct:
                rating = AGAIN
            elif time_taken_ms is not None and time_taken_ms < 5000:
                rating = EASY
            else:
                rating = GOOD

            new_card = schedule_review(card, rating)
            self.db.table('user_flashcards').update({
                'stability':   new_card.stability,
                'difficulty':  new_card.difficulty,
                'due_date':    (
                    new_card.due_date.isoformat() if new_card.due_date else None
                ),
                'last_review': date.today().isoformat(),
                'reps':        new_card.reps,
                'lapses':      new_card.lapses,
                'state':       new_card.state,
                'updated_at':  'now()',
            }).eq('id', row['id']).execute()

            if new_card.lapses > card.lapses:
                try:
                    self.db.rpc('bkt_apply_lapse_penalty', {
                        'p_user_id':  user_id,
                        'p_sense_id': sense_id,
                    }).execute()
                except Exception as lapse_err:
                    logger.error(
                        'BKT lapse penalty failed for sense %s: %s',
                        sense_id, lapse_err,
                    )
        except Exception as e:
            logger.error('FSRS update failed for sense %s: %s', sense_id, e)


    # ------------------------------------------------------------------
    # Back-compat: legacy session API
    # ------------------------------------------------------------------
    # Routes/exercises.py originally called these on ExerciseSessionService.
    # They now translate into get_session() calls so the legacy /api/exercises
    # surface keeps working unchanged through the deprecation cycle.

    def get_or_create_daily_session(
        self, user_id: str, language_id: int
    ) -> Dict[str, Any]:
        """Legacy entry point — wraps get_session('auto', ...).

        Returns the legacy shape:
          { load_date, exercises: [...], progress: {completed, total}, session_size }

        target_minutes derived from the user's preferred session_size
        (DEFAULT_EXERCISE_SESSION_SIZE) × 0.6 (matches the deprecation
        wrapper convention in phase12_deprecation_wrappers.sql).
        """
        from datetime import date as _date
        try:
            prefs_resp = (
                self.db.table('users')
                .select('exercise_preferences')
                .eq('id', user_id)
                .single()
                .execute()
            )
            prefs = (prefs_resp.data or {}).get('exercise_preferences') or {}
        except Exception:
            prefs = {}
        size = int(prefs.get('session_size', Config.DEFAULT_EXERCISE_SESSION_SIZE))
        size = max(
            Config.MIN_EXERCISE_SESSION_SIZE,
            min(Config.MAX_EXERCISE_SESSION_SIZE, size),
        )
        target_minutes = max(1, round(size * 0.6))

        payload = self.get_session(
            user_id=user_id,
            language_id=int(language_id),
            mode='auto',
            target_minutes=target_minutes,
            debug=False,
        )

        if isinstance(payload, dict) and 'error' in payload:
            return {
                'load_date':    _date.today().isoformat(),
                'exercises':    [],
                'progress':     {'completed': 0, 'total': 0},
                'session_size': size,
                'error':        payload.get('error'),
            }

        items = (payload or {}).get('items', []) or []
        # Strip gate / stress markers and injected DT error cards (TASK-618)
        # from the legacy shape — old callers don't know what to do with them
        # and would render as empty/broken exercises.
        exercises = [
            it for it in items
            if not it.get('is_gate_marker')
            and not it.get('is_stress_test_marker')
            and not it.get('is_error_exercise')
        ]
        return {
            'load_date':    _date.today().isoformat(),
            'exercises':    exercises,
            'progress':     {'completed': 0, 'total': len(exercises)},
            'session_size': size,
        }

    def mark_exercise_complete(
        self, user_id: str, language_id: int, exercise_id: str
    ) -> Dict[str, Any]:
        """Legacy entry point — no-op under the merged service.

        The merged Practice Engine doesn't cache per-session-item completion
        state (every session is recomputed live from current ladder/FSRS
        state). Kept as a no-op so legacy callers don't 500.
        """
        return {
            'ok': True,
            'note': 'completion tracking is implicit in the merged Practice Engine',
        }


# ---------------------------------------------------------------------------
# Module-level singleton factory (matches the codebase pattern used by
# TestService, AuthService, etc.)
# ---------------------------------------------------------------------------
_singleton: Optional[PracticeSessionService] = None


def get_practice_session_service() -> PracticeSessionService:
    """Process-wide singleton."""
    global _singleton
    if _singleton is None:
        _singleton = PracticeSessionService()
    return _singleton


