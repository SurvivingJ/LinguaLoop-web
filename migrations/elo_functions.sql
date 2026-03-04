-- ELO Calculation Functions for Supabase/PostgreSQL
-- Run this in Supabase SQL Editor

-- 1. Volatility multiplier function
CREATE OR REPLACE FUNCTION calculate_volatility_multiplier(
    attempts INTEGER,
    last_date DATE DEFAULT NULL,
    base_volatility NUMERIC DEFAULT 1.0
)
RETURNS NUMERIC AS $$
DECLARE
    multiplier NUMERIC := base_volatility;
BEGIN
    -- Low attempts = higher volatility
    IF attempts < 10 THEN
        multiplier := multiplier + 0.5;
    END IF;

    -- Long time since last attempt = higher volatility
    IF last_date IS NOT NULL AND (CURRENT_DATE - last_date) > 90 THEN
        multiplier := multiplier + 0.5;
    END IF;

    RETURN multiplier;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- 2. Core ELO calculation function
CREATE OR REPLACE FUNCTION calculate_elo_rating(
    current_rating INTEGER,
    opposing_rating INTEGER,
    actual_score NUMERIC,  -- 0.0 to 1.0
    k_factor INTEGER DEFAULT 32,
    volatility_multiplier NUMERIC DEFAULT 1.0
)
RETURNS INTEGER AS $$
DECLARE
    expected_score NUMERIC;
    adjusted_k NUMERIC;
    new_rating NUMERIC;
BEGIN
    expected_score := 1.0 / (1.0 + POWER(10, (opposing_rating - current_rating) / 400.0));
    adjusted_k := k_factor * volatility_multiplier;
    new_rating := current_rating + (adjusted_k * (actual_score - expected_score));

    -- Clamp between 400 and 3000
    RETURN GREATEST(400, LEAST(3000, ROUND(new_rating)::INTEGER));
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- 3. Main stored procedure for processing test submissions
CREATE OR REPLACE FUNCTION process_test_submission(
    p_user_id UUID,
    p_test_id UUID,
    p_language TEXT,
    p_skill_type TEXT,
    p_score INTEGER,
    p_total_questions INTEGER,
    p_test_mode TEXT,
    p_tokens_consumed INTEGER DEFAULT 0,
    p_was_free_test BOOLEAN DEFAULT TRUE
)
RETURNS JSONB AS $$
DECLARE
    v_user_elo INTEGER;
    v_test_elo INTEGER;
    v_user_tests_taken INTEGER;
    v_user_last_date DATE;
    v_test_attempts INTEGER;
    v_percentage NUMERIC;
    v_user_volatility NUMERIC;
    v_test_volatility NUMERIC;
    v_new_user_elo INTEGER;
    v_new_test_elo INTEGER;
    v_attempt_id UUID;
    v_user_rating_exists BOOLEAN;
    v_test_rating_exists BOOLEAN;
BEGIN
    -- Calculate percentage score (0.0 to 1.0)
    v_percentage := p_score::NUMERIC / p_total_questions::NUMERIC;

    -- Get or create user skill rating
    SELECT elo_rating, tests_taken, last_test_date, TRUE
    INTO v_user_elo, v_user_tests_taken, v_user_last_date, v_user_rating_exists
    FROM user_skill_ratings
    WHERE user_id = p_user_id
      AND language = LOWER(p_language)
      AND skill_type = LOWER(p_skill_type);

    IF NOT FOUND THEN
        v_user_elo := 1200;
        v_user_tests_taken := 0;
        v_user_last_date := NULL;
        v_user_rating_exists := FALSE;
    END IF;

    -- Get or create test skill rating
    SELECT elo_rating, total_attempts, TRUE
    INTO v_test_elo, v_test_attempts, v_test_rating_exists
    FROM test_skill_ratings
    WHERE test_id = p_test_id
      AND skill_type = LOWER(p_skill_type);

    IF NOT FOUND THEN
        v_test_elo := 1400;
        v_test_attempts := 0;
        v_test_rating_exists := FALSE;
    END IF;

    -- Calculate volatility multipliers
    v_user_volatility := calculate_volatility_multiplier(v_user_tests_taken, v_user_last_date, 1.0);
    v_test_volatility := calculate_volatility_multiplier(v_test_attempts, NULL, 1.0);

    -- Calculate new ELO ratings
    -- User: actual_score = percentage (how well they did)
    v_new_user_elo := calculate_elo_rating(v_user_elo, v_test_elo, v_percentage, 32, v_user_volatility);

    -- Test: actual_score = 1 - percentage (inverse - if user does well, test was "easier")
    v_new_test_elo := calculate_elo_rating(v_test_elo, v_user_elo, (1.0 - v_percentage), 16, v_test_volatility);

    -- Upsert user_skill_ratings
    IF v_user_rating_exists THEN
        UPDATE user_skill_ratings
        SET elo_rating = v_new_user_elo,
            tests_taken = tests_taken + 1,
            last_test_date = CURRENT_DATE,
            updated_at = NOW()
        WHERE user_id = p_user_id
          AND language = LOWER(p_language)
          AND skill_type = LOWER(p_skill_type);
    ELSE
        INSERT INTO user_skill_ratings (user_id, language, skill_type, elo_rating, tests_taken, last_test_date)
        VALUES (p_user_id, LOWER(p_language), LOWER(p_skill_type), v_new_user_elo, 1, CURRENT_DATE);
    END IF;

    -- Upsert test_skill_ratings
    IF v_test_rating_exists THEN
        UPDATE test_skill_ratings
        SET elo_rating = v_new_test_elo,
            total_attempts = total_attempts + 1,
            updated_at = NOW()
        WHERE test_id = p_test_id
          AND skill_type = LOWER(p_skill_type);
    ELSE
        INSERT INTO test_skill_ratings (test_id, skill_type, elo_rating, total_attempts)
        VALUES (p_test_id, LOWER(p_skill_type), v_new_test_elo, 1);
    END IF;

    -- Insert test attempt
    INSERT INTO test_attempts (
        user_id, test_id, score, total_questions, test_mode, language,
        user_elo_before, test_elo_before, user_elo_after, test_elo_after,
        was_free_test, tokens_consumed
    ) VALUES (
        p_user_id, p_test_id, p_score, p_total_questions, LOWER(p_test_mode), LOWER(p_language),
        v_user_elo, v_test_elo, v_new_user_elo, v_new_test_elo,
        p_was_free_test, p_tokens_consumed
    )
    RETURNING id INTO v_attempt_id;

    -- Update tests total_attempts
    UPDATE tests
    SET total_attempts = total_attempts + 1, updated_at = NOW()
    WHERE id = p_test_id;

    -- Upsert user_languages
    INSERT INTO user_languages (user_id, language, total_tests_taken, last_test_date)
    VALUES (p_user_id, LOWER(p_language), 1, CURRENT_DATE)
    ON CONFLICT (user_id, language)
    DO UPDATE SET
        total_tests_taken = user_languages.total_tests_taken + 1,
        last_test_date = CURRENT_DATE,
        updated_at = NOW();

    -- Return result
    RETURN jsonb_build_object(
        'success', TRUE,
        'attempt_id', v_attempt_id,
        'user_elo_before', v_user_elo,
        'user_elo_after', v_new_user_elo,
        'user_elo_change', v_new_user_elo - v_user_elo,
        'test_elo_before', v_test_elo,
        'test_elo_after', v_new_test_elo,
        'test_elo_change', v_new_test_elo - v_test_elo,
        'score', p_score,
        'percentage', v_percentage
    );

EXCEPTION WHEN OTHERS THEN
    RETURN jsonb_build_object(
        'success', FALSE,
        'error', SQLERRM
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Add unique constraint on user_languages if not exists
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'user_languages_user_id_language_key'
    ) THEN
        ALTER TABLE user_languages ADD CONSTRAINT user_languages_user_id_language_key UNIQUE (user_id, language);
    END IF;
END $$;

-- Grant execute permission
GRANT EXECUTE ON FUNCTION process_test_submission TO authenticated;
GRANT EXECUTE ON FUNCTION calculate_elo_rating TO authenticated;
GRANT EXECUTE ON FUNCTION calculate_volatility_multiplier TO authenticated;
