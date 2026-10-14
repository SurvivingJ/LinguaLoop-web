-- =============================================================================
-- Weekly minutes: current-week backfill of public.study_time_ledger (TASK-886, ADR-035)
--
-- *** REQUIRES EXPLICIT USER APPROVAL TO APPLY LIVE, and only AFTER
-- *** migrations/study_time_ledger.sql is applied (TASK-896 order: migration, code, backfill).
-- *** Report the dry-run counts below to the user before the write.
--
-- Scope: the learner-local CURRENT week per (user, language) only. Older weeks are not
-- backfilled. Local week = week_start_for(plan_local_date(user, language, <ts>)) compared
-- against week_start_for(plan_local_date(user, language)) (user_study_plans.timezone, UTC fallback).
--
-- Sources and keys (equal to the live credit keys, so replays and the first live
-- credit never double count; ON CONFLICT DO NOTHING):
--   test_attempts      -> ('test_attempts',     id::text)  kind 'test', or 'drill' when
--                          dim_test_types.type_code IN ('classifier_drill','counter_drill').
--                          seconds = clamp(round(duration_ms/1000), 1, 1200); rows with NULL
--                          or <= 0 duration_ms are skipped (measured time only, no estimate).
--                          Time = created_at (attempt submit time).
--   exercise_attempts  -> ('exercise_attempts', id::text)  kind 'practice'.
--                          seconds = round(time_taken_ms/1000) when 0 < ms <= 300000, else the
--                          estimate (mirrors PracticeSessionService._effective_practice_seconds):
--                          COALESCE(round(dim_exercise_types.expected_seconds_p50),
--                          dim_exercise_types.expected_seconds, 45), clamped 1..300. NOTE: the
--                          live path uses the item's served expected_seconds; the type-level
--                          value is the best available approximation here.
--                          Language: exercise_attempts.sense_id -> dim_word_senses.vocab_id ->
--                          dim_vocabulary.language_id; rows with NULL sense_id are skipped.
-- NOT backfilled: flashcard and dual_translation (no stored timing).
--
-- Columns used (from repo DDL: create_all_tables.sql, exercise_scheduling.sql,
-- vocabulary_ladder_schema.sql, phase13_test_attempts_duration.sql, phase12_dim_exercise_types.sql;
-- the live information_schema check could NOT be run from this session, see TASK-886 note):
--   test_attempts(id, user_id, language_id, test_type_id, duration_ms, created_at)
--   dim_test_types(id, type_code)
--   exercise_attempts(id, user_id, sense_id, exercise_type, time_taken_ms, created_at)
--   dim_exercise_types(type_code, expected_seconds, expected_seconds_p50)
--   dim_word_senses(id, vocab_id), dim_vocabulary(id, language_id)
--
-- Idempotent: a second run inserts 0 rows. No BEGIN/COMMIT here (each INSERT is atomic and
-- safe to re-run); a NOTICE reports rows inserted per source.
-- =============================================================================

-- ---- DRY RUN (read-only; aggregates only). Uncomment to report counts before the write ----
-- WITH cand AS (
--   SELECT CASE WHEN dtt.type_code IN ('classifier_drill','counter_drill') THEN 'drill' ELSE 'test' END AS kind,
--          LEAST(1200, GREATEST(1, round(ta.duration_ms / 1000.0)))::int AS seconds
--   FROM public.test_attempts ta
--   JOIN public.dim_test_types dtt ON dtt.id = ta.test_type_id
--   WHERE ta.duration_ms > 0
--     AND ta.created_at >= now() - interval '9 days'
--     AND public.week_start_for(public.plan_local_date(ta.user_id, ta.language_id, ta.created_at))
--       = public.week_start_for(public.plan_local_date(ta.user_id, ta.language_id))
--   UNION ALL
--   SELECT 'practice',
--          LEAST(300, GREATEST(1, CASE WHEN ea.time_taken_ms > 0 AND ea.time_taken_ms <= 300000
--                 THEN round(ea.time_taken_ms / 1000.0)
--                 ELSE COALESCE(round(det.expected_seconds_p50), det.expected_seconds, 45) END))::int
--   FROM public.exercise_attempts ea
--   JOIN public.dim_word_senses dws ON dws.id = ea.sense_id
--   JOIN public.dim_vocabulary dv ON dv.id = dws.vocab_id
--   LEFT JOIN public.dim_exercise_types det ON det.type_code = ea.exercise_type
--   WHERE ea.created_at >= now() - interval '9 days'
--     AND public.week_start_for(public.plan_local_date(ea.user_id, dv.language_id::smallint, ea.created_at))
--       = public.week_start_for(public.plan_local_date(ea.user_id, dv.language_id::smallint))
-- )
-- SELECT kind, count(*) AS rows, sum(seconds) AS seconds FROM cand GROUP BY kind ORDER BY kind;

DO $backfill$
DECLARE
    v_tests     integer;
    v_practice  integer;
BEGIN
    -- Tests and drills. created_at >= now() - 9 days is a cheap pre-filter: any local week
    -- start is at most 7 days + 14h (UTC+14) before now.
    INSERT INTO public.study_time_ledger
        (user_id, language_id, week_start_date, kind, seconds, source_table, source_id, credited_at)
    SELECT ta.user_id,
           ta.language_id,
           public.week_start_for(public.plan_local_date(ta.user_id, ta.language_id)),
           CASE WHEN dtt.type_code IN ('classifier_drill', 'counter_drill') THEN 'drill' ELSE 'test' END,
           LEAST(1200, GREATEST(1, round(ta.duration_ms / 1000.0)))::int,
           'test_attempts',
           ta.id::text,
           now()
    FROM public.test_attempts ta
    JOIN public.dim_test_types dtt ON dtt.id = ta.test_type_id
    WHERE ta.duration_ms > 0
      AND ta.created_at >= now() - interval '9 days'
      AND public.week_start_for(public.plan_local_date(ta.user_id, ta.language_id, ta.created_at))
        = public.week_start_for(public.plan_local_date(ta.user_id, ta.language_id))
    ON CONFLICT (kind, source_table, source_id) DO NOTHING;
    GET DIAGNOSTICS v_tests = ROW_COUNT;

    -- Vocabulary practice.
    INSERT INTO public.study_time_ledger
        (user_id, language_id, week_start_date, kind, seconds, source_table, source_id, credited_at)
    SELECT ea.user_id,
           dv.language_id::smallint,
           public.week_start_for(public.plan_local_date(ea.user_id, dv.language_id::smallint)),
           'practice',
           LEAST(300, GREATEST(1,
               CASE WHEN ea.time_taken_ms > 0 AND ea.time_taken_ms <= 300000
                    THEN round(ea.time_taken_ms / 1000.0)
                    ELSE COALESCE(round(det.expected_seconds_p50), det.expected_seconds, 45)
               END))::int,
           'exercise_attempts',
           ea.id::text,
           now()
    FROM public.exercise_attempts ea
    JOIN public.dim_word_senses dws ON dws.id = ea.sense_id
    JOIN public.dim_vocabulary dv ON dv.id = dws.vocab_id
    LEFT JOIN public.dim_exercise_types det ON det.type_code = ea.exercise_type
    WHERE ea.created_at >= now() - interval '9 days'
      AND public.week_start_for(public.plan_local_date(ea.user_id, dv.language_id::smallint, ea.created_at))
        = public.week_start_for(public.plan_local_date(ea.user_id, dv.language_id::smallint))
    ON CONFLICT (kind, source_table, source_id) DO NOTHING;
    GET DIAGNOSTICS v_practice = ROW_COUNT;

    RAISE NOTICE 'study_time_ledger backfill: % test/drill rows, % practice rows inserted',
        v_tests, v_practice;
END
$backfill$;
