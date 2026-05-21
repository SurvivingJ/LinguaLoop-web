-- ============================================================================
-- Phase 13 — Study Plans — dim_study_goals (V2 placeholder)
-- Date: 2026-05-21
--
-- Empty table created now so user_study_plans.goal_id has an FK target. V1
-- adapter ignores goals; V2 will add a goal_pressure(s) term to the weakness
-- signal that biases test allocation toward goal-aligned skills as a
-- target_date approaches.
--
-- See wiki/decisions/ADR-008-study-plan-orchestration-layer.md
-- and wiki/features/study-plans.tech.md section "Goal feature".
-- ============================================================================

BEGIN;

CREATE TABLE IF NOT EXISTS public.dim_study_goals (
    goal_id       smallint PRIMARY KEY,
    goal_type     text     NOT NULL,
    target_value  text,
    target_date   date,
    language_id   smallint REFERENCES public.dim_languages(id),
    CONSTRAINT dim_study_goals_type_known CHECK (
        goal_type IN ('hsk_level','jlpt','cefr','date_target','custom')
    )
);

COMMENT ON TABLE public.dim_study_goals IS
    'V2 placeholder. user_study_plans.goal_id references this table but V1 '
    'adapter ignores it. V2 will introduce goal_pressure(s) in the weakness '
    'signal.';

COMMIT;
