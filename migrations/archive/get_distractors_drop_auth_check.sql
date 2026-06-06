-- ============================================================================
-- Drop the auth.uid() guard from get_distractors RPC
-- Date: 2026-05-03
--
-- The RPC was raising 'Authentication required' when called from the admin
-- vocab pipeline (which uses the service-role key — auth.uid() returns NULL
-- for service-role JWTs, so the existing IF block always failed).
--
-- The RPC reads dim_word_senses.definition strings, which are not sensitive:
-- the same content is rendered into every public exercise served by the app.
-- Drop the auth check; rely on Supabase's outer permission layer (anon key
-- can call this RPC; service-role can call this RPC). If we later want to
-- rate-limit unauthenticated callers, do it at the API gateway, not here.
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
