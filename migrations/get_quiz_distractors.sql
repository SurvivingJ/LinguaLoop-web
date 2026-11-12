-- ============================================================================
-- get_quiz_distractors.sql — word-quiz wrong options: same part of speech,
-- and each option's own headword
-- Date: 2026-11-11
--
-- get_distractors (the post-test "Quick Vocab Check") returned random
-- definitions of any part of speech and only the definition text. Many
-- definitions written in the word's own language start with or contain the
-- word itself (~13% of zh rank-1 standard definitions), so the right option
-- was the one containing the word being asked about. The caller now hides
-- each option's own headword (services/vocabulary/mask.py), which needs the
-- headword; and wrong options of the same part of speech are preferred, with
-- any other part of speech only filling a shortfall. Tags are compared through
-- public.pos_class (defined here), since the dictionary mixes tag sets.
--
-- Same filters and auth check as get_distractors (which is left in place).
-- ============================================================================

BEGIN;

CREATE OR REPLACE FUNCTION public.pos_class(p_pos text)
RETURNS text
LANGUAGE sql
IMMUTABLE
SET search_path = public, pg_temp
AS $$
    -- Mirror of static/js/session/lexicon.js posClass / services/vocabulary/lexicon.py
    -- pos_class (tests/fixtures/lexicon/cases.json). Dictionary tags are mixed:
    -- "noun" / "n" / "名词" / "NOUN" / "名詞" / "nr" are one class.
    SELECT CASE
        WHEN t = ANY (ARRAY['noun','n','nr','ns','nt','nz','nw','ng','nrt','nrfg','vn','an','propn','名词','名詞']) THEN 'noun'
        WHEN t = ANY (ARRAY['verb','v','vd','vg','vi','aux','动词','動詞']) THEN 'verb'
        WHEN t = ANY (ARRAY['adjective','adj','a','ag','形容词','形容詞','形状詞']) THEN 'adj'
        WHEN t = ANY (ARRAY['adverb','adv','d','ad','副词','副詞']) THEN 'adv'
        WHEN t = ANY (ARRAY['measure_word','q','量词','助数詞']) THEN 'measure'
        WHEN t = ANY (ARRAY['pronoun','pron','r','代词','代名詞']) THEN 'pron'
        ELSE t
    END
    FROM (SELECT lower(trim(COALESCE(p_pos, ''))) AS t) x
$$;

REVOKE ALL ON FUNCTION public.pos_class(text) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.pos_class(text) TO service_role;

CREATE OR REPLACE FUNCTION public.get_quiz_distractors(
    p_sense_id                integer,
    p_language_id             smallint,
    p_count                   integer  DEFAULT 3,
    p_definition_language_id  smallint DEFAULT NULL
) RETURNS TABLE(out_definition text, out_lemma text)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
    v_def_lang smallint := COALESCE(p_definition_language_id, p_language_id);
    v_vocab_id integer;
    v_pos      text;
BEGIN
    IF auth.role() NOT IN ('authenticated', 'service_role') THEN
        RAISE EXCEPTION 'Authentication required' USING ERRCODE = '42501';
    END IF;

    SELECT dws.vocab_id, public.pos_class(dv.part_of_speech)
      INTO v_vocab_id, v_pos
      FROM dim_word_senses dws JOIN dim_vocabulary dv ON dv.id = dws.vocab_id
     WHERE dws.id = p_sense_id;

    RETURN QUERY
    SELECT c.definition, c.lemma
      FROM (
        SELECT DISTINCT ON (dv.id) dws.definition, dv.lemma,
               COALESCE(v_pos <> '' AND public.pos_class(dv.part_of_speech) = v_pos, false) AS same_pos,
               random() AS r
          FROM dim_word_senses dws
          JOIN dim_vocabulary dv ON dv.id = dws.vocab_id
         WHERE dv.language_id = p_language_id
           AND dws.definition_language_id = v_def_lang
           AND dws.id <> p_sense_id
           AND dws.vocab_id IS DISTINCT FROM v_vocab_id
           AND dws.sense_rank = 1
           AND dws.definition_level = 'standard'
           AND dws.definition IS NOT NULL
         ORDER BY dv.id, random()
      ) c
     ORDER BY c.same_pos DESC, c.r
     LIMIT GREATEST(LEAST(p_count, 10), 0);
END;
$$;

REVOKE ALL ON FUNCTION public.get_quiz_distractors(integer, smallint, integer, smallint)
    FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.get_quiz_distractors(integer, smallint, integer, smallint)
    TO service_role;

COMMENT ON FUNCTION public.get_quiz_distractors(integer, smallint, integer, smallint) IS
    'Word-quiz wrong options: same part of speech first, each with its own headword so the '
    'caller can hide it. See migrations/get_quiz_distractors.sql.';

COMMIT;
