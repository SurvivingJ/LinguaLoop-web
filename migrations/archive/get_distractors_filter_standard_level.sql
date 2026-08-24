-- Migration: get_distractors filters definition_level='standard'
--
-- Two-level senses store both a `simple` and a `standard` row per sense at the
-- same sense_rank. Without this predicate the distractor pool would return both
-- rows of a sense, producing duplicate / near-duplicate multiple-choice options.
-- Restricting to the standard level keeps one definition per sense, matching the
-- pre-migration single-definition behaviour.
--
-- Preserves the live function's SECURITY DEFINER + search_path + auth guard
-- (see restore_get_distractors_auth_check.sql); only the level predicate is new.

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
      AND dws.id != p_sense_id
      AND dws.vocab_id != (SELECT vocab_id FROM dim_word_senses WHERE id = p_sense_id)
      AND dws.sense_rank = 1
      AND dws.definition_level = 'standard'
    ORDER BY random()
    LIMIT p_count;
END;
$function$;
