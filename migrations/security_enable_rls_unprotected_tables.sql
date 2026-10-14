-- =============================================================================
-- security_enable_rls_unprotected_tables.sql  (TASK-876, security-hardening S2)
-- =============================================================================
-- Purpose: 32 public tables have RLS OFF and arwdDxtm for anon + authenticated
-- (prompt_templates, llm_calls, exercises, word_assets, user_classifier_mastery,
-- dt_*, generation_*, corpus_*, dim_classifier*, topics, categories, ...). Enable
-- RLS and revoke every client privilege. No policies are created: only
-- service_role (bypasses RLS, keeps its grants) accesses them. FORCE RLS is NOT
-- used (postgres/table owner must be unchanged).
--
-- The table list is DERIVED from pg_class at apply time (relkind='r', public,
-- relrowsecurity=false) rather than hardcoded, and the migration FAILS if the
-- count differs from the 32 observed on 2026-10-14 (so a drifted schema is
-- reviewed instead of silently swept). Tables that already have RLS are not
-- touched. Sequences: anon/authenticated lose all privileges on every sequence in
-- public (no client does direct inserts; Flask uses service_role).
--
-- Pre-flight (code + read-only catalog, 2026-10-14):
--   * Anon-client (get_supabase()) users: middleware/auth.py, test_service.py
--     (tests/questions/test_attempts/attempt_responses), dimension_service.py
--     (dim_languages, dim_test_types, dim_exercise_capabilities), routes/users.py
--     (users). None reads any of the 32 tables. llm_service.py / model_health.py /
--     timing.py / judges/base.py prefer the admin client and only fall back to anon
--     when SUPABASE_SERVICE_ROLE_KEY is missing (that fallback will now be denied:
--     the service key must be set in every deployed environment).
--   * Routes touching exercises/word_assets/topics/categories (exercises.py,
--     vocab_admin.py, practice.py, test_generation/topic_generation clients) use
--     get_supabase_admin().
--   * SECURITY INVOKER functions referencing these tables (get_practice_session,
--     get_exercise_session, ladder_record_attempt, get_prompt_template,
--     get_top_collocations_for_sources, bkt_phase, sync_exercise_history,
--     trg_*_sense_quarantine) are only called through the admin client
--     (practice_session_service, ladder_service). Any direct authenticated-JWT
--     RPC call to them would now fail: that is intended.
--   * Views over these tables (corpus_statistics, v_ladder_judge_reject_rates,
--     v_sense_family_coverage, vw_distractor_error_analysis,
--     vw_exercise_performance_by_type) are NOT security_invoker (live reloptions is NULL,
--     owner postgres): they run as their owner and BYPASS RLS, so this migration
--     does NOT close client access to them (anon/authenticated still hold arwdDxtm
--     on the views). They stay exposed until security_views_invoker.sql (TASK-879)
--     is applied: apply it immediately after this file.
--   * Live: 87 public base tables, 32 with RLS off; sequence ACLs are rwU for
--     anon+authenticated on every public sequence.
--
-- Idempotent and re-runnable: once RLS is on, the derived list is empty. Because
-- of the count assertion, re-running after success is handled by the
-- "already applied" branch (0 unprotected tables is a no-op, not an error).
-- REQUIRES USER APPROVAL TO APPLY LIVE.
-- =============================================================================

BEGIN;

DO $$
DECLARE
  expected_count CONSTANT int := 32;
  tbls  text[];
  t     text;
  n     int;
BEGIN
  SELECT coalesce(array_agg(c.relname::text ORDER BY c.relname), '{}')
    INTO tbls
    FROM pg_class c
    JOIN pg_namespace ns ON ns.oid = c.relnamespace
   WHERE ns.nspname = 'public'
     AND c.relkind = 'r'
     AND NOT c.relispartition
     AND NOT c.relrowsecurity;

  n := coalesce(array_length(tbls, 1), 0);

  IF n = 0 THEN
    RAISE NOTICE 'TASK-876: no public tables with RLS off (already applied); skipping table loop';
  ELSIF n <> expected_count THEN
    RAISE EXCEPTION 'TASK-876: expected % unprotected public tables, found % (%). Review before applying.',
      expected_count, n, array_to_string(tbls, ', ');
  END IF;

  FOREACH t IN ARRAY tbls LOOP
    EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', t);
    -- PUBLIC too: anon inherits through the =X pseudo-role grant.
    EXECUTE format('REVOKE ALL ON TABLE public.%I FROM PUBLIC, anon, authenticated', t);
  END LOOP;

  -- Post-conditions for the tables handled in this run.
  FOREACH t IN ARRAY tbls LOOP
    IF NOT (SELECT relrowsecurity FROM pg_class WHERE oid = format('public.%I', t)::regclass) THEN
      RAISE EXCEPTION 'TASK-876: RLS still off on %', t;
    END IF;
    IF has_table_privilege('anon', format('public.%I', t), 'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER')
       OR has_table_privilege('authenticated', format('public.%I', t), 'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER') THEN
      RAISE EXCEPTION 'TASK-876: client privilege remains on %', t;
    END IF;
    IF NOT has_table_privilege('service_role', format('public.%I', t), 'SELECT,INSERT,UPDATE,DELETE') THEN
      RAISE EXCEPTION 'TASK-876: service_role lost access on %', t;
    END IF;
  END LOOP;
END $$;

-- Sequences: no client uses nextval directly (inserts go through service_role).
-- service_role/postgres keep their grants.
REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM PUBLIC, anon, authenticated;

COMMIT;
