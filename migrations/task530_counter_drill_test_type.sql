-- ============================================================================
-- TASK-530 — the `counter_drill` test type.
--
-- The drill's tables, RPC and ELO sentinel test ('__counter_drill_ja') were all
-- applied on 2026-08-08, but no dim_test_types row was ever added. Submission
-- resolves its type through DimensionService.get_test_type_id('counter_drill'),
-- which filters on is_active = TRUE, so without this row every submission would
-- 500 on "Counter drill test type missing" — the drill would serve items and
-- then be unable to record a single one.
--
-- Why not reuse classifier_drill (id 14)
-- --------------------------------------
-- The two drills would then share one ELO series and one line in every
-- per-type report, so a learner strong on Mandarin measure words would look
-- competent at Japanese counters. They are different skills in different
-- languages; conflating them makes both numbers meaningless.
--
-- is_active = TRUE is required by the resolver above and does NOT make the
-- drill schedulable: recommendations select from `tests`, and the sentinel row
-- is is_active = FALSE precisely so it never surfaces as a recommendable test.
-- That is the same arrangement the classifier drill already runs under.
--
-- id is left to the sequence rather than hardcoded.
-- ============================================================================

INSERT INTO public.dim_test_types
    (type_code, type_name, description, category, requires_audio, is_active, display_order)
VALUES
    ('counter_drill', 'Counters',
     'Japanese counter (助数詞) recall drill — Choose and Type modes',
     NULL, FALSE, TRUE, 7)
ON CONFLICT (type_code) DO UPDATE
SET type_name   = EXCLUDED.type_name,
    description = EXCLUDED.description,
    is_active   = EXCLUDED.is_active;


-- ============================================================================
-- Verification
-- ============================================================================
--   SELECT id, type_code, type_name, is_active
--   FROM dim_test_types WHERE type_code IN ('classifier_drill','counter_drill');
--   -- expect two distinct ids, both is_active = true.
--
-- The sentinel stays unschedulable:
--   SELECT slug, is_active FROM tests WHERE slug = '__counter_drill_ja';
--   -- expect is_active = false.
-- ============================================================================
