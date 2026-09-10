-- TASK-746 — `user_skill_rating_adjustments`: the audit trail for every
-- calibration-driven rating decision, INCLUDING every skip.
-- =============================================================================
-- PROBLEM
--   TASK-747 adds a second writer of user_skill_ratings.elo_rating next to
--   process_test_submission. ADR-024 §4 separates the two with temporal guards
--   rather than by editing process_test_submission, and §5 requires that every
--   decision the new writer makes — each write, and each refusal with its reason
--   — be recorded. Today no rating write in the system is auditable at all:
--   user_skill_ratings keeps only the current value.
--
-- FIX (features/vocabulary-aware-test-selection.tech §2.3)
--   Append-only table, one row per (user, language, type) decision:
--     source   'calibration_seed' | 'calibration_correct' | 'skipped'
--     reason   the gate code (G1_no_state … G6_rate_limit), 'within_deadband',
--              or for a write 'seed_tests_taken_lt_5' / 'correct_outside_deadband'
--     elo_before / elo_after   equal when skipped (NULL both when the learner had
--              no rating row yet and nothing was written)
--     ability_zipf, ability_se, seed_elo_computed, tests_taken_at_write
--              — the inputs, so any decision can be reproduced from its row
--   It is the source of truth for gate G6 (≤ 1 non-skipped write per
--   (user, language, type) per 7 days), served by the (…, created_at DESC) index.
--
-- SAFETY
--   - Additive. Nothing existing is modified.
--   - Idempotent: IF NOT EXISTS / guarded policy and trigger drops.
--   - Append-only is ENFORCED, not just documented: a trigger refuses UPDATE for
--     every role. DELETE stays possible so the users FK can cascade.
--   - RLS: a learner may SELECT their own rows (the calibration result view shows
--     them); no client INSERT. Rows are written only by the SECURITY DEFINER
--     writer, apply_calibration_to_skill_ratings (TASK-747).
--
-- APPLIED LIVE: 2026-09-10 11:49:16 UTC (schema_migrations 20260910114916).
--   0 rows live; exercised end to end (and rolled back) by
--   tests/sql/test_task747_rating_writer.sql.
-- =============================================================================

CREATE TABLE IF NOT EXISTS public.user_skill_rating_adjustments (
    id                   bigserial   PRIMARY KEY,
    user_id              uuid        NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    language_id          smallint    NOT NULL REFERENCES public.dim_languages(id),
    test_type_id         smallint    NOT NULL REFERENCES public.dim_test_types(id),
    source               text        NOT NULL,
    elo_before           integer,
    elo_after            integer,
    ability_zipf         numeric,
    ability_se           numeric,
    seed_elo_computed    integer,
    tests_taken_at_write integer,
    reason               text        NOT NULL,
    created_at           timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT usra_source_chk
        CHECK (source IN ('calibration_seed', 'calibration_correct', 'skipped')),
    -- A skip changes nothing, by definition.
    CONSTRAINT usra_skip_is_noop
        CHECK (source <> 'skipped' OR elo_before IS NOT DISTINCT FROM elo_after),
    -- A write always lands a value.
    CONSTRAINT usra_write_has_value
        CHECK (source = 'skipped' OR elo_after IS NOT NULL)
);

COMMENT ON TABLE public.user_skill_rating_adjustments IS
  'TASK-746 / ADR-024 §5: append-only audit of every calibration-driven user_skill_ratings decision, including skips and their gate code. Source of truth for gate G6 (7-day rate limit). Written only by apply_calibration_to_skill_ratings.';

CREATE INDEX IF NOT EXISTS idx_usra_user_lang_type_created
    ON public.user_skill_rating_adjustments (user_id, language_id, test_type_id, created_at DESC);

-- Append-only, enforced.
CREATE OR REPLACE FUNCTION public.usra_refuse_update()
RETURNS trigger
LANGUAGE plpgsql
SET search_path TO 'public', 'pg_temp'
AS $function$
BEGIN
    RAISE EXCEPTION 'user_skill_rating_adjustments is append-only (TASK-746)';
END;
$function$;

DROP TRIGGER IF EXISTS usra_append_only ON public.user_skill_rating_adjustments;
CREATE TRIGGER usra_append_only
    BEFORE UPDATE ON public.user_skill_rating_adjustments
    FOR EACH ROW EXECUTE FUNCTION public.usra_refuse_update();

ALTER TABLE public.user_skill_rating_adjustments ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS usra_select_own ON public.user_skill_rating_adjustments;
CREATE POLICY usra_select_own ON public.user_skill_rating_adjustments
    FOR SELECT TO authenticated
    USING (auth.uid() = user_id);

REVOKE ALL ON public.user_skill_rating_adjustments FROM PUBLIC, anon, authenticated;
GRANT SELECT ON public.user_skill_rating_adjustments TO authenticated;
GRANT SELECT, INSERT, DELETE ON public.user_skill_rating_adjustments TO service_role;
GRANT USAGE ON SEQUENCE public.user_skill_rating_adjustments_id_seq TO service_role;

-- =============================================================================
-- Verification
-- =============================================================================
--   SELECT indexdef FROM pg_indexes WHERE tablename = 'user_skill_rating_adjustments';
--   BEGIN; SET LOCAL ROLE authenticated;
--   INSERT INTO user_skill_rating_adjustments (user_id, language_id, test_type_id,
--          source, reason) VALUES (gen_random_uuid(), 3, 2, 'skipped', 'x');
--   -- expect 42501 permission denied
--   ROLLBACK;
-- =============================================================================
