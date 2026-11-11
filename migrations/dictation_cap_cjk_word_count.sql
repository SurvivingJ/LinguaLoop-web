-- ============================================================================
-- dictation_cap_cjk_word_count.sql — count Chinese/Japanese transcript words
-- Date: 2026-11-11
--
-- The dictation length cap (dictation_max_words, TASK-715) is checked in
-- get_recommended_tests and recommended_tests_ranked as
--     array_length(string_to_array(trim(t.transcript), ' '), 1)
-- Chinese and Japanese transcripts have no spaces, so every one counted as
-- ~1 word and passed the cap: a 983-character Chinese passage (638 words by
-- the dictation grader) was served as a daily dictation.
--
-- transcript_word_count(text): the space count for spaced scripts; for text
-- containing kana or CJK ideographs, non-space non-punctuation characters /
-- 1.5 (rounded up) — the grader's own ratio on live zh content (983 chars ->
-- 638 words). Both selection functions are rewritten in place from their live
-- definitions with only that expression replaced (idempotent: a function that
-- no longer contains the old expression is left alone).
-- ============================================================================

BEGIN;

CREATE OR REPLACE FUNCTION public.transcript_word_count(p_text text)
RETURNS integer
LANGUAGE sql
IMMUTABLE
SET search_path = public, pg_temp
AS $$
    SELECT CASE
        WHEN p_text IS NULL THEN NULL
        WHEN p_text ~ '[぀-ヿ㐀-鿿]' THEN
            ceil(char_length(regexp_replace(
                p_text, '[[:space:][:punct:]、。，！？；：「」『』（）“”‘’《》…—・]', '', 'g'
            )) / 1.5)::integer
        ELSE array_length(string_to_array(trim(p_text), ' '), 1)
    END
$$;

COMMENT ON FUNCTION public.transcript_word_count(text) IS
    'Transcript length in words for the dictation cap: space-split for spaced scripts; '
    'kana/CJK text counts non-space non-punctuation characters / 1.5. '
    'See migrations/dictation_cap_cjk_word_count.sql.';

DO $migration$
DECLARE
    f   regprocedure;
    def text;
    old_expr constant text := 'array_length(string_to_array(trim(t.transcript), '' ''), 1)';
BEGIN
    FOR f IN
        SELECT p.oid::regprocedure
          FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
         WHERE n.nspname = 'public'
           AND p.proname IN ('get_recommended_tests', 'recommended_tests_ranked')
    LOOP
        def := pg_get_functiondef(f);
        IF position(old_expr IN def) > 0 THEN
            EXECUTE replace(def, old_expr, 'public.transcript_word_count(t.transcript)');
            RAISE NOTICE 'dictation cap: rewrote %', f;
        END IF;
    END LOOP;
END
$migration$;

COMMIT;
