-- =============================================================================
-- APPLIED live 2026-08-30, with explicit operator sign-off. See
-- wiki/decisions/ADR-023-topic-recency-session-exclusion.md for the full
-- rationale and the alternatives considered.
-- =============================================================================
--
-- TASK-740 Phase 5b (finding #3, 2026-08-29 review) — per-user topic-recency
-- half of dedup decision Q5. Generation-time dedup (Phase 5a,
-- migrations/task740_phase5_question_passage_dedup.sql) stops near-duplicate
-- passages from being generated; this half stops a learner from being served
-- two different tests on the same topic within a short window, once
-- test_attempts-based exclusion is no longer enough to prevent it (a topic at
-- its Phase-4 fan-out cap, still has a handful of untried tests).
--
-- Redefines public.get_recommended_tests (previously canonical at
-- migrations/archive/task715_get_recommended_tests_tier_cap.sql, now
-- archived per migrations/CLAUDE.md — see migrations/archive/README.md) —
-- adds one new DEFAULT-valued parameter (backward compatible for existing
-- 2-arg callers) and one new NOT EXISTS clause in the all_candidates CTE.
-- Nothing else changes.
-- =============================================================================

CREATE OR REPLACE FUNCTION public.get_recommended_tests(
    p_user_id uuid,
    p_language_id smallint,
    p_topic_recency_days smallint DEFAULT 14
)
 RETURNS TABLE(test_id uuid, slug text, test_type text, title text, difficulty_level integer, elo_rating integer, elo_diff integer, tier text)
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
DECLARE
    v_user_tier_code TEXT;
    v_is_premium BOOLEAN;
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
          -- TASK-740 Phase 5b (PROPOSED): exclude any test whose topic the
          -- user has attempted (in ANY test type) within the recency window
          -- — not just the exact test_id, per ADR-023.
          AND NOT EXISTS (
              SELECT 1 FROM test_attempts ta2
              JOIN tests t2 ON t2.id = ta2.test_id
              WHERE ta2.user_id = p_user_id
                AND t2.topic_id = t.topic_id
                AND ta2.created_at >= now() - (p_topic_recency_days || ' days')::interval
          )
          AND (
              us.type_code <> 'dictation'
              OR t.transcript IS NULL
              OR array_length(string_to_array(trim(t.transcript), ' '), 1)
                 <= public.dictation_max_words(t.difficulty)
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

-- ──────────────────────────────────────────────────────────────
-- Verification
-- ──────────────────────────────────────────────────────────────
-- See tests/sql/test_task740_phase5b_topic_recency.sql for a rollback-only
-- exercise of the new exclusion.
