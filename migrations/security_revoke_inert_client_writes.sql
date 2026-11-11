-- =============================================================================
-- security_revoke_inert_client_writes.sql  (security-hardening tidy-up, 2026-11-11)
-- =============================================================================
-- After TASK-875/876/880/882, no RLS policy lets a client role (anon /
-- authenticated) write any public table except `user_reports` (own-row
-- INSERT, kept on purpose by TASK-875). But 25 tables and 4 sequences still
-- GRANT write privileges to those roles: inert while RLS stays on and no write
-- policy exists, live again the moment someone adds a policy or turns RLS off.
-- ADR-034: no client DB writes; Flask writes through service_role.
--
-- What this does:
--   1. app_error_logs: drop "Authenticated insert error logs" (any signed-in
--      user could insert log rows through PostgREST; only Flask writes this
--      table, app.py via supabase_service).
--   2. Every public table / view / materialized view / foreign table not owned
--      by an extension: REVOKE INSERT, UPDATE, DELETE, TRUNCATE, REFERENCES,
--      TRIGGER (table- and column-level) from PUBLIC, anon, authenticated.
--      Exception: user_reports keeps authenticated INSERT (TASK-875).
--      SELECT is untouched (who may read reference data is a separate decision).
--   3. Every public sequence not owned by an extension: REVOKE ALL from PUBLIC,
--      anon, authenticated (no client inserts remain to need nextval). A
--      sequence feeding user_reports (none live; its id is not serial) would keep
--      authenticated access only.
--
-- Live pre-flight (read-only, 2026-11-11):
--   * 26 client-writable tables by grant: app_error_logs, calibration_anchor_blocklist,
--     dim_character_components, dim_complexity_tiers, dim_counter_distractor_groups,
--     dim_counter_noun_pairs, dim_counters, dim_distractor_bands,
--     dim_exercise_capabilities, dim_exercise_types, dim_languages, dim_lens,
--     dim_practice_modes, dim_question_types, dim_status, dim_study_plan_templates,
--     dim_test_types, dim_vocabulary, dim_word_senses, test_skill_ratings,
--     tests_tier_backup_20260926, tests_tier_backup_20260927_v1, trusted_devices,
--     user_exercise_history, user_reports (kept), user_test_intros_seen.
--   * 4 client sequences: prestudy_followups_id_seq, study_time_ledger_id_seq,
--     test_sentence_references_id_seq, test_sentences_id_seq.
--   * No views or column-level write grants; nothing granted to PUBLIC; no other
--     role writes through a grant; no SECURITY INVOKER function executable by
--     a client role writes a table; the only auth.users trigger
--     (handle_new_user) is SECURITY DEFINER.
--   * Repo: no Python writes through the anon client (all writes use
--     supabase_service / get_supabase_admin()); no browser Supabase client.
--
-- Idempotent and re-runnable. DDL only; no row is touched.
-- Rollback (restores the grants, not the policy):
--   GRANT INSERT, UPDATE, DELETE, TRUNCATE, REFERENCES, TRIGGER ON <each table above>
--     TO anon, authenticated;  GRANT ALL ON SEQUENCE <each sequence> TO anon, authenticated;
--   CREATE POLICY "Authenticated insert error logs" ON public.app_error_logs AS PERMISSIVE
--     FOR INSERT TO public WITH CHECK (((( SELECT auth.uid() AS uid) IS NOT NULL)
--     OR (( SELECT auth.role() AS role) = 'service_role'::text)));
-- =============================================================================

BEGIN;

-- ---- 1. app_error_logs: no client inserts --------------------------------------
DROP POLICY IF EXISTS "Authenticated insert error logs" ON public.app_error_logs;

-- ---- 2 + 3. Revoke client write grants ---------------------------------------
DO $$
DECLARE
  keep_tables text[] := ARRAY['user_reports'];
  r record;
  cols text;
  n_rel int := 0;
  n_seq int := 0;
BEGIN
  FOR r IN
    SELECT c.oid, c.relname
      FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
     WHERE n.nspname = 'public' AND c.relkind IN ('r', 'p', 'v', 'm', 'f')
       AND NOT EXISTS (SELECT 1 FROM pg_depend d WHERE d.objid = c.oid AND d.deptype = 'e')
       AND c.relname <> ALL (keep_tables)
     ORDER BY c.relname
  LOOP
    IF has_table_privilege('anon', r.oid, 'INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER')
       OR has_table_privilege('authenticated', r.oid, 'INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER')
       OR has_any_column_privilege('anon', r.oid, 'INSERT,UPDATE,REFERENCES')
       OR has_any_column_privilege('authenticated', r.oid, 'INSERT,UPDATE,REFERENCES') THEN
      n_rel := n_rel + 1;
    END IF;
    EXECUTE format('REVOKE INSERT, UPDATE, DELETE, TRUNCATE, REFERENCES, TRIGGER ON TABLE public.%I FROM PUBLIC, anon, authenticated', r.relname);
    SELECT string_agg(quote_ident(attname), ', ') INTO cols
      FROM pg_attribute WHERE attrelid = r.oid AND attnum > 0 AND NOT attisdropped;
    IF cols IS NOT NULL THEN
      EXECUTE format('REVOKE INSERT (%s), UPDATE (%s), REFERENCES (%s) ON TABLE public.%I FROM PUBLIC, anon, authenticated',
                     cols, cols, cols, r.relname);
    END IF;
  END LOOP;

  FOR r IN
    SELECT c.oid, c.relname,
           EXISTS (SELECT 1 FROM pg_depend d JOIN pg_class t ON t.oid = d.refobjid
                    WHERE d.objid = c.oid AND d.deptype IN ('a', 'i')
                      AND t.relname = ANY (keep_tables)) AS feeds_kept_table
      FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
     WHERE n.nspname = 'public' AND c.relkind = 'S'
       AND NOT EXISTS (SELECT 1 FROM pg_depend d WHERE d.objid = c.oid AND d.deptype = 'e')
  LOOP
    IF has_sequence_privilege('anon', r.oid, 'USAGE,UPDATE,SELECT')
       OR (NOT r.feeds_kept_table AND has_sequence_privilege('authenticated', r.oid, 'USAGE,UPDATE,SELECT')) THEN
      n_seq := n_seq + 1;
    END IF;
    -- A sequence feeding a kept table (user_reports) stays usable by
    -- authenticated, whose INSERT needs it; nobody else keeps access.
    EXECUTE format('REVOKE ALL ON SEQUENCE public.%I FROM PUBLIC, anon', r.relname);
    IF NOT r.feeds_kept_table THEN
      EXECUTE format('REVOKE ALL ON SEQUENCE public.%I FROM authenticated', r.relname);
    END IF;
  END LOOP;

  RAISE NOTICE 'Revoked client writes on % relation(s) and client access to % sequence(s).', n_rel, n_seq;
END $$;

-- ---- 4. Post-conditions (fail the migration if not met) ----------------------
DO $$
DECLARE bad text;
BEGIN
  SELECT string_agg(c.relname, ', ') INTO bad
    FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
   WHERE n.nspname = 'public' AND c.relkind IN ('r', 'p', 'v', 'm', 'f')
     AND NOT EXISTS (SELECT 1 FROM pg_depend d WHERE d.objid = c.oid AND d.deptype = 'e')
     AND (has_table_privilege('anon', c.oid, 'INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER')
          OR has_any_column_privilege('anon', c.oid, 'INSERT,UPDATE,REFERENCES')
          OR (c.relname <> 'user_reports' AND
              (has_table_privilege('authenticated', c.oid, 'INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER')
               OR has_any_column_privilege('authenticated', c.oid, 'INSERT,UPDATE,REFERENCES')))
          OR (c.relname = 'user_reports' AND
              has_table_privilege('authenticated', c.oid, 'UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER')));
  IF bad IS NOT NULL THEN
    RAISE EXCEPTION 'client write privilege remains on: %', bad;
  END IF;

  SELECT string_agg(c.relname, ', ') INTO bad
    FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
   WHERE n.nspname = 'public' AND c.relkind = 'S'
     AND NOT EXISTS (SELECT 1 FROM pg_depend d WHERE d.objid = c.oid AND d.deptype = 'e')
     AND (has_sequence_privilege('anon', c.oid, 'USAGE,UPDATE,SELECT')
          OR (has_sequence_privilege('authenticated', c.oid, 'USAGE,UPDATE,SELECT')
              AND NOT EXISTS (SELECT 1 FROM pg_depend d JOIN pg_class t ON t.oid = d.refobjid
                               WHERE d.objid = c.oid AND d.deptype IN ('a', 'i')
                                 AND t.relname = 'user_reports')));
  IF bad IS NOT NULL THEN
    RAISE EXCEPTION 'client sequence privilege remains on: %', bad;
  END IF;

  IF EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'app_error_logs'
              AND policyname = 'Authenticated insert error logs') THEN
    RAISE EXCEPTION 'app_error_logs insert policy still exists';
  END IF;
  IF NOT has_table_privilege('authenticated', 'public.user_reports', 'INSERT') THEN
    RAISE EXCEPTION 'user_reports lost authenticated INSERT (should be kept)';
  END IF;
  IF NOT has_table_privilege('service_role', 'public.app_error_logs', 'INSERT')
     OR NOT has_table_privilege('service_role', 'public.dim_word_senses', 'UPDATE')
     OR NOT has_table_privilege('service_role', 'public.trusted_devices', 'DELETE') THEN
    RAISE EXCEPTION 'service_role lost a write privilege (unexpected)';
  END IF;
END $$;

COMMIT;
