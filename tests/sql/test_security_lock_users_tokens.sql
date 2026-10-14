-- =============================================================================
-- TASK-875 / TASK-876 — client roles are locked out (rollback-only SQL test)
-- =============================================================================
-- Requires migrations/security_lock_users_tokens_reports.sql and
-- migrations/security_enable_rls_unprotected_tables.sql applied:
--
--   psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f tests/sql/test_security_lock_users_tokens.sql
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

-- ---- TASK-875 ---------------------------------------------------------------------
-- The headline attack: self-escalation to an admin tier.
SELECT pg_temp.expect_denied('authenticated',
  $$UPDATE public.users SET subscription_tier_id = 5 WHERE id = '00000000-0000-0000-0000-000000000001'$$,
  'UPDATE users.subscription_tier_id');
SELECT pg_temp.expect_denied('authenticated',
  $$UPDATE public.user_tokens SET purchased_tokens = 1000000 WHERE user_id = '00000000-0000-0000-0000-000000000001'$$,
  'UPDATE user_tokens.purchased_tokens');
SELECT pg_temp.expect_denied('authenticated',
  $$INSERT INTO public.user_tokens (user_id, purchased_tokens) VALUES (gen_random_uuid(), 1)$$,
  'INSERT user_tokens');
SELECT pg_temp.expect_denied('authenticated',
  $$INSERT INTO public.token_transactions (user_id, tokens_added, action) VALUES (gen_random_uuid(), 100, 'forged')$$,
  'INSERT token_transactions');

DO $$
DECLARE r text; t text; p text;
BEGIN
  FOREACH r IN ARRAY ARRAY['anon','authenticated'] LOOP
    FOREACH t IN ARRAY ARRAY['users','user_tokens','token_transactions'] LOOP
      FOREACH p IN ARRAY ARRAY['INSERT','UPDATE','DELETE','TRUNCATE','REFERENCES','TRIGGER'] LOOP
        IF has_table_privilege(r, 'public.'||t, p) THEN
          RAISE EXCEPTION 'FAIL: % has % on %', r, p, t;
        END IF;
      END LOOP;
    END LOOP;
  END LOOP;
  RAISE NOTICE 'PASS: no client DML/TRUNCATE/REFERENCES/TRIGGER on users, user_tokens, token_transactions';

  -- own-row SELECT survives for authenticated
  IF NOT has_table_privilege('authenticated','public.users','SELECT')
     OR NOT has_table_privilege('authenticated','public.user_tokens','SELECT') THEN
    RAISE EXCEPTION 'FAIL: authenticated lost own-row SELECT on users/user_tokens';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname='public' AND tablename='user_tokens'
                 AND policyname='Users can view own tokens' AND cmd='SELECT') THEN
    RAISE EXCEPTION 'FAIL: own-row SELECT policy missing on user_tokens';
  END IF;

  -- dropped policies
  IF EXISTS (SELECT 1 FROM pg_policies WHERE schemaname='public' AND policyname IN
      ('users_admin_all','users_update_own','Users can update own profile','Users update own profile',
       'System can update tokens','tokens_own_data','Admin can view all reports')) THEN
    RAISE EXCEPTION 'FAIL: a dropped policy still exists';
  END IF;
  RAISE NOTICE 'PASS: dropped policies gone, own-row SELECT kept';

  -- user_reports: anon none, authenticated INSERT+SELECT only
  IF has_table_privilege('anon','public.user_reports','SELECT')
     OR has_table_privilege('anon','public.user_reports','INSERT') THEN
    RAISE EXCEPTION 'FAIL: anon has access to user_reports';
  END IF;
  IF NOT has_table_privilege('authenticated','public.user_reports','INSERT')
     OR has_table_privilege('authenticated','public.user_reports','UPDATE')
     OR has_table_privilege('authenticated','public.user_reports','DELETE') THEN
    RAISE EXCEPTION 'FAIL: authenticated user_reports grants wrong';
  END IF;
  RAISE NOTICE 'PASS: user_reports grants';

  -- service_role unaffected
  IF NOT has_table_privilege('service_role','public.users','UPDATE')
     OR NOT has_table_privilege('service_role','public.user_tokens','UPDATE') THEN
    RAISE EXCEPTION 'FAIL: service_role lost access';
  END IF;
END $$;

SELECT pg_temp.expect_denied('anon', $$SELECT 1 FROM public.user_reports LIMIT 1$$, 'SELECT user_reports');

-- ---- TASK-876 ---------------------------------------------------------------------
SELECT pg_temp.expect_denied('anon', $$SELECT 1 FROM public.prompt_templates LIMIT 1$$, 'SELECT prompt_templates');
SELECT pg_temp.expect_denied('authenticated', $$SELECT 1 FROM public.llm_calls LIMIT 1$$, 'SELECT llm_calls');
SELECT pg_temp.expect_denied('authenticated', $$DELETE FROM public.exercises WHERE false$$, 'DELETE exercises');

DO $$
DECLARE bad text;
BEGIN
  SELECT string_agg(c.relname, ', ') INTO bad
    FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
   WHERE n.nspname='public' AND c.relkind='r' AND NOT c.relrowsecurity;
  IF bad IS NOT NULL THEN RAISE EXCEPTION 'FAIL: RLS still off on: %', bad; END IF;

  SELECT string_agg(c.relname, ', ') INTO bad
    FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
   WHERE n.nspname='public' AND c.relkind='S'
     AND (has_sequence_privilege('anon', c.oid, 'USAGE,SELECT,UPDATE')
          OR has_sequence_privilege('authenticated', c.oid, 'USAGE,SELECT,UPDATE'));
  IF bad IS NOT NULL THEN RAISE EXCEPTION 'FAIL: client sequence privileges remain: %', bad; END IF;
  RAISE NOTICE 'PASS: RLS on for every public table, no client sequence privileges';
END $$;

ROLLBACK;
