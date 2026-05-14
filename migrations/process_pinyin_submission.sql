-- ============================================================================
-- process_pinyin_submission — accuracy-based test submission for the
-- Pinyin Tone Trainer.
-- ============================================================================
-- The Pinyin trainer does not use MC questions; it produces a per-character
-- accuracy. process_test_submission cannot grade accuracy-based attempts
-- because it iterates the `questions` table and string-compares answers. This
-- dedicated function accepts pre-counted correct/total chars and records the
-- attempt + updates ELO without touching `questions`.
-- ============================================================================

CREATE OR REPLACE FUNCTION process_pinyin_submission(
  p_user_id UUID,
  p_test_id UUID,
  p_language_id SMALLINT,
  p_test_type_id SMALLINT,
  p_correct_chars INTEGER,
  p_total_chars INTEGER,
  p_was_free_test BOOLEAN DEFAULT TRUE,
  p_idempotency_key UUID DEFAULT NULL
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
  v_score integer;
  v_total_questions integer;
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

  IF p_total_chars IS NULL OR p_total_chars <= 0 THEN
    RAISE EXCEPTION 'Invalid total_chars: must be > 0';
  END IF;

  IF p_correct_chars IS NULL OR p_correct_chars < 0 OR p_correct_chars > p_total_chars THEN
    RAISE EXCEPTION 'Invalid correct_chars: must satisfy 0 <= correct_chars <= total_chars';
  END IF;

  v_score := p_correct_chars;
  v_total_questions := p_total_chars;

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
        'user_elo_before', v_existing_attempt.user_elo_before,
        'user_elo_after', v_existing_attempt.user_elo_after,
        'user_elo_change', COALESCE(
          v_existing_attempt.user_elo_after - v_existing_attempt.user_elo_before,
          0
        ),
        'test_elo_before', v_existing_attempt.test_elo_before,
        'test_elo_after', v_existing_attempt.test_elo_after,
        'test_elo_change', COALESCE(
          v_existing_attempt.test_elo_after - v_existing_attempt.test_elo_before,
          0
        ),
        'score', v_existing_attempt.score,
        'total_questions', v_existing_attempt.total_questions,
        'percentage', v_existing_attempt.percentage,
        'message', 'Duplicate submission detected - returning cached result'
      );
    END IF;
  END IF;

  -- ========================================================================
  -- TOKEN COST
  -- ========================================================================

  v_tokens_cost := get_test_token_cost(p_user_id);

  -- ========================================================================
  -- PERCENTAGE
  -- ========================================================================

  v_percentage := (v_score::numeric / v_total_questions::numeric) * 100;
  v_percentage_decimal := v_percentage / 100.0;

  -- ========================================================================
  -- ATTEMPT NUMBER & FIRST ATTEMPT STATUS
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

  IF v_is_first_attempt THEN
    DECLARE
      expected_user_score numeric;
      k_factor integer := 32;
    BEGIN
      expected_user_score := 1.0 / (1.0 + POWER(10, (v_test_elo - v_user_elo) / 400.0));

      v_new_user_elo := ROUND(v_user_elo + k_factor * (v_percentage_decimal - expected_user_score));
      v_new_test_elo := ROUND(v_test_elo + k_factor * ((1.0 - v_percentage_decimal) - (1.0 - expected_user_score)));

      v_new_user_elo := GREATEST(400, LEAST(3000, v_new_user_elo));
      v_new_test_elo := GREATEST(400, LEAST(3000, v_new_test_elo));
    END;

    UPDATE user_skill_ratings
    SET
      elo_rating = v_new_user_elo,
      tests_taken = tests_taken + 1,
      last_test_date = CURRENT_DATE,
      updated_at = NOW()
    WHERE user_id = p_user_id
      AND language_id = p_language_id
      AND test_type_id = p_test_type_id;

    UPDATE test_skill_ratings
    SET
      elo_rating = v_new_test_elo,
      total_attempts = total_attempts + 1,
      updated_at = NOW()
    WHERE test_id = p_test_id
      AND test_type_id = p_test_type_id;
  ELSE
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
  -- RETURN SUCCESS RESPONSE
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

GRANT EXECUTE ON FUNCTION process_pinyin_submission TO authenticated;
