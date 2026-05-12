-- ============================================================================
-- Phase 10: Cross-Session Ring Advancement Gating + Ring Demotion
-- Date: 2026-05-12
-- Prerequisites:
--   phase4_schema_evolution.sql  -- Phase 4 counter columns
--   phase8_momentum_bands.sql    -- ladder_record_attempt (replaced here)
--
-- Layers two new behaviours onto Phase 8 Momentum Bands:
--
--   (a) Cross-session advancement gating. Ring advancement currently fires
--       the instant family confidence crosses its threshold. After Phase 10,
--       each required family must additionally have had first-attempt
--       successes on at least TWO distinct calendar days. Prevents same-day
--       farming from racing a word up the rings.
--
--   (b) Ring demotion on repeated failure. When `consecutive_failures` for
--       the family that gates the current ring reaches 3 (per the existing
--       per-family heuristic via `last_exercised_family`), the word drops
--       one ring. The gate that guards exit from the dropped-into ring
--       resets (gate_a on demotion into R2, gate_b on demotion into R3);
--       other gates survive. R1 is the floor — no further demotion.
--
-- Sections:
--   10.1  Schema: family_success_dates column
--   10.2  Core: ladder_record_attempt (CREATE OR REPLACE)
-- ============================================================================


-- ============================================================================
-- 10.1 Schema: family_success_dates
-- ============================================================================
-- Tracks per-family first-attempt-success calendar dates for cross-session
-- gating. Each key is a family name; each value is an array of ISO dates,
-- trimmed to the most recent 2 — anything beyond that is irrelevant to the
-- "≥ 2 distinct dates" check.

ALTER TABLE public.user_word_ladder
    ADD COLUMN IF NOT EXISTS family_success_dates jsonb NOT NULL
        DEFAULT '{"form_recognition":[],"meaning_recall":[],"form_production":[],"collocation":[],"semantic_discrimination":[],"contextual_use":[]}'::jsonb;


-- ============================================================================
-- 10.2 Core: ladder_record_attempt (CREATE OR REPLACE)
-- ============================================================================
-- Replaces the Phase 8 definition. Adds:
--   - v_new_consecutive_failures: computed pre-UPDATE so demotion can use it
--   - v_fc_dates: in-memory mutation of family_success_dates so the same
--                 attempt that adds the second date can clear the ring
--   - v_demoted, v_required_after_demote: new locals for the demotion path
--   - cross-session check inside the v_ring_cleared block
--   - demotion block after word_state computation
--   - two new return-JSONB keys: 'demoted', 'family_success_sessions'
--
-- All other behaviour (family BKT update, momentum band scheduling, lapse
-- path, FSRS schedule on lapse, BKT lapse penalty, overall BKT UPSERT)
-- is unchanged from Phase 8.

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
    v_fc_dates jsonb;
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
    v_required_after_demote text[];
    v_min_conf_threshold numeric;
    v_i integer;
    v_old_p_known numeric;
    v_new_bkt numeric;
    v_semantic_class text;
    v_active_levels integer[];
    v_fsrs_result jsonb;
    v_is_lapse boolean := false;
    v_new_consecutive_failures integer;
    v_demoted boolean := false;
    v_family_session_counts jsonb;
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

    v_family := ladder_get_family(v_ladder_level);

    -- =================================================================
    -- 2. Get or create user_word_ladder row (locked for atomic update)
    -- =================================================================
    SELECT * INTO v_ladder FROM user_word_ladder
    WHERE user_id = p_user_id AND sense_id = p_sense_id
    FOR UPDATE;

    IF NOT FOUND THEN
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
    -- 3. Insert exercise attempt (trigger syncs user_exercise_history)
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

    CASE p_exercise_context
        WHEN 'gate' THEN
            v_learn_rate := 0.18; v_slip_rate := 0.10;
        WHEN 'stress_test' THEN
            v_learn_rate := 0.20; v_slip_rate := 0.12;
        ELSE
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
    v_p_known_overall := ladder_compute_p_known(v_fc);

    -- =================================================================
    -- 4b. Compute updated family_success_dates (Phase 10)
    -- =================================================================
    -- Append CURRENT_DATE to the family's array if today's date isn't
    -- already there, then keep the most recent 2 dates. Used both by
    -- the cross-session gate below and by the UPDATE in step 6.
    v_fc_dates := COALESCE(v_ladder.family_success_dates, '{}'::jsonb);

    IF p_is_correct AND p_is_first_attempt THEN
        v_fc_dates := jsonb_set(
            v_fc_dates,
            ARRAY[v_family],
            COALESCE(
                (
                    SELECT to_jsonb(array_agg(d::text ORDER BY d::date DESC))
                    FROM (
                        SELECT d::date AS d
                        FROM (
                            SELECT jsonb_array_elements_text(
                                COALESCE(v_fc_dates->v_family, '[]'::jsonb)
                            ) AS d
                            UNION
                            SELECT CURRENT_DATE::text AS d
                        ) AS combined
                        GROUP BY d::date
                        ORDER BY d::date DESC
                        LIMIT 2
                    ) AS recent
                ),
                '[]'::jsonb
            )
        );
    END IF;

    -- =================================================================
    -- 4c. Compute updated consecutive_failures (Phase 10)
    -- =================================================================
    -- Compute pre-UPDATE so the demotion check below can read it.
    -- Mirrors the per-family heuristic from Phase 8 (resets on success or
    -- family change).
    v_new_consecutive_failures := CASE
        WHEN p_is_correct THEN 0
        WHEN p_is_first_attempt AND NOT p_is_correct
            AND v_family = COALESCE(v_ladder.last_exercised_family, '')
        THEN COALESCE(v_ladder.consecutive_failures, 0) + 1
        WHEN p_is_first_attempt AND NOT p_is_correct
        THEN 1
        ELSE COALESCE(v_ladder.consecutive_failures, 0)
    END;

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

        v_new_conf := GREATEST(0.02, v_new_conf * 0.70);
        v_fc := jsonb_set(v_fc, ARRAY[v_family], to_jsonb(ROUND(v_new_conf, 4)));
        v_p_known_overall := ladder_compute_p_known(v_fc);

        v_word_state := 'relearning';
        v_review_due := (CURRENT_DATE + 1)::timestamptz;

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

        IF v_p_known_overall < 0.45 THEN
            v_review_due := (CURRENT_DATE + 1)::timestamptz;
        ELSIF v_p_known_overall < 0.75 THEN
            v_review_due := (CURRENT_DATE + 1)::timestamptz;
        ELSE
            v_review_due := (CURRENT_DATE + 2)::timestamptz;
        END IF;

        IF NOT p_is_correct AND p_is_first_attempt THEN
            v_review_due := (CURRENT_DATE + 1)::timestamptz;
        END IF;

        -- Confidence threshold check
        v_required_families := ladder_ring_families(v_current_ring, v_ladder.active_levels);
        v_min_conf_threshold := CASE
            WHEN v_current_ring <= 2 THEN 0.50
            WHEN v_current_ring = 3 THEN 0.65
            ELSE 0.72
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

        -- Cross-session gate (Phase 10):
        -- Every required family must have first-attempt successes on at
        -- least 2 distinct calendar days. Uses the in-memory v_fc_dates
        -- so the same attempt that adds the second date can clear here.
        IF v_ring_cleared
           AND v_required_families IS NOT NULL
           AND array_length(v_required_families, 1) > 0 THEN
            FOR v_i IN 1..array_length(v_required_families, 1) LOOP
                IF jsonb_array_length(
                    COALESCE(v_fc_dates->v_required_families[v_i], '[]'::jsonb)
                ) < 2 THEN
                    v_ring_cleared := false;
                    EXIT;
                END IF;
            END LOOP;
        END IF;

        -- Ring transitions
        IF v_ring_cleared THEN
            IF v_current_ring = 1 THEN
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
            WHEN v_ladder.word_state = 'mastered'
                THEN 'mastered'
            WHEN v_current_ring >= 4
                AND COALESCE((v_gates->>'gate_b')::boolean, false)
                AND v_ring_cleared
                AND v_p_known_overall >= 0.88
                THEN 'pre_mastery'
            WHEN v_gate_pending IS NOT NULL
                THEN 'gated'
            WHEN v_current_ring <= 1 AND v_p_known_overall < 0.20
                THEN 'new'
            ELSE 'active'
        END;

        -- Stress test readiness
        IF v_word_state = 'pre_mastery' THEN
            v_stress_test_ready := true;
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

        -- ---------------------------------------------------------
        -- Ring demotion (Phase 10)
        -- ---------------------------------------------------------
        -- Trigger when:
        --   - This attempt is a first-attempt failure
        --   - The word is past 'new' (not still being introduced)
        --   - We're not at ring 1 (the floor)
        --   - The failing family is one required by the current ring
        --     (otherwise a stray failure on a non-required family shouldn't
        --     demote — the ring isn't gated by it)
        --   - consecutive_failures will reach 3 with this attempt
        --
        -- Effect:
        --   - Drop one ring
        --   - Reset only the gate that guards exit from the dropped-into
        --     ring (gate_a on demote→R2, gate_b on demote→R3); other gates
        --     survive as lifetime achievements
        --   - Reset family_success_dates of the demoted-into-ring required
        --     families so cross-session stability must be re-established
        --   - Set word_state='active' (clears any 'gated' or 'pre_mastery')
        --   - consecutive_failures resets to 0 in the UPDATE block below
        IF NOT p_is_correct
           AND p_is_first_attempt
           AND v_ladder.word_state NOT IN ('mastered', 'new')
           AND v_current_ring > 1
           AND v_family = ANY(v_required_families)
           AND v_new_consecutive_failures >= 3
        THEN
            v_demoted := true;
            v_current_ring := v_current_ring - 1;

            IF v_current_ring = 2 THEN
                v_gates := jsonb_set(v_gates, ARRAY['gate_a'], 'false'::jsonb);
            ELSIF v_current_ring = 3 THEN
                v_gates := jsonb_set(v_gates, ARRAY['gate_b'], 'false'::jsonb);
            END IF;

            v_required_after_demote := ladder_ring_families(v_current_ring, v_ladder.active_levels);
            IF v_required_after_demote IS NOT NULL
               AND array_length(v_required_after_demote, 1) > 0 THEN
                FOR v_i IN 1..array_length(v_required_after_demote, 1) LOOP
                    v_fc_dates := jsonb_set(
                        v_fc_dates,
                        ARRAY[v_required_after_demote[v_i]],
                        '[]'::jsonb
                    );
                END LOOP;
            END IF;

            v_word_state := 'active';
            v_gate_pending := NULL;
            v_stress_test_ready := false;
        END IF;
    END IF;

    -- =================================================================
    -- 6. Update user_word_ladder
    -- =================================================================
    UPDATE user_word_ladder SET
        family_confidence = v_fc,
        family_success_dates = v_fc_dates,
        gates_passed = v_gates,
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
        -- On demotion, reset the counter so the demoted-into ring starts
        -- with a clean failure budget. Otherwise use the value computed
        -- in step 4c.
        consecutive_failures = CASE
            WHEN v_demoted THEN 0
            ELSE v_new_consecutive_failures
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

    IF v_is_lapse THEN
        PERFORM bkt_apply_lapse_penalty(p_user_id, p_sense_id);
    END IF;

    -- =================================================================
    -- 8. Return result
    -- =================================================================
    -- Build family_session_counts: per-family count of distinct cross-session
    -- successes (capped at 2 by the storage trim). Frontend can use this to
    -- show "one more session" advancement progress.
    SELECT jsonb_object_agg(family, jsonb_array_length(dates))
    INTO v_family_session_counts
    FROM jsonb_each(v_fc_dates) AS j(family, dates);

    RETURN jsonb_build_object(
        'is_correct', p_is_correct,
        'family', v_family,
        'family_confidence', v_fc,
        'family_success_sessions', COALESCE(v_family_session_counts, '{}'::jsonb),
        'p_known_overall', v_p_known_overall,
        'current_ring', v_current_ring,
        'word_state', v_word_state,
        'review_due_at', v_review_due,
        'requeue', NOT p_is_correct AND p_is_first_attempt,
        'gate_pending', v_gate_pending,
        'stress_test_ready', v_stress_test_ready,
        'bkt_p_known', ROUND(v_new_bkt::numeric, 4),
        'is_lapse', v_is_lapse,
        'demoted', v_demoted
    );
END;
$function$;
