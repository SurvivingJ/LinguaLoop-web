-- ============================================================================
-- Phase 17 — Practice Engine merger — drop deprecation wrappers (TASK-220)
-- Date: 2026-07-13
--
-- The one-release deprecation window opened by phase12_deprecation_wrappers.sql
-- has elapsed (Study Plans stable T+30 days). Both legacy session RPCs are now
-- fully superseded by public.get_practice_session(...) and have no remaining
-- live callers:
--   * the /api/exercises/session and /api/vocab-dojo/session handlers now 302
--     to /api/practice/session
--   * services.practice_session_service routes everything through
--     get_practice_session
--
-- This migration drops both wrappers. phase12_deprecation_wrappers.sql is moved
-- to migrations/archive/ in the same change (it defined only these two
-- functions, both now dropped).
--
-- See wiki/features/practice-engine.tech.md and ADR-007.
-- ============================================================================

BEGIN;

DROP FUNCTION IF EXISTS public.get_exercise_session(uuid, smallint, integer, numeric);
DROP FUNCTION IF EXISTS public.get_ladder_session(uuid, smallint, integer);

COMMIT;
