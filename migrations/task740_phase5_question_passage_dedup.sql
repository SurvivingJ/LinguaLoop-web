-- TASK-740 Phase 5: question/passage-level dedup (finding #3, 2026-08-29 review)
-- =============================================================================
-- CONTEXT
--   Finding #3: duplicate/near-duplicate passages (and by extension their
--   generated questions) show up within a topic+tier over time — the
--   recurring "cat t-shirt"-style Chinese topic reads as a copy of an
--   earlier test at the same tier. Phase 4 capped how many tests a topic can
--   fan out to, but did nothing to stop those tests from being near-copies
--   of each other; this phase adds the actual duplicate check.
--
--   Decision Q5 (confirmed): dedup runs at BOTH generation time (this file +
--   services/test_generation/dedup.py, scoped to topic+tier) AND per-user
--   session-recency (build_daily_session / get_recommended_tests side,
--   handled separately — see wiki/decisions for that half, which touches a
--   live RPC and needs explicit sign-off before applying).
--
-- THIS FILE (generation-time half only)
--   1. tests.passage_hash — SHA-256 of the normalized transcript (see
--      services/test_generation/dedup.py:normalize_passage for the exact
--      normalization: whitespace-collapsed, casefolded). A UNIQUE index
--      scoped to (topic_id, target_age_tier, passage_hash) makes an exact
--      re-generation of the same passage at the same topic+tier impossible
--      to insert twice, as a hard backstop behind the orchestrator's
--      application-level check-before-insert.
--   2. tests.passage_embedding — same pattern as dim_word_senses.embedding
--      (migrations/dim_word_senses_embedding.sql): vector(1536) + HNSW
--      cosine index, used for the near-duplicate fallback when the hash
--      doesn't collide but the passage is still suspiciously similar
--      (paraphrase of an existing passage, not a byte-identical repeat).
--   3. match_test_passages_by_topic_tier RPC — cosine-similarity search
--      scoped to ONE topic+tier (never global; a passage about the same
--      topic at a different tier is supposed to differ in complexity, not
--      content, so it is deliberately not compared against). Purely
--      additive new function, no existing RPC touched.
--
-- Both new columns are nullable — existing rows are left NULL rather than
-- backfilled (the passage-level content needed to compute either value only
-- exists for rows going through the orchestrator from here on; backfilling
-- history would mean re-hashing/re-embedding every live transcript for a
-- pass whose whole point is stopping *new* duplicates, so it's out of scope
-- here). NULL values are excluded from both the unique index and the
-- similarity search, so old rows neither collide nor get matched against.
-- =============================================================================

-- ──────────────────────────────────────────────────────────────
-- 1 & 2. New columns on tests
-- ──────────────────────────────────────────────────────────────

ALTER TABLE public.tests
  ADD COLUMN IF NOT EXISTS passage_hash text,
  ADD COLUMN IF NOT EXISTS passage_embedding vector(1536);

COMMENT ON COLUMN public.tests.passage_hash IS
  'SHA-256 hex of the normalized transcript (see '
  'services/test_generation/dedup.py:normalize_passage). TASK-740 Phase 5 '
  'exact-duplicate backstop, scoped per (topic_id, target_age_tier).';

COMMENT ON COLUMN public.tests.passage_embedding IS
  'Embedding of the transcript (same model/dimensions as topics.embedding '
  'and dim_word_senses.embedding). TASK-740 Phase 5 near-duplicate check, '
  'scoped per (topic_id, target_age_tier) via match_test_passages_by_topic_tier.';

-- Exact-duplicate backstop: NULLs (legacy rows, or a row inserted before the
-- orchestrator started populating this) are excluded via the partial WHERE,
-- since a NULL hash means "not computed", not "matches every other NULL".
CREATE UNIQUE INDEX IF NOT EXISTS idx_tests_topic_tier_passage_hash
  ON public.tests (topic_id, target_age_tier, passage_hash)
  WHERE passage_hash IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_tests_passage_embedding
  ON public.tests USING hnsw (passage_embedding vector_cosine_ops);

-- ──────────────────────────────────────────────────────────────
-- 3. match_test_passages_by_topic_tier — scoped near-dup search
-- ──────────────────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION public.match_test_passages_by_topic_tier(
    p_topic_id uuid,
    p_tier_id smallint,
    query_embedding vector,
    match_threshold double precision DEFAULT 0.92,
    match_count integer DEFAULT 3
)
RETURNS TABLE(id uuid, similarity double precision)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path TO 'public', 'pg_temp'
AS $function$
BEGIN
    RETURN QUERY
    SELECT
        t.id,
        (1 - (t.passage_embedding <=> query_embedding))::FLOAT AS similarity
    FROM tests t
    WHERE t.topic_id = p_topic_id
      AND t.target_age_tier = p_tier_id
      AND t.passage_embedding IS NOT NULL
      AND (1 - (t.passage_embedding <=> query_embedding)) > match_threshold
    ORDER BY t.passage_embedding <=> query_embedding
    LIMIT match_count;
END;
$function$;

-- ──────────────────────────────────────────────────────────────
-- 4. Verification queries (run manually after migration)
-- ──────────────────────────────────────────────────────────────
-- SELECT count(*) FROM public.tests WHERE passage_hash IS NOT NULL;
--
-- SELECT * FROM public.match_test_passages_by_topic_tier(
--   (SELECT topic_id FROM tests WHERE passage_embedding IS NOT NULL LIMIT 1),
--   (SELECT target_age_tier FROM tests WHERE passage_embedding IS NOT NULL LIMIT 1),
--   (SELECT passage_embedding FROM tests WHERE passage_embedding IS NOT NULL LIMIT 1),
--   0.80, 10
-- );
