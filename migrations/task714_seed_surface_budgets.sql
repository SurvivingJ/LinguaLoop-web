-- TASK-714 — seed flashcards + dual_translation budgets into the study-plan
--   templates. Data-only; no DDL, no function bodies.
-- =============================================================================
-- WHY
--   Tier B (compute_weekly_plan) walks dim_study_plan_templates.weekly_test_counts
--   to decide which skills exist for a learner at all — a key absent from the
--   template can never appear in weekly_plan_states.target_counts, and so can
--   never reach the Tier C resolver. Landing the resolver support without this
--   seed would ship a feature no learner ever sees.
--
-- BUDGETS
--   flashcards: 7/week — one review block a day. FSRS reviews are due-driven
--     and inherently daily (ADR-021), so anything less would under-budget the
--     single largest source of previously-uncounted time. The resolver clamps
--     each day to what is actually due, so a learner with an empty deck simply
--     gets no block rather than an empty one.
--   dual_translation: scales with plan size (2 / 3 / 4 per week for the 30 /
--     45 / 60-minute templates). Graded production work is expensive per item
--     (12 min/slot) and heavy to do daily, so it is a few-times-a-week surface.
--
--   Both are the TEMPLATE value, i.e. the anchor the bandit water-fill clamps
--   to +/-50% (allocate_test_counts) — not a fixed quota.
--
--   These budgets do NOT lengthen the learner's week: compute_weekly_plan
--   clamps total_weekly_minutes to daily_minutes * 7 (TASK-714), so counting
--   flashcards and DT makes them COMPETE with test slots for the same minutes
--   rather than inflating the day. That is the point of ADR-021 — the surfaces
--   were always consuming that time, the plan just could not see it.
--
-- DT LANGUAGE COVERAGE
--   dt_* content exists for zh/en/ja (language_id 1/2/3), which is every
--   template row, so no template is skipped. (dim_languages has no 'es' row —
--   es is a UI locale, not a study-language dimension.)
--
-- jsonb || jsonb overwrites on key collision, so re-running this is a no-op
-- rather than an accumulation. Idempotent.
-- =============================================================================

BEGIN;

-- One review block a day, every template.
UPDATE public.dim_study_plan_templates
   SET weekly_test_counts = weekly_test_counts || jsonb_build_object('flashcards', 7);

-- DT scales with the daily_minutes tier of the template.
UPDATE public.dim_study_plan_templates
   SET weekly_test_counts = weekly_test_counts || jsonb_build_object(
           'dual_translation',
           CASE
               WHEN daily_minutes <= 30 THEN 2
               WHEN daily_minutes <= 45 THEN 3
               ELSE 4
           END
       );

COMMIT;

-- Verify (run manually, outside the transaction):
--   SELECT template_id, daily_minutes, weekly_test_counts
--     FROM public.dim_study_plan_templates ORDER BY template_id;
-- Expect every row to carry flashcards=7 and dual_translation in {2,3,4}.
