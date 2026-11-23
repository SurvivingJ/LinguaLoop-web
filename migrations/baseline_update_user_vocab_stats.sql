-- ============================================================================
-- baseline_update_user_vocab_stats.sql — repo record of the live public.update_user_vocab_stats
-- ============================================================================
--
-- WHAT: Trigger function: sets NEW.total_senses_tracked to the number of keys in NEW.sense_learning_stats.
-- Used by: No trigger uses it live (checked pg_trigger 2026-11-23) and no app caller: dead (finding F-08).
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
-- whitespace removed = 5ba36f7897a9c6e157e33efe085bcc4b), and the attributes, owner and grants
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
--            = '5ba36f7897a9c6e157e33efe085bcc4b' AS body_matches,
--          p.prosecdef AS definer, p.proconfig AS search_path, pg_get_userbyid(p.proowner) AS owner,
--          has_function_privilege('anon', p.oid, 'EXECUTE') AS anon_x,
--          has_function_privilege('authenticated', p.oid, 'EXECUTE') AS auth_x,
--          has_function_privilege('service_role', p.oid, 'EXECUTE') AS service_x
--     FROM pg_proc p WHERE p.oid = 'public.update_user_vocab_stats()'::regprocedure;
--
-- ROLLBACK: none needed (the file changes nothing). If a later edit of this
-- file is applied by mistake, re-apply this file at the commit that added it.
--
-- Idempotent: CREATE OR REPLACE + REVOKE/GRANT; safe to re-run.
-- ============================================================================

CREATE OR REPLACE FUNCTION public.update_user_vocab_stats()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
  NEW.total_senses_tracked := (
    SELECT COUNT(*) FROM jsonb_object_keys(NEW.sense_learning_stats)
  );
  RETURN NEW;
END;
$function$;
ALTER FUNCTION public.update_user_vocab_stats() OWNER TO postgres;
REVOKE ALL ON FUNCTION public.update_user_vocab_stats() FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.update_user_vocab_stats() TO service_role;
