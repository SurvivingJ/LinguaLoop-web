-- ============================================================================
-- Drop unused RPCs surfaced by the 2026-05-15 production-code audit.
-- Date: 2026-05-15
--
-- Each function below was verified to have:
--   - no caller in routes/ or services/ (no `.rpc('<name>')` references)
--   - no caller in any other migration's SQL body (only its own DEFINITION
--     site, plus incidental comment mentions)
--
-- If any of these resurfaces a missing-dependency error in staging, restore
-- it from the original migration file rather than re-applying this one.
--
-- Verification commands run before this migration:
--   grep -rn "rpc(['\"]<name>"          routes/ services/  → no matches
--   grep -n  "<name>"                    migrations/*.sql   → definition site only
-- ============================================================================

DROP FUNCTION IF EXISTS public.can_use_free_test(uuid);

DROP FUNCTION IF EXISTS public.get_model_for_task(text, smallint);

DROP FUNCTION IF EXISTS public.get_prompt_template(character varying, integer);

DROP FUNCTION IF EXISTS public.get_vocab_recommendations(
    uuid, integer, double precision, double precision, integer
);

-- NOTE: calculate_volatility_multiplier and calculate_elo_rating are kept.
-- The audit flagged them as superseded, but process_test_submission_reduced_repeats.sql
-- (the latest active version) still references them internally.
