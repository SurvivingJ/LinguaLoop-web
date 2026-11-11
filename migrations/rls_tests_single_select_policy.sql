-- =============================================================================
-- rls_tests_single_select_policy.sql  (TASK-932 follow-up, 2026-11-11)
-- =============================================================================
-- `tests` was the one table rls_consolidate_permissive_policies.sql skipped
-- (its SELECT policies have different role lists). Live before this file:
--   public_free_tests        TO public         USING (is_active = true AND tier = 'free-tier')
--   tests_authenticated_read TO authenticated  USING (is_active IS TRUE)
--   tests_moderator_view     TO public         USING (is_moderator((SELECT auth.uid())))
-- Since TASK-882, anon (and PUBLIC) hold no privilege on `tests`, so the two
-- `TO public` policies only ever apply to `authenticated`, where
-- public_free_tests is a subset of tests_authenticated_read. One policy
-- therefore gives exactly the same access:
--   tests_select TO authenticated USING (is_active IS TRUE OR is_moderator((SELECT auth.uid())))
-- (`is_active = true` and `is_active IS TRUE` differ only for NULL, where both
-- deny.) Clears the last Supabase advisor 0006 findings.
--
-- Guards: refuses if a login role other than through role switching could read
-- `tests` under RLS (it would lose the `TO public` policies), and probes, as anon,
-- up to 4 regular users and every moderator/admin, the rows each can SELECT
-- (count + hash) before and after; any difference raises and nothing changes.
--
-- Idempotent: a re-run finds only tests_select and does nothing.
-- Rollback:
--   DROP POLICY tests_select ON public.tests;
--   CREATE POLICY public_free_tests ON public.tests AS PERMISSIVE FOR SELECT TO public
--     USING (((is_active = true) AND (tier = 'free-tier'::text)));
--   CREATE POLICY tests_authenticated_read ON public.tests AS PERMISSIVE FOR SELECT TO authenticated
--     USING ((is_active IS TRUE));
--   CREATE POLICY tests_moderator_view ON public.tests AS PERMISSIVE FOR SELECT TO public
--     USING (is_moderator(( SELECT auth.uid() AS uid)));
-- =============================================================================

DO $$
DECLARE
    persona    record;
    v_count    bigint;
    v_hash     text;
    v_state    text;
    v_pass     int;
    mismatches int;
    n_probes   int;
    pol        record;
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'tests'
                    AND policyname <> 'tests_select') THEN
        RAISE NOTICE 'tests already has a single SELECT policy: nothing to do.';
        RETURN;
    END IF;

    -- Guard 1: the old policy set must be exactly the one this file replaces.
    IF (SELECT array_agg(policyname::text ORDER BY policyname) FROM pg_policies
         WHERE schemaname = 'public' AND tablename = 'tests')
       <> ARRAY['public_free_tests', 'tests_authenticated_read', 'tests_moderator_view'] THEN
        RAISE EXCEPTION 'tests policies differ from the expected three; review before consolidating';
    END IF;

    -- Guard 2: no client role but authenticated may read tests under RLS.
    IF has_table_privilege('anon', 'public.tests', 'SELECT') THEN
        RAISE EXCEPTION 'anon can SELECT tests (TASK-882 not applied?)';
    END IF;
    IF EXISTS (SELECT 1 FROM pg_roles r
                WHERE r.rolcanlogin AND NOT r.rolsuper AND NOT r.rolbypassrls
                  AND has_table_privilege(r.oid, 'public.tests', 'SELECT')) THEN
        RAISE EXCEPTION 'a login role without BYPASSRLS can read tests directly and would lose the TO public policies';
    END IF;

    CREATE TEMP TABLE _tp_personas ON COMMIT DROP AS
    SELECT 'anon'::text AS label, 'anon'::text AS role, '{"role":"anon"}'::text AS claims
    UNION ALL
    SELECT 'user:' || u.id, 'authenticated', json_build_object('sub', u.id, 'role', 'authenticated')::text
      FROM (SELECT u.id FROM public.users u
             LEFT JOIN public.dim_subscription_tiers t ON t.id = u.subscription_tier_id
             WHERE NOT coalesce(t.is_admin OR t.is_moderator, false)
             ORDER BY u.id LIMIT 4) u
    UNION ALL
    SELECT 'moderator:' || u.id, 'authenticated', json_build_object('sub', u.id, 'role', 'authenticated')::text
      FROM public.users u JOIN public.dim_subscription_tiers t ON t.id = u.subscription_tier_id
     WHERE coalesce(t.is_admin OR t.is_moderator, false);

    CREATE TEMP TABLE _tp_probe (pass int, label text, n bigint, hash text, state text) ON COMMIT DROP;

    FOR v_pass IN 1..2 LOOP
        FOR persona IN SELECT * FROM _tp_personas LOOP
            BEGIN
                PERFORM set_config('request.jwt.claims', persona.claims, true);
                PERFORM set_config('request.jwt.claim.sub', coalesce(persona.claims::json->>'sub', ''), true);
                PERFORM set_config('request.jwt.claim.role', persona.claims::json->>'role', true);
                EXECUTE format('SET LOCAL ROLE %I', persona.role);
                SELECT count(*), md5(coalesce(string_agg(t.id::text, ',' ORDER BY t.id), ''))
                  INTO v_count, v_hash FROM public.tests t;
                v_state := 'ok';
                RESET ROLE;
            EXCEPTION WHEN OTHERS THEN
                v_count := NULL; v_hash := NULL; v_state := SQLSTATE;
                RESET ROLE;
            END;
            INSERT INTO _tp_probe VALUES (v_pass, persona.label, v_count, v_hash, v_state);
        END LOOP;
        PERFORM set_config('request.jwt.claims', '', true);
        PERFORM set_config('request.jwt.claim.sub', '', true);
        PERFORM set_config('request.jwt.claim.role', '', true);

        EXIT WHEN v_pass = 2;

        FOR pol IN SELECT policyname FROM pg_policies WHERE schemaname = 'public' AND tablename = 'tests' LOOP
            EXECUTE format('DROP POLICY %I ON public.tests', pol.policyname);
        END LOOP;
        CREATE POLICY tests_select ON public.tests AS PERMISSIVE FOR SELECT TO authenticated
            USING (is_active IS TRUE OR public.is_moderator((SELECT auth.uid())));
    END LOOP;

    SELECT count(*) INTO mismatches
      FROM _tp_probe b JOIN _tp_probe a ON a.pass = 2 AND a.label = b.label
     WHERE b.pass = 1
       AND (a.n IS DISTINCT FROM b.n OR a.hash IS DISTINCT FROM b.hash OR a.state IS DISTINCT FROM b.state);
    IF mismatches > 0 THEN
        RAISE EXCEPTION 'tests policy consolidation changed access for % persona(s); nothing applied. First: %', mismatches,
            (SELECT format('%s: before n=%s state=%s, after n=%s state=%s', b.label, b.n, b.state, a.n, a.state)
               FROM _tp_probe b JOIN _tp_probe a ON a.pass = 2 AND a.label = b.label
              WHERE b.pass = 1
                AND (a.n IS DISTINCT FROM b.n OR a.hash IS DISTINCT FROM b.hash OR a.state IS DISTINCT FROM b.state)
              LIMIT 1);
    END IF;

    SELECT count(*) INTO n_probes FROM _tp_probe p WHERE p.pass = 2;
    RAISE NOTICE 'tests: 3 SELECT policies -> tests_select; % personas see identical rows before and after.', n_probes;
END $$;
