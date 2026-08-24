-- TASK-714 — build_daily_session: flashcards + dual_translation as plannable
--   surfaces. Implements [[decisions/ADR-021-plannable-surface-boundary]].
--   Folds forward TASK-702 / 704 / 705 / 710 unchanged; adds TASK-715's
--   tier-aware dictation estimate at both the budget and accounting ends.
-- =============================================================================
-- PROBLEM (F11 / ADR-021)
--   FSRS flashcard reviews and Dual Translation are real, recurring study time
--   that the weekly budget could not see. Neither is a dim_test_types row and
--   neither resolves to an ELO-rated `tests` row, so they could not be
--   expressed in target_counts at all — the plan therefore systematically
--   UNDER-COUNTED study load and scheduled on top of time the learner had
--   already spent. Flashcards in particular are daily by construction, so the
--   gap was systematic rather than occasional.
--
-- APPROACH — a plannable KIND, not two more test types.
--   target_counts gains 'flashcards' / 'dual_translation' keys like any other
--   skill (Tier B does not care what a key means), but the resolver splits its
--   candidate rows into kind='test' and kind='surface'. Surface candidates are
--   budgeted by the same greedy value-per-minute loop and compete for the same
--   minutes, then HYDRATE against their own pools instead of
--   get_recommended_tests:
--       flashcards       -> user_flashcards due today (15 cards == 1 slot)
--       dual_translation -> approved dt_passage rows the learner has not yet
--                           submitted against
--   They never enter chosen_tests, so test_ids, daily_test_load_items, the ELO
--   path and the retry/replay machinery are all untouched.
--
--   One budgeted slot == one queue item, so target_counts stays homogeneous
--   (a count of slots) and test_time_estimate stays homogeneous (minutes per
--   slot). Seeds live in task715_test_time_estimate_tiered.sql: flashcards 7.0,
--   dual_translation 12.0 — explicitly, because the SQL fallback is a silent
--   ELSE 5.0 (ADR-021).
--
--   listening_lab and mystery are deliberately NOT here (ADR-021): both ARE
--   dim_test_types rows, but that is a modelling artefact, not an intent to
--   schedule them. tests/test_plannable_surfaces.py pins their absence.
--
-- SHORTFALL TELEMETRY (extends TASK-702 to the new kinds)
--   requested_counts / hydrated_counts now include surface skills, so the
--   existing test_service._log_hydration_shortfalls WARNING fires unchanged
--   when e.g. 3 flashcard blocks are budgeted but only 20 cards are due
--   (2 blocks' worth). That is a REAL shortfall — the learner cannot review
--   cards that are not due — and it is exactly the class of silent drop F3 was
--   about. surface_counts (hydrated) is what the runner composes from.
--
-- CARRIED FORWARD UNCHANGED from task702_build_daily_session.sql (archived by
-- this change): TASK-710 single-pass budgeting, TASK-705 same-day re-entrancy,
-- TASK-704 retry slot, TASK-702 replay fallback + shortfall counts.
--
-- TASK-715 coupling: the dictation estimate is now tier-aware, so
--   * the BUDGET pass sizes a dictation slot at the learner's EXPECTED tier
--     (their dictation ELO matched to dim_complexity_tiers.initial_elo), and
--   * the HYDRATED accounting sizes it at the tier of the test actually
--     placed.
--   Shipping the per-tier word cap without this would let an advanced
--   learner's day be budgeted at 6 min for a passage that takes 20.
--
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
    -- same minutes.
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

    -- TASK-714: same shape, for surface skills. Kept separate from
    -- skill_counts so the hydration loop, the retry/replay guards and the
    -- chosen_tests bookkeeping below stay exactly as TASK-702/704/705 left
    -- them — a surface can never be mistaken for a test row.
    DROP TABLE IF EXISTS pg_temp.surface_budget;
    CREATE TEMP TABLE pg_temp.surface_budget (
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
        IF v_cand.kind IN ('test','surface')
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
        ELSIF v_cand.kind = 'surface' THEN
            IF NOT (v_cand.skill = ANY(v_skills_today)) THEN
                v_skills_today := array_append(v_skills_today, v_cand.skill);
            END IF;
            INSERT INTO pg_temp.surface_budget (skill, count) VALUES (v_cand.skill, 1)
            ON CONFLICT (skill) DO UPDATE SET count = pg_temp.surface_budget.count + 1;
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
            'used_minutes',             v_used_min_hyd,
            'budgeted_minutes',         v_used_min,
            'requested_counts',         v_requested_counts,
            'hydrated_counts',          v_hydrated_counts,
            'replay_counts',            v_replay_counts,
            'surface_counts',           v_surface_counts
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
        'practice_acquisition_min', v_acq_min
    );
END $function$;
