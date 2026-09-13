-- TASK-773 — Calibration: cache the distractor sets.
-- =============================================================================
-- PROBLEM
--   semantic_distractors() measured 1064-1252 ms COLD and 17 ms warm
--   (EXPLAIN ANALYZE, 2026-09-13, three separate anchors). Cold is the normal
--   case and cannot be tuned away on this instance:
--
--     shared_buffers                        224 MB
--     seven HNSW indexes on dim_word_senses 442 MB
--
--   The working set does not fit, so each new anchor's HNSW probe reads graph
--   pages from disk. The function asks for ef_search = 100 and then fetches 100
--   candidate heap rows from a table whose rows carry a vector(1536). ~1.1 s per
--   item, every item, and it was on the critical path of every /next.
--
-- DECISIONS
--
--   1. CACHING THE SEMANTIC PICKER IS FREE, NOT A TRADE-OFF.
--      This is the fact the whole task rests on: semantic_distractors() contains
--      NO random(). Its final ORDER BY is (freq_tier, similarity DESC), fully
--      determined by the data. The same anchor has ALWAYS returned the same three
--      foils. So a cache of its output is not "an approximation to save time" —
--      it is the same answer, precomputed. Item quality is untouched, and ADR-025
--      (semantic, difficulty-matched foils) still holds exactly as written.
--
--      This is why the cache is safe and the fallback is not a quality cliff:
--      a cache miss computes the identical rows, just slowly.
--
--   2. PRONUNCIATION IS CACHED AS A POOL AND SAMPLED, BECAUSE IT **IS** RANDOM.
--      pronunciation_distractors() does contain random(), so freezing three of
--      its foils forever would remove variety that the live picker has today.
--      Instead the cache stores a POOL of up to 8 and three are sampled per
--      serve. Variety preserved, 181 ms of picking avoided.
--
--   3. THE CACHE FILLS ITSELF, AND IS ALSO FILLED AHEAD.
--      calibration_fill_distractor_cache() is called by the batch item builder
--      on a miss, so a newly-eligible sense is never unserveable — it just costs
--      what it costs today, once, ever. The bulk filler below is what stops that
--      from happening during a learner's run.
--
--   4. THE BULK FILLER WORKS ONE LANGUAGE PAIR AT A TIME, ON PURPOSE.
--      Each pair has its own partial HNSW index (56-86 MB). Draining one pair
--      before starting the next keeps that one index resident in the 224 MB of
--      shared_buffers, so anchors after the first few cost ~20-60 ms instead of
--      ~1.1 s. Interleaving pairs would thrash and turn a ~30 minute build into
--      an overnight one. scripts/build_calibration_distractor_cache.py drives it.
--
--   5. AN ANCHOR THAT CANNOT BE FILLED IS LEFT UNCACHED, NOT MARKED BAD.
--      If the picker comes up short the anchor simply has too few cache rows and
--      the item builder skips it, exactly as the old Python did. Recording a
--      permanent "this anchor is bad" verdict is the blocklist's job
--      (TASK-767/768), and it is a human judgement, not a cache's.
--
-- CONSEQUENCES
--   Distractor selection drops from ~1.1 s to an index lookup. Combined with
--   TASK-772 this is what makes a 20-item batch (TASK-770) a single fast query
--   instead of twenty slow ones.
--
--   The cache is derived data. Rebuild it (delete the affected rows, re-run the
--   filler) whenever definitions or embeddings change for a language pair —
--   otherwise a corrected definition keeps being served as a stale foil.
-- =============================================================================

CREATE TABLE IF NOT EXISTS public.calibration_distractor_cache (
    mode                   text     NOT NULL
        CHECK (mode IN ('definition', 'pronunciation')),
    anchor_sense_id        integer  NOT NULL,
    rank                   smallint NOT NULL,
    sense_id               integer  NOT NULL,
    vocab_id               integer  NOT NULL,
    -- The rendered option text: a definition in definition mode, a reading in
    -- pronunciation mode. Denormalised so serving an item needs no join.
    option_text            text     NOT NULL,
    similarity             real,
    frequency              real,
    -- Frequency tier in definition mode; edit distance in pronunciation mode.
    -- Reusing one column mirrors calibration_response_options, which records the
    -- same two things in the same slot.
    freq_tier              smallint,
    word_language_id       smallint NOT NULL,
    definition_language_id smallint NOT NULL,
    built_at               timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (mode, anchor_sense_id, rank)
);

COMMENT ON TABLE public.calibration_distractor_cache IS
'TASK-773. Precomputed distractor sets. DERIVED DATA — rebuild when definitions
or embeddings change. Definition mode is an exact cache of the deterministic
semantic_distractors(); pronunciation mode is a POOL that is sampled at serve
time because pronunciation_distractors() is random.';

CREATE INDEX IF NOT EXISTS idx_cal_distractor_cache_pair
    ON public.calibration_distractor_cache
       (word_language_id, definition_language_id, mode);

ALTER TABLE public.calibration_distractor_cache ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.calibration_distractor_cache FROM anon, authenticated;
GRANT SELECT ON TABLE public.calibration_distractor_cache TO service_role;


-- ---------------------------------------------------------------------------
-- Fill one anchor. Returns the number of cache rows the anchor now has.
-- Idempotent: an anchor that already has rows is left alone.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.calibration_fill_distractor_cache(
    p_anchor_sense_id        integer,
    p_word_language_id       smallint,
    p_definition_language_id smallint,
    p_mode                   text DEFAULT 'definition'
)
RETURNS integer
LANGUAGE plpgsql
VOLATILE
SECURITY DEFINER
SET search_path TO 'public', 'pg_temp'
AS $function$
DECLARE
    v_existing integer;
BEGIN
    IF auth.role() NOT IN ('authenticated', 'service_role') THEN
        RAISE EXCEPTION 'Authentication required' USING ERRCODE = '42501';
    END IF;

    SELECT count(*) INTO v_existing
      FROM calibration_distractor_cache c
     WHERE c.mode = p_mode AND c.anchor_sense_id = p_anchor_sense_id;

    IF v_existing > 0 THEN
        RETURN v_existing;
    END IF;

    IF p_mode = 'pronunciation' THEN
        -- A POOL of 8. Three are sampled per serve, so the variety the random
        -- picker provides survives the cache.
        INSERT INTO calibration_distractor_cache (
            mode, anchor_sense_id, rank, sense_id, vocab_id, option_text,
            similarity, frequency, freq_tier,
            word_language_id, definition_language_id)
        SELECT 'pronunciation', p_anchor_sense_id,
               (row_number() OVER () - 1)::smallint,
               d.out_sense_id, d.out_vocab_id, d.out_pronunciation,
               NULL, d.out_frequency, d.out_distance::smallint,
               p_word_language_id, p_definition_language_id
          FROM pronunciation_distractors(p_anchor_sense_id,
                                         p_word_language_id, 8) d
         WHERE d.out_pronunciation IS NOT NULL
           AND btrim(d.out_pronunciation) <> ''
        ON CONFLICT DO NOTHING;
    ELSE
        -- SIX, not three. The picker's ORDER BY is a prefix order, so the first
        -- three of six are byte-identical to asking for three — the extra rows
        -- cost nothing at build time and leave headroom if the item ever widens.
        INSERT INTO calibration_distractor_cache (
            mode, anchor_sense_id, rank, sense_id, vocab_id, option_text,
            similarity, frequency, freq_tier,
            word_language_id, definition_language_id)
        SELECT 'definition', p_anchor_sense_id,
               (row_number() OVER () - 1)::smallint,
               d.out_sense_id, d.out_vocab_id, d.out_definition,
               d.out_similarity, d.out_frequency, d.out_freq_tier,
               p_word_language_id, p_definition_language_id
          FROM semantic_distractors(p_anchor_sense_id, p_word_language_id,
                                    p_definition_language_id, 6) d
         WHERE d.out_definition IS NOT NULL
           AND btrim(d.out_definition) <> ''
        ON CONFLICT DO NOTHING;
    END IF;

    SELECT count(*) INTO v_existing
      FROM calibration_distractor_cache c
     WHERE c.mode = p_mode AND c.anchor_sense_id = p_anchor_sense_id;

    RETURN v_existing;
END;
$function$;

COMMENT ON FUNCTION public.calibration_fill_distractor_cache(integer, smallint, smallint, text) IS
'TASK-773. Populates the distractor cache for one anchor if it is empty, and
returns how many rows it now has. Idempotent.';

REVOKE ALL ON FUNCTION public.calibration_fill_distractor_cache(integer, smallint, smallint, text) FROM public;
GRANT EXECUTE ON FUNCTION public.calibration_fill_distractor_cache(integer, smallint, smallint, text)
    TO authenticated, service_role;


-- ---------------------------------------------------------------------------
-- Bulk filler, one chunk at a time. Resumable by construction: it selects
-- anchors that have no cache rows, so re-running it simply continues.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.calibration_cache_distractors_chunk(
    p_word_language_id       smallint,
    p_definition_language_id smallint,
    p_mode                   text    DEFAULT 'definition',
    p_batch                  integer DEFAULT 25
)
RETURNS TABLE(anchors_processed integer, anchors_filled integer, anchors_short integer)
LANGUAGE plpgsql
VOLATILE
SECURITY DEFINER
SET search_path TO 'public', 'pg_temp'
-- A cold chunk of 25 can legitimately take 25 x 1.1 s. The default timeout would
-- kill the build halfway through and lose nothing but time; this makes the
-- bound explicit instead of accidental.
SET statement_timeout TO '600s'
AS $function$
DECLARE
    v_anchor    record;
    v_rows      integer;
    v_processed integer := 0;
    v_filled    integer := 0;
    v_short     integer := 0;
    v_batch     integer := LEAST(GREATEST(COALESCE(p_batch, 25), 1), 200);
BEGIN
    IF auth.role() <> 'service_role' THEN
        RAISE EXCEPTION 'service_role required' USING ERRCODE = '42501';
    END IF;

    FOR v_anchor IN
        SELECT p.sense_id
          FROM calibration_anchor_pool p
         WHERE p.word_language_id       = p_word_language_id
           AND p.definition_language_id = p_definition_language_id
           AND (CASE WHEN p_mode = 'pronunciation' THEN p.has_pronunciation
                     ELSE p.has_embedding END)
           AND NOT EXISTS (SELECT 1 FROM calibration_distractor_cache c
                            WHERE c.mode = p_mode
                              AND c.anchor_sense_id = p.sense_id)
         ORDER BY p.sense_id
         LIMIT v_batch
    LOOP
        v_rows := calibration_fill_distractor_cache(
            v_anchor.sense_id, p_word_language_id, p_definition_language_id, p_mode);
        v_processed := v_processed + 1;
        IF v_rows >= 3 THEN
            v_filled := v_filled + 1;
        ELSE
            -- Left uncached deliberately (decision 5). The item builder will skip
            -- this anchor; a genuinely broken one belongs on the blocklist.
            v_short := v_short + 1;
        END IF;
    END LOOP;

    RETURN QUERY SELECT v_processed, v_filled, v_short;
END;
$function$;

COMMENT ON FUNCTION public.calibration_cache_distractors_chunk(smallint, smallint, text, integer) IS
'TASK-773. Fills the distractor cache for up to p_batch not-yet-cached anchors of
one language pair and mode. Resumable — call repeatedly until anchors_processed
is 0. Drive it with scripts/build_calibration_distractor_cache.py, one pair at a
time so that pair''s HNSW index stays resident.';

REVOKE ALL ON FUNCTION public.calibration_cache_distractors_chunk(smallint, smallint, text, integer) FROM public;
GRANT EXECUTE ON FUNCTION public.calibration_cache_distractors_chunk(smallint, smallint, text, integer)
    TO service_role;


-- ---------------------------------------------------------------------------
-- Coverage, for the build script and for anyone asking "is this warm yet?".
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.calibration_distractor_cache_coverage()
RETURNS TABLE(word_language_id smallint, definition_language_id smallint,
              mode text, anchors integer, cached integer)
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path TO 'public', 'pg_temp'
AS $function$
    SELECT p.word_language_id,
           p.definition_language_id,
           m.mode,
           count(*)::integer AS anchors,
           count(*) FILTER (
               WHERE EXISTS (SELECT 1 FROM calibration_distractor_cache c
                              WHERE c.mode = m.mode
                                AND c.anchor_sense_id = p.sense_id)
           )::integer AS cached
      FROM calibration_anchor_pool p
      CROSS JOIN (VALUES ('definition'), ('pronunciation')) AS m(mode)
     WHERE (CASE WHEN m.mode = 'pronunciation' THEN p.has_pronunciation
                 ELSE p.has_embedding END)
     GROUP BY p.word_language_id, p.definition_language_id, m.mode
     ORDER BY 1, 2, 3;
$function$;

COMMENT ON FUNCTION public.calibration_distractor_cache_coverage() IS
'TASK-773. Cached-vs-total anchor counts per language pair and mode.';

REVOKE ALL ON FUNCTION public.calibration_distractor_cache_coverage() FROM public;
GRANT EXECUTE ON FUNCTION public.calibration_distractor_cache_coverage() TO service_role;
