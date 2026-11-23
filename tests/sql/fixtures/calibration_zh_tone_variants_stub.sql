-- =============================================================================
-- calibration_zh_tone_variants_stub.sql — TEST-ONLY stub. NEVER apply live.
-- =============================================================================
-- Same signature as TASK-1092's calibration_zh_tone_variants(text, integer)
-- (migrations/calibration_zh_tones.sql): every variant changes the FIRST full-tone
-- syllable to each other full tone (the mark stays on the same vowel), minus any
-- reading of the same lemma. No inventory, no sandhi or 一/不 rule. The placement
-- functions only consume its output; use the real migration when it is available
-- (tests/test_calibration_placement_sql.py loads either).
-- =============================================================================

CREATE OR REPLACE FUNCTION public.calibration_zh_tone_variants(p_pronunciation text, p_vocab_id integer)
RETURNS text[]
LANGUAGE plpgsql STABLE
SET search_path = public, pg_temp
AS $$
DECLARE
    v_marks text[] := ARRAY[U&'\0304', U&'\0301', U&'\030C', U&'\0300'];
    v_syl   text[];
    v_alt   text[];
    v_nfd   text;
    v_mark  text;
    v_m     text;
    v_own   text[];
    v_cand  text;
    v_out   text[] := '{}';
BEGIN
    IF p_pronunciation IS NULL OR btrim(p_pronunciation) = '' THEN
        RETURN v_out;
    END IF;
    v_syl := regexp_split_to_array(
        btrim(regexp_replace(p_pronunciation, '\s*\([^)]*\)\s*', '', 'g')), '\s+');
    SELECT coalesce(array_agg(DISTINCT calibration_display_pronunciation(s.pronunciation, 1::smallint)), '{}')
      INTO v_own
      FROM dim_word_senses s
     WHERE s.vocab_id = p_vocab_id AND s.pronunciation IS NOT NULL;
    FOR i IN 1..cardinality(v_syl) LOOP
        v_nfd := normalize(v_syl[i], NFD);
        v_mark := NULL;
        FOREACH v_m IN ARRAY v_marks LOOP
            IF strpos(v_nfd, v_m) > 0 THEN v_mark := v_m; END IF;
        END LOOP;
        CONTINUE WHEN v_mark IS NULL;
        FOREACH v_m IN ARRAY v_marks LOOP
            CONTINUE WHEN v_m = v_mark;
            v_alt := v_syl;
            v_alt[i] := normalize(replace(v_nfd, v_mark, v_m), NFC);
            v_cand := array_to_string(v_alt, ' ');
            IF NOT (v_cand = ANY (v_own)) THEN
                v_out := v_out || v_cand;
            END IF;
        END LOOP;
        EXIT;
    END LOOP;
    RETURN v_out;
END;
$$;
REVOKE ALL ON FUNCTION public.calibration_zh_tone_variants(text, integer) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.calibration_zh_tone_variants(text, integer) TO service_role;
