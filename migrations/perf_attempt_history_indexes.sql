-- =============================================================================
-- perf_attempt_history_indexes.sql  (codebase review 2026-11, Efficiency)
-- =============================================================================
-- Purpose: composite indexes for the per-user attempt-history lookups that run
-- on every test submission and every practice answer. Today each one is served
-- by a single-column index (or by none recorded in the repo) and filters the
-- rest of the predicate row by row, so the cost grows with a learner's history.
--
-- Pre-checks:
--   1. See what already exists; skip an index here if an equivalent one is live
--      under another name (the repo does not record every live index):
--        SELECT tablename, indexname, indexdef FROM pg_indexes
--         WHERE schemaname = 'public'
--           AND tablename IN ('test_attempts', 'question_attempt_results', 'exercise_attempts')
--         ORDER BY 1, 2;
--   2. Table sizes, to decide between this file as written and CONCURRENTLY:
--        SELECT relname, n_live_tup FROM pg_stat_user_tables
--         WHERE relname IN ('test_attempts', 'question_attempt_results', 'exercise_attempts');
--
-- Locking: a plain CREATE INDEX blocks writes to the table for the duration of
-- the build. On a large table apply each statement on its own, OUTSIDE a
-- transaction, as  CREATE INDEX CONCURRENTLY IF NOT EXISTS ...  (it cannot run
-- inside BEGIN/COMMIT or the Supabase migration runner's implicit transaction).
-- If a CONCURRENTLY build fails it leaves an INVALID index: DROP it and retry.
-- This file has no BEGIN/COMMIT for that reason.
--
-- Idempotent (IF NOT EXISTS). Adds indexes only; no data or behaviour change.
-- REQUIRES USER APPROVAL TO APPLY LIVE.
--
-- Rollback:
--   DROP INDEX IF EXISTS public.idx_test_attempts_user_test_type;
--   DROP INDEX IF EXISTS public.idx_test_attempts_user_language_created;
--   DROP INDEX IF EXISTS public.idx_qar_user_incorrect;
--   DROP INDEX IF EXISTS public.idx_ea_user_exercise;
-- =============================================================================

-- process_test_submission: attempt number and first-attempt detection
--   SELECT COUNT(*) FROM test_attempts
--    WHERE user_id = $1 AND test_id = $2 AND test_type_id = $3;
-- Also its retry-slot checks (user_id, test_id) and the "latest attempt on this
-- test" lookups in services/prestudy.py and routes/tests.py::_has_attempt_today.
CREATE INDEX IF NOT EXISTS idx_test_attempts_user_test_type
    ON public.test_attempts (user_id, test_id, test_type_id);

-- Test history page (routes/tests.py::get_test_history):
--   ... WHERE user_id = $1 [AND language_id = $2] ORDER BY created_at DESC LIMIT n
-- and the recent-tests intake read in services/practice_session_service.py:
--   ... WHERE user_id = $1 AND language_id = $2 AND created_at >= $3
CREATE INDEX IF NOT EXISTS idx_test_attempts_user_language_created
    ON public.test_attempts (user_id, language_id, created_at DESC);

-- Wrong-answer sense intake (services/practice_session_service.py):
--   SELECT question_id ... FROM question_attempt_results
--    WHERE user_id = $1 AND is_correct = false LIMIT n
-- Partial: only incorrect rows are indexed, so it stays small.
CREATE INDEX IF NOT EXISTS idx_qar_user_incorrect
    ON public.question_attempt_results (user_id)
    WHERE NOT is_correct;

-- First-attempt detection on every practice answer
-- (services/practice_session_service.py):
--   SELECT id FROM exercise_attempts WHERE user_id = $1 AND exercise_id = $2 LIMIT 1
CREATE INDEX IF NOT EXISTS idx_ea_user_exercise
    ON public.exercise_attempts (user_id, exercise_id);

-- -----------------------------------------------------------------------------
-- OPTIONAL FOLLOW-UP, not executed. Once the indexes above are live and
-- pg_stat_user_indexes shows the old ones idle (idx_scan not growing over a
-- normal week), these single-column indexes are candidates to drop. Names are
-- from wiki/database/schema.tech.md; confirm them with pre-check 1.
--
--   -- leading column of both new test_attempts indexes
--   DROP INDEX IF EXISTS public.idx_test_attempts_user_id;
--   -- low-selectivity columns, only ever filtered together with user_id
--   DROP INDEX IF EXISTS public.idx_test_attempts_language_id;
--   DROP INDEX IF EXISTS public.idx_test_attempts_test_type_id;
--   -- the repo only reads user_response with ->> (a view), which a GIN index cannot serve
--   DROP INDEX IF EXISTS public.idx_ea_user_response_gin;
--
-- Keep: idx_test_attempts_test_id (per-test rollups), idx_test_attempts_created_at,
-- idx_qar_user (still serves correct-answer reads by user), idx_ea_exercise_id,
-- idx_ea_user_created, idx_test_attempts_user_idempotency.
--
--   SELECT indexrelname, idx_scan FROM pg_stat_user_indexes
--    WHERE relname IN ('test_attempts', 'question_attempt_results', 'exercise_attempts');
-- -----------------------------------------------------------------------------
