-- ============================================================================
-- dictation_cap_cjk_word_count.sql — count Chinese/Japanese transcript words
-- Date: 2026-11-11
--
-- The dictation length cap (dictation_max_words, TASK-715) was checked in
-- get_recommended_tests and recommended_tests_ranked as
--     array_length(string_to_array(trim(t.transcript), ' '), 1)
-- Chinese and Japanese transcripts have no spaces, so every one counted as
-- ~1 word and passed the cap: a 983-character Chinese passage (638 words by
-- the dictation grader) was served as a daily dictation.
--
-- transcript_word_count(text): the space count for spaced scripts; for text
-- containing kana or CJK ideographs, non-space non-punctuation characters /
-- 1.5 (rounded up) — the grader's own ratio on live zh content (983 chars ->
-- 638 words).
--
-- Canonical definitions. The two selection functions below are the previous
-- canonical bodies (get_recommended_tests from
-- task748_get_recommended_tests_vocab_aware.sql, recommended_tests_ranked from
-- task780_selection_combine_mode.sql) with only that expression replaced.
-- Applied live 2026-11-11 by an in-place rewrite of the live definitions;
-- verified afterwards that md5(prosrc) of each live function equals the body
-- written here (get_recommended_tests 1e11065394da7807f3b97e919165a42f,
-- recommended_tests_ranked 1f0dddf9f7d0472708cf48ffd0ffb15b).
-- ============================================================================

BEGIN;

CREATE OR REPLACE FUNCTION public.transcript_word_count(p_text text)
RETURNS integer
LANGUAGE sql
IMMUTABLE
SET search_path = public, pg_temp
AS $$
    SELECT CASE
        WHEN p_text IS NULL THEN NULL
        WHEN p_text ~ '[\u3040-\u30ff\u3400-\u9fff]' THEN
            ceil(char_length(regexp_replace(
                p_text, '[[:space:][:punct:]、。，！？；：「」『』（）“”‘’《》…—・]', '', 'g'
            )) / 1.5)::integer
        ELSE array_length(string_to_array(trim(p_text), ' '), 1)
    END
$$;

REVOKE ALL ON FUNCTION public.transcript_word_count(text) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.transcript_word_count(text) TO service_role;

COMMENT ON FUNCTION public.transcript_word_count(text) IS
    'Transcript length in words for the dictation cap: space-split for spaced scripts; '
    'kana/CJK text counts non-space non-punctuation characters / 1.5. '
    'See migrations/dictation_cap_cjk_word_count.sql.';

CREATE OR REPLACE FUNCTION public.get_recommended_tests(p_user_id uuid, p_language_id smallint, p_topic_recency_days smallint DEFAULT 14)
 RETURNS TABLE(test_id uuid, slug text, test_type text, title text, difficulty_level integer, elo_rating integer, elo_diff integer, tier text)
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
DECLARE
    v_user_tier_code TEXT;
    v_is_premium BOOLEAN;
    v_vocab_weight NUMERIC := 0;
BEGIN
    -- TASK-748 switch. Anything short of an explicit positive weight — a missing
    -- row, a missing table — means OFF.
    BEGIN
        SELECT COALESCE((SELECT st.value FROM selection_tuning st
                          WHERE st.key = 'vocab_weight'), 0)
          INTO v_vocab_weight;
    EXCEPTION WHEN undefined_table THEN
        v_vocab_weight := 0;
    END;

    IF v_vocab_weight > 0 THEN
        RETURN QUERY
        SELECT r.test_id, r.slug, r.test_type, r.title,
               r.difficulty_level, r.elo_rating, r.elo_diff, r.tier
          FROM recommended_tests_ranked(p_user_id, p_language_id,
                                        p_topic_recency_days, v_vocab_weight, NULL) r
         WHERE r.rank_in_type <= 10
         ORDER BY r.score, r.elo_diff, r.test_id;
        RETURN;
    END IF;

    -- vocab_weight = 0: the pre-TASK-748 query, VERBATIM (archived as
    -- migrations/archive/task748_prev_get_recommended_tests_live_3arg.sql). Do
    -- not edit this branch; the rollback guarantee is that it is unchanged.
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
              OR public.transcript_word_count(t.transcript)
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

CREATE OR REPLACE FUNCTION public.recommended_tests_ranked(
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
    v_combine        text;
    v_ability        numeric;
    v_source         text;
    v_learner_tier   integer;
BEGIN
    SELECT st.tier_code INTO v_user_tier_code
      FROM users u
      JOIN dim_subscription_tiers st ON u.subscription_tier_id = st.id
     WHERE u.id = p_user_id;
    v_is_premium := (v_user_tier_code NOT ILIKE '%free%');

    -- TASK-780: combine_mode joins the numeric knobs in the same single read.
    -- A missing row, a NULL value_text or anything other than 'product' is 'sum'
    -- — the mode cannot be switched on by absence.
    SELECT COALESCE(max(s.value) FILTER (WHERE s.key = 'elo_weight'),          1.0),
           COALESCE(max(s.value) FILTER (WHERE s.key = 'unknown_target'),      0.15),
           COALESCE(max(s.value) FILTER (WHERE s.key = 'unknown_tolerance'),   0.10),
           COALESCE(max(s.value) FILTER (WHERE s.key = 'tier_ceiling_offset'), 2)::integer,
           COALESCE(max(s.value_text) FILTER (WHERE s.key = 'combine_mode'),   'sum')
      INTO v_w_elo, v_u_star, v_u_tol, v_ceiling, v_combine
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
               OR public.transcript_word_count(t.transcript)
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
        -- TASK-780: computed on the RAW penalty, before the combination, so a
        -- neutral candidate carries the identical penalty in both modes.
        SELECT p.c_test_type AS co_type,
               percentile_cont(0.5) WITHIN GROUP (ORDER BY p.c_raw_penalty)::numeric AS co_median
          FROM penalised p
         WHERE p.c_raw_penalty IS NOT NULL
         GROUP BY p.c_test_type
    ),
    scored AS (
        -- TASK-780. ELSE is the TASK-748 expression VERBATIM: at combine_mode =
        -- 'sum' this function is output-identical to the pre-TASK-780 one.
        -- 'product' adds the cross term (1+e)(1+v) = 1 + e + v + e·v, so missing
        -- on both axes costs more than missing the same total on one. The 1 +
        -- shift is load-bearing: a bare e·v would rank a 90%-unknown test with a
        -- perfect ELO match FIRST, at score 0.
        SELECT p.*,
               COALESCE(p.c_raw_penalty, co.co_median, 0) AS c_penalty,
               CASE WHEN v_combine = 'product'
                    THEN (1 + v_w_elo * p.c_elo_diff / 400.0)
                       * (1 + p_vocab_weight * COALESCE(p.c_raw_penalty, co.co_median, 0))
                    ELSE v_w_elo * p.c_elo_diff / 400.0
                           + p_vocab_weight * COALESCE(p.c_raw_penalty, co.co_median, 0)
               END AS c_score
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

REVOKE ALL ON FUNCTION public.get_recommended_tests(uuid, smallint, smallint)
    FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.get_recommended_tests(uuid, smallint, smallint) TO service_role;
REVOKE ALL ON FUNCTION public.recommended_tests_ranked(uuid, smallint, smallint, numeric, timestamptz)
    FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.recommended_tests_ranked(uuid, smallint, smallint, numeric, timestamptz)
    TO service_role;

COMMIT;
