-- =============================================================================
-- TASK-879 / TASK-880 - views + progress tables locked (rollback-only SQL test)
-- =============================================================================
-- Requires migrations/security_views_invoker.sql and
-- migrations/security_lock_progress_tables.sql applied:
--
--   psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f tests/sql/test_security_progress_tables.sql
--
-- Run as the role that creates migrations (postgres) so the default-privilege
-- probe matches pg_default_acl. Everything is rolled back; no user data is read
-- (permission checks fire before row access; statements are column-agnostic).
-- =============================================================================

BEGIN;

CREATE FUNCTION pg_temp.expect_denied(p_role text, p_sql text, p_label text)
RETURNS void LANGUAGE plpgsql AS $f$
BEGIN
  EXECUTE format('SET LOCAL ROLE %I', p_role);
  BEGIN
    EXECUTE p_sql;
    EXECUTE 'RESET ROLE';
    RAISE EXCEPTION 'FAIL: % as % was NOT denied', p_label, p_role;
  EXCEPTION WHEN insufficient_privilege THEN
    EXECUTE 'RESET ROLE';
    RAISE NOTICE 'PASS: % as % denied', p_label, p_role;
  END;
END $f$;

SET LOCAL request.jwt.claims = '{"sub":"00000000-0000-0000-0000-000000000001","role":"authenticated"}';

-- ---- TASK-879: views --------------------------------------------------------------
SELECT pg_temp.expect_denied('anon', 'SELECT 1 FROM public.vw_distractor_error_analysis LIMIT 1', 'SELECT vw_distractor_error_analysis');
SELECT pg_temp.expect_denied('authenticated', 'SELECT 1 FROM public.vw_distractor_error_analysis LIMIT 1', 'SELECT vw_distractor_error_analysis');
SELECT pg_temp.expect_denied('authenticated', 'SELECT 1 FROM public.vw_exercise_type_effectiveness LIMIT 1', 'SELECT vw_exercise_type_effectiveness');

DO $$
DECLARE v text; r text; p text;
BEGIN
  FOREACH v IN ARRAY ARRAY['corpus_statistics','v_ladder_judge_reject_rates','v_sense_family_coverage',
      'v_test_difficulty_calibration','v_test_difficulty_calibration_summary',
      'vw_distractor_error_analysis','vw_exercise_performance_by_type','vw_exercise_type_effectiveness'] LOOP
    IF to_regclass('public.'||v) IS NULL THEN
      RAISE NOTICE 'SKIP: view % not present', v; CONTINUE;
    END IF;
    IF NOT ('security_invoker=true' = ANY (SELECT unnest(reloptions) FROM pg_class WHERE oid = ('public.'||v)::regclass)) THEN
      RAISE EXCEPTION 'FAIL: % is not security_invoker', v;
    END IF;
    FOREACH r IN ARRAY ARRAY['anon','authenticated'] LOOP
      FOREACH p IN ARRAY ARRAY['SELECT','INSERT','UPDATE','DELETE','TRUNCATE','REFERENCES','TRIGGER'] LOOP
        IF has_table_privilege(r, 'public.'||v, p) THEN
          RAISE EXCEPTION 'FAIL: % has % on view %', r, p, v;
        END IF;
      END LOOP;
    END LOOP;
    IF NOT has_table_privilege('service_role', 'public.'||v, 'SELECT') THEN
      RAISE EXCEPTION 'FAIL: service_role lost SELECT on %', v;
    END IF;
  END LOOP;
  RAISE NOTICE 'PASS: 8 views invoker + client grants revoked + service_role intact';
END $$;

-- ---- TASK-880: progress tables ----------------------------------------------------
SELECT pg_temp.expect_denied('authenticated',
  $$INSERT INTO public.test_attempts DEFAULT VALUES$$,
  'INSERT test_attempts');
SELECT pg_temp.expect_denied('authenticated',
  $$DELETE FROM public.user_skill_ratings WHERE false$$,
  'DELETE user_skill_ratings');
SELECT pg_temp.expect_denied('authenticated',
  $$INSERT INTO public.exercise_attempts DEFAULT VALUES$$,
  'INSERT exercise_attempts');
SELECT pg_temp.expect_denied('anon', 'SELECT 1 FROM public.user_word_ladder LIMIT 1', 'SELECT user_word_ladder');

DO $$
DECLARE t text; r text; p text;
BEGIN
  FOREACH t IN ARRAY ARRAY['user_skill_ratings','test_attempts','exercise_attempts','question_attempt_results',
      'user_vocabulary_knowledge','user_word_ladder','daily_test_loads','user_flashcards',
      'calibration_sessions','calibration_responses','weekly_plan_states','user_study_plans'] LOOP
    IF to_regclass('public.'||t) IS NULL THEN
      RAISE NOTICE 'SKIP: table % not present', t; CONTINUE;
    END IF;
    FOREACH r IN ARRAY ARRAY['anon','authenticated'] LOOP
      FOREACH p IN ARRAY ARRAY['INSERT','UPDATE','DELETE','TRUNCATE','REFERENCES','TRIGGER'] LOOP
        IF has_table_privilege(r, 'public.'||t, p) THEN
          RAISE EXCEPTION 'FAIL: % has % on %', r, p, t;
        END IF;
      END LOOP;
    END LOOP;
    IF has_table_privilege('anon', 'public.'||t, 'SELECT') THEN
      RAISE EXCEPTION 'FAIL: anon has SELECT on %', t;
    END IF;
    IF NOT has_table_privilege('authenticated', 'public.'||t, 'SELECT') THEN
      RAISE EXCEPTION 'FAIL: authenticated lost own-row SELECT on %', t;
    END IF;
    IF NOT (SELECT relrowsecurity FROM pg_class WHERE oid = ('public.'||t)::regclass) THEN
      RAISE EXCEPTION 'FAIL: RLS off on %', t;
    END IF;
    IF EXISTS (SELECT 1 FROM pg_policies WHERE schemaname='public' AND tablename=t
                AND cmd IN ('ALL','INSERT','UPDATE','DELETE')) THEN
      RAISE EXCEPTION 'FAIL: write-capable policy remains on %', t;
    END IF;
    IF NOT has_table_privilege('service_role', 'public.'||t, 'INSERT') THEN
      RAISE EXCEPTION 'FAIL: service_role lost INSERT on %', t;
    END IF;
  END LOOP;
  RAISE NOTICE 'PASS: progress tables locked, own-row SELECT + service_role intact';
END $$;

-- ---- TASK-880: default privileges (new objects are not client-granted) -------------
CREATE TABLE public._t880_probe (id serial PRIMARY KEY, v text);
DO $$
DECLARE r text; p text;
BEGIN
  FOREACH r IN ARRAY ARRAY['anon','authenticated'] LOOP
    FOREACH p IN ARRAY ARRAY['SELECT','INSERT','UPDATE','DELETE','TRUNCATE','REFERENCES','TRIGGER'] LOOP
      IF has_table_privilege(r, 'public._t880_probe', p) THEN
        RAISE EXCEPTION 'FAIL: new table granted % to % by default privileges', p, r;
      END IF;
    END LOOP;
    IF has_sequence_privilege(r, 'public._t880_probe_id_seq', 'USAGE')
       OR has_sequence_privilege(r, 'public._t880_probe_id_seq', 'SELECT')
       OR has_sequence_privilege(r, 'public._t880_probe_id_seq', 'UPDATE') THEN
      RAISE EXCEPTION 'FAIL: new sequence granted to % by default privileges', r;
    END IF;
  END LOOP;
  RAISE NOTICE 'PASS: default privileges do not grant new tables/sequences to client roles';
END $$;

ROLLBACK;
