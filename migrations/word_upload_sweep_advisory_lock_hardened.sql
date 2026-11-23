-- ============================================================================
-- word_upload_sweep_advisory_lock_hardened.sql — sweep advisory-lock RPCs and
-- watermark table for the nightly word-upload watchlist sweep, locked down
-- Date: 2026-11-23   Review: pkg8. NOT APPLIED.
--
-- *** DECISION REQUIRED: the watermark seed (OPTION A, the default, or OPTION
-- B; see "SEED" below). Read that section before applying. ***
--
-- Replaces migrations/word_upload_sweep_advisory_lock.sql, which is unsafe to
-- apply as written (it stays in place only because the security lint's
-- historical lists pin its path; its header now says so).
--
-- WHAT: the same three objects as that file, same logic:
--   * public.pg_try_advisory_lock_for_word_upload_sweep()  -> pg_try_advisory_lock(1465209719)
--   * public.pg_advisory_unlock_for_word_upload_sweep()    -> pg_advisory_unlock(1465209719)
--     (key 1465209719 = 'WUSw', distinct from the other lock keys; see the old
--     file's header)
--   * table public.word_upload_sweep_state (singleton id = 1,
--     last_swept_created_at, updated_at) and its one seed row.
-- Plus the lock-down the old file lacked, mirroring the live sibling lock pairs
-- (pg_try_advisory_lock_for_ / pg_advisory_unlock_for_ study_plan,
-- model_health, queue_drain, dt_synthesis, read 2026-11-23): LANGUAGE sql,
-- VOLATILE, SECURITY DEFINER, SET search_path = public (exactly as the
-- siblings, which pin public without pg_temp), owner postgres, EXECUTE for
-- service_role only. The table gets RLS on with no policy and no client
-- privilege; service_role (the Flask admin client the job uses,
-- web/scheduler.py _admin_client) bypasses RLS.
--
-- WHY: the nightly job word_upload_watchlist_sweep_nightly (web/scheduler.py,
-- 04:20 UTC) -> services/word_list_import/sweep_cron.run_watchlist_sweep reads
-- this table; today it does not exist live, so every run errors. The old file
-- would create both SECURITY DEFINER functions with Supabase's default EXECUTE
-- for PUBLIC/anon/authenticated and the table readable/writable by anon and
-- authenticated through PostgREST.
--
-- WHAT THE SWEEP DOES (read-only trace, 2026-11-23; no LLM call, no queue):
--   reads  word_upload_sweep_state, tests (id, created_at, vocab_sense_ids
--          WHERE created_at > watermark), user_word_watchlist (active rows whose
--          sense_id is in those tests), and per candidate row tests,
--          test_skill_ratings, dim_test_types, user_skill_ratings;
--   writes user_word_watchlist.last_matched_test_id / last_matched_at
--          (/ last_matched_surfaced_at = NULL on a new match) and the watermark.
--   No cap or batch limit on the tests it reads per run; watchlist writes are
--   chunked by 200.
--
-- SEED (DECISION REQUIRED). The watermark decides what the FIRST run scans.
--   OPTION A (default, conservative): seed at MAX(tests.created_at) as of the
--     apply. The first run sees only tests created after the apply. Nothing
--     is lost: user_word_watchlist is empty live (0 rows), and an upload's own
--     immediate sweep (Step 4) already matches new words against all existing
--     tests. MAX(observed created_at) rather than now() follows the job's own
--     rule (sweep_cron.py docstring: never advance past a value actually seen).
--   OPTION B (the old file's choice): '-infinity', so the first run scans all
--     491 tests and sends their 16,124 distinct sense ids as one
--     .in_('sense_id', [...]) filter, a GET query string of about 98 KB
--     (sum of id lengths + commas). That is far beyond usual HTTP request-line
--     limits (often 8-16 KB; the exact gateway limit was not verified). If the
--     request fails, the run raises before advancing the watermark, so every
--     night would retry the same full scan and fail again.
--   To choose B, swap the two marked lines in the INSERT below before applying.
--   Steady state: tests arrive in bursts (last 30 days: 25 on 2026-11-12, 160 on
--   2026-11-14, none since). A 25-test night sends about 2.4 KB of ids; the
--   160-test burst would have sent 4,682 ids (~30 KB), which may also be over
--   the limit. That is a code fix (chunk the .in_ in sweep_cron.py), not
--   something this file can change.
--
-- WHAT A LEARNER WOULD NOTICE: nothing until someone has watchlist rows (0
-- live). Afterwards, a word they uploaded with no matching test can get a
-- matched test the night one is generated, which then surfaces in their daily
-- session's word_upload slot.
--
-- PRECONDITIONS: none of the three objects exist (VERIFY BEFORE). No code
-- change needed. Idempotent: CREATE OR REPLACE / IF NOT EXISTS / ON CONFLICT DO
-- NOTHING (a re-run never moves a watermark the sweep has advanced).
--
-- VERIFY BEFORE (read-only; expect tbl, try_fn, unlock_fn all NULL):
--   SELECT to_regclass('public.word_upload_sweep_state') AS tbl,
--          to_regprocedure('public.pg_try_advisory_lock_for_word_upload_sweep()') AS try_fn,
--          to_regprocedure('public.pg_advisory_unlock_for_word_upload_sweep()') AS unlock_fn;
-- VERIFY AFTER (read-only; expect two function rows with definer = true,
-- search_path {search_path=public}, acl {postgres=X/postgres,service_role=X/postgres},
-- anon_x = auth_x = false; then rls = true, policies = 0, anon_sel = auth_sel =
-- false, one row with last_swept_created_at = MAX(tests.created_at) at apply
-- time (OPTION A) or -infinity (OPTION B)):
--   SELECT p.oid::regprocedure, p.prosecdef AS definer, p.proconfig AS search_path,
--          p.proacl::text AS acl,
--          has_function_privilege('anon', p.oid, 'EXECUTE') AS anon_x,
--          has_function_privilege('authenticated', p.oid, 'EXECUTE') AS auth_x
--     FROM pg_proc p
--    WHERE p.proname IN ('pg_try_advisory_lock_for_word_upload_sweep',
--                        'pg_advisory_unlock_for_word_upload_sweep');
--   SELECT c.relrowsecurity AS rls,
--          (SELECT count(*) FROM pg_policies WHERE schemaname = 'public'
--             AND tablename = 'word_upload_sweep_state') AS policies,
--          has_table_privilege('anon', c.oid, 'SELECT') AS anon_sel,
--          has_table_privilege('authenticated', c.oid, 'SELECT') AS auth_sel
--     FROM pg_class c WHERE c.oid = 'public.word_upload_sweep_state'::regclass;
--   SELECT id, last_swept_created_at, updated_at FROM public.word_upload_sweep_state;
--
-- ROLLBACK: migrations/word_upload_sweep_advisory_lock_hardened_rollback.sql
-- (drops the two functions and the table; the nightly job then errors again,
-- as it does today).
-- ============================================================================

BEGIN;

CREATE OR REPLACE FUNCTION public.pg_try_advisory_lock_for_word_upload_sweep()
RETURNS boolean
LANGUAGE sql
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT pg_try_advisory_lock(1465209719::bigint);
$$;

CREATE OR REPLACE FUNCTION public.pg_advisory_unlock_for_word_upload_sweep()
RETURNS boolean
LANGUAGE sql
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT pg_advisory_unlock(1465209719::bigint);
$$;

ALTER FUNCTION public.pg_try_advisory_lock_for_word_upload_sweep() OWNER TO postgres;
ALTER FUNCTION public.pg_advisory_unlock_for_word_upload_sweep() OWNER TO postgres;
REVOKE ALL ON FUNCTION public.pg_try_advisory_lock_for_word_upload_sweep() FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.pg_advisory_unlock_for_word_upload_sweep() FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.pg_try_advisory_lock_for_word_upload_sweep() TO service_role;
GRANT EXECUTE ON FUNCTION public.pg_advisory_unlock_for_word_upload_sweep() TO service_role;

CREATE TABLE IF NOT EXISTS public.word_upload_sweep_state (
    id                     smallint     PRIMARY KEY DEFAULT 1,
    last_swept_created_at  timestamptz  NOT NULL DEFAULT '-infinity'::timestamptz,
    updated_at             timestamptz  NOT NULL DEFAULT now(),
    CONSTRAINT word_upload_sweep_state_singleton CHECK (id = 1)
);

-- Service-role only: RLS on, no policy, no client privilege.
ALTER TABLE public.word_upload_sweep_state ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.word_upload_sweep_state FROM PUBLIC, anon, authenticated;
GRANT ALL ON public.word_upload_sweep_state TO service_role;

COMMENT ON TABLE public.word_upload_sweep_state IS
  'Singleton watermark for the recurring word-upload watchlist match sweep '
  '(wiki/tasklist/word-list-import.plan.md Step 5, '
  'services/word_list_import/sweep_cron.run_watchlist_sweep). '
  'last_swept_created_at is the MAX(tests.created_at) actually observed by '
  'the most recent successful sweep pass that found at least one new test — '
  'a run that finds zero new tests leaves this column untouched. Only ever '
  'advanced forward, never read as an exact log of "when the cron last ran" '
  '(see updated_at for that).';

COMMENT ON COLUMN public.word_upload_sweep_state.last_swept_created_at IS
  'Exclusive lower bound: the next sweep queries tests.created_at > this '
  'value. Defaults to -infinity so a fresh install''s first run scans every '
  'existing test exactly once. Advanced to MAX(created_at) of the batch just '
  'processed, never to wall-clock now() — see '
  'services/word_list_import/sweep_cron.py module docstring for the '
  'clock-skew rationale (a value we actually observed in a committed row is '
  'never ahead of reality; an optimistic "now()" can be, and an uncommitted '
  'transaction that lands with a created_at before that "now()" but becomes '
  'visible only after it would then be silently skipped forever).';

-- Seed the single row. ON CONFLICT DO NOTHING: a re-run never moves a
-- watermark the sweep has already advanced. DECISION REQUIRED (see header):
INSERT INTO public.word_upload_sweep_state (id, last_swept_created_at)
SELECT 1,
       COALESCE((SELECT max(created_at) FROM public.tests), '-infinity'::timestamptz)  -- OPTION A (default): start after the newest existing test
       -- '-infinity'::timestamptz                                                     -- OPTION B: first run scans every test (see header)
ON CONFLICT (id) DO NOTHING;

COMMIT;
