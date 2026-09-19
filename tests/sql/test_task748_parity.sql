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
-- TASK-780 appended steps 3 (sum-mode parity against a frozen copy of the
-- pre-780 ranker) and 4 (product mode is inert at vocab_weight = 0 and never
-- shrinks a pool). They are below, after step 2; nothing above them changed.
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
-- =============================================================================
-- TASK-780 — steps 3 and 4. Added when combine_mode shipped; everything above
-- is the TASK-748 proof, unchanged.
-- =============================================================================
-- 3. SUM-MODE PARITY. The pre-TASK-780 ranker body, verbatim, under the scratch
--    name _rtr_pre780 (generated from migrations/task748_get_recommended_tests_
--    vocab_aware.sql — the ONLY edit is the function name). With combine_mode =
--    'sum' the live ranker must return rows identical in content and order, for
--    every user in en/zh/ja, at p_vocab_weight 0 AND 1. This is what "sum mode
--    is byte-identical to TASK-748" means, proven rather than read off the diff.
-- 4. PRODUCT MODE IS SAFE. With combine_mode = 'product': the public RPC is
--    still unchanged at vocab_weight = 0 (it never reaches the ranker), and at
--    weight 1 no per-type candidate count falls (M5).
--
-- REVERT-RED: put the product expression in the ELSE branch of the `scored` CTE
-- — i.e. make product the behaviour of sum — and step 3 fails on every pair.
--
-- `product_output_differs_w1` in the report is a LIVENESS check, not a measure
-- of reordering: (1+e)(1+v) differs from e+v in value for every candidate, so it
-- is 1 whenever the product branch runs at all. How often the two arms actually
-- serve a different top-10 is TASK-781's question, not this test's.
-- =============================================================================

CREATE FUNCTION public._rtr_pre780(
    p_user_id            uuid,
    p_language_id        smallint,
    p_topic_recency_days smallint,
    p_vocab_weight       numeric,
    p_as_of              timestamptz DEFAULT NULL)
RETURNS TABLE(
    test_id          uuid,
    slug             text,
    test_type        text,
    title            text,
    difficulty_level integer,
    elo_rating       integer,
    elo_diff         integer,
    tier             text,
    rank_in_type     bigint,
    score            numeric,
    unknown_share    numeric,
    vocab_penalty    numeric,
    vocab_neutral    boolean,
    over_ceiling     boolean,
    n_senses         integer,
    n_resolved       integer,
    ability_zipf     numeric,
    ability_source   text)
LANGUAGE plpgsql
STABLE
SECURITY DEFINER
SET search_path TO 'public'
AS $function$
DECLARE
    v_user_tier_code text;
    v_is_premium     boolean;
    v_as_of          timestamptz := COALESCE(p_as_of, now());
    v_w_elo          numeric;
    v_u_star         numeric;
    v_u_tol          numeric;
    v_ceiling        integer;
    v_ability        numeric;
    v_source         text;
    v_learner_tier   integer;
BEGIN
    SELECT st.tier_code INTO v_user_tier_code
      FROM users u
      JOIN dim_subscription_tiers st ON u.subscription_tier_id = st.id
     WHERE u.id = p_user_id;
    v_is_premium := (v_user_tier_code NOT ILIKE '%free%');

    SELECT COALESCE(max(s.value) FILTER (WHERE s.key = 'elo_weight'),          1.0),
           COALESCE(max(s.value) FILTER (WHERE s.key = 'unknown_target'),      0.15),
           COALESCE(max(s.value) FILTER (WHERE s.key = 'unknown_tolerance'),   0.10),
           COALESCE(max(s.value) FILTER (WHERE s.key = 'tier_ceiling_offset'), 2)::integer
      INTO v_w_elo, v_u_star, v_u_tol, v_ceiling
      FROM selection_tuning s;

    SELECT a.ability_zipf, a.ability_source INTO v_ability, v_source
      FROM selection_vocab_ability(p_user_id, p_language_id, p_as_of) a;

    -- §4 safety rail: only with a calibration row, and only in the vocabulary
    -- arm. The learner's tier is the highest whose initial_elo their calibrated
    -- ELO reaches.
    IF v_source = 'calibration' AND p_vocab_weight > 0 THEN
        SELECT COALESCE(max(ct.id), 1) INTO v_learner_tier
          FROM dim_complexity_tiers ct
         WHERE ct.initial_elo <= calibration_zipf_to_elo(v_ability);
    END IF;

    RETURN QUERY
    WITH target_types AS (
        SELECT dtt.id AS type_id, dtt.type_code
          FROM dim_test_types dtt
         WHERE dtt.type_code IN ('listening', 'reading', 'dictation', 'pinyin', 'pitch_accent')
           AND dtt.is_active = true
    ),
    user_stats AS (
        SELECT tt.type_id,
               tt.type_code,
               CASE WHEN p_as_of IS NULL THEN COALESCE(usr.elo_rating, 1200)
                    ELSE COALESCE((
                        SELECT ta.user_elo_after
                          FROM test_attempts ta
                         WHERE ta.user_id = p_user_id
                           AND ta.language_id = p_language_id
                           AND ta.test_type_id = tt.type_id
                           AND ta.created_at < p_as_of
                         ORDER BY ta.created_at DESC
                         LIMIT 1), 1200)
               END AS current_elo
          FROM target_types tt
          LEFT JOIN user_skill_ratings usr
                 ON usr.user_id = p_user_id
                AND usr.language_id = p_language_id
                AND usr.test_type_id = tt.type_id
    ),
    -- The learner's uvk rows, read ONCE (§3.6), keyed by sense.
    user_uvk AS MATERIALIZED (
        SELECT k.sense_id AS u_sense_id, k.p_known::float8 AS u_p_known
          FROM user_vocabulary_knowledge k
         WHERE k.user_id = p_user_id
           AND (p_as_of IS NULL OR k.created_at < p_as_of)
    ),
    test_vocab AS (
        SELECT t.id AS tv_test_id,
               count(*)::integer                AS tv_n_s,
               count(v.frequency_rank)::integer AS tv_n_sp,
               avg(CASE
                       WHEN v.frequency_rank IS NULL THEN NULL          -- out of S'
                       WHEN u.u_p_known IS NOT NULL THEN u.u_p_known    -- evidence wins
                       ELSE 1.0 / (1.0 + exp(-(1.5 * (v.frequency_rank::float8 - v_ability::float8)
                                               + ln(0.85 / 0.15))))     -- 0.85 at ability_zipf
                   END) AS tv_known_share
          FROM tests t
         CROSS JOIN LATERAL (
               SELECT DISTINCT x AS sid FROM unnest(t.vocab_sense_ids) x WHERE x IS NOT NULL
         ) s
          LEFT JOIN dim_word_senses ws ON ws.id = s.sid
          LEFT JOIN dim_vocabulary v   ON v.id = ws.vocab_id
          LEFT JOIN user_uvk u         ON u.u_sense_id = s.sid
         WHERE t.language_id = p_language_id
           AND t.is_active = true
         GROUP BY t.id
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
               tv.tv_n_s AS c_n_s,
               tv.tv_n_sp AS c_n_sp,
               tv.tv_known_share AS c_known_share,
               (v_ability IS NULL
                OR tv.tv_test_id IS NULL
                OR tv.tv_n_sp < 5
                OR tv.tv_n_sp::numeric / tv.tv_n_s < 0.5) AS c_neutral,
               (v_learner_tier IS NOT NULL
                AND ct.id IS NOT NULL
                AND ct.id > v_learner_tier + v_ceiling) AS c_over_ceiling
          FROM user_stats us
          JOIN test_skill_ratings tsr ON tsr.test_type_id = us.type_id
          JOIN tests t ON t.id = tsr.test_id
          LEFT JOIN test_vocab tv ON tv.tv_test_id = t.id
          LEFT JOIN dim_complexity_tiers ct
                 ON t.difficulty BETWEEN ct.difficulty_min AND ct.difficulty_max
         WHERE t.language_id = p_language_id
           AND t.is_active = true
           AND (p_as_of IS NULL OR t.created_at <= p_as_of)
           AND (
               t.tier = 'free-tier'
               OR (t.tier != 'free-tier' AND v_is_premium)
           )
           AND NOT EXISTS (
               SELECT 1 FROM test_attempts ta
                WHERE ta.user_id = p_user_id
                  AND ta.test_id = t.id
                  AND ta.test_type_id = us.type_id
                  AND (p_as_of IS NULL OR ta.created_at < p_as_of)
           )
           AND NOT EXISTS (
               SELECT 1 FROM test_attempts ta2
                 JOIN tests t2 ON t2.id = ta2.test_id
                WHERE ta2.user_id = p_user_id
                  AND t2.topic_id = t.topic_id
                  AND ta2.created_at >= v_as_of - (p_topic_recency_days || ' days')::interval
                  AND (p_as_of IS NULL OR ta2.created_at < p_as_of)
           )
           AND (
               us.type_code <> 'dictation'
               OR t.transcript IS NULL
               OR array_length(string_to_array(trim(t.transcript), ' '), 1)
                  <= public.dictation_max_words(t.difficulty)
           )
    ),
    penalised AS (
        SELECT ac.*,
               CASE WHEN ac.c_neutral THEN NULL
                    ELSE abs((1 - ac.c_known_share::numeric) - v_u_star) / v_u_tol
               END AS c_raw_penalty
          FROM all_candidates ac
    ),
    cohort AS (
        -- "No opinion" = the median penalty of this (user, type) candidate set.
        SELECT p.c_test_type AS co_type,
               percentile_cont(0.5) WITHIN GROUP (ORDER BY p.c_raw_penalty)::numeric AS co_median
          FROM penalised p
         WHERE p.c_raw_penalty IS NOT NULL
         GROUP BY p.c_test_type
    ),
    scored AS (
        SELECT p.*,
               COALESCE(p.c_raw_penalty, co.co_median, 0) AS c_penalty,
               v_w_elo * p.c_elo_diff / 400.0
                 + p_vocab_weight * COALESCE(p.c_raw_penalty, co.co_median, 0) AS c_score
          FROM penalised p
          LEFT JOIN cohort co ON co.co_type = p.c_test_type
    ),
    ranked AS (
        SELECT s.*,
               ROW_NUMBER() OVER (
                   PARTITION BY s.c_test_type
                   ORDER BY s.c_over_ceiling, s.c_score, s.c_elo_diff, s.c_test_id
               ) AS c_rank
          FROM scored s
    ),
    deduplicated AS (
        SELECT DISTINCT ON (r.c_test_id, r.c_test_type) r.*
          FROM ranked r
         ORDER BY r.c_test_id, r.c_test_type, r.c_rank
    )
    SELECT d.c_test_id, d.c_slug, d.c_test_type, d.c_title,
           d.c_difficulty_level, d.c_elo_rating, d.c_elo_diff, d.c_tier,
           d.c_rank,
           round(d.c_score, 6),
           round((1 - d.c_known_share)::numeric, 4),
           round(d.c_penalty, 6),
           d.c_neutral,
           d.c_over_ceiling,
           d.c_n_s,
           d.c_n_sp,
           v_ability,
           v_source
      FROM deduplicated d
     ORDER BY d.c_test_type, d.c_rank;
END;
$function$;

CREATE TEMP TABLE _t780_parity (
    lang                smallint,
    user_id             uuid,
    rows_w0             integer,
    rows_w1             integer,
    sum_same_w0         boolean,
    sum_same_w1         boolean,
    prod_out_differs_w1 boolean,   -- liveness only: the score ALWAYS differs
    prod_rpc_same_w0    boolean,
    prod_min_type_delta integer
) ON COMMIT DROP;

DO $test$
DECLARE
    -- md5 of the live recommended_tests_ranked body, read from pg_proc on
    -- 2026-09-16 immediately BEFORE the TASK-780 migration was applied. The
    -- frozen copy above must still hash to it, or it is not the old function
    -- and step 3 proves nothing.
    c_pre780_md5 constant text := '7b44009489ed1628ba70b8b9e5ed03ad';
    v_md5     text;
    r         record;
    v_old0    jsonb;
    v_new0    jsonb;
    v_old1    jsonb;
    v_new1    jsonb;
    v_prod1   jsonb;
    v_rpc_s   jsonb;
    v_rpc_p   jsonb;
    v_delta   integer;
    v_bad     integer;
BEGIN
    SELECT md5(p.prosrc) INTO v_md5
      FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
     WHERE n.nspname = 'public' AND p.proname = '_rtr_pre780';
    IF v_md5 IS DISTINCT FROM c_pre780_md5 THEN
        RAISE EXCEPTION 'FAIL: _rtr_pre780 hashes to %, not the pre-TASK-780 body %. Re-copy it verbatim from migrations/task748_get_recommended_tests_vocab_aware.sql (only the function name may differ).', v_md5, c_pre780_md5;
    END IF;

    UPDATE public.selection_tuning SET value = 0     WHERE key = 'vocab_weight';
    UPDATE public.selection_tuning SET value_text = 'sum' WHERE key = 'combine_mode';

    FOR r IN SELECT u.id AS uid, l.lang::smallint AS lang
               FROM public.users u CROSS JOIN (VALUES (1), (2), (3)) AS l(lang)
              ORDER BY 2, 1
    LOOP
        -- Canonical order: (test_type, rank_in_type) is a total order per call,
        -- so any reordering shows up as a changed rank, i.e. changed jsonb.
        SELECT COALESCE(jsonb_agg(to_jsonb(x) ORDER BY x.test_type, x.rank_in_type), '[]'::jsonb)
          INTO v_old0 FROM public._rtr_pre780(r.uid, r.lang, 14::smallint, 0, NULL) x;
        SELECT COALESCE(jsonb_agg(to_jsonb(x) ORDER BY x.test_type, x.rank_in_type), '[]'::jsonb)
          INTO v_new0 FROM public.recommended_tests_ranked(r.uid, r.lang, 14::smallint, 0, NULL) x;
        SELECT COALESCE(jsonb_agg(to_jsonb(x) ORDER BY x.test_type, x.rank_in_type), '[]'::jsonb)
          INTO v_old1 FROM public._rtr_pre780(r.uid, r.lang, 14::smallint, 1, NULL) x;
        SELECT COALESCE(jsonb_agg(to_jsonb(x) ORDER BY x.test_type, x.rank_in_type), '[]'::jsonb)
          INTO v_new1 FROM public.recommended_tests_ranked(r.uid, r.lang, 14::smallint, 1, NULL) x;

        UPDATE public.selection_tuning SET value_text = 'product' WHERE key = 'combine_mode';

        SELECT COALESCE(jsonb_agg(to_jsonb(x) ORDER BY x.test_type, x.rank_in_type), '[]'::jsonb)
          INTO v_prod1 FROM public.recommended_tests_ranked(r.uid, r.lang, 14::smallint, 1, NULL) x;

        SELECT min(COALESCE(n.cnt, 0) - o.cnt) INTO v_delta
          FROM (SELECT g.test_type, count(*) AS cnt
                  FROM public._rtr_pre780(r.uid, r.lang, 14::smallint, 1, NULL) g GROUP BY 1) o
          LEFT JOIN (SELECT g.test_type, count(*) AS cnt
                       FROM public.recommended_tests_ranked(r.uid, r.lang, 14::smallint, 1, NULL) g
                      GROUP BY 1) n
                 USING (test_type);

        -- vocab_weight is still 0: the RPC must take the verbatim pre-748 branch
        -- whatever combine_mode says.
        SELECT COALESCE(jsonb_agg(to_jsonb(x) ORDER BY x.ord), '[]'::jsonb) INTO v_rpc_p
          FROM public.get_recommended_tests(r.uid, r.lang, 14::smallint) WITH ORDINALITY
               AS x(test_id, slug, test_type, title, difficulty_level, elo_rating, elo_diff, tier, ord);

        UPDATE public.selection_tuning SET value_text = 'sum' WHERE key = 'combine_mode';

        SELECT COALESCE(jsonb_agg(to_jsonb(x) ORDER BY x.ord), '[]'::jsonb) INTO v_rpc_s
          FROM public.get_recommended_tests(r.uid, r.lang, 14::smallint) WITH ORDINALITY
               AS x(test_id, slug, test_type, title, difficulty_level, elo_rating, elo_diff, tier, ord);

        INSERT INTO _t780_parity VALUES (
            r.lang, r.uid,
            jsonb_array_length(v_new0), jsonb_array_length(v_new1),
            v_old0 = v_new0, v_old1 = v_new1,
            v_prod1 IS DISTINCT FROM v_new1,   -- see the column comment
            v_rpc_p = v_rpc_s,
            v_delta);
    END LOOP;

    UPDATE public.selection_tuning SET value = 0 WHERE key = 'vocab_weight';

    SELECT count(*) INTO v_bad FROM _t780_parity WHERE NOT sum_same_w0 OR NOT sum_same_w1;
    IF v_bad > 0 THEN
        RAISE EXCEPTION 'FAIL TASK-780 sum parity: % (user, language) pairs differ from the pre-780 ranker at combine_mode = sum', v_bad;
    END IF;

    SELECT count(*) INTO v_bad FROM _t780_parity WHERE NOT prod_rpc_same_w0;
    IF v_bad > 0 THEN
        RAISE EXCEPTION 'FAIL: combine_mode changed the public RPC at vocab_weight = 0 on % pairs; the rollback branch must be unreachable from the mode', v_bad;
    END IF;

    SELECT count(*) INTO v_bad FROM _t780_parity WHERE prod_min_type_delta < 0;
    IF v_bad > 0 THEN
        RAISE EXCEPTION 'FAIL M5 in product mode: a per-type count fell on % pairs', v_bad;
    END IF;

    RAISE NOTICE 'TASK-780 PASS: sum mode identical to the pre-780 ranker at weights 0 and 1; product mode inert at vocab_weight = 0; no per-type count fell';
END $test$;

SELECT lang,
       count(*)                                            AS pairs,
       sum(rows_w1)                                        AS ranker_rows_w1,
       count(*) FILTER (WHERE sum_same_w0)                 AS sum_identical_w0,
       count(*) FILTER (WHERE sum_same_w1)                 AS sum_identical_w1,
       count(*) FILTER (WHERE prod_out_differs_w1)         AS product_output_differs_w1,
       count(*) FILTER (WHERE prod_rpc_same_w0)            AS rpc_inert_under_product,
       min(prod_min_type_delta)                            AS min_type_count_delta_product
  FROM _t780_parity
 GROUP BY lang
 ORDER BY lang;

ROLLBACK;
