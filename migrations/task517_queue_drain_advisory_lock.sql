-- ============================================================================
-- Generation-queue drain advisory-lock RPCs
-- Date: 2026-08-11
-- Task: TASK-517 (exercise-generation-v2)
--
-- Two helper RPCs the nightly generation-queue drain
-- (services/vocabulary_ladder/queue_drain.run_nightly_drain) calls through the
-- supabase client to serialise itself across gunicorn workers. Same pattern as
-- the nightly IRT calibrator's irt_try_lock() / irt_release_lock()
-- (migrations/add_irt_calibration_metadata.sql), the Study-Plan pacer
-- (migrations/study_plan_advisory_lock.sql) and the slug-health probe
-- (migrations/task510_model_health_advisory_lock.sql): postgrest cannot invoke
-- the built-in pg_try_advisory_lock(bigint) with a positional bigint via
-- supabase-py's rpc() helper, so we wrap it around a fixed key.
--
--   pg_try_advisory_lock_for_queue_drain() — true iff this session took it.
--   pg_advisory_unlock_for_queue_drain()   — releases the session's lock.
--
-- This lock matters more than the other three. _claim_batch() marks rows
-- `running` in a non-atomic read-then-write (supabase-py has no
-- SELECT ... FOR UPDATE SKIP LOCKED), and its docstring justifies that by
-- asserting the drain is single-writer. This lock is what makes that assertion
-- true. Without it, two workers firing at 04:15 would both claim the same
-- oldest rows and regenerate the same senses twice — paying twice for one
-- result.
--
-- Lock key 1363440238 = 0x5144726E = ASCII 'QDrn' (Queue Drain). Distinct from
-- the IRT job's key, the Study-Plan pacer's 1467840848 and model health's
-- 1298417772, so the 04:00/04:05/04:10/04:15 sweeps never contend.
-- Session-level lock: run_nightly_drain() acquires it at the top and releases
-- it in a finally, on the same connection.
--
-- New objects only — no existing object is redefined, so no older migration is
-- superseded by this file (migrations/CLAUDE.md rule 1).
-- ============================================================================

BEGIN;

CREATE OR REPLACE FUNCTION public.pg_try_advisory_lock_for_queue_drain()
RETURNS boolean
LANGUAGE sql
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT pg_try_advisory_lock(1363440238::bigint);
$$;

CREATE OR REPLACE FUNCTION public.pg_advisory_unlock_for_queue_drain()
RETURNS boolean
LANGUAGE sql
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT pg_advisory_unlock(1363440238::bigint);
$$;

COMMIT;


-- ----------------------------------------------------------------------------
-- Verification (run manually after applying)
-- ----------------------------------------------------------------------------
-- SELECT public.pg_try_advisory_lock_for_queue_drain();   -- expect true
-- SELECT public.pg_try_advisory_lock_for_queue_drain();   -- true again: a
--     -- session-level lock nests, so re-taking it in the SAME session proves
--     -- nothing. Test contention from a SECOND connection.
-- SELECT public.pg_advisory_unlock_for_queue_drain();     -- once per acquire
--
-- SELECT objid, mode, granted FROM pg_locks
--  WHERE locktype = 'advisory' AND objid = 1363440238;
