-- =============================================================================
-- TASK-994 — dim_vocabulary.frequency_rank fill (read-only checks)
-- =============================================================================
-- Run after migrations/task994_vocab_frequency_fill.sql is applied:
--
--   psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f tests/sql/test_task994_vocab_frequency_fill.sql
--
-- Read-only (SELECTs inside a DO block that only RAISEs). Asserts:
--   1. Rows still without a rank are at most the 76 the fill leaves NULL
--      (zh 12, ja 44, en 20: 64 wordfreq has no score for, plus 12 ja compounds
--      wordfreq scores only by their parts) — fewer is fine if since filled.
--   2. The basic words from the report have a Zipf rank >= 6.
--   3. No rank outside the column's Zipf scale (0 .. 8).
-- =============================================================================

DO $$
DECLARE
    v_null_zh integer;
    v_null_ja integer;
    v_null_en integer;
    v_basic   integer;
    v_bad     integer;
BEGIN
    SELECT count(*) FILTER (WHERE language_id = 1),
           count(*) FILTER (WHERE language_id = 3),
           count(*) FILTER (WHERE language_id = 2)
      INTO v_null_zh, v_null_ja, v_null_en
      FROM public.dim_vocabulary WHERE frequency_rank IS NULL;
    IF v_null_zh > 12 OR v_null_ja > 44 OR v_null_en > 20 THEN
        RAISE EXCEPTION 'FAIL 1: rows without a rank zh % (<=12) ja % (<=44) en % (<=20)',
            v_null_zh, v_null_ja, v_null_en;
    END IF;
    RAISE NOTICE 'PASS 1: rows without a rank zh % ja % en %', v_null_zh, v_null_ja, v_null_en;

    SELECT count(*) INTO v_basic FROM public.dim_vocabulary
     WHERE language_id = 1 AND lemma IN ('是', '都', '有', '不', '很', '人')
       AND frequency_rank >= 6.0;
    IF v_basic <> 6 THEN
        RAISE EXCEPTION 'FAIL 2: % of 是/都/有/不/很/人 have a rank >= 6', v_basic;
    END IF;
    RAISE NOTICE 'PASS 2: 是/都/有/不/很/人 ranked >= 6';

    SELECT count(*) INTO v_bad FROM public.dim_vocabulary
     WHERE frequency_rank IS NOT NULL AND (frequency_rank <= 0 OR frequency_rank > 8);
    IF v_bad <> 0 THEN
        RAISE EXCEPTION 'FAIL 3: % ranks outside (0, 8]', v_bad;
    END IF;
    RAISE NOTICE 'PASS 3: every rank on the Zipf scale';
END
$$;
