-- TASK-702 — get_recommended_tests: raise per-type candidate cap 3 -> 10
-- =============================================================================
-- PROBLEM (F3 shortfall class)
--   get_recommended_tests returned at most the top-3 never-attempted tests PER
--   TYPE (rank_in_type <= 3). Study-plan templates can budget more than 3 slots
--   of a single skill on a heavy weekday (e.g. reading:6). build_daily_session
--   hydrates each budgeted slot from this RPC's rows and simply gets fewer than
--   it asked for once the top-3 are exhausted — the surplus budgeted slots are
--   silently dropped. Three prior production incidents (pinyin, pitch_accent,
--   classifier_drill) were this same "budgeted-but-unhydrated" failure class.
--
-- FIX
--   Raise the cap to 10 (>= the max plausible per-day count of any single
--   slug-based skill a template schedules). This shrinks the frequency of the
--   shortfall by giving build_daily_session a deeper never-attempted pool to
--   draw from before it must fall back to replay slots (get_replay_tests).
--
--   Otherwise byte-identical to the prior canonical definition
--   (add_pitch_accent_to_get_recommended_tests.sql, now archived). The only
--   changed line is `WHERE rank_in_type <= 10`. Idempotent: CREATE OR REPLACE.
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
        WHERE type_code IN ('listening', 'reading', 'dictation', 'pinyin', 'pitch_accent')
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
        WHERE rank_in_type <= 10   -- TASK-702: raised from 3
        ORDER BY c_test_id, c_test_type, c_elo_diff ASC
    )
    SELECT d.c_test_id, d.c_slug, d.c_test_type, d.c_title,
           d.c_difficulty_level, d.c_elo_rating, d.c_elo_diff, d.c_tier
    FROM deduplicated d
    ORDER BY d.c_elo_diff ASC;
END;
$function$;
