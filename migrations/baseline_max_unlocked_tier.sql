-- ============================================================================
-- baseline_max_unlocked_tier.sql — repo record of the live public.max_unlocked_tier
-- ============================================================================
--
-- WHAT: Measure-word drill: highest classifier difficulty tier the user has unlocked (a tier unlocks the next when >= 80% of its classifiers are at mastery level >= 2).
-- Used by: Called by get_classifier_drill_session_v2 (live).
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
-- whitespace removed = 8088996a327a31b9fd33e8271f9d5f3d), and the attributes, owner and grants
-- are the live ones. It exists so the repo can rebuild the database and so the
-- next change to this function has a file to start from.
--
-- PRECONDITIONS: none beyond the tables/functions the body reads, all live.
--
-- VERIFY (read-only; run before and after; expect body_matches = true,
-- definer = true, search_path = {search_path=public, pg_temp}, anon_x = false, auth_x = false,
-- service_x = true):
--   SELECT md5(regexp_replace(regexp_replace(p.prosrc, '--[^\n]*', '', 'g'), '\s', '', 'g'))
--            = '8088996a327a31b9fd33e8271f9d5f3d' AS body_matches,
--          p.prosecdef AS definer, p.proconfig AS search_path, pg_get_userbyid(p.proowner) AS owner,
--          has_function_privilege('anon', p.oid, 'EXECUTE') AS anon_x,
--          has_function_privilege('authenticated', p.oid, 'EXECUTE') AS auth_x,
--          has_function_privilege('service_role', p.oid, 'EXECUTE') AS service_x
--     FROM pg_proc p WHERE p.oid = 'public.max_unlocked_tier(uuid,smallint)'::regprocedure;
--
-- ROLLBACK: none needed (the file changes nothing). If a later edit of this
-- file is applied by mistake, re-apply this file at the commit that added it.
--
-- Idempotent: CREATE OR REPLACE + REVOKE/GRANT; safe to re-run.
-- ============================================================================

CREATE OR REPLACE FUNCTION public.max_unlocked_tier(p_user_id uuid, p_language_id smallint)
 RETURNS smallint
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
 SET search_path TO 'public', 'pg_temp'
AS $function$
DECLARE
    v_unlocked smallint := 1;
    v_t smallint;
    v_total integer;
    v_mastered integer;
BEGIN
    FOR v_t IN 1..3 LOOP
        SELECT COUNT(*) INTO v_total
          FROM dim_classifiers
         WHERE language_id = p_language_id
           AND difficulty_tier = v_t;

        SELECT COUNT(*) INTO v_mastered
          FROM dim_classifiers c
          JOIN user_classifier_mastery m
            ON m.classifier_id = c.id
           AND m.user_id = p_user_id
         WHERE c.language_id = p_language_id
           AND c.difficulty_tier = v_t
           AND m.current_level >= 2;

        IF v_total > 0 AND (v_mastered::numeric / v_total) >= 0.80 THEN
            v_unlocked := v_t + 1;
        ELSE
            EXIT;
        END IF;
    END LOOP;

    RETURN v_unlocked;
END;
$function$;
ALTER FUNCTION public.max_unlocked_tier(uuid,smallint) OWNER TO postgres;
REVOKE ALL ON FUNCTION public.max_unlocked_tier(uuid,smallint) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.max_unlocked_tier(uuid,smallint) TO service_role;
