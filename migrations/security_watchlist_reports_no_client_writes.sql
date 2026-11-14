-- =============================================================================
-- security_watchlist_reports_no_client_writes.sql  (codebase review 2026-11, Security)
-- =============================================================================
-- Purpose: close the last two places where a client role can write a public
-- table directly (ADR-034: no client DB writes; Flask writes with service_role).
--
--   * user_word_watchlist: `uww_own_data` is FOR ALL (user_word_watchlist_schema.sql),
--     so a signed-in user can INSERT/UPDATE/DELETE their own rows through
--     PostgREST, e.g. flip ladder_exercises_generated or point
--     last_matched_test_id at any test. Every repo writer is service_role
--     (services/word_list_import/*, routes/word_list_import.py).
--   * user_reports: authenticated keeps INSERT plus the "Users can create
--     reports" policy (kept on purpose by security_lock_users_tokens_reports.sql
--     "so INSERT could be dropped later"). routes/reports.py inserts through
--     supabase_service, so the client path is a second write surface that
--     skips the validation done in the route.
--
-- Result:
--   user_word_watchlist : own-row SELECT only for authenticated; no write policy,
--                         no write privilege for PUBLIC / anon / authenticated.
--   user_reports        : own-row SELECT only for authenticated; no INSERT policy,
--                         no INSERT privilege.
--
-- Pre-checks:
--   1. No client writes either table:
--        grep -rnE "user_word_watchlist|user_reports" static templates    -> nothing
--        grep -rnE "table\(['\"](user_word_watchlist|user_reports)" routes services
--      and confirm every write uses supabase_service / get_supabase_admin().
--   2. Current state, for the rollback:
--        SELECT tablename, policyname, cmd, roles, qual, with_check FROM pg_policies
--         WHERE schemaname = 'public' AND tablename IN ('user_word_watchlist', 'user_reports');
--        SELECT table_name, grantee, privilege_type
--          FROM information_schema.role_table_grants
--         WHERE table_schema = 'public' AND table_name IN ('user_word_watchlist', 'user_reports');
--
-- Policies are handled by catalog lookup, not by name: after
-- rls_consolidate_permissive_policies.sql the live names differ from the ones in
-- the files that created them. A user_reports policy that is FOR ALL is not
-- guessed at: the migration raises and changes nothing.
--
-- Idempotent and re-runnable. DDL only; no row is touched.
-- REQUIRES USER APPROVAL TO APPLY LIVE.
--
-- Rollback:
--   GRANT INSERT, UPDATE, DELETE ON public.user_word_watchlist TO authenticated;
--   DROP POLICY IF EXISTS uww_select_own ON public.user_word_watchlist;
--   CREATE POLICY uww_own_data ON public.user_word_watchlist FOR ALL
--     USING ((SELECT auth.uid()) = user_id) WITH CHECK ((SELECT auth.uid()) = user_id);
--   GRANT INSERT ON public.user_reports TO authenticated;
--   CREATE POLICY "Users can create reports" ON public.user_reports FOR INSERT TO public
--     WITH CHECK ((SELECT auth.uid()) = user_id);
-- =============================================================================

BEGIN;

ALTER TABLE public.user_word_watchlist ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_reports        ENABLE ROW LEVEL SECURITY;

-- ---- user_word_watchlist: read-only for the owner ------------------------------
DO $$
DECLARE p record;
BEGIN
  -- Every policy that covers a write goes (FOR ALL and INSERT/UPDATE/DELETE).
  -- That includes uww_service_role, which never applied: service_role bypasses RLS.
  FOR p IN SELECT policyname FROM pg_policies
            WHERE schemaname = 'public' AND tablename = 'user_word_watchlist'
              AND cmd <> 'SELECT'
  LOOP
    EXECUTE format('DROP POLICY %I ON public.user_word_watchlist', p.policyname);
  END LOOP;

  -- Keep the owner's read unless a surviving SELECT policy already grants it.
  IF NOT EXISTS (SELECT 1 FROM pg_policies
                  WHERE schemaname = 'public' AND tablename = 'user_word_watchlist'
                    AND cmd = 'SELECT' AND qual ~ '\muser_id\M' AND qual ~ 'auth\.uid\(\)') THEN
    CREATE POLICY uww_select_own ON public.user_word_watchlist
      AS PERMISSIVE FOR SELECT TO authenticated
      USING ((SELECT auth.uid()) = user_id);
  END IF;
END $$;

REVOKE ALL ON TABLE public.user_word_watchlist FROM PUBLIC, anon, authenticated;
GRANT SELECT ON TABLE public.user_word_watchlist TO authenticated;

-- ---- user_reports: no client INSERT ---------------------------------------------
DO $$
DECLARE p record;
BEGIN
  IF EXISTS (SELECT 1 FROM pg_policies
              WHERE schemaname = 'public' AND tablename = 'user_reports' AND cmd = 'ALL') THEN
    RAISE EXCEPTION 'user_reports has a FOR ALL policy; split its read side by hand before applying';
  END IF;
  FOR p IN SELECT policyname FROM pg_policies
            WHERE schemaname = 'public' AND tablename = 'user_reports'
              AND cmd IN ('INSERT', 'UPDATE', 'DELETE')
  LOOP
    EXECUTE format('DROP POLICY %I ON public.user_reports', p.policyname);
  END LOOP;
END $$;

REVOKE INSERT, UPDATE, DELETE, TRUNCATE, REFERENCES, TRIGGER
  ON TABLE public.user_reports FROM PUBLIC, anon, authenticated;
-- service_role / postgres grants are intentionally untouched.

DO $$
DECLARE
  t text;
  r text;
  priv text;
BEGIN
  FOREACH t IN ARRAY ARRAY['user_word_watchlist', 'user_reports'] LOOP
    IF EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = 'public'
                  AND tablename = t AND cmd <> 'SELECT') THEN
      RAISE EXCEPTION 'public.% still has a write policy', t;
    END IF;
    FOREACH r IN ARRAY ARRAY['anon', 'authenticated'] LOOP
      FOREACH priv IN ARRAY ARRAY['INSERT', 'UPDATE', 'DELETE'] LOOP
        IF has_table_privilege(r, format('public.%I', t), priv) THEN
          RAISE EXCEPTION '% still has % on public.%', r, priv, t;
        END IF;
      END LOOP;
    END LOOP;
  END LOOP;
  IF has_table_privilege('anon', 'public.user_word_watchlist', 'SELECT') THEN
    RAISE EXCEPTION 'anon can read user_word_watchlist';
  END IF;
END $$;

COMMIT;
