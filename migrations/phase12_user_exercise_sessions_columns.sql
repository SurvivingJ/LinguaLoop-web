-- ============================================================================
-- Phase 12 — Practice Engine merger — user_exercise_sessions mode + target
-- Date: 2026-05-21
--
-- user_exercise_sessions is repurposed as the merged Practice session cache.
-- New columns:
--   mode            text — which mode this session was served (acquisition,
--                          maintenance, or auto — recorded at resolution time)
--   target_minutes  smallint — the time budget requested for the session
--
-- Existing rows pre-date the merger and keep NULL for both columns; the new
-- service writes both going forward. No backfill needed.
--
-- See wiki/features/practice-engine.tech.md and ADR-007.
-- ============================================================================

BEGIN;

ALTER TABLE public.user_exercise_sessions
    ADD COLUMN IF NOT EXISTS mode           text,
    ADD COLUMN IF NOT EXISTS target_minutes smallint;

-- Add CHECK separately so the ALTER stays idempotent on retry.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.check_constraints
        WHERE constraint_name = 'user_exercise_sessions_mode_check'
    ) THEN
        ALTER TABLE public.user_exercise_sessions
            ADD CONSTRAINT user_exercise_sessions_mode_check
            CHECK (mode IS NULL OR mode IN ('acquisition','maintenance','auto'));
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.check_constraints
        WHERE constraint_name = 'user_exercise_sessions_target_minutes_check'
    ) THEN
        ALTER TABLE public.user_exercise_sessions
            ADD CONSTRAINT user_exercise_sessions_target_minutes_check
            CHECK (target_minutes IS NULL OR
                   (target_minutes > 0 AND target_minutes <= 180));
    END IF;
END $$;

COMMENT ON COLUMN public.user_exercise_sessions.mode IS
    'Practice mode resolved for this session row. NULL on pre-merger rows.';
COMMENT ON COLUMN public.user_exercise_sessions.target_minutes IS
    'Time budget (minutes) requested for the session. Drives item-count fill.';

COMMIT;
