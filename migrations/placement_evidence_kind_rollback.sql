-- Rollback of placement_evidence_kind.sql (TASK-1081). Drops the batch function and the two counters.
-- The counters' values are lost; BKT p_known updates already applied by placements are kept.
DROP FUNCTION IF EXISTS public.update_vocabulary_from_placement_batch(uuid, smallint, jsonb);
ALTER TABLE public.user_vocabulary_knowledge
  DROP COLUMN IF EXISTS placement_correct,
  DROP COLUMN IF EXISTS placement_wrong;
