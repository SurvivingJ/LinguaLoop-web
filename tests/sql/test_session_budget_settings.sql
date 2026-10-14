-- =============================================================================
-- session-budget-settings — SQL tests (TASK-863 / 865 / 872 / 873 / 874)
-- =============================================================================
-- Rollback-only SQL test against the LIVE schema, same harness as
-- tests/sql/test_task705_same_day_safe.sql: assertions RAISE EXCEPTION, a clean run prints
-- PASS notices, everything is rolled back. Requires ALL session-budget migrations applied
-- (session_module_exclusions.sql, review_governor.sql,
--  session_module_exclusions_build_daily_session.sql, new_words_completed_accrual.sql,
--  calibration_bkt_evidence.sql):
--
--   psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f tests/sql/test_session_budget_settings.sql
--
-- WARNING: the fixtures DELETE the first users row's plan / weekly state / flashcards /
-- ladder rows / exercise_attempts for language 2 INSIDE the transaction (rolled back at the
-- end), exactly as test_task705_same_day_safe.sql does for its plan rows. Run against a
-- Supabase branch or a throwaway DB, not against production.
--
-- Fixture numbers (Monday date, flat shape, daily_minutes 30 => 30 min/day):
--   7 listening slots x 5 min = 35 test minutes, practice pool 21 min/week
--   => practice share B_p = 30 * 21 / (35 + 21) = 11.25 min.
--   18 due flashcards x 20 s (default item_seconds, < 20 timed samples) = 6.0 review min.
--   mpnw = 3.0 (dim_languages.new_word_minutes_est NULL).
--   Scenario A: reviews 6.0, floor((11.25 - 6.0) / 3.0) = 1 new word (3.0 min),
--               returned 11.25 - 6 - 3 = 2.25 min to tests => test budget 18.75 + 2.25 = 21.
-- =============================================================================

BEGIN;

-- ---- helpers (pg_temp: dropped at ROLLBACK) -------------------------------------------
CREATE FUNCTION pg_temp.sbs_fixture(
    p_user uuid, p_lang smallint, p_week date, p_npd int, p_shape jsonb,
    p_overdue int, p_due_today int, p_scope text, p_excluded text[] DEFAULT '{}'
) RETURNS void LANGUAGE plpgsql AS $f$
DECLARE v_tpl smallint; v_n int := p_overdue + p_due_today; v_i int := 0; r record;
BEGIN
  SELECT MIN(template_id) INTO v_tpl FROM public.dim_study_plan_templates;
  DELETE FROM public.daily_test_load_items WHERE load_id IN (
    SELECT id FROM public.daily_test_loads WHERE user_id=p_user AND language_id=p_lang AND load_date=p_week);
  DELETE FROM public.daily_test_loads   WHERE user_id=p_user AND language_id=p_lang AND load_date=p_week;
  DELETE FROM public.weekly_plan_states WHERE user_id=p_user AND language_id=p_lang AND week_start_date=p_week;
  DELETE FROM public.user_flashcards    WHERE user_id=p_user AND language_id=p_lang;
  DELETE FROM public.user_word_ladder   WHERE user_id=p_user
     AND sense_id IN (SELECT dws.id FROM public.dim_word_senses dws JOIN public.dim_vocabulary dv ON dv.id=dws.vocab_id WHERE dv.language_id=p_lang);
  DELETE FROM public.exercise_attempts  WHERE user_id=p_user;
  DELETE FROM public.user_study_plans   WHERE user_id=p_user AND language_id=p_lang;

  INSERT INTO public.user_study_plans(user_id, language_id, template_id, daily_minutes, weekday_shape,
                                      excluded_modules, budget_scope, new_words_per_day, timezone)
  VALUES (p_user, p_lang, v_tpl, 30, p_shape, p_excluded, p_scope, p_npd, 'UTC');

  IF p_scope = 'tests_only' THEN
    INSERT INTO public.weekly_plan_states(user_id, language_id, week_start_date, target_counts, skill_values,
        completed_counts, practice_target_minutes, maintenance_share, acquisition_share, total_weekly_minutes,
        budget_scope, review_target_minutes, new_words_target, acq_target_minutes)
    VALUES (p_user, p_lang, p_week, '{"listening":7}', '{"listening":0.5}', '{}', 0, 1.0, 0.0, 210,
        'tests_only', 14, 35, 0);
  ELSE
    INSERT INTO public.weekly_plan_states(user_id, language_id, week_start_date, target_counts, skill_values,
        completed_counts, practice_target_minutes, maintenance_share, acquisition_share, total_weekly_minutes,
        budget_scope, review_target_minutes, new_words_target, acq_target_minutes)
    VALUES (p_user, p_lang, p_week, '{"listening":7}', '{"listening":0.5}', '{}', 21, 0.67, 0.33, 210,
        'tests_and_review', 14, 35, 7);
  END IF;

  FOR r IN SELECT dws.id AS sense_id
             FROM public.dim_word_senses dws JOIN public.dim_vocabulary dv ON dv.id = dws.vocab_id
            WHERE dv.language_id = p_lang ORDER BY dws.id LIMIT v_n
  LOOP
    v_i := v_i + 1;
    INSERT INTO public.user_flashcards(user_id, sense_id, language_id, due_date)
    VALUES (p_user, r.sense_id, p_lang, CASE WHEN v_i <= p_overdue THEN p_week - 1 ELSE p_week END);
  END LOOP;
  IF v_i < v_n THEN RAISE EXCEPTION 'SETUP FAIL: only % senses available for language %', v_i, p_lang; END IF;
END $f$;

CREATE FUNCTION pg_temp.sbs_build(p_user uuid, p_lang smallint, p_date date, p_fresh boolean)
RETURNS jsonb LANGUAGE plpgsql AS $f$
BEGIN
  IF p_fresh THEN
    DELETE FROM public.daily_test_load_items WHERE load_id IN (
      SELECT id FROM public.daily_test_loads WHERE user_id=p_user AND language_id=p_lang AND load_date=p_date);
    DELETE FROM public.daily_test_loads WHERE user_id=p_user AND language_id=p_lang AND load_date=p_date;
  END IF;
  RETURN public.build_daily_session(p_user, p_lang, p_date);
END $f$;

CREATE FUNCTION pg_temp.sbs_targets(p_user uuid, p_lang smallint, p_date date)
RETURNS jsonb LANGUAGE sql AS $f$
  SELECT daily_session_targets FROM public.daily_test_loads
   WHERE user_id=p_user AND language_id=p_lang AND load_date=p_date $f$;

-- Review fix: ladder_new_word_state only counts servable words (>= 3 active exercises in the
-- language, mirroring LADDER_MIN_EXERCISES_PER_SENSE), so fixtures must give their words supply.
CREATE FUNCTION pg_temp.sbs_supply(p_lang smallint, p_sense int, p_n int DEFAULT 3) RETURNS void
LANGUAGE sql AS $f$
  INSERT INTO public.exercises(language_id, exercise_type, source_type, word_sense_id, content)
  SELECT p_lang, 'definition_match', 'vocabulary', p_sense, '{}'::jsonb FROM generate_series(1, p_n) $f$;

CREATE FUNCTION pg_temp.sbs_approx(a numeric, b numeric) RETURNS boolean LANGUAGE sql AS
  $f$ SELECT abs(a - b) < 0.001 $f$;

-- =============================================================================
-- Part 1 — Tier C: build_daily_session
-- =============================================================================
DO $test$
DECLARE
  v_user uuid; v_lang smallint := 2;
  v_week date := public.week_start_for(CURRENT_DATE);   -- a Monday: ISODOW 1 => weekday_shape[0]
  v_listen_t smallint := (SELECT id FROM public.dim_test_types WHERE type_code = 'listening');
  r jsonb; t jsonb; k text; v_n int; v_before int;
  v_keys text[] := ARRAY['budget_scope','new_words_quota','new_words_effective','new_words_in_budget',
      'new_words_shortfall','new_words_supply_checked','governor_level','review_due_minutes',
      'review_main_minutes','new_word_main_minutes','returned_to_tests_minutes','excluded_modules'];
BEGIN
  SELECT id INTO v_user FROM public.users LIMIT 1;
  IF v_user IS NULL THEN RAISE EXCEPTION 'no users row available to satisfy FKs'; END IF;
  UPDATE public.dim_languages SET new_word_minutes_est = NULL WHERE id = v_lang;   -- mpnw = 3.0

  -- Seven never-attempted listening tests so hydration can fill any slot count.
  INSERT INTO public.tests(id, gen_user, slug, difficulty, tier, title, language_id, is_active)
  SELECT gen_random_uuid(), v_user, '__sbs_l' || g, 1, 'free-tier', 'SBS L' || g, v_lang, true
    FROM generate_series(1, 7) g;
  INSERT INTO public.test_skill_ratings(test_id, test_type_id, elo_rating)
  SELECT id, v_listen_t, 1200 FROM public.tests WHERE slug LIKE '\_\_sbs\_l%' AND language_id = v_lang;

  -- ---------------------------------------------------------------- A: reviews first, new word, leftover to tests
  PERFORM pg_temp.sbs_fixture(v_user, v_lang, v_week, 5, '[1,1,1,1,1,1,1]', 9, 9, 'tests_and_review');
  r := pg_temp.sbs_build(v_user, v_lang, v_week, true);
  t := pg_temp.sbs_targets(v_user, v_lang, v_week);
  FOREACH k IN ARRAY v_keys LOOP
    IF NOT (t ? k) THEN RAISE EXCEPTION 'FAIL A: daily_session_targets lacks key %: %', k, t; END IF;
    IF NOT (r ? k) THEN RAISE EXCEPTION 'FAIL A: return value lacks key %: %', k, r; END IF;
  END LOOP;
  IF (r->>'practice_maintenance_min')::int <> 6 OR (r->>'practice_acquisition_min')::int <> 3 THEN
    RAISE EXCEPTION 'FAIL A: expected maint 6 / acq 3: %', r; END IF;
  IF (t->>'new_words_quota')::int <> 5 OR (t->>'new_words_effective')::int <> 5
     OR (t->>'new_words_in_budget')::int <> 1 OR t->>'governor_level' <> 'normal' THEN
    RAISE EXCEPTION 'FAIL A: quota/effective/in_budget/level: %', t; END IF;
  IF NOT pg_temp.sbs_approx((t->>'review_due_minutes')::numeric, 6.0)
     OR NOT pg_temp.sbs_approx((t->>'returned_to_tests_minutes')::numeric, 2.25)
     OR NOT pg_temp.sbs_approx((t->>'practice_budget_minutes')::numeric, 11.25)
     OR NOT pg_temp.sbs_approx((t->>'test_budget_minutes')::numeric, 21.0)
     OR NOT pg_temp.sbs_approx((t->>'today_budget_minutes')::numeric, 30.0) THEN
    RAISE EXCEPTION 'FAIL A: budget split: %', t; END IF;
  IF (t->>'new_words_supply_checked')::boolean IS DISTINCT FROM false THEN
    RAISE EXCEPTION 'FAIL A: supply flag should start false: %', t; END IF;
  SELECT COUNT(*) INTO v_n FROM jsonb_array_elements(r->'test_ids') e WHERE e->>'test_type' = 'listening';
  IF v_n <> 5 THEN RAISE EXCEPTION 'FAIL A: expected 5 listening slots in the enlarged 21-min test budget, got %', v_n; END IF;
  IF NOT pg_temp.sbs_approx((r->>'budgeted_minutes')::numeric, 25 + 6 + 3) THEN
    RAISE EXCEPTION 'FAIL A: budgeted_minutes should be 34: %', r->>'budgeted_minutes'; END IF;

  -- ---------------------------------------------------------------- B: tests_only => everything to tests
  PERFORM pg_temp.sbs_fixture(v_user, v_lang, v_week, 5, '[1,1,1,1,1,1,1]', 9, 9, 'tests_only');
  r := pg_temp.sbs_build(v_user, v_lang, v_week, true);
  t := pg_temp.sbs_targets(v_user, v_lang, v_week);
  IF (r->>'practice_maintenance_min')::int <> 0 OR (r->>'practice_acquisition_min')::int <> 0
     OR (t->>'new_words_in_budget')::int <> 0 OR (t->>'practice_budget_minutes')::numeric <> 0
     OR t->>'budget_scope' <> 'tests_only' OR (t->>'new_words_effective')::int <> 5
     OR NOT pg_temp.sbs_approx((t->>'test_budget_minutes')::numeric, 30.0) THEN
    RAISE EXCEPTION 'FAIL B: tests_only should put the whole day in tests, new words only effective (tail): %', t; END IF;

  -- ---------------------------------------------------------------- governor: normal control, reduced, paused
  -- npd = 1, 9 overdue + 9 due today => overdue 3.0 min <= T (3.0) => normal, E = 1, S = 1.
  PERFORM pg_temp.sbs_fixture(v_user, v_lang, v_week, 1, '[1,1,1,1,1,1,1]', 9, 9, 'tests_and_review');
  PERFORM pg_temp.sbs_build(v_user, v_lang, v_week, true);
  t := pg_temp.sbs_targets(v_user, v_lang, v_week);
  IF t->>'governor_level' <> 'normal' OR (t->>'new_words_effective')::int <> 1 OR (t->>'new_words_in_budget')::int <> 1
     OR NOT pg_temp.sbs_approx((t->>'returned_to_tests_minutes')::numeric, 2.25) THEN
    RAISE EXCEPTION 'FAIL governor control (normal): %', t; END IF;
  -- 18 overdue = 6.0 min = 2T => reduced; floor(1/2) = 0 new words; the share minutes go back to tests.
  PERFORM pg_temp.sbs_fixture(v_user, v_lang, v_week, 1, '[1,1,1,1,1,1,1]', 18, 0, 'tests_and_review');
  PERFORM pg_temp.sbs_build(v_user, v_lang, v_week, true);
  t := pg_temp.sbs_targets(v_user, v_lang, v_week);
  IF t->>'governor_level' <> 'reduced' OR (t->>'new_words_effective')::int <> 0 OR (t->>'new_words_in_budget')::int <> 0
     OR NOT pg_temp.sbs_approx((t->>'returned_to_tests_minutes')::numeric, 5.25)
     OR NOT pg_temp.sbs_approx((t->>'test_budget_minutes')::numeric, 24.0) THEN
    RAISE EXCEPTION 'FAIL governor reduced: %', t; END IF;
  -- 19 overdue = 6.33 min > 2T => paused: no new words at all.
  PERFORM pg_temp.sbs_fixture(v_user, v_lang, v_week, 5, '[1,1,1,1,1,1,1]', 19, 0, 'tests_and_review');
  PERFORM pg_temp.sbs_build(v_user, v_lang, v_week, true);
  t := pg_temp.sbs_targets(v_user, v_lang, v_week);
  IF t->>'governor_level' <> 'paused' OR (t->>'new_words_quota')::int <> 5 OR (t->>'new_words_effective')::int <> 0
     OR (t->>'new_words_in_budget')::int <> 0
     -- review_due_minutes is rounded to 2 decimals by review_governor_state (6.33), hence the loose bound
     OR abs((t->>'returned_to_tests_minutes')::numeric - (11.25 - 19 * 20 / 60.0)) > 0.01 THEN
    RAISE EXCEPTION 'FAIL governor paused: %', t; END IF;

  -- ---------------------------------------------------------------- weight-0 day => Q = 0
  PERFORM pg_temp.sbs_fixture(v_user, v_lang, v_week, 5, '[0,1,1,1,1,1,1]', 9, 9, 'tests_and_review');
  PERFORM pg_temp.sbs_build(v_user, v_lang, v_week, true);
  t := pg_temp.sbs_targets(v_user, v_lang, v_week);
  IF (t->>'new_words_quota')::int <> 0 OR (t->>'new_words_effective')::int <> 0 OR (t->>'new_words_in_budget')::int <> 0 THEN
    RAISE EXCEPTION 'FAIL weight-0 day: %', t; END IF;

  -- ---------------------------------------------------------------- practice excluded with new_words_per_day > 0
  PERFORM pg_temp.sbs_fixture(v_user, v_lang, v_week, 5, '[1,1,1,1,1,1,1]', 9, 9, 'tests_and_review', ARRAY['practice']);
  r := pg_temp.sbs_build(v_user, v_lang, v_week, true);
  t := pg_temp.sbs_targets(v_user, v_lang, v_week);
  IF (r->>'practice_maintenance_min')::int <> 0 OR (r->>'practice_acquisition_min')::int <> 0
     OR (t->>'practice_budget_minutes')::numeric <> 0 OR (t->>'new_words_in_budget')::int <> 0
     OR (t->>'new_words_effective')::int <> 5 OR t->'excluded_modules' <> '["practice"]'::jsonb THEN
    RAISE EXCEPTION 'FAIL practice excluded + npd>0 (all words go to the tail): %', t; END IF;

  -- ---------------------------------------------------------------- supply check / shortfall / TASK-705
  PERFORM pg_temp.sbs_fixture(v_user, v_lang, v_week, 5, '[1,1,1,1,1,1,1]', 9, 9, 'tests_and_review');
  PERFORM pg_temp.sbs_build(v_user, v_lang, v_week, true);
  UPDATE public.daily_test_loads SET completed_blocks = '["practice_maint_1"]'::jsonb
   WHERE user_id=v_user AND language_id=v_lang AND load_date=v_week;
  IF NOT public.set_new_words_shortfall(v_user, v_lang, v_week, 5, 5) THEN
    RAISE EXCEPTION 'FAIL: set_new_words_shortfall found no row'; END IF;
  t := pg_temp.sbs_targets(v_user, v_lang, v_week);
  IF (t->>'new_words_shortfall')::int <> 5 OR (t->>'new_words_supply_checked')::boolean IS NOT TRUE THEN
    RAISE EXCEPTION 'FAIL set_new_words_shortfall did not write both keys: %', t; END IF;
  -- same-day rebuild WITH the flag: E - shortfall = 0 words in budget, 5.25 min back to tests.
  PERFORM pg_temp.sbs_build(v_user, v_lang, v_week, false);
  t := pg_temp.sbs_targets(v_user, v_lang, v_week);
  IF (t->>'new_words_in_budget')::int <> 0 OR (t->>'new_words_shortfall')::int <> 5
     OR (t->>'new_words_supply_checked')::boolean IS NOT TRUE
     OR NOT pg_temp.sbs_approx((t->>'returned_to_tests_minutes')::numeric, 5.25)
     OR NOT pg_temp.sbs_approx((t->>'test_budget_minutes')::numeric, 24.0) THEN
    RAISE EXCEPTION 'FAIL rebuild with supply flag: %', t; END IF;
  IF (SELECT completed_blocks FROM public.daily_test_loads
       WHERE user_id=v_user AND language_id=v_lang AND load_date=v_week) <> '["practice_maint_1"]'::jsonb THEN
    RAISE EXCEPTION 'FAIL TASK-705: completed_blocks wiped by the rebuild'; END IF;
  -- same-day rebuild WITHOUT the flag: the prior shortfall is ignored.
  UPDATE public.daily_test_loads
     SET daily_session_targets = jsonb_set(daily_session_targets, '{new_words_supply_checked}', 'false'::jsonb)
   WHERE user_id=v_user AND language_id=v_lang AND load_date=v_week;
  PERFORM pg_temp.sbs_build(v_user, v_lang, v_week, false);
  t := pg_temp.sbs_targets(v_user, v_lang, v_week);
  IF (t->>'new_words_in_budget')::int <> 1 OR (t->>'new_words_supply_checked')::boolean IS NOT FALSE THEN
    RAISE EXCEPTION 'FAIL rebuild without supply flag should ignore the prior shortfall: %', t; END IF;

  -- ---------------------------------------------------------------- lowering npd never un-admits
  INSERT INTO public.user_word_ladder(user_id, sense_id)
  SELECT v_user, dws.id FROM public.dim_word_senses dws JOIN public.dim_vocabulary dv ON dv.id = dws.vocab_id
   WHERE dv.language_id = v_lang ORDER BY dws.id DESC LIMIT 3;
  PERFORM pg_temp.sbs_supply(v_lang, ladder.sense_id) FROM public.user_word_ladder ladder WHERE ladder.user_id = v_user;
  SELECT COUNT(*) INTO v_before FROM public.user_word_ladder WHERE user_id = v_user;
  UPDATE public.user_study_plans SET new_words_per_day = 1 WHERE user_id=v_user AND language_id=v_lang;
  PERFORM pg_temp.sbs_build(v_user, v_lang, v_week, false);
  SELECT COUNT(*) INTO v_n FROM public.user_word_ladder WHERE user_id = v_user;
  IF v_n <> v_before THEN RAISE EXCEPTION 'FAIL: rebuild changed user_word_ladder (% -> %)', v_before, v_n; END IF;
  t := pg_temp.sbs_targets(v_user, v_lang, v_week);
  IF (t->>'new_words_shortfall')::int <> 0 THEN
    RAISE EXCEPTION 'FAIL: 3 unstarted admitted words already cover E=1, shortfall must be 0: %', t; END IF;

  RAISE NOTICE 'session-budget Tier C PASS (A, tests_only, governor, weight-0, practice excluded, supply flag, no un-admit)';
END $test$;

-- =============================================================================
-- Part 2 — persist, CHECKs, accrual, governor state, ladder state, helpers
-- =============================================================================
DO $test$
DECLARE
  v_user uuid; v_lang smallint := 2; v_tpl smallint;
  v_cur date; v_day_start timestamptz; v_ls timestamptz; v_row jsonb; w public.weekly_plan_states%ROWTYPE;
  s1 int; s2 int; s3 int; s4 int; s5 int; s6 int; s7 int;
  a1 uuid := gen_random_uuid(); a2 uuid := gen_random_uuid(); a3 uuid := gen_random_uuid();
  a4 uuid := gen_random_uuid(); a5 uuid := gen_random_uuid(); a6 uuid := gen_random_uuid();
  gs jsonb; p numeric; c boolean; ok boolean;
BEGIN
  SELECT id INTO v_user FROM public.users LIMIT 1;
  SELECT MIN(template_id) INTO v_tpl FROM public.dim_study_plan_templates;
  DELETE FROM public.weekly_plan_states WHERE user_id=v_user AND language_id=v_lang;
  DELETE FROM public.user_flashcards    WHERE user_id=v_user AND language_id=v_lang;
  DELETE FROM public.user_word_ladder   WHERE user_id=v_user;
  DELETE FROM public.exercise_attempts  WHERE user_id=v_user;
  DELETE FROM public.user_study_plans   WHERE user_id=v_user AND language_id=v_lang;
  INSERT INTO public.user_study_plans(user_id, language_id, template_id, daily_minutes, weekday_shape, timezone)
  VALUES (v_user, v_lang, v_tpl, 30, '[1,1,1,1,1,1,1]', 'Asia/Tokyo');

  v_cur       := public.plan_local_date(v_user, v_lang);
  v_day_start := public.plan_local_day_start(v_user, v_lang);
  IF v_day_start IS DISTINCT FROM (v_cur::timestamp AT TIME ZONE 'Asia/Tokyo') THEN
    RAISE EXCEPTION 'FAIL plan_local_day_start: % vs local date %', v_day_start, v_cur; END IF;

  -- ---------------------------------------------------------------- pure helpers
  IF public.new_words_for_day(5, 1.1) <> 6 OR public.new_words_for_day(1, 0.5) <> 1
     OR public.new_words_for_day(5, 0) <> 0 OR public.new_words_for_day(0, 1) <> 0
     OR public.new_words_for_day(5, 1.0) <> 5 OR public.new_words_for_day(5, 1.4) <> 7 THEN
    RAISE EXCEPTION 'FAIL new_words_for_day grid'; END IF;
  IF public.review_governor_level(3, 3) <> 'normal' OR public.review_governor_level(3.01, 3) <> 'reduced'
     OR public.review_governor_level(6, 3) <> 'reduced' OR public.review_governor_level(6.01, 3) <> 'paused'
     OR public.review_governor_level(5, 0) <> 'normal' THEN
    RAISE EXCEPTION 'FAIL review_governor_level boundaries'; END IF;
  IF public.new_words_effective(5, 'reduced') <> 2 OR public.new_words_effective(1, 'reduced') <> 0
     OR public.new_words_effective(5, 'paused') <> 0 OR public.new_words_effective(5, 'normal') <> 5 THEN
    RAISE EXCEPTION 'FAIL new_words_effective'; END IF;
  UPDATE public.dim_languages SET new_word_minutes_est = NULL WHERE id = v_lang;
  IF public.new_word_minutes(v_lang) <> 3.0 THEN RAISE EXCEPTION 'FAIL new_word_minutes default'; END IF;
  UPDATE public.dim_languages SET new_word_minutes_est = 4.25 WHERE id = v_lang;
  IF public.new_word_minutes(v_lang) <> 4.25 THEN RAISE EXCEPTION 'FAIL new_word_minutes stored'; END IF;
  UPDATE public.dim_languages SET new_word_minutes_est = NULL WHERE id = v_lang;

  -- ---------------------------------------------------------------- bkt: calibration is numerically a definition_match
  FOREACH p IN ARRAY ARRAY[0.02, 0.10, 0.30, 0.50, 0.70, 0.95]::numeric[] LOOP
    FOREACH c IN ARRAY ARRAY[true, false] LOOP
      IF public.bkt_update_exercise(p, c, 'definition_match') IS DISTINCT FROM public.bkt_update_word_test(p, c) THEN
        RAISE EXCEPTION 'FAIL bkt equality at p=% correct=%: batch RPC would diverge from definition_match', p, c;
      END IF;
    END LOOP;
  END LOOP;

  -- ---------------------------------------------------------------- calibration marker column
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                  WHERE table_schema='public' AND table_name='calibration_sessions' AND column_name='bkt_applied_at') THEN
    RAISE EXCEPTION 'FAIL: calibration_sessions.bkt_applied_at missing'; END IF;

  -- ---------------------------------------------------------------- compute_weekly_plan_persist
  -- old six-key payload still persists; new columns take their defaults.
  v_row := public.compute_weekly_plan_persist(v_user, v_lang, public.week_start_for(v_cur),
      '{"target_counts":{"listening":2},"skill_values":{"listening":0.5},"practice_target_minutes":20,
        "maintenance_share":0.40,"acquisition_share":0.60,"total_weekly_minutes":100}'::jsonb);
  IF v_row->>'budget_scope' <> 'tests_and_review' OR (v_row->>'review_target_minutes')::int <> 0
     OR (v_row->>'new_words_completed')::int <> 0 THEN
    RAISE EXCEPTION 'FAIL persist (old payload): %', v_row; END IF;
  -- the four new keys are written; the three accrual counters are never overwritten.
  UPDATE public.weekly_plan_states
     SET new_words_completed = 7, tail_completed_min = 5, tail_new_words_completed = 3
   WHERE user_id=v_user AND language_id=v_lang AND week_start_date = public.week_start_for(v_cur);
  v_row := public.compute_weekly_plan_persist(v_user, v_lang, public.week_start_for(v_cur),
      '{"target_counts":{"listening":2},"skill_values":{"listening":0.5},"practice_target_minutes":20,
        "maintenance_share":1.00,"acquisition_share":0.00,"total_weekly_minutes":100,
        "budget_scope":"tests_only","review_target_minutes":12,"new_words_target":35,"acq_target_minutes":0}'::jsonb);
  IF v_row->>'budget_scope' <> 'tests_only' OR (v_row->>'review_target_minutes')::int <> 12
     OR (v_row->>'new_words_target')::int <> 35 OR (v_row->>'acq_target_minutes')::int <> 0 THEN
    RAISE EXCEPTION 'FAIL persist (new keys): %', v_row; END IF;
  IF (v_row->>'new_words_completed')::int <> 7 OR (v_row->>'tail_completed_min')::int <> 5
     OR (v_row->>'tail_new_words_completed')::int <> 3 THEN
    RAISE EXCEPTION 'FAIL persist overwrote an accrual counter: %', v_row; END IF;

  -- ---------------------------------------------------------------- relaxed shares CHECK
  UPDATE public.weekly_plan_states SET maintenance_share = 1.00, acquisition_share = 0.00
   WHERE user_id=v_user AND language_id=v_lang;
  UPDATE public.weekly_plan_states SET maintenance_share = 0.30, acquisition_share = 0.70
   WHERE user_id=v_user AND language_id=v_lang;
  ok := false;
  BEGIN
    UPDATE public.weekly_plan_states SET maintenance_share = 0.60, acquisition_share = 0.60
     WHERE user_id=v_user AND language_id=v_lang;
  EXCEPTION WHEN check_violation THEN ok := true; END;
  IF NOT ok THEN RAISE EXCEPTION 'FAIL: shares 0.6 / 0.6 must be rejected'; END IF;
  ok := false;
  BEGIN
    UPDATE public.user_study_plans SET new_words_per_day = 51 WHERE user_id=v_user AND language_id=v_lang;
  EXCEPTION WHEN check_violation THEN ok := true; END;
  IF NOT ok THEN RAISE EXCEPTION 'FAIL: new_words_per_day 51 must be rejected'; END IF;
  ok := false;
  BEGIN
    UPDATE public.user_study_plans SET budget_scope = 'everything' WHERE user_id=v_user AND language_id=v_lang;
  EXCEPTION WHEN check_violation THEN ok := true; END;
  IF NOT ok THEN RAISE EXCEPTION 'FAIL: unknown budget_scope must be rejected'; END IF;

  -- ---------------------------------------------------------------- ladder_new_word_state + record_session_progress
  SELECT dws.id INTO s1 FROM public.dim_word_senses dws JOIN public.dim_vocabulary dv ON dv.id = dws.vocab_id
   WHERE dv.language_id = v_lang ORDER BY dws.id OFFSET 0 LIMIT 1;
  SELECT dws.id INTO s2 FROM public.dim_word_senses dws JOIN public.dim_vocabulary dv ON dv.id = dws.vocab_id
   WHERE dv.language_id = v_lang ORDER BY dws.id OFFSET 1 LIMIT 1;
  SELECT dws.id INTO s3 FROM public.dim_word_senses dws JOIN public.dim_vocabulary dv ON dv.id = dws.vocab_id
   WHERE dv.language_id = v_lang ORDER BY dws.id OFFSET 2 LIMIT 1;
  IF s3 IS NULL THEN RAISE EXCEPTION 'SETUP FAIL: need 3 senses in language %', v_lang; END IF;

  PERFORM pg_temp.sbs_supply(v_lang, s1); PERFORM pg_temp.sbs_supply(v_lang, s2); PERFORM pg_temp.sbs_supply(v_lang, s3);
  INSERT INTO public.user_word_ladder(user_id, sense_id, created_at) VALUES
    (v_user, s1, now() - interval '5 days'),     -- admitted long ago, never attempted
    (v_user, s2, now() - interval '2 days'),     -- first attempt falls before today's local midnight
    (v_user, s3, now() - interval '1 hour');     -- admitted just now
  INSERT INTO public.exercise_attempts(user_id, sense_id, is_correct, created_at)
  VALUES (v_user, s2, true, v_day_start - interval '1 hour');

  gs := public.ladder_new_word_state(v_user, v_lang, v_day_start);
  IF (gs->>'unstarted')::int <> 2 OR (gs->>'started_today')::int <> 0
     OR gs->'unstarted_sense_ids' <> jsonb_build_array(s1, s3) THEN
    RAISE EXCEPTION 'FAIL ladder_new_word_state (no attempt today; oldest admission first): %', gs; END IF;

  -- s1: first-ever attempt today, admitted days ago => counts.
  INSERT INTO public.exercise_attempts(user_id, sense_id, is_correct, created_at) VALUES (v_user, s1, true, now());
  -- clean slate for the counters the persist test dirtied
  UPDATE public.weekly_plan_states SET new_words_completed = 0, tail_completed_min = 0, tail_new_words_completed = 0,
         practice_completed_acq_sec = 0, practice_completed_acq_min = 0, practice_completed_maint_sec = 0,
         practice_completed_maint_min = 0, session_progress_log = '{}'::jsonb
   WHERE user_id=v_user AND language_id=v_lang AND week_start_date = public.week_start_for(v_cur);
  ok := public.record_session_progress(v_user, v_lang, a1, 'practice_acq', NULL, 0, 0, 90, s1, false);
  SELECT * INTO w FROM public.weekly_plan_states
   WHERE user_id=v_user AND language_id=v_lang AND week_start_date = public.week_start_for(v_cur);
  IF NOT ok OR w.new_words_completed <> 1 OR w.tail_new_words_completed <> 0 OR w.tail_completed_min <> 0
     OR NOT (w.session_progress_log -> 'new_words' ? s1::text) THEN
    RAISE EXCEPTION 'FAIL accrual first attempt (ok=%): new=% tailnew=% tailmin=% log=%',
      ok, w.new_words_completed, w.tail_new_words_completed, w.tail_completed_min, w.session_progress_log; END IF;

  -- second attempt on the same sense: credited as practice, NOT counted as a new word again.
  INSERT INTO public.exercise_attempts(user_id, sense_id, is_correct, created_at) VALUES (v_user, s1, true, now());
  ok := public.record_session_progress(v_user, v_lang, a2, 'practice_acq', NULL, 0, 0, 0, s1, false);
  SELECT * INTO w FROM public.weekly_plan_states
   WHERE user_id=v_user AND language_id=v_lang AND week_start_date = public.week_start_for(v_cur);
  IF w.new_words_completed <> 1 THEN RAISE EXCEPTION 'FAIL accrual: second attempt double-counted (%)', w.new_words_completed; END IF;

  -- retried attempt (same p_attempt_id): no-op.
  ok := public.record_session_progress(v_user, v_lang, a1, 'practice_acq', NULL, 0, 0, 90, s1, false);
  SELECT * INTO w FROM public.weekly_plan_states
   WHERE user_id=v_user AND language_id=v_lang AND week_start_date = public.week_start_for(v_cur);
  IF ok OR w.new_words_completed <> 1 OR w.practice_completed_acq_sec <> 90 THEN
    RAISE EXCEPTION 'FAIL accrual: retried attempt not a no-op (ok=% new=% sec=%)', ok, w.new_words_completed, w.practice_completed_acq_sec; END IF;

  -- s2: first-ever attempt was BEFORE today's local midnight => not a new word today.
  INSERT INTO public.exercise_attempts(user_id, sense_id, is_correct, created_at) VALUES (v_user, s2, true, now());
  ok := public.record_session_progress(v_user, v_lang, a3, 'practice_acq', NULL, 0, 0, 0, s2, false);
  SELECT * INTO w FROM public.weekly_plan_states
   WHERE user_id=v_user AND language_id=v_lang AND week_start_date = public.week_start_for(v_cur);
  IF w.new_words_completed <> 1 THEN RAISE EXCEPTION 'FAIL accrual: sense first attempted yesterday was counted (%)', w.new_words_completed; END IF;

  -- s3 in the TAIL: counts as a new word + tail words; tail minutes = change of the rounded acq minutes (2 -> 4).
  INSERT INTO public.exercise_attempts(user_id, sense_id, is_correct, created_at) VALUES (v_user, s3, true, now());
  ok := public.record_session_progress(v_user, v_lang, a4, 'practice_acq', NULL, 0, 0, 120, s3, true);
  SELECT * INTO w FROM public.weekly_plan_states
   WHERE user_id=v_user AND language_id=v_lang AND week_start_date = public.week_start_for(v_cur);
  IF w.new_words_completed <> 2 OR w.tail_new_words_completed <> 1 OR w.practice_completed_acq_min <> 4
     OR w.tail_completed_min <> 2 THEN
    RAISE EXCEPTION 'FAIL accrual tail: new=% tailnew=% acq_min=% tail_min=%',
      w.new_words_completed, w.tail_new_words_completed, w.practice_completed_acq_min, w.tail_completed_min; END IF;

  -- practice_maint never counts words (even with a sense id) but tail minutes still accrue (10 min).
  ok := public.record_session_progress(v_user, v_lang, a5, 'practice_maint', NULL, 0, 0, 600, s1, true);
  -- acq without a sense id: minutes only.
  ok := public.record_session_progress(v_user, v_lang, a6, 'practice_acq', NULL, 0, 0, 0, NULL, false);
  SELECT * INTO w FROM public.weekly_plan_states
   WHERE user_id=v_user AND language_id=v_lang AND week_start_date = public.week_start_for(v_cur);
  IF w.new_words_completed <> 2 OR w.tail_completed_min <> 12 OR w.practice_completed_maint_min <> 10 THEN
    RAISE EXCEPTION 'FAIL accrual maint/no-sense: new=% tail_min=% maint_min=%',
      w.new_words_completed, w.tail_completed_min, w.practice_completed_maint_min; END IF;

  -- ladder state after the attempts: s1 + s3 started today, s2 started yesterday, nothing unstarted.
  gs := public.ladder_new_word_state(v_user, v_lang, v_day_start);
  IF (gs->>'unstarted')::int <> 0 OR (gs->>'started_today')::int <> 2 OR gs->'unstarted_sense_ids' <> '[]'::jsonb THEN
    RAISE EXCEPTION 'FAIL ladder_new_word_state (after attempts; retries do not change it): %', gs; END IF;

  -- ---------------------------------------------------------------- review_governor_state
  DELETE FROM public.user_word_ladder WHERE user_id = v_user;
  DELETE FROM public.exercise_attempts WHERE user_id = v_user;
  DELETE FROM public.weekly_plan_states WHERE user_id=v_user AND language_id=v_lang;
  SELECT dws.id INTO s4 FROM public.dim_word_senses dws JOIN public.dim_vocabulary dv ON dv.id = dws.vocab_id WHERE dv.language_id = v_lang ORDER BY dws.id OFFSET 3 LIMIT 1;
  SELECT dws.id INTO s5 FROM public.dim_word_senses dws JOIN public.dim_vocabulary dv ON dv.id = dws.vocab_id WHERE dv.language_id = v_lang ORDER BY dws.id OFFSET 4 LIMIT 1;
  SELECT dws.id INTO s6 FROM public.dim_word_senses dws JOIN public.dim_vocabulary dv ON dv.id = dws.vocab_id WHERE dv.language_id = v_lang ORDER BY dws.id OFFSET 5 LIMIT 1;
  SELECT dws.id INTO s7 FROM public.dim_word_senses dws JOIN public.dim_vocabulary dv ON dv.id = dws.vocab_id WHERE dv.language_id = v_lang ORDER BY dws.id OFFSET 6 LIMIT 1;
  IF s7 IS NULL THEN RAISE EXCEPTION 'SETUP FAIL: need 7 senses in language %', v_lang; END IF;
  v_ls := v_cur::timestamp AT TIME ZONE 'Asia/Tokyo';
  -- s1: flashcard overdue AND ladder overdue (counts once); s2: flashcard due today; s3: ladder due today (3h after midnight);
  -- s4: ladder due tomorrow (not counted); s5: flashcard due tomorrow (not counted); s6: ladder mastered (NULL, not counted).
  INSERT INTO public.user_flashcards(user_id, sense_id, language_id, due_date) VALUES
    (v_user, s1, v_lang, v_cur - 1), (v_user, s2, v_lang, v_cur), (v_user, s5, v_lang, v_cur + 1);
  INSERT INTO public.user_word_ladder(user_id, sense_id, review_due_at) VALUES
    (v_user, s1, v_ls - interval '2 hours'), (v_user, s3, v_ls + interval '3 hours'),
    (v_user, s4, v_ls + interval '1 day 3 hours'), (v_user, s6, NULL);
  gs := public.review_governor_state(v_user, v_lang, v_cur);
  IF (gs->>'overdue_items')::int <> 1 OR (gs->>'due_items')::int <> 3 OR gs->>'level' <> 'normal'
     OR NOT pg_temp.sbs_approx((gs->>'threshold_minutes')::numeric, 3.0)
     OR NOT pg_temp.sbs_approx((gs->>'item_seconds')::numeric, 20.0)
     OR abs((gs->>'overdue_minutes')::numeric - 1 * 20 / 60.0) > 0.01 THEN   -- rounded to 2 decimals
    RAISE EXCEPTION 'FAIL review_governor_state (once per sense across both sources, floor threshold): %', gs; END IF;
  -- threshold follows the weekly review target: 70 / 7 = 10 minutes.
  INSERT INTO public.weekly_plan_states(user_id, language_id, week_start_date, target_counts, skill_values,
      completed_counts, practice_target_minutes, maintenance_share, acquisition_share, total_weekly_minutes,
      review_target_minutes)
  VALUES (v_user, v_lang, public.week_start_for(v_cur), '{}', '{}', '{}', 70, 1.0, 0.0, 70, 70);
  gs := public.review_governor_state(v_user, v_lang, v_cur);
  IF NOT pg_temp.sbs_approx((gs->>'threshold_minutes')::numeric, 10.0) THEN
    RAISE EXCEPTION 'FAIL review_governor_state threshold from weekly review target: %', gs; END IF;
  -- practice excluded: normal, all zero.
  UPDATE public.user_study_plans SET excluded_modules = ARRAY['practice'] WHERE user_id=v_user AND language_id=v_lang;
  gs := public.review_governor_state(v_user, v_lang, v_cur);
  IF gs->>'level' <> 'normal' OR (gs->>'overdue_items')::int <> 0 OR (gs->>'due_items')::int <> 0
     OR (gs->>'threshold_minutes')::numeric <> 0 THEN
    RAISE EXCEPTION 'FAIL review_governor_state with practice excluded: %', gs; END IF;

  -- compute_weekly_plan_load_signals: prior_week is the whole weekly_plan_states row, so it carries
  -- review_target_minutes (Tier B reads it for the review carry-over).
  DELETE FROM public.weekly_plan_states WHERE user_id=v_user AND language_id=v_lang;
  INSERT INTO public.weekly_plan_states(user_id, language_id, week_start_date, target_counts, skill_values,
      completed_counts, practice_target_minutes, maintenance_share, acquisition_share, total_weekly_minutes,
      review_target_minutes)
  VALUES (v_user, v_lang, public.week_start_for(v_cur) - 7, '{}', '{}', '{}', 40, 1.0, 0.0, 40, 33);
  gs := public.compute_weekly_plan_load_signals(v_user, v_lang, public.week_start_for(v_cur));
  IF (gs->'prior_week'->>'review_target_minutes')::int IS DISTINCT FROM 33 THEN
    RAISE EXCEPTION 'FAIL load_signals prior_week lacks review_target_minutes: %', gs->'prior_week'; END IF;

  RAISE NOTICE 'session-budget helpers PASS (persist, CHECKs, accrual, ladder state, governor, bkt equality)';
END $test$;

-- =============================================================================
-- Part 3 — review fixes: ladder_new_word_state definition, grants, same-day rebuild,
--          stale supply flag, numeric rounding parity
-- =============================================================================
DO $test$
DECLARE
  v_user uuid; v_lang smallint := 2;
  v_week date := public.week_start_for(CURRENT_DATE);
  v_day_start timestamptz := v_week::timestamp AT TIME ZONE 'UTC';
  s int[]; gs jsonb; t jsonb; ex uuid;
BEGIN
  SELECT id INTO v_user FROM public.users LIMIT 1;
  SELECT array_agg(id ORDER BY id) INTO s FROM (
    SELECT dws.id FROM public.dim_word_senses dws JOIN public.dim_vocabulary dv ON dv.id = dws.vocab_id
     WHERE dv.language_id = v_lang
       AND NOT EXISTS (SELECT 1 FROM public.exercises e WHERE e.word_sense_id = dws.id)   -- fixtures own the supply
     ORDER BY dws.id LIMIT 8) q;
  IF array_length(s, 1) < 8 THEN RAISE EXCEPTION 'SETUP FAIL: need 8 senses in language %', v_lang; END IF;

  -- ---------------------------------------------------------------- ladder_new_word_state: what counts as "unstarted"
  PERFORM pg_temp.sbs_fixture(v_user, v_lang, v_week, 5, '[1,1,1,1,1,1,1]', 0, 0, 'tests_and_review');
  INSERT INTO public.user_word_ladder(user_id, sense_id, word_state, created_at) VALUES
    (v_user, s[1], 'new',      now() - interval '2 days'),    -- counts: servable, never attempted
    (v_user, s[2], 'active',   now() - interval '1 day'),     -- counts
    (v_user, s[3], 'mastered', now() - interval '3 days'),    -- NOT: mastered row is not an unstarted new word
    (v_user, s[4], 'new',      now() - interval '1 day'),     -- NOT: only 2 active exercises (unservable)
    (v_user, s[5], 'new',      now() - interval '1 day'),     -- NOT: legacy attempt (sense_id NULL) via exercise_id
    (v_user, s[6], 'new',      now() - interval '20 days'),   -- NOT: admitted > 14 days ago, abandoned
    (v_user, s[7], 'new',      now() - interval '1 day');     -- NOT: its 3 exercises are inactive
  PERFORM pg_temp.sbs_supply(v_lang, s[1]); PERFORM pg_temp.sbs_supply(v_lang, s[2]); PERFORM pg_temp.sbs_supply(v_lang, s[3]);
  PERFORM pg_temp.sbs_supply(v_lang, s[4], 2);
  PERFORM pg_temp.sbs_supply(v_lang, s[5]); PERFORM pg_temp.sbs_supply(v_lang, s[6]);
  PERFORM pg_temp.sbs_supply(v_lang, s[7]);
  UPDATE public.exercises SET is_active = false WHERE word_sense_id = s[7];
  SELECT id INTO ex FROM public.exercises WHERE word_sense_id = s[5] LIMIT 1;
  INSERT INTO public.exercise_attempts(user_id, exercise_id, sense_id, is_correct, created_at)
  VALUES (v_user, ex, NULL, true, v_day_start + interval '1 minute');     -- legacy attempt, started today
  gs := public.ladder_new_word_state(v_user, v_lang, v_day_start);
  IF (gs->>'unstarted')::int <> 2 OR gs->'unstarted_sense_ids' <> jsonb_build_array(s[1], s[2])
     OR (gs->>'started_today')::int <> 1 THEN
    RAISE EXCEPTION 'FAIL ladder_new_word_state definition (want U=2 [s1,s2], ST=1 via legacy attempt): %', gs; END IF;

  -- ---------------------------------------------------------------- grants: backend-only SECURITY DEFINER functions
    IF has_function_privilege('anon', 'public.record_session_progress(uuid,smallint,uuid,text,text,integer,integer,integer,bigint,boolean)', 'EXECUTE')
       OR has_function_privilege('authenticated', 'public.record_session_progress(uuid,smallint,uuid,text,text,integer,integer,integer,bigint,boolean)', 'EXECUTE')
       OR NOT has_function_privilege('service_role', 'public.record_session_progress(uuid,smallint,uuid,text,text,integer,integer,integer,bigint,boolean)', 'EXECUTE') THEN
      RAISE EXCEPTION 'FAIL grants: record_session_progress (10-arg) must be service_role only'; END IF;
    IF has_function_privilege('anon', 'public.plan_local_day_start(uuid,smallint)', 'EXECUTE')
       OR has_function_privilege('authenticated', 'public.plan_local_day_start(uuid,smallint)', 'EXECUTE')
       OR NOT has_function_privilege('service_role', 'public.plan_local_day_start(uuid,smallint)', 'EXECUTE') THEN
      RAISE EXCEPTION 'FAIL grants: plan_local_day_start must be service_role only'; END IF;
    IF has_function_privilege('authenticated', 'public.set_new_words_shortfall(uuid,smallint,date,integer,integer)', 'EXECUTE')
       OR has_function_privilege('authenticated', 'public.ladder_new_word_state(uuid,smallint,timestamptz)', 'EXECUTE') THEN
      RAISE EXCEPTION 'FAIL grants: set_new_words_shortfall / ladder_new_word_state must be service_role only'; END IF;

  -- ---------------------------------------------------------------- numeric rounding parity (Python == SQL)
  IF public.new_words_for_day(25, 0.58) <> 15 OR public.new_words_for_day(5, 0.5) <> 3 THEN
    RAISE EXCEPTION 'FAIL new_words_for_day(25, 0.58) must be 15 (exact numeric)'; END IF;

  -- ---------------------------------------------------------------- same-day rebuild does not re-plan words already started
  -- npd 3, nothing due: practice share 11.25 min = 3 words of 3.0 min, so S = 3 on a fresh day.
  DELETE FROM public.exercise_attempts WHERE user_id = v_user;
  DELETE FROM public.user_word_ladder  WHERE user_id = v_user;
  PERFORM pg_temp.sbs_fixture(v_user, v_lang, v_week, 3, '[1,1,1,1,1,1,1]', 0, 0, 'tests_and_review');
  PERFORM pg_temp.sbs_build(v_user, v_lang, v_week, true);
  t := pg_temp.sbs_targets(v_user, v_lang, v_week);
  IF (t->>'new_words_in_budget')::int <> 3 THEN RAISE EXCEPTION 'FAIL rebuild setup: S should be 3: %', t; END IF;
  -- two of today's words get started
  INSERT INTO public.user_word_ladder(user_id, sense_id, word_state) VALUES (v_user, s[1], 'new'), (v_user, s[2], 'new');
  INSERT INTO public.exercise_attempts(user_id, sense_id, is_correct, created_at)
  VALUES (v_user, s[1], true, now()), (v_user, s[2], true, now());
  PERFORM pg_temp.sbs_build(v_user, v_lang, v_week, false);
  t := pg_temp.sbs_targets(v_user, v_lang, v_week);
  IF (t->>'new_words_in_budget')::int <> 1 OR (t->>'new_word_main_minutes')::numeric <> 3 THEN
    RAISE EXCEPTION 'FAIL same-day rebuild re-planned started words (E=3, ST=2 => S=1): %', t; END IF;

  -- ---------------------------------------------------------------- stale supply flag after a mid-day quota change
  DELETE FROM public.exercise_attempts WHERE user_id = v_user;
  DELETE FROM public.user_word_ladder  WHERE user_id = v_user;
  UPDATE public.user_study_plans SET new_words_per_day = 5 WHERE user_id = v_user AND language_id = v_lang;
  PERFORM pg_temp.sbs_build(v_user, v_lang, v_week, true);
  PERFORM public.set_new_words_shortfall(v_user, v_lang, v_week, 4, 5);          -- checked under E=5: only 1 servable
  PERFORM pg_temp.sbs_build(v_user, v_lang, v_week, false);
  t := pg_temp.sbs_targets(v_user, v_lang, v_week);
  IF (t->>'new_words_in_budget')::int <> 1 OR (t->>'new_words_supply_checked')::boolean IS NOT TRUE
     OR (t->>'new_words_supply_checked_e')::int <> 5 THEN
    RAISE EXCEPTION 'FAIL same-E rebuild must keep the supply check (S=1, checked, e=5): %', t; END IF;
  UPDATE public.user_study_plans SET new_words_per_day = 4 WHERE user_id = v_user AND language_id = v_lang;   -- E: 5 -> 4
  PERFORM pg_temp.sbs_build(v_user, v_lang, v_week, false);
  t := pg_temp.sbs_targets(v_user, v_lang, v_week);
  IF (t->>'new_words_supply_checked')::boolean IS NOT FALSE OR (t->>'new_words_shortfall')::int <> 4
     OR (t->>'new_words_in_budget')::int <> 3 THEN
    RAISE EXCEPTION 'FAIL stale supply check after E changed must be discarded (unchecked, seed shortfall 4, S=3): %', t; END IF;

  RAISE NOTICE 'session-budget review fixes PASS (ladder state, grants, rounding, same-day rebuild, stale supply flag)';
END $test$;

ROLLBACK;
