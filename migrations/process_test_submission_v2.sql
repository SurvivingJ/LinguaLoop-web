-- ============================================================================
-- Updated process_test_submission Function with Answer Validation
-- ============================================================================
-- This migration updates the process_test_submission function to:
-- 1. Accept user responses as JSONB instead of pre-calculated score
-- 2. Validate answers against database questions
-- 3. Calculate score internally
-- 4. Return per-question results
-- ============================================================================

CREATE OR REPLACE FUNCTION process_test_submission(
  p_user_id UUID,
  p_test_id UUID,
  p_language_id SMALLINT,
  p_test_type_id SMALLINT,
  p_responses JSONB,              -- NEW: User's answers
  p_was_free_test BOOLEAN DEFAULT TRUE,
  p_idempotency_key UUID DEFAULT NULL  -- UUID to match test_attempts.idempotency_key
)
RETURNS JSONB AS $$
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
  -- NEW VARIABLES FOR VALIDATION
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
  -- ANSWER VALIDATION
  -- ========================================================================

  -- Build response lookup for O(1) access
  CREATE TEMP TABLE temp_user_responses AS
  SELECT
      (elem->>'question_id')::UUID as question_id,
      elem->>'selected_answer' as selected_answer
  FROM jsonb_array_elements(p_responses) as elem;

  -- Validate each question
  FOR v_question_record IN (
      SELECT q.id, q.answer
      FROM questions q
      WHERE q.test_id = p_test_id
      ORDER BY q.created_at
  ) LOOP
      -- Get user's answer from temp table
      SELECT selected_answer INTO v_user_answer
      FROM temp_user_responses
      WHERE question_id = v_question_record.id;

      -- Default to empty if not answered
      v_user_answer := COALESCE(v_user_answer, '');

      -- Extract correct answer from JSONB (stored as JSON string like "Answer text")
      v_correct_answer := v_question_record.answer #>> '{}';

      -- Compare answers (case-sensitive string match)
      v_is_correct := (v_user_answer = v_correct_answer);

      -- Increment score if correct
      IF v_is_correct THEN
          v_score := v_score + 1;
      END IF;

      -- Build result object for this question
      v_question_results := v_question_results || jsonb_build_object(
          'question_id', v_question_record.id::TEXT,
          'selected_answer', v_user_answer,
          'correct_answer', v_correct_answer,
          'is_correct', v_is_correct
      );

      v_total_questions := v_total_questions + 1;
  END LOOP;

  -- Clean up temp table
  DROP TABLE IF EXISTS temp_user_responses;

  -- ========================================================================
  -- IDEMPOTENCY CHECK
  -- ========================================================================

  IF p_idempotency_key IS NOT NULL THEN
    SELECT * INTO v_existing_attempt
    FROM test_attempts
    WHERE user_id = p_user_id AND idempotency_key = p_idempotency_key;

    IF FOUND THEN
      -- Return cached response
      RETURN jsonb_build_object(
        'success', true,
        'attempt_id', v_existing_attempt.id,
        'cached', true,
        'user_elo_change', COALESCE(
          v_existing_attempt.user_elo_after - v_existing_attempt.user_elo_before,
          0
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
  -- CALCULATE PERCENTAGE (0-100 scale to match generated column)
  -- ========================================================================

  v_percentage := (v_score::numeric / v_total_questions::numeric) * 100;
  v_percentage_decimal := v_percentage / 100.0;

  -- ========================================================================
  -- DETERMINE ATTEMPT NUMBER & FIRST ATTEMPT STATUS
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
    -- Create new user skill rating (starting ELO: 1200)
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
    -- Create new test skill rating (starting ELO: 1400)
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

  IF v_is_first_attempt THEN
    -- Simple ELO calculation (K-factor = 32)
    -- Expected score for user = 1 / (1 + 10^((test_elo - user_elo) / 400))
    DECLARE
      expected_user_score numeric;
      k_factor integer := 32;
    BEGIN
      expected_user_score := 1.0 / (1.0 + POWER(10, (v_test_elo - v_user_elo) / 400.0));

      -- New user ELO = old ELO + K * (actual_score - expected_score)
      -- Use decimal form (0-1) for ELO calculations
      v_new_user_elo := ROUND(v_user_elo + k_factor * (v_percentage_decimal - expected_user_score));

      -- New test ELO = old ELO + K * (inverse_score - expected_test_score)
      v_new_test_elo := ROUND(v_test_elo + k_factor * ((1.0 - v_percentage_decimal) - (1.0 - expected_user_score)));

      -- Clamp ELO to valid range (400-3000)
      v_new_user_elo := GREATEST(400, LEAST(3000, v_new_user_elo));
      v_new_test_elo := GREATEST(400, LEAST(3000, v_new_test_elo));
    END;

    -- Update user skill rating
    UPDATE user_skill_ratings
    SET
      elo_rating = v_new_user_elo,
      tests_taken = tests_taken + 1,
      last_test_date = CURRENT_DATE,
      updated_at = NOW()
    WHERE user_id = p_user_id
      AND language_id = p_language_id
      AND test_type_id = p_test_type_id;

    -- Update test skill rating
    UPDATE test_skill_ratings
    SET
      elo_rating = v_new_test_elo,
      total_attempts = total_attempts + 1,
      updated_at = NOW()
    WHERE test_id = p_test_id
      AND test_type_id = p_test_type_id;
  ELSE
    -- Retake: No ELO change
    v_new_user_elo := v_user_elo;
    v_new_test_elo := v_test_elo;
  END IF;

  -- ========================================================================
  -- INSERT ATTEMPT RECORD
  -- ========================================================================

  INSERT INTO test_attempts (
    user_id,
    test_id,
    test_type_id,
    language_id,
    score,
    total_questions,
    attempt_number,
    is_first_attempt,
    user_elo_before,
    user_elo_after,
    test_elo_before,
    test_elo_after,
    tokens_consumed,
    was_free_test,
    idempotency_key
  ) VALUES (
    p_user_id,
    p_test_id,
    p_test_type_id,
    p_language_id,
    v_score,
    v_total_questions,
    v_attempt_number,
    v_is_first_attempt,
    v_user_elo,
    v_new_user_elo,
    v_test_elo,
    v_new_test_elo,
    CASE WHEN p_was_free_test THEN 0 ELSE v_tokens_cost END,
    p_was_free_test,
    p_idempotency_key
  )
  RETURNING id INTO v_attempt_id;

  -- ========================================================================
  -- UPDATE USER_LANGUAGES (TRACK LANGUAGE ACTIVITY)
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
  -- RETURN SUCCESS RESPONSE WITH QUESTION RESULTS
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
    'question_results', v_question_results,  -- NEW: Per-question results
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

-- Grant execute permission
GRANT EXECUTE ON FUNCTION process_test_submission TO authenticated;
