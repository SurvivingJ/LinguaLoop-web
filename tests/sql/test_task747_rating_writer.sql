-- =============================================================================
-- Pairs with migrations/task746_user_skill_rating_adjustments.sql and
-- migrations/task747_apply_calibration_to_skill_ratings.sql (ADR-024 §4/§5).
-- =============================================================================
-- TASK-747 — the guarded calibration → user_skill_ratings writer. Rollback-only:
-- every synthetic state row, rating row, attempt and audit row is discarded.
--
-- Uses real users with no vocabulary, attempts or ratings (FKs require real
-- users), acting as each via request.jwt.claims, exactly as PostgREST would.
--
-- Pins:
--   * G1..G6 each skip AND leave an audit row naming the gate;
--   * G1 fires for EVERY real user today (user_calibration_state has 0 rows),
--     and a pronunciation-mode row never substitutes for a definition row;
--   * SEED below 5 tests_taken; CORRECT at >= 5 only past a 200 deadband
--     (exactly 200 is a no-op); damped by min(0.25·|diff|, 150); clamp [875,1925];
--   * the worked examples: pitch accent 1182 / tests_taken 5 with seed 1050 is a
--     no-op, and with seed 900 lands on 1112 — never a jump to 900;
--   * the auth re-check refuses another user and anon, admits service_role.
--
--   psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f tests/sql/test_task747_rating_writer.sql
-- =============================================================================

BEGIN;

CREATE TEMP TABLE _t747_log (step text, detail text) ON COMMIT DROP;

DO $test$
DECLARE
    v_lang    smallint := 3;
    c_read    smallint; c_listen smallint; c_dict smallint; c_pitch smallint;
    v_users   uuid[];
    u_g1 uuid; u_gate uuid; u_wx uuid; u_wy uuid; u_band uuid; u_cap uuid; u_other uuid;
    v_res     jsonb;
    v_n_types integer;
    v_cnt     integer;
    v_elo     integer;
    v_test    uuid;
    v_caught  boolean;
    v_real    record;

    -- helpers as inline expressions below
BEGIN
    SELECT id INTO c_read   FROM public.dim_test_types WHERE type_code = 'reading';
    SELECT id INTO c_listen FROM public.dim_test_types WHERE type_code = 'listening';
    SELECT id INTO c_dict   FROM public.dim_test_types WHERE type_code = 'dictation';
    SELECT id INTO c_pitch  FROM public.dim_test_types WHERE type_code = 'pitch_accent';

    SELECT array_agg(q.id ORDER BY q.id) INTO v_users FROM (
        SELECT u.id FROM public.users u
         WHERE NOT EXISTS (SELECT 1 FROM public.user_vocabulary_knowledge k WHERE k.user_id = u.id)
           AND NOT EXISTS (SELECT 1 FROM public.test_attempts a WHERE a.user_id = u.id)
           AND NOT EXISTS (SELECT 1 FROM public.user_skill_ratings s WHERE s.user_id = u.id)
           AND NOT EXISTS (SELECT 1 FROM public.user_calibration_state c WHERE c.user_id = u.id)
         ORDER BY u.id LIMIT 7) q;
    IF coalesce(array_length(v_users, 1), 0) < 7 THEN
        RAISE EXCEPTION 'need 7 clean users, found %', coalesce(array_length(v_users, 1), 0);
    END IF;
    u_g1 := v_users[1]; u_gate := v_users[2]; u_wx := v_users[3]; u_wy := v_users[4];
    u_band := v_users[5]; u_cap := v_users[6]; u_other := v_users[7];

    -- How many types apply to ja (the writer iterates only those with active tests).
    SELECT count(*) INTO v_n_types FROM public.dim_test_types dtt
     WHERE dtt.type_code IN ('reading', 'listening', 'dictation', 'pitch_accent') AND dtt.is_active
       AND EXISTS (SELECT 1 FROM public.test_skill_ratings tsr JOIN public.tests t ON t.id = tsr.test_id
                    WHERE tsr.test_type_id = dtt.id AND t.language_id = v_lang AND t.is_active);
    IF v_n_types <> 4 THEN RAISE EXCEPTION 'expected 4 applicable ja types, found %', v_n_types; END IF;

    -- =========================================================================
    -- G1 for every real user, as the service role (the Flask path).
    -- =========================================================================
    PERFORM set_config('request.jwt.claims', json_build_object('role', 'service_role')::text, true);
    FOR v_real IN SELECT u.id, l.lang::smallint AS lang
                    FROM public.users u CROSS JOIN (VALUES (1), (2), (3)) l(lang)
    LOOP
        v_res := public.apply_calibration_to_skill_ratings(v_real.id, v_real.lang);
        IF EXISTS (SELECT 1 FROM jsonb_array_elements(v_res->'decisions') d
                    WHERE d->>'reason' <> 'G1_no_state' OR d->>'source' <> 'skipped') THEN
            RAISE EXCEPTION 'FAIL: a real user got a non-G1 decision: %', v_res;
        END IF;
    END LOOP;
    SELECT count(*) INTO v_cnt FROM public.user_skill_rating_adjustments WHERE reason = 'G1_no_state';
    INSERT INTO _t747_log VALUES ('G1 sweep', v_cnt || ' G1 audit rows across all real users x 3 languages');

    -- =========================================================================
    -- Pronunciation row alone → still G1; nothing written.
    -- =========================================================================
    INSERT INTO public.user_calibration_state (user_id, language_id, mode, ability_zipf, ability_se, items_answered, sessions_pooled)
    VALUES (u_g1, v_lang, 'pronunciation', 5.0, 0.2, 100, 1);
    PERFORM set_config('request.jwt.claims', json_build_object('sub', u_g1, 'role', 'authenticated')::text, true);
    v_res := public.apply_calibration_to_skill_ratings(u_g1, v_lang);
    IF jsonb_array_length(v_res->'decisions') <> v_n_types
       OR EXISTS (SELECT 1 FROM jsonb_array_elements(v_res->'decisions') d WHERE d->>'reason' <> 'G1_no_state') THEN
        RAISE EXCEPTION 'FAIL G1 (pronunciation-only): %', v_res;
    END IF;
    IF EXISTS (SELECT 1 FROM public.user_skill_ratings WHERE user_id = u_g1) THEN
        RAISE EXCEPTION 'FAIL: a skipped decision wrote a rating';
    END IF;

    -- =========================================================================
    -- G2..G5, then SEED, then G6 — one learner walked through every gate.
    -- =========================================================================
    PERFORM set_config('request.jwt.claims', json_build_object('sub', u_gate, 'role', 'authenticated')::text, true);
    INSERT INTO public.user_calibration_state (user_id, language_id, mode, ability_zipf, ability_se, items_answered, sessions_pooled)
    VALUES (u_gate, v_lang, 'definition', 5.0, 0.2, 10, 1);

    v_res := public.apply_calibration_to_skill_ratings(u_gate, v_lang);
    IF EXISTS (SELECT 1 FROM jsonb_array_elements(v_res->'decisions') d WHERE d->>'reason' <> 'G2_low_items') THEN
        RAISE EXCEPTION 'FAIL G2: %', v_res; END IF;

    UPDATE public.user_calibration_state SET items_answered = 100, ability_se = 0.9 WHERE user_id = u_gate AND mode = 'definition';
    v_res := public.apply_calibration_to_skill_ratings(u_gate, v_lang);
    IF EXISTS (SELECT 1 FROM jsonb_array_elements(v_res->'decisions') d WHERE d->>'reason' <> 'G3_high_se') THEN
        RAISE EXCEPTION 'FAIL G3 (se 0.9): %', v_res; END IF;

    UPDATE public.user_calibration_state SET ability_se = NULL WHERE user_id = u_gate AND mode = 'definition';
    v_res := public.apply_calibration_to_skill_ratings(u_gate, v_lang);
    IF EXISTS (SELECT 1 FROM jsonb_array_elements(v_res->'decisions') d WHERE d->>'reason' <> 'G3_high_se') THEN
        RAISE EXCEPTION 'FAIL G3 (se NULL): %', v_res; END IF;

    UPDATE public.user_calibration_state SET ability_se = 0.2, last_run_at = now() - interval '100 days'
     WHERE user_id = u_gate AND mode = 'definition';
    v_res := public.apply_calibration_to_skill_ratings(u_gate, v_lang);
    IF EXISTS (SELECT 1 FROM jsonb_array_elements(v_res->'decisions') d WHERE d->>'reason' <> 'G4_stale') THEN
        RAISE EXCEPTION 'FAIL G4: %', v_res; END IF;

    UPDATE public.user_calibration_state SET last_run_at = now() WHERE user_id = u_gate AND mode = 'definition';
    SELECT t.id INTO v_test FROM public.tests t WHERE t.language_id = v_lang AND t.is_active LIMIT 1;
    INSERT INTO public.test_attempts (user_id, test_id, test_type_id, language_id, created_at, score, total_questions,
                                      user_elo_before, test_elo_before, user_elo_after, test_elo_after)
    VALUES (u_gate, v_test, c_read, v_lang, now() - interval '10 minutes', 0, 1, 1200, 1200, 1200, 1200);
    v_res := public.apply_calibration_to_skill_ratings(u_gate, v_lang);
    IF EXISTS (SELECT 1 FROM jsonb_array_elements(v_res->'decisions') d WHERE d->>'reason' <> 'G5_in_session') THEN
        RAISE EXCEPTION 'FAIL G5: %', v_res; END IF;
    DELETE FROM public.test_attempts WHERE user_id = u_gate;

    -- SEED: no ratings yet, tests_taken 0 → every type written at 1250.
    v_res := public.apply_calibration_to_skill_ratings(u_gate, v_lang);
    IF EXISTS (SELECT 1 FROM jsonb_array_elements(v_res->'decisions') d
                WHERE d->>'source' <> 'calibration_seed' OR (d->>'elo_after')::int <> 1250) THEN
        RAISE EXCEPTION 'FAIL SEED: %', v_res; END IF;
    SELECT count(*) INTO v_cnt FROM public.user_skill_ratings
     WHERE user_id = u_gate AND language_id = v_lang AND elo_rating = 1250 AND tests_taken = 0;
    IF v_cnt <> v_n_types THEN RAISE EXCEPTION 'FAIL SEED: % rating rows at 1250, want %', v_cnt, v_n_types; END IF;

    -- G6: straight away again → refused for every written type.
    v_res := public.apply_calibration_to_skill_ratings(u_gate, v_lang);
    IF EXISTS (SELECT 1 FROM jsonb_array_elements(v_res->'decisions') d WHERE d->>'reason' <> 'G6_rate_limit') THEN
        RAISE EXCEPTION 'FAIL G6: %', v_res; END IF;

    -- Every call audited every type: 7 calls x 4 types, reasons as walked.
    -- (Excluding G1: the opening sweep also audited this user, in every language.)
    SELECT count(*) INTO v_cnt FROM public.user_skill_rating_adjustments
     WHERE user_id = u_gate AND language_id = v_lang AND reason <> 'G1_no_state';
    IF v_cnt <> 7 * v_n_types THEN RAISE EXCEPTION 'FAIL audit: % rows for the gate walk, want %', v_cnt, 7 * v_n_types; END IF;
    IF EXISTS (SELECT 1 FROM public.user_skill_rating_adjustments
                WHERE user_id = u_gate AND source = 'skipped' AND elo_before IS DISTINCT FROM elo_after) THEN
        RAISE EXCEPTION 'FAIL: a skip row changed the rating'; END IF;
    INSERT INTO _t747_log
    SELECT 'gate walk', string_agg(reason || '×' || n, ', ' ORDER BY min_id)
      FROM (SELECT reason, count(*) n, min(id) min_id FROM public.user_skill_rating_adjustments
             WHERE user_id = u_gate AND language_id = v_lang AND reason <> 'G1_no_state'
             GROUP BY reason) q;

    -- =========================================================================
    -- Worked example 1: pitch accent 1182 / 5 tests, seed 1050 → no-op.
    -- zipf 5.6666667 → 875 + 300·(6.25 − 5.6666667) = 1050.
    -- =========================================================================
    PERFORM set_config('request.jwt.claims', json_build_object('sub', u_wx, 'role', 'authenticated')::text, true);
    INSERT INTO public.user_skill_ratings (user_id, language_id, test_type_id, elo_rating, tests_taken)
    VALUES (u_wx, v_lang, c_pitch, 1182, 5);
    INSERT INTO public.user_calibration_state (user_id, language_id, mode, ability_zipf, ability_se, items_answered, sessions_pooled)
    VALUES (u_wx, v_lang, 'definition', 5.6666667, 0.2, 100, 1);
    v_res := public.apply_calibration_to_skill_ratings(u_wx, v_lang);
    IF NOT EXISTS (SELECT 1 FROM jsonb_array_elements(v_res->'decisions') d
                    WHERE d->>'test_type' = 'pitch_accent' AND d->>'reason' = 'within_deadband'
                      AND (d->>'seed_elo')::int = 1050 AND (d->>'elo_after')::int = 1182) THEN
        RAISE EXCEPTION 'FAIL worked example (seed 1050 must be a no-op): %', v_res; END IF;
    SELECT elo_rating INTO v_elo FROM public.user_skill_ratings WHERE user_id = u_wx AND test_type_id = c_pitch;
    IF v_elo <> 1182 THEN RAISE EXCEPTION 'FAIL: pitch accent moved to %', v_elo; END IF;
    -- A deadband no-op is a skip, so it does not arm G6: a second call is again 'within_deadband'.
    v_res := public.apply_calibration_to_skill_ratings(u_wx, v_lang);
    IF NOT EXISTS (SELECT 1 FROM jsonb_array_elements(v_res->'decisions') d
                    WHERE d->>'test_type' = 'pitch_accent' AND d->>'reason' = 'within_deadband') THEN
        RAISE EXCEPTION 'FAIL: a skipped decision armed the rate limit: %', v_res; END IF;

    -- =========================================================================
    -- Worked example 2: same learner shape, seed 900 → 1112, never 900.
    -- zipf 6.1666667 → 875 + 300·(6.25 − 6.1666667) = 900.
    -- =========================================================================
    PERFORM set_config('request.jwt.claims', json_build_object('sub', u_wy, 'role', 'authenticated')::text, true);
    INSERT INTO public.user_skill_ratings (user_id, language_id, test_type_id, elo_rating, tests_taken)
    VALUES (u_wy, v_lang, c_pitch, 1182, 5);
    INSERT INTO public.user_calibration_state (user_id, language_id, mode, ability_zipf, ability_se, items_answered, sessions_pooled)
    VALUES (u_wy, v_lang, 'definition', 6.1666667, 0.2, 100, 1);
    v_res := public.apply_calibration_to_skill_ratings(u_wy, v_lang);
    SELECT elo_rating INTO v_elo FROM public.user_skill_ratings WHERE user_id = u_wy AND test_type_id = c_pitch;
    IF v_elo <> 1112 THEN RAISE EXCEPTION 'FAIL worked example (seed 900): pitch accent = %, want 1112', v_elo; END IF;
    IF NOT EXISTS (SELECT 1 FROM public.user_skill_rating_adjustments
                    WHERE user_id = u_wy AND test_type_id = c_pitch AND source = 'calibration_correct'
                      AND elo_before = 1182 AND elo_after = 1112 AND seed_elo_computed = 900
                      AND tests_taken_at_write = 5) THEN
        RAISE EXCEPTION 'FAIL: worked-example audit row missing or wrong'; END IF;

    -- =========================================================================
    -- Boundaries at seed 1250 (zipf 5.0).
    --   reading   1450 / 5  → diff −200 exactly → within_deadband
    --   listening 1451 / 5  → diff −201         → 1451 − 50.25 → 1401
    --   dictation 1500 / 4  → tests_taken 4     → SEED → 1250 (undamped)
    -- =========================================================================
    PERFORM set_config('request.jwt.claims', json_build_object('sub', u_band, 'role', 'authenticated')::text, true);
    INSERT INTO public.user_skill_ratings (user_id, language_id, test_type_id, elo_rating, tests_taken) VALUES
        (u_band, v_lang, c_read, 1450, 5), (u_band, v_lang, c_listen, 1451, 5), (u_band, v_lang, c_dict, 1500, 4);
    INSERT INTO public.user_calibration_state (user_id, language_id, mode, ability_zipf, ability_se, items_answered, sessions_pooled)
    VALUES (u_band, v_lang, 'definition', 5.0, 0.2, 100, 1);
    v_res := public.apply_calibration_to_skill_ratings(u_band, v_lang);
    IF (SELECT elo_rating FROM public.user_skill_ratings WHERE user_id = u_band AND test_type_id = c_read) <> 1450
       OR NOT EXISTS (SELECT 1 FROM jsonb_array_elements(v_res->'decisions') d
                       WHERE d->>'test_type' = 'reading' AND d->>'reason' = 'within_deadband') THEN
        RAISE EXCEPTION 'FAIL deadband at exactly 200: %', v_res; END IF;
    IF (SELECT elo_rating FROM public.user_skill_ratings WHERE user_id = u_band AND test_type_id = c_listen) <> 1401 THEN
        RAISE EXCEPTION 'FAIL correct just past the deadband: %', v_res; END IF;
    IF (SELECT elo_rating FROM public.user_skill_ratings WHERE user_id = u_band AND test_type_id = c_dict) <> 1250 THEN
        RAISE EXCEPTION 'FAIL seed at tests_taken 4: %', v_res; END IF;

    -- =========================================================================
    -- Cap and clamp at seed 1250.
    --   reading   1900 / 10 → diff −650 → 162.5 capped at 150 → 1750
    --   listening  700 / 5  → diff +550 → 137.5 → 837.5 → clamped to 875
    --   pitch     2000 / 6  → diff −750 → capped 150 → 1850
    -- =========================================================================
    PERFORM set_config('request.jwt.claims', json_build_object('sub', u_cap, 'role', 'authenticated')::text, true);
    INSERT INTO public.user_skill_ratings (user_id, language_id, test_type_id, elo_rating, tests_taken) VALUES
        (u_cap, v_lang, c_read, 1900, 10), (u_cap, v_lang, c_listen, 700, 5), (u_cap, v_lang, c_pitch, 2000, 6);
    INSERT INTO public.user_calibration_state (user_id, language_id, mode, ability_zipf, ability_se, items_answered, sessions_pooled)
    VALUES (u_cap, v_lang, 'definition', 5.0, 0.2, 100, 1);
    v_res := public.apply_calibration_to_skill_ratings(u_cap, v_lang);
    IF (SELECT elo_rating FROM public.user_skill_ratings WHERE user_id = u_cap AND test_type_id = c_read) <> 1750 THEN
        RAISE EXCEPTION 'FAIL 150 cap (reading): %', v_res; END IF;
    IF (SELECT elo_rating FROM public.user_skill_ratings WHERE user_id = u_cap AND test_type_id = c_listen) <> 875 THEN
        RAISE EXCEPTION 'FAIL clamp at 875 (listening): %', v_res; END IF;
    IF (SELECT elo_rating FROM public.user_skill_ratings WHERE user_id = u_cap AND test_type_id = c_pitch) <> 1850 THEN
        RAISE EXCEPTION 'FAIL 150 cap (pitch): %', v_res; END IF;

    -- =========================================================================
    -- Auth: another user's JWT, and anon, are refused.
    -- =========================================================================
    PERFORM set_config('request.jwt.claims', json_build_object('sub', u_other, 'role', 'authenticated')::text, true);
    v_caught := false;
    BEGIN
        PERFORM public.apply_calibration_to_skill_ratings(u_cap, v_lang);
    EXCEPTION WHEN others THEN v_caught := (SQLERRM LIKE 'Unauthorized%');
    END;
    IF NOT v_caught THEN RAISE EXCEPTION 'FAIL auth: another user was allowed to write'; END IF;

    PERFORM set_config('request.jwt.claims', json_build_object('role', 'anon')::text, true);
    v_caught := false;
    BEGIN
        PERFORM public.apply_calibration_to_skill_ratings(u_cap, v_lang);
    EXCEPTION WHEN others THEN v_caught := (SQLERRM LIKE 'Unauthorized%');
    END;
    IF NOT v_caught THEN RAISE EXCEPTION 'FAIL auth: anon was allowed to write'; END IF;

    INSERT INTO _t747_log VALUES ('result', 'PASS: G1-G6, seed/correct, deadband, cap, clamp, worked examples, auth');
    RAISE NOTICE 'TASK-747 PASS';
END $test$;

SELECT step, detail FROM _t747_log;

ROLLBACK;
