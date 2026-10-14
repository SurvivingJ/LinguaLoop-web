-- =============================================================================
-- security_questions_tests_policies.sql  (TASK-882 part 2, security-hardening S14)
-- =============================================================================
-- Purpose: stop `questions` (which holds the answer key and explanation) and
-- `tests` from being readable/writable directly through PostgREST with the
-- public anon key, now that every application read goes through the Flask
-- service-role client:
--   * routes/tests.py            -> current_app.supabase_service
--   * services/test_service.py   -> self.admin (reads of tests/questions and
--                                   the flagged_inputs insert moved off the anon
--                                   client in the same change)
--
-- Result:
--   questions : RLS on, NO policy, NO client privileges  (service_role only).
--               The answer key can no longer be fetched before submitting.
--   tests     : RLS on; `authenticated` may SELECT active rows only; `anon` has
--               no access; no client INSERT/UPDATE/DELETE (drops
--               tests_user_create and any other non-SELECT policy).
--
-- "Tier-aware" read access (plan wording) is deliberately NOT implemented in
-- SQL: no browser caller reads these tables, so the narrowest safe state is
-- service-only for questions and active-rows-only SELECT for tests. Tier
-- gating stays in Flask. Revisit if a client-side Supabase reader is added.
--
-- Pre-flight (UNCONFIRMED against live: the Supabase project id was not
-- available to the authoring session, so live policy names/ACLs were not read.
-- The policy drops below are therefore name-agnostic, driven by pg_policies):
--   SELECT policyname, cmd, roles, qual FROM pg_policies
--    WHERE schemaname='public' AND tablename IN ('tests','questions');
--   SELECT grantee, privilege_type FROM information_schema.role_table_grants
--    WHERE table_schema='public' AND table_name IN ('tests','questions');
-- Also confirm no SECURITY INVOKER view/function used by a client role reads
-- these tables (e.g. get_recommended_tests runs as service_role here).
--
-- Idempotent and re-runnable. DDL only; no row is touched.
-- REQUIRES USER APPROVAL TO APPLY LIVE. Deploy the Flask change first.
-- =============================================================================

BEGIN;

ALTER TABLE public.questions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.tests     ENABLE ROW LEVEL SECURITY;

-- ---- questions: drop every policy (incl. questions_read), revoke client access -
DO $$
DECLARE p record;
BEGIN
  FOR p IN SELECT policyname FROM pg_policies
            WHERE schemaname = 'public' AND tablename = 'questions'
  LOOP
    EXECUTE format('DROP POLICY IF EXISTS %I ON public.questions', p.policyname);
  END LOOP;
END $$;

REVOKE ALL ON public.questions FROM PUBLIC, anon, authenticated;

-- ---- tests: drop every non-SELECT policy (tests_user_create etc.) and the
--      broad public read; replace with authenticated active-rows read ----------
DO $$
DECLARE p record;
BEGIN
  FOR p IN SELECT policyname FROM pg_policies
            WHERE schemaname = 'public' AND tablename = 'tests'
              AND (cmd <> 'SELECT' OR policyname = 'tests_public_read')
  LOOP
    EXECUTE format('DROP POLICY IF EXISTS %I ON public.tests', p.policyname);
  END LOOP;
END $$;

DROP POLICY IF EXISTS tests_authenticated_read ON public.tests;
CREATE POLICY tests_authenticated_read ON public.tests
  FOR SELECT TO authenticated
  USING (is_active IS TRUE);

REVOKE ALL ON public.tests FROM PUBLIC, anon, authenticated;
GRANT SELECT ON public.tests TO authenticated;
-- service_role keeps its own grants and bypasses RLS (unchanged).

COMMIT;

-- Verification (read-only):
--   SET LOCAL ROLE authenticated; SELECT 1 FROM public.questions LIMIT 1;  -- permission denied
--   SET LOCAL ROLE anon;          SELECT 1 FROM public.tests LIMIT 1;      -- permission denied
--   SET LOCAL ROLE authenticated; INSERT INTO public.tests (...) ...;      -- permission denied
