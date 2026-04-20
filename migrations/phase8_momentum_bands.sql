-- ============================================================================
-- Phase 8: Momentum Bands — Family-Based Vocabulary Acquisition
-- Date: 2026-04-18
-- Prerequisites: vocabulary_ladder_schema.sql, phase4_schema_evolution.sql,
--                phase7_bkt_improvements.sql
--
-- Implements the Momentum Bands progression system:
--   - Per-family BKT confidence tracking (5 cognitive families)
--   - Ring-based progression (4 rings with threshold gates)
--   - Dynamic scheduling via momentum bands (low/medium/high)
--   - FSRS-4.5 in PostgreSQL for post-mastery maintenance
--   - Atomic attempt recording with family confidence updates
--   - A/B exercise variant support in word_assets
--
-- Sections:
--   8.1  Schema: user_word_ladder additions
--   8.2  Schema: word_state CHECK update
--   8.3  Schema: word_assets CHECK for A/B variants
--   8.4  Helpers: level/ring/family mapping functions
--   8.5  FSRS-4.5: fsrs_schedule_review RPC
--   8.6  Core: ladder_record_attempt RPC
--   8.7  Gate: ladder_pass_gate RPC
--   8.8  Graduation: ladder_graduate RPC (stress test → mastery → FSRS init)
-- ============================================================================


-- ============================================================================
-- 8.1 Schema: Extend user_word_ladder
-- ============================================================================
-- Phase 4 added: first_try_success_count, first_try_failure_count,
-- consecutive_failures, total_attempts, word_state, last_success_session_date,
-- review_due_at. Those columns are kept and repurposed.
--
-- New columns:
--   family_confidence     — per-family BKT confidence scores (JSONB)
--   gates_passed          — gate completion status (JSONB)
--   current_ring          — which ring the word is working through (1-4)
--   stress_test_score     — last stress test score (NULL if not taken)
--   last_exercised_family — tracks consecutive-failure family matching

ALTER TABLE public.user_word_ladder
    ADD COLUMN IF NOT EXISTS family_confidence jsonb NOT NULL
        DEFAULT '{"form_recognition":0.10,"meaning_recall":0.10,"form_production":0.10,"collocation":0.10,"semantic_discrimination":0.10,"contextual_use":0.10}'::jsonb,
    ADD COLUMN IF NOT EXISTS gates_passed jsonb NOT NULL
        DEFAULT '{"gate_a":false,"gate_b":false}'::jsonb,
    ADD COLUMN IF NOT EXISTS current_ring integer NOT NULL DEFAULT 1
        CHECK (current_ring BETWEEN 1 AND 4),
    ADD COLUMN IF NOT EXISTS stress_test_score real,
    ADD COLUMN IF NOT EXISTS last_exercised_family text;

CREATE INDEX IF NOT EXISTS idx_user_word_ladder_ring
    ON public.user_word_ladder(user_id, current_ring);


-- ============================================================================
-- 8.2 Update word_state CHECK constraint
-- ============================================================================
-- Phase 4: ('new','active','fragile','stable','mastered')
-- Momentum Bands: ('new','active','gated','pre_mastery','relearning','mastered')

UPDATE public.user_word_ladder SET word_state = 'active'
WHERE word_state IN ('fragile', 'stable');

ALTER TABLE public.user_word_ladder
    DROP CONSTRAINT IF EXISTS user_word_ladder_word_state_check;
ALTER TABLE public.user_word_ladder
    ADD CONSTRAINT user_word_ladder_word_state_check
    CHECK (word_state IN ('new', 'active', 'gated', 'pre_mastery', 'relearning', 'mastered'));


-- ============================================================================
-- 8.3 Expand word_assets asset_type CHECK for A/B variants
-- ============================================================================
-- Original types remain valid for backward compatibility with existing assets.
-- New A/B suffixed types support dual-variant generation.

ALTER TABLE public.word_assets DROP CONSTRAINT IF EXISTS word_assets_asset_type_check;
ALTER TABLE public.word_assets ADD CONSTRAINT word_assets_asset_type_check
    CHECK (asset_type IN (
        'prompt1_core',
        'prompt2_exercises', 'prompt2_exercises_A', 'prompt2_exercises_B',
        'prompt3_transforms', 'prompt3_transforms_A', 'prompt3_transforms_B'
    ));


-- ============================================================================
-- 8.4 Helper functions: level/ring/family mapping
-- ============================================================================

-- Map ladder level (1-9) → cognitive family name
CREATE OR REPLACE FUNCTION public.ladder_get_family(p_level integer)
RETURNS text
LANGUAGE sql IMMUTABLE AS $$
    SELECT CASE p_level
        WHEN 1 THEN 'form_recognition'
        WHEN 2 THEN 'form_recognition'
        WHEN 3 THEN 'meaning_recall'
        WHEN 4 THEN 'form_production'
        WHEN 5 THEN 'collocation'
        WHEN 6 THEN 'semantic_discrimination'
        WHEN 7 THEN 'semantic_discrimination'
        WHEN 8 THEN 'collocation'
        WHEN 9 THEN 'form_production'
    END;
$$;

-- Map ladder level (1-9) → ring number (1-4)
CREATE OR REPLACE FUNCTION public.ladder_get_ring(p_level integer)
RETURNS integer
LANGUAGE sql IMMUTABLE AS $$
    SELECT CASE
        WHEN p_level BETWEEN 1 AND 2 THEN 1
        WHEN p_level BETWEEN 3 AND 5 THEN 2
        WHEN p_level BETWEEN 6 AND 7 THEN 3
        WHEN p_level BETWEEN 8 AND 9 THEN 4
    END;
$$;

-- Get the required cognitive families for a ring, considering active levels.
-- Concrete nouns skip collocation levels (5, 8), so collocation may not
-- be required for their ring clearing.
CREATE OR REPLACE FUNCTION public.ladder_ring_families(
    p_ring integer,
    p_active_levels integer[]
)
RETURNS text[]
LANGUAGE plpgsql IMMUTABLE AS $function$
DECLARE
    v_families text[] := ARRAY[]::text[];
BEGIN
    IF p_ring = 1 THEN
        IF 1 = ANY(p_active_levels) OR 2 = ANY(p_active_levels) THEN
            v_families := array_append(v_families, 'form_recognition');
        END IF;
    ELSIF p_ring = 2 THEN
        IF 3 = ANY(p_active_levels) THEN
            v_families := array_append(v_families, 'meaning_recall');
        END IF;
        IF 4 = ANY(p_active_levels) THEN
            v_families := array_append(v_families, 'form_production');
        END IF;
        IF 5 = ANY(p_active_levels) THEN
            v_families := array_append(v_families, 'collocation');
        END IF;
    ELSIF p_ring = 3 THEN
        IF 6 = ANY(p_active_levels) OR 7 = ANY(p_active_levels) THEN
            v_families := array_append(v_families, 'semantic_discrimination');
        END IF;
    ELSIF p_ring = 4 THEN
        IF 8 = ANY(p_active_levels) THEN
            v_families := array_append(v_families, 'collocation');
        END IF;
        IF 9 = ANY(p_active_levels) THEN
            v_families := array_append(v_families, 'form_production');
        END IF;
    END IF;
    RETURN v_families;
END;
$function$;

-- Compute overall p_known as weighted aggregate of family confidences.
-- Weights: form_recognition=0.12, meaning_recall=0.18, form_production=0.20,
--          collocation=0.16, semantic_discrimination=0.16, contextual_use=0.18
CREATE OR REPLACE FUNCTION public.ladder_compute_p_known(p_fc jsonb)
RETURNS numeric
LANGUAGE sql IMMUTABLE AS $$
    SELECT ROUND((
        0.12 * COALESCE((p_fc->>'form_recognition')::numeric, 0.10) +
        0.18 * COALESCE((p_fc->>'meaning_recall')::numeric, 0.10) +
        0.20 * COALESCE((p_fc->>'form_production')::numeric, 0.10) +
        0.16 * COALESCE((p_fc->>'collocation')::numeric, 0.10) +
        0.16 * COALESCE((p_fc->>'semantic_discrimination')::numeric, 0.10) +
        0.18 * COALESCE((p_fc->>'contextual_use')::numeric, 0.10)
    )::numeric, 4);
$$;


-- ============================================================================
-- 8.5 FSRS-4.5: fsrs_schedule_review
-- ============================================================================
-- Port of services/vocabulary/fsrs.py to PostgreSQL.
-- Used for post-mastery maintenance scheduling.
--
-- Input: current card state + rating (1=again, 2=hard, 3=good, 4=easy)
-- Output: JSONB with new stability, difficulty, due_date, state, reps, lapses
--
-- Weight indices are 1-based (Python 0-based + 1).

CREATE OR REPLACE FUNCTION public.fsrs_schedule_review(
    p_stability real,
    p_difficulty real,
    p_last_review date,
    p_reps integer,
    p_lapses integer,
    p_state text,          -- 'new', 'learning', 'review', 'relearning'
    p_rating integer,      -- 1=again, 2=hard, 3=good, 4=easy
    p_review_date date DEFAULT CURRENT_DATE
)
RETURNS jsonb
LANGUAGE plpgsql
STABLE
AS $function$
DECLARE
    -- FSRS-4.5 default weights (17 parameters, 1-indexed)
    v_w real[] := ARRAY[
        0.4, 0.6, 2.4, 5.8,        -- [1-4]  initial stability: again/hard/good/easy
        4.93, 0.94, 0.86, 0.01,    -- [5-8]  difficulty params
        1.49, 0.14, 0.94,          -- [9-11] short-term + success stability
        2.18, 0.05, 0.34,          -- [12-14] success/failure stability
        1.26, 0.29, 2.61           -- [15-17] failure params
    ];
    v_retention real := 0.9;
    v_max_interval integer := 365;

    v_s real;              -- new stability
    v_d real;              -- new difficulty
    v_interval integer;
    v_new_state text;
    v_new_reps integer;
    v_new_lapses integer;
    v_new_due date;
    v_elapsed integer;
    v_retrievability real;
    v_delta real;
    v_d_new real;
    v_s_new real;
BEGIN
    -- =================================================================
    -- STATE: NEW — first ever review
    -- =================================================================
    IF p_state = 'new' THEN
        -- Initial stability from rating
        v_s := v_w[p_rating];

        -- Initial difficulty: w[5] - (rating-3)*w[6], clamped [1,10]
        v_d := LEAST(10.0, GREATEST(1.0,
            v_w[5] - (p_rating - 3) * v_w[6]));

        v_new_reps := 1;
        v_new_lapses := CASE WHEN p_rating = 1 THEN 1 ELSE 0 END;

        IF p_rating <= 2 THEN
            -- Again or Hard → learning state, review tomorrow
            v_new_state := 'learning';
            v_new_due := p_review_date + 1;
        ELSE
            -- Good or Easy → review state
            v_new_state := 'review';
            v_interval := LEAST(GREATEST(
                ROUND(v_s * 9.0 * (1.0 / v_retention - 1.0))::integer, 1
            ), v_max_interval);
            IF p_rating = 4 THEN
                v_interval := GREATEST(v_interval, 4);
            END IF;
            v_new_due := p_review_date + v_interval;
        END IF;

    -- =================================================================
    -- STATE: LEARNING / RELEARNING
    -- =================================================================
    ELSIF p_state IN ('learning', 'relearning') THEN
        -- Next difficulty
        v_delta := -(p_rating - 3) * v_w[7];
        v_d_new := p_difficulty + v_delta * (v_w[8] * (10.0 - p_difficulty));
        IF v_w[8] > 0 THEN
            v_d_new := v_w[5] * (1.0 - v_w[8]) + v_d_new * v_w[8];
        END IF;
        v_d := LEAST(10.0, GREATEST(1.0, v_d_new));

        -- Short-term stability
        IF p_rating = 1 THEN
            v_s := v_w[1];  -- reset to AGAIN initial stability
        ELSE
            v_s := p_stability * EXP(v_w[9] * (p_rating - 3 + v_w[10]));
        END IF;

        v_new_reps := p_reps + 1;
        v_new_lapses := p_lapses + CASE WHEN p_rating = 1 THEN 1 ELSE 0 END;

        IF p_rating = 1 THEN
            v_new_state := CASE WHEN p_state = 'review'
                THEN 'relearning' ELSE 'learning' END;
            v_new_due := p_review_date + 1;
        ELSIF p_rating = 2 THEN
            v_new_state := p_state;
            v_new_due := p_review_date + 1;
        ELSE
            -- Good or Easy → graduate to review
            v_new_state := 'review';
            v_interval := LEAST(GREATEST(
                ROUND(v_s * 9.0 * (1.0 / v_retention - 1.0))::integer, 1
            ), v_max_interval);
            IF p_rating = 4 THEN
                v_interval := GREATEST(v_interval, 4);
            END IF;
            v_new_due := p_review_date + v_interval;
        END IF;

    -- =================================================================
    -- STATE: REVIEW (the common case for post-mastery maintenance)
    -- =================================================================
    ELSE
        v_elapsed := COALESCE(p_review_date - p_last_review, 0);

        -- Next difficulty
        v_delta := -(p_rating - 3) * v_w[7];
        v_d_new := p_difficulty + v_delta * (v_w[8] * (10.0 - p_difficulty));
        IF v_w[8] > 0 THEN
            v_d_new := v_w[5] * (1.0 - v_w[8]) + v_d_new * v_w[8];
        END IF;
        v_d := LEAST(10.0, GREATEST(1.0, v_d_new));

        v_new_reps := p_reps + 1;

        IF p_rating = 1 THEN
            -- LAPSE: stability after failure
            v_retrievability := CASE WHEN p_stability > 0
                THEN EXP(-v_elapsed::real / p_stability) ELSE 0 END;
            v_s := GREATEST(
                v_w[14] * POWER(v_d, -v_w[15]) *
                (POWER(p_stability + 1, v_w[16]) - 1) *
                EXP((1.0 - v_retrievability) * v_w[17]),
                0.1);

            v_new_state := 'relearning';
            v_new_lapses := p_lapses + 1;
            v_new_due := p_review_date + 1;
        ELSE
            -- SUCCESS: stability after success
            v_retrievability := CASE WHEN p_stability > 0
                THEN EXP(-v_elapsed::real / p_stability) ELSE 0 END;
            v_s_new := p_stability * (
                1.0 + EXP(v_w[11]) *
                (11.0 - v_d) *
                POWER(p_stability, -v_w[12]) *
                (EXP((1.0 - v_retrievability) * v_w[13]) - 1.0) *
                CASE WHEN p_rating = 4 THEN v_w[16] ELSE 1.0 END
            );
            v_s := GREATEST(v_s_new, p_stability + 0.1);

            v_new_state := 'review';
            v_new_lapses := p_lapses;

            v_interval := LEAST(GREATEST(
                ROUND(v_s * 9.0 * (1.0 / v_retention - 1.0))::integer, 1
            ), v_max_interval);

            IF p_rating = 2 THEN
                v_interval := GREATEST(v_interval, 1);
            ELSIF p_rating = 4 THEN
                v_interval := GREATEST(v_interval, v_elapsed + 1);
            END IF;

            v_new_due := p_review_date + v_interval;
        END IF;
    END IF;

    RETURN jsonb_build_object(
        'stability', ROUND(v_s::numeric, 4),
        'difficulty', ROUND(v_d::numeric, 4),
        'due_date', v_new_due,
        'state', v_new_state,
        'reps', v_new_reps,
        'lapses', v_new_lapses
    );
END;
$function$;


-- ============================================================================
-- 8.6 Core: ladder_record_attempt
-- ============================================================================
-- Atomic RPC for recording a vocabulary exercise attempt and updating all
-- progression state in a single transaction.
--
-- Flow:
--   1. Resolve exercise metadata (type, level, language)
--   2. Get or create user_word_ladder row (locked for atomicity)
--   3. Insert exercise_attempt (triggers sync to user_exercise_history)
--   4. Update family confidence (BKT learn/slip rates)
--   5. Handle post-mastery lapse OR normal scheduling+advancement
--   6. Update user_word_ladder
--   7. Update overall BKT (user_vocabulary_knowledge)
--   8. Return comprehensive result

CREATE OR REPLACE FUNCTION public.ladder_record_attempt(
    p_user_id uuid,
    p_sense_id integer,
    p_exercise_id uuid,
    p_is_correct boolean,
    p_is_first_attempt boolean,
    p_time_taken_ms integer DEFAULT NULL,
    p_language_id smallint DEFAULT NULL,
    p_exercise_type text DEFAULT NULL,
    p_ladder_level integer DEFAULT NULL,
    p_exercise_context text DEFAULT 'standard'  -- 'standard', 'gate', 'stress_test'
)
RETURNS jsonb
LANGUAGE plpgsql
AS $function$
DECLARE
    v_ladder RECORD;
    v_exercise_type text;
    v_ladder_level integer;
    v_language_id smallint;
    v_family text;
    v_fc jsonb;
    v_current_conf numeric;
    v_new_conf numeric;
    v_learn_rate numeric;
    v_slip_rate numeric;
    v_p_known_overall numeric;
    v_review_due timestamptz;
    v_word_state text;
    v_current_ring integer;
    v_gates jsonb;
    v_ring_cleared boolean;
    v_gate_pending text;
    v_stress_test_ready boolean := false;
    v_required_families text[];
    v_min_conf_threshold numeric;
    v_i integer;
    v_old_p_known numeric;
    v_new_bkt numeric;
    v_semantic_class text;
    v_active_levels integer[];
    v_fsrs_result jsonb;
    v_is_lapse boolean := false;
BEGIN
    -- =================================================================
    -- 1. Resolve exercise metadata if not provided
    -- =================================================================
    IF p_exercise_type IS NULL OR p_ladder_level IS NULL OR p_language_id IS NULL THEN
        SELECT e.exercise_type, e.ladder_level, e.language_id
        INTO v_exercise_type, v_ladder_level, v_language_id
        FROM exercises e WHERE e.id = p_exercise_id;
    END IF;
    v_exercise_type := COALESCE(p_exercise_type, v_exercise_type);
    v_ladder_level := COALESCE(p_ladder_level, v_ladder_level);
    v_language_id := COALESCE(p_language_id, v_language_id);

    -- Determine cognitive family for this level
    v_family := ladder_get_family(v_ladder_level);

    -- =================================================================
    -- 2. Get or create user_word_ladder row (locked for atomic update)
    -- =================================================================
    SELECT * INTO v_ladder FROM user_word_ladder
    WHERE user_id = p_user_id AND sense_id = p_sense_id
    FOR UPDATE;

    IF NOT FOUND THEN
        -- Look up semantic class for active_levels computation
        SELECT dv.semantic_class INTO v_semantic_class
        FROM dim_word_senses dws
        JOIN dim_vocabulary dv ON dv.id = dws.vocab_id
        WHERE dws.id = p_sense_id;

        v_active_levels := CASE
            WHEN v_semantic_class = 'concrete_noun'
            THEN ARRAY[1,2,3,4,6,7,9]
            ELSE ARRAY[1,2,3,4,5,6,7,8,9]
        END;

        INSERT INTO user_word_ladder (
            user_id, sense_id, current_level, active_levels,
            word_state, current_ring
        ) VALUES (
            p_user_id, p_sense_id, 1, v_active_levels, 'new', 1
        );

        SELECT * INTO v_ladder FROM user_word_ladder
        WHERE user_id = p_user_id AND sense_id = p_sense_id
        FOR UPDATE;
    END IF;

    -- =================================================================
    -- 3. Insert exercise attempt
    --    (Phase 4 trigger auto-syncs to user_exercise_history)
    -- =================================================================
    INSERT INTO exercise_attempts (
        user_id, exercise_id, sense_id, exercise_type,
        is_correct, is_first_attempt, ladder_level, time_taken_ms
    ) VALUES (
        p_user_id, p_exercise_id, p_sense_id, v_exercise_type,
        p_is_correct, p_is_first_attempt, v_ladder_level, p_time_taken_ms
    );

    -- =================================================================
    -- 4. Update family confidence (BKT learn/slip)
    -- =================================================================
    v_fc := v_ladder.family_confidence;

    -- Learn/slip rates vary by exercise context
    CASE p_exercise_context
        WHEN 'gate' THEN
            v_learn_rate := 0.18; v_slip_rate := 0.10;
        WHEN 'stress_test' THEN
            v_learn_rate := 0.20; v_slip_rate := 0.12;
        ELSE  -- 'standard'
            v_learn_rate := 0.15; v_slip_rate := 0.12;
    END CASE;

    v_current_conf := COALESCE((v_fc->>v_family)::numeric, 0.10);

    IF p_is_correct THEN
        v_new_conf := v_current_conf + (1.0 - v_current_conf) * v_learn_rate;
    ELSE
        v_new_conf := v_current_conf * (1.0 - v_slip_rate);
    END IF;
    v_new_conf := GREATEST(0.02, LEAST(0.98, v_new_conf));

    v_fc := jsonb_set(v_fc, ARRAY[v_family], to_jsonb(ROUND(v_new_conf, 4)));

    -- Compute weighted overall p_known
    v_p_known_overall := ladder_compute_p_known(v_fc);

    -- =================================================================
    -- 5. Branching: post-mastery lapse vs normal progression
    -- =================================================================
    v_current_ring := v_ladder.current_ring;
    v_gates := v_ladder.gates_passed;
    v_gate_pending := NULL;

    IF v_ladder.word_state = 'mastered' AND NOT p_is_correct THEN
        -- ---------------------------------------------------------
        -- LAPSE PATH: mastered word failed → relearning
        -- ---------------------------------------------------------
        v_is_lapse := true;

        -- Extra 30% penalty on the failed family (on top of standard slip)
        v_new_conf := GREATEST(0.02, v_new_conf * 0.70);
        v_fc := jsonb_set(v_fc, ARRAY[v_family], to_jsonb(ROUND(v_new_conf, 4)));
        v_p_known_overall := ladder_compute_p_known(v_fc);

        v_word_state := 'relearning';
        v_review_due := (CURRENT_DATE + 1)::timestamptz;

        -- Update FSRS with AGAIN rating (if flashcard exists)
        SELECT fsrs_schedule_review(
            uf.stability, uf.difficulty, uf.last_review,
            uf.reps, uf.lapses, uf.state, 1, CURRENT_DATE
        ) INTO v_fsrs_result
        FROM user_flashcards uf
        WHERE uf.user_id = p_user_id AND uf.sense_id = p_sense_id;

        IF v_fsrs_result IS NOT NULL THEN
            UPDATE user_flashcards SET
                stability = (v_fsrs_result->>'stability')::real,
                difficulty = (v_fsrs_result->>'difficulty')::real,
                due_date = (v_fsrs_result->>'due_date')::date,
                state = v_fsrs_result->>'state',
                reps = (v_fsrs_result->>'reps')::integer,
                lapses = (v_fsrs_result->>'lapses')::integer,
                last_review = CURRENT_DATE,
                updated_at = now()
            WHERE user_id = p_user_id AND sense_id = p_sense_id;
        END IF;

    ELSE
        -- ---------------------------------------------------------
        -- NORMAL PATH: scheduling + ring clearing + word_state
        -- ---------------------------------------------------------

        -- Momentum band scheduling
        IF v_p_known_overall < 0.45 THEN
            v_review_due := (CURRENT_DATE + 1)::timestamptz;  -- Band 1: low
        ELSIF v_p_known_overall < 0.75 THEN
            v_review_due := (CURRENT_DATE + 1)::timestamptz;  -- Band 2: medium
        ELSE
            v_review_due := (CURRENT_DATE + 2)::timestamptz;  -- Band 3: high
        END IF;

        -- Override: always come back tomorrow on first-attempt failure
        IF NOT p_is_correct AND p_is_first_attempt THEN
            v_review_due := (CURRENT_DATE + 1)::timestamptz;
        END IF;

        -- Check if current ring's families meet confidence threshold
        v_required_families := ladder_ring_families(v_current_ring, v_ladder.active_levels);
        v_min_conf_threshold := CASE
            WHEN v_current_ring <= 2 THEN 0.50  -- Gate A threshold
            WHEN v_current_ring = 3 THEN 0.65   -- Gate B threshold
            ELSE 0.72                            -- Stress test threshold
        END;

        v_ring_cleared := true;
        IF v_required_families IS NOT NULL
           AND array_length(v_required_families, 1) > 0 THEN
            FOR v_i IN 1..array_length(v_required_families, 1) LOOP
                IF COALESCE((v_fc->>v_required_families[v_i])::numeric, 0.10)
                   < v_min_conf_threshold THEN
                    v_ring_cleared := false;
                    EXIT;
                END IF;
            END LOOP;
        END IF;

        -- Ring transitions
        IF v_ring_cleared THEN
            IF v_current_ring = 1 THEN
                -- R1 → R2: no gate needed, advance immediately
                v_current_ring := 2;
            ELSIF v_current_ring = 2
                  AND NOT COALESCE((v_gates->>'gate_a')::boolean, false) THEN
                v_gate_pending := 'gate_a';
            ELSIF v_current_ring = 3
                  AND NOT COALESCE((v_gates->>'gate_b')::boolean, false) THEN
                v_gate_pending := 'gate_b';
            END IF;
        END IF;

        -- Compute word_state
        v_word_state := CASE
            -- Keep mastered if still mastered (successful maintenance review)
            WHEN v_ladder.word_state = 'mastered'
                THEN 'mastered'
            -- Pre-mastery: R4 complete + Gate B passed + high p_known
            WHEN v_current_ring >= 4
                AND COALESCE((v_gates->>'gate_b')::boolean, false)
                AND v_ring_cleared
                AND v_p_known_overall >= 0.88
                THEN 'pre_mastery'
            -- Gated: waiting for a threshold gate
            WHEN v_gate_pending IS NOT NULL
                THEN 'gated'
            -- New: very low knowledge, early ring
            WHEN v_current_ring <= 1 AND v_p_known_overall < 0.20
                THEN 'new'
            -- Default: actively learning
            ELSE 'active'
        END;

        -- Check stress test readiness (only in pre_mastery)
        IF v_word_state = 'pre_mastery' THEN
            v_stress_test_ready := true;
            -- All active families must have confidence >= 0.72
            IF (1 = ANY(v_ladder.active_levels) OR 2 = ANY(v_ladder.active_levels))
               AND COALESCE((v_fc->>'form_recognition')::numeric, 0.10) < 0.72 THEN
                v_stress_test_ready := false;
            END IF;
            IF 3 = ANY(v_ladder.active_levels)
               AND COALESCE((v_fc->>'meaning_recall')::numeric, 0.10) < 0.72 THEN
                v_stress_test_ready := false;
            END IF;
            IF (4 = ANY(v_ladder.active_levels) OR 9 = ANY(v_ladder.active_levels))
               AND COALESCE((v_fc->>'form_production')::numeric, 0.10) < 0.72 THEN
                v_stress_test_ready := false;
            END IF;
            IF (5 = ANY(v_ladder.active_levels) OR 8 = ANY(v_ladder.active_levels))
               AND COALESCE((v_fc->>'collocation')::numeric, 0.10) < 0.72 THEN
                v_stress_test_ready := false;
            END IF;
            IF (6 = ANY(v_ladder.active_levels) OR 7 = ANY(v_ladder.active_levels))
               AND COALESCE((v_fc->>'semantic_discrimination')::numeric, 0.10) < 0.72 THEN
                v_stress_test_ready := false;
            END IF;
        END IF;
    END IF;

    -- =================================================================
    -- 6. Update user_word_ladder
    -- =================================================================
    UPDATE user_word_ladder SET
        family_confidence = v_fc,
        current_ring = v_current_ring,
        word_state = v_word_state,
        review_due_at = v_review_due,
        total_attempts = COALESCE(total_attempts, 0) + 1,
        first_try_success_count = CASE
            WHEN p_is_first_attempt AND p_is_correct
            THEN COALESCE(first_try_success_count, 0) + 1
            ELSE COALESCE(first_try_success_count, 0)
        END,
        first_try_failure_count = CASE
            WHEN p_is_first_attempt AND NOT p_is_correct
            THEN COALESCE(first_try_failure_count, 0) + 1
            ELSE COALESCE(first_try_failure_count, 0)
        END,
        consecutive_failures = CASE
            WHEN p_is_correct THEN 0
            WHEN p_is_first_attempt AND NOT p_is_correct
                AND v_family = COALESCE(last_exercised_family, '')
            THEN COALESCE(consecutive_failures, 0) + 1
            WHEN p_is_first_attempt AND NOT p_is_correct
            THEN 1
            ELSE COALESCE(consecutive_failures, 0)
        END,
        last_success_session_date = CASE
            WHEN p_is_correct AND p_is_first_attempt THEN CURRENT_DATE
            ELSE last_success_session_date
        END,
        last_exercised_family = v_family,
        updated_at = now()
    WHERE user_id = p_user_id AND sense_id = p_sense_id;

    -- =================================================================
    -- 7. Update overall BKT (user_vocabulary_knowledge)
    -- =================================================================
    SELECT uvk.p_known INTO v_old_p_known
    FROM user_vocabulary_knowledge uvk
    WHERE uvk.user_id = p_user_id AND uvk.sense_id = p_sense_id;

    v_new_bkt := bkt_update_exercise(
        COALESCE(v_old_p_known, 0.10), p_is_correct, v_exercise_type
    );

    INSERT INTO user_vocabulary_knowledge (
        user_id, sense_id, language_id, p_known, status,
        evidence_count, last_evidence_at, updated_at
    ) VALUES (
        p_user_id, p_sense_id, v_language_id, v_new_bkt,
        bkt_status(v_new_bkt), 1, now(), now()
    )
    ON CONFLICT (user_id, sense_id) DO UPDATE SET
        p_known = EXCLUDED.p_known,
        status = CASE
            WHEN user_vocabulary_knowledge.status = 'user_marked_unknown'
            THEN 'user_marked_unknown'
            ELSE bkt_status(EXCLUDED.p_known)
        END,
        evidence_count = user_vocabulary_knowledge.evidence_count + 1,
        last_evidence_at = now(),
        updated_at = now();

    -- Apply additional BKT lapse penalty for mastered words that failed
    IF v_is_lapse THEN
        PERFORM bkt_apply_lapse_penalty(p_user_id, p_sense_id);
    END IF;

    -- =================================================================
    -- 8. Return result
    -- =================================================================
    RETURN jsonb_build_object(
        'is_correct', p_is_correct,
        'family', v_family,
        'family_confidence', v_fc,
        'p_known_overall', v_p_known_overall,
        'current_ring', v_current_ring,
        'word_state', v_word_state,
        'review_due_at', v_review_due,
        'requeue', NOT p_is_correct AND p_is_first_attempt,
        'gate_pending', v_gate_pending,
        'stress_test_ready', v_stress_test_ready,
        'bkt_p_known', ROUND(v_new_bkt::numeric, 4),
        'is_lapse', v_is_lapse
    );
END;
$function$;


-- ============================================================================
-- 8.7 Gate: ladder_pass_gate
-- ============================================================================
-- Called by Python after evaluating a gate battery (3 exercises).
-- Marks the gate as passed, advances the ring, updates word_state.
-- If the gate fails, Python should call ladder_record_attempt for each
-- exercise in the battery (which applies gate BKT rates) — no separate
-- failure function needed.

CREATE OR REPLACE FUNCTION public.ladder_pass_gate(
    p_user_id uuid,
    p_sense_id integer,
    p_gate_name text  -- 'gate_a' or 'gate_b'
)
RETURNS jsonb
LANGUAGE plpgsql
AS $function$
DECLARE
    v_ladder RECORD;
    v_gates jsonb;
    v_new_ring integer;
    v_word_state text;
    v_p_known numeric;
BEGIN
    SELECT * INTO v_ladder FROM user_word_ladder
    WHERE user_id = p_user_id AND sense_id = p_sense_id
    FOR UPDATE;

    IF NOT FOUND THEN
        RETURN jsonb_build_object('error', 'ladder_not_found');
    END IF;

    v_gates := v_ladder.gates_passed;

    -- Mark gate as passed
    v_gates := jsonb_set(v_gates, ARRAY[p_gate_name], 'true'::jsonb);

    -- Advance ring
    v_new_ring := CASE p_gate_name
        WHEN 'gate_a' THEN 3
        WHEN 'gate_b' THEN 4
        ELSE v_ladder.current_ring
    END;

    -- Compute new word state
    v_p_known := ladder_compute_p_known(v_ladder.family_confidence);
    v_word_state := CASE
        WHEN v_new_ring >= 4
            AND COALESCE((v_gates->>'gate_b')::boolean, false)
            AND v_p_known >= 0.88
            THEN 'pre_mastery'
        ELSE 'active'
    END;

    UPDATE user_word_ladder SET
        gates_passed = v_gates,
        current_ring = v_new_ring,
        word_state = v_word_state,
        review_due_at = (CURRENT_DATE + 1)::timestamptz,
        updated_at = now()
    WHERE user_id = p_user_id AND sense_id = p_sense_id;

    RETURN jsonb_build_object(
        'gate', p_gate_name,
        'passed', true,
        'new_ring', v_new_ring,
        'word_state', v_word_state,
        'p_known_overall', v_p_known
    );
END;
$function$;


-- ============================================================================
-- 8.8 Graduation: ladder_graduate
-- ============================================================================
-- Called after a stress test battery passes. Transitions the word to 'mastered'
-- and initializes FSRS for long-term maintenance scheduling.
--
-- FSRS initialization from acquisition trace:
--   stability = 7 + 21 × p_known + 6 × stress_bonus, capped [7, 34]
--   difficulty = 8 - 5 × p_known + family_variance_penalty, clamped [2, 8.5]
--   due_date = today + round(stability × 0.6)

CREATE OR REPLACE FUNCTION public.ladder_graduate(
    p_user_id uuid,
    p_sense_id integer,
    p_stress_test_score real,  -- 0.0 to 1.0 (e.g. 6/8 = 0.75)
    p_language_id smallint
)
RETURNS jsonb
LANGUAGE plpgsql
AS $function$
DECLARE
    v_ladder RECORD;
    v_fc jsonb;
    v_p_known numeric;
    v_stress_bonus real;
    v_stability real;
    v_difficulty real;
    v_family_stddev numeric;
    v_variance_penalty real;
    v_due_date date;
BEGIN
    SELECT * INTO v_ladder FROM user_word_ladder
    WHERE user_id = p_user_id AND sense_id = p_sense_id
    FOR UPDATE;

    IF NOT FOUND THEN
        RETURN jsonb_build_object('error', 'ladder_not_found');
    END IF;

    v_fc := v_ladder.family_confidence;
    v_p_known := ladder_compute_p_known(v_fc);

    -- Stress bonus tiers
    v_stress_bonus := CASE
        WHEN p_stress_test_score >= 0.90 THEN 1.0
        WHEN p_stress_test_score >= 0.80 THEN 0.5
        ELSE 0.0
    END;

    -- FSRS stability from acquisition trace
    v_stability := 7.0 + 21.0 * v_p_known::real + 6.0 * v_stress_bonus;
    v_stability := LEAST(GREATEST(v_stability, 7.0), 34.0);

    -- Family variance penalty for difficulty
    SELECT stddev_pop(kv.value::numeric) INTO v_family_stddev
    FROM jsonb_each_text(v_fc) AS kv
    WHERE kv.key IN (
        'form_recognition', 'meaning_recall', 'form_production',
        'collocation', 'semantic_discrimination'
    );
    v_variance_penalty := LEAST(1.5, COALESCE(v_family_stddev, 0) * 4.0);

    -- FSRS difficulty from acquisition trace
    v_difficulty := 8.0 - 5.0 * v_p_known::real + v_variance_penalty;
    v_difficulty := LEAST(GREATEST(v_difficulty, 2.0), 8.5);

    -- First maintenance review: earlier than full stability (safer at handoff)
    v_due_date := CURRENT_DATE + ROUND(v_stability * 0.6)::integer;

    -- Update user_word_ladder → mastered
    UPDATE user_word_ladder SET
        word_state = 'mastered',
        stress_test_score = p_stress_test_score,
        review_due_at = NULL,  -- FSRS takes over scheduling
        updated_at = now()
    WHERE user_id = p_user_id AND sense_id = p_sense_id;

    -- Initialize or update FSRS flashcard
    INSERT INTO user_flashcards (
        user_id, sense_id, language_id,
        stability, difficulty, due_date, last_review,
        reps, lapses, state,
        created_at, updated_at
    ) VALUES (
        p_user_id, p_sense_id, p_language_id,
        v_stability, v_difficulty, v_due_date, CURRENT_DATE,
        1, 0, 'review',
        now(), now()
    )
    ON CONFLICT (user_id, sense_id) DO UPDATE SET
        stability = EXCLUDED.stability,
        difficulty = EXCLUDED.difficulty,
        due_date = EXCLUDED.due_date,
        last_review = EXCLUDED.last_review,
        state = EXCLUDED.state,
        lapses = 0,
        reps = GREATEST(user_flashcards.reps, 1),
        updated_at = now();

    RETURN jsonb_build_object(
        'word_state', 'mastered',
        'stress_test_score', p_stress_test_score,
        'fsrs_stability', ROUND(v_stability::numeric, 2),
        'fsrs_difficulty', ROUND(v_difficulty::numeric, 2),
        'fsrs_due_date', v_due_date,
        'p_known_overall', v_p_known
    );
END;
$function$;


-- ============================================================================
-- 8.9 Update Prompt 1 template: 6 → 10 sentences
-- ============================================================================
-- Deactivate old v1 template and insert v2 with 10-sentence requirement.
-- Prompt 2 and 3 templates remain unchanged — they accept sentence indices
-- as parameters and don't hard-code the pool size.

UPDATE public.prompt_templates
SET is_active = false
WHERE task_name = 'vocab_prompt1_core' AND version = 1;

INSERT INTO public.prompt_templates (task_name, language_id, version, template_text, is_active)
VALUES (
    'vocab_prompt1_core',
    2,  -- English
    2,
    $PROMPT$Role: Expert computational linguist generating English vocabulary assets.

Target word: {word}
Existing definition: {existing_definition}
Learner tier: {complexity_tier}

Corpus sentences already approved (use these unchanged):
{corpus_sentences_json}

Task: Generate the base linguistic assets for this vocabulary word.

Rules:
1. All output values must be in English only.
2. Return the part of speech as one of: noun, verb, adjective, adverb, preposition, conjunction, pronoun, determiner, interjection.
3. Return the semantic class as one of: concrete_noun, abstract_noun, action_verb, state_verb, adjective, adverb, other.
4. Return a definition suitable for the learner tier. If an existing definition is provided and adequate, reuse it.
5. Return the primary collocate for this word if one is strongly relevant; otherwise return null.
6. Return exactly 10 correct example sentences total. Use the provided corpus sentences unchanged. Generate exactly {sentences_needed} additional sentences so the total is 10.
7. Every sentence must place the word in a meaningfully different context or sentence structure.
8. For each sentence, return the exact substring used for the target word as it appears in that sentence.
9. Return the IPA pronunciation.
10. Return the syllable count.
11. Return 3-5 morphological forms with labels (e.g. past_tense, plural, comparative).
12. Output valid JSON only using numeric keys.

Output schema:
"1" = part_of_speech (string)
"2" = semantic_class (string)
"3" = definition (string)
"4" = primary_collocate (string or null)
"5" = pronunciation (string, natural reading)
"6" = ipa (string)
"7" = syllable_count (integer)
"8" = array of sentence objects, each: {"1": full_sentence, "2": exact_target_substring, "3": source ("corpus" or "generated"), "4": complexity_tier}
"9" = array of morphological form objects, each: {"1": form_text, "2": form_label}$PROMPT$,
    true
)
ON CONFLICT (task_name, language_id, version) DO NOTHING;


-- ============================================================================
-- 8.10 Session builder: get_ladder_session
-- ============================================================================
-- Family-aware session builder. Returns candidate exercises ordered by
-- priority score. Handles:
--   - Words due for review (review_due_at <= now)
--   - Priority scoring: overdue × 0.35 + weakness × 0.25 + gate × 0.20
--                        + novelty × 0.10 + relapse × 0.10
--   - Family selection: weakest family in current ring
--   - Variant alternation: prefer unseen variant based on exercise_history
--   - Gate and stress test flagging
--   - Anti-repetition: skip exercises seen today

CREATE OR REPLACE FUNCTION public.get_ladder_session(
    p_user_id uuid,
    p_language_id smallint,
    p_count integer DEFAULT 20
)
RETURNS TABLE(
    out_sense_id integer,
    out_exercise_id uuid,
    out_exercise_type text,
    out_content jsonb,
    out_ladder_level integer,
    out_family text,
    out_p_known numeric,
    out_word_state text,
    out_lemma text,
    out_definition text,
    out_pronunciation text,
    out_variant text,
    out_is_gate boolean,
    out_is_stress_test boolean,
    out_priority numeric
)
LANGUAGE plpgsql
STABLE
AS $function$
DECLARE
    v_today date := CURRENT_DATE;
BEGIN
    RETURN QUERY
    WITH
    -- Step 1: Candidate words with ladder state
    candidates AS (
        SELECT
            uwl.sense_id,
            uwl.current_ring,
            uwl.word_state,
            uwl.family_confidence,
            uwl.gates_passed,
            uwl.active_levels,
            uwl.review_due_at,
            uwl.last_exercised_family,
            ladder_compute_p_known(uwl.family_confidence) AS p_known,
            -- Overdue score: days overdue, capped at 7
            LEAST(7, GREATEST(0,
                EXTRACT(DAY FROM now() - COALESCE(uwl.review_due_at, now()))
            )) / 7.0 AS overdue_score,
            -- Weakness score: max gap between weakest family and its threshold
            GREATEST(0,
                CASE uwl.current_ring
                    WHEN 1 THEN 0.50
                    WHEN 2 THEN 0.50
                    WHEN 3 THEN 0.65
                    ELSE 0.72
                END
                - LEAST(
                    COALESCE((uwl.family_confidence->>'form_recognition')::numeric, 0.10),
                    COALESCE((uwl.family_confidence->>'meaning_recall')::numeric, 0.10),
                    COALESCE((uwl.family_confidence->>'form_production')::numeric, 0.10),
                    COALESCE((uwl.family_confidence->>'collocation')::numeric, 0.10),
                    COALESCE((uwl.family_confidence->>'semantic_discrimination')::numeric, 0.10)
                )
            ) AS weakness_score,
            -- Gate urgency: 1 if gated, 0 otherwise
            CASE WHEN uwl.word_state = 'gated' THEN 1.0 ELSE 0.0 END AS gate_urgency,
            -- Novelty: prefer words with different family than last exercised
            CASE WHEN uwl.last_exercised_family IS NULL THEN 0.5 ELSE 0.0 END AS novelty_score,
            -- Relapse risk: higher if relearning
            CASE WHEN uwl.word_state = 'relearning' THEN 1.0 ELSE 0.0 END AS relapse_score
        FROM user_word_ladder uwl
        WHERE uwl.user_id = p_user_id
          AND uwl.word_state IN ('new', 'active', 'gated', 'pre_mastery', 'relearning')
          AND COALESCE(uwl.review_due_at, '1970-01-01'::timestamptz) <= now()
          -- Verify exercises exist for this word
          AND EXISTS (
              SELECT 1 FROM exercises e
              WHERE e.word_sense_id = uwl.sense_id
                AND e.language_id = p_language_id
                AND e.is_active = true
                AND e.ladder_level IS NOT NULL
          )
    ),
    -- Step 2: Compute priority and pick target family for each word
    scored AS (
        SELECT
            c.*,
            -- Priority score
            (0.35 * c.overdue_score
           + 0.25 * c.weakness_score
           + 0.20 * c.gate_urgency
           + 0.10 * c.novelty_score
           + 0.10 * c.relapse_score) AS priority,
            -- Target family: weakest in current ring
            (SELECT f FROM unnest(ladder_ring_families(c.current_ring, c.active_levels)) AS f
             ORDER BY COALESCE((c.family_confidence->>f)::numeric, 0.10) ASC
             LIMIT 1
            ) AS target_family
        FROM candidates c
    ),
    -- Step 3: Select top words by priority
    top_words AS (
        SELECT * FROM scored
        ORDER BY priority DESC
        LIMIT p_count
    ),
    -- Step 4: Find exercises seen today (anti-repetition)
    seen_today AS (
        SELECT DISTINCT exercise_id
        FROM user_exercise_history
        WHERE user_id = p_user_id
          AND language_id = p_language_id
          AND session_date = v_today
    ),
    -- Step 5: Join exercises, prefer unseen variant
    word_exercises AS (
        SELECT
            tw.sense_id,
            tw.p_known,
            tw.word_state,
            tw.priority,
            tw.target_family,
            tw.gates_passed,
            e.id AS exercise_id,
            e.exercise_type,
            e.content,
            e.ladder_level,
            ladder_get_family(e.ladder_level) AS family,
            COALESCE(e.tags->>'variant', 'A') AS variant,
            -- Prefer: matching family, then unseen variant, then not seen today
            ROW_NUMBER() OVER (
                PARTITION BY tw.sense_id
                ORDER BY
                    -- Prefer exercises in target family
                    CASE WHEN ladder_get_family(e.ladder_level) = tw.target_family
                         THEN 0 ELSE 1 END,
                    -- Prefer exercise not seen today
                    CASE WHEN st.exercise_id IS NULL THEN 0 ELSE 1 END,
                    -- Prefer variant B if last was A (simple alternation)
                    CASE WHEN COALESCE(e.tags->>'variant', 'A') != COALESCE(
                        (SELECT ueh.exercise_id::text FROM user_exercise_history ueh
                         JOIN exercises ex ON ex.id = ueh.exercise_id
                         WHERE ueh.user_id = p_user_id
                           AND ueh.sense_id = tw.sense_id
                         ORDER BY ueh.created_at DESC LIMIT 1),
                        '') THEN 0 ELSE 1 END,
                    RANDOM()
            ) AS rn
        FROM top_words tw
        JOIN exercises e ON e.word_sense_id = tw.sense_id
            AND e.language_id = p_language_id
            AND e.is_active = true
            AND e.ladder_level IS NOT NULL
        LEFT JOIN seen_today st ON st.exercise_id = e.id
    ),
    -- Step 6: Pick best exercise per word
    selected AS (
        SELECT * FROM word_exercises WHERE rn = 1
    )
    -- Step 7: Join word metadata and return
    SELECT
        s.sense_id AS out_sense_id,
        s.exercise_id AS out_exercise_id,
        s.exercise_type AS out_exercise_type,
        s.content AS out_content,
        s.ladder_level AS out_ladder_level,
        s.family AS out_family,
        s.p_known AS out_p_known,
        s.word_state AS out_word_state,
        COALESCE(dv.lemma, '') AS out_lemma,
        COALESCE(dws.definition, '') AS out_definition,
        COALESCE(dws.pronunciation, '') AS out_pronunciation,
        s.variant AS out_variant,
        (s.word_state = 'gated') AS out_is_gate,
        (s.word_state = 'pre_mastery') AS out_is_stress_test,
        s.priority AS out_priority
    FROM selected s
    JOIN dim_word_senses dws ON dws.id = s.sense_id
    JOIN dim_vocabulary dv ON dv.id = dws.vocab_id
    ORDER BY s.priority DESC;
END;
$function$;
