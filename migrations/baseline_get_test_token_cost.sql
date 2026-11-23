-- ============================================================================
-- baseline_get_test_token_cost.sql — repo record of the live public.get_test_token_cost
-- ============================================================================
--
-- WHAT: Returns the token cost of one test for the user's subscription tier (tokens_per_test, default 10).
-- Used by: Called by the five submission RPCs (process_test_submission, process_dictation_submission, process_pinyin_submission, process_pitch_accent_submission, process_classifier_drill_submission).
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
-- whitespace removed = 806d5a069795596630b4a293a0f094a0), and the attributes, owner and grants
-- are the live ones. It exists so the repo can rebuild the database and so the
-- next change to this function has a file to start from.
--
-- PRECONDITIONS: none beyond the tables/functions the body reads, all live.
--
-- VERIFY (read-only; run before and after; expect body_matches = true,
-- definer = true, search_path = {search_path=public, pg_temp}, anon_x = false, auth_x = false,
-- service_x = true):
--   SELECT md5(regexp_replace(regexp_replace(p.prosrc, '--[^\n]*', '', 'g'), '\s', '', 'g'))
--            = '806d5a069795596630b4a293a0f094a0' AS body_matches,
--          p.prosecdef AS definer, p.proconfig AS search_path, pg_get_userbyid(p.proowner) AS owner,
--          has_function_privilege('anon', p.oid, 'EXECUTE') AS anon_x,
--          has_function_privilege('authenticated', p.oid, 'EXECUTE') AS auth_x,
--          has_function_privilege('service_role', p.oid, 'EXECUTE') AS service_x
--     FROM pg_proc p WHERE p.oid = 'public.get_test_token_cost(uuid)'::regprocedure;
--
-- ROLLBACK: none needed (the file changes nothing). If a later edit of this
-- file is applied by mistake, re-apply this file at the commit that added it.
--
-- Idempotent: CREATE OR REPLACE + REVOKE/GRANT; safe to re-run.
-- ============================================================================

CREATE OR REPLACE FUNCTION public.get_test_token_cost(p_user_id uuid)
 RETURNS integer
 LANGUAGE sql
 STABLE SECURITY DEFINER
 SET search_path TO 'public', 'pg_temp'
AS $function$
  SELECT COALESCE(dst.tokens_per_test, 10)
  FROM users u
  JOIN dim_subscription_tiers dst ON u.subscription_tier_id = dst.id
  WHERE u.id = p_user_id AND u.deleted_at IS NULL;
$function$;
ALTER FUNCTION public.get_test_token_cost(uuid) OWNER TO postgres;
REVOKE ALL ON FUNCTION public.get_test_token_cost(uuid) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.get_test_token_cost(uuid) TO service_role;
