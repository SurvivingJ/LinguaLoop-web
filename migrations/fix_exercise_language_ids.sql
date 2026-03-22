-- ============================================================================
-- Fix exercises with mismatched language_id
--
-- Some exercises have a language_id that doesn't match the language of their
-- source vocabulary/grammar/collocation. This causes exercises to appear
-- under the wrong language (e.g. Japanese content shown for Chinese).
--
-- Strategy:
--   1. For vocabulary exercises (word_sense_id set): derive correct language_id
--      from dim_word_senses.vocab_id → dim_vocabulary.language_id
--   2. For grammar exercises (grammar_pattern_id set): derive from
--      dim_grammar_patterns → language_id
--   3. Deactivate any exercises where the content language can't be determined
--      or doesn't match any known language
-- ============================================================================

-- Step 1: Preview mismatched vocabulary exercises (run SELECT first to verify)
-- SELECT
--     e.id,
--     e.exercise_type,
--     e.language_id AS current_lang,
--     dv.language_id AS correct_lang,
--     substring(e.content::text, 1, 100) AS content_preview
-- FROM exercises e
-- JOIN dim_word_senses dws ON dws.id = e.word_sense_id
-- JOIN dim_vocabulary dv ON dv.id = dws.vocab_id
-- WHERE e.word_sense_id IS NOT NULL
--   AND e.language_id != dv.language_id;

-- Step 2: Fix vocabulary exercises — set language_id from their word sense's vocabulary
UPDATE exercises e
SET language_id = dv.language_id
FROM dim_word_senses dws
JOIN dim_vocabulary dv ON dv.id = dws.vocab_id
WHERE e.word_sense_id = dws.id
  AND e.language_id != dv.language_id;

-- Step 3: Fix grammar exercises — set language_id from their grammar pattern
UPDATE exercises e
SET language_id = gp.language_id
FROM dim_grammar_patterns gp
WHERE e.grammar_pattern_id = gp.id
  AND e.language_id != gp.language_id;

-- Step 4: Deactivate orphaned exercises whose source record no longer exists
-- (vocabulary exercises with dangling word_sense_id)
UPDATE exercises e
SET is_active = false
WHERE e.word_sense_id IS NOT NULL
  AND NOT EXISTS (
      SELECT 1 FROM dim_word_senses dws WHERE dws.id = e.word_sense_id
  );

-- (grammar exercises with dangling grammar_pattern_id)
UPDATE exercises e
SET is_active = false
WHERE e.grammar_pattern_id IS NOT NULL
  AND NOT EXISTS (
      SELECT 1 FROM dim_grammar_patterns gp WHERE gp.id = e.grammar_pattern_id
  );
