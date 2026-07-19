-- ============================================================================
-- Phase 18 — Study Plans — practice time accrual at seconds granularity
-- Date: 2026-07-19  (TASK-701)
--
-- Problem (F2): record_session_progress rounded each attempt's ms to whole
-- minutes (round(ms/60000)), so a block of short attempts (e.g. 25 s each)
-- credited 0 minutes every time. Combined with players/practice.js posting
-- time_taken_ms: 0, the weekly practice_completed_*_min counters never moved,
-- the resolver re-scheduled the full practice target every day, and week-over-
-- week carry-over was wrong.
--
-- Fix: accrue practice time in SECONDS (new practice_completed_*_sec columns)
-- and derive the minute counters as ROUND(sec/60). The minute columns stay
-- real, readable smallints (compute_weekly_plan / build_daily_session read
-- them unchanged) — they are now a derived projection of the seconds ledger.
--
-- The caller (services/practice_session_service.py) computes the effective
-- per-attempt seconds: measured render→submit elapsed, with clamping — an
-- absurd value (>5 min, i.e. a tab left open) or a missing/zero value falls
-- back to the exercise's expected_seconds (p50) estimate instead of crediting
-- nothing.
--
-- Signature change: p_delta_seconds int is appended (DEFAULT 0). The old
-- 7-arg overload is DROPped first so the two do not become an ambiguous
-- overload set. Both live callers use named-argument invocation:
--   - practice_session_service.record_attempt_with_updates → passes p_delta_seconds
--   - apply_attempt_timing_and_progress (test path) → passes p_delta_minutes only;
--     p_delta_seconds defaults to 0 and the 'test' kind never touches the
--     practice_*_sec/min columns anyway.
--
-- Supersedes phase13_record_session_progress.sql (archived).
-- See wiki/features/study-plans.tech.md "Time accounting" and
-- wiki/features/practice-engine.tech.md.
-- ============================================================================

BEGIN;

-- ---------------------------------------------------------------------------
-- 1. Seconds ledger columns. Fast default (Postgres 11+); backfill from the
--    existing minute counters so no history is lost (sec = min * 60).
-- ---------------------------------------------------------------------------
ALTER TABLE public.weekly_plan_states
    ADD COLUMN IF NOT EXISTS practice_completed_maint_sec int NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS practice_completed_acq_sec   int NOT NULL DEFAULT 0;

UPDATE public.weekly_plan_states
   SET practice_completed_maint_sec = practice_completed_maint_min * 60,
       practice_completed_acq_sec   = practice_completed_acq_min   * 60
 WHERE practice_completed_maint_sec = 0
   AND practice_completed_acq_sec   = 0
   AND (practice_completed_maint_min > 0 OR practice_completed_acq_min > 0);

ALTER TABLE public.weekly_plan_states
    DROP CONSTRAINT IF EXISTS weekly_plan_states_completed_sec_non_negative;
ALTER TABLE public.weekly_plan_states
    ADD CONSTRAINT weekly_plan_states_completed_sec_non_negative
        CHECK (practice_completed_maint_sec >= 0
               AND practice_completed_acq_sec >= 0);

COMMENT ON COLUMN public.weekly_plan_states.practice_completed_maint_sec IS
    'Maintenance practice time accrued this week, in seconds (source of truth). '
    'practice_completed_maint_min is ROUND(this/60), a derived read for the resolver.';
COMMENT ON COLUMN public.weekly_plan_states.practice_completed_acq_sec IS
    'Acquisition practice time accrued this week, in seconds (source of truth). '
    'practice_completed_acq_min is ROUND(this/60), a derived read for the resolver.';

-- ---------------------------------------------------------------------------
-- 2. Redefine the RPC. Drop the old 7-arg overload, then create the 8-arg
--    version that accrues seconds and re-derives the minute counters.
-- ---------------------------------------------------------------------------
DROP FUNCTION IF EXISTS public.record_session_progress(
    uuid, smallint, uuid, text, text, int, int);

CREATE OR REPLACE FUNCTION public.record_session_progress(
    p_user_id        uuid,
    p_language_id    smallint,
    p_attempt_id     uuid,
    p_kind           text,        -- 'test' | 'practice_maint' | 'practice_acq'
    p_skill          text,        -- required when kind='test', else NULL
    p_delta_count    int DEFAULT 0,   -- typically 1 for tests; 0 for practice
    p_delta_minutes  int DEFAULT 0,   -- test path: minutes consumed (kept for tests)
    p_delta_seconds  int DEFAULT 0    -- practice path: seconds consumed (server-computed)
) RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
DECLARE
    v_week_start  date := date_trunc('week', NOW())::date;
    v_log_key     text;
    v_already     boolean;
    v_updated     integer;
    v_sec         int  := GREATEST(0, COALESCE(p_delta_seconds, 0));
    v_maint_delta int  := 0;
    v_acq_delta   int  := 0;
BEGIN
    IF p_kind NOT IN ('test','practice_maint','practice_acq') THEN
        RAISE EXCEPTION 'invalid p_kind=%; must be test|practice_maint|practice_acq', p_kind
            USING ERRCODE = 'check_violation';
    END IF;
    IF p_kind = 'test' AND p_skill IS NULL THEN
        RAISE EXCEPTION 'p_skill required when p_kind=test'
            USING ERRCODE = 'check_violation';
    END IF;

    IF p_kind = 'practice_maint' THEN
        v_maint_delta := v_sec;
    ELSIF p_kind = 'practice_acq' THEN
        v_acq_delta := v_sec;
    END IF;

    v_log_key := CASE p_kind WHEN 'test' THEN p_skill ELSE p_kind END;

    -- Probe for the current week's row; bail quietly if none yet.
    PERFORM 1 FROM public.weekly_plan_states
        WHERE user_id = p_user_id
          AND language_id = p_language_id
          AND week_start_date = v_week_start;
    IF NOT FOUND THEN
        RETURN true;   -- not an error; just nothing to update
    END IF;

    -- Idempotency check: skip if attempt_id is already in the per-key log.
    SELECT EXISTS (
        SELECT 1 FROM public.weekly_plan_states
        WHERE user_id = p_user_id
          AND language_id = p_language_id
          AND week_start_date = v_week_start
          AND session_progress_log -> v_log_key ? p_attempt_id::text
    ) INTO v_already;
    IF v_already THEN
        RETURN false;
    END IF;

    -- Accrue seconds; re-derive the minute counters as ROUND(sec/60). All SET
    -- RHS expressions read the OLD row values, so referencing sec + delta twice
    -- is self-consistent.
    UPDATE public.weekly_plan_states
       SET completed_counts =
             CASE
               WHEN p_kind = 'test' THEN
                 jsonb_set(
                   completed_counts,
                   ARRAY[p_skill],
                   to_jsonb(COALESCE((completed_counts->>p_skill)::int, 0) + p_delta_count)
                 )
               ELSE completed_counts
             END,
           practice_completed_maint_sec = practice_completed_maint_sec + v_maint_delta,
           practice_completed_acq_sec   = practice_completed_acq_sec   + v_acq_delta,
           practice_completed_maint_min =
             ROUND((practice_completed_maint_sec + v_maint_delta) / 60.0)::smallint,
           practice_completed_acq_min =
             ROUND((practice_completed_acq_sec + v_acq_delta) / 60.0)::smallint,
           session_progress_log = jsonb_set(
               session_progress_log,
               ARRAY[v_log_key],
               COALESCE(session_progress_log -> v_log_key, '[]'::jsonb)
                 || to_jsonb(p_attempt_id::text)
           )
     WHERE user_id = p_user_id
       AND language_id = p_language_id
       AND week_start_date = v_week_start;

    GET DIAGNOSTICS v_updated = ROW_COUNT;
    RETURN v_updated > 0;
END $$;

COMMENT ON FUNCTION public.record_session_progress IS
    'Idempotent counter update keyed by attempt_id. Practice time accrues in '
    'seconds (p_delta_seconds) into practice_completed_*_sec; the *_min columns '
    'are re-derived as ROUND(sec/60). Test path uses p_delta_count/p_delta_minutes '
    'and only touches completed_counts. Bails quietly if no weekly_plan_states '
    'row exists for the current week. Returns false on duplicate attempt_id.';

COMMIT;
