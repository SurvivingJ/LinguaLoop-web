-- Rollback of calibration_pool_refresh_language_and_katakana.sql (TASK-1075): restores the live definition of
-- 2026-11-19 (md5 of pg_get_functiondef 401d92af587c162133d9a8798276d0db). Pool rows are not changed; run the
-- refresh again after a rollback if katakana lemmas should return to pronunciation mode.
DROP FUNCTION IF EXISTS public.calibration_refresh_anchor_pool(smallint);

CREATE OR REPLACE FUNCTION public.calibration_refresh_anchor_pool()
 RETURNS integer
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public', 'pg_temp'
AS $function$
DECLARE
    v_rows integer;
BEGIN
    IF auth.role() <> 'service_role' THEN
        RAISE EXCEPTION 'service_role required' USING ERRCODE = '42501';
    END IF;

    -- DELETE rather than TRUNCATE: TRUNCATE takes an ACCESS EXCLUSIVE lock and
    -- would block a live calibration run for the duration of the rebuild.
    -- `WHERE true` is required: Supabase's pg_safeupdate rejects an unqualified
    -- DELETE issued through PostgREST ("DELETE requires a WHERE clause"), which
    -- made `build_calibration_distractor_cache.py --refresh-pool` fail (TASK-778).
    DELETE FROM calibration_anchor_pool WHERE true;

    INSERT INTO calibration_anchor_pool (
        word_language_id, definition_language_id, sense_id, vocab_id,
        lemma, definition, pronunciation, zipf, zipf_band,
        has_embedding, has_pronunciation)
    SELECT s.word_language_id,
           s.definition_language_id,
           s.id,
           s.vocab_id,
           v.lemma,
           s.definition,
           s.pronunciation,
           v.frequency_rank,
           calibration_zipf_band(v.frequency_rank),
           (n.embedding IS NOT NULL),
           (s.pronunciation IS NOT NULL AND btrim(s.pronunciation) <> ''
            -- A hiragana-only headword (もっと, ぐるぐる) IS its own reading, so
            -- a pronunciation item for it is answered by copying the prompt and
            -- measures nothing. Excluded from pronunciation mode only.
            AND v.lemma !~ '^[ぁ-ゟー]+$')
      FROM dim_word_senses s
      JOIN dim_vocabulary v ON v.id = s.vocab_id
      -- The sense's vector lives on its native standard twin (sense_embedding()).
      LEFT JOIN dim_word_senses n
        ON n.vocab_id               = s.vocab_id
       AND n.sense_rank             = s.sense_rank
       AND n.definition_language_id = s.word_language_id
       AND n.definition_level       = 'standard'
     WHERE s.definition_level = 'standard'
       AND v.frequency_rank IS NOT NULL
       AND s.word_language_id IS NOT NULL
       AND s.definition_language_id IS NOT NULL
       -- A row that qualifies for neither mode can never be served, so it is
       -- not an anchor and does not belong in the pool.
       AND (n.embedding IS NOT NULL
            OR (s.pronunciation IS NOT NULL AND btrim(s.pronunciation) <> ''
                AND v.lemma !~ '^[ぁ-ゟー]+$'));

    GET DIAGNOSTICS v_rows = ROW_COUNT;
    ANALYZE calibration_anchor_pool;
    RETURN v_rows;
END;
$function$;

REVOKE ALL ON FUNCTION public.calibration_refresh_anchor_pool() FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.calibration_refresh_anchor_pool() TO service_role;
