-- TASK-780 — multiplicative ELO × coverage scoring, shipped INERT.
-- Supersedes the `recommended_tests_ranked` definition in
-- migrations/task748_get_recommended_tests_vocab_aware.sql (that file is NOT
-- archived: it is still the only repo record of selection_vocab_ability and of
-- get_recommended_tests, both live and not redefined here — migrations/CLAUDE.md
-- rule 4). It also ALTERs the table created by
-- migrations/task744_selection_tuning_table.sql, which likewise stays.
-- =============================================================================
-- PROBLEM
--   TASK-748 ranks candidates on a SUM of two normalised misses:
--       score(t) = elo_weight·|Δelo|/400 + vocab_weight·|unknown − u*|/u_tol
--   A sum is indifferent to how a given total miss is distributed. A test that
--   is half a term wrong on difficulty AND half a term wrong on vocabulary
--   scores the same as one that is a full term wrong on difficulty alone and a
--   perfect match on vocabulary — but it is a worse lesson, because the learner
--   hits both frictions at once. The sum cannot express that interaction.
--
-- FIX (features/vocabulary-aware-test-selection.tech §3.3)
--   One new selection_tuning key, `combine_mode`, 'sum' (default) | 'product'.
--
--     sum      score = e + v
--     product  score = (1 + e) · (1 + v)   =   1 + e + v + e·v
--
--   with e = elo_weight·|Δelo|/400 and v = vocab_weight·|unknown − u*|/u_tol,
--   i.e. exactly today's terms, unchanged. Product is the sum plus the cross
--   term e·v (and a constant 1, which cannot reorder anything), so a candidate
--   that misses on BOTH axes is pushed down harder than one that misses the
--   same total amount on either axis alone. Lower is better in both modes.
--
--   WHY 1 + x AND NOT A BARE PRODUCT e·v. A bare product is not a worse ranker,
--   it is a broken one: any perfect match on either axis annihilates the other.
--   A test with a perfect ELO match and 90% unknown words would score 0 and rank
--   FIRST. The 1 + x shift makes each factor a multiplier ≥ 1 on the other's
--   miss, which is the intended reading ("this test is 2.2× as far off as an
--   ideal one"), and keeps both factors monotone increasing. Pinned by the
--   `too_hard` candidate in tests/sql/test_task780_combine_mode.sql, which must
--   rank LAST in both modes.
--
--   COVERAGE COUNTING IS UNCHANGED, DELIBERATELY. unknown(t) still counts each
--   DISTINCT sense in tests.vocab_sense_ids once. Per-occurrence counting (the
--   shape TASK-780 was originally sketched as, over tests.vocab_token_map) was
--   considered and dropped: a linked word appears 1.15 (ja) / 1.33 (zh) / 1.44
--   (en) times per test, so the two measures nearly coincide, while distinct-
--   word counting is the better match for "how much new vocabulary must this
--   learner absorb". TASK-779's token-map repair stands on its own merits.
--
-- WHAT CHANGES, AND WHAT PROVABLY DOES NOT
--   - recommended_tests_ranked: same signature, same RETURNS TABLE, same CTEs.
--     Two additions only: combine_mode is read alongside the other tuning keys,
--     and the `scored` CTE wraps the score in a CASE. The ELSE branch is the
--     TASK-748 expression VERBATIM, so combine_mode = 'sum' is output-identical
--     — proven against a frozen copy of the pre-TASK-780 body in
--     tests/sql/test_task748_parity.sql, not argued from the diff.
--   - get_recommended_tests is NOT TOUCHED. It still runs the verbatim
--     pre-TASK-748 query whenever vocab_weight = 0, so the rollback guarantee is
--     untouched and combine_mode is inert while vocab_weight = 0 — a 'product'
--     row changes nothing a learner sees until the weight is also raised. That
--     is what makes the TASK-781 replay safe to run against live.
--   - Degradation (§3.4) is untouched. The neutral term is still the MEDIAN raw
--     penalty of the (user, type) cohort, computed before the combination, so a
--     neutral candidate gets the identical vocab_penalty in both modes; never 0,
--     never +∞. Nothing is excluded, so M5 (per-type pool size never falls)
--     holds in product mode for the same reason it holds in sum mode.
--
-- NO NEW FUNCTION PARAMETER — ON PURPOSE
--   combine_mode is a settings row, not a defaulted argument, for the reason
--   migrations/get_recommended_tests_drop_ambiguous_overload.sql already had to
--   clean up once: a defaulted parameter creates an overload PostgREST resolves
--   unpredictably. It also means an operator flips a mode without re-applying a
--   migration. The TASK-781 replay switches arms with a transaction-local
--   `UPDATE selection_tuning ... ; ROLLBACK`, the same way the SQL tests do.
--
-- SCHEMA: selection_tuning GAINS A TEXT VALUE
--   `value` is numeric NOT NULL, and combine_mode is not a number. Encoding it
--   as 0/1 was rejected: an operator typing `UPDATE selection_tuning SET value =
--   1 WHERE key = 'combine_mode'` should not have to remember which mode 1 is.
--   So: a nullable `value_text` column, `value` made nullable, and a CHECK that
--   each key carries exactly one of the two — numeric keys keep their NOT NULL
--   guarantee through that CHECK rather than through the column.
--
-- SAFETY
--   - Idempotent: ADD COLUMN IF NOT EXISTS, DROP CONSTRAINT IF EXISTS before
--     each ADD CONSTRAINT, seed ON CONFLICT DO NOTHING (so re-running never
--     resets an operator's mode), CREATE OR REPLACE for the function.
--   - The new CHECKs are added VALID, not NOT VALID: selection_tuning holds six
--     rows, so migrations/CLAUDE.md's short-lock backfill pattern does not apply
--     — the validating scan is six tuples.
--   - A missing combine_mode row, or a NULL value_text, reads as 'sum'. So does
--     any value the CHECK would have to be dropped to allow: the CASE tests for
--     'product' and falls through to sum. Nothing can switch the product arm on
--     by accident.
--   - Grants and RLS unchanged; a new column inherits the table's privileges.
--     The function keeps SECURITY DEFINER, SET search_path, and service_role-only
--     EXECUTE (it reads one user's vocabulary).
--   - get_recommended_tests and selection_vocab_ability are not redefined; no
--     overload is created (still 1 row in pg_proc for get_recommended_tests).
--
-- APPLIED LIVE: 2026-09-16 (see the tasklist entry for the exact
--   schema_migrations timestamp), with selection_tuning.vocab_weight = 0 and
--   combine_mode = 'sum' — INERT ON BOTH SWITCHES. Verified live after applying:
--   the pre-TASK-780 ranker body, loaded under a scratch name inside a
--   rollback-only transaction, returns rows identical in content and order to
--   the new function at combine_mode = 'sum' for every user × en/zh/ja at
--   vocab_weight 0 and 1; the public RPC is unchanged at vocab_weight = 0 under
--   both modes; no per-type candidate count falls in either mode.
-- =============================================================================


-- -----------------------------------------------------------------------------
-- 1. selection_tuning: a text-valued key alongside the numeric ones.
-- -----------------------------------------------------------------------------
ALTER TABLE public.selection_tuning ADD COLUMN IF NOT EXISTS value_text text;
ALTER TABLE public.selection_tuning ALTER COLUMN value DROP NOT NULL;

-- `value NOT NULL` moves from the column to this CHECK, so the numeric keys are
-- exactly as protected as before while combine_mode carries text instead.
ALTER TABLE public.selection_tuning
    DROP CONSTRAINT IF EXISTS selection_tuning_value_shape;
ALTER TABLE public.selection_tuning
    ADD CONSTRAINT selection_tuning_value_shape CHECK (
        CASE WHEN key IN ('combine_mode')
             THEN value IS NULL     AND value_text IS NOT NULL
             ELSE value IS NOT NULL AND value_text IS NULL
        END);

ALTER TABLE public.selection_tuning
    DROP CONSTRAINT IF EXISTS selection_tuning_combine_mode_valid;
ALTER TABLE public.selection_tuning
    ADD CONSTRAINT selection_tuning_combine_mode_valid CHECK (
        key <> 'combine_mode' OR value_text IN ('sum', 'product'));

INSERT INTO public.selection_tuning (key, value, value_text) VALUES
    ('combine_mode', NULL, 'sum')   -- INERT on arrival; 'product' is the new arm
ON CONFLICT (key) DO NOTHING;

COMMENT ON TABLE public.selection_tuning IS
  'Operator-tunable constants for get_recommended_tests (TASK-744/748/780, ADR-024). Numeric keys use `value`; text-valued keys (combine_mode) use `value_text` — the selection_tuning_value_shape CHECK enforces exactly one per key. vocab_weight = 0 reproduces the pre-TASK-748 ranking exactly and is the rollback switch; combine_mode is inert while it is 0. Not writable by learners.';

COMMENT ON COLUMN public.selection_tuning.value_text IS
  'TASK-780: value for text-valued keys. combine_mode = ''sum'' (score = e + v) | ''product'' (score = (1+e)·(1+v), i.e. the sum plus the cross term e·v).';


-- -----------------------------------------------------------------------------
-- 2. The ranker, with the combination mode. Everything outside the `scored` CTE
--    and the tuning read is the TASK-748 body unchanged.
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

COMMENT ON FUNCTION public.recommended_tests_ranked(uuid, smallint, smallint, numeric, timestamptz) IS
  'TASK-748/780 ranker: every eligible candidate with its score decomposed. e = elo_weight·|Δelo|/400, v = p_vocab_weight·|unknown − u*|/u_tol; selection_tuning.combine_mode picks score = e + v (''sum'', the default) or (1+e)·(1+v) (''product'', which adds the cross term e·v so a candidate wrong on both axes is demoted below one equally wrong on a single axis). get_recommended_tests calls it only when selection_tuning.vocab_weight > 0, so combine_mode is inert while that is 0; p_as_of reconstructs a past candidate set for the offline replay. Service role only — it reads one user''s vocabulary.';

REVOKE ALL ON FUNCTION public.recommended_tests_ranked(uuid, smallint, smallint, numeric, timestamptz)
    FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.recommended_tests_ranked(uuid, smallint, smallint, numeric, timestamptz)
    TO service_role;

-- =============================================================================
-- Verification
-- =============================================================================
--   SELECT key, value, value_text FROM selection_tuning ORDER BY key;
--   -- combine_mode NULL sum | elo_weight 1.0 | tier_ceiling_offset 2 |
--   -- unknown_target 0.15 | unknown_tolerance 0.10 | vocab_weight 0
--
--   -- still exactly one public RPC, no overload:
--   SELECT count(*) FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
--    WHERE n.nspname = 'public' AND p.proname = 'get_recommended_tests';   -- 1
--
--   -- sum-mode parity against a frozen pre-TASK-780 body + pool health, and the
--   -- product-mode fixtures (both rollback-only):
--   psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f tests/sql/test_task748_parity.sql
--   psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f tests/sql/test_task780_combine_mode.sql
--
-- Switch the product arm on (operator decision, after the TASK-781 replay — and
-- it does nothing on its own: vocab_weight must be > 0 as well):
--   UPDATE selection_tuning SET value_text = 'product' WHERE key = 'combine_mode';
-- Roll back:
--   UPDATE selection_tuning SET value_text = 'sum'     WHERE key = 'combine_mode';
-- =============================================================================
