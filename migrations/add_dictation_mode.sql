-- ============================================================================
-- Dictation Mode — activate test type, add scoring columns, backfill ratings
-- ============================================================================
-- The 'dictation' row in dim_test_types (id=3) was seeded at project bootstrap
-- but kept inactive pending implementation. This migration:
--   1. Activates the dictation test type (is_active=true)
--   2. Adds nullable columns on test_attempts for dictation-specific telemetry
--   3. Backfills test_skill_ratings for every existing listening test so the
--      recommendation lane has something to surface immediately
--
-- All listening tests (test_type_id=1) already have audio_url + transcript
-- from the Azure TTS pipeline, so dictation reuses the same content pool at
-- zero generation cost. See ADR-007 logic (inline-documented) for the
-- replay K-multiplier persisted in elo_reduction_factor.
-- ============================================================================

-- 1. Activate dictation test type
UPDATE dim_test_types
SET is_active = true
WHERE type_code = 'dictation';

-- 2. Add dictation-specific telemetry columns to test_attempts
ALTER TABLE test_attempts
  ADD COLUMN IF NOT EXISTS replay_count          smallint NULL,
  ADD COLUMN IF NOT EXISTS dictation_word_correct integer  NULL,
  ADD COLUMN IF NOT EXISTS dictation_word_total   integer  NULL,
  ADD COLUMN IF NOT EXISTS dictation_diff         jsonb    NULL;

COMMENT ON COLUMN test_attempts.replay_count IS
  'Number of times the audio was played during a dictation attempt. NULL for non-dictation rows. 1 = single listen (no penalty).';
COMMENT ON COLUMN test_attempts.dictation_word_correct IS
  'Count of canonical words marked correct after fuzzy-tolerance scoring.';
COMMENT ON COLUMN test_attempts.dictation_word_total IS
  'Total canonical word tokens (punctuation-only tokens excluded).';
COMMENT ON COLUMN test_attempts.dictation_diff IS
  'Per-token opcodes for the result-screen inline diff. Capped at 200 tokens client-side.';

-- 3. Backfill test_skill_ratings for every listening-eligible test
-- Every test that already has audio (test_type_id = listening) becomes
-- dictation-eligible. Mirrors the pinyin backfill pattern.
INSERT INTO test_skill_ratings (test_id, test_type_id, elo_rating, total_attempts)
SELECT DISTINCT tsr.test_id, dt.id, 1400, 0
FROM test_skill_ratings tsr
JOIN dim_test_types listen ON listen.id = tsr.test_type_id AND listen.type_code = 'listening'
CROSS JOIN dim_test_types dt
WHERE dt.type_code = 'dictation'
  AND NOT EXISTS (
    SELECT 1 FROM test_skill_ratings existing
    WHERE existing.test_id = tsr.test_id AND existing.test_type_id = dt.id
  );
