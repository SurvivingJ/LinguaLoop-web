-- ============================================================================
-- TASK-534 — exercise-type effectiveness: outcome capture + the view.
--
-- Answers "which exercise types actually move knowledge, at which stage of
-- knowing a word, per minute of learner time" — the input to Phase-4
-- adaptivity (TASK-535/536) and to content QA.
--
-- Two parts, because the first is what makes the second possible:
--
--   1. Outcome capture on exercise_attempts. user_vocabulary_knowledge holds
--      only the CURRENT p_known and there is no history table, so the delta an
--      individual attempt produced is not recoverable after the fact. The BKT
--      RPC already returns out_p_known_before / out_p_known_after and the
--      service already reads them — they were simply never persisted. Both
--      columns are nullable: every attempt before this migration has no
--      capture, and inventing a value for them would be fabrication.
--
--   2. The view itself.
-- ============================================================================

-- ---------------------------------------------------------------------------
-- 1. Outcome capture
-- ---------------------------------------------------------------------------
ALTER TABLE public.exercise_attempts
  ADD COLUMN IF NOT EXISTS p_known_before numeric,
  ADD COLUMN IF NOT EXISTS p_known_after  numeric;

COMMENT ON COLUMN public.exercise_attempts.p_known_before IS
  'BKT p_known immediately before this attempt. NULL when BKT did not run '
  '(repeat attempts, non-sense-linked items, or rows predating TASK-534).';
COMMENT ON COLUMN public.exercise_attempts.p_known_after IS
  'BKT p_known immediately after this attempt. NULL under the same conditions.';

-- The view groups by bucket + type over captured rows only. Partial, because
-- captured rows will be a minority of the table for a long time.
CREATE INDEX IF NOT EXISTS idx_ea_effectiveness
  ON public.exercise_attempts (exercise_type, p_known_before)
  WHERE p_known_before IS NOT NULL AND p_known_after IS NOT NULL;


-- ---------------------------------------------------------------------------
-- 2. vw_exercise_type_effectiveness
-- ---------------------------------------------------------------------------
-- Design notes, in the order they bite:
--
-- * Only rows with BOTH p_known values are counted. An attempt where BKT never
--   ran did not have the opportunity to move knowledge, so charging its minutes
--   against a type's rate would penalise whichever types happen to be served
--   most often as repeats. The honest denominator is time on attempts that
--   could have moved the needle.
--
-- * Buckets are on p_known_BEFORE — the learner's state on arrival. Bucketing
--   on "after" would sort attempts by their own outcome and manufacture the
--   correlation the view exists to measure.
--
-- * time_taken_ms is clamped, not trusted. Missing/zero/negative rows are
--   excluded (a zero-minute denominator yields an infinite rate), and anything
--   over 5 minutes is capped at 5 — matching _effective_practice_seconds in
--   practice_session_service.py, whose reasoning is that a tab left open is not
--   study time. Uncapped, one abandoned tab makes a type look worthless.
--
-- * Rates are per MINUTE, so a fast type that moves knowledge a little can
--   legitimately beat a slow type that moves it a lot. That is the intended
--   comparison: learner time is the scarce resource.
--
-- * attempts is exposed alongside every rate so a reader can see which cells
--   are too thin to act on. A 3-attempt cell will happily report a
--   spectacular rate.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW public.vw_exercise_type_effectiveness AS
WITH captured AS (
    SELECT
        ea.exercise_type,
        ea.user_id,
        ea.sense_id,
        ea.is_correct,
        ea.p_known_before,
        ea.p_known_after,
        (ea.p_known_after - ea.p_known_before)                    AS delta_p_known,
        LEAST(ea.time_taken_ms, 300000)::numeric / 60000.0        AS minutes,
        CASE
            WHEN ea.p_known_before < 0.2 THEN '0.0-0.2'
            WHEN ea.p_known_before < 0.4 THEN '0.2-0.4'
            WHEN ea.p_known_before < 0.6 THEN '0.4-0.6'
            WHEN ea.p_known_before < 0.8 THEN '0.6-0.8'
            ELSE                               '0.8-1.0'
        END                                                       AS p_known_bucket
    FROM public.exercise_attempts ea
    WHERE ea.p_known_before IS NOT NULL
      AND ea.p_known_after  IS NOT NULL
      AND ea.exercise_type  IS NOT NULL
      AND ea.time_taken_ms  IS NOT NULL
      AND ea.time_taken_ms  > 0
)
SELECT
    p_known_bucket,
    exercise_type,
    count(*)                                                   AS attempts,
    count(DISTINCT user_id)                                    AS users,
    count(DISTINCT sense_id)                                   AS senses,
    round(avg(CASE WHEN is_correct THEN 1.0 ELSE 0.0 END), 4)  AS accuracy,
    round(avg(delta_p_known), 6)                               AS mean_delta_p_known,
    round(sum(minutes), 4)                                     AS total_minutes,
    CASE
        WHEN sum(minutes) > 0
        THEN round(sum(delta_p_known) / sum(minutes), 6)
        ELSE NULL
    END                                                        AS delta_p_known_per_minute
FROM captured
GROUP BY p_known_bucket, exercise_type
ORDER BY p_known_bucket, delta_p_known_per_minute DESC NULLS LAST;

COMMENT ON VIEW public.vw_exercise_type_effectiveness IS
  'TASK-534. Per (p_known bucket on arrival, exercise_type): knowledge gained '
  'per minute of learner time. Counts only attempts where BKT ran (both '
  'p_known values captured) and time_taken_ms is positive; per-attempt time is '
  'capped at 5 minutes. Read `attempts` before acting on any rate.';

GRANT SELECT ON public.vw_exercise_type_effectiveness TO authenticated;


-- ============================================================================
-- Verification
-- ============================================================================
-- Capture is landing (expect a growing count once practice traffic runs):
--   SELECT count(*) FILTER (WHERE p_known_before IS NOT NULL) AS captured,
--          count(*) AS total
--   FROM exercise_attempts;
--
-- The view returns one row per populated (bucket, type) cell:
--   SELECT * FROM vw_exercise_type_effectiveness;
--
-- No cell may report a rate without attempts backing it:
--   SELECT * FROM vw_exercise_type_effectiveness
--   WHERE delta_p_known_per_minute IS NOT NULL AND attempts = 0;   -- expect 0 rows
-- ============================================================================
