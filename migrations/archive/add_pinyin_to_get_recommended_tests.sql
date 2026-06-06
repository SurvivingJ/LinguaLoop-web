-- get_recommended_tests: include pinyin in the recommendable test types
-- =============================================================================
-- PROBLEM (same class as phase13_build_daily_session_classifier_drill.sql)
--   Chinese study-plan templates schedule pinyin (target_counts."pinyin": 1-2),
--   and build_daily_session budgets the slot, but it hydrates concrete test rows
--   via get_recommended_tests, whose target_types CTE was hardcoded to
--   ('listening','reading','dictation'). pinyin returned ZERO rows, so the
--   budgeted pinyin slot was silently dropped before reaching
--   daily_test_loads.test_ids — players/pinyin.js could never mount from a
--   study-plan load, and the weekly pinyin target was unsatisfiable via /session.
--
-- FIX
--   Unlike classifier_drill (an infinite trainer backed by a sentinel test row),
--   pinyin is a genuine slug-based test type (id 11) with real ELO-rated test
--   rows (test_skill_ratings.test_type_id = 11; 93 active Chinese tests). So the
--   correct fix is to let get_recommended_tests recommend it like any other
--   skill: add 'pinyin' to target_types. It then flows through the normal path
--   (ELO match, tier gate, per-type already-attempted exclusion) and is hydrated
--   by build_daily_session's existing get_recommended_tests loop — no resolver
--   change needed. The dictation-only transcript word-count filter does not apply
--   to pinyin (us.type_code <> 'dictation' short-circuits true).
--
--   This also makes pinyin appear in GET /api/tests/recommended (routes/tests.py),
--   which passes the rows straight through — a desirable surfacing, not a break.
--
--   pitch_accent (Japanese, id 13) has the identical latent gap but is out of
--   scope here; add it the same way when needed.
--
-- Otherwise byte-identical to the live definition; only the target_types IN list
-- changed. Idempotent: CREATE OR REPLACE.
-- =============================================================================

CREATE OR REPLACE FUNCTION public.get_recommended_tests(p_user_id uuid, p_language_id smallint)
 RETURNS TABLE(test_id uuid, slug text, test_type text, title text, difficulty_level integer, elo_rating integer, elo_diff integer, tier text)
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
DECLARE
    v_user_tier_code TEXT;
    v_is_premium BOOLEAN;
    v_dictation_max_words CONSTANT integer := 80;
BEGIN
    SELECT st.tier_code INTO v_user_tier_code
    FROM users u
    JOIN dim_subscription_tiers st ON u.subscription_tier_id = st.id
    WHERE u.id = p_user_id;

    v_is_premium := (v_user_tier_code NOT ILIKE '%free%');

    RETURN QUERY
    WITH target_types AS (
        SELECT id AS type_id, type_code
        FROM dim_test_types
        WHERE type_code IN ('listening', 'reading', 'dictation', 'pinyin')
          AND is_active = true
    ),
    user_stats AS (
        SELECT tt.type_id,
               tt.type_code,
               COALESCE(usr.elo_rating, 1200) AS current_elo
        FROM target_types tt
        LEFT JOIN user_skill_ratings usr
               ON usr.user_id = p_user_id
              AND usr.language_id = p_language_id
              AND usr.test_type_id = tt.type_id
    ),
    all_candidates AS (
        SELECT t.id AS c_test_id,
               t.slug::text AS c_slug,
               us.type_code::text AS c_test_type,
               t.title::text AS c_title,
               t.difficulty AS c_difficulty_level,
               tsr.elo_rating AS c_elo_rating,
               ABS(tsr.elo_rating - us.current_elo) AS c_elo_diff,
               t.tier::text AS c_tier,
               ROW_NUMBER() OVER (
                   PARTITION BY us.type_code
                   ORDER BY ABS(tsr.elo_rating - us.current_elo) ASC
               ) AS rank_in_type
        FROM user_stats us
        JOIN test_skill_ratings tsr ON tsr.test_type_id = us.type_id
        JOIN tests t ON t.id = tsr.test_id
        WHERE t.language_id = p_language_id
          AND t.is_active = true
          AND (
              t.tier = 'free-tier'
              OR (t.tier != 'free-tier' AND v_is_premium)
          )
          AND NOT EXISTS (
              SELECT 1 FROM test_attempts ta
              WHERE ta.user_id = p_user_id
                AND ta.test_id = t.id
                AND ta.test_type_id = us.type_id
          )
          AND (
              us.type_code <> 'dictation'
              OR t.transcript IS NULL
              OR array_length(string_to_array(trim(t.transcript), ' '), 1) <= v_dictation_max_words
          )
    ),
    deduplicated AS (
        SELECT DISTINCT ON (c_test_id, c_test_type)
               c_test_id, c_slug, c_test_type, c_title,
               c_difficulty_level, c_elo_rating, c_elo_diff, c_tier
        FROM all_candidates
        WHERE rank_in_type <= 3
        ORDER BY c_test_id, c_test_type, c_elo_diff ASC
    )
    SELECT d.c_test_id, d.c_slug, d.c_test_type, d.c_title,
           d.c_difficulty_level, d.c_elo_rating, d.c_elo_diff, d.c_tier
    FROM deduplicated d
    ORDER BY d.c_elo_diff ASC;
END;
$function$;
