-- ============================================================================
-- Listening Lab RPCs
-- ============================================================================
-- Idempotent: safe to re-run. Drops and recreates all functions.
--
-- 1. process_test_submission  (PATCHED to filter questions.pool_source='original'
--                              for canonical test types; listening_lab uses all)
-- 2. start_listening_lab_session
-- 3. submit_listening_lab_tier
-- 4. get_listening_lab_recommendations
-- ============================================================================


-- ============================================================================
-- 0. DROP EXISTING FUNCTIONS
-- ============================================================================

DROP FUNCTION IF EXISTS start_listening_lab_session(uuid, uuid);
DROP FUNCTION IF EXISTS submit_listening_lab_tier(uuid, uuid, smallint, jsonb, uuid);
DROP FUNCTION IF EXISTS get_listening_lab_recommendations(uuid, integer);


-- ============================================================================
-- 1. PATCH process_test_submission TO RESPECT questions.pool_source
-- ============================================================================
-- Before: graded against every row in `questions WHERE test_id = p_test_id`.
-- After:  graded against `pool_source='original'` only for canonical types;
--         listening_lab uses the full 20-question pool (5 original + 15
--         lab_expansion).
--
-- Everything else is identical to the prior live definition. The single
-- functional change is the new pool filter in the question loop.

CREATE OR REPLACE FUNCTION public.process_test_submission(
    p_user_id uuid,
    p_test_id uuid,
    p_language_id smallint,
    p_test_type_id smallint,
    p_responses jsonb,
    p_was_free_test boolean DEFAULT true,
    p_idempotency_key uuid DEFAULT NULL
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path TO 'public', 'pg_temp'
AS $function$
DECLARE
    v_user_elo integer;
    v_test_elo integer;
    v_user_tests_taken integer;
    v_user_last_date date;
    v_test_attempts integer;
    v_percentage numeric;
    v_percentage_decimal numeric;
    v_new_user_elo integer;
    v_new_test_elo integer;
    v_attempt_id uuid;
    v_attempt_number integer;
    v_is_first_attempt boolean;
    v_existing_attempt record;
    v_tokens_cost integer;
    v_score integer := 0;
    v_total_questions integer := 0;
    v_question_results jsonb := '[]'::jsonb;
    v_question_record record;
    v_user_answer text;
    v_correct_answer text;
    v_is_correct boolean;
    v_user_volatility numeric;
    v_is_retry_slot boolean := false;
    v_already_earned_today boolean := false;
    v_last_attempt_at timestamptz;
    v_prev_best numeric;
    v_days_since numeric;
    v_base numeric;
    v_bonus numeric;
    v_factor numeric;
    v_record_factor numeric := NULL;
    v_test_type_code text;
BEGIN
    IF p_user_id != auth.uid() THEN
        RAISE EXCEPTION 'Unauthorized: Cannot submit test for another user';
    END IF;

    IF p_responses IS NULL OR jsonb_array_length(p_responses) = 0 THEN
        RAISE EXCEPTION 'No responses provided';
    END IF;

    -- Resolve test_type_code so the question loop knows whether to include
    -- the lab_expansion pool.
    SELECT type_code INTO v_test_type_code
    FROM dim_test_types WHERE id = p_test_type_id;

    CREATE TEMP TABLE temp_user_responses ON COMMIT DROP AS
    SELECT
        (elem->>'question_id')::UUID as question_id,
        elem->>'selected_answer' as selected_answer
    FROM jsonb_array_elements(p_responses) as elem;

    FOR v_question_record IN (
        SELECT q.id, q.answer
        FROM questions q
        WHERE q.test_id = p_test_id
          AND (v_test_type_code = 'listening_lab' OR q.pool_source = 'original')
        ORDER BY q.created_at
    ) LOOP
        SELECT selected_answer INTO v_user_answer
        FROM temp_user_responses
        WHERE question_id = v_question_record.id;

        v_user_answer := COALESCE(v_user_answer, '');
        v_correct_answer := v_question_record.answer #>> '{}';
        v_is_correct := (v_user_answer = v_correct_answer);

        IF v_is_correct THEN
            v_score := v_score + 1;
        END IF;

        v_question_results := v_question_results || jsonb_build_object(
            'question_id', v_question_record.id::TEXT,
            'selected_answer', v_user_answer,
            'correct_answer', v_correct_answer,
            'is_correct', v_is_correct
        );

        v_total_questions := v_total_questions + 1;
    END LOOP;

    DROP TABLE IF EXISTS temp_user_responses;

    IF v_total_questions = 0 THEN
        RAISE EXCEPTION 'No questions found for test %', p_test_id;
    END IF;

    IF p_idempotency_key IS NOT NULL THEN
        SELECT * INTO v_existing_attempt
        FROM test_attempts
        WHERE user_id = p_user_id AND idempotency_key = p_idempotency_key;

        IF FOUND THEN
            RETURN jsonb_build_object(
                'success', true,
                'attempt_id', v_existing_attempt.id,
                'cached', true,
                'user_elo_change', COALESCE(
                    v_existing_attempt.user_elo_after - v_existing_attempt.user_elo_before, 0
                ),
                'message', 'Duplicate submission detected - returning cached result'
            );
        END IF;
    END IF;

    v_tokens_cost := get_test_token_cost(p_user_id);

    v_percentage := (v_score::numeric / v_total_questions::numeric) * 100;
    v_percentage_decimal := v_percentage / 100.0;

    SELECT COUNT(*) INTO v_attempt_number
    FROM test_attempts
    WHERE user_id = p_user_id
      AND test_id = p_test_id
      AND test_type_id = p_test_type_id;

    v_attempt_number := v_attempt_number + 1;
    v_is_first_attempt := (v_attempt_number = 1);

    SELECT elo_rating, tests_taken, last_test_date
    INTO v_user_elo, v_user_tests_taken, v_user_last_date
    FROM user_skill_ratings
    WHERE user_id = p_user_id
      AND language_id = p_language_id
      AND test_type_id = p_test_type_id;

    IF NOT FOUND THEN
        v_user_elo := 1200;
        v_user_tests_taken := 0;
        v_user_last_date := NULL;

        INSERT INTO user_skill_ratings (
            user_id, language_id, test_type_id, elo_rating, tests_taken
        ) VALUES (
            p_user_id, p_language_id, p_test_type_id, v_user_elo, 0
        );
    END IF;

    SELECT elo_rating, total_attempts
    INTO v_test_elo, v_test_attempts
    FROM test_skill_ratings
    WHERE test_id = p_test_id AND test_type_id = p_test_type_id;

    IF NOT FOUND THEN
        v_test_elo := 1400;
        v_test_attempts := 0;

        INSERT INTO test_skill_ratings (
            test_id, test_type_id, elo_rating, total_attempts
        ) VALUES (
            p_test_id, p_test_type_id, v_test_elo, 0
        );
    END IF;

    v_user_volatility := calculate_volatility_multiplier(
        v_user_tests_taken, v_user_last_date, 1.0
    );

    IF v_is_first_attempt THEN
        v_new_user_elo := calculate_elo_rating(
            v_user_elo, v_test_elo, v_percentage_decimal, 32, v_user_volatility
        );
        v_new_test_elo := calculate_elo_rating(
            v_test_elo, v_user_elo, 1.0 - v_percentage_decimal, 16, 1.0
        );

        UPDATE user_skill_ratings
        SET elo_rating = v_new_user_elo,
            tests_taken = tests_taken + 1,
            last_test_date = CURRENT_DATE,
            updated_at = NOW()
        WHERE user_id = p_user_id
          AND language_id = p_language_id
          AND test_type_id = p_test_type_id;

        UPDATE test_skill_ratings
        SET elo_rating = v_new_test_elo,
            total_attempts = total_attempts + 1,
            updated_at = NOW()
        WHERE test_id = p_test_id
          AND test_type_id = p_test_type_id;
    ELSE
        SELECT EXISTS (
            SELECT 1
            FROM daily_test_loads d,
                 jsonb_array_elements(d.test_ids) elem
            WHERE d.user_id = p_user_id
              AND d.language_id = p_language_id
              AND d.load_date = CURRENT_DATE
              AND elem->>'slot_type' = 'retry'
              AND (elem->>'test_id')::uuid = p_test_id
        ) INTO v_is_retry_slot;

        IF v_is_retry_slot THEN
            SELECT EXISTS (
                SELECT 1 FROM test_attempts
                WHERE user_id = p_user_id
                  AND test_id = p_test_id
                  AND elo_reduction_factor IS NOT NULL
                  AND created_at::date = CURRENT_DATE
            ) INTO v_already_earned_today;
        END IF;

        IF v_is_retry_slot AND NOT v_already_earned_today THEN
            SELECT MAX(created_at),
                   MAX((score::numeric / NULLIF(total_questions, 0)::numeric) * 100)
            INTO v_last_attempt_at, v_prev_best
            FROM test_attempts
            WHERE user_id = p_user_id
              AND test_id = p_test_id;

            v_days_since := EXTRACT(EPOCH FROM (NOW() - COALESCE(v_last_attempt_at, NOW()))) / 86400.0;
            v_base := LEAST(1.0, GREATEST(0.20, v_days_since / 60.0));

            IF v_prev_best IS NOT NULL AND (v_percentage - v_prev_best) >= 15 THEN
                v_bonus := 0.25;
            ELSE
                v_bonus := 0;
            END IF;

            v_factor := LEAST(1.0, v_base + v_bonus);
            v_record_factor := v_factor;

            v_new_user_elo := calculate_elo_rating(
                v_user_elo, v_test_elo, v_percentage_decimal,
                32, v_user_volatility * v_factor
            );
            v_new_test_elo := calculate_elo_rating(
                v_test_elo, v_user_elo, 1.0 - v_percentage_decimal,
                16, v_factor
            );

            UPDATE user_skill_ratings
            SET elo_rating = v_new_user_elo,
                tests_taken = tests_taken + 1,
                last_test_date = CURRENT_DATE,
                updated_at = NOW()
            WHERE user_id = p_user_id
              AND language_id = p_language_id
              AND test_type_id = p_test_type_id;

            UPDATE test_skill_ratings
            SET elo_rating = v_new_test_elo,
                total_attempts = total_attempts + 1,
                updated_at = NOW()
            WHERE test_id = p_test_id
              AND test_type_id = p_test_type_id;
        ELSE
            v_new_user_elo := v_user_elo;
            v_new_test_elo := v_test_elo;
        END IF;
    END IF;

    INSERT INTO test_attempts (
        user_id, test_id, test_type_id, language_id, score, total_questions,
        attempt_number, is_first_attempt, user_elo_before, user_elo_after,
        test_elo_before, test_elo_after, tokens_consumed, was_free_test,
        idempotency_key, elo_reduction_factor
    ) VALUES (
        p_user_id, p_test_id, p_test_type_id, p_language_id, v_score,
        v_total_questions, v_attempt_number, v_is_first_attempt,
        v_user_elo, v_new_user_elo, v_test_elo, v_new_test_elo,
        CASE WHEN p_was_free_test THEN 0 ELSE v_tokens_cost END,
        p_was_free_test, p_idempotency_key, v_record_factor
    )
    RETURNING id INTO v_attempt_id;

    INSERT INTO user_languages (user_id, language_id, total_tests_taken, last_test_date)
    VALUES (p_user_id, p_language_id, 1, CURRENT_DATE)
    ON CONFLICT (user_id, language_id)
    DO UPDATE SET
        total_tests_taken = user_languages.total_tests_taken + 1,
        last_test_date = CURRENT_DATE,
        updated_at = NOW();

    RETURN jsonb_build_object(
        'success', true,
        'attempt_id', v_attempt_id,
        'attempt_number', v_attempt_number,
        'is_first_attempt', v_is_first_attempt,
        'user_elo_before', v_user_elo,
        'user_elo_after', v_new_user_elo,
        'user_elo_change', v_new_user_elo - v_user_elo,
        'test_elo_before', v_test_elo,
        'test_elo_after', v_new_test_elo,
        'test_elo_change', v_new_test_elo - v_test_elo,
        'elo_reduction_factor', v_record_factor,
        'tokens_cost', CASE WHEN p_was_free_test THEN 0 ELSE v_tokens_cost END,
        'score', v_score,
        'total_questions', v_total_questions,
        'percentage', v_percentage,
        'question_results', v_question_results,
        'message', CASE
            WHEN v_is_first_attempt THEN 'First attempt - ELO updated'
            WHEN v_record_factor IS NOT NULL THEN 'Retry-slot repeat - reduced-volatility ELO applied'
            ELSE 'Retake - ELO unchanged'
        END
    );

EXCEPTION WHEN OTHERS THEN
    RETURN jsonb_build_object(
        'success', false,
        'error', SQLERRM,
        'error_detail', SQLSTATE
    );
END;
$function$;

GRANT EXECUTE ON FUNCTION process_test_submission TO authenticated;


-- ============================================================================
-- 2. start_listening_lab_session
-- ============================================================================
-- Creates (or returns the existing active) session for a user+passage.
-- Samples the first tier's 5 questions from the full 20-question pool.
-- Records tokens_consumed (informational); the route layer is responsible
-- for the wallet deduction before calling this RPC.

CREATE OR REPLACE FUNCTION public.start_listening_lab_session(
    p_user_id uuid,
    p_passage_id uuid
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path TO 'public', 'pg_temp'
AS $function$
DECLARE
    v_passage listening_lab_passages%ROWTYPE;
    v_existing listening_lab_sessions%ROWTYPE;
    v_session_id uuid;
    v_question_ids uuid[];
    v_questions jsonb;
    v_tokens_cost integer;
    v_test_id uuid;
    v_audio_url text;
BEGIN
    IF p_user_id != auth.uid() THEN
        RAISE EXCEPTION 'Unauthorized';
    END IF;

    SELECT * INTO v_passage
    FROM listening_lab_passages
    WHERE id = p_passage_id AND is_active = true;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Passage not found or inactive';
    END IF;

    -- Idempotency: if an active (non-completed, non-abandoned) session exists,
    -- return its current state. The unique partial index also enforces this.
    SELECT * INTO v_existing
    FROM listening_lab_sessions
    WHERE user_id = p_user_id
      AND passage_id = p_passage_id
      AND completed_at IS NULL
      AND abandoned_at IS NULL;

    IF FOUND THEN
        v_audio_url := CASE v_existing.current_tier
            WHEN 0 THEN v_passage.audio_url_075
            WHEN 1 THEN v_passage.audio_url_090
            WHEN 2 THEN v_passage.audio_url_100
            WHEN 3 THEN v_passage.audio_url_115
            ELSE NULL
        END;

        SELECT jsonb_agg(
            jsonb_build_object(
                'id', q.id::text,
                'question_text', q.question_text,
                'choices', q.choices
            ) ORDER BY array_position(v_existing.active_question_ids, q.id)
        )
        INTO v_questions
        FROM questions q
        WHERE q.id = ANY(v_existing.active_question_ids);

        RETURN jsonb_build_object(
            'success', true,
            'session_id', v_existing.id,
            'resumed', true,
            'tier', v_existing.current_tier,
            'audio_url', v_audio_url,
            'questions', COALESCE(v_questions, '[]'::jsonb),
            'tiers_passed', to_jsonb(v_existing.tiers_passed),
            'tokens_consumed', v_existing.tokens_consumed
        );
    END IF;

    v_tokens_cost := get_test_token_cost(p_user_id);
    v_test_id := v_passage.test_id;

    -- Sample 5 random questions from the test's full pool (20).
    SELECT array_agg(id ORDER BY r), jsonb_agg(
        jsonb_build_object(
            'id', id::text,
            'question_text', question_text,
            'choices', choices
        ) ORDER BY r
    )
    INTO v_question_ids, v_questions
    FROM (
        SELECT id, question_text, choices, random() AS r
        FROM questions
        WHERE test_id = v_test_id
        ORDER BY random()
        LIMIT 5
    ) sub;

    IF v_question_ids IS NULL OR array_length(v_question_ids, 1) < 5 THEN
        RAISE EXCEPTION 'Passage % has fewer than 5 questions available', p_passage_id;
    END IF;

    INSERT INTO listening_lab_sessions (
        user_id, passage_id, test_id, language_id,
        current_tier, tiers_passed,
        seen_question_ids, active_question_ids,
        tier_results, tokens_consumed
    ) VALUES (
        p_user_id, p_passage_id, v_test_id, v_passage.language_id,
        0, ARRAY[]::smallint[],
        v_question_ids, v_question_ids,
        '{}'::jsonb, v_tokens_cost
    )
    RETURNING id INTO v_session_id;

    RETURN jsonb_build_object(
        'success', true,
        'session_id', v_session_id,
        'resumed', false,
        'tier', 0,
        'speed', 0.75,
        'audio_url', v_passage.audio_url_075,
        'questions', v_questions,
        'tiers_passed', '[]'::jsonb,
        'tokens_cost', v_tokens_cost
    );

EXCEPTION WHEN OTHERS THEN
    RETURN jsonb_build_object(
        'success', false,
        'error', SQLERRM,
        'error_detail', SQLSTATE
    );
END;
$function$;

GRANT EXECUTE ON FUNCTION start_listening_lab_session TO authenticated;


-- ============================================================================
-- 3. submit_listening_lab_tier
-- ============================================================================
-- Grades responses for the current tier of a session.
--   passed (>=4/5) at tier 3  -> finalize via process_test_submission, set
--                                completed_at and final_attempt_id
--   passed at tier 0/1/2      -> advance current_tier, sample next 5 unseen
--   failed                    -> sample 5 fresh unseen for retry
--
-- Idempotency: pass p_idempotency_key to dedupe in-flight POST retries. If
-- the most recent attempt entry on this tier has the same key, the cached
-- result is returned without re-scoring.

CREATE OR REPLACE FUNCTION public.submit_listening_lab_tier(
    p_user_id uuid,
    p_session_id uuid,
    p_tier smallint,
    p_responses jsonb,
    p_idempotency_key uuid DEFAULT NULL
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path TO 'public', 'pg_temp'
AS $function$
DECLARE
    v_session listening_lab_sessions%ROWTYPE;
    v_passage listening_lab_passages%ROWTYPE;
    v_score smallint := 0;
    v_pass_threshold CONSTANT smallint := 4;
    v_tier_speeds CONSTANT numeric[] := ARRAY[0.75, 0.90, 1.00, 1.15];
    v_passed boolean;
    v_response_records jsonb := '[]'::jsonb;
    v_question_record record;
    v_user_answer text;
    v_correct_answer text;
    v_is_correct boolean;
    v_last_attempt jsonb;
    v_attempt_entry jsonb;
    v_next_tier smallint;
    v_next_question_ids uuid[];
    v_next_questions jsonb;
    v_next_audio text;
    v_test_type_id smallint;
    v_aggregated_responses jsonb;
    v_completion_result jsonb;
    v_tokens_already_charged boolean;
BEGIN
    IF p_user_id != auth.uid() THEN
        RAISE EXCEPTION 'Unauthorized';
    END IF;

    SELECT * INTO v_session
    FROM listening_lab_sessions
    WHERE id = p_session_id AND user_id = p_user_id
    FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Session not found';
    END IF;

    -- Already completed: surface the cached final result.
    IF v_session.completed_at IS NOT NULL AND v_session.final_attempt_id IS NOT NULL THEN
        RETURN jsonb_build_object(
            'success', true,
            'cached', true,
            'completed', true,
            'final_attempt_id', v_session.final_attempt_id
        );
    END IF;

    IF v_session.abandoned_at IS NOT NULL THEN
        RAISE EXCEPTION 'Session has been abandoned';
    END IF;

    IF p_tier != v_session.current_tier THEN
        RAISE EXCEPTION 'Tier mismatch: session is on tier %, request was for tier %',
            v_session.current_tier, p_tier;
    END IF;

    -- Idempotency: replay-safe within a tier.
    v_last_attempt := v_session.tier_results -> p_tier::text -> 'attempts' -> -1;
    IF p_idempotency_key IS NOT NULL
       AND v_last_attempt IS NOT NULL
       AND (v_last_attempt ->> 'idempotency_key')::uuid IS NOT DISTINCT FROM p_idempotency_key THEN
        RETURN jsonb_build_object(
            'success', true,
            'cached', true,
            'tier', p_tier,
            'score', (v_last_attempt ->> 'score')::int,
            'passed', (v_last_attempt ->> 'passed')::boolean
        );
    END IF;

    IF p_responses IS NULL OR jsonb_array_length(p_responses) = 0 THEN
        RAISE EXCEPTION 'No responses provided';
    END IF;

    -- Grade against the currently-active question set.
    FOR v_question_record IN (
        SELECT q.id, q.answer
        FROM questions q
        WHERE q.id = ANY(v_session.active_question_ids)
    ) LOOP
        SELECT (elem ->> 'selected_answer') INTO v_user_answer
        FROM jsonb_array_elements(p_responses) AS elem
        WHERE (elem ->> 'question_id')::uuid = v_question_record.id;

        v_user_answer := COALESCE(v_user_answer, '');
        v_correct_answer := v_question_record.answer #>> '{}';
        v_is_correct := (v_user_answer = v_correct_answer);

        IF v_is_correct THEN
            v_score := v_score + 1;
        END IF;

        v_response_records := v_response_records || jsonb_build_object(
            'question_id', v_question_record.id::text,
            'selected_answer', v_user_answer,
            'correct_answer', v_correct_answer,
            'is_correct', v_is_correct
        );
    END LOOP;

    v_passed := (v_score >= v_pass_threshold);

    v_attempt_entry := jsonb_build_object(
        'score', v_score,
        'passed', v_passed,
        'at', NOW(),
        'idempotency_key', p_idempotency_key,
        'responses', v_response_records
    );

    -- Initialize the tier slot in tier_results if absent.
    IF NOT (v_session.tier_results ? p_tier::text) THEN
        v_session.tier_results := jsonb_set(
            v_session.tier_results,
            ARRAY[p_tier::text],
            jsonb_build_object('attempts', '[]'::jsonb),
            true
        );
    END IF;

    v_session.tier_results := jsonb_set(
        v_session.tier_results,
        ARRAY[p_tier::text, 'attempts'],
        (v_session.tier_results -> p_tier::text -> 'attempts') || v_attempt_entry,
        true
    );

    IF v_passed THEN
        v_session.tier_results := jsonb_set(
            v_session.tier_results,
            ARRAY[p_tier::text, 'passed_at'],
            to_jsonb(NOW()::text),
            true
        );
        v_session.tiers_passed := v_session.tiers_passed || p_tier;

        IF p_tier = 3 THEN
            -- FINALIZE: aggregate the passing responses across all 4 tiers
            -- (5 per tier, 20 total) and hand off to process_test_submission
            -- for ELO + attempt-row writes.
            SELECT * INTO v_passage FROM listening_lab_passages WHERE id = v_session.passage_id;
            SELECT id INTO v_test_type_id FROM dim_test_types WHERE type_code = 'listening_lab';

            SELECT jsonb_agg(
                jsonb_build_object(
                    'question_id', elem ->> 'question_id',
                    'selected_answer', elem ->> 'selected_answer'
                )
            )
            INTO v_aggregated_responses
            FROM (
                SELECT jsonb_array_elements(
                    (each.value -> 'attempts' -> -1) -> 'responses'
                ) AS elem
                FROM jsonb_each(v_session.tier_results) AS each(key, value)
            ) sub;

            v_tokens_already_charged := (v_session.tokens_consumed > 0);

            v_completion_result := process_test_submission(
                p_user_id := p_user_id,
                p_test_id := v_session.test_id,
                p_language_id := v_session.language_id::smallint,
                p_test_type_id := v_test_type_id,
                p_responses := v_aggregated_responses,
                p_was_free_test := NOT v_tokens_already_charged,
                p_idempotency_key := v_session.id
            );

            -- If process_test_submission failed, propagate the error so
            -- the session row stays open and the route can show a retry UI.
            IF (v_completion_result ->> 'success')::boolean IS DISTINCT FROM true THEN
                RAISE EXCEPTION 'Final ELO submission failed: %',
                    v_completion_result ->> 'error';
            END IF;

            UPDATE listening_lab_sessions
            SET current_tier = 4,
                tiers_passed = v_session.tiers_passed,
                tier_results = v_session.tier_results,
                completed_at = NOW(),
                final_attempt_id = (v_completion_result ->> 'attempt_id')::uuid,
                updated_at = NOW()
            WHERE id = p_session_id;

            RETURN jsonb_build_object(
                'success', true,
                'tier', p_tier,
                'score', v_score,
                'passed', true,
                'completed', true,
                'question_results', v_response_records,
                'final_attempt_id', (v_completion_result ->> 'attempt_id')::uuid,
                'elo_result', v_completion_result
            );
        END IF;

        -- ADVANCE: sample next tier's 5 unseen questions.
        v_next_tier := p_tier + 1;

        SELECT array_agg(id ORDER BY r), jsonb_agg(
            jsonb_build_object(
                'id', id::text,
                'question_text', question_text,
                'choices', choices
            ) ORDER BY r
        )
        INTO v_next_question_ids, v_next_questions
        FROM (
            SELECT id, question_text, choices, random() AS r
            FROM questions
            WHERE test_id = v_session.test_id
              AND NOT (id = ANY(v_session.seen_question_ids))
            ORDER BY random()
            LIMIT 5
        ) sub;

        -- Pool exhaustion (shouldn't happen at 20 questions / 4 tiers, but
        -- handle gracefully): reshuffle the whole pool, reset seen tracking
        -- to the new draw so the lab can keep going.
        IF v_next_question_ids IS NULL OR array_length(v_next_question_ids, 1) < 5 THEN
            SELECT array_agg(id ORDER BY r), jsonb_agg(
                jsonb_build_object(
                    'id', id::text,
                    'question_text', question_text,
                    'choices', choices
                ) ORDER BY r
            )
            INTO v_next_question_ids, v_next_questions
            FROM (
                SELECT id, question_text, choices, random() AS r
                FROM questions
                WHERE test_id = v_session.test_id
                ORDER BY random()
                LIMIT 5
            ) sub;
            v_session.seen_question_ids := v_next_question_ids;
        ELSE
            v_session.seen_question_ids := v_session.seen_question_ids || v_next_question_ids;
        END IF;

        v_session.active_question_ids := v_next_question_ids;
        v_session.current_tier := v_next_tier;

        SELECT * INTO v_passage FROM listening_lab_passages WHERE id = v_session.passage_id;
        v_next_audio := CASE v_next_tier
            WHEN 1 THEN v_passage.audio_url_090
            WHEN 2 THEN v_passage.audio_url_100
            WHEN 3 THEN v_passage.audio_url_115
        END;

        UPDATE listening_lab_sessions
        SET current_tier = v_session.current_tier,
            tiers_passed = v_session.tiers_passed,
            tier_results = v_session.tier_results,
            seen_question_ids = v_session.seen_question_ids,
            active_question_ids = v_session.active_question_ids,
            updated_at = NOW()
        WHERE id = p_session_id;

        RETURN jsonb_build_object(
            'success', true,
            'tier', p_tier,
            'score', v_score,
            'passed', true,
            'completed', false,
            'question_results', v_response_records,
            'next_tier', v_next_tier,
            'next_speed', v_tier_speeds[v_next_tier + 1],
            'next_audio_url', v_next_audio,
            'next_questions', v_next_questions
        );

    ELSE
        -- RETRY: same tier, fresh 5 unseen.
        SELECT array_agg(id ORDER BY r), jsonb_agg(
            jsonb_build_object(
                'id', id::text,
                'question_text', question_text,
                'choices', choices
            ) ORDER BY r
        )
        INTO v_next_question_ids, v_next_questions
        FROM (
            SELECT id, question_text, choices, random() AS r
            FROM questions
            WHERE test_id = v_session.test_id
              AND NOT (id = ANY(v_session.seen_question_ids))
            ORDER BY random()
            LIMIT 5
        ) sub;

        IF v_next_question_ids IS NULL OR array_length(v_next_question_ids, 1) < 5 THEN
            SELECT array_agg(id ORDER BY r), jsonb_agg(
                jsonb_build_object(
                    'id', id::text,
                    'question_text', question_text,
                    'choices', choices
                ) ORDER BY r
            )
            INTO v_next_question_ids, v_next_questions
            FROM (
                SELECT id, question_text, choices, random() AS r
                FROM questions
                WHERE test_id = v_session.test_id
                ORDER BY random()
                LIMIT 5
            ) sub;
            v_session.seen_question_ids := v_next_question_ids;
        ELSE
            v_session.seen_question_ids := v_session.seen_question_ids || v_next_question_ids;
        END IF;

        v_session.active_question_ids := v_next_question_ids;

        UPDATE listening_lab_sessions
        SET tier_results = v_session.tier_results,
            seen_question_ids = v_session.seen_question_ids,
            active_question_ids = v_session.active_question_ids,
            updated_at = NOW()
        WHERE id = p_session_id;

        RETURN jsonb_build_object(
            'success', true,
            'tier', p_tier,
            'score', v_score,
            'passed', false,
            'completed', false,
            'question_results', v_response_records,
            'retry_questions', v_next_questions
        );
    END IF;
END;
$function$;

GRANT EXECUTE ON FUNCTION submit_listening_lab_tier TO authenticated;


-- ============================================================================
-- 4. get_listening_lab_recommendations
-- ============================================================================
-- Returns active, Lab-enrolled passages within ±200 ELO of the user's
-- listening_lab rating (or their listening rating as a cold-start fallback).
-- Excludes passages the user has already completed.

CREATE OR REPLACE FUNCTION public.get_listening_lab_recommendations(
    p_user_id uuid,
    p_language_id integer
)
RETURNS SETOF jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path TO 'public', 'pg_temp'
AS $function$
DECLARE
    v_lab_type_id integer;
    v_listening_type_id integer;
    v_user_elo integer;
BEGIN
    SELECT id INTO v_lab_type_id FROM dim_test_types WHERE type_code = 'listening_lab';
    SELECT id INTO v_listening_type_id FROM dim_test_types WHERE type_code = 'listening';

    -- Prefer the user's lab ELO; fall back to listening ELO; final fallback 1200.
    SELECT COALESCE(
        (SELECT elo_rating FROM user_skill_ratings
         WHERE user_id = p_user_id
           AND language_id = p_language_id
           AND test_type_id = v_lab_type_id),
        (SELECT elo_rating FROM user_skill_ratings
         WHERE user_id = p_user_id
           AND language_id = p_language_id
           AND test_type_id = v_listening_type_id),
        1200
    ) INTO v_user_elo;

    RETURN QUERY
    SELECT jsonb_build_object(
        'passage_id', llp.id,
        'test_id', llp.test_id,
        'test_slug', t.slug,
        'title', t.title,
        'difficulty', t.difficulty,
        'language_id', llp.language_id,
        'voice_id', llp.voice_id,
        'pool_size', llp.pool_size,
        'lab_elo', COALESCE(tsr.elo_rating, 1400),
        'user_elo', v_user_elo,
        'elo_gap', ABS(COALESCE(tsr.elo_rating, 1400) - v_user_elo)
    )
    FROM listening_lab_passages llp
    JOIN tests t ON t.id = llp.test_id
    LEFT JOIN test_skill_ratings tsr
        ON tsr.test_id = llp.test_id AND tsr.test_type_id = v_lab_type_id
    WHERE llp.is_active = true
      AND llp.language_id = p_language_id
      AND NOT EXISTS (
          SELECT 1 FROM listening_lab_sessions s
          WHERE s.user_id = p_user_id
            AND s.passage_id = llp.id
            AND s.completed_at IS NOT NULL
      )
      AND ABS(COALESCE(tsr.elo_rating, 1400) - v_user_elo) <= 200
    ORDER BY ABS(COALESCE(tsr.elo_rating, 1400) - v_user_elo) ASC
    LIMIT 10;
END;
$function$;

GRANT EXECUTE ON FUNCTION get_listening_lab_recommendations TO authenticated;
