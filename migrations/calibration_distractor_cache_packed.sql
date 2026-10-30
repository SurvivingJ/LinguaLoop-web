-- ============================================================================
-- calibration_distractor_cache: one row per (anchor, mode), options as arrays
-- Status: PENDING (not yet applied to live). ADR-038. Vocabulary storage phase 2.
-- ============================================================================
--
-- WHY
--   Supabase Free caps the database at 500 MB; the content target is 10k zh + 10k ja
--   words with full ladders (ADR-037). Measured 2026-10-29: calibration_distractor_cache
--   was 46 MB for 211,692 rows (one row per option: 162,613 definition + 49,079
--   pronunciation, ~133 B heap + ~60 B of index each). At target scale that grows to
--   ~110 MB.
--
--   Most of each row was derivable from sense_id. Verified on all 211,692 live rows
--   (2026-10-29), 0 mismatches:
--     option_text  = dim_word_senses.definition (definition mode), or
--                    calibration_display_pronunciation(pronunciation, word_language_id)
--                    (pronunciation mode)
--     vocab_id     = dim_word_senses.vocab_id
--     frequency    = dim_vocabulary.frequency_rank
--     word_language_id / definition_language_id = the anchor row's own languages
--   and every anchor's ranks were contiguous from 0.
--
-- WHAT
--   1. Repack to ONE row per (anchor_sense_id, mode): the ranked option sense_ids, their
--      similarities (definition mode) and freq tiers / edit distances, as arrays. The
--      existing contents are carried over, so no rebuild is needed.
--   2. calibration_cached_options(mode, anchor) expands a row back into the old shape
--      (rank, sense_id, vocab_id, option_text, similarity, frequency, freq_tier), joining
--      the text and frequency live, so a corrected definition is served immediately
--      instead of the cached copy.
--   3. calibration_fill_distractor_cache() writes the packed row;
--      calibration_build_items() reads through calibration_cached_options(). Bodies are
--      otherwise unchanged from the live definitions (pg_get_functiondef, 2026-10-29).
--   4. calibration_cache_distractors_chunk() and calibration_distractor_cache_coverage()
--      only test EXISTS on (mode, anchor_sense_id), which the new table keeps, so they are
--      not redefined.
--
--   Why keep a cache at all: pronunciation_distractors() costs ~180 ms per call and
--   calibration_build_items() builds 20 items per request (TASK-770), so a cacheless
--   design would put seconds on that path.
--
-- SIZE
--   Projected ~7 MB now (33,599 rows), ~18 MB at 10k zh + 10k ja words.
--
-- LOCKING
--   The DROP/CREATE takes ACCESS EXCLUSIVE on the cache for the length of one
--   transaction (seconds). A concurrent calibration_build_items call waits for it.
--
-- ROLLBACK
--   Recreate the row-per-option table from migrations/task773_calibration_distractor_cache.sql
--   and the two function bodies from task773 / task770, then refill with
--   PYTHONPATH=. python scripts/build_calibration_distractor_cache.py
--   (the cache is derived data; nothing is lost).
--
-- NOT ARCHIVED
--   task773_calibration_distractor_cache.sql stays: it is still the only record of
--   calibration_distractor_cache_coverage(). task770_calibration_build_items.sql stays:
--   it is still the only record of calibration_discard_unanswered().
-- ============================================================================

BEGIN;

SET LOCAL statement_timeout = '600s';
SET LOCAL lock_timeout = '30s';   -- fail fast rather than queue behind a long writer

-- ---------------------------------------------------------------------------
-- 1. Pack the current contents (one row per anchor and mode, ordered by rank).
-- ---------------------------------------------------------------------------
CREATE TEMP TABLE _packed ON COMMIT DROP AS
SELECT c.anchor_sense_id,
       c.mode,
       array_agg(c.sense_id ORDER BY c.rank)                          AS sense_ids,
       CASE WHEN c.mode = 'definition'
            THEN array_agg(c.similarity ORDER BY c.rank) END          AS similarities,
       array_agg(c.freq_tier ORDER BY c.rank)                         AS freq_tiers,
       min(c.built_at)                                                AS built_at
  FROM public.calibration_distractor_cache c
 GROUP BY c.anchor_sense_id, c.mode;

DROP TABLE public.calibration_distractor_cache;

CREATE TABLE public.calibration_distractor_cache (
    anchor_sense_id integer     NOT NULL,
    mode            text        NOT NULL
        CHECK (mode IN ('definition', 'pronunciation')),
    -- Ranked options; rank = array position - 1. Never empty: an anchor whose picker
    -- finds nothing gets no row (and a calibration_distractor_cache_misses entry).
    sense_ids       integer[]   NOT NULL
        CHECK (cardinality(sense_ids) > 0),
    -- Cosine to the anchor, definition mode only (NULL in pronunciation mode).
    similarities    real[],
    -- Frequency tier in definition mode; edit distance in pronunciation mode (the same
    -- slot calibration_response_options.freq_tier records).
    freq_tiers      smallint[]  NOT NULL,
    built_at        timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (anchor_sense_id, mode),
    CHECK (cardinality(freq_tiers) = cardinality(sense_ids)),
    CHECK (similarities IS NULL OR cardinality(similarities) = cardinality(sense_ids))
);

INSERT INTO public.calibration_distractor_cache
    (anchor_sense_id, mode, sense_ids, similarities, freq_tiers, built_at)
SELECT anchor_sense_id, mode, sense_ids, similarities, freq_tiers, built_at
  FROM _packed;

COMMENT ON TABLE public.calibration_distractor_cache IS
  'DERIVED. Precomputed calibration foils, one row per (anchor sense, mode): ranked option '
  'sense_ids with their similarities and freq tiers / edit distances. Option text, vocab_id '
  'and frequency are joined live by calibration_cached_options(). Rebuild with '
  'scripts/build_calibration_distractor_cache.py after definitions or embeddings change.';

ALTER TABLE public.calibration_distractor_cache ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.calibration_distractor_cache FROM PUBLIC, anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE, TRUNCATE ON public.calibration_distractor_cache TO service_role;

-- ---------------------------------------------------------------------------
-- 2. calibration_cached_options: a packed row expanded into the old row-per-option shape.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.calibration_cached_options(
    p_mode text, p_anchor_sense_id integer)
 RETURNS TABLE(rank smallint, sense_id integer, vocab_id integer, option_text text,
               similarity real, frequency real, freq_tier smallint)
 LANGUAGE sql
 STABLE
 SET search_path = public, pg_temp
AS $function$
    SELECT (o.ord - 1)::smallint,
           s.id,
           s.vocab_id,
           CASE WHEN c.mode = 'pronunciation'
                THEN calibration_display_pronunciation(s.pronunciation, s.word_language_id)
                ELSE s.definition
           END,
           c.similarities[o.ord],
           v.frequency_rank,
           c.freq_tiers[o.ord]
      FROM calibration_distractor_cache c
     CROSS JOIN LATERAL unnest(c.sense_ids) WITH ORDINALITY AS o(sense_id, ord)
      JOIN dim_word_senses s ON s.id = o.sense_id
      JOIN dim_vocabulary  v ON v.id = s.vocab_id
     WHERE c.mode = p_mode
       AND c.anchor_sense_id = p_anchor_sense_id;
$function$;

COMMENT ON FUNCTION public.calibration_cached_options(text, integer) IS
  'Cached calibration foils for one anchor and mode, in rank order, with option text, vocab_id '
  'and frequency joined live from dim_word_senses / dim_vocabulary. A foil whose sense row was '
  'deleted drops out rather than erroring.';

REVOKE ALL ON FUNCTION public.calibration_cached_options(text, integer) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.calibration_cached_options(text, integer) TO service_role;

-- ---------------------------------------------------------------------------
-- 3. calibration_fill_distractor_cache: write one packed row.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.calibration_fill_distractor_cache(
    p_anchor_sense_id integer, p_word_language_id smallint,
    p_definition_language_id smallint, p_mode text DEFAULT 'definition'::text)
 RETURNS integer
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public', 'pg_temp'
AS $function$
DECLARE
    v_existing integer;
BEGIN
    IF auth.role() NOT IN ('authenticated', 'service_role') THEN
        RAISE EXCEPTION 'Authentication required' USING ERRCODE = '42501';
    END IF;

    SELECT cardinality(c.sense_ids) INTO v_existing
      FROM calibration_distractor_cache c
     WHERE c.mode = p_mode AND c.anchor_sense_id = p_anchor_sense_id;

    IF v_existing > 0 THEN
        RETURN v_existing;
    END IF;

    IF p_mode = 'pronunciation' THEN
        INSERT INTO calibration_distractor_cache (
            anchor_sense_id, mode, sense_ids, similarities, freq_tiers)
        SELECT p_anchor_sense_id, 'pronunciation',
               array_agg(d.out_sense_id ORDER BY d.ord),
               NULL,
               array_agg(d.out_distance::smallint ORDER BY d.ord)
          FROM pronunciation_distractors(p_anchor_sense_id, p_word_language_id, 8)
               WITH ORDINALITY AS d(out_sense_id, out_vocab_id, out_lemma,
                                    out_pronunciation, out_distance, out_frequency, ord)
         WHERE d.out_pronunciation IS NOT NULL
           AND btrim(d.out_pronunciation) <> ''
        HAVING count(*) > 0
        ON CONFLICT DO NOTHING;
    ELSE
        INSERT INTO calibration_distractor_cache (
            anchor_sense_id, mode, sense_ids, similarities, freq_tiers)
        SELECT p_anchor_sense_id, 'definition',
               array_agg(d.out_sense_id ORDER BY d.ord),
               array_agg(d.out_similarity ORDER BY d.ord),
               array_agg(d.out_freq_tier ORDER BY d.ord)
          FROM semantic_distractors(p_anchor_sense_id, p_word_language_id,
                                    p_definition_language_id, 6)
               WITH ORDINALITY AS d(out_sense_id, out_vocab_id, out_lemma, out_definition,
                                    out_similarity, out_frequency, out_frequency_delta,
                                    out_freq_tier, ord)
         WHERE d.out_definition IS NOT NULL
           AND btrim(d.out_definition) <> ''
        HAVING count(*) > 0
        ON CONFLICT DO NOTHING;
    END IF;

    SELECT coalesce(cardinality(c.sense_ids), 0) INTO v_existing
      FROM calibration_distractor_cache c
     WHERE c.mode = p_mode AND c.anchor_sense_id = p_anchor_sense_id;

    RETURN coalesce(v_existing, 0);
END;
$function$;

REVOKE ALL ON FUNCTION public.calibration_fill_distractor_cache(integer, smallint, smallint, text)
    FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.calibration_fill_distractor_cache(integer, smallint, smallint, text)
    TO service_role;

-- ---------------------------------------------------------------------------
-- 4. calibration_build_items: read the cache through calibration_cached_options().
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.calibration_build_items(
    p_session_id uuid, p_user_id uuid, p_word_language_id smallint,
    p_definition_language_id smallint, p_mode text DEFAULT 'definition'::text,
    p_count integer DEFAULT 1, p_max_fill integer DEFAULT 4)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public', 'pg_temp'
AS $function$
DECLARE
    v_anchor       record;
    v_need_pron    boolean := (p_mode = 'pronunciation');
    v_count        integer := LEAST(GREATEST(COALESCE(p_count, 1), 1), 25);
    v_max_fill     integer := GREATEST(COALESCE(p_max_fill, 4), 0);
    v_slack        integer;
    v_key          text;
    v_have         integer;
    v_response_id  bigint;
    v_options      jsonb;
    v_items        jsonb := '[]'::jsonb;
    v_built        integer := 0;
    v_skipped      integer := 0;
    v_fills        integer := 0;
    v_anchors_seen integer := 0;
BEGIN
    IF auth.role() NOT IN ('authenticated', 'service_role') THEN
        RAISE EXCEPTION 'Authentication required' USING ERRCODE = '42501';
    END IF;

    v_slack := LEAST(CEIL(v_count * 1.4)::integer + 3, 50);

    FOR v_anchor IN
        SELECT * FROM calibration_next_anchors(
            p_session_id, p_word_language_id, p_definition_language_id,
            p_mode, v_slack)
    LOOP
        v_anchors_seen := v_anchors_seen + 1;
        EXIT WHEN v_built >= v_count;

        v_key := CASE WHEN v_need_pron THEN v_anchor.out_pronunciation
                      ELSE v_anchor.out_definition END;
        IF v_key IS NULL OR btrim(v_key) = '' THEN
            v_skipped := v_skipped + 1;
            CONTINUE;
        END IF;

        SELECT count(*) INTO v_have
          FROM calibration_cached_options(p_mode, v_anchor.out_sense_id) c
         WHERE btrim(c.option_text) <> btrim(v_key);

        IF v_have < 3 AND v_fills < v_max_fill THEN
            PERFORM calibration_fill_distractor_cache(
                v_anchor.out_sense_id, p_word_language_id,
                p_definition_language_id, p_mode);
            v_fills := v_fills + 1;

            SELECT count(*) INTO v_have
              FROM calibration_cached_options(p_mode, v_anchor.out_sense_id) c
             WHERE btrim(c.option_text) <> btrim(v_key);
        END IF;

        IF v_have < 3 THEN
            v_skipped := v_skipped + 1;
            CONTINUE;
        END IF;

        INSERT INTO calibration_responses (
            session_id, user_id, anchor_sense_id, anchor_vocab_id,
            anchor_zipf, zipf_band)
        VALUES (p_session_id, p_user_id, v_anchor.out_sense_id,
                v_anchor.out_vocab_id, v_anchor.out_zipf, v_anchor.out_zipf_band)
        RETURNING id INTO v_response_id;

        WITH picked AS (
            SELECT c.sense_id, c.vocab_id, c.option_text,
                   c.similarity, c.frequency, c.freq_tier
              FROM calibration_cached_options(p_mode, v_anchor.out_sense_id) c
             WHERE btrim(c.option_text) <> btrim(v_key)
             ORDER BY (CASE WHEN v_need_pron THEN random()
                            ELSE c.rank::double precision END)
             LIMIT 3
        ),
        opts AS (
            SELECT v_anchor.out_sense_id AS sense_id,
                   v_anchor.out_vocab_id AS vocab_id,
                   v_key                 AS option_text,
                   true                  AS is_key,
                   NULL::real            AS similarity,
                   v_anchor.out_zipf     AS frequency,
                   NULL::smallint        AS freq_tier
            UNION ALL
            SELECT p.sense_id, p.vocab_id, p.option_text, false,
                   p.similarity, p.frequency, p.freq_tier
              FROM picked p
        ),
        placed AS MATERIALIZED (
            SELECT o.*,
                   (row_number() OVER (ORDER BY random()) - 1)::smallint AS position
              FROM opts o
        ),
        ins AS (
            INSERT INTO calibration_response_options (
                response_id, sense_id, vocab_id, is_key, position,
                similarity, frequency, freq_tier)
            SELECT v_response_id, pl.sense_id, pl.vocab_id, pl.is_key,
                   pl.position, pl.similarity, pl.frequency, pl.freq_tier
              FROM placed pl
            RETURNING 1
        )
        SELECT jsonb_agg(jsonb_build_object('position', pl.position,
                                            'definition', pl.option_text)
                         ORDER BY pl.position)
          INTO v_options
          FROM placed pl;

        v_items := v_items || jsonb_build_array(jsonb_build_object(
            'response_id', v_response_id,
            'lemma',       v_anchor.out_lemma,
            'pronunciation', CASE WHEN v_need_pron THEN NULL
                                  ELSE v_anchor.out_pronunciation END,
            'zipf_band',   v_anchor.out_zipf_band,
            'mode',        p_mode,
            'options',     v_options
        ));
        v_built := v_built + 1;
    END LOOP;

    IF v_built > 0 THEN
        UPDATE calibration_sessions
           SET items_served = items_served + v_built
         WHERE id = p_session_id;
    END IF;

    RETURN jsonb_build_object(
        'items',   v_items,
        'built',   v_built,
        'skipped', v_skipped,
        'filled',  v_fills,
        'exhausted', (v_anchors_seen = 0)
    );
END;
$function$;

REVOKE ALL ON FUNCTION public.calibration_build_items(uuid, uuid, smallint, smallint, text, integer, integer)
    FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.calibration_build_items(uuid, uuid, smallint, smallint, text, integer, integer)
    TO service_role;

COMMIT;

-- ---------------------------------------------------------------------------
-- Post-apply checks
-- ---------------------------------------------------------------------------
-- SELECT pg_size_pretty(pg_total_relation_size('calibration_distractor_cache'));  -- expect ~7 MB
-- SELECT mode, count(*), sum(cardinality(sense_ids)) FROM calibration_distractor_cache
--  GROUP BY 1;                       -- expect definition 27,305 / 162,613; pronunciation 6,294 / 49,079
-- SELECT * FROM calibration_cached_options('definition', <anchor_sense_id>);
-- SELECT * FROM calibration_distractor_cache_coverage();   -- unchanged
