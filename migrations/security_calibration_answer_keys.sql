-- =============================================================================
-- security_calibration_answer_keys.sql  (codebase review 2026-11, Security)
-- =============================================================================
-- Purpose: a signed-in user can read their own PENDING calibration answer keys
-- through PostgREST. calibration_sessions_and_ability.sql gives `authenticated`
-- an own-row policy and SELECT on calibration_response_options, whose `is_key`
-- column marks the correct option of an item that has been served but not yet
-- answered; calibration_responses exposes the same item's anchor sense.
-- (security_lock_progress_tables.sql narrowed both tables to read-only but kept
-- the read.) Flask reads and writes both tables through get_supabase_admin()
-- only (services/calibration_service.py, services/practice_session_service.py).
--
-- Result:
--   calibration_response_options : RLS on, NO policy, NO client privilege.
--   calibration_responses        : RLS on, NO client privilege. Its own-row
--                                  SELECT policy is left in place (inert without
--                                  the grant) so a rollback is one GRANT.
--
-- Pre-checks:
--   1. No client reads either table:
--        grep -rnE "calibration_response" static templates          -> nothing
--        grep -rnE "table\(['\"]calibration_response" routes services
--      and confirm every hit uses get_supabase_admin() / the service client.
--   2. Current state, for the rollback:
--        SELECT tablename, policyname, cmd, roles, qual FROM pg_policies
--         WHERE schemaname = 'public'
--           AND tablename IN ('calibration_responses', 'calibration_response_options');
--        SELECT table_name, grantee, privilege_type
--          FROM information_schema.role_table_grants
--         WHERE table_schema = 'public'
--           AND table_name IN ('calibration_responses', 'calibration_response_options');
--
-- Policies are dropped by catalog lookup, not by name (the live name is
-- `calibration_options_own`, `calibration_options_own (select)` or a merged
-- name, depending on which earlier migrations ran).
--
-- Idempotent and re-runnable. DDL only; no row is touched.
-- REQUIRES USER APPROVAL TO APPLY LIVE.
--
-- Rollback:
--   GRANT SELECT ON public.calibration_responses, public.calibration_response_options
--     TO authenticated;
--   CREATE POLICY calibration_options_own ON public.calibration_response_options
--     FOR SELECT TO authenticated
--     USING (EXISTS (SELECT 1 FROM public.calibration_responses r
--                     WHERE r.id = response_id AND r.user_id = (SELECT auth.uid())));
-- =============================================================================

BEGIN;

ALTER TABLE public.calibration_response_options ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.calibration_responses        ENABLE ROW LEVEL SECURITY;

DO $$
DECLARE p record;
BEGIN
  FOR p IN SELECT policyname FROM pg_policies
            WHERE schemaname = 'public' AND tablename = 'calibration_response_options'
  LOOP
    EXECUTE format('DROP POLICY %I ON public.calibration_response_options', p.policyname);
  END LOOP;
END $$;

REVOKE ALL ON TABLE public.calibration_response_options FROM PUBLIC, anon, authenticated;
REVOKE ALL ON TABLE public.calibration_responses        FROM PUBLIC, anon, authenticated;
-- service_role / postgres grants are intentionally untouched.

DO $$
DECLARE
  t text;
  r text;
  priv text;
BEGIN
  IF EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = 'public'
                AND tablename = 'calibration_response_options') THEN
    RAISE EXCEPTION 'calibration_response_options still has a policy';
  END IF;
  FOREACH t IN ARRAY ARRAY['calibration_response_options', 'calibration_responses'] LOOP
    FOREACH r IN ARRAY ARRAY['anon', 'authenticated'] LOOP
      FOREACH priv IN ARRAY ARRAY['SELECT', 'INSERT', 'UPDATE', 'DELETE'] LOOP
        IF has_table_privilege(r, format('public.%I', t), priv) THEN
          RAISE EXCEPTION '% still has % on public.%', r, priv, t;
        END IF;
      END LOOP;
    END LOOP;
  END LOOP;
END $$;

COMMIT;
