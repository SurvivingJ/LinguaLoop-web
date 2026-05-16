-- ============================================================================
-- Add a partial compound index for process_test_submission's idempotency check.
-- Date: 2026-05-15
--
-- process_test_submission (phase3_rpc_fixes.sql and successors) looks up
--     SELECT * FROM test_attempts
--     WHERE user_id = p_user_id AND idempotency_key = p_idempotency_key;
-- on every submission. Without a covering index, this scans test_attempts
-- filtered by user_id alone, then evaluates the key match in memory. As a
-- user accumulates attempts this becomes slower linearly.
--
-- A partial index on the WHERE-IS-NOT-NULL subset is cheaper to maintain
-- than a full index, because most attempts have NULL idempotency_key.
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_test_attempts_user_idempotency
ON test_attempts (user_id, idempotency_key)
WHERE idempotency_key IS NOT NULL;
