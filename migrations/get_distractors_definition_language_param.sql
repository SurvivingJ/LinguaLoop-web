-- get_distractors: accept an optional definition-language override.
--
-- p_language_id still picks the WORD pool (other words studied in this
-- language). The new p_definition_language_id -- defaulting to p_language_id,
-- so every existing caller is unaffected -- picks which language the
-- returned definition TEXT is in. When it differs from p_language_id, only
-- OTHER words that actually have an 'llm_gloss' row in that language are
-- eligible; there is no fallback to the word's native definition, so a
-- returned distractor can never silently switch language mid-quiz.
--
-- Supersedes migrations/get_distractors_filter_gloss_language.sql (same
-- function; only the new optional param is added).
--
-- Applied live 2026-08-24 (project kpfqrjtfxmujzolwsvdq).

CREATE OR REPLACE FUNCTION public.get_distractors(
    p_sense_id integer,
    p_language_id smallint,
    p_count integer DEFAULT 3,
    p_definition_language_id smallint DEFAULT NULL
)
 RETURNS TABLE(out_definition text)
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
 SET search_path TO 'public', 'pg_temp'
AS $function$
DECLARE
    v_def_lang smallint;
BEGIN
    IF auth.role() NOT IN ('authenticated', 'service_role') THEN
        RAISE EXCEPTION 'Authentication required'
            USING ERRCODE = '42501';
    END IF;

    v_def_lang := COALESCE(p_definition_language_id, p_language_id);

    RETURN QUERY
    SELECT dws.definition
    FROM dim_word_senses dws
    JOIN dim_vocabulary dv ON dv.id = dws.vocab_id
    WHERE dv.language_id = p_language_id
      AND dws.definition_language_id = v_def_lang
      AND dws.id != p_sense_id
      AND dws.vocab_id != (SELECT vocab_id FROM dim_word_senses WHERE id = p_sense_id)
      AND dws.sense_rank = 1
      AND dws.definition_level = 'standard'
    ORDER BY random()
    LIMIT p_count;
END;
$function$;
