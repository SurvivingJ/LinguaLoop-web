-- ============================================================================
-- TASK-521 — sense embeddings: column, HNSW index, and the two read functions.
--
-- Repo-record migration. The column, the index and nearest_senses() were
-- applied live on 2026-08-08 with no migration file, against the rule in
-- migrations/CLAUDE.md. Everything below is IF NOT EXISTS / CREATE OR REPLACE
-- and matches the live definitions verbatim, so applying this to the live
-- project is a no-op for the pre-existing objects.
--
-- The one genuinely new object is sense_similarity_to_lemmas(). See the note
-- above it: the band-check caller has been calling a signature that does not
-- exist since the day it was written.
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS vector;

-- 1536 dims = OpenAI text-embedding-3-small, the model
-- scripts/backfill_sense_embeddings.py uses. Changing the model means changing
-- this type and re-running the backfill with --force.
ALTER TABLE public.dim_word_senses
  ADD COLUMN IF NOT EXISTS embedding vector(1536);

-- HNSW over cosine: the distractor-band queries are all cosine, and HNSW keeps
-- the "order by distance, then filter the band" plan index-backed. An ivfflat
-- index would need a training set sized to the corpus and re-tuning as it grew.
CREATE INDEX IF NOT EXISTS idx_dim_word_senses_embedding
  ON public.dim_word_senses USING hnsw (embedding vector_cosine_ops);


-- ---------------------------------------------------------------------------
-- nearest_senses — k nearest senses inside a cosine band.
--
-- Used for distractor GENERATION: "find me some senses near this one". Live
-- since 2026-08-08; reproduced here unchanged so the repo has the record.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.nearest_senses(
    p_sense_id integer,
    p_language_id smallint,
    p_pos text DEFAULT NULL::text,
    p_k integer DEFAULT 10,
    p_cos_min real DEFAULT 0.30,
    p_cos_max real DEFAULT 0.75
)
RETURNS TABLE(
    out_sense_id integer,
    out_lemma text,
    out_definition text,
    out_similarity real
)
LANGUAGE sql
STABLE SECURITY DEFINER
SET search_path TO 'public'
AS $function$
    with anchor as (
        select s.embedding, v.part_of_speech
        from dim_word_senses s
        join dim_vocabulary v on v.id = s.vocab_id
        where s.id = p_sense_id
          and s.embedding is not null
    )
    select
        s.id,
        v.lemma,
        s.definition,
        (1 - (s.embedding <=> a.embedding))::real as similarity
    from anchor a
    cross join lateral (
        select s.*
        from dim_word_senses s
        join dim_vocabulary v2 on v2.id = s.vocab_id
        where s.embedding is not null
          and s.id <> p_sense_id
          and v2.language_id = p_language_id
        -- Order by the index-backed operator first, then filter the band:
        -- the reverse would force a sequential scan over the whole language.
        order by s.embedding <=> a.embedding
        limit greatest(p_k * 20, 200)
    ) s
    join dim_vocabulary v on v.id = s.vocab_id
    where (1 - (s.embedding <=> a.embedding)) between p_cos_min and p_cos_max
      and (p_pos is null or v.part_of_speech = p_pos)
    order by s.embedding <=> a.embedding
    limit greatest(p_k, 1);
$function$;

GRANT EXECUTE ON FUNCTION public.nearest_senses TO authenticated;


-- ---------------------------------------------------------------------------
-- sense_similarity_to_lemmas — cosine between one sense and NAMED candidates.
--
-- Why this exists as a second function rather than a parameter on the first:
-- the two answer different questions. nearest_senses() searches ("what is near
-- this?"); the band check scores ("how near is each of THESE?"). A foil the
-- judge proposed will frequently fall outside nearest_senses' k-nearest window
-- or outside its cosine band — and being outside the band is precisely the
-- verdict the caller needs returned, not a reason to omit the row.
--
-- This closes a live defect. services/vocabulary_ladder/sense_neighbours.py has
-- always called nearest_senses(p_sense_id, p_language_id, p_lemmas), which has
-- never been a real signature, and read `lemma`/`similarity` where the live
-- function returns `out_lemma`/`out_similarity`. Its except-Exception handler
-- logged the resulting PGRST202 at INFO as "RPC unavailable", so TASK-522's
-- embedding band checks silently returned "no opinion" on every foil — a state
-- indistinguishable, in the logs, from the backfill simply not having run yet.
--
-- Column names here deliberately match what that caller already reads.
--
-- Best similarity per lemma: a lemma with several senses gets the closest one,
-- because "is this foil too close to the answer?" is about whether ANY reading
-- of the foil collides, not the average over its readings.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.sense_similarity_to_lemmas(
    p_sense_id integer,
    p_language_id smallint,
    p_lemmas text[]
)
RETURNS TABLE(
    lemma text,
    similarity real
)
LANGUAGE sql
STABLE SECURITY DEFINER
SET search_path TO 'public'
AS $function$
    with anchor as (
        select s.embedding
        from dim_word_senses s
        where s.id = p_sense_id
          and s.embedding is not null
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
    group by v.lemma;
$function$;

GRANT EXECUTE ON FUNCTION public.sense_similarity_to_lemmas TO authenticated;


-- ============================================================================
-- Verification
-- ============================================================================
-- Coverage (expect 0 NULL per language once the backfill has run):
--   SELECT v.language_id, count(*) FILTER (WHERE s.embedding IS NULL) AS unembedded
--   FROM dim_word_senses s JOIN dim_vocabulary v ON v.id = s.vocab_id
--   GROUP BY 1;
--
-- Band check now returns rows rather than erroring:
--   SELECT * FROM sense_similarity_to_lemmas(
--       (SELECT s.id FROM dim_word_senses s
--          JOIN dim_vocabulary v ON v.id = s.vocab_id
--         WHERE v.language_id = 2 AND v.lemma = 'precision' LIMIT 1),
--       2::smallint, ARRAY['accuracy','bicycle']);
--   -- expect accuracy high, bicycle low; both rows present.
-- ============================================================================
