-- ============================================================================
-- SECURITY (TASK-877, Group A of 2) - payment / token-crediting functions
-- Date: 2026-10-14
-- REQUIRES USER APPROVAL TO APPLY LIVE.  Apply this file ALONE and FIRST, then
-- security_function_grants_group_b.sql, then security_function_auth_checks.sql.
--
-- THE HOLE (plan finding S3, critical)
--   process_stripe_payment(uuid,integer,text,text,integer) is SECURITY DEFINER
--   and live proacl is {=X, anon=X, authenticated=X, service_role=X}: an
--   anonymous PostgREST caller (anon key only) can credit purchased tokens to
--   ANY user id.  It also had no pinned search_path.
--
-- THE FIX
--   * REVOKE ALL FROM PUBLIC, anon, authenticated; GRANT EXECUTE TO service_role.
--   * Pin search_path = public, pg_temp where the function has none.
--   * Same treatment for the other token-crediting functions, every overload,
--     found by name in pg_proc (not by hand-typed signature):
--       add_tokens_atomic   (live; stub that credits tokens)
--       grant_daily_free_tokens (NOT in the live DB as of 2026-10-14 - it is
--                           called by routes/users.py and auth_service.py, so
--                           it is pending from another branch; NOTICE only.
--                           Group B's generic loop re-covers it once it exists)
--
-- CALLER MAP (verified 2026-10-14)
--   process_stripe_payment: NO caller anywhere in the repo (no Flask route, no
--   script, no static/js, no supabase/ edge function).  PaymentService
--   (services/payment_service.py) never calls it and get_payment_service() is
--   never invoked.  If a Stripe webhook is ever added it MUST use
--   get_supabase_admin() (service_role).  Nothing legitimate breaks.
--   add_tokens_atomic: no caller in the repo.
--   grant_daily_free_tokens: routes/users.py uses
--   `current_app.supabase_service or current_app.supabase` and
--   services/auth_service.py uses get_supabase_admin() - service_role in
--   production.  (The anon fallback in routes/users.py would stop working;
--   see report - it only matters if the service key is missing.)
--
-- Idempotent and re-runnable: REVOKE/GRANT/ALTER FUNCTION SET are no-ops when
-- already in the target state.  Raises if process_stripe_payment is not found
-- so a rename cannot slip through silently.
--
-- ROLLBACK (only if a legitimate service_role-less caller is discovered):
--   GRANT EXECUTE ON FUNCTION public.process_stripe_payment(uuid,integer,text,text,integer) TO authenticated;
--   (do NOT restore PUBLIC/anon.)
-- ============================================================================

BEGIN;

DO $$
DECLARE
    r        record;
    v_found  int;
    v_req    constant text[] := ARRAY['process_stripe_payment'];
    v_opt    constant text[] := ARRAY['add_tokens_atomic', 'grant_daily_free_tokens'];
    v_name   text;
BEGIN
    -- Required names must each match at least one function.
    FOREACH v_name IN ARRAY v_req LOOP
        SELECT count(*) INTO v_found
        FROM pg_proc p
        WHERE p.pronamespace = 'public'::regnamespace AND p.proname = v_name;
        IF v_found = 0 THEN
            RAISE EXCEPTION 'TASK-877 group A: required function public.% not found', v_name;
        END IF;
    END LOOP;

    -- Optional (pending) names: note when absent.
    FOREACH v_name IN ARRAY v_opt LOOP
        SELECT count(*) INTO v_found
        FROM pg_proc p
        WHERE p.pronamespace = 'public'::regnamespace AND p.proname = v_name;
        IF v_found = 0 THEN
            RAISE NOTICE 'TASK-877 group A: public.% not present (pending migration?) - skipped', v_name;
        END IF;
    END LOOP;

    FOR r IN
        SELECT p.oid::regprocedure AS sig, p.prosecdef,
               EXISTS (SELECT 1 FROM unnest(coalesce(p.proconfig, '{}'::text[])) c
                       WHERE c LIKE 'search_path=%') AS has_sp
        FROM pg_proc p
        WHERE p.pronamespace = 'public'::regnamespace
          AND p.proname = ANY (v_req || v_opt)
          AND p.prokind IN ('f', 'p')
        ORDER BY p.proname, p.oid
    LOOP
        EXECUTE format('REVOKE ALL ON FUNCTION %s FROM PUBLIC, anon, authenticated', r.sig);
        EXECUTE format('GRANT EXECUTE ON FUNCTION %s TO service_role', r.sig);
        IF r.prosecdef AND NOT r.has_sp THEN
            EXECUTE format('ALTER FUNCTION %s SET search_path = public, pg_temp', r.sig);
        END IF;
        RAISE NOTICE 'TASK-877 group A: hardened %', r.sig;
    END LOOP;
END
$$;

-- Post-condition: nothing in Group A is callable by a client role, and every
-- SECURITY DEFINER one has a pinned search_path.  Aborts (rolls back) otherwise.
DO $$
DECLARE
    r record;
BEGIN
    FOR r IN
        SELECT p.oid::regprocedure AS sig, p.prosecdef, p.proconfig
        FROM pg_proc p
        WHERE p.pronamespace = 'public'::regnamespace
          AND p.proname IN ('process_stripe_payment', 'add_tokens_atomic', 'grant_daily_free_tokens')
    LOOP
        IF has_function_privilege('anon', r.sig, 'EXECUTE')
           OR has_function_privilege('authenticated', r.sig, 'EXECUTE') THEN
            RAISE EXCEPTION 'TASK-877 group A: % is still executable by anon/authenticated', r.sig;
        END IF;
        IF NOT has_function_privilege('service_role', r.sig, 'EXECUTE') THEN
            RAISE EXCEPTION 'TASK-877 group A: % lost service_role EXECUTE', r.sig;
        END IF;
        IF r.prosecdef AND NOT EXISTS (SELECT 1 FROM unnest(coalesce(r.proconfig, '{}'::text[])) c
                                       WHERE c LIKE 'search_path=%') THEN
            RAISE EXCEPTION 'TASK-877 group A: % has no pinned search_path', r.sig;
        END IF;
    END LOOP;
END
$$;

COMMIT;

-- Read-only verification after applying:
--   SELECT oid::regprocedure, proacl, proconfig FROM pg_proc
--   WHERE pronamespace='public'::regnamespace
--     AND proname IN ('process_stripe_payment','add_tokens_atomic','grant_daily_free_tokens');
--   Expect no '=X' / 'anon=X' / 'authenticated=X' entries.
