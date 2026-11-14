"""Practice attempt recording: the attempt row, exercise counters, BKT, FSRS,
ladder progress, study time and plan progress."""

from __future__ import annotations

import logging
import os
import time
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional

from config import Config
from services.concurrency import run_parallel
from services.vocabulary.knowledge_service import VocabularyKnowledgeService
from services.vocabulary.fsrs import CardState, schedule_review, AGAIN, GOOD, EASY
from services.practice.constants import (
    ATTEMPT_RPC_ENV_FLAG,
    ATTEMPT_RPC_RECHECK_SECONDS,
    COUNTER_WRITE_ATTEMPTS,
    DEFAULT_EXPECTED_SECONDS,
    PRACTICE_ATTEMPT_MAX_SECONDS,
)

logger = logging.getLogger(__name__)

_attempt_rpc_missing_until = 0.0


def _attempt_rpc_enabled() -> bool:
    return os.environ.get(ATTEMPT_RPC_ENV_FLAG, '').strip().lower() in ('1', 'true', 'yes', 'on')


class AttemptRecordingMixin:
    """Attempt recording for PracticeSessionService (expects ``self.db``)."""

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
        exercise_context: str = 'standard',
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
        if _attempt_rpc_enabled():
            via_rpc = self._record_attempt_via_rpc(
                user_id, exercise_id, is_correct, user_response, time_taken_ms,
                session_mode, language_id, expected_seconds, is_tail, exercise_context,
            )
            if via_rpc is not None:
                return via_rpc

        db = self.db

        # 1. Exercise metadata and the first-attempt check (gates BKT), together.
        def _read_exercise():
            return (
                db.table('exercises')
                .select(
                    'id, exercise_type, word_sense_id, '
                    'corpus_collocation_id, attempt_count, correct_count, language_id'
                )
                .eq('id', exercise_id)
                .single()
                .execute()
                .data
            )

        def _read_prior():
            return (
                db.table('exercise_attempts')
                .select('id')
                .eq('user_id', user_id)
                .eq('exercise_id', exercise_id)
                .limit(1)
                .execute()
                .data
            )

        exercise, prior = run_parallel(_read_exercise, _read_prior)
        if not exercise:
            return {'error': 'Exercise not found'}

        exercise_type = exercise.get('exercise_type')
        sense_id = exercise.get('word_sense_id')
        eff_language_id = language_id or exercise.get('language_id')
        is_first_attempt = not bool(prior)
        tracked = bool(sense_id and eff_language_id)

        # 2. Insert the attempt row; the flashcard is read alongside it.
        def _insert_attempt():
            inserted = db.table('exercise_attempts').insert({
                'user_id':          user_id,
                'exercise_id':      exercise_id,
                'user_response':    user_response or {},
                'is_correct':       is_correct,
                'time_taken_ms':    time_taken_ms,
                'exercise_type':    exercise_type,
                'sense_id':         sense_id,
                'is_first_attempt': is_first_attempt,
                'created_at':       datetime.now(timezone.utc).isoformat(),
            }).execute()
            return (inserted.data or [{}])[0].get('id')

        if tracked:
            attempt_id, card_row = run_parallel(
                _insert_attempt, lambda: self._read_fsrs_card(user_id, sense_id))
        else:
            attempt_id, card_row = _insert_attempt(), None

        result: Dict[str, Any] = {
            'attempt_id':      attempt_id,
            'is_correct':      is_correct,
            'exercise_type':   exercise_type,
            'is_first_attempt': is_first_attempt,
        }
        seconds = self._effective_practice_seconds(time_taken_ms, expected_seconds)

        # 3. Everything that only needs the attempt row, concurrently. Each
        # step logs and swallows its own failure except the exercise counters,
        # whose failure fails the request as before.
        def _bkt():
            try:
                return VocabularyKnowledgeService(db).update_from_word_test(
                    user_id=user_id,
                    sense_id=sense_id,
                    is_correct=is_correct,
                    language_id=eff_language_id,
                    exercise_type=exercise_type,
                )
            except Exception as e:
                logger.error('BKT update failed for sense %s: %s', sense_id, e)
                return None

        def _prestudy():
            # Test prestudy next-day review: answering any exercise of a due
            # follow-up sense completes it. No-op without the table.
            try:
                from services import prestudy
                prestudy.mark_followups(db, user_id, [sense_id], 'completed_at')
            except Exception as e:
                logger.info('prestudy follow-up not completed for sense %s: %s', sense_id, e)

        steps: Dict[str, Any] = {
            'counters': lambda: self._bump_exercise_counters(exercise_id, exercise, is_correct),
        }
        if sense_id:
            steps['prestudy'] = _prestudy
        if tracked and is_first_attempt:
            steps['bkt'] = _bkt
        if card_row:
            steps['fsrs'] = lambda: self._apply_fsrs_review(
                card_row, sense_id, is_correct, time_taken_ms)
        if attempt_id and eff_language_id:
            # Weekly minutes ledger (ADR-035): every attempt, in or out of a
            # planned session, once per exercise_attempts id.
            steps['study_time'] = lambda: self._credit_practice_time(
                user_id, eff_language_id, seconds, attempt_id)
            if Config.STUDY_PLAN_ENABLED and session_mode in ('acquisition', 'maintenance'):
                steps['progress'] = lambda: self._record_plan_progress(
                    user_id, eff_language_id, attempt_id, session_mode, seconds,
                    sense_id, is_tail)
        done = dict(zip(steps, run_parallel(*steps.values())))

        bkt_result = done.get('bkt')
        if bkt_result:
            result['bkt_update'] = bkt_result

        # 4. Steps that must follow the BKT write: the FSRS lapse penalty
        # (scales the p_known BKT just wrote) and the ladder, whose lapse path
        # applies the same penalty.
        after: List[Any] = []
        if bkt_result:
            after.append(lambda: self._capture_knowledge_outcome(attempt_id, bkt_result))
        if done.get('fsrs'):
            after.append(lambda: self._apply_lapse_penalty(user_id, sense_id))
        if sense_id:
            # Ladder progress (rings, gates, demotion): only moves the ladder,
            # for words on it, on first attempts.
            after.append(lambda: self._apply_ladder_progress(
                result, user_id, sense_id, exercise_id, is_correct,
                is_first_attempt, eff_language_id, exercise_context,
            ))
        run_parallel(*after)

        return result

    def _bump_exercise_counters(
        self, exercise_id: str, exercise: Dict[str, Any], is_correct: bool,
    ) -> None:
        """``attempt_count + 1`` (and ``correct_count + 1`` when correct).

        PostgREST cannot write ``col = col + 1``, so the write is conditional on
        the ``attempt_count`` that was read: when another attempt got in first
        no row matches, the counts are read again and the write retried. The
        common case is one round trip. ``record_exercise_attempt`` (the RPC
        path) increments in SQL instead.
        """
        row = exercise
        for attempt in range(COUNTER_WRITE_ATTEMPTS):
            seen = row.get('attempt_count')
            updates = {'attempt_count': (seen or 0) + 1}
            if is_correct:
                updates['correct_count'] = (row.get('correct_count') or 0) + 1
            query = self.db.table('exercises').update(updates).eq('id', exercise_id)
            if attempt == COUNTER_WRITE_ATTEMPTS - 1:
                query.execute()          # still contended: write unconditionally
                return
            query = (query.is_('attempt_count', 'null') if seen is None
                     else query.eq('attempt_count', seen))
            if query.execute().data:
                return
            fresh = (
                self.db.table('exercises')
                .select('attempt_count, correct_count')
                .eq('id', exercise_id)
                .limit(1)
                .execute()
                .data
            )
            if not isinstance(fresh, list) or not fresh:
                return
            row = fresh[0]

    def _credit_practice_time(
        self, user_id: str, language_id: int, seconds: int, attempt_id,
    ) -> None:
        try:
            from services.study_time import credit_study_time  # lazy: avoids import cycle
            credit_study_time(
                self.db, user_id, language_id, 'practice', seconds,
                'exercise_attempts', str(attempt_id),
            )
        except Exception as e:
            logger.warning(
                'study-time credit failed (non-fatal) for attempt=%s: %s',
                attempt_id, e,
            )

    def _record_plan_progress(
        self, user_id: str, language_id: int, attempt_id, session_mode: str,
        seconds: int, sense_id, is_tail: bool,
    ) -> None:
        """Study Plan weekly counters for one attempt. Best-effort."""
        try:
            self.db.rpc('record_session_progress', {
                'p_user_id':       user_id,
                'p_language_id':   language_id,
                'p_attempt_id':    attempt_id,
                'p_kind':          'practice_acq' if session_mode == 'acquisition'
                                   else 'practice_maint',
                'p_skill':         None,
                'p_delta_count':   0,
                'p_delta_seconds': seconds,
                # Session-budget-settings (TASK-872): the sense is passed
                # only for acquisition so the RPC can count a new word the
                # day it is first attempted; maintenance passes None.
                'p_sense_id':      sense_id if session_mode == 'acquisition'
                                   else None,
                'p_is_tail':       bool(is_tail),
            }).execute()
        except Exception as e:
            logger.warning(
                'record_session_progress failed (non-fatal) for attempt=%s: %s',
                attempt_id, e,
            )

    def _record_attempt_via_rpc(
        self,
        user_id: str,
        exercise_id: str,
        is_correct: bool,
        user_response: Optional[dict],
        time_taken_ms: Optional[int],
        session_mode: Optional[str],
        language_id: Optional[int],
        expected_seconds: Optional[int],
        is_tail: bool,
        exercise_context: str,
    ) -> Optional[Dict[str, Any]]:
        """The attempt through ``record_exercise_attempt`` (one transaction).

        Returns None when the function is not deployed, so the caller uses the
        per-step path; nothing has been written in that case. Any other RPC
        error propagates. FSRS scheduling and the new-word-drill restart stay
        in Python (migrations/record_exercise_attempt.sql).
        """
        global _attempt_rpc_missing_until
        if _attempt_rpc_missing_until > time.monotonic():
            return None
        plan_kind = None
        if Config.STUDY_PLAN_ENABLED and session_mode in ('acquisition', 'maintenance'):
            plan_kind = 'practice_acq' if session_mode == 'acquisition' else 'practice_maint'
        try:
            data = self.db.rpc('record_exercise_attempt', {
                'p_user_id':          user_id,
                'p_exercise_id':      exercise_id,
                'p_is_correct':       bool(is_correct),
                'p_user_response':    user_response or {},
                'p_time_taken_ms':    time_taken_ms,
                'p_language_id':      language_id or None,
                'p_credit_seconds':   self._effective_practice_seconds(
                    time_taken_ms, expected_seconds),
                'p_plan_kind':        plan_kind,
                'p_is_tail':          bool(is_tail),
                'p_exercise_context': exercise_context,
            }).execute().data
        except Exception as exc:
            text = str(exc)
            if 'PGRST202' in text or 'Could not find the function' in text:
                _attempt_rpc_missing_until = time.monotonic() + ATTEMPT_RPC_RECHECK_SECONDS
                logger.info('record_exercise_attempt not deployed; using the per-step path')
                return None
            raise
        if isinstance(data, list) and len(data) == 1:
            data = data[0]
        if not isinstance(data, dict):
            raise RuntimeError('record_exercise_attempt returned %r' % (data,))
        if data.get('error'):
            return {'error': 'Exercise not found'}

        for warning in data.get('warnings') or []:
            log = logger.info if warning.get('step') == 'prestudy_followups' else logger.warning
            log('record_exercise_attempt: %s failed (non-fatal) for attempt=%s: %s',
                warning.get('step'), data.get('attempt_id'), warning.get('error'))

        sense_id = data.get('sense_id')
        result: Dict[str, Any] = {
            'attempt_id':      data.get('attempt_id'),
            'is_correct':      is_correct,
            'exercise_type':   data.get('exercise_type'),
            'is_first_attempt': bool(data.get('is_first_attempt')),
        }
        if data.get('bkt_update'):
            result['bkt_update'] = data['bkt_update']

        card_row = data.get('flashcard')
        if card_row and self._apply_fsrs_review(card_row, sense_id, is_correct, time_taken_ms):
            self._apply_lapse_penalty(user_id, sense_id)
        if sense_id:
            self._report_ladder_progress(
                result, data.get('ladder'), user_id, sense_id, data.get('language_id'))
        return result

    def _apply_ladder_progress(
        self, result: Dict[str, Any], user_id: str, sense_id: int,
        exercise_id: str, is_correct: bool, is_first_attempt: bool,
        language_id: Optional[int], exercise_context: str,
    ) -> None:
        """Move the word's ladder (best effort; adds ``result['ladder']``).

        A word demoted from ring 2 that came through the new-word drill
        restarts the drill (ADR-040).
        """
        try:
            resp = self.db.rpc('ladder_apply_progress', {
                'p_user_id':          user_id,
                'p_sense_id':         sense_id,
                'p_exercise_id':      exercise_id,
                'p_is_correct':       bool(is_correct),
                'p_is_first_attempt': bool(is_first_attempt),
                'p_exercise_context': exercise_context
                if exercise_context in ('standard', 'gate', 'stress_test') else 'standard',
            }).execute()
            ladder = resp.data if isinstance(resp.data, dict) else None
        except Exception as e:
            logger.warning('ladder progress failed (non-fatal) for sense %s: %s', sense_id, e)
            return
        self._report_ladder_progress(result, ladder, user_id, sense_id, language_id)

    def _report_ladder_progress(
        self, result: Dict[str, Any], ladder: Optional[Dict[str, Any]],
        user_id: str, sense_id: int, language_id: Optional[int],
    ) -> None:
        """Summarise a ``ladder_apply_progress`` result onto ``result['ladder']``."""
        if not isinstance(ladder, dict) or ladder.get('skipped'):
            return
        result['ladder'] = {k: ladder.get(k) for k in (
            'family', 'current_ring', 'word_state', 'gate_pending',
            'stress_test_ready', 'demoted', 'is_lapse')}
        try:
            from services import intro_drill
            if intro_drill.restart_if_demoted(self.db, user_id, sense_id, language_id, ladder):
                result['ladder']['intro_restart'] = True
        except Exception as e:
            logger.warning('intro restart check failed for sense %s: %s', sense_id, e)

    def record_prestudy_exercise_attempt(
        self,
        user_id: str,
        exercise: Dict[str, Any],
        is_correct: bool,
        user_response: Optional[dict] = None,
    ) -> Dict[str, Any]:
        """Record a ladder exercise answered inside a test prestudy prime.

        Unlike ``record_attempt_with_updates`` this never touches the ladder,
        FSRS, Study Plan counters or the practice minutes ledger: prestudy is
        same-day priming, not a ladder admission, and its minutes are credited
        once for the whole prestudy session (kind ``prestudy``). The row is
        tagged ``source = 'prestudy'`` and the BKT update uses the exercise's
        own type parameters, on the first attempt at that exercise only (the
        same first-attempt gate as practice).

        ``exercise`` is an ``exercises`` row (id, exercise_type, word_sense_id,
        language_id) the caller has already checked belongs to the test.
        If ``exercise_attempts.source`` does not exist yet
        (migrations/prestudy_workflow.sql not applied), no row is written, so
        a prestudy answer is never mistaken for a practice attempt; the BKT
        evidence is still recorded.
        """
        exercise_id = exercise.get('id')
        sense_id = exercise.get('word_sense_id')
        exercise_type = exercise.get('exercise_type')
        language_id = exercise.get('language_id')
        prior = (
            self.db.table('exercise_attempts').select('id')
            .eq('user_id', user_id).eq('exercise_id', exercise_id).limit(1).execute()
        )
        is_first_attempt = not bool(prior.data)
        attempt_id = None
        try:
            inserted = self.db.table('exercise_attempts').insert({
                'user_id':       user_id,
                'exercise_id':   exercise_id,
                'user_response': user_response or {},
                'is_correct':    bool(is_correct),
                'exercise_type': exercise_type,
                'sense_id':      sense_id,
                'is_first_attempt': is_first_attempt,
                'source':        'prestudy',
                'created_at':    datetime.now(timezone.utc).isoformat(),
            }).execute()
            attempt_id = (inserted.data or [{}])[0].get('id')
        except Exception as e:
            logger.info('prestudy exercise attempt row not written (%s); BKT only', e)
        result: Dict[str, Any] = {'attempt_id': attempt_id, 'is_first_attempt': is_first_attempt}
        if sense_id and language_id and is_first_attempt:
            try:
                bkt = VocabularyKnowledgeService(self.db).update_from_word_test(
                    user_id=user_id, sense_id=sense_id, is_correct=bool(is_correct),
                    language_id=language_id, exercise_type=exercise_type,
                )
                if bkt:
                    result['bkt_update'] = bkt
                    if attempt_id:
                        self._capture_knowledge_outcome(attempt_id, bkt)
            except Exception as e:
                logger.error('prestudy BKT update failed for sense %s: %s', sense_id, e)
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
        row = self._read_fsrs_card(user_id, sense_id)
        if row and self._apply_fsrs_review(row, sense_id, is_correct, time_taken_ms):
            self._apply_lapse_penalty(user_id, sense_id)

    def _read_fsrs_card(self, user_id: str, sense_id: int) -> Optional[Dict[str, Any]]:
        """The learner's flashcard row for a sense, or None (no card, or a failed read)."""
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
            return card_resp.data[0] if card_resp.data else None
        except Exception as e:
            logger.error('FSRS update failed for sense %s: %s', sense_id, e)
            return None

    def _apply_fsrs_review(
        self,
        row: Dict[str, Any],
        sense_id: int,
        is_correct: bool,
        time_taken_ms: Optional[int] = None,
    ) -> bool:
        """Rate the card and write its new schedule. True when the review was a lapse.

        Never raises. The caller applies the BKT lapse penalty, after the BKT
        update for the same attempt has been written.
        """
        try:
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
            return new_card.lapses > card.lapses
        except Exception as e:
            logger.error('FSRS update failed for sense %s: %s', sense_id, e)
            return False

    def _apply_lapse_penalty(self, user_id: str, sense_id: int) -> None:
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
