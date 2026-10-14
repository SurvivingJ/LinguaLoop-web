-- calibration_bkt_evidence.sql — calibration feeds BKT evidence (cold start 4B)
-- =============================================================================
-- TASK-873 (session-budget-settings), Migration 6. Spec:
--   wiki/features/session-budget-settings.tech.md (Migration 6, 'Cold start').
--
-- That is the whole schema change for cold start 4B: user_vocabulary_knowledge gets NO new
-- column. Provenance of calibration evidence is read from the calibration ledger
-- (calibration_responses joined to calibration_sessions) and this marker.
--
-- Idempotent.
-- =============================================================================

ALTER TABLE public.calibration_sessions
    ADD COLUMN IF NOT EXISTS bkt_applied_at timestamptz NULL;

COMMENT ON COLUMN public.calibration_sessions.bkt_applied_at IS
  'Set once, when /end fed this session''s answered anchors to update_vocabulary_from_word_tests_batch. NULL = never applied (pronunciation sessions stay NULL). Idempotency guard and the marker that tells the ladder intake which user_vocabulary_knowledge evidence came from calibration.';
