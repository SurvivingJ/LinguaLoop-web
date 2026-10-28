-- ============================================================================
-- Sense vectors: one per sense (native standard row only), halfvec(768) -> halfvec(512)
-- Status: PENDING (not yet applied to live), ships with the Python writers that embed only the
--         native standard row and truncate to 512-d (scripts/backfill_sense_embeddings.py,
--         services/vocabulary/sense_generator.py). ADR-037.
-- ============================================================================
--
-- WHY
--   Supabase Free caps the database at 500 MB. Target content is 10k zh + 10k ja words
--   with full vocabulary ladders. Measured 2026-10-28: database 270 MB, of which
--   dim_word_senses is 113 MB and its embedding column alone 85 MB (55,002 vectors,
--   1,544 B each, stored inline so only 4 rows fit per 8 KB page). One meaning was
--   embedded up to SIX times: native simple + native standard + two cross-language
--   glosses x two levels. At target scale (~131k sense rows) that is ~270 MB for this
--   table alone, more than half the plan.
--
-- WHAT
--   1. A sense has ONE vector, stored on its native standard row
--      (definition_level = 'standard' AND definition_language_id = word_language_id).
--      Every other row of the same sense (native simple, every cross-language gloss)
--      borrows it through public.sense_embedding(sense_id): its "twin" is the native
--      standard row with the same (vocab_id, sense_rank). Verified 2026-10-28: all
--      26,158 simple rows and all 14,614 non-native standard rows have exactly one twin;
--      0 native standard rows lack a vector.
--      A CHECK constraint makes the invariant structural, so a writer cannot regress it.
--   2. Truncate the kept vectors to 512 dims and re-normalise (text-embedding-3-small is
--      Matryoshka-trained: identical to the API's dimensions=512).
--   3. semantic_distractors() scans the word language's native standard vectors, then
--      joins each neighbour to the row the learner actually reads (requested definition
--      language and level). sense_similarity_to_lemmas() and
--      calibration_refresh_anchor_pool() read the twin vector.
--   4. Cross-language pairs now measure similarity on native-language definitions, so
--      their dim_distractor_bands rows take the native pair's band.
--   5. Shift every band by the measured 768->512 truncation shift.
--   6. Drop the definition-mode distractor cache (its similarities were computed on the
--      old vectors) so it is refilled from the new ones. The cache is derived data.
--
-- MEASURED TRADE-OFFS (2026-10-28, live data, 3,000 unrelated native-standard pairs per
-- language, fixed md5 sample)
--   * 512-d vs 768-d: corr 0.983-0.988; top-20 neighbour overlap 90-92% (40 anchors/lang).
--   * p95 shift (the statistic cos_min is defined as): zh +0.016, en +0.016, ja +0.012.
--     Mean shift for pairs at cos 0.30-0.45 (BAND_MIN in sense_neighbours.py): +0.012.
--   * Simple-level vectors were never used as answers: semantic_distractors() ordered its
--     pool by vector BEFORE filtering on definition_level, so simple rows only took pool
--     slots and were then discarded. Borrowing the twin vector gives the full pool to the
--     requested level.
--   * Cross-language gloss vectors embedded "{lemma}: {gloss}" where a simple ja gloss is
--     ~3 characters; the native definition carries more meaning per vector.
--   * Projected: dim_word_senses ~45 MB now, ~75 MB at 10k zh + 10k ja words.
--
-- LOCKING / SPACE
--   One ALTER TABLE rewrites the table under ACCESS EXCLUSIVE (55k rows: seconds) and
--   validates the CHECK in the same pass. The rewrite needs ~45 MB of free space and
--   discards the old heap and its dead tuples; no VACUUM FULL needed.
--
-- ROLLBACK
--   Not reversible in SQL (dims 513-768 and the non-native vectors are discarded).
--   Re-embedding costs cents: drop the CHECK, restore the column type, restore the
--   function bodies from migrations/archive/shrink_sense_embeddings_halfvec768.sql and
--   migrations/archive/dim_word_senses_embedding.sql, and run
--   `python -m scripts.backfill_sense_embeddings --all-languages --force` with the old
--   writer code.
--
-- AFTER APPLYING (service role)
--   Rebuild the anchor pool, then refill the definition-mode cache one language pair
--   at a time:
--   PYTHONPATH=. python scripts/build_calibration_distractor_cache.py --refresh-pool --mode definition
-- ============================================================================

BEGIN;

SET LOCAL statement_timeout = '600s';
SET LOCAL lock_timeout = '30s';   -- fail fast rather than queue behind a long writer

-- ---------------------------------------------------------------------------
-- 0. Measure the per-language truncation shift BEFORE converting, on a fixed sample:
--    p95 of unrelated native-standard pairs (the statistic cos_min is defined as).
-- ---------------------------------------------------------------------------
CREATE TEMP TABLE _band_shift ON COMMIT DROP AS
WITH r AS (
    SELECT id, vocab_id, word_language_id w,
           row_number() OVER (PARTITION BY word_language_id ORDER BY md5(id::text)) rn
      FROM dim_word_senses
     WHERE definition_level = 'standard'
       AND definition_language_id = word_language_id
       AND embedding IS NOT NULL
), s AS (
    SELECT r.*, x.embedding e FROM r JOIN dim_word_senses x ON x.id = r.id WHERE r.rn <= 3001
), p AS (
    SELECT a.w,
           1 - (a.e <=> b.e)                                                     AS f,
           1 - (l2_normalize(subvector(a.e, 1, 512))::halfvec(512)
                <=> l2_normalize(subvector(b.e, 1, 512))::halfvec(512))          AS t
      FROM s a
      JOIN s b ON b.w = a.w AND b.rn = a.rn + 1 AND b.vocab_id <> a.vocab_id
     WHERE a.rn <= 3000
)
SELECT w,
       (percentile_cont(0.95) WITHIN GROUP (ORDER BY t)
      - percentile_cont(0.95) WITHIN GROUP (ORDER BY f))::real AS shift
  FROM p GROUP BY w;
-- Dry run 2026-10-28: zh +.016  en +.016  ja +.012

-- ---------------------------------------------------------------------------
-- 1. Rewrite the column: keep only native standard vectors, truncated to 512-d.
--    The CHECK is validated during the same rewrite pass.
-- ---------------------------------------------------------------------------
ALTER TABLE public.dim_word_senses
    ALTER COLUMN embedding TYPE halfvec(512)
    USING CASE
              WHEN definition_level = 'standard'
               AND definition_language_id = word_language_id
              THEN l2_normalize(subvector(embedding, 1, 512))::halfvec(512)
          END,
    ADD CONSTRAINT dim_word_senses_embedding_native_standard_chk
    CHECK (embedding IS NULL
           OR (definition_level = 'standard' AND definition_language_id = word_language_id));

COMMENT ON COLUMN public.dim_word_senses.embedding IS
  'text-embedding-3-small of "{lemma}: {definition}", truncated to 512 dims and L2-normalised '
  '(equivalent to the API''s dimensions=512), stored fp16. Present ONLY on the native standard '
  'row of a sense (CHECK dim_word_senses_embedding_native_standard_chk); every other row of the '
  'sense reads it through sense_embedding(id). No ANN index: semantic_distractors scans one '
  'word language exactly. Writers MUST send 512 values.';

-- ---------------------------------------------------------------------------
-- 2. sense_embedding: the vector for any sense row, read from its native standard twin.
--    Uses uq_sense_def_level (vocab_id, definition_language_id, definition_level, sense_rank).
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.sense_embedding(p_sense_id integer)
 RETURNS halfvec
 LANGUAGE sql
 STABLE
 SET search_path = public, pg_temp
AS $function$
    SELECT n.embedding
      FROM dim_word_senses s
      JOIN dim_word_senses n
        ON n.vocab_id               = s.vocab_id
       AND n.sense_rank             = s.sense_rank
       AND n.definition_language_id = s.word_language_id
       AND n.definition_level       = 'standard'
     WHERE s.id = p_sense_id;
$function$;

COMMENT ON FUNCTION public.sense_embedding(integer) IS
  'Embedding of a sense row: the vector stored on its native standard twin (same vocab_id and '
  'sense_rank, definition_language_id = word_language_id, definition_level = standard). NULL '
  'when the twin has not been embedded yet.';

REVOKE ALL ON FUNCTION public.sense_embedding(integer) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.sense_embedding(integer) TO service_role;

-- ---------------------------------------------------------------------------
-- 3. Bands: shift native pairs by the measured truncation shift; cross-language pairs
--    now score native-definition vectors, so they take their word language's native band.
--    cos_max is provisional (see calibration_semantic_distractors.sql); shifted +0.01 as
--    in the 768-d move so the band keeps its width.
-- ---------------------------------------------------------------------------
UPDATE public.dim_distractor_bands b
   SET cos_min = round((n.cos_min + s.shift)::numeric, 3)::real,
       cos_max = round((n.cos_max + 0.01)::numeric, 3)::real,
       notes   = coalesce(b.notes, '')
                 || CASE WHEN b.definition_language_id = b.word_language_id
                         THEN ' | cos_min +' || round(s.shift::numeric, 3)
                              || ', cos_max +0.01 for 512-d native-standard vectors (2026-10-28)'
                         ELSE ' | now scores native-definition vectors: band copied from the '
                              || 'native pair, then cos_min +' || round(s.shift::numeric, 3)
                              || ', cos_max +0.01 for 512-d (2026-10-28)'
                    END
  FROM public.dim_distractor_bands n, _band_shift s
 WHERE n.word_language_id       = b.word_language_id
   AND n.definition_language_id = b.word_language_id
   AND s.w                      = b.word_language_id;

-- ---------------------------------------------------------------------------
-- 4. semantic_distractors: score native standard vectors, return the requested rows.
--    Body otherwise unchanged from the live definition (pg_get_functiondef, 2026-10-28).
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
    v_embedding       halfvec(512);
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
    -- The anchor row is the one the learner reads (its definition feeds the synonym
    -- guard); its vector is its native standard twin's.
    SELECT sense_embedding(s.id), s.vocab_id, v.lemma, v.frequency_rank,
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
        -- Exact nearest-neighbour scan over the word language's native standard rows,
        -- the only rows that carry a vector (btree idx_dim_word_senses_wl_dl_level
        -- narrows to them; top-N heapsort).
        SELECT c.vocab_id,
               c.sense_rank,
               (1 - (c.embedding <=> v_embedding))::real AS similarity
          FROM dim_word_senses c
         WHERE c.word_language_id       = p_word_language_id
           AND c.definition_language_id = p_word_language_id
           AND c.definition_level       = 'standard'
           AND c.embedding IS NOT NULL
         ORDER BY c.embedding <=> v_embedding
         LIMIT v_pool
    ),
    shown AS (
        -- (4) the row of each neighbouring sense that the learner reads: requested
        -- definition language and level (uq_sense_def_level).
        SELECT t.id,
               t.vocab_id,
               t.definition,
               p.similarity
          FROM pool p
          JOIN dim_word_senses t
            ON t.vocab_id               = p.vocab_id
           AND t.sense_rank             = p.sense_rank
           AND t.definition_language_id = p_definition_language_id
           AND t.definition_level       = p_definition_level
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
          FROM shown p
          JOIN dim_vocabulary v ON v.id = p.vocab_id
         WHERE p.vocab_id <> v_vocab_id                                  -- (1) siblings
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
           -- also-correct option.
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

REVOKE ALL ON FUNCTION public.semantic_distractors(
    integer, smallint, smallint, integer, real, real, real, text, integer, boolean)
    FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.semantic_distractors(
    integer, smallint, smallint, integer, real, real, real, text, integer, boolean)
    TO service_role;

-- ---------------------------------------------------------------------------
-- 5. sense_similarity_to_lemmas: anchor vector from the twin. Candidate senses with a
--    vector are now exactly the native standard rows, so max() is over meanings.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.sense_similarity_to_lemmas(
    p_sense_id integer, p_language_id smallint, p_lemmas text[])
 RETURNS TABLE(lemma text, similarity real)
 LANGUAGE sql
 STABLE SECURITY DEFINER
 SET search_path TO 'public', 'pg_temp'
AS $function$
    with anchor as (
        select sense_embedding(p_sense_id) as embedding
    )
    select
        v.lemma,
        max(1 - (s.embedding <=> a.embedding))::real as similarity
    from anchor a
    join dim_vocabulary v
      on v.language_id = p_language_id
     and v.lemma = any(p_lemmas)
    join dim_word_senses s
      on s.vocab_id = v.id
     and s.embedding is not null
    where a.embedding is not null
    group by v.lemma;
$function$;

REVOKE ALL ON FUNCTION public.sense_similarity_to_lemmas(integer, smallint, text[])
    FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.sense_similarity_to_lemmas(integer, smallint, text[])
    TO service_role;

-- ---------------------------------------------------------------------------
-- 6. calibration_refresh_anchor_pool: has_embedding reads the twin vector.
--    Body otherwise unchanged from the live definition (pg_get_functiondef, 2026-10-28).
-- ---------------------------------------------------------------------------
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

-- ---------------------------------------------------------------------------
-- 7. The definition-mode distractor cache was computed on the old vectors: drop it
--    (and its recorded misses) so the filler rebuilds it. Pronunciation mode does not
--    use vectors and is kept.
-- ---------------------------------------------------------------------------
DELETE FROM public.calibration_distractor_cache        WHERE mode = 'definition';
DELETE FROM public.calibration_distractor_cache_misses WHERE mode = 'definition';

COMMIT;

-- ---------------------------------------------------------------------------
-- Post-apply checks
-- ---------------------------------------------------------------------------
-- SELECT pg_size_pretty(pg_total_relation_size('dim_word_senses'));       -- expect ~45 MB
-- SELECT count(*) FROM dim_word_senses WHERE embedding IS NOT NULL;       -- expect 14,230
-- SELECT count(*) FROM dim_word_senses s
--  WHERE definition_level = 'standard' AND definition_language_id = word_language_id
--    AND embedding IS NULL;                                              -- expect 0
-- SELECT * FROM dim_distractor_bands ORDER BY 1, 2;
-- EXPLAIN ANALYZE SELECT * FROM semantic_distractors(<sense_id>, 1::smallint, 2::smallint);
