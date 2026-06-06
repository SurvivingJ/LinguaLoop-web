-- ============================================================================
-- Restore an auth check on the get_distractors RPC.
-- Date: 2026-05-15
--
-- An earlier migration (get_distractors_drop_auth_check.sql) removed the
-- auth.uid() guard because it broke service-role calls (auth.uid() is NULL
-- under the service-role JWT). The collateral effect was that *anonymous*
-- callers (anon key) could also invoke the function and enumerate every
-- definition in dim_word_senses.
--
-- This migration re-adds a guard that allows authenticated users and the
-- service role but blocks anon. The function remains SECURITY DEFINER so
-- it can read the underlying tables regardless of RLS.
-- ============================================================================

CREATE OR REPLACE FUNCTION public.get_distractors(
    p_sense_id integer,
    p_language_id smallint,
    p_count integer DEFAULT 3
)
RETURNS TABLE(out_definition text)
LANGUAGE plpgsql
STABLE
SECURITY DEFINER
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
    ORDER BY random()
    LIMIT p_count;
END;
$function$;

-- Defense in depth: also revoke EXECUTE from anon at the role level.
REVOKE EXECUTE ON FUNCTION public.get_distractors(integer, smallint, integer) FROM anon;
GRANT EXECUTE ON FUNCTION public.get_distractors(integer, smallint, integer) TO authenticated, service_role;
