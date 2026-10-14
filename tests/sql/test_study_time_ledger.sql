-- =============================================================================
-- Weekly minutes - study_time_ledger SQL tests (TASK-887, ADR-035)
-- =============================================================================
-- Rollback-only, same harness as tests/sql/test_session_budget_settings.sql: assertions
-- RAISE EXCEPTION, a clean run prints PASS notices, everything is rolled back. Requires
-- migrations/study_time_ledger.sql applied (plus plan_local_date / week_start_for). Run from
-- the REPO ROOT (the backfill is included with \i using a relative path):
--
--   psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f tests/sql/test_study_time_ledger.sql
--
-- Run as the migration owner (postgres) on a Supabase branch or throwaway DB. Fixtures:
-- the first auth.users row and the language of the first dim_word_senses row. Inside the
-- transaction it DELETEs that user's user_study_plans / weekly_plan_states rows for that
-- language and any ledger rows for that user (all rolled back), and INSERTs test_attempts /
-- exercise_attempts rows.
--
-- Limitation: credit_study_time reads now(), which a test cannot move. The learner-local
-- week boundary is therefore asserted two ways: (a) the credited week equals
-- week_start_for(plan_local_date(user, lang)) for UTC+13 and UTC-10 plans right now, and
-- (b) the same helper expression is evaluated at a fixed instant (Sun 2026-10-11 12:00Z)
-- where those two zones fall in DIFFERENT weeks, proving the zone drives the week.
-- =============================================================================

BEGIN;

CREATE FUNCTION pg_temp.ok(p_cond boolean, p_label text) RETURNS void LANGUAGE plpgsql AS $f$
BEGIN
  IF p_cond IS DISTINCT FROM true THEN RAISE EXCEPTION 'FAIL: %', p_label; END IF;
  RAISE NOTICE 'PASS: %', p_label;
END $f$;

-- Expect an exception with the given SQLSTATE from p_sql.
CREATE FUNCTION pg_temp.raises(p_sql text, p_state text, p_label text) RETURNS void LANGUAGE plpgsql AS $f$
BEGIN
  BEGIN
    EXECUTE p_sql;
  EXCEPTION WHEN OTHERS THEN
    IF SQLSTATE = p_state THEN RAISE NOTICE 'PASS: %', p_label; RETURN; END IF;
    RAISE EXCEPTION 'FAIL: % raised % not %', p_label, SQLSTATE, p_state;
  END;
  RAISE EXCEPTION 'FAIL: % did not raise', p_label;
END $f$;

CREATE TEMP TABLE stl_ctx (u uuid, lang smallint);
INSERT INTO stl_ctx
SELECT (SELECT id FROM auth.users ORDER BY id LIMIT 1),
       (SELECT dv.language_id::smallint FROM public.dim_word_senses dws
          JOIN public.dim_vocabulary dv ON dv.id = dws.vocab_id ORDER BY dws.id LIMIT 1);

DELETE FROM public.study_time_ledger WHERE user_id = (SELECT u FROM stl_ctx);
DELETE FROM public.weekly_plan_states
 WHERE user_id = (SELECT u FROM stl_ctx) AND language_id = (SELECT lang FROM stl_ctx);
DELETE FROM public.user_study_plans
 WHERE user_id = (SELECT u FROM stl_ctx) AND language_id = (SELECT lang FROM stl_ctx);

-- ---- 1. ACL / RLS ------------------------------------------------------------------
DO $$
DECLARE r text;
BEGIN
  PERFORM pg_temp.ok((SELECT relrowsecurity FROM pg_class WHERE oid = 'public.study_time_ledger'::regclass),
                     'RLS enabled on study_time_ledger');
  PERFORM pg_temp.ok(NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'study_time_ledger'),
                     'no policy on study_time_ledger');
  FOREACH r IN ARRAY ARRAY['anon','authenticated'] LOOP
    PERFORM pg_temp.ok(NOT has_table_privilege(r, 'public.study_time_ledger', 'SELECT')
                   AND NOT has_table_privilege(r, 'public.study_time_ledger', 'INSERT')
                   AND NOT has_table_privilege(r, 'public.study_time_ledger', 'UPDATE')
                   AND NOT has_table_privilege(r, 'public.study_time_ledger', 'DELETE'),
                       r || ' has no table privileges on study_time_ledger');
    PERFORM pg_temp.ok(NOT has_function_privilege(r,
        'public.credit_study_time(uuid, smallint, text, integer, text, text)', 'EXECUTE'),
        r || ' cannot EXECUTE credit_study_time');
    PERFORM pg_temp.ok(NOT has_function_privilege(r,
        'public.get_weekly_study_seconds(uuid, smallint, date)', 'EXECUTE'),
        r || ' cannot EXECUTE get_weekly_study_seconds');
  END LOOP;
  PERFORM pg_temp.ok(has_function_privilege('service_role',
        'public.credit_study_time(uuid, smallint, text, integer, text, text)', 'EXECUTE')
     AND has_function_privilege('service_role',
        'public.get_weekly_study_seconds(uuid, smallint, date)', 'EXECUTE'),
        'service_role can EXECUTE both functions');
  PERFORM pg_temp.ok((SELECT bool_and(prosecdef AND EXISTS (
            SELECT 1 FROM unnest(proconfig) c WHERE c LIKE 'search_path=%'))
          FROM pg_proc WHERE oid IN (
            'public.credit_study_time(uuid, smallint, text, integer, text, text)'::regprocedure,
            'public.get_weekly_study_seconds(uuid, smallint, date)'::regprocedure)),
        'both functions SECURITY DEFINER with pinned search_path');
END $$;

-- ---- 2. credit basics: no weekly row, duplicate once, week = local week ----------------
DO $$
DECLARE v_u uuid; v_l smallint; v_wk date; v_cnt int;
BEGIN
  SELECT u, lang INTO v_u, v_l FROM stl_ctx;
  PERFORM pg_temp.ok(NOT EXISTS (SELECT 1 FROM public.weekly_plan_states
                                 WHERE user_id = v_u AND language_id = v_l),
                     'fixture: no weekly_plan_states row');
  PERFORM pg_temp.ok(public.credit_study_time(v_u, v_l, 'test', 100, 'test_attempts', 'dup-1') = true,
                     'credit with no weekly row returns true');
  PERFORM pg_temp.ok(public.credit_study_time(v_u, v_l, 'test', 100, 'test_attempts', 'dup-1') = false,
                     'duplicate source returns false');
  SELECT count(*) INTO v_cnt FROM public.study_time_ledger WHERE source_id = 'dup-1';
  PERFORM pg_temp.ok(v_cnt = 1, 'duplicate source stored once');
  v_wk := public.week_start_for(public.plan_local_date(v_u, v_l));
  PERFORM pg_temp.ok((SELECT week_start_date FROM public.study_time_ledger WHERE source_id = 'dup-1') = v_wk,
                     'week_start_date = learner-local Monday');
  PERFORM pg_temp.ok(EXTRACT(ISODOW FROM v_wk) = 1, 'week_start_date is a Monday');
  -- same source_id under a different kind / table is a distinct source
  PERFORM pg_temp.ok(public.credit_study_time(v_u, v_l, 'drill', 100, 'test_attempts', 'dup-1') = true,
                     'same id, different kind is a separate source');
END $$;

-- ---- 3. per-kind clamp -----------------------------------------------------------------
DO $$
DECLARE v_u uuid; v_l smallint; k text; cap int;
BEGIN
  SELECT u, lang INTO v_u, v_l FROM stl_ctx;
  FOR k, cap IN SELECT * FROM (VALUES ('test',1200),('drill',1200),('practice',300),
                                       ('flashcard',120),('dual_translation',900)) t(k, cap) LOOP
    PERFORM public.credit_study_time(v_u, v_l, k, 999999, 'clamp_src', 'clamp-' || k);
    PERFORM pg_temp.ok((SELECT seconds FROM public.study_time_ledger
                         WHERE kind = k AND source_table = 'clamp_src' AND source_id = 'clamp-' || k) = cap,
                       'clamp ' || k || ' to ' || cap);
  END LOOP;
  PERFORM public.credit_study_time(v_u, v_l, 'flashcard', 7, 'clamp_src', 'under-cap');
  PERFORM pg_temp.ok((SELECT seconds FROM public.study_time_ledger WHERE source_id = 'under-cap') = 7,
                     'value under cap stored as-is');
END $$;

-- ---- 4. zero / negative / NULL seconds, bad kind, empty source ---------------------------
DO $$
DECLARE v_u uuid; v_l smallint;
BEGIN
  SELECT u, lang INTO v_u, v_l FROM stl_ctx;
  PERFORM pg_temp.ok(public.credit_study_time(v_u, v_l, 'practice', 0, 't', 'zero') = false, 'zero seconds returns false');
  PERFORM pg_temp.ok(public.credit_study_time(v_u, v_l, 'practice', -5, 't', 'neg') = false, 'negative seconds returns false');
  PERFORM pg_temp.ok(public.credit_study_time(v_u, v_l, 'practice', NULL, 't', 'null') = false, 'NULL seconds returns false');
  PERFORM pg_temp.ok(NOT EXISTS (SELECT 1 FROM public.study_time_ledger WHERE source_id IN ('zero','neg','null')),
                     'zero/negative/NULL insert no row');
  PERFORM pg_temp.raises(format('SELECT public.credit_study_time(%L, %s::smallint, ''bogus'', 10, ''t'', ''x'')', v_u, v_l),
                         '23514', 'invalid kind raises check_violation');
  PERFORM pg_temp.raises(format('SELECT public.credit_study_time(%L, %s::smallint, ''test'', 10, ''t'', '''')', v_u, v_l),
                         '23514', 'empty source_id raises check_violation');
  PERFORM pg_temp.raises(format('SELECT public.credit_study_time(%L, %s::smallint, ''test'', 10, '''', ''x'')', v_u, v_l),
                         '23514', 'empty source_table raises check_violation');
END $$;

-- ---- 5. get_weekly_study_seconds -----------------------------------------------------------
DO $$
DECLARE v_u uuid; v_l smallint; v_wk date; j jsonb;
BEGIN
  SELECT u, lang INTO v_u, v_l FROM stl_ctx;
  v_wk := public.week_start_for(public.plan_local_date(v_u, v_l));
  j := public.get_weekly_study_seconds(v_u, v_l, v_wk);
  PERFORM pg_temp.ok(j ?& ARRAY['test','practice','flashcard','dual_translation','drill'], 'all five keys present');
  PERFORM pg_temp.ok((j->>'test')::int = 100 + 1200, 'test sum (dup-1 100 + clamp 1200)');
  PERFORM pg_temp.ok((j->>'flashcard')::int = 120 + 7, 'flashcard sum');
  PERFORM pg_temp.ok((j->>'practice')::int = 300 AND (j->>'dual_translation')::int = 900, 'practice and dual_translation sums');
  PERFORM pg_temp.ok((j->>'drill')::int = 100 + 1200, 'drill sum');
  j := public.get_weekly_study_seconds(v_u, v_l, v_wk - 7);
  PERFORM pg_temp.ok(j = '{"test":0,"practice":0,"flashcard":0,"dual_translation":0,"drill":0}'::jsonb,
                     'other week returns all five keys as 0');
  j := public.get_weekly_study_seconds(gen_random_uuid(), v_l, v_wk);
  PERFORM pg_temp.ok(j = '{"test":0,"practice":0,"flashcard":0,"dual_translation":0,"drill":0}'::jsonb,
                     'unknown user returns zeros');
END $$;

-- ---- 6. learner-local week for UTC+13 and UTC-10 -------------------------------------------
DO $$
DECLARE v_u uuid; v_l smallint; v_tpl smallint; tz text; v_exp date; v_got date;
BEGIN
  SELECT u, lang INTO v_u, v_l FROM stl_ctx;
  SELECT MIN(template_id) INTO v_tpl FROM public.dim_study_plan_templates;
  FOREACH tz IN ARRAY ARRAY['Pacific/Tongatapu','Pacific/Honolulu'] LOOP
    -- Pacific/Tongatapu is UTC+13, Pacific/Honolulu is UTC-10 (no DST in either).
    DELETE FROM public.user_study_plans WHERE user_id = v_u AND language_id = v_l;
    INSERT INTO public.user_study_plans(user_id, language_id, template_id, daily_minutes, weekday_shape, timezone)
    VALUES (v_u, v_l, v_tpl, 30, '[1,1,1,1,1,1,1]', tz);
    v_exp := public.week_start_for((now() AT TIME ZONE tz)::date);
    PERFORM public.credit_study_time(v_u, v_l, 'flashcard', 10, 'tz_src', 'tz-' || tz);
    SELECT week_start_date INTO v_got FROM public.study_time_ledger WHERE source_id = 'tz-' || tz;
    PERFORM pg_temp.ok(v_got = v_exp, 'credited week is the ' || tz || ' local week');
  END LOOP;

  -- Fixed instant Sun 2026-10-11 12:00Z: UTC+13 is already Mon 10-12, UTC-10 is still Sun 10-11.
  PERFORM pg_temp.ok(
    public.week_start_for((timestamptz '2026-10-11 12:00+00' AT TIME ZONE 'Pacific/Tongatapu')::date) = date '2026-10-12'
    AND public.week_start_for((timestamptz '2026-10-11 12:00+00' AT TIME ZONE 'Pacific/Honolulu')::date) = date '2026-10-05',
    'at one instant UTC+13 and UTC-10 learners are in different weeks');

  -- And through the real SQL helper with the stored plan timezone (currently Honolulu).
  PERFORM pg_temp.ok(
    public.week_start_for(public.plan_local_date(v_u, v_l, timestamptz '2026-10-11 12:00+00')) = date '2026-10-05',
    'plan_local_date honours the stored UTC-10 timezone');
  UPDATE public.user_study_plans SET timezone = 'Pacific/Tongatapu' WHERE user_id = v_u AND language_id = v_l;
  PERFORM pg_temp.ok(
    public.week_start_for(public.plan_local_date(v_u, v_l, timestamptz '2026-10-11 12:00+00')) = date '2026-10-12',
    'plan_local_date honours the stored UTC+13 timezone');
  -- Back to UTC for the backfill section.
  UPDATE public.user_study_plans SET timezone = 'UTC' WHERE user_id = v_u AND language_id = v_l;
END $$;

-- ---- 7. backfill: fixtures, idempotence, key equality, current week only ---------------------
DELETE FROM public.study_time_ledger WHERE user_id = (SELECT u FROM stl_ctx);

CREATE TEMP TABLE stl_fx (name text PRIMARY KEY, id uuid);

CREATE FUNCTION pg_temp.ins_ta(p_name text, p_u uuid, p_l smallint, p_test uuid, p_tt smallint,
                               p_dur int, p_age interval) RETURNS void LANGUAGE plpgsql AS $f$
DECLARE v_id uuid;
BEGIN
  INSERT INTO public.test_attempts(user_id, test_id, score, total_questions, user_elo_before, test_elo_before,
                                   user_elo_after, test_elo_after, language_id, test_type_id, duration_ms, created_at)
  VALUES (p_u, p_test, 1, 5, 1400, 1400, 1400, 1400, p_l, p_tt, p_dur, now() - p_age)
  RETURNING id INTO v_id;
  INSERT INTO stl_fx VALUES (p_name, v_id);
END $f$;

CREATE FUNCTION pg_temp.ins_ea(p_name text, p_u uuid, p_sense int, p_type text,
                               p_ms int, p_age interval) RETURNS void LANGUAGE plpgsql AS $f$
DECLARE v_id uuid;
BEGIN
  INSERT INTO public.exercise_attempts(user_id, is_correct, sense_id, exercise_type, time_taken_ms, created_at)
  VALUES (p_u, true, p_sense, p_type, p_ms, now() - p_age)
  RETURNING id INTO v_id;
  INSERT INTO stl_fx VALUES (p_name, v_id);
END $f$;

DO $$
DECLARE
  v_u uuid; v_l smallint; v_test uuid; v_tt_plain smallint; v_tt_drill smallint; v_sense int; v_et text;
BEGIN
  SELECT u, lang INTO v_u, v_l FROM stl_ctx;
  SELECT id INTO v_test FROM public.tests ORDER BY created_at LIMIT 1;
  SELECT id INTO v_tt_plain FROM public.dim_test_types
   WHERE type_code NOT IN ('classifier_drill','counter_drill') ORDER BY id LIMIT 1;
  SELECT id INTO v_tt_drill FROM public.dim_test_types
   WHERE type_code IN ('classifier_drill','counter_drill') ORDER BY id LIMIT 1;
  SELECT dws.id INTO v_sense FROM public.dim_word_senses dws
    JOIN public.dim_vocabulary dv ON dv.id = dws.vocab_id AND dv.language_id = v_l ORDER BY dws.id LIMIT 1;

  -- name, test type, duration_ms, age
  PERFORM pg_temp.ins_ta('ta_ok',      v_u, v_l, v_test, v_tt_plain, 90000,   interval '0');
  PERFORM pg_temp.ins_ta('ta_clamp',   v_u, v_l, v_test, v_tt_plain, 3000000, interval '0');
  PERFORM pg_temp.ins_ta('ta_old',     v_u, v_l, v_test, v_tt_plain, 90000,   interval '30 days');
  PERFORM pg_temp.ins_ta('ta_nodur',   v_u, v_l, v_test, v_tt_plain, NULL,    interval '0');
  IF v_tt_drill IS NOT NULL THEN
    PERFORM pg_temp.ins_ta('ta_drill', v_u, v_l, v_test, v_tt_drill, 45000,   interval '0');
  ELSE
    RAISE NOTICE 'SKIP: no classifier_drill/counter_drill dim_test_types row; drill backfill not asserted';
  END IF;
  SELECT type_code INTO v_et FROM public.dim_exercise_types ORDER BY type_code LIMIT 1;
  PERFORM pg_temp.ins_ea('ea_ok',      v_u, v_sense, v_et, 42000,  interval '0');
  PERFORM pg_temp.ins_ea('ea_absurd',  v_u, v_sense, v_et, 400000, interval '0');
  PERFORM pg_temp.ins_ea('ea_old',     v_u, v_sense, v_et, 42000,  interval '30 days');
END $$;

-- Pre-credit one backfill source with its live key: backfill must not double count it.
DO $$
DECLARE v_u uuid; v_l smallint;
BEGIN
  SELECT u, lang INTO v_u, v_l FROM stl_ctx;
  PERFORM pg_temp.ok(public.credit_study_time(v_u, v_l, 'test', 90, 'test_attempts',
                       (SELECT id::text FROM stl_fx WHERE name = 'ta_ok')) = true,
                     'pre-credit ta_ok under its live key');
END $$;

\i migrations/backfill_study_time_ledger.sql

CREATE TEMP TABLE stl_after1 AS
  SELECT kind, source_table, source_id, seconds, week_start_date FROM public.study_time_ledger
   WHERE user_id = (SELECT u FROM stl_ctx);

DO $$
DECLARE v_u uuid; v_l smallint; v_wk date; v_exp int; v_et text;
BEGIN
  SELECT u, lang INTO v_u, v_l FROM stl_ctx;
  v_wk := public.week_start_for(public.plan_local_date(v_u, v_l));
  PERFORM pg_temp.ok((SELECT count(*) FROM stl_after1 WHERE source_id = (SELECT id::text FROM stl_fx WHERE name='ta_ok')) = 1,
                     'ta_ok present exactly once (live key honoured, no double count)');
  PERFORM pg_temp.ok((SELECT seconds FROM stl_after1 WHERE source_id = (SELECT id::text FROM stl_fx WHERE name='ta_ok')) = 90,
                     'ta_ok = 90 s');
  PERFORM pg_temp.ok((SELECT seconds FROM stl_after1 WHERE source_table='test_attempts'
                        AND source_id = (SELECT id::text FROM stl_fx WHERE name='ta_clamp')) = 1200
                     AND (SELECT kind FROM stl_after1 WHERE source_id = (SELECT id::text FROM stl_fx WHERE name='ta_clamp')) = 'test',
                     'ta_clamp backfilled as test, clamped to 1200');
  PERFORM pg_temp.ok(NOT EXISTS (SELECT 1 FROM stl_after1 WHERE source_id IN
                       (SELECT id::text FROM stl_fx WHERE name IN ('ta_old','ta_nodur','ea_old'))),
                     'old-week and no-duration attempts are not backfilled');
  IF EXISTS (SELECT 1 FROM stl_fx WHERE name = 'ta_drill') THEN
    PERFORM pg_temp.ok((SELECT kind FROM stl_after1 WHERE source_table='test_attempts'
                          AND source_id = (SELECT id::text FROM stl_fx WHERE name='ta_drill')) = 'drill',
                       'drill test type backfilled as kind drill');
  END IF;
  PERFORM pg_temp.ok((SELECT seconds FROM stl_after1 WHERE source_table='exercise_attempts'
                        AND source_id = (SELECT id::text FROM stl_fx WHERE name='ea_ok')) = 42
                     AND (SELECT kind FROM stl_after1 WHERE source_id = (SELECT id::text FROM stl_fx WHERE name='ea_ok')) = 'practice',
                     'ea_ok = 42 s practice under key (exercise_attempts, id)');
  SELECT type_code INTO v_et FROM public.dim_exercise_types ORDER BY type_code LIMIT 1;
  SELECT LEAST(300, GREATEST(1, COALESCE(round(expected_seconds_p50), expected_seconds, 45)))::int
    INTO v_exp FROM public.dim_exercise_types WHERE type_code = v_et;
  PERFORM pg_temp.ok((SELECT seconds FROM stl_after1 WHERE source_table='exercise_attempts'
                        AND source_id = (SELECT id::text FROM stl_fx WHERE name='ea_absurd')) = v_exp,
                     'ea_absurd (>300 s) falls back to the type estimate');
  PERFORM pg_temp.ok(NOT EXISTS (SELECT 1 FROM stl_after1 WHERE week_start_date <> v_wk),
                     'every backfilled row is in the current local week');
END $$;

-- Second run must insert 0 rows and change nothing.
\i migrations/backfill_study_time_ledger.sql

DO $$
DECLARE v_n1 int; v_n2 int; v_s1 bigint; v_s2 bigint;
BEGIN
  SELECT count(*), COALESCE(sum(seconds),0) INTO v_n1, v_s1 FROM stl_after1;
  SELECT count(*), COALESCE(sum(seconds),0) INTO v_n2, v_s2 FROM public.study_time_ledger
   WHERE user_id = (SELECT u FROM stl_ctx);
  PERFORM pg_temp.ok(v_n2 = v_n1 AND v_s2 = v_s1, 'second backfill run inserted 0 rows (count and seconds unchanged)');
  -- a later live credit with the same key is a no-op too
  PERFORM pg_temp.ok(public.credit_study_time((SELECT u FROM stl_ctx), (SELECT lang FROM stl_ctx), 'practice', 42,
                       'exercise_attempts', (SELECT id::text FROM stl_fx WHERE name='ea_ok')) = false,
                     'live credit after backfill with same key returns false');
END $$;

ROLLBACK;
