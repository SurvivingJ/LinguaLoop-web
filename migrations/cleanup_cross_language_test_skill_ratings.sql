-- ============================================================================
-- DATA CLEANUP — delete test_skill_ratings rows for test types that don't
-- belong to the test's language
-- Date: 2026-09-11
--
-- WHY
--   get_recommended_tests / build_daily_session offer any (test, type) pair
--   that has a test_skill_ratings row, so e.g. a pitch_accent row on a zh test
--   lets zh learners be recommended and scheduled a Japanese-only exercise.
--
--   Language-specific types (mirrors Config.LANGUAGE_RESTRICTED_TEST_TYPES):
--     pinyin, classifier_drill  -> zh (language_id 1) only
--     pitch_accent, counter_drill -> ja (language_id 3) only
--
--   Rows found live on 2026-09-11 (all with zero attempts, and no
--   user_skill_ratings row exists for any of these language/type pairs):
--     en pinyin 8, en pitch_accent 38, zh pitch_accent 34,
--     en classifier_drill 38, ja classifier_drill 59,
--     en counter_drill 35, zh counter_drill 12          = 224
--
-- ROOT CAUSE (fixed in the same change)
--   services/test_generation/database_client.py::insert_test_skill_ratings
--   only filtered pinyin by language; scripts/backfill_test_skill_ratings.py
--   filtered nothing. Both now use Config.test_type_applies_to_language.
--
-- SAFETY
--   Deletes only rows no test_attempts row references, so no attempt history
--   loses its (test, type) rating. Idempotent — re-running deletes nothing.
-- ============================================================================

DELETE FROM public.test_skill_ratings tsr
USING public.tests t, public.dim_test_types tt
WHERE t.id = tsr.test_id
  AND tt.id = tsr.test_type_id
  AND (
        (tt.type_code IN ('pinyin', 'classifier_drill') AND t.language_id <> 1)
     OR (tt.type_code IN ('pitch_accent', 'counter_drill') AND t.language_id <> 3)
  )
  AND NOT EXISTS (
        SELECT 1 FROM public.test_attempts ta
        WHERE ta.test_id = tsr.test_id AND ta.test_type_id = tsr.test_type_id
  );
