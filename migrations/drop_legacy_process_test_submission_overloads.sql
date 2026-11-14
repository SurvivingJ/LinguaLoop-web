-- =============================================================================
-- drop_legacy_process_test_submission_overloads.sql  (codebase review 2026-11)
-- =============================================================================
-- Purpose: make the repo say, in a non-archived file, that the two legacy
-- signatures of process_test_submission are gone. Until now their only DROP
-- lived in migrations/archive/process_test_submission_v2.sql, while active
-- files still CREATE them (elo_functions.sql, which also grants EXECUTE to
-- authenticated; phase3_rpc_fixes.sql; wire_volatility_and_exclude_attempted.sql;
-- and listening_lab_rpcs.sql, archived together with this change). A function
-- created on Supabase is executable by anon and authenticated unless revoked,
-- so a surviving overload would be a client-callable SECURITY DEFINER function
-- with the old NULL-permissive auth gate.
--
--   7-argument  (uuid, uuid, smallint, smallint, jsonb, boolean, uuid)
--   legacy text (uuid, uuid, text, text, integer, integer, text, integer, boolean)
--
-- The current function is the 9-argument one (prestudy_elo_factor.sql; body
-- now in process_test_submission_set_based_grading.sql). Nothing in the repo
-- calls the legacy text signature, and a surviving 7-argument overload would
-- only make calls that omit the newer optional arguments ambiguous. The
-- 8-argument overload is dropped by prestudy_elo_factor.sql itself and is not
-- touched here.
--
-- Pre-checks:
--   1. Which overloads exist live (expected: only the 9-argument one, in which
--      case this file is a no-op):
--        SELECT p.oid::regprocedure, p.proacl FROM pg_proc p
--         WHERE p.pronamespace = 'public'::regnamespace AND p.proname = 'process_test_submission';
--   2. If a legacy overload does exist, save it before dropping:
--        SELECT pg_get_functiondef(p.oid) FROM pg_proc p
--         WHERE p.pronamespace = 'public'::regnamespace AND p.proname = 'process_test_submission';
--
-- The guard refuses to run unless the 9-argument function exists, so this can
-- never leave the app without a submission RPC.
--
-- Idempotent (DROP ... IF EXISTS). REQUIRES USER APPROVAL TO APPLY LIVE.
--
-- Rollback: recreate the dropped overload from the definition saved in
-- pre-check 2 (there is no reason to: nothing in the repo calls either).
-- =============================================================================

BEGIN;

DO $$
BEGIN
  IF to_regprocedure('public.process_test_submission(uuid,uuid,smallint,smallint,jsonb,boolean,uuid,boolean,boolean)') IS NULL THEN
    RAISE EXCEPTION 'the 9-argument process_test_submission is missing; apply prestudy_elo_factor.sql first';
  END IF;
END $$;

DROP FUNCTION IF EXISTS public.process_test_submission(uuid, uuid, smallint, smallint, jsonb, boolean, uuid);
DROP FUNCTION IF EXISTS public.process_test_submission(uuid, uuid, text, text, integer, integer, text, integer, boolean);

COMMIT;
