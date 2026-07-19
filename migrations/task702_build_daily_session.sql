-- TASK-702 — build_daily_session: surface & reduce hydration shortfalls
-- =============================================================================
-- PROBLEM (F3 shortfall class — three prior prod incidents)
--   The resolver BUDGETS test slots per skill (pg_temp.skill_counts) then
--   HYDRATES each with concrete rows from get_recommended_tests. When the
--   never-attempted pool can't fill a budgeted count, the surplus slots were
--   silently dropped: they never reached test_ids, the /session runner never
--   saw them, and used_minutes over-reported time the learner never actually
--   got scheduled. There was no signal that a slot vanished.
--
-- FIX (this revision) — three coordinated changes:
--   1. SHORTFALL VISIBILITY. Record per-skill requested_counts (budgeted),
--      hydrated_counts (never-attempted / primary fill only) and replay_counts
--      (fallback fill) into the return jsonb AND daily_session_targets jsonb
--      (no schema change). hydrated is primary-pool only ON PURPOSE: replay is a
--      band-aid, so a budgeted slot covered only by replay is STILL a shortfall
--      worth surfacing (the never-attempted pool ran dry). test_service logs a
--      WARNING when hydrated_counts[skill] < requested_counts[skill].
--   2. REPLAY FALLBACK. When the never-attempted pool underfills a skill, top up
--      the remaining budgeted slots from get_replay_tests (nearest-ELO,
--      previously-attempted, not seen in c_replay_min_age_days) stamped
--      slot_type='replay' (ADR-006 reduced-volatility ELO applies downstream).
--      Shared selection code with TASK-704 retry slots.
--   3. USED_MINUTES = HYDRATED. used_minutes now reflects the test slots that
--      were actually placed (new + replay) + practice minutes, not the budgeted
--      slots. today_budget_minutes / objective_value keep their budget meaning;
--      the raw budget-loop total is preserved as budgeted_minutes.
--
--   get_recommended_tests's per-type cap was also raised 3 -> 10
--   (task702_get_recommended_tests_rank_cap.sql) to shrink shortfall frequency
--   before replay is even needed.
--
-- Supersedes phase13_build_daily_session_classifier_drill.sql (archived). The
-- budgeting loop, spacing cost, and practice-minute accounting are unchanged;
-- only the hydration loop, counts bookkeeping, and return/targets shape changed.
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
    v_used_min_hyd   numeric := 0;
    v_objective      numeric := 0;
    v_skills_today   text[] := ARRAY[]::text[];
    v_test_ids       jsonb := '[]'::jsonb;
    v_requested_counts jsonb := '{}'::jsonb;
    v_hydrated_counts  jsonb := '{}'::jsonb;
    v_replay_counts    jsonb := '{}'::jsonb;
    v_maint_min      int := 0;
    v_acq_min        int := 0;
    v_load_id        bigint;
    v_cand           RECORD;
    v_test           RECORD;
    v_spacing_cost   numeric;
    v_hydrated       int;
    c_alpha_m        constant numeric := 0.02;
    c_alpha_a        constant numeric := 0.02;
    c_gamma          constant numeric := 0.15;
    c_replay_min_age_days constant int := 7;   -- TASK-702: replay age floor (N)
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

    -- Per-skill BUDGETED test-slot counts (requested_counts). Re-walks the same
    -- ordered candidate set with the same spacing/cap gates as the budget loop.
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
        test_id   uuid NOT NULL,
        skill     text NOT NULL,
        slot_type text NOT NULL DEFAULT 'new'
    ) ON COMMIT DROP;

    -- ---------------------------------------------------------------
    -- Hydrate test slots (TASK-702).
    --   * classifier_drill  -> per-language sentinel row (no ELO pool).
    --   * every other skill -> never-attempted ELO matches (get_recommended_tests),
    --     then top up any shortfall from get_replay_tests (slot_type='replay').
    -- ---------------------------------------------------------------
    FOR v_test IN
        SELECT sc.skill, sc.count
        FROM pg_temp.skill_counts sc
    LOOP
        IF v_test.skill = 'classifier_drill' THEN
            INSERT INTO pg_temp.chosen_tests (test_id, skill, slot_type)
            SELECT t.id, 'classifier_drill', 'new'
            FROM public.tests t
            WHERE t.language_id = p_language_id
              AND t.slug LIKE '\_\_classifier\_drill\_%'
            ORDER BY t.id
            LIMIT v_test.count;
        ELSE
            INSERT INTO pg_temp.chosen_tests (test_id, skill, slot_type)
            SELECT rec.test_id, v_test.skill, 'new'
            FROM public.get_recommended_tests(p_user_id, p_language_id) rec
            WHERE rec.test_type = v_test.skill
            ORDER BY ABS(rec.elo_diff)
            LIMIT v_test.count;

            GET DIAGNOSTICS v_hydrated = ROW_COUNT;

            -- Exhausted-pool fallback: top up remaining budgeted slots with
            -- nearest-ELO previously-attempted tests (older than the age floor),
            -- excluding anything already chosen today.
            IF v_hydrated < v_test.count THEN
                INSERT INTO pg_temp.chosen_tests (test_id, skill, slot_type)
                SELECT r.test_id, v_test.skill, 'replay'
                FROM public.get_replay_tests(
                         p_user_id,
                         p_language_id,
                         v_test.skill,
                         c_replay_min_age_days,
                         ARRAY(SELECT ct.test_id FROM pg_temp.chosen_tests ct),
                         (v_test.count - v_hydrated)
                     ) r;
            END IF;
        END IF;
    END LOOP;

    -- Shortfall bookkeeping (kept in daily_session_targets jsonb — no schema change).
    SELECT COALESCE(jsonb_object_agg(skill, count), '{}'::jsonb)
      INTO v_requested_counts
    FROM pg_temp.skill_counts;

    -- hydrated_counts = primary (never-attempted / sentinel) fill ONLY, so a
    -- slot covered solely by replay still reads as a shortfall vs requested.
    SELECT COALESCE(jsonb_object_agg(sc.skill, COALESCE(h.n, 0)), '{}'::jsonb)
      INTO v_hydrated_counts
    FROM pg_temp.skill_counts sc
    LEFT JOIN (
        SELECT skill, COUNT(*) AS n
        FROM pg_temp.chosen_tests
        WHERE slot_type = 'new'
        GROUP BY skill
    ) h ON h.skill = sc.skill;

    SELECT COALESCE(jsonb_object_agg(skill, n), '{}'::jsonb)
      INTO v_replay_counts
    FROM (
        SELECT skill, COUNT(*) AS n
        FROM pg_temp.chosen_tests
        WHERE slot_type = 'replay'
        GROUP BY skill
    ) rc;

    -- used_minutes now reflects HYDRATED test slots (new + replay) + practice mins.
    SELECT COALESCE(SUM(public.test_time_estimate(ct.skill)), 0)
      INTO v_used_min_hyd
    FROM pg_temp.chosen_tests ct;
    v_used_min_hyd := v_used_min_hyd + v_maint_min + v_acq_min;

    SELECT COALESCE(
        jsonb_agg(
            jsonb_build_object(
                'test_id',   test_id,
                'test_type', skill,
                'slot_type', slot_type
            )
            ORDER BY skill, slot_type, test_id
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
            'used_minutes',             v_used_min_hyd,
            'budgeted_minutes',         v_used_min,
            'requested_counts',         v_requested_counts,
            'hydrated_counts',          v_hydrated_counts,
            'replay_counts',            v_replay_counts
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
        'used_minutes',           v_used_min_hyd,
        'budgeted_minutes',       v_used_min,
        'objective_value',        v_objective,
        'test_ids',               v_test_ids,
        'skills_today',           to_jsonb(v_skills_today),
        'requested_counts',       v_requested_counts,
        'hydrated_counts',        v_hydrated_counts,
        'replay_counts',          v_replay_counts,
        'practice_maintenance_min', v_maint_min,
        'practice_acquisition_min', v_acq_min
    );
END $function$;
