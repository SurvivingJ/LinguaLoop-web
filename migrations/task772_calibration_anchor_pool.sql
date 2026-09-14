-- TASK-772 — Calibration: a narrow anchor pool, and batch anchor selection.
-- =============================================================================
-- PROBLEM
--   calibration_next_anchor() measured 202-565 ms per item (EXPLAIN ANALYZE,
--   2026-09-13). It is not doing much arithmetic; it is reading the wrong table.
--
--   The old function scanned dim_word_senses JOIN dim_vocabulary TWICE: once
--   inside a correlated EXISTS evaluated for each of the seven Zipf bands, and
--   once to pick the row. dim_word_senses is 56,022 rows and carries a
--   vector(1536) `embedding` column, so every candidate row touched is a wide
--   heap fetch. Roughly 3,300 candidates x 7 bands of EXISTS + a final scan, all
--   to choose ONE integer.
--
--   The instance makes this worse and cannot be tuned out of it: shared_buffers
--   is 224 MB and the seven HNSW indexes on dim_word_senses total 442 MB, so the
--   wide table's pages are constantly evicted. Cold is the normal case here.
--
-- DECISIONS
--
--   1. THE ANCHOR SET IS MATERIALISED INTO A NARROW TABLE.
--      calibration_anchor_pool holds exactly the rows that are eligible to be
--      asked about, and none of the columns that make dim_word_senses expensive
--      to scan. ~27k rows, a few MB, small enough to stay resident permanently.
--      Eligibility (definition_level = 'standard', frequency_rank NOT NULL) is
--      baked in at build time because it does not vary per request.
--
--   2. THE BLOCKLIST IS **NOT** BAKED IN.
--      calibration_anchor_blocklist is edited by TASK-767/768 as bad dictionary
--      rows are found, and a blocklist that only takes effect after a pool
--      rebuild is a blocklist that silently serves known-bad items. It stays a
--      live anti-join against a tiny table.
--
--   3. ONE TABLE SERVES BOTH MODES, VIA TWO FLAGS.
--      Definition mode needs `embedding IS NOT NULL`; pronunciation mode needs a
--      non-blank `pronunciation` and ignores the session's definition language
--      entirely (readings are stored only on the native row). Carrying
--      has_embedding and has_pronunciation as columns keeps one pool rather than
--      two that could drift apart.
--
--   4. PRONUNCIATION IS STORED RAW, RENDERED AT READ TIME.
--      calibration_display_pronunciation() is presentation, and presentation
--      rules change. Baking its output into the pool would mean a display fix
--      needed a data rebuild.
--
--   5. SELECTION BECOMES ONE BATCH FUNCTION; THE SINGULAR ONE IS A WRAPPER.
--      calibration_next_anchors(..., p_count) picks N anchors in ONE query by
--      round-robin over the least-served bands:
--
--        rn   = random rank of a candidate within its own band
--        load = how many items this session has already had from that band
--        order by (load + rn), random()  ->  take N
--
--      For p_count = 1 this reduces exactly to the old behaviour: the least
--      served band that still has candidates, then a uniformly random word
--      inside it. For p_count = 20 it keeps the same balance without twenty
--      round trips (TASK-770 needs that).
--
--      calibration_next_anchor() keeps its old signature and delegates, so no
--      caller has to change in the same commit as the storage change.
--
-- CONSEQUENCES
--   Anchor selection drops from 202-565 ms to single-digit ms, and a 20-item
--   batch costs one query instead of twenty.
--   The pool is a CACHE: it must be refreshed when senses, embeddings,
--   pronunciations or frequency ranks change. calibration_refresh_anchor_pool()
--   does that in one statement and is cheap enough to run after any dictionary
--   job. A stale pool cannot serve a word that no longer qualifies in a way that
--   corrupts a measurement — it can only fail to offer a newly-eligible one —
--   but it will go stale silently, so the refresh belongs in the same scripts
--   that write dim_word_senses.
-- =============================================================================

CREATE TABLE IF NOT EXISTS public.calibration_anchor_pool (
    word_language_id       smallint NOT NULL,
    definition_language_id smallint NOT NULL,
    sense_id               integer  NOT NULL,
    vocab_id               integer  NOT NULL,
    lemma                  text     NOT NULL,
    definition             text,
    pronunciation          text,
    zipf                   real     NOT NULL,
    zipf_band              smallint NOT NULL,
    has_embedding          boolean  NOT NULL,
    has_pronunciation      boolean  NOT NULL,
    PRIMARY KEY (word_language_id, definition_language_id, sense_id)
);

COMMENT ON TABLE public.calibration_anchor_pool IS
'TASK-772. Materialised, narrow copy of the calibration-eligible senses. A CACHE
of dim_word_senses JOIN dim_vocabulary — rebuild with
calibration_refresh_anchor_pool() whenever either changes. The blocklist is
deliberately NOT baked in; it is applied live at selection time.';

-- One partial index per mode. Both lead with the columns every query equates on
-- and end with the band, which is what the round-robin orders by.
CREATE INDEX IF NOT EXISTS idx_cal_anchor_pool_definition
    ON public.calibration_anchor_pool (word_language_id, definition_language_id, zipf_band)
    WHERE has_embedding;

CREATE INDEX IF NOT EXISTS idx_cal_anchor_pool_pronunciation
    ON public.calibration_anchor_pool (word_language_id, definition_language_id, zipf_band)
    WHERE has_pronunciation;

ALTER TABLE public.calibration_anchor_pool ENABLE ROW LEVEL SECURITY;
-- Read-only reference data. No policy is granted to `authenticated`: every read
-- goes through the SECURITY DEFINER selectors below, exactly as the underlying
-- dictionary tables are reached today.
REVOKE ALL ON TABLE public.calibration_anchor_pool FROM anon, authenticated;
GRANT SELECT ON TABLE public.calibration_anchor_pool TO service_role;


-- ---------------------------------------------------------------------------
-- Rebuild. Whole-table, because the source is only ~27k rows and an incremental
-- refresh would need change tracking on dim_word_senses that does not exist.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.calibration_refresh_anchor_pool()
RETURNS integer
LANGUAGE plpgsql
VOLATILE
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
           (s.embedding IS NOT NULL),
           (s.pronunciation IS NOT NULL AND btrim(s.pronunciation) <> ''
            -- A hiragana-only headword (もっと, ぐるぐる) IS its own reading, so
            -- a pronunciation item for it is answered by copying the prompt and
            -- measures nothing. Excluded from pronunciation mode only.
            AND v.lemma !~ '^[ぁ-ゟー]+$')
      FROM dim_word_senses s
      JOIN dim_vocabulary v ON v.id = s.vocab_id
     WHERE s.definition_level = 'standard'
       AND v.frequency_rank IS NOT NULL
       AND s.word_language_id IS NOT NULL
       AND s.definition_language_id IS NOT NULL
       -- A row that qualifies for neither mode can never be served, so it is
       -- not an anchor and does not belong in the pool.
       AND (s.embedding IS NOT NULL
            OR (s.pronunciation IS NOT NULL AND btrim(s.pronunciation) <> ''
                AND v.lemma !~ '^[ぁ-ゟー]+$'));

    GET DIAGNOSTICS v_rows = ROW_COUNT;
    ANALYZE calibration_anchor_pool;
    RETURN v_rows;
END;
$function$;

COMMENT ON FUNCTION public.calibration_refresh_anchor_pool() IS
'TASK-772. Rebuilds calibration_anchor_pool from dim_word_senses/dim_vocabulary
and returns the row count. Run after any job that writes senses, embeddings,
pronunciations or frequency ranks.';

REVOKE ALL ON FUNCTION public.calibration_refresh_anchor_pool() FROM public;
GRANT EXECUTE ON FUNCTION public.calibration_refresh_anchor_pool() TO service_role;


-- ---------------------------------------------------------------------------
-- Batch anchor selection.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.calibration_next_anchors(
    p_session_id             uuid,
    p_word_language_id       smallint,
    p_definition_language_id smallint,
    p_mode                   text    DEFAULT 'definition',
    p_count                  integer DEFAULT 1
)
RETURNS TABLE(out_sense_id integer, out_vocab_id integer, out_lemma text,
              out_definition text, out_pronunciation text,
              out_zipf real, out_zipf_band smallint)
LANGUAGE plpgsql
STABLE
SECURITY DEFINER
SET search_path TO 'public', 'pg_temp'
AS $function$
DECLARE
    v_def_lang  smallint;
    v_need_pron boolean := (p_mode = 'pronunciation');
    v_count     integer := LEAST(GREATEST(COALESCE(p_count, 1), 1), 50);
BEGIN
    IF auth.role() NOT IN ('authenticated', 'service_role') THEN
        RAISE EXCEPTION 'Authentication required' USING ERRCODE = '42501';
    END IF;

    -- Readings are stored ONLY on the native row: every cross-language gloss row
    -- has pronunciation NULL (verified 2026-09-08). So in pronunciation mode the
    -- session's definition language is irrelevant and would select an empty set
    -- if honoured. Unchanged from the pre-TASK-772 function.
    v_def_lang := CASE WHEN v_need_pron THEN p_word_language_id
                       ELSE p_definition_language_id END;

    RETURN QUERY
    WITH served AS MATERIALIZED (
        SELECT cr.anchor_sense_id, cr.zipf_band
          FROM calibration_responses cr
         WHERE cr.session_id = p_session_id
    ),
    band_load AS (
        SELECT s.zipf_band AS band, count(*)::integer AS n
          FROM served s
         GROUP BY s.zipf_band
    ),
    cand AS MATERIALIZED (
        SELECT p.sense_id, p.vocab_id, p.lemma, p.definition, p.pronunciation,
               p.zipf, p.zipf_band
          FROM calibration_anchor_pool p
         WHERE p.word_language_id       = p_word_language_id
           AND p.definition_language_id = v_def_lang
           AND (CASE WHEN v_need_pron THEN p.has_pronunciation
                     ELSE p.has_embedding END)
           AND NOT EXISTS (SELECT 1 FROM served s
                            WHERE s.anchor_sense_id = p.sense_id)
           AND NOT EXISTS (SELECT 1 FROM calibration_anchor_blocklist bl
                            WHERE bl.sense_id = p.sense_id)
    ),
    ranked AS (
        -- rn is the position this word would take if its band were drained one
        -- word at a time in random order. Adding the band's existing load turns
        -- that into a global round-robin over the least-served bands.
        SELECT c.*, row_number() OVER (PARTITION BY c.zipf_band
                                       ORDER BY random()) AS rn
          FROM cand c
    )
    SELECT r.sense_id, r.vocab_id, r.lemma, r.definition,
           calibration_display_pronunciation(r.pronunciation, p_word_language_id),
           r.zipf, r.zipf_band
      FROM ranked r
      LEFT JOIN band_load b ON b.band = r.zipf_band
     ORDER BY (COALESCE(b.n, 0) + r.rn), random()
     LIMIT v_count;
END;
$function$;

COMMENT ON FUNCTION public.calibration_next_anchors(uuid, smallint, smallint, text, integer) IS
'TASK-772. Picks up to p_count unserved anchors for a session, round-robin over
the least-served Zipf bands, in one pass over calibration_anchor_pool. At
p_count = 1 this is exactly the old calibration_next_anchor behaviour.';

REVOKE ALL ON FUNCTION public.calibration_next_anchors(uuid, smallint, smallint, text, integer) FROM public;
GRANT EXECUTE ON FUNCTION public.calibration_next_anchors(uuid, smallint, smallint, text, integer)
    TO authenticated, service_role;


-- ---------------------------------------------------------------------------
-- The singular selector keeps its signature and delegates. Anything still
-- calling it gets the fast path without being edited.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.calibration_next_anchor(
    p_session_id             uuid,
    p_word_language_id       smallint,
    p_definition_language_id smallint,
    p_mode                   text DEFAULT 'definition'
)
RETURNS TABLE(out_sense_id integer, out_vocab_id integer, out_lemma text,
              out_definition text, out_pronunciation text,
              out_zipf real, out_zipf_band smallint)
LANGUAGE sql
STABLE
SECURITY INVOKER
SET search_path TO 'public', 'pg_temp'
AS $function$
    SELECT * FROM public.calibration_next_anchors(
        p_session_id, p_word_language_id, p_definition_language_id, p_mode, 1);
$function$;

COMMENT ON FUNCTION public.calibration_next_anchor(uuid, smallint, smallint, text) IS
'TASK-772. Thin wrapper over calibration_next_anchors(..., 1), kept so existing
callers need no change. SECURITY INVOKER on purpose: the callee is the definer
and owns the auth check, so this adds no privilege of its own.';

GRANT EXECUTE ON FUNCTION public.calibration_next_anchor(uuid, smallint, smallint, text)
    TO authenticated, service_role;
