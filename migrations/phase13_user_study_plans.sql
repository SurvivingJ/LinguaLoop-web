-- ============================================================================
-- Phase 13 — Study Plans — user_study_plans
-- Date: 2026-05-21
--
-- One row per (user_id, language_id). Each row carries:
--   - template_id              — bucket the plan was built from
--   - daily_minutes            — user-editable; copied from template at
--                                 creation
--   - weekday_shape jsonb      — 7 floats summing to 7 (uniform default);
--                                 [Mon, Tue, ..., Sun]
--   - skill_weight_overrides   — per-skill multiplier applied to value(s)
--                                 in Tier B; default {} (== all 1.0)
--   - goal_id                  — V2 placeholder, nullable, ignored by V1
--   - timezone                 — display only V1; V2 will use this for
--                                 per-user cron windowing
--
-- Per-language independent (ADR-011); the PK is (user_id, language_id).
--
-- See wiki/features/study-plans.tech.md section "User plan model".
-- ============================================================================

BEGIN;

CREATE TABLE IF NOT EXISTS public.user_study_plans (
    user_id                  uuid     NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    language_id              smallint NOT NULL REFERENCES public.dim_languages(id),
    template_id              smallint NOT NULL REFERENCES public.dim_study_plan_templates(template_id),
    daily_minutes            smallint NOT NULL,
    weekday_shape            jsonb    NOT NULL DEFAULT '[1,1,1,1,1,1,1]'::jsonb,
    skill_weight_overrides   jsonb    NOT NULL DEFAULT '{}'::jsonb,
    goal_id                  smallint REFERENCES public.dim_study_goals(goal_id),
    timezone                 text     NOT NULL DEFAULT 'UTC',
    created_at               timestamptz NOT NULL DEFAULT NOW(),
    updated_at               timestamptz NOT NULL DEFAULT NOW(),
    PRIMARY KEY (user_id, language_id),
    CONSTRAINT user_study_plans_daily_minutes_range
        CHECK (daily_minutes BETWEEN 10 AND 180),
    CONSTRAINT user_study_plans_weekday_shape_shape
        CHECK (jsonb_typeof(weekday_shape) = 'array'
               AND jsonb_array_length(weekday_shape) = 7),
    CONSTRAINT user_study_plans_overrides_object
        CHECK (jsonb_typeof(skill_weight_overrides) = 'object')
);

COMMENT ON TABLE public.user_study_plans IS
    'Per-(user, language) Study Plan. One row per active language. Per-language '
    'independent per ADR-011.';

-- ---------------------------------------------------------------------------
-- Trigger: keep updated_at fresh on every UPDATE.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.touch_user_study_plans_updated_at()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at := NOW();
    RETURN NEW;
END $$;

DROP TRIGGER IF EXISTS trg_user_study_plans_updated_at ON public.user_study_plans;
CREATE TRIGGER trg_user_study_plans_updated_at
    BEFORE UPDATE ON public.user_study_plans
    FOR EACH ROW EXECUTE FUNCTION public.touch_user_study_plans_updated_at();

-- ---------------------------------------------------------------------------
-- RLS: users see only their own plans.
-- ---------------------------------------------------------------------------
ALTER TABLE public.user_study_plans ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS user_study_plans_self_select ON public.user_study_plans;
CREATE POLICY user_study_plans_self_select ON public.user_study_plans
    FOR SELECT USING (user_id = auth.uid());

DROP POLICY IF EXISTS user_study_plans_self_modify ON public.user_study_plans;
CREATE POLICY user_study_plans_self_modify ON public.user_study_plans
    FOR ALL USING (user_id = auth.uid()) WITH CHECK (user_id = auth.uid());

COMMIT;
