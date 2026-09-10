-- TASK-744 — `selection_tuning`: operator-tunable constants for test selection.
-- =============================================================================
-- PROBLEM
--   TASK-748 adds a vocabulary coverage term to get_recommended_tests. Its
--   constants (the term's weight, the target unknown-word rate, the tolerance,
--   the tier-ceiling offset) are judgement calls that will be retuned as BKT and
--   dictionary coverage improve, and the feature must ship INERT and be switched
--   on only after a 7-day shadow window. Hardcoding them means a migration per
--   retune and no instant rollback.
--
--   A defaulted `p_vocab_weight` parameter was rejected: it creates the ambiguous
--   overload PostgREST resolves unpredictably, which
--   migrations/get_recommended_tests_drop_ambiguous_overload.sql already had to
--   clean up once.
--
-- FIX
--   A one-row-per-key numeric settings table, read inside the function.
--   Seeds (features/vocabulary-aware-test-selection.tech §3.5):
--     vocab_weight        0     -- INERT on arrival. Rollback = set back to 0.
--     elo_weight          1.0
--     unknown_target      0.15  -- u*; 3-7% is unreachable on live content
--     unknown_tolerance   0.10  -- u_tol; divides, so CHECKed > 0
--     tier_ceiling_offset 2     -- the §4 safety rail, in tiers
--
-- SAFETY
--   - Additive: one table, one trigger function. Nothing existing is modified.
--   - Idempotent: CREATE TABLE IF NOT EXISTS; seeds are ON CONFLICT DO NOTHING,
--     so re-running NEVER resets a value an operator has changed.
--   - Operator-writable only. RLS on with no policy, and anon/authenticated have
--     every privilege revoked: a learner must not tune their own recommender.
--     get_recommended_tests is SECURITY DEFINER and reads it as the owner.
--   - A missing key must read as the inert default (the function COALESCEs
--     vocab_weight to 0), so deleting a row cannot switch the feature ON.
--
-- APPLIED LIVE: 2026-09-10 11:34:48 UTC (schema_migrations 20260910113448), and
--   again at 11:38:01 UTC (20260910113801, `..._rerun_idempotency`) to prove
--   idempotency: every row's updated_at stayed at 11:34:48 after the re-run, and
--   inside a rolled-back transaction an operator-set elo_weight = 0.42 survived
--   a re-run of the seed INSERT. UPDATE and SELECT as `authenticated` are both
--   refused (42501 permission denied for table selection_tuning).
-- =============================================================================

CREATE TABLE IF NOT EXISTS public.selection_tuning (
    key        text        PRIMARY KEY,
    value      numeric     NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT now(),
    -- The two values whose wrong setting breaks the function rather than just
    -- tuning it: a zero tolerance divides by zero, and a negative weight would
    -- REWARD distance from the target.
    CONSTRAINT selection_tuning_tolerance_positive
        CHECK (key <> 'unknown_tolerance' OR value > 0),
    CONSTRAINT selection_tuning_weights_nonnegative
        CHECK (key NOT IN ('vocab_weight', 'elo_weight') OR value >= 0)
);

COMMENT ON TABLE public.selection_tuning IS
  'Operator-tunable constants for get_recommended_tests (TASK-744/748, ADR-024). vocab_weight = 0 reproduces the pre-TASK-748 ranking exactly and is the rollback switch. Not writable by learners.';

INSERT INTO public.selection_tuning (key, value) VALUES
    ('vocab_weight',        0),
    ('elo_weight',          1.0),
    ('unknown_target',      0.15),
    ('unknown_tolerance',   0.10),
    ('tier_ceiling_offset', 2)
ON CONFLICT (key) DO NOTHING;

-- updated_at tells an operator when a knob last moved; keep it truthful.
CREATE OR REPLACE FUNCTION public.selection_tuning_touch()
RETURNS trigger
LANGUAGE plpgsql
SET search_path TO 'public', 'pg_temp'
AS $function$
BEGIN
    NEW.updated_at := now();
    RETURN NEW;
END;
$function$;

DROP TRIGGER IF EXISTS selection_tuning_touch ON public.selection_tuning;
CREATE TRIGGER selection_tuning_touch
    BEFORE UPDATE ON public.selection_tuning
    FOR EACH ROW EXECUTE FUNCTION public.selection_tuning_touch();

ALTER TABLE public.selection_tuning ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.selection_tuning FROM PUBLIC, anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.selection_tuning TO service_role;

-- =============================================================================
-- Verification
-- =============================================================================
--   SELECT key, value FROM selection_tuning ORDER BY key;
--   -- elo_weight 1.0 | tier_ceiling_offset 2 | unknown_target 0.15 |
--   -- unknown_tolerance 0.10 | vocab_weight 0
--
--   BEGIN; SET LOCAL ROLE authenticated;
--   UPDATE selection_tuning SET value = 1 WHERE key = 'vocab_weight';
--   -- expect: ERROR 42501 permission denied for table selection_tuning
--   ROLLBACK;
--
-- Turn the vocabulary term on (operator decision, after the shadow window):
--   UPDATE selection_tuning SET value = 1 WHERE key = 'vocab_weight';
-- Roll back:
--   UPDATE selection_tuning SET value = 0 WHERE key = 'vocab_weight';
-- =============================================================================
