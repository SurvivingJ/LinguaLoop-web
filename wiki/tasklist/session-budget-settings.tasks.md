---
title: "Session Budget Settings — Task Breakdown"
feature: session-budget-settings
prose_page: ../features/session-budget-settings.md
tech_page: ../features/session-budget-settings.tech.md
total_tasks: 5
done: 5
---

# Session Budget Settings — Task Breakdown

Implements the new-word quota, optional tail, review governor, calibration evidence and budget scope per
[[features/session-budget-settings.tech]] and [[decisions/ADR-033-budget-scope-and-new-word-budget]] (Revision 2026-10-13 (b)).
These tasks extend the schema, Tier B, Tier C, API and UI tasks that live in [[tasklist/session-modules.tasks]] (TASK-863–869,
amended 2026-10-13 and again in revision (b)). Critical path: 863 → 874 → 865 + (870 → 864) → 871 → 866 → 868. TASK-865 needs the
governor SQL helpers from 874; 871 needs 864 (`new_words_for_day`, `effective_new_words`), 865 (`set_new_words_shortfall`) and 874
(`get_review_governor`); 864 itself waits on 870 and 874. TASK-872 can run in parallel with 870 after 863 (its tail-route half needs 874
and 871). TASK-873 needs 871 for the nomination function; its evidence-writing half is independent.

## Open Questions

- **ANSWERED 2026-10-13:** the `new_words_per_day` backfill `max(1, daily_minutes // 6)` is **per day** (5/day at 30 min), about 7x
  the old per-week reading of `target_new_rate()` (`study_plan_service.py` lines 86-88); accepted knowingly. TASK-874's forecast and
  governor manage the consequence.
- **ANSWERED 2026-10-13:** cold start = 4A + 4B (intro-test evidence, plus calibration BKT evidence at `/end`, TASK-873). No starter queue.
- **ANSWERED 2026-10-13:** layout of the Daily session card = Option A (TASK-868).
- **ANSWERED 2026-10-13:** Vocabulary review off with `new_words_per_day > 0` is allowed (the API does not reject it); all new words go to the optional
  tail; the settings page warns `study_plan.session.new_words_no_review_warning` (TASK-868).
- **ANSWERED 2026-10-13:** Anki-like quota. `new_words_per_day` counts words **started** per local day. Started = the sense's first-ever `exercise_attempts` row
  (`MIN(created_at)` per user and `sense_id`; `user_word_ladder` has only the admission `created_at`). Admitted-but-unstarted words carry over, are served first,
  and intake tops up `(unstarted + started today)` to the effective quota (TASK-871, TASK-872, TASK-865). The old rollover rule is removed.
- **ANSWERED 2026-10-13:** `review_item_seconds` is the median over all timed vocabulary-exercise attempts (no review-only filter) in v1; the forecast is labelled an estimate.
- **ANSWERED 2026-10-13:** an explicit calibration skip (`chosen_sense_id IS NULL`, `is_correct = false`, `answered_at` set) is wrong evidence; unanswered items
  (`answered_at IS NULL`) are ignored (TASK-873).
- **OPEN:** `REVIEWS_PER_NEW_WORD_30D = 7` and the steady-state forecast formula.
- **OPEN:** other tunables without data (`RECENT_TEST_WINDOW_DAYS`, `REVIEW_PRESSURE_OFFSET`, `NEW_WORD_MINUTES_DEFAULT`,
  `REVIEW_BACKLOG_THRESHOLD_DAYS`, `REVIEW_ALLOWANCE_FLOOR_MIN`, `REVIEW_ITEM_SECONDS_DEFAULT`, `TAIL_OFFER_MAX_MIN`,
  `CALIBRATION_EVIDENCE_MAX_AGE_DAYS`), listed in the tech spec frontmatter.

---

## TASK-870: Per-language `minutes_per_new_word` estimate

**Status:** [x] Done (code complete 2026-10-13; migrations not yet applied live)
**Feature:** session-budget-settings
**Type:** feature
**Complexity:** S (1-3h)
**Depends On:** TASK-863

**Description:**
Compute how many minutes one new word costs on day one, per language, so Tier B/C can turn
`new_words_per_day` into minutes. The estimate is (exercise attempts per new word in the first 24
hours after the ladder row is created) × (median `COALESCE(expected_seconds_p50, expected_seconds)`
of those attempts) / 60. It is computed by the new SQL RPC `refresh_new_word_minutes()`, called from
the existing `_refresh_exercise_time_estimates` job after `refresh_practice_time_estimates`, and is
stored on `dim_languages.new_word_minutes_est` (column added by TASK-863). Readers fall back to
`Config.NEW_WORD_MINUTES_DEFAULT` when it is NULL.

**Acceptance Criteria:**
- [x] `Config.NEW_WORD_MINUTES_DEFAULT = 3.0` exists and is used when a language has no usable
      acquisition-item timing data
- [x] New `migrations/new_word_minutes_estimate.sql` defines `public.refresh_new_word_minutes()
      RETURNS jsonb` (service-role only). Per `dim_languages` row: `W` = `user_word_ladder` rows created
      in the last 30 days whose sense belongs to the language; `items_w` = that user's
      `exercise_attempts` on the sense with `created_at` in `[w.created_at, w.created_at + 24 hours)`;
      require at least 10 words with `items_w >= 1`, else leave the column unchanged;
      `new_word_minutes_est = LEAST(15.0, GREATEST(0.5, ROUND(AVG(items_w) · percentile_cont(0.5) of
      COALESCE(det.expected_seconds_p50, det.expected_seconds) / 60.0, 2)))`; returns
      `{languages_updated: int}`
- [x] `_refresh_exercise_time_estimates` (`services/study_plan_service.py`, line 678) calls the RPC after
      `refresh_practice_time_estimates` succeeds, merges `languages_updated` into its summary and logs it
- [x] `get_minutes_per_new_word(db, language_id) -> float` in `services/study_plan_service.py` reads
      `dim_languages.new_word_minutes_est` (single-row lookup, no join) and returns
      `Config.NEW_WORD_MINUTES_DEFAULT` when the row or value is missing or the read fails; it is used by
      Tier B (TASK-864) and `GET /api/study-plan` (TASK-866)
- [x] A language with too little data keeps NULL and so reads as the default, never 0 or NaN
- [x] Unit test: known items-per-word and expected_seconds produce the expected minutes (including the
      0.5 / 15.0 clamps and the 10-word minimum); a NULL column produces 3.0

**Technical Notes:**
`_refresh_exercise_time_estimates` exists in `services/study_plan_service.py` (verified by grep; also
referenced from `app.py`) and currently refreshes exercise-type and test-type timing. `expected_seconds`
is a field on the exercise-type registry (`dim_exercise_types.expected_seconds` per
[[database/schema.tech]]). `Config.NEW_WORD_MINUTES_DEFAULT` does **not** exist yet and must be
added to the config module. Storage is decided: a column on `dim_languages`
(`new_word_minutes_est numeric(4,2)`, 0.5..15.0), added by TASK-863, with precedent in
`dim_exercise_types.expected_seconds_p50`; a separate table was rejected (see Migration 3 in
[[features/session-budget-settings.tech]]). The 24-hour window (not the local day) avoids a per-row
timezone join and is a documented approximation. Live engagement is thin, so the 3.0 default will
apply for a long time. The SQL `new_word_minutes` helper that mirrors the default is defined in
TASK-863's migration; a test pins `Config.NEW_WORD_MINUTES_DEFAULT` against it.

**Files to Create / Modify:**
- `config.py` (or the project's Config module) — add `NEW_WORD_MINUTES_DEFAULT`
- `migrations/new_word_minutes_estimate.sql` — new
- `services/study_plan_service.py` — extend `_refresh_exercise_time_estimates`, add `get_minutes_per_new_word`
- `tests/test_new_word_minutes.py` — new, cases above

**Verification:**
`pytest tests/test_new_word_minutes.py -q` passes; running the job against a dev DB logs a
per-language `minutes_per_new_word`.

---

## TASK-871: Ladder intake rework — per-local-day governed new-word quota

**Status:** [x] Done (code complete 2026-10-13; migrations not yet applied live)
**Feature:** session-budget-settings
**Type:** refactor
**Complexity:** M (3-8h)
**Depends On:** TASK-863, TASK-864, TASK-865, TASK-874

**Description:**
Replace the pool-floor trigger of the ladder top-up with a per-local-day quota driven by
`new_words_for_day(new_words_per_day, weekday weight)` reduced by the review-load governor, read from the plan (not from
`daily_session_targets`). Admit enough words to meet today's governed quota, choosing candidates from recent-test and word-quiz
unknowns first (Queue A1), then calibration wrongs (A2, TASK-873 supplies the evidence), then lookahead pre-teaching cohorts once that
feature ships (Queue B). Record any shortfall, request generation when the supply gate starves, and ask for one same-day rebuild when
fewer words can be served than Tier C planned inside the budget.

**Acceptance Criteria:**
- [x] New `local_day_start_utc(tz_name, now=None) -> datetime` in `services/day_boundary.py` (the
      module has `resolve_zone`, `local_date`, `plan_timezone`, `plan_today`, `plan_today_iso` but no such helper): UTC
      instant of 00:00 on the learner's current local date, falling back to UTC on a bad zone
- [x] New public `admit_daily_new_words(user_id, language_id) -> {'admitted': [...], 'needs_rebuild': bool}`; `_maybe_top_up_ladder` delegates to
      the same body. It reads `new_words_per_day`, `weekday_shape`, `timezone`, `excluded_modules` in one plan query
      (no plan row or read failure → `[]`); `quota = new_words_for_day(npd, shape[local_today.weekday()])` using the shared helper from TASK-864;
      `new_today = effective_new_words(quota, get_review_governor(...)['level'])` (TASK-874; level `normal` when `practice` is excluded);
      `new_today <= 0` → `[]`
- [x] Quota state (Anki-like, replaces the old `admitted_today` count; no rollover rule): `st = db.rpc('ladder_new_word_state', {p_user_id, p_language_id, p_day_start: local_day_start_utc(tz).isoformat()})`
      (defined in TASK-874's `review_governor.sql`); `U = st['unstarted']` (ladder rows of the user and language that are servable and still startable: `word_state IN ('new','active','gated','pre_mastery','relearning')`, no `exercise_attempts` row by `sense_id` OR via `exercise_id → exercises.word_sense_id` (legacy NULL `sense_id`), >= `LADDER_MIN_EXERCISES_PER_SENSE` (3) active exercises in the language, admitted within the last 14 days; review fix 2026-10-14), `ST = st['started_today']`
      (rows whose `MIN(exercise_attempts.created_at) >= local_day_start_utc(tz)`, admitted today or earlier). Started = first-ever attempt, any outcome, retries do not matter. RPC failure → `[]`
- [x] `want_raw = new_today − (U + ST)`; `want = min(max(want_raw, 0), LADDER_TOPUP_MAX_PER_CALL)`; `want <= 0` → `[]`; admitted-but-unstarted words from earlier days
      carry over, are counted in `U` and so reduce intake one for one; `LADDER_TOPUP_MAX_PER_CALL` (12) stays as a per-call safety cap
- [x] Acquisition serving takes `st['unstarted_sense_ids']` (oldest `user_word_ladder.created_at` first) before any sense whose ladder is already in progress
      (`get_session(mode='acquisition')` and the tail acquisition chunks)
- [x] The pool-floor trigger is removed: a large existing pool no longer suppresses admission
- [x] Nomination (`_nominate_new_words`): **Queue A1** = unknown words from recent tests and word quizzes, via
      `_recent_test_sense_ids` (`test_attempts` within `RECENT_TEST_WINDOW_DAYS = 28`, limit
      `RECENT_TEST_ROW_LIMIT = 1000`, unioning `tests.vocab_sense_ids` and `questions.sense_ids` in chunks
      of `RECENT_TEST_CHUNK = 100`; a failed read returns an empty set) intersected with
      `_evidence_candidates(..., recency_first=True)` (new keyword: most-recent `last_evidence_at`
      first, then wrong count, then frequency; evidence thresholds `LADDER_EVIDENCE_MIN_COUNT` /
      `LADDER_EVIDENCE_P_KNOWN_MAX` unchanged); then **Queue A2** = `_calibration_wrong_candidates` (implemented in TASK-873; until it ships it
      returns `[]`), called only if A1 did not fill `want`; then **Queue B** = `_nominate_from_lookahead` stub
      returning `[]` until [[features/lookahead-preteaching]] ships, called only if A1 and A2 did not fill `want`. Order: test + word-quiz unknowns →
      calibration wrongs → Queue B pre-teaching
- [x] All queues go through one extracted `_gate_and_admit(candidates, want, language_id)`: overfetch
      (`want · NOMINATION_OVERFETCH`), `_senses_with_supply` (>= `LADDER_MIN_EXERCISES_PER_SENSE`),
      `_request_generation` for the starved (cap `DEMAND_GENERATION_MAX_PER_CALL`), return `admitted[:want]`
- [x] `shortfall = max(0, want_raw − len(fresh))` is written best-effort through
      `set_new_words_shortfall(user, language, plan_today_iso(...), shortfall)` (defined in TASK-865; also sets `new_words_supply_checked = true`;
      WARNING on failure, never raise)
- [x] `needs_rebuild` is true only when `daily_session_targets.new_words_supply_checked` was false before this call and
      `new_words_in_budget > min(new_today, U + ST + len(fresh))`; `GET /api/study-session` calls `admit_daily_new_words` best-effort before reading `targets` and calls
      `StudyPlanService.rebuild_today` once when `needs_rebuild` (the supply flag prevents a second rebuild)
- [x] `_eligible_ladder_count` is still called once, only for its side effect of requesting
      generation for subscribed-but-unservable rows and for the log line; it no longer gates intake and
      `target_active_pool` is no longer read
- [x] When candidates are starved, `_request_generation` is called for the missing senses
- [x] Cold start (4A): a learner with one introductory test whose questions carry `sense_ids` and whose wrong answers meet `LADDER_EVIDENCE_MIN_COUNT`
      gets Queue A1 nominations; a learner with calibration data only is covered by TASK-873 (A2) and, before that task ships, yields no nominations and
      `_nominate_from_lookahead` is consulted (all covered in `tests/test_ladder_new_word_quota.py`)
- [ ] Data check recorded in the task notes before rollout: the share of introductory tests (those the
      recommender serves right after calibration) with non-empty `tests.vocab_sense_ids`; tests below
      full coverage are queued for the test-sense-linking skill
- [x] `new_words_per_day = 0`, a governor `paused` level, and rest days admit nothing; a `reduced` level halves (floor) the quota
- [x] `tests/test_ladder_new_word_quota.py` (new) covers: the quota resets at **local** midnight
      (`Asia/Tokyo`, a UTC instant just before and after Tokyo midnight); `want_raw = new_today − (U + ST)` with the governor at each level; 3 unstarted carried-over
      words and `E = 5` admit 2; after the learner starts words, `ST` rises and intake stops at `U + ST = E`; a repeat call the same day admits 0; the cap; Queue A1 restricted
      to the window and recency-ranked; A2 consulted only when A1 is short; the Queue B stub; starved nominations reach `_request_generation`;
      `set_new_words_shortfall` called with the unmet count; `needs_rebuild` only on the first supply check; no plan, `npd = 0` and weight-0 days return
      `[]`; `local_day_start_utc` across a DST change and a bad zone name. `tests/test_ladder_topup.py` is
      updated for the removed pool-floor semantics

**Technical Notes:**
`_maybe_top_up_ladder` exists in `services/practice_session_service.py` (verified), as do
`LADDER_TOPUP_MAX_PER_CALL = 12`, `LADDER_EVIDENCE_MIN_COUNT = 2`, `LADDER_EVIDENCE_P_KNOWN_MAX = 0.40`
and `_request_generation`. `_evidence_candidates(self, user_id, language_id)` currently has no `recency_first` keyword (it sorts wrong count, recency,
frequency); add it. The code comment near line 61 already anticipates a per-calendar-day
quota based on `user_word_ladder.created_at` (task741). `RECENT_TEST_WINDOW_DAYS` does **not** exist
yet; add it next to the other ladder constants. `services/day_boundary.py` has no "local midnight as UTC timestamp" helper; `local_day_start_utc`
is new there (do not duplicate timezone math). `user_word_ladder` has no
`language_id` column of its own, so filter by language through the sense join, as the existing code
does. **Cold start (ANSWERED 2026-10-13, 4A + 4B):** no Queue C starter list. 4A is the introductory tests' evidence (A1). 4B is TASK-873: calibration
(definition mode) writes BKT evidence at `/end` and a single wrong calibration answer admits a sense to A2. The earlier finding that calibration wrote no
vocabulary evidence (only `calibration_*` tables, `user_calibration_state` and `user_skill_ratings`) is the **pre-TASK-873** state.

**Files to Create / Modify:**
- `services/practice_session_service.py` — rework `_maybe_top_up_ladder`, add `admit_daily_new_words`, `_nominate_new_words`, `_recent_test_sense_ids`, `_gate_and_admit`, constants
- `services/day_boundary.py` — add `local_day_start_utc`
- `routes/study_session.py` — call `admit_daily_new_words` and the one-off rebuild (shared edit with TASK-872)
- `tests/test_ladder_new_word_quota.py` — new
- `tests/test_ladder_topup.py` — update

**Verification:**
`pytest tests/test_ladder_new_word_quota.py tests/test_ladder_topup.py -q` passes. On a dev account with `new_words_per_day = 5` and
recent test misses, two `/api/study-session` loads in one local day admit 5 words in total, not 5
each. With 3 admitted-but-never-attempted words left from yesterday, the first load today admits only 2 more.

---

## TASK-872: Accrue `new_words_completed` and tail stats; serve the optional tail

**Status:** [x] Done (code complete 2026-10-13; migrations not yet applied live)
**Feature:** session-budget-settings
**Type:** feature
**Complexity:** M (3-8h)
**Depends On:** TASK-863, TASK-871, TASK-874

**Description:**
Count a new word toward the weekly `new_words_completed` on the local day it is **started**, i.e. the day of its first-ever `exercise_attempts` row for the
(user, sense), whether the word was admitted that day or earlier (ANSWERED 2026-10-13), count optional-tail work in `tail_completed_min` / `tail_new_words_completed`, and serve the optional tail from the session
route: after the required items are complete, `GET /api/study-session` returns a live `tail` summary and a `tail_queue` (reviews before new words,
most overdue first), and the session page asks "Session done — N reviews and M new words left today. Keep going?".

**Acceptance Criteria:**
- [x] New `migrations/new_words_completed_accrual.sql` redefines `record_session_progress` from its
      canonical source `migrations/task716_local_day_boundary.sql` (which superseded
      `phase18_practice_time_seconds.sql`): `DROP FUNCTION IF EXISTS` the 8-argument signature
      `(uuid, smallint, uuid, text, text, integer, integer, integer)`, then recreate with `p_sense_id bigint DEFAULT NULL` and
      `p_is_tail boolean DEFAULT false`; all existing logic carried forward verbatim
- [x] Inside the same `UPDATE`: when `p_kind = 'practice_acq'`, `p_sense_id IS NOT NULL`, the user has a
      `user_word_ladder` row for that sense, `(SELECT MIN(created_at) FROM public.exercise_attempts WHERE user_id = p_user_id AND sense_id = p_sense_id) >=
      public.plan_local_day_start(p_user_id, p_language_id)` (the current attempt is already inserted when `record_attempt_with_updates` calls the RPC), and
      `session_progress_log -> 'new_words'` does not contain `p_sense_id::text`:
      `new_words_completed + 1`, append the id to `session_progress_log['new_words']`, and `tail_new_words_completed + 1` when `p_is_tail`
      (idempotent per sense per week; the existing per-attempt dedupe returns first on a retried attempt). `'new_words'`
      is a reserved log key
- [x] When `p_is_tail` and `p_kind IN ('practice_acq','practice_maint')`, `tail_completed_min` grows by the same minutes added to
      `practice_completed_acq_min` / `practice_completed_maint_min`; tail work therefore also counts toward the weekly practice counters
- [x] New `plan_local_day_start(uuid, smallint) RETURNS timestamptz` in the same file:
      `plan_local_date(...)::timestamp AT TIME ZONE <user_study_plans.timezone, default 'UTC'>`
- [x] Review (`practice_maint`) attempts, later attempts on the same sense, and senses whose first-ever attempt was before today's local midnight do not increment
      `new_words_completed`; a word admitted days ago and first attempted today **does** increment it
- [x] Call site (`record_attempt_with_updates`, around line 585 of `services/practice_session_service.py`)
      passes `'p_sense_id': sense_id` (the exercise's `word_sense_id`) only when
      `session_mode == 'acquisition'` (maintenance passes `None`), and `'p_is_tail': True` when the practice session was requested with `tail=1`
      (the payload echoes `tail: true`; the client echoes it on the attempt POST)
- [x] `get_session(..., tail=True, mode='maintenance')` re-sorts the selected maintenance items most-overdue first (earliest `user_flashcards.due_date` /
      `user_word_ladder.review_due_at`); the main-session maintenance chunks use the same ordering
- [x] `GET /api/study-session` adds `governor`, `tail` and `tail_queue`: `tail` is non-null only when every non-`is_bonus` item of `queue` is complete and
      something is left (`reviews_left_items = governor.due_items`, 0 if `practice` excluded; `new_words_left = max(0, min(E − ST, U))` with `E` the effective quota and `U`, `ST` from `ladder_new_word_state` (TASK-871; `ST` counts carried-over words started today));
      `tail_queue` has `tail_maint_{k}` chunks before `tail_acq_{k}` chunks (`kind:'practice'`, `is_bonus:true`, `is_tail:true`, ≤10 min each, ≤ `TAIL_OFFER_MAX_MIN`
      = 20 min per round, `k` continues from completed tail ids so ids never collide); tail items are never in `queue`, so `progress` and session completion are unchanged
- [x] `_valid_block_ids` also accepts the current `tail_queue` ids, so `POST /api/study-session/complete-block` works for tail chunks
- [x] Session page (`templates/study_session.html`, `static/js/session/controller.js`, i18n en/zh/ja/es): after the last required item, if `tail` is not null the summary
      shows `session.tail.prompt` **"Session done — {n} reviews and {m} new words left today. Keep going?"** (variants `…_reviews_only`, `…_words_only`) with
      "Keep going" / "Done for today"; "Keep going" appends `tail_queue` and requests `/api/practice/session?...&tail=1`; after each round the controller re-fetches and asks
      again until `tail` is null. The governor banner shows `session.governor.paused` / `.reduced` ("New words paused — catching up on {n} reviews" / "reduced")
- [x] The stat tile reads `new_words_completed` / `new_words_target` and `tail_completed_min` from `GET /api/study-plan` `current_week` (TASK-866 / TASK-868)
- [x] SQL test (in `tests/sql/test_session_budget_settings.sql`): increments once per sense, only when the sense's first-ever attempt is on the local day (including a word
      admitted days earlier), not on a second attempt or a first attempt on an earlier day, tail columns only with `p_is_tail`, and a no-op on a retried attempt
- [x] `tests/test_study_session_tail.py` (new) covers the tail cases listed in the tech spec's Testing Strategy

**Technical Notes:**
`record_session_progress` is a SQL RPC (no Python definition). It is called from
`services/practice_session_service.py` (around line 585) and `routes/study_session.py`; the
canonical definition is `migrations/task716_local_day_boundary.sql` (see the `session_progress_log`
ledger in [[features/study-plans.tech]]). Confirm against the live `pg_get_functiondef` before
editing. Idempotency uses the sense's first-attempt time (`MIN(exercise_attempts.created_at)`) and the `session_progress_log['new_words']`
list; the full contract is Migration 4 and "Session route: optional tail" in [[features/session-budget-settings.tech]]. Precedent for an optional
appended block: the speed round (`is_bonus`, `build_session_queue` in `routes/study_session.py`), which credits no weekly counter; the tail differs in that
it **does** credit the practice counters. "Started" is defined once in [[features/session-budget-settings.tech]] ('Quota semantics'): a sense is started on the day of its first-ever `exercise_attempts` row
(`exercise_attempts.sense_id`, set by `record_attempt_with_updates`); rows with `sense_id IS NULL` predate `exercise_scheduling.sql` and are invisible (legacy words count as unstarted and are served first).
The maintenance selection RPC is not modified; the re-sort applies to the items it returns.

**Files to Create / Modify:**
- `migrations/new_words_completed_accrual.sql` — new; redefines `record_session_progress`, adds `plan_local_day_start`
- `services/practice_session_service.py` — pass `p_sense_id` / `p_is_tail`, `tail` handling and overdue-first ordering
- `routes/study_session.py` — `governor`, `tail`, `tail_queue`, valid tail block ids, `admit_daily_new_words` call
- `templates/study_session.html`, `static/js/session/controller.js`, `static/i18n/{en,zh,ja,es}.json` — tail prompt and governor banner
- `tests/sql/test_session_budget_settings.sql` — new (shared with TASK-865)
- `tests/test_study_session_tail.py` — new

**Verification:**
Run the SQL test against a branch or local DB; make a first acquisition attempt on a word (admitted today or on an earlier day) on the test account and confirm `weekly_plan_states.new_words_completed` is 1; a second attempt
on the same word leaves it at 1. On a dev account with 4 new words left after the main session, `/session` shows the "Keep going?" prompt and completing a
tail chunk raises `tail_completed_min`.

---

## TASK-873: Calibration BKT evidence + calibration-wrong admission (cold start 4B)

**Status:** [x] Done (code complete 2026-10-13; migrations not yet applied live)
**Feature:** session-budget-settings
**Type:** feature
**Complexity:** M (3-8h)
**Depends On:** TASK-871

**Description:**
Today calibration writes no vocabulary evidence. At `/api/calibration/end`, **definition mode only** (pronunciation excluded), send the answered anchor senses through
the existing batch RPC `update_vocabulary_from_word_tests_batch` so the learner's `user_vocabulary_knowledge` reflects what calibration showed. Then add the admission
rule: a **single wrong calibration answer** is enough to nominate a sense (Queue A2), bypassing `LADDER_EVIDENCE_MIN_COUNT` and `LADDER_EVIDENCE_P_KNOWN_MAX`, ranked **below**
test and word-quiz evidence (A1). Nomination order: recent-test + word-quiz unknowns → calibration wrongs → Queue B pre-teaching.

**Acceptance Criteria:**
- [x] New `migrations/calibration_bkt_evidence.sql`: `ALTER TABLE public.calibration_sessions ADD COLUMN IF NOT EXISTS bkt_applied_at timestamptz NULL` with a column COMMENT; idempotent.
      No change to `user_vocabulary_knowledge`
- [x] `calibration_service.end_session` (`services/calibration_service.py`, line 642), after the session is closed: if `mode == MODE_DEFINITION`, claim the write with
      `UPDATE calibration_sessions SET bkt_applied_at = now() WHERE id = :id AND bkt_applied_at IS NULL AND mode = 'definition' RETURNING id`; no row → do nothing (a second `/end` is a no-op)
- [x] When claimed: `results = [{'sense_id': anchor_sense_id, 'is_correct': bool(is_correct)}]` for `calibration_responses` of the session with the exact predicate `answered_at IS NOT NULL AND is_correct IS NOT NULL` (ANSWERED 2026-10-13). An explicit skip exists
      (`#calSkipBtn` "I don't know" in `templates/calibration.html` posts `position: null`; `calibration_record_answer` stores `chosen_sense_id IS NULL`, `is_correct = false`, `answered_at = now()`;
      no separate flag) and is sent as `is_correct = false`, exactly like a wrong option. Items never answered (`answered_at IS NULL`, `is_correct IS NULL`, session abandoned) are ignored;
      `calibration_discard_unanswered` already removes them at `/end`, the predicate guards the rest. Then `VocabularyKnowledgeService().update_from_word_tests_batch(user_id, word_language_id, results, side_effects=False)`
- [x] `update_from_word_tests_batch` (`services/vocabulary/knowledge_service.py`, line 113) gains `side_effects: bool = True`; `False` skips `_auto_create_flashcards`, `_seed_ladder_for_new_words` and
      `_trigger_frequency_inference` (otherwise calibration would create ladder rows outside the daily quota and the supply gate). The default keeps the dictation call at `routes/tests.py` unchanged
- [x] Any failure in the write is logged at WARNING, `bkt_applied_at` is reset to NULL (best effort) and `/end` still succeeds (same non-fatal contract as `write_calibration_state`)
- [x] **Exercise type justified in code comment and test:** the call is semantically `definition_match` (four-option definition recognition, as in the post-test word quiz at `routes/vocabulary.py` line 16 →
      `record_word_quiz_results` → `update_from_word_test(exercise_type='definition_match')`). The batch RPC takes no `p_exercise_type` and applies `bkt_update_word_test`, whose slip 0.05 / guess 0.25 /
      transit 0.05 equal the `definition_match` branch of `bkt_update_exercise` (`migrations/phase7_bkt_improvements.sql`); a SQL/Python test pins `bkt_update_exercise(p, c, 'definition_match') =
      bkt_update_word_test(p, c)` on a grid, so a future divergence forces the RPC to gain `p_exercise_type`
- [x] `_calibration_ledger(user_id, language_id)` reads `calibration_responses` joined (`!inner`) to `calibration_sessions` (`mode = 'definition'`, `word_language_id = language_id`,
      `bkt_applied_at IS NOT NULL`, `answered_at IS NOT NULL AND is_correct IS NOT NULL` (so a skip counts as a wrong answer and an unanswered item is ignored); limit `CALIBRATION_ROW_LIMIT = 500`) and returns per `anchor_sense_id`: `cal_n` (distinct sessions answered), `cal_wrong` (sessions whose answers
      for the sense were all incorrect), `last_answer_wrong`, `last_at`
- [x] `_evidence_candidates` (A1) subtracts the calibration contribution before applying thresholds: `evidence = evidence_count − cal_n`, `word_test_wrong = word_test_wrong − cal_wrong`; a row with `evidence <= 0`
      is not test or word-quiz evidence and is dropped from A1
- [x] `_calibration_wrong_candidates(user_id, language_id, exclude)` (Queue A2): senses with `last_answer_wrong = true`, `last_at` within `CALIBRATION_EVIDENCE_MAX_AGE_DAYS = 90`, not in `exclude`, whose current
      `user_vocabulary_knowledge.status` is not `'known'` / `'probably_known'`; **no** `evidence_count` or `p_known` threshold; ordered by `_sense_frequency` (Zipf desc) then `last_at` desc; goes through `_gate_and_admit`
      (supply gate and generation requests unchanged); consulted only when A1 did not fill `want`
- [x] Tests (`tests/test_calibration_bkt_evidence.py`, new; A2 cases also in `tests/test_ladder_new_word_quota.py`): definition-mode `/end` calls the batch method once with `side_effects=False` and only the answered
      anchors; pronunciation mode never calls it; a second `/end` does not; a failure resets the marker and does not fail `/end`; `side_effects=False` skips the three helpers and the default still runs them; A1 ignores the
      calibration contribution; A2 admits one wrong calibration answer with no other evidence, and skips known, out-of-window, excluded and correct-latest senses; A1 outranks A2

**Technical Notes:**
Facts verified 2026-10-13: calibration items are anchor senses (`calibration_responses.anchor_sense_id` / `anchor_vocab_id`, `migrations/task770_calibration_build_items.sql` lines 160-163; options with `is_key` in
`calibration_response_options`, same file lines 168-206; anchors from `calibration_anchor_pool`, `migrations/task772_calibration_anchor_pool.sql`); `calibration_record_answer` writes only calibration tables
(`migrations/task769_calibration_record_answer.sql` lines 141-155); `/end` upserts `user_calibration_state` (`services/calibration_service.py` line 590) and in definition mode calls
`apply_calibration_to_skill_ratings` (lines 627, 673), which touches ELO only; `calibration_sessions.mode` exists (`migrations/calibration_pronunciation_mode.sql` line 285). The batch RPC signature is
`update_vocabulary_from_word_tests_batch(p_user_id uuid, p_language_id smallint, p_results jsonb)` returning `out_sense_id, out_p_known_before, out_p_known_after, out_status`
(`migrations/bkt_word_test_batch.sql` line 27); it dedupes by `bool_or` and is granted to `authenticated`. The service file is `services/vocabulary/knowledge_service.py` (not `services/knowledge_service.py`).
The post-test word quiz deliberately avoids the batch wrapper because of those side effects (comment above line 366 of that file). Provenance of calibration evidence is read from the calibration ledger and
`bkt_applied_at`, not from a column on `user_vocabulary_knowledge` (one row mixes sources). Rule (i) trade-off: one calibration answer can be a bad foil or a careless tap, hence A2 ranks below A1, a later "known"
status vetoes, and the supply gate still applies. Unlike the dictation caller, calibration evidence also changes `p_known` for the correctly answered anchors, which the vocabulary-aware test selection reads; check
that nothing double-counts calibration with its frequency priors before rollout.

**Files to Create / Modify:**
- `migrations/calibration_bkt_evidence.sql` — new
- `services/calibration_service.py` — `end_session` hook and a helper `apply_calibration_to_vocabulary(user_id, session)`
- `services/vocabulary/knowledge_service.py` — `side_effects` keyword on `update_from_word_tests_batch`
- `services/practice_session_service.py` — `_calibration_ledger`, `_calibration_wrong_candidates`, A1 adjustment in `_evidence_candidates`, constants
- `tests/test_calibration_bkt_evidence.py` — new; `tests/test_ladder_new_word_quota.py` — A2 cases

**Verification:**
`pytest tests/test_calibration_bkt_evidence.py tests/test_ladder_new_word_quota.py -q` passes. On a dev account finish a definition-mode calibration run with a few wrong answers: `user_vocabulary_knowledge` has rows for the
answered anchors, `calibration_sessions.bkt_applied_at` is set, no new `user_word_ladder` or `user_flashcards` rows appear, and a second `/end` changes nothing. The next `/api/study-session` admits the wrong anchors (after
test-based nominations) subject to the supply gate.

---

## TASK-874: Review-load governor and review forecast

**Status:** [x] Done (code complete 2026-10-13; migrations not yet applied live)
**Feature:** session-budget-settings
**Type:** feature
**Complexity:** S (1-3h)
**Depends On:** TASK-863

**Description:**
Add the backlog-based governor that scales the daily new-word quota, and the review forecast shown beside the new-words input. SQL helpers (read by Tier C, TASK-865) and their Python mirrors (read by
intake, TASK-871, and the API, TASK-866). Reviews are scheduled before new words; the governor keeps a high quota from burying the learner.

**Acceptance Criteria:**
- [x] New `migrations/review_governor.sql` defines: pure `review_governor_level(numeric, numeric) -> text` (`normal` if `backlog <= T`, `reduced` if `T < backlog <= 2T`, else `paused`); pure
      `new_words_effective(int, text) -> int` (`quota`, `quota / 2` integer division, `0`); `review_item_seconds(uuid, smallint) -> numeric` (median `exercise_attempts.time_taken_ms / 1000` over 30 days with 1000 ≤ ms ≤ 120000 for
      the user's senses in the language through `dim_word_senses.vocab_id → dim_vocabulary.language_id`; fewer than 20 samples → 20.0); `review_governor_state(uuid, smallint, date) -> jsonb`
      `{overdue_items, overdue_minutes, due_items, due_minutes, threshold_minutes, item_seconds, level}`; and `ladder_new_word_state(p_user_id uuid, p_language_id smallint, p_day_start timestamptz) -> jsonb`
      `{unstarted, started_today, unstarted_sense_ids}` (SQL in [[features/session-budget-settings.tech]] Migration 5; read by TASK-865's shortfall seed and TASK-871/872): per `user_word_ladder` row of the user and
      language, `started_at = MIN(exercise_attempts.created_at)` for the sense; `unstarted` = no attempt row; `started_today` = `started_at >= p_day_start`; `unstarted_sense_ids` oldest admission first (max 200);
      `SECURITY DEFINER`, pinned `search_path`, EXECUTE revoked from `PUBLIC, anon, authenticated`
- [x] `review_governor_state`: overdue = distinct senses with `user_flashcards.due_date < p_date` OR `user_word_ladder.review_due_at IS NOT NULL AND review_due_at < local midnight of p_date` (language through the sense join);
      due-now = `due_date <= p_date` OR `review_due_at < local midnight + 1 day`; minutes = items · item_seconds / 60; `T = REVIEW_BACKLOG_THRESHOLD_DAYS (1.0) · GREATEST(REVIEW_ALLOWANCE_FLOOR_MIN (3.0),
      review_target_minutes / 7.0)` with `review_target_minutes` from the Monday-start `weekly_plan_states` row (none → floor); `practice` in `excluded_modules` → level `normal`, all values 0
- [x] Python (`services/study_plan_service.py`): `review_governor_level`, `effective_new_words`, `review_forecast_min_per_day(avg_new_words_per_day, item_seconds) = avg · REVIEWS_PER_NEW_WORD_30D · item_seconds / 60`,
      and `get_review_governor(db, user_id, language_id, plan_date)` (calls the RPC; any failure returns level `normal` and zeros, never raises). Config constants `REVIEW_BACKLOG_THRESHOLD_DAYS = 1.0`,
      `REVIEW_ALLOWANCE_FLOOR_MIN = 3.0`, `REVIEW_ITEM_SECONDS_DEFAULT = 20.0`, `REVIEWS_PER_NEW_WORD_30D = 7`, each marked tunable in a comment
- [x] **Forecast formula (steady state, no division by 30):** `X = n · N · item_seconds / 60` minutes per day, `n = new_words_week_target(npd, shape) / 7`, `N = REVIEWS_PER_NEW_WORD_30D`; 5 words a day at 20 s →
      11.67 min/day. Documented in code and in the tech spec ("Review forecast"); `N = 7` and the steady-state reading are OPEN. `item_seconds` is the all-vocabulary-exercise median (ANSWERED 2026-10-13, no review-only
      filter in v1), so the settings text is an estimate (the "≈" in the UI string)
- [x] Tests: level boundaries (`backlog == T` normal, just above reduced, `== 2T` reduced, above paused); `effective_new_words(5,'reduced') == 2`, `(1,'reduced') == 0`, `(5,'paused') == 0`; forecast value; RPC failure → `normal`;
      Python/SQL agreement on a grid and on the four constants; SQL: overdue and due-now counted once per sense across flashcards and ladder, `practice` excluded gives `normal`, no weekly row uses the floor threshold
      (SQL cases live in `tests/sql/test_session_budget_settings.sql`; Python in `tests/test_session_budget_settings.py`)

**Technical Notes:**
`user_flashcards.due_date` (date) and `user_word_ladder.review_due_at` (timestamptz, NULL for mastered) are verified in [[database/schema.tech]]; completing a review moves them forward, so "overdue and not done" is just "still in
the past". `exercise_attempts` has `time_taken_ms`, `sense_id`, `exercise_type` but no maintenance flag, so `review_item_seconds` uses all timed attempts (ANSWERED 2026-10-13: accepted for v1, labelled an estimate). Governor messages are rendered by TASK-868 (plan page) and TASK-872
(session page). The governor is re-evaluated on every session load and every Tier C build; it never un-admits words.

**Files to Create / Modify:**
- `migrations/review_governor.sql` — new
- `config.py` — four constants
- `services/study_plan_service.py` — mirrors and `get_review_governor`
- `tests/test_session_budget_settings.py`, `tests/sql/test_session_budget_settings.sql` — cases above

**Verification:**
`pytest tests/test_session_budget_settings.py -q` passes. On a dev account call `select review_governor_state('<uid>', <lang>, current_date)` and confirm the counts against `user_flashcards` and `user_word_ladder`.

---
