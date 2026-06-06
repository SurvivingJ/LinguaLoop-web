-- ============================================================================
-- Part F #2 — Seeded-vs-empirical difficulty calibration (query/view only)
-- Date: 2026-06-06
--
-- WHAT
--   Two read-only views comparing the difficulty_scorer's a-priori seed
--   (tests.seeded_elo) against the empirical, attempt-driven rating
--   (test_skill_ratings.elo_rating):
--     * v_test_difficulty_calibration          — per-test rows
--     * v_test_difficulty_calibration_summary  — MAE / bias rollup
--
-- WHY
--   Tells us whether services.test_generation.difficulty_scorer actually
--   predicts difficulty, and surfaces the data needed to refit its three
--   weights (_W_ZIPF, _W_LEN, _W_TTR in difficulty_scorer.py). Per the scorer's
--   own docstring the refit target is test_skill_ratings.elo_rating over tests
--   with >= 20 attempts — exactly what the summary view's *_20plus columns give.
--
-- No schema change, no data written. CREATE OR REPLACE VIEW is idempotent.
-- ============================================================================

BEGIN;

-- ---------------------------------------------------------------------------
-- Per-test calibration rows. Only tests that (a) have a scorer seed and
-- (b) have accrued at least one attempt are meaningful to compare.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW public.v_test_difficulty_calibration AS
SELECT
  t.id                                AS test_id,
  t.slug,
  t.language_id,
  t.difficulty,                       -- operator-chosen tier (1..9)
  t.tier,
  t.seeded_elo,                       -- a-priori scorer prediction
  tsr.test_type_id,
  tsr.elo_rating                      AS empirical_elo,
  tsr.total_attempts,
  (tsr.elo_rating - t.seeded_elo)     AS elo_error,       -- + = test harder than seeded
  abs(tsr.elo_rating - t.seeded_elo)  AS abs_elo_error
FROM public.tests t
JOIN public.test_skill_ratings tsr ON tsr.test_id = t.id
WHERE t.seeded_elo IS NOT NULL
  AND tsr.total_attempts > 0;

COMMENT ON VIEW public.v_test_difficulty_calibration IS
    'Part F #2: per-test seeded_elo vs empirical elo_rating. elo_error > 0 '
    'means learners found the test harder than the scorer predicted.';

-- ---------------------------------------------------------------------------
-- Rollup: mean absolute error + mean bias, overall and over the >=20-attempt
-- cohort the scorer refit should train on.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW public.v_test_difficulty_calibration_summary AS
SELECT
  count(*)                                                         AS n_tests,
  count(*) FILTER (WHERE total_attempts >= 20)                     AS n_tests_20plus,
  round(avg(abs_elo_error), 1)                                     AS mae_all,
  round(avg(abs_elo_error) FILTER (WHERE total_attempts >= 20), 1) AS mae_20plus,
  round(avg(elo_error), 1)                                         AS mean_bias_all,
  round(avg(elo_error) FILTER (WHERE total_attempts >= 20), 1)     AS mean_bias_20plus
FROM public.v_test_difficulty_calibration;

COMMENT ON VIEW public.v_test_difficulty_calibration_summary IS
    'Part F #2: scorer-accuracy rollup. mae_20plus / mean_bias_20plus are the '
    'headline numbers for evaluating + refitting difficulty_scorer weights.';

COMMIT;
