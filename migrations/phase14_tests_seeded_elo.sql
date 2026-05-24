-- ============================================================================
-- Phase 14 — Generation Quality — tests.seeded_elo column
-- Date: 2026-05-24
--
-- Stores the lexical-complexity-derived seed ELO produced by
-- services.test_generation.difficulty_scorer at test creation time.
--
-- Why a separate column rather than overwriting test_skill_ratings.elo_rating?
--   * test_skill_ratings.elo_rating is the empirical ELO that drifts with
--     learner attempts — that's the ground truth we want to preserve.
--   * tests.seeded_elo is the model's a-priori prediction. Holding both lets
--     us measure scorer accuracy post-hoc:
--         MAE = mean(|seeded_elo - empirical_elo|)
--             over tests with >= 20 total_attempts
--     and refit scorer weights once data accumulates.
--   * On insert, test_skill_ratings.elo_rating is also seeded from the
--     scorer (via existing get_initial_elo path), so day-zero behaviour
--     matches what the scorer predicts. The two values only diverge as
--     attempts roll in.
--
-- Nullable — pre-existing tests have no scorer output. Backfill is optional
-- and not part of this migration.
-- ============================================================================

BEGIN;

ALTER TABLE public.tests
    ADD COLUMN IF NOT EXISTS seeded_elo integer;

COMMENT ON COLUMN public.tests.seeded_elo IS
    'Lexical-complexity-derived seed ELO from '
    'services.test_generation.difficulty_scorer at test creation. Compare '
    'against test_skill_ratings.elo_rating (empirical) for tests with '
    '>=20 attempts to evaluate scorer accuracy.';

COMMIT;
