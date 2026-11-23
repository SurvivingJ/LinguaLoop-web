-- ============================================================================
-- word_upload_sweep_advisory_lock_hardened_rollback.sql — rollback of
-- migrations/word_upload_sweep_advisory_lock_hardened.sql
--
-- Drops the two sweep advisory-lock functions and the watermark table (its one
-- row is the only data: the watermark). Afterwards the nightly
-- word_upload_watchlist_sweep_nightly job errors on every run again, as it did
-- before the forward file (web/scheduler.py logs and continues). Watchlist
-- matches already written to user_word_watchlist are kept.
-- Learner-visible: no new nightly matches after the rollback.
--
-- VERIFY AFTER (read-only; expect all three NULL):
--   SELECT to_regclass('public.word_upload_sweep_state') AS tbl,
--          to_regprocedure('public.pg_try_advisory_lock_for_word_upload_sweep()') AS try_fn,
--          to_regprocedure('public.pg_advisory_unlock_for_word_upload_sweep()') AS unlock_fn;
--
-- Idempotent: IF EXISTS; safe to re-run.
-- ============================================================================

BEGIN;

DROP FUNCTION IF EXISTS public.pg_try_advisory_lock_for_word_upload_sweep();
DROP FUNCTION IF EXISTS public.pg_advisory_unlock_for_word_upload_sweep();
DROP TABLE IF EXISTS public.word_upload_sweep_state;

COMMIT;
