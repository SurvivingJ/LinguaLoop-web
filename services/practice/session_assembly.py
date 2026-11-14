"""Practice session assembly: the session RPC, the floor, follow-ups, ordering,
extra rounds and serve-time preparation."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from services.concurrency import run_parallel
from services import study_plan_service as _plan
from services.day_boundary import plan_today_iso
from services.practice.constants import (
    EXTRA_NEW_WORDS_MAX,
    EXTRA_REVIEW_ITEMS,
    EXTRA_REVIEW_RECENT_MINUTES,
    PRACTICE_SESSION_MIN_ITEMS,
    PRESTUDY_FOLLOWUPS_PER_SESSION,
    PRESTUDY_FOLLOWUP_EXPECTED_SECONDS,
    _settled,
    _unwrap,
)

logger = logging.getLogger(__name__)


class SessionAssemblyMixin:
    """Session retrieval for PracticeSessionService (expects ``self.db``)."""

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

        # The session RPC, together with the reads the later steps need that
        # do not depend on its result.
        db = self.db
        from services import intro_drill, prestudy
        from services.vocabulary_ladder import script_serving
        reads: Dict[str, Any] = {
            'session': lambda: self._practice_session_rpc(
                user_id, language_id, mode, target_minutes, user_theta),
        }
        want_followups = mode in ('maintenance', 'auto') and not tail
        if want_followups:
            # The plan row is cached per request, so resolve "today" here and
            # not on a pool thread.
            today_iso = _settled(lambda: plan_today_iso(db, user_id, language_id))()
            reads['followups'] = lambda: prestudy.due_followup_senses(
                db, user_id, language_id, _unwrap(today_iso),
                limit=PRESTUDY_FOLLOWUPS_PER_SESSION)
        if intro_drill.ENABLED:
            reads['intro_ids'] = lambda: intro_drill.intro_sense_ids(db, user_id)
        if language_id in script_serving.SCRIPT_VARIANT_LANGUAGES:
            reads['preferences'] = lambda: self._exercise_preferences(user_id)
        fetched = dict(zip(reads, run_parallel(*[_settled(r) for r in reads.values()])))

        try:
            payload = _unwrap(fetched['session'])
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

        # Test prestudy next-day review: senses flagged by yesterday's prestudy
        # (prestudy_followups) get one exercise each inside Maintenance. Not a
        # ladder admission, not counted against new_words_per_day.
        if want_followups:
            try:
                self._inject_prestudy_followups(
                    payload, user_id, language_id, due=_unwrap(fetched['followups']))
            except Exception as e:
                logger.warning(
                    'prestudy follow-up injection failed (non-fatal) for user=%s '
                    'lang=%s: %s', user_id, language_id, e,
                )

        # New-word drill (ADR-040): due intro words run first as one block.
        # Stage 2-4 words in every mode; brand-new stage-1 words only where new
        # words are taught (acquisition / auto), within today's quota. Optional
        # tail rounds serve them too: that is where today's leftover words go.
        try:
            if intro_drill.ENABLED:
                # Intro words are drilled only by the drill: drop them from
                # the regular items (BKT/FSRS reviews can still pick them).
                intro_ids = _unwrap(fetched['intro_ids'])
                if intro_ids and payload.get('items'):
                    payload['items'] = [i for i in payload['items']
                                        if i.get('sense_id') not in intro_ids]
                block = intro_drill.block_for_session(self, user_id, language_id, mode)
                if block:
                    payload['intro_drill'] = block
                    if payload.get('no_content_reason'):
                        payload['no_content_reason'] = None
        except Exception as e:
            logger.warning(
                'intro drill block failed (non-fatal) for user=%s lang=%s: %s',
                user_id, language_id, e,
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
            self._apply_script_variant(
                payload, user_id, language_id,
                preferences=_unwrap(fetched['preferences'])
                if 'preferences' in fetched else None)
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

    def _practice_session_rpc(
        self, user_id: str, language_id: int, mode: str, target_minutes: int,
        user_theta: Optional[float] = None,
    ):
        """One ``get_practice_session`` call; returns its jsonb. Raises on failure."""
        return self.db.rpc('get_practice_session', {
            'p_user_id':        user_id,
            'p_language_id':    language_id,
            'p_mode':           mode,
            'p_target_minutes': target_minutes,
            'p_user_theta':     user_theta,
        }).execute().data

    def _inject_prestudy_followups(
        self, payload: Dict[str, Any], user_id: str, language_id: int,
        due: Optional[List[int]] = None,
    ) -> int:
        """Add one exercise per due prestudy next-day review sense, in place.

        Senses already in the session are only marked served; senses with no
        active exercise stay due (they were sent to generation when primed).
        Items carry ``mode: 'maintenance'`` and ``prestudy_followup: true``;
        the review completes when the learner answers any exercise of that
        sense (``record_attempt_with_updates``). ``due`` is the due sense list
        when the caller has already read it.
        """
        from services import prestudy
        if due is None:
            today = plan_today_iso(self.db, user_id, language_id)
            due = prestudy.due_followup_senses(
                self.db, user_id, language_id, today, limit=PRESTUDY_FOLLOWUPS_PER_SESSION)
        if not due:
            return 0
        items = payload.get('items') or []
        in_session = {i.get('sense_id') for i in items if i.get('sense_id') is not None}
        need = [s for s in due if s not in in_session]
        extras: List[Dict[str, Any]] = []
        if need:
            rows = (
                self.db.table('exercises')
                .select('id, word_sense_id, exercise_type, content, ladder_level')
                .eq('is_active', True).in_('word_sense_id', need)
                .order('ladder_level').execute().data or []
            )
            seen = {i.get('exercise_id') for i in items}
            picked: Dict[int, Dict[str, Any]] = {}
            for r in rows:
                sid = r.get('word_sense_id')
                if sid in picked or r.get('id') in seen:
                    continue
                picked[sid] = {
                    'exercise_id':      r['id'],
                    'sense_id':         sid,
                    'exercise_type':    r.get('exercise_type'),
                    'family':           None,
                    'content':          r.get('content'),
                    'ladder_level':     r.get('ladder_level'),
                    'p_known':          None,
                    'expected_seconds': PRESTUDY_FOLLOWUP_EXPECTED_SECONDS,
                    'mode':             'maintenance',
                    'prestudy_followup': True,
                }
            extras = [picked[s] for s in need if s in picked]
        if extras:
            payload['items'] = self._interleave_extras(items, extras)
            payload['prestudy_followups'] = len(extras)
            if payload.get('no_content_reason'):
                payload['no_content_reason'] = None
        served = [s for s in due if s in in_session] + [e['sense_id'] for e in extras]
        prestudy.mark_followups(self.db, user_id, served, 'served_at')
        return len(extras)

    # ------------------------------------------------------------------
    # Extra rounds (practice-extra-rounds, ADR-036)
    # ------------------------------------------------------------------

    def get_extra_round(
        self,
        user_id: str,
        language_id: int,
        reviews: bool,
        new_words: int,
        exclude_sense_ids: Optional[List[int]] = None,
    ) -> Dict[str, Any]:
        """One open-ended Practice round, beyond today's budget.

        ``new_words`` (0..EXTRA_NEW_WORDS_MAX): admit enough words past the
        daily quota that ``new_words`` never-started words are available, then
        serve acquisition items for them. ``reviews``: serve up to
        EXTRA_REVIEW_ITEMS review items -- due work first (the Maintenance
        pool), then review-ahead (``get_review_ahead_items``).

        Attempts go through the normal attempt path with is_tail=True, so FSRS,
        BKT and the weekly counters update as for any tail round.

        Returns the session payload shape plus ``extra`` stats:
        ``{requested_new_words, new_words_served, new_words_admitted,
        new_words_beyond_quota, reviews_served}``.
        """
        new_words = max(0, min(int(new_words or 0), EXTRA_NEW_WORDS_MAX))
        if not reviews and new_words == 0:
            return {'error': 'nothing_requested', 'code': 'E_EMPTY'}
        exclude = set(int(s) for s in (exclude_sense_ids or []))

        acq_items: List[Dict[str, Any]] = []
        admitted: List[int] = []
        targets: List[int] = []
        beyond_quota = 0
        if new_words:
            admitted, targets, beyond_quota = self._admit_extra_new_words(
                user_id, language_id, new_words)

        # The acquisition and maintenance session calls do not depend on each
        # other: start both, then build each half from its result.
        calls: Dict[str, Any] = {}
        if targets:
            minutes = self._extra_acquisition_minutes(language_id, new_words)
            calls['acquisition'] = lambda: self._practice_session_rpc(
                user_id, language_id, 'acquisition', minutes)
        if reviews:
            calls['maintenance'] = lambda: self._practice_session_rpc(
                user_id, language_id, 'maintenance', 15)
        fetched = dict(zip(calls, run_parallel(*[_settled(c) for c in calls.values()])))

        if new_words:
            acq_items = self._extra_acquisition_items(
                user_id, language_id, targets, new_words,
                fetched=fetched.get('acquisition'))

        rev_items: List[Dict[str, Any]] = []
        if reviews:
            rev_items = self._extra_review_items(
                user_id, language_id, exclude, fetched=fetched.get('maintenance'))

        items = self._interleave_extras(rev_items, acq_items) if (
            rev_items and acq_items) else (rev_items or acq_items)

        payload: Dict[str, Any] = {
            'items': items,
            'tail': True,
            'extra': {
                'requested_new_words':    new_words,
                'new_words_served':       len({i.get('sense_id') for i in acq_items}),
                'new_words_admitted':     len(admitted),
                'new_words_beyond_quota': beyond_quota,
                'reviews_served':         len(rev_items),
            },
            'no_content_reason': None if items else 'all_complete',
        }
        # New-word drill: extra new words are intro words, so they come as an
        # intro block (session 1), not ladder items. A review round also
        # carries the drill words whose next session (2-4) is due: they are
        # reviews, and the regular items never include intro words.
        if reviews or (new_words and targets):
            try:
                from services import intro_drill
                if intro_drill.ENABLED:
                    rows: List[Dict[str, Any]] = []
                    if reviews:
                        today = intro_drill._today(self.db, user_id, language_id)
                        rows = intro_drill.select_block_rows(
                            intro_drill.due_rows(self.db, user_id, language_id, today),
                            'maintenance', 0)
                    if new_words and targets:
                        have = {int(r['sense_id']) for r in rows}
                        rows += [r for r in (self.db.table('user_word_ladder').select(
                            'sense_id, intro_stage, intro_due_date, intro_history, created_at'
                        ).eq('user_id', user_id).eq('word_state', 'intro').in_(
                            'sense_id', list(targets)).execute().data or [])
                            if int(r['sense_id']) not in have]
                    block = intro_drill.build_block(
                        self.db, user_id, language_id, rows[:intro_drill.INTRO_BLOCK_MAX_WORDS])
                    if block:
                        target_set = {int(t) for t in targets}
                        drilled = {w['sense_id'] for w in block['words']}
                        # a drill word is drilled by the drill only
                        payload['items'] = [i for i in payload['items']
                                            if i.get('sense_id') not in drilled]
                        payload['intro_drill'] = block
                        payload['extra']['new_words_served'] = sum(
                            1 for w in block['words'] if w['sense_id'] in target_set)
                        payload['extra']['reviews_served'] += sum(
                            1 for w in block['words'] if w['sense_id'] not in target_set)
                        payload['no_content_reason'] = None
            except Exception as e:
                logger.warning('extra round: intro block failed (non-fatal): %s', e)
        try:
            self._apply_script_variant(payload, user_id, language_id)
        except Exception as e:
            logger.warning('extra round: script variant failed (non-fatal): %s', e)
        self._prepare_jumbled_items(payload['items'], language_id)
        for item in payload['items']:
            item.pop('score_breakdown', None)
        return payload

    def _extra_acquisition_minutes(self, language_id: int, n: int) -> int:
        return max(1, min(180, int(round(
            n * float(_plan.get_minutes_per_new_word(self.db, language_id))))))

    def _extra_acquisition_items(
        self, user_id: str, language_id: int, targets: List[int], n: int,
        fetched=None,
    ) -> List[Dict[str, Any]]:
        """Acquisition items for the round's target words (oldest first).

        ``fetched`` is the ``(data, error)`` of an acquisition session call the
        caller already made; without it the call is made here.
        """
        if not targets:
            return []
        try:
            data = _unwrap(fetched) if fetched is not None else self._practice_session_rpc(
                user_id, language_id, 'acquisition',
                self._extra_acquisition_minutes(language_id, n))
        except Exception as e:
            logger.warning('extra round acquisition call failed: %s', e)
            return []
        data = data if isinstance(data, dict) else {}
        items = [
            i for i in (data.get('items') or [])
            if not i.get('is_gate_marker') and not i.get('is_stress_test_marker')
        ]
        rank = {sid: k for k, sid in enumerate(targets)}
        picked = [i for i in items if i.get('sense_id') in rank]
        picked.sort(key=lambda i: rank[i['sense_id']])  # stable within a word
        for i in picked:
            i['mode'] = 'acquisition'
        return picked

    def _extra_review_items(
        self, user_id: str, language_id: int, exclude: set, fetched=None,
    ) -> List[Dict[str, Any]]:
        """Up to EXTRA_REVIEW_ITEMS reviews: due work first (prestudy next-day
        reviews, then the Maintenance pool), then review-ahead.

        ``fetched`` is the ``(data, error)`` of a maintenance session call the
        caller already made; without it the call is made here."""
        items: List[Dict[str, Any]] = []
        seen_senses = set(exclude)
        try:
            # Prestudy follow-ups are due review work too; get_session injects
            # them only outside tail rounds, so a learner whose day has no
            # practice chunk never saw them here.
            holder: Dict[str, Any] = {'items': []}
            self._inject_prestudy_followups(holder, user_id, language_id)
            for i in holder.get('items') or []:
                sid = i.get('sense_id')
                if sid is None or sid in seen_senses:
                    continue
                seen_senses.add(sid)
                items.append(i)
        except Exception as e:
            logger.warning('extra round prestudy follow-ups failed: %s', e)
        try:
            data = _unwrap(fetched) if fetched is not None else self._practice_session_rpc(
                user_id, language_id, 'maintenance', 15)
            data = data if isinstance(data, dict) else {}
            due = [i for i in (data.get('items') or [])
                   if i.get('mode') == 'maintenance']
            if len(due) > 1:
                self._most_overdue_first(due, user_id)
            for i in due:
                sid = i.get('sense_id')
                if sid is None or sid in seen_senses:
                    continue
                seen_senses.add(sid)
                items.append(i)
                if len(items) >= EXTRA_REVIEW_ITEMS:
                    return items
        except Exception as e:
            logger.warning('extra round maintenance call failed: %s', e)

        try:
            resp = self.db.rpc('get_review_ahead_items', {
                'p_user_id':                user_id,
                'p_language_id':            language_id,
                'p_limit':                  EXTRA_REVIEW_ITEMS - len(items),
                'p_exclude_recent_minutes': EXTRA_REVIEW_RECENT_MINUTES,
                'p_exclude_sense_ids':      sorted(seen_senses),
            }).execute()
            ahead = resp.data if isinstance(resp.data, list) else []
        except Exception as e:
            logger.warning('review-ahead call failed: %s', e)
            ahead = []
        for i in ahead:
            if i.get('sense_id') in seen_senses:
                continue
            seen_senses.add(i.get('sense_id'))
            items.append(i)
        return items[:EXTRA_REVIEW_ITEMS]

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
            # Ask for the full budget rather than the deficit: the RPC
            # spends minutes, and a two-minute request comes back with two
            # items regardless of how much review is actually due.
            data = self._practice_session_rpc(
                user_id, language_id, 'maintenance', target_minutes)
        except Exception as e:
            logger.warning('session floor maintenance call failed: %s', e)
            return

        extra = data if isinstance(data, dict) else {}
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

        sources = (('user_flashcards', 'due_date'),
                   ('user_word_ladder', 'review_due_at'))
        db = self.db

        def _read(table, column):
            return lambda: (db.table(table).select(f'sense_id, {column}')
                            .eq('user_id', user_id).in_('sense_id', sense_ids)
                            .execute().data)

        for (table, column), rows in zip(
                sources, run_parallel(*[_read(t, c) for t, c in sources])):
            for row in (rows or []):
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
        preferences: Optional[dict] = None,
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
            self._exercise_preferences(user_id) if preferences is None else preferences
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
