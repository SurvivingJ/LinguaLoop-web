-- ============================================================================
-- word_quiz_retake_fallback_hardened.sql — tiered word-quiz candidates for
-- retakes, with the live security hardening kept (finding F-09)
-- Date: 2026-11-23   Review: pkg8. NOT APPLIED.
--
-- *** DECISION REQUIRED *** and *** LEARNER-VISIBLE ***
-- Apply only if the developer wants retakes to get a post-test word quiz again.
--
-- WHAT: CREATE OR REPLACE public.get_word_quiz_candidates(uuid, integer[],
-- smallint, integer). Query logic is that of the never-applied
-- word_quiz_retake_fallback.sql (now in migrations/archive/), verbatim:
--   Tier 1: the test's tracked words in the uncertain zone (p_known 0.25-0.75),
--           best score first, up to p_max_words (exactly what live returns now);
--   Tier 2: if fewer than p_max_words were found, fill the remaining slots from
--           the test's other tracked words (p_known < 0.25 or > 0.75), same score
--           order. 'user_marked_unknown' words are excluded in both tiers.
-- Attributes restored to the live (phase6_security_hardening.sql) ones, which
-- the archived file omitted: STABLE, SECURITY DEFINER, SET search_path =
-- public, pg_temp, owner postgres, EXECUTE service_role only. Applying the
-- archived file as written would have made the function SECURITY INVOKER with
-- a mutable search_path and left its ACL as live has it.
--
-- WHY: after a first attempt and its quiz, BKT pushes most of a test's words
-- out of the 0.25-0.75 band, so on a retake live returns no candidates and no
-- quiz is shown.
--
-- WHAT A LEARNER WOULD NOTICE: on a retake (or any test whose words are all
-- well known or well unknown), the "Quick Vocab Check" appears again with up
-- to p_max_words words; first attempts are unchanged whenever the uncertain
-- zone already fills the quiz. Quiz answers then update word knowledge as for
-- any quiz.
--
-- PRECONDITIONS: live body unchanged since 2026-11-23 (VERIFY BEFORE).
--
-- VERIFY BEFORE (read-only; expect body_md5 = 7670f2d5b030e5944aa3b182d8a98d90,
-- definer = true, search_path {public, pg_temp}, anon_x = auth_x = false):
-- VERIFY AFTER (read-only; expect body_md5 = d2d821195ae59177987bc518cf1d5c6c (= the archived file body),
-- the same attributes and grants, and has_tier2 = true):
--   SELECT md5(regexp_replace(regexp_replace(p.prosrc, '--[^\n]*', '', 'g'), '\s', '', 'g')) AS body_md5,
--          p.prosrc LIKE '%Tier 2%' AS has_tier2,
--          p.prosecdef AS definer, p.provolatile AS volatility, p.proconfig AS search_path,
--          has_function_privilege('anon', p.oid, 'EXECUTE') AS anon_x,
--          has_function_privilege('authenticated', p.oid, 'EXECUTE') AS auth_x
--     FROM pg_proc p
--    WHERE p.oid = 'public.get_word_quiz_candidates(uuid,integer[],smallint,integer)'::regprocedure;
--
-- ROLLBACK: migrations/word_quiz_retake_fallback_hardened_rollback.sql (the
-- live single-band body verbatim, live attributes and grants).
--
-- After applying: this file is canonical for get_word_quiz_candidates;
-- phase6_security_hardening.sql and bkt_vocabulary_tracking.sql keep stale
-- copies (multi-object files, rule 4: keep them, do not re-run).
--
-- Idempotent: CREATE OR REPLACE + REVOKE/GRANT; safe to re-run.
-- ============================================================================

BEGIN;

CREATE OR REPLACE FUNCTION public.get_word_quiz_candidates(
    p_user_id UUID,
    p_sense_ids INTEGER[],
    p_language_id SMALLINT,
    p_max_words INTEGER DEFAULT 5
)
RETURNS TABLE(
    out_sense_id INTEGER,
    out_lemma TEXT,
    out_definition TEXT,
    out_pronunciation TEXT,
    out_p_known NUMERIC,
    out_score NUMERIC
)
LANGUAGE plpgsql
STABLE
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
    v_found INTEGER;
BEGIN
    -- Tier 1: uncertain-zone words (highest learning value)
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

    GET DIAGNOSTICS v_found = ROW_COUNT;

    -- Tier 2: fill remaining slots from all other tracked words (for retakes)
    IF v_found < p_max_words THEN
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
          AND (uvk.p_known < 0.25 OR uvk.p_known > 0.75)
          AND uvk.status != 'user_marked_unknown'
        ORDER BY score DESC
        LIMIT (p_max_words - v_found);
    END IF;
END;
$$;

ALTER FUNCTION public.get_word_quiz_candidates(uuid, integer[], smallint, integer) OWNER TO postgres;
REVOKE ALL ON FUNCTION public.get_word_quiz_candidates(uuid, integer[], smallint, integer) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.get_word_quiz_candidates(uuid, integer[], smallint, integer) TO service_role;

COMMIT;
