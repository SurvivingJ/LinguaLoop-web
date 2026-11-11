-- =============================================================================
-- security_lock_progress_tables.sql  (TASK-880, security-hardening S10 / S12)
-- =============================================================================
-- Purpose:
--   (S10) Progress tables allowed own-row writes from `authenticated`, so a user
--   could forge ELO ratings, attempts and ladder state with just the anon key + a
--   login. test_attempts even had an INSERT policy contradicting
--   attempts_no_manual_insert. Remove every client write path.
--   (S12) The public schema's DEFAULT PRIVILEGES grant every new table/sequence to
--   anon + authenticated, so protection of new objects rests on RLS alone. Stop that.
--
-- Tables (12): user_skill_ratings, test_attempts, exercise_attempts,
--   question_attempt_results, user_vocabulary_knowledge, user_word_ladder,
--   daily_test_loads, user_flashcards, calibration_sessions, calibration_responses,
--   weekly_plan_states, user_study_plans.
--   Result: RLS on; write-capable policies (INSERT/UPDATE/DELETE) dropped; an `ALL`
--   policy is first split into a SELECT policy with the identical USING clause so
--   the own-row read path survives; INSERT/UPDATE/DELETE/TRUNCATE/REFERENCES/TRIGGER
--   revoked from PUBLIC, anon, authenticated; anon loses SELECT too; authenticated
--   keeps SELECT (own rows, via the remaining policy). service_role is untouched.
--
-- Pre-flight (code trace, 2026-10-14) - none of these tables is written, or read,
-- by an anon or user-JWT client:
--   * routes/study_plan.py, flashcards.py, study_session.py -> get_supabase_admin().
--   * routes/dual_translation.py -> current_app.supabase_service.
--   * routes/tests.py:1175 reads test_attempts via `supabase_service or supabase`
--     (service key present in deployed envs; the anon fallback reads nothing useful
--     under RLS anyway).
--   * services/test_service.py: reads/writes of daily_test_loads, user_study_plans,
--     test_attempts use self.admin. TestService.record_attempt() inserts
--     test_attempts/attempt_responses via the ANON client but has NO callers and the
--     anon client carries no user session (auth.uid() is NULL, so it already fails
--     RLS today): dead code. attempt_responses is not in the plan's list and is left
--     alone (see report).
--   * scripts/* (validate_effectiveness_view, calibration_*, verify_calibration_state,
--     simulate_*, measure_selection_quality) use get_supabase_admin()/service key.
--   * No static JS/HTML uses supabase-js (no browser DB client exists).
--   * Writers inside the DB (ladder_record_attempt, record_session_progress,
--     update_classifier_mastery, calibration_* ...) are called via the admin client
--     (TASK-877 revokes their EXECUTE from client roles).
--
-- Default privileges: for roles postgres and supabase_admin (the creators of
-- objects in public), future TABLES and SEQUENCES in public are no longer granted
-- to anon/authenticated/PUBLIC. FUNCTIONS are handled in TASK-877. Consequence:
-- every future migration that creates a client-readable table must GRANT explicitly.
-- The supabase_admin statement is skipped with a NOTICE if the migration role is not
-- permitted to alter that role's defaults - confirm via pg_default_acl after applying.
--
-- Not in this migration: a blanket REVOKE over all EXISTING tables/sequences (run
-- after 876/879 with Flask smoke tests, per the plan).
--
-- Idempotent and re-runnable. DDL only; no row is touched.
-- REQUIRES USER APPROVAL TO APPLY LIVE. Apply after 875 (policy drops) and 877.
--
-- REVISED 2026-11-11 against the live catalog (read-only review; TASK-877/876/879
-- were found applied live on 2026-10-14, this file was not):
--   * +6 tables that still had an own-row ALL/INSERT/UPDATE policy AND full client
--     grants, i.e. were client-writable: user_calibration_state,
--     calibration_response_options, daily_test_load_items, word_quiz_results,
--     user_languages, user_exercise_sessions. All are written by Flask through
--     service_role only.
--   * `*_service_role` ALL policies (USING auth.role() = 'service_role') are
--     dropped, not split: service_role has BYPASSRLS, so they never applied.
--   * An ALL policy is not split into a SELECT copy when an equivalent own-row
--     SELECT policy already exists (avoids duplicates such as
--     user_study_plans_self_modify (select) next to user_study_plans_self_select).
--   * dim_subscription_tiers: client write grants revoked and the admin-JWT write
--     policy dim_tiers_admin_write dropped (ADR-034: no client DB writes; admin
--     changes go through Flask). Public SELECT of active tiers is kept.
-- =============================================================================

BEGIN;

-- Expression normaliser for "is there already an equivalent SELECT policy?":
-- strips whitespace and parentheses and orders the two sides of a single `=`.
CREATE OR REPLACE FUNCTION pg_temp.rls_norm(e text) RETURNS text LANGUAGE sql IMMUTABLE AS $f$
  SELECT CASE WHEN array_length(parts, 1) = 2
              THEN least(parts[1], parts[2]) || '=' || greatest(parts[1], parts[2])
              ELSE flat END
    FROM (SELECT regexp_replace(coalesce(e, ''), '[[:space:]()]', '', 'g') AS flat) f,
         LATERAL (SELECT string_to_array(f.flat, '=') AS parts) p
$f$;

DO $$
DECLARE
  tbl text;
  tables text[] := ARRAY[
    'user_skill_ratings','test_attempts','exercise_attempts','question_attempt_results',
    'user_vocabulary_knowledge','user_word_ladder','daily_test_loads','user_flashcards',
    'calibration_sessions','calibration_responses','weekly_plan_states','user_study_plans',
    -- added 2026-11-11 (client-writable on the live catalog)
    'user_calibration_state','calibration_response_options','daily_test_load_items',
    'word_quiz_results','user_languages','user_exercise_sessions'];
  pol record;
  priv text;
  r text;
  new_name text;
BEGIN
  FOREACH tbl IN ARRAY tables LOOP
    IF to_regclass(format('public.%I', tbl)) IS NULL THEN
      RAISE NOTICE 'TASK-880: table public.% not found, skipped', tbl;
      CONTINUE;
    END IF;

    EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', tbl);

    -- 1. Policies. ALL -> preserve read side as a SELECT policy, then drop.
    FOR pol IN
      SELECT policyname, cmd, roles, qual
        FROM pg_policies WHERE schemaname = 'public' AND tablename = tbl
    LOOP
      IF pol.cmd = 'ALL' AND pg_temp.rls_norm(pol.qual) = pg_temp.rls_norm('( SELECT auth.role() AS role) = ''service_role''::text') THEN
        -- service_role bypasses RLS: this policy never applied to anyone. Drop it.
        EXECUTE format('DROP POLICY %I ON public.%I', pol.policyname, tbl);
      ELSIF pol.cmd = 'ALL' THEN
        new_name := left(pol.policyname, 50) || ' (select)';
        IF pol.qual IS NOT NULL AND NOT EXISTS (
             SELECT 1 FROM pg_policies WHERE schemaname='public' AND tablename=tbl
                AND policyname = new_name)
           AND NOT EXISTS (   -- an equivalent own-row SELECT policy already exists
             SELECT 1 FROM pg_policies WHERE schemaname='public' AND tablename=tbl
                AND cmd = 'SELECT' AND roles = pol.roles
                AND pg_temp.rls_norm(qual) = pg_temp.rls_norm(pol.qual)) THEN
          EXECUTE format('CREATE POLICY %I ON public.%I FOR SELECT TO %s USING (%s)',
                         new_name, tbl, array_to_string(pol.roles, ','), pol.qual);
        END IF;
        EXECUTE format('DROP POLICY %I ON public.%I', pol.policyname, tbl);
      ELSIF pol.cmd IN ('INSERT','UPDATE','DELETE') THEN
        EXECUTE format('DROP POLICY %I ON public.%I', pol.policyname, tbl);
      END IF;
    END LOOP;

    -- 2. Privileges. Revoke everything, give authenticated back SELECT only.
    EXECUTE format('REVOKE ALL ON TABLE public.%I FROM PUBLIC, anon, authenticated', tbl);
    EXECUTE format('GRANT SELECT ON TABLE public.%I TO authenticated', tbl);
    EXECUTE format('REVOKE ALL (%s) ON TABLE public.%I FROM PUBLIC, anon, authenticated',
      (SELECT string_agg(quote_ident(attname), ',') FROM pg_attribute
        WHERE attrelid = format('public.%I', tbl)::regclass AND attnum > 0 AND NOT attisdropped), tbl);

    -- 3. Post-conditions.
    FOREACH r IN ARRAY ARRAY['anon','authenticated'] LOOP
      FOREACH priv IN ARRAY ARRAY['INSERT','UPDATE','DELETE','TRUNCATE','REFERENCES','TRIGGER'] LOOP
        IF has_table_privilege(r, format('public.%I', tbl), priv) THEN
          RAISE EXCEPTION 'TASK-880: % still has % on %', r, priv, tbl;
        END IF;
      END LOOP;
    END LOOP;
    IF has_table_privilege('anon', format('public.%I', tbl), 'SELECT') THEN
      RAISE EXCEPTION 'TASK-880: anon still has SELECT on %', tbl;
    END IF;
    IF EXISTS (SELECT 1 FROM pg_policies WHERE schemaname='public' AND tablename=tbl
                AND cmd IN ('ALL','INSERT','UPDATE','DELETE')) THEN
      RAISE EXCEPTION 'TASK-880: write-capable policy remains on %', tbl;
    END IF;
    IF NOT has_table_privilege('service_role', format('public.%I', tbl), 'INSERT') THEN
      RAISE EXCEPTION 'TASK-880: service_role lost INSERT on % (unexpected)', tbl;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname='public' AND tablename=tbl AND cmd='SELECT') THEN
      RAISE NOTICE 'TASK-880: % now has NO SELECT policy (own-row reads return nothing for clients)', tbl;
    END IF;
  END LOOP;
END $$;

-- ---- dim_subscription_tiers: read-only for clients (ADR-034) ----
DO $$
BEGIN
  DROP POLICY IF EXISTS dim_tiers_admin_write ON public.dim_subscription_tiers;
  REVOKE INSERT, UPDATE, DELETE, TRUNCATE, REFERENCES, TRIGGER
    ON TABLE public.dim_subscription_tiers FROM PUBLIC, anon, authenticated;
  IF has_table_privilege('authenticated', 'public.dim_subscription_tiers', 'UPDATE')
     OR has_table_privilege('anon', 'public.dim_subscription_tiers', 'INSERT') THEN
    RAISE EXCEPTION 'TASK-880: client write privilege remains on dim_subscription_tiers';
  END IF;
  IF EXISTS (SELECT 1 FROM pg_policies WHERE schemaname='public' AND tablename='dim_subscription_tiers'
              AND cmd IN ('ALL','INSERT','UPDATE','DELETE')) THEN
    RAISE EXCEPTION 'TASK-880: write-capable policy remains on dim_subscription_tiers';
  END IF;
END $$;

-- ---- Default privileges (S12): new TABLES and SEQUENCES are not client-granted ----
DO $$
DECLARE creator text;
BEGIN
  FOREACH creator IN ARRAY ARRAY['postgres','supabase_admin'] LOOP
    BEGIN
      EXECUTE format('ALTER DEFAULT PRIVILEGES FOR ROLE %I IN SCHEMA public REVOKE ALL ON TABLES FROM anon, authenticated, PUBLIC', creator);
      EXECUTE format('ALTER DEFAULT PRIVILEGES FOR ROLE %I IN SCHEMA public REVOKE ALL ON SEQUENCES FROM anon, authenticated, PUBLIC', creator);
    EXCEPTION WHEN insufficient_privilege OR undefined_object THEN
      RAISE NOTICE 'TASK-880: could not alter default privileges for role % (%); apply as that role', creator, SQLERRM;
    END;
  END LOOP;
END $$;

COMMIT;
