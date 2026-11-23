-- ============================================================================
-- skill_ratings_writers_on_conflict.sql — rating-row writers tolerate the new
-- natural-key unique indexes (finding F-10, part 2 of 2)
-- Date: 2026-11-23   Review: pkg8. NOT APPLIED.
--
-- APPLY ORDER: AFTER skill_ratings_natural_key_unique.sql. ON CONFLICT (cols)
-- needs a unique index on exactly those columns; before the indexes exist,
-- every call that reaches one of these INSERTs fails with 42P10 ("no unique or
-- exclusion constraint matching the ON CONFLICT specification"), i.e. every
-- learner's first submission of a test type and every first attempt on a test.
--
-- WHAT: CREATE OR REPLACE of the six functions that create user_skill_ratings /
-- test_skill_ratings rows. Each body is its canonical file's body (md5-equal
-- to live on 2026-11-23) with ONLY the get-or-create INSERTs changed:
--   * process_test_submission, process_dictation_submission,
--     process_pinyin_submission, process_pitch_accent_submission,
--     process_classifier_drill_submission: INSERT ... ON CONFLICT (natural key)
--     DO NOTHING, then re-read the row into the same variables the function's
--     own get-or-create SELECT fills (with FOR UPDATE where that SELECT has it:
--     process_test_submission only). The drill reads back only elo_rating,
--     because its not-found branch sets only the ELO.
--   * apply_calibration_to_skill_ratings: its seed INSERT becomes
--     ON CONFLICT DO UPDATE SET elo_rating, updated_at, which is exactly what its
--     v_has_usr branch does.
-- Grading, ELO formulas, tokens, attempts and error envelopes are untouched
-- (byte-identical outside the marked INSERT blocks; diff against the canonical
-- files to see it). Attributes, owner and grants are the live ones: SECURITY
-- DEFINER; search_path 'public', 'pg_temp' (apply_calibration_to_skill_ratings:
-- 'public' only, as live); EXECUTE service_role only. Note the canonical
-- task747_apply_calibration_to_skill_ratings.sql GRANTs EXECUTE to
-- authenticated, which live does not have; this file follows live.
--
-- WHY: once the unique indexes exist, the plain INSERT of a learner's or test's
-- first rating row raises unique_violation when two first submissions race.
-- The submission RPCs would catch it in WHEN OTHERS and return success:false
-- (the learner's submission is lost); apply_calibration_to_skill_ratings has no
-- handler, so the calibration call would error. With this file both proceed
-- against the one row.
--
-- WHAT A LEARNER WOULD NOTICE: nothing in normal use. The re-read returns the
-- values the function just inserted (1200 / 0 / NULL for the learner row,
-- 1400 / 0 for the test row: the same values its not-found branch assigns), so
-- every non-racing submission computes exactly what it computes today. In the
-- rare race, the second submission now scores against the row the first one
-- created (and, for process_test_submission, waits for it), instead of
-- creating a duplicate row.
--
-- PRECONDITIONS: skill_ratings_natural_key_unique.sql applied and both indexes
-- valid (its VERIFY AFTER query). Live bodies unchanged since 2026-11-23 (VERIFY
-- BEFORE below: every ok = true; if one is false, a later migration changed it:
-- do not apply this file, re-derive it).
--
-- VERIFY BEFORE (read-only; expect ok = true, anon_x = false, auth_x = false):
--   SELECT v.fn, md5(regexp_replace(regexp_replace(p.prosrc, '--[^\n]*', '', 'g'), '\s', '', 'g')) = v.expected AS ok,
--          has_function_privilege('anon', p.oid, 'EXECUTE') AS anon_x,
--          has_function_privilege('authenticated', p.oid, 'EXECUTE') AS auth_x
--     FROM (VALUES
--   ('public.process_test_submission(uuid,uuid,smallint,smallint,jsonb,boolean,uuid,boolean,boolean)'::regprocedure, 'd41268bad067cad2791f8ad6457d10bf'),
--   ('public.process_dictation_submission(uuid,uuid,smallint,smallint,integer,integer,smallint,jsonb,boolean,uuid)'::regprocedure, '8574313a4ad2206834e80d996ca340ed'),
--   ('public.process_pinyin_submission(uuid,uuid,smallint,smallint,integer,integer,boolean,uuid)'::regprocedure, '1b7078d5d262848b8387694bf7ce1cb6'),
--   ('public.process_pitch_accent_submission(uuid,uuid,smallint,smallint,integer,integer,boolean,uuid,boolean)'::regprocedure, '42583de070e622fabd00954553489a63'),
--   ('public.process_classifier_drill_submission(uuid,uuid,smallint,smallint,integer,integer,boolean,uuid)'::regprocedure, '90791cd1b64cb28ca67063f1aa2af57a'),
--   ('public.apply_calibration_to_skill_ratings(uuid,smallint)'::regprocedure, 'd08aa2936fcba38620590e390da5bf69')
--   ) AS v(fn, expected) JOIN pg_proc p ON p.oid = v.fn;
--
-- VERIFY AFTER (read-only; expect ok = true, anon_x = false, auth_x = false):
--   SELECT v.fn, md5(regexp_replace(regexp_replace(p.prosrc, '--[^\n]*', '', 'g'), '\s', '', 'g')) = v.expected AS ok,
--          has_function_privilege('anon', p.oid, 'EXECUTE') AS anon_x,
--          has_function_privilege('authenticated', p.oid, 'EXECUTE') AS auth_x
--     FROM (VALUES
--   ('public.process_test_submission(uuid,uuid,smallint,smallint,jsonb,boolean,uuid,boolean,boolean)'::regprocedure, '3718f167bb3b8c5f55e8d9ad439c19ff'),
--   ('public.process_dictation_submission(uuid,uuid,smallint,smallint,integer,integer,smallint,jsonb,boolean,uuid)'::regprocedure, '886f1a285487dbece7002c0f3bc721cd'),
--   ('public.process_pinyin_submission(uuid,uuid,smallint,smallint,integer,integer,boolean,uuid)'::regprocedure, '1d61bae8c203d6168f357b4a41e286c3'),
--   ('public.process_pitch_accent_submission(uuid,uuid,smallint,smallint,integer,integer,boolean,uuid,boolean)'::regprocedure, '771d97aec0a95af66bb1a31836f0f8e7'),
--   ('public.process_classifier_drill_submission(uuid,uuid,smallint,smallint,integer,integer,boolean,uuid)'::regprocedure, 'cfa1cad029740bcf5e7095fa776e7b0a'),
--   ('public.apply_calibration_to_skill_ratings(uuid,smallint)'::regprocedure, '614a9b736674a4adc6dc2a7624a3d626')
--   ) AS v(fn, expected) JOIN pg_proc p ON p.oid = v.fn;
--
-- ROLLBACK: migrations/skill_ratings_writers_on_conflict_rollback.sql (the six
-- live bodies verbatim, live grants). Roll this file back BEFORE dropping the
-- indexes.
--
-- After applying: this file is the canonical definition of the six functions;
-- archive process_test_submission_set_based_grading.sql, process_dictation_submission.sql,
-- process_pinyin_submission.sql, process_pitch_accent_submission.sql,
-- process_classifier_drill_submission.sql per migrations/CLAUDE.md (check
-- rule 4 for task747_apply_calibration_to_skill_ratings.sql and the
-- pitch-accent file's DROP of the old overload).
--
-- security-lint: allow-uid-compare apply_calibration_to_skill_ratings tests auth.uid() IS NULL
-- first, so its `p_user_id <> auth.uid()` branch only runs with a non-NULL uid
-- (verbatim live body; task747 is in HISTORICAL_UID_COMPARE_FILES for the same line).
--
-- Idempotent: CREATE OR REPLACE + REVOKE/GRANT in one transaction.
-- ============================================================================

BEGIN;

-- ---------------------------------------------------------------------------
-- public.process_test_submission(uuid,uuid,smallint,smallint,jsonb,boolean,uuid,boolean,boolean)
-- source: migrations/process_test_submission_set_based_grading.sql
-- ---------------------------------------------------------------------------
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
    )
    ON CONFLICT (user_id, language_id, test_type_id) DO NOTHING;
    -- unique index on the natural key (skill_ratings_natural_key_unique.sql):
    -- a concurrent first submission may have created the row; read what is there.
    SELECT elo_rating, tests_taken, last_test_date
    INTO v_user_elo, v_user_tests_taken, v_user_last_date
    FROM user_skill_ratings
    WHERE user_id = p_user_id AND language_id = p_language_id AND test_type_id = p_test_type_id
    FOR UPDATE;
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
    )
    ON CONFLICT (test_id, test_type_id) DO NOTHING;
    -- unique index on the natural key (skill_ratings_natural_key_unique.sql):
    -- a concurrent first submission may have created the row; read what is there.
    SELECT elo_rating, total_attempts
    INTO v_test_elo, v_test_attempts
    FROM test_skill_ratings
    WHERE test_id = p_test_id AND test_type_id = p_test_type_id
    FOR UPDATE;
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

REVOKE ALL ON FUNCTION public.process_test_submission(uuid,uuid,smallint,smallint,jsonb,boolean,uuid,boolean,boolean) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.process_test_submission(uuid,uuid,smallint,smallint,jsonb,boolean,uuid,boolean,boolean) TO service_role;

-- ---------------------------------------------------------------------------
-- public.process_dictation_submission(uuid,uuid,smallint,smallint,integer,integer,smallint,jsonb,boolean,uuid)
-- source: migrations/process_dictation_submission.sql
-- ---------------------------------------------------------------------------
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
SET search_path = public, pg_temp
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
  -- Caller must be the user themselves, or the service-role backend (which has
  -- already verified the user's JWT). Written so a NULL auth.uid() REJECTS.
  -- RETURN (not RAISE) so WHEN OTHERS doesn't flatten it.
  IF p_user_id IS NULL
     OR (auth.uid() IS DISTINCT FROM p_user_id
         AND COALESCE(auth.role(), '') <> 'service_role') THEN
    RETURN jsonb_build_object('success', false, 'error_code', 'unauthorized');
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
    )
    ON CONFLICT (user_id, language_id, test_type_id) DO NOTHING;
    -- unique index on the natural key (skill_ratings_natural_key_unique.sql):
    -- a concurrent first submission may have created the row; read what is there.
    SELECT elo_rating, tests_taken, last_test_date
    INTO v_user_elo, v_user_tests_taken, v_user_last_date
    FROM user_skill_ratings
    WHERE user_id = p_user_id AND language_id = p_language_id AND test_type_id = p_test_type_id;
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
    )
    ON CONFLICT (test_id, test_type_id) DO NOTHING;
    -- unique index on the natural key (skill_ratings_natural_key_unique.sql):
    -- a concurrent first submission may have created the row; read what is there.
    SELECT elo_rating, total_attempts
    INTO v_test_elo, v_test_attempts
    FROM test_skill_ratings
    WHERE test_id = p_test_id AND test_type_id = p_test_type_id;
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
  -- CR-04: see migrations/phase14_test_kfactor_decay.sql for rationale.
  RAISE WARNING 'process_dictation_submission failed: % (SQLSTATE=%)', SQLERRM, SQLSTATE;
  RETURN jsonb_build_object(
    'success', false,
    'error_code', 'submission_failed',
    'sqlstate', SQLSTATE
  );
END;
$function$;

REVOKE ALL ON FUNCTION public.process_dictation_submission(uuid,uuid,smallint,smallint,integer,integer,smallint,jsonb,boolean,uuid) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.process_dictation_submission(uuid,uuid,smallint,smallint,integer,integer,smallint,jsonb,boolean,uuid) TO service_role;

-- ---------------------------------------------------------------------------
-- public.process_pinyin_submission(uuid,uuid,smallint,smallint,integer,integer,boolean,uuid)
-- source: migrations/process_pinyin_submission.sql
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.process_pinyin_submission(
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

  -- Caller must be the user themselves, or the service-role backend (which has
  -- already verified the user's JWT). Written so a NULL auth.uid() REJECTS.
  -- RETURN (not RAISE) so WHEN OTHERS doesn't flatten it.
  IF p_user_id IS NULL
     OR (auth.uid() IS DISTINCT FROM p_user_id
         AND COALESCE(auth.role(), '') <> 'service_role') THEN
    RETURN jsonb_build_object('success', false, 'error_code', 'unauthorized');
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
    )
    ON CONFLICT (user_id, language_id, test_type_id) DO NOTHING;
    -- unique index on the natural key (skill_ratings_natural_key_unique.sql):
    -- a concurrent first submission may have created the row; read what is there.
    SELECT elo_rating, tests_taken, last_test_date
    INTO v_user_elo, v_user_tests_taken, v_user_last_date
    FROM user_skill_ratings
    WHERE user_id = p_user_id AND language_id = p_language_id AND test_type_id = p_test_type_id;
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
    )
    ON CONFLICT (test_id, test_type_id) DO NOTHING;
    -- unique index on the natural key (skill_ratings_natural_key_unique.sql):
    -- a concurrent first submission may have created the row; read what is there.
    SELECT elo_rating, total_attempts
    INTO v_test_elo, v_test_attempts
    FROM test_skill_ratings
    WHERE test_id = p_test_id AND test_type_id = p_test_type_id;
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
  -- CR-04: see migrations/phase14_test_kfactor_decay.sql for rationale.
  RAISE WARNING 'process_pinyin_submission failed: % (SQLSTATE=%)', SQLERRM, SQLSTATE;
  RETURN jsonb_build_object(
    'success', false,
    'error_code', 'submission_failed',
    'sqlstate', SQLSTATE
  );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER
SET search_path = public, pg_temp;

REVOKE ALL ON FUNCTION public.process_pinyin_submission(uuid,uuid,smallint,smallint,integer,integer,boolean,uuid) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.process_pinyin_submission(uuid,uuid,smallint,smallint,integer,integer,boolean,uuid) TO service_role;

-- ---------------------------------------------------------------------------
-- public.process_pitch_accent_submission(uuid,uuid,smallint,smallint,integer,integer,boolean,uuid,boolean)
-- source: migrations/process_pitch_accent_submission.sql
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.process_pitch_accent_submission(
  p_user_id UUID,
  p_test_id UUID,
  p_language_id SMALLINT,
  p_test_type_id SMALLINT,
  p_correct_units INTEGER,
  p_total_units INTEGER,
  p_was_free_test BOOLEAN DEFAULT TRUE,
  p_idempotency_key UUID DEFAULT NULL,
  p_furigana_used BOOLEAN DEFAULT FALSE
)
RETURNS JSONB AS $$
DECLARE
  c_furigana_dampener constant numeric := 0.5;
  v_user_k_factor numeric;
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

  -- Caller must be the user themselves, or the service-role backend (which has
  -- already verified the user's JWT). Written so a NULL auth.uid() REJECTS.
  -- RETURN (not RAISE) so WHEN OTHERS doesn't flatten it.
  IF p_user_id IS NULL
     OR (auth.uid() IS DISTINCT FROM p_user_id
         AND COALESCE(auth.role(), '') <> 'service_role') THEN
    RETURN jsonb_build_object('success', false, 'error_code', 'unauthorized');
  END IF;

  -- ========================================================================
  -- INPUT VALIDATION
  -- ========================================================================

  IF p_total_units IS NULL OR p_total_units <= 0 THEN
    RAISE EXCEPTION 'Invalid total_units: must be > 0';
  END IF;

  IF p_correct_units IS NULL OR p_correct_units < 0 OR p_correct_units > p_total_units THEN
    RAISE EXCEPTION 'Invalid correct_units: must satisfy 0 <= correct_units <= total_units';
  END IF;

  v_score := p_correct_units;
  v_total_questions := p_total_units;

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
    )
    ON CONFLICT (user_id, language_id, test_type_id) DO NOTHING;
    -- unique index on the natural key (skill_ratings_natural_key_unique.sql):
    -- a concurrent first submission may have created the row; read what is there.
    SELECT elo_rating, tests_taken, last_test_date
    INTO v_user_elo, v_user_tests_taken, v_user_last_date
    FROM user_skill_ratings
    WHERE user_id = p_user_id AND language_id = p_language_id AND test_type_id = p_test_type_id;
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
    )
    ON CONFLICT (test_id, test_type_id) DO NOTHING;
    -- unique index on the natural key (skill_ratings_natural_key_unique.sql):
    -- a concurrent first submission may have created the row; read what is there.
    SELECT elo_rating, total_attempts
    INTO v_test_elo, v_test_attempts
    FROM test_skill_ratings
    WHERE test_id = p_test_id AND test_type_id = p_test_type_id;
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

      -- Dampen user K when the learner had furigana on; test K unchanged.
      v_user_k_factor := k_factor * CASE WHEN p_furigana_used THEN c_furigana_dampener ELSE 1.0 END;

      v_new_user_elo := ROUND(v_user_elo + v_user_k_factor * (v_percentage_decimal - expected_user_score));
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
    idempotency_key,
    furigana_used
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
    p_idempotency_key,
    p_furigana_used
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
  -- CR-04: see migrations/phase14_test_kfactor_decay.sql for rationale.
  RAISE WARNING 'process_pitch_accent_submission failed: % (SQLSTATE=%)', SQLERRM, SQLSTATE;
  RETURN jsonb_build_object(
    'success', false,
    'error_code', 'submission_failed',
    'sqlstate', SQLSTATE
  );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER
SET search_path = public, pg_temp;

REVOKE ALL ON FUNCTION public.process_pitch_accent_submission(uuid,uuid,smallint,smallint,integer,integer,boolean,uuid,boolean) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.process_pitch_accent_submission(uuid,uuid,smallint,smallint,integer,integer,boolean,uuid,boolean) TO service_role;

-- ---------------------------------------------------------------------------
-- public.process_classifier_drill_submission(uuid,uuid,smallint,smallint,integer,integer,boolean,uuid)
-- source: migrations/process_classifier_drill_submission.sql
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.process_classifier_drill_submission(
  p_user_id UUID,
  p_test_id UUID,
  p_language_id SMALLINT,
  p_test_type_id SMALLINT,
  p_correct_items INTEGER,
  p_total_items INTEGER,
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
  -- SECURITY: caller must be the user submitting
  -- Caller must be the user themselves, or the service-role backend (which has
  -- already verified the user's JWT). Written so a NULL auth.uid() REJECTS.
  -- RETURN (not RAISE) so WHEN OTHERS doesn't flatten it.
  IF p_user_id IS NULL
     OR (auth.uid() IS DISTINCT FROM p_user_id
         AND COALESCE(auth.role(), '') <> 'service_role') THEN
    RETURN jsonb_build_object('success', false, 'error_code', 'unauthorized');
  END IF;

  -- VALIDATION
  IF p_total_items IS NULL OR p_total_items <= 0 THEN
    RAISE EXCEPTION 'Invalid total_items: must be > 0';
  END IF;
  IF p_correct_items IS NULL OR p_correct_items < 0 OR p_correct_items > p_total_items THEN
    RAISE EXCEPTION 'Invalid correct_items: must satisfy 0 <= correct_items <= total_items';
  END IF;

  v_score := p_correct_items;
  v_total_questions := p_total_items;

  -- IDEMPOTENCY
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
        'user_elo_change', COALESCE(v_existing_attempt.user_elo_after - v_existing_attempt.user_elo_before, 0),
        'test_elo_before', v_existing_attempt.test_elo_before,
        'test_elo_after', v_existing_attempt.test_elo_after,
        'test_elo_change', COALESCE(v_existing_attempt.test_elo_after - v_existing_attempt.test_elo_before, 0),
        'score', v_existing_attempt.score,
        'total_questions', v_existing_attempt.total_questions,
        'percentage', v_existing_attempt.percentage,
        'message', 'Duplicate submission detected - returning cached result'
      );
    END IF;
  END IF;

  -- TOKEN COST
  v_tokens_cost := get_test_token_cost(p_user_id);

  -- PERCENTAGE
  v_percentage := (v_score::numeric / v_total_questions::numeric) * 100;
  v_percentage_decimal := v_percentage / 100.0;

  -- ATTEMPT NUMBER (classifier drill is replayable; ELO motion is
  -- subject to the same first-attempt-only rule as pinyin/pitch).
  SELECT COUNT(*) INTO v_attempt_number
  FROM test_attempts
  WHERE user_id = p_user_id
    AND test_id = p_test_id
    AND test_type_id = p_test_type_id;

  v_attempt_number := v_attempt_number + 1;
  v_is_first_attempt := (v_attempt_number = 1);

  -- USER ELO (create row on first run)
  SELECT elo_rating, tests_taken, last_test_date
  INTO v_user_elo, v_user_tests_taken, v_user_last_date
  FROM user_skill_ratings
  WHERE user_id = p_user_id
    AND language_id = p_language_id
    AND test_type_id = p_test_type_id;

  IF NOT FOUND THEN
    v_user_elo := 1200;
    INSERT INTO user_skill_ratings (user_id, language_id, test_type_id, elo_rating, tests_taken)
    VALUES (p_user_id, p_language_id, p_test_type_id, v_user_elo, 0)
    ON CONFLICT (user_id, language_id, test_type_id) DO NOTHING;
    -- unique index on the natural key (skill_ratings_natural_key_unique.sql):
    -- a concurrent first submission may have created the row; read what is there.
    SELECT elo_rating
    INTO v_user_elo
    FROM user_skill_ratings
    WHERE user_id = p_user_id AND language_id = p_language_id AND test_type_id = p_test_type_id;
  END IF;

  -- TEST ELO (sentinel test row)
  SELECT elo_rating, total_attempts
  INTO v_test_elo, v_test_attempts
  FROM test_skill_ratings
  WHERE test_id = p_test_id AND test_type_id = p_test_type_id;

  IF NOT FOUND THEN
    v_test_elo := 1400;
    INSERT INTO test_skill_ratings (test_id, test_type_id, elo_rating, total_attempts)
    VALUES (p_test_id, p_test_type_id, v_test_elo, 0)
    ON CONFLICT (test_id, test_type_id) DO NOTHING;
    -- unique index on the natural key (skill_ratings_natural_key_unique.sql):
    -- a concurrent first submission may have created the row; read what is there.
    SELECT elo_rating
    INTO v_test_elo
    FROM test_skill_ratings
    WHERE test_id = p_test_id AND test_type_id = p_test_type_id;
  END IF;

  -- ELO UPDATE (first attempt only, per process_pinyin_submission policy).
  -- The classifier drill is infinite, so "first attempt" means first ever
  -- session against the sentinel test for this user. Repeats compound their
  -- skill via flashcard/BKT layers in the future (Phase 2).
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
    -- Repeats: count as practice (increment total_attempts) but no ELO
    -- motion. This matches the pinyin/pitch convention and prevents
    -- infinite-grind farming.
    v_new_user_elo := v_user_elo;
    v_new_test_elo := v_test_elo;

    UPDATE user_skill_ratings
       SET tests_taken = tests_taken + 1,
           last_test_date = CURRENT_DATE,
           updated_at = NOW()
     WHERE user_id = p_user_id
       AND language_id = p_language_id
       AND test_type_id = p_test_type_id;

    UPDATE test_skill_ratings
       SET total_attempts = total_attempts + 1,
           updated_at = NOW()
     WHERE test_id = p_test_id
       AND test_type_id = p_test_type_id;
  END IF;

  -- ATTEMPT RECORD
  INSERT INTO test_attempts (
    user_id, test_id, test_type_id, language_id,
    score, total_questions,
    attempt_number, is_first_attempt,
    user_elo_before, user_elo_after, test_elo_before, test_elo_after,
    tokens_consumed, was_free_test, idempotency_key
  ) VALUES (
    p_user_id, p_test_id, p_test_type_id, p_language_id,
    v_score, v_total_questions,
    v_attempt_number, v_is_first_attempt,
    v_user_elo, v_new_user_elo, v_test_elo, v_new_test_elo,
    CASE WHEN p_was_free_test THEN 0 ELSE v_tokens_cost END,
    p_was_free_test, p_idempotency_key
  )
  RETURNING id INTO v_attempt_id;

  -- LANGUAGE ACTIVITY TRACKING
  INSERT INTO user_languages (user_id, language_id, total_tests_taken, last_test_date)
  VALUES (p_user_id, p_language_id, 1, CURRENT_DATE)
  ON CONFLICT (user_id, language_id) DO UPDATE
    SET total_tests_taken = user_languages.total_tests_taken + 1,
        last_test_date = CURRENT_DATE,
        updated_at = NOW();

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
      ELSE 'Repeat - ELO unchanged'
    END
  );

EXCEPTION WHEN OTHERS THEN
  RETURN jsonb_build_object(
    'success', false,
    'error', SQLERRM,
    'error_detail', SQLSTATE
  );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER
SET search_path = public, pg_temp;

REVOKE ALL ON FUNCTION public.process_classifier_drill_submission(uuid,uuid,smallint,smallint,integer,integer,boolean,uuid) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.process_classifier_drill_submission(uuid,uuid,smallint,smallint,integer,integer,boolean,uuid) TO service_role;

-- ---------------------------------------------------------------------------
-- public.apply_calibration_to_skill_ratings(uuid,smallint)
-- source: migrations/task747_apply_calibration_to_skill_ratings.sql
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.apply_calibration_to_skill_ratings(
    p_user_id     uuid,
    p_language_id smallint)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path TO 'public'
AS $function$
DECLARE
    c_min_items    constant integer  := 20;
    c_max_se       constant numeric  := 0.75;
    c_stale        constant interval := interval '90 days';
    c_session_gap  constant interval := interval '1 hour';
    c_rate_limit   constant interval := interval '7 days';
    c_seed_below   constant integer  := 5;
    c_deadband     constant integer  := 200;
    c_damp         constant numeric  := 0.25;
    c_cap          constant numeric  := 150;
    c_floor        constant integer  := 875;
    c_ceiling      constant integer  := 1925;

    v_has_state    boolean;
    v_zipf         numeric;
    v_se           numeric;
    v_items        integer;
    v_last_run     timestamptz;
    v_seed         integer;
    v_in_session   boolean;

    v_type         record;
    v_has_usr      boolean;
    v_elo_before   integer;
    v_tests        integer;
    v_diff         integer;
    v_new          integer;
    v_source       text;
    v_reason       text;
    v_decisions    jsonb := '[]'::jsonb;
BEGIN
    IF auth.uid() IS NULL THEN
        IF COALESCE(auth.role(), '') <> 'service_role' THEN
            RAISE EXCEPTION 'Unauthorized: no authenticated user';
        END IF;
    ELSIF p_user_id <> auth.uid() THEN
        RAISE EXCEPTION 'Unauthorized: Cannot adjust ratings for another user';
    END IF;

    PERFORM pg_advisory_xact_lock(
        hashtextextended('apply_calibration_to_skill_ratings:' || p_user_id::text
                         || ':' || p_language_id::text, 0));

    SELECT ucs.ability_zipf, ucs.ability_se, ucs.items_answered, ucs.last_run_at
      INTO v_zipf, v_se, v_items, v_last_run
      FROM user_calibration_state ucs
     WHERE ucs.user_id = p_user_id
       AND ucs.language_id = p_language_id
       AND ucs.mode = 'definition';
    v_has_state := FOUND;

    IF v_has_state AND v_zipf IS NOT NULL THEN
        v_seed := calibration_zipf_to_elo(v_zipf);   -- + type_offset, 0 in v1
    END IF;

    v_in_session := EXISTS (
        SELECT 1 FROM test_attempts ta
         WHERE ta.user_id = p_user_id
           AND ta.language_id = p_language_id
           AND ta.created_at > now() - c_session_gap);

    FOR v_type IN
        SELECT dtt.id, dtt.type_code
          FROM dim_test_types dtt
         WHERE dtt.type_code IN ('reading', 'listening', 'dictation', 'pitch_accent')
           AND dtt.is_active = true
           AND EXISTS (SELECT 1 FROM test_skill_ratings tsr
                         JOIN tests t ON t.id = tsr.test_id
                        WHERE tsr.test_type_id = dtt.id
                          AND t.language_id = p_language_id
                          AND t.is_active = true)
         ORDER BY dtt.id
    LOOP
        SELECT usr.elo_rating, usr.tests_taken
          INTO v_elo_before, v_tests
          FROM user_skill_ratings usr
         WHERE usr.user_id = p_user_id
           AND usr.language_id = p_language_id
           AND usr.test_type_id = v_type.id
         ORDER BY usr.updated_at DESC NULLS LAST
         LIMIT 1;
        v_has_usr := FOUND;
        IF NOT v_has_usr THEN
            v_elo_before := NULL;
            v_tests := 0;
        END IF;

        v_source := 'skipped';
        v_new := v_elo_before;
        v_reason := NULL;

        IF NOT v_has_state OR v_zipf IS NULL THEN
            v_reason := 'G1_no_state';
        ELSIF v_items < c_min_items THEN
            v_reason := 'G2_low_items';
        ELSIF v_se IS NULL OR v_se > c_max_se THEN
            v_reason := 'G3_high_se';
        ELSIF v_last_run < now() - c_stale THEN
            v_reason := 'G4_stale';
        ELSIF v_in_session THEN
            v_reason := 'G5_in_session';
        ELSIF EXISTS (
            SELECT 1 FROM user_skill_rating_adjustments a
             WHERE a.user_id = p_user_id
               AND a.language_id = p_language_id
               AND a.test_type_id = v_type.id
               AND a.source <> 'skipped'
               AND a.created_at > now() - c_rate_limit) THEN
            v_reason := 'G6_rate_limit';
        ELSIF v_tests < c_seed_below THEN
            v_source := 'calibration_seed';
            v_reason := 'seed_tests_taken_lt_5';
            v_new := GREATEST(c_floor, LEAST(c_ceiling, v_seed));
        ELSE
            v_diff := v_seed - v_elo_before;
            IF abs(v_diff) > c_deadband THEN
                v_source := 'calibration_correct';
                v_reason := 'correct_outside_deadband';
                v_new := GREATEST(c_floor, LEAST(c_ceiling,
                            round(v_elo_before
                                  + sign(v_diff) * LEAST(c_damp * abs(v_diff), c_cap))::integer));
            ELSE
                v_reason := 'within_deadband';
            END IF;
        END IF;

        IF v_source <> 'skipped' THEN
            IF v_has_usr THEN
                UPDATE user_skill_ratings
                   SET elo_rating = v_new, updated_at = now()
                 WHERE user_id = p_user_id
                   AND language_id = p_language_id
                   AND test_type_id = v_type.id;
            ELSE
                INSERT INTO user_skill_ratings (user_id, language_id, test_type_id, elo_rating, tests_taken)
                VALUES (p_user_id, p_language_id, v_type.id, v_new, 0)
                -- a submission created the row since the read above: do what the
                -- v_has_usr branch does (unique index, skill_ratings_natural_key_unique.sql).
                ON CONFLICT (user_id, language_id, test_type_id)
                DO UPDATE SET elo_rating = EXCLUDED.elo_rating, updated_at = now();
            END IF;
        END IF;

        INSERT INTO user_skill_rating_adjustments (
            user_id, language_id, test_type_id, source, elo_before, elo_after,
            ability_zipf, ability_se, seed_elo_computed, tests_taken_at_write, reason)
        VALUES (
            p_user_id, p_language_id, v_type.id, v_source, v_elo_before, v_new,
            v_zipf, v_se, v_seed, v_tests, v_reason);

        v_decisions := v_decisions || jsonb_build_object(
            'test_type',   v_type.type_code,
            'source',      v_source,
            'reason',      v_reason,
            'elo_before',  v_elo_before,
            'elo_after',   v_new,
            'seed_elo',    v_seed,
            'tests_taken', v_tests);
    END LOOP;

    RETURN jsonb_build_object(
        'user_id',      p_user_id,
        'language_id',  p_language_id,
        'ability_zipf', v_zipf,
        'ability_se',   v_se,
        'decisions',    v_decisions);
END;
$function$;

REVOKE ALL ON FUNCTION public.apply_calibration_to_skill_ratings(uuid,smallint) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.apply_calibration_to_skill_ratings(uuid,smallint) TO service_role;

COMMIT;
