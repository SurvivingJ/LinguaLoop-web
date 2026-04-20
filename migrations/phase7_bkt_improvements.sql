-- ============================================================================
-- Phase 7: BKT Algorithm Improvements
-- Date: 2026-04-16
--
-- 7.1 Transit parameter P(T) — learning credit after each evidence event
-- 7.2 FSRS Stability-Informed Decay (replaces flat 60-day half-life)
-- 7.3 FSRS Lapse → BKT Penalty (reverse bridge)
-- 7.4 Frequency-Tier Inference
-- ============================================================================


-- ============================================================================
-- 7.1  Transit parameter P(T)
-- ============================================================================
-- Standard BKT has 4 parameters: P(L0), P(T), P(S), P(G). Our model only
-- uses slip and guess. The transit parameter models the probability that the
-- student actually learned from the exercise attempt, regardless of whether
-- they answered correctly. Without it, learning rate = 0.
--
-- Applied AFTER the Bayesian posterior update, BEFORE clamping.
-- Formula: p_with_transit = p_post + (1 - p_post) * P_TRANSIT

-- Comprehension: very weak learning signal (just reading/listening)
CREATE OR REPLACE FUNCTION public.bkt_update_comprehension(
    p_current numeric,
    p_correct boolean
)
RETURNS numeric
LANGUAGE plpgsql
IMMUTABLE
AS $function$
DECLARE
    v_p_post numeric;
    v_p_transit numeric := 0.02;
BEGIN
    v_p_post := bkt_update(p_current, p_correct, 0.10, 0.25);
    -- Apply transit: small learning credit
    v_p_post := v_p_post + (1.0 - v_p_post) * v_p_transit;
    RETURN GREATEST(0.02, LEAST(0.98, v_p_post));
END;
$function$;

-- Word test: moderate learning signal
CREATE OR REPLACE FUNCTION public.bkt_update_word_test(
    p_current numeric,
    p_correct boolean
)
RETURNS numeric
LANGUAGE plpgsql
IMMUTABLE
AS $function$
DECLARE
    v_p_post numeric;
    v_p_transit numeric := 0.05;
BEGIN
    v_p_post := bkt_update(p_current, p_correct, 0.05, 0.25);
    v_p_post := v_p_post + (1.0 - v_p_post) * v_p_transit;
    RETURN GREATEST(0.02, LEAST(0.98, v_p_post));
END;
$function$;

-- Exercise-type-specific: transit varies by cognitive demand
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
    v_transit numeric;
    v_p_post numeric;
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
            v_transit := 0.05;

        -- Tier 2: Recall — requires active retrieval
        WHEN p_exercise_type IN (
            'morphology_slot',
            'jumbled_sentence',
            'tl_nl_translation', 'nl_tl_translation',
            'spot_incorrect_sentence', 'spot_incorrect_part'
        ) THEN
            v_slip := 0.10;
            v_guess := 0.10;
            v_transit := 0.08;

        -- Tier 3: Nuanced — requires discrimination between similar items
        WHEN p_exercise_type IN (
            'semantic_discrimination',
            'collocation_gap_fill', 'collocation_repair',
            'odd_one_out', 'odd_collocation_out'
        ) THEN
            v_slip := 0.15;
            v_guess := 0.20;
            v_transit := 0.08;

        -- Tier 4: Production — requires generation, very low guess chance
        WHEN p_exercise_type IN (
            'verb_noun_match', 'context_spectrum',
            'timed_speed_round', 'style_imitation',
            'free_production', 'sentence_writing'
        ) THEN
            v_slip := 0.20;
            v_guess := 0.05;
            v_transit := 0.10;

        -- Default: same as word test
        ELSE
            v_slip := 0.05;
            v_guess := 0.25;
            v_transit := 0.05;
    END CASE;

    v_p_post := bkt_update(p_current, p_correct, v_slip, v_guess);
    -- Apply transit: learning credit proportional to cognitive demand
    v_p_post := v_p_post + (1.0 - v_p_post) * v_transit;
    RETURN GREATEST(0.02, LEAST(0.98, v_p_post));
END;
$function$;


-- ============================================================================
-- 7.2  FSRS Stability-Informed Decay
-- ============================================================================
-- Replaces the flat 60-day half-life with a two-path decay:
--   Path A: If FSRS stability is available, use it as the decay rate
--           (retrievability = exp(-days / stability))
--   Path B: Fallback — evidence-count-scaled half-life
--           (half_life = 30 * (1 + 0.5 * ln(1 + evidence_count)))
--
-- This bridges the BKT/FSRS gap: when FSRS says a word is fragile
-- (low stability), effective_p_known drops accordingly.

CREATE OR REPLACE FUNCTION public.bkt_apply_decay(
    p_known numeric,
    p_last_evidence_at timestamptz,
    p_stability real DEFAULT NULL,
    p_evidence_count integer DEFAULT 0
)
RETURNS numeric
LANGUAGE plpgsql
IMMUTABLE
AS $function$
DECLARE
    v_days_since numeric;
    v_retrievability numeric;
    v_half_life numeric;
    v_base_prior numeric := 0.10;
BEGIN
    -- No decay if no evidence timestamp
    IF p_last_evidence_at IS NULL THEN
        RETURN p_known;
    END IF;

    v_days_since := EXTRACT(EPOCH FROM (now() - p_last_evidence_at)) / 86400.0;

    -- No decay within 1 day
    IF v_days_since <= 1.0 THEN
        RETURN p_known;
    END IF;

    -- Path A: FSRS stability-informed decay
    IF p_stability IS NOT NULL AND p_stability > 0 THEN
        v_retrievability := exp(-v_days_since / p_stability);
    ELSE
        -- Path B: evidence-count-scaled half-life fallback
        v_half_life := 30.0 * (1.0 + 0.5 * ln(1.0 + GREATEST(0, p_evidence_count)));
        v_retrievability := POWER(0.5, v_days_since / v_half_life);
    END IF;

    RETURN GREATEST(v_base_prior,
        v_base_prior + (p_known - v_base_prior) * v_retrievability
    );
END;
$function$;

-- Convenience wrapper — accepts all needed columns from a joined query
CREATE OR REPLACE FUNCTION public.bkt_effective_p_known(
    p_known numeric,
    p_last_evidence_at timestamptz,
    p_stability real DEFAULT NULL,
    p_evidence_count integer DEFAULT 0
)
RETURNS numeric
LANGUAGE sql
IMMUTABLE
AS $function$
    SELECT bkt_apply_decay(p_known, p_last_evidence_at, p_stability, p_evidence_count);
$function$;


-- ============================================================================
-- 7.3  FSRS Lapse → BKT Penalty (reverse bridge)
-- ============================================================================
-- When FSRS records a lapse (user failed to recall a word), apply a 20%
-- penalty to BKT p_known. This prevents BKT from showing a word as "known"
-- when FSRS says the memory is fragile.

CREATE OR REPLACE FUNCTION public.bkt_apply_lapse_penalty(
    p_user_id uuid,
    p_sense_id integer
)
RETURNS void
LANGUAGE plpgsql
AS $function$
BEGIN
    UPDATE user_vocabulary_knowledge
    SET p_known = GREATEST(0.10, p_known * 0.80),
        status = CASE
            WHEN status = 'user_marked_unknown' THEN 'user_marked_unknown'
            ELSE bkt_status(GREATEST(0.10, p_known * 0.80))
        END,
        updated_at = NOW()
    WHERE user_id = p_user_id
      AND sense_id = p_sense_id;
END;
$function$;


-- ============================================================================
-- 7.4  Frequency-Tier Inference
-- ============================================================================
-- When a user demonstrates knowledge of a rare word (reaches p_known >= 0.90),
-- boost common untracked/low-evidence words to their frequency-based prior.
-- Logic: if you know uncommon words, you almost certainly know common ones.
--
-- Only affects words with evidence_count < 3 and currently below their
-- frequency prior (safe: only raises floors, never lowers).

CREATE OR REPLACE FUNCTION public.bkt_infer_from_frequency(
    p_user_id uuid,
    p_language_id smallint,
    p_known_sense_id integer,
    p_new_p_known numeric
)
RETURNS integer  -- count of words boosted
LANGUAGE plpgsql
AS $function$
DECLARE
    v_freq_rank real;
    v_boosted integer;
BEGIN
    -- Only fire when the word just reached "known" status
    IF p_new_p_known < 0.90 THEN
        RETURN 0;
    END IF;

    -- Get frequency rank of the known word
    SELECT dv.frequency_rank INTO v_freq_rank
    FROM dim_word_senses dws
    JOIN dim_vocabulary dv ON dv.id = dws.vocab_id
    WHERE dws.id = p_known_sense_id;

    -- If the known word has no frequency data, nothing to infer
    IF v_freq_rank IS NULL THEN
        RETURN 0;
    END IF;

    -- Boost common words that are below their expected prior
    WITH targets AS (
        SELECT
            uvk.sense_id,
            uvk.p_known AS old_p_known,
            CASE
                WHEN dv.frequency_rank >= 6.0 THEN 0.85
                WHEN dv.frequency_rank >= 5.0 THEN 0.65
                WHEN dv.frequency_rank >= 4.0 THEN 0.35
                ELSE NULL  -- don't boost words that aren't significantly more common
            END AS target_prior
        FROM user_vocabulary_knowledge uvk
        JOIN dim_word_senses dws ON dws.id = uvk.sense_id
        JOIN dim_vocabulary dv ON dv.id = dws.vocab_id
        WHERE uvk.user_id = p_user_id
          AND dv.language_id = p_language_id
          AND uvk.evidence_count < 3
          AND dv.frequency_rank > v_freq_rank + 1.0
          AND uvk.status != 'user_marked_unknown'
    )
    UPDATE user_vocabulary_knowledge uvk
    SET p_known = t.target_prior,
        status = bkt_status(t.target_prior),
        updated_at = NOW()
    FROM targets t
    WHERE uvk.user_id = p_user_id
      AND uvk.sense_id = t.sense_id
      AND t.target_prior IS NOT NULL
      AND uvk.p_known < t.target_prior;

    GET DIAGNOSTICS v_boosted = ROW_COUNT;
    RETURN v_boosted;
END;
$function$;


-- ============================================================================
-- 7.5  Session Builder RPC — single query replacing 3 Python fetch methods
-- ============================================================================
-- Returns all candidate senses for a daily session, with decay-applied
-- effective_p_known and bucket assignment. Keeps ALL BKT math in SQL.
--
-- Buckets:
--   'due'      — FSRS due flashcards (state in review/relearning, due_date <= today)
--   'learning' — uncertainty zone (effective_p_known 0.25–0.75)
--   'new'      — low knowledge (effective_p_known < 0.30, status encountered/unknown)
--
-- Each row includes effective_p_known (with FSRS-informed decay) and
-- an entropy score for prioritization within buckets.

CREATE OR REPLACE FUNCTION public.get_session_senses(
    p_user_id uuid,
    p_language_id smallint,
    p_due_limit integer DEFAULT 30,
    p_learning_limit integer DEFAULT 30,
    p_new_limit integer DEFAULT 30
)
RETURNS TABLE(
    out_sense_id integer,
    out_effective_p_known numeric,
    out_bucket text,
    out_entropy numeric
)
LANGUAGE plpgsql
STABLE
AS $function$
BEGIN
    RETURN QUERY

    -- Bucket 1: FSRS due reviews
    (
        SELECT
            uf.sense_id AS out_sense_id,
            bkt_effective_p_known(
                COALESCE(uvk.p_known, 0.50),
                uvk.last_evidence_at,
                uf.stability,
                COALESCE(uvk.evidence_count, 0)
            ) AS out_effective_p_known,
            'due'::text AS out_bucket,
            -- Entropy for tie-breaking: p*(1-p), max at 0.5
            COALESCE(uvk.p_known, 0.50) * (1 - COALESCE(uvk.p_known, 0.50)) AS out_entropy
        FROM user_flashcards uf
        LEFT JOIN user_vocabulary_knowledge uvk
            ON uvk.user_id = uf.user_id AND uvk.sense_id = uf.sense_id
        WHERE uf.user_id = p_user_id
          AND uf.language_id = p_language_id
          AND uf.due_date <= CURRENT_DATE
          AND uf.state IN ('review', 'relearning')
        ORDER BY uf.due_date
        LIMIT p_due_limit
    )

    UNION ALL

    -- Bucket 2: Active learning (uncertainty zone after decay)
    (
        SELECT
            sub.sense_id,
            sub.eff_p,
            'learning'::text,
            sub.eff_p * (1 - sub.eff_p)
        FROM (
            SELECT
                uvk.sense_id,
                bkt_effective_p_known(
                    uvk.p_known,
                    uvk.last_evidence_at,
                    uf.stability,
                    uvk.evidence_count
                ) AS eff_p
            FROM user_vocabulary_knowledge uvk
            LEFT JOIN user_flashcards uf
                ON uf.user_id = uvk.user_id AND uf.sense_id = uvk.sense_id
            WHERE uvk.user_id = p_user_id
              AND uvk.language_id = p_language_id
              -- Widen stored range to catch words that decay into target zone
              AND uvk.p_known BETWEEN 0.20 AND 0.85
              AND uvk.status NOT IN ('user_marked_unknown', 'unknown')
        ) sub
        WHERE sub.eff_p BETWEEN 0.25 AND 0.75
        ORDER BY sub.eff_p * (1 - sub.eff_p) DESC  -- highest entropy first
        LIMIT p_learning_limit
    )

    UNION ALL

    -- Bucket 3: New/encountered senses (low effective p_known)
    (
        SELECT
            sub.sense_id,
            sub.eff_p,
            'new'::text,
            0.0  -- entropy not used for sorting new words
        FROM (
            SELECT
                uvk.sense_id,
                bkt_effective_p_known(
                    uvk.p_known,
                    uvk.last_evidence_at,
                    uf.stability,
                    uvk.evidence_count
                ) AS eff_p,
                uvk.last_evidence_at
            FROM user_vocabulary_knowledge uvk
            LEFT JOIN user_flashcards uf
                ON uf.user_id = uvk.user_id AND uf.sense_id = uvk.sense_id
            WHERE uvk.user_id = p_user_id
              AND uvk.language_id = p_language_id
              AND uvk.p_known < 0.40  -- wider to catch decay
              AND uvk.status IN ('encountered', 'unknown')
        ) sub
        WHERE sub.eff_p < 0.30
        ORDER BY sub.last_evidence_at DESC NULLS LAST
        LIMIT p_new_limit
    );
END;
$function$;


-- ============================================================================
-- 7.6  Sentence-Level Contextual Inference
-- ============================================================================
-- When a user answers comprehension questions correctly, apply a dampened
-- BKT update to vocabulary in the test transcript that was NOT directly
-- tested by any question. This lets each test provide evidence for more words.
--
-- Dampening factor: 0.30 (contextual signal is much weaker than direct test).
-- For incorrect overall performance (< 50% score), skip contextual inference
-- to avoid false positive boosts.

CREATE OR REPLACE FUNCTION public.bkt_contextual_inference(
    p_user_id uuid,
    p_language_id smallint,
    p_contextual_sense_ids integer[],   -- senses in transcript but NOT in questions
    p_score_ratio numeric               -- overall test score (0.0 to 1.0)
)
RETURNS integer  -- count of senses updated
LANGUAGE plpgsql
AS $function$
DECLARE
    v_dampening numeric := 0.30;
    v_updated integer := 0;
    v_sense_id integer;
    v_p_current numeric;
    v_p_post numeric;
    v_p_dampened numeric;
BEGIN
    -- Only apply contextual inference when user scored well (>= 50%)
    IF p_score_ratio < 0.50 THEN
        RETURN 0;
    END IF;

    -- Scale dampening by score: at 100% score, full 0.30 dampening;
    -- at 50% score, only 0.15 dampening
    v_dampening := 0.30 * p_score_ratio;

    FOREACH v_sense_id IN ARRAY p_contextual_sense_ids
    LOOP
        -- Get current p_known or frequency-based prior
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
            ON uvk.user_id = p_user_id AND uvk.sense_id = v_sense_id
        WHERE dws.id = v_sense_id;

        IF v_p_current IS NULL THEN
            CONTINUE;
        END IF;

        -- Compute what a full comprehension update would give
        v_p_post := bkt_update_comprehension(v_p_current, true);
        -- Apply dampening: only move a fraction of the way
        v_p_dampened := v_p_current + (v_p_post - v_p_current) * v_dampening;
        v_p_dampened := GREATEST(0.02, LEAST(0.98, v_p_dampened));

        -- Only update if the dampened value is higher (contextual = positive only)
        IF v_p_dampened > v_p_current THEN
            INSERT INTO user_vocabulary_knowledge
                (user_id, sense_id, language_id, p_known, status,
                 evidence_count, comprehension_correct,
                 last_evidence_at, updated_at)
            VALUES (
                p_user_id, v_sense_id, p_language_id,
                v_p_dampened, bkt_status(v_p_dampened),
                1, 1, NOW(), NOW()
            )
            ON CONFLICT (user_id, sense_id) DO UPDATE SET
                p_known = CASE
                    WHEN EXCLUDED.p_known > user_vocabulary_knowledge.p_known
                    THEN EXCLUDED.p_known
                    ELSE user_vocabulary_knowledge.p_known
                END,
                status = CASE
                    WHEN user_vocabulary_knowledge.status = 'user_marked_unknown'
                    THEN 'user_marked_unknown'
                    WHEN EXCLUDED.p_known > user_vocabulary_knowledge.p_known
                    THEN EXCLUDED.status
                    ELSE user_vocabulary_knowledge.status
                END,
                last_evidence_at = NOW(),
                updated_at = NOW();

            v_updated := v_updated + 1;
        END IF;
    END LOOP;

    RETURN v_updated;
END;
$function$;
