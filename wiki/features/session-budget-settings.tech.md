---
title: Session Budget Settings — Technical Specification
type: feature-tech
status: planned
prose_page: ./session-budget-settings.md
last_updated: 2026-10-13
dependencies:
  - "table: user_study_plans (new columns excluded_modules, budget_scope, new_words_per_day)"
  - "table: weekly_plan_states (new columns budget_scope, review_target_minutes, new_words_target, new_words_completed, acq_target_minutes, tail_completed_min, tail_new_words_completed; constraint weekly_plan_states_shares_sum relaxed)"
  - "table: dim_languages (new column new_word_minutes_est)"
  - "table: calibration_sessions (new column bkt_applied_at; existing mode, word_language_id, ended_at), calibration_responses (read: anchor_sense_id, is_correct, answered_at, session_id)"
  - "table: daily_test_loads (daily_session_targets jsonb gains keys)"
  - "table: user_word_ladder (created_at task741; review_due_at), user_flashcards (due_date), exercise_attempts (time_taken_ms, sense_id), user_vocabulary_knowledge, question_attempt_results, test_attempts, tests (vocab_sense_ids), questions (sense_ids, test_id)"
  - "RPC: build_daily_session (redefined, carries session-modules TASK-865 filters)"
  - "RPC: compute_weekly_plan_persist (redefined), record_session_progress (redefined, new args p_sense_id, p_is_tail)"
  - "RPC: update_vocabulary_from_word_tests_batch (existing, migrations/bkt_word_test_batch.sql; called by calibration /end, unchanged)"
  - "RPC (new): new_words_for_day, new_word_minutes, set_new_words_shortfall, refresh_new_word_minutes, plan_local_day_start, ladder_new_word_state, review_item_seconds, review_governor_state, review_governor_level, new_words_effective"
  - "service: services/study_plan_service.py (Tier B), services/practice_session_service.py (ladder intake, tail ordering), services/day_boundary.py, services/calibration_service.py (end_session), services/vocabulary/knowledge_service.py (update_from_word_tests_batch)"
  - "routes: routes/study_plan.py, routes/study_session.py, routes/calibration.py (/end)"
  - "template: templates/study_plan.html, templates/study_session.html + static/js/session/controller.js + static/i18n/{en,zh,ja,es}.json"
  - "feature: session-modules (this spec amends TASK-863, 864, 865, 866, 868, 869)"
  - "feature: lookahead-preteaching (Queue B; not yet built)"
  - "feature: calibration (cold-start evidence, 4B)"
breaking_change_risk: high
open_questions:
  - "ANSWERED 2026-10-13: Daily session card layout = Option A, single card with stacked sections (TASK-868)."
  - "ANSWERED 2026-10-13: cold start = 4A + 4B. 4A: the intro tests' evidence (Queue A1). 4B: calibration (definition mode only) writes BKT evidence at /end (TASK-873); a single wrong calibration answer admits a sense to Queue A2, ranked below test and word-quiz evidence. Verified facts are in 'Cold start' below."
  - "ANSWERED 2026-10-13: backfill unit. new_words_per_day default and backfill = max(1, daily_minutes // 6) PER DAY (5/day at 30 min). target_new_rate() is documented as per WEEK (study_plan_service.py lines 86-88), so this is about 7x the old rate; accepted knowingly. The review forecast (below) makes the resulting review load visible."
  - "ANSWERED 2026-10-13: the 'extra pool outside the budget' model, the 'freed acquisition minutes scale tests up' mechanism and extra_weekly_minutes are removed (ADR-033 Revision 2026-10-13 (b))."
  - "OPEN: weekday-shape scaling of new words (new_words_for_day multiplies by the normalised weight) differs from the design text 'words per active day, 0 on rest days'."
  - "ANSWERED 2026-10-13: new_words_completed counts words STARTED on that local day (see 'Quota semantics'): the first-ever exercise_attempts row for the (user, sense) falls on the day, whether the word was admitted that day or earlier, in the main session or the tail."
  - "ANSWERED 2026-10-13: Vocabulary review excluded (or tests_only) with new_words_per_day > 0 is ALLOWED and not rejected by the API. The in-budget practice share is 0, so all new words go to the optional tail. The settings page shows i18n study_plan.session.new_words_no_review_warning under the new-words input."
  - "ANSWERED 2026-10-13: quota semantics are Anki-like. new_words_per_day counts words STARTED per local day, not words admitted. Admitted-but-unstarted words carry over and are served first; intake only tops up so that (unstarted admitted + started today) reaches the effective quota E. The old rollover rule is removed (see 'Quota semantics')."
  - "OPEN: REVIEWS_PER_NEW_WORD_30D = 7 and the steady-state forecast formula (no division by 30; see 'Review forecast')."
  - "ANSWERED 2026-10-13: for v1 review_item_seconds uses the median of ALL the learner's timed vocabulary-exercise attempts (no review-only filter; exercise_attempts has no maintenance flag). The review forecast is an estimate and is labelled as one in the UI."
  - "ANSWERED 2026-10-13: an explicit skip ('I don't know', calibration_responses.chosen_sense_id IS NULL AND answered_at IS NOT NULL AND is_correct = false) counts as WRONG evidence for BKT (TASK-873) and for Queue A2. Items never answered (answered_at IS NULL, session abandoned) are ignored. Exact predicate in 'Cold start' below."
  - "OPEN: tunables without data: RECENT_TEST_WINDOW_DAYS=28, REVIEW_PRESSURE_OFFSET=0.5, NEW_WORD_MINUTES_DEFAULT=3.0, REVIEW_BACKLOG_THRESHOLD_DAYS=1.0, REVIEW_ALLOWANCE_FLOOR_MIN=3.0, REVIEW_ITEM_SECONDS_DEFAULT=20.0, TAIL_OFFER_MAX_MIN=20, CALIBRATION_EVIDENCE_MAX_AGE_DAYS=90."
---

# Session Budget Settings — Technical Specification

## Architecture Overview

One settings card ("Daily session") drives three per-language settings stored on
`user_study_plans`:

| Setting | Column | Meaning |
|---|---|---|
| Module include/exclude | `excluded_modules text[]` | Unchanged from [[features/session-modules.tech]], except `practice` now means **Vocabulary review** only |
| Budget scope | `budget_scope text` | `'tests_and_review'` (default) or `'tests_only'`: whether vocabulary review (and the new-word practice share) sits inside `daily_minutes` |
| New words per day | `new_words_per_day smallint` | 0..50, an **Anki-style daily quota** of new words. It is not a separate time pool |

### Day model

```
Daily session = MAIN SESSION (inside daily_minutes)  +  OPTIONAL TAIL (outside, never required)

main  = tests + surfaces (flashcards, dual_translation)
        + [scope = tests_and_review AND practice not excluded]:
            in-budget practice share  =  due reviews first, then as many of today's new words as fit
        - unused practice-share minutes return to tests

tail  = due reviews that did not fit (most-overdue first)
        then the remaining new words  (E − started today; admitted-but-unstarted words are served first)
        ordered reviews BEFORE new words; counted toward weekly targets; not needed for completion
```

Rules:

- The **quota** `Q = new_words_for_day(new_words_per_day, weekday weight)`. The review-load
  **governor** turns it into the **effective quota** `E` (`Q`, `floor(Q/2)` or `0`).
- Tier C fits what it can of `E` inside the in-budget practice share: `S` words (`S <= E`). The
  rest, `E - S`, are served in the tail.
- Under `budget_scope = 'tests_only'`, or when `practice` (Vocabulary review) is excluded, the
  in-budget pool holds only tests and surfaces. **All review and all new words go to the tail.**
- If the supply gate or cold start yields fewer new words than planned, the unused minutes return to
  tests inside the budget. The budget is never left empty.
- `flashcards` and `dual_translation` are "tests" for scope purposes (in-budget under both scopes).
  "Exercises" means only the vocabulary ladder practice: **review** (FSRS/BKT maintenance plus the
  speed-round tail, the `practice` module) and **new-word acquisition** (`new_words_per_day`, not a module).
- `weekly_plan_states.total_weekly_minutes` is the in-budget weekly total (clamped to
  `daily_minutes * 7`) = tests/surfaces minutes + `practice_target_minutes`.
- `new_words_per_day > 0` with Vocabulary review excluded (or `budget_scope = 'tests_only'`) is **allowed**. The API
  does not reject it. The in-budget practice share is 0, so all new words go to the optional tail. The settings
  UI shows a warning under the new-words input (see the page component).

### Quota semantics (decided 2026-10-13, Anki-like)

`new_words_per_day` counts words **started** per local day, not words admitted.

- **Started (exact definition).** A word is the ladder row `(user_id, sense_id)` in `user_word_ladder`. Its
  `started_at` is `MIN(exercise_attempts.created_at)` over the rows of `exercise_attempts` with that `user_id` and
  `sense_id` (the denormalised column added by `migrations/exercise_scheduling.sql`; written by `record_attempt_with_updates`,
  `services/practice_session_service.py` around line 525, for every first or repeat attempt on a ladder or
  acquisition exercise). No attempt row: `started_at IS NULL` (the word is **unstarted**). A word is
  **started today** when `started_at >= local_day_start` (00:00 of the learner's local date,
  `local_day_start_utc(tz)`, [[decisions/ADR-022-local-day-boundary]]). Any attempt counts, right or wrong, retries
  included; the first one fixes `started_at` forever, so a word is started on exactly one day.
  Verified 2026-10-13: `user_word_ladder` has `created_at` (added by `migrations/task741_pack_key_words_bridge.sql`) but no
  first-attempt column; `exercise_attempts` columns are `id, user_id, exercise_id, user_response, is_correct, created_at`
  plus `exercise_type, sense_id` (`exercise_scheduling.sql`), `is_first_attempt, ladder_level, time_taken_ms`
  (`vocabulary_ladder_schema.sql`) and `p_known_before/after` (`task534`). `is_first_attempt` is per exercise, not per
  sense, so it is **not** used. There is no separate acquisition-attempt table.
  Known limitation: `exercise_attempts` rows written before `exercise_scheduling.sql` have `sense_id IS NULL` and are
  invisible; a legacy ladder word whose only attempts are such rows counts as unstarted and is simply served first.
- **Three counts per learner, language and local day** (one RPC, `ladder_new_word_state`, Migration 5): `U` = unstarted
  admitted words, `ST` = words started today (admitted today or earlier), `E` = effective quota (after the governor).
- **Intake tops up, never over-fills:** `want_raw = E - (U + ST)`; `want = min(max(want_raw, 0), LADDER_TOPUP_MAX_PER_CALL)`.
  Admitted-but-unstarted words **carry over** from earlier days and are counted in `U`, so they are served first and
  reduce today's intake one for one. There is no rollover rule and no separate "owed" counter.
- **Serving order:** within acquisition, never-attempted ladder senses are served first, oldest `user_word_ladder.created_at`
  first (`ladder_new_word_state.unstarted_sense_ids` is in that order), before any sense whose ladder is already in progress.
- **Remaining quota today:** `new_words_left = max(0, min(E - ST, U_now))` where `U_now` is `U` after this call's admissions.
  This drives the tail and the Tier C seed. `new_words_shortfall = max(0, want_raw - len(fresh))` (words the supply gate could
  not provide).
- **Weekly counter:** `weekly_plan_states.new_words_completed` counts words started that local day (same definition),
  once per sense (Migration 4).
- Worked: `E = 5`; yesterday 3 admitted words were never started (`U = 3`), nothing started today (`ST = 0`):
  `want_raw = 5 - 3 = 2`, so 2 are admitted. After the learner starts 4 words (`ST = 4`, `U = 1`):
  `want_raw = 5 - 5 = 0`; `new_words_left = min(5 - 4, 1) = 1`.

### Data flow

```
PUT /api/study-plan {excluded_modules?, budget_scope?, new_words_per_day?}
   │ validate (merged with stored values) → UPDATE user_study_plans
   ├─► Tier B  compute_weekly_plan(current LOCAL week)
   │     apply_module_exclusions(excluded ∪ {'practice' if tests_only})
   │     rebalance_practice → practice pool P, review (due pressure)
   │     acq_target = min(quota minutes, P − review)           (0 if no in-budget practice)
   │     compute_weekly_plan_persist (+ new keys; preserves new_words_completed, tail_*)
   └─► Tier C  rebuild_today → build_daily_session(user, lang, local_today)
         reviews first, then new words, inside the practice share; leftover → tests

GET /api/study-session
   ├─► admit_daily_new_words (per-LOCAL-day quota intake, governor applied, best effort)
   │     Queue A1 (test + word-quiz unknowns) → A2 (calibration wrongs) → Queue B (lookahead, empty)
   │     → supply gate → INSERT user_word_ladder, request generation for starved,
   │       set_new_words_shortfall; if main-session words are unobtainable → rebuild_today once
   ├─► queue (required items)          + governor {...}
   └─► tail / tail_queue (only when the required items are all complete)

POST practice attempt → record_session_progress(p_sense_id, p_is_tail)
        → new_words_completed (+ tail_new_words_completed), tail_completed_min
POST /api/calibration/end (definition mode) → update_vocabulary_from_word_tests_batch (BKT evidence)
```

## Database Impact

Reference [[database/schema.tech]] for current state (not edited by this page).

### Migration 1: `migrations/session_module_exclusions.sql` (amends TASK-863)

The new columns go **in the same file** as the `excluded_modules` column from
[[features/session-modules.tech]]; that spec's DDL is unchanged and the statements below are added
to it. Pattern per `migrations/CLAUDE.md`: single-pass `UPDATE`, every new `CHECK` added
`NOT VALID` inside the transaction, `VALIDATE` as separate statements after `COMMIT`.

```sql
BEGIN;

-- (a) session-modules DDL: excluded_modules + user_study_plans_excluded_modules_known (unchanged)

-- (b) user_study_plans
ALTER TABLE public.user_study_plans
    ADD COLUMN IF NOT EXISTS budget_scope text NOT NULL DEFAULT 'tests_and_review',
    ADD COLUMN IF NOT EXISTS new_words_per_day smallint NOT NULL DEFAULT 5;
-- DEFAULT 5 is a SAFETY default only (a row inserted by a path that does not set the column,
-- e.g. the apply_study_plan_template RPC). The intended default is
-- max(1, daily_minutes // 6) PER DAY: the route sets it explicitly (see PUT), and the backfill
-- below sets it for existing rows.

ALTER TABLE public.user_study_plans
    ADD CONSTRAINT user_study_plans_budget_scope_known
        CHECK (budget_scope IN ('tests_and_review','tests_only')) NOT VALID,
    ADD CONSTRAINT user_study_plans_new_words_per_day_range
        CHECK (new_words_per_day BETWEEN 0 AND 50) NOT VALID;

-- Backfill: one pass, predicate keeps unaffected rows from being rewritten.
-- Integer division; max 180/6 = 30, inside the 0..50 range.
UPDATE public.user_study_plans
   SET new_words_per_day = GREATEST(1, daily_minutes / 6)
 WHERE new_words_per_day IS DISTINCT FROM GREATEST(1, daily_minutes / 6);

-- (c) weekly_plan_states
ALTER TABLE public.weekly_plan_states
    ADD COLUMN IF NOT EXISTS budget_scope              text NOT NULL DEFAULT 'tests_and_review',
    ADD COLUMN IF NOT EXISTS review_target_minutes     int  NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS new_words_target          int  NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS new_words_completed       int  NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS acq_target_minutes        int  NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS tail_completed_min        int  NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS tail_new_words_completed  int  NOT NULL DEFAULT 0;

ALTER TABLE public.weekly_plan_states
    ADD CONSTRAINT weekly_plan_states_budget_scope_known
        CHECK (budget_scope IN ('tests_and_review','tests_only')) NOT VALID,
    ADD CONSTRAINT weekly_plan_states_new_columns_non_negative
        CHECK (review_target_minutes >= 0 AND new_words_target >= 0
               AND new_words_completed >= 0 AND acq_target_minutes >= 0
               AND tail_completed_min >= 0 AND tail_new_words_completed >= 0) NOT VALID;

-- The original shares CHECK (phase13_weekly_plan_states.sql) demands
-- maintenance_share in [0.10, 0.55] and acquisition_share in [0.45, 0.90]. The shares are now
-- DERIVED (maintenance = review / (review + acq_in_budget)), so they legitimately reach 1.0 / 0.0
-- (new_words_per_day = 0, tests_only, practice excluded). Relax it to "valid shares that sum to 1".
-- This relaxation is STILL REQUIRED after the 2026-10-13 (b) revision.
ALTER TABLE public.weekly_plan_states DROP CONSTRAINT IF EXISTS weekly_plan_states_shares_sum;
ALTER TABLE public.weekly_plan_states
    ADD CONSTRAINT weekly_plan_states_shares_sum
        CHECK (maintenance_share BETWEEN 0 AND 1
               AND acquisition_share BETWEEN 0 AND 1
               AND abs(maintenance_share + acquisition_share - 1.0) <= 0.011) NOT VALID;

-- In-flight rows at deploy time: split the old practice target into review and acquisition so the
-- current week still schedules both until Tier B recomputes. Current and prior week only.
UPDATE public.weekly_plan_states
   SET review_target_minutes = ROUND(practice_target_minutes * maintenance_share)::int,
       acq_target_minutes    = practice_target_minutes
                               - ROUND(practice_target_minutes * maintenance_share)::int
 WHERE week_start_date >= (CURRENT_DATE - 14)
   AND review_target_minutes = 0;

-- (d) per-language cost of one new word (written nightly by TASK-870)
ALTER TABLE public.dim_languages
    ADD COLUMN IF NOT EXISTS new_word_minutes_est numeric(4,2) NULL
        CHECK (new_word_minutes_est IS NULL OR new_word_minutes_est BETWEEN 0.5 AND 15.0);

-- (e) helper functions (see "SQL helpers" below) and the redefined compute_weekly_plan_persist.
COMMIT;

ALTER TABLE public.user_study_plans VALIDATE CONSTRAINT user_study_plans_excluded_modules_known;
ALTER TABLE public.user_study_plans VALIDATE CONSTRAINT user_study_plans_budget_scope_known;
ALTER TABLE public.user_study_plans VALIDATE CONSTRAINT user_study_plans_new_words_per_day_range;
ALTER TABLE public.weekly_plan_states VALIDATE CONSTRAINT weekly_plan_states_budget_scope_known;
ALTER TABLE public.weekly_plan_states VALIDATE CONSTRAINT weekly_plan_states_new_columns_non_negative;
ALTER TABLE public.weekly_plan_states VALIDATE CONSTRAINT weekly_plan_states_shares_sum;
```

Column reference:

| Table.column | Type | Null / default | Meaning |
|---|---|---|---|
| `user_study_plans.excluded_modules` | `text[]` | NOT NULL `'{}'` | session-modules; CHECK `user_study_plans_excluded_modules_known` |
| `user_study_plans.budget_scope` | `text` | NOT NULL `'tests_and_review'` | CHECK `user_study_plans_budget_scope_known` |
| `user_study_plans.new_words_per_day` | `smallint` | NOT NULL `5` (safety) | daily new-word quota, 0..50 (`user_study_plans_new_words_per_day_range`) |
| `weekly_plan_states.budget_scope` | `text` | NOT NULL `'tests_and_review'` | snapshot of the scope the row was computed under |
| `weekly_plan_states.review_target_minutes` | `int` | NOT NULL `0` | weekly review minutes sized by due pressure (in-budget under `tests_and_review`; the tail target under `tests_only`; 0 if `practice` excluded) |
| `weekly_plan_states.new_words_target` | `int` | NOT NULL `0` | Σ over 7 weekdays of `new_words_for_day` = the weekly quota, before the governor |
| `weekly_plan_states.new_words_completed` | `int` | NOT NULL `0` | words STARTED that local day (the sense's first-ever `exercise_attempts` row falls on that day; see 'Quota semantics'), main session or tail, counted once per sense; preserved across recomputes |
| `weekly_plan_states.acq_target_minutes` | `int` | NOT NULL `0` | in-budget new-word minutes this week = `min(round(new_words_target * mpnw), practice_target_minutes - review_target_minutes)`; 0 when there is no in-budget practice share |
| `weekly_plan_states.tail_completed_min` | `int` | NOT NULL `0` | minutes of practice done in optional-tail blocks this week (informational; the same minutes are also in `practice_completed_*_min`); preserved across recomputes |
| `weekly_plan_states.tail_new_words_completed` | `int` | NOT NULL `0` | subset of `new_words_completed` that was started in the tail; preserved across recomputes |
| `dim_languages.new_word_minutes_est` | `numeric(4,2)` | NULL | 0.5..15.0 |

`practice_target_minutes` keeps its meaning: the in-budget practice pool `P` (review + new-word
practice + any spare that Tier C returns to tests). Removed by revision (b): `extra_weekly_minutes`.
`maintenance_share` / `acquisition_share` are **derived, persisted for observability only**; nothing
reads them for scheduling:

```
maintenance_share  = round(review_target_minutes / (review_target_minutes + acq_target_minutes), 2)
acquisition_share  = round(1 - maintenance_share, 2)
both  = 1.00 / 0.00  when review_target_minutes + acq_target_minutes = 0
```

(`acquisition_share` is computed from the rounded `maintenance_share`, so the pair always sums to
1.00 and passes the relaxed CHECK.) Under `tests_only` the in-budget acquisition is 0, so the shares
are 1.00 / 0.00 whatever the review target is.

No new index. No RLS change: `user_study_plans_self_modify` covers the new columns and
`weekly_plan_states` stays select-only for users.

### SQL helpers (same file; all `SECURITY DEFINER`, `SET search_path TO 'public','pg_temp'` except the pure ones)

```sql
-- Pure. MUST agree with services/study_plan_service.py::new_words_for_day (test-pinned).
-- floor(x + 0.5), NOT ROUND/Python round(): banker's rounding would disagree at .5.
CREATE OR REPLACE FUNCTION public.new_words_for_day(p_new_words_per_day int, p_weight numeric)
RETURNS int LANGUAGE sql IMMUTABLE AS $$
    SELECT CASE WHEN p_weight IS NULL OR p_weight <= 0 OR p_new_words_per_day <= 0 THEN 0
                ELSE FLOOR(p_new_words_per_day * p_weight + 0.5)::int END
$$;

-- Mirrors Config.NEW_WORD_MINUTES_DEFAULT (3.0). Change one, change both (test-pinned),
-- same discipline as test_time_estimate's ELSE branch.
CREATE OR REPLACE FUNCTION public.new_word_minutes(p_language_id smallint)
RETURNS numeric LANGUAGE sql STABLE AS $$
    SELECT COALESCE((SELECT dl.new_word_minutes_est FROM public.dim_languages dl
                      WHERE dl.id = p_language_id), 3.0)
$$;
```

`compute_weekly_plan_persist(p_user_id uuid, p_language_id smallint, p_week_start date, p_computed jsonb) RETURNS jsonb`
is redefined from `phase13_compute_weekly_plan_helpers.sql` (that file is multi-object, so it is
**not archived**; add a header note that this function is superseded). Behaviour:

- The six original required keys stay required. The four new keys `budget_scope` (default
  `'tests_and_review'`), `review_target_minutes`, `new_words_target`, `acq_target_minutes`
  (integers, default 0) are **optional**, so a Tier B deployed before this migration, or an older
  worker, still persists.
- INSERT sets `new_words_completed = 0`, `tail_completed_min = 0`, `tail_new_words_completed = 0`.
- `ON CONFLICT DO UPDATE` sets the four new keys' columns from EXCLUDED and **never touches**
  `new_words_completed`, `tail_completed_min`, `tail_new_words_completed` (same contract as
  `completed_counts` and `practice_completed_*`).
- Returns `to_jsonb(row)`.

### Migration 2: `migrations/session_module_exclusions_build_daily_session.sql` (amends TASK-865)

Redefines `public.build_daily_session(uuid, smallint, date)`. As in
[[features/session-modules.tech]], start from the live definition (`pg_get_functiondef`, probe for
the `word_upload` marker); the current repo canonical file is
`migrations/word_upload_slot_scheduling.sql` (lines 116-887), which stays (not archived, it also adds a
column) with a header note. It carries the session-modules edits 1-9 **plus** the edits below,
each tagged `-- session-budget` in comments. It also defines `set_new_words_shortfall` (below).
It calls the governor helpers of Migration 5, so Migration 5 is applied first.

**New DECLAREs:** `v_scope text; v_practice_in boolean; v_npd int; v_quota int; v_new_eff int;
v_mpnw numeric; v_gov jsonb; v_level text; v_due_min numeric; v_r_main numeric; v_s_words int;
v_a_main numeric; v_returned numeric := 0; v_local_midnight timestamptz; v_lw jsonb; v_unstarted int; v_started_today int;
v_shortfall int; v_prior_shortfall int; v_prior_checked boolean;`

**Setup (after `v_weekday_w`, which is read from `v_plan.weekday_shape`):**

```sql
v_scope       := v_state.budget_scope;       -- consistent with the state's own totals
v_practice_in := (v_scope = 'tests_and_review' AND NOT ('practice' = ANY(v_excluded)));
v_npd         := v_plan.new_words_per_day;   -- live: a stale state never hides a setting
v_quota       := public.new_words_for_day(v_npd, v_weekday_w);               -- Q
v_mpnw        := public.new_word_minutes(p_language_id);
v_gov         := public.review_governor_state(p_user_id, p_language_id, p_date);
v_level       := CASE WHEN 'practice' = ANY(v_excluded) THEN 'normal' ELSE v_gov->>'level' END;
v_new_eff     := public.new_words_effective(v_quota, v_level);               -- E
v_due_min     := CASE WHEN 'practice' = ANY(v_excluded) THEN 0
                      ELSE (v_gov->>'due_minutes')::numeric END;
```

**Prior supply check (same-day rebuild only).** `daily_test_loads.daily_session_targets` of the
existing row for `p_date` may carry `new_words_supply_checked = true` and `new_words_shortfall`
written by ladder intake (`set_new_words_shortfall`). Read them into `v_prior_checked`,
`v_prior_shortfall` before the row is replaced. If not checked, `v_prior_shortfall := 0`.

**Pool split (the TASK-732 split is kept; the practice side changes).**

- `v_practice_minutes_total := CASE WHEN v_practice_in THEN GREATEST(0, v_state.practice_target_minutes - v_state.practice_completed_maint_min - v_state.practice_completed_acq_min) ELSE 0 END`.
  (The session-modules `IF 'practice' = ANY(v_excluded)` wrap is subsumed because `v_practice_in` is false.)
- `v_practice_budget` (the day's in-budget practice share, "B_p") and `v_test_budget` come from the
  existing TASK-732 proportional formula.
- **The practice-side candidate INSERTs and the practice greedy loop are deleted.** Reviews first, new
  words second is a priority order, not a value ranking, so the practice side is assigned directly:

```sql
-- 1. due reviews first (due = overdue + due today, in minutes)
v_r_main  := CASE WHEN v_practice_in THEN LEAST(v_practice_budget, v_due_min) ELSE 0 END;
-- 2. then new words, as many whole words as fit in what is left of the share;
--    after a supply check, never plan more than the words that can actually be served
v_s_words := CASE WHEN v_practice_in AND v_new_eff > 0 AND v_mpnw > 0
                  THEN LEAST(v_new_eff,
                             GREATEST(0, v_new_eff - v_prior_shortfall),
                             FLOOR((v_practice_budget - v_r_main) / v_mpnw)::int)
                  ELSE 0 END;
v_a_main  := v_s_words * v_mpnw;
-- 3. unused share minutes return to tests (never an empty budget)
v_returned    := GREATEST(0, v_practice_budget - v_r_main - v_a_main);
v_test_budget := v_test_budget + v_returned;
v_maint_min   := ROUND(v_r_main);            -- runner reads practice_maintenance_min
v_acq_min     := ROUND(v_a_main);            -- runner reads practice_acquisition_min
```

  The test/surface greedy loop is unchanged and runs against the enlarged `v_test_budget` (its 1.5x cap
  applies to the enlarged value). `v_used_min := v_used_min_test + v_maint_min + v_acq_min`. The old
  10-minute chunking, the `/10` floor division, the `'acq'` candidate and the `'x_acq'` / `'x_maint'`
  extra-pool candidates do not exist. The runner keeps chunking the two minute values into <=10-minute
  practice chunks, so `routes/study_session.py` needs no queue change for the main session.

**Shortfall seed** (words still to admit at build time; intake overwrites it with the final unmet count):

```sql
v_local_midnight := (p_date::timestamp AT TIME ZONE COALESCE(v_plan.timezone, 'UTC'));
v_lw             := public.ladder_new_word_state(p_user_id, p_language_id, v_local_midnight);  -- Migration 5
v_unstarted      := (v_lw->>'unstarted')::int;             -- U: admitted, never attempted
v_started_today  := (v_lw->>'started_today')::int;         -- ST: first-ever attempt on or after local midnight
v_shortfall := GREATEST(0, v_new_eff - (v_unstarted + v_started_today));
```

(See 'Quota semantics' for the definition of started. The old seed counted words admitted today; that is removed.
`uwl.sense_id -> dim_word_senses.id`, `dim_word_senses.vocab_id -> dim_vocabulary.id`,
`dim_vocabulary.language_id`: verified in `migrations/bkt_word_test_batch.sql` and in
`database/schema.tech`.) Tier C keeps `S = min(E, floor(remaining / minutes_per_new_word))` for the in-budget share (the
share is sized for the whole day and completed chunks stay completed); only intake, the tail and the shortfall use `ST`. When a prior supply check exists, `new_words_shortfall` keeps the prior value.

**`daily_session_targets` and the return value** gain: `budget_scope`, `new_words_quota` (Q),
`new_words_effective` (E), `new_words_in_budget` (S = `v_s_words`), `new_words_shortfall`,
`new_words_supply_checked` (copied from the prior row, else false), `governor_level`,
`review_due_minutes` (`v_due_min`, at build time), `review_main_minutes` (`v_maint_min`),
`new_word_main_minutes` (`v_acq_min`), `returned_to_tests_minutes` (`v_returned`). Existing keys stay:
`practice_budget_minutes` is the in-budget practice share B_p (0 when `v_practice_in` is false),
`test_budget_minutes` is the enlarged test budget, `today_budget_minutes` is the in-budget budget only.

**TASK-705 re-entrancy is unchanged.** A same-day rebuild re-derives the practice minutes from the
current settings; `completed_blocks` is never reset, so finished chunks stay finished. Lowering
`new_words_per_day` below the number already admitted (or started) today does not un-admit anything.

```sql
CREATE OR REPLACE FUNCTION public.set_new_words_shortfall(
    p_user_id uuid, p_language_id smallint, p_date date, p_shortfall int
) RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER
  SET search_path TO 'public','pg_temp' AS $$
BEGIN
    UPDATE public.daily_test_loads
       SET daily_session_targets =
             jsonb_set(
               jsonb_set(COALESCE(daily_session_targets, '{}'::jsonb),
                         '{new_words_shortfall}', to_jsonb(GREATEST(0, p_shortfall))),
               '{new_words_supply_checked}', 'true'::jsonb)
     WHERE user_id = p_user_id AND language_id = p_language_id AND load_date = p_date;
    RETURN FOUND;
END $$;
REVOKE EXECUTE ON FUNCTION public.set_new_words_shortfall(uuid, smallint, date, int)
    FROM PUBLIC, anon, authenticated;   -- service-role (backend) only
```

### Migration 3: `migrations/new_word_minutes_estimate.sql` (TASK-870)

Defines `public.refresh_new_word_minutes() RETURNS jsonb`. Called by
`_refresh_exercise_time_estimates` (`services/study_plan_service.py` line 678; fires daily at
04:05 UTC and delegates to the `refresh_practice_time_estimates` RPC) **after** that RPC succeeds,
so `dim_exercise_types.expected_seconds_p50` is fresh. For each `dim_languages` row `L`:

1. `W` = `user_word_ladder` rows created in the last 30 days whose sense belongs to `L`.
2. For each `w` in `W`, `items_w` = count of that user's `exercise_attempts` on `w.sense_id`
   with `created_at` in `[w.created_at, w.created_at + 24 hours)`. (24 hours, not the local day,
   to avoid a per-row timezone join; documented approximation.)
3. Require at least 10 words with `items_w >= 1`; otherwise leave `new_word_minutes_est` unchanged.
4. `items_per_word = AVG(items_w)` over those words.
   `median_seconds = percentile_cont(0.5)` over those attempts of
   `COALESCE(det.expected_seconds_p50, det.expected_seconds)` (`dim_exercise_types det`).
5. `new_word_minutes_est = LEAST(15.0, GREATEST(0.5, ROUND(items_per_word * median_seconds / 60.0, 2)))`.

Returns `{languages_updated: int}`; `_refresh_exercise_time_estimates` merges it into its summary
and logs it. Live engagement is thin (15 exercise attempts ever at the time of the lookahead
measurements), so `NEW_WORD_MINUTES_DEFAULT = 3.0` will apply for a long time.

**Where it is stored, and why.** A column on `dim_languages` (`new_word_minutes_est`).
Precedent: the same job already writes observed stats onto dimension rows
(`dim_exercise_types.expected_seconds_p50`, `dim_test_types.expected_minutes_p50`), the value is
one number per language, and readers (Tier B, Tier C, the route) need a single-row lookup with no
join. A separate table (`language_new_word_cost`) was rejected: it would add a join and a table for
one scalar, and it only pays off if we later want to keep the history or the inputs (items per
word, sample size). If that becomes useful, add the table then.

### Migration 4: `migrations/new_words_completed_accrual.sql` (TASK-872)

Canonical `record_session_progress` is `migrations/task716_local_day_boundary.sql` (it superseded
`phase18_practice_time_seconds.sql`). Redefine it with two extra arguments:

```sql
DROP FUNCTION IF EXISTS public.record_session_progress(
    uuid, smallint, uuid, text, text, integer, integer, integer);   -- avoid ambiguous overloads
CREATE OR REPLACE FUNCTION public.record_session_progress(
    p_user_id uuid, p_language_id smallint, p_attempt_id uuid, p_kind text, p_skill text,
    p_delta_count integer DEFAULT 0, p_delta_minutes integer DEFAULT 0,
    p_delta_seconds integer DEFAULT 0,
    p_sense_id bigint DEFAULT NULL,                     -- NEW
    p_is_tail boolean DEFAULT false                     -- NEW
) RETURNS boolean ...
```

All existing logic is carried forward verbatim. New behaviour, inside the same `UPDATE`:

- **New-word accrual.** When `p_kind = 'practice_acq'` and `p_sense_id IS NOT NULL` and the user has a
  `user_word_ladder` row for that sense and
  `(SELECT MIN(ea.created_at) FROM public.exercise_attempts ea WHERE ea.user_id = p_user_id AND ea.sense_id = p_sense_id)
  >= public.plan_local_day_start(p_user_id, p_language_id)` (the sense's first-ever attempt is today; the current attempt
  is already inserted when `record_attempt_with_updates` calls this function, step 3 before step 6) and
  `session_progress_log -> 'new_words'` does not already contain `p_sense_id::text`: `new_words_completed = new_words_completed + 1`, append `p_sense_id::text` to
  `session_progress_log['new_words']`, and, if `p_is_tail`, `tail_new_words_completed + 1`. Idempotent
  per sense per week (the existing per-attempt dedupe returns before this point on a retried attempt). A word admitted
  on an earlier day and first attempted today **does** count; a word admitted today and first attempted tomorrow counts
  tomorrow.
- **Tail minutes.** When `p_is_tail` and `p_kind IN ('practice_acq','practice_maint')`:
  `tail_completed_min` increases by the same minutes the function already adds to
  `practice_completed_acq_min` / `practice_completed_maint_min` for that call. The work also counts
  toward those weekly counters (so tail work is "counted toward weekly targets").

`plan_local_day_start(uuid, smallint) RETURNS timestamptz` is new in the same file:
`plan_local_date(...)::timestamp AT TIME ZONE <user_study_plans.timezone, default 'UTC'>`.
`'new_words'` is a reserved log key (skill codes and `practice_acq` / `practice_maint` are the others).

### Migration 5: `migrations/review_governor.sql` (TASK-874)

Review-load governor helpers. All are read-only; the pure ones are `IMMUTABLE`.

```sql
-- Mirrors Config.REVIEW_BACKLOG_THRESHOLD_DAYS (1.0), REVIEW_ALLOWANCE_FLOOR_MIN (3.0),
-- REVIEW_ITEM_SECONDS_DEFAULT (20.0). Change one, change both (test-pinned).

-- Pure. level of the governor for a backlog and a threshold, both in minutes.
CREATE OR REPLACE FUNCTION public.review_governor_level(p_backlog_min numeric, p_threshold_min numeric)
RETURNS text LANGUAGE sql IMMUTABLE AS $$
    SELECT CASE WHEN p_threshold_min IS NULL OR p_threshold_min <= 0 THEN 'normal'
                WHEN p_backlog_min <= p_threshold_min      THEN 'normal'
                WHEN p_backlog_min <= 2 * p_threshold_min  THEN 'reduced'
                ELSE 'paused' END
$$;

-- Pure. effective new words = quota | floor(quota/2) | 0.
CREATE OR REPLACE FUNCTION public.new_words_effective(p_quota int, p_level text)
RETURNS int LANGUAGE sql IMMUTABLE AS $$
    SELECT CASE p_level WHEN 'paused'  THEN 0
                        WHEN 'reduced' THEN GREATEST(p_quota, 0) / 2     -- integer division = floor
                        ELSE GREATEST(p_quota, 0) END
$$;

-- Median seconds of one timed exercise attempt for this learner and language over 30 days
-- (time_taken_ms between 1000 and 120000); fewer than 20 samples -> 20.0.
-- v1 (ANSWERED 2026-10-13): ALL vocabulary-exercise attempts, no review-only filter (no maintenance flag exists).
-- It is therefore an ESTIMATE of review seconds; the UI labels the forecast as an estimate.
CREATE OR REPLACE FUNCTION public.review_item_seconds(p_user_id uuid, p_language_id smallint)
RETURNS numeric ...;   -- SECURITY DEFINER; exercise_attempts ea JOIN dim_word_senses dws ON dws.id = ea.sense_id
                       --   JOIN dim_vocabulary dv ON dv.id = dws.vocab_id AND dv.language_id = p_language_id

-- {overdue_items, overdue_minutes, due_items, due_minutes, threshold_minutes, item_seconds, level}
CREATE OR REPLACE FUNCTION public.review_governor_state(
    p_user_id uuid, p_language_id smallint, p_date date) RETURNS jsonb ...;

-- Quota-semantics counts (see 'Quota semantics'). p_day_start = 00:00 of the learner's local date as timestamptz.
-- {unstarted: int, started_today: int, unstarted_sense_ids: int[] (oldest uwl.created_at first, max 200)}
-- REVIEW FIX 2026-10-14: U counts only word_state IN ('new','active','gated','pre_mastery','relearning'), no attempt by sense_id OR via
-- exercise_id -> exercises.word_sense_id (legacy NULL sense_id), >= 3 active exercises in the language, admitted <= 14 days ago;
-- ST uses the same started_at. set_new_words_shortfall gained p_checked_e (key new_words_supply_checked_e): a supply check is stale when E differs.
-- The authoritative text is migrations/review_governor.sql.
CREATE OR REPLACE FUNCTION public.ladder_new_word_state(
    p_user_id uuid, p_language_id smallint, p_day_start timestamptz)
RETURNS jsonb LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public, pg_temp AS $$
  WITH w AS (
    SELECT uwl.sense_id, uwl.created_at AS admitted_at,
           (SELECT MIN(ea.created_at) FROM public.exercise_attempts ea
             WHERE ea.user_id = uwl.user_id AND ea.sense_id = uwl.sense_id) AS started_at
      FROM public.user_word_ladder uwl
      JOIN public.dim_word_senses dws ON dws.id = uwl.sense_id
      JOIN public.dim_vocabulary  dv  ON dv.id  = dws.vocab_id
     WHERE uwl.user_id = p_user_id AND dv.language_id = p_language_id)
  SELECT jsonb_build_object(
    'unstarted',     COUNT(*) FILTER (WHERE started_at IS NULL),
    'started_today', COUNT(*) FILTER (WHERE started_at >= p_day_start),
    'unstarted_sense_ids', COALESCE((SELECT jsonb_agg(sense_id ORDER BY admitted_at, sense_id)
        FROM (SELECT sense_id, admitted_at FROM w WHERE started_at IS NULL
               ORDER BY admitted_at, sense_id LIMIT 200) u), '[]'::jsonb))
  FROM w;
$$;
-- REVOKE ALL ... FROM PUBLIC, anon, authenticated; GRANT EXECUTE ... TO service_role (same as review_governor_state).
-- Uses idx_ea_user_sense_type (user_id, sense_id, exercise_type, created_at DESC) from exercise_scheduling.sql.
```

`review_governor_state` definitions (all sets are DISTINCT `sense_id`, union of the two sources):

- `v_local_start` = `p_date::timestamp AT TIME ZONE COALESCE(user_study_plans.timezone, 'UTC')`.
- **Overdue** (the backlog): `user_flashcards` rows (user, `language_id`) with `due_date < p_date`, UNION
  `user_word_ladder` rows of the user (language through `dim_word_senses` -> `dim_vocabulary`) with
  `review_due_at IS NOT NULL AND review_due_at < v_local_start`. Completing a review moves
  `due_date` / `review_due_at` forward (`_update_fsrs_for_exercise` and the ladder attempt writer), so
  "overdue and not done" is simply "still in the past".
- **Due now** (`due_items`): the same two sources with `due_date <= p_date` and
  `review_due_at < v_local_start + interval '1 day'` (overdue plus due today).
- `item_seconds = review_item_seconds(...)`; `overdue_minutes = overdue_items * item_seconds / 60`;
  `due_minutes = due_items * item_seconds / 60`.
- **Threshold T** (minutes) = `REVIEW_BACKLOG_THRESHOLD_DAYS * GREATEST(REVIEW_ALLOWANCE_FLOOR_MIN, review_target_minutes / 7.0)`,
  where `review_target_minutes` is read from `weekly_plan_states` for the Monday-start week of `p_date`
  (`p_date - (EXTRACT(ISODOW FROM p_date)::int - 1)`). "One day's review allowance" is therefore the
  weekly review target / 7 in both scopes (under `tests_only` the in-budget review allowance is 0, so the
  weekly review target is the only sensible yardstick). No weekly state row: `T` uses the floor.
- `level = review_governor_level(overdue_minutes, T)`; `practice` excluded in `user_study_plans.excluded_modules`:
  `level = 'normal'`, all minute values 0 (the learner turned review off).

Effective new words today: `E = new_words_effective(Q, level)`. Python mirrors `review_governor_level`,
`effective_new_words` and `review_forecast_min_per_day` (below) as pure functions; the Python side never
recomputes the state, it calls the RPC.

### Migration 6: `migrations/calibration_bkt_evidence.sql` (TASK-873)

```sql
ALTER TABLE public.calibration_sessions
    ADD COLUMN IF NOT EXISTS bkt_applied_at timestamptz NULL;
COMMENT ON COLUMN public.calibration_sessions.bkt_applied_at IS
  'Set once, when /end fed this session''s answered anchors to update_vocabulary_from_word_tests_batch. NULL = never applied (pronunciation sessions stay NULL). Idempotency guard and the marker that tells the ladder intake which user_vocabulary_knowledge evidence came from calibration.';
```

That is the whole schema change for cold start 4B. `user_vocabulary_knowledge` gets **no** new
column (see "Cold start: how calibration evidence is identified").

## Tier B: `services/study_plan_service.py`

### New and changed constants

```python
BUDGET_SCOPES = ('tests_and_review', 'tests_only')
NEW_WORDS_MAX_PER_DAY = 50
REVIEW_TAIL_CAP_FRACTION = 0.5      # tests_only: review_target_minutes <= daily*7*0.5 (a weekly TARGET, not a budget)
REVIEW_PRESSURE_OFFSET = 0.5        # assumed; see rebalance_practice
DEFAULT_WEEKDAY_SHAPE = (1.0,) * 7
TAIL_OFFER_MAX_MIN = 20             # max minutes of tail chunks offered per "Keep going?" round (tunable)
# Config (config.py), mirrored in SQL where noted (test-pinned):
#   NEW_WORD_MINUTES_DEFAULT = 3.0          (SQL new_word_minutes fallback)
#   REVIEW_BACKLOG_THRESHOLD_DAYS = 1.0     (SQL review_governor_state)
#   REVIEW_ALLOWANCE_FLOOR_MIN = 3.0        (SQL review_governor_state)
#   REVIEW_ITEM_SECONDS_DEFAULT = 20.0      (SQL review_item_seconds)
#   REVIEWS_PER_NEW_WORD_30D = 7            (Python only; forecast)
```

Removed by revision (b): `REVIEW_EXTRA_CAP_FRACTION`, `EXTRA_REVIEW_MIN_CHUNK_MIN`, `scale_up_to_target`,
and the shared `_largest_remainder_scale` factoring (`apply_module_exclusions` keeps its own step 6).

`target_new_rate()` stays (lines 86-88) and is used only to document the default
`new_words_per_day`; `target_active_pool()` is no longer used by intake (keep it, other code may
call it).

### `new_words_for_day(new_words_per_day: int, weight: float) -> int`

- **Purpose:** the day's quota `Q` for the given weekday weight.
- **Algorithm:** `0` if `weight <= 0` or `new_words_per_day <= 0`; else
  `int(math.floor(new_words_per_day * weight + 0.5))`. Not `round()` (banker's rounding).
- **Mirror:** SQL `public.new_words_for_day`. A test evaluates both on a grid including `.5` ties.

### `new_words_week_target(new_words_per_day: int, shape: Sequence[float]) -> int`

`sum(new_words_for_day(new_words_per_day, w) for w in (shape or DEFAULT_WEEKDAY_SHAPE))`. The
shape is the plan's `weekday_shape` (7 floats normalised by the route to sum 7, so all-ones is
the default). **Discrepancy with the design text (OPEN):** the design wrote
`Σ new_words_per_day * [weight_d > 0]`. The code normalises weights to sum 7, so a 5-day shape
gives each active day weight 1.4; Tier C scales by weight, so Tier B uses the same helper to keep the
weekly target equal to what Tier C will actually schedule. For the default shape both forms give
`7 * npd`; rest days give 0 in both.

### Governor and forecast helpers (pure; TASK-874)

```python
def review_governor_level(backlog_min: float, threshold_min: float) -> str        # 'normal'|'reduced'|'paused'
def effective_new_words(quota: int, level: str) -> int                            # quota | quota // 2 | 0
def review_forecast_min_per_day(avg_new_words_per_day: float, item_seconds: float) -> float
def get_review_governor(db, user_id, language_id, plan_date) -> dict              # calls RPC review_governor_state;
                                                                                  # any failure -> level 'normal', zeros
```

Mirrors of the SQL pure functions; the grid test pins them.

#### Review forecast

Each new word is assumed to need `N = REVIEWS_PER_NEW_WORD_30D` (7) reviews during its first 30 days,
spread evenly. After the learner has introduced `n` words per day for 30 days, the number of words
inside their first-30-day window is `30 * n`, each producing `N / 30` reviews per day, so the steady
state review load is

```
reviews_per_day   = (30 * n) * (N / 30) = n * N
X (minutes / day) = n * N * item_seconds / 60                 -- "≈ +X min/day of reviews in a month"
n = new_words_week_target(new_words_per_day, weekday_shape) / 7   (average words per calendar day)
item_seconds = estimated seconds per review (review_item_seconds: median over ALL the learner's timed vocabulary-exercise
               attempts, 30 days, no review-only filter in v1; default 20.0)
```

Worked: `n = 5`, `N = 7`, `item_seconds = 20` -> `X = 5 * 7 * 20 / 60 = 11.67` ("≈ +12 min/day"). The 30-day
window cancels, so the formula has **no further division by 30**. (A literal `... / 60 / 30` would give
0.39 min/day, which is the load of a single day's cohort, not the load "in a month".) `N = 7` and the
steady-state reading are tunable/OPEN. `item_seconds` is a v1 estimate (all-vocabulary-exercise median, ANSWERED
2026-10-13) and the UI says "≈". The forecast is a hint on the settings page only; it does not feed
the planner.

### `rebalance_practice(...)` — now sizes the practice pool and the review share

```python
def rebalance_practice(
    daily_minutes: int, practice_total_minutes: int, flex_pct: float,
    base_maintenance_share: float, fsrs: Dict[str, int], bkt: Dict[str, int],
    weakness_global: float, cap_minutes: int,
) -> Tuple[int, int, float]:      # (practice_minutes, review_minutes, review_share)
```

- Acquisition pressure, the `ladder` argument and `acq_share` are **removed**: the acquisition share is
  no longer a pressure-driven split, it is whatever of the pool the learner's quota needs.
- `flex_factor = 1 + flex_pct * (2*weakness_global - 1)` (unchanged).
- `practice_minutes = clamp(0, round(practice_total_minutes * flex_factor), cap_minutes)` (as before the
  budget settings: flex plus clamp to `daily_minutes * 7`).
- `maint_pressure` is unchanged: `clamp01(fsrs.due_7d_lookahead / max(trr*7, 1)) + 0.5 * clamp01(bkt.decayed_count / known_words)` (range 0..1.5).
- `review_share = clamp(MAINT_SHARE_FLOOR, base_maintenance_share * (REVIEW_PRESSURE_OFFSET + maint_pressure), MAINT_SHARE_CEIL)`
  (0.15..0.50). The formula is new (the old share compared maintenance to acquisition pressure);
  the offset is an assumption, tracked in `open_questions`.
- `review_minutes = round(practice_minutes * review_share)`.
- The caller passes the template's **original** `practice_total_minutes` (not the exclusion-adjusted
  one, which is 0 under `tests_only`). Breaking signature change; update every caller and test.

### `get_minutes_per_new_word(db, language_id: int) -> float`

Reads `dim_languages.new_word_minutes_est` for the language; returns `Config.NEW_WORD_MINUTES_DEFAULT`
when the row or value is missing or the read fails. Mirror of SQL `new_word_minutes`.

### `compute_weekly_plan` changes (order matters)

1. Plan SELECT adds `weekday_shape, excluded_modules, budget_scope, new_words_per_day`.
   `scope = plan.budget_scope`, falling back to `'tests_and_review'` if absent/unknown.
   `practice_in = (scope == 'tests_and_review' and 'practice' not in excluded)`.
2. `eff_excluded = set(excluded) | ({'practice'} if scope == 'tests_only' else set())`.
   `(weekly_template, _) = apply_module_exclusions(template.weekly_test_counts, template.practice_total_minutes, eff_excluded, minutes_of)`
   (the returned practice minutes are discarded; under `tests_only` the freed practice template minutes
   go to tests/surfaces exactly as in ADR-032).
3. Weakness, `skill_values`, bandit scores: unchanged, over `weekly_template` keys.
4. Practice pool and review. If `'practice' in excluded`: `P0 = review = 0`. Else
   `P0, review, _ = rebalance_practice(..., practice_total_minutes=template.practice_total_minutes, cap_minutes=daily*7)`.
   Review carry-over: `left = max(0, prior.review_target_minutes - prior.practice_completed_maint_min)`;
   `review = min(review + round(CARRY_OVER_DECAY * left), review_cap)` with `review_cap = daily*7` for
   `tests_and_review` and `floor(daily*7*REVIEW_TAIL_CAP_FRACTION)` for `tests_only`. New-word minutes are
   **not** carried over: they are a daily quota, and an unmet quota is reported as a shortfall, not owed.
5. New words: `mpnw = get_minutes_per_new_word(db, language_id)`;
   `new_words_target = new_words_week_target(plan.new_words_per_day, plan.weekday_shape)`;
   `acq_quota_min = round(new_words_target * mpnw)`.
6. In-budget practice pool. If `practice_in`: `P = min(max(P0, review), daily*7)`;
   `acq_target_minutes = min(acq_quota_min, P - review)`. Else `P = 0` and `acq_target_minutes = 0`
   (tests_only keeps `review_target_minutes = review` as a weekly **tail target**, not as scheduled
   in-budget minutes; with `practice` excluded `review_target_minutes = 0`). The part of `P` that is
   neither review nor new-word practice is deliberately kept in `P`: Tier C hands it back to tests each
   day (see Tier C), so the pool is never silently shortened.
7. `target_counts = allocate_test_counts(weekly_template, scores)`, then the unchanged test
   carry-over loop. **No scale-up step**: tests are not rescaled to absorb freed acquisition minutes.
8. `test_minutes = Σ target_counts[s] * minutes_of(s)`;
   `total_weekly_minutes = min(int(round(test_minutes + P)), daily*7)` (the existing ceiling);
   `practice_target_minutes = P`.
9. Persist `computed` with the original six keys (`maintenance_share` / `acquisition_share` derived as in
   the column reference) plus `budget_scope`, `review_target_minutes = review`, `new_words_target`,
   `acq_target_minutes`.

Idempotency: still deterministic. No new randomness. With the defaults (`tests_and_review`, nothing
excluded) `target_counts`, `practice_target_minutes` and `total_weekly_minutes` equal the pre-change
values; only the derived shares, the new columns and Tier C's practice composition change.

### `typical_day_inputs(db, language_id, plan, week) -> dict` (new, used by GET /api/study-plan)

Returns `{practice_room_min_per_day, review_min_per_day}`, the two numbers that do **not** depend on the
new-words input, so the settings card can preview any `new_words_per_day` client-side:

```
test_min      = Σ week.target_counts[s] * minutes_of(s)                          (memoised minutes_of)
practice_day  = (week.total_weekly_minutes / 7) * P / (P + test_min)   if P > 0 else 0   (P = week.practice_target_minutes)
review_min_per_day     = week.review_target_minutes / 7
practice_room_min_per_day = max(0, practice_day - review_min_per_day)  if P > 0 else 0
```

### `StudyPlanService.rebuild_today`

As in session-modules; no change.

## Tier C: `build_daily_session`

See Migration 2. Contract for the resolver: the in-budget practice share B_p is filled **reviews first**
(`min(B_p, due minutes)`), then **whole new words** (`min(E, supply-capped, floor(remaining / mpnw))`),
and anything left **returns to the test budget**. Nothing is added outside the budget; the tail is
derived live by the session route.

## Ladder intake: `services/practice_session_service.py`

### New constants

```python
RECENT_TEST_WINDOW_DAYS = 28      # tunable (assumed, no data)
RECENT_TEST_ROW_LIMIT = 1000
RECENT_TEST_CHUNK = 100
CALIBRATION_EVIDENCE_MAX_AGE_DAYS = 90   # tunable (assumed, no data)
CALIBRATION_ROW_LIMIT = 500
```

`LADDER_TOPUP_MAX_PER_CALL = 12` (line 63) stays as a safety cap. `LADDER_MIN_EXERCISES_PER_SENSE`
(3), `LADDER_EVIDENCE_MIN_COUNT` (2), `LADDER_EVIDENCE_P_KNOWN_MAX` (0.40),
`NOMINATION_OVERFETCH` (20), `DEMAND_GENERATION_MAX_PER_CALL` (5) are unchanged.

### `services/day_boundary.py`: `local_day_start_utc(tz_name: Any, now: Optional[datetime] = None) -> datetime` (new)

Returns the UTC instant of 00:00 on the learner's current local date:
`zone = resolve_zone(tz_name)`; `local = (now or datetime.now(_UTC)).astimezone(zone)`;
`datetime.combine(local.date(), time.min, tzinfo=zone).astimezone(_UTC)`. Falls back to UTC on a bad
zone, like the rest of the module. (The module has `resolve_zone`, `local_date`, `plan_today`,
`plan_today_iso`; this helper does not exist yet.)

### `admit_daily_new_words(self, user_id: str, language_id: int) -> dict` (new public wrapper) and `_maybe_top_up_ladder`

`admit_daily_new_words` is called best-effort at the top of `GET /api/study-session` and returns
`{'admitted': [sense ids], 'needs_rebuild': bool}`. `_maybe_top_up_ladder(self, user_id, language_id)`
(called from `get_session`, as today) delegates to the same body and returns the admitted ids. The body:

1. Read the plan (`new_words_per_day`, `weekday_shape`, `timezone`, `excluded_modules`) in one query.
   No plan row, or any read failure: return `[]` / no rebuild.
2. `local_today = local_date(tz)`; weekday index `local_today.weekday()` (Mon=0, matching
   `weekday_shape`); `quota = new_words_for_day(npd, shape[idx])`. `gov = get_review_governor(...)`;
   `new_today = effective_new_words(quota, gov['level'])` (level is `'normal'` when `practice` is
   excluded). If `new_today <= 0`: return `[]`.
3. Quota state: `st = db.rpc('ladder_new_word_state', {'p_user_id': user_id, 'p_language_id': language_id,
   'p_day_start': local_day_start_utc(tz).isoformat()})` (Migration 5; see 'Quota semantics'); `U = st['unstarted']`,
   `ST = st['started_today']`. This counts every admission path (recent-test queue, calibration queue, lookahead
   cohorts, `_seed_ladder_for_new_words`, anything else) because it reads `user_word_ladder` itself. RPC failure:
   return `[]` (intake adds nothing rather than over-admitting).
4. `want_raw = new_today - (U + ST)`; `want = min(max(want_raw, 0), LADDER_TOPUP_MAX_PER_CALL)`. If `want <= 0`: return `[]`.
   (Admitted-but-unstarted words carry over: they are in `U` and reduce intake one for one.)
5. `subscribed = self._subscribed_sense_ids(user_id)`;
   `fresh = self._nominate_new_words(user_id, language_id, want, subscribed)`.
6. If `fresh`: `_insert_ladder_rows` (on failure return `[]`). Log source, counts and quota.
7. `shortfall = max(0, want_raw - len(fresh))` (the unmet part of the top-up); call
   `set_new_words_shortfall(user, language, plan_today_iso(...), shortfall)` best-effort (log
   WARNING on failure, never raise). This also sets `new_words_supply_checked = true`.
8. `needs_rebuild`: the targets row for today had `new_words_supply_checked` false before this call, and
   `S_planned = targets.new_words_in_budget` is greater than `U + ST + len(fresh)` capped at `new_today` (the words that can
   be served today are fewer than the words Tier C planned inside the budget). `GET /api/study-session` then
   calls `StudyPlanService.rebuild_today` **once** (the supply flag prevents a second rebuild), and Tier C
   returns the unused practice minutes to tests.
9. `_eligible_ladder_count` is still called once, only for its side effect of requesting generation
   for subscribed-but-unservable rows and for the log line. It no longer gates intake and
   `target_active_pool` is no longer read.

Admission on `'new'` rows stays as today (`_insert_ladder_rows`, `word_state='new'`).
Repeated calls on the same day are idempotent: `U + ST` already includes what an earlier call admitted. The governor
can lower `new_today` later in the day as well as raise it again once the backlog clears; admission never un-admits.
Acquisition serving takes `st['unstarted_sense_ids']` first (oldest admission first), see 'Quota semantics'.

### `_nominate_new_words(self, user_id, language_id, want, exclude) -> List[int]`

Nomination order (decided 2026-10-13):

1. **Queue A1: test and word-quiz unknowns.** `recent = self._recent_test_sense_ids(user_id, language_id)`.
   `candidates = [c for c in self._evidence_candidates(user_id, language_id, recency_first=True)
   if c['sense_id'] in recent and c['sense_id'] not in exclude]`. Evidence thresholds are the current
   ones (`evidence >= LADDER_EVIDENCE_MIN_COUNT` or `p_known <= LADDER_EVIDENCE_P_KNOWN_MAX`, or at least two distinct missed
   questions), **computed on non-calibration evidence only** (see below). `_evidence_candidates` gains a
   keyword `recency_first: bool = False`: when `True` the stable-sort order becomes most-recent
   `last_evidence_at` first, then wrong count, then frequency (the default is wrong count, then recency,
   then frequency). Word-quiz evidence is part of A1: the quiz words come from the test's own senses (so
   they are in `recent`) and land in `user_vocabulary_knowledge.word_test_wrong` via `record_word_quiz_results`.
2. **Queue A2: calibration wrongs** — `self._calibration_wrong_candidates(user_id, language_id, exclude)`,
   called only if A1 did not fill `want`. **A single wrong calibration answer is sufficient**: it
   bypasses `LADDER_EVIDENCE_MIN_COUNT` and `LADDER_EVIDENCE_P_KNOWN_MAX`. It is ranked **below** A1.
3. **Queue B: lookahead cohorts** ([[features/lookahead-preteaching]]).
   `_nominate_from_lookahead(...) -> []` is a stub returning an empty list until that feature
   ships; it is called only if A1 and A2 did not fill `want`.
4. **No frequency-based cold-start queue.**

All three queues pass through one extracted helper `_gate_and_admit(candidates, want, language_id)`:
the existing overfetch (`want * NOMINATION_OVERFETCH`), `_senses_with_supply`
(>= `LADDER_MIN_EXERCISES_PER_SENSE` active exercises), `_request_generation` for the starved
(capped by `DEMAND_GENERATION_MAX_PER_CALL`), return `admitted[:want]`. At about 3% exercise
coverage most nominations starve, so shortfall is expected and the generation requests are the
point. Note that calibration anchors come from `calibration_anchor_pool`, which is not filtered on
exercise coverage, so A2 nominations feed generation like any other starved sense.

### Cold start: how calibration evidence is identified (4B)

**Verified facts (2026-10-13):**

- Calibration items are anchor senses. `calibration_responses` stores `anchor_sense_id` and
  `anchor_vocab_id` (`migrations/task770_calibration_build_items.sql` lines 160-163); the options
  (`calibration_response_options`, `is_key` marks the key) are inserted at lines 168-206; anchors are drawn from
  `calibration_anchor_pool` (`migrations/task772_calibration_anchor_pool.sql`).
- `calibration_record_answer` writes only calibration tables: `UPDATE calibration_responses` (grade, sets
  `answered_at` also for a skip) and `UPDATE calibration_sessions` counters
  (`migrations/task769_calibration_record_answer.sql` lines 141-155).
- `end_session` (`services/calibration_service.py` line 642) upserts `user_calibration_state` (`write_calibration_state`,
  line 590) and, in definition mode only, calls `apply_calibration_to_skill_ratings` (line 627, invoked from
  `end_session` near line 673). That is ELO only. **No BKT write exists anywhere in calibration today.**
- `calibration_sessions.mode` exists (`migrations/calibration_pronunciation_mode.sql` line 285; values
  `'definition'` / `'pronunciation'`, `MODE_DEFINITION = 'definition'`).
- The developer's reference path is the post-test word quiz: `POST /word-quiz` (`routes/vocabulary.py` line 16) ->
  `VocabularyKnowledgeService.record_word_quiz_results` -> `update_from_word_test(exercise_type='definition_match')`
  (`services/vocabulary/knowledge_service.py`, calls at lines 372-379). **The file is
  `services/vocabulary/knowledge_service.py`, not `services/knowledge_service.py`.**
- The batch RPC `update_vocabulary_from_word_tests_batch(p_user_id uuid, p_language_id smallint, p_results jsonb)`
  (`migrations/bkt_word_test_batch.sql` line 27; `p_results = [{"sense_id": int, "is_correct": bool}, ...]`;
  returns `out_sense_id, out_p_known_before, out_p_known_after, out_status`; dedupes by `bool_or`) is used by
  dictation at `routes/tests.py` lines 967-973 via `VocabularyKnowledgeService.update_from_word_tests_batch`
  (`knowledge_service.py` line 113).
- The batch RPC takes **no `p_exercise_type`** and applies `bkt_update_word_test` (slip 0.05, guess 0.25, transit
  0.05). The `definition_match` branch of `bkt_update_exercise` (`migrations/phase7_bkt_improvements.sql`) uses
  exactly slip 0.05, guess 0.25, transit 0.05. **The two are numerically identical.**
- The service wrapper `update_from_word_tests_batch` also runs `_auto_create_flashcards`,
  `_seed_ladder_for_new_words` (creates `user_word_ladder` rows with `init_ladder`, which would **bypass the
  daily quota and the supply gate**) and `_trigger_frequency_inference`.

**Decision (TASK-873).** At `end_session`, **definition mode only** (pronunciation excluded):

1. Claim the write: `UPDATE calibration_sessions SET bkt_applied_at = now() WHERE id = :id AND bkt_applied_at IS NULL
   AND mode = 'definition' RETURNING id`. No row: do nothing (already applied, or not definition mode).
2. `results = [{'sense_id': r.anchor_sense_id, 'is_correct': bool(r.is_correct)} for r in calibration_responses
   WHERE session_id = :id AND answered_at IS NOT NULL AND is_correct IS NOT NULL]`. ANSWERED 2026-10-13, verified in
   `templates/calibration.html` (button `#calSkipBtn`, "I don't know", `answer(null)`, line 646),
   `routes/calibration.py` `/answer` (`position` null = skip) and `migrations/task769_calibration_record_answer.sql`
   (lines 141-155): an **explicit skip exists** and is stored as `chosen_sense_id IS NULL`, `is_correct = false`,
   `answered_at = now()` (no separate flag column). A wrong option is `chosen_sense_id` set, `is_correct = false`. Both are
   **wrong evidence** and are sent as `is_correct = false`. An item that was served but never answered (session abandoned)
   has `is_correct IS NULL AND answered_at IS NULL` and is **ignored**: `calibration_discard_unanswered`
   (`services/calibration_service.py` line 649 at `/end`, `migrations/task770_calibration_build_items.sql` line 70)
   removes such rows, and the predicate excludes them even if a retry sees one. Same predicate for the ledger (A2).
3. `VocabularyKnowledgeService().update_from_word_tests_batch(user_id, word_language_id, results, side_effects=False)`.
   `side_effects: bool = True` is a new keyword on the wrapper; `False` skips `_auto_create_flashcards`,
   `_seed_ladder_for_new_words` and `_trigger_frequency_inference`. The ladder is admitted only through the
   quota. The default keeps dictation unchanged.
4. Any failure: log WARNING, set `bkt_applied_at = NULL` (best effort) so a retried `/end` can try again, and never
   fail `/end` (the same non-fatal contract as `write_calibration_state`).

**Exercise type.** Semantically `exercise_type = 'definition_match'`: a four-option definition recognition item,
exactly what the post-test word quiz is. No RPC change is needed because the batch RPC's default branch computes
the same numbers. A test pins `bkt_update_exercise(p, c, 'definition_match') = bkt_update_word_test(p, c)` on a grid
of `p` and `c`; if the two ever diverge, the batch RPC must gain an optional `p_exercise_type` before calibration
keeps using it.

**Identifying calibration-sourced evidence.** `user_vocabulary_knowledge` has no source column (columns:
`p_known, status, evidence_count, comprehension_*, word_test_*, last_evidence_at`), and calibration's single
batch call increments the same `evidence_count` / `word_test_wrong` as a word quiz. The durable ledger is
`calibration_responses` joined to `calibration_sessions`. The marker is `calibration_sessions.bkt_applied_at IS NOT NULL`
(Migration 6). No new column on `user_vocabulary_knowledge`.

For a learner and language, `_calibration_ledger(user_id, language_id)` reads (limit `CALIBRATION_ROW_LIMIT`)
`calibration_responses` joined (`!inner`) to `calibration_sessions` with `mode = 'definition'`,
`word_language_id = language_id`, `bkt_applied_at IS NOT NULL`, `answered_at IS NOT NULL`, and returns per
`anchor_sense_id`: `cal_n` = number of distinct sessions in which the sense was answered; `cal_wrong` = number of those
sessions whose answers for the sense were all incorrect (the batch dedupes with `bool_or` per submission);
`last_answer_wrong` = the latest answer (by `answered_at`) was incorrect; `last_at`.

- **Keeping A1 pure.** In `_evidence_candidates`, subtract the calibration contribution:
  `evidence = evidence_count - cal_n`, `word_test_wrong = word_test_wrong - cal_wrong`. A row with
  `evidence <= 0` is not test or word-quiz evidence and is dropped from A1 (its `p_known` may still reflect calibration, which is
  fine for ranking, not for admission). All existing thresholds then apply to the adjusted numbers.
- **A2 (`_calibration_wrong_candidates`).** Senses with `last_answer_wrong = true`, `last_at` within
  `CALIBRATION_EVIDENCE_MAX_AGE_DAYS`, not in `exclude`, whose current `user_vocabulary_knowledge.status` is not
  `'known'` / `'probably_known'` (later evidence that the learner knows the word vetoes it). Ordered by lemma
  frequency (`_sense_frequency`, Zipf desc: teaching a common word is worth more), then `last_at` desc.
  No `evidence_count` or `p_known` threshold applies.
- **Why A1 outranks A2.** A calibration item is one four-option guess with distractors picked by similarity (a wrong
  click can be a bad foil or a careless tap); test and word-quiz evidence is context-bound and repeated. The
  supply gate and the unchanged `_senses_with_supply` check still apply to A2.

Calibration still seeds ability ratings through `apply_calibration_to_skill_ratings`, so the recommender serves
suitable introductory tests (4A); the intro tests then feed A1 (only for senses linked through `tests.vocab_sense_ids` /
`questions.sense_ids`; link coverage is a data check in TASK-871).

### `_recent_test_sense_ids(self, user_id, language_id) -> set[int]`

`test_attempts` for the user and language with `created_at >= now - RECENT_TEST_WINDOW_DAYS`
(`.limit(RECENT_TEST_ROW_LIMIT)`) give `test_id`s. In chunks of `RECENT_TEST_CHUNK`, union
`tests.vocab_sense_ids` for those ids with `questions.sense_ids` for `questions.test_id in (...)`.
A failed read returns an empty set (so intake adds nothing rather than admitting unrelated words).

### Accrual call site (`record_attempt_with_updates`, around line 585)

Pass `'p_sense_id': sense_id` (the exercise's `word_sense_id`, already resolved in that method) to
`record_session_progress`. Pass it only when `session_mode == 'acquisition'`; maintenance attempts
pass `None`. Pass `'p_is_tail': True` when the practice session was requested with `tail=1` (the payload
echoes `tail: true`; the client echoes it on the attempt POST), else `False`.

### Tail ordering

`get_session(..., tail=True, mode='maintenance')` re-sorts the selected maintenance items most-overdue first
(earliest `user_flashcards.due_date` / `user_word_ladder.review_due_at` first; one query for the selected
senses). The existing maintenance selection RPC is not modified (its internal ordering is not verified in
this spec); the re-sort applies to the items it returns. The main-session maintenance chunks use the same
ordering when `tail` is absent and reviews are scheduled in the main session, so the most overdue reviews are
always served first.

## Session route: optional tail (`routes/study_session.py`, TASK-872)

`GET /api/study-session` response adds:

```
governor: {level, overdue_items, overdue_minutes, threshold_minutes, new_words_quota, new_words_effective}
tail:     null | {reviews_left_items, reviews_left_minutes, new_words_left, new_words_left_minutes}
tail_queue: [ ... ]   # [] unless tail is not null
```

- `main_complete` = every item of `queue` with `is_bonus` falsy is completed. `progress.total` and
  `progress.completed` keep counting only `queue`; **tail items are never in `queue`**, so session
  completion is unchanged ("optional tail = not required for session completion").
- `tail` is computed live, only when `main_complete`: `reviews_left_items = gov.due_items` (0 if `practice` is
  excluded), `reviews_left_minutes = reviews_left_items * gov.item_seconds / 60`;
  `new_words_left = max(0, min(E - ST, U))` with `E = effective_new_words(quota_today, gov.level)` and `U`, `ST` from
  `ladder_new_word_state` (see 'Quota semantics'; `ST` includes carried-over words started today);
  `new_words_left_minutes = round(new_words_left * mpnw)`. If both
  are 0 the value is `null`. Tail acquisition chunks serve `unstarted_sense_ids` first.
- `tail_queue` items (reviews **before** new words; reviews most-overdue first):
  `{'kind': 'practice', 'id': 'tail_maint_{k}', 'mode': 'maintenance', 'minutes': c, 'is_bonus': True, 'is_tail': True, 'is_completed': False}`,
  then `tail_acq_{k}` with `'mode': 'acquisition'`. Chunk sizes are <= `_PRACTICE_CHUNK_MAX_MIN` (10). At most
  `TAIL_OFFER_MAX_MIN` (20) minutes are offered per round: `maint_min = min(reviews_left_minutes, 20)`, then
  `acq_min = min(new_words_left_minutes, 20 - maint_min)`. `k` continues from the number of already completed
  `tail_maint_*` / `tail_acq_*` ids in `completed_blocks`, so ids never collide across rounds.
- `_valid_block_ids` also accepts the ids of the current `tail_queue`, so `POST /complete-block` works. The
  practice service credits the minutes (`record_session_progress`, with `p_is_tail`), so tail work counts toward
  `practice_completed_*_min`, `new_words_completed` and the tail statistics.
- `admit_daily_new_words` runs before `targets` are read; a `needs_rebuild` result triggers one
  `StudyPlanService.rebuild_today`.

Session page (`templates/study_session.html`, `static/js/session/controller.js`): when the last required item
completes and `tail` is not null, the summary panel (`#sessionSummary`, `session.done_title`) shows the prompt
`session.tail.prompt` — **"Session done — {n} reviews and {m} new words left today. Keep going?"** — with
"Keep going" / "Done for today". "Keep going" appends `tail_queue` to the runner and requests
`/api/practice/session?mode=...&minutes=...&tail=1`; when a round ends, the controller re-fetches
`GET /api/study-session` and asks again with the updated counts until `tail` is null. Variants when one count is 0:
`session.tail.prompt_reviews_only`, `session.tail.prompt_words_only`. The governor banner (also on the plan page):
`session.governor.paused` — **"New words paused — catching up on {n} reviews"** (`level = 'paused'`) or
`session.governor.reduced` — **"New words reduced — catching up on {n} reviews"** (`level = 'reduced'`), with
`n = governor.overdue_items`.

## API / RPC Surface

### `GET /api/study-plan?language_id=L` (modified, `routes/study_plan.py`)

- Plan SELECT adds `excluded_modules, budget_scope, new_words_per_day`.
- Week SELECT adds `budget_scope, review_target_minutes, new_words_target, new_words_completed,
  acq_target_minutes, tail_completed_min, tail_new_words_completed`.
- Response adds `available_modules: string[]` (as in session-modules; `practice` is labelled
  "Vocabulary review" in the UI), `minutes_per_new_word: float` (`get_minutes_per_new_word`),
  `typical_day: {practice_room_min_per_day, review_min_per_day}` (`typical_day_inputs`),
  `governor: {level, overdue_items, overdue_minutes, threshold_minutes}` (`get_review_governor`, level `normal`
  when it fails), `forecast: {reviews_per_new_word_30d, item_seconds, min_per_day}` (`min_per_day` for the saved
  `new_words_per_day`), and `today_new_words_shortfall: int | null`
  (`daily_test_loads.daily_session_targets.new_words_shortfall` for `plan_today`, null if no row).
- The current-week lookup keeps using the server date (`_monday_of(date.today())`), as today;
  not changed here.

### `PUT /api/study-plan` (modified)

New body fields: `excluded_modules?: string[]`, `budget_scope?: string`, `new_words_per_day?: int`.

Validation (all `400` via `bad_request`):

| Field | Rule | Message |
|---|---|---|
| `budget_scope` | exactly `'tests_and_review'` or `'tests_only'` | `"budget_scope must be 'tests_and_review' or 'tests_only'"` |
| `new_words_per_day` | `int` (not `bool`, not float) in `[0, 50]` | `"new_words_per_day must be int in [0, 50]"` |
| `excluded_modules` | list of strings | `"excluded_modules must be a list of module codes"` |
| `excluded_modules` | every code in `available_modules` for this language | `"unknown module for this language: <code>"` |

Cross-field rules are evaluated on the **merged** state (value from the request if present, else
the stored value), and run whenever any of the three fields is present:

- `included = available_modules - effective_excluded`. If `included` is empty **and**
  `effective_new_words_per_day == 0`: `"at least one module must remain included"`.
  (Amendment of the session-modules rule: new words per day above 0 counts as an included module.)
- If `effective_scope == 'tests_only'` and `included - {'practice'}` is empty:
  `"tests_only scope needs at least one test or surface module included"`.

Other changes:

- `is_template_only` other-fields tuple adds `'excluded_modules'`, `'budget_scope'`,
  `'new_words_per_day'`.
- **Default for new rows.** In the template-only branch, check before calling
  `apply_study_plan_template` whether a plan row exists. If not, after the RPC runs
  `UPDATE user_study_plans SET new_words_per_day = max(1, daily_minutes // 6)` for the new row
  (the RPC does not set the column, so the DB default 5 would otherwise apply). This is **words per day**:
  5 per day at 30 minutes, about 7x the old per-week reading of `target_new_rate()` (accepted). Changing
  `daily_minutes` or the template on an existing row does **not** recompute `new_words_per_day`.
- **On change.** When any of the three fields is in the request and differs from the stored value,
  run best-effort (as session-modules): `compute_weekly_plan(user, lang, _monday_of(plan_today(...)))`
  then, if `Config.STUDY_PLAN_ENABLED`, `rebuild_today(user, lang)`. Failures log a WARNING and do
  not fail the PUT. Response adds `session_rebuilt: bool`.
- `updated_fields` still lists the keys written.

### `GET /api/study-session` (`routes/study_session.py`)

Speed round: `speed_round_available` is forced `False` when `'practice' in targets.get('excluded_modules', [])`
(session-modules). New fields and tail behaviour: see "Session route: optional tail". Queue building for the
main session still reads `practice_acquisition_min` and `practice_maintenance_min`.

### `POST /api/calibration/end` (`routes/calibration.py`, line 198)

Response unchanged. Side effect added in `calibration_service.end_session`: BKT evidence write for definition mode
(see "Cold start").

### Auth

Unchanged (`supabase_jwt_required`, `g.current_user_id`). `set_new_words_shortfall` and
`refresh_new_word_minutes` are callable only by the backend service role (EXECUTE revoked from `PUBLIC`,
`anon`, `authenticated`). The governor RPCs are `SECURITY DEFINER` and called with the service client with the JWT's `user_id`.

## Component Specification (UI)

### `templates/study_plan.html`: card "Daily session" — layout Option A (ANSWERED 2026-10-13)

- **Placement:** inside `#planEditor`, between the "Weekday shape" card and the "Advanced"
  collapse. It **replaces** the "Daily session modules" card from [[features/session-modules.tech]]
  (same `#moduleToggles` markup, now inside this card).
- **Layout (Option A, single card, stacked sections):** one `.card` titled "Daily session" containing four
  `<section>` blocks stacked in one column and separated by `<hr>`, in this order. The same order on phone width; no
  two-column arrangement, no tabs, no nested cards. (Options B and C of the earlier mock-ups are dropped.)
  1. **What the daily time covers.** Radios `input[name=budgetScope]` with values `tests_and_review` /
     `tests_only` and helper text under each. The `tests_only` radio is disabled when no test or surface module is checked.
  2. **Modules.** `#moduleToggles`, one `form-check form-switch` per `available_modules` entry, checked means
     included. The `practice` label key is `study_plan.modules.practice`, text "Vocabulary review". A toggle is
     disabled only when it is the last checked one **and** `#newWordsInput` is 0.
  3. **New words.** `<input type="number" id="newWordsInput" min="0" max="50" step="1">` with the unit
     "words per day". Hint `#newWordsHint` (below the input). `#reviewForecast` (beside the input):
     **"≈ +{X} min/day of reviews in a month"**, `X = round(avgNewWords * reviews_per_new_word_30d * item_seconds / 60)`
     with `avgNewWords = new_words_week_target(input, weekday_shape) / 7` and the constants taken from
     `forecast` in the GET response (the client never hard-codes 7 or 20). `#governorNote` shows the governor
     message when `governor.level != 'normal'`. **No-review warning:** `#newWordsNoReviewWarning`, a `.form-text text-warning`
     element directly under `#newWordsInput`, is visible when `practice` is excluded (the Vocabulary review toggle is
     unchecked) **and** the input is > 0. Text `T('study_plan.session.new_words_no_review_warning')`:
     **"Vocabulary review is off — words you learn won't be reviewed."** It is advisory only: Save is not blocked and
     the API does not reject the combination (ANSWERED 2026-10-13). Under `tests_only` with Vocabulary review still
     included there is no warning (reviews still happen, in the optional round).
  4. **Typical day.** `#typicalDaySummary`, recomputed on every input change from `typical_day`, `minutes_per_new_word`
     and `current_week` (omitted if there is no current week):
     `inBudgetWords = min(input, floor(typical_day.practice_room_min_per_day / mpnw))` (0 when scope is `tests_only` or
     `practice` is excluded), `tailWords = input - inBudgetWords`.
     - `tests_and_review`: "Typical day: {daily} min (about {inBudgetWords} new words and ~{review_min_per_day} min of
       review inside it). Optional extra round: ~{tailWords} new words (~{round(tailWords*mpnw)} min)." The second
       sentence is omitted when `tailWords = 0`.
     - `tests_only` (or `practice` excluded): "Typical day: {daily} min of tests. Optional extra round: ~{review_min_per_day}
       min of review and {input} new words (~{round(input*mpnw)} min)." The review clause is omitted when `practice` is excluded.
- **Hint text (`#newWordsHint`):** `tests_and_review`: "About {inBudgetWords} of these fit inside your {daily} min; the rest come
  in an optional extra round after your session." `tests_only`: "New words come in an optional extra round after your session."
- **State:** derived from `plan` on `showPlanEditor`; every input change recomputes the hint, forecast, summary and the
  toggle/radio disabled states.
- **Cross-language tally:** `#totalTally` and the per-language `.lang-summary` show `daily_minutes` only (the main
  session). Optional round minutes are not added to the tally.
- **This-week stat tiles:** "New words: {new_words_completed} / {new_words_target}" in `#weekStats`; when
  `tail_completed_min > 0`, a sub-line "{tail_completed_min} min in optional rounds". When `today_new_words_shortfall > 0`, a note:
  `T('study_plan.daily_session.shortfall')` ("{n} short today: exercises for more words are still being prepared").
- **Save:** `#saveBtn` adds `excluded_modules`, `budget_scope`, `new_words_per_day` to the PUT body.
  Banner uses `session_rebuilt`.
- **i18n keys** (add to `static/i18n/{en,zh,ja,es}.json`): `study_plan.daily_session.title`,
  `.scope.tests_and_review`, `.scope.tests_only`, `.scope.hint`, `.new_words.label`, `.new_words.unit`,
  `.new_words.hint_in_budget`, `.new_words.hint_tail_only`, `.forecast`, `.typical_day`, `.typical_day_tail`,
  `.typical_day_tests_only`, `.shortfall`, `.last_module_hint`, `.governor.paused`, `.governor.reduced`,
  `study_plan.session.new_words_no_review_warning` ("Vocabulary review is off — words you learn won't be reviewed."), plus the `study_plan.modules.*` keys of session-modules with `study_plan.modules.practice` reworded.
  Stat tile: `study_plan.stats.new_words`. Session page: `session.tail.prompt`, `session.tail.prompt_reviews_only`,
  `session.tail.prompt_words_only`, `session.tail.keep_going`, `session.tail.done`, `session.governor.paused`,
  `session.governor.reduced`.

## Key Architectural Decisions

1. **Decision:** `budget_scope` is stored on the plan and snapshotted onto each weekly state.
   - **Rationale:** the plan is the live setting (Tier C reads it for defence in depth); the state
     snapshot keeps the weekly numbers self-consistent when a recompute lags.
   - **Alternatives rejected:** a scope read only from the plan (state numbers could contradict it).
2. **Decision:** `new_words_per_day` is an Anki-style daily quota inside the planner, not a separate time pool.
   Tier C fits what fits in the in-budget practice share; the rest is an optional tail. See
   [[decisions/ADR-033-budget-scope-and-new-word-budget]] (Revision 2026-10-13 (b)).
   - **Alternatives rejected:** an extra pool outside `daily_minutes` (superseded: made the day longer than
     the learner's number); new-word minutes (hides the cost per word); a hard cap at what fits (the learner
     asked for a quota, not a ceiling).
3. **Decision:** minutes per new word is a per-language nightly estimate on `dim_languages`,
   with `Config.NEW_WORD_MINUTES_DEFAULT` as fallback.
   - **Alternatives rejected:** a separate table (see Migration 3); a single global constant (ignores script and language differences).
4. **Decision:** a per-local-day admission quota replaces the pool-floor trigger.
   - **Rationale:** the floor was an eligible-pool target, not a rate; `user_word_ladder.created_at`
     (task741) makes the quota expressible, and the local-day boundary follows [[decisions/ADR-022-local-day-boundary]].
5. **Decision:** shortfall is surfaced, not hidden or back-filled with unservable words; the minutes that
   unserved words would have used return to tests inside the budget.
   - **Alternatives rejected:** admitting words below the supply gate (the live failure the gate was built for);
     silently padding with review; leaving the day short.
6. **Decision:** reviews are scheduled before new words inside the budget; due reviews that do not fit go to the tail,
   ahead of the remaining new words, most-overdue first.
   - **Alternatives rejected:** new words first (new cards starve reviews, the classic failure of a fixed new-card quota).
7. **Decision:** a review-load governor scales the quota by backlog: `E = Q` if `backlog <= T`, `floor(Q/2)` if
   `T < backlog <= 2T`, `0` otherwise, with `T = REVIEW_BACKLOG_THRESHOLD_DAYS` days of the weekly review target / 7
   (floor 3 min). Disabled when `practice` is excluded.
   - **Alternatives rejected:** a continuous scale (harder to explain and test); no governor (a quota of 5/day is about
     7x the old rate, and unchecked it buries the learner in reviews).
8. **Decision:** the shares stay in the schema as derived observability values; the relaxed CHECK stays because the derived
   values reach 1.0 / 0.0.
   - **Alternatives rejected:** dropping the columns (high blast radius across migrations and readers); writing a constant
     1.0 / 0.0 (misleading now that acquisition lives in the practice pool again); restoring the original bounds (cannot hold
     when `new_words_per_day = 0`).
9. **Decision:** calibration (definition mode) writes BKT evidence through the existing batch RPC with
   `side_effects=False`; a single wrong answer admits to Queue A2, below A1. Evidence provenance is read from the existing
   calibration ledger plus one `bkt_applied_at` marker, not from a new column on `user_vocabulary_knowledge`.
   - **Alternatives rejected:** a `source` column on `user_vocabulary_knowledge` (one row mixes sources, so a column cannot
     be right per sense without a per-source counter table); extending the batch RPC with `p_exercise_type` (numerically
     identical today); letting calibration seed the ladder directly (bypasses the quota and the supply gate).
10. **Decision:** with Vocabulary review excluded or `tests_only`, all new words are served in the tail.
    - **Rationale:** the in-budget pool then holds only tests and surfaces. ANSWERED 2026-10-13: confirmed; the combination
      `new_words_per_day > 0` with Vocabulary review off is allowed, the API does not reject it, and the UI warns
      (`study_plan.session.new_words_no_review_warning`).
11. **Decision:** `new_words_per_day` is an Anki-like count of words **started** per local day. Intake tops up
    `(unstarted admitted + started today)` to the effective quota; unstarted words carry over and are served first.
    - **Rationale:** a learner who skips a day should not accumulate an unbounded new-word backlog, and admitted words
      should not be silently dropped.
    - **Alternatives rejected:** counting admissions (unstarted words would be re-admitted on top of the carried-over ones,
      inflating the ladder); a rollover/owed counter (extra state, and it compounds a missed day).

## Security Considerations

- Writes only through the authenticated route with `user_id` from the JWT. Enum and range checks
  in the route plus the DB CHECKs; booleans are rejected for `new_words_per_day`.
- `set_new_words_shortfall`, `refresh_new_word_minutes` are service-role only. All new
  `SECURITY DEFINER` functions pin `search_path`. `new_words_for_day`, `new_word_minutes`,
  `review_governor_level` and `new_words_effective` are pure/read-only and expose no user data;
  `review_governor_state`, `ladder_new_word_state` and `review_item_seconds` read only the caller-supplied `p_user_id`'s rows and are not
  granted to `anon` / `authenticated`.
- `new_words_per_day <= 50` bounds how many ladder rows one learner can create per day; combined with
  `LADDER_TOPUP_MAX_PER_CALL` it bounds the generation-queue load.
- `/api/calibration/end` ownership is already checked by `_load_session`; the BKT write uses the session's own
  `user_id`. `bkt_applied_at` makes a replayed `/end` a no-op, so a client cannot inflate `evidence_count`.
- No new data exposure: `minutes_per_new_word` is a public aggregate.

## Testing Strategy

- **Unit, Tier B (`tests/test_session_budget_settings.py`, new):**
  - `new_words_for_day`: ties at .5 (`npd=5, w=1.1 -> 6`; `npd=1, w=0.5 -> 1`), 0 on weight 0, 0 on npd 0, shape default.
  - `new_words_week_target`: all-ones shape = `7*npd`; `[1.4,1.4,1.4,1.4,1.4,0,0]` and `npd=5` -> `5*7=35`.
  - `rebalance_practice`: review share clamps to 0.15/0.50; practice clamped to the cap; returns `(0, 0, ...)` for zero template minutes.
  - `compute_weekly_plan` (stubbed DB): both scopes persist the expected keys; derived shares sum to 1.00 and equal
    1.00/0.00 when `review + acq = 0`; `acq_target_minutes = min(quota minutes, P - review)`; `tests_only` and
    `practice`-excluded give `acq_target_minutes = 0` and `practice_target_minutes = 0`; `tests_only` keeps a review
    target within the tail cap; with defaults `target_counts`, `practice_target_minutes` and `total_weekly_minutes`
    equal the pre-change values; review carry-over decays and respects the cap; new words are not carried.
  - Governor and forecast: `review_governor_level` at `backlog == T` (normal), just above `T` (reduced), `== 2T` (reduced),
    above `2T` (paused); `effective_new_words(5,'reduced') == 2`, `(1,'reduced') == 0`, `(5,'paused') == 0`;
    `review_forecast_min_per_day(5, 20.0) == 11.666...`; `get_review_governor` failure returns `normal`.
  - Mirror pins: Python vs SQL `new_words_for_day`, `review_governor_level`, `new_words_effective` on a grid;
    `Config.NEW_WORD_MINUTES_DEFAULT`, `REVIEW_BACKLOG_THRESHOLD_DAYS`, `REVIEW_ALLOWANCE_FLOOR_MIN`,
    `REVIEW_ITEM_SECONDS_DEFAULT` vs the SQL constants; `BUDGET_SCOPES` vs the SQL CHECK list parsed from
    `migrations/session_module_exclusions.sql`.
- **Route (`tests/test_session_budget_settings_routes.py`, new):** each validation message above; merged-state rules
  (`new_words_per_day=0` PUT while stored exclusions cover every module -> 400; excluding every module with
  `new_words_per_day>0` -> 200); `tests_only` with only `practice` included -> 400; `is_template_only` false for each new
  field; new-row default `max(1, daily//6)` as words per day; recompute and `rebuild_today` only on change; `session_rebuilt`;
  GET shape including `typical_day`, `governor`, `forecast`.
- **SQL (`tests/sql/test_session_budget_settings.sql`, new, same harness as `tests/sql/test_task705_same_day_safe.sql`):**
  - scenario A Monday (reviews first, then new words, leftover to tests) and scenario B (all 30 minutes to tests,
    `practice_*_min = 0`); weight-0 day yields `Q = 0`; `practice` excluded gives `practice_maintenance_min = 0` and
    `practice_acquisition_min = 0` with `new_words_per_day > 0` (all words go to the tail);
  - governor levels `reduced` and `paused` change `new_words_effective`, `new_words_in_budget` and `returned_to_tests_minutes`;
  - a same-day rebuild with `new_words_supply_checked = true` and a shortfall lowers `new_words_in_budget` and raises
    the test budget; without the flag the prior shortfall is ignored;
  - `daily_session_targets` carries the new keys; same-day rebuild keeps completed slots (TASK-705);
  - `compute_weekly_plan_persist` accepts the old six-key payload and never overwrites `new_words_completed`,
    `tail_completed_min`, `tail_new_words_completed`;
  - `record_session_progress` increments `new_words_completed` once per sense, only when the sense's first-ever
    `exercise_attempts` row is on the learner's local day (a word admitted days ago and first attempted today counts; a
    second attempt or a first attempt on an earlier day does not), adds the
    tail columns only with `p_is_tail`, and is a no-op on a retried attempt;
  - the relaxed shares CHECK accepts `1.00 / 0.00` and `0.30 / 0.70` and rejects `0.6 / 0.6`;
  - `bkt_update_exercise(p, c, 'definition_match') = bkt_update_word_test(p, c)` on a grid;
  - `review_governor_state` counts overdue (`due_date < p_date`, `review_due_at < local midnight`) and due-now items once per sense
    across both sources.
- **Service, intake (`tests/test_ladder_new_word_quota.py`, new):** quota resets at **local** midnight (use `Asia/Tokyo`
  and a UTC instant just before and after Tokyo midnight); `want_raw = new_today - (U + ST)` with the governor applied; unstarted admitted words from earlier days carry over and reduce intake one for one; `ladder_new_word_state` counts a word as started by its first-ever `exercise_attempts` row (SQL test: no attempts = unstarted, attempt before local midnight = not started today, attempt after = started today, retries do not change it)
  (`reduced`, `paused`); capped by `LADDER_TOPUP_MAX_PER_CALL`; Queue A1 restricted to senses seen in tests within the window,
  recency-ranked first; A1 ignores the calibration contribution (`evidence_count - cal_n`); A2 admits a sense with one wrong
  calibration answer and no other evidence, is skipped when `status` is `known`, outside the age window, in `exclude`, or when
  the latest answer was correct; A2 is only consulted when A1 did not fill `want`; Queue B stub returns `[]`; starved
  nominations reach `_request_generation`; `set_new_words_shortfall` called with the unmet count; `needs_rebuild` only on the first
  supply check; no plan, `npd=0` and weight-0 days return `[]`; `local_day_start_utc` across a DST change and a bad zone name.
- **Calibration (`tests/test_calibration_bkt_evidence.py`, new):** definition-mode `/end` calls the batch method once with
  `side_effects=False` and the answered anchors only; pronunciation mode never calls it; a second `/end` does not call it again
  (`bkt_applied_at`); a write failure resets the marker and does not fail `/end`; skips (`chosen_sense_id IS NULL`,
  `is_correct = false`, `answered_at` set) are sent as incorrect and unanswered rows are not sent;
  `update_from_word_tests_batch(side_effects=False)` does not call `_seed_ladder_for_new_words`, `_auto_create_flashcards` or
  `_trigger_frequency_inference`, and the default still does (dictation unchanged).
- **Session route (`tests/test_study_session_tail.py`, new):** `tail` null until every non-bonus `queue` item is complete; `tail_queue`
  puts `tail_maint_*` before `tail_acq_*`, at most 20 minutes per round, ids continue across rounds; `progress` ignores tail
  items; `complete-block` accepts a current tail id and rejects a stale one; governor fields present; under `tests_only` all
  new words appear in the tail.
- **Settings UI:** `#newWordsNoReviewWarning` is visible only when Vocabulary review is unchecked and `#newWordsInput > 0`; it
  does not block Save; `PUT /api/study-plan` with `excluded_modules = ['practice']` and `new_words_per_day = 5` returns 200.
- **Regression:** `tests/test_weekly_plan_seeding.py`, `tests/test_plannable_surfaces.py`, `tests/test_daily_load_retry_slot.py`,
  and the existing `rebalance_practice` tests (rewrite for the new signature). The defaults (`tests_and_review`, nothing
  excluded) leave the weekly counts and totals unchanged; only Tier C's practice composition (reviews first, whole new words,
  leftover to tests) differs.
- **Rollout check (TASK-869 amended):** apply migrations 1, 5, 2, 3, 4, 6 in that order; deploy code; run the weekly recompute
  (`_run_weekly_plan_recompute`) so every in-flight week has the new columns; spot-check one learner per scope.

## Worked Example

ZH 30-minute template (101), the same numbers as the worked example in
[[features/session-modules.tech]]: per-slot minutes reading 6, listening 5, dictation 6,
pinyin 4, classifier_drill 4, flashcards 7, dual_translation 12; weekly counts reading 6, listening 5,
dictation 2, pinyin 1, classifier_drill 1, flashcards 7, dual_translation 2; template
`practice_total_minutes = 90`. Test/surface minutes = 36+25+12+4+4+49+24 = **154**.
Settings: `daily_minutes = 30` (ceiling `30*7 = 210`), default shape (all weekday weights 1),
`new_words_per_day = 5` (backfill `30 // 6`, per day), nothing excluded, `minutes_per_new_word = 3.0` (fallback),
`item_seconds = 20` (fallback).
Assumed signals: `weakness_global = 0.5` (so `flex_factor = 1.0`), `maint_pressure = 0.5`,
`base_maintenance_share = 0.30`.

**Scenario A, `tests_and_review` (defaults). Tier B:**
- `apply_module_exclusions` is the identity; counts stay at the template (154 min).
- `P0 = round(90 * 1.0) = 90`. `review_share = clamp(0.15, 0.30 * (0.5 + 0.5), 0.50) = 0.30`; `review = round(90 * 0.30) = 27`.
  `P = min(max(90, 27), 210) = 90`.
- `new_words_target = 7 * 5 = 35`; `acq_quota_min = 35 * 3.0 = 105`; `acq_target_minutes = min(105, 90 - 27) = 63`.
- `total_weekly_minutes = min(154 + 90, 210) = 210`; `practice_target_minutes = 90`.
  Shares: `maintenance_share = 27 / (27 + 63) = 0.30`, `acquisition_share = 0.70`.
- Typical-day inputs: `practice_day = 210/7 * 90 / 244 = 11.07`; `review_min_per_day = 27/7 = 3.86`;
  `practice_room_min_per_day = 7.21`.

**Scenario A, Monday (Tier C).** `today_budget = 30`; `v_practice_minutes_total = 90`, test outstanding 154, so
`v_practice_budget = 30 * 90 / 244 = 11.07`, `v_test_budget = 18.93`. Governor: overdue backlog 0, `level = normal`, so `E = Q = 5`.
Due reviews now: 18 items, `v_due_min = 18 * 20 / 60 = 6.0`.
- Reviews first: `v_r_main = min(11.07, 6.0) = 6.0`.
- New words: `S = min(5, floor((11.07 - 6.0) / 3.0)) = min(5, 1) = 1`; `v_a_main = 3.0`.
- Returned to tests: `11.07 - 6.0 - 3.0 = 2.07`; `v_test_budget = 21.0`.
- Main session: ~21 min tests/surfaces + 6 review + 3 new-word (1 word) = **30 min**. Optional tail: 4 new words (~12 min), 0 reviews.
  Session end: "Session done — 0 reviews and 4 new words left today. Keep going?" (reviews-0 variant: "Session done — 4 new words left today. Keep going?").
- Typical-day text (card): `inBudgetWords = min(5, floor(7.21 / 3.0)) = 2`, `tailWords = 3` -> "Typical day: 30 min (about 2 new words
  and ~4 min of review inside it). Optional extra round: ~3 new words (~9 min)."
- Forecast beside the input: `X = 5 * 7 * 20 / 60 = 11.67` -> "≈ +12 min/day of reviews in a month". At 5 new words a day the
  review load a month on is about the size of the whole in-budget practice share, which is the cost the developer accepted.

**Governor on the same Monday** (assume every due item is also overdue, so due minutes equal backlog minutes).
`T = 1.0 * max(3, 27/7 = 3.857) = 3.857` min (about 11.6 items at 20 s):
- backlog 10 items (3.33 min): `normal`, `E = 5`.
- backlog 18 items (6.0 min): `3.857 < 6.0 <= 7.714` -> `reduced`, `E = floor(5/2) = 2`; `v_r_main = 6.0`; `S = min(2, 1) = 1`; tail new words 1.
  Banner: "New words reduced — catching up on 18 reviews".
- backlog 45 items (15.0 min): `> 7.714` -> `paused`, `E = 0`, `S = 0`; `v_r_main = min(11.07, 15.0) = 11.07`, nothing returned to tests.
  Tail: the other 3.93 min (about 12 items) of due reviews, no new words. Banner: "New words paused — catching up on 45 reviews".

**Scenario B, `tests_only`. Tier B:**
- `eff_excluded = {'practice'}`: `apply_module_exclusions`: `M_total = 244`, `M_fixed = 49`, `M_scalable = 105`, `k = 195/105 = 1.857`.
  Raw: reading 11.143, listening 9.286, dictation 3.714, pinyin 1.857, classifier_drill 1.857, dual_translation 3.714 (sum 31.571, N = 32).
  Floors 11, 9, 3, 1, 1, 3 = 28; the 4 spare units go to classifier_drill and pinyin (.857; classifier_drill first on key order), then dictation and dual_translation (.714).
- Counts: reading 11, listening 9, dictation 4, pinyin 2, classifier_drill 2, flashcards 7, dual_translation 4 = 248 min.
- `P = 0`, `acq_target_minutes = 0`, `practice_target_minutes = 0`. Review is still sized as a weekly **tail target**:
  `review = 27`, tail cap `floor(210 * 0.5) = 105`, so `review_target_minutes = 27`. Shares 1.00 / 0.00.
- `total_weekly_minutes = min(248 + 0, 210) = 210`.
- Monday, Tier C: `v_practice_in = false`, so `v_practice_budget = 0`, `v_test_budget = 30`, `practice_*_min = 0`. Main session: 30 min of tests.
  Tail: the 18 due reviews (6 min), then 5 new words (15 min): "Session done — 18 reviews and 5 new words left today. Keep going?"
  Round 1 offers 6 min of review + 14 min of new words (20 min cap), round 2 the rest.
- Typical-day text: "Typical day: 30 min of tests. Optional extra round: ~4 min of review and 5 new words (~15 min)."

**Intake, Monday 09:00 Tokyo, new learner after calibration and two intro tests:** `Q = 5`, governor `normal`, `new_today = 5`,
`U = 0`, `ST = 0`, `want_raw = 5`, `want = 5`. Queue A1 (intro-test unknowns, recency first) yields 2 candidates, 1 passes the supply gate. A2
(calibration wrongs, most frequent first) yields 12 candidates, 2 pass the gate, so 3 words are admitted; Queue B is empty.
`shortfall = 5 - 3 = 2`, written with `new_words_supply_checked = true`. `S_planned = 1 <= U + ST + 3 = 3`, so no rebuild is needed. The tail
then offers the 2 other admitted words; the 2 unobtainable words are reported as "2 short today" on the plan page, and exercise
generation has been requested for the starved nominations. Had `S_planned` been 4, the one-off rebuild would have returned the unusable
minutes to tests.
