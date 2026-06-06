-- ============================================================================
-- Wire Up ELO Volatility & Exclude Attempted Tests in Single Recommendation
-- Date: 2026-05-08
--
-- Two surgical fixes from elo-implementation-analysis.md priorities 1 and 2:
--
--   1. process_test_submission() — V2 rewrote ELO inline with symmetric K=32
--      and dropped the volatility multiplier. The helper functions still
--      exist (calculate_volatility_multiplier, calculate_elo_rating) but
--      were disconnected. This restores user-side volatility (1.5x for
--      <10 tests or >90 days inactive) and asymmetric K (32 user / 16 test).
--
--   2. get_recommended_test() — added NOT EXISTS exclusion against
--      test_attempts so users are no longer re-recommended tests they have
--      already taken. The expanding-radius loop was untouched otherwise.
--
-- Both functions keep their signatures and return shapes; no Python or
-- caller changes needed. Idempotent: CREATE OR REPLACE only.
-- ============================================================================


-- ============================================================================
-- 1. process_test_submission — re-enable volatility, asymmetric K-factors
-- ============================================================================

-- SUPERSEDED: this process_test_submission body is no longer canonical. The
-- live definition is migrations/phase14_test_kfactor_decay.sql. This file is
-- retained only for its get_recommended_test definition (still live).
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
    -- Volatility multiplier amplifies user K-factor for new (<10 tests) and
    -- returning (>90 days inactive) users. Tests use K=16 with no volatility.
    IF v_is_first_attempt THEN
        DECLARE
            v_user_volatility numeric;
        BEGIN
            v_user_volatility := calculate_volatility_multiplier(
                v_user_tests_taken, v_user_last_date, 1.0
            );

            v_new_user_elo := calculate_elo_rating(
                v_user_elo, v_test_elo, v_percentage_decimal, 32, v_user_volatility
            );

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
-- 2. get_recommended_test — exclude already-attempted tests
-- ============================================================================

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
    SELECT id INTO v_listening_type_id FROM dim_test_types WHERE type_code = 'listening';
    SELECT id INTO v_reading_type_id FROM dim_test_types WHERE type_code = 'reading';

    SELECT
        MAX(CASE WHEN test_type_id = v_listening_type_id THEN elo_rating END),
        MAX(CASE WHEN test_type_id = v_reading_type_id THEN elo_rating END)
    INTO v_user_listening_elo, v_user_reading_elo
    FROM user_skill_ratings
    WHERE user_id = p_user_id AND language_id = p_language_id;

    IF v_user_listening_elo IS NULL THEN v_user_listening_elo := 1200; END IF;
    IF v_user_reading_elo IS NULL THEN v_user_reading_elo := 1200; END IF;

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
