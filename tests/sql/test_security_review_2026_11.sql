-- =============================================================================
-- Codebase review 2026-11 security migrations (rollback-only SQL test)
-- =============================================================================
-- Requires, applied:
--   migrations/security_tests_service_role_only.sql
--   migrations/security_calibration_answer_keys.sql
--   migrations/security_watchlist_reports_no_client_writes.sql
--   the hardened process_*_submission.sql / get_classifier_drill_session.sql
--
--   psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f tests/sql/test_security_review_2026_11.sql
--
-- Needs roles anon / authenticated / service_role (Supabase, or a local stub that
-- creates them). Assertions RAISE EXCEPTION; a clean run prints PASS notices.
-- Everything is rolled back; no data is read or written (permission checks fire
-- before row access, and the writes target a random uuid).
-- =============================================================================

BEGIN;

-- Run $sql as $role; PASS only when it fails with insufficient_privilege (42501).
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

-- ---- tests: no client read (transcripts, premium tests) ----------------------------
SELECT pg_temp.expect_denied('authenticated', $$SELECT id, transcript FROM public.tests LIMIT 1$$, 'SELECT tests');
SELECT pg_temp.expect_denied('anon',          $$SELECT id FROM public.tests LIMIT 1$$,             'SELECT tests');

-- ---- calibration answer keys ---------------------------------------------------------
SELECT pg_temp.expect_denied('authenticated',
  $$SELECT is_key FROM public.calibration_response_options LIMIT 1$$, 'SELECT calibration_response_options');
SELECT pg_temp.expect_denied('authenticated',
  $$SELECT id FROM public.calibration_responses LIMIT 1$$, 'SELECT calibration_responses');

-- ---- watchlist / reports: no client writes -------------------------------------------
SELECT pg_temp.expect_denied('authenticated',
  $$DELETE FROM public.user_word_watchlist WHERE user_id = '00000000-0000-0000-0000-000000000001'$$,
  'DELETE user_word_watchlist');
SELECT pg_temp.expect_denied('authenticated',
  $$UPDATE public.user_word_watchlist SET sense_id = sense_id WHERE user_id = '00000000-0000-0000-0000-000000000001'$$,
  'UPDATE user_word_watchlist');
SELECT pg_temp.expect_denied('authenticated',
  $$INSERT INTO public.user_reports (user_id, description) VALUES ('00000000-0000-0000-0000-000000000001', 'x')$$,
  'INSERT user_reports');

DO $$
DECLARE r text; t text; p text;
BEGIN
  FOREACH r IN ARRAY ARRAY['anon','authenticated'] LOOP
    FOREACH t IN ARRAY ARRAY['tests','calibration_response_options','calibration_responses'] LOOP
      FOREACH p IN ARRAY ARRAY['SELECT','INSERT','UPDATE','DELETE','TRUNCATE','REFERENCES','TRIGGER'] LOOP
        IF has_table_privilege(r, 'public.'||t, p) THEN
          RAISE EXCEPTION 'FAIL: % has % on %', r, p, t;
        END IF;
      END LOOP;
    END LOOP;
    FOREACH t IN ARRAY ARRAY['user_word_watchlist','user_reports'] LOOP
      FOREACH p IN ARRAY ARRAY['INSERT','UPDATE','DELETE','TRUNCATE','REFERENCES','TRIGGER'] LOOP
        IF has_table_privilege(r, 'public.'||t, p) THEN
          RAISE EXCEPTION 'FAIL: % has % on %', r, p, t;
        END IF;
      END LOOP;
    END LOOP;
  END LOOP;
  RAISE NOTICE 'PASS: no client privilege on tests / calibration answer tables; no client writes on watchlist / reports';

  IF EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = 'public'
                AND tablename IN ('tests', 'calibration_response_options')) THEN
    RAISE EXCEPTION 'FAIL: a policy remains on tests or calibration_response_options';
  END IF;
  IF EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = 'public'
                AND tablename IN ('user_word_watchlist', 'user_reports') AND cmd <> 'SELECT') THEN
    RAISE EXCEPTION 'FAIL: a write policy remains on user_word_watchlist or user_reports';
  END IF;
  RAISE NOTICE 'PASS: no leftover policies';

  -- The owner can still read their own watchlist and reports (RLS-filtered).
  IF NOT has_table_privilege('authenticated', 'public.user_word_watchlist', 'SELECT')
     OR NOT has_table_privilege('authenticated', 'public.user_reports', 'SELECT') THEN
    RAISE EXCEPTION 'FAIL: authenticated lost own-row SELECT on watchlist / reports';
  END IF;
  RAISE NOTICE 'PASS: own-row SELECT kept on watchlist / reports';
END $$;

-- ---- submission RPCs: service_role only, search_path pinned, NULL-safe gate ------------
DO $$
DECLARE f record; n int := 0;
BEGIN
  FOR f IN
    SELECT p.oid, p.oid::regprocedure AS sig, p.proconfig, p.prosrc
      FROM pg_proc p
     WHERE p.pronamespace = 'public'::regnamespace
       AND p.proname IN ('process_pinyin_submission', 'process_pitch_accent_submission',
                         'process_classifier_drill_submission', 'process_dictation_submission',
                         'process_test_submission', 'get_classifier_drill_session')
  LOOP
    n := n + 1;
    IF has_function_privilege('anon', f.oid, 'EXECUTE')
       OR has_function_privilege('authenticated', f.oid, 'EXECUTE') THEN
      RAISE EXCEPTION 'FAIL: % is executable by a client role', f.sig;
    END IF;
    IF NOT has_function_privilege('service_role', f.oid, 'EXECUTE') THEN
      RAISE EXCEPTION 'FAIL: service_role cannot execute %', f.sig;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM unnest(coalesce(f.proconfig, '{}')) c WHERE c LIKE 'search_path=%') THEN
      RAISE EXCEPTION 'FAIL: % has no pinned search_path', f.sig;
    END IF;
    IF f.prosrc ~ '(!=|<>)\s*auth\.uid\(\)' AND f.prosrc !~ 'IS DISTINCT FROM p_user_id' THEN
      RAISE EXCEPTION 'FAIL: % still uses the NULL-permissive auth.uid() gate', f.sig;
    END IF;
  END LOOP;
  IF n < 6 THEN
    RAISE EXCEPTION 'FAIL: expected 6 submission / drill RPCs, found % (stale overloads dropped? missing function?)', n;
  END IF;
  IF n > 6 THEN
    RAISE EXCEPTION 'FAIL: % functions match; a legacy overload is still present (see drop_legacy_process_test_submission_overloads.sql)', n;
  END IF;
  RAISE NOTICE 'PASS: 6 submission / drill RPCs are service_role only with pinned search_path';
END $$;

-- With no JWT the gate must refuse (the old `p_user_id != auth.uid()` let this through).
SET LOCAL request.jwt.claims = '';
DO $$
DECLARE r jsonb;
BEGIN
  r := public.process_pinyin_submission(gen_random_uuid(), gen_random_uuid(), 1::smallint, 1::smallint, 1, 2);
  IF r->>'error_code' IS DISTINCT FROM 'unauthorized' THEN
    RAISE EXCEPTION 'FAIL: process_pinyin_submission without a JWT returned %', r;
  END IF;
  r := public.process_dictation_submission(gen_random_uuid(), gen_random_uuid(), 1::smallint, 1::smallint, 1, 2, 1::smallint, '[]'::jsonb);
  IF r->>'error_code' IS DISTINCT FROM 'unauthorized' THEN
    RAISE EXCEPTION 'FAIL: process_dictation_submission without a JWT returned %', r;
  END IF;
  RAISE NOTICE 'PASS: submission RPCs refuse a caller with no JWT';
END $$;

ROLLBACK;
