---
title: Practice Package (services/practice) — Technical Specification
type: feature-tech
status: complete
prose_page: ./practice-package.md
last_updated: 2026-11-23
dependencies:
  - "services/practice_session_service.py (composition and import point)"
  - "services/practice/{session_assembly,attempt_recording,new_word_admission,constants}.py"
  - "RPC: get_practice_session, get_review_ahead_items, record_exercise_attempt, ladder_new_word_state, new_word_state_inputs, review_governor_state (via study_plan_service), set_new_words_shortfall, bkt_apply_lapse_penalty"
  - "services/exercise_content/store.py (ADR-049), services/intro_drill.py, services/prestudy.py, services/study_plan_service.py, services/day_boundary.py, services/request_cache.py, services/optional_rpc.py, services/concurrency.py (run_parallel), services/vocabulary/{fsrs,knowledge_service}.py, services/vocabulary_ladder/{queue_drain,script_serving,speed_round}.py, services/dual_translation/cards.py"
  - "tables: user_word_ladder, user_vocabulary_knowledge, user_flashcards, exercises, exercise_attempts, calibration_responses, calibration_sessions, question_attempt_results, questions, tests, test_attempts, dim_word_senses, daily_test_loads, prestudy_followups"
breaking_change_risk: medium
open_questions:
  - "OPEN (known issue, not fixed): admission queue A1 has no known / probably_known veto; A2 and A2r do; [[decisions/ADR-047-basic-word-knowledge-prior]] says such words are vetoed. Owner: repeated recent misses override 'known'; the ADR is to be amended elsewhere. This page documents the code."
  - "OPEN (known limitation, not fixed): FSRS dating is server-UTC; see 'Known limitation: FSRS dates' in [[features/practice-engine.tech]]. Fix must move readers and writers together."
  - "Verified against the branch review/integration (HEAD of main plus the 2026-11-23 review packages) on 2026-11-23, not against a deployed build. The live database was checked for record_exercise_attempt (present, advisory lock in source) and the other RPC names; the md5 of the live record_exercise_attempt body was not compared with migrations/record_exercise_attempt.sql."
  - "OPEN: the supply check, placement admission (A2 / A2r) and the 2026-11-23 attempt path are described from code and unit tests; no production run was observed."
---

# Practice Package (`services/practice`) — Technical Specification

## Architecture Overview

`services/practice/` holds the three mixins and the constants of the Practice engine; `services/practice_session_service.py` composes them and is the only import point.

```
routes/practice.py ─┐
routes/study_session.py (via services/study_session/session.py) ─┤
routes/tests/prestudy.py ─┘── get_practice_session_service()  (singleton)
                                    │
        PracticeSessionService(SessionAssemblyMixin, AttemptRecordingMixin, NewWordAdmissionMixin)
                                    │  self.db = get_supabase_admin()
   ┌────────────────────────────────┼─────────────────────────────────┐
   session_assembly.py        attempt_recording.py            new_word_admission.py
   (get_session,              (record_attempt_with_updates,   (new_word_state, admit_daily_new_words,
    get_extra_round, floor,    record_prestudy_exercise_      _nominate_new_words, _gate_and_admit,
    follow-ups, ordering,      attempt, record_speed_round_   _insert_ladder_rows, _admit_extra_new_words)
    hydration)                 attempt, FSRS)
                      \________ constants.py (tunables, _settled / _unwrap) ________/
```

`practice_session_service.py` re-exports every public name of `constants.py` (`from services.practice.constants import *`), so `services.study_time` and `services.study_session.session` import `PRACTICE_ATTEMPT_MAX_SECONDS`, `PRESTUDY_FOLLOWUPS_PER_SESSION`, `PRESTUDY_FOLLOWUP_EXPECTED_SECONDS` and `routes/practice.py` imports `EXTRA_NEW_WORDS_MAX` from there. It also imports `services.study_plan_service as _plan` (tests read it as `pss._plan`). `services/practice/__init__.py` is a docstring only. Line counts at `review/integration`: `session_assembly.py` 913, `new_word_admission.py` 1226, `attempt_recording.py` 436, `constants.py` 134.

The package was split out of `services/exercise_session_service.py` (deleted 2026-11-14); `routes/exercises.py` was deleted the same day. The service holds no per-request state except what `services/request_cache.py` stores for the current Flask request (`new_word_state`, `daily_load_row`).

## Module map

### `services/practice_session_service.py`
- `class PracticeSessionService(SessionAssemblyMixin, AttemptRecordingMixin, NewWordAdmissionMixin)`; `__init__(db=None)` sets `self.db`.
- `get_practice_session_service() -> PracticeSessionService`: process-wide singleton; also called at start-up in `app.py` (warm-up).
- **Called by:** `routes/practice.py` (`_service()`), `routes/study_session.py` (`_practice_service()`), `routes/tests/prestudy.py` (prestudy admission and evidence), `services/study_session/session.py` (constants), `services/study_time.py` (constant).

### `services/practice/constants.py`
Tunables and two helpers. Values at `review/integration`:

| Name | Value | Used by |
|---|---|---|
| `LADDER_TOPUP_MAX_PER_CALL` | 12 | cap on words admitted per intake call |
| `EXTRA_NEW_WORDS_MAX` | 10 | max new words in one extra round (`routes/practice.py` validates) |
| `EXTRA_REVIEW_ITEMS` | 10 | review items per extra round |
| `EXTRA_REVIEW_RECENT_MINUTES` | 10 | review-ahead keeps just-attempted senses out |
| `LADDER_ELIGIBLE_STATES` | `new, active, gated, pre_mastery, relearning` | pool count |
| `LADDER_MIN_EXERCISES_PER_SENSE` | 3 | supply gate |
| `LADDER_EVIDENCE_MIN_COUNT` | 2 | A1 evidence threshold |
| `LADDER_EVIDENCE_P_KNOWN_MAX` | 0.40 | A1 "confident unknown" |
| `NOMINATION_OVERFETCH` | 20 | candidates examined per wanted word (drill off) |
| `SUPPLY_GATE_CHUNK` / `SUPPLY_GATE_ROW_LIMIT` | 100 / 10000 | supply and veto query chunking |
| `EVIDENCE_ROW_LIMIT` / `WRONG_ANSWER_ROW_LIMIT` / `LADDER_SUBSCRIBED_ROW_LIMIT` | 2000 / 5000 / 5000 | row ceilings |
| `RECENT_TEST_WINDOW_DAYS` | `Config.RECENT_TEST_WINDOW_DAYS` else 28 | A1 recency |
| `RECENT_TEST_ROW_LIMIT` / `RECENT_TEST_CHUNK` | 1000 / 100 | A1 reads |
| `CALIBRATION_EVIDENCE_MAX_AGE_DAYS` | `Config` else 90 | A2 / A2r recency |
| `CALIBRATION_ROW_LIMIT` | 500 | calibration reads (placement reads use 4x) |
| `DEMAND_GENERATION_MAX_PER_CALL` | 5 | starved senses queued per call |
| `PRACTICE_SESSION_MIN_ITEMS` | 20 | session floor |
| `PRESTUDY_FOLLOWUPS_PER_SESSION` / `PRESTUDY_FOLLOWUP_EXPECTED_SECONDS` | 5 / 30 | follow-up injection |
| `PRACTICE_ATTEMPT_MAX_SECONDS` / `DEFAULT_EXPECTED_SECONDS` | 300 / 45 | credited seconds |

`_settled(fn)` wraps a callable so it returns `(value, error)` instead of raising; `_unwrap((value, error))` re-raises. They let reads started in `run_parallel` fail where their result is used. The removed `ATTEMPT_RPC_ENV_FLAG` / `PRACTICE_ATTEMPT_RPC_ENABLED` and the "not deployed" probe no longer exist (2026-11-23).

### `services/practice/session_assembly.py` — `SessionAssemblyMixin`
Public: `get_session(user_id, language_id, mode='auto', target_minutes=15, user_theta=None, debug=False, tail=False) -> dict`, `get_extra_round(user_id, language_id, reviews, new_words, exclude_sense_ids=None) -> dict`. Private helpers: `_practice_session_rpc`, `_inject_prestudy_followups`, `_apply_session_floor`, `_order_items` (`_unstarted_first`, `_most_overdue_first`), `_hydrate_items`, `_prepare_jumbled_items` (static), `_apply_script_variant`, `_exercise_preferences`, `_interleave_extras`, `_extra_acquisition_minutes`, `_extra_acquisition_items`, `_extra_review_items`. Module function `_lacks_content(item)`. **Called by** `routes/practice.py` (`/session`, `/extra`).

#### Session-assembly stages (`get_session`)
Error returns (dict with `error` and `code`): `invalid_mode` / `E_MODE`, `target_minutes_out_of_range` / `E_RANGE`; `rpc_failed` / `E_RPC` (detail = exception text) and `malformed_response` / `E_SHAPE` when the session RPC fails or returns a non-dict. An RPC payload containing `error` is returned unchanged. The route maps `E_LANG`, `E_MODE`, `E_RANGE` to 400 and everything else to 500.

1. **Intake pre-step** (modes `acquisition`, `auto`): `_maybe_top_up_ladder` -> `admit_daily_new_words(...)['admitted']`; the result is returned as `cold_subscribed` when non-empty. Exceptions are logged and ignored.
2. **Parallel reads** (`run_parallel` of `_settled` callables): the `get_practice_session` RPC (always; args `p_user_id, p_language_id, p_mode, p_target_minutes, p_user_theta` plus `**store.rpc_content_args()` = `p_include_content: false`); `prestudy.due_followup_senses(db, user, language, today, limit=PRESTUDY_FOLLOWUPS_PER_SESSION)` when `mode` is `maintenance` or `auto` and not `tail`; `intro_drill.intro_sense_ids` when the drill is enabled; `_exercise_preferences` when the language is in `script_serving.SCRIPT_VARIANT_LANGUAGES` (`(1,)`, Chinese).
3. **Floor** (`acquisition`, `auto`): `_apply_session_floor`. If fewer than 20 items and not an empty session, calls the RPC again with `mode='maintenance'` and the same minutes, appends up to the deficit of items with unseen `exercise_id`, sets each `mode='maintenance'`, adds `floor_backfilled`, clears `no_content_reason`.
4. **Prestudy follow-ups** (`maintenance`, `auto`, not tail): `_inject_prestudy_followups`: one exercise per due sense not already in the session (lowest `ladder_level` active exercise), item fields `mode='maintenance'`, `prestudy_followup=True`, `content_version`; marks `served_at` via `prestudy.mark_followups`.
5. **New-word drill** (when `intro_drill.ENABLED`): `route_untaught` (ADR-046; sets `untaught_routed`), drop items whose sense is an intro sense, `block_for_session` -> `payload['intro_drill']` (clears `no_content_reason`).
6. **Ordering**: `_order_items`: acquisition items grouped by sense and sorted so never-attempted admitted words come first in admission order (`new_word_state.unstarted_sense_ids`); maintenance items most overdue first (earliest `user_flashcards.due_date` / `user_word_ladder.review_due_at`; two parallel reads).
7. `tail` echoed as `payload['tail'] = True`; `score_breakdown` stripped unless `debug`.
8. **Hydration** (ADR-049): `_hydrate_items` = one `store.hydrate(items, language_id, id_key='exercise_id', sense_key='sense_id')`; items with no content are dropped, `no_content_reason='content_unavailable'` if that empties the list.
9. **Script variant** (Chinese Traditional preference) then **jumbled preparation** (`prepare_jumbled_content` for `jumbled_sentence` items).
10. **DT error cards**: `dual_translation.cards.select_error_exercises_for_practice(db, user, language_id=, normal_item_count=)` interleaved by `_interleave_extras`; `error_cards_injected`.

Every step after the RPC is wrapped so its failure is logged and the session is still returned.

#### Extra rounds (`get_extra_round`)
`new_words` clamped to 0..`EXTRA_NEW_WORDS_MAX`; `{'error': 'nothing_requested', 'code': 'E_EMPTY'}` if no reviews and no new words. New words: `_admit_extra_new_words`; then acquisition and maintenance RPC calls run in parallel; reviews = prestudy follow-ups, then due maintenance items, then `get_review_ahead_items` top-up, at most `EXTRA_REVIEW_ITEMS`. Attempts from an extra round are posted with `is_tail = true`. Payload gains `extra: {requested_new_words, new_words_served, new_words_admitted, new_words_beyond_quota, reviews_served}`. See [[features/practice-extra-rounds.tech]].

### `services/practice/attempt_recording.py` — `AttemptRecordingMixin`
Public: `record_attempt_with_updates(user_id, exercise_id, is_correct, user_response=None, time_taken_ms=None, session_mode=None, language_id=None, expected_seconds=None, is_tail=False, exercise_context='standard')`, `record_prestudy_exercise_attempt(user_id, exercise, is_correct, user_response=None)`, `record_speed_round_attempt(user_id, exercise_id, is_correct, time_taken_ms=None, timed_out=False)`. Private: `_report_ladder_progress`, `_capture_knowledge_outcome`, `_effective_practice_seconds` (static), `_update_fsrs_for_exercise`, `_read_fsrs_card`, `_apply_fsrs_review`, `_apply_lapse_penalty`. **Called by** `routes/practice.py` (`POST /attempt`) and `routes/tests/prestudy.py` (`record_prestudy_exercise_attempt`).

#### Attempt-recording flow (the only path since 2026-11-23)
1. Route: `exercise_id` and `is_correct` required; `virtual-*` ids return success without recording; gate / stress markers are rejected (they use `/api/vocab-dojo/gate` and `/stress-test`); `session_mode` must be `acquisition`, `maintenance` or absent; `cloze_typed` is re-graded server-side (fails open); `is_speed_round` goes to `record_speed_round_attempt`; `time_taken_ms` goes through `services.attempt_timing.clamp_time_taken_ms`.
2. `record_attempt_with_updates` calls `record_exercise_attempt` once (full contract, step table, return shape and call counts in [[features/practice-engine.tech]]); then, in Python, rates the returned `flashcard` row with `fsrs.schedule_review` (AGAIN if wrong; EASY if correct and `time_taken_ms < 5000`; else GOOD), writes `user_flashcards`, and on a lapse calls `bkt_apply_lapse_penalty`; then `_report_ladder_progress` sets `result['ladder']` and may call `intro_drill.restart_if_demoted`.
3. Error handling: RPC exception -> propagates, the route's `api_errors` answers with the normal failure envelope and nothing is written; `{error:'exercise_not_found'}` -> `{'error': 'Exercise not found'}` -> 500. FSRS and lapse-penalty failures are logged and never raised.
4. Concurrency: the RPC takes `pg_advisory_xact_lock(hashtextextended(user_id || ':' || exercise_id, 0))` before the first-attempt check, so two simultaneous submissions cannot both be `is_first_attempt`.
5. Database calls per answer from Python: 2 (RPC + card update) with a flashcard, 1 without a card or without a sense; +1 on a lapse; the intro-restart check adds reads only after a ladder demotion. (Before: 12 / 10 / 9 / 5.)

### `services/practice/new_word_admission.py` — `NewWordAdmissionMixin`
Public: `new_word_state(user_id, language_id)`, `admit_daily_new_words(user_id, language_id) -> {'admitted': [...], 'needs_rebuild': bool}`. Internal entry points used elsewhere: `_maybe_top_up_ladder` (from `get_session`), `_admit_extra_new_words` (from `get_extra_round`), `_nominate_new_words`, `_insert_ladder_rows`, `_unstarted_sense_ids`. **Called by** `services/study_session/session.py` (`admit_daily_new_words`, `new_word_state`), `services/intro_drill.py` (`new_word_state`, `_insert_ladder_rows` indirectly via prestudy admission), `session_assembly.py`.

#### New-word state (`_new_word_state`, memoised per request)
Reads the plan row (`day_boundary.plan_row`): `new_words_per_day` (npd), `weekday_shape`, `timezone`, `excluded_modules`. Quota `Q = _plan.new_words_for_day(npd, weekday weight)`. One call to bundle RPC `new_word_state_inputs(p_user_id, p_language_id, p_date, p_day_start, p_with_governor)` through `optional_rpc.call_bundle` (falls back to `review_governor_state` via `_plan.get_review_governor` plus `ladder_new_word_state`). Governor skipped (`level: normal`) when `'practice'` is in `excluded_modules`. `E = _plan.effective_new_words(Q, level)`. Returns `{timezone, excluded, quota, effective, level, governor, unstarted, started_today, unstarted_sense_ids}` or `None` (no plan row, failed read; never cached; callers admit nothing). `request_cache.invalidate('new_word_state', user_id)` after any write to `user_word_ladder`.

#### Admission (`_admit_daily_new_words`)
`want_raw = E - (unstarted + started_today)`; `want = min(max(want_raw, 0), 12)`; nothing if `E <= 0` or `want <= 0`. In parallel: `_eligible_ladder_count` (side effect: generation requests for subscribed-but-unservable senses), `_today_supply_flags` (reads `daily_test_loads.daily_session_targets`: `new_words_supply_checked`, `new_words_in_budget`, `new_words_supply_checked_e`; a check made under a different E counts as unchecked), `_subscribed_sense_ids`. Then `_nominate_new_words`, `_insert_ladder_rows` (insert failure returns empty), `set_new_words_shortfall(p_user_id, p_language_id, p_date, p_shortfall = max(0, want_raw - admitted), p_checked_e = E)`; `needs_rebuild` is true once per day when Tier C planned more in-budget words than `min(E, unstarted + started_today + admitted)` can serve. Never raises.

#### Nomination queues (`_nominate_new_words`)
Reads in parallel: `_recent_test_sense_ids`, `_wrong_answer_sense_counts`, `_calibration_ledger`, `_evidence_rows`, `_placement_ledger`. Order, each queue consulted only if earlier ones left `want` unmet, every queue through `_gate_and_admit`:

| Queue | Source | Rule | Known / probably_known veto |
|---|---|---|---|
| **A1** recent tests | `_evidence_candidates(recency_first=True)` restricted to senses carried by tests the learner took in the last 28 days (`test_attempts` -> `tests.vocab_sense_ids` and `questions.sense_ids`) | evidence (after subtracting calibration `cal_n` and placement writes) >= 2, or p_known <= 0.40, or >= 2 distinct missed questions carrying the sense; calibration-only or placement-only evidence is dropped; ranked by latest evidence, wrong count, then Zipf | **None (known issue)**: `_evidence_rows` selects rows with status unknown/learning OR `word_test_wrong > 0` OR `comprehension_wrong > 0`, so known words with misses qualify |
| **A2** calibration + placement misses | `_calibration_wrong_candidates`: senses whose latest applied definition-mode calibration answer (including an explicit skip) was wrong within 90 days; plus `_placement_candidates` A2 list (placement meaning missed) | one wrong answer suffices; ranked by Zipf then recency | **Yes**, fail closed (read failure returns nothing) |
| **A2r** placement reading misses | `_placement_candidates` second list: meaning right but reading not right (zh: any answer but the key, tones included) | alternates with A2 in one list via `_interleave(a2 + placement_a2, a2r)` | **Yes**, fail closed |
| **B** lookahead | `_nominate_from_lookahead` | stub returning `[]` until [[features/lookahead-preteaching]] ships | n/a |

Placement (ADR-059, [[features/vocab-placement]]): `_placement_ledger` reads `calibration_responses` of sessions with `mode='placement'`, the learner's word language and `bkt_applied_at` set (scored items only, no probes), and returns `{'a2': {vocab_id: last_at}, 'a2r': {...}, 'written': {sense_id: n}}`; placement words map to the word's own-language rank-1 `standard` sense (`_native_rank1_senses`). Placement evidence writes raise `evidence_count` on the anchor row, so A1 subtracts `written` to avoid counting them as test evidence. Fails soft to empty dicts.

#### Supply gate (`_gate_and_admit(candidates, want, language_id)`)
`head = candidates[:max(want * 20, want)]`.
- **Drill on** (`intro_drill.ENABLED`, `Config.NEW_WORD_DRILL_ENABLED`, default true): `admitted = head[:want]`; `supplied = _senses_with_supply(admitted, language_id)`; `starved = admitted - supplied`. The supply check therefore reads only the admitted senses: **one `exercises` query for any batch size** (chunked at 100; the cap on a daily call is 12, an extra round 10). Previously it ran over the whole overfetched head (2 queries at 10 words, 3 at 15). Starved words are still admitted and sent to generation.
- **Drill off**: `supplied = _senses_with_supply(head)`; `admitted = head ∩ supplied`; `starved = head - supplied`.
- `_senses_with_supply`: a sense passes with >= 3 active exercises in the learner's language; fails closed (returns empty on a read error).
- `_request_generation(starved, language_id)` enqueues up to 5 per call in `generation_queue` through `queue_drain.enqueue(... REASON_SUBSCRIBE_TOPUP, detail={'source': 'evidence_queue'})`; best effort.
Returns `admitted[:want]`.

`_insert_ladder_rows` inserts `user_word_ladder` rows (`word_state='new'`, ring 1, `family_confidence` 0.10 in six families, `review_due_at = now`), with `intro_drill.new_intro_fields(today)` when the drill is enabled; it invalidates `new_word_state` in a `finally`. `_admit_extra_new_words` ignores the quota and writes no shortfall; it uses already admitted unstarted words first, nominates `want = n - len(unstarted)` more, and promotes never-started `word_state='new'` rows into intro session 1.

## Database Impact

Tables read and written are listed under dependencies; schema in [[database/schema.tech]], RPC contracts in [[api/rpcs.tech]] and [[database/rpcs.tech]]. Writes from this package: `user_word_ladder` (insert, intro promotion), `daily_test_loads` via `set_new_words_shortfall`, `generation_queue` via `enqueue`, `exercise_attempts`/`exercises`/`user_vocabulary_knowledge`/ladder/ledger/plan via `record_exercise_attempt`, `user_flashcards` (FSRS), `prestudy_followups` (`served_at`).

## API / RPC Surface

HTTP routes using this package (`routes/practice.py`, prefix `/api/practice`):

| Route | Calls |
|---|---|
| `GET /session` (`language_id`, `mode`, `minutes` 1-180, `debug`, `tail`) | `get_session` |
| `GET /extra` (`reviews`, `new_words` 0-10, `exclude`) | `get_extra_round` |
| `POST /attempt` | `record_attempt_with_updates` / `record_speed_round_attempt` |
| `GET /speed-round` | `vocabulary_ladder.speed_round` (not this package) |
| `POST /intro/complete` | `intro_drill.complete_word` |

All require `@supabase_jwt_required`. `user_id` always comes from `g.current_user_id`.

## Key Architectural Decisions

1. **Decision:** one SQL function records an attempt; FSRS stays in Python. **Rationale:** 12 round trips down to 2, and the per-user-and-exercise advisory lock closes the double-first-attempt race; `fsrs_schedule_review` in SQL is not an exact port of `services/vocabulary/fsrs.py`. **Alternatives rejected:** keeping the Python path behind an env flag (deleted: two paths drift); porting FSRS to SQL.
2. **Decision:** mixins composed in one service class. **Rationale:** the old file was one 2,000-line class; tests patch the service's methods. **Alternatives rejected:** free functions (every caller would need `db`).
3. **Decision:** post-RPC assembly steps are best effort and never fail the session; the content hydration step drops items instead. **Rationale:** a learner should get a session.

## Security Considerations

- All writes use the service-role client; `record_exercise_attempt` is `REVOKE`d from `PUBLIC`, `anon`, `authenticated` and granted to `service_role` only.
- `user_id` is never accepted from the client. `exercise_id` ownership is not checked (an attempt is always recorded for the caller).
- The typed-answer verdict is decided on the server for `cloze_typed`.

## Testing Strategy

Existing tests at `review/integration`: `tests/test_practice_attempt_recording.py`, `test_practice_ladder_progress.py`, `test_practice_session_floor.py`, `test_practice_session_reads.py`, `test_practice_session_budget.py`, `test_practice_extra_rounds.py`, `test_practice_route_tail.py`, `test_practice_error_card_injection.py`, `test_ladder_new_word_quota.py`, `test_new_word_admission_gate.py`, `test_placement_admission.py`, `test_intro_drill.py`. Gaps to cover: a test that pins the A1 behaviour for a known word (so the decision on the open question is explicit), and a database test for the advisory lock under two concurrent calls.

## Related Pages

- [[features/practice-package]] — plain-English counterpart
- [[features/practice-engine.tech]] — RPC, scoring, hydration, attempt-recording contract
- [[features/new-word-drill.tech]] — the drill and the open known-word question
- [[features/study-session-package.tech]] — the caller that builds the daily queue
- [[features/session-budget-settings.tech]] — quota, governor, tail
- [[features/practice-extra-rounds.tech]]
- [[features/test-prestudy.tech]]
- [[decisions/ADR-049-exercise-content-in-storage]], [[decisions/ADR-046-untaught-words-start-the-drill]], [[decisions/ADR-047-basic-word-knowledge-prior]], [[decisions/ADR-041-practice-moves-the-ladder]]
