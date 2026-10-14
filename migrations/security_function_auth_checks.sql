-- ============================================================================
-- SECURITY (TASK-877, decision 6) - in-function auth.uid() checks for the only
-- functions that must REMAIN executable by anon / authenticated
-- Date: 2026-10-14
-- security-lint: allow-definer-exposed is_admin/is_moderator are RLS helpers that must stay callable, guarded in-function, ADR-034
-- REQUIRES USER APPROVAL TO APPLY LIVE.  Apply after
-- security_function_grants_group_b.sql.
--
-- Developer decision 6: add in-function auth.uid() checks ONLY to functions that
-- stay EXECUTE-able by authenticated after hardening.  The allowlist derived
-- from the caller map (see group B header) contains exactly two functions:
--
--   public.is_admin(uuid)       - used by ~20 RLS policies (TO public)
--   public.is_moderator(uuid)   - used by tests_moderator_view,
--                                 attempts_moderator_view
--
-- Every other function is service_role-only after group B and needs no check
-- (decision 6): process_*_submission, record_session_progress, calibration_*,
-- get_token_balance, anonymize_user_data, etc.
--
-- THE LEAK
--   Both are SECURITY DEFINER and take an arbitrary uuid, so any client could
--   call POST /rest/v1/rpc/is_admin {"p_user_id": "<victim>"} and learn whether
--   any user holds an admin / moderator tier (user enumeration + target
--   selection for the users/tier escalation paths in TASK-875).
--
-- THE FIX
--   For callers whose JWT role is anon or authenticated, the answer is only
--   given when p_user_id is the caller's own auth.uid(); otherwise false.
--   Policies always pass auth.uid(), so their behaviour is unchanged.
--   service_role / postgres / direct connections (auth.role() NULL or
--   'service_role') are unrestricted, so SECURITY DEFINER callers invoked by
--   Flask (get_token_balance, add_tokens_atomic, anonymize_user_data, ...) keep
--   working: auth.role() reads the request JWT, which a nested call inherits.
--   anon (auth.uid() NULL): NULL IS DISTINCT FROM NULL is false, so policy
--   evaluation for anon falls through to the normal lookup (returns NULL for no
--   user) exactly as before.
--
-- BASE
--   Starting point is the LIVE definition, read via pg_get_functiondef on
--   2026-10-14 (LANGUAGE sql, STABLE, SECURITY DEFINER, search_path =
--   public, pg_temp, body = join users/dim_subscription_tiers with
--   deleted_at IS NULL).  Only the CASE guard is new.  Signature, volatility,
--   ownership and ACL are unchanged (CREATE OR REPLACE keeps the ACL; no
--   function in the repo's migrations/ currently defines these two - they were
--   created outside migrations/, so THIS FILE is now their canonical
--   definition).  No-row semantics preserved: the scalar subquery still yields
--   NULL for an unknown / deleted user (callers' `IF NOT is_admin(..)` behave
--   as before); only the denied branch returns false.
--
-- Idempotent: CREATE OR REPLACE.
-- ROLLBACK: re-create the two functions without the CASE (body = live def above).
-- ============================================================================

BEGIN;

CREATE OR REPLACE FUNCTION public.is_admin(p_user_id uuid)
 RETURNS boolean
 LANGUAGE sql
 STABLE SECURITY DEFINER
 SET search_path TO 'public', 'pg_temp'
AS $function$
  SELECT CASE
    WHEN (SELECT auth.role()) IN ('anon', 'authenticated')
         AND p_user_id IS DISTINCT FROM (SELECT auth.uid())
    THEN false
    ELSE (
      SELECT COALESCE(dst.is_admin, false)
      FROM users u
      JOIN dim_subscription_tiers dst ON u.subscription_tier_id = dst.id
      WHERE u.id = p_user_id AND u.deleted_at IS NULL
    )
  END;
$function$;

CREATE OR REPLACE FUNCTION public.is_moderator(p_user_id uuid)
 RETURNS boolean
 LANGUAGE sql
 STABLE SECURITY DEFINER
 SET search_path TO 'public', 'pg_temp'
AS $function$
  SELECT CASE
    WHEN (SELECT auth.role()) IN ('anon', 'authenticated')
         AND p_user_id IS DISTINCT FROM (SELECT auth.uid())
    THEN false
    ELSE (
      SELECT COALESCE(dst.is_moderator OR dst.is_admin, false)
      FROM users u
      JOIN dim_subscription_tiers dst ON u.subscription_tier_id = dst.id
      WHERE u.id = p_user_id AND u.deleted_at IS NULL
    )
  END;
$function$;

COMMENT ON FUNCTION public.is_admin(uuid) IS
    'RLS helper. For anon/authenticated JWTs only answers for the caller''s own auth.uid() (else false). See migrations/security_function_auth_checks.sql.';
COMMENT ON FUNCTION public.is_moderator(uuid) IS
    'RLS helper. For anon/authenticated JWTs only answers for the caller''s own auth.uid() (else false). See migrations/security_function_auth_checks.sql.';

-- Post-condition: still executable by the roles that evaluate policies, still
-- pinned, still STABLE SECURITY DEFINER.
DO $$
DECLARE
    f regprocedure;
BEGIN
    FOREACH f IN ARRAY ARRAY['public.is_admin(uuid)'::regprocedure, 'public.is_moderator(uuid)'::regprocedure] LOOP
        IF NOT (has_function_privilege('anon', f, 'EXECUTE')
            AND has_function_privilege('authenticated', f, 'EXECUTE')
            AND has_function_privilege('service_role', f, 'EXECUTE')) THEN
            RAISE EXCEPTION 'TASK-877 auth checks: % lost EXECUTE for a policy-evaluating role', f;
        END IF;
        IF NOT EXISTS (SELECT 1 FROM pg_proc p
                       WHERE p.oid = f AND p.prosecdef AND p.provolatile = 's'
                         AND EXISTS (SELECT 1 FROM unnest(p.proconfig) c WHERE c LIKE 'search_path=%')) THEN
            RAISE EXCEPTION 'TASK-877 auth checks: % is not STABLE SECURITY DEFINER with pinned search_path', f;
        END IF;
    END LOOP;
END
$$;

COMMIT;

-- Verification (staging / in a rolled-back transaction):
--   BEGIN;
--   SET LOCAL ROLE authenticated;
--   SET LOCAL request.jwt.claims = '{"sub":"<non-admin uuid>","role":"authenticated"}';
--   SELECT public.is_admin('<admin uuid>');            -- expect false (was true)
--   SELECT public.is_admin('<non-admin uuid>');        -- expect false
--   SET LOCAL request.jwt.claims = '{"sub":"<admin uuid>","role":"authenticated"}';
--   SELECT public.is_admin('<admin uuid>');            -- expect true
--   ROLLBACK;
