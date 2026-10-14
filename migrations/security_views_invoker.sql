-- =============================================================================
-- security_views_invoker.sql  (TASK-879, security-hardening S11)
-- =============================================================================
-- Purpose: the analytics views were created WITHOUT security_invoker, so they run
-- as their owner (bypassing RLS on exercise_attempts / exercises / ...), and they
-- carry client grants (anon + authenticated, including write privileges).
-- vw_distractor_error_analysis is per-user (user_id + error pattern) and is the
-- real leak: any visitor with the anon key could read every user's error profile.
--
-- Developer decisions (2026-10-14):
--   (4) vw_exercise_type_effectiveness: REVOKE authenticated SELECT as well. The
--       grant at migrations/task534_exercise_type_effectiveness.sql:119 was never
--       exercised by a browser: the only repo reader is
--       scripts/validate_effectiveness_view.py (get_supabase_admin() =
--       service_role). templates/exercise_type_effectiveness.html exists but NO
--       route or service in the repo renders it or queries the view. If an admin
--       route is added later it MUST read through get_supabase_admin().
--
-- Views covered (8, all in public; any not present is skipped):
--   corpus_statistics, v_ladder_judge_reject_rates, v_sense_family_coverage,
--   v_test_difficulty_calibration, v_test_difficulty_calibration_summary,
--   vw_distractor_error_analysis, vw_exercise_performance_by_type,
--   vw_exercise_type_effectiveness
--
-- Result per view:
--   * security_invoker = true (defence in depth: a future accidental client grant
--     would still be filtered by RLS on the base tables);
--   * ALL privileges revoked from PUBLIC, anon and authenticated (reads AND writes);
--   * service_role keeps SELECT (granted explicitly if missing) so Flask/scripts
--     (queue_drain.py, dedupe_legacy_vocab_exercises.py, validate_effectiveness_view.py)
--     are unaffected. service_role bypasses RLS, so invoker semantics change
--     nothing for it. 876 already revoked client grants on the base tables.
--
-- Pre-flight (code, 2026-10-14): no repo caller reads any of these views with an
-- anon or user-JWT client. Live reloptions/relacl were NOT confirmed read-only
-- (no project ref available to this session) - run the verification query below
-- before and after applying.
--
-- Requires PostgreSQL 15+ (security_invoker). Idempotent and re-runnable. DDL only.
-- REQUIRES USER APPROVAL TO APPLY LIVE. Apply after 876
-- (security_enable_rls_unprotected_tables.sql).
--
-- Verification:
--   SELECT c.relname, c.reloptions, c.relacl FROM pg_class c
--   JOIN pg_namespace n ON n.oid=c.relnamespace
--   WHERE n.nspname='public' AND c.relkind='v' AND c.relname IN
--    ('corpus_statistics','v_ladder_judge_reject_rates','v_sense_family_coverage',
--     'v_test_difficulty_calibration','v_test_difficulty_calibration_summary',
--     'vw_distractor_error_analysis','vw_exercise_performance_by_type',
--     'vw_exercise_type_effectiveness');
-- =============================================================================

BEGIN;

DO $$
DECLARE
  v text;
  views text[] := ARRAY[
    'corpus_statistics','v_ladder_judge_reject_rates','v_sense_family_coverage',
    'v_test_difficulty_calibration','v_test_difficulty_calibration_summary',
    'vw_distractor_error_analysis','vw_exercise_performance_by_type',
    'vw_exercise_type_effectiveness'];
  p text;
  r text;
BEGIN
  FOREACH v IN ARRAY views LOOP
    IF to_regclass(format('public.%I', v)) IS NULL THEN
      RAISE NOTICE 'TASK-879: view public.% not found, skipped', v;
      CONTINUE;
    END IF;

    EXECUTE format('ALTER VIEW public.%I SET (security_invoker = true)', v);
    EXECUTE format('REVOKE ALL ON TABLE public.%I FROM PUBLIC, anon, authenticated', v);
    EXECUTE format('GRANT SELECT ON TABLE public.%I TO service_role', v);

    -- post-conditions
    IF NOT coalesce('security_invoker=true' = ANY (SELECT unnest(reloptions)
         FROM pg_class WHERE oid = format('public.%I', v)::regclass), false) THEN
      RAISE EXCEPTION 'TASK-879: % is not security_invoker', v;
    END IF;
    FOREACH r IN ARRAY ARRAY['anon','authenticated'] LOOP
      FOREACH p IN ARRAY ARRAY['SELECT','INSERT','UPDATE','DELETE','TRUNCATE','REFERENCES','TRIGGER'] LOOP
        IF has_table_privilege(r, format('public.%I', v), p) THEN
          RAISE EXCEPTION 'TASK-879: % still has % on view %', r, p, v;
        END IF;
      END LOOP;
    END LOOP;
  END LOOP;
END $$;

-- Report (not fail) any other public view that still exposes client grants.
DO $$
DECLARE rec record;
BEGIN
  FOR rec IN
    SELECT c.relname FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
     WHERE n.nspname = 'public' AND c.relkind IN ('v','m')
       AND (has_table_privilege('anon', c.oid, 'SELECT')
         OR has_table_privilege('authenticated', c.oid, 'SELECT'))
  LOOP
    RAISE NOTICE 'TASK-879: other public view/matview with client SELECT: % (review)', rec.relname;
  END LOOP;
END $$;

COMMIT;
