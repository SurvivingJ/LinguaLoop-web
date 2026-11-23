-- =============================================================================
-- knowledge_calibration_inputs_rollback.sql  (TASK-1079) — reverses
-- knowledge_calibration_inputs.sql. Roll back knowledge_report_summary (TASK-1036)
-- first if it embeds this function. REQUIRES USER APPROVAL TO APPLY LIVE.
-- =============================================================================
DROP FUNCTION IF EXISTS public.knowledge_calibration_inputs(uuid, smallint, timestamptz, integer, smallint, uuid);
