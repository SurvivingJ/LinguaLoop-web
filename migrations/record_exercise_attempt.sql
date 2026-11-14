-- =============================================================================
-- record_exercise_attempt: the Practice attempt write path in one transaction
--
-- PracticeSessionService.record_attempt_with_updates makes 11-13 PostgREST
-- round trips per answer. This function does the same writes in one call:
--
--   1. first-attempt check (serialised per user + exercise by an advisory lock)
--   2. exercise_attempts insert, with is_first_attempt set
--   3. exercises.attempt_count / correct_count, incremented atomically
--   4. prestudy follow-up completion                                  (best effort)
--   5. BKT (update_vocabulary_from_word_test), frequency inference and the
--      p_known before/after capture, on first attempts only           (best effort)
--   6. ladder_apply_progress                                          (best effort)
--   7. credit_study_time                                              (best effort)
--   8. record_session_progress, when p_plan_kind is given             (best effort)
--
-- "Best effort" matches the Python path: the step runs in its own sub-block, a
-- failure is rolled back to that step's savepoint and reported in "warnings",
-- and the attempt is still recorded. Steps 1-3 fail the whole call.
--
-- NOT done here (stays in Python, services/practice/attempt_recording.py):
--   * FSRS scheduling. services/vocabulary/fsrs.py is the scheduler in use and
--     public.fsrs_schedule_review is not an exact port of it. The learner's
--     user_flashcards row is returned ("flashcard") so Python can rate the card
--     without reading it again; Python also applies bkt_apply_lapse_penalty.
--   * The new-word-drill restart after a ring-2 demotion (intro_drill.py).
--
-- Python calls this only when PRACTICE_ATTEMPT_RPC_ENABLED is set (default off).
-- Additive and idempotent: no existing object is changed.
-- =============================================================================

CREATE OR REPLACE FUNCTION public.record_exercise_attempt(
    p_user_id          uuid,
    p_exercise_id      uuid,
    p_is_correct       boolean,
    p_user_response    jsonb    DEFAULT '{}'::jsonb,
    p_time_taken_ms    integer  DEFAULT NULL,
    p_language_id      smallint DEFAULT NULL,   -- override; else exercises.language_id
    p_credit_seconds   integer  DEFAULT 0,      -- effective seconds for the ledger and the plan
    p_plan_kind        text     DEFAULT NULL,   -- 'practice_acq' | 'practice_maint' | NULL
    p_is_tail          boolean  DEFAULT false,
    p_exercise_context text     DEFAULT 'standard'
)
RETURNS jsonb
LANGUAGE plpgsql
SET search_path = public, pg_temp
AS $function$
DECLARE
    v_type       text;
    v_sense      integer;
    v_lang       smallint;
    v_first      boolean;
    v_attempt_id uuid;
    v_bkt        record;
    v_bkt_json   jsonb;
    v_before     numeric;
    v_after      numeric;
    v_ladder     jsonb;
    v_card       jsonb;
    v_secs       integer := GREATEST(0, COALESCE(p_credit_seconds, 0));
    v_warnings   jsonb := '[]'::jsonb;
BEGIN
    SELECT e.exercise_type, e.word_sense_id, e.language_id
      INTO v_type, v_sense, v_lang
      FROM public.exercises e
     WHERE e.id = p_exercise_id;
    IF NOT FOUND THEN
        RETURN jsonb_build_object('error', 'exercise_not_found');
    END IF;
    v_lang := COALESCE(NULLIF(p_language_id, 0), v_lang);

    -- Two submissions of the same exercise by the same learner must not both
    -- count as the first attempt.
    PERFORM pg_advisory_xact_lock(
        hashtextextended(p_user_id::text || ':' || p_exercise_id::text, 0));

    v_first := NOT EXISTS (
        SELECT 1 FROM public.exercise_attempts ea
         WHERE ea.user_id = p_user_id AND ea.exercise_id = p_exercise_id);

    INSERT INTO public.exercise_attempts
        (user_id, exercise_id, user_response, is_correct, time_taken_ms,
         exercise_type, sense_id, is_first_attempt, created_at)
    VALUES
        (p_user_id, p_exercise_id, COALESCE(p_user_response, '{}'::jsonb), p_is_correct,
         p_time_taken_ms, v_type, v_sense, v_first, now())
    RETURNING id INTO v_attempt_id;

    UPDATE public.exercises
       SET attempt_count = COALESCE(attempt_count, 0) + 1,
           correct_count = CASE WHEN p_is_correct THEN COALESCE(correct_count, 0) + 1
                                ELSE correct_count END
     WHERE id = p_exercise_id;

    IF v_sense IS NOT NULL THEN
        BEGIN
            UPDATE public.prestudy_followups
               SET completed_at = now()
             WHERE user_id = p_user_id AND sense_id = v_sense AND completed_at IS NULL;
        EXCEPTION
            WHEN undefined_table THEN NULL;   -- prestudy_workflow.sql not applied
            WHEN OTHERS THEN
                v_warnings := v_warnings || jsonb_build_object('step', 'prestudy_followups', 'error', SQLERRM);
        END;
    END IF;

    IF v_sense IS NOT NULL AND v_lang IS NOT NULL AND v_first THEN
        BEGIN
            SELECT * INTO v_bkt
              FROM public.update_vocabulary_from_word_test(
                       p_user_id, v_sense, p_is_correct, v_lang, v_type);
            IF FOUND THEN
                v_before := v_bkt.out_p_known_before;
                v_after  := v_bkt.out_p_known_after;
                v_bkt_json := jsonb_build_object(
                    'out_sense_id',       v_bkt.out_sense_id,
                    'out_p_known_before', v_bkt.out_p_known_before,
                    'out_p_known_after',  v_bkt.out_p_known_after,
                    'out_status',         v_bkt.out_status);
            END IF;
        EXCEPTION WHEN OTHERS THEN
            v_bkt_json := NULL; v_before := NULL; v_after := NULL;
            v_warnings := v_warnings || jsonb_build_object('step', 'bkt', 'error', SQLERRM);
        END;

        -- A word that has just crossed 0.90 raises the floor of commoner words.
        IF v_after >= 0.90 AND v_before < 0.90 THEN
            BEGIN
                PERFORM public.bkt_infer_from_frequency(
                    p_user_id, v_lang, v_sense, v_after);
            EXCEPTION WHEN OTHERS THEN
                v_warnings := v_warnings || jsonb_build_object('step', 'frequency_inference', 'error', SQLERRM);
            END;
        END IF;

        IF v_before IS NOT NULL AND v_after IS NOT NULL THEN
            BEGIN
                UPDATE public.exercise_attempts
                   SET p_known_before = v_before,
                       p_known_after  = v_after
                 WHERE id = v_attempt_id;
            EXCEPTION WHEN OTHERS THEN
                v_warnings := v_warnings || jsonb_build_object('step', 'p_known_capture', 'error', SQLERRM);
            END;
        END IF;
    END IF;

    IF v_sense IS NOT NULL THEN
        BEGIN
            v_ladder := public.ladder_apply_progress(
                p_user_id, v_sense, p_exercise_id, p_is_correct, v_first,
                CASE WHEN p_exercise_context IN ('standard', 'gate', 'stress_test')
                     THEN p_exercise_context ELSE 'standard' END);
        EXCEPTION WHEN OTHERS THEN
            v_ladder := NULL;
            v_warnings := v_warnings || jsonb_build_object('step', 'ladder', 'error', SQLERRM);
        END;
    END IF;

    IF v_lang IS NOT NULL AND v_secs > 0 THEN
        BEGIN
            PERFORM public.credit_study_time(
                p_user_id, v_lang, 'practice', v_secs, 'exercise_attempts', v_attempt_id::text);
        EXCEPTION WHEN OTHERS THEN
            v_warnings := v_warnings || jsonb_build_object('step', 'study_time', 'error', SQLERRM);
        END;
    END IF;

    IF v_lang IS NOT NULL AND p_plan_kind IN ('practice_acq', 'practice_maint') THEN
        BEGIN
            PERFORM public.record_session_progress(
                p_user_id       => p_user_id,
                p_language_id   => v_lang,
                p_attempt_id    => v_attempt_id,
                p_kind          => p_plan_kind,
                p_skill         => NULL,
                p_delta_count   => 0,
                p_delta_seconds => v_secs,
                p_sense_id      => CASE WHEN p_plan_kind = 'practice_acq' THEN v_sense::bigint END,
                p_is_tail       => COALESCE(p_is_tail, false));
        EXCEPTION WHEN OTHERS THEN
            v_warnings := v_warnings || jsonb_build_object('step', 'session_progress', 'error', SQLERRM);
        END;
    END IF;

    -- Read last: ladder_apply_progress does not write user_flashcards, so this
    -- is the row Python rates.
    IF v_sense IS NOT NULL AND v_lang IS NOT NULL THEN
        SELECT to_jsonb(c) INTO v_card
          FROM (SELECT uf.id, uf.stability, uf.difficulty, uf.due_date, uf.last_review,
                       uf.reps, uf.lapses, uf.state
                  FROM public.user_flashcards uf
                 WHERE uf.user_id = p_user_id AND uf.sense_id = v_sense
                 ORDER BY uf.id
                 LIMIT 1) c;
    END IF;

    RETURN jsonb_build_object(
        'attempt_id',       v_attempt_id,
        'is_first_attempt', v_first,
        'exercise_type',    v_type,
        'sense_id',         v_sense,
        'language_id',      v_lang,
        'bkt_update',       v_bkt_json,
        'ladder',           v_ladder,
        'flashcard',        v_card,
        'warnings',         v_warnings);
END
$function$;

REVOKE ALL ON FUNCTION public.record_exercise_attempt(
    uuid, uuid, boolean, jsonb, integer, smallint, integer, text, boolean, text)
    FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.record_exercise_attempt(
    uuid, uuid, boolean, jsonb, integer, smallint, integer, text, boolean, text)
    TO service_role;

COMMENT ON FUNCTION public.record_exercise_attempt IS
    'One-transaction Practice attempt write path (attempt row with is_first_attempt, atomic '
    'exercise counters, prestudy follow-up, BKT, ladder, study-time ledger, plan progress). '
    'FSRS stays in Python: the user_flashcards row is returned for it. Service role only; '
    'used when PRACTICE_ATTEMPT_RPC_ENABLED is set.';
