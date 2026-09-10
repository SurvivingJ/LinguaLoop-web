-- =============================================================================
-- Pairs with migrations/task748_get_recommended_tests_vocab_aware.sql (ADR-024).
-- =============================================================================
-- TASK-748 — synthetic-fixture tests for the vocabulary term (tech spec §5.2.3,
-- §6). Rollback-only: nothing survives the transaction.
--
-- Isolation: the real Japanese tests are deactivated INSIDE the transaction so
-- the seven synthetic reading tests are the whole pool. A learner with no
-- vocabulary, attempts or ratings is used, so every test's ELO distance is 0 and
-- the ranking is decided by the vocabulary term alone.
--
-- Calibration row: ability_zipf 5.0 (mode 'definition') → 1250 → tier T2, so the
-- §4 ceiling (offset 2) is T4 and a difficulty-9 (T6) test is over it.
--
-- Expected penalties |unknown − 0.15| / 0.10, prior σ(1.5·(z − 5.0) + ln(0.85/0.15)):
--   target      Zipf ~5.0, the 85% point           → unknown 0.15 → ~0
--   known_rare  Zipf ~3.3 BUT uvk p_known 0.95     → unknown 0.05 → 1.0
--   easy        Zipf ~6.0                          → unknown 0.04 → ~1.12
--   midhard     Zipf ~4.0                          → unknown 0.44 → ~2.92
--   hard        Zipf ~3.3, no uvk rows             → unknown 0.69 → ~5.43
--   d9_twin     target's senses at difficulty 9    → ~0, but OVER CEILING
--   unlinked    vocab_sense_ids NULL               → neutral = cohort median
-- so the order must be: target, known_rare, unlinked, easy, midhard, hard, d9_twin.
--
--   psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f tests/sql/test_task748_vocab_ranking.sql
-- =============================================================================

BEGIN;

CREATE TEMP TABLE _t748_rank (
    phase text, label text, rank_in_type bigint, unknown_share numeric,
    vocab_penalty numeric, vocab_neutral boolean, over_ceiling boolean,
    n_senses integer, n_resolved integer, ability_source text
) ON COMMIT DROP;

DO $test$
DECLARE
    v_user   uuid;
    v_lang   smallint := 3;
    v_type   smallint;
    s_target int[]; s_easy int[]; s_midhard int[]; s_hard int[]; s_rare int[];
    s_null   int;
    t_target uuid := gen_random_uuid();
    t_rare   uuid := gen_random_uuid();
    t_unlink uuid := gen_random_uuid();
    t_easy   uuid := gen_random_uuid();
    t_mid    uuid := gen_random_uuid();
    t_hard   uuid := gen_random_uuid();
    t_d9     uuid := gen_random_uuid();
    v_order  text[];
    v_want   text[] := ARRAY['target','known_rare','unlinked','easy','midhard','hard','d9_twin'];
    v_n0     integer;
    v_n1     integer;
    r        record;
BEGIN
    SELECT u.id INTO v_user FROM public.users u
     WHERE NOT EXISTS (SELECT 1 FROM public.user_vocabulary_knowledge k WHERE k.user_id = u.id)
       AND NOT EXISTS (SELECT 1 FROM public.test_attempts a WHERE a.user_id = u.id)
       AND NOT EXISTS (SELECT 1 FROM public.user_skill_ratings s WHERE s.user_id = u.id)
     ORDER BY u.id LIMIT 1;
    IF v_user IS NULL THEN RAISE EXCEPTION 'no clean user available'; END IF;

    SELECT id INTO v_type FROM public.dim_test_types WHERE type_code = 'reading';

    SELECT array_agg(q.id) INTO s_target FROM (
        SELECT ws.id FROM public.dim_word_senses ws JOIN public.dim_vocabulary v ON v.id = ws.vocab_id
         WHERE v.language_id = v_lang AND v.frequency_rank BETWEEN 4.98 AND 5.02 ORDER BY ws.id LIMIT 10) q;
    SELECT array_agg(q.id) INTO s_easy FROM (
        SELECT ws.id FROM public.dim_word_senses ws JOIN public.dim_vocabulary v ON v.id = ws.vocab_id
         WHERE v.language_id = v_lang AND v.frequency_rank BETWEEN 5.95 AND 6.05 ORDER BY ws.id LIMIT 10) q;
    SELECT array_agg(q.id) INTO s_midhard FROM (
        SELECT ws.id FROM public.dim_word_senses ws JOIN public.dim_vocabulary v ON v.id = ws.vocab_id
         WHERE v.language_id = v_lang AND v.frequency_rank BETWEEN 3.98 AND 4.02 ORDER BY ws.id LIMIT 10) q;
    SELECT array_agg(q.id) INTO s_hard FROM (
        SELECT ws.id FROM public.dim_word_senses ws JOIN public.dim_vocabulary v ON v.id = ws.vocab_id
         WHERE v.language_id = v_lang AND v.frequency_rank BETWEEN 3.28 AND 3.32 ORDER BY ws.id LIMIT 10) q;
    SELECT array_agg(q.id) INTO s_rare FROM (
        SELECT ws.id FROM public.dim_word_senses ws JOIN public.dim_vocabulary v ON v.id = ws.vocab_id
         WHERE v.language_id = v_lang AND v.frequency_rank BETWEEN 3.28 AND 3.32 ORDER BY ws.id OFFSET 10 LIMIT 10) q;
    SELECT ws.id INTO s_null FROM public.dim_word_senses ws JOIN public.dim_vocabulary v ON v.id = ws.vocab_id
     WHERE v.language_id = v_lang AND v.frequency_rank IS NULL ORDER BY ws.id LIMIT 1;
    IF array_length(s_target,1) < 10 OR array_length(s_easy,1) < 10 OR array_length(s_midhard,1) < 10
       OR array_length(s_hard,1) < 10 OR array_length(s_rare,1) < 10 OR s_null IS NULL THEN
        RAISE EXCEPTION 'could not find enough senses in the Zipf bands';
    END IF;

    -- Isolate the pool (rolled back).
    UPDATE public.tests SET is_active = false WHERE language_id = v_lang AND is_active;

    INSERT INTO public.tests (id, gen_user, slug, difficulty, tier, title, language_id, is_active, vocab_sense_ids) VALUES
      (t_target, v_user, '__t748_target',  1, 'free-tier', 'target',     v_lang, true, s_target || s_null),
      (t_rare,   v_user, '__t748_rare',    1, 'free-tier', 'known_rare', v_lang, true, s_rare),
      (t_unlink, v_user, '__t748_unlink',  1, 'free-tier', 'unlinked',   v_lang, true, NULL),
      (t_easy,   v_user, '__t748_easy',    1, 'free-tier', 'easy',       v_lang, true, s_easy),
      (t_mid,    v_user, '__t748_mid',     1, 'free-tier', 'midhard',    v_lang, true, s_midhard),
      (t_hard,   v_user, '__t748_hard',    1, 'free-tier', 'hard',       v_lang, true, s_hard),
      (t_d9,     v_user, '__t748_d9',      9, 'free-tier', 'd9_twin',    v_lang, true, s_target);
    INSERT INTO public.test_skill_ratings (test_id, test_type_id, elo_rating)
    SELECT x, v_type, 1200 FROM unnest(ARRAY[t_target, t_rare, t_unlink, t_easy, t_mid, t_hard, t_d9]) x;

    -- Evidence that must beat the prior: rare words the learner does know.
    INSERT INTO public.user_vocabulary_knowledge (user_id, sense_id, language_id, p_known, status)
    SELECT v_user, x, v_lang, 0.95, 'known' FROM unnest(s_rare) x;

    INSERT INTO public.user_calibration_state (user_id, language_id, mode, ability_zipf, ability_se,
                                               items_answered, sessions_pooled, last_run_at)
    VALUES (v_user, v_lang, 'definition', 5.0, 0.2, 100, 1, now());

    -- ---- phase A: calibrated, vocab_weight 1 -------------------------------
    INSERT INTO _t748_rank
    SELECT 'A', x.title, x.rank_in_type, x.unknown_share, x.vocab_penalty, x.vocab_neutral,
           x.over_ceiling, x.n_senses, x.n_resolved, x.ability_source
      FROM public.recommended_tests_ranked(v_user, v_lang, 14::smallint, 1, NULL) x
     WHERE x.test_type = 'reading';

    SELECT array_agg(label ORDER BY rank_in_type) INTO v_order FROM _t748_rank WHERE phase = 'A';
    IF v_order IS DISTINCT FROM v_want THEN
        RAISE EXCEPTION 'FAIL order: got %, want %', v_order, v_want;
    END IF;

    PERFORM 1 FROM _t748_rank WHERE phase = 'A' AND ability_source <> 'calibration';
    IF FOUND THEN RAISE EXCEPTION 'FAIL: calibration row not used'; END IF;

    SELECT * INTO r FROM _t748_rank WHERE phase = 'A' AND label = 'target';
    IF abs(r.unknown_share - 0.15) > 0.02 THEN
        RAISE EXCEPTION 'FAIL: the prior is not 0.85 at ability_zipf (target unknown = %)', r.unknown_share;
    END IF;
    IF r.n_senses <> 11 OR r.n_resolved <> 10 THEN
        RAISE EXCEPTION 'FAIL: NULL-Zipf sense must leave the denominator (n_senses %, n_resolved %)',
            r.n_senses, r.n_resolved;
    END IF;

    SELECT * INTO r FROM _t748_rank WHERE phase = 'A' AND label = 'known_rare';
    IF abs(r.unknown_share - 0.05) > 0.001 THEN
        RAISE EXCEPTION 'FAIL: uvk p_known did not win over the prior (unknown = %)', r.unknown_share;
    END IF;

    SELECT * INTO r FROM _t748_rank WHERE phase = 'A' AND label = 'unlinked';
    IF NOT r.vocab_neutral OR r.n_senses IS NOT NULL THEN
        RAISE EXCEPTION 'FAIL: unlinked test not neutral';
    END IF;
    -- Tolerance: the function takes the median of raw penalties and rounds it;
    -- this recomputes it from the already-rounded (6 dp) outputs.
    IF abs(r.vocab_penalty - (SELECT percentile_cont(0.5) WITHIN GROUP (ORDER BY vocab_penalty)::numeric
                                FROM _t748_rank WHERE phase = 'A' AND NOT vocab_neutral)) > 0.00001 THEN
        RAISE EXCEPTION 'FAIL: unlinked penalty % is not the cohort median', r.vocab_penalty;
    END IF;

    SELECT * INTO r FROM _t748_rank WHERE phase = 'A' AND label = 'd9_twin';
    IF NOT r.over_ceiling THEN RAISE EXCEPTION 'FAIL: d9 twin not over the tier ceiling'; END IF;

    -- Pool health: the public RPC returns the same count at weight 1 and 0.
    UPDATE public.selection_tuning SET value = 1 WHERE key = 'vocab_weight';
    SELECT count(*) INTO v_n1 FROM public.get_recommended_tests(v_user, v_lang, 14::smallint);
    UPDATE public.selection_tuning SET value = 0 WHERE key = 'vocab_weight';
    SELECT count(*) INTO v_n0 FROM public.get_recommended_tests(v_user, v_lang, 14::smallint);
    IF v_n1 <> v_n0 OR v_n0 <> 7 THEN
        RAISE EXCEPTION 'FAIL pool health: % at weight 1 vs % at weight 0 (want 7)', v_n1, v_n0;
    END IF;

    -- ---- phase B: no calibration → no ceiling ------------------------------
    DELETE FROM public.user_calibration_state WHERE user_id = v_user;
    INSERT INTO _t748_rank
    SELECT 'B', x.title, x.rank_in_type, x.unknown_share, x.vocab_penalty, x.vocab_neutral,
           x.over_ceiling, x.n_senses, x.n_resolved, x.ability_source
      FROM public.recommended_tests_ranked(v_user, v_lang, 14::smallint, 1, NULL) x
     WHERE x.test_type = 'reading';
    -- The learner's only uvk rows are one band, all known: no crossing → 'none'.
    PERFORM 1 FROM _t748_rank WHERE phase = 'B' AND (ability_source <> 'none' OR over_ceiling OR NOT vocab_neutral);
    IF FOUND THEN
        RAISE EXCEPTION 'FAIL: without calibration or a crossing, every test must be neutral and none over a ceiling';
    END IF;

    -- A pronunciation row must NOT stand in for the missing definition row.
    INSERT INTO public.user_calibration_state (user_id, language_id, mode, ability_zipf, ability_se,
                                               items_answered, sessions_pooled, last_run_at)
    VALUES (v_user, v_lang, 'pronunciation', 5.0, 0.2, 100, 1, now());
    PERFORM 1 FROM public.selection_vocab_ability(v_user, v_lang) a WHERE a.ability_source <> 'none';
    IF FOUND THEN RAISE EXCEPTION 'FAIL: a pronunciation-mode row was read as vocabulary'; END IF;

    -- ---- phase C: an entirely unlinked pool keeps its count ----------------
    UPDATE public.tests SET vocab_sense_ids = NULL WHERE slug LIKE '__t748_%';
    UPDATE public.selection_tuning SET value = 1 WHERE key = 'vocab_weight';
    SELECT count(*) INTO v_n1 FROM public.get_recommended_tests(v_user, v_lang, 14::smallint);
    UPDATE public.selection_tuning SET value = 0 WHERE key = 'vocab_weight';
    IF v_n1 <> 7 THEN RAISE EXCEPTION 'FAIL: an all-unlinked pool returned % (want 7)', v_n1; END IF;

    RAISE NOTICE 'TASK-748 ranking PASS';
END $test$;

SELECT phase, rank_in_type, label, unknown_share, vocab_penalty, vocab_neutral,
       over_ceiling, n_senses, n_resolved, ability_source
  FROM _t748_rank ORDER BY phase, rank_in_type;

ROLLBACK;
