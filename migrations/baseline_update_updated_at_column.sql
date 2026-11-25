-- ============================================================================
-- baseline_update_updated_at_column.sql — repo record of the live public.update_updated_at_column
-- ============================================================================
--
-- WHAT: Trigger function: sets NEW.updated_at = now() before an UPDATE.
-- Used by: BEFORE UPDATE triggers on seven public tables (definitions below, for reference).
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
-- whitespace removed = 976aa1a9d8a76703090d1a9459f8e6c2), and the attributes, owner and grants
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
--            = '976aa1a9d8a76703090d1a9459f8e6c2' AS body_matches,
--          p.prosecdef AS definer, p.proconfig AS search_path, pg_get_userbyid(p.proowner) AS owner,
--          has_function_privilege('anon', p.oid, 'EXECUTE') AS anon_x,
--          has_function_privilege('authenticated', p.oid, 'EXECUTE') AS auth_x,
--          has_function_privilege('service_role', p.oid, 'EXECUTE') AS service_x
--     FROM pg_proc p WHERE p.oid = 'public.update_updated_at_column()'::regprocedure;
--
-- ROLLBACK: none needed (the file changes nothing). If a later edit of this
-- file is applied by mistake, re-apply this file at the commit that added it.
--
-- Idempotent: CREATE OR REPLACE + REVOKE/GRANT; safe to re-run.
-- ============================================================================

-- Live trigger(s) using this function, for reference only (not created here):
--   CREATE TRIGGER update_vocab_timestamp BEFORE UPDATE ON public.dim_vocabulary FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
--   CREATE TRIGGER update_sense_timestamp BEFORE UPDATE ON public.dim_word_senses FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
--   CREATE TRIGGER update_tests_updated_at BEFORE UPDATE ON public.tests FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
--   CREATE TRIGGER update_user_languages_updated_at BEFORE UPDATE ON public.user_languages FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
--   CREATE TRIGGER update_user_reports_updated_at BEFORE UPDATE ON public.user_reports FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
--   CREATE TRIGGER update_user_skill_ratings_updated_at BEFORE UPDATE ON public.user_skill_ratings FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
--   CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON public.users FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE OR REPLACE FUNCTION public.update_updated_at_column()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$function$;
ALTER FUNCTION public.update_updated_at_column() OWNER TO postgres;
REVOKE ALL ON FUNCTION public.update_updated_at_column() FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.update_updated_at_column() TO service_role;
