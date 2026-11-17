-- Dual translation "Skip this passage", 2026-11-17 (TASK-991 b).
--
-- GET /api/dual-translation/next now resumes the passage the learner was last
-- shown until they translate it or skip it. A skip is recorded here: the open
-- dt_submission row (no grade, empty reproduction) gets skipped_at. A skipped
-- passage is served again only after everything the learner has not seen yet,
-- and its skipped_at is cleared when that happens (it is the current passage
-- again).
--
-- 1. One new NULLable column; no default, so no table rewrite. Code deployed
--    before this change never reads or writes it.
-- 2. One bounded backfill: every open row that exists today is marked skipped,
--    so that old never-started passages do not all come back as "resume this"
--    (measured before applying: see the count in wiki/log.md 2026-11-17; all
--    rows belong to the developer's test account). Only rows whose skipped_at
--    is NULL, reproduction is empty and that have no grade are touched.
--
-- Apply BEFORE re-applying migrations/dt_next_inputs.sql (it reads the column).
-- Rollback: migrations/dt_submission_skip_rollback.sql

ALTER TABLE public.dt_submission
    ADD COLUMN IF NOT EXISTS skipped_at timestamptz;

COMMENT ON COLUMN public.dt_submission.skipped_at IS
    'When the learner pressed "Skip this passage" on this open submission (no grade, empty '
    'reproduction). NULL on an open row means GET /next resumes it. Cleared when the passage '
    'is served again.';

UPDATE public.dt_submission s
   SET skipped_at = now()
 WHERE s.skipped_at IS NULL
   AND coalesce(s.reproduction, '') = ''
   AND NOT EXISTS (SELECT 1 FROM public.dt_grade g WHERE g.submission_id = s.id);
