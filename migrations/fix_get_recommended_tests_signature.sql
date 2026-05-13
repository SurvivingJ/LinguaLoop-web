-- migrations/fix_get_recommended_tests_signature.sql
-- Closes the RPC parameter-convention gap surfaced in the 2026-05-12 wiki audit.
-- get_recommended_tests was the lone outlier accepting p_language text (code
-- or name), resolved internally via a case-insensitive lookup against
-- dim_languages. Every other RPC in the project takes p_language_id smallint
-- directly. Both callers already have language_id in hand and were doing an
-- LANGUAGE_ID_TO_NAME reverse-lookup just to feed this RPC, which the
-- function then re-resolved back to an id — a round-trip for nothing.
--
-- This migration drops the old function (CREATE OR REPLACE cannot change a
-- parameter type) and recreates it with p_language_id smallint. The body is
-- the same as the previous implementation except the dim_languages lookup
-- block is removed and p_language_id is used directly.
--
-- Callers updated in the same change set: routes/tests.py and
-- services/test_service.py — both now pass language_id (smallint) directly.

DROP FUNCTION IF EXISTS public.get_recommended_tests(uuid, text);

CREATE OR REPLACE FUNCTION public.get_recommended_tests(
  p_user_id     uuid,
  p_language_id smallint
)
RETURNS TABLE(
  test_id          uuid,
  slug             text,
  test_type        text,
  title            text,
  difficulty_level integer,
  elo_rating       integer,
  elo_diff         integer,
  tier             text
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path TO 'public'
AS $function$
DECLARE
  v_user_tier_code TEXT;
  v_is_premium     BOOLEAN;
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
    WHERE type_code IN ('listening', 'reading', 'dictation')
  ),
  user_stats AS (
    SELECT
      tt.type_id,
      tt.type_code,
      COALESCE(usr.elo_rating, 1200) as current_elo
    FROM target_types tt
    LEFT JOIN user_skill_ratings usr
      ON usr.user_id = p_user_id
      AND usr.language_id = p_language_id
      AND usr.test_type_id = tt.type_id
  ),
  all_candidates AS (
    SELECT
      t.id AS c_test_id,
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
        SELECT 1
        FROM test_attempts ta
        WHERE ta.user_id = p_user_id
          AND ta.test_id = t.id
      )
  ),
  deduplicated AS (
    SELECT DISTINCT ON (c_test_id)
      c_test_id, c_slug, c_test_type, c_title,
      c_difficulty_level, c_elo_rating, c_elo_diff, c_tier
    FROM all_candidates
    WHERE rank_in_type <= 3
    ORDER BY c_test_id, c_elo_diff ASC
  )
  SELECT
    d.c_test_id, d.c_slug, d.c_test_type, d.c_title,
    d.c_difficulty_level, d.c_elo_rating, d.c_elo_diff, d.c_tier
  FROM deduplicated d
  ORDER BY d.c_elo_diff ASC;
END;
$function$;

GRANT EXECUTE ON FUNCTION public.get_recommended_tests(uuid, smallint)
  TO authenticated, service_role;

-- ===========================================================================
-- Verification queries
-- ===========================================================================
-- 1) Confirm new signature exists and old one is gone:
--    \df public.get_recommended_tests
--    Expected exactly one row: get_recommended_tests(p_user_id uuid, p_language_id smallint)
--
-- 2) Smoke-call (replace with a real user UUID + language id):
--    SELECT * FROM public.get_recommended_tests('<user-uuid>'::uuid, 1::smallint);
