-- ============================================================================
-- drop_update_vocabulary_from_word_test_4arg_rollback.sql — rollback of
-- migrations/drop_update_vocabulary_from_word_test_4arg.sql
--
-- Recreates public.update_vocabulary_from_word_test(uuid, integer, boolean,
-- smallint) exactly as live on 2026-11-23 (pg_get_functiondef, CRLF line ends
-- normalised to LF; body md5 without comments/whitespace
-- 32f5891ffb84292976bec4e87ff48228; SECURITY INVOKER, no pinned search_path,
-- owner postgres, EXECUTE service_role only). This brings back the 4-argument
-- ambiguity (42725) the forward file removes.
-- Learner-visible: yes, in reverse: 4-argument word-test updates are lost again.
--
-- VERIFY AFTER (read-only; expect true, false, false, true):
--   SELECT md5(regexp_replace(regexp_replace(p.prosrc, '--[^\n]*', '', 'g'), '\s', '', 'g'))
--            = '32f5891ffb84292976bec4e87ff48228' AS body_matches,
--          has_function_privilege('anon', p.oid, 'EXECUTE') AS anon_x,
--          has_function_privilege('authenticated', p.oid, 'EXECUTE') AS auth_x,
--          has_function_privilege('service_role', p.oid, 'EXECUTE') AS service_x
--     FROM pg_proc p
--    WHERE p.oid = 'public.update_vocabulary_from_word_test(uuid,integer,boolean,smallint)'::regprocedure;
--
-- Idempotent: CREATE OR REPLACE + REVOKE/GRANT; safe to re-run.
-- ============================================================================

CREATE OR REPLACE FUNCTION public.update_vocabulary_from_word_test(p_user_id uuid, p_sense_id integer, p_is_correct boolean, p_language_id smallint)
 RETURNS TABLE(out_sense_id integer, out_p_known_before numeric, out_p_known_after numeric, out_status text)
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_p_current NUMERIC;
    v_p_new NUMERIC;
    v_status TEXT;
BEGIN
    -- Get current p_known or compute prior
    SELECT COALESCE(uvk.p_known,
        CASE
            WHEN dv.frequency_rank IS NULL THEN 0.10
            WHEN dv.frequency_rank >= 6.0 THEN 0.85
            WHEN dv.frequency_rank >= 5.0 THEN 0.65
            WHEN dv.frequency_rank >= 4.0 THEN 0.35
            WHEN dv.frequency_rank >= 3.0 THEN 0.15
            ELSE 0.05
        END
    ) INTO v_p_current
    FROM dim_word_senses dws
    JOIN dim_vocabulary dv ON dv.id = dws.vocab_id
    LEFT JOIN user_vocabulary_knowledge uvk
        ON uvk.user_id = p_user_id AND uvk.sense_id = p_sense_id
    WHERE dws.id = p_sense_id;

    IF v_p_current IS NULL THEN
        v_p_current := 0.10;
    END IF;

    v_p_new := bkt_update_word_test(v_p_current, p_is_correct);
    v_status := bkt_status(v_p_new);

    INSERT INTO user_vocabulary_knowledge
        (user_id, sense_id, language_id, p_known, status,
         evidence_count, word_test_correct, word_test_wrong,
         last_evidence_at, updated_at)
    VALUES (
        p_user_id, p_sense_id, p_language_id,
        v_p_new, v_status,
        1,
        CASE WHEN p_is_correct THEN 1 ELSE 0 END,
        CASE WHEN p_is_correct THEN 0 ELSE 1 END,
        NOW(), NOW()
    )
    ON CONFLICT (user_id, sense_id) DO UPDATE SET
        p_known = EXCLUDED.p_known,
        status = CASE
            WHEN user_vocabulary_knowledge.status = 'user_marked_unknown'
            THEN 'user_marked_unknown'
            ELSE EXCLUDED.status
        END,
        evidence_count = user_vocabulary_knowledge.evidence_count + 1,
        word_test_correct = user_vocabulary_knowledge.word_test_correct + EXCLUDED.word_test_correct,
        word_test_wrong = user_vocabulary_knowledge.word_test_wrong + EXCLUDED.word_test_wrong,
        last_evidence_at = NOW(),
        updated_at = NOW();

    RETURN QUERY SELECT p_sense_id, v_p_current, v_p_new, v_status;
END;
$function$;

ALTER FUNCTION public.update_vocabulary_from_word_test(uuid, integer, boolean, smallint) OWNER TO postgres;
REVOKE ALL ON FUNCTION public.update_vocabulary_from_word_test(uuid, integer, boolean, smallint) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.update_vocabulary_from_word_test(uuid, integer, boolean, smallint) TO service_role;
