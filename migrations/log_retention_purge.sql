-- =============================================================================
-- log_retention_purge.sql  (codebase review 2026-11, Efficiency)
-- =============================================================================
-- Purpose: the append-only log tables have no retention and grow without bound:
--   llm_calls                 one row per LLM call, with the full raw_response text
--   generation_stage_timings  one row per pipeline stage per artifact
--   app_error_logs            one row per logged application error
-- This adds public.purge_old_log_rows(...), which trims them by age. It is NOT
-- scheduled anywhere: creating the function changes nothing until someone calls
-- it (by hand, or from a job added later).
--
-- What a call does, per table (a NULL age skips that table):
--   llm_calls                 SET raw_response = NULL on rows older than
--                             p_llm_raw_response_days. The row itself (model,
--                             cost, latency, verdict) is kept for reporting.
--   generation_stage_timings  DELETE rows older than p_stage_timings_days.
--   app_error_logs            DELETE rows older than p_error_logs_days.
-- At most p_batch_limit rows per table per call, so one call holds its locks
-- briefly; call again until every count comes back below the limit.
-- p_dry_run defaults to TRUE: it only counts what a real run would touch.
-- Ages under 7 days are refused.
--
-- Pre-checks before the first real run:
--   1. Confirm nothing needs old raw responses or old rows. In the repo:
--        grep -rnE "table\(['\"](llm_calls|generation_stage_timings|app_error_logs)" services scripts routes app.py
--      (readers found at authoring time are reporting / smoke scripts under
--      scripts/; check that none reads raw_response or rows older than the
--      ages you pass.)
--   2. Size of the job:
--        SELECT public.purge_old_log_rows();          -- dry run, default ages
--   3. Export first if old raw responses matter: a real run cannot be undone.
--
-- Example real run:
--   SELECT public.purge_old_log_rows(p_dry_run => false);
--   SELECT public.purge_old_log_rows(180, NULL, 30, 20000, false);
-- Space is returned to the table by autovacuum, not to the disk; run
-- VACUUM (FULL) or pg_repack separately if disk must shrink.
--
-- Idempotent (CREATE OR REPLACE). Not SECURITY DEFINER; EXECUTE for service_role only.
-- REQUIRES USER APPROVAL TO APPLY LIVE, and separately to run with
-- p_dry_run => false: nulled responses and deleted rows cannot be restored.
--
-- Rollback:
--   DROP FUNCTION IF EXISTS public.purge_old_log_rows(integer, integer, integer, integer, boolean);
-- =============================================================================

BEGIN;

CREATE OR REPLACE FUNCTION public.purge_old_log_rows(
    p_llm_raw_response_days integer DEFAULT 90,
    p_stage_timings_days    integer DEFAULT 180,
    p_error_logs_days       integer DEFAULT 90,
    p_batch_limit           integer DEFAULT 50000,
    p_dry_run               boolean DEFAULT true
) RETURNS jsonb
LANGUAGE plpgsql
SET search_path = public, pg_temp
AS $$
DECLARE
    c_min_days constant integer := 7;
    v_limit   integer := GREATEST(COALESCE(p_batch_limit, 50000), 1);
    v_dry     boolean := COALESCE(p_dry_run, true);
    v_llm     bigint;
    v_timings bigint;
    v_errors  bigint;
BEGIN
    IF LEAST(p_llm_raw_response_days, p_stage_timings_days, p_error_logs_days) < c_min_days THEN
        RAISE EXCEPTION 'retention ages must be at least % days', c_min_days;
    END IF;

    IF p_llm_raw_response_days IS NOT NULL THEN
        IF v_dry THEN
            SELECT count(*) INTO v_llm FROM (
                SELECT 1 FROM llm_calls
                 WHERE created_at < now() - make_interval(days => p_llm_raw_response_days)
                   AND raw_response IS NOT NULL
                 LIMIT v_limit) s;
        ELSE
            WITH old AS (
                SELECT id FROM llm_calls
                 WHERE created_at < now() - make_interval(days => p_llm_raw_response_days)
                   AND raw_response IS NOT NULL
                 LIMIT v_limit
            )
            UPDATE llm_calls l SET raw_response = NULL FROM old WHERE l.id = old.id;
            GET DIAGNOSTICS v_llm = ROW_COUNT;
        END IF;
    END IF;

    IF p_stage_timings_days IS NOT NULL THEN
        IF v_dry THEN
            SELECT count(*) INTO v_timings FROM (
                SELECT 1 FROM generation_stage_timings
                 WHERE created_at < now() - make_interval(days => p_stage_timings_days)
                 LIMIT v_limit) s;
        ELSE
            WITH old AS (
                SELECT id FROM generation_stage_timings
                 WHERE created_at < now() - make_interval(days => p_stage_timings_days)
                 LIMIT v_limit
            )
            DELETE FROM generation_stage_timings g USING old WHERE g.id = old.id;
            GET DIAGNOSTICS v_timings = ROW_COUNT;
        END IF;
    END IF;

    IF p_error_logs_days IS NOT NULL THEN
        IF v_dry THEN
            SELECT count(*) INTO v_errors FROM (
                SELECT 1 FROM app_error_logs
                 WHERE created_at < now() - make_interval(days => p_error_logs_days)
                 LIMIT v_limit) s;
        ELSE
            WITH old AS (
                SELECT id FROM app_error_logs
                 WHERE created_at < now() - make_interval(days => p_error_logs_days)
                 LIMIT v_limit
            )
            DELETE FROM app_error_logs e USING old WHERE e.id = old.id;
            GET DIAGNOSTICS v_errors = ROW_COUNT;
        END IF;
    END IF;

    RETURN jsonb_build_object(
        'dry_run', v_dry,
        'batch_limit', v_limit,
        'llm_calls_raw_response_cleared', v_llm,
        'generation_stage_timings_deleted', v_timings,
        'app_error_logs_deleted', v_errors
    );
END;
$$;

REVOKE ALL ON FUNCTION public.purge_old_log_rows(integer, integer, integer, integer, boolean)
    FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.purge_old_log_rows(integer, integer, integer, integer, boolean)
    TO service_role;

COMMENT ON FUNCTION public.purge_old_log_rows(integer, integer, integer, integer, boolean) IS
    'Retention for llm_calls.raw_response, generation_stage_timings and app_error_logs. '
    'Dry run by default; not scheduled. See migrations/log_retention_purge.sql.';

COMMIT;
