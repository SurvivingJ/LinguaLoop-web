-- =============================================================================
-- Rollback of migrations/knowledge_report_summary.sql (TASK-1036).
-- *** LIVE-DB: the OWNER runs it. Drops the summary RPC only (no data is stored by it).
-- The /api/knowledge/summary route and the nightly snapshot job stop working until it is
-- re-applied; turn KNOWLEDGE_REPORT_ENABLED off first.
-- =============================================================================

BEGIN;

DROP FUNCTION IF EXISTS public.knowledge_report_summary(uuid, smallint, timestamptz, integer, timestamptz[]);

NOTIFY pgrst, 'reload schema';

COMMIT;
