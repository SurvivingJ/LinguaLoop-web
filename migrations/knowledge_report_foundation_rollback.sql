-- =============================================================================
-- Rollback of migrations/knowledge_report_foundation.sql (TASK-1034).
-- *** LIVE-DB: the OWNER runs it. It DROPS the snapshot table: every stored snapshot (the
-- *** report's growth history, ADR-053) is lost and cannot be rebuilt (no back-fill, OQ7).
-- Apply the rollbacks of the dependent files first:
--   knowledge_report_summary_rollback.sql, knowledge_report_words_rollback.sql
-- (they do not reference these objects, but the feature is removed as a whole).
-- =============================================================================

BEGIN;

DROP FUNCTION IF EXISTS public.knowledge_snapshots_prune(integer);
DROP FUNCTION IF EXISTS public.knowledge_active_pairs(timestamptz);
DROP FUNCTION IF EXISTS public.knowledge_frame_bands();
DROP TABLE IF EXISTS public.user_knowledge_snapshots;

NOTIFY pgrst, 'reload schema';

COMMIT;
