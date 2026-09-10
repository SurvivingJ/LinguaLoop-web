-- Calibration Phase 2 — session storage, anchor selection, ability estimate.
-- =============================================================================
-- PROBLEM
--   Phase 1 built the distractor picker. Nothing yet serves an item, records an
--   answer, or turns answers into a number. Three things have to be decided, not
--   just coded:
--
--   1. WHAT DOES CALIBRATION OUTPUT? A single "score" out of nothing is not
--      actionable and not comparable across languages.
--   2. WHICH WORD DO WE ASK NEXT? Asking random words measures an average, and an
--      average is the one statistic that cannot tell you where a learner's
--      knowledge stops.
--   3. WHAT DO WE STORE? ADR-025 states plainly that the only way to catch a
--      distractor that is secretly a second correct answer is response data. If
--      we record only "right/wrong", that evidence is destroyed at write time.
--
-- DECISIONS
--
--   1. THE OUTPUT IS A ZIPF KNOWLEDGE CURVE, NOT A SCORE.
--      Every anchor carries dim_vocabulary.frequency_rank — a ZIPF SCORE (higher
--      = more common; the column name is a misnomer, see
--      services/vocabulary_ladder/deterministic/lexicon.py:266). Bucketing answers
--      by Zipf band gives known-share as a function of word frequency, and the
--      interesting number is where that curve CROSSES a threshold.
--
--      This is deliberately the same statistic the vocabulary-aware-test-selection
--      work is blocked on. ADR-024 §1.2 needs `ability_zipf` defined as "the
--      Zipf at which known-share crosses 1 - u* (85%)", and the wiki log records
--      that the definition alone swings the result 430 ELO points — so it must be
--      MEASURED, not assumed. Calibration is the instrument that measures it.
--      calibration_ability() returns the 85% crossing and the 50% crossing, plus
--      the per-band counts they were derived from, so the caller can see the
--      evidence and not just the answer.
--
--   2. ANCHORS ARE STRATIFIED ACROSS ZIPF BANDS, NOT SAMPLED AT RANDOM.
--      To locate a crossing you need points on BOTH sides of it. Uniform random
--      sampling concentrates items wherever the dictionary happens to be dense and
--      can leave a band empty, which makes the crossing uninterpolatable.
--      calibration_next_anchor() therefore serves the band with the fewest items
--      answered so far in this session (random tie-break), which sweeps the curve
--      evenly and degrades gracefully when a band runs dry.
--
--   3. EVERY OPTION SHOWN IS STORED, NOT JUST THE CHOSEN ONE.
--      calibration_response_options keeps one row per rendered option with its
--      cosine similarity and frequency tier. This is what makes the also-correct
--      analysis in ADR-025 / TASK-763 possible later: a distractor that strong
--      learners pick as often as the key IS a second right answer, and that is only
--      visible if the un-chosen options were recorded too.
--
--   4. CALIBRATION DOES NOT WRITE BACK TO ELO OR STUDY PLANNING.
--      It is a measuring instrument and is explicitly outside session planning. It
--      writes only its own tables. Feeding `ability_zipf` into test selection is
--      TASK-748's (selection) and TASK-747's (the guarded rating writer) to make
--      with their own guards (ADR-024 is emphatic that
--      seeding ratings needs hard guards), and a measurement that silently moved
--      the thing it measures would be a feedback loop, not a calibration.
--      Consequently there is no sentinel test row and no process_*_submission call
--      here — unlike classifier_drill, which is deliberately plannable.
--
--   5. THE ANCHOR BLOCKLIST.
--      TASK-757 found dictionary rows whose definition does not define the lemma
--      (sense 14968 is `hand` defined as "Closely connected or associated with
--      something else" — that is *hand in hand*). No picker can rescue such an
--      item. calibration_anchor_blocklist lets those be suppressed from
--      Calibration immediately, without blocking on the upstream dictionary fix
--      and without inventing a column on dim_word_senses for one consumer.
--
-- SAFETY
--   - Additive: four new tables, three new functions. Nothing existing is touched.
--   - Idempotent (CREATE TABLE / CREATE INDEX IF NOT EXISTS, CREATE OR REPLACE).
--   - RLS on all four tables; a user reads only their own rows. The service role
--     (which the Flask layer uses) bypasses RLS as it does everywhere else.
--   - calibration_next_anchor() and calibration_ability() are STABLE and read-only.
--
-- APPLIED LIVE: 2026-09-08
--
-- SUPERSEDED IN PART — read before trusting anything below
--   * calibration_next_anchor() is redefined by
--     migrations/calibration_pronunciation_mode.sql, which adds a p_mode
--     parameter and DROPS this 3-argument signature. That file is canonical for
--     this function; the version below is history.
--   * calibration_ability() is still live and still the source of the per-band
--     curve, but its `ability_zipf_85` / `ability_zipf_50` outputs are NO LONGER
--     USED. They were piecewise-linear interpolations between band midpoints and
--     were measured biased high by ~+0.24 Zipf (TASK-764). The crossings are now
--     computed by maximum likelihood in
--     services/calibration_service._fit_ability(), which overwrites both fields
--     on every call. Do not reintroduce a caller that reads them from SQL.
--   This file is kept, not archived: it is the only repo record of the four
--   calibration tables, calibration_zipf_band() and calibration_band_midpoint().
-- =============================================================================


-- -----------------------------------------------------------------------------
-- Zipf bands. One definition, used by both the sampler and the estimator, so the
-- curve is always reported on the same axis it was sampled on.
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.calibration_zipf_band(p_zipf real)
RETURNS smallint
LANGUAGE sql
IMMUTABLE
PARALLEL SAFE
AS $function$
    SELECT CASE
        WHEN p_zipf IS NULL  THEN NULL
        WHEN p_zipf <  3.0   THEN 1::smallint
        WHEN p_zipf <  3.5   THEN 2::smallint
        WHEN p_zipf <  4.0   THEN 3::smallint
        WHEN p_zipf <  4.5   THEN 4::smallint
        WHEN p_zipf <  5.0   THEN 5::smallint
        WHEN p_zipf <  5.5   THEN 6::smallint
        ELSE                      7::smallint
    END;
$function$;

-- Band midpoints, for interpolating a crossing. Band 1 and 7 are open-ended, so
-- their midpoints are the observed corpus edges rather than half of infinity.
CREATE OR REPLACE FUNCTION public.calibration_band_midpoint(p_band smallint)
RETURNS real
LANGUAGE sql
IMMUTABLE
PARALLEL SAFE
AS $function$
    SELECT CASE p_band
        WHEN 1 THEN 2.75::real
        WHEN 2 THEN 3.25::real
        WHEN 3 THEN 3.75::real
        WHEN 4 THEN 4.25::real
        WHEN 5 THEN 4.75::real
        WHEN 6 THEN 5.25::real
        WHEN 7 THEN 5.75::real
    END;
$function$;


-- -----------------------------------------------------------------------------
-- Storage
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.calibration_sessions (
    id                      uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id                 uuid     NOT NULL,
    word_language_id        smallint NOT NULL REFERENCES public.dim_languages(id),
    definition_language_id  smallint NOT NULL REFERENCES public.dim_languages(id),
    started_at              timestamptz NOT NULL DEFAULT now(),
    ended_at                timestamptz,
    items_served            integer  NOT NULL DEFAULT 0,
    items_answered          integer  NOT NULL DEFAULT 0,
    items_correct           integer  NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_calibration_sessions_user
    ON public.calibration_sessions (user_id, started_at DESC);

CREATE TABLE IF NOT EXISTS public.calibration_responses (
    id              bigserial PRIMARY KEY,
    session_id      uuid NOT NULL REFERENCES public.calibration_sessions(id) ON DELETE CASCADE,
    user_id         uuid NOT NULL,
    anchor_sense_id integer NOT NULL REFERENCES public.dim_word_senses(id),
    anchor_vocab_id integer NOT NULL,
    anchor_zipf     real,
    zipf_band       smallint,
    -- NULL = served but never answered (the learner quit on this item). Kept
    -- rather than deleted: an abandoned item is weak evidence of difficulty, and
    -- silently dropping it would bias the curve upward.
    chosen_sense_id integer,
    is_correct      boolean,
    latency_ms      integer,
    served_at       timestamptz NOT NULL DEFAULT now(),
    answered_at     timestamptz
);

CREATE INDEX IF NOT EXISTS idx_calibration_responses_session
    ON public.calibration_responses (session_id, served_at);
CREATE INDEX IF NOT EXISTS idx_calibration_responses_anchor
    ON public.calibration_responses (anchor_sense_id);

-- One row per option actually rendered. See decision 3.
CREATE TABLE IF NOT EXISTS public.calibration_response_options (
    response_id  bigint   NOT NULL REFERENCES public.calibration_responses(id) ON DELETE CASCADE,
    sense_id     integer  NOT NULL,
    vocab_id     integer  NOT NULL,
    is_key       boolean  NOT NULL,
    position     smallint NOT NULL,
    similarity   real,      -- NULL for the key: it is not a distractor of itself
    frequency    real,      -- zipf score
    freq_tier    smallint,
    was_chosen   boolean  NOT NULL DEFAULT false,
    PRIMARY KEY (response_id, sense_id)
);

-- The also-correct query in TASK-763 reads this: "which non-key options get
-- picked, and by whom".
CREATE INDEX IF NOT EXISTS idx_calibration_options_chosen_distractors
    ON public.calibration_response_options (sense_id)
    WHERE was_chosen AND NOT is_key;

CREATE TABLE IF NOT EXISTS public.calibration_anchor_blocklist (
    sense_id    integer PRIMARY KEY REFERENCES public.dim_word_senses(id) ON DELETE CASCADE,
    reason      text NOT NULL,
    added_at    timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE public.calibration_anchor_blocklist IS
  'Senses that must never be used as a Calibration prompt. Seeded from TASK-757: dictionary rows whose definition does not define the bare lemma (e.g. sense 14968, lemma "hand", defined as "Closely connected or associated with something else" — that defines *hand in hand*). No distractor picker can rescue such an item.';


-- -----------------------------------------------------------------------------
-- RLS — a learner sees only their own calibration data.
-- -----------------------------------------------------------------------------
ALTER TABLE public.calibration_sessions          ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.calibration_responses         ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.calibration_response_options  ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.calibration_anchor_blocklist  ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS calibration_sessions_own ON public.calibration_sessions;
CREATE POLICY calibration_sessions_own ON public.calibration_sessions
    FOR ALL TO authenticated USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS calibration_responses_own ON public.calibration_responses;
CREATE POLICY calibration_responses_own ON public.calibration_responses
    FOR ALL TO authenticated USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS calibration_options_own ON public.calibration_response_options;
CREATE POLICY calibration_options_own ON public.calibration_response_options
    FOR ALL TO authenticated
    USING (EXISTS (SELECT 1 FROM public.calibration_responses r
                    WHERE r.id = response_id AND r.user_id = auth.uid()))
    WITH CHECK (EXISTS (SELECT 1 FROM public.calibration_responses r
                    WHERE r.id = response_id AND r.user_id = auth.uid()));

DROP POLICY IF EXISTS calibration_blocklist_read ON public.calibration_anchor_blocklist;
CREATE POLICY calibration_blocklist_read ON public.calibration_anchor_blocklist
    FOR SELECT TO authenticated USING (true);

GRANT SELECT, INSERT, UPDATE ON public.calibration_sessions          TO authenticated, service_role;
GRANT SELECT, INSERT, UPDATE ON public.calibration_responses         TO authenticated, service_role;
GRANT SELECT, INSERT, UPDATE ON public.calibration_response_options  TO authenticated, service_role;
GRANT SELECT                 ON public.calibration_anchor_blocklist  TO authenticated, service_role;
GRANT USAGE, SELECT ON SEQUENCE public.calibration_responses_id_seq  TO authenticated, service_role;


-- -----------------------------------------------------------------------------
-- calibration_next_anchor — stratified anchor selection. See decision 2.
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.calibration_next_anchor(
    p_session_id             uuid,
    p_word_language_id       smallint,
    p_definition_language_id smallint
)
RETURNS TABLE(
    out_sense_id    integer,
    out_vocab_id    integer,
    out_lemma       text,
    out_definition  text,
    out_pronunciation text,
    out_zipf        real,
    out_zipf_band   smallint
)
LANGUAGE plpgsql
STABLE SECURITY DEFINER
SET search_path TO 'public', 'pg_temp'
AS $function$
DECLARE
    v_target_band smallint;
BEGIN
    IF auth.role() NOT IN ('authenticated', 'service_role') THEN
        RAISE EXCEPTION 'Authentication required' USING ERRCODE = '42501';
    END IF;

    -- The band this session has the least evidence about, preferring bands that
    -- still have unseen anchors. Random tie-break so two sessions do not walk the
    -- dictionary in the same order.
    SELECT b.band INTO v_target_band
    FROM (SELECT generate_series(1, 7)::smallint AS band) b
    LEFT JOIN (
        SELECT zipf_band, count(*) AS served
        FROM calibration_responses
        WHERE session_id = p_session_id
        GROUP BY zipf_band
    ) r ON r.zipf_band = b.band
    WHERE EXISTS (
        SELECT 1
        FROM dim_word_senses s
        JOIN dim_vocabulary v ON v.id = s.vocab_id
        WHERE s.word_language_id       = p_word_language_id
          AND s.definition_language_id = p_definition_language_id
          AND s.definition_level = 'standard'
          AND s.embedding IS NOT NULL
          AND v.frequency_rank IS NOT NULL
          AND calibration_zipf_band(v.frequency_rank) = b.band
          AND NOT EXISTS (SELECT 1 FROM calibration_anchor_blocklist bl WHERE bl.sense_id = s.id)
          AND NOT EXISTS (SELECT 1 FROM calibration_responses cr
                           WHERE cr.session_id = p_session_id AND cr.anchor_sense_id = s.id)
    )
    ORDER BY coalesce(r.served, 0), random()
    LIMIT 1;

    IF v_target_band IS NULL THEN
        RETURN;   -- every band exhausted for this session
    END IF;

    RETURN QUERY
    SELECT s.id, s.vocab_id, v.lemma, s.definition, s.pronunciation,
           v.frequency_rank, calibration_zipf_band(v.frequency_rank)
      FROM dim_word_senses s
      JOIN dim_vocabulary v ON v.id = s.vocab_id
     WHERE s.word_language_id       = p_word_language_id
       AND s.definition_language_id = p_definition_language_id
       AND s.definition_level = 'standard'
       AND s.embedding IS NOT NULL
       AND v.frequency_rank IS NOT NULL
       AND calibration_zipf_band(v.frequency_rank) = v_target_band
       AND NOT EXISTS (SELECT 1 FROM calibration_anchor_blocklist bl WHERE bl.sense_id = s.id)
       AND NOT EXISTS (SELECT 1 FROM calibration_responses cr
                        WHERE cr.session_id = p_session_id AND cr.anchor_sense_id = s.id)
     ORDER BY random()
     LIMIT 1;
END;
$function$;

REVOKE EXECUTE ON FUNCTION public.calibration_next_anchor(uuid, smallint, smallint) FROM anon;
GRANT EXECUTE ON FUNCTION public.calibration_next_anchor(uuid, smallint, smallint)
    TO authenticated, service_role;


-- -----------------------------------------------------------------------------
-- calibration_ability — the curve, and where it crosses. See decision 1.
-- -----------------------------------------------------------------------------
-- Returns JSONB:
--   { "answered": int, "correct": int,
--     "bands": [ {band, zipf_mid, n, correct, known_share}, ... ],
--     "ability_zipf_85": real|null,     -- the ADR-024 §1.2 contract
--     "ability_zipf_50": real|null,     -- the crossover
--     "confidence": "none"|"low"|"medium"|"good" }
--
-- Crossings are linearly interpolated between adjacent band midpoints, walking
-- from the COMMON end (band 7) downward — known-share is monotonically decreasing
-- in rarity, so the first downward crossing is the meaningful one. Bands with
-- fewer than p_min_band_n answers are skipped rather than trusted: a single
-- lucky guess in an empty band would otherwise move the estimate by half a Zipf
-- point. NULL is returned when the curve never crosses within the sampled range —
-- an honest "not measured yet" rather than an extrapolated number.
CREATE OR REPLACE FUNCTION public.calibration_ability(
    p_session_id    uuid,
    p_min_band_n    integer DEFAULT 3
)
RETURNS jsonb
LANGUAGE plpgsql
STABLE SECURITY DEFINER
SET search_path TO 'public', 'pg_temp'
AS $function$
DECLARE
    v_bands      jsonb;
    v_answered   integer;
    v_correct    integer;
    v_85         real;
    v_50         real;
    v_confidence text;
    v_usable     integer;
BEGIN
    IF auth.role() NOT IN ('authenticated', 'service_role') THEN
        RAISE EXCEPTION 'Authentication required' USING ERRCODE = '42501';
    END IF;

    WITH b AS (
        SELECT r.zipf_band AS band,
               calibration_band_midpoint(r.zipf_band) AS zipf_mid,
               count(*)::int AS n,
               (count(*) FILTER (WHERE r.is_correct))::int AS correct,
               (count(*) FILTER (WHERE r.is_correct))::real / nullif(count(*), 0) AS known_share
          FROM calibration_responses r
         WHERE r.session_id = p_session_id
           AND r.is_correct IS NOT NULL
           AND r.zipf_band IS NOT NULL
         GROUP BY r.zipf_band
    )
    SELECT
      coalesce(sum(n), 0)::int,
      coalesce(sum(correct), 0)::int,
      coalesce(jsonb_agg(jsonb_build_object(
          'band', band, 'zipf_mid', zipf_mid, 'n', n,
          'correct', correct, 'known_share', round(known_share::numeric, 3)
      ) ORDER BY band), '[]'::jsonb),
      count(*) FILTER (WHERE n >= p_min_band_n)::int
    INTO v_answered, v_correct, v_bands, v_usable
    FROM b;

    -- Both crossings in one pass. Walking from the COMMON end downward matters:
    -- known-share decreases with rarity, so the first downward crossing is the
    -- meaningful one. Bands under p_min_band_n are excluded from BOTH ends of the
    -- interpolation, so one lucky guess in a thin band cannot move the estimate.
    WITH b AS (
        SELECT r.zipf_band AS band,
               calibration_band_midpoint(r.zipf_band) AS zipf_mid,
               count(*)::int AS n,
               (count(*) FILTER (WHERE r.is_correct))::real / nullif(count(*), 0) AS known_share
          FROM calibration_responses r
         WHERE r.session_id = p_session_id
           AND r.is_correct IS NOT NULL
           AND r.zipf_band IS NOT NULL
         GROUP BY r.zipf_band
    )
    SELECT
      (SELECT CASE WHEN hi.known_share = lo.known_share THEN lo.zipf_mid
                   ELSE lo.zipf_mid + (0.85 - lo.known_share)
                        * (hi.zipf_mid - lo.zipf_mid) / (hi.known_share - lo.known_share) END
         FROM b hi JOIN b lo ON lo.band = hi.band - 1
        WHERE hi.n >= p_min_band_n AND lo.n >= p_min_band_n
          AND hi.known_share >= 0.85 AND lo.known_share < 0.85
        ORDER BY hi.band ASC LIMIT 1),
      (SELECT CASE WHEN hi.known_share = lo.known_share THEN lo.zipf_mid
                   ELSE lo.zipf_mid + (0.50 - lo.known_share)
                        * (hi.zipf_mid - lo.zipf_mid) / (hi.known_share - lo.known_share) END
         FROM b hi JOIN b lo ON lo.band = hi.band - 1
        WHERE hi.n >= p_min_band_n AND lo.n >= p_min_band_n
          AND hi.known_share >= 0.50 AND lo.known_share < 0.50
        ORDER BY hi.band ASC LIMIT 1)
    INTO v_85, v_50;

    v_confidence := CASE
        WHEN v_answered < 10 OR v_usable < 2 THEN 'none'
        WHEN v_answered < 25 OR v_usable < 4 THEN 'low'
        WHEN v_answered < 60 OR v_usable < 5 THEN 'medium'
        ELSE 'good'
    END;

    RETURN jsonb_build_object(
        'answered',        v_answered,
        'correct',         v_correct,
        'bands',           v_bands,
        'ability_zipf_85', v_85,
        'ability_zipf_50', v_50,
        'confidence',      v_confidence
    );
END;
$function$;

REVOKE EXECUTE ON FUNCTION public.calibration_ability(uuid, integer) FROM anon;
GRANT EXECUTE ON FUNCTION public.calibration_ability(uuid, integer)
    TO authenticated, service_role;


-- -----------------------------------------------------------------------------
-- Seed the blocklist with the case TASK-756 actually found.
-- -----------------------------------------------------------------------------
INSERT INTO public.calibration_anchor_blocklist (sense_id, reason)
SELECT 14968, 'TASK-757: lemma "hand" carries the definition of the idiom "hand in hand" ("Closely connected or associated with something else"). The key does not define the prompt, so the item is unanswerable however good the distractors are.'
WHERE EXISTS (SELECT 1 FROM public.dim_word_senses WHERE id = 14968)
ON CONFLICT (sense_id) DO NOTHING;


-- =============================================================================
-- Verification
-- =============================================================================
-- Stratification actually stratifies (expect roughly equal counts per band, not
-- a pile in whichever band the dictionary is densest):
--   SELECT zipf_band, count(*) FROM calibration_responses
--    WHERE session_id = '<id>' GROUP BY 1 ORDER BY 1;
--
-- An anchor is never served twice in one session:
--   SELECT anchor_sense_id, count(*) FROM calibration_responses
--    WHERE session_id = '<id>' GROUP BY 1 HAVING count(*) > 1;   -- expect none
--
-- The blocked sense never appears:
--   SELECT count(*) FROM calibration_responses r
--     JOIN calibration_anchor_blocklist b ON b.sense_id = r.anchor_sense_id;  -- 0
--
-- Every option shown was recorded (expect 4 per answered item):
--   SELECT r.id, count(o.*) FROM calibration_responses r
--     LEFT JOIN calibration_response_options o ON o.response_id = r.id
--    WHERE r.session_id = '<id>' GROUP BY r.id HAVING count(o.*) <> 4;  -- expect none
--
-- The also-correct signal TASK-763 needs is queryable:
--   SELECT o.sense_id, count(*) AS picked
--     FROM calibration_response_options o
--    WHERE o.was_chosen AND NOT o.is_key
--    GROUP BY 1 ORDER BY picked DESC LIMIT 20;
-- =============================================================================
