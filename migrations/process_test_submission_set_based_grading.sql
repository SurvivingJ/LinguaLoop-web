-- =============================================================================
-- process_test_submission_set_based_grading.sql  (codebase review 2026-11, Efficiency)
-- =============================================================================
-- Purpose: same results from process_test_submission with less work per call
-- and no lost rating updates under concurrency. Three changes, nothing else:
--
--   1. Grading is one joined query over `questions` and the submitted answers.
--      Before: CREATE TEMP TABLE per call (catalog churn on every submission),
--      a loop over the questions with one lookup each, then DROP TABLE.
--   2. The duplicate-submission (idempotency key) check runs BEFORE grading, so
--      a retried request returns the cached attempt without grading again.
--   3. The learner's user_skill_ratings row and the test's test_skill_ratings
--      row are read FOR UPDATE. Before, two concurrent submissions could both
--      read the same ELO and the later write discarded the earlier change; two
--      identical retries could both pass the duplicate check.
--
-- Base: the body in prestudy_elo_factor.sql, verbatim from the ELO branch
-- (`IF v_is_first_attempt THEN`) to the end. Signature, return shape, auth
-- gate, error envelope, ELO maths, retry-slot rule and every INSERT are
-- unchanged. This file supersedes the function definition in
-- prestudy_elo_factor.sql (which stays: it is the only record of
-- test_attempts.prestudied).
--
-- Known differences from the previous body (all on invalid or racing input):
--   * A retried request with a known idempotency key and a malformed payload
--     (a question_id that is not a UUID) now returns the cached attempt; before
--     it failed on the cast first.
--   * A test with no questions and a malformed payload now fails with
--     "division by zero" instead of the UUID cast error (both are the same
--     {success:false} envelope).
--   * Two questions of one test with exactly the same created_at keep the order
--     the sort gives them, as before; no tie-break was added.
--   * Concurrent submissions by one learner (same language and test type) now
--     wait for each other instead of interleaving.
--
-- Not covered: FOR UPDATE cannot lock a row that does not exist yet, so two
-- concurrent FIRST-EVER submissions (no rating row) can still both insert one.
-- That needs unique constraints the repo does not record; see the optional
-- follow-up at the end of this file.
--
-- Validated on a local PostgreSQL 16 stub schema only (not against live):
-- the old and new bodies were run side by side over 4,000 generated
-- submissions (first attempts, repeats, retry slot with aged history, prestudy,
-- furigana, duplicate keys, unanswered and duplicated answers, JSON-null keys,
-- unknown question ids, questions sharing one created_at, empty tests, missing
-- and foreign JWTs). Every reply was identical apart from attempt_id, except
-- 4 cases of the empty-test difference above, and test_attempts,
-- user_skill_ratings, test_skill_ratings, user_languages and
-- question_attempt_results ended with identical rows. Two overlapping retries
-- with one idempotency key produced two attempts with the old body, and one
-- attempt plus a cached reply with the new one.
--
-- Pre-checks:
--   1. prestudy_elo_factor.sql is applied (this replaces its 9-argument function):
--        SELECT 'public.process_test_submission(uuid,uuid,smallint,smallint,jsonb,boolean,uuid,boolean,boolean)'::regprocedure;
--   2. Keep the current body for the rollback:
--        SELECT pg_get_functiondef('public.process_test_submission(uuid,uuid,smallint,smallint,jsonb,boolean,uuid,boolean,boolean)'::regprocedure);
--      and confirm it still matches prestudy_elo_factor.sql (marker: `CREATE TEMP
--      TABLE temp_user_responses`). If live has moved on, re-derive this file.
--   3. Apply in a quiet period and submit one test end to end afterwards.
--
-- Idempotent: CREATE OR REPLACE, same signature; REVOKE/GRANT repeated.
-- REQUIRES USER APPROVAL TO APPLY LIVE.
--
-- Rollback: re-run the CREATE OR REPLACE FUNCTION statement from
-- migrations/prestudy_elo_factor.sql (or the definition saved in pre-check 2).
-- =============================================================================

BEGIN;

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
  v_user_rating_found boolean;
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

  -- Lock this learner's rating row for the rest of the transaction. Two
  -- submissions from the same learner for the same language and test type now
  -- run one after the other: the second waits here, then sees the first one's
  -- attempt in the duplicate check and the attempt count below. (A learner's
  -- very first submission has no row to lock yet; see the header.)
  SELECT elo_rating, tests_taken, last_test_date
  INTO v_user_elo, v_user_tests_taken, v_user_last_date
  FROM user_skill_ratings
  WHERE user_id = p_user_id
    AND language_id = p_language_id
    AND test_type_id = p_test_type_id
  FOR UPDATE;
  v_user_rating_found := FOUND;

  -- Duplicate submission: answer from the stored attempt before doing any work.
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

  -- Grade every question of the test in one statement (no temp table, no
  -- per-question lookup). Same rules as before: questions in created_at
  -- order; an unanswered question counts as '' and is wrong; when a question
  -- id appears twice in the payload the first entry wins.
  WITH resp AS (
    SELECT DISTINCT ON (x.question_id) x.question_id, x.selected_answer
    FROM (
      SELECT (e.elem->>'question_id')::uuid AS question_id,
             e.elem->>'selected_answer' AS selected_answer,
             e.n
      FROM jsonb_array_elements(p_responses) WITH ORDINALITY AS e(elem, n)
    ) x
    ORDER BY x.question_id, x.n
  ),
  graded AS (
    SELECT q.id,
           q.ord,
           COALESCE(r.selected_answer, '') AS selected_answer,
           q.answer #>> '{}' AS correct_answer,
           COALESCE(r.selected_answer, '') = (q.answer #>> '{}') AS is_correct
    FROM (
      SELECT qq.id, qq.answer, row_number() OVER (ORDER BY qq.created_at) AS ord
      FROM questions qq
      WHERE qq.test_id = p_test_id
    ) q
    LEFT JOIN resp r ON r.question_id = q.id
  )
  SELECT COUNT(*),
         COUNT(*) FILTER (WHERE g.is_correct),
         COALESCE(jsonb_agg(jsonb_build_object(
             'question_id', g.id::TEXT,
             'selected_answer', g.selected_answer,
             'correct_answer', g.correct_answer,
             'is_correct', g.is_correct
           ) ORDER BY g.ord), '[]'::jsonb)
  INTO v_total_questions, v_score, v_question_results
  FROM graded g;

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

  IF NOT v_user_rating_found THEN
    v_user_elo := 1200;
    v_user_tests_taken := 0;
    v_user_last_date := NULL;

    INSERT INTO user_skill_ratings (
      user_id, language_id, test_type_id, elo_rating, tests_taken
    ) VALUES (
      p_user_id, p_language_id, p_test_type_id, v_user_elo, 0
    );
  END IF;

  -- Locked as well: concurrent first attempts on one test by different
  -- learners would otherwise both start from the same test ELO and the
  -- second write would discard the first one's change.
  SELECT elo_rating, total_attempts
  INTO v_test_elo, v_test_attempts
  FROM test_skill_ratings
  WHERE test_id = p_test_id AND test_type_id = p_test_type_id
  FOR UPDATE;

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

-- -----------------------------------------------------------------------------
-- OPTIONAL FOLLOW-UP, not executed: unique constraints so a rating row cannot
-- be duplicated by two concurrent first submissions. The repo does not show
-- whether live already has them. Check for existing constraints and duplicates
-- first; each statement fails if duplicates exist.
--
--   SELECT conrelid::regclass, conname, pg_get_constraintdef(oid) FROM pg_constraint
--    WHERE conrelid IN ('public.user_skill_ratings'::regclass, 'public.test_skill_ratings'::regclass)
--      AND contype IN ('u', 'p');
--   SELECT user_id, language_id, test_type_id, count(*) FROM public.user_skill_ratings
--    GROUP BY 1, 2, 3 HAVING count(*) > 1;
--   SELECT test_id, test_type_id, count(*) FROM public.test_skill_ratings
--    GROUP BY 1, 2 HAVING count(*) > 1;
--
--   CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS user_skill_ratings_user_lang_type_key
--       ON public.user_skill_ratings (user_id, language_id, test_type_id);
--   CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS test_skill_ratings_test_type_key
--       ON public.test_skill_ratings (test_id, test_type_id);
-- -----------------------------------------------------------------------------
