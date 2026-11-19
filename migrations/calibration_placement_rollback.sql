-- =============================================================================
-- calibration_placement_rollback.sql  (TASK-1076) — reverses calibration_placement.sql
-- =============================================================================
-- Order: apply calibration_placement_rpcs_rollback.sql (and
-- knowledge_calibration_inputs_rollback.sql) FIRST; those functions read the
-- columns dropped here.
--
-- Refuses to run while placement sessions exist, because the restored mode CHECK
-- would not hold and dropping the columns would lose their keys and results. To
-- discard them deliberately (their responses go by ON DELETE CASCADE):
--   DELETE FROM public.calibration_sessions WHERE mode = 'placement';
-- DROP COLUMN is catalog-only (no rewrite). REQUIRES USER APPROVAL TO APPLY LIVE.
-- =============================================================================

BEGIN;

DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM public.calibration_sessions WHERE mode = 'placement') THEN
    RAISE EXCEPTION 'placement sessions exist; delete them first (see the header of this file)';
  END IF;
END $$;

DROP INDEX IF EXISTS public.idx_calibration_responses_pair;
DROP INDEX IF EXISTS public.idx_calibration_responses_user_vocab_answered;

ALTER TABLE public.calibration_responses
  DROP CONSTRAINT IF EXISTS calibration_responses_pair_response_id_fkey,
  DROP CONSTRAINT IF EXISTS calibration_responses_instrument_chk,
  DROP CONSTRAINT IF EXISTS calibration_responses_probe_kind_chk,
  DROP CONSTRAINT IF EXISTS calibration_responses_item_kind_chk;

ALTER TABLE public.calibration_responses
  DROP COLUMN IF EXISTS chosen_position,
  DROP COLUMN IF EXISTS option_texts,
  DROP COLUMN IF EXISTS option_roles,
  DROP COLUMN IF EXISTS key_position,
  DROP COLUMN IF EXISTS option_sense_ids,
  DROP COLUMN IF EXISTS pair_response_id,
  DROP COLUMN IF EXISTS instrument,
  DROP COLUMN IF EXISTS probe_kind,
  DROP COLUMN IF EXISTS item_kind;

ALTER TABLE public.calibration_sessions
  DROP CONSTRAINT IF EXISTS calibration_sessions_stop_reason_chk;
ALTER TABLE public.calibration_sessions
  DROP COLUMN IF EXISTS result,
  DROP COLUMN IF EXISTS stop_reason;

ALTER TABLE public.calibration_sessions DROP CONSTRAINT IF EXISTS calibration_sessions_mode_chk;
ALTER TABLE public.calibration_sessions ADD CONSTRAINT calibration_sessions_mode_chk
  CHECK (mode IN ('definition', 'pronunciation'));

COMMIT;
