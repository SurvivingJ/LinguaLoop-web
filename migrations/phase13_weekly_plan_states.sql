-- ============================================================================
-- Phase 13 — Study Plans — weekly_plan_states
-- Date: 2026-05-21
--
-- One row per (user, language, week_start_date). Tier B (Sunday 23:00 UTC
-- cron) UPSERTs target_counts + practice_target_minutes + shares; per-attempt
-- record_session_progress increments the completed_* counters and appends to
-- session_progress_log for idempotency.
--
-- Idempotency:
--   UPSERT on the 3-col PK. Mid-week re-runs change target_counts but
--   preserve completed_counts, practice_completed_*_min, and
--   session_progress_log via the conditional UPDATE in compute_weekly_plan.
--
-- Retention:
--   Keep forever (audit trail, per R4.11). Index on week_start_date for the
--   carry-over lookup (compute_weekly_plan reads prior week).
--
-- See wiki/features/study-plans.tech.md section "Schema".
-- ============================================================================

BEGIN;

CREATE TABLE IF NOT EXISTS public.weekly_plan_states (
    user_id                       uuid     NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    language_id                   smallint NOT NULL REFERENCES public.dim_languages(id),
    week_start_date               date     NOT NULL,
    target_counts                 jsonb    NOT NULL,
    skill_values                  jsonb    NOT NULL DEFAULT '{}'::jsonb,
    completed_counts              jsonb    NOT NULL DEFAULT '{}'::jsonb,
    practice_target_minutes       smallint NOT NULL,
    practice_completed_maint_min  smallint NOT NULL DEFAULT 0,
    practice_completed_acq_min    smallint NOT NULL DEFAULT 0,
    maintenance_share             numeric(3,2) NOT NULL,
    acquisition_share             numeric(3,2) NOT NULL,
    total_weekly_minutes          smallint NOT NULL,
    session_progress_log          jsonb    NOT NULL DEFAULT '{}'::jsonb,
    computed_at                   timestamptz NOT NULL DEFAULT NOW(),
    PRIMARY KEY (user_id, language_id, week_start_date),
    CONSTRAINT weekly_plan_states_practice_target_positive
        CHECK (practice_target_minutes >= 0),
    CONSTRAINT weekly_plan_states_completed_non_negative
        CHECK (practice_completed_maint_min >= 0
               AND practice_completed_acq_min >= 0),
    CONSTRAINT weekly_plan_states_shares_sum
        CHECK (maintenance_share >= 0.10 AND maintenance_share <= 0.55
               AND acquisition_share >= 0.45 AND acquisition_share <= 0.90),
    CONSTRAINT weekly_plan_states_target_counts_object
        CHECK (jsonb_typeof(target_counts) = 'object'),
    CONSTRAINT weekly_plan_states_skill_values_object
        CHECK (jsonb_typeof(skill_values) = 'object'),
    CONSTRAINT weekly_plan_states_completed_counts_object
        CHECK (jsonb_typeof(completed_counts) = 'object'),
    CONSTRAINT weekly_plan_states_log_object
        CHECK (jsonb_typeof(session_progress_log) = 'object'),
    CONSTRAINT weekly_plan_states_week_start_is_monday
        CHECK (EXTRACT(DOW FROM week_start_date) = 1)
);

CREATE INDEX IF NOT EXISTS idx_weekly_plan_states_week
    ON public.weekly_plan_states (week_start_date);

CREATE INDEX IF NOT EXISTS idx_weekly_plan_states_user_lang
    ON public.weekly_plan_states (user_id, language_id, week_start_date DESC);

COMMENT ON TABLE public.weekly_plan_states IS
    'Tier B output: weekly target_counts, practice_target_minutes, '
    'maintenance/acquisition shares. completed_* and session_progress_log '
    'are updated per-attempt via record_session_progress and preserved '
    'across mid-week recomputes.';

-- ---------------------------------------------------------------------------
-- RLS: users see only their own rows; service role bypasses.
-- ---------------------------------------------------------------------------
ALTER TABLE public.weekly_plan_states ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS weekly_plan_states_self_select ON public.weekly_plan_states;
CREATE POLICY weekly_plan_states_self_select ON public.weekly_plan_states
    FOR SELECT USING (user_id = auth.uid());

-- INSERT / UPDATE / DELETE are restricted to the service role (cron + RPCs
-- running with SECURITY DEFINER). No user-facing direct writes.

COMMIT;
