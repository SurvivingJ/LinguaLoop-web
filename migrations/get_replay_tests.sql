-- get_replay_tests — nearest-ELO previously-attempted tests for slot backfill
-- =============================================================================
-- PURPOSE (TASK-702; shared with TASK-704 retry slots)
--   When build_daily_session budgets more slug-based test slots for a skill than
--   the never-attempted pool (get_recommended_tests) can hydrate, the surplus
--   slots would be silently dropped. This helper supplies the exhausted-pool
--   fallback: the nearest-ELO tests the user HAS attempted, but not within the
--   last p_min_age_days, so a budgeted slot lands as a 'replay' rather than
--   vanishing. It is the inverse of get_recommended_tests (attempted instead of
--   never-attempted) with an age floor and an explicit exclusion set.
--
--   The technical note on TASK-702 requires the replay fallback and TASK-704's
--   retry slots to share selection code — hence a standalone SRF rather than an
--   inline query in build_daily_session.
--
-- ELO / damping
--   Rows are ordered by |test_elo - user_elo| (nearest first), tie-broken by the
--   oldest last-attempt. Callers stamp slot_type='replay' (or 'retry'); ADR-006
--   reduced-volatility ELO is applied downstream at submission time by whatever
--   scans the daily load's slot_type — this helper only selects candidates.
--
--   Premium gating mirrors get_recommended_tests: free-tier tests are always
--   eligible; non-free tests only for premium users.
--
-- Idempotent: CREATE OR REPLACE. New object (no prior definition).
-- =============================================================================

CREATE OR REPLACE FUNCTION public.get_replay_tests(
    p_user_id      uuid,
    p_language_id  smallint,
    p_test_type    text,
    p_min_age_days integer DEFAULT 7,
    p_exclude      uuid[]  DEFAULT '{}'::uuid[],
    p_limit        integer DEFAULT 10
)
 RETURNS TABLE(test_id uuid, test_type text, elo_rating integer, elo_diff integer, last_attempt_at timestamptz)
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
DECLARE
    v_type_id     int;
    v_user_elo    int;
    v_tier_code   text;
    v_is_premium  boolean;
BEGIN
    SELECT id INTO v_type_id
    FROM dim_test_types
    WHERE type_code = p_test_type AND is_active = true;

    IF v_type_id IS NULL THEN
        RETURN;   -- unknown / inactive skill -> no replay candidates
    END IF;

    SELECT st.tier_code INTO v_tier_code
    FROM users u
    JOIN dim_subscription_tiers st ON u.subscription_tier_id = st.id
    WHERE u.id = p_user_id;
    v_is_premium := (v_tier_code NOT ILIKE '%free%');

    SELECT COALESCE(usr.elo_rating, 1200) INTO v_user_elo
    FROM user_skill_ratings usr
    WHERE usr.user_id = p_user_id
      AND usr.language_id = p_language_id
      AND usr.test_type_id = v_type_id;
    v_user_elo := COALESCE(v_user_elo, 1200);

    RETURN QUERY
    SELECT t.id,
           p_test_type,
           tsr.elo_rating,
           ABS(tsr.elo_rating - v_user_elo)::int AS c_elo_diff,
           la.last_at
    FROM tests t
    JOIN test_skill_ratings tsr
      ON tsr.test_id = t.id
     AND tsr.test_type_id = v_type_id
    JOIN LATERAL (
        SELECT MAX(ta.created_at) AS last_at
        FROM test_attempts ta
        WHERE ta.user_id = p_user_id
          AND ta.test_id = t.id
          AND ta.test_type_id = v_type_id
    ) la ON la.last_at IS NOT NULL                     -- previously attempted
    WHERE t.language_id = p_language_id
      AND t.is_active = true
      AND (
          t.tier = 'free-tier'
          OR (t.tier != 'free-tier' AND v_is_premium)
      )
      AND la.last_at < (CURRENT_DATE - p_min_age_days)::timestamptz   -- age floor
      AND NOT (t.id = ANY(p_exclude))
    ORDER BY ABS(tsr.elo_rating - v_user_elo) ASC, la.last_at ASC
    LIMIT GREATEST(0, p_limit);
END;
$function$;
