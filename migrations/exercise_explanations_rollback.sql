-- Rollback of migrations/exercise_explanations.sql (ADR-064).
-- *** LIVE-DB: the OWNER runs it. It DROPS the cache table: every stored explanation is
-- *** lost and is generated again (one model call per item and language) when next served.
-- =============================================================================

BEGIN;

DROP TABLE IF EXISTS public.exercise_explanations;

NOTIFY pgrst, 'reload schema';

COMMIT;
