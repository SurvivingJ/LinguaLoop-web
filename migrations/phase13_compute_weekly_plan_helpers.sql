-- ============================================================================
-- Phase 13 — Study Plans — compute_weekly_plan SQL helpers
-- Date: 2026-05-21
--
-- Tier B (compute_weekly_plan) lives in Python (services/study_plan_service.py)
-- because:
--   - Beta sampling with deterministic per-(user, week, skill) seeds is
--     trivial in numpy and awkward in pure pgSQL (no seedable per-call PRNG).
--   - The bandit + water-fill allocator is small Python (≤ 60 lines) but
--     verbose in PL/pgSQL.
--   - pytest + the worked-example in wiki/features/study-plans.tech.md
--     section "Worked Example" gives a clean numerical-equality test surface.
--
-- The two helpers in this file are the SQL surface Python calls:
--
--   compute_weekly_plan_load_signals(user, lang, week_start)
--     → ONE round-trip jsonb carrying every signal the Python adapter needs:
--       per-skill ELO, accuracy, attempt counts (28d), ladder stagnation,
--       FSRS lapse rate, prior week's carry-over.
--
--   compute_weekly_plan_persist(user, lang, week_start, computed jsonb)
--     → atomic UPSERT preserving completed_counts and session_progress_log
--       per R3.8. Returns the upserted row as jsonb.
--
-- See wiki/algorithms/study-plan-adaptation.tech.md.
-- ============================================================================

BEGIN;

-- ---------------------------------------------------------------------------
-- compute_weekly_plan_load_signals
--
-- Loads every input the Python adapter needs in one round-trip. Returned
-- jsonb shape:
-- {
--   "user_id": uuid,
--   "language_id": int,
--   "week_start": date,
--   "user_mean_elo": numeric,
--   "skills": {
--     "reading":   { "elo": int, "first_attempt_correct_28d": int,
--                    "first_attempt_wrong_28d": int },
--     "listening": { ... }, ...
--   },
--   "ladder": { "subscribed": int, "stagnant_14d": int,
--               "active_count": int, "stuck_count": int,
--               "new_intro_7d": int },
--   "fsrs":   { "lapses_28d": int, "reviews_28d": int,
--               "due_7d_lookahead": int },
--   "bkt":    { "known_count_p80": int, "decayed_count": int },
--   "prior_week": { ... weekly_plan_states row from week_start - 7d ... } | null
-- }
--
-- All values are pure aggregates over existing tables; no Python-side
-- queries needed.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.compute_weekly_plan_load_signals(
    p_user_id     uuid,
    p_language_id smallint,
    p_week_start  date
) RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER
   SET search_path = public, pg_temp AS $$
DECLARE
    v_today       date := CURRENT_DATE;
    v_28d_ago     timestamptz := NOW() - INTERVAL '28 days';
    v_14d_ago     timestamptz := NOW() - INTERVAL '14 days';
    v_7d_ago      timestamptz := NOW() - INTERVAL '7 days';
    v_user_mean   numeric;
    v_skills      jsonb;
    v_ladder      jsonb;
    v_fsrs        jsonb;
    v_bkt         jsonb;
    v_prior       jsonb;
BEGIN
    ---------------------------------------------------------------------
    -- Per-skill ELO + recent first-attempt counts.
    -- Each row of user_skill_ratings (per test_type) contributes one
    -- per-skill object keyed by dim_test_types.type_code.
    ---------------------------------------------------------------------
    SELECT AVG(elo_rating) INTO v_user_mean
    FROM public.user_skill_ratings
    WHERE user_id = p_user_id AND language_id = p_language_id;

    SELECT COALESCE(jsonb_object_agg(skill_data.type_code, skill_data.payload), '{}'::jsonb)
    INTO v_skills
    FROM (
        SELECT
            dtt.type_code,
            jsonb_build_object(
                'elo', usr.elo_rating,
                'tests_taken', usr.tests_taken,
                'first_attempt_correct_28d', COALESCE(att.fa_correct, 0),
                'first_attempt_wrong_28d',   COALESCE(att.fa_wrong,   0)
            ) AS payload
        FROM public.user_skill_ratings usr
        JOIN public.dim_test_types dtt ON dtt.id = usr.test_type_id
        LEFT JOIN LATERAL (
            SELECT
                COUNT(*) FILTER (WHERE percentage >= 70) AS fa_correct,
                COUNT(*) FILTER (WHERE percentage <  70) AS fa_wrong
            FROM public.test_attempts ta
            WHERE ta.user_id = p_user_id
              AND ta.language_id = p_language_id
              AND ta.test_type_id = usr.test_type_id
              AND ta.is_first_attempt
              AND ta.created_at >= v_28d_ago
        ) att ON TRUE
        WHERE usr.user_id = p_user_id
          AND usr.language_id = p_language_id
    ) skill_data;

    ---------------------------------------------------------------------
    -- Ladder signals.
    -- subscribed     — any user_word_ladder row.
    -- stagnant_14d   — no family_confidence change in 14d AND no
    --                  consecutive_failures reset (i.e. no recent activity).
    --                  Approximated via last_exercised_at / updated_at.
    -- active_count   — words in active learning states.
    -- stuck_count    — consecutive_failures ≥ 3 OR not advanced 14d.
    -- new_intro_7d   — rows created in last 7 days.
    ---------------------------------------------------------------------
    SELECT jsonb_build_object(
        'subscribed',
            (SELECT COUNT(*) FROM public.user_word_ladder
             WHERE user_id = p_user_id AND language_id = p_language_id),
        'stagnant_14d',
            (SELECT COUNT(*) FROM public.user_word_ladder
             WHERE user_id = p_user_id AND language_id = p_language_id
               AND (last_exercised_at IS NULL OR last_exercised_at < v_14d_ago)),
        'active_count',
            (SELECT COUNT(*) FROM public.user_word_ladder
             WHERE user_id = p_user_id AND language_id = p_language_id
               AND word_state IN ('active','gated','pre_mastery','relearning')),
        'stuck_count',
            (SELECT COUNT(*) FROM public.user_word_ladder
             WHERE user_id = p_user_id AND language_id = p_language_id
               AND (consecutive_failures >= 3
                    OR (last_exercised_at IS NOT NULL
                        AND last_exercised_at < v_14d_ago
                        AND word_state IN ('active','gated','pre_mastery')))),
        'new_intro_7d',
            (SELECT COUNT(*) FROM public.user_word_ladder
             WHERE user_id = p_user_id AND language_id = p_language_id
               AND created_at >= v_7d_ago)
    ) INTO v_ladder;

    ---------------------------------------------------------------------
    -- FSRS signals.
    -- lapses_28d   — sum of lapses on flashcards touched in the window.
    -- reviews_28d  — count of reviews in the window (approx via last_review).
    -- due_7d       — cards with due_date in next 7 days.
    ---------------------------------------------------------------------
    SELECT jsonb_build_object(
        'lapses_28d',
            (SELECT COALESCE(SUM(lapses), 0) FROM public.user_flashcards
             WHERE user_id = p_user_id AND language_id = p_language_id
               AND last_review >= v_28d_ago::date),
        'reviews_28d',
            (SELECT COALESCE(SUM(reps), 0) FROM public.user_flashcards
             WHERE user_id = p_user_id AND language_id = p_language_id
               AND last_review >= v_28d_ago::date),
        'due_7d_lookahead',
            (SELECT COUNT(*) FROM public.user_flashcards
             WHERE user_id = p_user_id AND language_id = p_language_id
               AND due_date <= v_today + 7)
    ) INTO v_fsrs;

    ---------------------------------------------------------------------
    -- BKT signals.
    -- known_count_p80 — senses with p_known ≥ 0.80 (denominator for decay
    --                   pressure).
    -- decayed_count   — senses where effective_p_known < raw - 0.05.
    ---------------------------------------------------------------------
    SELECT jsonb_build_object(
        'known_count_p80',
            (SELECT COUNT(*) FROM public.user_vocabulary_knowledge
             WHERE user_id = p_user_id AND language_id = p_language_id
               AND p_known >= 0.80),
        'decayed_count',
            (SELECT COUNT(*)
             FROM public.user_vocabulary_knowledge uvk
             LEFT JOIN public.user_flashcards fc
                ON fc.user_id = uvk.user_id AND fc.sense_id = uvk.sense_id
             WHERE uvk.user_id = p_user_id
               AND uvk.language_id = p_language_id
               AND public.bkt_effective_p_known(
                     uvk.p_known, uvk.last_evidence_at,
                     fc.stability, uvk.evidence_count
                   ) < uvk.p_known - 0.05)
    ) INTO v_bkt;

    ---------------------------------------------------------------------
    -- Prior week (for carry-over decay).
    ---------------------------------------------------------------------
    SELECT to_jsonb(wps.*) INTO v_prior
    FROM public.weekly_plan_states wps
    WHERE user_id = p_user_id
      AND language_id = p_language_id
      AND week_start_date = p_week_start - 7;

    RETURN jsonb_build_object(
        'user_id',       p_user_id,
        'language_id',   p_language_id,
        'week_start',    p_week_start,
        'user_mean_elo', COALESCE(v_user_mean, 1200),
        'skills',        COALESCE(v_skills, '{}'::jsonb),
        'ladder',        v_ladder,
        'fsrs',          v_fsrs,
        'bkt',           v_bkt,
        'prior_week',    v_prior
    );
END $$;

COMMENT ON FUNCTION public.compute_weekly_plan_load_signals IS
    'Loads every signal the Python Tier B adapter needs in one round-trip. '
    'Returns jsonb keyed by category (skills, ladder, fsrs, bkt, prior_week).';


-- ---------------------------------------------------------------------------
-- compute_weekly_plan_persist
--
-- Atomic UPSERT of Python-computed adapter output. Preserves completed_*
-- and session_progress_log on update (R3.8).
--
-- p_computed jsonb shape (produced by services/study_plan_service.py):
--   {
--     "target_counts":           { "reading": int, ... },
--     "skill_values":            { "reading": numeric, ... },  -- value(s)
--                                                              -- per skill
--                                                              -- (drives
--                                                              -- Tier C
--                                                              -- ranking)
--     "practice_target_minutes": int,
--     "maintenance_share":       numeric,
--     "acquisition_share":       numeric,
--     "total_weekly_minutes":    int
--   }
--
-- Returns the upserted row as jsonb.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.compute_weekly_plan_persist(
    p_user_id     uuid,
    p_language_id smallint,
    p_week_start  date,
    p_computed    jsonb
) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER
   SET search_path = public, pg_temp AS $$
DECLARE
    v_row public.weekly_plan_states%ROWTYPE;
BEGIN
    -- Validate shape
    IF NOT (p_computed ? 'target_counts'
            AND p_computed ? 'skill_values'
            AND p_computed ? 'practice_target_minutes'
            AND p_computed ? 'maintenance_share'
            AND p_computed ? 'acquisition_share'
            AND p_computed ? 'total_weekly_minutes') THEN
        RAISE EXCEPTION 'p_computed missing required keys; got %', p_computed
            USING ERRCODE = 'check_violation';
    END IF;

    INSERT INTO public.weekly_plan_states (
        user_id, language_id, week_start_date,
        target_counts, skill_values, completed_counts,
        practice_target_minutes, practice_completed_maint_min,
        practice_completed_acq_min,
        maintenance_share, acquisition_share,
        total_weekly_minutes, session_progress_log,
        computed_at
    ) VALUES (
        p_user_id, p_language_id, p_week_start,
        p_computed->'target_counts',
        p_computed->'skill_values',
        '{}'::jsonb,                                       -- fresh on insert
        (p_computed->>'practice_target_minutes')::smallint,
        0, 0,
        (p_computed->>'maintenance_share')::numeric,
        (p_computed->>'acquisition_share')::numeric,
        (p_computed->>'total_weekly_minutes')::smallint,
        '{}'::jsonb,                                       -- fresh log on insert
        NOW()
    )
    ON CONFLICT (user_id, language_id, week_start_date) DO UPDATE
        SET target_counts            = EXCLUDED.target_counts,
            skill_values             = EXCLUDED.skill_values,
            practice_target_minutes  = EXCLUDED.practice_target_minutes,
            maintenance_share        = EXCLUDED.maintenance_share,
            acquisition_share        = EXCLUDED.acquisition_share,
            total_weekly_minutes     = EXCLUDED.total_weekly_minutes,
            computed_at              = EXCLUDED.computed_at
            -- completed_counts, practice_completed_*_min,
            -- session_progress_log INTENTIONALLY UNTOUCHED
    RETURNING * INTO v_row;

    RETURN to_jsonb(v_row);
END $$;

COMMENT ON FUNCTION public.compute_weekly_plan_persist IS
    'Atomic UPSERT of Tier B adapter output. Preserves completed_counts, '
    'practice_completed_*_min, and session_progress_log across mid-week '
    'recomputes (R3.8 idempotency contract).';

COMMIT;
