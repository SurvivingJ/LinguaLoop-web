-- ============================================================================
-- Part G — Drop per-question response_time_ms from comprehension capture
-- Date: 2026-06-06
--
-- WHAT
--   * ALTER TABLE question_attempt_results DROP COLUMN response_time_ms.
--   * process_test_submission redefined = the live Part F body MINUS every
--     response-time bit (v_response_time_ms decl, the temp-table column, the
--     SELECT ... INTO it, the 'response_time_ms' key in v_question_results, and
--     the response_time_ms column+value in the question_attempt_results INSERT).
--
-- WHY
--   Comprehension reading/listening tests let users answer questions in any
--   order, so a per-question response time is meaningless — there is no
--   1->2->3 sequence to attribute time to. Total test time is already captured
--   via started_at/finished_at -> apply_attempt_timing_and_progress (Phase 13).
--   The per-question OUTCOME capture (is_correct, selected_answer,
--   correct_answer, is_first_attempt) is kept: it still powers distractor
--   pick-rate calibration and mis-key detection.
--
-- DRIFT NOTE (inherited from Part F, still deliberate)
--   The body below is the *live* definition of process_test_submission
--   (TEMP TABLE staging; RAISE EXCEPTION on unauthorized; SQLERRM in the error
--   envelope), NOT migrations/phase14_test_kfactor_decay.sql (unapplied CR-04).
--   This change is strictly subtractive relative to the live body: ELO maths,
--   scoring, idempotency, the per-question outcome INSERT (still wrapped in its
--   own BEGIN/EXCEPTION) and the error/auth surface are unchanged.
--
-- Idempotent: DROP COLUMN IF EXISTS; CREATE OR REPLACE FUNCTION.
-- Part G is now the canonical definer of process_test_submission (supersedes
-- the function definition in partF_question_attempt_results.sql; partF stays as
-- the canonical definer of the question_attempt_results table + RLS).
-- ============================================================================

BEGIN;

-- ---------------------------------------------------------------------------
-- 1. Drop the per-question response-time column
-- ---------------------------------------------------------------------------
ALTER TABLE public.question_attempt_results DROP COLUMN IF EXISTS response_time_ms;

-- ---------------------------------------------------------------------------
-- 2. process_test_submission — live body minus response-time capture
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.process_test_submission(
  p_user_id uuid,
  p_test_id uuid,
  p_language_id smallint,
  p_test_type_id smallint,
  p_responses jsonb,
  p_was_free_test boolean DEFAULT true,
  p_idempotency_key uuid DEFAULT NULL::uuid,
  p_furigana_used boolean DEFAULT false
)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
AS $function$
DECLARE
  c_furigana_dampener constant numeric := 0.5;
  v_user_k_factor numeric;
  v_test_k_factor integer;
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
  IF p_user_id != auth.uid() THEN
    RAISE EXCEPTION 'Unauthorized: Cannot submit test for another user';
  END IF;

  IF p_responses IS NULL OR jsonb_array_length(p_responses) = 0 THEN
    RAISE EXCEPTION 'No responses provided';
  END IF;

  CREATE TEMP TABLE temp_user_responses AS
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
      -- Reset per-iteration: SELECT INTO leaves stale values on a no-row match.
      v_user_answer := NULL;

      SELECT selected_answer
      INTO v_user_answer
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
          v_existing_attempt.user_elo_after - v_existing_attempt.user_elo_before,
          0
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

  IF v_is_first_attempt THEN
    DECLARE
      expected_user_score numeric;
      c_user_k_factor constant integer := 32;
    BEGIN
      expected_user_score := 1.0 / (1.0 + POWER(10, (v_test_elo - v_user_elo) / 400.0));

      v_user_k_factor := c_user_k_factor * CASE WHEN p_furigana_used
        THEN c_furigana_dampener ELSE 1.0 END;

      v_test_k_factor := CASE
        WHEN v_test_attempts < 20 THEN 48
        WHEN v_test_attempts < 50 THEN 24
        ELSE 16
      END;

      v_new_user_elo := ROUND(v_user_elo + v_user_k_factor * (v_percentage_decimal - expected_user_score));
      v_new_test_elo := ROUND(v_test_elo + v_test_k_factor * ((1.0 - v_percentage_decimal) - (1.0 - expected_user_score)));

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

  INSERT INTO test_attempts (
    user_id, test_id, test_type_id, language_id, score, total_questions,
    attempt_number, is_first_attempt,
    user_elo_before, user_elo_after, test_elo_before, test_elo_after,
    tokens_consumed, was_free_test, idempotency_key, furigana_used
  ) VALUES (
    p_user_id, p_test_id, p_test_type_id, p_language_id,
    v_score, v_total_questions, v_attempt_number, v_is_first_attempt,
    v_user_elo, v_new_user_elo, v_test_elo, v_new_test_elo,
    CASE WHEN p_was_free_test THEN 0 ELSE v_tokens_cost END,
    p_was_free_test, p_idempotency_key, p_furigana_used
  )
  RETURNING id INTO v_attempt_id;

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
  -- Part F #1 — persist per-question outcomes (additive, never fatal)
  -- ========================================================================
  -- Wrapped in its own block: a failure here must never roll back or mask a
  -- learner's already-computed submission. v_question_results is the exact
  -- per-question array returned to the client below.
  BEGIN
    INSERT INTO question_attempt_results (
      user_id, test_id, question_id, attempt_id,
      is_correct, selected_answer, correct_answer,
      is_first_attempt
    )
    SELECT
      p_user_id,
      p_test_id,
      (qr->>'question_id')::uuid,
      v_attempt_id,
      (qr->>'is_correct')::boolean,
      NULLIF(qr->>'selected_answer', ''),  -- '' (unanswered) -> NULL
      qr->>'correct_answer',
      v_is_first_attempt
    FROM jsonb_array_elements(v_question_results) AS qr;
  EXCEPTION WHEN OTHERS THEN
    RAISE WARNING 'question_attempt_results insert failed (non-fatal): % (SQLSTATE=%)',
      SQLERRM, SQLSTATE;
  END;

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
$function$;

COMMIT;
