-- =============================================================================
-- Rollback of migrations/knowledge_report_words.sql (TASK-1044).
-- *** LIVE-DB: the OWNER runs it. Drops the words RPC only (no data is stored by it).
-- The Pro word table, Missed recently tab and the words export stop working until it is
-- re-applied; turn KNOWLEDGE_REPORT_ENABLED off first.
-- =============================================================================

BEGIN;

DROP FUNCTION IF EXISTS public.knowledge_report_words(uuid, smallint, smallint, jsonb, text, jsonb, integer, timestamptz);

NOTIFY pgrst, 'reload schema';

COMMIT;
