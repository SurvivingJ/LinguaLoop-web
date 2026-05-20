-- Furigana overlay: deterministic kanji→kana annotations for Japanese tests.
-- ============================================================================
-- Mirrors add_pitch_accent_mode.sql. Adds the tests.furigana_payload JSONB
-- column (pre-computed ruby tokens per transcript / question / choice) and a
-- test_attempts.furigana_used flag for audit + ELO dampening.
--
-- Per-user opt-in is stored in users.exercise_preferences (existing JSONB,
-- key 'furigana_enabled'), so no new users column is required.
-- ============================================================================

ALTER TABLE tests
    ADD COLUMN IF NOT EXISTS furigana_payload JSONB;

ALTER TABLE test_attempts
    ADD COLUMN IF NOT EXISTS furigana_used BOOLEAN NOT NULL DEFAULT FALSE;
