-- Pitch Accent Trainer: Add Japanese-only test type, payload column,
-- and backfill skill ratings.
-- ============================================================================
-- Mirrors migrations/add_pinyin_mode.sql. Adds the dim_test_types row, the
-- tests.pitch_payload JSONB column for pre-computed accent tokens, and
-- seeds a test_skill_ratings row for every existing Japanese test
-- (language_id=3) at the default 1400 ELO.
-- ============================================================================

-- 1. Add pitch_accent test type to dim_test_types
INSERT INTO dim_test_types (type_code, type_name, requires_audio, is_active, display_order)
VALUES ('pitch_accent', 'Pitch Accent', false, true, 5)
ON CONFLICT (type_code) DO NOTHING;

-- 2. Add pitch_payload JSONB column to tests table
ALTER TABLE tests ADD COLUMN IF NOT EXISTS pitch_payload JSONB;

-- 3. Create pitch_accent skill ratings for all existing Japanese tests
INSERT INTO test_skill_ratings (test_id, test_type_id, elo_rating, total_attempts)
SELECT t.id, dt.id, 1400, 0
FROM tests t
CROSS JOIN dim_test_types dt
WHERE dt.type_code = 'pitch_accent'
  AND t.language_id = 3
  AND NOT EXISTS (
    SELECT 1 FROM test_skill_ratings tsr
    WHERE tsr.test_id = t.id AND tsr.test_type_id = dt.id
  );
