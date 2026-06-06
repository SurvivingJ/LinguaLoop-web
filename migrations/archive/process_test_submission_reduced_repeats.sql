-- ============================================================================
-- Reduced-Volatility ELO on Daily-Load Retry-Slot Repeats
-- Date: 2026-05-15
--
-- Today, repeat attempts (is_first_attempt = false) skip ELO entirely. The
-- only surface that re-shows a previously-attempted test is the daily-load
-- retry slot (services/test_service.py _compute_daily_load), which picks
-- sub-70% tests with a 24h cooldown and stores them in daily_test_loads
-- with slot_type = 'retry'. This migration grants reduced-volatility ELO
-- movement on the first daily-retry-slot submission per (user, test, day),
-- using a continuous time-decay factor with an improvement bonus.
--
-- Eligibility (server-side, no client flag):
--   1. is_first_attempt = false
--   2. test appears in today's daily_test_loads.test_ids with slot_type='retry'
--      for this user and language
--   3. user has not already earned reduced-ELO on this (user, test) today
--
-- Factor:
--   base   = clamp(0.20, days_since_last_attempt / 60.0, 1.0)
--   bonus  = 0.25 if (current_percentage - max_prior_percentage) >= 15 else 0
--   factor = LEAST(1.0, base + bonus)
--
-- Applied symmetrically:
--   user K = 32 * volatility_multiplier * factor
--   test K = 16 * factor   (test side still skips the volatility helper)
--
-- The applied factor is persisted in test_attempts.elo_reduction_factor:
--   NULL  → no factor applied (first attempt = full ELO, or off-rec = 0 ELO)
--   <1.0  → reduced-volatility repeat
--   1.0   → eligible repeat that hit the long-gap ceiling (effectively fresh)
--
-- Idempotent (CREATE OR REPLACE, ADD COLUMN IF NOT EXISTS); no signature
-- change so existing Python callers continue to work unchanged.
-- ============================================================================


-- 1. Add the audit column
ALTER TABLE public.test_attempts
    ADD COLUMN IF NOT EXISTS elo_reduction_factor numeric NULL;

COMMENT ON COLUMN public.test_attempts.elo_reduction_factor IS
    'Volatility reduction factor applied to ELO updates on this attempt. '
    'NULL when no factor was applied (first attempt or off-recommendation repeat). '
    'See migrations/process_test_submission_reduced_repeats.sql.';


-- 2. Rewrite process_test_submission with the retry-slot reduced-ELO path
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
    v_user_volatility numeric;
    -- reduced-volatility repeat additions
    v_is_retry_slot boolean := false;
    v_already_earned_today boolean := false;
    v_last_attempt_at timestamptz;
    v_prev_best numeric;
    v_days_since numeric;
    v_base numeric;
    v_bonus numeric;
    v_factor numeric;
    v_record_factor numeric := NULL;
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
    -- TOKEN COST
    -- ========================================================================
    v_tokens_cost := get_test_token_cost(p_user_id);

    -- ========================================================================
    -- PERCENTAGE
    -- ========================================================================
    v_percentage := (v_score::numeric / v_total_questions::numeric) * 100;
    v_percentage_decimal := v_percentage / 100.0;

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
    -- USER ELO ROW (get-or-create)
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
    -- TEST ELO ROW (get-or-create)
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
        -- Status-quo first-attempt path: full K with user volatility on user side,
        -- K=16 with no volatility on test side. No factor recorded.
        v_new_user_elo := calculate_elo_rating(
            v_user_elo, v_test_elo, v_percentage_decimal, 32, v_user_volatility
        );
        v_new_test_elo := calculate_elo_rating(
            v_test_elo, v_user_elo, 1.0 - v_percentage_decimal, 16, 1.0
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
        -- Repeat attempt: check retry-slot eligibility.
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
            -- Anti-grind: only the first reduced-ELO submission per
            -- (user, test) per day counts; subsequent same-day repeats
            -- fall back to status-quo 0 ELO.
            SELECT EXISTS (
                SELECT 1 FROM test_attempts
                WHERE user_id = p_user_id
                  AND test_id = p_test_id
                  AND elo_reduction_factor IS NOT NULL
                  AND created_at::date = CURRENT_DATE
            ) INTO v_already_earned_today;
        END IF;

        IF v_is_retry_slot AND NOT v_already_earned_today THEN
            -- Time-decay base + improvement bonus
            SELECT MAX(created_at),
                   MAX((score::numeric / NULLIF(total_questions, 0)::numeric) * 100)
            INTO v_last_attempt_at, v_prev_best
            FROM test_attempts
            WHERE user_id = p_user_id
              AND test_id = p_test_id;

            v_days_since := EXTRACT(EPOCH FROM (NOW() - COALESCE(v_last_attempt_at, NOW()))) / 86400.0;
            v_base := LEAST(1.0, GREATEST(0.20, v_days_since / 60.0));

            IF v_prev_best IS NOT NULL AND (v_percentage - v_prev_best) >= 15 THEN
                v_bonus := 0.25;
            ELSE
                v_bonus := 0;
            END IF;

            v_factor := LEAST(1.0, v_base + v_bonus);
            v_record_factor := v_factor;

            v_new_user_elo := calculate_elo_rating(
                v_user_elo, v_test_elo, v_percentage_decimal,
                32, v_user_volatility * v_factor
            );
            v_new_test_elo := calculate_elo_rating(
                v_test_elo, v_user_elo, 1.0 - v_percentage_decimal,
                16, v_factor
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
            -- Off-recommendation repeat or already-earned-today: status quo.
            v_new_user_elo := v_user_elo;
            v_new_test_elo := v_test_elo;
        END IF;
    END IF;

    -- ========================================================================
    -- INSERT ATTEMPT
    -- ========================================================================
    INSERT INTO test_attempts (
        user_id, test_id, test_type_id, language_id, score, total_questions,
        attempt_number, is_first_attempt, user_elo_before, user_elo_after,
        test_elo_before, test_elo_after, tokens_consumed, was_free_test,
        idempotency_key, elo_reduction_factor
    ) VALUES (
        p_user_id, p_test_id, p_test_type_id, p_language_id, v_score,
        v_total_questions, v_attempt_number, v_is_first_attempt,
        v_user_elo, v_new_user_elo, v_test_elo, v_new_test_elo,
        CASE WHEN p_was_free_test THEN 0 ELSE v_tokens_cost END,
        p_was_free_test, p_idempotency_key, v_record_factor
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
        'tokens_cost', CASE WHEN p_was_free_test THEN 0 ELSE v_tokens_cost END,
        'score', v_score,
        'total_questions', v_total_questions,
        'percentage', v_percentage,
        'question_results', v_question_results,
        'message', CASE
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
