-- ============================================================================
-- process_dictation_submission — word-accuracy submission for dictation mode
-- ============================================================================
-- Dictation accepts a free-form typed transcript. Scoring (tokenization +
-- word-level alignment + Levenshtein fuzzy match) happens in Python before
-- this RPC is called — pure-SQL Levenshtein over tokenized jsonb arrays is
-- fragile, slower, and harder to test than the Python implementation.
--
-- Inputs are pre-computed:
--   p_word_correct / p_word_total — counts from the grader
--   p_replay_count                — number of audio plays
--   p_diff_payload                — per-token opcodes for the result UI
--
-- ELO logic mirrors process_test_submission (V4) but composes a fresh-attempt
-- replay penalty multiplier into the K factor on first attempts AND retry-slot
-- repeats:
--   replay_factor = GREATEST(0.5, 1.0 - 0.10 * GREATEST(0, replay_count - 1))
--
-- One replay is free (typical learner plays once). The 0.50 floor mirrors
-- ADR-006 retry-slot logic in spirit but higher (a fresh attempt with many
-- replays still carries more signal than a same-day repeat).
--
-- The composed factor is persisted to test_attempts.elo_reduction_factor so
-- the existing profile.html "Review · 0.45×" badge renderer picks it up.
-- ============================================================================

CREATE OR REPLACE FUNCTION public.process_dictation_submission(
  p_user_id          uuid,
  p_test_id          uuid,
  p_language_id      smallint,
  p_test_type_id     smallint,
  p_word_correct     integer,
  p_word_total       integer,
  p_replay_count     smallint,
  p_diff_payload     jsonb,
  p_was_free_test    boolean DEFAULT true,
  p_idempotency_key  uuid    DEFAULT NULL
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
  v_user_volatility numeric;
  v_replay_factor numeric;
  v_is_retry_slot boolean := false;
  v_already_earned_today boolean := false;
  v_last_attempt_at timestamptz;
  v_prev_best numeric;
  v_days_since numeric;
  v_base numeric;
  v_bonus numeric;
  v_retry_factor numeric;
  v_composed_factor numeric;
  v_record_factor numeric := NULL;
BEGIN
  -- ========================================================================
  -- SECURITY
  -- ========================================================================
  IF p_user_id != auth.uid() THEN
    RAISE EXCEPTION 'Unauthorized: Cannot submit test for another user';
  END IF;

  -- ========================================================================
  -- INPUT VALIDATION
  -- ========================================================================
  IF p_word_total IS NULL OR p_word_total <= 0 THEN
    RAISE EXCEPTION 'Invalid word_total: must be > 0';
  END IF;

  IF p_word_correct IS NULL OR p_word_correct < 0 OR p_word_correct > p_word_total THEN
    RAISE EXCEPTION 'Invalid word_correct: must satisfy 0 <= word_correct <= word_total';
  END IF;

  IF p_replay_count IS NULL OR p_replay_count < 1 THEN
    RAISE EXCEPTION 'Invalid replay_count: must be >= 1';
  END IF;

  -- ========================================================================
  -- IDEMPOTENCY
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
          v_existing_attempt.user_elo_after - v_existing_attempt.user_elo_before, 0
        ),
        'test_elo_before', v_existing_attempt.test_elo_before,
        'test_elo_after', v_existing_attempt.test_elo_after,
        'test_elo_change', COALESCE(
          v_existing_attempt.test_elo_after - v_existing_attempt.test_elo_before, 0
        ),
        'score', v_existing_attempt.score,
        'total_questions', v_existing_attempt.total_questions,
        'percentage', v_existing_attempt.percentage,
        'replay_count', v_existing_attempt.replay_count,
        'replay_factor', v_existing_attempt.elo_reduction_factor,
        'diff', v_existing_attempt.dictation_diff,
        'message', 'Duplicate submission detected - returning cached result'
      );
    END IF;
  END IF;

  -- ========================================================================
  -- TOKEN COST + PERCENTAGE
  -- ========================================================================
  v_tokens_cost := get_test_token_cost(p_user_id);
  v_percentage := (p_word_correct::numeric / p_word_total::numeric) * 100;
  v_percentage_decimal := v_percentage / 100.0;

  -- Replay penalty: first listen is free, then -0.10 per extra play, floor 0.50
  v_replay_factor := GREATEST(0.5, 1.0 - 0.10 * GREATEST(0, p_replay_count - 1));

  -- ========================================================================
  -- ATTEMPT NUMBER
  -- ========================================================================
  SELECT COUNT(*) INTO v_attempt_number
  FROM test_attempts
  WHERE user_id = p_user_id
    AND test_id = p_test_id
    AND test_type_id = p_test_type_id;

  v_attempt_number := v_attempt_number + 1;
  v_is_first_attempt := (v_attempt_number = 1);

  -- ========================================================================
  -- USER ELO (get-or-create)
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
  -- TEST ELO (get-or-create)
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

  v_user_volatility := calculate_volatility_multiplier(
    v_user_tests_taken, v_user_last_date, 1.0
  );

  -- ========================================================================
  -- ELO UPDATE PATH
  -- ========================================================================
  IF v_is_first_attempt THEN
    -- Fresh attempt: full K * volatility * replay_factor
    v_composed_factor := v_replay_factor;

    v_new_user_elo := calculate_elo_rating(
      v_user_elo, v_test_elo, v_percentage_decimal,
      32, v_user_volatility * v_replay_factor
    );
    v_new_test_elo := calculate_elo_rating(
      v_test_elo, v_user_elo, 1.0 - v_percentage_decimal,
      16, v_replay_factor
    );

    -- Persist composed factor (replay_factor) so badge rendering works for
    -- replay-penalised first attempts. NULL only when replay_count = 1 AND
    -- no other factor applies (i.e. factor == 1.0).
    v_record_factor := CASE WHEN v_replay_factor < 1.0 THEN v_replay_factor ELSE NULL END;

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
    -- Repeat attempt: check retry-slot eligibility (mirrors comprehension RPC)
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
      WHERE user_id = p_user_id AND test_id = p_test_id;

      v_days_since := EXTRACT(EPOCH FROM (NOW() - COALESCE(v_last_attempt_at, NOW()))) / 86400.0;
      v_base := LEAST(1.0, GREATEST(0.20, v_days_since / 60.0));

      IF v_prev_best IS NOT NULL AND (v_percentage - v_prev_best) >= 15 THEN
        v_bonus := 0.25;
      ELSE
        v_bonus := 0;
      END IF;

      v_retry_factor := LEAST(1.0, v_base + v_bonus);
      -- Compose retry decay with replay penalty multiplicatively
      v_composed_factor := v_retry_factor * v_replay_factor;
      v_record_factor := v_composed_factor;

      v_new_user_elo := calculate_elo_rating(
        v_user_elo, v_test_elo, v_percentage_decimal,
        32, v_user_volatility * v_composed_factor
      );
      v_new_test_elo := calculate_elo_rating(
        v_test_elo, v_user_elo, 1.0 - v_percentage_decimal,
        16, v_composed_factor
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

  -- ========================================================================
  -- INSERT ATTEMPT
  -- ========================================================================
  INSERT INTO test_attempts (
    user_id, test_id, test_type_id, language_id,
    score, total_questions,
    attempt_number, is_first_attempt,
    user_elo_before, user_elo_after,
    test_elo_before, test_elo_after,
    tokens_consumed, was_free_test, idempotency_key,
    elo_reduction_factor,
    replay_count, dictation_word_correct, dictation_word_total, dictation_diff
  ) VALUES (
    p_user_id, p_test_id, p_test_type_id, p_language_id,
    p_word_correct, p_word_total,
    v_attempt_number, v_is_first_attempt,
    v_user_elo, v_new_user_elo,
    v_test_elo, v_new_test_elo,
    CASE WHEN p_was_free_test THEN 0 ELSE v_tokens_cost END,
    p_was_free_test, p_idempotency_key,
    v_record_factor,
    p_replay_count, p_word_correct, p_word_total, p_diff_payload
  )
  RETURNING id INTO v_attempt_id;

  -- ========================================================================
  -- USER_LANGUAGES
  -- ========================================================================
  INSERT INTO user_languages (user_id, language_id, total_tests_taken, last_test_date)
  VALUES (p_user_id, p_language_id, 1, CURRENT_DATE)
  ON CONFLICT (user_id, language_id)
  DO UPDATE SET
    total_tests_taken = user_languages.total_tests_taken + 1,
    last_test_date = CURRENT_DATE,
    updated_at = NOW();

  -- ========================================================================
  -- RETURN
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
    'test_elo_change', v_new_test_elo - v_test_elo,
    'elo_reduction_factor', v_record_factor,
    'replay_count', p_replay_count,
    'replay_factor', v_replay_factor,
    'tokens_cost', CASE WHEN p_was_free_test THEN 0 ELSE v_tokens_cost END,
    'score', p_word_correct,
    'total_questions', p_word_total,
    'percentage', v_percentage,
    'diff', p_diff_payload,
    'message', CASE
      WHEN v_is_first_attempt AND v_replay_factor < 1.0
        THEN 'First attempt - reduced ELO applied (' || p_replay_count || ' plays)'
      WHEN v_is_first_attempt THEN 'First attempt - ELO updated'
      WHEN v_record_factor IS NOT NULL THEN 'Retry-slot repeat - composed factor applied'
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

GRANT EXECUTE ON FUNCTION public.process_dictation_submission TO authenticated;
