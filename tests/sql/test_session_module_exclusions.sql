-- =============================================================================
-- TASK-865 / session-modules — build_daily_session honours user_study_plans.excluded_modules
-- =============================================================================
-- Rollback-only SQL test against the LIVE schema (same harness as
-- tests/sql/test_task705_same_day_safe.sql: assertions RAISE EXCEPTION, a clean run prints
-- the PASS NOTICE, then ROLLBACK). Requires migrations/session_module_exclusions.sql,
-- review_governor.sql and session_module_exclusions_build_daily_session.sql applied:
--
--   psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f tests/sql/test_session_module_exclusions.sql
--
-- Cases (see wiki/tasklist/session-modules.tasks.md TASK-865):
--   (a) an excluded test skill is absent from test_ids and requested_counts
--   (b) the TASK-704 retry slot and the word_upload slot skip excluded types
--   (c) {practice} gives practice_*_min = 0 and practice_budget_minutes = 0
--   (d) a same-day re-run after excluding a skill keeps that skill's completed slot
--   (e) the default '{}' leaves the test side untouched and echoes excluded_modules
-- =============================================================================

BEGIN;

DO $test$
DECLARE
  v_user   uuid;
  v_lang   smallint := 2;
  v_today  date     := CURRENT_DATE;
  v_week   date     := public.week_start_for(CURRENT_DATE);
  v_listen_t  smallint := (SELECT id FROM public.dim_test_types WHERE type_code = 'listening');
  v_read_t    smallint := (SELECT id FROM public.dim_test_types WHERE type_code = 'reading');
  v_l1 uuid := gen_random_uuid(); v_l2 uuid := gen_random_uuid(); v_l3 uuid := gen_random_uuid();
  v_r1 uuid := gen_random_uuid(); v_r2 uuid := gen_random_uuid();
  v_poor uuid := gen_random_uuid(); v_wu uuid := gen_random_uuid();
  r jsonb; v_t jsonb; v_n int; v_tpl smallint;
BEGIN
  SELECT id INTO v_user FROM public.users LIMIT 1;
  IF v_user IS NULL THEN RAISE EXCEPTION 'no users row available to satisfy FKs'; END IF;
  SELECT MIN(template_id) INTO v_tpl FROM public.dim_study_plan_templates;

  DELETE FROM public.daily_test_load_items WHERE load_id IN (
    SELECT id FROM public.daily_test_loads WHERE user_id=v_user AND language_id=v_lang AND load_date=v_today);
  DELETE FROM public.daily_test_loads   WHERE user_id=v_user AND language_id=v_lang AND load_date=v_today;
  DELETE FROM public.weekly_plan_states WHERE user_id=v_user AND language_id=v_lang AND week_start_date=v_week;
  DELETE FROM public.user_study_plans   WHERE user_id=v_user AND language_id=v_lang;

  -- 140 weekly minutes, flat shape => 20 minutes today. Targets: 3 listening + 2 reading;
  -- practice pool 14 min/week (tests_and_review). new_words_per_day = 0 isolates the exclusion logic.
  INSERT INTO public.user_study_plans(user_id, language_id, template_id, daily_minutes, weekday_shape,
                                      excluded_modules, budget_scope, new_words_per_day)
  VALUES (v_user, v_lang, v_tpl, 30, '[1,1,1,1,1,1,1]'::jsonb, '{}', 'tests_and_review', 0);

  INSERT INTO public.weekly_plan_states(
    user_id, language_id, week_start_date, target_counts, skill_values, completed_counts,
    practice_target_minutes, maintenance_share, acquisition_share, total_weekly_minutes,
    budget_scope, review_target_minutes)
  VALUES (v_user, v_lang, v_week,
          '{"listening":3,"reading":2}'::jsonb, '{"listening":0.5,"reading":0.4}'::jsonb, '{}'::jsonb,
          14, 1.0, 0.0, 140, 'tests_and_review', 14);

  INSERT INTO public.tests(id, gen_user, slug, difficulty, tier, title, language_id, is_active) VALUES
    (v_l1, v_user, '__sme_l1', 1, 'free-tier', 'SME L1', v_lang, true),
    (v_l2, v_user, '__sme_l2', 1, 'free-tier', 'SME L2', v_lang, true),
    (v_l3, v_user, '__sme_l3', 1, 'free-tier', 'SME L3', v_lang, true),
    (v_r1, v_user, '__sme_r1', 1, 'free-tier', 'SME R1', v_lang, true),
    (v_r2, v_user, '__sme_r2', 1, 'free-tier', 'SME R2', v_lang, true),
    (v_poor, v_user, '__sme_poor', 1, 'free-tier', 'SME POOR', v_lang, true),
    (v_wu, v_user, '__sme_wu', 1, 'free-tier', 'SME WU', v_lang, true);
  INSERT INTO public.test_skill_ratings(test_id, test_type_id, elo_rating) VALUES
    (v_l1, v_listen_t, 1200), (v_l2, v_listen_t, 1200), (v_l3, v_listen_t, 1200),
    (v_r1, v_read_t, 1200), (v_r2, v_read_t, 1200),
    (v_poor, v_listen_t, 1200), (v_wu, v_listen_t, 1200);

  -- ---------------------------------------------------------------- (e) baseline: nothing excluded
  r := public.build_daily_session(v_user, v_lang, v_today);
  SELECT COUNT(*) INTO v_n FROM jsonb_array_elements(r->'test_ids') e WHERE e->>'test_type' = 'listening';
  IF v_n = 0 THEN RAISE EXCEPTION 'SETUP FAIL (e): baseline has no listening slot: %', r->'test_ids'; END IF;
  IF r->'excluded_modules' <> '[]'::jsonb THEN
    RAISE EXCEPTION 'FAIL (e): excluded_modules not echoed as [] : %', r->'excluded_modules';
  END IF;
  SELECT daily_session_targets INTO v_t FROM public.daily_test_loads
   WHERE user_id=v_user AND language_id=v_lang AND load_date=v_today;
  IF v_t->'excluded_modules' <> '[]'::jsonb THEN
    RAISE EXCEPTION 'FAIL (e): daily_session_targets.excluded_modules missing: %', v_t;
  END IF;

  -- ---------------------------------------------------------------- (a) excluded skill is absent
  DELETE FROM public.daily_test_load_items WHERE load_id IN (
    SELECT id FROM public.daily_test_loads WHERE user_id=v_user AND language_id=v_lang AND load_date=v_today);
  DELETE FROM public.daily_test_loads WHERE user_id=v_user AND language_id=v_lang AND load_date=v_today;
  UPDATE public.user_study_plans SET excluded_modules = ARRAY['listening']
   WHERE user_id=v_user AND language_id=v_lang;
  r := public.build_daily_session(v_user, v_lang, v_today);
  IF EXISTS (SELECT 1 FROM jsonb_array_elements(r->'test_ids') e WHERE e->>'test_type' = 'listening') THEN
    RAISE EXCEPTION 'FAIL (a): listening slot present although excluded: %', r->'test_ids';
  END IF;
  IF (r->'requested_counts') ? 'listening' THEN
    RAISE EXCEPTION 'FAIL (a): requested_counts still has listening: %', r->'requested_counts';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM jsonb_array_elements(r->'test_ids') e WHERE e->>'test_type' = 'reading') THEN
    RAISE EXCEPTION 'FAIL (a): reading (not excluded) lost its slots: %', r->'test_ids';
  END IF;

  -- ---------------------------------------------------------------- (b) retry + word_upload skip excluded types
  -- A poor (<70%) listening attempt older than 24h would normally become the retry slot;
  -- a watchlist match whose only rating is listening would normally become the word_upload slot.
  INSERT INTO public.test_attempts(user_id, test_id, score, total_questions, percentage,
        user_elo_before, test_elo_before, user_elo_after, test_elo_after, language_id, test_type_id, created_at)
  VALUES (v_user, v_poor, 1, 5, 20, 1200, 1200, 1190, 1210, v_lang, v_listen_t, now() - interval '3 days');
  INSERT INTO public.user_word_watchlist(user_id, sense_id, language_id, upload_batch_id, active,
                                         last_matched_test_id, last_matched_at)
  SELECT v_user, dws.id, v_lang, gen_random_uuid(), true, v_wu, now()
    FROM public.dim_word_senses dws
    JOIN public.dim_vocabulary dv ON dv.id = dws.vocab_id AND dv.language_id = v_lang
   LIMIT 1;
  DELETE FROM public.daily_test_load_items WHERE load_id IN (
    SELECT id FROM public.daily_test_loads WHERE user_id=v_user AND language_id=v_lang AND load_date=v_today);
  DELETE FROM public.daily_test_loads WHERE user_id=v_user AND language_id=v_lang AND load_date=v_today;
  r := public.build_daily_session(v_user, v_lang, v_today);
  IF EXISTS (SELECT 1 FROM jsonb_array_elements(r->'test_ids') e
              WHERE e->>'slot_type' IN ('retry','word_upload')) THEN
    RAISE EXCEPTION 'FAIL (b): retry/word_upload picked an excluded type: %', r->'test_ids';
  END IF;
  -- Control: with listening included again the retry slot returns (proves the fixture bites).
  UPDATE public.user_study_plans SET excluded_modules = '{}' WHERE user_id=v_user AND language_id=v_lang;
  DELETE FROM public.daily_test_load_items WHERE load_id IN (
    SELECT id FROM public.daily_test_loads WHERE user_id=v_user AND language_id=v_lang AND load_date=v_today);
  DELETE FROM public.daily_test_loads WHERE user_id=v_user AND language_id=v_lang AND load_date=v_today;
  r := public.build_daily_session(v_user, v_lang, v_today);
  IF NOT EXISTS (SELECT 1 FROM jsonb_array_elements(r->'test_ids') e WHERE e->>'slot_type' = 'retry') THEN
    RAISE EXCEPTION 'SETUP FAIL (b): control run produced no retry slot: %', r->'test_ids';
  END IF;

  -- ---------------------------------------------------------------- (c) {practice} excluded
  DELETE FROM public.daily_test_load_items WHERE load_id IN (
    SELECT id FROM public.daily_test_loads WHERE user_id=v_user AND language_id=v_lang AND load_date=v_today);
  DELETE FROM public.daily_test_loads WHERE user_id=v_user AND language_id=v_lang AND load_date=v_today;
  UPDATE public.user_study_plans SET excluded_modules = ARRAY['practice'], new_words_per_day = 5
   WHERE user_id=v_user AND language_id=v_lang;
  r := public.build_daily_session(v_user, v_lang, v_today);
  IF (r->>'practice_maintenance_min')::int <> 0 OR (r->>'practice_acquisition_min')::int <> 0
     OR (r->>'practice_budget_minutes')::numeric <> 0 THEN
    RAISE EXCEPTION 'FAIL (c): practice not zeroed when excluded: %', r;
  END IF;
  IF (r->>'test_budget_minutes')::numeric <> (r->>'today_budget_minutes')::numeric THEN
    RAISE EXCEPTION 'FAIL (c): test budget should equal the whole day: %', r;
  END IF;

  -- ---------------------------------------------------------------- (d) same-day re-run keeps a completed slot
  DELETE FROM public.daily_test_load_items WHERE load_id IN (
    SELECT id FROM public.daily_test_loads WHERE user_id=v_user AND language_id=v_lang AND load_date=v_today);
  DELETE FROM public.daily_test_loads WHERE user_id=v_user AND language_id=v_lang AND load_date=v_today;
  DELETE FROM public.test_attempts WHERE user_id=v_user AND test_id = v_poor;   -- no retry noise
  UPDATE public.user_study_plans SET excluded_modules = '{}', new_words_per_day = 0
   WHERE user_id=v_user AND language_id=v_lang;
  r := public.build_daily_session(v_user, v_lang, v_today);
  SELECT (e->>'test_id')::uuid INTO v_l1
    FROM jsonb_array_elements(r->'test_ids') e WHERE e->>'test_type' = 'listening' LIMIT 1;
  IF v_l1 IS NULL THEN RAISE EXCEPTION 'SETUP FAIL (d): no listening slot to complete: %', r->'test_ids'; END IF;
  UPDATE public.daily_test_loads SET completed_test_ids = jsonb_build_array(v_l1::text)
   WHERE user_id=v_user AND language_id=v_lang AND load_date=v_today;
  UPDATE public.user_study_plans SET excluded_modules = ARRAY['listening']
   WHERE user_id=v_user AND language_id=v_lang;
  r := public.build_daily_session(v_user, v_lang, v_today);
  SELECT COUNT(*) INTO v_n FROM jsonb_array_elements(r->'test_ids') e WHERE e->>'test_id' = v_l1::text;
  IF v_n <> 1 THEN RAISE EXCEPTION 'FAIL (d): completed listening slot not retained exactly once (n=%): %', v_n, r->'test_ids'; END IF;
  IF NOT EXISTS (SELECT 1 FROM public.daily_test_load_items dtli
                  JOIN public.daily_test_loads d ON d.id = dtli.load_id
                 WHERE d.user_id=v_user AND d.language_id=v_lang AND d.load_date=v_today
                   AND dtli.test_id = v_l1 AND dtli.is_completed) THEN
    RAISE EXCEPTION 'FAIL (d): items mirror lost completion of the retained excluded-skill slot';
  END IF;
  SELECT COUNT(*) INTO v_n FROM jsonb_array_elements(r->'test_ids') e
   WHERE e->>'test_type' = 'listening' AND e->>'test_id' <> v_l1::text;
  IF v_n <> 0 THEN RAISE EXCEPTION 'FAIL (d): other (incomplete) listening slots survived the exclusion: %', r->'test_ids'; END IF;

  RAISE NOTICE 'session-module-exclusions PASS (a,b,c,d,e)';
END $test$;

ROLLBACK;
