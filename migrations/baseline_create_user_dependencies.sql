-- ============================================================================
-- baseline_create_user_dependencies.sql — repo record of the live public.create_user_dependencies
-- ============================================================================
--
-- WHAT: Trigger function: after a public.users row is inserted, creates its user_tokens row (0 purchased tokens) if missing.
-- Used by: Trigger create_user_dependencies_trigger on public.users (definition below, for reference).
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
-- whitespace removed = d56d74cb837c8a831f27864c5ee69563), and the attributes, owner and grants
-- are the live ones. It exists so the repo can rebuild the database and so the
-- next change to this function has a file to start from.
--
-- Live this function is SECURITY INVOKER with no pinned search_path; reproduced as live
-- (advisor function_search_path_mutable, finding F-14, is a separate task).
--
-- PRECONDITIONS: none beyond the tables/functions the body reads, all live.
--
-- VERIFY (read-only; run before and after; expect body_matches = true,
-- definer = false, search_path = NULL, anon_x = false, auth_x = false,
-- service_x = true):
--   SELECT md5(regexp_replace(regexp_replace(p.prosrc, '--[^\n]*', '', 'g'), '\s', '', 'g'))
--            = 'd56d74cb837c8a831f27864c5ee69563' AS body_matches,
--          p.prosecdef AS definer, p.proconfig AS search_path, pg_get_userbyid(p.proowner) AS owner,
--          has_function_privilege('anon', p.oid, 'EXECUTE') AS anon_x,
--          has_function_privilege('authenticated', p.oid, 'EXECUTE') AS auth_x,
--          has_function_privilege('service_role', p.oid, 'EXECUTE') AS service_x
--     FROM pg_proc p WHERE p.oid = 'public.create_user_dependencies()'::regprocedure;
--
-- ROLLBACK: none needed (the file changes nothing). If a later edit of this
-- file is applied by mistake, re-apply this file at the commit that added it.
--
-- Idempotent: CREATE OR REPLACE + REVOKE/GRANT; safe to re-run.
-- ============================================================================

-- Live trigger(s) using this function, for reference only (not created here):
--   CREATE TRIGGER create_user_dependencies_trigger AFTER INSERT ON public.users FOR EACH ROW EXECUTE FUNCTION create_user_dependencies();

CREATE OR REPLACE FUNCTION public.create_user_dependencies()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
    INSERT INTO user_tokens (user_id, purchased_tokens)
    VALUES (NEW.id, 0)
    ON CONFLICT (user_id) DO NOTHING;

    RETURN NEW;
END;
$function$;
ALTER FUNCTION public.create_user_dependencies() OWNER TO postgres;
REVOKE ALL ON FUNCTION public.create_user_dependencies() FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.create_user_dependencies() TO service_role;
