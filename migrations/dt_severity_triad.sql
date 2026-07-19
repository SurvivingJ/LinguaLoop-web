-- ============================================================================
-- Dual Translation - severity triad migration (TASK-625, Evidence-First Phase 2).
-- Moves dt_error_instance.severity from the 2-level global/local vocabulary to
-- the MQM triad minor/major/critical (see wiki/algorithms/evidence-first-grading.tech.md §3).
--
-- Two-step CHECK change so the constraint never blocks the backfill:
--   1. extend the CHECK to accept the union ('minor','major','critical','global','local')
--   2. backfill  local -> minor,  global -> major
--   3. verify zero rows still carry the old values (RAISE if any survive)
--   4. tighten the CHECK to the triad ('minor','major','critical')
--
-- Backfill mapping (per tech spec §3): local (reader reads on, meaning intact)
-- -> minor; global (reader stumbles / meaning at risk) -> major. `critical`
-- (meaning lost/inverted, real offence) has no old-vocabulary equivalent, so no
-- existing row maps to it — it is a new, initially-unused severity level.
--
-- SEARCH-BEFORE-ARCHIVE (migrations/CLAUDE.md): the severity CHECK originates in
-- migrations/dual_translation_groundwork.sql (TASK-602) as an inline
-- `CHECK (severity IN ('global','local'))`, constraint name
-- dt_error_instance_severity_check. That groundwork file also defines the
-- dt_error_instance table itself plus dt_taxonomy_version / dt_rubric_version and
-- is NOT superseded by this file — it stays (do not archive a still-canonical
-- multi-object file). This migration redefines only that one constraint; the
-- groundwork inline CHECK is historical for the severity column from here on.
-- ============================================================================

BEGIN;

-- Step 1: extend the CHECK to the union of old + new values so the backfill
-- UPDATEs are never rejected mid-flight.
ALTER TABLE public.dt_error_instance DROP CONSTRAINT dt_error_instance_severity_check;
ALTER TABLE public.dt_error_instance ADD CONSTRAINT dt_error_instance_severity_check
    CHECK (severity IN ('minor', 'major', 'critical', 'global', 'local'));

-- Step 2: backfill the old vocabulary onto the triad.
UPDATE public.dt_error_instance SET severity = 'minor' WHERE severity = 'local';
UPDATE public.dt_error_instance SET severity = 'major' WHERE severity = 'global';

-- Step 3: verify no old values survive before tightening the constraint.
DO $$
DECLARE
    stale integer;
BEGIN
    SELECT count(*) INTO stale
    FROM public.dt_error_instance
    WHERE severity IN ('global', 'local');
    IF stale > 0 THEN
        RAISE EXCEPTION 'severity backfill incomplete: % rows still carry global/local', stale;
    END IF;
END $$;

-- Step 4: tighten the CHECK to the triad only.
ALTER TABLE public.dt_error_instance DROP CONSTRAINT dt_error_instance_severity_check;
ALTER TABLE public.dt_error_instance ADD CONSTRAINT dt_error_instance_severity_check
    CHECK (severity IN ('minor', 'major', 'critical'));

COMMIT;

-- ============================================================================
-- Verification (run manually after applying):
--   SELECT DISTINCT severity FROM public.dt_error_instance;   -- expect only minor/major/critical
--   SELECT pg_get_constraintdef(oid) FROM pg_constraint
--   WHERE conname = 'dt_error_instance_severity_check';       -- expect the triad CHECK
-- ============================================================================
