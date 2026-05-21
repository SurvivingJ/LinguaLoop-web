-- ============================================================================
-- Phase 13 — Study Plans — daily_test_loads.daily_session_targets
-- Date: 2026-05-21
--
-- Adds a jsonb column on the existing daily-load row that carries today's
-- Practice minute targets (Maintenance vs Acquisition) along with resolver
-- metadata. This keeps the "today's plan" state in one place — the row
-- already carries the day's test_ids; this column adds the practice side.
--
-- Shape:
--   {
--     "practice_maintenance_min": int,
--     "practice_acquisition_min": int,
--     "resolver_solved_at":       timestamptz,
--     "objective_value":          numeric
--   }
--
-- Read by get_practice_session to constrain session size when the Study
-- Plan is active. NULL means the row predates the orchestrator or the
-- orchestrator was disabled at resolve time.
--
-- See wiki/features/study-plans.tech.md and ADR-008.
-- ============================================================================

BEGIN;

ALTER TABLE public.daily_test_loads
    ADD COLUMN IF NOT EXISTS daily_session_targets jsonb;

COMMENT ON COLUMN public.daily_test_loads.daily_session_targets IS
    'Tier C resolver output: practice_maintenance_min, practice_acquisition_min, '
    'resolver_solved_at, objective_value. NULL on pre-orchestrator rows.';

COMMIT;
