-- Add dt_submission.correction_style — the correction-style A/B arm actually
-- shown to the learner for this submission (dual-translation TASK-617).
--
-- The arm is assigned by config.py::Config.resolve_correction_style — a
-- deterministic 50/50 hash of user_id in 'experiment' mode, or a forced value
-- via the DT_CORRECTION_STYLE flag — and stamped here at GET /next time, when
-- the dt_submission row is created (routes/dual_translation.py::get_next).
--
-- Why a column and not just recompute-from-user_id at analysis time: the arm is
-- only reproducible while the config mode AND bucketing stay fixed. Persisting
-- it per-submission keeps the experiment analyzable even if either changes
-- later — each row records exactly what that learner saw.
--
-- Nullable: rows created before this column existed (including the TASK-607
-- smoke submission) carry no assignment, so readers must tolerate NULL. The
-- CHECK restricts values to the two known arms while still allowing NULL.

ALTER TABLE public.dt_submission
  ADD COLUMN IF NOT EXISTS correction_style text
    CHECK (correction_style IN ('direct_metalinguistic', 'flag_only'));

COMMENT ON COLUMN public.dt_submission.correction_style IS
    'Correction-style A/B arm shown for this submission (dual-translation '
    'TASK-617): direct_metalinguistic (eager) or flag_only (reveal-on-demand). '
    'Stamped at GET /next by config.resolve_correction_style. NULL for rows '
    'created before the experiment existed.';
