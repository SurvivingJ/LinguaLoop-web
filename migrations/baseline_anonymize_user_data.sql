-- ============================================================================
-- baseline_anonymize_user_data.sql — repo record of the live public.anonymize_user_data
-- ============================================================================
--
-- WHAT: Soft-deletes and anonymises one public.users row (email, display_name, deleted_at, anonymized_at).
-- Used by: No caller in the app code (finding F-08).
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
-- whitespace removed = f13c400324f5d6c0bd773bbe00554ebb), and the attributes, owner and grants
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
--            = 'f13c400324f5d6c0bd773bbe00554ebb' AS body_matches,
--          p.prosecdef AS definer, p.proconfig AS search_path, pg_get_userbyid(p.proowner) AS owner,
--          has_function_privilege('anon', p.oid, 'EXECUTE') AS anon_x,
--          has_function_privilege('authenticated', p.oid, 'EXECUTE') AS auth_x,
--          has_function_privilege('service_role', p.oid, 'EXECUTE') AS service_x
--     FROM pg_proc p WHERE p.oid = 'public.anonymize_user_data(uuid)'::regprocedure;
--
-- ROLLBACK: none needed (the file changes nothing). If a later edit of this
-- file is applied by mistake, re-apply this file at the commit that added it.
--
-- Idempotent: CREATE OR REPLACE + REVOKE/GRANT; safe to re-run.
-- ============================================================================

CREATE OR REPLACE FUNCTION public.anonymize_user_data(p_user_id uuid)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public', 'pg_temp'
AS $function$
BEGIN
  -- Verify caller owns this user_id OR is admin
  IF p_user_id != auth.uid() AND NOT is_admin(auth.uid()) THEN
    RAISE EXCEPTION 'Unauthorized: Cannot anonymize another user';
  END IF;

  -- Soft delete and anonymize
  UPDATE users
  SET
    email = 'deleted-' || id || '@lingualoop.local',
    display_name = 'Deleted User',
    deleted_at = NOW(),
    anonymized_at = NOW()
  WHERE id = p_user_id;

  RAISE NOTICE 'User % anonymized successfully', p_user_id;
END;
$function$;
ALTER FUNCTION public.anonymize_user_data(uuid) OWNER TO postgres;
REVOKE ALL ON FUNCTION public.anonymize_user_data(uuid) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.anonymize_user_data(uuid) TO service_role;
