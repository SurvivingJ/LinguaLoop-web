-- ============================================================================
-- Dual Translation nightly-synthesis advisory-lock RPCs
-- Date: 2026-08-21
-- Task: TASK-731 (dt-remediation-infrastructure)
--
-- Two helper RPCs the nightly DT error-synthesis cron calls through the
-- supabase client to serialise itself across gunicorn workers. Same pattern as
-- the weekly Study-Plan recompute (migrations/study_plan_advisory_lock.sql) and
-- the nightly IRT calibrator (migrations/add_irt_calibration_metadata.sql):
-- postgrest cannot invoke the built-in pg_try_advisory_lock(bigint) directly
-- with a positional bigint via the supabase-py rpc() helper, so we wrap it
-- around a fixed key.
--
--   pg_try_advisory_lock_for_dt_synthesis() — wraps pg_try_advisory_lock, true
--                                             iff this session took the lock.
--   pg_advisory_unlock_for_dt_synthesis()   — wraps pg_advisory_unlock,
--                                             releases the lock this session
--                                             holds.
--
-- Lock key 1146377081 = 0x44545379 = ASCII 'DTSy' (Dual Translation Synthesis).
-- Distinct from the Study-Plan key (1467840848) and the IRT key
-- (8901234567890123) so the three sweeps never contend with each other.
--
-- Why a lock at all: without it both gunicorn workers run synthesize() over the
-- same window and race on the dt_error_profile_entry upsert
-- (user_id, l1_language_id, l2_language_id, subtype). The upsert is idempotent,
-- so the race is not corrupting, but a lost update can drop a freshly-promoted
-- 'queued' status back to a stale count — which silently delays remediation.
--
-- Idempotent: CREATE OR REPLACE FUNCTION.
-- ============================================================================

BEGIN;

CREATE OR REPLACE FUNCTION public.pg_try_advisory_lock_for_dt_synthesis()
RETURNS boolean
LANGUAGE sql
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT pg_try_advisory_lock(1146377081::bigint);
$$;

CREATE OR REPLACE FUNCTION public.pg_advisory_unlock_for_dt_synthesis()
RETURNS boolean
LANGUAGE sql
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT pg_advisory_unlock(1146377081::bigint);
$$;

COMMIT;

-- ============================================================================
-- Verification (run manually after migration):
-- SELECT proname FROM pg_proc
-- WHERE proname LIKE '%dt_synthesis%' ORDER BY proname;
-- Expect: pg_advisory_unlock_for_dt_synthesis,
--         pg_try_advisory_lock_for_dt_synthesis.
--
-- SELECT public.pg_try_advisory_lock_for_dt_synthesis();  -- expect true
-- SELECT public.pg_advisory_unlock_for_dt_synthesis();    -- expect true
-- ============================================================================
