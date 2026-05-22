-- ============================================================================
-- Phase 13 — Study Plans — build_daily_session (Tier C resolver)
-- Date: 2026-05-21
--
-- Lazy daily resolver. Reads the current week's weekly_plan_states row,
-- computes today_budget from weekday_shape, and solves a small constrained
-- optimization for today's mix: test slots + Practice maint/acq minutes.
--
-- Algorithm: greedy fill by value-per-minute within upper_cap (1.5 ×
-- today_budget per R3.4); local-swap pass omitted in this V1 PL/pgSQL
-- implementation (commented TODO — a Python wrapper layer can post-process
-- the output if telemetry indicates greedy converges suboptimally).
--
-- Outputs (UPSERTs daily_test_loads + populates daily_session_targets jsonb).
--
-- If weekly_plan_states row is missing for the current week (e.g., new user
-- before first Sunday cron tick), returns { "error": "no_weekly_plan", ... }
-- and the caller (get_or_create_daily_load) falls back to legacy
-- _compute_daily_load. If Config.STUDY_PLAN_ENABLED is false at the route
-- layer the caller short-circuits before calling this RPC at all.
--
-- See wiki/algorithms/study-plan-adaptation.tech.md section "Tier C".
-- ============================================================================

BEGIN;

-- ---------------------------------------------------------------------------
-- Helper: test_time_estimate(skill_code text) → minutes
-- Reads dim_test_types.expected_minutes_p50 when populated (≥30 samples),
-- else uses hardcoded seed defaults matching Config.TEST_TYPE_MINUTES.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.test_time_estimate(p_skill text)
RETURNS numeric LANGUAGE sql STABLE AS $$
    SELECT COALESCE(
        (SELECT expected_minutes_p50 FROM public.dim_test_types
         WHERE type_code = p_skill AND expected_minutes_p50 IS NOT NULL),
        CASE p_skill
            WHEN 'reading'       THEN 6.0
            WHEN 'listening'     THEN 5.0
            WHEN 'dictation'     THEN 6.0
            WHEN 'pinyin'        THEN 4.0
            WHEN 'measure_word'  THEN 4.0
            WHEN 'pitch_accent'  THEN 4.0
            ELSE 5.0
        END
    )::numeric
$$;

COMMENT ON FUNCTION public.test_time_estimate IS
    'Returns expected minutes per test of the given skill. Prefers '
    'dim_test_types.expected_minutes_p50 (refreshed nightly from observed '
    'P50s) when set; otherwise falls back to Config.TEST_TYPE_MINUTES seed.';


-- ---------------------------------------------------------------------------
-- Helper: week_start_for(date) → Monday of that week
-- Monday-anchored per the weekly_plan_states CHECK constraint.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.week_start_for(p_date date)
RETURNS date LANGUAGE sql IMMUTABLE AS $$
    SELECT (p_date - ((EXTRACT(ISODOW FROM p_date)::int - 1) || ' days')::interval)::date
$$;


-- ---------------------------------------------------------------------------
-- Main entry point
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.build_daily_session(
    p_user_id     uuid,
    p_language_id smallint,
    p_date        date DEFAULT CURRENT_DATE
) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER
   SET search_path = public, pg_temp AS $$
DECLARE
    v_week_start     date;
    v_state          public.weekly_plan_states%ROWTYPE;
    v_plan           public.user_study_plans%ROWTYPE;
    v_weekday_idx    int;
    v_weekday_w      numeric;
    v_today_budget   numeric;
    v_upper_cap      numeric;
    v_used_min       numeric := 0;
    v_objective      numeric := 0;
    v_skills_today   text[] := ARRAY[]::text[];
    v_test_ids       jsonb := '[]'::jsonb;
    v_maint_min      int := 0;
    v_acq_min        int := 0;
    v_load_id        bigint;
    v_cand           RECORD;
    v_test           RECORD;
    v_spacing_cost   numeric;
    -- coefficients (mirror wiki/algorithms/study-plan-adaptation.tech.md)
    c_alpha_m        constant numeric := 0.02;
    c_alpha_a        constant numeric := 0.02;
    c_gamma          constant numeric := 0.15;
BEGIN
    v_week_start := public.week_start_for(p_date);

    -- ---------------------------------------------------------------
    -- 1. Load plan + weekly state. Bail with error if no plan row.
    -- ---------------------------------------------------------------
    SELECT * INTO v_plan
    FROM public.user_study_plans
    WHERE user_id = p_user_id AND language_id = p_language_id;

    IF NOT FOUND THEN
        RETURN jsonb_build_object(
            'error', 'no_user_study_plan',
            'code',  'E_NOPLAN',
            'hint',  'Call apply_study_plan_template first or fall back to legacy daily-load.'
        );
    END IF;

    SELECT * INTO v_state
    FROM public.weekly_plan_states
    WHERE user_id = p_user_id
      AND language_id = p_language_id
      AND week_start_date = v_week_start;

    IF NOT FOUND THEN
        RETURN jsonb_build_object(
            'error', 'no_weekly_plan',
            'code',  'E_NOWEEK',
            'week_start', v_week_start,
            'hint',  'compute_weekly_plan has not run for this user/week. Caller should retry after Tier B fires.'
        );
    END IF;

    -- ---------------------------------------------------------------
    -- 2. today_budget from weekday shape (ISODOW: Mon=1..Sun=7)
    -- weekday_shape is a 7-element jsonb array indexed [Mon..Sun] (idx 0..6)
    -- ---------------------------------------------------------------
    v_weekday_idx := EXTRACT(ISODOW FROM p_date)::int - 1;  -- 0..6
    v_weekday_w   := COALESCE(
        (v_plan.weekday_shape->>v_weekday_idx)::numeric, 1.0
    );
    v_today_budget := v_state.total_weekly_minutes::numeric * v_weekday_w / 7;
    v_upper_cap    := v_today_budget * 1.5;

    -- ---------------------------------------------------------------
    -- 3. Last 3 days' skills (for spacing penalty)
    --
    -- IMPORTANT SCHEMA NOTE (patched 2026-05-22 during verification):
    -- public.tests has NO test_type_id column — a single test row can be
    -- served as reading/listening/dictation. The skill is captured per
    -- ATTEMPT on test_attempts.test_type_id. Query test_attempts directly
    -- for what the user actually took, which is a better signal than what
    -- was scheduled anyway.
    -- ---------------------------------------------------------------
    DROP TABLE IF EXISTS pg_temp.last3_skills;
    CREATE TEMP TABLE pg_temp.last3_skills (
        skill text NOT NULL
    ) ON COMMIT DROP;

    INSERT INTO pg_temp.last3_skills (skill)
    SELECT dtt.type_code
    FROM public.test_attempts ta
    JOIN public.dim_test_types dtt ON dtt.id = ta.test_type_id
    WHERE ta.user_id = p_user_id
      AND ta.language_id = p_language_id
      AND ta.created_at >= (p_date - 3)::timestamptz
      AND ta.created_at <  (p_date)::timestamptz;

    -- ---------------------------------------------------------------
    -- 4. Build candidate list: test slots + 10-min practice chunks.
    -- Each candidate carries (kind, skill, mins, per_min_value).
    -- ---------------------------------------------------------------
    DROP TABLE IF EXISTS pg_temp.candidates;
    CREATE TEMP TABLE pg_temp.candidates (
        seq            serial,
        kind           text NOT NULL,    -- 'test'|'maint'|'acq'
        skill          text,
        mins           numeric NOT NULL,
        per_min_value  numeric NOT NULL
    ) ON COMMIT DROP;

    -- Test slots: one row per remaining test for each skill.
    -- value(s) sourced from weekly_plan_states.skill_values (Python-computed).
    INSERT INTO pg_temp.candidates (kind, skill, mins, per_min_value)
    SELECT 'test',
           skill_key,
           public.test_time_estimate(skill_key),
           COALESCE((v_state.skill_values->>skill_key)::numeric, 0.10)
             / NULLIF(public.test_time_estimate(skill_key), 0)
    FROM jsonb_each_text(v_state.target_counts) AS tc(skill_key, target_text),
         generate_series(1,
           GREATEST(0,
             target_text::int
             - COALESCE((v_state.completed_counts->>skill_key)::int, 0)
           )
         );

    -- Practice maint chunks (10-min each)
    INSERT INTO pg_temp.candidates (kind, skill, mins, per_min_value)
    SELECT 'maint', NULL, 10, c_alpha_m * v_state.maintenance_share
    FROM generate_series(1,
        GREATEST(0,
            ROUND(v_state.practice_target_minutes::numeric * v_state.maintenance_share)::int
            - v_state.practice_completed_maint_min
        ) / 10
    );

    -- Practice acq chunks (10-min each)
    INSERT INTO pg_temp.candidates (kind, skill, mins, per_min_value)
    SELECT 'acq', NULL, 10, c_alpha_a * v_state.acquisition_share
    FROM generate_series(1,
        GREATEST(0,
            ROUND(v_state.practice_target_minutes::numeric * v_state.acquisition_share)::int
            - v_state.practice_completed_acq_min
        ) / 10
    );

    -- ---------------------------------------------------------------
    -- 5. Greedy fill: highest per_min_value first, applying spacing
    --    penalty once per skill (not once per slot).
    --    TODO (V2 / Python wrapper): local-swap pass that tries
    --    replacing each accepted test slot with a different skill
    --    if value(other) − value(s) > spacing_savings.
    -- ---------------------------------------------------------------
    FOR v_cand IN
        SELECT * FROM pg_temp.candidates
        ORDER BY per_min_value DESC, seq
    LOOP
        EXIT WHEN v_used_min >= v_today_budget;
        CONTINUE WHEN v_used_min + v_cand.mins > v_upper_cap;

        -- Spacing penalty: only on first appearance of a test skill today
        v_spacing_cost := 0;
        IF v_cand.kind = 'test'
           AND NOT (v_cand.skill = ANY(v_skills_today)) THEN
            SELECT c_gamma
                 * COALESCE((SELECT COUNT(*)::numeric FROM pg_temp.last3_skills
                             WHERE skill = v_cand.skill), 0)
                 / 3.0
              INTO v_spacing_cost;

            -- Skip if spacing cost negates the marginal value of this slot
            IF v_spacing_cost > (v_cand.per_min_value * v_cand.mins) THEN
                CONTINUE;
            END IF;
        END IF;

        -- Accept candidate
        IF v_cand.kind = 'test' THEN
            IF NOT (v_cand.skill = ANY(v_skills_today)) THEN
                v_skills_today := array_append(v_skills_today, v_cand.skill);
            END IF;
        ELSIF v_cand.kind = 'maint' THEN
            v_maint_min := v_maint_min + v_cand.mins::int;
        ELSIF v_cand.kind = 'acq' THEN
            v_acq_min   := v_acq_min   + v_cand.mins::int;
        END IF;
        v_used_min  := v_used_min  + v_cand.mins;
        v_objective := v_objective + (v_cand.per_min_value * v_cand.mins)
                                    - v_spacing_cost;
    END LOOP;

    -- ---------------------------------------------------------------
    -- 6. Hydrate test slots: one test per skill slot via
    --    get_recommended_tests, filtered to the skill.
    --    For now, take the top-N recommended of each skill (where N is
    --    the count of times the skill appears in v_skills_today × the
    --    times-per-skill-accepted ratio — approximated by re-counting
    --    candidates accepted per skill).
    -- ---------------------------------------------------------------
    -- Reconstruct per-skill counts from the loop's effects.
    -- Since v_skills_today is just "skills that appear", we need a more
    -- precise count. Re-run a smaller version of the greedy to count.
    DROP TABLE IF EXISTS pg_temp.skill_counts;
    CREATE TEMP TABLE pg_temp.skill_counts (
        skill text PRIMARY KEY,
        count int NOT NULL
    ) ON COMMIT DROP;

    -- Quick recount: greedy is deterministic given stable inputs, so we
    -- replay the accept logic counting per-skill acceptances.
    DECLARE
        v_replay_used numeric := 0;
        v_replay_skills text[] := ARRAY[]::text[];
        v_replay_cost numeric;
    BEGIN
        FOR v_cand IN
            SELECT * FROM pg_temp.candidates
            ORDER BY per_min_value DESC, seq
        LOOP
            EXIT WHEN v_replay_used >= v_today_budget;
            CONTINUE WHEN v_replay_used + v_cand.mins > v_upper_cap;

            v_replay_cost := 0;
            IF v_cand.kind = 'test'
               AND NOT (v_cand.skill = ANY(v_replay_skills)) THEN
                SELECT c_gamma
                     * COALESCE((SELECT COUNT(*)::numeric FROM pg_temp.last3_skills
                                 WHERE skill = v_cand.skill), 0)
                     / 3.0
                  INTO v_replay_cost;
                IF v_replay_cost > (v_cand.per_min_value * v_cand.mins) THEN
                    CONTINUE;
                END IF;
            END IF;

            IF v_cand.kind = 'test' THEN
                IF NOT (v_cand.skill = ANY(v_replay_skills)) THEN
                    v_replay_skills := array_append(v_replay_skills, v_cand.skill);
                END IF;
                INSERT INTO pg_temp.skill_counts (skill, count) VALUES (v_cand.skill, 1)
                ON CONFLICT (skill) DO UPDATE SET count = pg_temp.skill_counts.count + 1;
            END IF;
            v_replay_used := v_replay_used + v_cand.mins;
        END LOOP;
    END;

    -- Now pull top-K ELO-matched tests per skill.
    DROP TABLE IF EXISTS pg_temp.chosen_tests;
    CREATE TEMP TABLE pg_temp.chosen_tests (
        test_id uuid NOT NULL,
        skill   text NOT NULL
    ) ON COMMIT DROP;

    FOR v_test IN
        SELECT sc.skill, sc.count
        FROM pg_temp.skill_counts sc
    LOOP
        INSERT INTO pg_temp.chosen_tests (test_id, skill)
        SELECT rec.test_id, v_test.skill
        FROM public.get_recommended_tests(p_user_id, p_language_id) rec
        WHERE rec.test_type = v_test.skill
        ORDER BY ABS(rec.elo_diff)
        LIMIT v_test.count;
    END LOOP;

    -- Build the test_ids jsonb array (preserves order: per-skill, ELO-best first)
    SELECT COALESCE(jsonb_agg(test_id ORDER BY skill, test_id), '[]'::jsonb)
      INTO v_test_ids
    FROM pg_temp.chosen_tests;

    -- ---------------------------------------------------------------
    -- 7. UPSERT daily_test_loads + daily_test_load_items
    -- ---------------------------------------------------------------
    INSERT INTO public.daily_test_loads (
        user_id, language_id, load_date,
        test_ids, completed_test_ids, daily_session_targets
    ) VALUES (
        p_user_id, p_language_id, p_date,
        v_test_ids, '[]'::jsonb,
        jsonb_build_object(
            'practice_maintenance_min', v_maint_min,
            'practice_acquisition_min', v_acq_min,
            'resolver_solved_at',       NOW(),
            'objective_value',          v_objective,
            'today_budget_minutes',     v_today_budget,
            'used_minutes',             v_used_min
        )
    )
    ON CONFLICT (user_id, language_id, load_date) DO UPDATE
        SET test_ids              = EXCLUDED.test_ids,
            completed_test_ids    = '[]'::jsonb,
            daily_session_targets = EXCLUDED.daily_session_targets
    RETURNING id INTO v_load_id;

    -- Refresh daily_test_load_items: clear then re-insert
    DELETE FROM public.daily_test_load_items WHERE load_id = v_load_id;

    INSERT INTO public.daily_test_load_items (load_id, test_id, is_completed)
    SELECT v_load_id, ct.test_id, false
    FROM pg_temp.chosen_tests ct
    ON CONFLICT (load_id, test_id) DO NOTHING;

    -- ---------------------------------------------------------------
    -- 8. Return the resolved plan
    -- ---------------------------------------------------------------
    RETURN jsonb_build_object(
        'load_id',                v_load_id,
        'load_date',              p_date,
        'week_start',             v_week_start,
        'today_budget_minutes',   v_today_budget,
        'used_minutes',           v_used_min,
        'objective_value',        v_objective,
        'test_ids',               v_test_ids,
        'skills_today',           to_jsonb(v_skills_today),
        'practice_maintenance_min', v_maint_min,
        'practice_acquisition_min', v_acq_min
    );
END $$;

COMMENT ON FUNCTION public.build_daily_session IS
    'Tier C daily resolver. Greedy fill by value-per-minute within 1.5× '
    'today_budget; spacing penalty per skill not per slot. Hydrates test '
    'slots via get_recommended_tests (top-N ELO-matched per skill). UPSERTs '
    'daily_test_loads + daily_test_load_items. Returns error jsonb with '
    'code=E_NOPLAN or E_NOWEEK if prerequisites missing — caller falls back '
    'to legacy _compute_daily_load on either.';

COMMIT;
