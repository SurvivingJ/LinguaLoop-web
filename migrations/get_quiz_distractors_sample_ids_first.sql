-- =============================================================================
-- get_quiz_distractors_sample_ids_first.sql  (codebase review 2026-11, Efficiency)
-- =============================================================================
-- Purpose: same wrong options from get_quiz_distractors, without sorting a
-- language's whole sense list on every call.
--
-- Before (get_quiz_distractors.sql): every eligible sense of the language was
-- read WITH its definition text, public.pos_class() was called on every one of
-- those rows, and the whole set was sorted by (headword, random()) to keep one
-- sense per headword before p_count rows were taken. Once per quiz word.
-- pos_class carries SET search_path, so it cannot be inlined: on a local
-- 150,000-sense dictionary those calls were most of the run time.
--
-- Now:
--   1. Work out once which raw part-of-speech tags of the language belong to
--      the asked word's class (a DISTINCT over one column, then pos_class on
--      the handful of distinct tags).
--   2. Read only the ids of the eligible senses (sense id, headword id, a
--      random number each; no definition text, no function call per row).
--   3. Per headword keep the smallest random number (hash aggregate, no sort)
--      and take the top p_count headwords by (same part of speech, that
--      number). With LIMIT this is a bounded top-N pass.
--   4. Fetch definition and headword for those few senses only.
--
-- Equivalent by construction: the filters are the same, and the old body's
-- DISTINCT ON (headword) ORDER BY headword, random() also kept, per headword,
-- the sense with the smallest random number and then ranked headwords by that
-- same number. So the choice of headwords, the sense shown for each, the
-- output columns, the order (same part of speech first, then random), the row
-- cap (p_count, at most 10), the auth check and the grants are unchanged.
-- "Same part of speech" is the same test: a tag is in the precomputed list
-- exactly when pos_class(tag) equals the asked word's class.
--
-- Carried over unchanged, noted for whoever owns quiz quality: because a
-- headword is ranked by the smallest of its senses' random numbers, a headword
-- with several eligible senses (rank 1, standard level, in the definition
-- language) is picked more often than one with a single sense. In a local run
-- a 3-sense headword among four candidates for 3 slots was shown in 95% of
-- calls against 68% for the others. This file keeps that behaviour.
--
-- Validated on a local PostgreSQL 16 stub only (not against live): on a
-- generated dictionary the old and new bodies returned the expected number of
-- rows, only rows from the eligible set, one per headword, never the asked
-- word's own headword, same-part-of-speech rows first; and over 20,000 calls
-- each the selection frequencies per headword and per sense matched
-- (two-sample chi-square within the expected range). On a synthetic
-- 150,000-sense language the call went from about 990 ms to about 240 ms.
-- Timing on live data was not measured.
--
-- Pre-checks:
--   1. get_quiz_distractors.sql is applied (this replaces its function; it also
--      defines public.pos_class, which this file does not touch):
--        SELECT 'public.get_quiz_distractors(integer,smallint,integer,smallint)'::regprocedure,
--               'public.pos_class(text)'::regprocedure;
--   2. Keep the current body for the rollback:
--        SELECT pg_get_functiondef('public.get_quiz_distractors(integer,smallint,integer,smallint)'::regprocedure);
--   3. Optional, for the before/after plan:
--        EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM public.get_quiz_distractors(<sense_id>, <language_id>::smallint, 3);
--
-- Idempotent: CREATE OR REPLACE, same signature; REVOKE/GRANT repeated.
-- REQUIRES USER APPROVAL TO APPLY LIVE.
--
-- Rollback: re-run the CREATE OR REPLACE FUNCTION public.get_quiz_distractors
-- statement from migrations/get_quiz_distractors.sql.
-- =============================================================================

BEGIN;

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
    v_same_tags text[];
BEGIN
    IF auth.role() NOT IN ('authenticated', 'service_role') THEN
        RAISE EXCEPTION 'Authentication required' USING ERRCODE = '42501';
    END IF;

    SELECT dws.vocab_id, public.pos_class(dv.part_of_speech)
      INTO v_vocab_id, v_pos
      FROM dim_word_senses dws JOIN dim_vocabulary dv ON dv.id = dws.vocab_id
     WHERE dws.id = p_sense_id;

    -- The raw part-of-speech tags of this language that fall in the asked
    -- word's class, worked out once instead of calling pos_class on every row.
    -- MATERIALIZED keeps the planner from pushing the pos_class test below the
    -- DISTINCT, which would put the per-row calls back.
    WITH tags AS MATERIALIZED (
        SELECT DISTINCT dv.part_of_speech AS tag
          FROM dim_vocabulary dv
         WHERE dv.language_id = p_language_id
    )
    SELECT array_agg(t.tag) INTO v_same_tags
      FROM tags t
     WHERE v_pos <> '' AND public.pos_class(t.tag) = v_pos;

    RETURN QUERY
    WITH cand AS MATERIALIZED (
        -- Ids only: one row per eligible sense, with its random number.
        SELECT dws.id AS sense_id, dv.id AS vocab_id,
               COALESCE(dv.part_of_speech = ANY (v_same_tags), false) AS same_pos,
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
    ),
    picked AS (
        -- One row per headword (its smallest random number), top p_count.
        SELECT c.vocab_id, c.same_pos, min(c.r) AS r
          FROM cand c
         GROUP BY c.vocab_id, c.same_pos
         ORDER BY c.same_pos DESC, min(c.r)
         LIMIT GREATEST(LEAST(p_count, 10), 0)
    )
    -- Definitions for the picked senses only.
    SELECT dws.definition, dv.lemma
      FROM picked p
      JOIN cand c ON c.vocab_id = p.vocab_id AND c.r = p.r
      JOIN dim_word_senses dws ON dws.id = c.sense_id
      JOIN dim_vocabulary dv ON dv.id = p.vocab_id
     ORDER BY p.same_pos DESC, p.r
     LIMIT GREATEST(LEAST(p_count, 10), 0);
END;
$$;

REVOKE ALL ON FUNCTION public.get_quiz_distractors(integer, smallint, integer, smallint)
    FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.get_quiz_distractors(integer, smallint, integer, smallint)
    TO service_role;

COMMENT ON FUNCTION public.get_quiz_distractors(integer, smallint, integer, smallint) IS
    'Word-quiz wrong options: same part of speech first, each with its own headword so the '
    'caller can hide it. See migrations/get_quiz_distractors_sample_ids_first.sql.';

COMMIT;
