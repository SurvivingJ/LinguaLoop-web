-- get_distractors: exclude cross-language gloss rows from the distractor pool.
--
-- dim_word_senses can now hold gloss rows (source='llm_gloss') whose
-- definition_language_id differs from the word's own dim_vocabulary.language_id
-- (e.g. an English gloss row on a Japanese vocab_id). The prior version filtered
-- only on dv.language_id (the WORD's language), so a Japanese test's distractor
-- pool could return an English gloss's `definition` text as a "Japanese"
-- distractor. Add the missing predicate: the DEFINITION's own language must
-- match p_language_id too.
--
-- Supersedes migrations/get_distractors_filter_standard_level.sql (same
-- function; only the new predicate is added -- archived per migrations/CLAUDE.md).
--
-- Applied live 2026-08-23 (project kpfqrjtfxmujzolwsvdq).

CREATE OR REPLACE FUNCTION public.get_distractors(p_sense_id integer, p_language_id smallint, p_count integer DEFAULT 3)
 RETURNS TABLE(out_definition text)
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
 SET search_path TO 'public', 'pg_temp'
AS $function$
BEGIN
    IF auth.role() NOT IN ('authenticated', 'service_role') THEN
        RAISE EXCEPTION 'Authentication required'
            USING ERRCODE = '42501';
    END IF;

    RETURN QUERY
    SELECT dws.definition
    FROM dim_word_senses dws
    JOIN dim_vocabulary dv ON dv.id = dws.vocab_id
    WHERE dv.language_id = p_language_id
      AND dws.definition_language_id = p_language_id
      AND dws.id != p_sense_id
      AND dws.vocab_id != (SELECT vocab_id FROM dim_word_senses WHERE id = p_sense_id)
      AND dws.sense_rank = 1
      AND dws.definition_level = 'standard'
    ORDER BY random()
    LIMIT p_count;
END;
$function$;
