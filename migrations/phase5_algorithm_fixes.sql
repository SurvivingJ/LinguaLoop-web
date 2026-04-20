-- ============================================================================
-- Phase 5: Algorithm Fixes
-- Date: 2026-04-12
--
-- 5.1 Exercise-type-specific BKT parameters
-- 5.2 Add p_exercise_type param to update_vocabulary_from_word_test
-- 5.3 Temporal decay function for BKT p_known
-- 5.4 Unify phase thresholds (single source of truth)
-- ============================================================================


-- ============================================================================
-- 5.1 Exercise-type-specific BKT function
-- ============================================================================
-- All exercises currently use the same slip/guess parameters. A flashcard
-- correct (easy recognition, high guess probability) should count less than
-- a capstone production correct (hard, low guess probability).
--
-- Four tiers based on cognitive demand:
--   Recognition: high guess (0.25), low slip (0.05) — flashcards, cloze, MCQ
--   Recall:      low guess (0.10), moderate slip (0.10) — translation, morphology
--   Nuanced:     moderate guess (0.20), higher slip (0.15) — collocation, discrimination
--   Production:  very low guess (0.05), highest slip (0.20) — free text, style

CREATE OR REPLACE FUNCTION public.bkt_update_exercise(
    p_current numeric,
    p_correct boolean,
    p_exercise_type text
)
RETURNS numeric
LANGUAGE plpgsql
IMMUTABLE
AS $function$
DECLARE
    v_slip numeric;
    v_guess numeric;
BEGIN
    CASE
        -- Tier 1: Recognition — high guess probability, easy tasks
        WHEN p_exercise_type IN (
            'phonetic_recognition', 'definition_match',
            'text_flashcard', 'listening_flashcard',
            'cloze_completion'
        ) THEN
            v_slip := 0.05;
            v_guess := 0.25;

        -- Tier 2: Recall — requires active retrieval
        WHEN p_exercise_type IN (
            'morphology_slot',
            'jumbled_sentence',
            'tl_nl_translation', 'nl_tl_translation',
            'spot_incorrect_sentence', 'spot_incorrect_part'
        ) THEN
            v_slip := 0.10;
            v_guess := 0.10;

        -- Tier 3: Nuanced — requires discrimination between similar items
        WHEN p_exercise_type IN (
            'semantic_discrimination',
            'collocation_gap_fill', 'collocation_repair',
            'odd_one_out', 'odd_collocation_out'
        ) THEN
            v_slip := 0.15;
            v_guess := 0.20;

        -- Tier 4: Production — requires generation, very low guess chance
        WHEN p_exercise_type IN (
            'verb_noun_match', 'context_spectrum',
            'timed_speed_round', 'style_imitation',
            'free_production', 'sentence_writing'
        ) THEN
            v_slip := 0.20;
            v_guess := 0.05;

        -- Default: same as current bkt_update_word_test
        ELSE
            v_slip := 0.05;
            v_guess := 0.25;
    END CASE;

    RETURN bkt_update(p_current, p_correct, v_slip, v_guess);
END;
$function$;


-- ============================================================================
-- 5.2 Add p_exercise_type param to update_vocabulary_from_word_test
-- ============================================================================
-- Optional DEFAULT NULL for backward compatibility. Routes to 5.1 when
-- provided, falls back to existing bkt_update_word_test when NULL.

CREATE OR REPLACE FUNCTION public.update_vocabulary_from_word_test(
    p_user_id uuid,
    p_sense_id integer,
    p_is_correct boolean,
    p_language_id smallint,
    p_exercise_type text DEFAULT NULL
)
RETURNS TABLE(
    out_sense_id integer,
    out_p_known_before numeric,
    out_p_known_after numeric,
    out_status text
)
LANGUAGE plpgsql
AS $function$
DECLARE
    v_p_current NUMERIC;
    v_p_new NUMERIC;
    v_status TEXT;
BEGIN
    -- Get current p_known or compute frequency-based prior
    SELECT COALESCE(uvk.p_known,
        CASE
            WHEN dv.frequency_rank IS NULL THEN 0.10
            WHEN dv.frequency_rank >= 6.0 THEN 0.85
            WHEN dv.frequency_rank >= 5.0 THEN 0.65
            WHEN dv.frequency_rank >= 4.0 THEN 0.35
            WHEN dv.frequency_rank >= 3.0 THEN 0.15
            ELSE 0.05
        END
    ) INTO v_p_current
    FROM dim_word_senses dws
    JOIN dim_vocabulary dv ON dv.id = dws.vocab_id
    LEFT JOIN user_vocabulary_knowledge uvk
        ON uvk.user_id = p_user_id AND uvk.sense_id = p_sense_id
    WHERE dws.id = p_sense_id;

    IF v_p_current IS NULL THEN
        v_p_current := 0.10;
    END IF;

    -- Use exercise-type-specific BKT when type is provided
    IF p_exercise_type IS NOT NULL THEN
        v_p_new := bkt_update_exercise(v_p_current, p_is_correct, p_exercise_type);
    ELSE
        v_p_new := bkt_update_word_test(v_p_current, p_is_correct);
    END IF;

    v_status := bkt_status(v_p_new);

    -- Upsert knowledge state
    INSERT INTO user_vocabulary_knowledge
        (user_id, sense_id, language_id, p_known, status,
         evidence_count, word_test_correct, word_test_wrong,
         last_evidence_at, updated_at)
    VALUES (
        p_user_id, p_sense_id, p_language_id,
        v_p_new, v_status,
        1,
        CASE WHEN p_is_correct THEN 1 ELSE 0 END,
        CASE WHEN p_is_correct THEN 0 ELSE 1 END,
        NOW(), NOW()
    )
    ON CONFLICT (user_id, sense_id) DO UPDATE SET
        p_known = EXCLUDED.p_known,
        status = CASE
            WHEN user_vocabulary_knowledge.status = 'user_marked_unknown'
            THEN 'user_marked_unknown'
            ELSE EXCLUDED.status
        END,
        evidence_count = user_vocabulary_knowledge.evidence_count + 1,
        word_test_correct = user_vocabulary_knowledge.word_test_correct + EXCLUDED.word_test_correct,
        word_test_wrong = user_vocabulary_knowledge.word_test_wrong + EXCLUDED.word_test_wrong,
        last_evidence_at = NOW(),
        updated_at = NOW();

    RETURN QUERY SELECT p_sense_id, v_p_current, v_p_new, v_status;
END;
$function$;


-- ============================================================================
-- 5.3 Temporal decay function for BKT p_known
-- ============================================================================
-- Applied at read-time in session-building queries, not stored.
-- Words not seen for a long time decay toward the base prior (0.10).
-- Half-life of 60 days: after 60 days, a word at p_known=0.90 decays
-- to 0.10 + (0.90-0.10)*0.5 = 0.50.

CREATE OR REPLACE FUNCTION public.bkt_apply_decay(
    p_known numeric,
    p_last_evidence_at timestamptz,
    p_half_life_days numeric DEFAULT 60.0
)
RETURNS numeric
LANGUAGE plpgsql
IMMUTABLE
AS $function$
DECLARE
    v_days_since numeric;
    v_decay_factor numeric;
    v_base_prior numeric := 0.10;
BEGIN
    -- No decay if no evidence timestamp or very recent
    IF p_last_evidence_at IS NULL THEN
        RETURN p_known;
    END IF;

    v_days_since := EXTRACT(EPOCH FROM (now() - p_last_evidence_at)) / 86400.0;

    -- No decay within 1 day
    IF v_days_since <= 1.0 THEN
        RETURN p_known;
    END IF;

    -- Exponential decay toward base prior
    v_decay_factor := POWER(0.5, v_days_since / p_half_life_days);

    RETURN GREATEST(v_base_prior,
        v_base_prior + (p_known - v_base_prior) * v_decay_factor
    );
END;
$function$;

-- Convenience wrapper that applies decay to a user's effective p_known
-- for use in session-building queries:
--   SELECT bkt_effective_p_known(uvk.p_known, uvk.last_evidence_at)
--   FROM user_vocabulary_knowledge uvk ...
CREATE OR REPLACE FUNCTION public.bkt_effective_p_known(
    p_known numeric,
    p_last_evidence_at timestamptz
)
RETURNS numeric
LANGUAGE sql
IMMUTABLE
AS $function$
    SELECT bkt_apply_decay(p_known, p_last_evidence_at, 60.0);
$function$;


-- ============================================================================
-- 5.4 Unify phase thresholds — single source of truth
-- ============================================================================
-- Python uses (0.30, 0.55, 0.80). SQL RPCs may use different values.
-- This function becomes the canonical reference. Python should import
-- from config or call this function rather than hardcoding thresholds.

CREATE OR REPLACE FUNCTION public.bkt_phase(p_known numeric)
RETURNS text
LANGUAGE sql
IMMUTABLE
AS $function$
    SELECT CASE
        WHEN p_known < 0.30 THEN 'A'   -- New/unknown: receptive exercises
        WHEN p_known < 0.55 THEN 'B'   -- Learning: recognition + recall
        WHEN p_known < 0.80 THEN 'C'   -- Consolidating: nuanced + production
        ELSE 'D'                         -- Known: maintenance review only
    END;
$function$;

-- Also expose the thresholds as a table-returning function for Python to query
CREATE OR REPLACE FUNCTION public.bkt_phase_thresholds()
RETURNS TABLE(phase text, min_p_known numeric, max_p_known numeric)
LANGUAGE sql
IMMUTABLE
AS $function$
    VALUES
        ('A'::text, 0.00::numeric, 0.30::numeric),
        ('B'::text, 0.30::numeric, 0.55::numeric),
        ('C'::text, 0.55::numeric, 0.80::numeric),
        ('D'::text, 0.80::numeric, 1.00::numeric);
$function$;
