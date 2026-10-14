-- session_module_exclusions.sql — daily-session settings: module exclusions + budget
-- =============================================================================
-- TASK-863 (session-modules) as amended 2026-10-13 by session-budget-settings.
-- Spec: wiki/features/session-modules.tech.md (Database Impact),
--       wiki/features/session-budget-settings.tech.md (Migration 1),
--       wiki/decisions/ADR-032-session-module-exclusion.md,
--       wiki/decisions/ADR-033-budget-scope-and-new-word-budget.md.
--
-- Contents:
--   (a) user_study_plans.excluded_modules text[]  + CHECK ..._excluded_modules_known
--   (b) user_study_plans.budget_scope, new_words_per_day (+ CHECKs, per-day backfill)
--   (c) weekly_plan_states: budget_scope, review_target_minutes, new_words_target,
--       new_words_completed, acq_target_minutes, tail_completed_min,
--       tail_new_words_completed (+ CHECKs); relaxed weekly_plan_states_shares_sum;
--       in-flight rows split practice_target_minutes into review / acquisition
--   (d) dim_languages.new_word_minutes_est (written nightly by TASK-870)
--   (e) SQL helpers new_words_for_day, new_word_minutes and the redefined
--       compute_weekly_plan_persist (supersedes phase13_compute_weekly_plan_helpers.sql)
--
-- Apply order (TASK-869): this file, review_governor.sql, then
-- session_module_exclusions_build_daily_session.sql, new_word_minutes_estimate.sql,
-- new_words_completed_accrual.sql, calibration_bkt_evidence.sql.
--
-- Pattern per migrations/CLAUDE.md: single-pass UPDATEs, every new CHECK is added
-- NOT VALID inside the transaction and VALIDATEd in separate statements after COMMIT.
-- Idempotent: safe to run twice (the new_words_per_day backfill only runs on the
-- run that adds the column, so a re-run never clobbers a learner's setting).
-- =============================================================================

BEGIN;

-- (a) session-modules DDL ------------------------------------------------------
ALTER TABLE public.user_study_plans
    ADD COLUMN IF NOT EXISTS excluded_modules text[] NOT NULL DEFAULT '{}'::text[];

-- Known module vocabulary. Mirrors services/study_plan_service.py::ALL_MODULES.
-- Adding a module means changing both; test_session_modules.py pins that they agree.
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint
                    WHERE conname = 'user_study_plans_excluded_modules_known'
                      AND conrelid = 'public.user_study_plans'::regclass) THEN
        ALTER TABLE public.user_study_plans
            ADD CONSTRAINT user_study_plans_excluded_modules_known
            CHECK (excluded_modules <@ ARRAY[
                'reading','listening','dictation','pinyin','classifier_drill',
                'pitch_accent','flashcards','dual_translation','practice'
            ]::text[]) NOT VALID;
    END IF;
END $$;

COMMENT ON COLUMN public.user_study_plans.excluded_modules IS
    'Modules left out of daily-session planning (Tier B + Tier C) for this language. '
    'Does not restrict manual use. See wiki/features/session-modules.tech.md.';

-- (b) user_study_plans: budget scope + new words per day -------------------------
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                    WHERE table_schema = 'public' AND table_name = 'user_study_plans'
                      AND column_name = 'new_words_per_day') THEN
        ALTER TABLE public.user_study_plans
            ADD COLUMN new_words_per_day smallint NOT NULL DEFAULT 5;
        -- DEFAULT 5 is a SAFETY default only (a row inserted by a path that does not
        -- set the column, e.g. the apply_study_plan_template RPC). The intended default
        -- is max(1, daily_minutes // 6) PER DAY: the route sets it for new rows and
        -- this backfill sets it for existing rows. ANSWERED 2026-10-13: about 7x the
        -- old per-week rate, accepted knowingly. Integer division; max 180/6 = 30.
        UPDATE public.user_study_plans
           SET new_words_per_day = GREATEST(1, daily_minutes / 6)
         WHERE new_words_per_day IS DISTINCT FROM GREATEST(1, daily_minutes / 6);
    END IF;
END $$;

ALTER TABLE public.user_study_plans
    ADD COLUMN IF NOT EXISTS budget_scope text NOT NULL DEFAULT 'tests_and_review';

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint
                    WHERE conname = 'user_study_plans_budget_scope_known'
                      AND conrelid = 'public.user_study_plans'::regclass) THEN
        ALTER TABLE public.user_study_plans
            ADD CONSTRAINT user_study_plans_budget_scope_known
            CHECK (budget_scope IN ('tests_and_review','tests_only')) NOT VALID;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint
                    WHERE conname = 'user_study_plans_new_words_per_day_range'
                      AND conrelid = 'public.user_study_plans'::regclass) THEN
        ALTER TABLE public.user_study_plans
            ADD CONSTRAINT user_study_plans_new_words_per_day_range
            CHECK (new_words_per_day BETWEEN 0 AND 50) NOT VALID;
    END IF;
END $$;

COMMENT ON COLUMN public.user_study_plans.budget_scope IS
    'tests_and_review (default): vocabulary review and the new-word practice share sit inside daily_minutes. '
    'tests_only: only tests/surfaces are in budget; all review and new words go to the optional tail. '
    'See wiki/features/session-budget-settings.tech.md.';
COMMENT ON COLUMN public.user_study_plans.new_words_per_day IS
    'Anki-style daily quota of new words STARTED per local day (0..50). Not a separate time pool. '
    'Default and backfill: max(1, daily_minutes // 6).';

-- (c) weekly_plan_states -------------------------------------------------------
ALTER TABLE public.weekly_plan_states
    ADD COLUMN IF NOT EXISTS budget_scope              text NOT NULL DEFAULT 'tests_and_review',
    ADD COLUMN IF NOT EXISTS review_target_minutes     int  NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS new_words_target          int  NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS new_words_completed       int  NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS acq_target_minutes        int  NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS tail_completed_min        int  NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS tail_new_words_completed  int  NOT NULL DEFAULT 0;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint
                    WHERE conname = 'weekly_plan_states_budget_scope_known'
                      AND conrelid = 'public.weekly_plan_states'::regclass) THEN
        ALTER TABLE public.weekly_plan_states
            ADD CONSTRAINT weekly_plan_states_budget_scope_known
            CHECK (budget_scope IN ('tests_and_review','tests_only')) NOT VALID;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint
                    WHERE conname = 'weekly_plan_states_new_columns_non_negative'
                      AND conrelid = 'public.weekly_plan_states'::regclass) THEN
        ALTER TABLE public.weekly_plan_states
            ADD CONSTRAINT weekly_plan_states_new_columns_non_negative
            CHECK (review_target_minutes >= 0 AND new_words_target >= 0
                   AND new_words_completed >= 0 AND acq_target_minutes >= 0
                   AND tail_completed_min >= 0 AND tail_new_words_completed >= 0) NOT VALID;
    END IF;
END $$;

-- The original shares CHECK (phase13_weekly_plan_states.sql) demands
-- maintenance_share in [0.10, 0.55] and acquisition_share in [0.45, 0.90]. The shares are
-- now DERIVED (maintenance = review / (review + acq_in_budget)), so they legitimately reach
-- 1.0 / 0.0 (new_words_per_day = 0, tests_only, practice excluded). Relax to "valid shares
-- that sum to 1". Still required after the 2026-10-13 (b) revision.
ALTER TABLE public.weekly_plan_states DROP CONSTRAINT IF EXISTS weekly_plan_states_shares_sum;
ALTER TABLE public.weekly_plan_states
    ADD CONSTRAINT weekly_plan_states_shares_sum
        CHECK (maintenance_share BETWEEN 0 AND 1
               AND acquisition_share BETWEEN 0 AND 1
               AND abs(maintenance_share + acquisition_share - 1.0) <= 0.011) NOT VALID;

-- In-flight rows at deploy time: split the old practice target into review and
-- acquisition so the current week still schedules both until Tier B recomputes.
-- Current and prior week only; single pass; rows already split are not rewritten.
UPDATE public.weekly_plan_states
   SET review_target_minutes = ROUND(practice_target_minutes * maintenance_share)::int,
       acq_target_minutes    = practice_target_minutes
                               - ROUND(practice_target_minutes * maintenance_share)::int
 WHERE week_start_date >= (CURRENT_DATE - 14)
   AND review_target_minutes = 0
   AND practice_target_minutes > 0;

COMMENT ON COLUMN public.weekly_plan_states.new_words_completed IS
    'Words STARTED that local day (the sense''s first-ever exercise_attempts row falls on that day), '
    'main session or tail, counted once per sense. Preserved across recomputes.';
COMMENT ON COLUMN public.weekly_plan_states.tail_completed_min IS
    'Minutes of practice done in optional-tail blocks this week (informational; also in practice_completed_*_min). Preserved across recomputes.';

-- (d) per-language cost of one new word (written nightly by TASK-870) ---------------
ALTER TABLE public.dim_languages
    ADD COLUMN IF NOT EXISTS new_word_minutes_est numeric(4,2) NULL
        CHECK (new_word_minutes_est IS NULL OR new_word_minutes_est BETWEEN 0.5 AND 15.0);

COMMENT ON COLUMN public.dim_languages.new_word_minutes_est IS
    'Observed minutes to introduce one new word in this language (refresh_new_word_minutes, TASK-870). '
    'NULL = use the 3.0 default (public.new_word_minutes).';

-- (e) helper functions ---------------------------------------------------------
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

-- compute_weekly_plan_persist — SUPERSEDES the definition in
-- phase13_compute_weekly_plan_helpers.sql (that file is multi-object and stays).
--
-- Differences vs phase13:
--   * four NEW keys are OPTIONAL: budget_scope (default 'tests_and_review'),
--     review_target_minutes, new_words_target, acq_target_minutes (integers, default 0),
--     so a Tier B deployed before this migration, or an older worker, still persists.
--   * INSERT sets new_words_completed = tail_completed_min = tail_new_words_completed = 0.
--   * ON CONFLICT DO UPDATE writes the four new keys' columns from EXCLUDED and NEVER
--     touches new_words_completed / tail_completed_min / tail_new_words_completed (same
--     contract as completed_counts, practice_completed_*, session_progress_log).
CREATE OR REPLACE FUNCTION public.compute_weekly_plan_persist(
    p_user_id     uuid,
    p_language_id smallint,
    p_week_start  date,
    p_computed    jsonb
) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER
   SET search_path = public, pg_temp AS $$
DECLARE
    v_row   public.weekly_plan_states%ROWTYPE;
    v_scope text := COALESCE(NULLIF(p_computed->>'budget_scope', ''), 'tests_and_review');
BEGIN
    IF NOT (p_computed ? 'target_counts'
            AND p_computed ? 'skill_values'
            AND p_computed ? 'practice_target_minutes'
            AND p_computed ? 'maintenance_share'
            AND p_computed ? 'acquisition_share'
            AND p_computed ? 'total_weekly_minutes') THEN
        RAISE EXCEPTION 'p_computed missing required keys; got %', p_computed
            USING ERRCODE = 'check_violation';
    END IF;

    INSERT INTO public.weekly_plan_states (
        user_id, language_id, week_start_date,
        target_counts, skill_values, completed_counts,
        practice_target_minutes, practice_completed_maint_min,
        practice_completed_acq_min,
        maintenance_share, acquisition_share,
        total_weekly_minutes, session_progress_log,
        budget_scope, review_target_minutes, new_words_target, acq_target_minutes,
        new_words_completed, tail_completed_min, tail_new_words_completed,
        computed_at
    ) VALUES (
        p_user_id, p_language_id, p_week_start,
        p_computed->'target_counts',
        p_computed->'skill_values',
        '{}'::jsonb,                                       -- fresh on insert
        (p_computed->>'practice_target_minutes')::smallint,
        0, 0,
        (p_computed->>'maintenance_share')::numeric,
        (p_computed->>'acquisition_share')::numeric,
        (p_computed->>'total_weekly_minutes')::smallint,
        '{}'::jsonb,                                       -- fresh log on insert
        v_scope,
        COALESCE((p_computed->>'review_target_minutes')::int, 0),
        COALESCE((p_computed->>'new_words_target')::int, 0),
        COALESCE((p_computed->>'acq_target_minutes')::int, 0),
        0, 0, 0,
        NOW()
    )
    ON CONFLICT (user_id, language_id, week_start_date) DO UPDATE
        SET target_counts            = EXCLUDED.target_counts,
            skill_values             = EXCLUDED.skill_values,
            practice_target_minutes  = EXCLUDED.practice_target_minutes,
            maintenance_share        = EXCLUDED.maintenance_share,
            acquisition_share        = EXCLUDED.acquisition_share,
            total_weekly_minutes     = EXCLUDED.total_weekly_minutes,
            budget_scope             = EXCLUDED.budget_scope,
            review_target_minutes    = EXCLUDED.review_target_minutes,
            new_words_target         = EXCLUDED.new_words_target,
            acq_target_minutes       = EXCLUDED.acq_target_minutes,
            computed_at              = EXCLUDED.computed_at
            -- completed_counts, practice_completed_*_min, session_progress_log,
            -- new_words_completed, tail_completed_min, tail_new_words_completed
            -- INTENTIONALLY UNTOUCHED
    RETURNING * INTO v_row;

    RETURN to_jsonb(v_row);
END $$;

COMMENT ON FUNCTION public.compute_weekly_plan_persist IS
    'Atomic UPSERT of Tier B adapter output. Preserves completed_counts, '
    'practice_completed_*_min, session_progress_log, new_words_completed, '
    'tail_completed_min and tail_new_words_completed across mid-week '
    'recomputes (R3.8 idempotency contract). Optional keys: budget_scope, '
    'review_target_minutes, new_words_target, acq_target_minutes.';

COMMIT;

-- VALIDATE outside the exclusive-lock window (SHARE UPDATE EXCLUSIVE; does not block I/O).
ALTER TABLE public.user_study_plans   VALIDATE CONSTRAINT user_study_plans_excluded_modules_known;
ALTER TABLE public.user_study_plans   VALIDATE CONSTRAINT user_study_plans_budget_scope_known;
ALTER TABLE public.user_study_plans   VALIDATE CONSTRAINT user_study_plans_new_words_per_day_range;
ALTER TABLE public.weekly_plan_states VALIDATE CONSTRAINT weekly_plan_states_budget_scope_known;
ALTER TABLE public.weekly_plan_states VALIDATE CONSTRAINT weekly_plan_states_new_columns_non_negative;
ALTER TABLE public.weekly_plan_states VALIDATE CONSTRAINT weekly_plan_states_shares_sum;
