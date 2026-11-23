-- ============================================================================
-- word_quiz_retake_fallback_hardened_rollback.sql — rollback of
-- migrations/word_quiz_retake_fallback_hardened.sql
--
-- Restores public.get_word_quiz_candidates exactly as live on 2026-11-23
-- (pg_get_functiondef, CRLF normalised to LF; body md5 without
-- comments/whitespace 7670f2d5b030e5944aa3b182d8a98d90, the
-- phase6_security_hardening.sql body): uncertain zone only, STABLE, SECURITY
-- DEFINER, search_path public, pg_temp, owner postgres, EXECUTE service_role only.
-- Learner-visible: yes, in reverse: retakes get no word quiz again.
--
-- VERIFY AFTER (read-only; expect true, false, false):
--   SELECT md5(regexp_replace(regexp_replace(p.prosrc, '--[^\n]*', '', 'g'), '\s', '', 'g'))
--            = '7670f2d5b030e5944aa3b182d8a98d90' AS body_matches,
--          has_function_privilege('anon', p.oid, 'EXECUTE') AS anon_x,
--          has_function_privilege('authenticated', p.oid, 'EXECUTE') AS auth_x
--     FROM pg_proc p
--    WHERE p.oid = 'public.get_word_quiz_candidates(uuid,integer[],smallint,integer)'::regprocedure;
--
-- Idempotent: CREATE OR REPLACE + REVOKE/GRANT; safe to re-run.
-- ============================================================================

BEGIN;

CREATE OR REPLACE FUNCTION public.get_word_quiz_candidates(p_user_id uuid, p_sense_ids integer[], p_language_id smallint, p_max_words integer DEFAULT 5)
 RETURNS TABLE(out_sense_id integer, out_lemma text, out_definition text, out_pronunciation text, out_p_known numeric, out_score numeric)
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
 SET search_path TO 'public', 'pg_temp'
AS $function$
BEGIN
    RETURN QUERY
    SELECT
        uvk.sense_id,
        dv.lemma,
        dws.definition,
        dws.pronunciation,
        uvk.p_known,
        (uvk.p_known * (1 - uvk.p_known) *
         (1.0 / GREATEST(1.0, ln(GREATEST(1.0, COALESCE(dv.frequency_rank, 1.0)::numeric))))
        ) AS score
    FROM user_vocabulary_knowledge uvk
    JOIN dim_word_senses dws ON dws.id = uvk.sense_id
    JOIN dim_vocabulary dv ON dv.id = dws.vocab_id
    WHERE uvk.user_id = p_user_id
      AND uvk.sense_id = ANY(p_sense_ids)
      AND uvk.p_known BETWEEN 0.25 AND 0.75
      AND uvk.status != 'user_marked_unknown'
    ORDER BY score DESC
    LIMIT p_max_words;
END;
$function$;

ALTER FUNCTION public.get_word_quiz_candidates(uuid, integer[], smallint, integer) OWNER TO postgres;
REVOKE ALL ON FUNCTION public.get_word_quiz_candidates(uuid, integer[], smallint, integer) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.get_word_quiz_candidates(uuid, integer[], smallint, integer) TO service_role;

COMMIT;
