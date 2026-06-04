-- ============================================================================
-- Phase 13 — Study Plans — daily_test_loads.completed_blocks
-- Date: 2026-06-03
--
-- The single-page daily-session runner serves test slots AND practice blocks.
-- Test-slot completion is already tracked in daily_test_loads.completed_test_ids.
-- Practice blocks (acquisition / maintenance) have no per-block completion flag,
-- so the runner could not tell, on resume, whether today's practice block was
-- already done.
--
-- This column records the non-test blocks the user has finished today, e.g.
--   ["practice_acq", "practice_maint"]
-- so the session resumes past completed practice blocks. Real weekly practice
-- minutes still accrue separately via /api/practice/attempt ->
-- record_session_progress; this is purely a per-day session-position marker.
--
-- Idempotent: ADD COLUMN IF NOT EXISTS.
-- ============================================================================

BEGIN;

ALTER TABLE public.daily_test_loads
    ADD COLUMN IF NOT EXISTS completed_blocks jsonb NOT NULL DEFAULT '[]'::jsonb;

COMMENT ON COLUMN public.daily_test_loads.completed_blocks IS
    'Phase 13 daily-session runner: array of non-test block ids completed today '
    '(e.g. ["practice_acq","practice_maint"]). Lets the single-page session '
    'resume past finished practice blocks. Test-slot completion stays in '
    'completed_test_ids; real practice minutes accrue via record_session_progress.';

COMMIT;
