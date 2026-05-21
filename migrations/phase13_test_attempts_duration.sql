-- ============================================================================
-- Phase 13 — Study Plans — test_attempts.started_at + duration_ms
-- Date: 2026-05-21
--
-- Captures per-attempt timing so:
--   1) dim_test_types.expected_minutes_p50 can be refreshed nightly from
--      observed P50 durations (replacing the seeded TEST_TYPE_MINUTES const).
--   2) Tier C daily resolver can use real per-skill timings to compute
--      today_budget vs the upper cap accurately.
--
-- FE captures both timestamps and sends them with the submit payload; the
-- server computes duration_ms = (finished_at - started_at) * 1000. Hard cap
-- 1 hour to reject obvious tab-left-open noise.
--
-- Backwards-compat: both columns nullable. Existing submit RPCs will be
-- amended (TASK-212) to accept the new params; old callers still work and
-- leave both NULL.
--
-- See wiki/features/study-plans.tech.md.
-- ============================================================================

BEGIN;

ALTER TABLE public.test_attempts
    ADD COLUMN IF NOT EXISTS started_at  timestamptz,
    ADD COLUMN IF NOT EXISTS duration_ms integer;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.check_constraints
        WHERE constraint_name = 'test_attempts_duration_ms_check'
    ) THEN
        ALTER TABLE public.test_attempts
            ADD CONSTRAINT test_attempts_duration_ms_check
            CHECK (duration_ms IS NULL OR
                   (duration_ms > 0 AND duration_ms < 3600000));
    END IF;
END $$;

COMMENT ON COLUMN public.test_attempts.started_at  IS
    'FE-supplied attempt start timestamp (ISO). Server validates against finished_at.';
COMMENT ON COLUMN public.test_attempts.duration_ms IS
    'Server-computed (finished_at − started_at)·1000. Capped at 1 hour. '
    'Drives dim_test_types.expected_minutes_p50 refresh and Tier C budgeting.';

COMMIT;
