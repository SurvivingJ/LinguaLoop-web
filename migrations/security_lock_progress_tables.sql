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
-- REQUIRES USER APPROVAL TO APPLY LIVE. Live policy names were not read (no project
-- ref available to this session), hence the dynamic policy handling; apply after 875 and 877.
-- =============================================================================

BEGIN;

DO $$
DECLARE
  tbl text;
  tables text[] := ARRAY[
    'user_skill_ratings','test_attempts','exercise_attempts','question_attempt_results',
    'user_vocabulary_knowledge','user_word_ladder','daily_test_loads','user_flashcards',
    'calibration_sessions','calibration_responses','weekly_plan_states','user_study_plans'];
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
      IF pol.cmd = 'ALL' THEN
        new_name := left(pol.policyname, 50) || ' (select)';
        IF pol.qual IS NOT NULL AND NOT EXISTS (
             SELECT 1 FROM pg_policies WHERE schemaname='public' AND tablename=tbl
                AND policyname = new_name) THEN
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
