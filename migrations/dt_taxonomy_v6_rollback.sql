-- ============================================================================
-- Dual Translation - taxonomy v6 ROLLBACK (TASK-853, ADR-031)
-- Date: 2026-11-14
--
-- Mirror of dt_taxonomy_v6_activate.sql: reactivates taxonomy v5 and deactivates
-- every other row. NOT APPLIED; written for the record.
--
-- CONTEXT: dt_taxonomy_v6_activate.sql was APPLIED TO PRODUCTION on 2026-11-14.
-- DT learner history was DELETED rather than rewritten (no dt_v5_snapshot_*
-- tables exist), so `dt_rewrite_history_v6.py --restore` DOES NOT APPLY and
-- there is nothing to restore. This file changes only which taxonomy grades
-- new submissions. Rows graded under v6 since the cutover keep their v6 subtype
-- names and taxonomy_version = 6; they are not rewritten back. Policy once DT
-- traffic has resumed is fix-forward; use this only as an emergency stop.
--
-- AFTER APPLYING: restart ALL web workers (or call grader_cascade.clear_caches()
-- in each) - the taxonomy is cached per process with no TTL. Note that the
-- single-call grader (ADR-044) requires taxonomy v6; under v5 it is skipped and
-- the configured v2 flow grades (grader_trace.single_call.reason says why).
-- ============================================================================

BEGIN;

DO $guard$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM public.dt_taxonomy_version WHERE version = 5) THEN
        RAISE EXCEPTION 'dt_taxonomy_version 5 is missing; nothing to roll back to';
    END IF;
END
$guard$;

UPDATE public.dt_taxonomy_version SET is_active = false WHERE is_active AND version <> 5;
UPDATE public.dt_taxonomy_version SET is_active = true  WHERE version = 5 AND NOT is_active;

DO $verify$
DECLARE
    n_active integer;
    active_version integer;
BEGIN
    SELECT count(*), max(version) INTO n_active, active_version
    FROM public.dt_taxonomy_version WHERE is_active;
    IF n_active <> 1 OR active_version <> 5 THEN
        RAISE EXCEPTION 'rollback check failed: % active row(s), active version %', n_active, active_version;
    END IF;
END
$verify$;

COMMIT;

-- ============================================================================
-- Verification (run manually after applying):
--   SELECT count(*) FROM public.dt_taxonomy_version WHERE is_active;   -- expect 1
--   SELECT version FROM public.dt_taxonomy_version WHERE is_active;    -- expect 5
-- ============================================================================
