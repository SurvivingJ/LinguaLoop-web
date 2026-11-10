-- =============================================================================
-- New-word drill: finish one word of an intro session in one transaction
-- (ADR-040 cleanup, 2026-11-10)
--
-- services/intro_drill.complete_word computes the recount and the ladder-row
-- update in Python; this function applies them atomically:
--   1. lock the learner's ladder row; it must still be word_state 'intro' at
--      intro_stage = p_stage (else return false: a replay or a stale post),
--   2. insert the session's exercise_attempts rows (source 'intro'),
--   3. update the ladder row from p_update (only the keys present).
-- Word-knowledge evidence, the minutes ledger and generation requests stay in
-- Python after the commit (each is independent and best-effort).
-- Idempotent.
-- =============================================================================

CREATE OR REPLACE FUNCTION public.intro_commit_word(
    p_user_id uuid, p_sense_id integer, p_stage smallint,
    p_attempts jsonb, p_update jsonb
) RETURNS boolean
LANGUAGE plpgsql
SET search_path = public, pg_temp
AS $$
DECLARE
    v_row record;
BEGIN
    SELECT word_state, intro_stage INTO v_row
      FROM user_word_ladder
     WHERE user_id = p_user_id AND sense_id = p_sense_id
       FOR UPDATE;
    IF NOT FOUND OR v_row.word_state <> 'intro' OR v_row.intro_stage IS DISTINCT FROM p_stage THEN
        RETURN false;
    END IF;

    INSERT INTO exercise_attempts (
        user_id, sense_id, source, exercise_id, exercise_type, is_correct,
        is_first_attempt, time_taken_ms, user_response, created_at)
    SELECT p_user_id, p_sense_id, 'intro', a.exercise_id, a.exercise_type, a.is_correct,
           a.is_first_attempt, a.time_taken_ms, a.user_response, COALESCE(a.created_at, now())
      FROM jsonb_to_recordset(COALESCE(p_attempts, '[]'::jsonb)) AS a(
           exercise_id uuid, exercise_type text, is_correct boolean, is_first_attempt boolean,
           time_taken_ms integer, user_response jsonb, created_at timestamptz);

    UPDATE user_word_ladder SET
        intro_history  = CASE WHEN p_update ? 'intro_history' THEN p_update->'intro_history' ELSE intro_history END,
        intro_stage    = CASE WHEN p_update ? 'intro_stage' THEN (p_update->>'intro_stage')::smallint ELSE intro_stage END,
        intro_due_date = CASE WHEN p_update ? 'intro_due_date' THEN (p_update->>'intro_due_date')::date ELSE intro_due_date END,
        word_state     = CASE WHEN p_update ? 'word_state' THEN p_update->>'word_state' ELSE word_state END,
        current_ring   = CASE WHEN p_update ? 'current_ring' THEN (p_update->>'current_ring')::integer ELSE current_ring END,
        family_confidence    = CASE WHEN p_update ? 'family_confidence' THEN p_update->'family_confidence' ELSE family_confidence END,
        family_success_dates = CASE WHEN p_update ? 'family_success_dates' THEN p_update->'family_success_dates' ELSE family_success_dates END,
        review_due_at  = CASE WHEN p_update ? 'review_due_at' THEN (p_update->>'review_due_at')::timestamptz ELSE review_due_at END,
        updated_at     = now()
     WHERE user_id = p_user_id AND sense_id = p_sense_id;
    RETURN true;
END
$$;

REVOKE ALL ON FUNCTION public.intro_commit_word(uuid, integer, smallint, jsonb, jsonb) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.intro_commit_word(uuid, integer, smallint, jsonb, jsonb) TO service_role;
