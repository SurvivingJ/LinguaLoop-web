"""New-word admission: the daily quota state, nomination queues, the supply
gate and ladder subscription."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from services.concurrency import run_parallel
from services import study_plan_service as _plan
from services.day_boundary import local_date, local_day_start_utc, plan_row, plan_today_iso
from services.practice.constants import (
    CALIBRATION_EVIDENCE_MAX_AGE_DAYS,
    CALIBRATION_ROW_LIMIT,
    DEMAND_GENERATION_MAX_PER_CALL,
    EVIDENCE_ROW_LIMIT,
    LADDER_ELIGIBLE_STATES,
    LADDER_EVIDENCE_MIN_COUNT,
    LADDER_EVIDENCE_P_KNOWN_MAX,
    LADDER_MIN_EXERCISES_PER_SENSE,
    LADDER_SUBSCRIBED_ROW_LIMIT,
    LADDER_TOPUP_MAX_PER_CALL,
    NOMINATION_OVERFETCH,
    RECENT_TEST_CHUNK,
    RECENT_TEST_ROW_LIMIT,
    RECENT_TEST_WINDOW_DAYS,
    SUPPLY_GATE_CHUNK,
    SUPPLY_GATE_ROW_LIMIT,
    WRONG_ANSWER_ROW_LIMIT,
)

logger = logging.getLogger(__name__)


class NewWordAdmissionMixin:
    """Ladder intake for PracticeSessionService (expects ``self.db``)."""

    def _admit_extra_new_words(
        self, user_id: str, language_id: int, n: int,
    ):
        """Admit words past the daily quota so ``n`` unstarted words exist.

        Returns ``(admitted, target_sense_ids, beyond_quota)``. Unlike
        admit_daily_new_words this ignores the quota E and writes no
        shortfall: extra words are not part of the plan. Already-admitted
        unstarted words are used first, so repeated rounds do not bloat the
        pool. ``beyond_quota`` is how many of the round's words go past what
        is left of today's quota (for the UI warning).
        """
        state = self.new_word_state(user_id, language_id) or {}
        unstarted = list(state.get('unstarted_sense_ids') or [])
        if not state:
            # No study plan row (or the state read failed): the learner still
            # asked for new words, so serve the words already admitted and not
            # started -- e.g. prestudy words queued for later, which no plan
            # quota would otherwise ever release -- before admitting more.
            unstarted = self._unstarted_sense_ids(user_id, language_id)
        quota_left = max(0, int(state.get('effective') or 0)
                         - int(state.get('started_today') or 0))
        admitted: List[int] = []
        want = n - len(unstarted)
        if want > 0:
            try:
                subscribed = self._subscribed_sense_ids(user_id)
                fresh = self._nominate_new_words(
                    user_id, language_id, want, subscribed)
                if fresh and self._insert_ladder_rows(user_id, fresh, language_id):
                    admitted = list(fresh)
            except Exception as e:
                logger.warning(
                    'extra new-word intake failed for user=%s lang=%s: %s',
                    user_id, language_id, e,
                )
        targets = (unstarted + admitted)[:n]
        # Words admitted before the drill shipped (word_state 'new', never
        # attempted) would otherwise skip the drill and depend on the
        # acquisition RPC happening to pick them, which it mostly does not.
        self._promote_unstarted_to_intro(
            user_id, language_id, [t for t in targets if t in set(unstarted)])
        if admitted:
            logger.info(
                'extra intake admitted %d sense(s) beyond quota for user=%s lang=%s',
                len(admitted), user_id, language_id,
            )
        return admitted, targets, max(0, len(targets) - quota_left)

    def _promote_unstarted_to_intro(
        self, user_id: str, language_id: int, sense_ids: List[int],
    ) -> None:
        """Move never-started ``word_state='new'`` rows into intro session 1.

        ``sense_ids`` come from ``unstarted_sense_ids`` (no attempt, no intro
        history), so nothing learned is lost: the drill replaces ring 1 for
        them exactly as for a freshly admitted word. Rows already in intro
        (or any other state) are left alone. Best effort.
        """
        from services import intro_drill
        if not intro_drill.ENABLED or not sense_ids:
            return
        try:
            today = plan_today_iso(self.db, user_id, language_id)
            fields = intro_drill.new_intro_fields(today)
            fields['updated_at'] = datetime.now(timezone.utc).isoformat()
            (self.db.table('user_word_ladder').update(fields)
             .eq('user_id', user_id).eq('word_state', 'new')
             .in_('sense_id', list(sense_ids)).execute())
        except Exception as e:
            logger.warning('extra round: intro promotion failed for user=%s lang=%s: %s',
                           user_id, language_id, e)
        finally:
            from services.request_cache import invalidate
            invalidate('new_word_state', str(user_id))

    def _unstarted_sense_ids(self, user_id: str, language_id: int) -> List[int]:
        """Admitted, never-started words (oldest admission first), read without
        a study plan row: the same ladder_new_word_state count new_word_state
        uses, with the day boundary from plan_timezone (UTC when unset).
        Best effort: [] on any failure."""
        try:
            from services.day_boundary import plan_timezone
            tz = plan_timezone(self.db, user_id, language_id)
            st = self.db.rpc('ladder_new_word_state', {
                'p_user_id':     user_id,
                'p_language_id': language_id,
                'p_day_start':   local_day_start_utc(tz).isoformat(),
            }).execute().data
        except Exception as e:
            logger.warning('unstarted words read failed for user=%s lang=%s: %s',
                           user_id, language_id, e)
            return []
        if isinstance(st, list):
            st = st[0] if st else None
        if not isinstance(st, dict):
            return []
        return [int(s) for s in (st.get('unstarted_sense_ids') or [])]

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
        """``_new_word_state``, computed at most once per GET request.

        A Practice GET asked for it up to three times (intake, intro block,
        ordering) and a daily-session GET twice; each costs the plan read plus
        two RPCs. Writers of ``user_word_ladder`` call
        ``request_cache.invalidate('new_word_state', ...)`` so a word admitted
        mid-request is counted by the next read. A None (failed read) is never
        cached.
        """
        from services.request_cache import memo
        return memo(
            ('new_word_state', str(user_id), str(language_id)),
            lambda: self._new_word_state(user_id, language_id),
            cache_none=False,
        )

    def _new_word_state(
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
            plan = plan_row(self.db, user_id, language_id)
        except Exception as e:
            logger.warning(
                'new-word state: plan read failed for user=%s lang=%s: %s',
                user_id, language_id, e,
            )
            return None
        if not plan:
            return None

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

        with_governor = 'practice' not in excluded
        day_start = local_day_start_utc(tz).isoformat()

        # One round trip for both RPCs (ADR-043 option B). None when the
        # bundle is not deployed yet or fails: then the two separate calls.
        from services.optional_rpc import call_bundle
        bundle = call_bundle(self.db, 'new_word_state_inputs', {
            'p_user_id':       user_id,
            'p_language_id':   language_id,
            'p_date':          today.isoformat(),
            'p_day_start':     day_start,
            'p_with_governor': with_governor,
        })

        if not with_governor:
            gov: Dict[str, Any] = {'level': 'normal'}
        elif bundle is not None:
            gov = _plan.parse_review_governor(bundle.get('governor'))
        else:
            gov = _plan.get_review_governor(
                self.db, user_id, language_id, today
            ) or {'level': 'normal'}
        level = gov.get('level') or 'normal'
        effective = _plan.effective_new_words(quota, level)

        if bundle is not None:
            st = bundle.get('ladder')
        else:
            try:
                st = self.db.rpc('ladder_new_word_state', {
                    'p_user_id':     user_id,
                    'p_language_id': language_id,
                    'p_day_start':   day_start,
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

        def _servable_pool():
            # Side effect only: asks for exercises for subscribed-but-unservable
            # rows. No longer gates intake and target_active_pool is not read.
            try:
                self._eligible_ladder_count(user_id, language_id)
            except Exception as e:
                logger.warning('eligible ladder count failed (non-fatal): %s', e)

        # Read the supply flag BEFORE set_new_words_shortfall flips it.
        today_iso = plan_today_iso(self.db, user_id, language_id)
        _, (prior_checked, planned_in_budget, checked_e), subscribed = run_parallel(
            _servable_pool,
            lambda: self._today_supply_flags(user_id, language_id, today_iso),
            lambda: self._subscribed_sense_ids(user_id),
        )
        # A supply check is only valid for the E it was made under. A mid-day
        # quota change (settings edit, governor level change) makes it stale:
        # treat the day as unchecked so the rebuild flag can fire once more.
        # (checked_e is None only for rows written before the key existed.)
        if prior_checked and checked_e is not None and checked_e != new_today:
            prior_checked = False

        fresh = self._nominate_new_words(user_id, language_id, want, subscribed)

        inserted = bool(fresh) and self._insert_ladder_rows(user_id, fresh, language_id)
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
            # Rewrites today's daily_test_loads targets: drop the request copy.
            from services.request_cache import invalidate
            invalidate('daily_load_row', str(user_id))
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

        recent, wrong_by_question, ledger, rows = run_parallel(
            lambda: self._recent_test_sense_ids(user_id, language_id),
            lambda: self._wrong_answer_sense_counts(user_id),
            lambda: self._calibration_ledger(user_id, language_id),
            lambda: self._evidence_rows(user_id, language_id),
        )
        a1 = [
            c for c in self._evidence_candidates(
                user_id, language_id, recency_first=True,
                wrong_by_question=wrong_by_question, ledger=ledger, rows=rows)
            if c['sense_id'] in recent and c['sense_id'] not in taken
        ]
        admitted += self._gate_and_admit(
            [c['sense_id'] for c in a1], want, language_id)
        taken.update(admitted)

        if len(admitted) < want:
            a2 = self._calibration_wrong_candidates(
                user_id, language_id, taken, ledger=ledger)
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
        from services import intro_drill
        if intro_drill.ENABLED:
            # Intro session 1 needs no ladder exercises (gloss + sentence +
            # reading); starved words are still queued for generation below.
            starved = [sid for sid in head[:want] if sid not in supplied]
            admitted = head[:want]
        else:
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
                .order('created_at', desc=True)
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
                q = (self.db.table('questions').select('sense_ids')
                     .in_('test_id', chunk)
                     .filter('sense_ids', 'not.is', 'null').execute())
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
        ledger: Optional[Dict[int, Dict[str, Any]]] = None,
    ) -> List[int]:
        """Queue A2: senses whose latest calibration answer was wrong.

        Rule (i): a single wrong (or explicit "I don't know") calibration answer
        is sufficient; neither LADDER_EVIDENCE_MIN_COUNT nor
        LADDER_EVIDENCE_P_KNOWN_MAX applies. Within CALIBRATION_EVIDENCE_MAX_AGE_DAYS,
        not in ``exclude``, and not currently 'known' / 'probably_known'. Ordered
        by lemma frequency (Zipf desc) then most recent answer. Ranked below A1
        by the caller; the supply gate still applies.
        """
        if ledger is None:
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

    def _evidence_rows(self, user_id: str, language_id: int) -> List[Dict[str, Any]]:
        """Knowledge rows that carry test / word-quiz evidence ([] on a failed read)."""
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
            return resp.data or []
        except Exception as e:
            logger.warning(
                'evidence queue read failed for user=%s lang=%s: %s',
                user_id, language_id, e,
            )
            return []

    def _evidence_candidates(
        self, user_id: str, language_id: int, recency_first: bool = False,
        wrong_by_question: Optional[Dict[int, int]] = None,
        ledger: Optional[Dict[int, Dict[str, Any]]] = None,
        rows: Optional[List[Dict[str, Any]]] = None,
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
        # The three reads, unless the caller has already made them.
        if wrong_by_question is None:
            wrong_by_question = self._wrong_answer_sense_counts(user_id)
        if ledger is None:
            ledger = self._calibration_ledger(user_id, language_id)
        if rows is None:
            rows = self._evidence_rows(user_id, language_id)

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
                # A question without sense ids counts nothing: leave its rows
                # in the database and out of the row cap.
                .filter('questions.sense_ids', 'not.is', 'null')
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

    def _insert_ladder_rows(self, user_id: str, sense_ids: List[int], language_id: Optional[int] = None) -> bool:
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
        from services import intro_drill
        if intro_drill.ENABLED and rows:
            from services.day_boundary import plan_today_iso, utc_today_iso
            today = plan_today_iso(self.db, user_id, language_id) if language_id else utc_today_iso()
            for r in rows:
                r.update(intro_drill.new_intro_fields(today))
        try:
            self.db.table('user_word_ladder').insert(rows).execute()
        except Exception as e:
            logger.error('ladder subscribe insert failed: %s', e)
            return False
        finally:
            from services.request_cache import invalidate
            invalidate('new_word_state', str(user_id))
        return True
