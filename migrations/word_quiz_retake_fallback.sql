-- Migration: Word quiz fallback for retakes
-- Previously, get_word_quiz_candidates only returned words in the "uncertain zone"
-- (p_known 0.25-0.75). After a first attempt + quiz, BKT pushes most words outside
-- this band, so retakes got zero candidates and no quiz appeared.
-- Now uses tiered selection: uncertain-zone first, then fills from all tracked words.

CREATE OR REPLACE FUNCTION get_word_quiz_candidates(
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
) AS $$
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
$$ LANGUAGE plpgsql;
