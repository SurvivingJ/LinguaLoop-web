-- =============================================================================
-- Pairs with migrations/task780_selection_combine_mode.sql (ADR-024, tech §3.3).
-- =============================================================================
-- TASK-780 — synthetic fixtures for `selection_tuning.combine_mode`. Rollback-
-- only: the real Japanese tests are deactivated INSIDE the transaction so the
-- five synthetic reading tests are the whole pool, and nothing survives.
--
-- A learner with no vocabulary, attempts or ratings is used, so every type's
-- current ELO is 1200 and both score terms are set exactly by the fixture:
--
--     e = elo_weight · |test_elo − 1200| / 400          (elo_weight = 1)
--     v = vocab_weight · |unknown − 0.15| / 0.10        (vocab_weight = 1)
--     unknown = 1 − mean p_known, and every sense carries a uvk row, so the
--     Zipf prior never runs and `unknown` is whatever the fixture says.
--
--   label      test_elo  p_known    e      v       sum     product=(1+e)(1+v)
--   good_both   1240     0.86      0.10   0.10     0.20    1.210
--   unlinked    1200     (none)    0.00   0.325*   0.325   1.325
--   bad_both    1400     0.795     0.50   0.55     1.05    2.325
--   bad_elo     1600     0.84      1.00   0.10     1.10    2.200
--   too_hard    1200     0.10      0.00   7.50     7.50    8.500
--   * the §3.4 neutral term: the MEDIAN raw penalty of the cohort
--     {0.10, 0.10, 0.55, 7.50} = 0.325, identical in both modes.
--
-- The point of the fixture is the pair in the middle. `bad_both` misses on BOTH
-- axes by half a term each; `bad_elo` misses a full term on difficulty alone and
-- is a near-perfect vocabulary match. Their summed misses are 1.05 and 1.10, so
-- SUM prefers bad_both — and PRODUCT reverses them (2.325 vs 2.200), because the
-- cross term e·v only exists when both axes miss. Expected orders:
--
--   sum      good_both, unlinked, bad_both, bad_elo, too_hard
--   product  good_both, unlinked, bad_elo, bad_both, too_hard
--
-- `too_hard` is the guard against the WRONG multiplicative form: a bare e·v
-- would score it 0 (perfect ELO match, 90% of its words unknown) and rank it
-- FIRST. It must rank LAST in both modes.
--
-- REVERT-RED: delete the `product` branch of the CASE in the `scored` CTE and
-- the two orders become equal, which assertion 3 reports by name.
--
--   psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f tests/sql/test_task780_combine_mode.sql
-- =============================================================================

BEGIN;

CREATE TEMP TABLE _t780_rank (
    mode text, label text, rank_in_type bigint, score numeric, unknown_share numeric,
    vocab_penalty numeric, vocab_neutral boolean, over_ceiling boolean,
    n_senses integer, n_resolved integer, ability_source text
) ON COMMIT DROP;

DO $test$
DECLARE
    v_user   uuid;
    v_lang   smallint := 3;
    v_type   smallint;
    s_good   int[]; s_bad_elo int[]; s_bad_both int[]; s_hard int[];
    t_good   uuid := gen_random_uuid();
    t_unlink uuid := gen_random_uuid();
    t_bboth  uuid := gen_random_uuid();
    t_belo   uuid := gen_random_uuid();
    t_hard   uuid := gen_random_uuid();
    v_sum    text[];
    v_prod   text[];
    v_want_s text[] := ARRAY['good_both','unlinked','bad_both','bad_elo','too_hard'];
    v_want_p text[] := ARRAY['good_both','unlinked','bad_elo','bad_both','too_hard'];
    v_n      integer;
    v_n0     integer;
    v_n_sum  integer;
    v_n_prod integer;
    v_rpc0_s jsonb;
    v_rpc0_p jsonb;
    r        record;
BEGIN
    SELECT u.id INTO v_user FROM public.users u
     WHERE NOT EXISTS (SELECT 1 FROM public.user_vocabulary_knowledge k WHERE k.user_id = u.id)
       AND NOT EXISTS (SELECT 1 FROM public.test_attempts a WHERE a.user_id = u.id)
       AND NOT EXISTS (SELECT 1 FROM public.user_skill_ratings s WHERE s.user_id = u.id)
     ORDER BY u.id LIMIT 1;
    IF v_user IS NULL THEN RAISE EXCEPTION 'no clean user available'; END IF;

    SELECT id INTO v_type FROM public.dim_test_types WHERE type_code = 'reading';

    -- Four disjoint blocks of ten senses, all with a Zipf (so none is dropped
    -- from S'). Which Zipf does not matter: every one gets a uvk row below, and
    -- recorded evidence wins over the prior.
    SELECT array_agg(q.id) INTO s_good FROM (
        SELECT ws.id FROM public.dim_word_senses ws JOIN public.dim_vocabulary v ON v.id = ws.vocab_id
         WHERE v.language_id = v_lang AND v.frequency_rank IS NOT NULL
         ORDER BY ws.id OFFSET 0 LIMIT 10) q;
    SELECT array_agg(q.id) INTO s_bad_elo FROM (
        SELECT ws.id FROM public.dim_word_senses ws JOIN public.dim_vocabulary v ON v.id = ws.vocab_id
         WHERE v.language_id = v_lang AND v.frequency_rank IS NOT NULL
         ORDER BY ws.id OFFSET 10 LIMIT 10) q;
    SELECT array_agg(q.id) INTO s_bad_both FROM (
        SELECT ws.id FROM public.dim_word_senses ws JOIN public.dim_vocabulary v ON v.id = ws.vocab_id
         WHERE v.language_id = v_lang AND v.frequency_rank IS NOT NULL
         ORDER BY ws.id OFFSET 20 LIMIT 10) q;
    SELECT array_agg(q.id) INTO s_hard FROM (
        SELECT ws.id FROM public.dim_word_senses ws JOIN public.dim_vocabulary v ON v.id = ws.vocab_id
         WHERE v.language_id = v_lang AND v.frequency_rank IS NOT NULL
         ORDER BY ws.id OFFSET 30 LIMIT 10) q;
    IF array_length(s_good,1) < 10 OR array_length(s_bad_elo,1) < 10
       OR array_length(s_bad_both,1) < 10 OR array_length(s_hard,1) < 10 THEN
        RAISE EXCEPTION 'could not find 40 Japanese senses with a frequency_rank';
    END IF;

    -- Pin the knobs the arithmetic above assumes (rolled back with everything).
    UPDATE public.selection_tuning SET value = 1.0  WHERE key = 'elo_weight';
    UPDATE public.selection_tuning SET value = 0.15 WHERE key = 'unknown_target';
    UPDATE public.selection_tuning SET value = 0.10 WHERE key = 'unknown_tolerance';
    UPDATE public.selection_tuning SET value = 2    WHERE key = 'tier_ceiling_offset';

    -- Isolate the pool (rolled back).
    UPDATE public.tests SET is_active = false WHERE language_id = v_lang AND is_active;

    INSERT INTO public.tests (id, gen_user, slug, difficulty, tier, title, language_id, is_active, vocab_sense_ids) VALUES
      (t_good,   v_user, '__t780_good',   1, 'free-tier', 'good_both', v_lang, true, s_good),
      (t_unlink, v_user, '__t780_unlink', 1, 'free-tier', 'unlinked',  v_lang, true, NULL),
      (t_bboth,  v_user, '__t780_bboth',  1, 'free-tier', 'bad_both',  v_lang, true, s_bad_both),
      (t_belo,   v_user, '__t780_belo',   1, 'free-tier', 'bad_elo',   v_lang, true, s_bad_elo),
      (t_hard,   v_user, '__t780_hard',   1, 'free-tier', 'too_hard',  v_lang, true, s_hard);

    INSERT INTO public.test_skill_ratings (test_id, test_type_id, elo_rating) VALUES
      (t_good, v_type, 1240), (t_unlink, v_type, 1200), (t_bboth, v_type, 1400),
      (t_belo, v_type, 1600), (t_hard,  v_type, 1200);

    -- The vocabulary side, set exactly: unknown = 1 − p_known.
    INSERT INTO public.user_vocabulary_knowledge (user_id, sense_id, language_id, p_known, status)
    SELECT v_user, x, v_lang, 0.86,  'known'   FROM unnest(s_good) x;
    INSERT INTO public.user_vocabulary_knowledge (user_id, sense_id, language_id, p_known, status)
    SELECT v_user, x, v_lang, 0.84,  'known'   FROM unnest(s_bad_elo) x;
    INSERT INTO public.user_vocabulary_knowledge (user_id, sense_id, language_id, p_known, status)
    SELECT v_user, x, v_lang, 0.795, 'known'   FROM unnest(s_bad_both) x;
    INSERT INTO public.user_vocabulary_knowledge (user_id, sense_id, language_id, p_known, status)
    SELECT v_user, x, v_lang, 0.10,  'unknown' FROM unnest(s_hard) x;

    -- A calibration row, so the vocabulary term is live at all (without an
    -- ability the whole pool would be neutral) and the §4 ceiling is armed.
    INSERT INTO public.user_calibration_state (user_id, language_id, mode, ability_zipf, ability_se,
                                               items_answered, sessions_pooled, last_run_at)
    VALUES (v_user, v_lang, 'definition', 5.0, 0.2, 100, 1, now());

    -- ---- the two arms ------------------------------------------------------
    UPDATE public.selection_tuning SET value_text = 'sum' WHERE key = 'combine_mode';
    INSERT INTO _t780_rank
    SELECT 'sum', x.title, x.rank_in_type, x.score, x.unknown_share, x.vocab_penalty,
           x.vocab_neutral, x.over_ceiling, x.n_senses, x.n_resolved, x.ability_source
      FROM public.recommended_tests_ranked(v_user, v_lang, 14::smallint, 1, NULL) x
     WHERE x.test_type = 'reading';

    UPDATE public.selection_tuning SET value_text = 'product' WHERE key = 'combine_mode';
    INSERT INTO _t780_rank
    SELECT 'product', x.title, x.rank_in_type, x.score, x.unknown_share, x.vocab_penalty,
           x.vocab_neutral, x.over_ceiling, x.n_senses, x.n_resolved, x.ability_source
      FROM public.recommended_tests_ranked(v_user, v_lang, 14::smallint, 1, NULL) x
     WHERE x.test_type = 'reading';

    -- ---- 1. the fixture is what it claims to be ----------------------------
    PERFORM 1 FROM _t780_rank WHERE ability_source <> 'calibration';
    IF FOUND THEN RAISE EXCEPTION 'FAIL: calibration row not used'; END IF;

    PERFORM 1 FROM _t780_rank WHERE over_ceiling;
    IF FOUND THEN
        RAISE EXCEPTION 'FAIL: a difficulty-1 fixture test is over the tier ceiling; the expected orders assume none is';
    END IF;

    SELECT count(*) INTO v_n FROM _t780_rank WHERE mode = 'sum' AND NOT vocab_neutral
       AND abs(unknown_share - (CASE label WHEN 'good_both' THEN 0.14 WHEN 'bad_elo' THEN 0.16
                                           WHEN 'bad_both'  THEN 0.205 ELSE 0.90 END)) > 0.0005;
    IF v_n > 0 THEN
        RAISE EXCEPTION 'FAIL: % fixture unknown_share values are not what p_known implies', v_n;
    END IF;

    -- ---- 2. sum mode is unchanged ------------------------------------------
    SELECT array_agg(label ORDER BY rank_in_type) INTO v_sum FROM _t780_rank WHERE mode = 'sum';
    IF v_sum IS DISTINCT FROM v_want_s THEN
        RAISE EXCEPTION 'FAIL sum order: got %, want %', v_sum, v_want_s;
    END IF;

    FOR r IN SELECT label, score,
                    CASE label WHEN 'good_both' THEN 0.20  WHEN 'unlinked' THEN 0.325
                               WHEN 'bad_both'  THEN 1.05  WHEN 'bad_elo'  THEN 1.10
                               ELSE 7.50 END AS want
               FROM _t780_rank WHERE mode = 'sum'
    LOOP
        IF abs(r.score - r.want) > 0.0001 THEN
            RAISE EXCEPTION 'FAIL sum score for %: got %, want % (e + v)', r.label, r.score, r.want;
        END IF;
    END LOOP;

    -- ---- 3. product mode: the cross term, and only the cross term ----------
    SELECT array_agg(label ORDER BY rank_in_type) INTO v_prod FROM _t780_rank WHERE mode = 'product';
    IF v_prod IS DISTINCT FROM v_want_p THEN
        RAISE EXCEPTION 'FAIL product order: got %, want %', v_prod, v_want_p;
    END IF;
    IF v_prod = v_sum THEN
        RAISE EXCEPTION 'FAIL: combine_mode = product ranked identically to sum — the product branch of the scored CTE is not running';
    END IF;

    FOR r IN SELECT label, score,
                    CASE label WHEN 'good_both' THEN 1.210 WHEN 'unlinked' THEN 1.325
                               WHEN 'bad_both'  THEN 2.325 WHEN 'bad_elo'  THEN 2.200
                               ELSE 8.500 END AS want
               FROM _t780_rank WHERE mode = 'product'
    LOOP
        IF abs(r.score - r.want) > 0.0001 THEN
            RAISE EXCEPTION 'FAIL product score for %: got %, want % ((1+e)(1+v))', r.label, r.score, r.want;
        END IF;
    END LOOP;

    -- The requirement in one assertion: worse on both beats nothing.
    IF NOT ((SELECT rank_in_type FROM _t780_rank WHERE mode = 'product' AND label = 'bad_both')
          > (SELECT rank_in_type FROM _t780_rank WHERE mode = 'product' AND label = 'bad_elo'))
       OR NOT ((SELECT rank_in_type FROM _t780_rank WHERE mode = 'sum' AND label = 'bad_both')
             < (SELECT rank_in_type FROM _t780_rank WHERE mode = 'sum' AND label = 'bad_elo')) THEN
        RAISE EXCEPTION 'FAIL: a candidate wrong on BOTH axes must rank below one equally wrong on a single axis under product (and above it under sum)';
    END IF;

    -- The wrong multiplicative form, pinned: a bare e·v scores too_hard 0.
    PERFORM 1 FROM _t780_rank a
     WHERE a.label = 'too_hard'
       AND a.rank_in_type <> (SELECT max(b.rank_in_type) FROM _t780_rank b WHERE b.mode = a.mode);
    IF FOUND THEN
        RAISE EXCEPTION 'FAIL: a perfect-ELO / 90%%-unknown test is not last — the score is a bare product of the two gaps, not (1+e)(1+v)';
    END IF;

    -- ---- 4. the §3.4 neutral path is identical in both modes ---------------
    SELECT count(*) INTO v_n
      FROM _t780_rank s JOIN _t780_rank p ON p.label = s.label AND p.mode = 'product'
     WHERE s.mode = 'sum'
       AND (s.vocab_neutral IS DISTINCT FROM p.vocab_neutral
         OR s.vocab_penalty IS DISTINCT FROM p.vocab_penalty
         OR s.unknown_share IS DISTINCT FROM p.unknown_share
         OR s.n_senses      IS DISTINCT FROM p.n_senses
         OR s.n_resolved    IS DISTINCT FROM p.n_resolved);
    IF v_n > 0 THEN
        RAISE EXCEPTION 'FAIL: % candidates differ in a pre-combination column between modes; combine_mode must change only the score', v_n;
    END IF;

    SELECT * INTO r FROM _t780_rank WHERE mode = 'product' AND label = 'unlinked';
    IF NOT r.vocab_neutral OR r.n_senses IS NOT NULL THEN
        RAISE EXCEPTION 'FAIL: the unlinked test is not neutral in product mode';
    END IF;
    IF abs(r.vocab_penalty - 0.325) > 0.0001 THEN
        RAISE EXCEPTION 'FAIL: the neutral term is %, not the cohort median 0.325 — it must be neither 0 nor infinite', r.vocab_penalty;
    END IF;

    -- ---- 5. M5: no pool shrinks, in either mode ----------------------------
    UPDATE public.selection_tuning SET value = 0 WHERE key = 'vocab_weight';
    SELECT count(*) INTO v_n0 FROM public.get_recommended_tests(v_user, v_lang, 14::smallint);
    SELECT COALESCE(jsonb_agg(to_jsonb(x) ORDER BY x.ord), '[]'::jsonb) INTO v_rpc0_p
      FROM public.get_recommended_tests(v_user, v_lang, 14::smallint) WITH ORDINALITY
           AS x(test_id, slug, test_type, title, difficulty_level, elo_rating, elo_diff, tier, ord);

    UPDATE public.selection_tuning SET value_text = 'sum' WHERE key = 'combine_mode';
    SELECT COALESCE(jsonb_agg(to_jsonb(x) ORDER BY x.ord), '[]'::jsonb) INTO v_rpc0_s
      FROM public.get_recommended_tests(v_user, v_lang, 14::smallint) WITH ORDINALITY
           AS x(test_id, slug, test_type, title, difficulty_level, elo_rating, elo_diff, tier, ord);
    IF v_rpc0_s IS DISTINCT FROM v_rpc0_p THEN
        RAISE EXCEPTION 'FAIL: combine_mode changed the public RPC at vocab_weight = 0 — the rollback branch must be reached whatever the mode says';
    END IF;

    UPDATE public.selection_tuning SET value = 1 WHERE key = 'vocab_weight';
    SELECT count(*) INTO v_n_sum FROM public.get_recommended_tests(v_user, v_lang, 14::smallint);
    UPDATE public.selection_tuning SET value_text = 'product' WHERE key = 'combine_mode';
    SELECT count(*) INTO v_n_prod FROM public.get_recommended_tests(v_user, v_lang, 14::smallint);
    UPDATE public.selection_tuning SET value = 0 WHERE key = 'vocab_weight';
    UPDATE public.selection_tuning SET value_text = 'sum' WHERE key = 'combine_mode';

    IF v_n0 <> 5 OR v_n_sum <> v_n0 OR v_n_prod <> v_n0 THEN
        RAISE EXCEPTION 'FAIL M5: candidate count is % at weight 0, % at sum, % at product (want 5, 5, 5)',
            v_n0, v_n_sum, v_n_prod;
    END IF;

    RAISE NOTICE 'TASK-780 combine_mode PASS: sum unchanged, product reorders only the both-axes miss, neutral path identical, M5 holds';
END $test$;

SELECT mode, rank_in_type, label, score, unknown_share, vocab_penalty,
       vocab_neutral, over_ceiling, n_senses, n_resolved
  FROM _t780_rank ORDER BY mode DESC, rank_in_type;

ROLLBACK;
