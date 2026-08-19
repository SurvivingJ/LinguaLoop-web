-- ============================================================================
-- Model-slug health nightly advisory-lock RPCs
-- Date: 2026-08-08
-- Task: TASK-510 (exercise-generation-v2)
--
-- Two helper RPCs the nightly slug-health probe (services/model_health.py)
-- calls through the supabase client to serialise itself across gunicorn
-- workers. Same pattern as the nightly IRT calibrator's irt_try_lock() /
-- irt_release_lock() (migrations/add_irt_calibration_metadata.sql) and the
-- Study-Plan pacer (migrations/study_plan_advisory_lock.sql): postgrest cannot
-- invoke the built-in pg_try_advisory_lock(bigint) with a positional bigint
-- via supabase-py's rpc() helper, so we wrap it around a fixed key.
--
--   pg_try_advisory_lock_for_model_health() — true iff this session took it.
--   pg_advisory_unlock_for_model_health()   — releases the session's lock.
--
-- Lock key 1298417772 = 0x4D64486C = ASCII 'MdHl' (Model Health). Distinct
-- from the IRT job's key and the Study-Plan pacer's 1467840848 so the nightly
-- sweeps never contend. Session-level lock: run_slug_health_check() acquires
-- it at the top and releases it in a finally, on the same connection.
--
-- New objects only — no existing object is redefined, so no older migration
-- is superseded by this file (migrations/CLAUDE.md rule 1).
-- ============================================================================

BEGIN;

CREATE OR REPLACE FUNCTION public.pg_try_advisory_lock_for_model_health()
RETURNS boolean
LANGUAGE sql
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT pg_try_advisory_lock(1298417772::bigint);
$$;

CREATE OR REPLACE FUNCTION public.pg_advisory_unlock_for_model_health()
RETURNS boolean
LANGUAGE sql
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT pg_advisory_unlock(1298417772::bigint);
$$;

COMMIT;
