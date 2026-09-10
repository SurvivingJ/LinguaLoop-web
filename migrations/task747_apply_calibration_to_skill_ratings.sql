-- TASK-747 — `apply_calibration_to_skill_ratings`: the ONLY path by which a
-- Calibration measurement may move user_skill_ratings, behind hard guards.
-- =============================================================================
-- PROBLEM
--   Calibration measures ability_zipf (the Zipf at which the learner's
--   known-share crosses 85%, guess floor removed) and publishes it to
--   user_calibration_state. ELO cannot close the gap on its own (ADR-024: the MC
--   chance floor caps its reach at ~191 points), so the measurement must be able
--   to seed and nudge the rating — but process_test_submission already writes
--   the same column at K=32 on every first attempt. An unguarded second writer
--   would fight it, and whichever ran last would win, invisibly.
--
-- FIX (features/vocabulary-aware-test-selection.tech §2.2)
--   One call per completed calibration run, one decision per applicable type.
--   Hard gates, in order; the first to fail skips the type and is audited:
--     G1_no_state    no user_calibration_state row with mode = 'definition'
--                    (or its ability_zipf is NULL — nothing usable to seed from)
--     G2_low_items   items_answered < 20
--     G3_high_se     ability_se > 0.75 Zipf (or NULL: unknown precision)
--     G4_stale       last_run_at older than 90 days
--     G5_in_session  a test_attempts row for this (user, language) < 1 hour old
--     G6_rate_limit  a NON-skipped adjustment for (user, language, type) < 7 days old
--   Then:
--     SEED     tests_taken < 5            → write seed_elo
--     CORRECT  tests_taken >= 5 and |seed_elo − live| > 200
--              → live + sign(diff)·min(0.25·|diff|, 150)
--     else     NO-OP, audited 'within_deadband' (a diff of exactly 200 is inside)
--   Final clamp [875, 1925] — the ladder the seed came from.
--   seed_elo = calibration_zipf_to_elo(ability_zipf) + type_offset, type_offset
--   = 0 for every type in v1 (TASK-750 fits real offsets once there is data).
--
--   Worked examples, pinned in tests/sql/test_task747_rating_writer.sql:
--     pitch accent live 1182, tests_taken 5, seed 1050: diff −132 → no-op.
--     same, seed 900: diff −282 → move min(70.5, 150) → 1111.5 → 1112.
--
-- DECISIONS WORTH KNOWING
--   - mode = 'definition' ONLY. Pronunciation measures reading, not vocabulary;
--     a pronunciation row never stands in for a missing definition row (G1).
--   - Types: the spec's four (reading, listening, dictation, pitch_accent),
--     restricted to those with at least one active test_skill_ratings row in the
--     language — i.e. exactly the types get_recommended_tests can serve there.
--     NOTE (live 2026-09-10): that does NOT exclude pitch_accent for zh/en —
--     zh and en tests carry 34 and 38 pitch_accent rating rows (and en 8 pinyin
--     rows), a backfill artefact outside this task. The writer mirrors what
--     selection can serve rather than hardcoding language ids; if those rows are
--     cleaned up, the writer follows automatically. pinyin (not vocabulary) is
--     deliberately left out, as in the spec.
--   - The clamp is applied after the damped move, as specified; for a live
--     rating below 875 this can move further than the 150 cap. Such a rating can
--     only come from process_test_submission's wider [400, 3000] range.
--   - user_skill_ratings has no unique key on (user, language, type). Like
--     process_test_submission, an UPDATE touches every matching row; a rating
--     row is INSERTed only when none exists (SEED from nothing).
--   - A per-(user, language) transaction advisory lock serialises concurrent
--     calls, so two racing runs cannot both pass G6.
--
-- SECURITY
--   SECURITY DEFINER. p_user_id must equal auth.uid() — the check
--   process_test_submission makes first. Stricter than that function in one
--   respect: its `p_user_id != auth.uid()` is NULL-permissive, so it lets any
--   caller with no JWT subject through. Here a NULL auth.uid() is accepted only
--   for the service_role (the Flask layer, which has already verified the JWT),
--   and anon is refused outright. EXECUTE is revoked from PUBLIC and anon.
--
-- NOT TOUCHED
--   process_test_submission: md5 of pg_get_functiondef identical before and
--   after (b6b8e04eca0d09ef9496c484bf80209c).
--
-- APPLIED LIVE: 2026-09-10 11:52:31 UTC (schema_migrations 20260910115231).
--   Proven by tests/sql/test_task747_rating_writer.sql on live inside a
--   rolled-back transaction: G1 for all 13 real users × 3 languages (156 rows —
--   user_calibration_state has 0 rows, so G1 is the correct live outcome today),
--   G2..G6 each audited, SEED 1250, both worked examples (1182 stays at seed
--   1050; 1182 -> 1112 at seed 900), deadband at exactly 200, the 150 cap, the
--   875 clamp, and refusal of another user's JWT and of anon.
-- =============================================================================

CREATE OR REPLACE FUNCTION public.apply_calibration_to_skill_ratings(
    p_user_id     uuid,
    p_language_id smallint)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path TO 'public'
AS $function$
DECLARE
    c_min_items    constant integer  := 20;
    c_max_se       constant numeric  := 0.75;
    c_stale        constant interval := interval '90 days';
    c_session_gap  constant interval := interval '1 hour';
    c_rate_limit   constant interval := interval '7 days';
    c_seed_below   constant integer  := 5;
    c_deadband     constant integer  := 200;
    c_damp         constant numeric  := 0.25;
    c_cap          constant numeric  := 150;
    c_floor        constant integer  := 875;
    c_ceiling      constant integer  := 1925;

    v_has_state    boolean;
    v_zipf         numeric;
    v_se           numeric;
    v_items        integer;
    v_last_run     timestamptz;
    v_seed         integer;
    v_in_session   boolean;

    v_type         record;
    v_has_usr      boolean;
    v_elo_before   integer;
    v_tests        integer;
    v_diff         integer;
    v_new          integer;
    v_source       text;
    v_reason       text;
    v_decisions    jsonb := '[]'::jsonb;
BEGIN
    IF auth.uid() IS NULL THEN
        IF COALESCE(auth.role(), '') <> 'service_role' THEN
            RAISE EXCEPTION 'Unauthorized: no authenticated user';
        END IF;
    ELSIF p_user_id <> auth.uid() THEN
        RAISE EXCEPTION 'Unauthorized: Cannot adjust ratings for another user';
    END IF;

    PERFORM pg_advisory_xact_lock(
        hashtextextended('apply_calibration_to_skill_ratings:' || p_user_id::text
                         || ':' || p_language_id::text, 0));

    SELECT ucs.ability_zipf, ucs.ability_se, ucs.items_answered, ucs.last_run_at
      INTO v_zipf, v_se, v_items, v_last_run
      FROM user_calibration_state ucs
     WHERE ucs.user_id = p_user_id
       AND ucs.language_id = p_language_id
       AND ucs.mode = 'definition';
    v_has_state := FOUND;

    IF v_has_state AND v_zipf IS NOT NULL THEN
        v_seed := calibration_zipf_to_elo(v_zipf);   -- + type_offset, 0 in v1
    END IF;

    v_in_session := EXISTS (
        SELECT 1 FROM test_attempts ta
         WHERE ta.user_id = p_user_id
           AND ta.language_id = p_language_id
           AND ta.created_at > now() - c_session_gap);

    FOR v_type IN
        SELECT dtt.id, dtt.type_code
          FROM dim_test_types dtt
         WHERE dtt.type_code IN ('reading', 'listening', 'dictation', 'pitch_accent')
           AND dtt.is_active = true
           AND EXISTS (SELECT 1 FROM test_skill_ratings tsr
                         JOIN tests t ON t.id = tsr.test_id
                        WHERE tsr.test_type_id = dtt.id
                          AND t.language_id = p_language_id
                          AND t.is_active = true)
         ORDER BY dtt.id
    LOOP
        SELECT usr.elo_rating, usr.tests_taken
          INTO v_elo_before, v_tests
          FROM user_skill_ratings usr
         WHERE usr.user_id = p_user_id
           AND usr.language_id = p_language_id
           AND usr.test_type_id = v_type.id
         ORDER BY usr.updated_at DESC NULLS LAST
         LIMIT 1;
        v_has_usr := FOUND;
        IF NOT v_has_usr THEN
            v_elo_before := NULL;
            v_tests := 0;
        END IF;

        v_source := 'skipped';
        v_new := v_elo_before;
        v_reason := NULL;

        IF NOT v_has_state OR v_zipf IS NULL THEN
            v_reason := 'G1_no_state';
        ELSIF v_items < c_min_items THEN
            v_reason := 'G2_low_items';
        ELSIF v_se IS NULL OR v_se > c_max_se THEN
            v_reason := 'G3_high_se';
        ELSIF v_last_run < now() - c_stale THEN
            v_reason := 'G4_stale';
        ELSIF v_in_session THEN
            v_reason := 'G5_in_session';
        ELSIF EXISTS (
            SELECT 1 FROM user_skill_rating_adjustments a
             WHERE a.user_id = p_user_id
               AND a.language_id = p_language_id
               AND a.test_type_id = v_type.id
               AND a.source <> 'skipped'
               AND a.created_at > now() - c_rate_limit) THEN
            v_reason := 'G6_rate_limit';
        ELSIF v_tests < c_seed_below THEN
            v_source := 'calibration_seed';
            v_reason := 'seed_tests_taken_lt_5';
            v_new := GREATEST(c_floor, LEAST(c_ceiling, v_seed));
        ELSE
            v_diff := v_seed - v_elo_before;
            IF abs(v_diff) > c_deadband THEN
                v_source := 'calibration_correct';
                v_reason := 'correct_outside_deadband';
                v_new := GREATEST(c_floor, LEAST(c_ceiling,
                            round(v_elo_before
                                  + sign(v_diff) * LEAST(c_damp * abs(v_diff), c_cap))::integer));
            ELSE
                v_reason := 'within_deadband';
            END IF;
        END IF;

        IF v_source <> 'skipped' THEN
            IF v_has_usr THEN
                UPDATE user_skill_ratings
                   SET elo_rating = v_new, updated_at = now()
                 WHERE user_id = p_user_id
                   AND language_id = p_language_id
                   AND test_type_id = v_type.id;
            ELSE
                INSERT INTO user_skill_ratings (user_id, language_id, test_type_id, elo_rating, tests_taken)
                VALUES (p_user_id, p_language_id, v_type.id, v_new, 0);
            END IF;
        END IF;

        INSERT INTO user_skill_rating_adjustments (
            user_id, language_id, test_type_id, source, elo_before, elo_after,
            ability_zipf, ability_se, seed_elo_computed, tests_taken_at_write, reason)
        VALUES (
            p_user_id, p_language_id, v_type.id, v_source, v_elo_before, v_new,
            v_zipf, v_se, v_seed, v_tests, v_reason);

        v_decisions := v_decisions || jsonb_build_object(
            'test_type',   v_type.type_code,
            'source',      v_source,
            'reason',      v_reason,
            'elo_before',  v_elo_before,
            'elo_after',   v_new,
            'seed_elo',    v_seed,
            'tests_taken', v_tests);
    END LOOP;

    RETURN jsonb_build_object(
        'user_id',      p_user_id,
        'language_id',  p_language_id,
        'ability_zipf', v_zipf,
        'ability_se',   v_se,
        'decisions',    v_decisions);
END;
$function$;

COMMENT ON FUNCTION public.apply_calibration_to_skill_ratings(uuid, smallint) IS
  'TASK-747 / ADR-024 §4: the only path by which Calibration moves user_skill_ratings. Reads user_calibration_state mode=definition; gates G1-G6; SEED below 5 tests_taken, else damped CORRECT past a 200 deadband (min(0.25·|diff|,150)); clamp [875,1925]; audits EVERY decision to user_skill_rating_adjustments. Returns {decisions:[...]}.';

REVOKE ALL ON FUNCTION public.apply_calibration_to_skill_ratings(uuid, smallint) FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.apply_calibration_to_skill_ratings(uuid, smallint)
    TO authenticated, service_role;

-- =============================================================================
-- Verification (rollback-only):
--   psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f tests/sql/test_task747_rating_writer.sql
-- =============================================================================
