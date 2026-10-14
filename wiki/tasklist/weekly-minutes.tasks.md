---
title: "Weekly Minutes — Task Breakdown"
feature: weekly-minutes
prose_page: ../features/weekly-minutes.md
tech_page: ../features/weekly-minutes.tech.md
total_tasks: 12
done: 9
---

# Weekly Minutes — Task Breakdown

Spec: [[features/weekly-minutes]], [[features/weekly-minutes.tech]], [[decisions/ADR-035-study-time-ledger]]. Developer decisions 2026-10-14 are binding (measured time, clamped; activity outside sessions counts; page shows one progress line plus breakdown; current-week backfill; learner-local week; idempotent). Nothing is applied live.

**Parallelism.** Agent A owns TASK-885..887 (SQL files only), agent B owns TASK-888..892 (Python only), agent C owns TASK-893..895 (templates, static JS, i18n). File sets are disjoint. The contract between them is fixed in the tech page: SQL signatures, `weekly_study` response shape, and the `active_ms` / `client_event_id` request fields. TASK-896 runs last and is the only live-apply step, requiring user approval.

---

## TASK-885: LIVE-DB (apply gated): `study_time_ledger` table + `credit_study_time` + `get_weekly_study_seconds`

**Status:** Done (repo) — awaiting live apply approval
**Feature:** weekly-minutes
**Agent:** A
**Type:** infra
**Complexity:** M
**Depends On:** none

**Description:**
Create migration `migrations/study_time_ledger.sql` exactly as specified in the tech page: table, UNIQUE (kind, source_table, source_id), week index, RLS enabled, all client privileges revoked, `credit_study_time(p_user_id uuid, p_language_id smallint, p_kind text, p_seconds integer, p_source_table text, p_source_id text) RETURNS boolean` and `get_weekly_study_seconds(p_user_id uuid, p_language_id smallint, p_week_start date) RETURNS jsonb`. Week = `week_start_for(plan_local_date(user, language))`. Per-kind SQL clamp. SECURITY DEFINER, pinned search_path, REVOKE from PUBLIC/anon/authenticated, GRANT service_role. Header comment: requires user approval to apply live.

**Acceptance Criteria:**
- [x] File passes `tests/test_migration_security_lint.py`
- [x] Re-running the file is a no-op (IF NOT EXISTS / CREATE OR REPLACE)
- [x] anon and authenticated cannot EXECUTE either function or SELECT the table
- [x] Credit works when no `weekly_plan_states` row exists

**Technical Notes:**
Mirror the style of `migrations/new_words_completed_accrual.sql` and `migrations/task716_local_day_boundary.sql`. Check `grep -rn study_time_ledger migrations` for no name clash. Add the two functions to the allowlist logic only if the lint requires it (it should not: service_role only).

**Files to Create / Modify:**
- `migrations/study_time_ledger.sql` — create

**Verification:**
`pytest tests/test_migration_security_lint.py`; SQL tests in TASK-887.

---

## TASK-886: Idempotent current-week backfill script for the ledger (LIVE-DB, apply gated)

**Status:** Done (repo) — awaiting live apply approval
**Feature:** weekly-minutes
**Agent:** A
**Type:** infra
**Complexity:** M
**Depends On:** TASK-885

**Description:**
Write `migrations/backfill_study_time_ledger.sql`: for each (user, language) insert ledger rows for the learner-local current week from `test_attempts` (duration_ms/1000, clamp 1200, kind `test`, or `drill` for classifier/counter tests) and `exercise_attempts` (time_taken_ms with the `_credited_seconds` estimate fallback, clamp 300, kind `practice`). Source keys must equal the live keys. `ON CONFLICT DO NOTHING`. Header documents that flashcard/DT have no stored timing and are not backfilled.

**Acceptance Criteria:**
- [x] Running twice inserts 0 rows the second time
- [x] Only rows in the current local week are inserted
- [x] Keys are ('test_attempts', id) and ('exercise_attempts', id)
- [x] Read-only dry-run SELECT is included as a commented block that reports row and second counts per kind

**Technical Notes:**
First verify real column names read-only (`information_schema.columns` for test_attempts, exercise_attempts, language/test-type joins) and record them in the header; resolve the OPEN item in the tech page. No data rows are selected into the report, aggregates only.

**Files to Create / Modify:**
- `migrations/backfill_study_time_ledger.sql` — create

**Verification:**
Run against a scratch Postgres with fixtures in TASK-887; live run only with user approval (TASK-896).

---

## TASK-887: SQL tests for ledger, credit function, week attribution and backfill

**Status:** [x] Done
**Feature:** weekly-minutes
**Agent:** A
**Type:** test
**Complexity:** M
**Depends On:** TASK-885, TASK-886

**Description:**
Add `tests/sql/test_study_time_ledger.sql` covering: duplicate source credited once, per-kind clamp, zero/negative seconds, invalid kind raises, credit with no weekly row, week boundary for a UTC+13 and a UTC-10 learner near local midnight, `get_weekly_study_seconds` returns all five keys, ACL checks, backfill idempotence. Extend the catalog check expectations only if needed.

**Acceptance Criteria:**
- [x] Script passes on Postgres 16 stub with no errors
- [x] Second backfill run inserts 0
- [x] ACL assertions fail if anon/authenticated gain access

**Technical Notes:**
Follow the structure of `tests/sql/test_security_progress_tables.sql` and `tests/sql/test_session_budget_settings.sql`.

**Files to Create / Modify:**
- `tests/sql/test_study_time_ledger.sql` — create

**Verification:**
psql -v ON_ERROR_STOP=1 -f the file against a scratch DB with migrations applied.

---

## TASK-888: `services/study_time.py`: caps, clamp, best-effort credit wrapper, weekly summary

**Status:** [x] Done
**Feature:** weekly-minutes
**Agent:** B
**Type:** feature
**Complexity:** S
**Depends On:** none (SQL signatures are fixed in the tech page; mock the RPC)

**Description:**
Create `services/study_time.py` with `KIND_CAPS_SECONDS`, `clamp_active_ms(kind, value)`, `credit_study_time(db, user_id, language_id, kind, seconds, source_table, source_id) -> bool` (never raises, logs a warning), and `weekly_study_summary(db, user_id, language_id, week_start, target_minutes) -> dict` returning exactly the `weekly_study` shape in the tech page.

**Acceptance Criteria:**
- [x] Caps reuse `MAX_CREDITED_ATTEMPT_SECONDS` and `PRACTICE_ATTEMPT_MAX_SECONDS`
- [x] junk/bool/NaN/negative -> 0
- [x] RPC exception returns False without raising
- [x] Summary has all five kinds and rounds minutes
- [x] summary returns None on RPC failure

**Technical Notes:**
RPC names: `credit_study_time`, `get_weekly_study_seconds`. Seconds are ints.

**Files to Create / Modify:**
- `services/study_time.py` — create
- `tests/test_study_time.py` — create

**Verification:**
`pytest tests/test_study_time.py`.

---

## TASK-889: Credit tests and classifier/counter drills from measured duration

**Status:** [x] Done
**Feature:** weekly-minutes
**Agent:** B
**Type:** feature
**Complexity:** S
**Depends On:** TASK-888

**Description:**
In `_apply_timing_and_progress` (`routes/tests.py:284`) and the classifier/counter drill callers, compute seconds from the validated window (`validate_attempt_window`) and call `credit_study_time` kind `test` (drill routes: `drill`), source `('test_attempts', str(attempt_id))`. Pass the language id (extend the helper signature with `user_id`/`language_id`, update all four call sites in tests.py plus the two drill routes). Missing window -> no credit. Keep it after the existing RPC and non-fatal.

**Acceptance Criteria:**
- [x] Reading, listening, dictation, pinyin, pitch_accent submissions credit once
- [x] classifier and counter drills credit kind `drill`
- [x] over-long window credits at most 1200 s
- [x] no started_at/finished_at -> no ledger call
- [x] a repeated call for one attempt id credits once (RPC dedupe)

**Technical Notes:**
Do not change `apply_attempt_timing_and_progress`. Verify the drill routes send a window (frontend task TASK-894 covers client side).

**Files to Create / Modify:**
- `routes/tests.py` — modify
- `routes/classifier_drill.py` — modify
- `routes/counter_drill.py` — modify
- `tests/test_study_time_tests_route.py` — create

**Verification:**
`pytest tests/test_study_time_tests_route.py tests/test_attempt_timing*.py`.

---

## TASK-890: Credit every vocabulary practice attempt (in or out of a session)

**Status:** [x] Done
**Feature:** weekly-minutes
**Agent:** B
**Type:** feature
**Complexity:** S
**Depends On:** TASK-888

**Description:**
In `PracticeSessionService` after the exercise attempt insert (~line 696-711), call `credit_study_time` kind `practice` with the same credited seconds already computed for `record_session_progress`, source `('exercise_attempts', str(attempt_id))`, regardless of whether a session item context was passed. Speed round shares this path.

**Acceptance Criteria:**
- [x] Attempt without session context credits the ledger
- [x] Attempt with session context credits ledger and still calls record_session_progress unchanged
- [x] estimate fallback seconds are what is credited
- [x] failure of the credit never fails the attempt

**Technical Notes:**
Do not alter `record_session_progress` arguments (planner math stays).

**Files to Create / Modify:**
- `services/practice_session_service.py` — modify
- `tests/test_study_time_practice.py` — create

**Verification:**
`pytest tests/test_study_time_practice.py tests/test_practice_route_tail.py`.

---

## TASK-891: Flashcard and dual-translation endpoints accept and credit `active_ms`

**Status:** [x] Done
**Feature:** weekly-minutes
**Agent:** B
**Type:** feature
**Complexity:** M
**Depends On:** TASK-888

**Description:**
Extend `POST /api/flashcards/review` (`routes/flashcards.py:107`), `POST /api/dual-translation/<id>/submit` (`routes/dual_translation.py:148`, credit only on first grading, not the cached path) and `POST /api/dual-translation/cards/<id>/review` (:293) to read optional `active_ms` and `client_event_id`, clamp via `clamp_active_ms`, and credit kinds `flashcard` / `dual_translation`. Sources: `('flashcard_review', client_event_id)`, `('dt_submission', str(submission_id))`, `('dt_card_review', client_event_id)`. Missing/invalid `client_event_id` where required -> no credit. Language for flashcards is the card row's `language_id`; for DT the submission's L2 (passage) language. Also remove the `p_delta_seconds: 0` assumption comment in `routes/study_session.py` ~725 (behavior unchanged: surface blocks still credit counts only).

**Acceptance Criteria:**
- [x] Credits are clamped (flashcard 120 s, DT submit 900 s, DT card 120 s)
- [x] same client_event_id twice credits once
- [x] absent fields change nothing (old clients)
- [x] validation error in client_event_id is ignored, not a 400

**Technical Notes:**
Response bodies unchanged. Use `uuid.UUID(...)` to validate the event id.

**Files to Create / Modify:**
- `routes/flashcards.py` — modify
- `routes/dual_translation.py` — modify
- `routes/study_session.py` — comment only
- `tests/test_study_time_surfaces.py` — create

**Verification:**
`pytest tests/test_study_time_surfaces.py`.

---

## TASK-892: Study Plan reader: learner-local week everywhere + `weekly_study` response field

**Status:** [x] Done
**Feature:** weekly-minutes
**Agent:** B
**Type:** bug
**Complexity:** M
**Depends On:** TASK-888

**Description:**
In `routes/study_plan.py` replace `_monday_of(date.today())` with `_monday_of(plan_today(db, user_id, language_id))` at the three sites (~234, ~505, ~698; use `g.current_user_id` where needed) and add the `weekly_study` field to `GET /api/study-plan` using `weekly_study_summary` with `target_minutes = current_week['total_weekly_minutes']` or null. Degrade to `weekly_study: null` on failure.

**Acceptance Criteria:**
- [x] No remaining `date.today()` week derivations in study_plan.py
- [x] A learner whose local Monday differs from server Monday gets their local week in the GET, template-apply compute and recompute
- [x] response contains `weekly_study` exactly as specified, `current_week` unchanged
- [x] no weekly row -> target_minutes null and totals still present

**Technical Notes:**
Check `tests/study_plan_route_harness.py` for the fake db; extend it with the new RPC.

**Files to Create / Modify:**
- `routes/study_plan.py` — modify
- `tests/test_study_plan_weekly_study.py` — create

**Verification:**
`pytest tests/test_study_plan_weekly_study.py tests -k study_plan`.

---

## TASK-893: Client active-time helper; flashcards and dual translation send `active_ms` + `client_event_id`

**Status:** [x] Done
**Feature:** weekly-minutes
**Agent:** C
**Type:** feature
**Complexity:** M
**Depends On:** none (payload fields fixed in tech page)

**Description:**
Create `static/js/active-timer.js` (`window.ActiveTimer`: start/stop/reset; counts only visible-tab time with input in the last 45 s). Use it in `static/js/session/players/flashcards.js` (per card, review POST ~154), the standalone `templates/flashcards.html` flow, `static/js/dual_translation.js` (submit ~362, per passage), `static/js/session/players/dual_translation.js` and `static/js/dt-error-card.js` (card review). Send integer `active_ms` and a `client_event_id` generated once per card/submission and reused on retry.

**Acceptance Criteria:**
- [x] Hidden-tab and idle time excluded
- [x] payloads contain active_ms and client_event_id
- [x] retry reuses the same client_event_id
- [x] missing crypto.randomUUID falls back to a uuid4 generator

**Technical Notes:**
Load the helper script in the templates that need it (flashcards.html, dual_translation.html, study_session.html).

**Files to Create / Modify:**
- `static/js/active-timer.js` — create
- `static/js/session/players/flashcards.js`, `static/js/session/players/dual_translation.js`, `static/js/dual_translation.js`, `static/js/dt-error-card.js` — modify
- `templates/flashcards.html`, `templates/dual_translation.html`, `templates/study_session.html` — script tag + standalone flow
- `tests/unit/active-timer.test.js` — create

**Verification:**
`npx vitest run tests/unit/active-timer.test.js`; `npx eslint .`.

---

## TASK-894: Audit: every test and drill client sends `started_at` and `finished_at`

**Status:** [x] Done
**Feature:** weekly-minutes
**Agent:** C
**Type:** bug
**Complexity:** S
**Depends On:** none

**Description:**
Verify and fix that reading/listening (`templates/test.html`, `static/js/session/players/reading_listening.js`), dictation, pinyin, pitch accent, classifier drill (`static/js/session/players/classifier_drill.js`, `templates/classifier_drill.html`) and counter drill (`templates/counter_drill.html:520`) include ISO `started_at` (when the test was shown) and `finished_at` (at submit) in their submit bodies; add where missing. Speed round uses `/api/practice/attempt` (no change).

**Acceptance Criteria:**
- [x] Each submit body contains both timestamps
- [x] a unit test per player pins the payload keys

**Technical Notes:**
Only the keys named; do not alter scoring payloads. Server rejects one-sided windows, so always send both.

**Files to Create / Modify:**
- `templates/classifier_drill.html`, `templates/counter_drill.html`, `static/js/session/players/classifier_drill.js` and any player found missing — modify
- `tests/unit/test-timing-payload.test.js` — create

**Verification:**
`npx vitest run`; manual: submit each test type and check the request body.

---

## TASK-895: Study Plan page: "Studied this week: X / Y min" + breakdown, i18n en/zh/ja/es

**Status:** [x] Done
**Feature:** weekly-minutes
**Agent:** C
**Type:** feature
**Complexity:** M
**Depends On:** TASK-892 (field shape only; can stub)

**Description:**
In `renderWeekSummary` (`templates/study_plan.html` ~677) replace the `practice_done` tile with the progress bar and a breakdown by kind (tests, vocabulary practice, flashcards, dual translation, other drills) from `payload.weekly_study`; handle `target_minutes: null` and `weekly_study: null` (hide). Keep the per-skill counts table. Add the i18n keys listed in the tech page to all four `static/i18n/*.json`; remove the unused `study_plan.stat.practice_done`.

**Acceptance Criteria:**
- [x] Shows "Studied this week: 34 / 210 min" with fixture data
- [x] no-target and null cases render without errors
- [x] all four languages have every new key (i18n coverage test passes)
- [x] per-skill table unchanged

**Technical Notes:**
Escape nothing new: values are numbers; labels come from i18n.

**Files to Create / Modify:**
- `templates/study_plan.html` — modify
- `static/i18n/en.json`, `zh.json`, `ja.json`, `es.json` — modify
- `tests/unit/study-plan-weekly-study.test.js` — create

**Verification:**
`npx vitest run`; load the page with the fixture and screenshot.

---

## TASK-896: Integration, wiki sync and rollout (live apply approval-gated)

**Status:** [ ] Not Started
**Feature:** weekly-minutes
**Agent:** ALL
**Type:** infra
**Complexity:** M
**Depends On:** TASK-885..895

**Description:**
Run full pytest, vitest, eslint and the SQL tests; reconcile branch merges. With the user's explicit approval: apply `study_time_ledger.sql`, then deploy code, then run the backfill, then run `tests/sql/check_function_acls.sql` live (all result sets empty). Update `database/schema.tech.md` (new table), `api/rpcs.tech.md` (two RPCs, new request/response fields), `features/study-plans.tech.md`, and mark TASK-878 note (minutes bug root cause is the missing credit, not tampering).

**Acceptance Criteria:**
- [ ] Nothing applied live without recorded user approval
- [ ] migrations applied before code (as TASK-869)
- [ ] after backfill, page total for a fixture learner equals the sum of their current-week attempt seconds
- [ ] ACL check empty

**Technical Notes:**
Read-only verification first; backfill dry-run counts reported to the user before the write.

**Files to Create / Modify:**
- `wiki/database/schema.tech.md`, `wiki/api/rpcs.tech.md`, `wiki/features/study-plans.tech.md`, `wiki/tasklist/*` — modify

**Verification:**
Live: `SELECT kind, count(*), sum(seconds) FROM study_time_ledger GROUP BY 1` (aggregates only).

---
