-- ============================================================================
-- baseline_handle_new_user.sql — repo record of the live public.handle_new_user
-- ============================================================================
--
-- WHAT: Trigger function on auth.users: after Supabase Auth creates an account, creates (or refreshes) the matching public.users profile on the free tier, creating the free tier row if it is missing. Errors are logged as WARNING and swallowed so sign-up never fails.
-- Used by: Trigger on_auth_user_created on auth.users (definition below, for reference only: it lives in the auth schema, which Supabase manages; this file does not create or replace it).
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
-- whitespace removed = 86f122350bd2b56c67ce6366246d7fea), and the attributes, owner and grants
-- are the live ones. It exists so the repo can rebuild the database and so the
-- next change to this function has a file to start from.
--
-- PRECONDITIONS: none beyond the tables/functions the body reads, all live.
--
-- VERIFY (read-only; run before and after; expect body_matches = true,
-- definer = true, search_path = {search_path=public, pg_temp}, anon_x = false, auth_x = false,
-- service_x = true):
--   SELECT md5(regexp_replace(regexp_replace(p.prosrc, '--[^\n]*', '', 'g'), '\s', '', 'g'))
--            = '86f122350bd2b56c67ce6366246d7fea' AS body_matches,
--          p.prosecdef AS definer, p.proconfig AS search_path, pg_get_userbyid(p.proowner) AS owner,
--          has_function_privilege('anon', p.oid, 'EXECUTE') AS anon_x,
--          has_function_privilege('authenticated', p.oid, 'EXECUTE') AS auth_x,
--          has_function_privilege('service_role', p.oid, 'EXECUTE') AS service_x
--     FROM pg_proc p WHERE p.oid = 'public.handle_new_user()'::regprocedure;
--
-- ROLLBACK: none needed (the file changes nothing). If a later edit of this
-- file is applied by mistake, re-apply this file at the commit that added it.
--
-- Idempotent: CREATE OR REPLACE + REVOKE/GRANT; safe to re-run.
-- ============================================================================

-- Live trigger(s) using this function, for reference only (not created here):
--   CREATE TRIGGER on_auth_user_created AFTER INSERT ON auth.users FOR EACH ROW EXECUTE FUNCTION handle_new_user();

CREATE OR REPLACE FUNCTION public.handle_new_user()
 RETURNS trigger
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public', 'pg_temp'
AS $function$
DECLARE
    v_free_tier_id integer;
BEGIN
    -- Get the ID of the 'free' subscription tier
    SELECT id INTO v_free_tier_id
    FROM dim_subscription_tiers
    WHERE tier_code = 'free'
    LIMIT 1;

    -- If free tier doesn't exist, create it
    IF v_free_tier_id IS NULL THEN
        INSERT INTO dim_subscription_tiers (
            tier_code,
            display_name,
            can_generate_tests,
            can_create_custom_tests,
            daily_free_tests
        )
        VALUES ('free', 'Free', false, false, 2)
        RETURNING id INTO v_free_tier_id;

        RAISE LOG 'Created free tier with ID: %', v_free_tier_id;
    END IF;

    -- Insert into public.users with correct column name
    INSERT INTO public.users (
        id,
        email,
        subscription_tier_id,  -- ✅ FIXED: Changed from subscription_tier
        email_verified,
        created_at,
        last_login,
        total_tests_taken,
        total_tests_generated
    )
    VALUES (
        NEW.id,
        NEW.email,
        v_free_tier_id,  -- ✅ FIXED: Using tier ID instead of text
        COALESCE(NEW.email_confirmed_at IS NOT NULL, false),
        NOW(),
        NOW(),
        0,
        0
    )
    ON CONFLICT (id) DO UPDATE SET
        email = EXCLUDED.email,
        email_verified = COALESCE(NEW.email_confirmed_at IS NOT NULL, false),
        last_login = NOW();

    RAISE LOG 'User profile created successfully for: % (tier_id: %)', NEW.email, v_free_tier_id;

    RETURN NEW;

EXCEPTION WHEN OTHERS THEN
    -- Log the full error for debugging
    RAISE WARNING 'Failed to create user profile for %: % (SQLSTATE: %)',
        NEW.email, SQLERRM, SQLSTATE;
    -- Still return NEW so auth user creation doesn't fail
    RETURN NEW;
END;
$function$;
ALTER FUNCTION public.handle_new_user() OWNER TO postgres;
REVOKE ALL ON FUNCTION public.handle_new_user() FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.handle_new_user() TO service_role;
