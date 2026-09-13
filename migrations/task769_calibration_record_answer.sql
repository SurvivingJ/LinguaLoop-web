-- TASK-769 — Calibration: grade one answer in a single round trip.
-- =============================================================================
-- PROBLEM
--   Clicking an option took ~570 ms to reveal correct/incorrect. None of that
--   was computation. Measured on 2026-09-13:
--
--     * REST round trip, Flask -> Supabase ap-southeast-2, keep-alive:
--       53-108 ms, median ~65 ms.
--     * calibration_ability(): 47 ms server-side.
--
--   and services/calibration_service.record_answer() made EIGHT sequential
--   Supabase calls to grade one click:
--
--     1. auth.get_user()                      (middleware, every request)
--     2. SELECT calibration_sessions          (route _load_session)
--     3. SELECT calibration_responses         (ownership + already-answered)
--     4. SELECT calibration_response_options  (find key and chosen)
--     5. UPDATE calibration_responses         (grade)
--     6. UPDATE calibration_response_options  (was_chosen)
--     7. UPDATE calibration_sessions          (counters)
--     8. RPC calibration_ability(fit=false)   (header counts)
--
--   8 x 65 ms + 47 ms ~= 570 ms, of which ~520 ms is network. The work itself is
--   a handful of index lookups on tables with a few thousand rows. This is a
--   round-trip problem, and the only fix for a round-trip problem is fewer round
--   trips.
--
-- DECISIONS
--
--   1. ONE RPC DOES THE WHOLE GRADE.
--      Steps 2-8 collapse into this function. Every check the Python performed
--      is performed here, in the same order, with the same outcomes — this is a
--      transport change, not a policy change. The behaviour that must not drift:
--        * a response that is not this user's is "unknown item" (NOT "forbidden"
--          — an id belonging to someone else must be indistinguishable from one
--          that does not exist, same reasoning as get_session);
--        * a response whose is_correct is already set is refused, so an answer
--          cannot be overwritten by a replayed request;
--        * position NULL is a SKIP and is graded INCORRECT, never dropped —
--          not knowing is the thing being measured.
--
--   2. FAILURES RETURN jsonb, THEY DO NOT RAISE.
--      Every check runs before the first write, so returning {"error": ...} is
--      exactly equivalent to raising and rolling back, and it does not make the
--      service depend on how the PostgREST driver happens to shape an exception
--      message. The service maps these strings back to CalibrationError, so the
--      route still answers 400 with the same text it always did.
--
--   3. THE COUNTERS ARE INCREMENTED IN SQL, NOT READ-MODIFY-WRITTEN IN PYTHON.
--      The old path computed items_answered + 1 from a session row it had
--      fetched earlier in the request. That is a lost-update race across two
--      tabs. `items_answered = items_answered + 1` cannot lose one.
--
--   4. THE HEADER COUNTS COME BACK FROM THIS CALL, SO calibration_ability()
--      IS NOT CALLED ON THE HOT PATH AT ALL.
--      The running header renders `answered` and `correct` and nothing else. The
--      session row already holds both, and this function has just written them.
--      The old code called calibration_ability(fit=False) — 47 ms plus a round
--      trip — to read two integers it could have returned itself, and then threw
--      away every other field. The ability CURVE is still computed the same way
--      it always was, at /ability and /end, by the same estimator.
--
-- CONSEQUENCES
--   /answer drops from 8 Supabase calls to 2 (auth + this), ~570 ms -> ~130 ms.
--   TASK-774 removes the auth round trip, taking it to ~70 ms.
--   Nothing about grading, the stored evidence, or the ability fit changes.
-- =============================================================================

CREATE OR REPLACE FUNCTION public.calibration_record_answer(
    p_response_id bigint,
    p_user_id     uuid,
    p_session_id  uuid,
    p_position    integer DEFAULT NULL,
    p_latency_ms  integer DEFAULT NULL
)
RETURNS jsonb
LANGUAGE plpgsql
VOLATILE
SECURITY DEFINER
SET search_path TO 'public', 'pg_temp'
AS $function$
DECLARE
    v_resp            calibration_responses%ROWTYPE;
    v_key_position    smallint;
    v_chosen_sense_id integer;
    v_chosen_is_key   boolean;
    v_option_count    integer;
    v_is_correct      boolean;
    v_answered        integer;
    v_correct         integer;
BEGIN
    IF auth.role() NOT IN ('authenticated', 'service_role') THEN
        RAISE EXCEPTION 'Authentication required' USING ERRCODE = '42501';
    END IF;

    -- ---- checks, all before any write -------------------------------------
    SELECT * INTO v_resp
      FROM calibration_responses
     WHERE id = p_response_id
       AND user_id = p_user_id;

    IF NOT FOUND THEN
        RETURN jsonb_build_object('error', 'unknown item');
    END IF;

    IF v_resp.session_id <> p_session_id THEN
        RETURN jsonb_build_object('error', 'item does not belong to this session');
    END IF;

    IF v_resp.is_correct IS NOT NULL THEN
        RETURN jsonb_build_object('error', 'item already answered');
    END IF;

    SELECT count(*), min(o.position) FILTER (WHERE o.is_key)
      INTO v_option_count, v_key_position
      FROM calibration_response_options o
     WHERE o.response_id = p_response_id;

    IF COALESCE(v_option_count, 0) = 0 THEN
        RETURN jsonb_build_object('error', 'item has no recorded options');
    END IF;

    IF p_position IS NOT NULL THEN
        SELECT o.sense_id, o.is_key
          INTO v_chosen_sense_id, v_chosen_is_key
          FROM calibration_response_options o
         WHERE o.response_id = p_response_id
           AND o.position = p_position::smallint;

        IF NOT FOUND THEN
            RETURN jsonb_build_object('error', 'no such option');
        END IF;
    END IF;

    -- A skip grades incorrect. So does picking a non-key option. The two are
    -- distinguished in the stored row (chosen_sense_id NULL vs set), never in
    -- the grade.
    v_is_correct := COALESCE(v_chosen_is_key, false);

    -- ---- writes ------------------------------------------------------------
    UPDATE calibration_responses
       SET chosen_sense_id = v_chosen_sense_id,
           is_correct      = v_is_correct,
           latency_ms      = p_latency_ms,
           answered_at     = now()
     WHERE id = p_response_id;

    IF v_chosen_sense_id IS NOT NULL THEN
        UPDATE calibration_response_options
           SET was_chosen = true
         WHERE response_id = p_response_id
           AND sense_id    = v_chosen_sense_id;
    END IF;

    UPDATE calibration_sessions
       SET items_answered = items_answered + 1,
           items_correct  = items_correct + CASE WHEN v_is_correct THEN 1 ELSE 0 END
     WHERE id = p_session_id
    RETURNING items_answered, items_correct INTO v_answered, v_correct;

    RETURN jsonb_build_object(
        'is_correct',       v_is_correct,
        'correct_position', v_key_position,
        'skipped',          (p_position IS NULL),
        'answered',         COALESCE(v_answered, 0),
        'correct',          COALESCE(v_correct, 0)
    );
END;
$function$;

COMMENT ON FUNCTION public.calibration_record_answer(bigint, uuid, uuid, integer, integer) IS
'TASK-769. Grades one calibration answer and returns the running counts, in one
round trip. Replaces six sequential Supabase calls in calibration_service.
p_position NULL is a skip, graded incorrect. Invariant failures come back as
{"error": ...} before any write, never as an exception.';

REVOKE ALL ON FUNCTION public.calibration_record_answer(bigint, uuid, uuid, integer, integer) FROM public;
GRANT EXECUTE ON FUNCTION public.calibration_record_answer(bigint, uuid, uuid, integer, integer)
    TO authenticated, service_role;
