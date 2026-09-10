-- =============================================================================
-- Pairs with migrations/task748_get_recommended_tests_vocab_aware.sql (ADR-024).
-- =============================================================================
-- TASK-748 — the rollback guarantee and the pool-health guarantee. Runs entirely
-- inside a rollback-only transaction; leaves nothing behind.
--
--   1. PARITY. Loads the pre-TASK-748 live body (archived verbatim as
--      migrations/archive/task748_prev_get_recommended_tests_live_3arg.sql)
--      under the scratch name _grt_pre748, and asserts that with
--      vocab_weight = 0 the live get_recommended_tests returns rows IDENTICAL in
--      content and order, for every user in en, zh and ja.
--   2. POOL HEALTH (M5). With vocab_weight = 1, the per-type candidate count
--      never falls below the old function's, for every (user, language, type).
--
-- Also reports, per language, how many (user, language) orderings the
-- vocabulary term changes and which ability source it ran on.
--
--   psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f tests/sql/test_task748_parity.sql
--
-- The PRE-APPLY proof on 2026-09-10 was this same script with the migration's
-- three CREATE OR REPLACE statements inserted after step 0, so the comparison
-- ran against the old live function and the new one inside one transaction.
-- =============================================================================

BEGIN;

-- 0. The old body under a scratch name (identical to the archive file).
CREATE FUNCTION public._grt_pre748(p_user_id uuid, p_language_id smallint, p_topic_recency_days smallint DEFAULT 14)
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
        WHERE rank_in_type <= 10
        ORDER BY c_test_id, c_test_type, c_elo_diff ASC
    )
    SELECT d.c_test_id, d.c_slug, d.c_test_type, d.c_title,
           d.c_difficulty_level, d.c_elo_rating, d.c_elo_diff, d.c_tier
    FROM deduplicated d
    ORDER BY d.c_elo_diff ASC;
END;
$function$;

CREATE TEMP TABLE _t748_parity (
    lang               smallint,
    user_id            uuid,
    old_json           jsonb,
    old_rows           integer,
    new_rows           integer,
    same_w0            boolean,
    old_self_same      boolean,
    w1_same_order      boolean,
    w1_min_type_delta  integer,
    ability_source     text
) ON COMMIT DROP;

DO $test$
DECLARE
    r       record;
    v_old   jsonb;
    v_old2  jsonb;
    v_new   jsonb;
    v_w1    jsonb;
    v_delta integer;
    v_src   text;
    v_bad   integer;
BEGIN
    -- ---- 1. parity at vocab_weight = 0 -------------------------------------
    UPDATE public.selection_tuning SET value = 0 WHERE key = 'vocab_weight';

    FOR r IN SELECT u.id AS uid, l.lang::smallint AS lang
               FROM public.users u CROSS JOIN (VALUES (1), (2), (3)) AS l(lang)
              ORDER BY 2, 1
    LOOP
        SELECT COALESCE(jsonb_agg(to_jsonb(x) ORDER BY x.ord), '[]'::jsonb) INTO v_old
          FROM public._grt_pre748(r.uid, r.lang, 14::smallint) WITH ORDINALITY
               AS x(test_id, slug, test_type, title, difficulty_level, elo_rating, elo_diff, tier, ord);
        SELECT COALESCE(jsonb_agg(to_jsonb(x) ORDER BY x.ord), '[]'::jsonb) INTO v_old2
          FROM public._grt_pre748(r.uid, r.lang, 14::smallint) WITH ORDINALITY
               AS x(test_id, slug, test_type, title, difficulty_level, elo_rating, elo_diff, tier, ord);
        SELECT COALESCE(jsonb_agg(to_jsonb(x) ORDER BY x.ord), '[]'::jsonb) INTO v_new
          FROM public.get_recommended_tests(r.uid, r.lang, 14::smallint) WITH ORDINALITY
               AS x(test_id, slug, test_type, title, difficulty_level, elo_rating, elo_diff, tier, ord);

        INSERT INTO _t748_parity (lang, user_id, old_json, old_rows, new_rows, same_w0, old_self_same)
        VALUES (r.lang, r.uid, v_old, jsonb_array_length(v_old), jsonb_array_length(v_new),
                v_old = v_new, v_old = v_old2);
    END LOOP;

    -- ---- 2. pool health at vocab_weight = 1 --------------------------------
    UPDATE public.selection_tuning SET value = 1 WHERE key = 'vocab_weight';

    FOR r IN SELECT p.user_id AS uid, p.lang, p.old_json FROM _t748_parity p
    LOOP
        SELECT min(COALESCE(n.cnt, 0) - o.cnt) INTO v_delta
          FROM (SELECT g.test_type, count(*) AS cnt
                  FROM public._grt_pre748(r.uid, r.lang, 14::smallint) g GROUP BY 1) o
          LEFT JOIN (SELECT g.test_type, count(*) AS cnt
                       FROM public.get_recommended_tests(r.uid, r.lang, 14::smallint) g GROUP BY 1) n
                 USING (test_type);

        SELECT COALESCE(jsonb_agg(to_jsonb(x) ORDER BY x.ord), '[]'::jsonb) INTO v_w1
          FROM public.get_recommended_tests(r.uid, r.lang, 14::smallint) WITH ORDINALITY
               AS x(test_id, slug, test_type, title, difficulty_level, elo_rating, elo_diff, tier, ord);

        SELECT a.ability_source INTO v_src
          FROM public.selection_vocab_ability(r.uid, r.lang) a;

        UPDATE _t748_parity
           SET w1_min_type_delta = v_delta,
               w1_same_order     = (v_w1 = r.old_json),
               ability_source    = v_src
         WHERE user_id = r.uid AND lang = r.lang;
    END LOOP;

    UPDATE public.selection_tuning SET value = 0 WHERE key = 'vocab_weight';

    -- ---- assertions ---------------------------------------------------------
    SELECT count(*) INTO v_bad FROM _t748_parity WHERE NOT same_w0;
    IF v_bad > 0 THEN
        RAISE EXCEPTION 'FAIL parity: % (user, language) pairs differ at vocab_weight = 0', v_bad;
    END IF;

    SELECT count(*) INTO v_bad FROM _t748_parity WHERE w1_min_type_delta < 0;
    IF v_bad > 0 THEN
        RAISE EXCEPTION 'FAIL pool health: a per-type count fell at vocab_weight = 1 for % pairs', v_bad;
    END IF;

    SELECT count(*) INTO v_bad
      FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
     WHERE n.nspname = 'public' AND p.proname = 'get_recommended_tests';
    IF v_bad <> 1 THEN
        RAISE EXCEPTION 'FAIL: % get_recommended_tests overloads (want exactly 1)', v_bad;
    END IF;

    RAISE NOTICE 'TASK-748 PASS: parity at w=0 on every pair; no per-type count fell at w=1';
END $test$;

SELECT lang,
       count(*)                                   AS pairs,
       sum(old_rows)                              AS old_rows,
       sum(new_rows)                              AS new_rows_w0,
       count(*) FILTER (WHERE same_w0)            AS identical_at_w0,
       count(*) FILTER (WHERE old_self_same)      AS old_self_consistent,
       min(w1_min_type_delta)                     AS min_type_count_delta_w1,
       count(*) FILTER (WHERE NOT w1_same_order)  AS reordered_at_w1,
       string_agg(DISTINCT ability_source, ',')   AS ability_sources
  FROM _t748_parity
 GROUP BY lang
 ORDER BY lang;

ROLLBACK;
