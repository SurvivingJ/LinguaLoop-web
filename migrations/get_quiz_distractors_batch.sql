-- ============================================================================
-- get_quiz_distractors_batch.sql — word-quiz wrong options for several words
-- in one call
--
-- The post-test "Quick Vocab Check" called get_quiz_distractors once per quiz
-- word (up to five round trips, more when a gloss quiz falls back to the
-- word's own language). This function takes the words as an array and returns
-- the options for all of them. Per word it applies exactly the selection of
-- get_quiz_distractors (migrations/get_quiz_distractors.sql, left in place):
-- same filters, one definition per other headword, same part of speech first,
-- random within that, at most LEAST(p_count, 10) rows.
--
-- p_definition_language_ids is aligned with p_sense_ids; a NULL element (or a
-- NULL / shorter array) means "the word's own language", as a NULL
-- p_definition_language_id does in get_quiz_distractors.
--
-- out_position is the 1-based position of the word in p_sense_ids, so a
-- repeated sense id gets its own draw.
--
-- Not called until QUIZ_DISTRACTORS_BATCH=1 is set for the app
-- (services/vocabulary/knowledge_service.py).
-- ============================================================================

BEGIN;

CREATE OR REPLACE FUNCTION public.get_quiz_distractors_batch(
    p_sense_ids                integer[],
    p_language_id              smallint,
    p_count                    integer    DEFAULT 3,
    p_definition_language_ids  smallint[] DEFAULT NULL
) RETURNS TABLE(out_position integer, out_sense_id integer, out_definition text, out_lemma text)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
BEGIN
    IF auth.role() NOT IN ('authenticated', 'service_role') THEN
        RAISE EXCEPTION 'Authentication required' USING ERRCODE = '42501';
    END IF;

    IF COALESCE(array_length(p_sense_ids, 1), 0) > 50 THEN
        RAISE EXCEPTION 'At most 50 senses per call' USING ERRCODE = '22023';
    END IF;

    RETURN QUERY
    SELECT req.pos::integer, req.sense_id, d.definition, d.lemma
      FROM (
        SELECT u.pos,
               u.sense_id,
               COALESCE(u.def_lang, p_language_id) AS def_lang,
               src.vocab_id,
               public.pos_class(srcv.part_of_speech) AS pos_cls,
               (src.id IS NOT NULL) AS found
          FROM unnest(p_sense_ids, COALESCE(p_definition_language_ids, ARRAY[]::smallint[]))
               WITH ORDINALITY AS u(sense_id, def_lang, pos)
          LEFT JOIN dim_word_senses src  ON src.id  = u.sense_id
          LEFT JOIN dim_vocabulary  srcv ON srcv.id = src.vocab_id
         WHERE u.sense_id IS NOT NULL
      ) req
     CROSS JOIN LATERAL (
        SELECT c.definition, c.lemma, c.same_pos, c.r
          FROM (
            SELECT DISTINCT ON (dv.id) dws.definition, dv.lemma,
                   COALESCE(req.found AND req.pos_cls <> ''
                            AND public.pos_class(dv.part_of_speech) = req.pos_cls, false) AS same_pos,
                   random() AS r
              FROM dim_word_senses dws
              JOIN dim_vocabulary dv ON dv.id = dws.vocab_id
             WHERE dv.language_id = p_language_id
               AND dws.definition_language_id = req.def_lang
               AND dws.id <> req.sense_id
               AND dws.vocab_id IS DISTINCT FROM req.vocab_id
               AND dws.sense_rank = 1
               AND dws.definition_level = 'standard'
               AND dws.definition IS NOT NULL
             ORDER BY dv.id, random()
          ) c
         ORDER BY c.same_pos DESC, c.r
         LIMIT GREATEST(LEAST(p_count, 10), 0)
     ) d
     ORDER BY req.pos, d.same_pos DESC, d.r;
END;
$$;

REVOKE ALL ON FUNCTION public.get_quiz_distractors_batch(integer[], smallint, integer, smallint[])
    FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.get_quiz_distractors_batch(integer[], smallint, integer, smallint[])
    TO service_role;

COMMENT ON FUNCTION public.get_quiz_distractors_batch(integer[], smallint, integer, smallint[]) IS
    'get_quiz_distractors for several words in one call; out_position is the word''s '
    '1-based position in p_sense_ids. See migrations/get_quiz_distractors_batch.sql.';

COMMIT;
