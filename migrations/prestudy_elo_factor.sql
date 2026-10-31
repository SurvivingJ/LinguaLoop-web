-- ============================================================================
-- prestudy_elo_factor.sql — 0.5x ELO on a first attempt made after prestudy
-- Date: 2026-10-31
-- Spec: wiki/features/test-prestudy.md (decision 2026-10-29: ELO factor 0.5)
--
-- * test_attempts.prestudied boolean NOT NULL DEFAULT false.
-- * process_test_submission gains p_prestudied boolean DEFAULT false. When
--   true on a FIRST attempt, both the user and the test K factor are halved
--   (composing with the furigana dampener) and elo_reduction_factor = 0.5 is
--   recorded. Repeat attempts are unchanged: the retry-slot factor and the
--   zero-ELO off-recommendation rule still apply, prestudied or not.
--
-- The body is the canonical one from sec_submission_rpcs_auth_gate.sql with
-- only those edits (checked live 2026-10-31: 8-arg signature, markers
-- c_furigana_dampener and v_record_factor present). Adding a parameter makes
-- a new overload, so the 8-arg function is dropped in the same transaction;
-- callers that omit p_prestudied resolve to the new function via its default.
-- Supersedes the process_test_submission definition in
-- sec_submission_rpcs_auth_gate.sql (that file also defines
-- process_dictation_submission, so it is not archived).
-- ============================================================================

BEGIN;

ALTER TABLE public.test_attempts
    ADD COLUMN IF NOT EXISTS prestudied boolean NOT NULL DEFAULT false;

COMMENT ON COLUMN public.test_attempts.prestudied IS
    'True when the learner studied the test with prestudy before this attempt; '
    'a prestudied first attempt moves ELO at 0.5x (elo_reduction_factor = 0.5).';

DROP FUNCTION IF EXISTS public.process_test_submission(uuid,uuid,smallint,smallint,jsonb,boolean,uuid,boolean);

CREATE OR REPLACE FUNCTION public.process_test_submission(
  p_user_id uuid,
  p_test_id uuid,
  p_language_id smallint,
  p_test_type_id smallint,
  p_responses jsonb,
  p_was_free_test boolean DEFAULT true,
  p_idempotency_key uuid DEFAULT NULL::uuid,
  p_furigana_used boolean DEFAULT false,
  p_prestudied boolean DEFAULT false
)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path = public, pg_temp
AS $function$
DECLARE
  c_furigana_dampener constant numeric := 0.5;
  c_prestudy_factor constant numeric := 0.5;
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
  v_record_factor numeric := NULL;   -- TASK-704: applied ADR-006 factor (NULL = none)
BEGIN
  -- Caller must be the user themselves, or the service-role backend (which has
  -- already verified the user's JWT). Written so a NULL auth.uid() REJECTS:
  -- the previous `p_user_id != auth.uid()` evaluated to NULL for anon callers
  -- and let them through. RETURN (not RAISE) so WHEN OTHERS doesn't flatten it.
  IF p_user_id IS NULL
     OR (auth.uid() IS DISTINCT FROM p_user_id
         AND COALESCE(auth.role(), '') <> 'service_role') THEN
    RETURN jsonb_build_object('success', false, 'error_code', 'unauthorized');
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
        THEN c_furigana_dampener ELSE 1.0 END
        * CASE WHEN p_prestudied THEN c_prestudy_factor ELSE 1.0 END;

      v_test_k_factor := CASE
        WHEN v_test_attempts < 20 THEN 48
        WHEN v_test_attempts < 50 THEN 24
        ELSE 16
      END;

      -- Prestudied first attempt (wiki/features/test-prestudy.md): both K
      -- factors at 0.5, recorded in elo_reduction_factor so the existing
      -- "0.5x ELO" badge explains the smaller move.
      IF p_prestudied THEN
        v_record_factor := c_prestudy_factor;
      END IF;

      v_new_user_elo := ROUND(v_user_elo + v_user_k_factor * (v_percentage_decimal - expected_user_score));
      v_new_test_elo := ROUND(v_test_elo + (v_test_k_factor * CASE WHEN p_prestudied THEN c_prestudy_factor ELSE 1.0 END)
        * ((1.0 - v_percentage_decimal) - (1.0 - expected_user_score)));

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
    -- ======================================================================
    -- TASK-704 / ADR-006 — repeat attempt: reduced-volatility ELO if and only
    -- if this test is in today's retry slot for this (user, language) and no
    -- reduced-ELO repeat was already recorded for this (user, test) today.
    -- Otherwise status quo (0 ELO), preserving prior behaviour.
    -- ======================================================================
    DECLARE
      v_is_retry_slot boolean := false;
      v_already_earned_today boolean := false;
      v_last_attempt_at timestamptz;
      v_prev_best numeric;
      v_days_since numeric;
      v_base numeric;
      v_bonus numeric;
      v_factor numeric;
      expected_user_score numeric;
      c_user_k_factor constant integer := 32;
      c_test_k_factor constant integer := 16;   -- ADR-006 retry test-side base K
    BEGIN
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
        v_bonus := CASE
          WHEN v_prev_best IS NOT NULL AND (v_percentage - v_prev_best) >= 15 THEN 0.25
          ELSE 0
        END;
        v_factor := LEAST(1.0, v_base + v_bonus);
        v_record_factor := v_factor;

        -- Live inline-ELO style (logistic expected score), scaled by v_factor.
        expected_user_score := 1.0 / (1.0 + POWER(10, (v_test_elo - v_user_elo) / 400.0));
        v_user_k_factor := c_user_k_factor
          * CASE WHEN p_furigana_used THEN c_furigana_dampener ELSE 1.0 END
          * v_factor;

        v_new_user_elo := ROUND(v_user_elo + v_user_k_factor * (v_percentage_decimal - expected_user_score));
        v_new_test_elo := ROUND(v_test_elo + (c_test_k_factor * v_factor) * ((1.0 - v_percentage_decimal) - (1.0 - expected_user_score)));

        v_new_user_elo := GREATEST(400, LEAST(3000, v_new_user_elo));
        v_new_test_elo := GREATEST(400, LEAST(3000, v_new_test_elo));

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
        -- Off-retry-slot repeat, or already earned today: status quo (0 ELO).
        v_new_user_elo := v_user_elo;
        v_new_test_elo := v_test_elo;
      END IF;
    END;
  END IF;

  INSERT INTO test_attempts (
    user_id, test_id, test_type_id, language_id, score, total_questions,
    attempt_number, is_first_attempt,
    user_elo_before, user_elo_after, test_elo_before, test_elo_after,
    tokens_consumed, was_free_test, idempotency_key, furigana_used,
    elo_reduction_factor, prestudied
  ) VALUES (
    p_user_id, p_test_id, p_test_type_id, p_language_id,
    v_score, v_total_questions, v_attempt_number, v_is_first_attempt,
    v_user_elo, v_new_user_elo, v_test_elo, v_new_test_elo,
    CASE WHEN p_was_free_test THEN 0 ELSE v_tokens_cost END,
    p_was_free_test, p_idempotency_key, p_furigana_used,
    v_record_factor, p_prestudied
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
    'test_elo_change', CASE
      WHEN v_is_first_attempt OR v_record_factor IS NOT NULL THEN v_new_test_elo - v_test_elo
      ELSE 0
    END,
    'elo_reduction_factor', v_record_factor,
    'tokens_cost', CASE WHEN p_was_free_test THEN 0 ELSE v_tokens_cost END,
    'score', v_score,
    'total_questions', v_total_questions,
    'percentage', v_percentage,
    'question_results', v_question_results,
    'message', CASE
      WHEN v_is_first_attempt AND p_prestudied THEN 'First attempt after prestudy - ELO at 0.5x'
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

REVOKE ALL ON FUNCTION public.process_test_submission(uuid,uuid,smallint,smallint,jsonb,boolean,uuid,boolean,boolean)
    FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.process_test_submission(uuid,uuid,smallint,smallint,jsonb,boolean,uuid,boolean,boolean) TO service_role;

COMMIT;
