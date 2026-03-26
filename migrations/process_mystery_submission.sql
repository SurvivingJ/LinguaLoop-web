-- ============================================================================
-- Murder Mystery RPCs
-- ============================================================================
-- Idempotent: safe to re-run. Drops and recreates all mystery functions.
--
-- 1. process_mystery_submission — ELO scoring for mystery completions
-- 2. get_recommended_mysteries — ELO-matched mystery recommendations
-- ============================================================================


-- ============================================================================
-- 0. DROP EXISTING FUNCTIONS
-- ============================================================================

DROP FUNCTION IF EXISTS process_mystery_submission(UUID, UUID, SMALLINT, SMALLINT, JSONB, UUID);
DROP FUNCTION IF EXISTS get_recommended_mysteries(UUID, INTEGER);


-- ============================================================================
-- 1. PROCESS MYSTERY SUBMISSION
-- ============================================================================
-- Mirrors process_test_submission but for mysteries:
-- 1. Validates answers against mystery_questions (joined via mystery_scenes)
-- 2. Calculates ELO changes (K=32, same formula)
-- 3. Records attempt in mystery_attempts
-- 4. Updates user_skill_ratings and mystery_skill_ratings

CREATE OR REPLACE FUNCTION process_mystery_submission(
    p_user_id UUID,
    p_mystery_id UUID,
    p_language_id SMALLINT,
    p_test_type_id SMALLINT,
    p_responses JSONB,
    p_idempotency_key UUID DEFAULT NULL
)
RETURNS JSONB AS $$
DECLARE
    v_user_elo integer;
    v_mystery_elo integer;
    v_user_tests_taken integer;
    v_mystery_attempts integer;
    v_new_user_elo integer;
    v_new_mystery_elo integer;
    v_attempt_id uuid;
    v_attempt_number integer;
    v_is_first_attempt boolean;
    v_existing_attempt record;
    v_score integer := 0;
    v_total_questions integer := 0;
    v_question_results jsonb := '[]'::jsonb;
    v_question_record record;
    v_user_answer text;
    v_correct_answer text;
    v_is_correct boolean;
    v_percentage numeric;
    v_percentage_decimal numeric;
BEGIN
    -- ========================================================================
    -- SECURITY VALIDATION
    -- ========================================================================

    IF p_user_id != auth.uid() THEN
        RAISE EXCEPTION 'Unauthorized: Cannot submit mystery for another user';
    END IF;

    -- ========================================================================
    -- INPUT VALIDATION
    -- ========================================================================

    IF p_responses IS NULL OR jsonb_array_length(p_responses) = 0 THEN
        RAISE EXCEPTION 'No responses provided';
    END IF;

    -- ========================================================================
    -- ANSWER VALIDATION
    -- ========================================================================

    CREATE TEMP TABLE temp_mystery_responses ON COMMIT DROP AS
    SELECT
        (elem->>'question_id')::UUID as question_id,
        elem->>'selected_answer' as selected_answer
    FROM jsonb_array_elements(p_responses) as elem;

    -- Validate each question across all scenes of this mystery
    FOR v_question_record IN (
        SELECT mq.id, mq.answer
        FROM mystery_questions mq
        JOIN mystery_scenes ms ON ms.id = mq.scene_id
        WHERE ms.mystery_id = p_mystery_id
        ORDER BY ms.scene_number, mq.created_at
    ) LOOP
        SELECT selected_answer INTO v_user_answer
        FROM temp_mystery_responses
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

    DROP TABLE IF EXISTS temp_mystery_responses;

    IF v_total_questions = 0 THEN
        RAISE EXCEPTION 'No questions found for this mystery';
    END IF;

    -- ========================================================================
    -- IDEMPOTENCY CHECK
    -- ========================================================================

    IF p_idempotency_key IS NOT NULL THEN
        SELECT * INTO v_existing_attempt
        FROM mystery_attempts
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
    -- CALCULATE PERCENTAGE
    -- ========================================================================

    v_percentage := (v_score::numeric / v_total_questions::numeric) * 100;
    v_percentage_decimal := v_percentage / 100.0;

    -- ========================================================================
    -- DETERMINE ATTEMPT NUMBER
    -- ========================================================================

    SELECT COUNT(*) INTO v_attempt_number
    FROM mystery_attempts
    WHERE user_id = p_user_id AND mystery_id = p_mystery_id;

    v_attempt_number := v_attempt_number + 1;
    v_is_first_attempt := (v_attempt_number = 1);

    -- ========================================================================
    -- GET OR CREATE USER ELO RATING
    -- ========================================================================

    SELECT elo_rating, tests_taken
    INTO v_user_elo, v_user_tests_taken
    FROM user_skill_ratings
    WHERE user_id = p_user_id
      AND language_id = p_language_id
      AND test_type_id = p_test_type_id;

    IF NOT FOUND THEN
        v_user_elo := 1200;
        v_user_tests_taken := 0;

        INSERT INTO user_skill_ratings (
            user_id, language_id, test_type_id, elo_rating, tests_taken
        ) VALUES (
            p_user_id, p_language_id, p_test_type_id, v_user_elo, 0
        );
    END IF;

    -- ========================================================================
    -- GET OR CREATE MYSTERY ELO RATING
    -- ========================================================================

    SELECT elo_rating, total_attempts
    INTO v_mystery_elo, v_mystery_attempts
    FROM mystery_skill_ratings
    WHERE mystery_id = p_mystery_id;

    IF NOT FOUND THEN
        v_mystery_elo := 1400;
        v_mystery_attempts := 0;

        INSERT INTO mystery_skill_ratings (mystery_id, elo_rating, total_attempts)
        VALUES (p_mystery_id, v_mystery_elo, 0);
    END IF;

    -- ========================================================================
    -- CALCULATE ELO CHANGES (ONLY FOR FIRST ATTEMPTS)
    -- ========================================================================

    IF v_is_first_attempt THEN
        DECLARE
            expected_user_score numeric;
            k_factor integer := 32;
        BEGIN
            expected_user_score := 1.0 / (1.0 + POWER(10, (v_mystery_elo - v_user_elo) / 400.0));

            v_new_user_elo := ROUND(v_user_elo + k_factor * (v_percentage_decimal - expected_user_score));
            v_new_mystery_elo := ROUND(v_mystery_elo + k_factor * ((1.0 - v_percentage_decimal) - (1.0 - expected_user_score)));

            v_new_user_elo := GREATEST(400, LEAST(3000, v_new_user_elo));
            v_new_mystery_elo := GREATEST(400, LEAST(3000, v_new_mystery_elo));
        END;

        UPDATE user_skill_ratings
        SET elo_rating = v_new_user_elo,
            tests_taken = tests_taken + 1,
            last_test_date = CURRENT_DATE,
            updated_at = NOW()
        WHERE user_id = p_user_id
          AND language_id = p_language_id
          AND test_type_id = p_test_type_id;

        UPDATE mystery_skill_ratings
        SET elo_rating = v_new_mystery_elo,
            total_attempts = total_attempts + 1,
            updated_at = NOW()
        WHERE mystery_id = p_mystery_id;

        UPDATE mysteries
        SET total_attempts = total_attempts + 1,
            updated_at = NOW()
        WHERE id = p_mystery_id;
    ELSE
        v_new_user_elo := v_user_elo;
        v_new_mystery_elo := v_mystery_elo;
    END IF;

    -- ========================================================================
    -- INSERT ATTEMPT RECORD
    -- ========================================================================

    INSERT INTO mystery_attempts (
        user_id, mystery_id, score, total_questions,
        user_elo_before, user_elo_after,
        mystery_elo_before, mystery_elo_after,
        language_id, test_type_id,
        attempt_number, is_first_attempt,
        idempotency_key
    ) VALUES (
        p_user_id, p_mystery_id, v_score, v_total_questions,
        v_user_elo, v_new_user_elo,
        v_mystery_elo, v_new_mystery_elo,
        p_language_id, p_test_type_id,
        v_attempt_number, v_is_first_attempt,
        p_idempotency_key
    )
    RETURNING id INTO v_attempt_id;

    -- ========================================================================
    -- UPDATE USER_LANGUAGES
    -- ========================================================================

    INSERT INTO user_languages (
        user_id, language_id, total_tests_taken, last_test_date
    ) VALUES (
        p_user_id, p_language_id, 1, CURRENT_DATE
    )
    ON CONFLICT (user_id, language_id)
    DO UPDATE SET
        total_tests_taken = user_languages.total_tests_taken + 1,
        last_test_date = CURRENT_DATE,
        updated_at = NOW();

    -- ========================================================================
    -- RETURN RESULT
    -- ========================================================================

    RETURN jsonb_build_object(
        'success', true,
        'attempt_id', v_attempt_id,
        'attempt_number', v_attempt_number,
        'is_first_attempt', v_is_first_attempt,
        'user_elo_before', v_user_elo,
        'user_elo_after', v_new_user_elo,
        'user_elo_change', v_new_user_elo - v_user_elo,
        'mystery_elo_before', v_mystery_elo,
        'mystery_elo_after', v_new_mystery_elo,
        'score', v_score,
        'total_questions', v_total_questions,
        'percentage', v_percentage,
        'question_results', v_question_results,
        'message', CASE
            WHEN v_is_first_attempt THEN 'First attempt - ELO updated'
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
$$ LANGUAGE plpgsql SECURITY DEFINER;

GRANT EXECUTE ON FUNCTION process_mystery_submission TO authenticated;


-- ============================================================================
-- 2. GET RECOMMENDED MYSTERIES
-- ============================================================================
-- Returns mysteries within ±200 ELO of the user's mystery rating.

CREATE OR REPLACE FUNCTION get_recommended_mysteries(
    p_user_id UUID,
    p_language_id INTEGER
)
RETURNS SETOF JSONB AS $$
DECLARE
    v_user_elo integer;
    v_mystery_type_id integer;
BEGIN
    -- Get mystery test_type_id
    SELECT id INTO v_mystery_type_id
    FROM dim_test_types WHERE type_code = 'mystery';

    -- Get user's mystery ELO (default 1200 if no rating)
    SELECT COALESCE(
        (SELECT elo_rating FROM user_skill_ratings
         WHERE user_id = p_user_id
           AND language_id = p_language_id
           AND test_type_id = v_mystery_type_id),
        1200
    ) INTO v_user_elo;

    -- Return matching mysteries
    RETURN QUERY
    SELECT jsonb_build_object(
        'id', m.id,
        'slug', m.slug,
        'title', m.title,
        'premise', m.premise,
        'difficulty', m.difficulty,
        'language_id', m.language_id,
        'suspects', m.suspects,
        'total_attempts', m.total_attempts,
        'mystery_elo', COALESCE(msr.elo_rating, 1400),
        'user_elo', v_user_elo,
        'elo_gap', ABS(COALESCE(msr.elo_rating, 1400) - v_user_elo)
    )
    FROM mysteries m
    LEFT JOIN mystery_skill_ratings msr ON msr.mystery_id = m.id
    WHERE m.language_id = p_language_id
      AND m.is_active = true
      AND ABS(COALESCE(msr.elo_rating, 1400) - v_user_elo) <= 200
    ORDER BY ABS(COALESCE(msr.elo_rating, 1400) - v_user_elo) ASC
    LIMIT 10;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

GRANT EXECUTE ON FUNCTION get_recommended_mysteries TO authenticated;
