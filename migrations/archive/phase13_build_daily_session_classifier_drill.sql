-- Phase 13 — Study Plans — build_daily_session: hydrate classifier_drill slots
-- =============================================================================
-- PROBLEM
--   Chinese study-plan templates schedule classifier_drill
--   (dim_study_plan_templates.target_counts e.g. {"classifier_drill":1}).
--   build_daily_session correctly BUDGETS the slot (test_time_estimate
--   ('classifier_drill') = 4.0) and counts it into pg_temp.skill_counts, but the
--   hydration step pulls concrete test rows from get_recommended_tests, whose
--   target_types CTE is hardcoded to ('listening','reading','dictation'). It
--   returns ZERO classifier_drill rows, so the budgeted slot is silently dropped
--   and never lands in daily_test_loads.test_ids — the /session runner therefore
--   never sees it (it reaches neither the queue nor the placeholder card).
--
-- FIX
--   classifier_drill is an infinite recall trainer (routes/classifier_drill.py,
--   /classifier-drill), NOT a slug-based comprehension test, so it legitimately
--   has no get_recommended_tests entry. Its ELO/attempt bookkeeping already runs
--   against a per-language SENTINEL test row (process_classifier_drill_submission
--   header: "the route handler supplies the per-language sentinel test_id"),
--   slug '__classifier_drill_<lang>', is_active=false. Hydrate that sentinel
--   directly for the classifier_drill skill. It then flows through the normal
--   path: _enrich_daily_load (no is_active filter) → queue item
--   test_type='classifier_drill' → players/classifier_drill.js → completion via
--   the standard /api/tests/daily-load/complete. Only Chinese has a drill today;
--   for any other language the sentinel lookup returns 0 rows and the budgeted
--   slot drops exactly as before.
--
-- This is otherwise byte-identical to phase13_build_daily_session_test_objs.sql;
-- only the per-skill hydration loop changed (see "CHANGED" marker below).
-- Idempotent: CREATE OR REPLACE.
-- =============================================================================

CREATE OR REPLACE FUNCTION public.build_daily_session(p_user_id uuid, p_language_id smallint, p_date date DEFAULT CURRENT_DATE)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public', 'pg_temp'
AS $function$
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
    c_alpha_m        constant numeric := 0.02;
    c_alpha_a        constant numeric := 0.02;
    c_gamma          constant numeric := 0.15;
BEGIN
    v_week_start := public.week_start_for(p_date);

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

    v_weekday_idx := EXTRACT(ISODOW FROM p_date)::int - 1;
    v_weekday_w   := COALESCE(
        (v_plan.weekday_shape->>v_weekday_idx)::numeric, 1.0
    );
    v_today_budget := v_state.total_weekly_minutes::numeric * v_weekday_w / 7;
    v_upper_cap    := v_today_budget * 1.5;

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

    DROP TABLE IF EXISTS pg_temp.candidates;
    CREATE TEMP TABLE pg_temp.candidates (
        seq            serial,
        kind           text NOT NULL,
        skill          text,
        mins           numeric NOT NULL,
        per_min_value  numeric NOT NULL
    ) ON COMMIT DROP;

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

    INSERT INTO pg_temp.candidates (kind, skill, mins, per_min_value)
    SELECT 'maint', NULL, 10, c_alpha_m * v_state.maintenance_share
    FROM generate_series(1,
        GREATEST(0,
            ROUND(v_state.practice_target_minutes::numeric * v_state.maintenance_share)::int
            - v_state.practice_completed_maint_min
        ) / 10
    );

    INSERT INTO pg_temp.candidates (kind, skill, mins, per_min_value)
    SELECT 'acq', NULL, 10, c_alpha_a * v_state.acquisition_share
    FROM generate_series(1,
        GREATEST(0,
            ROUND(v_state.practice_target_minutes::numeric * v_state.acquisition_share)::int
            - v_state.practice_completed_acq_min
        ) / 10
    );

    FOR v_cand IN
        SELECT * FROM pg_temp.candidates
        ORDER BY per_min_value DESC, seq
    LOOP
        EXIT WHEN v_used_min >= v_today_budget;
        CONTINUE WHEN v_used_min + v_cand.mins > v_upper_cap;

        v_spacing_cost := 0;
        IF v_cand.kind = 'test'
           AND NOT (v_cand.skill = ANY(v_skills_today)) THEN
            SELECT c_gamma
                 * COALESCE((SELECT COUNT(*)::numeric FROM pg_temp.last3_skills
                             WHERE skill = v_cand.skill), 0)
                 / 3.0
              INTO v_spacing_cost;

            IF v_spacing_cost > (v_cand.per_min_value * v_cand.mins) THEN
                CONTINUE;
            END IF;
        END IF;

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

    DROP TABLE IF EXISTS pg_temp.skill_counts;
    CREATE TEMP TABLE pg_temp.skill_counts (
        skill text PRIMARY KEY,
        count int NOT NULL
    ) ON COMMIT DROP;

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

    DROP TABLE IF EXISTS pg_temp.chosen_tests;
    CREATE TEMP TABLE pg_temp.chosen_tests (
        test_id uuid NOT NULL,
        skill   text NOT NULL
    ) ON COMMIT DROP;

    -- ---------------------------------------------------------------
    -- Hydrate test slots. CHANGED (phase13_build_daily_session_classifier_drill):
    -- classifier_drill has no get_recommended_tests entry, so hydrate its
    -- per-language sentinel test row directly; all other skills use the
    -- ELO-matched recommendation path unchanged.
    -- ---------------------------------------------------------------
    FOR v_test IN
        SELECT sc.skill, sc.count
        FROM pg_temp.skill_counts sc
    LOOP
        IF v_test.skill = 'classifier_drill' THEN
            INSERT INTO pg_temp.chosen_tests (test_id, skill)
            SELECT t.id, 'classifier_drill'
            FROM public.tests t
            WHERE t.language_id = p_language_id
              AND t.slug LIKE '\_\_classifier\_drill\_%'
            ORDER BY t.id
            LIMIT 1;
        ELSE
            INSERT INTO pg_temp.chosen_tests (test_id, skill)
            SELECT rec.test_id, v_test.skill
            FROM public.get_recommended_tests(p_user_id, p_language_id) rec
            WHERE rec.test_type = v_test.skill
            ORDER BY ABS(rec.elo_diff)
            LIMIT v_test.count;
        END IF;
    END LOOP;

    SELECT COALESCE(
        jsonb_agg(
            jsonb_build_object(
                'test_id',   test_id,
                'test_type', skill,
                'slot_type', 'new'
            )
            ORDER BY skill, test_id
        ),
        '[]'::jsonb
    )
      INTO v_test_ids
    FROM pg_temp.chosen_tests;

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

    DELETE FROM public.daily_test_load_items WHERE load_id = v_load_id;

    INSERT INTO public.daily_test_load_items (load_id, test_id, is_completed)
    SELECT v_load_id, ct.test_id, false
    FROM pg_temp.chosen_tests ct
    ON CONFLICT (load_id, test_id) DO NOTHING;

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
END $function$;
