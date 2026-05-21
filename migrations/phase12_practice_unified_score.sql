-- ============================================================================
-- Phase 12 — Practice Engine merger — practice_unified_score SQL helper
-- Date: 2026-05-21
--
-- IMMUTABLE function that returns the unified score for one candidate item.
-- Called once per (candidate, mode-weights) tuple inside get_practice_session.
--
--   score = alpha · ladder_priority(clamp 0..1)
--         + beta  · norm_irt = min(1, (a² · P · (1−P)) / 0.25)
--         + gamma · norm_bkt = 1 − 2·|p_known − 0.5|
--         + delta · norm_fsrs = sigmoid(clamp(-2, days_overdue/stability, 4))
--
-- Cold-state defaults:
--   p_p_known IS NULL → treat as 0.5 (peak uncertainty)
--   p_ladder_priority IS NULL → treat as 0
--   p_due_date OR p_stability IS NULL → fsrs term = 0
--   p_a IS NULL → treat as 1.0 (calibration default)
--   p_b IS NULL → treat as 0.0
--
-- See wiki/algorithms/practice-unified-score.tech.md.
-- ============================================================================

BEGIN;

CREATE OR REPLACE FUNCTION public.practice_unified_score(
    p_a               numeric,
    p_b               numeric,
    p_theta           numeric,
    p_p_known         numeric,
    p_due_date        date,
    p_stability       real,
    p_today           date,
    p_ladder_priority numeric,
    p_alpha           numeric,
    p_beta            numeric,
    p_gamma           numeric,
    p_delta           numeric
) RETURNS numeric LANGUAGE sql IMMUTABLE AS $$
    WITH params AS (
        SELECT
            COALESCE(p_a, 1.0)   AS a,
            COALESCE(p_b, 0.0)   AS b,
            COALESCE(p_theta, 0.0) AS theta,
            COALESCE(p_p_known, 0.5) AS p_known,
            p_due_date AS due_date,
            p_stability::numeric AS stability,
            COALESCE(p_today, CURRENT_DATE) AS today,
            COALESCE(p_ladder_priority, 0) AS lp,
            COALESCE(p_alpha, 0) AS alpha,
            COALESCE(p_beta,  0) AS beta,
            COALESCE(p_gamma, 0) AS gamma,
            COALESCE(p_delta, 0) AS delta
    ),
    irt AS (
        SELECT
            params.*,
            1.0 / (1.0 + exp(-(a) * ((theta) - (b)))) AS p_correct
        FROM params
    ),
    terms AS (
        SELECT
            irt.*,
            -- ladder term: clamp [0,1]
            GREATEST(0::numeric, LEAST(1::numeric, lp)) AS norm_lad,
            -- IRT term: min(1, a² · P · (1−P) / 0.25)
            LEAST(1.0::numeric,
                  (a * a * p_correct * (1.0 - p_correct)) / 0.25
            ) AS norm_irt,
            -- BKT term: 1 − 2·|p_known − 0.5|
            (1::numeric - 2 * abs(p_known - 0.5)) AS norm_bkt,
            -- FSRS term: sigmoid(clamp(-2, days/stab, 4))
            CASE
                WHEN due_date IS NULL OR stability IS NULL OR stability <= 0 THEN 0::numeric
                ELSE 1::numeric / (1 + exp(-LEAST(4.0::numeric, GREATEST(-2.0::numeric,
                    (today - due_date)::numeric / GREATEST(stability, 1::numeric)
                ))))
            END AS norm_fsrs
        FROM irt
    )
    SELECT alpha * norm_lad
         + beta  * norm_irt
         + gamma * norm_bkt
         + delta * norm_fsrs
    FROM terms
$$;

COMMENT ON FUNCTION public.practice_unified_score IS
    'Unified Practice Engine score: alpha·ladder + beta·irt + gamma·bkt + '
    'delta·fsrs, each term normalized to [0,1]. Mode-dependent weights come '
    'from dim_practice_modes.default_weights. NULL inputs use safe defaults.';

COMMIT;
