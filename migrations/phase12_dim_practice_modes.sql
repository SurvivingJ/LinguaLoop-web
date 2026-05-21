-- ============================================================================
-- Phase 12 — Practice Engine merger — practice-mode registry
-- Date: 2026-05-21
--
-- Three rows:
--   acquisition  — word-anchored learning; ladder dominates
--   maintenance  — retention; FSRS dominates
--   auto         — dispatcher (NULL weights); resolves to one of the above
--                  via (FSRS-due-today + decayed) >= active-ladder-words
--                  rule. See wiki/algorithms/practice-unified-score.tech.md.
--
-- Weights are jsonb so they're tunable without a migration. The merged
-- get_practice_session RPC loads them once per call and passes as constants
-- to the practice_unified_score helper.
--
-- See wiki/features/practice-engine.tech.md and ADR-007.
-- ============================================================================

BEGIN;

CREATE TABLE IF NOT EXISTS public.dim_practice_modes (
    mode_id          smallint PRIMARY KEY,
    name             text     NOT NULL UNIQUE,
    default_weights  jsonb,                              -- null for 'auto'
    is_active        boolean  NOT NULL DEFAULT true,
    CONSTRAINT dim_practice_modes_weights_shape CHECK (
        default_weights IS NULL OR (
            jsonb_typeof(default_weights) = 'object'
            AND default_weights ? 'alpha'
            AND default_weights ? 'beta'
            AND default_weights ? 'gamma'
            AND default_weights ? 'delta'
        )
    )
);

COMMENT ON TABLE public.dim_practice_modes IS
    'Practice mode registry. default_weights jsonb carries the {alpha,beta,'
    'gamma,delta} tuple used by practice_unified_score. The auto row carries '
    'no weights; its dispatcher resolves to acquisition or maintenance at '
    'session-start.';

INSERT INTO public.dim_practice_modes (mode_id, name, default_weights) VALUES
    (1, 'acquisition',
        '{"alpha":0.40,"beta":0.30,"gamma":0.25,"delta":0.05}'::jsonb),
    (2, 'maintenance',
        '{"alpha":0.05,"beta":0.15,"gamma":0.30,"delta":0.50}'::jsonb),
    (3, 'auto', NULL)
ON CONFLICT (mode_id) DO UPDATE
    SET name = EXCLUDED.name,
        default_weights = EXCLUDED.default_weights;

COMMIT;
