-- ============================================================================
-- Phase 13 — Study Plans — record_session_progress RPC
-- Date: 2026-05-21
--
-- Called by every test/practice submit to increment the live counters on the
-- current week's weekly_plan_states row.
--
-- Idempotency:
--   Keyed by p_attempt_id (test_attempts.id OR exercise_attempts.id). The
--   per-skill or per-mode jsonb array in session_progress_log carries
--   every attempt_id we've already counted. Second call with the same
--   attempt_id returns false; counters are NOT incremented.
--
-- Resilience:
--   If no weekly_plan_states row exists for the current week (e.g., Sunday
--   cron hasn't run yet for a brand-new user), the function returns true
--   without doing anything — Tier B will pick the user up at the next cron
--   tick and start fresh counters.
--
-- Week boundary:
--   Monday 00:00 UTC. The week_start_date is derived from NOW() via
--   date_trunc('week') which uses ISO weeks (Monday-anchored).
--
-- See wiki/features/study-plans.tech.md.
-- ============================================================================

BEGIN;

CREATE OR REPLACE FUNCTION public.record_session_progress(
    p_user_id        uuid,
    p_language_id    smallint,
    p_attempt_id     uuid,
    p_kind           text,        -- 'test' | 'practice_maint' | 'practice_acq'
    p_skill          text,        -- required when kind='test', else NULL
    p_delta_count    int,         -- typically 1 for tests; 0 for practice
    p_delta_minutes  int          -- minutes consumed (server-computed)
) RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
DECLARE
    v_week_start date := date_trunc('week', NOW())::date;
    v_log_key    text;
    v_already    boolean;
    v_updated    integer;
BEGIN
    IF p_kind NOT IN ('test','practice_maint','practice_acq') THEN
        RAISE EXCEPTION 'invalid p_kind=%; must be test|practice_maint|practice_acq', p_kind
            USING ERRCODE = 'check_violation';
    END IF;
    IF p_kind = 'test' AND p_skill IS NULL THEN
        RAISE EXCEPTION 'p_skill required when p_kind=test'
            USING ERRCODE = 'check_violation';
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
           practice_completed_maint_min =
             practice_completed_maint_min
             + CASE WHEN p_kind = 'practice_maint' THEN GREATEST(0, p_delta_minutes) ELSE 0 END,
           practice_completed_acq_min =
             practice_completed_acq_min
             + CASE WHEN p_kind = 'practice_acq' THEN GREATEST(0, p_delta_minutes) ELSE 0 END,
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
    'Idempotent counter update keyed by attempt_id. Bails quietly if no '
    'weekly_plan_states row exists for the current week. Returns false on '
    'duplicate attempt_id, true on first apply or no-op.';

COMMIT;
