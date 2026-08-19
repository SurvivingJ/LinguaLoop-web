-- ============================================================================
-- Study-Plan weekly-recompute advisory-lock RPCs
-- Date: 2026-07-20
-- Task: TASK-706 (daily-session-hardening)
--
-- Two small helper RPCs the weekly Study-Plan recompute cron calls through the
-- supabase client to serialise itself across gunicorn workers. Same pattern as
-- the nightly IRT calibrator's irt_try_lock()/irt_release_lock()
-- (migrations/add_irt_calibration_metadata.sql): postgrest cannot invoke the
-- built-in pg_try_advisory_lock(bigint) directly with a positional bigint via
-- the supabase-py rpc() helper, so we wrap it around a fixed key.
--
--   pg_try_advisory_lock_for_study_plan() — wraps pg_try_advisory_lock, true
--                                           iff this session took the lock.
--   pg_advisory_unlock_for_study_plan()   — wraps pg_advisory_unlock, releases
--                                           the lock this session holds.
--
-- Lock key 1467840848 = 0x577D7950 = ASCII 'StPP' (Study Plan Pacer). Distinct
-- from the IRT job's key (8901234567890123) so the two nightly sweeps never
-- contend. Session-level lock: _run_weekly_plan_recompute() acquires it at the
-- top of the sweep and releases it in a finally, on the same connection.
-- ============================================================================

BEGIN;

CREATE OR REPLACE FUNCTION public.pg_try_advisory_lock_for_study_plan()
RETURNS boolean
LANGUAGE sql
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT pg_try_advisory_lock(1467840848::bigint);
$$;

CREATE OR REPLACE FUNCTION public.pg_advisory_unlock_for_study_plan()
RETURNS boolean
LANGUAGE sql
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT pg_advisory_unlock(1467840848::bigint);
$$;

COMMIT;
