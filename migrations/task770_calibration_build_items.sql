-- TASK-770 — Calibration: build a whole batch of items in one round trip.
-- =============================================================================
-- DEPENDS ON: TASK-772 (calibration_anchor_pool, calibration_next_anchors)
--             TASK-773 (calibration_distractor_cache)
--
-- PROBLEM
--   /next cost ~1.8-2.1 s per item and sat between every answer and the next
--   word. Measured on 2026-09-13, seven sequential Supabase calls:
--
--     auth.get_user                65 ms
--     SELECT calibration_sessions  65 ms
--     calibration_next_anchor      65 + 202-565 ms
--     semantic_distractors         65 + ~1100 ms  (cold; see TASK-773)
--     INSERT calibration_responses 65 ms
--     INSERT ..._response_options  65 ms
--     UPDATE calibration_sessions  65 ms
--
--   TASK-772 and TASK-773 removed the two slow RPCs. What is left is still six
--   round trips PER ITEM, which is ~390 ms of network to hand the learner one
--   four-option question. Prefetching twenty items the old way would be 120
--   round trips.
--
-- DECISIONS
--
--   1. ONE CALL BUILDS N ITEMS.
--      Anchor selection, distractor lookup, both inserts, the option shuffle and
--      the served counter happen inside this function. A 20-item prefetch is one
--      request. This is what makes TASK-771's client-side queue affordable.
--
--   2. THE SHUFFLE MOVES INTO SQL, AND IS MATERIALIZED.
--      Option order was `random.shuffle` in Python. Here it is
--      `row_number() OVER (ORDER BY random())`. The CTE that does it is declared
--      MATERIALIZED, and that word is load-bearing: the same CTE feeds both the
--      INSERT of the stored options and the JSON returned to the client. If it
--      were evaluated twice, random() would deal a different order each time and
--      the client would render the options at positions the database does not
--      agree with — every answer would then be graded against the wrong option.
--
--   3. ANCHORS ARE OVER-FETCHED, AND A SHORT ANCHOR IS SKIPPED, NOT PADDED.
--      We ask calibration_next_anchors for ~1.4x the items wanted. Any anchor
--      whose cache cannot supply three usable foils is skipped and the next one
--      used, so a skip costs nothing.
--
--      This RETIRES the get_distractors() random-foil fallback for calibration.
--      That fallback existed because the singular builder had no second chance:
--      with one anchor in hand it either padded the item or failed. Its own
--      comment called it "a real quality drop — random foils make an item
--      answerable by elimination", and the pronunciation path already refused to
--      do it ("Better to skip the anchor"). A batch builder always has a second
--      chance, so the two modes now agree: an item is built from real foils or
--      it is not built. Measured rate at which this bites: 1 anchor in ~1,400.
--
--   4. A COLD CACHE IS FILLED, BUT AT MOST p_max_fill TIMES PER CALL.
--      A miss costs ~1.1 s (TASK-773). Uncapped, a batch of 20 against an
--      unbuilt cache would be a 22-second request. The cap bounds the worst case
--      at ~4.5 s; anchors past it are skipped and will be filled by the bulk
--      builder or a later call. With the cache built ahead, no call fills at all.
--
--   5. THE KEY IS STILL NEVER SENT TO THE CLIENT.
--      The returned options carry `position` and text and nothing else, exactly
--      as the singular builder did. Prefetching more items does not mean
--      prefetching more answers: the learner still only learns which option was
--      right by submitting one. This is the property that lets calibration's
--      output be trusted by the rating writer (ADR-024 §4/§5), so it survives
--      the optimisation unchanged.
--
--   6. items_served IS INCREMENTED BY WHAT WAS ACTUALLY BUILT.
--      Prefetched items the learner never reaches stay is_correct NULL and are
--      excluded from every estimate (_fit_points already filters them).
--      calibration_discard_unanswered() at /end removes them, so an abandoned
--      prefetch does not leave the anchor permanently "already seen".
--
-- CONSEQUENCES
--   20 items in one request instead of 120 round trips. With the cache warm the
--   whole call is one anchor query plus 20 small index lookups and two inserts.
-- =============================================================================

CREATE OR REPLACE FUNCTION public.calibration_build_items(
    p_session_id             uuid,
    p_user_id                uuid,
    p_word_language_id       smallint,
    p_definition_language_id smallint,
    p_mode                   text    DEFAULT 'definition',
    p_count                  integer DEFAULT 1,
    p_max_fill               integer DEFAULT 4
)
RETURNS jsonb
LANGUAGE plpgsql
VOLATILE
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

    -- Enough spare anchors that the expected number of skips cannot shorten the
    -- batch, without asking for so many that a long tail is selected for nothing.
    v_slack := LEAST(CEIL(v_count * 1.4)::integer + 3, 50);

    FOR v_anchor IN
        SELECT * FROM calibration_next_anchors(
            p_session_id, p_word_language_id, p_definition_language_id,
            p_mode, v_slack)
    LOOP
        v_anchors_seen := v_anchors_seen + 1;
        EXIT WHEN v_built >= v_count;

        -- In pronunciation mode the reading IS the answer; in definition mode
        -- the definition is.
        v_key := CASE WHEN v_need_pron THEN v_anchor.out_pronunciation
                      ELSE v_anchor.out_definition END;
        IF v_key IS NULL OR btrim(v_key) = '' THEN
            v_skipped := v_skipped + 1;
            CONTINUE;
        END IF;

        -- A foil whose text matches the key would make the item unanswerable, so
        -- it is excluded here and not counted toward the three needed.
        SELECT count(*) INTO v_have
          FROM calibration_distractor_cache c
         WHERE c.mode = p_mode
           AND c.anchor_sense_id = v_anchor.out_sense_id
           AND btrim(c.option_text) <> btrim(v_key);

        IF v_have < 3 AND v_fills < v_max_fill THEN
            PERFORM calibration_fill_distractor_cache(
                v_anchor.out_sense_id, p_word_language_id,
                p_definition_language_id, p_mode);
            v_fills := v_fills + 1;

            SELECT count(*) INTO v_have
              FROM calibration_distractor_cache c
             WHERE c.mode = p_mode
               AND c.anchor_sense_id = v_anchor.out_sense_id
               AND btrim(c.option_text) <> btrim(v_key);
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
              FROM calibration_distractor_cache c
             WHERE c.mode = p_mode
               AND c.anchor_sense_id = v_anchor.out_sense_id
               AND btrim(c.option_text) <> btrim(v_key)
             -- Definition mode takes the picker's own order, which is the whole
             -- point of caching it. Pronunciation mode samples, because its
             -- picker is random and freezing three foils would remove variety.
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
            -- MATERIALIZED is required, not stylistic: see decision 2.
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
            -- Withheld in pronunciation mode: the reading is the answer, so it
            -- must not also be printed under the prompt.
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
        -- TRUE only when the language pair has nothing left to ask about. A
        -- batch that built nothing because every candidate was skipped is NOT
        -- exhaustion, and is reported by built = 0 instead.
        'exhausted', (v_anchors_seen = 0)
    );
END;
$function$;

COMMENT ON FUNCTION public.calibration_build_items(uuid, uuid, smallint, smallint, text, integer, integer) IS
'TASK-770. Builds up to p_count calibration items in one round trip: selects
anchors, reads cached distractors, persists the served items and their shuffled
options, and returns the items WITHOUT the key. Skips anchors that cannot supply
three real foils rather than padding them with random ones.';

REVOKE ALL ON FUNCTION public.calibration_build_items(uuid, uuid, smallint, smallint, text, integer, integer) FROM public;
GRANT EXECUTE ON FUNCTION public.calibration_build_items(uuid, uuid, smallint, smallint, text, integer, integer)
    TO authenticated, service_role;


-- ---------------------------------------------------------------------------
-- Housekeeping for prefetch: drop items that were served but never answered.
--
-- Without this, every abandoned prefetch leaves rows that make their anchors
-- permanently "already seen" for that session and inflate items_served. They
-- never affected an estimate — _fit_points and calibration_ability both require
-- is_correct IS NOT NULL — so this is tidiness, not correctness.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.calibration_discard_unanswered(
    p_session_id uuid,
    p_user_id    uuid
)
RETURNS integer
LANGUAGE plpgsql
VOLATILE
SECURITY DEFINER
SET search_path TO 'public', 'pg_temp'
AS $function$
DECLARE
    v_deleted integer;
BEGIN
    IF auth.role() NOT IN ('authenticated', 'service_role') THEN
        RAISE EXCEPTION 'Authentication required' USING ERRCODE = '42501';
    END IF;

    DELETE FROM calibration_response_options o
     USING calibration_responses r
     WHERE o.response_id = r.id
       AND r.session_id  = p_session_id
       AND r.user_id     = p_user_id
       AND r.is_correct IS NULL;

    DELETE FROM calibration_responses r
     WHERE r.session_id = p_session_id
       AND r.user_id    = p_user_id
       AND r.is_correct IS NULL;

    GET DIAGNOSTICS v_deleted = ROW_COUNT;

    UPDATE calibration_sessions s
       SET items_served = GREATEST(s.items_served - v_deleted, s.items_answered)
     WHERE s.id = p_session_id
       AND s.user_id = p_user_id;

    RETURN v_deleted;
END;
$function$;

COMMENT ON FUNCTION public.calibration_discard_unanswered(uuid, uuid) IS
'TASK-770. Deletes a session''s served-but-unanswered items and corrects
items_served. Called at /end so an abandoned prefetch leaves no trace.';

REVOKE ALL ON FUNCTION public.calibration_discard_unanswered(uuid, uuid) FROM public;
GRANT EXECUTE ON FUNCTION public.calibration_discard_unanswered(uuid, uuid)
    TO authenticated, service_role;
