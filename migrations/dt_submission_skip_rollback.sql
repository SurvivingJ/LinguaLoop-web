-- Rollback for migrations/dt_submission_skip.sql. Not applied; kept for an operator.
--
-- Order matters: public.dt_next_inputs reads dt_submission.skipped_at, so first
-- restore the function to the definition without it (the version of
-- migrations/dt_next_inputs.sql at commit 972548c) or drop it
-- (migrations/dt_next_inputs_rollback.sql; GET /next then uses its per-table
-- reads, which must also be on code that does not select skipped_at).
-- Then:

ALTER TABLE public.dt_submission DROP COLUMN IF EXISTS skipped_at;
