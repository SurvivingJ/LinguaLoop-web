-- ============================================================================
-- Phase 13 — Study Plans — apply_study_plan_template RPC
-- Date: 2026-05-21
--
-- Onboarding / settings helper. Idempotent UPSERT on
-- (user_id, language_id) — first call inserts; subsequent calls update the
-- template_id and re-copy daily_minutes from the template.
--
-- weekday_shape, skill_weight_overrides, goal_id, timezone are NOT touched
-- on update — those are user-edited fields that the template should not
-- overwrite.
--
-- See wiki/features/study-plans.tech.md.
-- ============================================================================

BEGIN;

CREATE OR REPLACE FUNCTION public.apply_study_plan_template(
    p_user_id     uuid,
    p_language_id smallint,
    p_template_id smallint
) RETURNS public.user_study_plans
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
DECLARE
    v_template public.dim_study_plan_templates%ROWTYPE;
    v_row      public.user_study_plans%ROWTYPE;
BEGIN
    SELECT * INTO v_template
    FROM public.dim_study_plan_templates
    WHERE template_id = p_template_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'unknown template_id=%', p_template_id
            USING ERRCODE = 'foreign_key_violation';
    END IF;

    IF v_template.language_id <> p_language_id THEN
        RAISE EXCEPTION
            'template_id=% belongs to language_id=%, not requested %',
            p_template_id, v_template.language_id, p_language_id
            USING ERRCODE = 'check_violation';
    END IF;

    INSERT INTO public.user_study_plans (
        user_id, language_id, template_id, daily_minutes
    ) VALUES (
        p_user_id, p_language_id, p_template_id, v_template.daily_minutes
    )
    ON CONFLICT (user_id, language_id) DO UPDATE
        SET template_id   = EXCLUDED.template_id,
            daily_minutes = EXCLUDED.daily_minutes,
            updated_at    = NOW()
    RETURNING * INTO v_row;

    RETURN v_row;
END $$;

COMMENT ON FUNCTION public.apply_study_plan_template IS
    'Idempotent UPSERT helper. Sets template_id and copies daily_minutes; '
    'preserves user-edited weekday_shape, skill_weight_overrides, goal_id, '
    'timezone on existing rows.';

COMMIT;
