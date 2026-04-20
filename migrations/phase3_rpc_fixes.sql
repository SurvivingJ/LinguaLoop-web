-- ============================================================================
-- Phase 3: RPC Bug Fixes
-- Date: 2026-04-12
--
-- 3.1 Re-enable ELO volatility in process_test_submission
-- 3.2 Fix get_recommended_test — exclude already-attempted tests
-- 3.3 Implement can_use_free_test properly
-- 3.4 Implement get_token_balance
-- 3.5 Replace COUNT(*) triggers with O(1) increments
-- 3.6 Add auth check to get_distractors
-- ============================================================================


-- ============================================================================
-- 3.1 Re-enable ELO volatility in process_test_submission
-- ============================================================================
-- V2 dropped volatility and inlined ELO with symmetric K=32.
-- This restores: volatility multiplier for new/returning users,
-- asymmetric K (32 for users with vol, 16 for tests).
-- The existing helper functions calculate_elo_rating() and
-- calculate_volatility_multiplier() are wired back in.

CREATE OR REPLACE FUNCTION public.process_test_submission(
    p_user_id uuid,
    p_test_id uuid,
    p_language_id smallint,
    p_test_type_id smallint,
    p_responses jsonb,
    p_was_free_test boolean DEFAULT true,
    p_idempotency_key uuid DEFAULT NULL::uuid
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
BEGIN
    -- ========================================================================
    -- SECURITY VALIDATION
    -- ========================================================================
    IF p_user_id != auth.uid() THEN
        RAISE EXCEPTION 'Unauthorized: Cannot submit test for another user';
    END IF;

    -- ========================================================================
    -- INPUT VALIDATION
    -- ========================================================================
    IF p_responses IS NULL OR jsonb_array_length(p_responses) = 0 THEN
        RAISE EXCEPTION 'No responses provided';
    END IF;

    -- ========================================================================
    -- ANSWER VALIDATION (server-side grading)
    -- ========================================================================
    CREATE TEMP TABLE temp_user_responses ON COMMIT DROP AS
    SELECT
        (elem->>'question_id')::UUID as question_id,
        elem->>'selected_answer' as selected_answer
    FROM jsonb_array_elements(p_responses) as elem;

    FOR v_question_record IN (
        SELECT q.id, q.answer
        FROM questions q
        WHERE q.test_id = p_test_id
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

    -- ========================================================================
    -- IDEMPOTENCY CHECK
    -- ========================================================================
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

    -- ========================================================================
    -- GET TOKEN COST
    -- ========================================================================
    v_tokens_cost := get_test_token_cost(p_user_id);

    -- ========================================================================
    -- CALCULATE PERCENTAGE
    -- ========================================================================
    v_percentage := (v_score::numeric / v_total_questions::numeric) * 100;
    v_percentage_decimal := v_percentage / 100.0;

    -- ========================================================================
    -- DETERMINE ATTEMPT NUMBER
    -- ========================================================================
    SELECT COUNT(*) INTO v_attempt_number
    FROM test_attempts
    WHERE user_id = p_user_id
      AND test_id = p_test_id
      AND test_type_id = p_test_type_id;

    v_attempt_number := v_attempt_number + 1;
    v_is_first_attempt := (v_attempt_number = 1);

    -- ========================================================================
    -- GET OR CREATE USER ELO RATING
    -- ========================================================================
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

    -- ========================================================================
    -- GET OR CREATE TEST ELO RATING
    -- ========================================================================
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

    -- ========================================================================
    -- CALCULATE ELO CHANGES (ONLY FOR FIRST ATTEMPTS)
    -- ========================================================================
    -- FIX: Re-enable volatility multiplier and asymmetric K-factors.
    -- Uses existing calculate_volatility_multiplier() and calculate_elo_rating()
    -- that were disconnected in V2.
    IF v_is_first_attempt THEN
        DECLARE
            v_user_volatility numeric;
        BEGIN
            -- Calculate user volatility (new users and returning users get boost)
            v_user_volatility := calculate_volatility_multiplier(
                v_user_tests_taken, v_user_last_date, 1.0
            );

            -- User ELO: K=32 with volatility multiplier
            v_new_user_elo := calculate_elo_rating(
                v_user_elo, v_test_elo, v_percentage_decimal, 32, v_user_volatility
            );

            -- Test ELO: K=16, no volatility (tests should be stable)
            v_new_test_elo := calculate_elo_rating(
                v_test_elo, v_user_elo, 1.0 - v_percentage_decimal, 16, 1.0
            );
        END;

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

    -- ========================================================================
    -- INSERT ATTEMPT RECORD (always store ELO snapshots)
    -- ========================================================================
    INSERT INTO test_attempts (
        user_id, test_id, test_type_id, language_id, score, total_questions,
        attempt_number, is_first_attempt, user_elo_before, user_elo_after,
        test_elo_before, test_elo_after, tokens_consumed, was_free_test,
        idempotency_key
    ) VALUES (
        p_user_id, p_test_id, p_test_type_id, p_language_id, v_score,
        v_total_questions, v_attempt_number, v_is_first_attempt,
        v_user_elo, v_new_user_elo, v_test_elo, v_new_test_elo,
        CASE WHEN p_was_free_test THEN 0 ELSE v_tokens_cost END,
        p_was_free_test, p_idempotency_key
    )
    RETURNING id INTO v_attempt_id;

    -- ========================================================================
    -- UPDATE USER_LANGUAGES
    -- ========================================================================
    INSERT INTO user_languages (user_id, language_id, total_tests_taken, last_test_date)
    VALUES (p_user_id, p_language_id, 1, CURRENT_DATE)
    ON CONFLICT (user_id, language_id)
    DO UPDATE SET
        total_tests_taken = user_languages.total_tests_taken + 1,
        last_test_date = CURRENT_DATE,
        updated_at = NOW();

    -- ========================================================================
    -- RETURN SUCCESS
    -- ========================================================================
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
        'test_elo_change', CASE WHEN v_is_first_attempt THEN v_new_test_elo - v_test_elo ELSE 0 END,
        'tokens_cost', CASE WHEN p_was_free_test THEN 0 ELSE v_tokens_cost END,
        'score', v_score,
        'total_questions', v_total_questions,
        'percentage', v_percentage,
        'question_results', v_question_results,
        'message', CASE WHEN v_is_first_attempt THEN 'First attempt - ELO updated' ELSE 'Retake - ELO unchanged' END
    );

EXCEPTION WHEN OTHERS THEN
    RETURN jsonb_build_object(
        'success', false,
        'error', SQLERRM,
        'error_detail', SQLSTATE
    );
END;
$function$;


-- ============================================================================
-- 3.2 Fix get_recommended_test — exclude already-attempted tests
-- ============================================================================
-- The current version selects random tests within an ELO radius but never
-- checks test_attempts. Users receive repeated recommendations.

CREATE OR REPLACE FUNCTION public.get_recommended_test(
    p_user_id uuid,
    p_language_id integer
)
RETURNS SETOF tests
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path TO 'public', 'pg_temp'
AS $function$
DECLARE
    v_listening_type_id SMALLINT;
    v_reading_type_id SMALLINT;
    v_user_listening_elo INT := 1200;
    v_user_reading_elo INT := 1200;
    v_radius INT;
    v_radii INT[] := ARRAY[50, 100, 250, 500, 10000];
    v_test_found tests%ROWTYPE;
BEGIN
    -- 1. Get Test Type IDs
    SELECT id INTO v_listening_type_id FROM dim_test_types WHERE type_code = 'listening';
    SELECT id INTO v_reading_type_id FROM dim_test_types WHERE type_code = 'reading';

    -- 2. Fetch User's Current Ratings
    SELECT
        MAX(CASE WHEN test_type_id = v_listening_type_id THEN elo_rating END),
        MAX(CASE WHEN test_type_id = v_reading_type_id THEN elo_rating END)
    INTO v_user_listening_elo, v_user_reading_elo
    FROM user_skill_ratings
    WHERE user_id = p_user_id AND language_id = p_language_id;

    IF v_user_listening_elo IS NULL THEN v_user_listening_elo := 1200; END IF;
    IF v_user_reading_elo IS NULL THEN v_user_reading_elo := 1200; END IF;

    -- 3. Expanding Radius Loop
    FOREACH v_radius IN ARRAY v_radii
    LOOP
        SELECT t.*
        INTO v_test_found
        FROM tests t
        JOIN test_skill_ratings tsr ON t.id = tsr.test_id
        WHERE t.language_id = p_language_id
          AND t.is_active = TRUE
          AND tsr.test_type_id IN (v_listening_type_id, v_reading_type_id)
          AND (
              (tsr.test_type_id = v_listening_type_id
               AND tsr.elo_rating BETWEEN (v_user_listening_elo - v_radius)
                                       AND (v_user_listening_elo + v_radius))
              OR
              (tsr.test_type_id = v_reading_type_id
               AND tsr.elo_rating BETWEEN (v_user_reading_elo - v_radius)
                                       AND (v_user_reading_elo + v_radius))
          )
          -- FIX: Exclude tests the user has already attempted
          AND NOT EXISTS (
              SELECT 1 FROM test_attempts ta
              WHERE ta.user_id = p_user_id AND ta.test_id = t.id
          )
        ORDER BY random()
        LIMIT 1;

        IF v_test_found.id IS NOT NULL THEN
            RETURN NEXT v_test_found;
            RETURN;
        END IF;
    END LOOP;
END;
$function$;


-- ============================================================================
-- 3.3 Implement can_use_free_test properly
-- ============================================================================
-- Currently returns daily_limit > 0 without checking actual usage.

CREATE OR REPLACE FUNCTION public.can_use_free_test(p_user_id uuid)
RETURNS boolean
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path TO 'public', 'pg_temp'
AS $function$
DECLARE
    v_daily_limit integer;
    v_used_today integer;
    v_last_free_date date;
BEGIN
    -- Security: only self-check
    IF p_user_id != auth.uid() THEN
        RAISE EXCEPTION 'Unauthorized: Cannot check free test status for another user';
    END IF;

    -- Get daily limit from subscription tier
    v_daily_limit := get_daily_free_test_limit(p_user_id);

    -- Get actual usage today
    SELECT free_tests_used_today, last_free_test_date
    INTO v_used_today, v_last_free_date
    FROM users
    WHERE id = p_user_id AND deleted_at IS NULL;

    -- If last free test date is not today, counter resets to 0
    IF v_last_free_date IS NULL OR v_last_free_date < CURRENT_DATE THEN
        v_used_today := 0;
    END IF;

    RETURN COALESCE(v_used_today, 0) < v_daily_limit;
END;
$function$;


-- ============================================================================
-- 3.4 Implement get_token_balance
-- ============================================================================
-- Currently returns hardcoded 0.

CREATE OR REPLACE FUNCTION public.get_token_balance(p_user_id uuid)
RETURNS integer
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path TO 'public', 'pg_temp'
AS $function$
DECLARE
    v_balance integer;
BEGIN
    -- Security: self or admin/moderator
    IF p_user_id != auth.uid() THEN
        IF NOT (is_admin(auth.uid()) OR is_moderator(auth.uid())) THEN
            RAISE EXCEPTION 'Unauthorized: Cannot view another user''s token balance';
        END IF;
    END IF;

    SELECT COALESCE(purchased_tokens + bonus_tokens, 0)
    INTO v_balance
    FROM user_tokens
    WHERE user_id = p_user_id;

    RETURN COALESCE(v_balance, 0);
END;
$function$;


-- ============================================================================
-- 3.5 Replace COUNT(*) triggers with O(1) increments
-- ============================================================================

CREATE OR REPLACE FUNCTION public.update_skill_attempts_count()
RETURNS trigger
LANGUAGE plpgsql
AS $function$
BEGIN
    UPDATE test_skill_ratings
    SET total_attempts = total_attempts + 1,
        updated_at = NOW()
    WHERE test_id = NEW.test_id
      AND test_type_id = NEW.test_type_id;
    RETURN NEW;
END;
$function$;

CREATE OR REPLACE FUNCTION public.update_test_attempts_count()
RETURNS trigger
LANGUAGE plpgsql
AS $function$
BEGIN
    UPDATE public.tests
    SET total_attempts = total_attempts + 1
    WHERE id = NEW.test_id;
    RETURN NEW;
END;
$function$;

-- One-time reconciliation to ensure counts are accurate before switching
-- (Run this AFTER deploying the trigger changes)
-- UPDATE tests t SET total_attempts = (
--     SELECT COUNT(*) FROM test_attempts ta WHERE ta.test_id = t.id
-- );
-- UPDATE test_skill_ratings tsr SET total_attempts = (
--     SELECT COUNT(*) FROM test_attempts ta
--     WHERE ta.test_id = tsr.test_id AND ta.test_type_id = tsr.test_type_id
-- );


-- ============================================================================
-- 3.6 Add auth check to get_distractors
-- ============================================================================
-- Currently no auth check, no SECURITY DEFINER.

CREATE OR REPLACE FUNCTION public.get_distractors(
    p_sense_id integer,
    p_language_id smallint,
    p_count integer DEFAULT 3
)
RETURNS TABLE(out_definition text)
LANGUAGE plpgsql
STABLE
SECURITY DEFINER
SET search_path TO 'public', 'pg_temp'
AS $function$
BEGIN
    -- Require authenticated user
    IF auth.uid() IS NULL THEN
        RAISE EXCEPTION 'Authentication required';
    END IF;

    RETURN QUERY
    SELECT dws.definition
    FROM dim_word_senses dws
    JOIN dim_vocabulary dv ON dv.id = dws.vocab_id
    WHERE dv.language_id = p_language_id
      AND dws.id != p_sense_id
      AND dws.vocab_id != (SELECT vocab_id FROM dim_word_senses WHERE id = p_sense_id)
      AND dws.sense_rank = 1
    ORDER BY random()
    LIMIT p_count;
END;
$function$;
