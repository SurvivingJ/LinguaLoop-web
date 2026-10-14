-- =============================================================================
-- security_lock_users_tokens_reports.sql  (TASK-875, security-hardening S1/S4/S9)
-- =============================================================================
-- Purpose: close the self-escalation and balance-forgery holes reachable with just
-- the public anon key + a normal login:
--   * users: a user could PATCH their own subscription_tier_id to an admin tier.
--   * user_tokens: a user could write their own purchased_tokens.
--   * token_transactions: client-writable ledger.
--   * user_reports: "Admin can view all reports" was USING (true) => any visitor
--     could read every report.
--
-- Developer decisions (2026-10-14):
--   (1) DROP users_admin_all (ALL, is_admin(auth.uid())). Admin operations go
--       through Flask with the service role. Read-only admin SELECT policies
--       ("Admin read all users", tokens_admin_view, transactions_admin_view) are
--       KEPT: they cannot write and are not part of this task.
--   (3) users: FULL REVOKE of client write privileges (no column allowlist).
--       There is no browser caller; Flask uses service_role (bypasses RLS and
--       keeps its own grants).
--
-- Pre-flight findings (code + read-only catalog queries, 2026-10-14):
--   * Writes to users/user_tokens/token_transactions/user_reports in repo code all
--     use get_supabase_admin() / supabase_service (auth_service, device_service,
--     routes/users.py, routes/reports.py). services/payment_service.py uses an
--     ANON client (get_payment_service) but that factory has no callers in the
--     repo (routes/payments.py only mentions it in a comment): dead code, would
--     break if wired up -> see report.
--   * tests/conftest.py mocks the Supabase client; no live PATCH on users.
--   * SECURITY INVOKER trigger create_user_dependencies() (AFTER INSERT on users)
--     inserts user_tokens as the caller. Callers of INSERT users are service_role
--     (Flask) or handle_new_user() (SECURITY DEFINER, owner postgres): both retain
--     INSERT. No other INVOKER function/trigger writes these tables.
--   * is_admin()/is_moderator() are SECURITY DEFINER: unaffected by revokes.
--   * Live ACLs before this migration: anon+authenticated hold arwdDxtm on all four
--     tables; column-level ACLs: none.
--
-- Idempotent and re-runnable. DDL only; no row is touched.
-- REQUIRES USER APPROVAL TO APPLY LIVE. Run migrations/audits/security_users_tokens_audit.sql
-- first and review (admins / non-default tiers / balance vs ledger); rotating admin
-- sessions is NOT part of this task (decision 2).
-- =============================================================================

BEGIN;

-- ---- 1. Drop client write-path policies --------------------------------------
-- Dropping the policy is defence in depth; the privilege revoke below is what
-- actually stops the write (RLS policies on revoked privileges are inert).
DROP POLICY IF EXISTS users_admin_all              ON public.users;  -- decision 1
DROP POLICY IF EXISTS users_update_own             ON public.users;
DROP POLICY IF EXISTS "Users can update own profile" ON public.users;
DROP POLICY IF EXISTS "Users update own profile"   ON public.users;
DROP POLICY IF EXISTS "System can update tokens"   ON public.user_tokens;
DROP POLICY IF EXISTS tokens_own_data              ON public.user_tokens;  -- ALL
DROP POLICY IF EXISTS "Admin can view all reports" ON public.user_reports; -- USING (true)

-- Own-row SELECT policies must exist (create if a drop above removed the only one
-- or the live DB drifted). "Users can view own tokens" already exists live.
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname='public'
                 AND tablename='user_tokens' AND policyname='Users can view own tokens') THEN
    CREATE POLICY "Users can view own tokens" ON public.user_tokens
      FOR SELECT USING (auth.uid() = user_id);
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname='public'
                 AND tablename='users'
                 AND policyname IN ('users_select_own','Users can view own profile','Users read own profile')) THEN
    CREATE POLICY users_select_own ON public.users
      FOR SELECT USING (id = auth.uid() AND deleted_at IS NULL);
  END IF;
END $$;

-- Ensure RLS stays on (already true live).
ALTER TABLE public.users              ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_tokens        ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.token_transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_reports       ENABLE ROW LEVEL SECURITY;

-- ---- 2. Revoke client privileges ---------------------------------------------
-- users / user_tokens / token_transactions: no client writes at all. A role that
-- already had SELECT keeps it (own-row policies still scope it; broader anon
-- revokes belong to TASK-880). PUBLIC is revoked too: a revoke from anon alone is
-- a no-op when the privilege comes via the PUBLIC pseudo-role.
DO $$
DECLARE
  t text;
  r text;
  had_select boolean;
BEGIN
  FOREACH t IN ARRAY ARRAY['users','user_tokens','token_transactions'] LOOP
    EXECUTE format('REVOKE ALL ON TABLE public.%I FROM PUBLIC', t);
    FOREACH r IN ARRAY ARRAY['anon','authenticated'] LOOP
      had_select := has_table_privilege(r, format('public.%I', t), 'SELECT');
      EXECUTE format('REVOKE ALL ON TABLE public.%I FROM %I', t, r);
      IF had_select THEN
        EXECUTE format('GRANT SELECT ON TABLE public.%I TO %I', t, r);
      END IF;
    END LOOP;
    -- column-level grants (none live today; guards against drift)
    EXECUTE format('REVOKE ALL (%s) ON TABLE public.%I FROM anon, authenticated, PUBLIC',
      (SELECT string_agg(quote_ident(attname), ',') FROM pg_attribute
        WHERE attrelid = format('public.%I', t)::regclass AND attnum > 0 AND NOT attisdropped), t);
  END LOOP;
END $$;

-- user_reports: anon gets nothing; authenticated keeps INSERT + own-row SELECT only.
-- (routes/reports.py inserts via service_role, so INSERT could be dropped later.)
REVOKE ALL ON TABLE public.user_reports FROM PUBLIC, anon, authenticated;
GRANT SELECT, INSERT ON TABLE public.user_reports TO authenticated;

-- service_role / postgres grants are intentionally untouched.

-- ---- 3. Post-conditions (fail the migration if not met) ----------------------
DO $$
DECLARE t text; r text; p text;
BEGIN
  FOREACH t IN ARRAY ARRAY['users','user_tokens','token_transactions'] LOOP
    FOREACH r IN ARRAY ARRAY['anon','authenticated'] LOOP
      FOREACH p IN ARRAY ARRAY['INSERT','UPDATE','DELETE','TRUNCATE','REFERENCES','TRIGGER'] LOOP
        IF has_table_privilege(r, format('public.%I', t), p) THEN
          RAISE EXCEPTION 'TASK-875: % still has % on %', r, p, t;
        END IF;
      END LOOP;
    END LOOP;
  END LOOP;
  IF has_table_privilege('anon', 'public.user_reports', 'SELECT')
     OR has_table_privilege('anon', 'public.user_reports', 'INSERT') THEN
    RAISE EXCEPTION 'TASK-875: anon still has access to user_reports';
  END IF;
  IF has_table_privilege('authenticated', 'public.user_reports', 'UPDATE')
     OR has_table_privilege('authenticated', 'public.user_reports', 'DELETE') THEN
    RAISE EXCEPTION 'TASK-875: authenticated can still modify user_reports';
  END IF;
  IF EXISTS (SELECT 1 FROM pg_policies WHERE schemaname='public' AND (
        (tablename='users' AND policyname IN ('users_admin_all','users_update_own',
              'Users can update own profile','Users update own profile'))
     OR (tablename='user_tokens' AND policyname IN ('System can update tokens','tokens_own_data'))
     OR (tablename='user_reports' AND policyname = 'Admin can view all reports'))) THEN
    RAISE EXCEPTION 'TASK-875: a listed policy still exists';
  END IF;
  IF NOT has_table_privilege('service_role', 'public.users', 'UPDATE') THEN
    RAISE EXCEPTION 'TASK-875: service_role lost UPDATE on users';
  END IF;
END $$;

COMMIT;
