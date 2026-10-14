-- session_module_exclusions_build_daily_session.sql — build_daily_session (Tier C)
-- =============================================================================
-- TASK-865 (session-modules) as amended 2026-10-13 by session-budget-settings (Migration 2).
-- Specs: wiki/features/session-modules.tech.md (edits 1-9, tagged `-- session-modules`),
--        wiki/features/session-budget-settings.tech.md (Migration 2, tagged `-- session-budget`),
--        wiki/decisions/ADR-032-session-module-exclusion.md,
--        wiki/decisions/ADR-033-budget-scope-and-new-word-budget.md.
--
-- SUPERSEDES the public.build_daily_session(uuid, smallint, date) body in
-- migrations/word_upload_slot_scheduling.sql (canonical until now; verified by grepping
-- migrations/ excluding archive/ — phase13_build_daily_session.sql holds only the older
-- phase-13 definition). word_upload_slot_scheduling.sql is NOT archived: it is still the
-- only repo record of user_word_watchlist.last_matched_surfaced_at and its index.
-- This body is word_upload_slot_scheduling.sql's function carried forward verbatim plus:
--   session-modules: exclusion filters (<> ALL(v_excluded)) on the TASK-732 test-minutes sum,
--     the test/surface candidate INSERT, the TASK-704 retry SELECT and the word_upload SELECT;
--     'excluded_modules' echoed into daily_session_targets. TASK-705 carry-over is unchanged.
--   session-budget: ONE in-budget pool. The practice share (TASK-732 split) exists only when
--     budget_scope = 'tests_and_review' AND 'practice' not excluded; it is filled DIRECTLY:
--     due reviews first (min(share, due minutes)), then whole new words from the governed
--     quota, and unused minutes RETURN to the test budget. The practice candidate INSERTs,
--     the practice greedy loop and any extra pool do not exist. The optional tail is derived
--     live by the session route, not here.
--   New daily_session_targets keys: excluded_modules, budget_scope, new_words_quota,
--     new_words_effective, new_words_in_budget, new_words_shortfall, new_words_supply_checked, new_words_supply_checked_e,
--     governor_level, review_due_minutes, review_main_minutes, new_word_main_minutes,
--     returned_to_tests_minutes. The same keys are added to the return value.
--
-- Also defines set_new_words_shortfall(uuid, smallint, date, int) (service role only).
--
-- APPLY ORDER: session_module_exclusions.sql and review_governor.sql FIRST (this function
-- calls new_words_for_day, new_word_minutes, review_governor_state, new_words_effective,
-- ladder_new_word_state and reads user_study_plans.excluded_modules / budget_scope /
-- new_words_per_day and weekly_plan_states.budget_scope).
-- ALSO REQUIRED FIRST (checked against the live DB 2026-10-13): this body keeps the
-- word_upload slot block of word_upload_slot_scheduling.sql, which reads and updates
-- public.user_word_watchlist. That table (migrations/user_word_watchlist_schema.sql) and the
-- watchlist column/index from migrations/word_upload_slot_scheduling.sql were NOT yet applied
-- live, and the live build_daily_session has no word_upload block. Apply those two files
-- before this one, or build_daily_session fails at runtime with "relation
-- user_word_watchlist does not exist".
-- Idempotent: CREATE OR REPLACE.
-- =============================================================================

-- Records the final unmet new-word count after ladder intake's supply check and marks the
-- day as supply-checked so the next same-day rebuild plans only servable words.
-- Review fix: also stores the effective quota E the check was made under
-- (new_words_supply_checked_e). A same-day quota change (settings edit, governor level
-- change) makes the stored shortfall stale; build_daily_session and the intake service
-- ignore a supply check whose E differs from the current E. The pre-fix 4-arg overload is
-- dropped so PostgREST has no ambiguous overload (p_checked_e defaults to NULL = unknown E).
DROP FUNCTION IF EXISTS public.set_new_words_shortfall(uuid, smallint, date, int);
CREATE OR REPLACE FUNCTION public.set_new_words_shortfall(
    p_user_id uuid, p_language_id smallint, p_date date, p_shortfall int,
    p_checked_e int DEFAULT NULL
) RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER
  SET search_path TO 'public','pg_temp' AS $$
BEGIN
    UPDATE public.daily_test_loads
       SET daily_session_targets =
             jsonb_set(
               jsonb_set(
                 jsonb_set(COALESCE(daily_session_targets, '{}'::jsonb),
                           '{new_words_shortfall}', to_jsonb(GREATEST(0, COALESCE(p_shortfall, 0)))),
                 '{new_words_supply_checked}', 'true'::jsonb),
               '{new_words_supply_checked_e}', COALESCE(to_jsonb(p_checked_e), 'null'::jsonb))
     WHERE user_id = p_user_id AND language_id = p_language_id AND load_date = p_date;
    RETURN FOUND;
END $$;
REVOKE EXECUTE ON FUNCTION public.set_new_words_shortfall(uuid, smallint, date, int, int)
    FROM PUBLIC, anon, authenticated;   -- service-role (backend) only
GRANT EXECUTE ON FUNCTION public.set_new_words_shortfall(uuid, smallint, date, int, int) TO service_role;

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
    -- TASK-732: today's budget split by side, replacing the single
    -- v_today_budget/v_upper_cap pair the combined loop used to share.
    v_test_minutes_total     numeric;
    v_practice_minutes_total numeric;
    v_test_budget            numeric;
    v_practice_budget        numeric;
    v_upper_cap_test         numeric;
    v_upper_cap_practice     numeric;
    v_used_min_test          numeric := 0;
    v_used_min_practice      numeric := 0;
    v_used_min       numeric := 0;
    v_used_min_hyd   numeric := 0;
    v_objective      numeric := 0;
    v_skills_today   text[] := ARRAY[]::text[];
    v_test_ids       jsonb := '[]'::jsonb;
    v_requested_counts jsonb := '{}'::jsonb;
    v_hydrated_counts  jsonb := '{}'::jsonb;
    v_replay_counts    jsonb := '{}'::jsonb;
    v_surface_counts   jsonb := '{}'::jsonb;
    v_maint_min      int := 0;
    v_acq_min        int := 0;
    v_load_id        bigint;
    v_cand           RECORD;
    v_test           RECORD;
    v_spacing_cost   numeric;
    v_hydrated       int;
    v_dict_difficulty int;
    c_alpha_m        constant numeric := 0.02;
    c_alpha_a        constant numeric := 0.02;
    c_gamma          constant numeric := 0.15;
    c_replay_min_age_days constant int := 7;   -- TASK-702: replay age floor (N)
    -- TASK-714 / ADR-021. Plannable but NOT dim_test_types rows and never
    -- resolvable to an ELO-rated `tests` row. Adding a code here without also
    -- seeding test_time_estimate budgets it at the silent ELSE 5.0.
    c_surface_skills constant text[] := ARRAY['flashcards','dual_translation'];
    -- TASK-714: cards per 'flashcards' slot. Mirrors
    -- routes/study_session.py::_FLASHCARD_CARDS_PER_BLOCK and the 7.0-minute
    -- seed in test_time_estimate — change one, change all three.
    c_cards_per_block constant int := 15;
    -- session-modules (TASK-865)
    v_excluded       text[];
    -- session-budget (TASK-865 / ADR-033)
    v_scope          text;
    v_practice_in    boolean;
    v_npd            int;
    v_quota          int;
    v_new_eff        int;
    v_mpnw           numeric;
    v_gov            jsonb;
    v_level          text;
    v_due_min        numeric := 0;
    v_r_main         numeric := 0;
    v_s_words        int := 0;
    v_a_main         numeric := 0;
    v_returned       numeric := 0;
    v_local_midnight timestamptz;
    v_lw             jsonb;
    v_unstarted      int := 0;
    v_started_today  int := 0;
    v_shortfall      int := 0;
    v_prior_shortfall int := 0;
    v_prior_checked  boolean := false;
    v_prior_checked_e int;
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

    -- session-modules: excluded modules (never NULL).
    v_excluded := COALESCE(v_plan.excluded_modules, '{}'::text[]);

    -- session-budget: scope comes from the state row (consistent with its own totals); the
    -- new-word quota comes live from the plan so a stale state never hides a setting.
    v_scope       := COALESCE(v_state.budget_scope, 'tests_and_review');
    v_practice_in := (v_scope = 'tests_and_review' AND NOT ('practice' = ANY(v_excluded)));
    v_npd         := COALESCE(v_plan.new_words_per_day, 0);
    v_quota       := public.new_words_for_day(v_npd, v_weekday_w);                 -- Q
    v_mpnw        := public.new_word_minutes(p_language_id);
    v_gov         := public.review_governor_state(p_user_id, p_language_id, p_date);
    v_level       := CASE WHEN 'practice' = ANY(v_excluded) THEN 'normal'
                          ELSE COALESCE(v_gov->>'level', 'normal') END;
    v_new_eff     := public.new_words_effective(v_quota, v_level);                 -- E
    v_due_min     := CASE WHEN 'practice' = ANY(v_excluded) THEN 0
                          ELSE COALESCE((v_gov->>'due_minutes')::numeric, 0) END;

    -- session-budget: prior supply check (same-day rebuild only). Ladder intake writes
    -- new_words_supply_checked = true and the unmet new_words_shortfall through
    -- set_new_words_shortfall; read them BEFORE the row is replaced below. An unchecked
    -- prior row contributes 0.
    SELECT COALESCE((dtl.daily_session_targets->>'new_words_supply_checked')::boolean, false),
           COALESCE((dtl.daily_session_targets->>'new_words_shortfall')::int, 0),
           NULLIF(dtl.daily_session_targets->>'new_words_supply_checked_e', '')::int
      INTO v_prior_checked, v_prior_shortfall, v_prior_checked_e
      FROM public.daily_test_loads dtl
     WHERE dtl.user_id = p_user_id
       AND dtl.language_id = p_language_id
       AND dtl.load_date = p_date;
    IF NOT FOUND OR NOT COALESCE(v_prior_checked, false) THEN
        v_prior_checked   := false;
        v_prior_shortfall := 0;
    END IF;
    -- Review fix: a supply check is valid only for the E it was made under. A mid-day quota
    -- change leaves the stored shortfall stale, so drop it (NULL E = row written before the
    -- key existed: trusted).
    IF v_prior_checked AND v_prior_checked_e IS NOT NULL AND v_prior_checked_e <> v_new_eff THEN
        v_prior_checked   := false;
        v_prior_shortfall := 0;
        v_prior_checked_e := NULL;
    END IF;

    -- TASK-715: the learner's EXPECTED dictation difficulty — the tier whose
    -- seeded initial_elo sits closest to their current dictation ELO. Used to
    -- size dictation slots during BUDGETING, before any concrete test is
    -- known. Defaults to the 1200-ELO tier for an unrated learner.
    SELECT ct.difficulty_max INTO v_dict_difficulty
    FROM public.dim_complexity_tiers ct
    ORDER BY ABS(
        ct.initial_elo - COALESCE(
            (SELECT usr.elo_rating
             FROM public.user_skill_ratings usr
             JOIN public.dim_test_types dtt ON dtt.id = usr.test_type_id
             WHERE usr.user_id = p_user_id
               AND usr.language_id = p_language_id
               AND dtt.type_code = 'dictation'),
            1200
        )
    )
    LIMIT 1;

    -- TASK-732: size each side's "this week still wants X minutes" total
    -- independently of the (unreconciled) weekly_ceiling clamp upstream, then
    -- split today's budget proportionally. v_test_minutes_total mirrors
    -- services/study_plan_service.py's own test_minutes sum (same skills,
    -- same test_time_estimate) so the ratio reflects the real, current
    -- target_counts rather than a stale weekly snapshot.
    SELECT COALESCE(SUM(
        public.test_time_estimate(
            tc.skill_key,
            CASE WHEN tc.skill_key = 'dictation' THEN v_dict_difficulty END
        ) * GREATEST(0,
            tc.target_text::int - COALESCE((v_state.completed_counts->>tc.skill_key)::int, 0)
        )
    ), 0)
      INTO v_test_minutes_total
    FROM jsonb_each_text(v_state.target_counts) AS tc(skill_key, target_text)
    WHERE tc.skill_key <> ALL(v_excluded);   -- session-modules

    -- session-budget: the in-budget practice pool exists only when v_practice_in
    -- (budget_scope = 'tests_and_review' AND 'practice' not excluded). This subsumes the
    -- session-modules `IF 'practice' = ANY(v_excluded)` wrap.
    v_practice_minutes_total := CASE WHEN v_practice_in THEN GREATEST(0,
        ROUND(v_state.practice_target_minutes::numeric)::int
        - v_state.practice_completed_maint_min
        - v_state.practice_completed_acq_min
    ) ELSE 0 END;

    IF v_test_minutes_total + v_practice_minutes_total > 0 THEN
        v_practice_budget := v_today_budget * v_practice_minutes_total
                              / (v_test_minutes_total + v_practice_minutes_total);
    ELSE
        v_practice_budget := 0;
    END IF;
    v_test_budget        := v_today_budget - v_practice_budget;

    -- session-budget: "started" per ADR-033 / Quota semantics. Computed BEFORE v_s_words:
    -- words already started today must not be re-planned by a same-day rebuild.
    v_local_midnight := (p_date::timestamp AT TIME ZONE public.resolve_plan_timezone(v_plan.timezone));
    v_lw            := public.ladder_new_word_state(p_user_id, p_language_id, v_local_midnight);
    v_unstarted     := COALESCE((v_lw->>'unstarted')::int, 0);          -- U
    v_started_today := COALESCE((v_lw->>'started_today')::int, 0);      -- ST

    -- session-budget: the practice side is assigned DIRECTLY (reviews first, then whole new
    -- words, then the rest goes back to tests); the practice candidate INSERTs and the
    -- practice greedy loop no longer exist. "Reviews first, new words second" is a priority
    -- order, not a value ranking.
    -- 1. due reviews first (due = overdue + due today, in minutes)
    v_r_main  := CASE WHEN v_practice_in THEN LEAST(v_practice_budget, v_due_min) ELSE 0 END;
    -- 2. then new words, as many whole words as fit in what is left of the share; after a
    --    supply check, never plan more than the words that can actually be served
    v_s_words := CASE WHEN v_practice_in AND v_new_eff > 0 AND v_mpnw > 0
                      THEN GREATEST(0, LEAST(
                                 GREATEST(0, v_new_eff - v_started_today),
                                 GREATEST(0, v_new_eff - v_started_today - v_prior_shortfall),
                                 FLOOR((v_practice_budget - v_r_main) / v_mpnw)::int))
                      ELSE 0 END;
    v_a_main  := v_s_words * v_mpnw;
    -- 3. unused share minutes return to tests (the budget is never left empty)
    v_returned    := GREATEST(0, v_practice_budget - v_r_main - v_a_main);
    v_test_budget := v_test_budget + v_returned;
    v_maint_min   := ROUND(v_r_main)::int;   -- runner reads practice_maintenance_min
    v_acq_min     := ROUND(v_a_main)::int;   -- runner reads practice_acquisition_min

    -- session-budget: shortfall seed = words still to admit at build time (ladder intake
    -- overwrites it with the final unmet count). The ST term nets out words already started
    -- today (computed above, before v_s_words).
    v_shortfall     := GREATEST(0, v_new_eff - (v_unstarted + v_started_today));
    IF v_prior_checked THEN
        v_shortfall := v_prior_shortfall;   -- a real supply check outranks the seed
    END IF;

    v_upper_cap_test      := v_test_budget * 1.5;
    v_upper_cap_practice  := 0;   -- unused since the practice greedy loop was removed

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

    -- One candidate row per still-outstanding slot of every plannable skill.
    -- TASK-714: surface skills get kind='surface' so the hydration loop below
    -- can route them away from get_recommended_tests; the BUDGET loop treats
    -- both kinds identically, which is the whole point — they compete for the
    -- same minutes (now the test/surface side's minutes specifically —
    -- TASK-732).
    -- TASK-715: dictation is sized through the 2-arg, tier-aware estimate.
    INSERT INTO pg_temp.candidates (kind, skill, mins, per_min_value)
    SELECT CASE WHEN skill_key = ANY(c_surface_skills) THEN 'surface' ELSE 'test' END,
           skill_key,
           public.test_time_estimate(
               skill_key,
               CASE WHEN skill_key = 'dictation' THEN v_dict_difficulty END
           ),
           COALESCE((v_state.skill_values->>skill_key)::numeric, 0.10)
             / NULLIF(public.test_time_estimate(
                   skill_key,
                   CASE WHEN skill_key = 'dictation' THEN v_dict_difficulty END
               ), 0)
    FROM jsonb_each_text(v_state.target_counts) AS tc(skill_key, target_text),
         generate_series(1,
           GREATEST(0,
             target_text::int
             - COALESCE((v_state.completed_counts->>skill_key)::int, 0)
           )
         )
    WHERE skill_key <> ALL(v_excluded);   -- session-modules

    -- session-budget: the 'maint' / 'acq' candidate INSERTs are deleted (practice side is
    -- assigned directly above; no 10-minute chunking, no extra-pool candidates).

    -- Per-skill BUDGETED test-slot counts (requested_counts) are recorded in the
    -- SAME greedy pass that computes the budget totals (TASK-710). Created before
    -- the loop so the selection can populate it inline; the TASK-705 carry-over
    -- and TASK-704 retry blocks below still consume a fully-populated table.
    DROP TABLE IF EXISTS pg_temp.skill_counts;
    CREATE TEMP TABLE pg_temp.skill_counts (
        skill text PRIMARY KEY,
        count int NOT NULL
    ) ON COMMIT DROP;

    -- TASK-714: same shape, for surface skills. Kept separate from
    -- skill_counts so the hydration loop, the retry/replay guards and the
    -- chosen_tests bookkeeping below stay exactly as TASK-702/704/705 left
    -- them — a surface can never be mistaken for a test row.
    DROP TABLE IF EXISTS pg_temp.surface_budget;
    CREATE TEMP TABLE pg_temp.surface_budget (
        skill text PRIMARY KEY,
        count int NOT NULL
    ) ON COMMIT DROP;

    -- TASK-732: test/surface candidates now rank ONLY against each other,
    -- bounded by v_test_budget/v_upper_cap_test instead of the shared
    -- v_today_budget/v_upper_cap. Ordering and spacing-cost logic unchanged.
    FOR v_cand IN
        SELECT * FROM pg_temp.candidates
        WHERE kind IN ('test', 'surface')
        ORDER BY per_min_value DESC, seq
    LOOP
        EXIT WHEN v_used_min_test >= v_test_budget;
        CONTINUE WHEN v_used_min_test + v_cand.mins > v_upper_cap_test;

        v_spacing_cost := 0;
        IF NOT (v_cand.skill = ANY(v_skills_today)) THEN
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
        ELSE -- 'surface'
            IF NOT (v_cand.skill = ANY(v_skills_today)) THEN
                v_skills_today := array_append(v_skills_today, v_cand.skill);
            END IF;
            INSERT INTO pg_temp.surface_budget (skill, count) VALUES (v_cand.skill, 1)
            ON CONFLICT (skill) DO UPDATE SET count = pg_temp.surface_budget.count + 1;
        END IF;
        v_used_min_test := v_used_min_test + v_cand.mins;
        v_objective      := v_objective + (v_cand.per_min_value * v_cand.mins)
                                         - v_spacing_cost;
    END LOOP;

    -- session-budget: the TASK-732 practice greedy loop is deleted (see the direct
    -- assignment above). The practice minutes are v_maint_min + v_acq_min.
    v_used_min_practice := v_maint_min + v_acq_min;
    v_used_min := v_used_min_test + v_used_min_practice;

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
    --
    -- Surfaces need no equivalent: their completion lives in completed_blocks,
    -- which the ON CONFLICT branch never touches, and the runner derives
    -- per-block is_completed from it directly.
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
          AND dtt.type_code <> ALL(v_excluded)                                         -- session-modules
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
    -- word_upload slot (wiki/tasklist/word-list-import.plan.md Step 6).
    -- Reserve AT MOST ONE slot for the most-recently-matched, not-yet-
    -- surfaced watchlist test. Mirrors the TASK-704 retry block immediately
    -- above: single LIMIT-1 pick, guarded against anything already in
    -- chosen_tests (TASK-705 carry-over + retry), decrements skill_counts to
    -- borrow a budgeted 'new' slot of the matched test's skill when that
    -- skill is budgeted today (additive [+1 over budget] otherwise). Runs
    -- BEFORE hydration for the same reason retry does: so the borrow is
    -- visible to the skill_counts the hydration loop below consumes.
    --
    -- Skill resolution: a watchlisted match is a bare test_id (Step 4/5 only
    -- know it satisfied a vocab_sense_ids overlap, not which test_type to
    -- serve it as), so — like get_recommended_tests/get_replay_tests do for
    -- their own candidates — the skill is chosen as whichever active
    -- test_skill_ratings row for that test sits closest to the user's
    -- current ELO in that skill (defaulting unrated skills to 1200, same as
    -- get_recommended_tests).
    --
    -- Eligibility (all must hold):
    --   * wl.active = true, wl.language_id = p_language_id (this build is
    --     already scoped to one language; a match belongs to that scope only).
    --   * wl.last_matched_test_id IS NOT NULL (Step 4/5 found a match).
    --   * not already attempted by this user (surfacing an already-done test
    --     serves no purpose — mirrors get_recommended_tests' NOT EXISTS guard).
    --   * not already present in today's chosen_tests (no double-booking a
    --     retry/carried-over slot onto the same test_id).
    --   * premium gating identical to get_recommended_tests/get_replay_tests
    --     (free-tier tests always eligible; non-free only for premium users).
    --   * "not already surfaced" per the header comment: surfaced_at IS NULL
    --     OR surfaced_at was stamped earlier TODAY (same-day re-entrancy safe).
    -- Tie-break when more than one watchlist row qualifies: most recently
    -- matched first (freshest word upload takes the single daily slot).
    --
    -- On a hit: borrow/extend the budget exactly like retry, insert the
    -- chosen_tests row with slot_type = 'word_upload', and stamp
    -- last_matched_surfaced_at (COALESCE-guarded so a same-day re-solve does
    -- not keep sliding the "first surfaced" timestamp forward).
    -- ---------------------------------------------------------------
    DECLARE
        v_wordup_watchlist_id bigint;
        v_wordup_test_id      uuid;
        v_wordup_skill        text;
        v_wordup_tier_code    text;
        v_wordup_is_premium   boolean;
    BEGIN
        SELECT st.tier_code INTO v_wordup_tier_code
        FROM public.users u
        JOIN public.dim_subscription_tiers st ON st.id = u.subscription_tier_id
        WHERE u.id = p_user_id;
        v_wordup_is_premium := (v_wordup_tier_code NOT ILIKE '%free%');

        SELECT wl.id, wl.last_matched_test_id, dtt.type_code
          INTO v_wordup_watchlist_id, v_wordup_test_id, v_wordup_skill
        FROM public.user_word_watchlist wl
        JOIN public.tests t ON t.id = wl.last_matched_test_id
        JOIN public.test_skill_ratings tsr ON tsr.test_id = t.id
        JOIN public.dim_test_types dtt ON dtt.id = tsr.test_type_id AND dtt.is_active = true
        LEFT JOIN public.user_skill_ratings usr
               ON usr.user_id = wl.user_id
              AND usr.language_id = wl.language_id
              AND usr.test_type_id = tsr.test_type_id
        WHERE wl.user_id = p_user_id
          AND wl.language_id = p_language_id
          AND wl.active = true
          AND wl.last_matched_test_id IS NOT NULL
          AND (
              wl.last_matched_surfaced_at IS NULL
              OR wl.last_matched_surfaced_at::date = p_date
          )
          AND t.is_active = true
          AND (
              t.tier = 'free-tier'
              OR (t.tier != 'free-tier' AND v_wordup_is_premium)
          )
          AND NOT EXISTS (
              SELECT 1 FROM public.test_attempts ta
              WHERE ta.user_id = p_user_id AND ta.test_id = t.id
          )
          AND wl.last_matched_test_id NOT IN (SELECT ct.test_id FROM pg_temp.chosen_tests ct)
          AND dtt.type_code <> ALL(v_excluded)                                         -- session-modules
        ORDER BY wl.last_matched_at DESC NULLS LAST,
                 ABS(tsr.elo_rating - COALESCE(usr.elo_rating, 1200)) ASC
        LIMIT 1;

        IF v_wordup_test_id IS NOT NULL THEN
            -- Free one budgeted 'new' slot of this skill if it is budgeted today.
            UPDATE pg_temp.skill_counts
               SET count = count - 1
             WHERE skill = v_wordup_skill AND count > 0;
            DELETE FROM pg_temp.skill_counts WHERE count <= 0;

            INSERT INTO pg_temp.chosen_tests (test_id, skill, slot_type)
            VALUES (v_wordup_test_id, v_wordup_skill, 'word_upload');

            UPDATE public.user_word_watchlist
               SET last_matched_surfaced_at = COALESCE(last_matched_surfaced_at, NOW())
             WHERE id = v_wordup_watchlist_id;
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

    -- ---------------------------------------------------------------
    -- Hydrate SURFACE slots (TASK-714). Each surface is clamped to what its
    -- own pool can actually supply today, so a budgeted-but-unsupplied slot
    -- shows up as a shortfall (hydrated < requested) instead of being emitted
    -- as a block the learner opens to find empty — the F3 failure shape.
    --
    --   flashcards       -> ceil(due cards / 15). "Due" is due_date <= p_date,
    --                       the same predicate GET /api/flashcards/due uses.
    --   dual_translation -> passages GET /api/dual-translation/next can serve:
    --                       status='active' (NOT 'approved' — that value does
    --                       not exist in this table), source_kind =
    --                       'test_transcript', sourced from a test the learner
    --                       has attempted, and carrying an L1 reference for
    --                       their resolved L1 (users.native_language_id, else
    --                       English=2 per routes/dual_translation.py).
    --
    -- Each predicate deliberately mirrors its serving endpoint rather than
    -- approximating it. A resolver that hydrates against a DIFFERENT rule than
    -- the route serves produces phantom shortfalls (or, worse, blocks the
    -- runner mounts and cannot fill) — the same class of mismatch F3 was.
    -- Note /next does not exclude already-submitted passages, so neither does
    -- this: excluding them here would report a shortfall for a surface the
    -- route would happily serve.
    -- ---------------------------------------------------------------
    DROP TABLE IF EXISTS pg_temp.surface_counts;
    CREATE TEMP TABLE pg_temp.surface_counts (
        skill     text PRIMARY KEY,
        requested int NOT NULL,
        hydrated  int NOT NULL
    ) ON COMMIT DROP;

    INSERT INTO pg_temp.surface_counts (skill, requested, hydrated)
    SELECT sb.skill,
           sb.count,
           LEAST(
               sb.count,
               CASE sb.skill
                   WHEN 'flashcards' THEN (
                       SELECT CEIL(COUNT(*)::numeric / c_cards_per_block)::int
                       FROM public.user_flashcards uf
                       WHERE uf.user_id = p_user_id
                         AND uf.language_id = p_language_id
                         AND uf.due_date <= p_date
                   )
                   WHEN 'dual_translation' THEN (
                       SELECT COUNT(*)::int
                       FROM public.dt_passage dp
                       WHERE dp.l2_language_id = p_language_id
                         AND dp.status = 'active'
                         AND dp.source_kind = 'test_transcript'
                         AND EXISTS (
                             SELECT 1 FROM public.test_attempts ta
                             WHERE ta.user_id = p_user_id
                               AND ta.test_id = dp.source_ref_id
                         )
                         AND EXISTS (
                             SELECT 1 FROM public.dt_passage_reference r
                             WHERE r.passage_id = dp.id
                               AND r.l1_language_id = COALESCE(
                                   (SELECT u.native_language_id FROM public.users u
                                     WHERE u.id = p_user_id),
                                   2
                               )
                         )
                   )
                   ELSE 0
               END
           )
    FROM pg_temp.surface_budget sb;

    -- Shortfall bookkeeping (kept in daily_session_targets jsonb — no schema change).
    -- TASK-714: surface skills join requested/hydrated so the existing
    -- test_service._log_hydration_shortfalls WARNING covers them unchanged.
    SELECT COALESCE(jsonb_object_agg(skill, count), '{}'::jsonb)
      INTO v_requested_counts
    FROM (
        SELECT skill, count FROM pg_temp.skill_counts
        UNION ALL
        SELECT skill, requested FROM pg_temp.surface_counts
    ) req;

    -- hydrated_counts = primary (never-attempted / sentinel) fill ONLY, so a
    -- slot covered solely by replay still reads as a shortfall vs requested.
    -- NOT is_completed: retained same-day completions (TASK-705) are carried over,
    -- not freshly hydrated, so they must not mask (or inflate) this call's fill.
    SELECT COALESCE(jsonb_object_agg(skill, n), '{}'::jsonb)
      INTO v_hydrated_counts
    FROM (
        SELECT sc.skill, COALESCE(h.n, 0) AS n
        FROM pg_temp.skill_counts sc
        LEFT JOIN (
            SELECT skill, COUNT(*) AS n
            FROM pg_temp.chosen_tests
            WHERE slot_type = 'new' AND NOT is_completed
            GROUP BY skill
        ) h ON h.skill = sc.skill
        UNION ALL
        SELECT skill, hydrated FROM pg_temp.surface_counts
    ) hyd;

    SELECT COALESCE(jsonb_object_agg(skill, n), '{}'::jsonb)
      INTO v_replay_counts
    FROM (
        SELECT skill, COUNT(*) AS n
        FROM pg_temp.chosen_tests
        WHERE slot_type = 'replay' AND NOT is_completed
        GROUP BY skill
    ) rc;

    -- What the runner actually composes queue items from: hydrated surface
    -- slots only. routes/study_session.py reads this key.
    SELECT COALESCE(jsonb_object_agg(skill, hydrated), '{}'::jsonb)
      INTO v_surface_counts
    FROM pg_temp.surface_counts
    WHERE hydrated > 0;

    -- used_minutes now reflects HYDRATED test slots (new + replay) + hydrated
    -- surface slots + practice mins.
    -- TASK-715: dictation is priced at the tier of the test ACTUALLY placed,
    -- not the learner's expected tier, so this stays an honest account even
    -- when hydration lands a passage above or below their level.
    SELECT COALESCE(SUM(
        public.test_time_estimate(
            ct.skill,
            CASE WHEN ct.skill = 'dictation' THEN t.difficulty END
        )
    ), 0)
      INTO v_used_min_hyd
    FROM pg_temp.chosen_tests ct
    LEFT JOIN public.tests t ON t.id = ct.test_id;

    v_used_min_hyd := v_used_min_hyd
                    + COALESCE((
                        SELECT SUM(public.test_time_estimate(skill) * hydrated)
                        FROM pg_temp.surface_counts
                      ), 0)
                    + v_maint_min + v_acq_min;

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
            -- TASK-732: the budget split itself, for observability.
            'test_budget_minutes',      v_test_budget,
            'practice_budget_minutes',  v_practice_budget,
            'used_minutes',             v_used_min_hyd,
            'budgeted_minutes',         v_used_min,
            'requested_counts',         v_requested_counts,
            'hydrated_counts',          v_hydrated_counts,
            'replay_counts',            v_replay_counts,
            'surface_counts',           v_surface_counts,
            -- session-modules (edit 9): observability; the session route also reads it to gate the speed round.
            'excluded_modules',         to_jsonb(v_excluded),
            -- session-budget (ADR-033)
            'budget_scope',             v_scope,
            'new_words_quota',          v_quota,
            'new_words_effective',      v_new_eff,
            'new_words_in_budget',      v_s_words,
            'new_words_shortfall',      v_shortfall,
            'new_words_supply_checked', v_prior_checked,
            'new_words_supply_checked_e', CASE WHEN v_prior_checked THEN to_jsonb(v_prior_checked_e) END,
            'governor_level',           v_level,
            'review_due_minutes',       v_due_min,
            'review_main_minutes',      v_maint_min,
            'new_word_main_minutes',    v_acq_min,
            'returned_to_tests_minutes', v_returned
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
    -- after a same-day rebuild (TASK-705). Surfaces are absent by design: they
    -- have no test_id and their completion lives in completed_blocks.
    INSERT INTO public.daily_test_load_items (load_id, test_id, is_completed)
    SELECT v_load_id, ct.test_id, ct.is_completed
    FROM pg_temp.chosen_tests ct
    ON CONFLICT (load_id, test_id) DO NOTHING;

    RETURN jsonb_build_object(
        'load_id',                v_load_id,
        'load_date',              p_date,
        'week_start',             v_week_start,
        'today_budget_minutes',   v_today_budget,
        'test_budget_minutes',    v_test_budget,
        'practice_budget_minutes', v_practice_budget,
        'used_minutes',           v_used_min_hyd,
        'budgeted_minutes',       v_used_min,
        'objective_value',        v_objective,
        'test_ids',               v_test_ids,
        'skills_today',           to_jsonb(v_skills_today),
        'requested_counts',       v_requested_counts,
        'hydrated_counts',        v_hydrated_counts,
        'replay_counts',          v_replay_counts,
        'surface_counts',         v_surface_counts,
        'practice_maintenance_min', v_maint_min,
        'practice_acquisition_min', v_acq_min,
        'excluded_modules',         to_jsonb(v_excluded),
        'budget_scope',             v_scope,
        'new_words_quota',          v_quota,
        'new_words_effective',      v_new_eff,
        'new_words_in_budget',      v_s_words,
        'new_words_shortfall',      v_shortfall,
        'new_words_supply_checked', v_prior_checked,
        'new_words_supply_checked_e', CASE WHEN v_prior_checked THEN to_jsonb(v_prior_checked_e) END,
        'governor_level',           v_level,
        'review_due_minutes',       v_due_min,
        'review_main_minutes',      v_maint_min,
        'new_word_main_minutes',    v_acq_min,
        'returned_to_tests_minutes', v_returned
    );
END $function$;
