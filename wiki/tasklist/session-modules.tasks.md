---
title: "Daily Session Modules — Task Breakdown"
feature: session-modules
prose_page: ../features/session-modules.md
tech_page: ../features/session-modules.tech.md
total_tasks: 7
done: 5
---

# Daily Session Modules — Task Breakdown

Implements [[features/session-modules.tech]] per [[decisions/ADR-032-session-module-exclusion]].
Critical path: 863 → 874 → 865 + (870 → 864) → 871 → 866 → 868. TASK-865 needs the governor SQL helpers from TASK-874 and the SQL helpers from TASK-863's migration; it runs in parallel with 870/864. TASK-867 can run in parallel after 865.
TASK-869 is the live rollout and needs user approval.

**Amended 2026-10-13:** the `practice` module now means "Vocabulary review" only; new words are
governed by `user_study_plans.new_words_per_day` (0 = off), and `new_words_per_day > 0` counts as
"included" for the at-least-one rule. Tasks 863–866, 868 and 869 are amended below. The new
columns, the new-word quota model and new-word tasks are specified in [[features/session-budget-settings.tech]]
and [[decisions/ADR-033-budget-scope-and-new-word-budget]]; new tasks TASK-870–874 live in
[[tasklist/session-budget-settings.tasks]]. TASK-864 now also depends on TASK-870 (it reads
`get_minutes_per_new_word`). TASK-865 does **not** need TASK-870: the SQL `new_word_minutes` helper
and the `dim_languages.new_word_minutes_est` column ship in TASK-863's migration, with a 3.0 fallback.
Reconciled against the spec 2026-10-13.

**Amended again 2026-10-13 (b)** (ADR-033 Revision (b)): the "extra pool outside the budget" model is removed.
`new_words_per_day` is a daily quota inside the planner: Tier C fits whole new words into the in-budget practice share
after due reviews, unused share minutes return to tests, and the rest is an optional tail served after the main
session. Removed from this file's tasks: `extra_weekly_minutes`, `scale_up_to_target`, `_largest_remainder_scale`
factoring, Tier C pool 2 (`x_acq` / `x_maint`), `REVIEW_EXTRA_CAP_FRACTION`, `EXTRA_REVIEW_MIN_CHUNK_MIN`. Added:
`tail_completed_min`, `tail_new_words_completed`, the review-load governor (TASK-874, which TASK-865 now depends on), derived
shares, and layout Option A for TASK-868.

---

## TASK-863: Migration — `user_study_plans.excluded_modules`

**Status:** [x] Done (code complete 2026-10-13; migrations not yet applied live)
**Feature:** session-modules
**Type:** infra
**Complexity:** S (1-3h)
**Depends On:** none

**Description:**
Add the per-language module-exclusion column with a CHECK limited to the known module
vocabulary. Every existing row defaults to `'{}'`, meaning nothing is excluded and behaviour is
unchanged. (2026-10-13) The same file also carries the budget columns, the relaxed shares CHECK,
`dim_languages.new_word_minutes_est`, the SQL helpers and the redefined `compute_weekly_plan_persist`
(complexity raised from XS).

**Acceptance Criteria:**
- [x] `migrations/session_module_exclusions.sql` adds `excluded_modules text[] NOT NULL DEFAULT '{}'`
- [x] The CHECK `user_study_plans_excluded_modules_known` is added `NOT VALID`, then validated in a
      separate statement after `COMMIT`
- [x] A column COMMENT points to the tech spec
- [x] The file is idempotent (`ADD COLUMN IF NOT EXISTS`; constraint add guarded with a
      `DO $$ … IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = …)` block)
- [x] (2026-10-13) The same file adds `user_study_plans.budget_scope text NOT NULL DEFAULT
      'tests_and_review'` with CHECK `budget_scope IN ('tests_and_review','tests_only')`
- [x] (2026-10-13) The same file adds `user_study_plans.new_words_per_day smallint NOT NULL
      DEFAULT 5` with CHECK `new_words_per_day BETWEEN 0 AND 50`, and backfills existing rows to
      `max(1, daily_minutes // 6)` **per day** (ANSWERED 2026-10-13: accepted knowingly; 5/day at 30 min is about 7x the old per-week rate)
- [x] (2026-10-13) The same file adds to `weekly_plan_states`: `budget_scope text NOT NULL DEFAULT
      'tests_and_review'` and the six `int NOT NULL DEFAULT 0` columns `review_target_minutes`,
      `new_words_target`, `new_words_completed`, `acq_target_minutes`, `tail_completed_min`,
      `tail_new_words_completed` (revision (b): `extra_weekly_minutes` is **not** added), with
      CHECKs `weekly_plan_states_budget_scope_known` and `weekly_plan_states_new_columns_non_negative`;
      in-flight rows (week_start_date >= CURRENT_DATE - 14, `review_target_minutes = 0`) get
      `review_target_minutes = ROUND(practice_target_minutes * maintenance_share)::int` and
      `acq_target_minutes = practice_target_minutes - review_target_minutes`
- [x] (2026-10-13) New CHECKs follow the `NOT VALID` then `VALIDATE` pattern
- [x] (2026-10-13) The `weekly_plan_states_shares_sum` CHECK (maintenance_share 0.10–0.55,
      acquisition_share 0.45–0.90, from `phase13_weekly_plan_states.sql`) is dropped and re-added
      relaxed (`maintenance_share` and `acquisition_share` each BETWEEN 0 AND 1 and
      `abs(sum - 1.0) <= 0.011`) `NOT VALID`, then validated after `COMMIT`. Revision (b): the shares are now **derived**
      (`maintenance = review / (review + acq_target_minutes)`, 1.00 / 0.00 when both are 0), and the relaxation is still
      required because derived values reach 1.0 / 0.0 (`new_words_per_day = 0`, `tests_only`, `practice` excluded).
      Without it the Tier B persist is rejected
- [x] (2026-10-13) The same file adds `dim_languages.new_word_minutes_est numeric(4,2) NULL` with
      CHECK `IS NULL OR BETWEEN 0.5 AND 15.0` (written nightly by TASK-870)
- [x] (2026-10-13) The same file defines the pure SQL helpers `new_words_for_day(int, numeric)`
      (`FLOOR(npd * weight + 0.5)`, 0 on weight <= 0 or npd <= 0, `IMMUTABLE`) and
      `new_word_minutes(smallint)` (`COALESCE(dim_languages.new_word_minutes_est, 3.0)`, `STABLE`)
- [x] (2026-10-13) The same file redefines `compute_weekly_plan_persist(uuid, smallint, date, jsonb)`:
      the six original keys stay required; the four new keys (`budget_scope` default
      `'tests_and_review'`, `review_target_minutes`, `new_words_target`, `acq_target_minutes` default 0) are **optional**;
      INSERT sets `new_words_completed`, `tail_completed_min`, `tail_new_words_completed` to 0; `ON CONFLICT DO UPDATE`
      writes the four new keys' columns from EXCLUDED and never touches `new_words_completed`, `tail_completed_min`,
      `tail_new_words_completed`; returns `to_jsonb(row)`
- [x] (2026-10-13) `migrations/phase13_compute_weekly_plan_helpers.sql` gets a header note that
      `compute_weekly_plan_persist` is superseded (the file is multi-object, so it is **not** archived)

**Technical Notes:**
The DDL is in [[features/session-modules.tech#Database Impact]]. Do **not** apply it live here.
TASK-869 does that. The CHECK list must equal `ALL_MODULES` in TASK-864. The budget DDL (Migration 1,
sections b–e) is specified in full in [[features/session-budget-settings.tech]]; copy it from there.
The file name stays `session_module_exclusions.sql`. Pattern per `migrations/CLAUDE.md`: single-pass
`UPDATE`, every new CHECK `NOT VALID` inside the transaction, `VALIDATE` as separate statements
after `COMMIT` (six constraints: the three `user_study_plans` ones plus the three `weekly_plan_states`
ones). Migration order in TASK-869: this file, `review_governor.sql` (TASK-874), the `build_daily_session` file (TASK-865). The `new_words_per_day` backfill is integer division (`daily_minutes / 6`, max 30).
**ANSWERED 2026-10-13:** the backfill reads `target_new_rate()` as words per day although the code documents it as per
week, so it is about 7x the old effective rate; the developer accepted this knowingly (see
[[features/session-budget-settings.tech]]); the review governor (TASK-874) and the forecast exist to manage the consequence.

**Files to Create / Modify:**
- `migrations/session_module_exclusions.sql` — new
- `migrations/phase13_compute_weekly_plan_helpers.sql` — header note only

**Verification:**
`psql` against a local/branch DB: run the file twice (no error), then
`UPDATE user_study_plans SET excluded_modules='{bogus}' …` fails with a CHECK violation, and
`UPDATE weekly_plan_states SET maintenance_share=1.0, acquisition_share=0.0 …` succeeds while
`0.6 / 0.6` is rejected.

---

## TASK-864: Tier B — `apply_module_exclusions` + `compute_weekly_plan` wiring

**Status:** [x] Done (code complete 2026-10-13; migrations not yet applied live)
**Feature:** session-modules
**Type:** feature
**Complexity:** M (3-8h)
**Depends On:** TASK-863, TASK-870, TASK-874

**Description:**
Add a pure, deterministic helper. It removes excluded modules from the template and rescales the
scalable remaining modules by one common factor, so the template's total minutes are preserved.
Wire it into `compute_weekly_plan` so persisted `target_counts` never contain an excluded module
and `review_target_minutes` is 0 when practice is excluded (`practice_target_minutes` is then 0).
(2026-10-13, revised (b)) Tier B also carries the new-word quota model: `rebalance_practice` sizes the practice pool and the
review share, in-budget acquisition minutes are `min(quota minutes, practice pool − review)`, the `tests_only` scope and a
`practice` exclusion move all vocabulary work to the optional tail, and the new-word and scope fields are computed and
persisted. There is **no** scale-up of tests and no extra-pool minutes.

**Acceptance Criteria:**
- [x] `MODULE_PRACTICE`, `ALL_MODULES` and `NON_SCALABLE_MODULES` constants exist in
      `services/study_plan_service.py`
- [x] `apply_module_exclusions(...)` matches the tech-spec algorithm, including the empty-set
      identity short-circuit, largest-remainder rounding with the `(remainder desc, key asc)`
      tie-break, and flashcards-only giving no redistribution
- [x] The ZH-30 worked example (exclude listening) gives reading 7, dictation 3, pinyin 1,
      classifier_drill 1, flashcards 7, dual_translation 2, practice 103
- [x] `compute_weekly_plan` selects `excluded_modules` and feeds the adjusted template into the
      weakness/bandit/`allocate_test_counts`/`rebalance_practice` steps
- [x] With practice excluded: `rebalance_practice` is skipped, `review = 0`, `acq_target_minutes = 0`,
      `practice_target_minutes = 0`, and there is no review carry-over
- [x] `tests/test_session_modules.py` covers every case under "Unit" in the spec's Testing
      Strategy, including `ALL_MODULES` equalling the SQL CHECK list parsed from the TASK-863 file
- [x] (2026-10-13, revised (b)) `rebalance_practice(daily_minutes, practice_total_minutes, flex_pct,
      base_maintenance_share, fsrs, bkt, weakness_global, cap_minutes) -> (practice_minutes, review_minutes,
      review_share)`: `practice_minutes = clamp(0, round(practice_total_minutes · flex_factor), cap_minutes)`
      (flex plus clamp to `daily_minutes·7`, as before the budget settings); `review_share = clamp(0.15,
      base_maintenance_share · (REVIEW_PRESSURE_OFFSET + maint_pressure), 0.50)` with `REVIEW_PRESSURE_OFFSET = 0.5`;
      `review_minutes = round(practice_minutes · review_share)`. The `ladder` argument and acquisition pressure are removed. The
      caller passes the template's **original** `practice_total_minutes`. Every existing caller and test is updated (breaking
      signature change)
- [x] (2026-10-13, revised (b)) `maintenance_share` / `acquisition_share` are persisted as **derived** values
      (`maintenance = round(review / (review + acq_target_minutes), 2)`, `acquisition = round(1 − maintenance, 2)`, 1.00 / 0.00 when both
      are 0), using the relaxed CHECK from TASK-863; the four new keys (`budget_scope`, `review_target_minutes`,
      `new_words_target`, `acq_target_minutes`) are passed to `compute_weekly_plan_persist` (redefined in TASK-863)
- [x] (2026-10-13, revised (b)) New constants `BUDGET_SCOPES`, `NEW_WORDS_MAX_PER_DAY = 50`,
      `REVIEW_TAIL_CAP_FRACTION = 0.5`, `REVIEW_PRESSURE_OFFSET = 0.5`, `TAIL_OFFER_MAX_MIN = 20`,
      `DEFAULT_WEEKDAY_SHAPE = (1.0,) * 7`; `BUDGET_SCOPES` equals the SQL CHECK list. (`REVIEW_EXTRA_CAP_FRACTION` and
      `EXTRA_REVIEW_MIN_CHUNK_MIN` do not exist)
- [x] (2026-10-13, revised (b)) With `budget_scope='tests_only'`: `eff_excluded = excluded ∪ {'practice'}` goes into
      `apply_module_exclusions` (its practice output is discarded; freed practice minutes go to tests/surfaces as in ADR-032);
      `practice_target_minutes = 0` and `acq_target_minutes = 0`; review is still sized from due pressure as a weekly **tail
      target**, `review ≤ cap = floor(daily_minutes·7·REVIEW_TAIL_CAP_FRACTION)`, with carry-over `min(review + round(CARRY_OVER_DECAY ·
      left), cap)` where `left = max(0, prior.review_target_minutes − prior.practice_completed_maint_min)`
- [x] (2026-10-13, revised (b)) With `tests_and_review` and `practice` not excluded: `P0, review, _ = rebalance_practice(…,
      cap_minutes = daily_minutes·7)`; review carry-over as above with `cap = daily_minutes·7`; `P = min(max(P0, review),
      daily_minutes·7)`; `acq_target_minutes = min(round(new_words_target · mpnw), P − review)`; `practice_target_minutes = P` (the
      spare `P − review − acq_target_minutes` stays in `P`; Tier C returns it to tests daily)
- [x] (2026-10-13, revised (b)) **Removed** (do not implement): `scale_up_to_target`, the shared `_largest_remainder_scale`
      factoring (`apply_module_exclusions` keeps its own step 6), `extra_weekly_minutes`
- [x] (2026-10-13) The shared `new_words_for_day(new_words_per_day, weight) -> int` is
      `0` if weight <= 0 or npd <= 0, else `int(math.floor(npd · weight + 0.5))` (**not** `round()`,
      which is banker's rounding); it mirrors SQL `public.new_words_for_day` and is used by Tier B
      (here), Tier C and ladder intake. `new_words_week_target(npd, shape) = Σ new_words_for_day(npd,
      w) for w in (shape or DEFAULT_WEEKDAY_SHAPE)` (shape is normalised to sum 7, so a 5-day shape gives
      each active day weight 1.4); `acq_quota_min = round(new_words_target · mpnw)`
- [x] (2026-10-13, revised (b)) `total_weekly_minutes = min(round(test_minutes + P), daily_minutes·7)`; new
      `typical_day_inputs(db, language_id, plan, week) -> {practice_room_min_per_day, review_min_per_day}` per the tech spec
      (used by TASK-866)
- [x] (2026-10-13, revised (b)) Tests (`tests/test_session_budget_settings.py`, new) cover: `new_words_for_day` ties
      (npd 5, w 1.1 → 6; npd 1, w 0.5 → 1) and Python/SQL agreement on a grid; `new_words_week_target`
      (all-ones = 7·npd; `[1.4]*5+[0,0]` with npd 5 → 35); `rebalance_practice` clamps and cap; both scopes persist the
      expected keys; derived shares sum to 1.00; `tests_only` and `practice`-excluded give `acq_target_minutes = 0` and
      `practice_target_minutes = 0`; with defaults `target_counts`, `practice_target_minutes` and `total_weekly_minutes` equal the
      pre-change values; review carry-over decays and respects the cap; new words are **not** carried over; `new_words_per_day = 0`
      gives `new_words_target = 0` and `acq_target_minutes = 0`; `typical_day_inputs`; `Config.NEW_WORD_MINUTES_DEFAULT` equals the SQL
      `new_word_minutes` fallback. The ZH-30 worked-example numbers in [[features/session-budget-settings.tech]] (scenarios A
      and B) are the fixtures
- [x] (2026-10-13, revised (b)) The default settings (`tests_and_review`, nothing excluded) leave the weekly counts and totals
      unchanged, so the regression suites that pin them stay green
- [x] `tests/test_weekly_plan_seeding.py` and `tests/test_plannable_surfaces.py` still pass

**Technical Notes:**
Memoise `_test_time_estimate` per `compute_weekly_plan` call (a dict). It hits the DB per skill,
and the helper and step 8 both need it. Keep the helper free of DB access by passing
`minutes_of` in. Do not touch `allocate_test_counts` itself. Order of steps is in "compute_weekly_plan changes" of
[[features/session-budget-settings.tech]].

**Files to Create / Modify:**
- `services/study_plan_service.py` — constants, helpers, `rebalance_practice`, `compute_weekly_plan` wiring, `typical_day_inputs`
- `tests/test_session_modules.py` — new
- `tests/test_session_budget_settings.py` — new (2026-10-13)

**Verification:**
`pytest tests/test_session_modules.py tests/test_session_budget_settings.py tests/test_weekly_plan_seeding.py tests/test_plannable_surfaces.py -q`
passes.

---

## TASK-865: Tier C — `build_daily_session` honours `excluded_modules`

**Status:** [~] In Progress (2026-10-13: code written and the migration compiles on Postgres 16; the build_daily_session scenarios in tests/sql/test_session_budget_settings.sql and test_session_module_exclusions.sql have NOT been run, they need the full live schema plus the unapplied user_word_watchlist/word_upload prerequisites; not applied live)
**Feature:** session-modules
**Type:** feature
**Complexity:** M (3-8h)
**Depends On:** TASK-863, TASK-874

**Description:**
Redefine `build_daily_session` so it reads `v_plan.excluded_modules`. It filters excluded keys
out of the TASK-732 budget split and the candidate pool, drops practice when
`practice` is excluded, and keeps retry and word_upload off excluded test types. This is defence
in depth on top of TASK-864. It also echoes `excluded_modules` into `daily_session_targets`.

(2026-10-13, revised (b)) The function keeps **one** pool. The in-budget practice share (the TASK-732 split) exists only when
`budget_scope='tests_and_review'` and `practice` is not excluded. It is filled directly, not by a greedy loop: **due reviews first**,
then **whole new words** from the governed quota, and any unused share minutes **return to the test budget**. The old extra pool
(`x_acq` / `x_maint`, own budget, 1.5x cap) is not built. The optional tail is derived live by the session route (TASK-872), not by
this function. The function reads the governor and `minutes_per_new_word` through the SQL helpers from TASK-874 and TASK-863
(3.0 fallback), so it does not wait for TASK-870's nightly estimate.

**Acceptance Criteria:**
- [x] New `migrations/session_module_exclusions_build_daily_session.sql`, built from the **live**
      `pg_get_functiondef` (confirm the `word_upload` marker is present), with all nine edits
      from the tech spec, each tagged `-- session-modules`, plus the budget edits below, each tagged
      `-- session-budget`
- [x] `migrations/word_upload_slot_scheduling.sql` gets a header note that its function body is
      superseded. It is **not** archived, because it is the only record of
      `last_matched_surfaced_at`
- [ ] `tests/sql/test_session_module_exclusions.sql` covers four cases: (a) an excluded test
      skill is absent from `test_ids` and `requested_counts`; (b) retry and word_upload skip
      excluded types; (c) `{practice}` gives `practice_*_min = 0` and `practice_budget_minutes = 0`;
      (d) a same-day re-run after excluding a skill keeps that skill's completed slot
- [ ] With `excluded_modules = '{}'`, `budget_scope = 'tests_and_review'` and `new_words_per_day = 0`, the test/surface output equals the
      pre-change function's for the same fixture (the practice side is now reviews-first and unused minutes return to tests)
- [x] (2026-10-13, revised (b)) New DECLAREs and setup: `v_scope := v_state.budget_scope`; `v_practice_in := (v_scope = 'tests_and_review' AND
      NOT 'practice' = ANY(v_excluded))`; `v_npd := v_plan.new_words_per_day` (live); `v_quota := public.new_words_for_day(v_npd, v_weekday_w)`;
      `v_mpnw := public.new_word_minutes(p_language_id)`; `v_gov := public.review_governor_state(p_user_id, p_language_id, p_date)`;
      `v_level` = `'normal'` if `practice` excluded else `v_gov->>'level'`; `v_new_eff := public.new_words_effective(v_quota, v_level)`;
      `v_due_min` = 0 if `practice` excluded else `(v_gov->>'due_minutes')::numeric`
- [x] (2026-10-13, revised (b)) `v_practice_minutes_total := GREATEST(0, practice_target_minutes − practice_completed_maint_min −
      practice_completed_acq_min)` when `v_practice_in`, else 0. `v_practice_budget` / `v_test_budget` come from the existing TASK-732
      formula. The practice-side candidate INSERTs (`'maint'`, `'acq'`) and the practice greedy loop are **deleted**. Assignment:
      `v_r_main := LEAST(v_practice_budget, v_due_min)`; `v_s_words := LEAST(v_new_eff, GREATEST(0, v_new_eff − v_prior_shortfall),
      FLOOR((v_practice_budget − v_r_main)/v_mpnw))` (0 unless `v_practice_in`); `v_a_main := v_s_words · v_mpnw`;
      `v_returned := GREATEST(0, v_practice_budget − v_r_main − v_a_main)`; `v_test_budget := v_test_budget + v_returned`;
      `v_maint_min := ROUND(v_r_main)`, `v_acq_min := ROUND(v_a_main)` (the runner still reads `practice_maintenance_min` /
      `practice_acquisition_min`); `v_used_min := v_used_min_test + v_maint_min + v_acq_min`
- [x] (2026-10-13, revised (b)) `v_prior_shortfall` / `v_prior_checked`: read from the existing `daily_test_loads.daily_session_targets` for
      `p_date` before the row is replaced; the prior shortfall counts only if `new_words_supply_checked` is true, else 0
- [x] (2026-10-13, revised (b)) `daily_session_targets` adds `budget_scope`, `new_words_quota`, `new_words_effective`, `new_words_in_budget`,
      `new_words_shortfall`, `new_words_supply_checked`, `governor_level`, `review_due_minutes`, `review_main_minutes`,
      `new_word_main_minutes`, `returned_to_tests_minutes`. `practice_budget_minutes` means the in-budget practice share (0 when
      `v_practice_in` is false); `today_budget_minutes` stays in-budget only. There is no `extra_budget_minutes` and no
      `review_budget_minutes`
- [x] (2026-10-13, revised (c)) Shortfall seed (Anki-like quota; replaces the former `v_admitted_today` count): `v_local_midnight := p_date::timestamp AT TIME ZONE
      COALESCE(v_plan.timezone,'UTC')`; `v_lw := public.ladder_new_word_state(p_user_id, p_language_id, v_local_midnight)` (defined in `migrations/review_governor.sql`, TASK-874, applied first);
      `v_unstarted := (v_lw->>'unstarted')::int` (admitted ladder rows with no `exercise_attempts` row for the sense), `v_started_today := (v_lw->>'started_today')::int` (first-ever attempt on or
      after local midnight); `v_shortfall := GREATEST(0, v_new_eff − (v_unstarted + v_started_today))`. DECLAREs `v_lw jsonb; v_unstarted int; v_started_today int` replace `v_admitted_today`.
      Tier C keeps `S = min(E, floor(remaining / minutes_per_new_word))` for the in-budget share
- [x] (2026-10-13, revised (b)) The same file defines `set_new_words_shortfall(uuid, smallint, date, int)` (`SECURITY DEFINER`, pinned `search_path`,
      `jsonb_set` on `new_words_shortfall` **and** `new_words_supply_checked = true`, EXECUTE revoked from `PUBLIC, anon, authenticated`)
- [ ] (2026-10-13, revised (b)) `new_words_per_day = 0` gives `new_words_effective = 0` and no new-word minutes; rest days (weekday weight 0) give `Q = 0`; `practice`
      excluded or `tests_only` gives `practice_*_min = 0` (all vocabulary work is in the tail)
- [ ] (2026-10-13, revised (b)) SQL tests (`tests/sql/test_session_budget_settings.sql`, new): scenario A Monday of the worked example (18 due items →
      6.0 review min, 1 new word, 2.07 min returned to tests, ~21 test min) and scenario B (all 30 min to tests); governor `reduced` and `paused` change
      `new_words_effective`, `new_words_in_budget` and `returned_to_tests_minutes`; `{practice}` excluded with `new_words_per_day > 0` gives
      `practice_*_min = 0`; a same-day rebuild with `new_words_supply_checked = true` and a shortfall lowers `new_words_in_budget` and raises the test budget,
      and without the flag ignores the prior shortfall; weight-0 day gives `Q = 0`; `daily_session_targets` carries the new keys; same-day rebuild keeps
      completed slots (TASK-705); lowering `new_words_per_day` below the number already admitted does not un-admit anything

**Technical Notes:**
Use `<> ALL(v_excluded)`, not `NOT IN`, because the array may be empty. The surface hydration
reads `skill_counts`, so it needs no change. TASK-705 carry-over is deliberately left unchanged.
This task seeds `new_words_shortfall` (words still to admit at build time); the ladder intake
(TASK-871) overwrites it with the final unmet count through `set_new_words_shortfall`, which also sets the supply flag so the next
rebuild plans only servable words. The governor helpers live in `migrations/review_governor.sql` (TASK-874), which is applied before this file.

**Files to Create / Modify:**
- `migrations/session_module_exclusions_build_daily_session.sql` — new
- `migrations/word_upload_slot_scheduling.sql` — header note only
- `tests/sql/test_session_module_exclusions.sql` — new
- `tests/sql/test_session_budget_settings.sql` — new (2026-10-13)

**Verification:**
Run the SQL tests against a Supabase branch or local DB in the same way as
`tests/sql/test_task705_same_day_safe.sql`. All assertions pass.

---

## TASK-866: API — `excluded_modules` on GET/PUT `/api/study-plan` + immediate rebuild

**Status:** [x] Done (code complete 2026-10-13; migrations not yet applied live)
**Feature:** session-modules
**Type:** feature
**Complexity:** M (3-8h)
**Depends On:** TASK-864, TASK-865, TASK-874

**Description:**
Expose and validate the setting. When it changes, recompute the learner-local current week and
re-resolve today's not-yet-completed slots, so the change applies immediately.

**Acceptance Criteria:**
- [x] GET returns `plan.excluded_modules` and `available_modules` (the union of all of the
      language's template keys ∩ `ALL_MODULES`, plus `practice`, in `ALL_MODULES` order)
- [x] PUT validates through `_validate_excluded_modules`, with three 400 cases: not a list of
      strings, a module not offered for the language, and all modules excluded
- [x] `'excluded_modules'` is in the `is_template_only` exclusion tuple
- [x] Only when the value changed: `compute_weekly_plan(…, _monday_of(plan_today(…)))` runs, then
      `StudyPlanService.rebuild_today` (new) when `STUDY_PLAN_ENABLED`. Both are best-effort, and
      a failure logs a WARNING and still returns 200
- [x] The response includes `session_rebuilt`
- [x] (2026-10-13, revised (b)) GET adds `budget_scope`, `new_words_per_day` to the plan SELECT and
      `budget_scope, review_target_minutes, new_words_target, new_words_completed, acq_target_minutes,
      tail_completed_min, tail_new_words_completed` to the week SELECT (no `extra_weekly_minutes`); the response adds
      `minutes_per_new_word` (`get_minutes_per_new_word`, TASK-870), `typical_day` (`typical_day_inputs`, TASK-864),
      `governor` (`get_review_governor`, TASK-874; level `normal` on failure), `forecast` (`{reviews_per_new_word_30d, item_seconds,
      min_per_day}`, `min_per_day` from `review_forecast_min_per_day`) and `today_new_words_shortfall` (from
      `daily_test_loads.daily_session_targets.new_words_shortfall` for `plan_today`, null if no row)
- [x] (2026-10-13) PUT validates `budget_scope` (`"budget_scope must be 'tests_and_review' or
      'tests_only'"`) and `new_words_per_day` (int, not bool or float, in [0, 50]: `"new_words_per_day
      must be int in [0, 50]"`), 400 on violation
- [x] (2026-10-13) Cross-field rules run on the **merged** state (request value, else stored) whenever
      any of the three fields is present: empty `included` with effective `new_words_per_day == 0` →
      `"at least one module must remain included"`; `tests_only` with `included − {'practice'}` empty →
      `"tests_only scope needs at least one test or surface module included"`
- [x] (2026-10-13) New-row default: in the template-only branch, if no plan row existed before
      `apply_study_plan_template`, afterwards `UPDATE user_study_plans SET new_words_per_day =
      max(1, daily_minutes // 6)` (words **per day**; the RPC does not set the column, so the DB default 5 would apply).
      Changing `daily_minutes` or the template on an existing row does not recompute it
- [x] (2026-10-13) The `is_template_only` tuple also lists `budget_scope` and `new_words_per_day`
- [x] (2026-10-13) A change to **any** of `excluded_modules`, `budget_scope`, `new_words_per_day`
      triggers the recompute and `rebuild_today`
- [x] (2026-10-13) `_validate_excluded_modules` treats `new_words_per_day > 0` as included (all
      modules may be excluded only if `new_words_per_day > 0`)
- [x] `rebuild_today` only calls the RPC when today's `daily_test_loads` row exists
- [x] `tests/test_session_modules_routes.py` covers the cases under "Route" in the spec
- [x] (2026-10-13) `tests/test_session_budget_settings_routes.py` (new) covers each validation message,
      the merged-state rules, the new-row default, recompute/rebuild only on change, `session_rebuilt`
      and the GET shape

**Technical Notes:**
`plan_today` is in `services.day_boundary`. Compare the requested value against the stored value
after normalisation (dedupe and sort), so a no-op save doesn't trigger a rebuild. Update the
module docstring's endpoint table.

**Files to Create / Modify:**
- `routes/study_plan.py` — GET/PUT changes and the validator
- `services/study_plan_service.py` — `rebuild_today`
- `tests/test_session_modules_routes.py` — new
- `tests/test_session_budget_settings_routes.py` — new (2026-10-13)

**Verification:**
`pytest tests/test_session_modules_routes.py tests/test_session_budget_settings_routes.py -q` passes. Then run it manually on a local server:
PUT `{language_id, excluded_modules:["listening"]}`, and the next `GET /api/study-session` has
no listening items.

---

## TASK-867: Session runner + legacy fallback honour exclusions

**Status:** [x] Done (code complete 2026-10-13; migrations not yet applied live)
**Feature:** session-modules
**Type:** feature
**Complexity:** S (1-3h)
**Depends On:** TASK-865

**Description:**
Suppress the speed-round tail when `practice` is excluded, using
`daily_session_targets.excluded_modules` with no new query. Make the legacy `_compute_daily_load`
fallback skip excluded test types when a plan row exists.

**Acceptance Criteria:**
- [x] `routes/study_session.py` sets `speed_round_available = False` when
      `'practice' in targets.get('excluded_modules', [])`
- [x] `TestService._compute_daily_load` drops retry and recommended candidates whose `test_type`
      is excluded, reading `excluded_modules` from `user_study_plans`. With no row there is no
      filter
- [x] Tests cover both cases. Existing `tests/test_daily_load_retry_slot.py` stays green

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

## TASK-868: Settings UI — "Daily session" card (layout Option A) + i18n

**Status:** [x] Done (code complete 2026-10-13; migrations not yet applied live)
**Feature:** session-modules
**Type:** feature
**Complexity:** M (3-8h)
**Depends On:** TASK-866

**Description:**
Add a toggle card to `/study-plan` so learners can include or exclude modules per language. The
last included toggle can't be switched off, and a hint appears when only flashcards remains.
Save sends `excluded_modules` with the existing PUT.

(2026-10-13, revised (b)) The card becomes **"Daily session"**: budget-scope radios, the module toggles, a
new-words-per-day input with a review forecast, and a typical-day summary. **Layout resolved: Option A, a single card with
stacked sections** (ANSWERED 2026-10-13; Options B and C are dropped). This task resolves the layout open question; nothing is
left pending. The governor message and the end-of-session prompt on the session page belong to TASK-872.

**Acceptance Criteria:**
- [x] The card sits between "Weekday shape" and "Advanced", with one `form-switch` per
      `available_modules` entry; checked means included
- [x] With one toggle left on, it is disabled with the `last_one` tooltip
- [x] With only flashcards on, `#moduleShortHint` is visible
- [x] Save includes `excluded_modules`, and when `session_rebuilt` is true the success banner
      uses the `session_rebuilt` copy
- [x] All `study_plan.modules.*` keys are present in `en`, `zh`, `ja` and `es`. zh/ja use the
      in-app terms already used for those skills elsewhere in the i18n files
- [x] `eslint .` reports 0 errors
- [ ] (2026-10-13, revised (b)) **Option A layout:** one `.card` titled "Daily session" with four `<section>` blocks in one column, separated by `<hr>`,
      in this order: (1) scope radios `input[name=budgetScope]` (`tests_and_review` / `tests_only`; `tests_only` disabled when no test or surface module is
      checked), (2) `#moduleToggles` (same markup as the former "Daily session modules" card), (3) new words, (4) typical day. Same order and single
      column at phone width; no tabs, no nested cards
- [x] (2026-10-13, revised (b)) Section 3: `<input type="number" id="newWordsInput" min="0" max="50" step="1">` ("words per day"); `#newWordsHint` ("About {inBudgetWords}
      of these fit inside your {daily} min; the rest come in an optional extra round after your session." / under `tests_only` or `practice` excluded "New
      words come in an optional extra round after your session."); `#reviewForecast` beside the input: **"≈ +{X} min/day of reviews in a month"**, `X = round(avgNewWords ·
      forecast.reviews_per_new_word_30d · forecast.item_seconds / 60)`, `avgNewWords = new_words_week_target(input, weekday_shape) / 7` (constants come from the
      GET response; the client hard-codes neither 7 nor 20); `#governorNote` shows `study_plan.daily_session.governor.paused` / `.reduced`
      (**"New words paused — catching up on {n} reviews"** / "reduced") when `governor.level != 'normal'`
- [x] (2026-10-13, revised (c)) Under `#newWordsInput`, `#newWordsNoReviewWarning` (`.form-text text-warning`) is visible when the `practice` (Vocabulary review) toggle is unchecked **and**
      the input is > 0, with `T('study_plan.session.new_words_no_review_warning')` = **"Vocabulary review is off — words you learn won't be reviewed."** (add the key in en/zh/ja/es). Advisory only:
      Save is not blocked and `PUT /api/study-plan` does not reject `excluded_modules` containing `practice` with `new_words_per_day > 0` (all new words then go to the optional tail). Under `tests_only`
      with Vocabulary review still checked there is no warning. `#reviewForecast` is an estimate ("≈", as in the string above); its `item_seconds` is the all-vocabulary-exercise median
- [x] (2026-10-13, revised (b)) Section 4: `#typicalDaySummary` from `typical_day`, `minutes_per_new_word` and the input: `inBudgetWords = min(input,
      floor(typical_day.practice_room_min_per_day / mpnw))` (0 under `tests_only` / `practice` excluded), `tailWords = input − inBudgetWords`. Text, scope
      `tests_and_review`: "Typical day: {daily} min (about {inBudgetWords} new words and ~{review_min_per_day} min of review inside it). Optional extra round:
      ~{tailWords} new words (~{round(tailWords·mpnw)} min)." (second sentence omitted when `tailWords = 0`); scope `tests_only`: "Typical day: {daily} min of
      tests. Optional extra round: ~{review_min_per_day} min of review and {input} new words (~{round(input·mpnw)} min)." (omitted with no current week)
- [x] (2026-10-13, revised (b)) `#totalTally` and the per-language `.lang-summary` show `daily_minutes` only; optional-round minutes are **not** added
- [x] (2026-10-13) A toggle is disabled only when it is the last checked one **and** `#newWordsInput`
      is 0
- [x] (2026-10-13) The practice toggle is labelled "Vocabulary review" in en/zh/ja/es
      (`study_plan.modules.practice`)
- [x] (2026-10-13, revised (b)) The `/study-plan` page `#weekStats` shows a "New words: {new_words_completed} / {new_words_target}" tile (plus "{tail_completed_min} min in
      optional rounds" when above 0), and a note `study_plan.daily_session.shortfall` when `today_new_words_shortfall > 0`
- [x] (2026-10-13, revised (b)) i18n keys added in en/zh/ja/es: `study_plan.daily_session.title`, `.scope.tests_and_review`, `.scope.tests_only`, `.scope.hint`,
      `.new_words.label`, `.new_words.unit`, `.new_words.hint_in_budget`, `.new_words.hint_tail_only`, `.forecast`, `.typical_day`, `.typical_day_tail`,
      `.typical_day_tests_only`, `.shortfall`, `.last_module_hint`, `.governor.paused`, `.governor.reduced`, `study_plan.stats.new_words`, and `study_plan.session.new_words_no_review_warning`

**Technical Notes:**
Follow the existing `T()` helper and `data-i18n` patterns in `templates/study_plan.html`. Reuse
the existing skill labels from the i18n files where present rather than writing new
translations. The skill-override list needs no change. The preview needs only `typical_day`, `minutes_per_new_word`, `forecast`
and `weekday_shape` from GET, none of which depend on the unsaved new-words value.

**Files to Create / Modify:**
- `templates/study_plan.html` — the card, state and save body
- `static/i18n/en.json`, `zh.json`, `ja.json`, `es.json` — the new keys

**Verification:**
Run the app (`/run`). On `/study-plan` for zh, untick Listening and Pinyin, then save. The
banner confirms the rebuild, and `/session` shows no listening or pinyin items while the total
minutes stay about the same. Try to untick the last module: it is disabled. Change the new-words box from 5 to 10: the
forecast, hint and typical-day line update without saving.

---

## TASK-869: Live rollout — apply migrations + end-to-end check (user-approved)

**Status:** [ ] Not Started
**Feature:** session-modules
**Type:** infra
**Complexity:** S (1-3h)
**Depends On:** TASK-863, TASK-864, TASK-865, TASK-866, TASK-867, TASK-868, TASK-870, TASK-871, TASK-872, TASK-873, TASK-874

**Description:**
Apply the six migrations to the live DB after the developer approves, deploy the code, run the
weekly recompute (`_run_weekly_plan_recompute`) so every in-flight week has the new columns, and verify
on the test account that excluding a module removes it from the current week and today's
session while completed work is kept.

**Acceptance Criteria:**
- [ ] The developer approves before any live DB write
- [ ] Migrations are applied in this order: `session_module_exclusions.sql` (TASK-863), then `review_governor.sql`
      (TASK-874), then `session_module_exclusions_build_daily_session.sql` (TASK-865), then `new_word_minutes_estimate.sql`
      (TASK-870), then `new_words_completed_accrual.sql` (TASK-872), then `calibration_bkt_evidence.sql` (TASK-873). The live
      `pg_get_functiondef` of `build_daily_session` contains the `session-modules` and `session-budget` markers
- [ ] With the plan at `'{}'`, today's rebuild output is unchanged from before (spot check on the
      test account)
- [ ] Excluding `listening` on the test account removes listening from
      `weekly_plan_states.target_counts` and from today's `daily_test_loads.test_ids` (except
      completed slots), with `today_budget_minutes` about unchanged
- [ ] [[database/schema.tech]] and [[features/study-plans.tech]] (HTTP endpoints table) are updated
- [ ] (2026-10-13, revised (b)) Rollout covers the new columns: `budget_scope`, `new_words_per_day` (with the
      backfill) on `user_study_plans`, the new `weekly_plan_states` columns and `calibration_sessions.bkt_applied_at`; verify the
      backfill (`new_words_per_day = max(1, daily_minutes // 6)`, words per day, about 7x the old rate: accepted) and that, with
      `new_words_per_day` at its backfilled value, the main session length still equals `daily_minutes` and the optional tail appears
      at session end

**Technical Notes:**
Apply with the same `supabase db query --linked` flow used for TASK-861. Revert the test account
to `'{}'` afterwards.

**Prerequisites found 2026-10-13 (integration pass, live schema read-only check):** the live DB has NO
`user_word_watchlist` table and its `build_daily_session` has no `word_upload` block (live matches
`word_upload_slot_scheduling.sql` minus that block and comments). The new `build_daily_session` keeps the
word_upload block, so `migrations/user_word_watchlist_schema.sql` and `migrations/word_upload_slot_scheduling.sql`
must be applied BEFORE `session_module_exclusions_build_daily_session.sql`, or the function fails at runtime
(also noted in that file's header). Also run `tests/sql/test_session_budget_settings.sql` Part 1 and
`tests/sql/test_session_module_exclusions.sql` on a Supabase branch first; they have not been run (only Part 2
ran, on a stub Postgres 16). `compute_weekly_plan_load_signals` needs no redefinition: its `prior_week` is
`to_jsonb(weekly_plan_states row)` and so carries `review_target_minutes` once Migration 1 is applied.

**Files to Create / Modify:**
- `wiki/database/schema.tech.md`, `wiki/features/study-plans.tech.md`, `wiki/log.md`

**Verification:**
Run the SQL probes listed above and load `/session` on the test account.

---
