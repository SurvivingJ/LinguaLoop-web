-- ============================================================================
-- Phase 13 — Study Plans — wipe user-state tables for pre-launch flip
-- Date: 2026-05-21
--
-- ONE-SHOT script. Run ONCE against the target DB right before flipping
-- Config.STUDY_PLAN_ENABLED = True. Supersedes the originally-planned
-- "non-destructive backfill" approach per plan revision R4.2:
--
--   "Pre-launch wipe; no backfill needed. Target environment is dev/pre-
--    launch with no real-user history to preserve. Plan-creation happens
--    lazily — at onboarding via apply_study_plan_template."
--
-- WHAT GETS WIPED:
--   All per-user state and per-day session caches. After this runs, every
--   ELO rating, every BKT p_known, every FSRS card, every ladder ring, every
--   attempt history row, and every daily-load row is gone. Users that
--   re-sign-up (or re-onboard) start completely fresh.
--
-- WHAT DOES NOT GET WIPED:
--   Reference data — dim_*, dim_languages, dim_study_plan_templates,
--   dim_practice_modes, dim_exercise_types, dim_test_types, dim_word_senses,
--   dim_vocabulary, dim_grammar_patterns, dim_classifiers — and content —
--   tests, questions, exercises, word_assets, packs, pack_key_words,
--   conversations, mysteries, etc. Auth (auth.users + public.users)
--   intentionally untouched: the wipe is about LEARNING state, not identity.
--
-- AFTER THIS RUNS:
--   - First daily-load request per (user, language) triggers
--     get_or_create_daily_load → has no user_study_plans row → falls
--     through to legacy _compute_daily_load. Users without plans keep
--     functioning.
--   - Users who go through onboarding (or PUT /api/study-plan with a
--     template_id) get a user_study_plans row → next daily-load uses
--     build_daily_session.
--   - Sunday 23:00 UTC cron iterates user_study_plans rows; computes the
--     first weekly_plan_states entry for each.
--
-- ROLLBACK:
--   None. This is destructive. If you need to roll back the rollout, restore
--   from a pre-wipe backup and set Config.STUDY_PLAN_ENABLED = False. The
--   merger code itself is non-destructive to a restored DB (Phase 12 just
--   adds tables / columns / RPCs).
--
-- See wiki/features/study-plans.tech.md section "Migration sequence" /
-- "Rollout" and ADR-013.
-- ============================================================================

BEGIN;

-- Single TRUNCATE … CASCADE statement so foreign-key cycles don't matter and
-- the operation is atomic. RESTART IDENTITY resets the bigint sequences so
-- post-wipe IDs start from 1 again — useful for cleaner debug logs.
TRUNCATE TABLE
    public.user_skill_ratings,
    public.user_vocabulary_knowledge,
    public.user_word_ladder,
    public.user_flashcards,
    public.user_exercise_sessions,
    public.user_exercise_history,
    public.daily_test_load_items,
    public.daily_test_loads,
    public.test_attempts,
    public.exercise_attempts,
    public.user_study_plans,
    public.weekly_plan_states
RESTART IDENTITY CASCADE;

-- Sanity log — pg_log will record the row counts (all zero) so an operator
-- can confirm the wipe succeeded.
DO $$
DECLARE
    v_total bigint := 0;
    v_n     bigint;
BEGIN
    FOR v_n IN
        SELECT COUNT(*) FROM public.user_skill_ratings        UNION ALL
        SELECT COUNT(*) FROM public.user_vocabulary_knowledge UNION ALL
        SELECT COUNT(*) FROM public.user_word_ladder          UNION ALL
        SELECT COUNT(*) FROM public.user_flashcards           UNION ALL
        SELECT COUNT(*) FROM public.user_exercise_sessions    UNION ALL
        SELECT COUNT(*) FROM public.user_exercise_history     UNION ALL
        SELECT COUNT(*) FROM public.daily_test_load_items     UNION ALL
        SELECT COUNT(*) FROM public.daily_test_loads          UNION ALL
        SELECT COUNT(*) FROM public.test_attempts             UNION ALL
        SELECT COUNT(*) FROM public.exercise_attempts         UNION ALL
        SELECT COUNT(*) FROM public.user_study_plans          UNION ALL
        SELECT COUNT(*) FROM public.weekly_plan_states
    LOOP
        v_total := v_total + v_n;
    END LOOP;
    RAISE NOTICE '[phase13_wipe] all 12 user-state tables wiped; total rows now %', v_total;
END $$;

COMMIT;
