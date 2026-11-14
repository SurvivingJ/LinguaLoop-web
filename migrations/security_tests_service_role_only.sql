-- =============================================================================
-- security_tests_service_role_only.sql  (codebase review 2026-11, Security)
-- =============================================================================
-- Purpose: `tests` is readable by every signed-in user straight through
-- PostgREST. The `tests_select` policy (rls_tests_single_select_policy.sql)
-- allows any `authenticated` caller to SELECT every active row, including
-- `transcript` (the dictation answer key) and premium-tier tests, so the tier
-- gating done in Flask can be bypassed with the public anon key plus a login.
-- Flask reads `tests` with the service role only, so no client access is needed.
--
-- Result:
--   tests : RLS stays on, NO policy, NO privilege for PUBLIC / anon /
--           authenticated (service_role only, like `questions`).
--
-- Pre-checks (run these first; all must come back clean):
--   1. No browser code reads the table. In the repo:
--        grep -rnE "from\(['\"]tests['\"]\)|createClient\(" static templates
--      must print nothing (there is no browser Supabase client today).
--   2. No Python reads it with a user-JWT or anon client:
--        grep -rnE "table\(['\"]tests['\"]\)" routes services middleware utils
--      and confirm each hit uses supabase_service / get_supabase_admin() /
--      TestService.admin. Any `supabase_service or supabase` fallback to the
--      anon client stops returning rows once this is applied, so the
--      service-role key must be configured in every environment.
--   3. Nothing a client role can still reach depends on reading `tests` as the
--      caller. The guard below refuses to run if an RLS policy on another table
--      references `tests`, or if a view that reads `tests` is selectable by
--      anon/authenticated. It cannot see inside function bodies, so also check:
--        SELECT p.oid::regprocedure FROM pg_proc p
--         WHERE p.pronamespace = 'public'::regnamespace AND NOT p.prosecdef
--           AND has_function_privilege('authenticated', p.oid, 'EXECUTE')
--           AND p.prosrc ~* '\mtests\M';
--      (expected: no rows, or only functions no client calls).
--   4. Current state, for the rollback:
--        SELECT policyname, cmd, roles, qual FROM pg_policies
--         WHERE schemaname = 'public' AND tablename = 'tests';
--        SELECT grantee, privilege_type FROM information_schema.role_table_grants
--         WHERE table_schema = 'public' AND table_name = 'tests';
--
-- Policies are dropped by catalog lookup, not by name: the live name is
-- `tests_select` if rls_tests_single_select_policy.sql was applied, otherwise
-- the three policies that file replaces.
--
-- Idempotent and re-runnable. DDL only; no row is touched.
-- REQUIRES USER APPROVAL TO APPLY LIVE.
--
-- Rollback (restores the state left by rls_tests_single_select_policy.sql):
--   GRANT SELECT ON public.tests TO authenticated;
--   CREATE POLICY tests_select ON public.tests AS PERMISSIVE FOR SELECT TO authenticated
--     USING (is_active IS TRUE OR public.is_moderator((SELECT auth.uid())));
-- =============================================================================

BEGIN;

DO $$
DECLARE
  v_found text;
  p record;
BEGIN
  -- Guard 1: an RLS policy on another table that reads `tests` would start
  -- failing with "permission denied" for the client roles it serves.
  SELECT string_agg(format('%I.%I', tablename, policyname), ', ') INTO v_found
    FROM pg_policies
   WHERE schemaname = 'public' AND tablename <> 'tests'
     AND (coalesce(qual, '') ~* '\mtests\M' OR coalesce(with_check, '') ~* '\mtests\M');
  IF v_found IS NOT NULL THEN
    RAISE EXCEPTION 'policies on other tables read public.tests (%); review before locking tests', v_found;
  END IF;

  -- Guard 2: a view over `tests` that a client role can select.
  SELECT string_agg(DISTINCT c.oid::regclass::text, ', ') INTO v_found
    FROM pg_depend d
    JOIN pg_rewrite r ON r.oid = d.objid AND d.classid = 'pg_rewrite'::regclass
    JOIN pg_class c ON c.oid = r.ev_class AND c.relkind IN ('v', 'm')
   WHERE d.refclassid = 'pg_class'::regclass
     AND d.refobjid = 'public.tests'::regclass
     AND (has_table_privilege('authenticated', c.oid, 'SELECT')
          OR has_table_privilege('anon', c.oid, 'SELECT'));
  IF v_found IS NOT NULL THEN
    RAISE EXCEPTION 'client-readable views read public.tests (%); review before locking tests', v_found;
  END IF;

  FOR p IN SELECT policyname FROM pg_policies
            WHERE schemaname = 'public' AND tablename = 'tests'
  LOOP
    EXECUTE format('DROP POLICY %I ON public.tests', p.policyname);
  END LOOP;
END $$;

ALTER TABLE public.tests ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.tests FROM PUBLIC, anon, authenticated;
-- service_role / postgres grants are intentionally untouched.

-- Verify: nothing left for client roles.
DO $$
DECLARE
  r text;
  priv text;
BEGIN
  IF EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'tests') THEN
    RAISE EXCEPTION 'public.tests still has a policy';
  END IF;
  FOREACH r IN ARRAY ARRAY['anon', 'authenticated'] LOOP
    FOREACH priv IN ARRAY ARRAY['SELECT', 'INSERT', 'UPDATE', 'DELETE'] LOOP
      IF has_table_privilege(r, 'public.tests', priv) THEN
        RAISE EXCEPTION '% still has % on public.tests', r, priv;
      END IF;
    END LOOP;
  END LOOP;
  IF EXISTS (SELECT 1 FROM information_schema.column_privileges
              WHERE table_schema = 'public' AND table_name = 'tests'
                AND grantee IN ('anon', 'authenticated', 'PUBLIC')) THEN
    RAISE EXCEPTION 'column-level grants remain on public.tests for a client role';
  END IF;
END $$;

COMMIT;
