-- =============================================================================
-- placement_harness_fks.sql — TEST-ONLY fixture for the local placement harness.
-- NEVER apply to the live database. Not a migration.
-- =============================================================================
-- The live foreign keys the harness DDL omits (read from the live catalog 2026-11-19),
-- so ON DELETE CASCADE behaves as live. Load after the harness base files and before
-- migrations/calibration_placement.sql.
-- =============================================================================

ALTER TABLE public.calibration_responses
  ADD CONSTRAINT calibration_responses_session_id_fkey
    FOREIGN KEY (session_id) REFERENCES public.calibration_sessions(id) ON DELETE CASCADE,
  ADD CONSTRAINT calibration_responses_anchor_sense_id_fkey
    FOREIGN KEY (anchor_sense_id) REFERENCES public.dim_word_senses(id);
ALTER TABLE public.calibration_response_options
  ADD CONSTRAINT calibration_response_options_response_id_fkey
    FOREIGN KEY (response_id) REFERENCES public.calibration_responses(id) ON DELETE CASCADE;
