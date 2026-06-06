-- ============================================================================
-- Part F #1 — Per-question outcome capture (content-QA feedback loop)
-- Date: 2026-06-06
--
-- response_time_ms removed by partG (comprehension is order-free; total time only)
--   The per-question response_time_ms column (#4) and all of its plumbing were
--   dropped by migrations/partG_qar_drop_response_time.sql. This file has been
--   edited to its final, response-time-free state. partG is now the canonical
--   definer of process_test_submission; this file remains the canonical definer
--   of the question_attempt_results table + RLS.
--
-- WHAT
--   * New table public.question_attempt_results — one row per gradable
--     comprehension question per attempt, mirroring word_quiz_results.
--   * process_test_submission redefined to persist those rows (it already
--     computed them in v_question_results and discarded them).
--
-- WHY (no IRT required)
--   * Distractor pick-rates calibrate the live distractor-plausibility judge.
--   * Mis-key detection: strong scorers consistently "wrong" on an item ⇒ the
--     LLM keyed the wrong answer (content bug).
--   * Per-question p-values flag trivial / broken items.
--   Side benefit: keeps item-grain (IRT) possible later without a backfill.
--
-- DRIFT NOTE (deliberate)
--   The body below is based on the *live* definition of process_test_submission
--   (TEMP TABLE staging; RAISE EXCEPTION on unauthorized; SQLERRM in the error
--   envelope), NOT on migrations/phase14_test_kfactor_decay.sql, which carries
--   an unapplied CR-04 hardening (typed error_code envelope, jsonb_to_recordset,
--   masked SQLERRM) that never reached live. Per the Part F decision this change
--   is strictly additive: ELO maths, scoring, idempotency and the error/auth
--   surface are byte-for-byte the live behaviour. The ONLY addition is the
--   question_attempt_results INSERT, wrapped in its own BEGIN/EXCEPTION so a
--   logging-table failure can never fail a learner's submission.
--   Aligning live to the CR-04 version is intentionally left out of scope.
--
-- Idempotent: CREATE TABLE/INDEX IF NOT EXISTS; CREATE OR REPLACE FUNCTION;
-- DROP POLICY IF EXISTS before each CREATE POLICY.
-- ============================================================================

BEGIN;

-- ---------------------------------------------------------------------------
-- 1. Table — mirrors word_quiz_results (bkt_vocabulary_tracking.sql)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.question_attempt_results (
    id               BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id          UUID NOT NULL REFERENCES public.users(id),
    test_id          UUID NOT NULL REFERENCES public.tests(id),
    question_id      UUID NOT NULL REFERENCES public.questions(id),
    attempt_id       UUID REFERENCES public.test_attempts(id),
    is_correct       BOOLEAN NOT NULL,
    selected_answer  TEXT,            -- NULL = question left unanswered
    correct_answer   TEXT,
    is_first_attempt BOOLEAN NOT NULL DEFAULT true,
    created_at       TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE public.question_attempt_results IS
    'Part F #1: per-question comprehension outcomes. Powers distractor '
    'pick-rate calibration, mis-key detection, and per-item p-values. '
    'Written by process_test_submission (definer).';

-- Per-item analytics (p-values, mis-key detection)
CREATE INDEX IF NOT EXISTS idx_qar_question ON public.question_attempt_results(question_id);
-- Distractor pick-rate per item
CREATE INDEX IF NOT EXISTS idx_qar_question_selected ON public.question_attempt_results(question_id, selected_answer);
-- First-attempt-only p-values (the honest difficulty signal)
CREATE INDEX IF NOT EXISTS idx_qar_question_first ON public.question_attempt_results(question_id, is_first_attempt);
-- Per-test rollups + per-user / per-attempt lookups
CREATE INDEX IF NOT EXISTS idx_qar_test ON public.question_attempt_results(test_id);
CREATE INDEX IF NOT EXISTS idx_qar_user ON public.question_attempt_results(user_id);
CREATE INDEX IF NOT EXISTS idx_qar_attempt ON public.question_attempt_results(attempt_id);

-- ---------------------------------------------------------------------------
-- 2. RLS — own-data + service-role + admin-view triple
--    (mirrors enable_rls_on_user_owned_tables.sql / word_quiz_results)
-- ---------------------------------------------------------------------------
ALTER TABLE public.question_attempt_results ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS qar_own_data ON public.question_attempt_results;
CREATE POLICY qar_own_data ON public.question_attempt_results
  FOR ALL
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS qar_service_role ON public.question_attempt_results;
CREATE POLICY qar_service_role ON public.question_attempt_results
  FOR ALL
  USING (auth.role() = 'service_role');

DROP POLICY IF EXISTS qar_admin_view ON public.question_attempt_results;
CREATE POLICY qar_admin_view ON public.question_attempt_results
  FOR SELECT
  USING (is_admin(auth.uid()));

-- ---------------------------------------------------------------------------
-- 3. process_test_submission — live body + additive per-question outcome capture
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
