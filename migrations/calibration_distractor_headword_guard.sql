-- TASK-776 — Calibration: shared-headword guard for semantic_distractors().
-- =============================================================================
-- PROBLEM
--   A ja/en Calibration item for 先生 offered, as a WRONG answer,
--     "teacher; an instructor at a school"                      (教師)
--   next to the right one,
--     "a teacher — a person who teaches knowledge or skills..." (先生)
--   Both are correct. 教師 is a synonym, not a near-miss, and a learner who
--   knows 先生 can still be marked wrong -- which pulls their measured ability
--   down, the one thing a calibration item must not do.
--
--   None of the existing guards can catch it:
--     * cosine was 0.71, under the 0.75 ceiling. The ceiling was always
--       provisional (see dim_distractor_bands' comment): short dictionary glosses
--       for true synonyms routinely score high-0.6s to low-0.7s.
--     * the sibling and stem-variant guards compare LEMMAS, and 教師 / 先生
--       share no characters.
--     * the final ORDER BY is similarity DESC, so a synonym just under the
--       ceiling is not merely admitted -- it is ranked FIRST.
--
-- MEASURED (calibration_distractor_cache, 2026-09-14, top-3 served foils)
--   Anchors with a foil sharing a head gloss with the right answer:
--     ja/en 680 of 3,268 | ja/zh 395 of 3,267 | zh/en 293 of 3,680
--     zh/ja 122 of 3,681 | en/en 18 of 6,110  | zh/zh 5 of 4,041 | ja/ja 0
--   Monolingual pairs barely register because their definitions are prose
--   ("学校や塾などで、生徒に…教える人。") with no leading gloss to compare.
--   A random sample of 85 matches read by hand was overwhelmingly true
--   synonyms (降低/降低, 普通/普通, ratio/ratio, 只是/仅仅). The loosest were
--   cross-POS (to plant / plant) and generic class glosses ("a chemical
--   substance"); dropping those as foils is still correct, because the shared
--   gloss gives the answer away even when the senses differ.
--
-- DECISIONS
--   1. COMPARE THE HEAD GLOSSES, ANY OVERLAP -- not just the first gloss.
--      Cross-language definitions are "gloss; gloss — explanation". The head is
--      everything before the first em dash, split on ; ； ：. Matching only the
--      first gloss caught 354 ja/en anchors; any-overlap catches 680, and the
--      extra ones read as synonyms too (a proportion; a ratio / a ratio).
--   2. NORMALISE LIGHTLY. Lowercase, drop parentheticals, drop a leading
--      a/an/the/to, drop trailing 。.,，、. Nothing cleverer: every extra rule is
--      a way to make two different glosses collide.
--   3. ALWAYS ON, NO PARAMETER. Unlike the stem guard there is no caller that
--      wants a foil sharing the answer's gloss, and adding a parameter would
--      change the signature (DROP + re-GRANT, and a window where the cache
--      filler has no function to call).
--   4. THE GUARD IS A FILTER AFTER THE INDEX SCAN, like every other guard, so a
--      rejected candidate is replaced by the next-nearest one rather than
--      shrinking the item. See the pool CTE's comment.
--   5. NOT A SYNONYM DETECTOR. It only catches synonyms that SAY the same
--      gloss. Paraphrased synonyms ("instructor" vs "teacher") still pass; an
--      offline LLM judge over the cache is the open follow-up (TASK-777).
--
-- THE CACHE MUST BE REBUILT
--   calibration_distractor_cache is an exact copy of this function's output
--   (task773, decision 1). Changing the function without rebuilding it changes
--   nothing a learner sees. Anchors whose cached rows contain no match are
--   provably unaffected (the guard only removes rows, and every row it would
--   remove from their top 6 is already in the cache to be checked), so only
--   the affected anchors need deleting and refilling -- see Rebuild below.
--
-- CANONICAL FILE
--   This file is now canonical for semantic_distractors(). The older
--   calibration_semantic_distractors.sql is NOT archived: it is still the only
--   record of dim_distractor_bands and shared_prefix_len() (migrations/CLAUDE.md
--   rule 4).
-- =============================================================================


-- -----------------------------------------------------------------------------
-- definition_head_glosses — the normalised glosses before a definition's dash.
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.definition_head_glosses(p_definition text)
RETURNS text[]
LANGUAGE sql
IMMUTABLE
PARALLEL SAFE
AS $function$
    SELECT coalesce(array_agg(DISTINCT g), '{}'::text[])
      FROM (
        SELECT lower(
                 regexp_replace(
                   regexp_replace(btrim(part), '\s*[（(][^）)]*[）)]', '', 'g'),
                   '^(a|an|the|to)\s+|[。.,，、]+$', '', 'gi')) AS g
          FROM unnest(regexp_split_to_array(
                 -- "gloss - explanation" with a spaced hyphen counts as a dash;
                 -- an unspaced hyphen is part of a word (well-known) and does not.
                 split_part(regexp_replace(coalesce(p_definition, ''), '\s+-\s+', '—'),
                            '—', 1),
                 '[;；：]')) AS part
      ) q
     WHERE g <> '';
$function$;

COMMENT ON FUNCTION public.definition_head_glosses(text) IS
  'Normalised glosses in the head of a definition (text before the first em dash, split on ; ； ：; lowercased, parentheticals and a leading a/an/the/to removed). Used by semantic_distractors() to drop foils that share a gloss with the correct answer, i.e. synonyms that would also be correct.';


-- -----------------------------------------------------------------------------
-- semantic_distractors — unchanged except for v_anchor_glosses and guard (6).
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.semantic_distractors(
    p_sense_id               integer,
    p_word_language_id       smallint,
    p_definition_language_id smallint,
    p_count                  integer DEFAULT 3,
    p_cos_min                real    DEFAULT NULL,   -- NULL => dim_distractor_bands
    p_cos_max                real    DEFAULT NULL,   -- NULL => dim_distractor_bands
    p_freq_band              real    DEFAULT 1.0,    -- zipf points, tier-0 half-width
    p_definition_level       text    DEFAULT 'standard',
    p_pool                   integer DEFAULT 100,    -- index fetch depth
    p_exclude_stem_variants  boolean DEFAULT true
)
RETURNS TABLE(
    out_sense_id        integer,
    out_vocab_id        integer,
    out_lemma           text,
    out_definition      text,
    out_similarity      real,
    out_frequency       real,     -- zipf score, higher = more common
    out_frequency_delta real,     -- |zipf difference| from the anchor, NULL if unknown
    out_freq_tier       smallint  -- 0 in band, 1 loose or unknown, 2 out of band
)
LANGUAGE plpgsql
STABLE SECURITY DEFINER
SET search_path TO 'public', 'pg_temp'
-- hnsw.ef_search is set with set_config() in the body; plan_cache_mode keeps the
-- partial HNSW indexes matchable. Both explained in calibration_semantic_distractors.sql.
SET plan_cache_mode TO 'force_custom_plan'
AS $function$
DECLARE
    v_embedding       vector(1536);
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
    PERFORM set_config('hnsw.ef_search', v_pool::text, true);

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
        -- Pure index scan; the WHERE is exactly the partial index predicate.
        -- Every other filter belongs downstream of the LIMIT.
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

REVOKE EXECUTE ON FUNCTION public.semantic_distractors(
    integer, smallint, smallint, integer, real, real, real, text, integer, boolean) FROM anon;
GRANT EXECUTE ON FUNCTION public.semantic_distractors(
    integer, smallint, smallint, integer, real, real, real, text, integer, boolean)
    TO authenticated, service_role;


-- =============================================================================
-- Rebuild (run after applying; not part of the migration transaction)
-- =============================================================================
-- 1. Delete every definition-mode cache row of each anchor that has a match:
--      DELETE FROM calibration_distractor_cache c
--       USING dim_word_senses a
--       WHERE c.mode = 'definition'
--         AND a.id = c.anchor_sense_id
--         AND c.anchor_sense_id IN (
--               SELECT c2.anchor_sense_id
--                 FROM calibration_distractor_cache c2
--                 JOIN dim_word_senses a2 ON a2.id = c2.anchor_sense_id
--                WHERE c2.mode = 'definition'
--                  AND definition_head_glosses(c2.option_text)
--                      && definition_head_glosses(a2.definition));
--    Also clear calibration_distractor_cache_misses (task773b) —
--    calibration_clear_distractor_cache_misses() — so the bulk builder retries
--    anchors that were short before the guard changed their candidate list.
-- 2. Refill those anchors, one language pair at a time so that pair's HNSW index
--    stays resident (task773 decision 4):
--      python -m scripts.build_calibration_distractor_cache --mode definition \
--          --word-language 3 --definition-language 2
--    and likewise 3/1, 1/2, 1/3, 2/2, 1/1 (ja/ja had no matches).
--    A missed anchor is not an outage: calibration_build_items fills on a miss.
--
-- Verification -- expect 0:
--   SELECT count(*)
--     FROM calibration_distractor_cache c
--     JOIN dim_word_senses a ON a.id = c.anchor_sense_id
--    WHERE c.mode = 'definition'
--      AND definition_head_glosses(c.option_text) && definition_head_glosses(a.definition);
--
-- The 先生 item (anchor 43399, ja/en) must no longer offer 教師 (sense 56314):
--   SELECT count(*) FROM calibration_distractor_cache
--    WHERE mode = 'definition' AND anchor_sense_id = 43399 AND sense_id = 56314;
-- =============================================================================
