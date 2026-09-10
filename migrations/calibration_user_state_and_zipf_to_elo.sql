-- Calibration Phase 4 — the handoff to test selection.
-- =============================================================================
-- PROBLEM
--   Calibration measures a learner's vocabulary and then throws the answer away
--   at the end of the session. Meanwhile test selection ranks candidates purely
--   by |test_elo - user_elo|, and ADR-024 records why that rating cannot express
--   the gap: the multiple-choice chance floor caps the reachable Elo distance at
--   ~191 points, so a learner who knows almost nothing still settles only ~190
--   below the pool. The measurement exists and the consumer exists; nothing
--   connects them.
--
-- FIX
--   Two objects, and deliberately nothing more.
--
--   1. `user_calibration_state` — the handoff table. Its shape is not invented
--      here: [[features/vocabulary-aware-test-selection.tech]] §1.1 already
--      specifies it as an input contract ("Built in parallel; this feature
--      consumes it"). Calibration writes it; selection reads it. Neither side
--      calls the other.
--
--   2. `calibration_zipf_to_elo(numeric)` — the Zipf→ELO anchor map, §1.2.
--
-- WHY THE MAP LIVES IN SQL AND NOWHERE ELSE
--   [[two-difficulty-to-tier-maps]] records that three copies of the
--   difficulty→tier bands already have to be kept in step. This does not add a
--   fourth. The ELO half of every anchor is read from `dim_complexity_tiers` AT
--   CALL TIME rather than being written out as literals, so the map cannot drift
--   from the tiers even if someone re-seeds them. Only the Zipf half is a
--   constant here, mirroring `difficulty_scorer._REF_ZIPF`.
--
--   Python reads this through the RPC. The single permitted Python copy is a test
--   fixture asserting agreement with this function.
--
-- THE CONTRACT THIS DEPENDS ON, AND WHY IT IS NOW SATISFIED
--   §1.2 is emphatic: `ability_zipf` MUST be the Zipf at which the learner's
--   known-share crosses 1 - u* (85%). Not a 50% crossover, not a mean of known
--   senses. On live data those differ by **430 ELO points**, and the wrong end is
--   silently catastrophic — a 50% crossover maps a learner who knows 17% of T4
--   vocabulary to T5 "Uni Student" content.
--
--   Calibration's `ability_zipf_85` is that construct, and after TASK-764 it is
--   the *knowledge* crossing rather than the *accuracy* crossing: the estimator
--   fits p(z) = 0.25 + 0.75·σ(a(z−b)) with the four-option guess floor fixed, so
--   "85%" means 85% of words genuinely known and not 85% of items answered
--   right. Those two differ substantially at the bottom of the curve, which is
--   exactly where a struggling learner sits — so the guess-floor term is part of
--   satisfying the contract, not a refinement of it.
--
-- WHAT THIS MIGRATION DELIBERATELY DOES NOT DO
--   It does not touch `get_recommended_tests`, `process_test_submission`, or
--   `user_skill_ratings`. ADR-024 §4 puts the rating write behind hard guards
--   (below 5 attempts write directly; above 5 only on a >200 point disagreement,
--   moving at most min(0.25·diff, 150), at most weekly, never within an hour of a
--   test, clamped to [875, 1925]) and §5 requires every decision INCLUDING every
--   skip to be appended to `user_skill_rating_adjustments`. That audit table does
--   not exist yet: it is TASK-746's, built with the guarded writer it audits
--   (TASK-747); selection's consumption of this table is TASK-748. Shipping
--   the writer without its audit trail would be an unaudited automated write to
--   live user ratings, which is precisely what those guards exist to prevent.
--
--   So this migration ships the measurement and stops at the boundary. Selection
--   begins consuming it the moment TASK-746 lands, with no further change here.
--
-- SAFETY
--   - Additive: one table, one function. Nothing existing is modified.
--   - Idempotent (CREATE TABLE / OR REPLACE / guarded policy drops).
--   - RLS on; a learner reads only their own row. The Flask layer uses the
--     service role and bypasses RLS as it does everywhere else.
--   - `calibration_zipf_to_elo` is IMMUTABLE-unsafe by design (it reads a table),
--     so it is STABLE. Do not mark it IMMUTABLE to win an index — that would
--     freeze a stale ladder into any expression index built on it.
--
-- APPLIED LIVE: before 2026-09-10 (TASK-765). Verified 2026-09-10 against
--   project kpfqrjtfxmujzolwsvdq: user_calibration_state exists with PK
--   (user_id, language_id, mode) and the mode/se CHECKs; calibration_zipf_to_elo
--   is STABLE and returns 7.0->875, 6.25->875, 5.25->1175, 5.0->1250,
--   4.5->1400, 4.2->1550, 3.85->1681, 3.8->1700, 3.25->1925, 1.0->1925.
--   `python -m scripts.verify_calibration_state --self-test`: zipf->elo map
--   PASS (61 probe points, 0 mismatches), state handoff PASS. NOTE: there is no
--   row for it in supabase_migrations.schema_migrations — it was applied
--   outside the migration history, so the exact timestamp is not recorded.
-- =============================================================================


-- -----------------------------------------------------------------------------
-- 1. The handoff table (spec §1.1, shape unchanged)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.user_calibration_state (
    user_id         uuid        NOT NULL,
    language_id     smallint    NOT NULL REFERENCES public.dim_languages(id),

    -- The Zipf at which known-share crosses 85%. NULL when the curve is not yet
    -- identifiable — an honest "not measured", never an extrapolation.
    ability_zipf    numeric,
    -- Standard error of ability_zipf, in Zipf units. Measured, not assumed:
    -- 0.63 at 20 answers, 0.27 at 60, 0.16 at 120, 0.11 at 300. ADR-024 gate
    -- G3_high_se skips the rating write above 0.75.
    ability_se      numeric,

    -- Per-Zipf-band known share: the evidence the estimate was derived from.
    -- Kept so a downstream consumer can see the curve rather than trust a scalar.
    band_accuracies jsonb       NOT NULL DEFAULT '[]'::jsonb,

    items_answered  integer     NOT NULL DEFAULT 0,
    sessions_pooled integer     NOT NULL DEFAULT 0,
    -- 'definition' | 'pronunciation'. Definition mode measures vocabulary
    -- knowledge and is what selection wants; pronunciation measures reading
    -- ability and is stored separately rather than averaged into it.
    mode            text        NOT NULL DEFAULT 'definition',
    last_run_at     timestamptz NOT NULL DEFAULT now(),

    PRIMARY KEY (user_id, language_id, mode),
    CONSTRAINT user_calibration_state_mode_chk
        CHECK (mode IN ('definition', 'pronunciation')),
    CONSTRAINT user_calibration_state_se_chk
        CHECK (ability_se IS NULL OR ability_se >= 0)
);

COMMENT ON TABLE public.user_calibration_state IS
  'Handoff from Calibration to test selection. Input contract of features/vocabulary-aware-test-selection.tech §1.1: Calibration writes, selection reads, neither calls the other. ability_zipf is the Zipf at which KNOWN-SHARE crosses 85% (not a 50% crossover, and not accuracy — the estimator removes the 1-in-4 guess floor first); those constructs differ by ~430 ELO through the §1.2 map.';

COMMENT ON COLUMN public.user_calibration_state.ability_se IS
  'Standard error of ability_zipf in Zipf units, from the measured precision table in scripts/calibration_estimator_bias.py. ADR-024 gate G3_high_se skips the rating write when this exceeds 0.75. Propagate it; do not treat ability_zipf as exact.';

CREATE INDEX IF NOT EXISTS idx_user_calibration_state_user
    ON public.user_calibration_state (user_id, language_id);

ALTER TABLE public.user_calibration_state ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS user_calibration_state_own ON public.user_calibration_state;
CREATE POLICY user_calibration_state_own ON public.user_calibration_state
    FOR ALL TO authenticated
    USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

GRANT SELECT, INSERT, UPDATE ON public.user_calibration_state
    TO authenticated, service_role;


-- -----------------------------------------------------------------------------
-- 2. ability_zipf -> ELO (spec §1.2). SQL is the ONLY copy.
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.calibration_zipf_to_elo(p_ability_zipf numeric)
RETURNS integer
LANGUAGE plpgsql
STABLE
SET search_path TO 'public', 'pg_temp'
AS $function$
DECLARE
    v_elo numeric;
BEGIN
    IF p_ability_zipf IS NULL THEN
        RETURN NULL;
    END IF;

    WITH anchors AS (
        -- Zipf side mirrors difficulty_scorer._REF_ZIPF (T1..T6). ELO side is read
        -- from the live tiers rather than written out, so the two halves cannot
        -- drift apart. Monotone DECREASING in Zipf: rarer vocabulary, higher ELO.
        SELECT t.id AS tier,
               (ARRAY[6.25, 5.25, 4.50, 4.20, 3.80, 3.25])[t.id]::numeric AS zipf,
               t.initial_elo::numeric AS elo
          FROM dim_complexity_tiers t
         WHERE t.id BETWEEN 1 AND 6
    ),
    bounds AS (
        SELECT max(elo) AS elo_max, min(elo) AS elo_min,
               max(zipf) AS zipf_max, min(zipf) AS zipf_min
          FROM anchors
    ),
    bracket AS (
        -- The one segment containing p_ability_zipf, taken from the pair of
        -- adjacent tiers that straddle it.
        SELECT hi.zipf AS z_hi, hi.elo AS e_hi, lo.zipf AS z_lo, lo.elo AS e_lo
          FROM anchors hi
          JOIN anchors lo ON lo.tier = hi.tier + 1
         WHERE p_ability_zipf <= hi.zipf AND p_ability_zipf >= lo.zipf
         ORDER BY hi.tier
         LIMIT 1
    )
    SELECT CASE
        -- Clamp rather than extrapolate: outside the ladder there is no
        -- calibration, and a linear run-out would invent ratings for learners at
        -- the edges from nothing.
        WHEN p_ability_zipf >= (SELECT zipf_max FROM bounds) THEN (SELECT elo_min FROM bounds)
        WHEN p_ability_zipf <= (SELECT zipf_min FROM bounds) THEN (SELECT elo_max FROM bounds)
        ELSE (SELECT e_hi + (e_lo - e_hi)
                   * ((z_hi - p_ability_zipf) / NULLIF(z_hi - z_lo, 0))
                FROM bracket)
    END
    INTO v_elo;

    -- Belt and braces: the ladder's own range is the hard clamp.
    RETURN GREATEST(875, LEAST(1925, round(v_elo)))::integer;
END;
$function$;

COMMENT ON FUNCTION public.calibration_zipf_to_elo(numeric) IS
  'Maps a calibration ability_zipf onto the age-tier ELO ladder by piecewise-linear interpolation, clamped to [875, 1925]. THE ONLY COPY of this map — the ELO anchors are read from dim_complexity_tiers at call time so they cannot drift, per two-difficulty-to-tier-maps. Python must call this rather than reimplement it; the sole permitted Python copy is a test fixture asserting agreement.';

GRANT EXECUTE ON FUNCTION public.calibration_zipf_to_elo(numeric)
    TO authenticated, service_role;


-- =============================================================================
-- Verification
-- =============================================================================
-- The anchors round-trip to the tier ELOs exactly:
--   SELECT z, calibration_zipf_to_elo(z) FROM unnest(
--       ARRAY[6.25, 5.25, 4.50, 4.20, 3.80, 3.25]::numeric[]) z;
--   -- expect 875, 1175, 1400, 1550, 1700, 1925
--
-- The worked example from spec §1.2 reproduces (85%-known Zipf 5.0 -> ~1250):
--   SELECT calibration_zipf_to_elo(5.00);      -- expect 1250
-- ...and the wrong construct is visibly far away, which is the point of the
-- contract (50% crossover Zipf 3.85 -> ~1681):
--   SELECT calibration_zipf_to_elo(3.85);      -- expect ~1681
--
-- Clamping, not extrapolation, outside the ladder:
--   SELECT calibration_zipf_to_elo(7.0), calibration_zipf_to_elo(1.0);
--   -- expect 875, 1925
--
-- =============================================================================
-- APPLYING THIS
-- =============================================================================
-- Applied live (TASK-765; see the APPLIED LIVE line in the header). The session
-- that wrote it on 2026-09-09 had no DDL path, so it was applied afterwards.
-- Downstream still FAILS CLOSED if the table is ever absent —
-- calibration_service.write_calibration_state() logs a warning and returns
-- rather than pretending to have persisted anything.
--
-- Verify:
--   PYTHONIOENCODING=utf-8 python -m scripts.verify_calibration_state --self-test
-- =============================================================================
