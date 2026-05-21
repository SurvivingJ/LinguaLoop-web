-- ============================================================================
-- Phase 12 — Practice Engine merger — exercise-type registry with timing
-- Date: 2026-05-21
--
-- Adds dim_exercise_types: the canonical per-type registry carrying:
--   - family (one of the 6 cognitive families from ADR-005)
--   - expected_seconds (P50 seed; nightly job updates _p50 from observations)
--
-- The merged Practice Engine (TASK-105 / TASK-107) reads this to convert
-- target_minutes into an item count: fill items until
--   Σ expected_seconds ≥ target_minutes · 60.
--
-- Seeding strategy:
--   1) Insert one row per DISTINCT exercise_type from the existing exercises
--      table with expected_seconds=45 (project-wide average).
--   2) Map each type to a family by best-effort string match. Unmappable
--      types default to 'meaning_recall' and MUST be reviewed manually
--      before flag flip — log lists every defaulted row.
--   3) Nightly job (phase12_exercise_time_estimate_refresh, TASK-112) later
--      populates expected_seconds_p50 from observed P50s once ≥ 30 samples
--      per type accrue.
--
-- See wiki/features/practice-engine.tech.md and ADR-007.
-- ============================================================================

BEGIN;

CREATE TABLE IF NOT EXISTS public.dim_exercise_types (
    type_code             text     PRIMARY KEY,
    family                text     NOT NULL,
    expected_seconds      smallint NOT NULL DEFAULT 45,
    expected_seconds_p50  numeric(5,1),
    is_active             boolean  NOT NULL DEFAULT true,
    CONSTRAINT dim_exercise_types_family_check
        CHECK (family IN ('form_recognition','meaning_recall','form_production',
                          'collocation','semantic_discrimination','contextual_use')),
    CONSTRAINT dim_exercise_types_expected_seconds_positive
        CHECK (expected_seconds > 0 AND expected_seconds <= 600),
    CONSTRAINT dim_exercise_types_p50_positive
        CHECK (expected_seconds_p50 IS NULL OR
               (expected_seconds_p50 > 0 AND expected_seconds_p50 <= 600))
);

COMMENT ON TABLE public.dim_exercise_types IS
    'Canonical exercise-type registry. Drives time-budget accounting in the '
    'merged Practice Engine. expected_seconds is the seed P50; '
    'expected_seconds_p50 is refreshed nightly from observed durations.';

-- ---------------------------------------------------------------------------
-- Seed family mapping helper. This is a one-shot best-effort mapping; any
-- unmapped type falls through to 'meaning_recall' and is logged via a
-- NOTICE for manual review.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION pg_temp.map_exercise_type_to_family(p_type text)
RETURNS text LANGUAGE sql IMMUTABLE AS $$
    SELECT CASE
        -- form_recognition: lookups, MC meaning-from-form
        WHEN p_type ILIKE '%mcq_meaning%' OR p_type ILIKE '%recognition%'
          OR p_type ILIKE '%pinyin_match%' OR p_type ILIKE '%kana_match%'
          THEN 'form_recognition'
        -- meaning_recall: produce meaning, definition
        WHEN p_type ILIKE '%meaning_recall%' OR p_type ILIKE '%definition%'
          OR p_type ILIKE '%mcq_definition%'
          THEN 'meaning_recall'
        -- form_production: type / produce the form
        WHEN p_type ILIKE '%spelling%' OR p_type ILIKE '%production%'
          OR p_type ILIKE '%typed%'   OR p_type ILIKE '%character_writing%'
          OR p_type ILIKE '%dictation%'
          THEN 'form_production'
        -- collocation: jumbled, cloze, partner-pairing
        WHEN p_type ILIKE '%cloze%'    OR p_type ILIKE '%jumbled%'
          OR p_type ILIKE '%collocation%' OR p_type ILIKE '%fill_blank%'
          OR p_type ILIKE '%word_order%'
          THEN 'collocation'
        -- semantic_discrimination: synonym, antonym, semantic MC
        WHEN p_type ILIKE '%synonym%'   OR p_type ILIKE '%antonym%'
          OR p_type ILIKE '%discrimin%' OR p_type ILIKE '%nuance%'
          THEN 'semantic_discrimination'
        -- contextual_use: sentence-building, free production in context
        WHEN p_type ILIKE '%sentence_build%' OR p_type ILIKE '%contextual%'
          OR p_type ILIKE '%capstone%'
          THEN 'contextual_use'
        ELSE 'meaning_recall'  -- fallback
    END
$$;

-- ---------------------------------------------------------------------------
-- Seed insert. Log fallback assignments for follow-up review.
-- ---------------------------------------------------------------------------
DO $$
DECLARE
    r RECORD;
    v_total int := 0;
    v_defaulted int := 0;
BEGIN
    FOR r IN
        SELECT DISTINCT exercise_type
        FROM exercises
        WHERE exercise_type IS NOT NULL
        ORDER BY exercise_type
    LOOP
        INSERT INTO dim_exercise_types (type_code, family, expected_seconds)
        VALUES (
            r.exercise_type,
            pg_temp.map_exercise_type_to_family(r.exercise_type),
            45
        )
        ON CONFLICT (type_code) DO NOTHING;
        v_total := v_total + 1;
        IF pg_temp.map_exercise_type_to_family(r.exercise_type) = 'meaning_recall'
           AND r.exercise_type NOT ILIKE '%meaning%'
           AND r.exercise_type NOT ILIKE '%definition%' THEN
            v_defaulted := v_defaulted + 1;
            RAISE NOTICE '[dim_exercise_types] defaulted family=meaning_recall for type_code=%; review manually',
                r.exercise_type;
        END IF;
    END LOOP;
    RAISE NOTICE '[dim_exercise_types] seeded % types (% defaulted to meaning_recall)',
        v_total, v_defaulted;
END $$;

-- ---------------------------------------------------------------------------
-- Helper index for the nightly refresh join.
-- ---------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_exercise_attempts_exercise_type_created_at
    ON public.exercise_attempts (exercise_type, created_at)
    WHERE time_taken_ms IS NOT NULL;

COMMIT;
