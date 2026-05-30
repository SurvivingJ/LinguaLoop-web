-- ============================================================================
-- Phase 13 — Study Plans — dim_study_plan_templates public read policy
-- Date: 2026-05-30
--
-- Bug fix: dim_study_plan_templates had ROW LEVEL SECURITY enabled but NO
-- policy, so every non-bypass role (the app's client) read 0 rows. This broke
-- compute_weekly_plan step 2, whose `.single()` lookup on the user's
-- template_id raised PGRST116 ("0 rows / cannot coerce to single object"),
-- which surfaced as a 500 from POST /api/study-plan/recompute. It also blocked
-- weekly_plan_states from ever being created, so study-time stats never moved.
--
-- dim_* tables are world-readable reference data (see routes/study_plan.py).
-- This mirrors the sibling policy dim_test_types_public_read.
-- ============================================================================

BEGIN;

DROP POLICY IF EXISTS dim_study_plan_templates_public_read
    ON public.dim_study_plan_templates;

CREATE POLICY dim_study_plan_templates_public_read
    ON public.dim_study_plan_templates
    FOR SELECT USING (true);

COMMIT;
