-- =============================================================================
-- TASK-705 — build_daily_session same-day-safe: SQL unit test (double-call)
-- =============================================================================
-- Verifies that a SECOND same-day invocation of build_daily_session does NOT
-- wipe progress (the F6 regression: ON CONFLICT ... SET completed_test_ids='[]'
-- + items rebuilt as is_completed=false). Runs entirely inside a rollback-only
-- transaction against the LIVE schema — it stands up a throwaway plan / weekly
-- state / two never-attempted tests for an arbitrary existing user in a language
-- they have no plan in, exercises the RPC twice with one completion in between,
-- asserts, then ROLLBACKs so nothing persists.
--
-- Assumes the TASK-705 revision of public.build_daily_session is deployed
-- (migrations/task702_build_daily_session.sql). This file is the DB-side
-- counterpart to tests/test_daily_load_retry_slot.py (which pins the Python
-- contract); there is no pgTAP harness in this repo, so the assertions RAISE
-- EXCEPTION on failure and the script is meant to be piped to psql:
--
--   psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f tests/sql/test_task705_same_day_safe.sql
--
-- A clean run prints the PASS NOTICE and rolls back; any failure aborts with the
-- failing assertion. Verified live in a rollback-only transaction 2026-07-20.
-- =============================================================================

BEGIN;

DO $test$
DECLARE
  v_user   uuid;
  v_lang   smallint := 2;               -- en (no dim_languages 'es' study dimension)
  v_today  date     := CURRENT_DATE;
  v_week   date     := public.week_start_for(CURRENT_DATE);
  v_t1     uuid     := gen_random_uuid();
  v_t2     uuid     := gen_random_uuid();
  r1 jsonb; r2 jsonb;
  v_completed jsonb; v_testids jsonb; v_blocks jsonb;
  v_item_completed boolean; v_t1_in_testids int;
BEGIN
  SELECT id INTO v_user FROM public.users LIMIT 1;
  IF v_user IS NULL THEN RAISE EXCEPTION 'no users row available to satisfy FKs'; END IF;

  -- Clean slate for (user, lang) inside the txn (rolled back at the end).
  DELETE FROM public.daily_test_load_items WHERE load_id IN (
    SELECT id FROM public.daily_test_loads WHERE user_id=v_user AND language_id=v_lang AND load_date=v_today);
  DELETE FROM public.daily_test_loads   WHERE user_id=v_user AND language_id=v_lang AND load_date=v_today;
  DELETE FROM public.weekly_plan_states WHERE user_id=v_user AND language_id=v_lang AND week_start_date=v_week;
  DELETE FROM public.user_study_plans   WHERE user_id=v_user AND language_id=v_lang;

  -- Minimal plan + weekly state: only 'listening', 2 slots. total_weekly=70 and a
  -- flat weekday shape => today budget 10; test_time_estimate('listening')=5 => 2 slots fit.
  INSERT INTO public.user_study_plans(user_id, language_id, template_id, daily_minutes, weekday_shape)
  VALUES (v_user, v_lang, (SELECT MIN(template_id) FROM public.dim_study_plan_templates), 10, '[1,1,1,1,1,1,1]'::jsonb);

  INSERT INTO public.weekly_plan_states(
    user_id, language_id, week_start_date, target_counts, skill_values, completed_counts,
    practice_target_minutes, maintenance_share, acquisition_share, total_weekly_minutes)
  VALUES (v_user, v_lang, v_week, '{"listening":2}'::jsonb, '{"listening":0.5}'::jsonb, '{}'::jsonb,
          0, 0.5, 0.5, 70);

  -- Two never-attempted free-tier listening tests so get_recommended_tests can fill both slots.
  INSERT INTO public.tests(id, gen_user, slug, difficulty, tier, title, language_id, is_active) VALUES
    (v_t1, v_user, '__t705_a', 1, 'free-tier', 'T705 A', v_lang, true),
    (v_t2, v_user, '__t705_b', 1, 'free-tier', 'T705 B', v_lang, true);
  INSERT INTO public.test_skill_ratings(test_id, test_type_id, elo_rating) VALUES
    (v_t1, 1, 1200), (v_t2, 1, 1200);

  -- FIRST call — expect >= 2 listening slots.
  r1 := public.build_daily_session(v_user, v_lang, v_today);
  IF jsonb_array_length(r1->'test_ids') < 2 THEN
    RAISE EXCEPTION 'SETUP FAIL: first call produced <2 slots: %', r1->'test_ids';
  END IF;

  -- Simulate the learner completing test A + one practice block (as the app does
  -- via mark_daily_test_complete / complete-block).
  UPDATE public.daily_test_loads
     SET completed_test_ids = jsonb_build_array(v_t1::text),
         completed_blocks   = '["practice_acq_1"]'::jsonb
   WHERE user_id=v_user AND language_id=v_lang AND load_date=v_today;

  -- SECOND same-day call — must preserve progress.
  r2 := public.build_daily_session(v_user, v_lang, v_today);

  SELECT completed_test_ids, test_ids, completed_blocks
    INTO v_completed, v_testids, v_blocks
    FROM public.daily_test_loads WHERE user_id=v_user AND language_id=v_lang AND load_date=v_today;

  -- AC1: completed_test_ids and completed_blocks survive the re-solve.
  IF NOT (v_completed ? v_t1::text) THEN
    RAISE EXCEPTION 'FAIL AC1a: completed_test_ids wiped on same-day re-solve: %', v_completed;
  END IF;
  IF v_blocks <> '["practice_acq_1"]'::jsonb THEN
    RAISE EXCEPTION 'FAIL AC1b: completed_blocks wiped on same-day re-solve: %', v_blocks;
  END IF;

  -- AC2: completed slot retained exactly once; incomplete slot re-resolved.
  SELECT COUNT(*) INTO v_t1_in_testids
    FROM jsonb_array_elements(v_testids) e WHERE e->>'test_id' = v_t1::text;
  IF v_t1_in_testids <> 1 THEN
    RAISE EXCEPTION 'FAIL AC2a: completed slot not retained exactly once (count=%): %', v_t1_in_testids, v_testids;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM jsonb_array_elements(v_testids) e WHERE e->>'test_id' = v_t2::text) THEN
    RAISE EXCEPTION 'FAIL AC2b: incomplete portion not re-resolved (t2 missing): %', v_testids;
  END IF;

  -- AC2 (items mirror): daily_test_load_items retains completion for the kept slot.
  SELECT dtli.is_completed INTO v_item_completed
    FROM public.daily_test_load_items dtli
    JOIN public.daily_test_loads d ON d.id = dtli.load_id
   WHERE d.user_id=v_user AND d.language_id=v_lang AND d.load_date=v_today AND dtli.test_id=v_t1;
  IF v_item_completed IS DISTINCT FROM true THEN
    RAISE EXCEPTION 'FAIL AC2c: items mirror lost completion for retained slot: %', v_item_completed;
  END IF;

  RAISE NOTICE 'TASK-705 PASS: completed=% blocks=% t1_retained=% total_slots=%',
    v_completed, v_blocks, v_t1_in_testids, jsonb_array_length(v_testids);
END $test$;

ROLLBACK;
