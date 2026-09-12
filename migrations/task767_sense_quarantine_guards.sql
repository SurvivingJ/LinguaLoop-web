-- =============================================================================
-- TASK-767 — make the sense blocklist bind every exercise consumer, not only
-- Calibration.
-- =============================================================================
--
-- The defect
-- ----------
-- calibration_anchor_blocklist holds senses whose dictionary row is known to be
-- wrong: a definition that defines a different word or a longer phrase (TASK-757
-- screen — `carbon` defined as "carbon footprint", `accessible` as "difficult to
-- obtain"), LLM refusal text stored as a definition ("The word 'bring' is not
-- used in the provided text."), and ja lemmas that are MeCab morpheme output
-- (`作る れる ます`). Only the two Calibration picker RPCs read it. Exercise
-- generation and practice serving did not, so on 2026-09-11 225 active exercises
-- across 27 blocklisted senses were still being served, each built on the bad
-- definition.
--
-- The fix: quarantine at the exercises table, not in each reader
-- --------------------------------------------------------------
-- Every serving path already filters `exercises.is_active` — get_practice_session,
-- get_exercise_session, vocab_dojo, ladder_service, speed_round, the ladder
-- supply gate. So one invariant covers them all without touching any of those
-- RPCs: *an exercise whose sense is blocklisted is never active.* Three triggers
-- hold it:
--
--   1. exercises BEFORE INSERT/UPDATE — a row written for a blocklisted sense is
--      forced inactive. Covers every generator (queue drain, batch scripts,
--      hand-authored uploads, the test-derived orchestrator) with no code change
--      in any of them. It demotes rather than raises: generators insert many
--      senses per statement, and one quarantined sense must not fail the batch.
--   2. calibration_anchor_blocklist AFTER INSERT — a newly flagged sense has its
--      existing exercises retired immediately.
--   3. generation_queue BEFORE INSERT — a quarantined sense is dropped from the
--      queue. Without this the guard becomes a spend loop: the ladder supply gate
--      sees a sense with no active exercises and queues it for generation, and
--      the nightly drain regenerates it only for trigger 1 to retire the output.
--
-- Deliberately NOT done: un-blocklisting does not reactivate. The retired
-- exercises were written from the bad definition; once the definition is fixed
-- they must be regenerated, not revived. (Ladder senses with a valid
-- prompt1_core asset regenerate automatically — their inactive exercises show as
-- gaps in v_sense_family_coverage and the nightly drain picks them up.)
--
-- The table keeps its Calibration name. Renaming it would break the two
-- Calibration RPCs and the screen script for a cosmetic gain; the name now
-- under-describes its reach, and this header plus the table comment say so.
--
-- Idempotent: CREATE OR REPLACE + DROP TRIGGER IF EXISTS.
-- =============================================================================

BEGIN;

CREATE OR REPLACE FUNCTION public.is_sense_quarantined(p_sense_id integer)
RETURNS boolean
LANGUAGE sql
STABLE
SET search_path = public
AS $$
    SELECT p_sense_id IS NOT NULL
       AND EXISTS (SELECT 1 FROM public.calibration_anchor_blocklist
                    WHERE sense_id = p_sense_id);
$$;

COMMENT ON FUNCTION public.is_sense_quarantined(integer) IS
  'TASK-767: true when the sense is on calibration_anchor_blocklist. Used by the '
  'exercises / generation_queue guard triggers.';


-- 1. exercises: a blocklisted sense can never carry an active exercise --------
CREATE OR REPLACE FUNCTION public.trg_exercises_sense_quarantine()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = public
AS $$
BEGIN
    IF NEW.is_active AND public.is_sense_quarantined(NEW.word_sense_id) THEN
        NEW.is_active := false;
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS exercises_sense_quarantine ON public.exercises;
CREATE TRIGGER exercises_sense_quarantine
    BEFORE INSERT OR UPDATE OF is_active, word_sense_id ON public.exercises
    FOR EACH ROW EXECUTE FUNCTION public.trg_exercises_sense_quarantine();


-- 2. blocklist: flagging a sense retires what is already live -----------------
CREATE OR REPLACE FUNCTION public.trg_blocklist_retire_exercises()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    UPDATE public.exercises
       SET is_active = false
     WHERE word_sense_id = NEW.sense_id
       AND is_active;
    RETURN NULL;
END;
$$;

DROP TRIGGER IF EXISTS blocklist_retire_exercises ON public.calibration_anchor_blocklist;
CREATE TRIGGER blocklist_retire_exercises
    AFTER INSERT ON public.calibration_anchor_blocklist
    FOR EACH ROW EXECUTE FUNCTION public.trg_blocklist_retire_exercises();


-- 3. generation_queue: never spend generation on a quarantined sense ----------
CREATE OR REPLACE FUNCTION public.trg_generation_queue_sense_quarantine()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = public
AS $$
BEGIN
    IF public.is_sense_quarantined(NEW.sense_id) THEN
        RETURN NULL;   -- drop the row; the caller's insert simply affects 0 rows
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS generation_queue_sense_quarantine ON public.generation_queue;
CREATE TRIGGER generation_queue_sense_quarantine
    BEFORE INSERT ON public.generation_queue
    FOR EACH ROW EXECUTE FUNCTION public.trg_generation_queue_sense_quarantine();


-- Backfill: retire what is live today, close anything already queued ---------
UPDATE public.exercises e
   SET is_active = false
 WHERE e.is_active
   AND EXISTS (SELECT 1 FROM public.calibration_anchor_blocklist b
                WHERE b.sense_id = e.word_sense_id);

UPDATE public.generation_queue g
   SET status = 'failed',
       completed_at = now(),
       detail = coalesce(g.detail, '{}'::jsonb)
                || jsonb_build_object('error', 'TASK-767: sense is quarantined')
 WHERE g.status IN ('pending', 'running')
   AND EXISTS (SELECT 1 FROM public.calibration_anchor_blocklist b
                WHERE b.sense_id = g.sense_id);

COMMENT ON TABLE public.calibration_anchor_blocklist IS
  'Senses whose dictionary row is known to be wrong (definition defines another '
  'word or phrase, refusal text as definition, malformed lemma). Named for its '
  'first consumer, but since TASK-767 it quarantines the sense everywhere: '
  'Calibration never uses it as a prompt, its exercises are forced inactive, and '
  'generation_queue drops it. Remove a row only after the dictionary row is '
  'fixed; removal does not reactivate retired exercises (they must be regenerated).';

COMMIT;

-- -----------------------------------------------------------------------------
-- Verification
-- -----------------------------------------------------------------------------
-- No active exercise on a quarantined sense:
--   SELECT count(*) FROM exercises e
--     JOIN calibration_anchor_blocklist b ON b.sense_id = e.word_sense_id
--    WHERE e.is_active;                                                   -- 0
--
-- Trigger 1 demotes (run in a rolled-back transaction):
--   BEGIN;
--   UPDATE exercises SET is_active = true
--    WHERE word_sense_id = (SELECT sense_id FROM calibration_anchor_blocklist LIMIT 1);
--   SELECT bool_or(is_active) FROM exercises
--    WHERE word_sense_id = (SELECT sense_id FROM calibration_anchor_blocklist LIMIT 1);  -- false
--   ROLLBACK;
--
-- Trigger 3 drops:
--   BEGIN;
--   INSERT INTO generation_queue (sense_id, language_id, reason)
--   SELECT sense_id, 2, 'regen' FROM calibration_anchor_blocklist LIMIT 1;  -- INSERT 0 0
--   ROLLBACK;
