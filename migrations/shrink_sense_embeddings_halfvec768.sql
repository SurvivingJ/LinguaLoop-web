-- ============================================================================
-- Shrink dim_word_senses embeddings: vector(1536) + 7 HNSW  ->  halfvec(768), no ANN
-- Status: APPLIED 2026-09-22, together with the Python change that truncates new
--         sense vectors to 768-d (scripts/backfill_sense_embeddings.py::sense_vector).
-- ============================================================================
--
-- WHY
--   Measured 2026-09-21: database 1144 MB, of which dim_word_senses is 961 MB (84%).
--     * 466 MB  TOAST — 55,002 float32 1536-d vectors (322 MB live) + update bloat
--     * 456 MB  seven partial HNSW indexes, one per (word, definition) language pair.
--               A 6 KB element fits once per 8 KB HNSW page, so ~25% of each is padding.
--   Everything else in the database is ~182 MB. The target (<400 MB) cannot be reached
--   without changing how embeddings are stored.
--
-- WHAT
--   1. Drop the seven HNSW indexes.
--   2. Store the first 768 dims as halfvec, re-normalised. text-embedding-3-small is
--      Matryoshka-trained: OpenAI's `dimensions=768` is defined as truncate + L2-normalise,
--      so migrated rows and newly-embedded rows are identical in kind.
--   3. semantic_distractors() does an exact scan instead of an ANN scan.
--   4. Shift dim_distractor_bands.cos_min by the measured truncation shift, per pair.
--
-- MEASURED TRADE-OFFS (2026-09-21, live data)
--   * fp16 at full 1536-d is lossless (100% top-100 overlap) but still ~660 MB total. Too big.
--   * 768-d vs 1536-d: corr 0.980, top-10 overlap 92%, top-100 overlap 90%, cosine +0.011.
--     512-d: corr 0.970, top-100 overlap 87%, cosine +0.022.
--   * Exact scan over the largest pair (en/en, 10,774 rows, 768-d halfvec): 12.6 ms warm.
--     HNSW at ef_search<=200 is itself approximate, and this path only runs on
--     calibration-cache misses (the cache is warm).
--   * Projected size: dim_word_senses ~130 MB, database ~310 MB (headroom for ~40k more
--     senses at ~2.1 MB per 1,000). Keeping HNSW at 768-d would add ~105 MB (~415 MB: over).
--
-- LOCKING / SPACE
--   ALTER COLUMN TYPE rewrites the table under ACCESS EXCLUSIVE (55k rows: seconds).
--   The HNSW indexes are dropped first, freeing 456 MB before the rewrite needs ~130 MB.
--   The rewrite also discards the TOAST bloat and 9k dead tuples; no VACUUM FULL needed.
--
-- ROLLBACK
--   Not reversible in SQL (dims 769-1536 are discarded). Re-embedding the whole dictionary
--   at 1536-d costs ~$0.03 (~1.6M tokens x $0.02/M): restore the column type, run
--   `python -m scripts.backfill_sense_embeddings --all-languages --force`, then recreate
--   the indexes from migrations/calibration_sense_word_language_and_partial_hnsw.sql.
--
-- AFTER APPLYING
--   PYTHONPATH=. python scripts/build_calibration_distractor_cache.py --refresh-pool
--   then rebuild calibration_distractor_cache (its stored similarities were computed on
--   the old vectors; the cache is derived data — see that script's header).
-- ============================================================================

BEGIN;

SET LOCAL statement_timeout = '600s';
SET LOCAL lock_timeout = '30s';   -- fail fast rather than queue behind a long writer

-- ---------------------------------------------------------------------------
-- 0. Measure the per-pair truncation shift BEFORE converting, on a fixed sample:
--    p95 of random unrelated sense pairs (the statistic cos_min is defined as).
-- ---------------------------------------------------------------------------
CREATE TEMP TABLE _band_shift ON COMMIT DROP AS
WITH r AS (
    -- rank without touching the vectors (IS NOT NULL reads the null bitmap only)
    SELECT id, vocab_id, word_language_id w, definition_language_id d,
           row_number() OVER (PARTITION BY word_language_id, definition_language_id
                              ORDER BY md5(id::text)) rn
      FROM dim_word_senses
     WHERE definition_level = 'standard' AND embedding IS NOT NULL
), s AS (
    SELECT r.*, x.embedding e FROM r JOIN dim_word_senses x ON x.id = r.id WHERE r.rn <= 3001
), p AS (
    SELECT a.w, a.d,
           1 - (a.e <=> b.e)                                                     AS f,
           1 - (l2_normalize(subvector(a.e, 1, 768))::halfvec(768)
                <=> l2_normalize(subvector(b.e, 1, 768))::halfvec(768))          AS t
      FROM s a
      JOIN s b ON b.w = a.w AND b.d = a.d AND b.rn = a.rn + 1 AND b.vocab_id <> a.vocab_id
     WHERE a.rn <= 3000
)
SELECT w, d,
       (percentile_cont(0.95) WITHIN GROUP (ORDER BY t)
      - percentile_cont(0.95) WITHIN GROUP (ORDER BY f))::real AS shift
  FROM p GROUP BY w, d;
-- Dry run 2026-09-21: zh/zh +.019 zh/en +.015 zh/ja +.016 en/en +.010
--                     ja/zh +.017 ja/en +.011 ja/ja +.011

-- ---------------------------------------------------------------------------
-- 1. Drop the ANN indexes (also required: they bind vector_cosine_ops to the column).
-- ---------------------------------------------------------------------------
DROP INDEX IF EXISTS public.idx_dws_emb_w1_d1;
DROP INDEX IF EXISTS public.idx_dws_emb_w1_d2;
DROP INDEX IF EXISTS public.idx_dws_emb_w1_d3;
DROP INDEX IF EXISTS public.idx_dws_emb_w2_d2;
DROP INDEX IF EXISTS public.idx_dws_emb_w3_d1;
DROP INDEX IF EXISTS public.idx_dws_emb_w3_d2;
DROP INDEX IF EXISTS public.idx_dws_emb_w3_d3;

-- ---------------------------------------------------------------------------
-- 2. Convert the column (table rewrite).
-- ---------------------------------------------------------------------------
ALTER TABLE public.dim_word_senses
    ALTER COLUMN embedding TYPE halfvec(768)
    USING l2_normalize(subvector(embedding, 1, 768))::halfvec(768);

COMMENT ON COLUMN public.dim_word_senses.embedding IS
  'text-embedding-3-small of "{lemma}: {definition}", truncated to 768 dims and L2-normalised '
  '(equivalent to the API''s dimensions=768), stored fp16. No ANN index: semantic_distractors '
  'scans one language pair exactly (~13 ms warm). Writers MUST send 768 values.';

-- ---------------------------------------------------------------------------
-- 3. Shift each pair's band floor by its measured truncation shift.
-- ---------------------------------------------------------------------------
UPDATE public.dim_distractor_bands b
   SET cos_min = round((b.cos_min + s.shift)::numeric, 3)::real,
       -- cos_max is provisional; shifted by the ~+0.009 measured near 0.75 so the
       -- band keeps its width (n=23 pairs on en/en, 2026-09-22).
       cos_max = round((b.cos_max + 0.01)::numeric, 3)::real,
       notes   = coalesce(b.notes, '') || ' | cos_min +' || round(s.shift::numeric, 3)
                 || ', cos_max +0.01 for 768-d halfvec truncation (2026-09-22)'
  FROM _band_shift s
 WHERE s.w = b.word_language_id AND s.d = b.definition_language_id;

-- ---------------------------------------------------------------------------
-- 4. semantic_distractors: halfvec(768) anchor, exact scan, no hnsw.ef_search.
--    Body otherwise unchanged from the live definition (pg_get_functiondef, 2026-09-21).
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.semantic_distractors(
    p_sense_id integer, p_word_language_id smallint, p_definition_language_id smallint,
    p_count integer DEFAULT 3, p_cos_min real DEFAULT NULL::real, p_cos_max real DEFAULT NULL::real,
    p_freq_band real DEFAULT 1.0, p_definition_level text DEFAULT 'standard'::text,
    p_pool integer DEFAULT 100, p_exclude_stem_variants boolean DEFAULT true)
 RETURNS TABLE(out_sense_id integer, out_vocab_id integer, out_lemma text, out_definition text,
               out_similarity real, out_frequency real, out_frequency_delta real, out_freq_tier smallint)
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
 SET search_path TO 'public', 'pg_temp'
 SET plan_cache_mode TO 'force_custom_plan'
AS $function$
DECLARE
    v_embedding       halfvec(768);
    v_vocab_id        integer;
    v_lemma           text;
    v_zipf            real;
    v_anchor_glosses  text[];
    v_cos_min         real;
    v_cos_max         real;
    v_pool            integer;
BEGIN
    IF auth.role() NOT IN ('authenticated', 'service_role') THEN
        RAISE EXCEPTION 'Authentication required' USING ERRCODE = '42501';
    END IF;

    v_pool := LEAST(GREATEST(COALESCE(p_pool, 100), p_count * 10), 200);

    SELECT s.embedding, s.vocab_id, v.lemma, v.frequency_rank,
           definition_head_glosses(s.definition)
      INTO v_embedding, v_vocab_id, v_lemma, v_zipf, v_anchor_glosses
      FROM dim_word_senses s
      JOIN dim_vocabulary v ON v.id = s.vocab_id
     WHERE s.id = p_sense_id;

    IF v_embedding IS NULL THEN
        RETURN;
    END IF;

    IF p_cos_min IS NULL OR p_cos_max IS NULL THEN
        SELECT b.cos_min, b.cos_max
          INTO v_cos_min, v_cos_max
          FROM dim_distractor_bands b
         WHERE b.word_language_id       = p_word_language_id
           AND b.definition_language_id = p_definition_language_id;
    END IF;

    v_cos_min := COALESCE(p_cos_min, v_cos_min, 0.40);
    v_cos_max := COALESCE(p_cos_max, v_cos_max, 0.75);

    RETURN QUERY
    WITH pool AS (
        -- Exact nearest-neighbour scan over one language pair (the btree
        -- idx_dim_word_senses_wl_dl_level narrows to the pair; top-N heapsort).
        -- Every other filter belongs downstream of the LIMIT, as before.
        SELECT c.id,
               c.vocab_id,
               c.definition,
               c.definition_level,
               (1 - (c.embedding <=> v_embedding))::real AS similarity
          FROM dim_word_senses c
         WHERE c.word_language_id       = p_word_language_id
           AND c.definition_language_id = p_definition_language_id
           AND c.embedding IS NOT NULL
         ORDER BY c.embedding <=> v_embedding
         LIMIT v_pool
    ),
    filtered AS (
        SELECT p.id,
               p.vocab_id,
               v.lemma,
               p.definition,
               p.similarity,
               v.frequency_rank AS zipf,
               CASE
                   WHEN v_zipf IS NULL OR v.frequency_rank IS NULL THEN NULL
                   ELSE abs(v.frequency_rank - v_zipf)
               END::real AS zipf_delta
          FROM pool p
          JOIN dim_vocabulary v ON v.id = p.vocab_id
         WHERE p.vocab_id <> v_vocab_id                                  -- (1) siblings
           AND p.definition_level = p_definition_level                   -- (4) 'standard'
           AND p.similarity >= v_cos_min                                 -- (2) measured floor
           AND p.similarity <= v_cos_max
           AND btrim(p.definition) <> btrim(v_lemma)
           -- (5) morphological variants of the anchor lemma
           AND NOT (
                 p_exclude_stem_variants
                 AND shared_prefix_len(v.lemma, v_lemma) >= 4
                 AND shared_prefix_len(v.lemma, v_lemma)
                     >= 0.6 * least(length(v.lemma), length(v_lemma))
               )
           -- (6) shares a head gloss with the right answer: a synonym, so an
           -- also-correct option (先生 "a teacher" / 教師 "teacher; ...").
           AND NOT (definition_head_glosses(p.definition) && v_anchor_glosses)
    ),
    tiered AS (
        SELECT f.*,
               CASE                                                      -- (3) soft key
                   WHEN f.zipf_delta IS NULL              THEN 1::smallint
                   WHEN f.zipf_delta <= p_freq_band       THEN 0::smallint
                   WHEN f.zipf_delta <= p_freq_band * 2   THEN 1::smallint
                   ELSE                                        2::smallint
               END AS freq_tier
          FROM filtered f
    ),
    per_word AS (
        SELECT DISTINCT ON (t.vocab_id) t.*
          FROM tiered t
         ORDER BY t.vocab_id, t.freq_tier, t.similarity DESC
    ),
    per_text AS (
        SELECT DISTINCT ON (lower(btrim(w.definition))) w.*
          FROM per_word w
         ORDER BY lower(btrim(w.definition)), w.freq_tier, w.similarity DESC
    )
    SELECT r.id, r.vocab_id, r.lemma, r.definition,
           r.similarity, r.zipf, r.zipf_delta, r.freq_tier
      FROM per_text r
     ORDER BY r.freq_tier, r.similarity DESC
     LIMIT GREATEST(p_count, 1);
END;
$function$;

COMMIT;

-- ---------------------------------------------------------------------------
-- Post-apply checks
-- ---------------------------------------------------------------------------
-- SELECT pg_size_pretty(pg_database_size(current_database()));          -- expect ~310 MB
-- SELECT pg_size_pretty(pg_total_relation_size('dim_word_senses'));     -- expect ~130 MB
-- SELECT count(*) FROM dim_word_senses WHERE embedding IS NULL;         -- expect 0
-- SELECT * FROM dim_distractor_bands ORDER BY 1,2;                      -- cos_min up .010-.019
-- EXPLAIN ANALYZE SELECT * FROM semantic_distractors(<sense_id>, 2::smallint, 2::smallint);
--
-- Code that must ship with this (1536 floats written into halfvec(768) are rejected;
-- embed-on-create logs and swallows the failure, leaving NULL embeddings until backfilled):
--   * scripts/backfill_sense_embeddings.py — add sense_vector(v): v[:768], L2-normalised;
--     use it in embed_and_store before the UPDATE.
--   * services/vocabulary/sense_generator.py::_embed_new_senses — same helper before the UPDATE.
--   * services/vocabulary_ladder/sense_neighbours.py BAND_MIN 0.35 -> ~0.365 (same shift).
--   * Do NOT change EmbeddingService globally: topics/test passages stay 1536-d.
