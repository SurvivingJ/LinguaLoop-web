-- ============================================================================
-- Dual Translation - taxonomy v6 ACTIVATION (TASK-853, ADR-031)
-- Date: 2026-11-14
--
-- APPLIED TO PRODUCTION on 2026-11-14 by the orchestrator, at the owner's explicit
-- instruction ("get rid of history and activate v6 in database now"), in one
-- transaction. Kept here as the repo record of what ran.
--
-- DEVIATION FROM THE TASK-853 RUNBOOK: DT learner history was DELETED, not
-- rewritten (5 dt_submission, 2 dt_grade, 16 dt_error_instance, 4
-- dt_error_profile_entry, 4 dt_card, 5 dt_card_review; one user, the developer's
-- test data). The five dt_v5_snapshot_* tables were therefore never created, the
-- TASK-852 rewrite (dt_rewrite_history_v6.*) was not run and is no longer
-- needed, and `dt_rewrite_history_v6.py --restore` DOES NOT APPLY: there is no
-- snapshot to restore. Rollback is dt_taxonomy_v6_rollback.sql (grading
-- version only) and nothing more.
--
-- Prerequisites (applied earlier the same day, in this order):
--   migrations/dt_taxonomy_v6_columns.sql (column part only; no snapshot tables)
--   migrations/dt_taxonomy_v6_seed.sql    (version 6 inserted INACTIVE)
--
-- What this does: deactivate every active row other than 6, activate 6. v5 stays
-- in the table, inactive. Idempotent (re-running changes nothing once v6 is the
-- single active row). Aborts, rolling back, if version 6 has not been seeded.
--
-- AFTER APPLYING: restart ALL web workers (every gunicorn/worker process, or call
-- grader_cascade.clear_caches() in each). The unpinned `taxonomy` /
-- `taxonomy_version` entries in the process-wide _cfg_cache have no TTL, so a
-- worker that is not restarted keeps grading AND stamping v5 indefinitely.
-- Then verify with one test grade that grader_trace.prompt_version.taxonomy = 6
-- and its errors carry taxonomy_version = 6.
-- ============================================================================

BEGIN;

DO $guard$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM public.dt_taxonomy_version WHERE version = 6) THEN
        RAISE EXCEPTION 'dt_taxonomy_version 6 is not seeded; apply dt_taxonomy_v6_seed.sql first';
    END IF;
END
$guard$;

-- Deactivate first: idx_dt_taxonomy_version_one_active (single active row) would
-- reject activating 6 while another row is still active.
UPDATE public.dt_taxonomy_version SET is_active = false WHERE is_active AND version <> 6;
UPDATE public.dt_taxonomy_version SET is_active = true  WHERE version = 6 AND NOT is_active;

-- Footer verification inside the transaction: exactly one active row and it is 6.
DO $verify$
DECLARE
    n_active integer;
    active_version integer;
BEGIN
    SELECT count(*), max(version) INTO n_active, active_version
    FROM public.dt_taxonomy_version WHERE is_active;
    IF n_active <> 1 OR active_version <> 6 THEN
        RAISE EXCEPTION 'activation check failed: % active row(s), active version %', n_active, active_version;
    END IF;
END
$verify$;

COMMIT;

-- ============================================================================
-- Verification (run manually after applying):
--   SELECT count(*) FROM public.dt_taxonomy_version WHERE is_active;   -- expect 1
--   SELECT version FROM public.dt_taxonomy_version WHERE is_active;    -- expect 6
--   SELECT version, is_active FROM public.dt_taxonomy_version ORDER BY version;
--       -- expect v5 present and inactive
-- ============================================================================
