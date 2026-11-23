-- ============================================================================
-- baseline_add_tokens_atomic.sql — repo record of the live public.add_tokens_atomic
-- ============================================================================
--
-- WHAT: Placeholder token-credit RPC: checks the caller may credit tokens for p_user_id (self, admin or moderator) and returns true. It adds no tokens (the body is a Phase 3 TODO).
-- Used by: No caller in routes/, services/, scripts/, web/ (finding F-08); token credit runs through process_stripe_payment.
--
-- WHY: this function exists live but had no CREATE in any migrations/ file
-- (including archive/): finding F-03 of the 2026-11-23 database review. The
-- definition below is pg_get_functiondef() read from live
-- (kpfqrjtfxmujzolwsvdq) on 2026-11-23, with CRLF line ends normalised to LF,
-- plus the live owner and the live ACL ({postgres=X/postgres,service_role=X/postgres}:
-- EXECUTE for service_role only, nothing for PUBLIC / anon / authenticated).
--
-- WHAT A LEARNER OR THE APP WOULD NOTICE: nothing. Applying this file is a
-- no-op: the body hashes equal to live (md5 of prosrc with -- comments and all
-- whitespace removed = 03bbee6ec90bd7bac714b76581c3ae20), and the attributes, owner and grants
-- are the live ones. It exists so the repo can rebuild the database and so the
-- next change to this function has a file to start from.
--
-- security-lint: allow-uid-compare verbatim capture of the live body; the
-- `p_user_id != auth.uid()` gate is NULL-permissive, but EXECUTE is
-- service_role-only so no client can reach it. Fixing the gate is a real
-- change and belongs in its own migration, not in this capture.
--
-- PRECONDITIONS: none beyond the tables/functions the body reads, all live.
--
-- VERIFY (read-only; run before and after; expect body_matches = true,
-- definer = true, search_path = {search_path=public, pg_temp}, anon_x = false, auth_x = false,
-- service_x = true):
--   SELECT md5(regexp_replace(regexp_replace(p.prosrc, '--[^\n]*', '', 'g'), '\s', '', 'g'))
--            = '03bbee6ec90bd7bac714b76581c3ae20' AS body_matches,
--          p.prosecdef AS definer, p.proconfig AS search_path, pg_get_userbyid(p.proowner) AS owner,
--          has_function_privilege('anon', p.oid, 'EXECUTE') AS anon_x,
--          has_function_privilege('authenticated', p.oid, 'EXECUTE') AS auth_x,
--          has_function_privilege('service_role', p.oid, 'EXECUTE') AS service_x
--     FROM pg_proc p WHERE p.oid = 'public.add_tokens_atomic(uuid,integer,text,text,text,text)'::regprocedure;
--
-- ROLLBACK: none needed (the file changes nothing). If a later edit of this
-- file is applied by mistake, re-apply this file at the commit that added it.
--
-- Idempotent: CREATE OR REPLACE + REVOKE/GRANT; safe to re-run.
-- ============================================================================

CREATE OR REPLACE FUNCTION public.add_tokens_atomic(p_user_id uuid, p_tokens_to_add integer, p_action text, p_idempotency_key text, p_payment_intent_id text DEFAULT NULL::text, p_package_id text DEFAULT NULL::text)
 RETURNS boolean
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public', 'pg_temp'
AS $function$
BEGIN
  -- SECURITY: Allow only self-service OR admin/moderator role
  IF p_user_id != auth.uid() THEN
    IF NOT (is_admin(auth.uid()) OR is_moderator(auth.uid())) THEN
      RAISE EXCEPTION 'Unauthorized: Cannot add tokens for another user';
    END IF;
  END IF;

  -- TODO: Token addition logic will be implemented in Phase 3
  -- For now, just validate authorization

  RETURN true;
END;
$function$;
ALTER FUNCTION public.add_tokens_atomic(uuid,integer,text,text,text,text) OWNER TO postgres;
REVOKE ALL ON FUNCTION public.add_tokens_atomic(uuid,integer,text,text,text,text) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.add_tokens_atomic(uuid,integer,text,text,text,text) TO service_role;
