-- Phase 13 fix — rename orphan study-plan skill key measure_word -> classifier_drill
-- (classifier_drill is the real dim_test_types.type_code, id 14). Idempotent.
BEGIN;
UPDATE public.dim_study_plan_templates
SET weekly_test_counts = (weekly_test_counts - 'measure_word')
    || jsonb_build_object('classifier_drill', weekly_test_counts->'measure_word')
WHERE weekly_test_counts ? 'measure_word';

UPDATE public.weekly_plan_states
SET target_counts = (target_counts - 'measure_word')
    || jsonb_build_object('classifier_drill', target_counts->'measure_word')
WHERE target_counts ? 'measure_word';

UPDATE public.weekly_plan_states
SET skill_values = (skill_values - 'measure_word')
    || jsonb_build_object('classifier_drill', skill_values->'measure_word')
WHERE skill_values ? 'measure_word';
COMMIT;
