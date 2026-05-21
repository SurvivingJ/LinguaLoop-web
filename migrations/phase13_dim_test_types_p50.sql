-- ============================================================================
-- Phase 13 — Study Plans — dim_test_types.expected_minutes_p50
-- Date: 2026-05-21
--
-- Nightly job (exercise_time_estimate_refresh, runs at 04:05 UTC) populates
-- this from observed test_attempts.duration_ms P50 once ≥ 30 samples exist
-- per type. Service layer (test_time_estimate helper) reads _p50 when not
-- NULL, else falls back to Config.TEST_TYPE_MINUTES constants.
--
-- See wiki/features/study-plans.tech.md.
-- ============================================================================

BEGIN;

ALTER TABLE public.dim_test_types
    ADD COLUMN IF NOT EXISTS expected_minutes_p50 numeric(4,1);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.check_constraints
        WHERE constraint_name = 'dim_test_types_expected_minutes_p50_check'
    ) THEN
        ALTER TABLE public.dim_test_types
            ADD CONSTRAINT dim_test_types_expected_minutes_p50_check
            CHECK (expected_minutes_p50 IS NULL OR
                   (expected_minutes_p50 > 0 AND expected_minutes_p50 < 120));
    END IF;
END $$;

COMMENT ON COLUMN public.dim_test_types.expected_minutes_p50 IS
    'Observed P50 of test_attempts.duration_ms / 60000, refreshed nightly. '
    'NULL until ≥ 30 samples accrue for the type.';

COMMIT;
