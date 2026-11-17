-- ============================================================================
-- dt_passage_reference_drop.sql — drop the whole-passage reference table
-- Date: 2026-11-17
--
-- dt_passage_reference held one L1 reference per whole dual-translation passage
-- (migrations/dual_translation_groundwork.sql). Passages are sentence windows
-- now (ADR-037): their L1 text comes from test_sentence_references. The
-- whole-passage pool was retired and its rows deleted on 2026-11-17 (backup:
-- data/backups/dt_legacy_passages_2026-11-17.json), leaving this table empty.
--
-- Nothing reads it any more:
--   * build_daily_session counts sentence windows
--     (migrations/build_daily_session_dt_windows.sql, applied first; now canonical in
--      migrations/build_daily_session_dt_agreed.sql);
--   * dt_next_inputs no longer returns the legacy list (migrations/dt_next_inputs.sql);
--   * services/dual_translation/cards.py and repair/ read the sentence references.
--
-- Apply only after the application code on this branch is deployed: code
-- deployed before it still queries the table (error cards, sentence repair)
-- and would fail on a missing relation.
--
-- The guard refuses to drop a table that has rows.
-- Rollback: re-create the table from migrations/dual_translation_groundwork.sql
-- (section "dt_passage_reference") and restore rows from the backup file.
-- ============================================================================

DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM public.dt_passage_reference LIMIT 1) THEN
    RAISE EXCEPTION 'dt_passage_reference is not empty; not dropping';
  END IF;
  IF EXISTS (
    SELECT 1 FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
     WHERE n.nspname = 'public' AND p.prokind = 'f' AND p.prosrc ILIKE '%dt_passage_reference%'
  ) THEN
    RAISE EXCEPTION 'a database function still reads dt_passage_reference; not dropping';
  END IF;
END $$;

DROP TABLE public.dt_passage_reference;
