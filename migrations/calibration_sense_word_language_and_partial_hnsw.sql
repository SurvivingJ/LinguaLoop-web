-- Calibration Phase 1, move 2 — make filtered vector search index-backed.
-- =============================================================================
-- PROBLEM
--   Every distractor query fixes TWO languages: the WORD's language (which words
--   are legitimate candidates) and the DEFINITION's language (what the learner
--   actually reads). `definition_language_id` is already a local column on
--   dim_word_senses. The word's language is not — it lives on dim_vocabulary and
--   requires a join.
--
--   That join is what kills the index. public.nearest_senses() does:
--
--       cross join lateral (
--           select s.* from dim_word_senses s
--           join dim_vocabulary v2 on v2.id = s.vocab_id
--           where v2.language_id = p_language_id            -- <-- joined table
--           order by s.embedding <=> a.embedding            -- <-- wants HNSW
--           limit greatest(p_k * 20, 200)
--       ) s
--
--   An HNSW index can only serve a clean `ORDER BY embedding <=> <const> LIMIT k`.
--   A predicate on a JOINED table cannot be pushed into the index scan, so the
--   planner abandons HNSW and sequentially scans every embedded sense, computing
--   ~56,000 1536-dimension cosine distances per call. Live, that is a hard
--   Postgres 57014 statement timeout — verified 2026-09-08:
--
--       select * from nearest_senses(41404, 1::smallint, null, 10, 0.30, 0.75);
--       ERROR: 57014: canceling statement due to statement timeout
--
--   The comment inside that function claims ordering-before-filtering keeps the
--   plan index-backed. It does not, because the language filter is on v2, not s.
--
-- FIX
--   1. Denormalise the word's language onto dim_word_senses as `word_language_id`,
--      so the predicate sits on the SAME table as the vector being ordered.
--   2. SEVEN partial HNSW cosine indexes, one per (word language, definition
--      language) pair that actually exists, so
--        WHERE word_language_id = X AND definition_language_id = Y
--              AND embedding IS NOT NULL
--        ORDER BY embedding <=> $1 LIMIT k
--      is a pure index scan with nothing left to discard afterwards. The
--      predicate is satisfied by the CHOICE of index, not by filtering rows.
--   3. Drop the broken nearest_senses() rather than leave it live as a trap.
--
-- WHY SEVEN INDEXES AND NOT THREE — THIS WAS MEASURED, NOT ASSUMED
--   The obvious design is three indexes, one per WORD language, leaving definition
--   language as an ordinary post-index filter. Within one word language the
--   definitions split almost exactly three ways (zh 8,214/7,828/7,828 —
--   ja 7,126/7,126/7,126), so that post-filter costs a KNOWN ~3x over-fetch (~6x
--   once definition_level is also filtered) rather than a guess. That reasoning is
--   sound about predictability and wrong about cost.
--
--   Measured on the real corpus, ja, anchor sense 41404, warm cache:
--
--     three-index design:  pool 400, hnsw.ef_search 400  ->  3,947 ms
--                          (Buffers: shared hit=4473 read=3701 — spills to disk)
--     seven-index design:  pool 100, hnsw.ef_search 100  ->     19 ms
--                          (Buffers: shared hit=2274 read=0    — fully cached)
--
--   A ~200x difference, because HNSW cost grows superlinearly in ef_search and the
--   larger working set stops fitting in shared_buffers. The over-fetch is not a
--   constant factor on a cheap operation; it is the dominant cost of the query.
--   Keying the index on both languages removes it entirely.
--
--   It costs nothing to do this. The seven predicates are DISJOINT, so they
--   partition the same rows the three would have covered: total size is 438 MB
--   versus 482 MB for the single global index they all replace, and any given
--   write still touches exactly ONE index, so write amplification is unchanged.
--   definition_level stays a post-filter (~2x) because it is a caller-overridable
--   parameter; at pool 100 that still leaves ~50 candidates for 3 slots.
--
-- WHY DENORMALISING IS SAFE HERE
--   A word's language is fixed at creation and never changes: dim_vocabulary is
--   keyed (language_id, lemma), and "the same lemma in another language" is a
--   DIFFERENT vocabulary row, not an edit to this one. So the copy cannot drift
--   from the source in normal operation.
--
--   That argument is not left to convention. The column is DERIVED, never
--   supplied: a BEFORE INSERT OR UPDATE OF vocab_id trigger overwrites whatever
--   the caller passed with dim_vocabulary.language_id, and raises if vocab_id
--   resolves to no row. A writer cannot create a sense without it, and cannot set
--   it wrongly. An AFTER UPDATE OF language_id trigger on dim_vocabulary
--   propagates the theoretical relabel, so even the case the paragraph above
--   calls impossible stays consistent.
--
--   Both trigger functions are SECURITY DEFINER because RLS is enabled on
--   dim_vocabulary and dim_word_senses; a plain trigger would read zero rows
--   under a restricted role and the derive would fail closed on every insert.
--
-- SAFETY
--   - Idempotent throughout (IF NOT EXISTS / CREATE OR REPLACE / guarded DO block).
--   - The backfill is ONE UPDATE with no per-value passes, per migrations/CLAUDE.md.
--   - NOT NULL is established via a NOT VALID check that is validated under
--     SHARE UPDATE EXCLUSIVE (does not block reads or writes), then promoted with
--     SET NOT NULL, which Postgres 17 satisfies FROM the validated constraint
--     without a second full-table scan under ACCESS EXCLUSIVE.
--   - DROP INDEX idx_dim_word_senses_embedding is NOT a capability loss. It was
--     482 MB with idx_scan = 0 against a pg_stat_database.stats_reset of NULL —
--     it never served a single scan in its entire lifetime, while
--     dim_word_senses_pkey shows 166,356. Nothing read it: the one live embedding
--     consumer, sense_similarity_to_lemmas(), scores a NAMED candidate list and
--     has no ORDER BY <=> at all, so it never used an index and does not now.
--
-- ORDERING IS LOAD-BEARING — DROP THE OLD INDEX FIRST
--   Step 1 drops idx_dim_word_senses_embedding BEFORE the step-4 backfill, and
--   that order is not cosmetic. The backfill UPDATEs all 56,022 rows, and in
--   Postgres an UPDATE writes a new heap tuple that must be inserted into EVERY
--   index on the table — including a 482 MB HNSW graph, by far the most expensive
--   index to maintain. Running the backfill with that index still present timed
--   out on the first attempt here (2026-09-08) and rolled back whole. Dropping it
--   first took the table from 859 MB to 393 MB and the same UPDATE then completed
--   in seconds. The partial graphs are built afterwards, in step 7, over final
--   data — one bulk build instead of 56k incremental inserts.
--
-- APPLIED LIVE: 2026-09-08
-- =============================================================================


-- -----------------------------------------------------------------------------
-- 1. Retire the old global index FIRST — see ORDERING above.
-- -----------------------------------------------------------------------------
DROP INDEX IF EXISTS public.idx_dim_word_senses_embedding;


-- -----------------------------------------------------------------------------
-- 2. The column
-- -----------------------------------------------------------------------------
ALTER TABLE public.dim_word_senses
  ADD COLUMN IF NOT EXISTS word_language_id smallint;

COMMENT ON COLUMN public.dim_word_senses.word_language_id IS
  'Language of the WORD (copied from dim_vocabulary.language_id). Derived by trigger trg_dim_word_senses_word_language — never set this by hand. Exists so the partial HNSW indexes can filter word language on the same table as the vector being ordered; a join to dim_vocabulary defeats the index entirely.';


-- -----------------------------------------------------------------------------
-- 3. Derive-on-write, so the column cannot be absent or wrong
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.set_sense_word_language()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path TO 'public', 'pg_temp'
AS $function$
BEGIN
    -- Overwrite unconditionally. The caller's value is not consulted: this is a
    -- derived column, and accepting a supplied value is exactly how the copy
    -- would drift from dim_vocabulary.
    SELECT v.language_id INTO NEW.word_language_id
    FROM public.dim_vocabulary v
    WHERE v.id = NEW.vocab_id;

    IF NEW.word_language_id IS NULL THEN
        RAISE EXCEPTION
            'dim_word_senses.vocab_id=% resolves to no dim_vocabulary row; cannot derive word_language_id',
            NEW.vocab_id
            USING ERRCODE = '23503';
    END IF;

    RETURN NEW;
END;
$function$;

DROP TRIGGER IF EXISTS trg_dim_word_senses_word_language ON public.dim_word_senses;
CREATE TRIGGER trg_dim_word_senses_word_language
    BEFORE INSERT OR UPDATE OF vocab_id ON public.dim_word_senses
    FOR EACH ROW EXECUTE FUNCTION public.set_sense_word_language();

-- The relabel case the header argues is impossible. Cheap: an UPDATE OF trigger
-- only fires when language_id actually appears in the UPDATE's column list, so
-- ordinary dim_vocabulary writes never reach it.
CREATE OR REPLACE FUNCTION public.propagate_vocab_language_to_senses()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path TO 'public', 'pg_temp'
AS $function$
BEGIN
    IF NEW.language_id IS DISTINCT FROM OLD.language_id THEN
        -- Does not re-fire the derive trigger: that one is UPDATE OF vocab_id.
        UPDATE public.dim_word_senses
           SET word_language_id = NEW.language_id
         WHERE vocab_id = NEW.id
           AND word_language_id IS DISTINCT FROM NEW.language_id;
    END IF;
    RETURN NEW;
END;
$function$;

DROP TRIGGER IF EXISTS trg_dim_vocabulary_language_propagate ON public.dim_vocabulary;
CREATE TRIGGER trg_dim_vocabulary_language_propagate
    AFTER UPDATE OF language_id ON public.dim_vocabulary
    FOR EACH ROW EXECUTE FUNCTION public.propagate_vocab_language_to_senses();


-- -----------------------------------------------------------------------------
-- 4. Backfill — one pass, one write-lock span
-- -----------------------------------------------------------------------------
UPDATE public.dim_word_senses s
   SET word_language_id = v.language_id
  FROM public.dim_vocabulary v
 WHERE v.id = s.vocab_id
   AND s.word_language_id IS DISTINCT FROM v.language_id;   -- a re-run rewrites nothing


-- -----------------------------------------------------------------------------
-- 5. NOT NULL, without an ACCESS EXCLUSIVE full scan
-- -----------------------------------------------------------------------------
DO $do$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'public.dim_word_senses'::regclass
          AND conname  = 'dim_word_senses_word_language_id_present'
    ) THEN
        ALTER TABLE public.dim_word_senses
          ADD CONSTRAINT dim_word_senses_word_language_id_present
          CHECK (word_language_id IS NOT NULL) NOT VALID;
    END IF;
END
$do$;

ALTER TABLE public.dim_word_senses
  VALIDATE CONSTRAINT dim_word_senses_word_language_id_present;

ALTER TABLE public.dim_word_senses
  ALTER COLUMN word_language_id SET NOT NULL;

-- The column constraint now says everything the check said. Keeping both would
-- cost a redundant per-row expression evaluation on every write.
ALTER TABLE public.dim_word_senses
  DROP CONSTRAINT IF EXISTS dim_word_senses_word_language_id_present;


-- -----------------------------------------------------------------------------
-- 6. Retire the broken searcher
-- -----------------------------------------------------------------------------
-- Decision: DROP, not repair.
--   * It times out on every call (57014), so nothing can currently be relying on
--     its results — a caller would be visibly broken, not quietly degraded.
--   * It has zero callers. The only references anywhere in the repo are comments
--     and a regression test in tests/test_sense_neighbour_band_checks.py whose
--     entire purpose is asserting sense_neighbours.py does NOT call it.
--   * Its use case — "find me distractor senses near this one" — is served by
--     public.semantic_distractors(), which is index-backed, excludes vocab_id
--     siblings, and takes its band as parameters.
--   * Repairing it would leave a second, subtly different neighbour searcher with
--     no callers, which is how it rotted the first time.
-- Recoverable: its verbatim definition is preserved in
-- migrations/dim_word_senses_embedding.sql.
DROP FUNCTION IF EXISTS public.nearest_senses(integer, smallint, text, integer, real, real);


-- -----------------------------------------------------------------------------
-- 7. Build the partial graphs (run LAST, over complete data)
-- -----------------------------------------------------------------------------
-- `embedding IS NOT NULL` sits in each predicate deliberately, and every query
-- must repeat it: it keeps unembedded senses out of the graph, and a partial
-- index is only usable when the query's predicate implies the index's. The same
-- goes for BOTH language columns — semantic_distractors() names all three.
--
-- Language ids: 1 = zh, 2 = en, 3 = ja (dim_languages). Only these seven pairs
-- exist; en words have no zh or ja glosses.
--
-- BUILD NOTES (Supabase, 2026-09-08)
--   Serial builds only. `max_parallel_maintenance_workers > 0` fails here with
--   "53100: could not resize shared memory segment ... No space left on device"
--   — /dev/shm on this instance is smaller than the DSM segment a parallel HNSW
--   build wants, at both 1GB and 256MB maintenance_work_mem. 512MB serial works.
--   Measured build times were 36-40s per ~7-11k-row index, which is also why the
--   pair-keyed design was buildable through a client with a ~2 minute ceiling
--   while a 21-24k-row per-word-language index was not.
--
--     SET max_parallel_maintenance_workers = 0;
--     SET maintenance_work_mem = '512MB';
--
CREATE INDEX IF NOT EXISTS idx_dws_emb_w1_d1 ON public.dim_word_senses
  USING hnsw (embedding vector_cosine_ops)
  WHERE word_language_id = 1 AND definition_language_id = 1 AND embedding IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_dws_emb_w1_d2 ON public.dim_word_senses
  USING hnsw (embedding vector_cosine_ops)
  WHERE word_language_id = 1 AND definition_language_id = 2 AND embedding IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_dws_emb_w1_d3 ON public.dim_word_senses
  USING hnsw (embedding vector_cosine_ops)
  WHERE word_language_id = 1 AND definition_language_id = 3 AND embedding IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_dws_emb_w2_d2 ON public.dim_word_senses
  USING hnsw (embedding vector_cosine_ops)
  WHERE word_language_id = 2 AND definition_language_id = 2 AND embedding IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_dws_emb_w3_d1 ON public.dim_word_senses
  USING hnsw (embedding vector_cosine_ops)
  WHERE word_language_id = 3 AND definition_language_id = 1 AND embedding IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_dws_emb_w3_d2 ON public.dim_word_senses
  USING hnsw (embedding vector_cosine_ops)
  WHERE word_language_id = 3 AND definition_language_id = 2 AND embedding IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_dws_emb_w3_d3 ON public.dim_word_senses
  USING hnsw (embedding vector_cosine_ops)
  WHERE word_language_id = 3 AND definition_language_id = 3 AND embedding IS NOT NULL;

-- Supports the post-index definition_level filter and the anchor CTE lookups.
CREATE INDEX IF NOT EXISTS idx_dim_word_senses_wl_dl_level
  ON public.dim_word_senses (word_language_id, definition_language_id, definition_level);


-- =============================================================================
-- Runbook
-- =============================================================================
-- Run the embedding backfill to completion FIRST. Building the graphs over a
-- complete corpus is far cheaper than building them over a partial one and
-- letting thousands of inserts trickle in afterwards:
--     python -m scripts.backfill_sense_embeddings --all-languages --batch 256
--
-- =============================================================================
-- Verification
-- =============================================================================
-- Column is populated and agrees with the source:
--   SELECT count(*) AS disagreements
--     FROM dim_word_senses s JOIN dim_vocabulary v ON v.id = s.vocab_id
--    WHERE s.word_language_id IS DISTINCT FROM v.language_id;    -- expect 0
--
-- The derive trigger actually fires (supply 2 for a Japanese word, expect 3 back):
--   WITH w AS (
--     INSERT INTO dim_word_senses (vocab_id, definition_language_id, definition,
--                                  definition_level, word_language_id)
--     SELECT id, 2, 'trigger probe', 'standard', 2 FROM dim_vocabulary
--      WHERE language_id = 3 LIMIT 1
--     RETURNING vocab_id, word_language_id)
--   SELECT * FROM w;                                             -- expect 3, not 2
--   -- then: DELETE FROM dim_word_senses WHERE definition = 'trigger probe';
--
-- The plan is an index scan on the PAIR index, not a seq scan (expect
-- "Index Scan using idx_dws_emb_w3_d2", Execution Time in the tens of ms warm):
--   SET hnsw.ef_search = 100;
--   EXPLAIN (ANALYZE, BUFFERS)
--   SELECT id FROM dim_word_senses
--    WHERE word_language_id = 3 AND definition_language_id = 2 AND embedding IS NOT NULL
--    ORDER BY embedding <=> (SELECT embedding FROM dim_word_senses WHERE id = 41404)
--    LIMIT 100;
--
-- The timeout is gone because the function is:
--   SELECT count(*) FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
--    WHERE n.nspname = 'public' AND p.proname = 'nearest_senses';   -- expect 0
-- =============================================================================
