---
title: Study Plans — Technical Specification
type: feature-tech
status: planned
prose_page: ./study-plans.md
last_updated: 2026-05-21
dependencies:
  - "migrations/study_plans_v1/003_dim_study_plan_templates.sql — templates seed"
  - "migrations/study_plans_v1/004_dim_study_goals.sql — empty in V1"
  - "migrations/study_plans_v1/005_alter_test_attempts_duration.sql — started_at + duration_ms"
  - "migrations/study_plans_v1/006_alter_daily_test_loads_targets.sql — daily_session_targets jsonb"
  - "migrations/study_plans_v1/009_create_user_study_plans.sql"
  - "migrations/study_plans_v1/010_create_weekly_plan_states.sql"
  - "migrations/study_plans_v1/rpcs/{apply_study_plan_template,compute_weekly_plan,build_daily_session,record_session_progress}.sql"
  - "services/study_plan_service.py (new)"
  - "services/test_service.py — get_or_create_daily_load routing"
  - "routes/settings.py — /api/study-plan endpoints"
  - "app.py — cron registration"
  - "user_skill_ratings, user_word_ladder, user_vocabulary_knowledge, user_flashcards (read)"
  - "daily_test_loads, daily_test_load_items, test_attempts, exercise_attempts (read/write)"
breaking_change_risk: medium
---

# Study Plans — Technical Specification

## Architecture Overview

```
                  ┌────────────────────────────────────┐
                  │  user_study_plans (per language)   │
                  │  template_id, daily_minutes,       │
                  │  weekday_shape, overrides, tz      │
                  └─────────────────┬──────────────────┘
                                    │
              ┌─────────────────────┴───────────────────┐
              │                                          │
   ┌──────────▼──────────┐                    ┌─────────▼──────────┐
   │ Tier B (weekly)     │                    │ Tier C (daily)      │
   │ compute_weekly_plan │                    │ build_daily_session │
   │ Cron: Sun 23:00 UTC │                    │ Lazy: first req/day │
   │                     │                    │                     │
   │ Reads:              │                    │ Reads:              │
   │  user_skill_ratings │                    │  weekly_plan_states │
   │  user_word_ladder   │                    │  daily_test_loads   │
   │  user_vocabulary_*  │                    │   (last 3 days)     │
   │  user_flashcards    │                    │                     │
   │  test_attempts(28d) │                    │ Writes:             │
   │                     │                    │  daily_test_loads   │
   │ Writes:             │                    │   .test_ids         │
   │  weekly_plan_states │                    │   .daily_session_   │
   │                     │                    │     targets jsonb   │
   └─────────────────────┘                    └─────────────────────┘
                                                       │
                                ┌──────────────────────┴───┐
                                │                          │
                       ┌────────▼────────┐       ┌────────▼─────────┐
                       │ Tests surface   │       │ Practice Engine  │
                       │ get_or_create_  │       │ get_practice_    │
                       │ daily_load      │       │ session reads    │
                       │ (reads test_ids)│       │ daily_session_   │
                       │                 │       │ targets minutes  │
                       └─────────────────┘       └──────────────────┘
                                                       │
                                                       │ each submit:
                                                       │
                                            ┌──────────▼───────────┐
                                            │ record_session_      │
                                            │ progress             │
                                            │ updates weekly_plan_ │
                                            │ states counters      │
                                            └──────────────────────┘
```

## Schema

### New columns on existing tables

```sql
-- 005_alter_test_attempts_duration.sql
ALTER TABLE test_attempts
  ADD COLUMN started_at  timestamptz,
  ADD COLUMN duration_ms integer
    CHECK (duration_ms IS NULL OR (duration_ms > 0 AND duration_ms < 3600000));

-- 006_alter_daily_test_loads_targets.sql
ALTER TABLE daily_test_loads
  ADD COLUMN daily_session_targets jsonb;
-- jsonb shape:
-- { "practice_maintenance_min": int, "practice_acquisition_min": int,
--   "resolver_solved_at": timestamptz, "objective_value": numeric }

-- 007_alter_user_exercise_sessions_mode.sql
ALTER TABLE user_exercise_sessions
  ADD COLUMN mode           text CHECK (mode IN ('acquisition','maintenance','auto')),
  ADD COLUMN target_minutes smallint;

-- 008_alter_dim_test_types_p50.sql
ALTER TABLE dim_test_types
  ADD COLUMN expected_minutes_p50 numeric(4,1);
```

### New tables

```sql
-- 003_dim_study_plan_templates.sql
CREATE TABLE dim_study_plan_templates (
  template_id                smallint PRIMARY KEY,
  language_id                smallint NOT NULL REFERENCES dim_languages(id),
  daily_minutes              smallint NOT NULL,
  weekly_test_counts         jsonb    NOT NULL,
  practice_total_minutes     smallint NOT NULL,
  base_maintenance_share     numeric(3,2) NOT NULL DEFAULT 0.30,
  practice_minutes_flex_pct  numeric(3,2) NOT NULL DEFAULT 0.25,
  is_default                 boolean  NOT NULL DEFAULT false,
  UNIQUE (language_id, daily_minutes)
);

-- Seed: Chinese
INSERT INTO dim_study_plan_templates VALUES
  (101, 1, 30, '{"reading":6,"listening":5,"dictation":2,"pinyin":1,"measure_word":1}',  90, 0.30, 0.25, true ),
  (102, 1, 45, '{"reading":8,"listening":7,"dictation":3,"pinyin":2,"measure_word":1}', 135, 0.30, 0.25, false),
  (103, 1, 60, '{"reading":10,"listening":9,"dictation":4,"pinyin":2,"measure_word":2}',180, 0.30, 0.25, false);
-- Japanese
INSERT INTO dim_study_plan_templates VALUES
  (201, 3, 30, '{"reading":6,"listening":6,"dictation":2,"pitch_accent":1}',  95, 0.30, 0.25, true ),
  (202, 3, 45, '{"reading":8,"listening":8,"dictation":3,"pitch_accent":2}', 140, 0.30, 0.25, false),
  (203, 3, 60, '{"reading":11,"listening":10,"dictation":4,"pitch_accent":3}',185, 0.30, 0.25, false);
-- English
INSERT INTO dim_study_plan_templates VALUES
  (301, 2, 30, '{"reading":7,"listening":6,"dictation":2}', 100, 0.30, 0.25, true ),
  (302, 2, 45, '{"reading":10,"listening":8,"dictation":3}',150, 0.30, 0.25, false),
  (303, 2, 60, '{"reading":13,"listening":11,"dictation":4}',200, 0.30, 0.25, false);

-- 004_dim_study_goals.sql (V2 placeholder; empty in V1)
CREATE TABLE dim_study_goals (
  goal_id      smallint PRIMARY KEY,
  goal_type    text NOT NULL,
  target_value text,
  target_date  date,
  language_id  smallint REFERENCES dim_languages(id)
);

-- 009_create_user_study_plans.sql
CREATE TABLE user_study_plans (
  user_id                  uuid     NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  language_id              smallint NOT NULL REFERENCES dim_languages(id),
  template_id              smallint NOT NULL REFERENCES dim_study_plan_templates(template_id),
  daily_minutes            smallint NOT NULL CHECK (daily_minutes BETWEEN 10 AND 180),
  weekday_shape            jsonb    NOT NULL DEFAULT '[1,1,1,1,1,1,1]'::jsonb,
  skill_weight_overrides   jsonb    NOT NULL DEFAULT '{}'::jsonb,
  goal_id                  smallint REFERENCES dim_study_goals(goal_id),
  timezone                 text     NOT NULL DEFAULT 'UTC',
  created_at               timestamptz NOT NULL DEFAULT NOW(),
  updated_at               timestamptz NOT NULL DEFAULT NOW(),
  PRIMARY KEY (user_id, language_id)
);

-- 010_create_weekly_plan_states.sql
CREATE TABLE weekly_plan_states (
  user_id                       uuid     NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  language_id                   smallint NOT NULL REFERENCES dim_languages(id),
  week_start_date               date     NOT NULL,                 -- Monday
  target_counts                 jsonb    NOT NULL,
  completed_counts              jsonb    NOT NULL DEFAULT '{}'::jsonb,
  practice_target_minutes       smallint NOT NULL,
  practice_completed_maint_min  smallint NOT NULL DEFAULT 0,
  practice_completed_acq_min    smallint NOT NULL DEFAULT 0,
  maintenance_share             numeric(3,2) NOT NULL,
  acquisition_share             numeric(3,2) NOT NULL,
  total_weekly_minutes          smallint NOT NULL,
  session_progress_log          jsonb    NOT NULL DEFAULT '{}'::jsonb,
  computed_at                   timestamptz NOT NULL DEFAULT NOW(),
  PRIMARY KEY (user_id, language_id, week_start_date)
);

CREATE INDEX idx_weekly_plan_states_week ON weekly_plan_states (week_start_date);
```

### Migration sequence

| # | File | Purpose |
|---|---|---|
| 001 | `dim_exercise_types.sql` | Create + backfill from `exercises.exercise_type DISTINCT` |
| 002 | `dim_practice_modes.sql` | Create + seed 3 rows |
| 003 | `dim_study_plan_templates.sql` | Create + seed 9 rows (3 langs × 3 buckets) |
| 004 | `dim_study_goals.sql` | Create (empty) |
| 005 | `alter_test_attempts_duration.sql` | Add `started_at`, `duration_ms` |
| 006 | `alter_daily_test_loads_targets.sql` | Add `daily_session_targets jsonb` |
| 007 | `alter_user_exercise_sessions_mode.sql` | Add `mode`, `target_minutes` |
| 008 | `alter_dim_test_types_p50.sql` | Add `expected_minutes_p50` |
| 009 | `create_user_study_plans.sql` | Create |
| 010 | `create_weekly_plan_states.sql` | Create + index |

**Pre-launch wipe (revised 2026-05-22 — supersedes backfill per plan R4.2 and [[decisions/ADR-013-global-feature-flag-rollout]])**

Run **once** against the target DB right before flipping `Config.STUDY_PLAN_ENABLED = True`. Drops all per-user state so the new flow starts on a clean slate. Reference data (`dim_*`, `tests`, `questions`, `exercises`, `word_assets`, packs, auth) is untouched.

```sql
-- migrations/phase13_wipe_user_state_for_launch.sql
BEGIN;
TRUNCATE TABLE
    public.user_skill_ratings,
    public.user_vocabulary_knowledge,
    public.user_word_ladder,
    public.user_flashcards,
    public.user_exercise_sessions,
    public.user_exercise_history,
    public.daily_test_load_items,
    public.daily_test_loads,
    public.test_attempts,
    public.exercise_attempts,
    public.user_study_plans,
    public.weekly_plan_states
RESTART IDENTITY CASCADE;
COMMIT;
```

After the wipe:
- New signups create `user_study_plans` rows via onboarding → `apply_study_plan_template` RPC.
- Any leftover users without plan rows fall through to legacy `_compute_daily_load` (handled in `services/test_service.py::get_or_create_daily_load`).
- No `INSERT … ON CONFLICT DO NOTHING` backfill is needed; the original backfill SQL is preserved as reference-only in the plan file (`C:\Users\James\.claude\plans\goal-continue-through-the-parsed-goblet.md`) for possible future scenarios where we want to seed plans for inherited users.

<details><summary>Reference-only backfill SQL (do NOT run during pre-launch rollout)</summary>

```sql
INSERT INTO user_study_plans (user_id, language_id, template_id, daily_minutes,
                              weekday_shape, skill_weight_overrides, goal_id, timezone)
SELECT u.id, l.id, t.template_id, 30, '[1,1,1,1,1,1,1]'::jsonb, '{}'::jsonb, NULL, 'UTC'
FROM (SELECT DISTINCT user_id AS id
        FROM test_attempts WHERE created_at > NOW() - INTERVAL '30 days') u
CROSS JOIN (SELECT id FROM dim_languages WHERE is_active) l
JOIN dim_study_plan_templates t
  ON t.language_id = l.id AND t.is_default = true
ON CONFLICT (user_id, language_id) DO NOTHING;
```
</details>

## RPC: `apply_study_plan_template`

```sql
CREATE OR REPLACE FUNCTION public.apply_study_plan_template(
  p_user_id uuid, p_language_id smallint, p_template_id smallint
) RETURNS user_study_plans
LANGUAGE sql AS $$
  INSERT INTO user_study_plans (user_id, language_id, template_id, daily_minutes)
  SELECT p_user_id, p_language_id, p_template_id, t.daily_minutes
  FROM dim_study_plan_templates t WHERE t.template_id = p_template_id
  ON CONFLICT (user_id, language_id) DO UPDATE
    SET template_id = EXCLUDED.template_id,
        daily_minutes = EXCLUDED.daily_minutes,
        updated_at = NOW()
  RETURNING *;
$$;
```

## RPC: `compute_weekly_plan` (Tier B)

Implementation in PL/pgSQL or Python (`services/study_plan_service.py`); pseudocode-equivalent in [[algorithms/study-plan-adaptation.tech]]. Idempotent (R3.8):

```sql
CREATE OR REPLACE FUNCTION public.compute_weekly_plan(
  p_user_id uuid, p_language_id smallint, p_week_start date
) RETURNS jsonb
```

Returns the upserted `weekly_plan_states` row as jsonb.

PK `(user_id, language_id, week_start_date)` guarantees one row per week. Re-running mid-week with changed inputs (e.g. new ELO from a Tuesday test) UPSERTs new `target_counts`, but `completed_counts`, `practice_completed_*_min`, and `session_progress_log` are preserved by the conditional UPDATE.

## RPC: `build_daily_session` (Tier C)

```sql
CREATE OR REPLACE FUNCTION public.build_daily_session(
  p_user_id uuid, p_language_id smallint, p_date date
) RETURNS jsonb
```

Returns the daily_test_loads row + daily_session_targets as jsonb.

Behavior:
1. Look up `weekly_plan_states` for the Monday of `p_date`'s week. If none and `Config.STUDY_PLAN_ENABLED`, call `compute_weekly_plan` then continue. If `Config.STUDY_PLAN_ENABLED = false`, return `{"error":"plan_disabled"}` (callers fall back to legacy `_compute_daily_load`).
2. Compute `today_budget = total_weekly_minutes · weekday_weight[today] / 7`.
3. Run greedy allocator (algorithm in [[algorithms/study-plan-adaptation.tech]]).
4. Hydrate test slots via existing `get_recommended_tests(user, language)` filtered per skill.
5. UPSERT `daily_test_loads` row with computed `test_ids` and `daily_session_targets` jsonb.
6. UPSERT `daily_test_load_items` for each test_id.
7. Return upserted row + targets.

If `weekly_plan_states` row exists but Tier B failed somehow, fall back to template defaults (no carry-over) and log a warning. Logged for monitoring.

## RPC: `record_session_progress`

```sql
CREATE OR REPLACE FUNCTION public.record_session_progress(
  p_user_id        uuid,
  p_language_id    smallint,
  p_attempt_id     uuid,            -- test_attempts.id or exercise_attempts.id
  p_kind           text,            -- 'test' | 'practice_maint' | 'practice_acq'
  p_skill          text,            -- nullable; required for 'test'
  p_delta_count    int,             -- typically 1 for tests, 0 for practice
  p_delta_minutes  int              -- minutes consumed
) RETURNS boolean                    -- false if attempt_id already recorded
LANGUAGE plpgsql AS $$
DECLARE
  v_week_start date := date_trunc('week', NOW())::date;  -- Monday
  v_log_key    text := CASE p_kind
                         WHEN 'test' THEN p_skill
                         ELSE p_kind
                       END;
  v_already    boolean;
BEGIN
  -- Idempotency: check if attempt_id already in log
  SELECT EXISTS (
    SELECT 1 FROM weekly_plan_states
    WHERE user_id = p_user_id AND language_id = p_language_id
      AND week_start_date = v_week_start
      AND session_progress_log -> v_log_key ? p_attempt_id::text
  ) INTO v_already;
  IF v_already THEN RETURN false; END IF;

  -- Update counters + append to log
  UPDATE weekly_plan_states SET
    completed_counts = CASE
      WHEN p_kind = 'test' THEN
        jsonb_set(completed_counts, ARRAY[p_skill],
                  to_jsonb(COALESCE((completed_counts->>p_skill)::int, 0) + p_delta_count))
      ELSE completed_counts
    END,
    practice_completed_maint_min = practice_completed_maint_min
      + CASE WHEN p_kind = 'practice_maint' THEN p_delta_minutes ELSE 0 END,
    practice_completed_acq_min = practice_completed_acq_min
      + CASE WHEN p_kind = 'practice_acq' THEN p_delta_minutes ELSE 0 END,
    session_progress_log = jsonb_set(
      session_progress_log,
      ARRAY[v_log_key],
      COALESCE(session_progress_log->v_log_key, '[]'::jsonb) || to_jsonb(p_attempt_id::text)
    )
  WHERE user_id = p_user_id AND language_id = p_language_id
    AND week_start_date = v_week_start;

  RETURN true;
END;
$$;
```

Called from:
- `process_test_submission` (inside the same transaction).
- `record_attempt_with_updates` in the practice service.

## Modified RPCs / services

| Surface | Change |
|---|---|
| `process_test_submission` (and dictation/pinyin/pitch variants) | **Unchanged.** Body-of-RPC modification was deferred during implementation in favor of a side-car hook RPC — see next row. The submission RPCs are entangled with ELO + idempotency + retry-slot factor + furigana and a 4× duplication would have been brittle. Timing capture has no influence on ELO calculation, so isolating it in a hook is clean. |
| `apply_attempt_timing_and_progress(p_attempt_id, p_started_at, p_finished_at) RETURNS jsonb` **(new)** | Post-submission hook called by `routes/tests.py` after each submission RPC returns its `attempt_id`. Atomically: (a) UPDATEs `test_attempts(started_at, duration_ms)` after computing `duration_ms = (finished − started)·1000` and silently capping to (0, 3_600_000); (b) calls `record_session_progress(..., 'test', <skill from dim_test_types.type_code>, 1, duration_minutes)`. NULL-timestamp-tolerant (skips the UPDATE while still recording progress). Best-effort: failures are warned, not raised. See `migrations/phase13_apply_attempt_timing_and_progress.sql`. |
| `services/test_service.py::get_or_create_daily_load` | If `Config.STUDY_PLAN_ENABLED` AND `user_study_plans` row exists for (user, language), call `build_daily_session(user, language, today)`; else legacy `_compute_daily_load`. External signature unchanged. |
| `services/practice_session_service.py::record_attempt_with_updates` | Accept `session_mode` from caller; call `record_session_progress(..., 'practice_'||mode, NULL, 0, time_taken_ms/60_000)`. |
| `routes/tests.py` — all 4 submit handlers (`submit_test_attempt`, `submit_pinyin_attempt`, `submit_pitch_accent_attempt`, `submit_dictation_attempt`) | Read `started_at` / `finished_at` from request body and call `_apply_timing_and_progress(client, attempt_id, body)` helper right after the submission RPC succeeds. Helper wraps the new hook RPC and logs (but does not raise) on failure. |

## Cron jobs

`app.py:227-251` additions:

```python
# Sunday 23:00 UTC — weekly recompute
scheduler.add_job(
    _run_weekly_plan_recompute,
    trigger=CronTrigger(day_of_week='sun', hour=23, minute=0),
    id='study_plan_weekly_recompute', coalesce=True, max_instances=1,
)

# 04:05 UTC — refresh time estimates
scheduler.add_job(
    _refresh_exercise_time_estimates,
    trigger=CronTrigger(hour=4, minute=5),
    id='exercise_time_estimate_refresh', coalesce=True, max_instances=1,
)
```

`_run_weekly_plan_recompute` iterates `user_study_plans` rows, calls `compute_weekly_plan(user, language, this_week_monday)` for each. Wraps in advisory lock (same pattern as `_run_irt_calibration`).

## HTTP endpoints

| Method | Path | Body | Returns |
|---|---|---|---|
| GET | `/api/study-plan?language_id=:l` | — | `user_study_plans` row + current `weekly_plan_states` row |
| PUT | `/api/study-plan` | `{ language_id, daily_minutes?, weekday_shape?, skill_weight_overrides?, template_id? }` | Updated row |
| POST | `/api/study-plan/recompute` | `{ language_id }` | Result of `compute_weekly_plan(user, lang, this_week_monday)` |
| GET | `/api/study-plan/templates?language_id=:l` | — | Array of `dim_study_plan_templates` for the language |

All require authenticated session; `user_id` from `flask.g.user_id`.

## Config additions

```python
class Config:
    # Existing constants...
    STUDY_PLAN_ENABLED                 = False  # flip in rollout step 6
    STUDY_PLAN_DEFAULT_DAILY_MINUTES   = 30
    STUDY_PLAN_TIER_C_ALPHA_M          = 0.02
    STUDY_PLAN_TIER_C_ALPHA_A          = 0.02
    STUDY_PLAN_TIER_C_GAMMA            = 0.15

    # Test-type minute seed (used until dim_test_types.expected_minutes_p50
    # accrues ≥ 30 samples per type)
    TEST_TYPE_MINUTES = {
        'reading':       6,
        'listening':     5,
        'dictation':     6,
        'pinyin':        4,
        'measure_word':  4,
        'pitch_accent':  4,
    }
```

## Rollout sequence

Per [[decisions/ADR-013-global-feature-flag-rollout]] (revised 2026-05-22 — pre-launch wipe path):

1. **Ship migrations.** Apply all `phase12_*.sql` and `phase13_*.sql` migrations (schema + RPCs + helpers + `phase13_wipe_user_state_for_launch.sql`). `Config.STUDY_PLAN_ENABLED = False` still. Schema-only effect; no behaviour change.
2. **Ship Practice merger.** Deploy `get_practice_session` + deprecation wrappers. Smoke-check against a handful of seeded dev users in both modes. Full parity testing (R4.7) is optional pre-launch since the wipe at step 4 drops all reference attempt history anyway.
3. **Ship Settings UI + onboarding.** Deploy the `routes/practice.py` + `routes/study_plan.py` blueprints and the Settings tab so onboarding can call `apply_study_plan_template`. Still flag-off — the route exists but `get_or_create_daily_load` continues routing to legacy.
4. **Wipe.** Run `phase13_wipe_user_state_for_launch.sql` once. TRUNCATE … RESTART IDENTITY CASCADE on all 12 user-state tables; reference data untouched.
5. **Flip.** Set `Config.STUDY_PLAN_ENABLED = True` and deploy. From this moment:
   - First-time signups → onboarding → `apply_study_plan_template` → `user_study_plans` row → next daily-load runs through `build_daily_session`.
   - Any leftover users without plans keep getting legacy `_compute_daily_load` until they visit Settings.
   - Sunday 23:00 UTC cron computes the first weekly state for every `user_study_plans` row.
6. **Monitor.** Track DAU, session-completion-rate, sessions-per-DAU, tests-per-session, practice-minutes-per-session.
7. **Rollback** by toggling `Config.STUDY_PLAN_ENABLED = False` if any metric looks pathological. Rollback is instant; legacy `_compute_daily_load` resumes for every user (`weekly_plan_states` rows just go unread).
8. **Deprecation cycle.** After 30 days stable, remove the `get_exercise_session` / `get_ladder_session` deprecation wrappers; replace `/api/exercises/session` and `/api/vocab-dojo/session` handlers with 302s to `/api/practice/session`.

## Worked Example

User U, Chinese, 45 min/day uniform weekday, week 4.

**Inputs (snapshot):**

| Skill | ELO | First-attempt acc 28d | n attempts 28d |
|---|---|---|---|
| reading | 1350 | 0.71 | 24 |
| listening | 1100 | 0.58 | 22 |
| dictation | 1280 | 0.68 | 12 |
| pinyin | 1450 | 0.82 | 8 |
| measure_word | 1380 | 0.74 | 8 |

Mean ELO 1312. Subscribed senses 180, stagnant 58, FSRS reviews 28d=92, lapses 28d=17. Active ladder 80, FSRS due today 22, BKT-decayed 12. Known words 105. Stuck 14. New 7d 6.

**Weakness per skill:**

```
ladder_stagnation = 58/180 = 0.322
fsrs_lapse_rate   = 17/92  = 0.185
elo_gap(listening) = 1.000 (saturates)
elo_gap(dictation) = 0.160
elo_gap(reading)   = 0      (above mean)
weakness(listening) = 0.40·1.0 + 0.25·0.17 + 0.20·0.322 + 0.15·0.185 = 0.535
weakness(reading)   = 0    + 0.25·0.04 + 0.0644 + 0.02775 = 0.102
weakness(dictation) = 0.40·0.16 + 0.25·0.07 + 0.0644 + 0.02775 = 0.174
weakness(pinyin)    = 0 + 0 + 0.0921 = 0.092
weakness(measure_word) = 0 + 0.0025 + 0.0921 = 0.095
```

All skills well below ELO 1800 → `diminishing = 0` → `value = weakness`.

**Bandit (seeded Beta sampling):**

```
acc_sample(reading)≈0.72, listening≈0.55, dictation≈0.66, pinyin≈0.78, measure_word≈0.73

bandit_score = value · (1 - acc_sample):
  reading: 0.0286, listening: 0.2408, dictation: 0.0592, pinyin: 0.0202, measure_word: 0.0257
  total: 0.3745
```

**Allocation (template total = 8+7+3+2+1 = 21):**

```
raw: reading 1.60, listening 13.50, dictation 3.32, pinyin 1.13, measure_word 1.44
floors:  reading 4, listening 4, dictation 2, pinyin 1, measure_word 1
ceilings: reading 12, listening 11, dictation 5, pinyin 3, measure_word 2

after clamp: reading 4, listening 11, dictation 3, pinyin 1, measure_word 1 = 20
overflow +1 → next highest unsaturated (listening saturated): dictation → 4

Final: reading=4, listening=11, dictation=4, pinyin=1, measure_word=1  (total 21) ✓
```

**Practice rebalancing (daily_minutes = 45):**

```
target_review_rate = 22, target_active_pool = 45, target_new_rate = 7

maintenance_pressure = clamp01(60/154) + 0.5·clamp01(12/105) = 0.390 + 0.057 = 0.447
acquisition_pressure = clamp01(14/45)  + 0.3·clamp01(6/7)   = 0.311 + 0.257 = 0.568

raw_ratio = 0.568 / (0.447 + 0.568) = 0.560
acq_share = clamp(0.50, 0.560, 0.85) = 0.560
maint_share = 0.440

weakness_global = 0.200
flex_factor = 1 + 0.25·(0.400 - 1) = 0.85
practice_minutes = round(135·0.85) = 115 min
  practice_maint = 115·0.440 ≈ 51
  practice_acq   = 115·0.560 ≈ 64
```

**Total weekly minutes:**

```
test min = 4·6 + 11·5 + 4·6 + 1·4 + 1·4 = 24+55+24+4+4 = 111
total_weekly_minutes = 111 + 115 = 226
```

**Monday daily resolve:**

```
today_budget = 226 · 1/7 ≈ 32.3
upper_cap    = 48.4
lower_cap    = 22.6

per-minute values:
  reading 0.017, listening 0.107, dictation 0.029, pinyin 0.023, measure_word 0.024
  maint chunk 0.0088/min, acq chunk 0.0112/min

Greedy fill (high → low) within upper_cap with spacing penalty for last-3-day repeats:
  listening (5 min) × 3 = 15 min   (spacing already paid for first; no per-slot penalty)
  dictation (6 min) × 1 = 6 min    (spacing 0.05)
  measure_word (4 min) × 1 = 4 min
  pinyin (4 min) × 1 = 4 min
  acq chunk (10 min) × 1 = 10 min
  reading (6 min) × 1 = 6 min      (spacing 0)
                              ────
                       total: 45 min  (within 48.4 cap)

Local swap pass: no profitable swaps.

Resolved: tests [listening, listening, listening, dictation, measure_word, pinyin, reading]
          acq_min 10, maint_min 0
```

Hydrated via `get_recommended_tests` taking top-1 ELO match per skill slot.

**Monday Practice call:**

`GET /api/practice/session?mode=auto&minutes=10`

`daily_session_targets = { practice_maintenance_min: 0, practice_acquisition_min: 10 }` → resolves to `'acquisition'`.

Top word by ladder priority: sense_id=4521 (Tier-2, ring=2, gated, priority=0.78). Ring 2 families = [meaning_recall, form_production, collocation], K=3.

```
For meaning_recall:  unified score 0.40·0.78 + 0.30·0.71 + 0.25·0.95 + 0.05·0.50 = 0.788
For form_production: pick top item (similar math)
For collocation:     pick top item
```

3 items × ~45s = 135s elapsed. Gate A pending → assemble 3-item battery (180s). Elapsed = 315s.

Next word: sense_id=2117, ring=1, K=1. Pick 1 item. Elapsed = 360s.
Next: sense_id=3801, ring=3, K=1. Pick 1 item. Elapsed = 405s.
Next: sense_id=5009, ring=2, K=3. Pick 3 items. Elapsed = 540s ≈ target. Stop.

Returned: 11 items across 4 words. User completes 8, submit fires `record_session_progress(..., 'practice_acq', NULL, 0, 7)` → `practice_completed_acq_min` becomes 7.

## Key Architectural Decisions

1. **Tier B writes once a week; Tier C runs lazily on first daily request.** Avoids unnecessary recomputes when a user is idle.
2. **`build_daily_session` UPSERTs `daily_test_loads`** rather than introducing a new "plan today" table. Existing daily-load infrastructure is reused; only one new column (`daily_session_targets jsonb`).
3. **Deterministic Beta seeding** makes Tier B idempotent. Same inputs always produce the same `target_counts`.
4. **Greedy + local-swap allocator in Tier C** rather than ILP. Variables are ≤ 8 (test skills + 2 Practice modes); the optimization is trivial enough that greedy converges to optimal in practice. ILP is a fallback for future expansion.
5. **`record_session_progress` keyed by `attempt_id`** for idempotency. Reuses existing primary keys; no separate dedup table.

## Security Considerations

- All RPCs `SECURITY INVOKER`; `user_id` is server-supplied. RLS protects `user_study_plans`, `weekly_plan_states` (one row per user, write-protected to own user).
- `compute_weekly_plan` and `build_daily_session` can be called by either the user or admin; admin override path is `SECURITY DEFINER` wrapper with `is_admin(...)` check.
- Cron runs with service-role auth; iterates rows directly.

## Testing Strategy

- **Unit:** weakness signal terms with seeded inputs (cold-start, saturated ELO gap, all-zero counters).
- **Unit:** `bandit_score()` determinism — same seed produces same sample across runs.
- **Unit:** Allocator water-fill — overflow redistribution under various floor/ceiling configurations.
- **Unit:** `rebalance_practice` boundary clamping (acq_share = 0.85 cap, 0.50 floor).
- **Integration:** End-to-end worked example reproduction (Section "Worked Example") — assert numerical match within 0.001.
- **Integration:** `record_session_progress` idempotency — call twice with same `attempt_id`; second returns `false`, counters unchanged.
- **Integration:** Cron job — fire `_run_weekly_plan_recompute` in test mode against seeded users; verify all rows updated.
- **Migration:** Wipe script on staging — verify all 12 user-state tables `COUNT(*) = 0` post-run; verify reference tables (`dim_languages`, `dim_study_plan_templates`, `tests`, `exercises`, `auth.users`, `public.users`) unaffected.

## Related Pages

- [[features/study-plans]] — Plain-English counterpart.
- [[algorithms/study-plan-adaptation.tech]] — Adapter math in depth.
- [[features/practice-engine.tech]] — The Practice surface this orchestrator allocates to.
- [[features/comprehension-tests.tech]] — Test side; `_compute_daily_load` becomes the fallback.
- [[database/schema.tech]] — Full schema (with this spec's tables).
- [[database/rpcs.tech]] — Full RPC catalog (with this spec's RPCs).
- [[decisions/ADR-008-study-plan-orchestration-layer]], [[decisions/ADR-009-two-budget-tests-vs-practice]],
  [[decisions/ADR-010-value-weighted-thompson-skill-mix]], [[decisions/ADR-011-per-language-independent-budgets]],
  [[decisions/ADR-013-global-feature-flag-rollout]].
