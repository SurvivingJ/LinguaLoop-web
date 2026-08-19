-- TASK-702 / TASK-704 / TASK-705 / TASK-710 — build_daily_session: hydration
--   shortfalls, retry slot, same-day re-entrancy, single-pass budgeting
-- =============================================================================
-- TASK-710 (consolidate the duplicated greedy pass, folded into this revision):
--   The resolver previously ran the greedy value-per-minute selection loop TWICE
--   over the identical ordered candidate set: once to compute the budget totals
--   (used_minutes, objective, skills_today) and a second time — with a parallel
--   set of accumulators (v_replay_used / v_replay_skills) — purely to populate
--   pg_temp.skill_counts. The two walks shared the same ORDER BY, the same
--   EXIT/CONTINUE gates and the same spacing formula, so the second could never
--   accept a different set of test candidates than the first; keeping them in
--   lockstep was a standing hazard (any edit had to touch both or totals would
--   diverge from hydration — F12). They are now a SINGLE pass that records each
--   budgeted test slot into skill_counts as it selects. Pure refactor: identical
--   test_ids + targets. Verified old-vs-new equal on a rollback-only live fixture
--   diff across seeded users, and the deployed body confirmed via
--   pg_get_functiondef post-apply (F13).
-- =============================================================================
-- TASK-705 (same-day-safe re-invocation, folded into this revision):
--   A second call for the same (user, language, date) MUST NOT wipe progress.
--   Previously the ON CONFLICT branch reset completed_test_ids to '[]' and the
--   items rebuild reset every slot to is_completed=false, so any re-solve of an
--   already-live day (E_NOWEEK retry, manual regenerate, pacer) erased the
--   learner's completions — only caller-side "row already exists, skip" checks
--   prevented it. Now the resolver, before rebuilding, CARRIES OVER every slot
--   already completed today (test_id in prior completed_test_ids), preserving its
--   slot_type / original_percentage and decrementing its skill's budgeted count
--   so only the still-incomplete slots are re-resolved (retained-completed +
--   fresh == today's budget). The ON CONFLICT branch no longer touches
--   completed_test_ids or completed_blocks, keeping completed_test_ids subset of
--   test_ids. get_recommended / classifier_drill hydration and the retry pick all
--   gained a NOT IN chosen_tests guard so a retained slot is never re-inserted.
--   Verified against the live DB in a rollback-only transaction (2026-07-20): a
--   double-call with one completion + one practice block in between preserves
--   completed_test_ids, completed_blocks, and the items-mirror is_completed, keeps
--   the completed slot exactly once, and re-resolves only the incomplete slot.
--   SQL unit test: tests/sql/test_task705_same_day_safe.sql.
-- =============================================================================
-- TASK-704 (ADR-006 retry slot, folded into this revision):
--   build_daily_session now reserves AT MOST ONE slot per day per language for
--   the learner's worst sub-70% attempt whose latest attempt is older than the
--   24h cooldown, stamped slot_type='retry' with original_percentage. This
--   bypasses the never-attempted filter (get_recommended_tests excludes
--   attempted tests) and displaces one budgeted 'new' slot of the same skill
--   when that skill is budgeted today, so used_minutes stays ~constant. The
--   reduced-volatility ELO on submitting a retry slot is applied downstream by
--   process_test_submission (task704_process_test_submission_retry_elo.sql),
--   which scans daily_test_loads for slot_type='retry'.
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

    -- Per-skill BUDGETED test-slot counts (requested_counts) are recorded in the
    -- SAME greedy pass that computes the budget totals (TASK-710). Created before
    -- the loop so the selection can populate it inline; the TASK-705 carry-over
    -- and TASK-704 retry blocks below still consume a fully-populated table.
    DROP TABLE IF EXISTS pg_temp.skill_counts;
    CREATE TEMP TABLE pg_temp.skill_counts (
        skill text PRIMARY KEY,
        count int NOT NULL
    ) ON COMMIT DROP;

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
            -- Record the budgeted slot for this skill in-pass (formerly a second,
            -- byte-identical loop over the same candidate order — F12).
            INSERT INTO pg_temp.skill_counts (skill, count) VALUES (v_cand.skill, 1)
            ON CONFLICT (skill) DO UPDATE SET count = pg_temp.skill_counts.count + 1;
        ELSIF v_cand.kind = 'maint' THEN
            v_maint_min := v_maint_min + v_cand.mins::int;
        ELSIF v_cand.kind = 'acq' THEN
            v_acq_min   := v_acq_min   + v_cand.mins::int;
        END IF;
        v_used_min  := v_used_min  + v_cand.mins;
        v_objective := v_objective + (v_cand.per_min_value * v_cand.mins)
                                    - v_spacing_cost;
    END LOOP;

    DROP TABLE IF EXISTS pg_temp.chosen_tests;
    CREATE TEMP TABLE pg_temp.chosen_tests (
        test_id             uuid NOT NULL,
        skill               text NOT NULL,
        slot_type           text NOT NULL DEFAULT 'new',
        original_percentage numeric,         -- populated for slot_type='retry' only
        is_completed        boolean NOT NULL DEFAULT false  -- TASK-705: retained same-day completion
    ) ON COMMIT DROP;

    -- ---------------------------------------------------------------
    -- TASK-705 — same-day re-entrancy. Before rebuilding today's plan, carry
    -- over every slot the learner already COMPLETED today: any element of the
    -- prior row's test_ids whose test_id is present in the prior completed_test_ids.
    -- Each is re-inserted into chosen_tests with its ORIGINAL slot_type /
    -- original_percentage and is_completed=true, and its skill's budgeted count is
    -- decremented so only the still-incomplete slots get re-resolved below
    -- (retained-completed + fresh == today's budget, so used_minutes stays sane).
    -- Seeding these first also excludes them from retry/replay selection (both
    -- guard against chosen_tests) and preserves the completed_test_ids subset test_ids
    -- invariant, since the ON CONFLICT branch keeps completed_test_ids as-is.
    -- No-op on the first call of the day (no prior row -> NULL).
    -- ---------------------------------------------------------------
    DECLARE
        v_prior_test_ids  jsonb;
        v_prior_completed jsonb;
    BEGIN
        SELECT dtl.test_ids, dtl.completed_test_ids
          INTO v_prior_test_ids, v_prior_completed
        FROM public.daily_test_loads dtl
        WHERE dtl.user_id = p_user_id
          AND dtl.language_id = p_language_id
          AND dtl.load_date = p_date;

        IF v_prior_completed IS NOT NULL
           AND jsonb_typeof(v_prior_completed) = 'array'
           AND jsonb_array_length(v_prior_completed) > 0 THEN

            INSERT INTO pg_temp.chosen_tests (test_id, skill, slot_type, original_percentage, is_completed)
            SELECT (elem->>'test_id')::uuid,
                   COALESCE(elem->>'test_type', 'listening'),
                   COALESCE(elem->>'slot_type', 'new'),
                   NULLIF(elem->>'original_percentage', '')::numeric,
                   true
            FROM jsonb_array_elements(COALESCE(v_prior_test_ids, '[]'::jsonb)) AS elem
            WHERE jsonb_typeof(elem) = 'object'
              AND elem ? 'test_id'
              AND v_prior_completed ? (elem->>'test_id');

            -- Free one budgeted 'new' slot per retained completed slot of its skill
            -- (when that skill is budgeted today), keeping the day at ~budget.
            UPDATE pg_temp.skill_counts sc
               SET count = sc.count - retained.n
            FROM (
                SELECT skill, COUNT(*) AS n
                FROM pg_temp.chosen_tests
                WHERE is_completed
                GROUP BY skill
            ) retained
            WHERE retained.skill = sc.skill;
            DELETE FROM pg_temp.skill_counts WHERE count <= 0;
        END IF;
    END;

    -- ---------------------------------------------------------------
    -- TASK-704 / ADR-006 retry slot. Reserve AT MOST ONE slot for the worst
    -- sub-70% latest attempt older than the 24h cooldown. Runs BEFORE hydration
    -- so decrementing skill_counts frees one budgeted 'new' slot of the retry's
    -- skill (when that skill is budgeted today), keeping used_minutes ~constant.
    -- Additive (+1 over budget) only when the skill isn't budgeted today.
    -- Reduced-volatility ELO on submission is applied downstream by
    -- process_test_submission scanning slot_type='retry'.
    -- ---------------------------------------------------------------
    DECLARE
        c_poor_threshold  constant numeric := 70;   -- Config.POOR_PERFORMANCE_THRESHOLD
        v_retry_test_id   uuid;
        v_retry_skill     text;
        v_retry_pct       numeric;
    BEGIN
        SELECT latest.test_id, dtt.type_code, latest.percentage
          INTO v_retry_test_id, v_retry_skill, v_retry_pct
        FROM (
            SELECT DISTINCT ON (ta.test_id)
                   ta.test_id, ta.test_type_id, ta.percentage, ta.created_at
            FROM public.test_attempts ta
            WHERE ta.user_id = p_user_id
              AND ta.language_id = p_language_id
            ORDER BY ta.test_id, ta.created_at DESC
        ) latest
        JOIN public.dim_test_types dtt ON dtt.id = latest.test_type_id
        WHERE latest.percentage IS NOT NULL
          AND latest.percentage < c_poor_threshold
          AND latest.created_at < (NOW() - INTERVAL '24 hours')   -- cooldown
          AND latest.test_id NOT IN (SELECT ct.test_id FROM pg_temp.chosen_tests ct)  -- TASK-705
        ORDER BY latest.percentage ASC, latest.created_at ASC     -- worst first
        LIMIT 1;

        IF v_retry_test_id IS NOT NULL THEN
            -- Free one budgeted 'new' slot of this skill if it is budgeted today.
            UPDATE pg_temp.skill_counts
               SET count = count - 1
             WHERE skill = v_retry_skill AND count > 0;
            DELETE FROM pg_temp.skill_counts WHERE count <= 0;

            INSERT INTO pg_temp.chosen_tests (test_id, skill, slot_type, original_percentage)
            VALUES (v_retry_test_id, v_retry_skill, 'retry', ROUND(v_retry_pct, 1));
        END IF;
    END;

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
              AND t.id NOT IN (SELECT ct.test_id FROM pg_temp.chosen_tests ct)  -- TASK-705: no dup w/ retained
            ORDER BY t.id
            LIMIT v_test.count;
        ELSE
            INSERT INTO pg_temp.chosen_tests (test_id, skill, slot_type)
            SELECT rec.test_id, v_test.skill, 'new'
            FROM public.get_recommended_tests(p_user_id, p_language_id) rec
            WHERE rec.test_type = v_test.skill
              AND rec.test_id NOT IN (SELECT ct.test_id FROM pg_temp.chosen_tests ct)  -- TASK-705: no dup w/ retained/retry
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
    -- NOT is_completed: retained same-day completions (TASK-705) are carried over,
    -- not freshly hydrated, so they must not mask (or inflate) this call's fill.
    SELECT COALESCE(jsonb_object_agg(sc.skill, COALESCE(h.n, 0)), '{}'::jsonb)
      INTO v_hydrated_counts
    FROM pg_temp.skill_counts sc
    LEFT JOIN (
        SELECT skill, COUNT(*) AS n
        FROM pg_temp.chosen_tests
        WHERE slot_type = 'new' AND NOT is_completed
        GROUP BY skill
    ) h ON h.skill = sc.skill;

    SELECT COALESCE(jsonb_object_agg(skill, n), '{}'::jsonb)
      INTO v_replay_counts
    FROM (
        SELECT skill, COUNT(*) AS n
        FROM pg_temp.chosen_tests
        WHERE slot_type = 'replay' AND NOT is_completed
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
            || CASE WHEN original_percentage IS NOT NULL
                    THEN jsonb_build_object('original_percentage', original_percentage)
                    ELSE '{}'::jsonb END
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
        -- TASK-705: do NOT reset completed_test_ids / completed_blocks on a same-day
        -- re-solve. Every completed slot is retained in EXCLUDED.test_ids above, so
        -- the prior completed_test_ids stays a subset of the rebuilt test_ids.
        SET test_ids              = EXCLUDED.test_ids,
            daily_session_targets = EXCLUDED.daily_session_targets
    RETURNING id INTO v_load_id;

    DELETE FROM public.daily_test_load_items WHERE load_id = v_load_id;

    -- Mirror per-slot completion so the items table matches completed_test_ids
    -- after a same-day rebuild (TASK-705).
    INSERT INTO public.daily_test_load_items (load_id, test_id, is_completed)
    SELECT v_load_id, ct.test_id, ct.is_completed
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
