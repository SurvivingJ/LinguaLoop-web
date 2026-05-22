---
title: "Study Plans — Task Breakdown"
feature: study-plans
prose_page: ../features/study-plans.md
tech_page: ../features/study-plans.tech.md
total_tasks: 20
done: 0
---

# Study Plans — Task Breakdown

Implements [[decisions/ADR-008-study-plan-orchestration-layer]] and downstream ADRs (009, 010, 011, 013). Depends on the Practice Engine merger (`TASK-101` through `TASK-112`) being shipped first — Tier C's Practice slot consumers call the merged `get_practice_session`. Order respects migration dependencies and the rollout sequence in [[features/study-plans.tech#rollout-sequence]].

---

## TASK-201: Migration — `test_attempts.started_at`, `duration_ms`

**Status:** [ ] Not Started
**Type:** infra
**Complexity:** XS
**Depends On:** none

**Description:**
`ALTER TABLE test_attempts ADD COLUMN started_at timestamptz, ADD COLUMN duration_ms integer CHECK (duration_ms IS NULL OR (duration_ms > 0 AND duration_ms < 3600000));`

**Acceptance Criteria:**
- [ ] Columns added with CHECK enforced.
- [ ] Existing rows unaffected (both columns NULL).

**Files:** `migrations/study_plans_v1/005_alter_test_attempts_duration.sql`.

**Verification:** `\d test_attempts` shows new columns; existing query patterns unchanged.

---

## TASK-202: Migration — `daily_test_loads.daily_session_targets`

**Status:** [ ] Not Started
**Type:** infra
**Complexity:** XS
**Depends On:** none

**Description:** `ALTER TABLE daily_test_loads ADD COLUMN daily_session_targets jsonb;`

**Acceptance Criteria:**
- [ ] Column added.
- [ ] Existing rows have NULL; backfilling not required.

**Files:** `migrations/study_plans_v1/006_alter_daily_test_loads_targets.sql`.

**Verification:** `\d daily_test_loads` shows new column.

---

## TASK-203: Migration — `dim_test_types.expected_minutes_p50`

**Status:** [ ] Not Started
**Type:** infra
**Complexity:** XS
**Depends On:** none

**Description:** `ALTER TABLE dim_test_types ADD COLUMN expected_minutes_p50 numeric(4,1);`

**Acceptance Criteria:**
- [ ] Column added.
- [ ] NULL on all existing rows.

**Files:** `migrations/study_plans_v1/008_alter_dim_test_types_p50.sql`.

**Verification:** `\d dim_test_types` shows new column.

---

## TASK-204: Migration — `dim_study_plan_templates` + seed

**Status:** [ ] Not Started
**Type:** infra
**Complexity:** S
**Depends On:** none

**Description:** Create table per spec; INSERT 9 rows (3 languages × 3 daily-minutes buckets) with exact `weekly_test_counts` jsonb per [[features/study-plans.tech#schema]]. Mark `daily_minutes=30` rows as `is_default=true`.

**Acceptance Criteria:**
- [ ] Table created with PK + UNIQUE(language_id, daily_minutes).
- [ ] 9 seed rows present.
- [ ] `(language_id=1, daily_minutes=30)` row has `weekly_test_counts->>'reading' = '6'` and so on per spec.
- [ ] Exactly 3 rows have `is_default=true` (one per language).

**Files:** `migrations/study_plans_v1/003_dim_study_plan_templates.sql`.

**Verification:** `SELECT language_id, daily_minutes, weekly_test_counts FROM dim_study_plan_templates ORDER BY language_id, daily_minutes;` matches the spec table.

---

## TASK-205: Migration — `dim_study_goals` (empty V2 placeholder)

**Status:** [ ] Not Started
**Type:** infra
**Complexity:** XS
**Depends On:** none

**Description:** Create empty table per spec.

**Acceptance Criteria:**
- [ ] Table created.
- [ ] No seed rows.

**Files:** `migrations/study_plans_v1/004_dim_study_goals.sql`.

**Verification:** `SELECT COUNT(*) FROM dim_study_goals;` returns 0.

---

## TASK-206: Migration — `user_study_plans`

**Status:** [ ] Not Started
**Type:** infra
**Complexity:** S
**Depends On:** TASK-204, TASK-205

**Description:** Create table per spec with PK on `(user_id, language_id)`, FKs to `auth.users`, `dim_languages`, `dim_study_plan_templates`, `dim_study_goals`. Defaults: `weekday_shape='[1,1,1,1,1,1,1]'`, `skill_weight_overrides='{}'`, `timezone='UTC'`. CHECK `daily_minutes BETWEEN 10 AND 180`.

**Acceptance Criteria:**
- [ ] Table created; constraints enforced.
- [ ] FKs cascade on user delete.
- [ ] Default jsonb values valid.

**Files:** `migrations/study_plans_v1/009_create_user_study_plans.sql`.

**Verification:** `\d user_study_plans` shows full schema.

---

## TASK-207: Migration — `weekly_plan_states`

**Status:** [ ] Not Started
**Type:** infra
**Complexity:** S
**Depends On:** TASK-206

**Description:** Create table per spec with PK `(user_id, language_id, week_start_date)`. Add index on `week_start_date`. Defaults per spec.

**Acceptance Criteria:**
- [ ] Table created; PK + index present.
- [ ] Default `'{}'::jsonb` for `completed_counts` and `session_progress_log`.

**Files:** `migrations/study_plans_v1/010_create_weekly_plan_states.sql`.

**Verification:** `\d weekly_plan_states` shows full schema and index.

---

## TASK-208: RPC `apply_study_plan_template`

**Status:** [ ] Not Started
**Type:** feature
**Complexity:** XS
**Depends On:** TASK-206

**Description:** Simple UPSERT helper per spec.

**Acceptance Criteria:**
- [ ] RPC created.
- [ ] First call inserts; second call (same args) updates `template_id`, `daily_minutes`, `updated_at`.
- [ ] Returns the upserted row.

**Files:** `migrations/study_plans_v1/rpcs/apply_study_plan_template.sql`.

**Verification:** `SELECT apply_study_plan_template('<uuid>', 1, 101);` returns a row; rerun produces no error and updates `updated_at`.

---

## TASK-209: Python — weakness signal helpers

**Status:** [ ] Not Started
**Type:** feature
**Complexity:** M
**Depends On:** TASK-207

**Description:** Implement `weakness(s)`, `value(s)`, `bandit_score(...)`, `allocate_test_counts(...)`, `rebalance_practice(...)` in Python per [[algorithms/study-plan-adaptation.tech]]. Each function has its own unit tests with seeded inputs. Cold-start, full-saturation, and zero-pressure edge cases covered.

**Acceptance Criteria:**
- [ ] All 5 functions implemented with full type hints.
- [ ] Unit tests cover: cold start (n<5 → weakness=0.50), saturated ELO gap (=1.0), zero-pressure (acq_share defaults to 0.70), water-fill overflow redistribution.
- [ ] `bandit_score` is deterministic for fixed seed (assert reproducibility).

**Files:**
- `services/study_plan_service.py::_weakness.py`, `_value.py`, `_bandit.py`, `_allocator.py`, `_rebalance.py`.
- `tests/services/test_study_plan_signals.py`.

**Verification:** `pytest tests/services/test_study_plan_signals.py` all green; cold-start case asserts weakness=0.50.

---

## TASK-210: RPC `compute_weekly_plan`

**Status:** [ ] Not Started
**Type:** feature
**Complexity:** L
**Depends On:** TASK-209

**Description:** Implement Python `compute_weekly_plan(user_id, language_id, week_start)` per [[algorithms/study-plan-adaptation.tech#6-compute_weekly_plan-orchestration]]. UPSERT to `weekly_plan_states`. Carry-over from prior week's row preserved (50% decay). Conditional UPDATE preserves `completed_counts`, `practice_completed_*_min`, `session_progress_log`.

**Acceptance Criteria:**
- [ ] Function implemented.
- [ ] UPSERT idempotency: re-running with same DB state produces identical `target_counts`.
- [ ] Re-running mid-week with changed inputs UPSERTs but does NOT zero out completed counters.
- [ ] Carry-over from prior week adds `0.5 · max(0, remaining)` to current targets.
- [ ] Skipped run (no prior row): no carry-over; defaults from template only.

**Files:**
- `services/study_plan_service.py::compute_weekly_plan.py`.
- `tests/services/test_compute_weekly_plan.py`.

**Verification:** Replicate the worked example from [[features/study-plans.tech#worked-example]] against a seeded user; assert `target_counts == {"reading":4,"listening":11,"dictation":4,"pinyin":1,"measure_word":1}`.

---

## TASK-211: RPC `record_session_progress`

**Status:** [ ] Not Started
**Type:** feature
**Complexity:** S
**Depends On:** TASK-207

**Description:** Implement the PL/pgSQL function per [[features/study-plans.tech#rpc-record_session_progress]]. Idempotency on `p_attempt_id` via `session_progress_log` jsonb.

**Acceptance Criteria:**
- [ ] Function created.
- [ ] First call with a new `attempt_id` updates counters and appends to log; returns `true`.
- [ ] Second call with same `attempt_id` returns `false`; counters unchanged.
- [ ] Test-kind requires `p_skill`; practice kinds accept NULL skill.

**Files:** `migrations/study_plans_v1/rpcs/record_session_progress.sql`. Test: `tests/sql/test_record_session_progress.py`.

**Verification:** SQL test calls twice with same attempt_id, asserts second returns false.

---

## TASK-212: Wire `record_session_progress` into submit paths

**Status:** [ ] Not Started
**Type:** refactor
**Complexity:** M
**Depends On:** TASK-211, TASK-201

**Description:** Modify `process_test_submission` (and dictation/pinyin/pitch variants) to accept `p_started_at`/`p_finished_at`, compute `duration_ms`, and call `record_session_progress(..., 'test', test_type_code, 1, duration_ms/60000)`. Modify `record_attempt_with_updates` in the practice service to call `record_session_progress(..., 'practice_'||mode, NULL, 0, time_taken_ms/60000)`. FE `test_runner.js` captures `started_at` on mount and includes both timestamps in submit payload.

**Acceptance Criteria:**
- [ ] All 4 test-submit RPCs accept new timestamp params (nullable for backwards compat in the first deploy window).
- [ ] `record_session_progress` called within the same transaction as the attempt insert.
- [ ] FE sends ISO timestamps; server validates and computes `duration_ms`.
- [ ] Practice attempts increment `practice_completed_maint_min` or `practice_completed_acq_min`.

**Files:**
- `migrations/study_plans_v1/rpcs/process_test_submission_v3.sql` (add params).
- `migrations/study_plans_v1/rpcs/process_dictation_submission_v2.sql`, etc.
- `services/practice_session_service.py::record_attempt_with_updates`.
- `routes/tests.py::submit_test_attempt`.
- `static/js/test_runner.js`.

**Verification:** Submit a test in staging; verify `test_attempts.duration_ms` populated, `weekly_plan_states.completed_counts` incremented for that skill.

---

## TASK-213: RPC `build_daily_session`

**Status:** [ ] Not Started
**Type:** feature
**Complexity:** L
**Depends On:** TASK-210, TASK-202

**Description:** Implement Python `build_daily_session(user_id, language_id, date)` per [[algorithms/study-plan-adaptation.tech#algorithm-greedy--local-swap]]. Greedy fill + local swap pass; hydrate test slots via existing `get_recommended_tests`; UPSERT to `daily_test_loads` with `daily_session_targets`. Fall-back to legacy `_compute_daily_load` if `STUDY_PLAN_ENABLED` is false or no `user_study_plans` row.

**Acceptance Criteria:**
- [ ] Function implemented; UPSERT writes test_ids + targets.
- [ ] `today_budget` computed from `weekly_plan_states.total_weekly_minutes · weekday_shape[weekday] / 7`.
- [ ] Upper cap = 1.5 × today_budget enforced.
- [ ] Spacing penalty applied per the formula.
- [ ] Local-swap pass attempts cheap improvements.
- [ ] Hydration calls `get_recommended_tests` once per skill.

**Files:**
- `services/study_plan_service.py::build_daily_session.py`.
- `tests/services/test_build_daily_session.py`.

**Verification:** Replicate the Monday resolve from the worked example; assert resulting `test_ids` count matches and `daily_session_targets` jsonb has the expected maint/acq split.

---

## TASK-214: Wire `build_daily_session` into `get_or_create_daily_load`

**Status:** [ ] Not Started
**Type:** refactor
**Complexity:** S
**Depends On:** TASK-213

**Description:** Modify `services/test_service.py::get_or_create_daily_load`: if `Config.STUDY_PLAN_ENABLED` AND `user_study_plans` row exists for `(user, language)`, call `build_daily_session(user, language, today)`; else legacy `_compute_daily_load`. External signature unchanged. `_compute_daily_load` itself is unchanged.

**Acceptance Criteria:**
- [ ] Routing logic added.
- [ ] Existing daily-load integration tests pass with flag off.
- [ ] With flag on + plan row present, returned daily-load is plan-driven.

**Files:**
- `services/test_service.py`.
- `tests/services/test_get_or_create_daily_load.py` — add cases for flag on/off.

**Verification:** Run with `STUDY_PLAN_ENABLED=False`: legacy behavior. With `=True` and a seeded plan row: new behavior with `daily_session_targets` populated.

---

## TASK-215: Cron — `study_plan_weekly_recompute`

**Status:** [ ] Not Started
**Type:** infra
**Complexity:** S
**Depends On:** TASK-210

**Description:** Add cron entry in `app.py:227-251` per spec — Sunday 23:00 UTC, advisory-lock-guarded, iterates `user_study_plans`. Same pattern as `irt_calibration_nightly`.

**Acceptance Criteria:**
- [ ] Cron registered.
- [ ] Advisory lock prevents duplicate fires across gunicorn workers.
- [ ] Failures per-row logged; the loop continues.

**Files:**
- `app.py`.
- `services/study_plan_service.py::_run_weekly_plan_recompute`.

**Verification:** Trigger manually via REPL: `_run_weekly_plan_recompute()` updates all `weekly_plan_states` rows for the current week.

---

## TASK-216: `/api/study-plan` endpoints

**Status:** [ ] Not Started
**Type:** feature
**Complexity:** S
**Depends On:** TASK-208, TASK-210

**Description:** Add endpoints per [[api/rpcs.tech|API tech]]: GET / PUT / POST recompute / GET templates. Validate inputs (daily_minutes 10–180; weekday_shape sums to 7; skill_weight_overrides values in [0.5, 2.0]).

**Acceptance Criteria:**
- [ ] All four endpoints functional.
- [ ] Input validation returns 400 with clear error messages.
- [ ] PUT updates `user_study_plans.updated_at`.

**Files:**
- `routes/settings.py` — append handlers.
- `tests/routes/test_study_plan_endpoints.py`.

**Verification:** `curl -X PUT /api/study-plan -d '{"language_id":1,"daily_minutes":45}'` returns 200; subsequent GET returns the new value.

---

## TASK-217: Settings UI — Study Plan tab

**Status:** [ ] Not Started
**Type:** feature
**Complexity:** M
**Depends On:** TASK-216

**Description:** Add a Study Plan tab to the existing settings page. Per-language editor (language selector + daily_minutes slider + weekday-shape sliders + Advanced disclosure with per-skill weight overrides). Display total-across-languages tally.

**Acceptance Criteria:**
- [ ] UI renders one plan per active language.
- [ ] Saving calls `PUT /api/study-plan` with validated payload.
- [ ] Weekday-shape sliders normalize to sum=7 on save.
- [ ] Per-skill overrides hidden behind "Advanced" disclosure; default 1.0; range 0.5–2.0.
- [ ] Total across languages displayed as `45 + 30 = 75 min/day total`.

**Files:**
- `templates/settings.html` (or React equivalent).
- `static/js/study_plan_settings.js`.

**Verification:** Manual UI walk-through on staging; verify save → DB round-trip.

---

## TASK-218: Wipe user-state tables for launch

**Status:** [ ] Not Started
**Type:** infra
**Complexity:** XS
**Depends On:** TASK-206, TASK-207
**Revised:** 2026-05-22 — was "Backfill SQL"; pre-launch DB has no real-user history to preserve. See plan revision R4.2 and [[decisions/ADR-013-global-feature-flag-rollout]].

**Description:** One-shot TRUNCATE … RESTART IDENTITY CASCADE on all 12 user-state tables (`user_skill_ratings`, `user_vocabulary_knowledge`, `user_word_ladder`, `user_flashcards`, `user_exercise_sessions`, `user_exercise_history`, `daily_test_load_items`, `daily_test_loads`, `test_attempts`, `exercise_attempts`, `user_study_plans`, `weekly_plan_states`). Run ONCE against the target DB immediately before flipping `Config.STUDY_PLAN_ENABLED = True`. Reference data (`dim_*`, content tables, auth) is untouched.

**Acceptance Criteria:**
- [ ] Script created and applied against the target DB.
- [ ] All 12 tables return `SELECT COUNT(*) = 0` after running.
- [ ] Reference data (`dim_languages`, `dim_study_plan_templates`, `tests`, `exercises`, `word_assets`, `auth.users`, `public.users`) is unaffected — row counts identical pre/post.
- [ ] `RAISE NOTICE` in the script logs the post-wipe row total (should be 0).

**Files:** `migrations/phase13_wipe_user_state_for_launch.sql` (already written this session).

**Verification:** After the wipe + flag flip, sign up a fresh test user, complete onboarding selecting a 30 min/day Chinese plan, then take a test → confirm a `user_study_plans` row exists, the next daily-load is built via `build_daily_session` (check `daily_test_loads.daily_session_targets` is non-NULL), and `weekly_plan_states` populates after the first Sunday cron tick.

---

## TASK-219: Flag flip + monitoring

**Status:** [ ] Not Started
**Type:** infra
**Complexity:** M
**Depends On:** TASK-214, TASK-215, TASK-217, TASK-218

**Description:** Set `Config.STUDY_PLAN_ENABLED = True` and deploy. Pre-flip: ensure backfill ran; ensure parity tests green (from `TASK-111`); ensure staging soak (10 seeded users × 2 weeks) clean. Post-flip: monitor DAU, session-completion-rate, sessions-per-DAU, tests-per-session, practice-minutes-per-session daily for 7 days.

**Acceptance Criteria:**
- [ ] Pre-flip checks documented in a PR description.
- [ ] Flag flipped on a low-traffic day.
- [ ] Monitoring dashboard records baseline + 7-day windows.
- [ ] Rollback procedure documented and tested in staging (toggle flag → legacy behavior resumes within one request cycle).

**Files:**
- PR description with checklist.
- `Config.py` — flag set to True.

**Verification:** 7-day post-flip metrics within ±10% of baseline.

---

## TASK-220: Deprecation cleanup (T+30 days)

**Status:** [ ] Not Started
**Type:** refactor
**Complexity:** M
**Depends On:** TASK-219 (T+30 days stable)

**Description:** Remove `get_exercise_session` and `get_ladder_session` deprecation wrappers. Replace `/api/exercises/session` and `/api/vocab-dojo/session` handlers with 302 redirects to `/api/practice/session` with appropriate query params. Mark `wiki/features/exercises.md` and `wiki/features/vocab-dojo.md` `status: deprecated` (already done in this round); consider deleting after one more release.

**Acceptance Criteria:**
- [ ] Wrapper RPCs dropped from DB.
- [ ] Old routes 302 to new canonical.
- [ ] All grep-able callers of old RPC names purged.
- [ ] FE uses `/api/practice/session` exclusively.

**Files:**
- `migrations/practice_merger/drop_deprecation_wrappers.sql`.
- `routes/exercises.py`, `routes/vocab_dojo.py` — replace handlers with 302.
- All FE callers updated.

**Verification:** `grep -r "get_exercise_session\|get_ladder_session" --include="*.py" --include="*.sql"` returns no matches; integration tests still green.

---
