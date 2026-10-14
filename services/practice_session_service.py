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
  2. Implements ladder top-up (R4.9) from the learner's own evidence before
     calling the RPC. (Pack-based intake was archived 2026-09-21 with the
     language-packs feature — archive/modules/language-packs-2026-09-21.zip.)
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
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from config import Config
from services.supabase_factory import get_supabase_admin
from services import study_plan_service as _plan
from services.day_boundary import local_date, local_day_start_utc, plan_today_iso
from services.vocabulary.knowledge_service import VocabularyKnowledgeService
from services.vocabulary.fsrs import CardState, schedule_review, AGAIN, GOOD, EASY

logger = logging.getLogger(__name__)

# ----------------------------------------------------------------------
# Ladder intake tunables (plan §4c)
# ----------------------------------------------------------------------

# Safety ceiling on how many senses one intake pass may add. Intake is driven
# by the per-local-day new-word quota (admit_daily_new_words), not by a pool
# floor; this cap only bounds a pathological quota (npd up to 50) on one call.
LADDER_TOPUP_MAX_PER_CALL = 12

# Ladder states that count towards the eligible pool. state='new' is in here,
# which is why a cold-start seed used to disarm all later intake.
LADDER_ELIGIBLE_STATES = ('new', 'active', 'gated', 'pre_mastery', 'relearning')

# T4.1 — the supply gate. A sense must already carry this many active
# exercises in the target language before it may be admitted to the ladder.
# Below three there is not enough material to cover even one ring of the
# family rotation, so the learner meets the same item every session; the
# measured floor is that 21 of 24 live subscriptions had *zero*.
LADDER_MIN_EXERCISES_PER_SENSE = 3

# T4.2 — evidence thresholds. One wrong answer can be a careless click or a
# bad distractor, so a single miss never subscribes: a sense needs either
# repeated evidence or a p_known the model is already confident about.
LADDER_EVIDENCE_MIN_COUNT = 2
LADDER_EVIDENCE_P_KNOWN_MAX = 0.40

# How many ranked nominations to run through the supply gate per slot wanted.
# Exercise coverage sits near 3% of tested senses, so most nominations fail
# the gate and a 1:1 slice would almost always come back empty.
NOMINATION_OVERFETCH = 20

# Row ceilings on the intake reads. All are per-user and comfortably above
# any real learner's history; they exist so a pathological account cannot pull
# an unbounded result set onto the request path.
SUPPLY_GATE_CHUNK = 100
SUPPLY_GATE_ROW_LIMIT = 10000
EVIDENCE_ROW_LIMIT = 2000
WRONG_ANSWER_ROW_LIMIT = 5000
LADDER_SUBSCRIBED_ROW_LIMIT = 5000

# Queue A1 (session-budget-settings, TASK-871): unknowns from tests and word
# quizzes the learner took recently. Tunable (assumed, no data). Config wins when
# it defines the name, so the planner and intake share one value.
RECENT_TEST_WINDOW_DAYS = getattr(Config, 'RECENT_TEST_WINDOW_DAYS', 28)
RECENT_TEST_ROW_LIMIT = 1000
RECENT_TEST_CHUNK = 100

# Queue A2 (TASK-873): calibration wrongs.
CALIBRATION_EVIDENCE_MAX_AGE_DAYS = getattr(
    Config, 'CALIBRATION_EVIDENCE_MAX_AGE_DAYS', 90)   # tunable (assumed, no data)
CALIBRATION_ROW_LIMIT = 500


# T4.3 — how many starved nominations one session request may queue for
# exercise generation. At ~3% exercise coverage of tested senses an unbounded
# pass would enqueue a learner's whole vocabulary history on the first request.
DEMAND_GENERATION_MAX_PER_CALL = 5

# T4.6 — session-size floor. A daily session that returns a handful of items
# reads as "there is nothing here" even when review work is available, so a
# short acquisition session is topped up from the maintenance (FSRS/BKT) pool.
PRACTICE_SESSION_MIN_ITEMS = 20

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
        tail: bool = False,
    ) -> Dict[str, Any]:
        """Return today's Practice session in the requested mode.

        Args:
            user_id: authenticated user UUID
            language_id: dim_languages.id
            mode: 'acquisition' | 'maintenance' | 'auto'
            target_minutes: time budget; 1..180
            user_theta: optional pre-computed IRT theta; RPC computes if None
            debug: when True, includes score_breakdown on each item
            tail: True for an optional-tail round (session-budget-settings).
                The payload echoes ``tail: true`` so the client can echo it on
                the attempt POST. Maintenance items are served most-overdue
                first in every case.

        Returns the RPC jsonb verbatim, augmented with `cold_subscribed`
        (list of senses auto-subscribed before the call) if any.

        Ladder intake (session-budget-settings):
          When acquisition is possible, admit enough words to meet today's
          governed started-per-day quota (admit_daily_new_words), capped at
          LADDER_TOPUP_MAX_PER_CALL per call. Nominations come from recent test
          unknowns, then calibration wrongs, and every nomination must clear
          the supply gate. Never-attempted admitted words are served first.

        Session floor (T4.6):
          A session shorter than PRACTICE_SESSION_MIN_ITEMS is topped up from
          the maintenance pool, so a thin acquisition pool reads as "a short
          day" rather than "there is nothing here".
        """
        if mode not in ('acquisition', 'maintenance', 'auto'):
            return {'error': 'invalid_mode', 'code': 'E_MODE'}
        if not (1 <= target_minutes <= 180):
            return {'error': 'target_minutes_out_of_range', 'code': 'E_RANGE'}

        cold_subscribed: List[int] = []

        # Ladder intake pre-step (acquisition-capable modes only).
        if mode in ('acquisition', 'auto'):
            try:
                cold_subscribed = self._maybe_top_up_ladder(
                    user_id, language_id
                )
            except Exception as e:
                logger.warning(
                    'ladder top-up failed for user=%s lang=%s: %s',
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

        # T4.6 — session-size floor. The RPC budgets by *time*, not by count,
        # so a learner whose acquisition pool is thin gets a three-item session
        # that reads as an empty engine. Top up from the maintenance pool
        # (FSRS-due / BKT-decayed senses), which the RPC already knows how to
        # select. Best-effort: a short session is still a session.
        if mode in ('acquisition', 'auto'):
            try:
                self._apply_session_floor(
                    payload, user_id, language_id, target_minutes,
                )
            except Exception as e:
                logger.warning(
                    'session floor top-up failed (non-fatal) for user=%s '
                    'lang=%s: %s', user_id, language_id, e,
                )

        # Session-budget-settings: serve never-attempted admitted words first
        # (oldest admission first), and maintenance reviews most-overdue first.
        try:
            self._order_items(payload, user_id, language_id, mode)
        except Exception as e:
            logger.warning(
                'session item ordering failed (non-fatal) for user=%s '
                'lang=%s: %s', user_id, language_id, e,
            )
        if tail:
            payload['tail'] = True

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

        # Most stored jumbled_sentence rows hold only `original_sentence`; the
        # renderer needs `chunks` + `correct_ordering`. Runs after the script
        # swap so a Traditional learner is chunked on the text they will see.
        self._prepare_jumbled_items(payload.get('items'), language_id)

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

    def _apply_session_floor(
        self,
        payload: Dict[str, Any],
        user_id: str,
        language_id: int,
        target_minutes: int,
    ) -> None:
        """Top a short session up to PRACTICE_SESSION_MIN_ITEMS, in place.

        The RPC budgets by time, so a thin acquisition pool yields a session of
        two or three items — indistinguishable, to a learner, from a broken
        engine. Backfill comes from the maintenance pool, which is review work
        the learner has already met, so the floor never invents new material:
        if maintenance is dry too the session stays short and honest.

        Adds ``floor_backfilled`` (count) when it does anything, so a session
        that only looks full because of the floor is still legible in
        telemetry. Does nothing when the RPC already returned enough, and does
        nothing when the RPC reported no content at all — an empty session with
        a ``no_content_reason`` is a real state the FE has a nudge for.
        """
        items = payload.get('items') or []
        if len(items) >= PRACTICE_SESSION_MIN_ITEMS:
            return

        deficit = PRACTICE_SESSION_MIN_ITEMS - len(items)
        seen = {
            item.get('exercise_id') for item in items
            if item.get('exercise_id') is not None
        }

        try:
            resp = self.db.rpc('get_practice_session', {
                'p_user_id':        user_id,
                'p_language_id':    language_id,
                'p_mode':           'maintenance',
                # Ask for the full budget rather than the deficit: the RPC
                # spends minutes, and a two-minute request comes back with two
                # items regardless of how much review is actually due.
                'p_target_minutes': target_minutes,
                'p_user_theta':     None,
            }).execute()
        except Exception as e:
            logger.warning('session floor maintenance call failed: %s', e)
            return

        extra = resp.data if isinstance(resp.data, dict) else {}
        if 'error' in extra:
            return

        backfill = []
        for item in (extra.get('items') or []):
            eid = item.get('exercise_id')
            if eid is None or eid in seen:
                continue
            seen.add(eid)
            item['mode'] = 'maintenance'
            backfill.append(item)
            if len(backfill) >= deficit:
                break

        if not backfill:
            return

        payload['items'] = items + backfill
        payload['floor_backfilled'] = len(backfill)
        # The floor found material, so an acquisition-side "nothing here"
        # verdict is no longer the truth about this session.
        if payload.get('no_content_reason'):
            payload['no_content_reason'] = None
        logger.info(
            'session floor: backfilled %d maintenance item(s) for user=%s '
            'lang=%s (%d -> %d items, floor %d)',
            len(backfill), user_id, language_id,
            len(items), len(payload['items']), PRACTICE_SESSION_MIN_ITEMS,
        )

    # ------------------------------------------------------------------
    # Item ordering (session-budget-settings, TASK-872)
    # ------------------------------------------------------------------

    def _order_items(
        self, payload: Dict[str, Any], user_id: str, language_id: int, mode: str,
    ) -> None:
        """Re-order the RPC's items in place (the RPC itself is not modified).

        * Acquisition items: words that have never been attempted come first,
          oldest admission first (``ladder_new_word_state.unstarted_sense_ids``
          order), before any word whose ladder is already in progress. Items of
          one word stay contiguous and keep their order.
        * Maintenance items: most overdue first (earliest
          ``user_flashcards.due_date`` / ``user_word_ladder.review_due_at``).
        """
        items = payload.get('items') or []
        if len(items) < 2:
            return
        if mode in ('acquisition', 'auto') and any(
            i.get('mode', 'acquisition') == 'acquisition' for i in items
        ):
            self._unstarted_first(items, user_id, language_id)
        if mode in ('maintenance', 'auto'):
            self._most_overdue_first(items, user_id)

    def _unstarted_first(
        self, items: List[Dict[str, Any]], user_id: str, language_id: int,
    ) -> None:
        state = self.new_word_state(user_id, language_id)
        if not state or not state['unstarted_sense_ids']:
            return
        rank = {sid: i for i, sid in enumerate(state['unstarted_sense_ids'])}
        # contiguous acquisition groups by sense, order of first appearance
        groups: List[List[Dict[str, Any]]] = []
        index: Dict[Any, int] = {}
        slots: List[Any] = []        # positions of acquisition items, in order
        for pos, item in enumerate(items):
            if item.get('mode', 'acquisition') != 'acquisition':
                continue
            slots.append(pos)
            key = item.get('sense_id')
            if key in index:
                groups[index[key]].append(item)
            else:
                index[key] = len(groups)
                groups.append([item])
        big = len(rank) + 1
        groups.sort(key=lambda g: rank.get(g[0].get('sense_id'), big))
        flat = [it for g in groups for it in g]
        for pos, it in zip(slots, flat):
            items[pos] = it

    def _most_overdue_first(
        self, items: List[Dict[str, Any]], user_id: str,
    ) -> None:
        positions = [
            p for p, i in enumerate(items)
            if i.get('mode') == 'maintenance' and i.get('sense_id') is not None
        ]
        if len(positions) < 2:
            return
        sense_ids = sorted({items[p]['sense_id'] for p in positions})
        due: Dict[Any, str] = {}

        def _norm(value) -> Optional[str]:
            if not value:
                return None
            text = str(value)
            return text[:10] + 'T00:00:00' if len(text) <= 10 else text[:19]

        for table, column in (('user_flashcards', 'due_date'),
                              ('user_word_ladder', 'review_due_at')):
            resp = (self.db.table(table).select(f'sense_id, {column}')
                    .eq('user_id', user_id).in_('sense_id', sense_ids)
                    .execute())
            for row in (resp.data or []):
                when = _norm(row.get(column))
                if when and (row['sense_id'] not in due or when < due[row['sense_id']]):
                    due[row['sense_id']] = when
        far = '9999-12-31T00:00:00'
        picked = sorted(
            (items[p] for p in positions),
            key=lambda it: due.get(it['sense_id'], far),
        )
        for p, it in zip(positions, picked):
            items[p] = it

    @staticmethod
    def _prepare_jumbled_items(items, language_id: int) -> None:
        """Fill in jumbled_sentence chunks/ordering, in place, per item.

        An item that cannot be prepared (or prepares to fewer than three
        chunks) is logged and REMOVED from ``items``: leaving it in made the
        renderer throw on the learner's screen. The list is mutated in place
        so the caller's payload sees the removal.
        """
        from services.exercise_generation.language_processor import (
            jumbled_is_servable, needs_jumbled_prep, prepare_jumbled_content,
        )
        if not items:
            return
        keep = []
        for item in items:
            if item.get('exercise_type') != 'jumbled_sentence':
                keep.append(item)
                continue
            try:
                if needs_jumbled_prep(item.get('content')):
                    item['content'] = prepare_jumbled_content(item['content'], language_id)
            except Exception as e:
                logger.error(
                    'Failed to prepare jumbled content for exercise %s: %s',
                    item.get('exercise_id'), e,
                )
                continue
            if jumbled_is_servable(item.get('content')):
                keep.append(item)
            else:
                logger.error(
                    'Dropping unservable jumbled_sentence exercise %s', item.get('exercise_id'),
                )
        items[:] = keep

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
        is_tail: bool = False,
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
          is_tail      : the attempt belongs to an optional-tail round
              (the session was requested with tail=1). Forwarded as
              ``p_is_tail`` so tail minutes and tail new words are tracked.
        """
        # 1. Look up exercise metadata
        exercise = (
            self.db.table('exercises')
            .select(
                'id, exercise_type, word_sense_id, '
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
                    # Session-budget-settings (TASK-872): the sense is passed
                    # only for acquisition so the RPC can count a new word the
                    # day it is first attempted; maintenance passes None.
                    'p_sense_id':      sense_id if session_mode == 'acquisition'
                                       else None,
                    'p_is_tail':       bool(is_tail),
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

    # ------------------------------------------------------------------
    # Ladder intake — two queues behind one supply gate (plan §4c)
    # ------------------------------------------------------------------

    def _maybe_top_up_ladder(
        self, user_id: str, language_id: int
    ) -> List[int]:
        """Admit today's new words; returns the newly-admitted sense ids.

        Delegates to :meth:`admit_daily_new_words`, which holds the body
        (per-local-day started quota, review governor, nomination queues, supply
        gate). Kept as the name ``get_session`` has always called.
        """
        return self.admit_daily_new_words(user_id, language_id)['admitted']

    # -- quota state (session-budget-settings, TASK-871) ----------------

    def new_word_state(
        self, user_id: str, language_id: int
    ) -> Optional[Dict[str, Any]]:
        """Today's new-word quota state for a learner, or None.

        Reads the plan once (``new_words_per_day``, ``weekday_shape``,
        ``timezone``, ``excluded_modules``), applies the review-load governor
        and counts the ladder through ``ladder_new_word_state``:

            quota       Q  = new_words_for_day(npd, weight of today's weekday)
            effective   E  = effective_new_words(Q, governor level)
            unstarted   U  = admitted words never attempted
            started_today ST = words whose first-ever attempt is on or after
                              local midnight (admitted today or earlier)
            unstarted_sense_ids  oldest admission first

        None means "no plan row or a read failed": callers admit nothing.
        Never raises.
        """
        try:
            resp = (
                self.db.table('user_study_plans')
                .select('new_words_per_day, weekday_shape, timezone, excluded_modules')
                .eq('user_id', user_id)
                .eq('language_id', language_id)
                .limit(1)
                .execute()
            )
        except Exception as e:
            logger.warning(
                'new-word state: plan read failed for user=%s lang=%s: %s',
                user_id, language_id, e,
            )
            return None
        if not getattr(resp, 'data', None):
            return None
        plan = resp.data[0]

        tz = plan.get('timezone')
        npd = int(plan.get('new_words_per_day') or 0)
        shape = plan.get('weekday_shape') or [1.0] * 7
        excluded = plan.get('excluded_modules') or []
        today = local_date(tz)
        try:
            weight = float(shape[today.weekday()])
        except (IndexError, TypeError, ValueError):
            weight = 1.0
        quota = _plan.new_words_for_day(npd, weight)

        if 'practice' in excluded:
            gov: Dict[str, Any] = {'level': 'normal'}
        else:
            gov = _plan.get_review_governor(
                self.db, user_id, language_id, today
            ) or {'level': 'normal'}
        level = gov.get('level') or 'normal'
        effective = _plan.effective_new_words(quota, level)

        try:
            st = self.db.rpc('ladder_new_word_state', {
                'p_user_id':     user_id,
                'p_language_id': language_id,
                'p_day_start':   local_day_start_utc(tz).isoformat(),
            }).execute().data
        except Exception as e:
            logger.warning(
                'new-word state: ladder_new_word_state failed for user=%s '
                'lang=%s: %s', user_id, language_id, e,
            )
            return None
        if isinstance(st, list):
            st = st[0] if st else None
        if not isinstance(st, dict):
            return None

        return {
            'timezone':      tz,
            'excluded':      list(excluded),
            'quota':         quota,
            'effective':     effective,
            'level':         level,
            'governor':      gov,
            'unstarted':     int(st.get('unstarted') or 0),
            'started_today': int(st.get('started_today') or 0),
            'unstarted_sense_ids': list(st.get('unstarted_sense_ids') or []),
        }

    def admit_daily_new_words(
        self, user_id: str, language_id: int
    ) -> Dict[str, Any]:
        """Top today's ladder intake up to the governed started-per-day quota.

        Returns ``{'admitted': [sense_id, ...], 'needs_rebuild': bool}``.

        Quota (Anki-like, ADR-033 revision (c)): ``new_words_per_day`` counts
        words *started* per local day, not words admitted. Admitted-but-unstarted
        words carry over and are counted, so intake only tops up:

            want_raw = E - (U + ST)
            want     = min(max(want_raw, 0), LADDER_TOPUP_MAX_PER_CALL)

        with ``E`` the effective quota after the review governor. A repeat call
        the same day admits nothing because ``U + ST`` already includes earlier
        admissions. The old pool-floor trigger is gone: a large existing pool no
        longer suppresses admission.

        Nominations: Queue A1 (recent test + word-quiz unknowns), then A2
        (calibration wrongs), then Queue B (lookahead; empty until built), all
        behind one supply gate. The unmet part of the quota is recorded as the
        day's shortfall; starved nominations are queued for generation.

        ``needs_rebuild`` is True once, on the first supply check of the day,
        when Tier C planned more in-budget new words than can be served.

        Never raises: a failure admits nothing.
        """
        empty: Dict[str, Any] = {'admitted': [], 'needs_rebuild': False}
        try:
            return self._admit_daily_new_words(user_id, language_id, empty)
        except Exception as e:
            logger.warning(
                'daily new-word intake failed for user=%s lang=%s: %s',
                user_id, language_id, e,
            )
            return empty

    def _admit_daily_new_words(
        self, user_id: str, language_id: int, empty: Dict[str, Any],
    ) -> Dict[str, Any]:
        state = self.new_word_state(user_id, language_id)
        if state is None:
            return empty
        new_today = state['effective']
        if new_today <= 0:
            return empty

        unstarted, started_today = state['unstarted'], state['started_today']
        want_raw = new_today - (unstarted + started_today)
        want = min(max(want_raw, 0), LADDER_TOPUP_MAX_PER_CALL)
        if want <= 0:
            return empty

        # Side effect only: asks for exercises for subscribed-but-unservable
        # rows. No longer gates intake and target_active_pool is not read.
        try:
            self._eligible_ladder_count(user_id, language_id)
        except Exception as e:
            logger.warning('eligible ladder count failed (non-fatal): %s', e)

        # Read the supply flag BEFORE set_new_words_shortfall flips it.
        today_iso = plan_today_iso(self.db, user_id, language_id)
        prior_checked, planned_in_budget, checked_e = self._today_supply_flags(
            user_id, language_id, today_iso
        )
        # A supply check is only valid for the E it was made under. A mid-day
        # quota change (settings edit, governor level change) makes it stale:
        # treat the day as unchecked so the rebuild flag can fire once more.
        # (checked_e is None only for rows written before the key existed.)
        if prior_checked and checked_e is not None and checked_e != new_today:
            prior_checked = False

        subscribed = self._subscribed_sense_ids(user_id)
        fresh = self._nominate_new_words(user_id, language_id, want, subscribed)

        inserted = bool(fresh) and self._insert_ladder_rows(user_id, fresh)
        if fresh and not inserted:
            return empty
        admitted = list(fresh) if inserted else []
        if admitted:
            logger.info(
                'ladder intake admitted %d sense(s) for user=%s lang=%s '
                '(E=%d, unstarted=%d, started_today=%d)',
                len(admitted), user_id, language_id, new_today,
                unstarted, started_today,
            )

        shortfall = max(0, want_raw - len(admitted))
        try:
            self.db.rpc('set_new_words_shortfall', {
                'p_user_id':     user_id,
                'p_language_id': language_id,
                'p_date':        today_iso,
                'p_shortfall':   shortfall,
                'p_checked_e':   new_today,
            }).execute()
        except Exception as e:
            logger.warning(
                'set_new_words_shortfall failed (non-fatal) for user=%s '
                'lang=%s: %s', user_id, language_id, e,
            )

        servable = min(new_today, unstarted + started_today + len(admitted))
        needs_rebuild = bool(
            not prior_checked
            and planned_in_budget is not None
            and planned_in_budget > servable
        )
        return {'admitted': admitted, 'needs_rebuild': needs_rebuild}

    def _today_supply_flags(
        self, user_id: str, language_id: int, load_date: str
    ):
        """(new_words_supply_checked, new_words_in_budget, checked_e) from today's targets.

        ``checked_e`` is the effective quota the supply check was made under
        (``new_words_supply_checked_e``), None when absent.

        ``planned`` is None when there is no row or no such key (nothing to
        compare against, so no rebuild).
        """
        try:
            resp = (
                self.db.table('daily_test_loads')
                .select('daily_session_targets')
                .eq('user_id', user_id)
                .eq('language_id', language_id)
                .eq('load_date', load_date)
                .limit(1)
                .execute()
            )
        except Exception as e:
            logger.warning('supply-flag read failed (non-fatal): %s', e)
            return True, None, None     # unknown: do not trigger a rebuild
        if not resp.data:
            return True, None, None
        targets = resp.data[0].get('daily_session_targets') or {}
        planned = targets.get('new_words_in_budget')
        checked_e = targets.get('new_words_supply_checked_e')
        return (
            bool(targets.get('new_words_supply_checked')),
            int(planned) if planned is not None else None,
            int(checked_e) if checked_e is not None else None,
        )

    # -- nomination queues ----------------------------------------------

    def _nominate_new_words(
        self, user_id: str, language_id: int, want: int, exclude: set,
    ) -> List[int]:
        """Nominate and gate senses for today's intake, best queue first.

        Order (decided 2026-10-13): Queue A1 (unknowns from recent tests and
        word quizzes) -> Queue A2 (calibration wrongs; one wrong answer is
        enough) -> Queue B (lookahead cohorts, empty until built). A later queue
        is consulted only if the earlier ones did not fill ``want``. Every queue
        goes through ``_gate_and_admit``. No frequency-based cold-start queue.
        """
        admitted: List[int] = []
        taken = set(exclude)

        recent = self._recent_test_sense_ids(user_id, language_id)
        a1 = [
            c for c in self._evidence_candidates(
                user_id, language_id, recency_first=True)
            if c['sense_id'] in recent and c['sense_id'] not in taken
        ]
        admitted += self._gate_and_admit(
            [c['sense_id'] for c in a1], want, language_id)
        taken.update(admitted)

        if len(admitted) < want:
            a2 = self._calibration_wrong_candidates(user_id, language_id, taken)
            got = self._gate_and_admit(
                a2, want - len(admitted), language_id)
            admitted += got
            taken.update(got)

        if len(admitted) < want:
            b = self._nominate_from_lookahead(
                user_id, language_id, want - len(admitted), taken)
            admitted += self._gate_and_admit(
                b, want - len(admitted), language_id)
        return admitted[:want]

    def _nominate_from_lookahead(
        self, user_id: str, language_id: int, want: int, exclude: set,
    ) -> List[int]:
        """Queue B: lookahead pre-teaching cohorts.

        Stub returning ``[]`` until [[features/lookahead-preteaching]] ships.
        """
        return []

    def _gate_and_admit(
        self, candidates: List[int], want: int, language_id: int,
    ) -> List[int]:
        """Run ranked candidate sense ids through the supply gate.

        Overfetches (``want * NOMINATION_OVERFETCH``) because exercise coverage
        sits near 3% of tested senses, keeps those with at least
        LADDER_MIN_EXERCISES_PER_SENSE active exercises, queues the starved for
        generation (capped by DEMAND_GENERATION_MAX_PER_CALL) and returns
        ``admitted[:want]``. Fails closed when supply cannot be verified.
        """
        if not candidates or want <= 0:
            return []
        head = candidates[:max(want * NOMINATION_OVERFETCH, want)]
        supplied = self._senses_with_supply(head, language_id)
        admitted = [sid for sid in head if sid in supplied]
        starved = [sid for sid in head if sid not in supplied]
        if starved:
            logger.info(
                'ladder intake: %d of %d nominated sense(s) for lang=%s have '
                'fewer than %d active exercises and were held back',
                len(starved), len(head), language_id,
                LADDER_MIN_EXERCISES_PER_SENSE,
            )
            self._request_generation(starved, language_id)
        return admitted[:want]

    def _recent_test_sense_ids(self, user_id: str, language_id: int) -> set:
        """Senses carried by tests the learner took in the recent window.

        ``test_attempts`` within RECENT_TEST_WINDOW_DAYS give test ids; in
        chunks of RECENT_TEST_CHUNK, ``tests.vocab_sense_ids`` and
        ``questions.sense_ids`` are unioned. A failed read returns an empty set
        (intake adds nothing rather than admitting unrelated words).
        """
        since = (
            datetime.now(timezone.utc) - timedelta(days=RECENT_TEST_WINDOW_DAYS)
        ).isoformat()
        try:
            resp = (
                self.db.table('test_attempts')
                .select('test_id')
                .eq('user_id', user_id)
                .eq('language_id', language_id)
                .gte('created_at', since)
                .limit(RECENT_TEST_ROW_LIMIT)
                .execute()
            )
            test_ids = sorted({
                r['test_id'] for r in (resp.data or [])
                if r.get('test_id') is not None
            })
            senses: set = set()
            for start in range(0, len(test_ids), RECENT_TEST_CHUNK):
                chunk = test_ids[start:start + RECENT_TEST_CHUNK]
                t = (self.db.table('tests').select('id, vocab_sense_ids')
                     .in_('id', chunk).execute())
                for row in (t.data or []):
                    senses.update(row.get('vocab_sense_ids') or [])
                q = (self.db.table('questions').select('test_id, sense_ids')
                     .in_('test_id', chunk).execute())
                for row in (q.data or []):
                    senses.update(row.get('sense_ids') or [])
            return senses
        except Exception as e:
            logger.warning(
                'recent-test sense read failed for user=%s lang=%s: %s',
                user_id, language_id, e,
            )
            return set()

    # -- calibration evidence (TASK-873) ---------------------------------

    def _calibration_ledger(
        self, user_id: str, language_id: int
    ) -> Dict[int, Dict[str, Any]]:
        """Per anchor sense: what applied definition-mode calibration showed.

        Reads ``calibration_responses`` joined (inner) to ``calibration_sessions``
        with mode 'definition', this word language and ``bkt_applied_at`` set,
        keeping only ``answered_at IS NOT NULL AND is_correct IS NOT NULL`` (an
        explicit skip is stored as a wrong answer; an unanswered item is
        ignored). Returns ``{sense_id: {cal_n, cal_wrong, last_answer_wrong,
        last_at}}``: ``cal_n`` distinct sessions answered, ``cal_wrong`` the
        sessions whose answers for the sense were all incorrect. A failed read
        returns ``{}``.
        """
        try:
            resp = (
                self.db.table('calibration_responses')
                .select(
                    'anchor_sense_id, is_correct, answered_at, session_id, '
                    'calibration_sessions!inner(mode, word_language_id, '
                    'bkt_applied_at)'
                )
                .eq('user_id', user_id)
                .eq('calibration_sessions.mode', 'definition')
                .eq('calibration_sessions.word_language_id', language_id)
                .limit(CALIBRATION_ROW_LIMIT)
                .execute()
            )
        except Exception as e:
            logger.warning(
                'calibration ledger read failed for user=%s lang=%s: %s',
                user_id, language_id, e,
            )
            return {}

        # sense -> session -> [is_correct, ...] and the latest answer
        per: Dict[int, Dict[Any, List[bool]]] = {}
        latest: Dict[int, tuple] = {}
        for row in (resp.data or []):
            sid = row.get('anchor_sense_id')
            sess = row.get('calibration_sessions') or {}
            if (
                sid is None
                or row.get('answered_at') is None
                or row.get('is_correct') is None
                or sess.get('bkt_applied_at') is None
                or (sess.get('mode') or 'definition') != 'definition'
            ):
                continue
            per.setdefault(sid, {}).setdefault(
                row.get('session_id'), []).append(bool(row['is_correct']))
            at = str(row['answered_at'])
            if sid not in latest or at > latest[sid][0]:
                latest[sid] = (at, bool(row['is_correct']))

        ledger: Dict[int, Dict[str, Any]] = {}
        for sid, sessions in per.items():
            ledger[sid] = {
                'cal_n':     len(sessions),
                'cal_wrong': sum(1 for ans in sessions.values() if not any(ans)),
                'last_answer_wrong': not latest[sid][1],
                'last_at':   latest[sid][0],
            }
        return ledger

    def _calibration_wrong_candidates(
        self, user_id: str, language_id: int, exclude: set,
    ) -> List[int]:
        """Queue A2: senses whose latest calibration answer was wrong.

        Rule (i): a single wrong (or explicit "I don't know") calibration answer
        is sufficient; neither LADDER_EVIDENCE_MIN_COUNT nor
        LADDER_EVIDENCE_P_KNOWN_MAX applies. Within CALIBRATION_EVIDENCE_MAX_AGE_DAYS,
        not in ``exclude``, and not currently 'known' / 'probably_known'. Ordered
        by lemma frequency (Zipf desc) then most recent answer. Ranked below A1
        by the caller; the supply gate still applies.
        """
        ledger = self._calibration_ledger(user_id, language_id)
        cutoff = (
            datetime.now(timezone.utc)
            - timedelta(days=CALIBRATION_EVIDENCE_MAX_AGE_DAYS)
        ).isoformat()
        wrong = [
            sid for sid, e in ledger.items()
            if e['last_answer_wrong'] and e['last_at'] >= cutoff
            and sid not in exclude
        ]
        if not wrong:
            return []

        vetoed: set = set()
        try:
            for start in range(0, len(wrong), SUPPLY_GATE_CHUNK):
                chunk = wrong[start:start + SUPPLY_GATE_CHUNK]
                resp = (
                    self.db.table('user_vocabulary_knowledge')
                    .select('sense_id, status')
                    .eq('user_id', user_id)
                    .in_('sense_id', chunk)
                    .execute()
                )
                vetoed.update(
                    r['sense_id'] for r in (resp.data or [])
                    if r.get('status') in ('known', 'probably_known')
                )
        except Exception as e:
            logger.warning('calibration status veto read failed: %s', e)
            return []          # fail closed: cannot confirm the words are not known

        remaining = [sid for sid in wrong if sid not in vetoed]
        frequency = self._sense_frequency(remaining)
        remaining.sort(key=lambda s: ledger[s]['last_at'], reverse=True)
        remaining.sort(key=lambda s: frequency.get(s, 0.0), reverse=True)
        return remaining

    # -- pool state ----------------------------------------------------

    def _eligible_ladder_count(self, user_id: str, language_id: int) -> int:
        """Eligible ladder rows this language can actually *serve*.

        Not a row count. A subscribed sense with no exercises behind it cannot
        produce a practice item, but it still occupies a pool slot, so counting
        it keeps the floor satisfied while the learner is served nothing. That
        is not hypothetical: the one live ladder holds 24 rows of which 3 are
        servable, and against a floor of 15 a raw row count returns "already
        full" forever. The supply gate alone would have stopped *new* dead rows
        without ever unblocking the learner who already has 21.

        A row whose exercises are later deactivated stops counting and the
        floor tops up around it. The dead row is inert rather than harmful, and
        growth is bounded by LADDER_TOPUP_MAX_PER_CALL and the floor itself.

        ``user_word_ladder`` has no language_id column of its own (a learner
        studying two languages would otherwise get intake suppressed for a
        brand-new language by an eligible word left over in another) — go
        through the embedded dim_word_senses -> dim_vocabulary join instead,
        same pattern as vocabulary_ladder.speed_round.mastered_sense_ids.
        """
        existing = (
            self.db.table('user_word_ladder')
            .select(
                'sense_id, '
                'dim_word_senses!inner(dim_vocabulary!inner(language_id))'
            )
            .eq('user_id', user_id)
            .in_('word_state', LADDER_ELIGIBLE_STATES)
            .eq('dim_word_senses.dim_vocabulary.language_id', language_id)
            .limit(LADDER_SUBSCRIBED_ROW_LIMIT)
            .execute()
        )
        sense_ids = [
            row['sense_id'] for row in (existing.data or [])
            if row.get('sense_id') is not None
        ]
        if not sense_ids:
            return 0
        servable = self._senses_with_supply(sense_ids, language_id)
        if len(servable) < len(sense_ids):
            logger.info(
                'ladder pool for user=%s lang=%s: %d eligible row(s), %d '
                'servable — %d subscribed sense(s) have fewer than %d active '
                'exercises and do not hold a pool slot',
                user_id, language_id, len(sense_ids), len(servable),
                len(sense_ids) - len(servable), LADDER_MIN_EXERCISES_PER_SENSE,
            )
            # These are the strongest demand-driven generation candidates
            # there are: the learner is already subscribed and getting nothing.
            self._request_generation(
                [s for s in sense_ids if s not in servable], language_id,
            )
        return len(servable)

    def _daily_minutes(self, user_id: str, language_id: int) -> int:
        """The learner's daily-minutes target, or the configured default."""
        plan_resp = (
            self.db.table('user_study_plans')
            .select('daily_minutes')
            .eq('user_id', user_id)
            .eq('language_id', language_id)
            .limit(1)
            .execute()
        )
        if plan_resp.data:
            return plan_resp.data[0].get(
                'daily_minutes', Config.STUDY_PLAN_DEFAULT_DAILY_MINUTES
            )
        return Config.STUDY_PLAN_DEFAULT_DAILY_MINUTES

    def _subscribed_sense_ids(self, user_id: str) -> set:
        """Every sense already on this user's ladder, in any state."""
        try:
            resp = (
                self.db.table('user_word_ladder')
                .select('sense_id')
                .eq('user_id', user_id)
                .limit(LADDER_SUBSCRIBED_ROW_LIMIT)
                .execute()
            )
        except Exception as e:
            # Fail closed: without knowing what is already subscribed we would
            # re-insert duplicates on every call.
            logger.error('could not read existing ladder rows: %s', e)
            raise
        return {
            row['sense_id'] for row in (resp.data or [])
            if row.get('sense_id') is not None
        }

    # -- the supply gate (T4.1) ----------------------------------------

    def _senses_with_supply(
        self, sense_ids: List[int], language_id: int
    ) -> set:
        """The subset of ``sense_ids`` that has enough exercises to serve.

        A sense passes when it carries at least
        LADDER_MIN_EXERCISES_PER_SENSE active exercises *in this language*.
        The language check is free here (``exercises.language_id`` is on the
        rows being counted anyway) and it is what keeps a sense nominated from
        a cross-language wrong answer out of the pool.

        Counted client-side because PostgREST cannot express
        ``HAVING COUNT(*) >= n``; row volume is bounded by
        candidates x exercises-per-sense, and candidates is capped by callers.

        Fails **closed** — a sense whose supply could not be verified is not
        admitted. Admitting one is precisely the dead end this gate exists to
        prevent.
        """
        if not sense_ids:
            return set()
        covered: set = set()
        ids = list(sense_ids)
        for start in range(0, len(ids), SUPPLY_GATE_CHUNK):
            chunk = ids[start:start + SUPPLY_GATE_CHUNK]
            try:
                resp = (
                    self.db.table('exercises')
                    .select('word_sense_id')
                    .in_('word_sense_id', chunk)
                    .eq('language_id', language_id)
                    .eq('is_active', True)
                    .limit(SUPPLY_GATE_ROW_LIMIT)
                    .execute()
                )
            except Exception as e:
                logger.error(
                    'supply gate lookup failed; admitting no senses: %s', e
                )
                return set()
            counts: Dict[int, int] = {}
            for row in (resp.data or []):
                sid = row.get('word_sense_id')
                if sid is not None:
                    counts[sid] = counts.get(sid, 0) + 1
            covered.update(
                sid for sid, n in counts.items()
                if n >= LADDER_MIN_EXERCISES_PER_SENSE
            )
        return covered

    # -- Queue A: evidence (T4.2) --------------------------------------

    def _request_generation(self, sense_ids: List[int], language_id: int) -> int:
        """Queue starved nominations for exercise generation (T4.3).

        This is what inverts generation from speculative to demand-driven: the
        budget goes to words this learner has demonstrably failed, instead of
        to a 31st variant for a word that already has 33 exercises. Reuses the
        existing ``generation_queue`` and its nightly drain rather than adding
        a second generation path — ``enqueue`` already de-duplicates against
        pending/running rows, so a sense nominated on every session request is
        queued once.

        Bounded per call by DEMAND_GENERATION_MAX_PER_CALL: at current coverage
        (~3% of tested senses have exercises) an unbounded pass would enqueue
        the learner's whole vocabulary history on the first request.

        Best-effort. A queue that cannot be written must not stop a session
        being served — the learner still gets the senses that passed the gate.
        """
        if not sense_ids:
            return 0
        try:
            from services.vocabulary_ladder import queue_drain
        except Exception as e:
            logger.warning('demand-driven generation unavailable: %s', e)
            return 0

        queued = 0
        for sense_id in sense_ids[:DEMAND_GENERATION_MAX_PER_CALL]:
            try:
                if queue_drain.enqueue(
                    self.db, sense_id, language_id,
                    queue_drain.REASON_SUBSCRIBE_TOPUP,
                    detail={'source': 'evidence_queue'},
                ):
                    queued += 1
            except Exception as e:
                logger.warning(
                    'could not queue sense %s for generation: %s', sense_id, e
                )
        if queued:
            logger.info(
                'demand-driven generation: queued %d starved sense(s) for '
                'lang=%s', queued, language_id,
            )
        return queued

    def _evidence_candidates(
        self, user_id: str, language_id: int, recency_first: bool = False,
    ) -> List[Dict[str, Any]]:
        """Ranked test / word-quiz evidence nominations (Queue A1), best first.

        The calibration contribution is subtracted before the thresholds apply
        (``evidence_count - cal_n``, ``word_test_wrong - cal_wrong``): a
        calibration answer is not test or word-quiz evidence and is handled by
        Queue A2. A row left with no evidence is dropped from A1.

        ``recency_first`` ranks most-recent ``last_evidence_at`` first, then wrong
        count, then frequency; the default is wrong count, then recency, then
        frequency.
        """
        wrong_by_question = self._wrong_answer_sense_counts(user_id)
        ledger = self._calibration_ledger(user_id, language_id)

        rows: List[Dict[str, Any]] = []
        try:
            resp = (
                self.db.table('user_vocabulary_knowledge')
                .select(
                    'sense_id, p_known, status, evidence_count, '
                    'word_test_wrong, comprehension_wrong, last_evidence_at'
                )
                .eq('user_id', user_id)
                .eq('language_id', language_id)
                .or_(
                    'status.in.(unknown,learning),'
                    'word_test_wrong.gt.0,'
                    'comprehension_wrong.gt.0'
                )
                .limit(EVIDENCE_ROW_LIMIT)
                .execute()
            )
            rows = resp.data or []
        except Exception as e:
            logger.warning(
                'evidence queue read failed for user=%s lang=%s: %s',
                user_id, language_id, e,
            )

        candidates: Dict[int, Dict[str, Any]] = {}
        for row in rows:
            sid = row.get('sense_id')
            if sid is None:
                continue
            cal = ledger.get(sid) or {}
            evidence = (row.get('evidence_count') or 0) - cal.get('cal_n', 0)
            word_test_wrong = max(
                0, (row.get('word_test_wrong') or 0) - cal.get('cal_wrong', 0))
            if cal and evidence <= 0:
                continue          # calibration-only evidence: Queue A2's job
            p_known = row.get('p_known')
            # One wrong answer is a careless click or a bad distractor, not a
            # knowledge gap. Admit on repeated evidence, or on a p_known the
            # model is already confident about. `evidence_count` exists for
            # exactly this decision.
            confident_unknown = (
                p_known is not None
                and float(p_known) <= LADDER_EVIDENCE_P_KNOWN_MAX
            )
            if evidence < LADDER_EVIDENCE_MIN_COUNT and not confident_unknown:
                continue
            candidates[sid] = {
                'sense_id': sid,
                'wrongs': (
                    word_test_wrong
                    + (row.get('comprehension_wrong') or 0)
                    + wrong_by_question.get(sid, 0)
                ),
                'last_evidence_at': row.get('last_evidence_at') or '',
            }

        # A sense with no knowledge row at all still qualifies once the learner
        # has missed LADDER_EVIDENCE_MIN_COUNT distinct questions carrying it:
        # the wrong-answer signal is evidence in its own right, and the same
        # "never on a single miss" rule applies.
        for sid, n in wrong_by_question.items():
            if sid in candidates or n < LADDER_EVIDENCE_MIN_COUNT:
                continue
            candidates[sid] = {
                'sense_id': sid, 'wrongs': n, 'last_evidence_at': '',
            }

        if not candidates:
            return []

        frequency = self._sense_frequency(list(candidates))
        # Stable sort, least significant key first: frequency (Zipf, desc) ->
        # most recent evidence -> wrong count.
        ordered = sorted(
            candidates.values(),
            key=lambda c: frequency.get(c['sense_id'], 0.0), reverse=True,
        )
        if recency_first:
            ordered.sort(key=lambda c: c['wrongs'], reverse=True)
            ordered.sort(key=lambda c: c['last_evidence_at'], reverse=True)
        else:
            ordered.sort(key=lambda c: c['last_evidence_at'], reverse=True)
            ordered.sort(key=lambda c: c['wrongs'], reverse=True)
        return ordered

    def _wrong_answer_sense_counts(self, user_id: str) -> Dict[int, int]:
        """How many distinct missed questions carry each sense.

        ``questions.sense_ids`` is populated on the large majority of rows;
        questions without it simply contribute nothing. Not language-scoped
        here — the supply gate is, and it is the cheaper place to do it.
        """
        try:
            resp = (
                self.db.table('question_attempt_results')
                .select('question_id, questions!inner(sense_ids)')
                .eq('user_id', user_id)
                .eq('is_correct', False)
                .limit(WRONG_ANSWER_ROW_LIMIT)
                .execute()
            )
        except Exception as e:
            logger.warning(
                'wrong-answer sense read failed for user=%s: %s', user_id, e
            )
            return {}
        counts: Dict[int, int] = {}
        seen: set = set()
        for row in (resp.data or []):
            question = row.get('questions') or {}
            for sid in (question.get('sense_ids') or []):
                key = (row.get('question_id'), sid)
                if key in seen:
                    continue
                seen.add(key)
                counts[sid] = counts.get(sid, 0) + 1
        return counts

    def _sense_frequency(self, sense_ids: List[int]) -> Dict[int, float]:
        """sense_id -> Zipf frequency of its lemma (higher is more frequent)."""
        if not sense_ids:
            return {}
        out: Dict[int, float] = {}
        for start in range(0, len(sense_ids), SUPPLY_GATE_CHUNK):
            chunk = sense_ids[start:start + SUPPLY_GATE_CHUNK]
            try:
                resp = (
                    self.db.table('dim_word_senses')
                    .select('id, dim_vocabulary!inner(frequency_rank)')
                    .in_('id', chunk)
                    .execute()
                )
            except Exception as e:
                # Frequency is only a tie-break; losing it degrades ordering,
                # not correctness.
                logger.warning('sense frequency lookup failed: %s', e)
                return out
            for row in (resp.data or []):
                vocab = row.get('dim_vocabulary') or {}
                rank = vocab.get('frequency_rank')
                if rank is not None:
                    out[row['id']] = float(rank)
        return out

    # -- subscription --------------------------------------------------

    def _insert_ladder_rows(self, user_id: str, sense_ids: List[int]) -> bool:
        """Seed ladder rows for ``sense_ids``. True if the insert landed.

        ``user_word_ladder`` has no language_id column (see
        _eligible_ladder_count) — including one here makes the whole insert
        fail against PostgREST's schema cache.
        """
        now = datetime.now(timezone.utc).isoformat()
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
                'review_due_at':     now,
            }
            for sid in sense_ids
        ]
        try:
            self.db.table('user_word_ladder').insert(rows).execute()
        except Exception as e:
            logger.error('ladder subscribe insert failed: %s', e)
            return False
        return True

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
