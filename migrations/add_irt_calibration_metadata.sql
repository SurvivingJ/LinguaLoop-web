-- ============================================================================
-- IRT calibration metadata columns + persistence/lock RPCs
-- Date: 2026-05-12
--
-- Adds three columns used by the nightly IRT calibrator
-- (services/irt/calibrator.py):
--   irt_n_attempts       — number of first-attempt observations that fed
--                          the latest fit (0 = never calibrated, still on
--                          tier-seeded defaults).
--   irt_calibrated_at    — timestamp of the latest successful fit; NULL
--                          means the row is still on its seeded values.
--   irt_se_difficulty    — standard error of the difficulty estimate from
--                          the inverse Hessian; consumers can widen the
--                          IRT target band for rows with high SE.
--
-- Plus three small helper RPCs the calibrator calls through the supabase
-- client (since postgrest can't invoke built-in functions with positional
-- bigint args, and we want `now()` evaluated server-side):
--   irt_apply_calibration(...) — persists a fitted row in one round-trip.
--   irt_try_lock()             — wraps pg_try_advisory_lock to a fixed key.
--   irt_release_lock()         — wraps pg_advisory_unlock to a fixed key.
--
-- The partial index lets selection-side IRT weighting cheaply filter to
-- the calibrated subset (`WHERE irt_calibrated_at IS NOT NULL`).
-- ============================================================================

BEGIN;

ALTER TABLE public.exercises
    ADD COLUMN IF NOT EXISTS irt_n_attempts    integer       NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS irt_calibrated_at timestamptz,
    ADD COLUMN IF NOT EXISTS irt_se_difficulty numeric(5,3);

CREATE INDEX IF NOT EXISTS idx_exercises_irt_calibrated
    ON public.exercises(irt_calibrated_at)
    WHERE irt_calibrated_at IS NOT NULL;


-- ----------------------------------------------------------------------------
-- Persistence RPC
-- ----------------------------------------------------------------------------
-- Called once per fitted exercise. Returns nothing; failure surfaces as an
-- exception to the python caller.

CREATE OR REPLACE FUNCTION public.irt_apply_calibration(
    p_exercise_id     uuid,
    p_discrimination  numeric,
    p_difficulty      numeric,
    p_se_difficulty   numeric,
    p_n_attempts      integer
)
RETURNS void
LANGUAGE sql
SECURITY DEFINER
SET search_path = public
AS $$
    UPDATE public.exercises
       SET irt_discrimination  = p_discrimination,
           irt_difficulty      = p_difficulty,
           irt_se_difficulty   = p_se_difficulty,
           irt_n_attempts      = p_n_attempts,
           irt_calibrated_at   = now()
     WHERE id = p_exercise_id;
$$;


-- ----------------------------------------------------------------------------
-- Advisory-lock wrappers
-- ----------------------------------------------------------------------------
-- 8901234567890123 is the fixed lock key for the nightly IRT job. Wrapped
-- because postgrest cannot call pg_try_advisory_lock(bigint) directly with
-- the supabase-py rpc() helper (which only forwards named args).

CREATE OR REPLACE FUNCTION public.irt_try_lock()
RETURNS boolean
LANGUAGE sql
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT pg_try_advisory_lock(8901234567890123::bigint);
$$;

CREATE OR REPLACE FUNCTION public.irt_release_lock()
RETURNS boolean
LANGUAGE sql
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT pg_advisory_unlock(8901234567890123::bigint);
$$;


-- ----------------------------------------------------------------------------
-- Theta computer
-- ----------------------------------------------------------------------------
-- One-shot logit-of-clipped-accuracy used by both the calibrator (real-time
-- lookup for the selection-side IRT weight in phase11_irt_selection.sql) and
-- the Python wrapper when no separate cache is needed. Clips to [0.05, 0.95]
-- so users with 0% or 100% first-attempt accuracy don't produce ±infinity.

CREATE OR REPLACE FUNCTION public.irt_compute_user_theta(
    p_user_id     uuid,
    p_language_id smallint
)
RETURNS numeric
LANGUAGE sql
STABLE
AS $$
    WITH agg AS (
        SELECT COUNT(*)                                     AS n,
               COUNT(*) FILTER (WHERE is_correct)::numeric  AS k
          FROM public.user_exercise_history
         WHERE user_id          = p_user_id
           AND language_id      = p_language_id
           AND is_first_attempt = true
    )
    SELECT CASE
        WHEN n = 0 THEN 0.0
        ELSE ln(
            LEAST(GREATEST(k / n::numeric, 0.05), 0.95)
            / (1 - LEAST(GREATEST(k / n::numeric, 0.05), 0.95))
        )
    END
      FROM agg;
$$;

COMMIT;
