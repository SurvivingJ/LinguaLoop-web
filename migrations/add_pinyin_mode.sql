-- Pinyin Tone Trainer: Add test type, payload column, and backfill skill ratings
-- ============================================================================

-- 1. Add pinyin test type to dim_test_types
INSERT INTO dim_test_types (type_code, type_name, requires_audio, is_active, display_order)
VALUES ('pinyin', 'Pinyin Tones', false, true, 4)
ON CONFLICT (type_code) DO NOTHING;

-- 2. Add pinyin_payload JSONB column to tests table
ALTER TABLE tests ADD COLUMN IF NOT EXISTS pinyin_payload JSONB;

-- 3. Create pinyin skill ratings for all existing Chinese tests
INSERT INTO test_skill_ratings (test_id, test_type_id, elo_rating, total_attempts)
SELECT t.id, dt.id, 1400, 0
FROM tests t
CROSS JOIN dim_test_types dt
WHERE dt.type_code = 'pinyin'
  AND t.language_id = 1
  AND NOT EXISTS (
    SELECT 1 FROM test_skill_ratings tsr
    WHERE tsr.test_id = t.id AND tsr.test_type_id = dt.id
  );
