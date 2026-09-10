-- TASK-748 — vocabulary-aware get_recommended_tests, shipped SWITCHED OFF.
-- Supersedes the live 3-arg body, archived verbatim as
-- migrations/archive/task748_prev_get_recommended_tests_live_3arg.sql.
-- =============================================================================
-- PROBLEM
--   get_recommended_tests ranks candidates on ABS(test_elo - user_elo) alone and
--   never reads vocabulary. ADR-024 records why ELO cannot fix itself: the MC
--   chance floor caps Elo's reach at ~191 points, while the measured ja ability
--   spread is 448 points inside an 88-point assigned band. Meanwhile the signal
--   ELO lacks — which of a test's senses this learner knows — sits unused in
--   user_vocabulary_knowledge (known share 73% / 17% / 9% at difficulty 1/6/9).
--
-- FIX (features/vocabulary-aware-test-selection.tech §3)
--   score(t) = elo_weight · |test_elo − user_elo| / 400
--            + vocab_weight · |unknown(t) − u*| / u_tol
--   ranked per test type, rank_in_type <= 10 kept, now on the score.
--
--   Three objects:
--     selection_vocab_ability(user, lang, as_of)   — the ability_zipf the prior uses
--     recommended_tests_ranked(user, lang, days, weight, as_of)
--                                                  — the ranker, every candidate,
--                                                    with its score decomposed
--     get_recommended_tests(user, lang, days)      — same 3-arg signature, same
--                                                    RETURNS TABLE; thin switch
--
--   unknown(t) = 1 − mean P_known(s) over S', where S' is the test's senses that
--   resolve to a dim_vocabulary row with a non-null Zipf (frequency_rank — a Zipf
--   SCORE, higher = more common, not a rank). Senses with no Zipf leave the
--   denominator; they are not counted as unknown.
--
--   P_known(s) = user_vocabulary_knowledge.p_known          if a row exists
--              = σ(1.5·(zipf(s) − ability_zipf) + ln(0.85/0.15))   otherwise
--
-- TWO CORRECTIONS TO THE SPEC, both recorded in tech spec §3.2 as well
--   (a) THE PRIOR IS 0.85 AT ability_zipf, NOT 0.5. ability_zipf is by contract
--       the 85%-KNOWN crossing (§1.2), so a sense exactly at the learner's
--       ability_zipf must be 85% likely known. The spec's σ(1.5·(zipf − a)) put
--       0.5 there, i.e. it treated a as a 50% crossover — the very construct
--       §1.2 forbids. The ln(0.85/0.15) = 1.7346 offset fixes it. Check: slope 1.5
--       then puts the 50% point 1.7346/1.5 = 1.16 Zipf below the threshold, which
--       matches the live ja curve (85% at ~5.0, 50% at ~3.85).
--   (b) THE NO-CALIBRATION FALLBACK IS AN 85% CROSSING, NOT A MEDIAN. The spec's
--       "median Zipf of senses with p_known >= 0.6" is a location of KNOWN words,
--       i.e. the "mean of known senses" construct §1.2 rules out by name. Instead:
--       bucket the learner's own uvk rows into 0.5-wide Zipf bands (n >= 5), take
--       known-share = share with p_known >= 0.6, and interpolate where it crosses
--       0.85 walking down from the commonest band. That needs a band >= 0.85
--       directly above a band < 0.85; with no such pair the crossing is not
--       identifiable and the vocabulary term is NEUTRAL. user_calibration_state
--       has 0 rows, so this fallback is the path that actually runs today.
--       Live 2026-09-10 for the one learner with data: ja 5.02 (spec measured
--       "~5.0"), zh 5.15.
--
-- DEGRADATION (§3.4) — never a filter
--   A test gets a NEUTRAL term (the median penalty of its (user, type) candidate
--   cohort — "no opinion"; 0 if the whole cohort is neutral) when vocab_sense_ids
--   is NULL/empty (27 zh, 21 en active tests live), when |S'| < 5 or
--   |S'|/|S| < 0.5, or when no ability_zipf is available at all. 0 would make
--   unlinked tests always win; +∞ would silently empty a fifth of the en/zh pool.
--
-- ONE DELIBERATE DEVIATION FROM §4 — the tier ceiling DEMOTES, it does not exclude
--   §4 says "exclude candidates more than tier_ceiling_offset tiers above the
--   learner's calibrated tier". Excluding contradicts M5 (per-type candidate
--   count must never fall) and ADR-024's "vocabulary may never remove the last
--   candidate from a pool": whenever fewer than 10 within-ceiling candidates
--   exist, exclusion shrinks the pool. So an over-ceiling test is ranked AFTER
--   every within-ceiling test instead. The day-one 840-character d9 dictation
--   still cannot be served while any within-ceiling dictation exists, and the
--   count never falls. Applies only when a mode='definition' calibration row
--   exists AND vocab_weight > 0; with no calibration it affects nothing.
--
-- THE ROLLBACK SWITCH IS EXACT BY CONSTRUCTION
--   vocab_weight = 0 (the shipped value) runs the captured pre-TASK-748 query
--   VERBATIM. Rather than hoping a new ORDER BY reproduces the old one: 48 of 60
--   ja tests share one ELO across all types, so the old ordering is full of ties,
--   and a rewritten query could legally break them differently. Parity was
--   proven live before applying — see tests/sql/test_task748_parity.sql and the
--   APPLIED LIVE line.
--
-- SAFETY
--   - Signature and RETURNS TABLE of get_recommended_tests unchanged; CREATE OR
--     REPLACE keeps its grants; no overload is created (verified: 1 row in
--     pg_proc). Do NOT add a defaulted weight parameter — see
--     migrations/get_recommended_tests_drop_ambiguous_overload.sql.
--   - The two new functions read one user's user_vocabulary_knowledge and take
--     p_user_id, so EXECUTE is revoked from PUBLIC/anon/authenticated and granted
--     to service_role only. p_user_id is carried into every CTE that reads uvk.
--   - Missing selection_tuning table or key reads as vocab_weight = 0: nothing
--     can switch the feature ON by accident.
--   - process_test_submission is not touched (md5 identical before and after).
--   - Idempotent: CREATE OR REPLACE throughout.
--
-- AS-OF REPLAY (p_as_of, used by scripts/measure_selection_quality.py only)
--   With p_as_of set, the ranker reconstructs the candidate set as of that
--   moment: attempts, topic recency, test existence, the learner's per-type ELO
--   (last user_elo_after before p_as_of, else 1200) and uvk rows created before
--   it. Two things it CANNOT rewind and uses current values for: test ELOs
--   (test_skill_ratings keeps no history; TASK-732 reseeded ja dictation/pitch
--   on 2026-08-22) and p_known on uvk rows that existed but were later updated.
--   The replay is therefore an approximation, not a re-enactment.
--
-- APPLIED LIVE: 2026-09-10 11:49:05 UTC (schema_migrations 20260910114905), with
--   selection_tuning.vocab_weight = 0 — INERT. Applied only after a rollback-only
--   pre-apply proof on live: across all 13 users × en/zh/ja (39 pairs; 620/650/520
--   rows) vocab_weight = 0 returned rows identical in content AND order to the
--   old function (the old function was also self-consistent on all 39), and at
--   vocab_weight = 1 no per-type candidate count fell (min delta 0). Re-run
--   post-apply: identical. 1 row in pg_proc for get_recommended_tests; new
--   helpers are service_role-only; process_test_submission md5 unchanged.
-- =============================================================================


-- -----------------------------------------------------------------------------
-- 1. ability_zipf for the prior: calibration first, else the uvk 85% crossing.
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.selection_vocab_ability(
    p_user_id     uuid,
    p_language_id smallint,
    p_as_of       timestamptz DEFAULT NULL)
RETURNS TABLE(ability_zipf numeric, ability_source text)
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path TO 'public'
AS $function$
    WITH cal AS (
        -- mode = 'definition' ONLY: pronunciation measures reading, not
        -- vocabulary, and must never stand in for a missing definition row.
        SELECT ucs.ability_zipf AS z
          FROM user_calibration_state ucs
         WHERE ucs.user_id = p_user_id
           AND ucs.language_id = p_language_id
           AND ucs.mode = 'definition'
           AND ucs.ability_zipf IS NOT NULL
           AND (p_as_of IS NULL OR ucs.last_run_at <= p_as_of)
    ),
    bands AS (
        SELECT floor(v.frequency_rank::numeric * 2) / 2 AS band_lo,
               avg((k.p_known >= 0.6)::int)::numeric   AS share
          FROM user_vocabulary_knowledge k
          JOIN dim_word_senses ws ON ws.id = k.sense_id
          JOIN dim_vocabulary v   ON v.id = ws.vocab_id
         WHERE k.user_id = p_user_id
           AND k.language_id = p_language_id
           AND v.frequency_rank IS NOT NULL
           AND (p_as_of IS NULL OR k.created_at < p_as_of)
         GROUP BY 1
        HAVING count(*) >= 5
    ),
    walked AS (
        -- Commonest band first; each band sees the next-commoner eligible band.
        SELECT b.band_lo + 0.25 AS mid, b.share,
               lag(b.band_lo + 0.25) OVER (ORDER BY b.band_lo DESC) AS prev_mid,
               lag(b.share)          OVER (ORDER BY b.band_lo DESC) AS prev_share
          FROM bands b
    ),
    crossing AS (
        -- First step down from >= 85% to < 85%, linearly interpolated between the
        -- two band midpoints. prev_share > share here, so no division by zero.
        SELECT w.mid + (w.prev_mid - w.mid) * (0.85 - w.share) / (w.prev_share - w.share) AS z
          FROM walked w
         WHERE w.prev_share >= 0.85 AND w.share < 0.85
         ORDER BY w.mid DESC
         LIMIT 1
    )
    SELECT COALESCE((SELECT z FROM cal), round((SELECT z FROM crossing), 4)),
           CASE WHEN EXISTS (SELECT 1 FROM cal)      THEN 'calibration'
                WHEN EXISTS (SELECT 1 FROM crossing) THEN 'uvk_crossing'
                ELSE 'none' END;
$function$;

COMMENT ON FUNCTION public.selection_vocab_ability(uuid, smallint, timestamptz) IS
  'TASK-748: the ability_zipf behind the untested-sense prior. user_calibration_state (mode=definition) if present, else the Zipf where the learner''s own uvk known-share (p_known >= 0.6, 0.5-wide bands, n >= 5) crosses 85%, else NULL (source ''none'' → neutral vocabulary term). Never a median of known senses — that is the construct tech spec §1.2 rules out.';

REVOKE ALL ON FUNCTION public.selection_vocab_ability(uuid, smallint, timestamptz)
    FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.selection_vocab_ability(uuid, smallint, timestamptz)
    TO service_role;


-- -----------------------------------------------------------------------------
-- 2. The ranker. Returns EVERY eligible candidate with its score decomposed, so
--    the measurement harness can see why a test ranked where it did.
-- -----------------------------------------------------------------------------
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

COMMENT ON FUNCTION public.recommended_tests_ranked(uuid, smallint, smallint, numeric, timestamptz) IS
  'TASK-748 ranker: every eligible candidate with score = elo_weight·|Δelo|/400 + p_vocab_weight·|unknown − u*|/u_tol decomposed. get_recommended_tests calls it only when selection_tuning.vocab_weight > 0; p_as_of reconstructs a past candidate set for the offline replay. Service role only — it reads one user''s vocabulary.';

REVOKE ALL ON FUNCTION public.recommended_tests_ranked(uuid, smallint, smallint, numeric, timestamptz)
    FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.recommended_tests_ranked(uuid, smallint, smallint, numeric, timestamptz)
    TO service_role;


-- -----------------------------------------------------------------------------
-- 3. The public RPC. Same 3-arg signature, same RETURNS TABLE.
-- -----------------------------------------------------------------------------
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

-- =============================================================================
-- Verification
-- =============================================================================
--   -- no overload:
--   SELECT count(*) FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
--    WHERE n.nspname = 'public' AND p.proname = 'get_recommended_tests';   -- 1
--   -- parity + pool health (rollback-only):
--   psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f tests/sql/test_task748_parity.sql
--   -- ranking fixtures (rollback-only):
--   psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f tests/sql/test_task748_vocab_ranking.sql
-- =============================================================================
