---
title: "Daily Session Modules — Task Breakdown"
feature: session-modules
prose_page: ../features/session-modules.md
tech_page: ../features/session-modules.tech.md
total_tasks: 7
done: 0
---

# Daily Session Modules — Task Breakdown

Implements [[features/session-modules.tech]] per [[decisions/ADR-032-session-module-exclusion]].
Critical path: 863 → 864 + 865 (parallel) → 866 → 868. TASK-867 can run in parallel after 865.
TASK-869 is the live rollout and needs user approval.

---

## TASK-863: Migration — `user_study_plans.excluded_modules`

**Status:** [ ] Not Started
**Feature:** session-modules
**Type:** infra
**Complexity:** XS (<1h)
**Depends On:** none

**Description:**
Add the per-language module-exclusion column with a CHECK limited to the known module
vocabulary. Every existing row defaults to `'{}'`, meaning nothing is excluded and behaviour is
unchanged.

**Acceptance Criteria:**
- [ ] `migrations/session_module_exclusions.sql` adds `excluded_modules text[] NOT NULL DEFAULT '{}'`
- [ ] The CHECK `user_study_plans_excluded_modules_known` is added `NOT VALID`, then validated in a
      separate statement after `COMMIT`
- [ ] A column COMMENT points to the tech spec
- [ ] The file is idempotent (`ADD COLUMN IF NOT EXISTS`; constraint add guarded with a
      `DO $$ … IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = …)` block)

**Technical Notes:**
The DDL is in [[features/session-modules.tech#Database Impact]]. Do **not** apply it live here.
TASK-869 does that. The CHECK list must equal `ALL_MODULES` in TASK-864.

**Files to Create / Modify:**
- `migrations/session_module_exclusions.sql` — new

**Verification:**
`psql` against a local/branch DB: run the file twice (no error), then
`UPDATE user_study_plans SET excluded_modules='{bogus}' …` fails with a CHECK violation.

---

## TASK-864: Tier B — `apply_module_exclusions` + `compute_weekly_plan` wiring

**Status:** [ ] Not Started
**Feature:** session-modules
**Type:** feature
**Complexity:** M (3-8h)
**Depends On:** TASK-863

**Description:**
Add a pure, deterministic helper. It removes excluded modules from the template and rescales the
scalable remaining modules by one common factor, so the template's total minutes are preserved.
Wire it into `compute_weekly_plan` so persisted `target_counts` never contain an excluded module
and `practice_target_minutes` is 0 when practice is excluded.

**Acceptance Criteria:**
- [ ] `MODULE_PRACTICE`, `ALL_MODULES` and `NON_SCALABLE_MODULES` constants exist in
      `services/study_plan_service.py`
- [ ] `apply_module_exclusions(...)` matches the tech-spec algorithm, including the empty-set
      identity short-circuit, largest-remainder rounding with the `(remainder desc, key asc)`
      tie-break, and flashcards-only giving no redistribution
- [ ] The ZH-30 worked example (exclude listening) gives reading 7, dictation 3, pinyin 1,
      classifier_drill 1, flashcards 7, dual_translation 2, practice 103
- [ ] `compute_weekly_plan` selects `excluded_modules` and feeds the adjusted template into the
      weakness/bandit/`allocate_test_counts`/`rebalance_practice` steps
- [ ] With practice excluded: `rebalance_practice` is skipped, `practice_minutes = 0`, shares are
      `base`/`1−base`, and there is no practice carry-over
- [ ] `tests/test_session_modules.py` covers every case under "Unit" in the spec's Testing
      Strategy, including `ALL_MODULES` equalling the SQL CHECK list parsed from the TASK-863 file
- [ ] `tests/test_weekly_plan_seeding.py` and `tests/test_plannable_surfaces.py` still pass

**Technical Notes:**
Memoise `_test_time_estimate` per `compute_weekly_plan` call (a dict). It hits the DB per skill,
and the helper and step 8 both need it. Keep the helper free of DB access by passing
`minutes_of` in. Do not touch `allocate_test_counts` itself.

**Files to Create / Modify:**
- `services/study_plan_service.py` — constants, helper, `compute_weekly_plan` wiring
- `tests/test_session_modules.py` — new

**Verification:**
`pytest tests/test_session_modules.py tests/test_weekly_plan_seeding.py tests/test_plannable_surfaces.py -q`
passes.

---

## TASK-865: Tier C — `build_daily_session` honours `excluded_modules`

**Status:** [ ] Not Started
**Feature:** session-modules
**Type:** feature
**Complexity:** M (3-8h)
**Depends On:** TASK-863

**Description:**
Redefine `build_daily_session` so it reads `v_plan.excluded_modules`. It filters excluded keys
out of the TASK-732 budget split and the candidate pool, drops practice candidates when
`practice` is excluded, and keeps retry and word_upload off excluded test types. This is defence
in depth on top of TASK-864. It also echoes `excluded_modules` into `daily_session_targets`.

**Acceptance Criteria:**
- [ ] New `migrations/session_module_exclusions_build_daily_session.sql`, built from the **live**
      `pg_get_functiondef` (confirm the `word_upload` marker is present), with all nine edits
      from the tech spec, each tagged `-- session-modules`
- [ ] `migrations/word_upload_slot_scheduling.sql` gets a header note that its function body is
      superseded. It is **not** archived, because it is the only record of
      `last_matched_surfaced_at`
- [ ] `tests/sql/test_session_module_exclusions.sql` covers four cases: (a) an excluded test
      skill is absent from `test_ids` and `requested_counts`; (b) retry and word_upload skip
      excluded types; (c) `{practice}` gives `practice_*_min = 0` and `practice_budget_minutes = 0`;
      (d) a same-day re-run after excluding a skill keeps that skill's completed slot
- [ ] With `excluded_modules = '{}'`, the output equals the pre-change function's for the same
      fixture

**Technical Notes:**
Use `<> ALL(v_excluded)`, not `NOT IN`, because the array may be empty. The surface hydration
reads `skill_counts`, so it needs no change. TASK-705 carry-over is deliberately left unchanged.

**Files to Create / Modify:**
- `migrations/session_module_exclusions_build_daily_session.sql` — new
- `migrations/word_upload_slot_scheduling.sql` — header note only
- `tests/sql/test_session_module_exclusions.sql` — new

**Verification:**
Run the SQL test against a Supabase branch or local DB in the same way as
`tests/sql/test_task705_same_day_safe.sql`. All assertions pass.

---

## TASK-866: API — `excluded_modules` on GET/PUT `/api/study-plan` + immediate rebuild

**Status:** [ ] Not Started
**Feature:** session-modules
**Type:** feature
**Complexity:** M (3-8h)
**Depends On:** TASK-864, TASK-865

**Description:**
Expose and validate the setting. When it changes, recompute the learner-local current week and
re-resolve today's not-yet-completed slots, so the change applies immediately.

**Acceptance Criteria:**
- [ ] GET returns `plan.excluded_modules` and `available_modules` (the union of all of the
      language's template keys ∩ `ALL_MODULES`, plus `practice`, in `ALL_MODULES` order)
- [ ] PUT validates through `_validate_excluded_modules`, with three 400 cases: not a list of
      strings, a module not offered for the language, and all modules excluded
- [ ] `'excluded_modules'` is in the `is_template_only` exclusion tuple
- [ ] Only when the value changed: `compute_weekly_plan(…, _monday_of(plan_today(…)))` runs, then
      `StudyPlanService.rebuild_today` (new) when `STUDY_PLAN_ENABLED`. Both are best-effort, and
      a failure logs a WARNING and still returns 200
- [ ] The response includes `session_rebuilt`
- [ ] `rebuild_today` only calls the RPC when today's `daily_test_loads` row exists
- [ ] `tests/test_session_modules_routes.py` covers the cases under "Route" in the spec

**Technical Notes:**
`plan_today` is in `services.day_boundary`. Compare the requested value against the stored value
after normalisation (dedupe and sort), so a no-op save doesn't trigger a rebuild. Update the
module docstring's endpoint table.

**Files to Create / Modify:**
- `routes/study_plan.py` — GET/PUT changes and the validator
- `services/study_plan_service.py` — `rebuild_today`
- `tests/test_session_modules_routes.py` — new

**Verification:**
`pytest tests/test_session_modules_routes.py -q` passes. Then run it manually on a local server:
PUT `{language_id, excluded_modules:["listening"]}`, and the next `GET /api/study-session` has
no listening items.

---

## TASK-867: Session runner + legacy fallback honour exclusions

**Status:** [ ] Not Started
**Feature:** session-modules
**Type:** feature
**Complexity:** S (1-3h)
**Depends On:** TASK-865

**Description:**
Suppress the speed-round tail when `practice` is excluded, using
`daily_session_targets.excluded_modules` with no new query. Make the legacy `_compute_daily_load`
fallback skip excluded test types when a plan row exists.

**Acceptance Criteria:**
- [ ] `routes/study_session.py` sets `speed_round_available = False` when
      `'practice' in targets.get('excluded_modules', [])`
- [ ] `TestService._compute_daily_load` drops retry and recommended candidates whose `test_type`
      is excluded, reading `excluded_modules` from `user_study_plans`. With no row there is no
      filter
- [ ] Tests cover both cases. Existing `tests/test_daily_load_retry_slot.py` stays green

**Technical Notes:**
The `targets` dict is already loaded in `get_study_session`, and the gate goes before the
`build_session_queue` call. In `_compute_daily_load`, fetch the plan row once at the top.

**Files to Create / Modify:**
- `routes/study_session.py` — speed-round gate
- `services/test_service.py` — legacy filter
- `tests/test_session_modules.py` — add cases

**Verification:**
`pytest tests/test_session_modules.py tests/test_daily_load_retry_slot.py -q` passes.

---

## TASK-868: Settings UI — "Daily session modules" card + i18n

**Status:** [ ] Not Started
**Feature:** session-modules
**Type:** feature
**Complexity:** M (3-8h)
**Depends On:** TASK-866

**Description:**
Add a toggle card to `/study-plan` so learners can include or exclude modules per language. The
last included toggle can't be switched off, and a hint appears when only flashcards remains.
Save sends `excluded_modules` with the existing PUT.

**Acceptance Criteria:**
- [ ] The card sits between "Weekday shape" and "Advanced", with one `form-switch` per
      `available_modules` entry; checked means included
- [ ] With one toggle left on, it is disabled with the `last_one` tooltip
- [ ] With only flashcards on, `#moduleShortHint` is visible
- [ ] Save includes `excluded_modules`, and when `session_rebuilt` is true the success banner
      uses the `session_rebuilt` copy
- [ ] All `study_plan.modules.*` keys are present in `en`, `zh`, `ja` and `es`. zh/ja use the
      in-app terms already used for those skills elsewhere in the i18n files
- [ ] `eslint .` reports 0 errors

**Technical Notes:**
Follow the existing `T()` helper and `data-i18n` patterns in `templates/study_plan.html`. Reuse
the existing skill labels from the i18n files where present rather than writing new
translations. The skill-override list needs no change.

**Files to Create / Modify:**
- `templates/study_plan.html` — the card, state and save body
- `static/i18n/en.json`, `zh.json`, `ja.json`, `es.json` — the new keys

**Verification:**
Run the app (`/run`). On `/study-plan` for zh, untick Listening and Pinyin, then save. The
banner confirms the rebuild, and `/session` shows no listening or pinyin items while the total
minutes stay about the same. Try to untick the last module: it is disabled.

---

## TASK-869: Live rollout — apply migrations + end-to-end check (user-approved)

**Status:** [ ] Not Started
**Feature:** session-modules
**Type:** infra
**Complexity:** S (1-3h)
**Depends On:** TASK-863, TASK-864, TASK-865, TASK-866, TASK-867, TASK-868

**Description:**
Apply both migrations to the live DB after the developer approves, deploy the code, and verify
on the test account that excluding a module removes it from the current week and today's
session while completed work is kept.

**Acceptance Criteria:**
- [ ] The developer approves before any live DB write
- [ ] `session_module_exclusions.sql` is applied, then
      `session_module_exclusions_build_daily_session.sql`. The live `pg_get_functiondef`
      contains the `session-modules` marker
- [ ] With the plan at `'{}'`, today's rebuild output is unchanged from before (spot check on the
      test account)
- [ ] Excluding `listening` on the test account removes listening from
      `weekly_plan_states.target_counts` and from today's `daily_test_loads.test_ids` (except
      completed slots), with `today_budget_minutes` about unchanged
- [ ] [[database/schema.tech]] and [[features/study-plans.tech]] (HTTP endpoints table) are updated

**Technical Notes:**
Apply with the same `supabase db query --linked` flow used for TASK-861. Revert the test account
to `'{}'` afterwards.

**Files to Create / Modify:**
- `wiki/database/schema.tech.md`, `wiki/features/study-plans.tech.md`, `wiki/log.md`

**Verification:**
Run the SQL probes listed above and load `/session` on the test account.

---
