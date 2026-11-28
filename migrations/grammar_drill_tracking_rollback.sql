-- ============================================================================
-- grammar_drill_tracking_rollback.sql - undo migrations/grammar_drill_tracking.sql
-- Date: 2026-11-27   Task: TASK-1259   ADR-066. NOT APPLIED.
--
-- WHAT: drops public.record_grammar_drill_round(uuid, smallint, uuid, date,
-- jsonb) and the tables public.grammar_drill_daily and
-- public.grammar_drill_state (with their policies and primary key indexes).
--
-- THE RECORDED HISTORY IS LOST. To keep it, save both tables first:
--   COPY (SELECT * FROM public.grammar_drill_daily) TO STDOUT WITH CSV HEADER;
--   COPY (SELECT * FROM public.grammar_drill_state) TO STDOUT WITH CSV HEADER;
--
-- WHAT A LEARNER WOULD NOTICE: the progress charts on /grammar-drill go away
-- and progress no longer follows them to another device. Each browser keeps
-- its own progress (localStorage) and the drills work as before; the page's
-- two API calls answer 503 again, which the page ignores. No code change is
-- needed before or after.
--
-- VERIFY AFTER (read-only; expect all three NULL):
--   SELECT to_regclass('public.grammar_drill_daily') AS daily,
--          to_regclass('public.grammar_drill_state') AS state,
--          to_regprocedure('public.record_grammar_drill_round(uuid,smallint,uuid,date,jsonb)') AS fn;
--
-- Idempotent: IF EXISTS; safe to re-run.
-- ============================================================================

BEGIN;

DROP FUNCTION IF EXISTS public.record_grammar_drill_round(uuid, smallint, uuid, date, jsonb);
DROP TABLE IF EXISTS public.grammar_drill_daily;
DROP TABLE IF EXISTS public.grammar_drill_state;

COMMIT;
